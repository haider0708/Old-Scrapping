#!/usr/bin/env python3
"""
Pipeline - Automated Scraping
===============================

Simple automated scraper that scrapes all websites one by one and saves JSON data.

Usage:
    python pipeline.py run --once
    python pipeline.py run --interval 720
"""
import argparse
import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict

import yaml

from scraper.base import LOGS_DIR
from scraper.base import rotate_tor_ip, TorPool
from scrape import run_full_scrape, setup_logger
from track_history import track_history_for_shop

# ── Per-site retry configuration ──────────────────────────────────
SITE_MAX_RETRIES = int(os.environ.get("PIPELINE_SITE_RETRIES", "2"))
SITE_RETRY_DELAY = int(os.environ.get("PIPELINE_RETRY_DELAY", "30"))  # seconds
# Watchdog: if a single site takes longer than this, abort and retry
SITE_TIMEOUT = int(os.environ.get("PIPELINE_SITE_TIMEOUT", "3600"))  # 60 min default

# Heartbeat file updated at the end of every successful pipeline cycle
_HEARTBEAT = Path("logs/.heartbeat")


def _touch_heartbeat():
    """Update the heartbeat file so the Docker healthcheck stays green."""
    try:
        _HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        _HEARTBEAT.touch()
    except OSError:
        pass


@dataclass
class SiteStats:
    """Statistics for a single site scrape."""
    site: str = ""
    started_at: str = ""
    ended_at: str = ""
    duration_seconds: float = 0
    products_total: int = 0
    details_scraped: int = 0
    success: bool = False
    error: str = ""
    attempts: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


