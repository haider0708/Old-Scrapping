#!/usr/bin/env python3
"""
Scrape - Fast E-commerce Scraper

High-performance scraper for Tunisian e-commerce sites.

Usage:
    python scrape.py test --site mytek --categories 3 --products 5
    python scrape.py full --site mytek
    python scrape.py list
"""
import argparse
import asyncio
import gc
import json
import logging
import sys
import time

# Suppress the "I/O operation on closed pipe" ValueError that fires inside
# asyncio._ProactorBasePipeTransport.__del__ on Windows after Playwright's
# Chromium subprocess pipes are closed.  The exception is un-raisable (it
# happens inside __del__) so we intercept it via sys.unraisablehook.
_orig_unraisablehook = sys.unraisablehook

def _unraisable_hook(unraisable):
    if isinstance(unraisable.exc_value, (ValueError, RuntimeError)) and any(
        phrase in str(unraisable.exc_value)
        for phrase in ("I/O operation on closed pipe", "Event loop is closed")
    ):
        return  # silently ignore Playwright subprocess cleanup noise
    _orig_unraisablehook(unraisable)

sys.unraisablehook = _unraisable_hook
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

try:
    from tqdm import tqdm
except ImportError:
    # Fallback if tqdm not installed
    class tqdm:
        def __init__(self, total=0, desc="", bar_format="", ncols=80):
            self.total = total
            self.n = 0
            self.desc = desc
        def update(self, n=1):
            self.n += n
        def close(self):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass

from scraper.base import (
    BASE_DIR, DATA_DIR, LOGS_DIR,
    ScrapeStats, CategoryInfo,
    load_json, save_json, format_duration, get_date_folder,
    save_jsonl, load_jsonl, playwright_launch_args,
    rotate_tor_ip, USE_TOR, TorPool,
)
from scraper.sites import get_scraper, list_available_sites

# Number of detail results kept in memory at once before flushing to disk.
# Larger values keep more workers busy; lower values reduce peak RAM.
DETAIL_BATCH_SIZE = 500


class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"


def print_header(text, char="=", width=70):
    print(f"\n{Colors.CYAN}{char * width}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.WHITE}  {text}{Colors.RESET}")
    print(f"{Colors.CYAN}{char * width}{Colors.RESET}")


def print_step(step, text):
    print(f"\n{Colors.BLUE}[{step}]{Colors.RESET} {Colors.BOLD}{text}{Colors.RESET}")


def print_success(text):
    print(f"  {Colors.GREEN}✓{Colors.RESET} {text}")


def print_error(text):
    print(f"  {Colors.RED}✗{Colors.RESET} {text}")


def print_info(text):
    print(f"  {Colors.DIM}→{Colors.RESET} {text}")


def print_stat(label, value, color=None):
    if color is None:
        color = Colors.WHITE
    print(f"  {Colors.DIM}{label}:{Colors.RESET} {color}{value}{Colors.RESET}")


def is_fast_scraper(scraper):
    from scraper.base import FastScraper
    return isinstance(scraper, FastScraper)


def setup_logger(site_name, log_level=logging.WARNING):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOGS_DIR / f"{site_name}_{timestamp}.log"
    logger = logging.getLogger(f"scraper_{site_name}_{timestamp}")
    logger.setLevel(logging.DEBUG)
    logger.handlers = []
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
    logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(log_level)
    ch.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(ch)
    return logger


