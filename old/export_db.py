import os
import sys
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from pymongo import MongoClient, UpdateOne
from pymongo.errors import ConnectionFailure
import certifi

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load env
load_dotenv()

class MongoDBExporter:
    def __init__(self):
        self.local_uri = os.getenv("MONGO_LOCAL_URI")
        self.atlas_uri = os.getenv("MONGO_ATLAS_URI")
        self.db_name = os.getenv("MONGO_DB_NAME", "scraping_archive")
        
        self.clients = []
        
        # Connect Local
        if self.local_uri:
            try:
                client = MongoClient(self.local_uri, serverSelectionTimeoutMS=2000)
                client.server_info() # Check connection
                self.clients.append(("local", client))
                logger.info(f"✅ Connected to Local MongoDB")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect to Local MongoDB: {e}")
                
        # Connect Atlas
        if self.atlas_uri:
            try:
                client = MongoClient(self.atlas_uri, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
                client.server_info()
                self.clients.append(("atlas", client))
                logger.info(f"✅ Connected to Atlas MongoDB")
            except Exception as e:
                logger.warning(f"⚠️ Could not connect to Atlas MongoDB: {e}")
                
        if not self.clients:
            logger.error("❌ No database connections available.")
            
    def close(self):
        for name, client in self.clients:
            client.close()
            logger.info(f"Closed {name} connection")

    def _get_file_type(self, filename: str) -> str:
        if "products_detailed" in filename: return "products_detailed"
        if "categories" in filename: return "categories"
        if "merged" in filename: return "merged"
        if "products" in filename and "detailed" not in filename: return "products"
        if "summary" in filename: return "summary"
        return "other"
        
    def _get_shop_from_path(self, path: Path) -> str:
        parts = path.parts
        # data/mytek/2025...
        if "merged" in parts: return "merged"
        if "state" in parts: return "state"
        for p in parts:
            if p in ["mytek", "spacenet", "tunisianet", "paranet"]:
                return p
        return "unknown"

    def export_collection(self, collection_name: str, data: List[Dict]):
        """
        Generic function to export a list of documents to a specific collection.
        Strategies:
        1. Products/Details/Merged -> Full Replace involved (Delete all -> Insert all) to ensure sync.
        2. History -> Upsert or Replace? History files grow, so Replace is safest to avoid duplicates.
        """
        if not data:
            return

        for name, client in self.clients:
            db = client[self.db_name]
            coll = db[collection_name]
            
            try:
                # Strategy: Full Replace (Simplest for consistency)
                # For very huge datasets (>1M), we might need bulk_write upserts, 
                # but for <100k, replacing the collection is fast and clean.
                
                # 1. Clear existing
                coll.delete_many({})
                
                # 2. Insert new (Batching handled by pymongo, but good to be explicit if huge)
                # Add metadata
                now = datetime.now()
                # If data is a list of dicts
                if isinstance(data, list):
                     # Add timestamp if missing
                    for d in data:
                        if isinstance(d, dict) and "_updated_at" not in d:
                            d["_updated_at"] = now
                    
                    if data:
                        coll.insert_many(data)
                        
                elif isinstance(data, dict):
                    # Single document (e.g. summary or analytics)
                    if "_updated_at" not in data:
                        data["_updated_at"] = now
                    coll.insert_one(data)

                logger.info(f"  -> Exported {len(data) if isinstance(data, list) else 1} items to '{collection_name}' on {name}")

            except Exception as e:
                logger.error(f"  ❌ Failed to export to '{collection_name}' on {name}: {e}")

    def export_shop_data(self, shop_name: str, latest_dir: Path):
        """
        Exports all relevant files for a shop to their respective collections.
        """
        logger.info(f"📦 Exporting full data for shop: {shop_name}")
        
        # Mapping: Filename -> Collection Suffix
        # e.g. products.json -> _products
        file_map = {
            "products.json": "_products",
            "products_detailed.json": "_details",
            "categories.json": "_categories",
            "products_summary.json": "_summary_products",
            "products_detailed_summary.json": "_summary_details"
        }
        
        for fname, suffix in file_map.items():
            fpath = latest_dir / fname
            if fpath.exists():
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    self.export_collection(f"{shop_name}{suffix}", data)
                except Exception as e:
                    logger.error(f"Failed to load {fname}: {e}")

        # Also look for History files in data/ directory (not inside timestamp dir usually)
        # History files are usually at data/products_price_history.json etc? 
        # Wait, track_history.py saves them to data/{shop}/...
        
        # Let's check where history files are. 
        # Based on track_history.py, they seem to be in data/{shop}/price_history.json etc.
        shop_base = latest_dir.parent # data/{shop}
        
        history_map = {
            "price_history.json": "_history_price",
            "availability_history.json": "_history_availability",
            "products_added.jsonl": "_products_added",
            "products_removed.jsonl": "_products_removed"
        }
        
        for fname, suffix in history_map.items():
            fpath = shop_base / fname
            if fpath.exists():
                try:
                    # Handle JSONL for added/removed
                    if fname.endswith(".jsonl"):
                        data = []
                        with open(fpath, 'r', encoding='utf-8') as f:
                            for line in f:
                                if line.strip():
                                    data.append(json.loads(line))
                    else:
                        with open(fpath, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            
                    # For history dicts (product_id -> history), we might want to flatten or save as one big doc?
                    # MongoDB has 16MB limit. If price_history.json is huge, this crashes.
                    # Better to convert Dict[ID, History] -> List[ {id: ID, history: History} ]
                    if isinstance(data, dict) and "history" not in fname: 
                         # This check is vague. Let's look at structure.
                         # price_history is { "id": [points] }. 
                         # We should convert to [ {"product_id": k, "history": v} ] for MongoDB!
                         flattened = [{"product_id": k, "data": v} for k, v in data.items()]
                         data = flattened
                    
                    self.export_collection(f"{shop_name}{suffix}", data)
                except Exception as e:
                     logger.error(f"Failed to export history {fname}: {e}")


def export_latest_run():
    """Finds the latest run directories for each shop and exports them."""
    exporter = MongoDBExporter()
    if not exporter.clients:
        return
        
    base_dir = Path("data")
    shops = ["mytek", "spacenet", "tunisianet"]
    
    # 1. Export Merged Data
    merged_dir = base_dir / "merged"
    if merged_dir.exists():
        logger.info("📦 Exporting Merged Data...")
        try:
            # Merged Products
            mp_path = merged_dir / "products_merged.json"
            if mp_path.exists():
                with open(mp_path, 'r', encoding='utf-8') as f:
                    exporter.export_collection("merged_products", json.load(f))
            
            # Merged Summary
            ms_path = merged_dir / "products_merged_summary.json"
            if ms_path.exists():
                with open(ms_path, 'r', encoding='utf-8') as f:
                     exporter.export_collection("merged_analytics", json.load(f))
                     
        except Exception as e:
            logger.error(f"Failed merged export: {e}")
    
    # 2. Export Shop Data
    for shop in shops:
        shop_dir = base_dir / shop
        if shop_dir.exists():
            # Find latest timestamp dir (2025-12-22...)
            subdirs = []
            for d in shop_dir.iterdir():
                if d.is_dir() and d.name[0].isdigit() and "_" in d.name:
                     subdirs.append(d)
            
            subdirs.sort(key=lambda x: x.name, reverse=True)
            
            if subdirs:
                latest = subdirs[0]
                exporter.export_shop_data(shop, latest)
    
    exporter.close()

if __name__ == "__main__":
    # If args, export specific path, else export latest
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
        exporter = MongoDBExporter()
        if path.is_file():
            exporter.export_file(path)
        elif path.is_dir():
            exporter.export_directory(path)
        exporter.close()
    else:
        export_latest_run()