class SimplePipeline:
    """Simple scraping pipeline - scrape and save JSON data."""

    def __init__(
        self,
        sites: List[Dict],
        data_dir: str = "data",
        interval_minutes: int = 720,
        workers: int = 16,
        detail_workers: int = 16
    ):
        # sites is now a list of dicts: [{"name": "mytek", "use_tor": False}, ...]
        self.sites = sites
        self.data_dir = Path(data_dir)
        self.interval_minutes = interval_minutes
        self.workers = workers
        self.detail_workers = detail_workers
        self.logger = self._setup_logger()
        self.run_stats: Dict[str, SiteStats] = {}

    def _setup_logger(self) -> logging.Logger:
        logging.getLogger("httpx").setLevel(logging.CRITICAL)

        logger = logging.getLogger("pipeline")
        logger.setLevel(logging.INFO)
        logger.handlers = []

        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOGS_DIR / f"pipeline_{timestamp}.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(file_handler)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console_handler)
        logger.propagate = False  # prevent duplicate lines via root logger

        return logger

    async def _scrape_with_timeout(self, site: str) -> dict:
        """Run run_full_scrape with a per-site watchdog timeout."""
        return await asyncio.wait_for(
            run_full_scrape(
                site_name=site,
                num_workers=self.workers,
                detail_workers=self.detail_workers,
                limit=None,
                logger=self.logger,
                scrape_details=True,
            ),
            timeout=SITE_TIMEOUT,
        )

    async def _process_site(self, site: str):
        """Process a single site with automatic retry on failure."""
        stats = SiteStats(site=site, started_at=datetime.now().isoformat())
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"🔄 Processing: {site.upper()}")
        self.logger.info(f"{'='*70}")

        last_error = ""
        for attempt in range(1, SITE_MAX_RETRIES + 1):
            stats.attempts = attempt
            if attempt > 1:
                self.logger.warning(
                    f"  ↩️  Retry {attempt}/{SITE_MAX_RETRIES} for {site} "
                    f"(waiting {SITE_RETRY_DELAY}s)..."
                )
                await asyncio.sleep(SITE_RETRY_DELAY)

            try:
                result = await self._scrape_with_timeout(site)

                if result.get("success"):
                    stats.products_total = result.get("stats", {}).get("total_products", 0)
                    stats.details_scraped = result.get("stats", {}).get("details_scraped", 0)
                    stats.success = True
                    last_error = ""
                    break  # success — stop retrying

                last_error = result.get("error", "Unknown error")
                self.logger.warning(f"  ⚠️  Attempt {attempt} failed: {last_error}")

            except asyncio.TimeoutError:
                last_error = f"Timed out after {SITE_TIMEOUT}s"
                self.logger.error(f"  ⏰ {site} timed out on attempt {attempt}")
            except Exception as e:
                last_error = str(e)
                self.logger.error(
                    f"  ❌ Attempt {attempt} exception for {site}: {e}\n"
                    + traceback.format_exc()
                )

        if not stats.success:
            stats.error = last_error
            self.logger.error(
                f"  ❌ {site} failed after {stats.attempts} attempt(s): {last_error}"
            )

        stats.ended_at = datetime.now().isoformat()
        start = datetime.fromisoformat(stats.started_at)
        end = datetime.fromisoformat(stats.ended_at)
        stats.duration_seconds = (end - start).total_seconds()
        self.run_stats[site] = stats

        m, s = divmod(int(stats.duration_seconds), 60)
        self.logger.info(f"  ⏱️  Completed in {m}m {s}s")

    async def run(self, continuous: bool = False):
        """Run the pipeline — never raises; loops forever if continuous=True."""
        mode = "Continuous" if continuous else "Single Run"
        self.logger.info(f"\n{'='*70}")
        self.logger.info("🚀 PIPELINE STARTED")
        self.logger.info(f"{'='*70}")
        site_names = [s["name"] for s in self.sites]
        self.logger.info(f"  Sites   : {', '.join(site_names)}")
        self.logger.info(f"  Mode    : {mode}")
        self.logger.info(f"  Retries : {SITE_MAX_RETRIES} per site")
        self.logger.info(f"  Timeout : {SITE_TIMEOUT}s per site")
        self.logger.info(f"  Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        pool = TorPool.get()

        while True:
            run_start = datetime.now()
            self.run_stats = {}

            for site_cfg in self.sites:
                site = site_cfg["name"]
                use_tor = site_cfg.get("use_tor", False)
                pool.activate(use_tor)
                try:
                    if use_tor:
                        await rotate_tor_ip(self.logger)
                    await self._process_site(site)
                except Exception as e:
                    self.logger.critical(
                        f"  💥 Unhandled exception for {site}: {e}\n"
                        + traceback.format_exc()
                    )
                finally:
                    pool.activate(False)
                await asyncio.sleep(2)

            duration_str = str(datetime.now() - run_start).split(".")[0]

            # ── Summary ───────────────────────────────────────────
            self.logger.info(f"\n{'='*70}")
            self.logger.info("✅ SCRAPING COMPLETE")
            self.logger.info(f"{'='*70}")
            self.logger.info(f"  Duration : {duration_str}")
            self.logger.info(f"  Sites    : {len(self.sites)}")
            for site_name, st in self.run_stats.items():
                icon = "✅" if st.success else "❌"
                self.logger.info(
                    f"    {icon} {site_name}: {st.products_total} products, "
                    f"{st.details_scraped} details"
                    + (f" | {st.error}" if not st.success else "")
                )

            success_count = sum(1 for st in self.run_stats.values() if st.success)

            # ── Price history tracking ────────────────────────────
            if success_count > 0:
                self.logger.info(f"\n{'='*70}")
                self.logger.info("🔄 PRICE HISTORY TRACKING")
                self.logger.info(f"{'='*70}")
                for site_cfg in self.sites:
                    site_name = site_cfg["name"]
                    if self.run_stats.get(site_name) and self.run_stats[site_name].success:
                        try:
                            self.logger.info(f"  Tracking history for {site_name}...")
                            track_history_for_shop(site_name)
                            self.logger.info(f"  ✅ History tracked for {site_name}")
                        except Exception as e:
                            self.logger.error(
                                f"  ❌ History tracking failed for {site_name}: {e}\n"
                                + traceback.format_exc()
                            )
            else:
                self.logger.warning("⚠️  Skipping price tracking: no sites succeeded")

            # ── Touch heartbeat so Docker healthcheck stays green ─
            _touch_heartbeat()

            if not continuous:
                break

            self.logger.info(f"\n⏰ Next run in {self.interval_minutes} minutes")
            next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
            self.logger.info(f"   Expected: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            await asyncio.sleep(self.interval_minutes * 60)


def load_config(config_path: str = "configs/pipeline_config.yaml") -> dict:
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_file) as f:
        return yaml.safe_load(f)


def create_pipeline(config_path: str = "configs/pipeline_config.yaml") -> SimplePipeline:
    config = load_config(config_path)
    scraping_config = config.get("scraping", {})

    # Normalize sites: support both old ["mytek", ...] and new [{"name": "mytek", ...}]
    raw_sites = config.get("sites", [])
    sites = []
    for entry in raw_sites:
        if isinstance(entry, str):
            sites.append({"name": entry, "use_tor": False})
        elif isinstance(entry, dict):
            sites.append({"name": entry["name"], "use_tor": entry.get("use_tor", False)})

    return SimplePipeline(
        sites=sites,
        data_dir=config.get("data_dir", "data"),
        interval_minutes=config.get("interval_minutes", 720),
        workers=scraping_config.get("workers", 16),
        detail_workers=scraping_config.get("detail_workers", 64),
    )


async def main():
    parser = argparse.ArgumentParser(description="Automated scraping pipeline")
    subparsers = parser.add_subparsers(dest="cmd", help="Command to run")

    run_parser = subparsers.add_parser("run", help="Run the automated scraping pipeline")
    run_parser.add_argument("--once", action="store_true", help="Run once and exit")
    run_parser.add_argument("--interval", type=int, help="Interval in minutes")
    run_parser.add_argument("--sites", nargs="+", help="Specific sites to scrape")
    run_parser.add_argument("--config", default="configs/pipeline_config.yaml")

    args = parser.parse_args()

    if args.cmd == "run":
        pipeline = create_pipeline(args.config)
        if args.sites:
            pipeline.sites = [{"name": s, "use_tor": False} for s in args.sites]
        if args.interval:
            pipeline.interval_minutes = args.interval
        await pipeline.run(continuous=not args.once)
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())