async def scrape_categories_fast(scraper, categories_list, num_workers, pbar, on_result=None):
    """Scrape categories concurrently, bounded by *num_workers* semaphore.

    When *on_result(url, result)* is supplied it is called synchronously as
    each category finishes, allowing the caller to stream-process results
    (e.g. write to disk) without waiting for all categories to complete.
    When omitted the classic ``{url: result}`` dict is returned for
    backwards compatibility.
    """
    results = {} if on_result is None else None
    sem = asyncio.Semaphore(num_workers)

    async def worker(cat):
        # Safe default so r is always defined even if the outer try fails.
        r = {"category": cat, "products": [], "success": False, "error": "Worker did not complete"}
        async with sem:
            try:
                prods = await scraper.scrape_all_pages(cat.url)
                r = {"category": cat, "products": prods, "success": True}
            except Exception as e:
                r = {"category": cat, "products": [], "success": False, "error": str(e)}
            finally:
                if pbar is not None:
                    pbar.update(1)
        if on_result is not None:
            on_result(cat.url, r)
        else:
            results[cat.url] = r

    await asyncio.gather(*[worker(c) for c in categories_list])
    return results


async def scrape_categories_playwright(scraper, categories_list, num_workers, stats, pbar):
    from playwright.async_api import async_playwright
    results = {}
    pool = TorPool.get()
    queue = asyncio.Queue()
    for c in categories_list:
        await queue.put(c)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=playwright_launch_args())
        try:
            async def worker(wid):
                ctx = await browser.new_context(proxy=pool.pw_proxy(wid))
                page = await ctx.new_page()
                try:
                    while True:
                        try:
                            cat = await asyncio.wait_for(queue.get(), timeout=1.0)
                        except asyncio.TimeoutError:
                            if queue.empty():
                                break
                            continue
                        try:
                            prods = await scraper.scrape_category_all_pages(ctx, cat, stats)
                            results[cat.url] = {"category": cat, "products": prods, "success": True}
                        except Exception as e:
                            results[cat.url] = {"category": cat, "products": [], "success": False, "error": str(e)}
                        finally:
                            if pbar is not None:
                                pbar.update(1)
                            queue.task_done()
                finally:
                    await page.close()
                    await ctx.close()

            await asyncio.gather(*[worker(i) for i in range(num_workers)])
            await queue.join()
        finally:
            await browser.close()
    return results


async def scrape_details_fast(scraper, items, num_workers, pbar):
    results = {}
    sem = asyncio.Semaphore(num_workers)

    async def worker(item):
        async with sem:
            url = item["url"]
            try:
                det = await scraper.scrape_product_details(url)
                results[url] = {"details": det, "item": item, "success": True}
            except Exception as e:
                results[url] = {"item": item, "success": False, "error": str(e)}
            finally:
                if pbar is not None:
                    pbar.update(1)

    await asyncio.gather(*[worker(i) for i in items])
    return results


async def scrape_details_playwright(scraper, items, num_workers, pbar):
    from playwright.async_api import async_playwright
    results = {}
    pool = TorPool.get()
    queue = asyncio.Queue()
    for i in items:
        await queue.put(i)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=playwright_launch_args())
        try:
            async def worker(wid):
                ctx = await browser.new_context(proxy=pool.pw_proxy(wid))
                page = await ctx.new_page()
                try:
                    while True:
                        try:
                            item = await asyncio.wait_for(queue.get(), timeout=1.0)
                        except asyncio.TimeoutError:
                            if queue.empty():
                                break
                            continue
                        url = item["url"]
                        try:
                            det = await scraper.scrape_product_details(page, url)
                            results[url] = {"details": det, "item": item, "success": True}
                        except Exception as e:
                            results[url] = {"item": item, "success": False, "error": str(e)}
                        finally:
                            if pbar is not None:
                                pbar.update(1)
                            queue.task_done()
                finally:
                    await page.close()
                    await ctx.close()

            await asyncio.gather(*[worker(i) for i in range(num_workers)])
            await queue.join()
        finally:
            await browser.close()
    return results


