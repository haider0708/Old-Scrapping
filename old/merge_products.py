#!/usr/bin/env python3
"""
Product Merge System
====================

Merges product data from three sources (mytek, spacenet, tunisianet) based on SKU matching.
Only includes products that exist in ALL THREE sources.

Output: data/merged/products_merged.json (single file, replaces previous)
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# === Configuration ===
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MERGED_DIR = DATA_DIR / "merged"
MERGED_FILE = MERGED_DIR / "products_merged.json"

REQUIRED_SOURCES = ["mytek", "spacenet", "tunisianet"]


# === Setup Logger ===
def setup_logger() -> logging.Logger:
    """Setup logger for merge operations."""
    logger = logging.getLogger("merge_products")
    logger.setLevel(logging.INFO)
    logger.handlers = []
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger


logger = setup_logger()


# === Core Functions ===

def find_latest_product_file(source: str) -> Optional[Path]:
    """
    Find the latest products_detailed.json file for a given source.
    
    Args:
        source: Source name (mytek, spacenet, tunisianet)
        
    Returns:
        Path to latest file or None if not found
    """
    source_dir = DATA_DIR / source
    
    if not source_dir.exists():
        logger.error(f"Source directory not found: {source_dir}")
        return None
    
    # Find all timestamped directories (format: YYYY-MM-DD_HH-MM-SS)
    # Exclude special directories like 'html'
    timestamp_dirs = []
    for d in source_dir.iterdir():
        if not d.is_dir():
            continue
        # Skip hidden directories and 'html' directory
        if d.name.startswith('.') or d.name == 'html':
            continue
        # Check if directory name matches timestamp format (contains date pattern)
        if '-' in d.name and '_' in d.name:
            timestamp_dirs.append(d)
    
    if not timestamp_dirs:
        logger.error(f"No data directories found for {source}")
        return None
    
    # Sort by name (timestamp format YYYY-MM-DD_HH-MM-SS sorts correctly)
    latest_dir = sorted(timestamp_dirs, reverse=True)[0]
    
    product_file = latest_dir / "products_detailed.json"
    
    if not product_file.exists():
        logger.error(f"products_detailed.json not found in {latest_dir}")
        return None
    
    return product_file


def load_product_file(filepath: Path) -> Dict:
    """
    Load and validate a product JSON file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        Loaded JSON data
        
    Raises:
        ValueError: If file is invalid or missing required fields
    """
    # Try loading as standard JSON
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        if isinstance(data, list):
            # New format: keys are inside list items
            return {"products": data}  # Wrap in dict to match expected interface
        elif isinstance(data, dict) and "products" in data:
            # Old format
            return data
        else:
            raise ValueError(f"Invalid format in {filepath}: expected list or dict with 'products' key")
            
    except Exception as e:
        raise ValueError(f"Failed to load {filepath}: {e}")
    
    # Validate structure
    if isinstance(data, list):
        # New format: keys are inside list items
        return {"products": data}  # Wrap in dict to match expected interface
    elif isinstance(data, dict) and "products" in data:
        # Old format
        return data
    else:
        raise ValueError(f"Invalid format in {filepath}: expected list or dict with 'products' key")


def deduplicate_products(products: List[Dict], source_name: str) -> List[Dict]:
    """
    Remove duplicate products based on 'product_id'.
    Keep the first occurrence.
    
    Args:
        products: List of product dictionaries
        source_name: Name of the source (for logging)
        
    Returns:
        Deduplicated list of products
    """
    seen_ids = set()
    unique_products = []
    duplicates = 0
    
    for product in products:
        pid = product.get("product_id")
        
        # If no product_id, fallback to keeping it (or skipping? safely keep for now)
        if not pid:
            unique_products.append(product)
            continue
            
        if pid in seen_ids:
            duplicates += 1
            continue
            
        seen_ids.add(pid)
        unique_products.append(product)
    
    if duplicates > 0:
        logger.info(f"  {source_name}: Removed {duplicates} duplicate products (duplicate product_id)")
        
    return unique_products


def index_by_sku(products: List[Dict]) -> Dict[str, Dict]:
    """
    Create SKU → product mapping, excluding products without SKU.
    
    Args:
        products: List of product dictionaries
        
    Returns:
        Dictionary mapping SKU to product data
    """
    index = {}
    skipped = 0
    
    for product in products:
        sku = product.get("sku")
        
        # Skip products without SKU or with null SKU
        if not sku or sku is None:
            skipped += 1
            continue
        
        # Use first occurrence if duplicate SKUs exist
        if sku not in index:
            index[sku] = product
    
    if skipped > 0:
        logger.debug(f"Skipped {skipped} products without valid SKU")
    
    return index


def find_common_skus(mytek_index: Dict, spacenet_index: Dict, tunisianet_index: Dict) -> List[str]:
    """
    Find SKUs that exist in ALL THREE sources (intersection).
    
    Args:
        mytek_index: SKU index for mytek
        spacenet_index: SKU index for spacenet
        tunisianet_index: SKU index for tunisianet
        
    Returns:
        List of common SKUs (sorted)
    """
    mytek_skus = set(mytek_index.keys())
    spacenet_skus = set(spacenet_index.keys())
    tunisianet_skus = set(tunisianet_index.keys())
    
    # Intersection: SKUs present in all three
    common_skus = mytek_skus & spacenet_skus & tunisianet_skus
    
    logger.info(f"SKU counts - mytek: {len(mytek_skus)}, spacenet: {len(spacenet_skus)}, tunisianet: {len(tunisianet_skus)}")
    logger.info(f"Common SKUs (in all 3 sources): {len(common_skus)}")
    
    return sorted(common_skus)








def merge_product_data(sku: str, 
                      mytek_product: Dict, 
                      spacenet_product: Dict, 
                      tunisianet_product: Dict) -> Dict:
    """
    Merge product data from three sources into unified structure.
    
    Args:
        sku: Product SKU
        mytek_product: Product data from mytek
        spacenet_product: Product data from spacenet
        tunisianet_product: Product data from tunisianet
        
    Returns:
        Merged product dictionary
    """
    # Use title from first available source (preference: mytek > spacenet > tunisianet)
    title = mytek_product.get("title") or spacenet_product.get("title") or tunisianet_product.get("title")
    
    # Build merged product
    merged = {
        "sku": sku,
        "title": title,
        "shops": {
            "mytek": {
                "url": mytek_product.get("url"),
                "price": mytek_product.get("price"),
                "old_price": mytek_product.get("old_price"),
                "availability": mytek_product.get("availability"),
                "available": mytek_product.get("available"),
                "store_availability": mytek_product.get("store_availability"),
                "brand": mytek_product.get("brand"),
                "images": mytek_product.get("images", []),
                "specifications": mytek_product.get("specifications", {}),
                "scraped_at": mytek_product.get("scraped_at")
            },
            "spacenet": {
                "url": spacenet_product.get("url"),
                "price": spacenet_product.get("price"),
                "old_price": spacenet_product.get("old_price"),
                "availability": spacenet_product.get("availability"),
                "available": spacenet_product.get("available"),
                "store_availability": spacenet_product.get("store_availability"),
                "brand": spacenet_product.get("brand"),
                "images": spacenet_product.get("images", []),
                "specifications": spacenet_product.get("specifications", {}),
                "scraped_at": spacenet_product.get("scraped_at")
            },
            "tunisianet": {
                "url": tunisianet_product.get("url"),
                "price": tunisianet_product.get("price"),
                "old_price": tunisianet_product.get("old_price"),
                "availability": tunisianet_product.get("availability"),
                "available": tunisianet_product.get("available"),
                "store_availability": tunisianet_product.get("store_availability"),
                "brand": tunisianet_product.get("brand"),
                "images": tunisianet_product.get("images", []),
                "specifications": tunisianet_product.get("specifications", {}),
                "scraped_at": tunisianet_product.get("scraped_at")
            }
        }
    }
    
    return merged
    
def calculate_analytics(products: List[Dict]) -> Dict:
    """
    Calculate price and discount statistics from merged products.
    """
    stats = {
        "shops": {},
        "global": {
            "cheapest_basket": {"shop": None, "total_cost": float('inf')},
            "best_availability": {"shop": None, "count": 0}
        }
    }
    
    # Initialize shop stats
    shops = ["mytek", "spacenet", "tunisianet"]
    for shop in shops:
        stats["shops"][shop] = {
            "product_count": 0,
            "available_count": 0,
            "total_price": 0.0,
            "average_price": 0.0,
            "cheapest_product_count": 0, # Times this shop was cheapest
            "discount_count": 0,
            "total_discount_value": 0.0,
            "average_discount_percent": 0.0,
            "sum_discount_percent": 0.0 # Temp for calculation
        }
        
    for p in products:
        if not p:
            continue
            
        shop_data = p.get("shops", {})
        
        # Phase 1: Determine cheapest price for this product across all shops
        min_price = float('inf')
        cheapest_shops_for_item = []
        
        for shop, data in shop_data.items():
            price = data.get("price")
            if price is not None and isinstance(price, (int, float)) and price > 0:
                if price < min_price:
                    min_price = price
                    cheapest_shops_for_item = [shop]
                elif price == min_price:
                    cheapest_shops_for_item.append(shop)
                    
        # Phase 2: Update per-shop stats
        for shop, data in shop_data.items():
            if shop not in stats["shops"]: continue
            
            s_stats = stats["shops"][shop]
            s_stats["product_count"] += 1
            
            # Availability
            if data.get("available") is True:
                s_stats["available_count"] += 1
                
            # Price
            price = data.get("price")
            if price is not None and isinstance(price, (int, float)):
                s_stats["total_price"] += price
                
                # Cheapest count
                if shop in cheapest_shops_for_item:
                    s_stats["cheapest_product_count"] += 1
                
                # Discount
                old_price = data.get("old_price")
                if old_price is not None and isinstance(old_price, (int, float)) and old_price > price:
                    s_stats["discount_count"] += 1
                    discount = old_price - price
                    s_stats["total_discount_value"] += discount
                    if old_price > 0:
                         pct = (discount / old_price) * 100
                         s_stats["sum_discount_percent"] += pct

    # Phase 3: Finalize averages and globals
    best_avail_count = -1
    
    for shop in shops:
        s = stats["shops"][shop]
        count = s["product_count"]
        
        # Averages
        if count > 0:
            s["average_price"] = round(s["total_price"] / count, 3)
        
        if s["discount_count"] > 0:
             s["average_discount_percent"] = round(s["sum_discount_percent"] / s["discount_count"], 2)
        
        # Cleanup temp
        del s["sum_discount_percent"]
        s["total_discount_value"] = round(s["total_discount_value"], 3)
        s["total_price"] = round(s["total_price"], 3)
             
        # Global: Cheapest Basket (Total cost of buying ALL items at this shop)
        if s["total_price"] < stats["global"]["cheapest_basket"]["total_cost"] and count > 0:
             stats["global"]["cheapest_basket"]["total_cost"] = s["total_price"]
             stats["global"]["cheapest_basket"]["shop"] = shop
             
        # Global: Best Availability
        if s["available_count"] > best_avail_count:
            best_avail_count = s["available_count"]
            stats["global"]["best_availability"]["count"] = best_avail_count
            stats["global"]["best_availability"]["shop"] = shop

    return stats


def delete_previous_merge(output_path: Path) -> None:
    """
    Delete previous merged file if it exists.
    
    Args:
        output_path: Path to merged file
    """
    if output_path.exists():
        try:
            output_path.unlink()
            logger.info(f"Deleted previous merged file: {output_path}")
        except Exception as e:
            logger.warning(f"Failed to delete previous merged file: {e}")


def save_merged_file(products: List[Dict], summary: Dict, output_path: Path) -> None:
    """
    Save merged data to NDJSON file and summary to JSON file.
    
    Args:
        products: List of merged product dictionaries
        summary: Metadata summary dictionary
        output_path: Path to products output file (will be NDJSON)
    """
    # Ensure directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 1. Save Products (JSON Array)
    temp_path = output_path.with_suffix('.json.tmp')
    try:
        with open(temp_path, 'w', encoding='utf-8') as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
        temp_path.rename(output_path)
        logger.info(f"✓ Saved merged products (JSON Array): {output_path}")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise RuntimeError(f"Failed to save merged products: {e}")

    # 2. Save Summary (JSON)
    summary_path = output_path.parent / "products_merged_summary.json"
    temp_summary = summary_path.with_suffix('.json.tmp')
    try:
        with open(temp_summary, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        temp_summary.rename(summary_path)
        logger.info(f"✓ Saved merged summary: {summary_path}")
    except Exception as e:
        if temp_summary.exists():
            temp_summary.unlink()
        logger.error(f"Failed to save summary: {e}")


def merge_latest_products() -> Dict:
    """
    Main merge function: loads latest files, merges by SKU, saves output.
    
    Returns:
        Dictionary with merge statistics
        
    Raises:
        RuntimeError: If merge fails
    """
    logger.info("=" * 70)
    logger.info("🔄 PRODUCT MERGE STARTED")
    logger.info("=" * 70)
    
    # Step 1: Find latest files for each source
    logger.info("Step 1: Finding latest product files...")
    source_files = {}
    
    for source in REQUIRED_SOURCES:
        filepath = find_latest_product_file(source)
        if filepath is None:
            raise RuntimeError(f"Failed to find latest file for {source}")
        source_files[source] = filepath
        logger.info(f"  {source}: {filepath}")
    
    # Step 2: Load and validate files
    logger.info("\nStep 2: Loading product files...")
    source_data = {}
    
    for source, filepath in source_files.items():
        try:
            data = load_product_file(filepath)
            source_data[source] = data
            logger.info(f"  {source}: {len(data['products'])} products loaded")
        except ValueError as e:
            raise RuntimeError(f"Failed to load {source}: {e}")
    
    # Step 3: Index products by SKU
    logger.info("\nStep 3: Indexing products by SKU...")
    indexes = {}
    
    for source, data in source_data.items():
        # Deduplicate first
        unique_products = deduplicate_products(data["products"], source)
        
        # Then index by SKU
        index = index_by_sku(unique_products)
        indexes[source] = index
        logger.info(f"  {source}: {len(index)} unique products with valid SKU")
    
    # Step 4: Find common SKUs (intersection)
    logger.info("\nStep 4: Finding common SKUs...")
    common_skus = find_common_skus(indexes["mytek"], indexes["spacenet"], indexes["tunisianet"])
    
    if len(common_skus) == 0:
        logger.warning("⚠️  No common products found across all three sources!")
    
    # Step 5: Merge products
    logger.info("\nStep 5: Merging products...")
    merged_products = []
    
    for sku in common_skus:
        merged_product = merge_product_data(
            sku,
            indexes["mytek"][sku],
            indexes["spacenet"][sku],
            indexes["tunisianet"][sku]
        )
        merged_products.append(merged_product)
    
    logger.info(f"  Merged {len(merged_products)} products")
    
    # Step 6: Build output structure
    analytics = calculate_analytics(merged_products)
    
    summary = {
        "merged_at": datetime.now().isoformat(),
        "source_files": {
            source: str(filepath) for source, filepath in source_files.items()
        },
        "total_products": len(merged_products),
        "merge_stats": {
            "mytek_total": len(indexes["mytek"]),
            "spacenet_total": len(indexes["spacenet"]),
            "tunisianet_total": len(indexes["tunisianet"]),
            "common_products": len(common_skus)
        },
        "analytics": analytics
    }
    
    # Step 7: Delete previous merge file (and summary if exists)
    logger.info("\nStep 6: Managing file lifecycle...")
    delete_previous_merge(MERGED_FILE)
    
    # Step 8: Save new merged file (NDJSON) and Summary
    logger.info("Step 7: Saving merged files...")
    save_merged_file(merged_products, summary, MERGED_FILE)
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ PRODUCT MERGE COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Total products merged: {len(merged_products)}")
    logger.info(f"Output: {MERGED_FILE}")
    logger.info("")
    
    return {
        "success": True,
        "total_products": len(merged_products),
        "output_path": str(MERGED_FILE),
        "source_files": source_files
    }


import traceback

def main():
    """CLI entry point."""
    try:
        result = merge_latest_products()
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Merge failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