@dataclass
class SiteStats:
    """Statistics for a single site scrape."""
    site: str = ""
    started_at: str = ""
    ended_at: str = ""
    duration_seconds: float = 0
    products_total: int = 0
    details_scraped: int = 0
    success: bool = False
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class SimplePipeline:
    """Simple scraping pipeline - scrape and save JSON data."""

    def __init__(
        self,
        sites: List[str],
        data_dir: str = "data",
        interval_minutes: int = 720,
        workers: int = 16,
        detail_workers: int = 16
    ):
        self.sites = sites
        self.data_dir = Path(data_dir)
        self.interval_minutes = interval_minutes
        self.workers = workers
        self.detail_workers = detail_workers

        # Setup logger
        self.logger = self._setup_logger()

        self.run_stats: Dict[str, SiteStats] = {}

    def _setup_logger(self) -> logging.Logger:
        """Setup logger."""
        # Suppress ALL httpx logging (HTTP requests, warnings, etc.)
        logging.getLogger("httpx").setLevel(logging.CRITICAL)

        logger = logging.getLogger("pipeline")
        logger.setLevel(logging.INFO)
        logger.handlers = []

        # Create log file for pipeline runs
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = LOGS_DIR / f"pipeline_{timestamp}.log"

        # File handler - logs everything to file
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        logger.addHandler(file_handler)

        # Console handler - still shows INFO to terminal
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        return logger
    
    async def _process_site(self, site: str):
        """Process a single site: scrape and save JSON data."""
        stats = SiteStats(site=site, started_at=datetime.now().isoformat())
        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"🔄 Processing: {site.upper()}")
        self.logger.info(f"{'='*70}")

        try:
            # Run full scrape (categories + products + details)
            result = await run_full_scrape(
                site_name=site,
                num_workers=self.workers,
                detail_workers=self.detail_workers,
                limit=None,
                logger=self.logger,
                scrape_details=True
            )

            if not result.get("success"):
                stats.error = result.get("error", "Unknown error")
                stats.success = False
                return

            stats.products_total = result.get("stats", {}).get("total_products", 0)
            stats.details_scraped = result.get("stats", {}).get("details_scraped", 0)
            stats.success = True

        except Exception as e:
            stats.error = str(e)
            stats.success = False
            self.logger.error(f"  ❌ Error processing {site}: {e}")

        finally:
            stats.ended_at = datetime.now().isoformat()
            if stats.started_at:
                start = datetime.fromisoformat(stats.started_at)
                end = datetime.fromisoformat(stats.ended_at)
                stats.duration_seconds = (end - start).total_seconds()

            self.run_stats[site] = stats
            duration_str = f"{int(stats.duration_seconds // 60)}m {int(stats.duration_seconds % 60)}s"
            self.logger.info(f"  ⏱️  Completed in {duration_str}")
    
    
    
    async def run(self, continuous: bool = False):
        """Run the pipeline."""
        mode = 'Continuous' if continuous else 'Single Run'

        self.logger.info(f"\n{'='*70}")
        self.logger.info(f"🚀 PIPELINE STARTED")
        self.logger.info(f"{'='*70}")
        self.logger.info(f"  Sites: {', '.join(self.sites)}")
        self.logger.info(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"  Mode: {mode}")

        while True:
            run_start = datetime.now()
            self.run_stats = {}  # Reset stats for each run

            for site in self.sites:
                await self._process_site(site)
                await asyncio.sleep(2)  # Small delay between sites

            run_end = datetime.now()
            duration = run_end - run_start
            duration_str = str(duration).split('.')[0]

            # Print summary
            self.logger.info(f"\n{'='*70}")
            self.logger.info(f"✅ SCRAPING COMPLETE")
            self.logger.info(f"{'='*70}")
            self.logger.info(f"  Duration: {duration_str}")
            self.logger.info(f"  Sites processed: {len(self.sites)}")
            for site, stats in self.run_stats.items():
                status = "✅" if stats.success else "❌"
                self.logger.info(f"    {status} {site}: {stats.products_total} products, {stats.details_scraped} details")

            success_count = sum(1 for stats in self.run_stats.values() if stats.success)

            # Run Price History Tracking
            if success_count > 0:
                self.logger.info(f"\n{'='*70}")
                self.logger.info("🔄 STARTING PRICE HISTORY TRACKING")
                self.logger.info(f"{'='*70}")
                for site in self.sites:
                    if self.run_stats.get(site) and self.run_stats[site].success:
                        try:
                            self.logger.info(f"  Tracking history for {site}...")
                            track_history_for_shop(site)
                            self.logger.info(f"  ✅ History tracking successful for {site}")
                        except Exception as e:
                            self.logger.error(f"  ❌ History tracking failed for {site}: {e}")
                            import traceback
                            self.logger.debug(traceback.format_exc())
                self.logger.info(f"\n{'='*70}")
                self.logger.info("✅ PRICE HISTORY TRACKING COMPLETE")
                self.logger.info(f"{'='*70}")
            else:
                self.logger.warning("\n⚠️  Skipping price tracking: No sites scraped successfully")

            if not continuous:
                break

            self.logger.info(f"\n⏰ Next run in {self.interval_minutes} minutes")
            next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
            self.logger.info(f"   Expected: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")
            await asyncio.sleep(self.interval_minutes * 60)