async def run_full_scrape(site_name, num_workers=16, detail_workers=16, limit=None, logger=None, scrape_details=True, category_filter=None):
    if logger is None:
        logger = setup_logger(site_name)
    
    start_time = time.time()
    ts = get_date_folder()
    result = {"site": site_name, "success": False, "error": None, "stats": None, "output_path": None, "duration_seconds": 0}

    print_header(f"🚀 SCRAPING: {site_name.upper()}")
    print_stat("Started", datetime.now().strftime('%Y-%m-%d %H:%M:%S'), Colors.CYAN)
    print_stat("Folder", ts, Colors.DIM)
    print_stat("Workers", f"{num_workers} / {detail_workers}", Colors.DIM)
    if category_filter:
        print_stat("Category", category_filter, Colors.YELLOW)
    if limit:
        print_stat("Limit", f"{limit} categories", Colors.YELLOW)
    
    try:
        scraper = get_scraper(site_name, logger)
        scraper._current_data_dir = DATA_DIR / site_name / ts
        scraper._current_data_dir.mkdir(parents=True, exist_ok=True)
    except ValueError as e:
        print_error(str(e))
        result["error"] = str(e)
        return result
    
    stats = ScrapeStats()
    stats.site = site_name
    stats.start_time = datetime.now().isoformat()
    stats.workers_used = num_workers
    
    # Step 1: Download
    print_step(1, "Downloading frontpage")
    t0 = time.time()
    try:
        await scraper.download_frontpage()
        print_success(f"Done in {time.time()-t0:.1f}s")
    except Exception as e:
        print_error(str(e))
        result["error"] = str(e)
        return result
    
    # Step 2: Categories
    print_step(2, "Extracting categories")
    t0 = time.time()
    try:
        cat_path = scraper.extract_categories()
        cat_data = load_json(cat_path)
        # Use the proper build_scrape_queue method with fallback logic
        cat_list = scraper.build_scrape_queue(cat_data)

        # Filter by top-level category name if requested
        if category_filter:
            cf_lower = category_filter.strip().lower()
            cat_list = [
                c for c in cat_list
                if (c.parent_names[0] if c.parent_names else c.name).lower() == cf_lower
            ]
            if not cat_list:
                print_error(f"No categories matched filter: '{category_filter}'")
                print_info("Available top-level categories:")
                for tc in cat_data.get("categories", []):
                    print_info(f"  • {tc.get('name','')}")
                result["error"] = f"No categories matched: {category_filter}"
                return result
            print_info(f"Filtered to top-category '{category_filter}': {len(cat_list)} sub-categories")

        stats.total_categories = len(cat_list)
        cs = cat_data.get("stats", {})
        print_success(f"Found {cs.get('top_level',0)} top → {cs.get('low_level',0)} low → {cs.get('subcategory',0)} sub")
        print_info(f"Total: {len(cat_list)} categories")
    except Exception as e:
        print_error(str(e))
        result["error"] = str(e)
        return result
    
    # Step 3: Products
    print_step(3, "Scraping products")
    t0 = time.time()
    if limit:
        cat_list = cat_list[:limit]
        print_info(f"Limited to {limit}")

    # ── Phase 3a: Scrape + stream-write products ───────────────────────────
    # For FastScraper sites, results are processed (written to disk) as each
    # category finishes via the on_result callback — so peak memory is bounded
    # to one category at a time rather than the entire site.
    # For Playwright sites the classic collect-then-process path is used.
    #
    # Products are buffered in RAM and flushed in chunks (_PROD_BUF_CAP) to
    # reduce the number of individual write() syscalls.

    _PROD_BUF_CAP = 256  # flush write buffer every N products

    # All mutable state for the callback is held in a dict so nested functions
    # can mutate it without nonlocal declarations.
    _ps = {
        "first_prod": True,
        "total_prods": 0,
        "write_buf": [],
        "failed_categories": [],
        "product_items": [],
    }

    out_path = scraper.data_dir / "products.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def _flush_prod_buf(f):
        buf = _ps["write_buf"]
        if not buf:
            return
        parts = []
        for item in buf:
            prefix = "\n" if _ps["first_prod"] else ",\n"
            parts.append(prefix + json.dumps(item, ensure_ascii=False))
            _ps["first_prod"] = False
        f.write("".join(parts))
        buf.clear()

    def _handle_cat_result(url, r, f):
        if not r.get("success"):
            cat = r.get("category")
            error = r.get("error", "Unknown error")
            _ps["failed_categories"].append({
                "url": url,
                "name": cat.name if cat else url,
                "error": error,
            })
            return

        cat = r["category"]
        prods = r["products"]
        loc = cat.location

        try:
            if len(loc) == 1:
                top_category = cat_data["categories"][loc[0]]["name"]
                low_category = None
                subcategory = None
            elif len(loc) == 2:
                top_category = cat_data["categories"][loc[0]]["name"]
                low_category = cat_data["categories"][loc[0]]["low_level_categories"][loc[1]]["name"]
                subcategory = None
            elif len(loc) == 3:
                top_category = cat_data["categories"][loc[0]]["name"]
                low_category = cat_data["categories"][loc[0]]["low_level_categories"][loc[1]]["name"]
                subcategory = cat_data["categories"][loc[0]]["low_level_categories"][loc[1]]["subcategories"][loc[2]]["name"]
            else:
                top_category = cat.name
                low_category = None
                subcategory = None
            stats.categories_scraped += 1
        except (IndexError, KeyError) as e:
            print_error(f"Failed to resolve category {cat.name}: {e}")
            _ps["failed_categories"].append({
                "url": url,
                "name": cat.name,
                "error": f"Category resolution error: {e}",
            })
            return

        for p in prods:
            product_copy = {
                **p,
                "shop": site_name,
                "top_category": top_category,
                "low_category": low_category,
                "subcategory": subcategory,
            }
            _ps["write_buf"].append(product_copy)
            _ps["total_prods"] += 1

            if p.get("url"):
                _ps["product_items"].append({
                    "id": p.get("id"),
                    "url": p["url"],
                    "top_category": top_category,
                    "low_category": low_category,
                    "subcategory": subcategory,
                })

        # Flush when buffer reaches capacity
        if len(_ps["write_buf"]) >= _PROD_BUF_CAP:
            _flush_prod_buf(f)

        # Release product data from this category immediately
        r["products"] = None

    pbar = tqdm(
        total=len(cat_list),
        desc=f"  {Colors.GREEN}Categories{Colors.RESET}",
        bar_format="{desc}: {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
        ncols=80,
    )

    with open(out_path, "w", encoding="utf-8") as prod_file:
        prod_file.write("[")
        try:
            if is_fast_scraper(scraper):
                # Streaming: each category result is written to disk as it arrives
                await scrape_categories_fast(
                    scraper, cat_list, num_workers, pbar,
                    on_result=lambda url, r: _handle_cat_result(url, r, prod_file),
                )
            else:
                cat_res = await scrape_categories_playwright(
                    scraper, cat_list, num_workers, stats, pbar
                )
                for url, r in cat_res.items():
                    _handle_cat_result(url, r, prod_file)
                del cat_res
                gc.collect()
        finally:
            pbar.close()

        _flush_prod_buf(prod_file)  # flush any remaining buffered products
        prod_file.write("\n]")

    failed_categories = _ps["failed_categories"]
    total_prods = _ps["total_prods"]
    product_items = _ps["product_items"]

    stats.total_products = total_prods
    fail = len(failed_categories)
    ok = stats.categories_scraped
    print_success(f"Scraped {ok}/{len(cat_list)} in {time.time()-t0:.1f}s")
    print_info(f"Found {Colors.GREEN}{total_prods:,}{Colors.RESET} products  (streamed to disk)")
    if fail > 0:
        print_info(f"{Colors.RED}{fail}{Colors.RESET} categories failed")
        if logger:
            for fc in failed_categories[:5]:
                logger.warning(f"  Failed category: {fc['name']} - {fc['error']}")
        failure_data = {
            "site": site_name,
            "scraped_at": datetime.now().isoformat(),
            "total_failures": len(failed_categories),
            "failures": failed_categories,
        }
        failure_path = scraper.data_dir / f"{site_name}_categories_failures.json"
        save_json(failure_data, failure_path, logger)
        print_info(f"Saved {len(failed_categories)} category failures to {failure_path}")

    summary = {
        "site": site_name,
        "shop": site_name,
        "scraped_at": datetime.now().isoformat(),
        "duration_seconds": time.time() - t0,
        "total_products": total_prods,
        "scrape_stats": asdict(stats),
        "failed_categories": failed_categories,
    }
    summary_path = scraper.data_dir / "products_summary.json"
    save_json(summary, summary_path, logger)

    # ── Phase 3b: Details – batched scraping with streaming file writes ─────
    # We process DETAIL_BATCH_SIZE products at a time.  After each batch the
    # scrape results dict is deleted and gc.collect() is called, keeping peak
    # RAM proportional to the batch size rather than the full dataset.
    det_count = 0
    if scrape_details and total_prods > 0:
        print_step(4, "Scraping product details")
        t0 = time.time()

        total_items = len(product_items)
        total_batches = (total_items + DETAIL_BATCH_SIZE - 1) // DETAIL_BATCH_SIZE
        print_info(f"Found {total_items:,} product URLs → {total_batches} batch{'es' if total_batches != 1 else ''} of {DETAIL_BATCH_SIZE}")

        failed_details = []
        det_path = scraper.data_dir / "products_detailed.json"
        det_path.parent.mkdir(parents=True, exist_ok=True)

        pbar = tqdm(
            total=total_items,
            desc=f"  {Colors.MAGENTA}Details{Colors.RESET}",
            bar_format="{desc}:   {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]",
            ncols=80,
        )

        with open(det_path, "w", encoding="utf-8") as det_file:
            det_file.write("[")
            first_written = True

            for batch_start in range(0, total_items, DETAIL_BATCH_SIZE):
                batch = product_items[batch_start: batch_start + DETAIL_BATCH_SIZE]
                batch_num = batch_start // DETAIL_BATCH_SIZE + 1

                try:
                    if is_fast_scraper(scraper):
                        det_res = await scrape_details_fast(scraper, batch, detail_workers, pbar)
                    else:
                        det_res = await scrape_details_playwright(scraper, batch, detail_workers, pbar)
                except Exception as e:
                    print_error(f"Batch {batch_num}/{total_batches} failed entirely: {e}")
                    for item in batch:
                        failed_details.append({"id": item.get("id"), "url": item["url"], "error": str(e)})
                    continue

                # ── Process batch results and write in one I/O call ──────────────
                # scraped_at is computed once per batch (not per product) and all
                # JSON strings are built in RAM then written together.
                batch_scraped_at = datetime.now().isoformat()
                batch_lines: List[str] = []

                for item in batch:
                    url = item["url"]
                    r = det_res.get(url)
                    if not r or not r.get("success"):
                        error = r.get("error", "Unknown error") if r else "No result"
                        failed_details.append({"id": item.get("id"), "url": url, "error": error})
                        continue

                    det = r["details"]

                    available_value = det.get("available")
                    if available_value is None and det.get("availability"):
                        avail_text = str(det.get("availability", "")).lower()
                        if "en stock" in avail_text or "disponible" in avail_text:
                            available_value = True
                        elif "epuisé" in avail_text or "rupture" in avail_text or "indisponible" in avail_text:
                            available_value = False

                    detailed_product = {
                        "url": url,
                        "shop": site_name,
                        "scraped_at": batch_scraped_at,
                        "top_category": item.get("top_category"),
                        "low_category": item.get("low_category"),
                        "subcategory": item.get("subcategory"),
                        **det,
                        "available": available_value,
                    }
                    batch_lines.append(json.dumps(detailed_product, ensure_ascii=False))
                    det_count += 1

                # Single write call for the entire batch
                if batch_lines:
                    parts = []
                    for line in batch_lines:
                        parts.append(("\n" if first_written else ",\n") + line)
                        first_written = False
                    det_file.write("".join(parts))

                # Free this batch's raw results from memory before the next batch
                del det_res
                gc.collect()

            det_file.write("\n]")

        pbar.close()

        fail_det = total_items - det_count
        print_success(f"Scraped {det_count:,}/{total_items:,} product details in {time.time()-t0:.1f}s  (streamed to disk)")
        if fail_det > 0:
            print_info(f"{Colors.RED}{fail_det:,}{Colors.RESET} details failed")
            if failed_details and logger:
                for fd in failed_details[:5]:
                    logger.warning(f"  Failed detail: {fd['url'][:60]}... - {fd['error']}")
            if failed_details:
                failure_data = {
                    "site": site_name,
                    "scraped_at": datetime.now().isoformat(),
                    "total_failures": len(failed_details),
                    "failures": failed_details,
                }
                failure_path = scraper.data_dir / f"{site_name}_details_failures.json"
                save_json(failure_data, failure_path, logger)
                print_info(f"Saved {len(failed_details)} details failures to {failure_path}")

        det_summary = {
            "site": site_name,
            "shop": site_name,
            "scraped_at": datetime.now().isoformat(),
            "total_products": det_count,
            "scrape_stats": {
                "total_attempted": total_items,
                "successful": det_count,
                "failed": fail_det,
                "batches": total_batches,
                "batch_size": DETAIL_BATCH_SIZE,
            },
            "failed_details": failed_details,
        }
        summary_path = scraper.data_dir / "products_detailed_summary.json"
        save_json(det_summary, summary_path, logger)

    dur = time.time() - start_time
    print_header(f"✅ COMPLETE: {site_name.upper()}", "-")
    print_stat("Duration", format_duration(dur), Colors.CYAN)
    print_stat("Categories", f"{stats.categories_scraped}/{stats.total_categories}", Colors.WHITE)
    print_stat("Products", f"{stats.total_products:,}", Colors.GREEN)
    print_stat("Details", f"{det_count:,}", Colors.MAGENTA)
    print_stat("Output", str(scraper.data_dir), Colors.DIM)
    print()

    result["success"] = True
    result["stats"] = asdict(stats)
    result["stats"]["details_scraped"] = det_count
    result["output_path"] = str(out_path)
    result["duration_seconds"] = dur

    # Close shared Playwright browser if scraper holds one (e.g. wiki, skymill, graiet)
    if hasattr(scraper, "_close_browser"):
        await scraper._close_browser()

    return result