def load_config(config_path: str = "configs/pipeline_config.yaml") -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_file) as f:
        return yaml.safe_load(f)


def create_pipeline(config_path: str = "configs/pipeline_config.yaml") -> SimplePipeline:
    """Create pipeline from config file."""
    config = load_config(config_path)

    scraping_config = config.get("scraping", {})

    return SimplePipeline(
        sites=config.get("sites", []),
        data_dir=config.get("data_dir", "data"),
        interval_minutes=config.get("interval_minutes", 720),
        workers=scraping_config.get("workers", 16),
        detail_workers=scraping_config.get("detail_workers", 64)
    )


async def main():
    parser = argparse.ArgumentParser(description="Automated scraping pipeline")
    subparsers = parser.add_subparsers(dest="cmd", help="Command to run")

    # Run command (automated scraping pipeline)
    run_parser = subparsers.add_parser("run", help="Run the automated scraping pipeline")
    run_parser.add_argument("--once", action="store_true", help="Run once and exit")
    run_parser.add_argument("--interval", type=int, help="Interval in minutes (default from config)")
    run_parser.add_argument("--sites", nargs="+", help="Specific sites to scrape")
    run_parser.add_argument("--config", default="configs/pipeline_config.yaml", help="Config file path")

    args = parser.parse_args()

    if args.cmd == "run":
        # Automated scraping run
        pipeline = create_pipeline(args.config)

        if args.sites:
            pipeline.sites = args.sites

        if args.interval:
            pipeline.interval_minutes = args.interval

        await pipeline.run(continuous=not args.once)

    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