def limit_products_in_data(data, n):
    # For flattened structure, limit products per category combination
    if "products" in data:
        # Group products by category combination and limit each group
        from collections import defaultdict
        category_groups = defaultdict(list)

        for product in data["products"]:
            key = (product.get("top_category", ""), product.get("low_category", ""), product.get("subcategory", ""))
            category_groups[key].append(product)

        limited_products = []
        for group_products in category_groups.values():
            if len(group_products) > n:
                limited_products.extend(group_products[:n])
            else:
                limited_products.extend(group_products)

        data["products"] = limited_products
        return len(limited_products)
    else:
        # Fallback for old nested structure (shouldn't be used anymore)
        total = 0
        for tc in data.get("categories", []):
            for lc in tc.get("low_level_categories", []):
                ps = lc.get("products", [])
                if len(ps) > n:
                    lc["products"] = ps[:n]
                total += len(lc.get("products", []))
                for sc in lc.get("subcategories", []):
                    ps = sc.get("products", [])
                    if len(ps) > n:
                        sc["products"] = ps[:n]
                    total += len(sc.get("products", []))
        return total


async def test_site(site, categories_limit=3, products_per_category=5, detail_workers=16, category_filter=None):
    logger = setup_logger(site)
    print_header(f"🧪 TESTING: {site.upper()}")
    print_stat("Categories", categories_limit, Colors.YELLOW)
    print_stat("Products/cat", products_per_category, Colors.YELLOW)
    if category_filter:
        print_stat("Category", category_filter, Colors.YELLOW)

    t0 = time.time()
    result = {"site": site, "success": False, "categories_scraped": 0, "products_found": 0, "details_scraped": 0, "duration": 0, "errors": []}

    try:
        pr = await run_full_scrape(site_name=site, num_workers=16, limit=categories_limit, logger=logger, scrape_details=False, category_filter=category_filter)
        if not pr.get("success"):
            result["errors"].append(pr.get("error"))
            return result
        
        result["categories_scraped"] = pr.get("stats", {}).get("categories_scraped", 0)
        
        scraper = get_scraper(site, logger)
        ppath = Path(pr.get("output_path", ""))
        if ppath.exists():
            scraper._current_data_dir = ppath.parent

        # Load as standard JSON list
        data = load_json(ppath)
        products_list = data if isinstance(data, list) else data.get("products", [])
        
        # Limit products directly in the list
        if len(products_list) > products_per_category:
             products_list = products_list[:products_per_category]
        
        # Save back the limited list as JSON Array
        save_json(products_list, ppath, logger)
        result["products_found"] = len(products_list)
        print_info(f"Limited to {result['products_found']} products")

        print_step(4, "Scraping details (limited)")
        items = []
        # For flat structure, collect URLs with category information
        for p in products_list:
            if p.get("url"):
                items.append({
                    "id": p.get("id"),
                    "url": p["url"],
                    "top_category": p.get("top_category"),
                    "low_category": p.get("low_category"),
                    "subcategory": p.get("subcategory")
                })

        if items:
            pbar = tqdm(total=len(items), desc=f"  {Colors.MAGENTA}Details{Colors.RESET}", bar_format="{desc}:   {percentage:3.0f}%|{bar:30}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]", ncols=80)
            try:
                if is_fast_scraper(scraper):
                    det_res = await scrape_details_fast(scraper, items, detail_workers, pbar)
                else:
                    det_res = await scrape_details_playwright(scraper, items, detail_workers, pbar)
            finally:
                pbar.close()

            # Create separate detailed products data structure
            detailed_products = []
            ok = 0

            # Track specific failures
            failed_details = []
            for item in items:
                url = item["url"]
                r = det_res.get(url)
                if not r or not r.get("success"):
                    error = r.get("error", "Unknown error") if r else "No result"
                    failed_details.append({"id": item.get("id"), "url": url, "error": error})
                    continue

                det = r["details"]

                # Ensure available is always boolean or null, never inconsistent
                available_value = det.get("available")
                if available_value is None and det.get("availability"):
                    avail_text = str(det.get("availability", "")).lower()
                    if "en stock" in avail_text or "disponible" in avail_text:
                        available_value = True
                    elif "epuisé" in avail_text or "rupture" in avail_text or "indisponible" in avail_text:
                        available_value = False

                # Build complete detailed product record with category information
                detailed_product = {
                    "url": url,
                    "shop": site,
                    "scraped_at": datetime.now().isoformat(),
                    "top_category": item.get("top_category"),
                    "low_category": item.get("low_category"),
                    "subcategory": item.get("subcategory"),
                    **det,  # Include all fields from detailed scraping
                    "available": available_value  # Override with processed value
                }

                detailed_products.append(detailed_product)
                ok += 1

            result["details_scraped"] = ok

            # Save detailed products as direct list (JSON Array)
            save_json(detailed_products, scraper.data_dir / "products_detailed.json", logger)
            
            # Save summary separately
            det_summary = {
                "site": site,
                "shop": site,
                "scraped_at": datetime.now().isoformat(),
                "total_products": len(detailed_products),
                "scrape_stats": {
                    "total_attempted": len(items),
                    "successful": ok,
                    "failed": len(items) - ok
                },
                "failed_details": failed_details,
            }
            save_json(det_summary, scraper.data_dir / "products_detailed_summary.json", logger)
            
            print_success(f"Scraped {ok}/{len(items)} details")

        result["success"] = True
    except Exception as e:
        print_error(str(e))
        result["errors"].append(str(e))
    finally:
        result["duration"] = time.time() - t0
        # Close shared Playwright browser if scraper holds one
        if hasattr(scraper, "_close_browser"):
            await scraper._close_browser()

    print_header(f"{'✅' if result['success'] else '❌'} RESULT: {site.upper()}", "-")
    print_stat("Duration", format_duration(result['duration']), Colors.CYAN)
    print_stat("Categories", result['categories_scraped'], Colors.WHITE)
    print_stat("Products", result['products_found'], Colors.GREEN)
    print_stat("Details", result['details_scraped'], Colors.MAGENTA)
    print()
    return result


async def test_all_sites(categories_limit=3, products_per_category=5, detail_workers=16, category_filter=None):
    sites = list_available_sites()
    print_header(f"🧪 TESTING ALL ({len(sites)} sites)")
    results = {}
    for i, site in enumerate(sites, 1):
        print(f"\n{Colors.DIM}[{i}/{len(sites)}]{Colors.RESET}")
        try:
            results[site] = await test_site(site, categories_limit, products_per_category, detail_workers, category_filter=category_filter)
            await asyncio.sleep(2)
        except Exception as e:
            print_error(f"Failed: {e}")
            results[site] = {"success": False, "error": str(e)}
    
    print_header("📊 SUMMARY")
    for site, r in results.items():
        st = f"{Colors.GREEN}✅{Colors.RESET}" if r.get("success") else f"{Colors.RED}❌{Colors.RESET}"
        print(f"  {st} {site.upper():12} {r.get('products_found',0):5} prods, {r.get('details_scraped',0):5} dets")
    print()
    return results


async def main():
    parser = argparse.ArgumentParser(description="Fast E-commerce Scraper")
    sub = parser.add_subparsers(dest="cmd")

    tp = sub.add_parser("test", help="Test site with limits")
    tp.add_argument("--site", help="Site to test")
    tp.add_argument("--all-sites", action="store_true", help="Test all")
    tp.add_argument("--categories", type=int, default=3)
    tp.add_argument("--products", type=int, default=5)
    tp.add_argument("--detail-workers", type=int, default=16)
    tp.add_argument("--category", help="Filter by top-level category name (e.g. 'ÉLECTROMÉNAGER')")

    fp = sub.add_parser("full", help="Full scrape")
    fp.add_argument("--site", required=True)
    fp.add_argument("--workers", type=int, default=16)
    fp.add_argument("--detail-workers", type=int, default=16)
    fp.add_argument("--no-details", action="store_true")
    fp.add_argument("--category", help="Filter by top-level category name (e.g. 'ÉLECTROMÉNAGER')")

    sub.add_parser("list", help="List sites")
    
    args = parser.parse_args()
    
    if args.cmd == "test":
        if args.all_sites:
            await test_all_sites(args.categories, args.products, args.detail_workers, category_filter=getattr(args, 'category', None))
        elif args.site:
            await test_site(args.site, args.categories, args.products, args.detail_workers, category_filter=getattr(args, 'category', None))
        else:
            parser.error("--site or --all-sites required")
            
    elif args.cmd == "full":
        await run_full_scrape(args.site, args.workers, args.detail_workers, scrape_details=not args.no_details, category_filter=getattr(args, 'category', None))
            
    elif args.cmd == "list":
        print_header("📋 AVAILABLE SITES")
        for s in list_available_sites():
            print(f"  {Colors.GREEN}•{Colors.RESET} {s}")
        print()
    else:
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
