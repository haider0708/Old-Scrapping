"""
Batam e-commerce web scraper.
Uses Playwright for CSR category extraction, httpx + selectolax for SSR listings/details.
Platform: Magento 2 (Hyva + Alpine.js + Tailwind)
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import orjson
from playwright.async_api import async_playwright
from selectolax.parser import HTMLParser

# Ensure shop directory is on path for config import
_shop_dir = Path(__file__).resolve().parent
if str(_shop_dir) not in sys.path:
    sys.path.insert(0, str(_shop_dir))
import config

# -----------------------------------------------------------------------------
# Setup
# -----------------------------------------------------------------------------

_logger: logging.Logger | None = None
_run_dir: Path | None = None


def setup_run_directory() -> Path:
    """Create timestamped output folder batam/data/YYYY-MM-DD_HH-MM-SS/."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = config.DATA_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    global _run_dir
    _run_dir = run_dir
    return run_dir


def setup_logging(run_dir: Path) -> None:
    """Configure logging to stdout and a file in the run directory."""
    global _logger
    log_file = run_dir / "scraper.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )
    _logger = logging.getLogger(__name__)


def get_previous_run() -> Path | None:
    """Find the latest previous run folder (if any) for incremental mode."""
    if not config.DATA_DIR.exists():
        return None
    dirs = [
        d
        for d in config.DATA_DIR.iterdir()
        if d.is_dir() and re.match(r"\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}", d.name)
    ]
    if not dirs:
        return None
    dirs.sort(key=lambda d: d.name, reverse=True)
    prev = dirs[0]
    if prev == _run_dir:
        return dirs[1] if len(dirs) > 1 else None
    return prev


# -----------------------------------------------------------------------------
# Anti-Detection / HTTP (async)
# -----------------------------------------------------------------------------


def create_client() -> httpx.AsyncClient:
    """Create httpx.AsyncClient with HTTP/2, connection pool. Minimal headers to avoid bot detection."""
    headers = {
        "User-Agent": random.choice(config.USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    }
    return httpx.AsyncClient(
        http2=True,
        headers=headers,
        timeout=httpx.Timeout(
            config.READ_TIMEOUT,
            connect=config.CONNECT_TIMEOUT,
        ),
        limits=httpx.Limits(
            max_connections=config.POOL_MAX_CONNECTIONS,
            max_keepalive_connections=config.POOL_MAX_KEEPALIVE,
        ),
        follow_redirects=True,
    )


async def random_delay() -> None:
    """Sleep for a random duration between MIN_DELAY and MAX_DELAY."""
    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))


async def safe_request(
    url: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore
) -> tuple[str | None, Exception | None]:
    """
    Async GET with exponential backoff + jitter.
    Acquires semaphore before request. Returns (text, error); never raises.
    """
    async with semaphore:
        last_error: Exception | None = None
        for attempt in range(config.MAX_RETRIES):
            try:
                await random_delay()
                resp = await client.get(url)
                resp.raise_for_status()
                return resp.text, None
            except Exception as e:
                last_error = e
                wait = min(
                    config.BACKOFF_BASE**attempt + random.uniform(0, 1),
                    config.BACKOFF_MAX,
                )
                _logger.warning("Request failed (attempt %d/%d): %s. Retrying in %.1fs", attempt + 1, config.MAX_RETRIES, e, wait)
                await asyncio.sleep(wait)
        return None, last_error


# -----------------------------------------------------------------------------
# HTML Parsing (selectolax)
# -----------------------------------------------------------------------------


def parse_node_text(node: Any) -> str:
    """Safely extract trimmed text from a selectolax Node."""
    if node is None:
        return ""
    text = node.text(strip=True) or ""
    return text.strip()


def parse_node_attr(node: Any, attr: str) -> str:
    """Safely extract an attribute value from a selectolax Node."""
    if node is None:
        return ""
    attrs = node.attributes or {}
    return (attrs.get(attr) or "").strip()


def _abs_url(url: str) -> str:
    """Convert relative URL to absolute using BASE_URL."""
    if not url:
        return ""
    if url.startswith("http"):
        return url
    base = config.BASE_URL.rstrip("/")
    path = url if url.startswith("/") else "/" + url
    return base + path


def _extract_slug_from_url(url: str) -> str:
    """Extract Magento category slug from URL (e.g. /informatique.html -> informatique, /a/b.html -> a-b)."""
    if not url:
        return ""
    if "://" in url:
        parts = url.split("/", 3)
        url = "/" + parts[-1] if len(parts) > 3 else ""
    url = url.split("?")[0].rstrip("/")
    if url.endswith(".html"):
        url = url[:-5]
    url = url.strip("/")
    slug = url.replace("/", "-").lower()
    pattern = config.URL_PATTERNS.get("slug_sanitize")
    if pattern:
        slug = re.sub(pattern, "", slug)
    return slug or "unknown"


def _extract_product_id_from_url(url: str) -> str | None:
    """Extract Magento product ID from URL (e.g. product-name-43007743.html -> 43007743)."""
    if not url:
        return None
    pattern = config.URL_PATTERNS.get("id_from_url")
    if not pattern:
        return None
    m = re.search(pattern, url)
    return m.group(1) if m else None


# -----------------------------------------------------------------------------
# Categories (Playwright for CSR)
# -----------------------------------------------------------------------------


async def scrape_categories() -> list[dict]:
    """
    Use Playwright to render homepage (Alpine.js), extract category nav.
    Parse with selectolax. Build flat list with id, name, url, parent_id, level.
    """
    html = ""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=config.PLAYWRIGHT_HEADLESS)
        try:
            page = await browser.new_page()
            await page.goto(config.BASE_URL, wait_until="domcontentloaded", timeout=config.PLAYWRIGHT_TIMEOUT)
            await page.wait_for_selector(
                config.PLAYWRIGHT_WAIT_SELECTOR,
                timeout=config.PLAYWRIGHT_TIMEOUT,
                state="attached",
            )
            await asyncio.sleep(1)
            html = await page.content()
        except Exception as e:
            _logger.error("Playwright category fetch failed: %s", e)
            return []
        finally:
            await browser.close()

    if not html:
        return []

    tree = HTMLParser(html)
    categories: list[dict] = []
    seen_urls: set[str] = set()

    cs = config.CATEGORY_SELECTORS
    top_lis = tree.css(cs["top_block"])
    for top_idx, top_li in enumerate(top_lis):
        top_name_sel = cs.get("top_name")
        top_span = top_li.css_first(top_name_sel) if top_name_sel else None
        top_name = parse_node_text(top_span) if top_span else ""
        link_fb = cs.get("link_fallback", "a[href]")
        top_a = top_li.css_first(cs.get("top_link") or link_fb) or top_li.css_first(link_fb)
        top_url = _abs_url(parse_node_attr(top_a, "href")) if top_a else ""
        top_id = _extract_slug_from_url(top_url) if top_url else f"top_{top_idx}"
        if top_url and top_url not in seen_urls:
            seen_urls.add(top_url)
        categories.append({
            "id": top_id,
            "name": top_name,
            "url": top_url or None,
            "parent_id": None,
            "level": 0,
        })

        low_lis = top_li.css(cs["low_block"])
        for low_li in low_lis:
            low_a = low_li.css_first(cs["low_link"]) or low_li.css_first(link_fb)
            if not low_a:
                continue
            low_url = _abs_url(parse_node_attr(low_a, "href"))
            low_id = _extract_slug_from_url(low_url)
            if not low_url or low_url in seen_urls:
                continue
            seen_urls.add(low_url)
            categories.append({
                "id": low_id,
                "name": parse_node_text(low_a),
                "url": low_url,
                "parent_id": top_id,
                "level": 1,
            })

            sub_lis = low_li.css(cs["sub_block"])
            for sub_li in sub_lis:
                sub_a = sub_li.css_first(cs["sub_link"]) or sub_li.css_first(link_fb)
                if not sub_a:
                    continue
                sub_url = _abs_url(parse_node_attr(sub_a, "href"))
                sub_id = _extract_slug_from_url(sub_url)
                if not sub_url or sub_url in seen_urls:
                    continue
                seen_urls.add(sub_url)
                categories.append({
                    "id": sub_id,
                    "name": parse_node_text(sub_a),
                    "url": sub_url,
                    "parent_id": low_id,
                    "level": 2,
                })

    return categories


def get_leaf_categories(categories: list[dict]) -> list[dict]:
    """Filter to categories that have a URL and no children (leaves only)."""
    parent_ids = {c["parent_id"] for c in categories if c.get("parent_id")}
    return [c for c in categories if c.get("url") and c["id"] not in parent_ids]


# -----------------------------------------------------------------------------
# Queue Management (coroutine-safe)
# -----------------------------------------------------------------------------


class QueueFile:
    """
    Queue file with [PENDING], [DONE], [ERROR] sections.
    Uses asyncio.Lock for coroutine-safe reads/writes.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._pending: dict[str, str] = {}
        self._done: list[str] = []
        self._errors: list[tuple[str, str]] = []

    async def load(self) -> None:
        """Load queue from file."""
        async with self._lock:
            if not self._path.exists():
                self._pending = {}
                self._done = []
                self._errors = []
                return
            text = self._path.read_text(encoding="utf-8")
            self._pending = {}
            self._done = []
            self._errors = []
            section = "pending"
            for line in text.splitlines():
                line = line.strip()
                if line == "[PENDING]":
                    section = "pending"
                    continue
                if line == "[DONE]":
                    section = "done"
                    continue
                if line == "[ERROR]":
                    section = "error"
                    continue
                if not line:
                    continue
                if section == "pending" and ":" in line:
                    key, _, url = line.partition(":")
                    self._pending[key.strip()] = url.strip()
                elif section == "done":
                    self._done.append(line)
                elif section == "error" and ":" in line:
                    key, _, rest = line.partition(":")
                    self._errors.append((key.strip(), rest.strip()))

    async def save(self) -> None:
        """Write queue to file."""
        async with self._lock:
            lines = ["[PENDING]"]
            for key, url in self._pending.items():
                lines.append(f"{key}: {url}")
            lines.append("[DONE]")
            for key in self._done:
                lines.append(key)
            lines.append("[ERROR]")
            for key, msg in self._errors:
                lines.append(f"{key}: {msg}")
            self._path.write_text("\n".join(lines), encoding="utf-8")

    async def move_to_done(self, key: str) -> None:
        """Move key from PENDING to DONE."""
        async with self._lock:
            if key in self._pending:
                del self._pending[key]
                self._done.append(key)

    async def move_to_error(self, key: str, msg: str = "") -> None:
        """Move key from PENDING to ERROR."""
        async with self._lock:
            if key in self._pending:
                del self._pending[key]
                self._errors.append((key, msg))

    @property
    def error_count(self) -> int:
        """Return number of entries in ERROR section."""
        return len(self._errors)


async def build_category_queue(leaf_categories: list[dict], run_dir: Path) -> QueueFile:
    """Create category_queue.txt from leaf categories."""
    path = run_dir / config.QUEUE_CATEGORY_FILENAME
    q = QueueFile(path)
    for cat in leaf_categories:
        key = f"cat_{cat['id']}"
        q._pending[key] = cat["url"]
    q._done = []
    q._errors = []
    await q.save()
    return q


async def build_product_queue(products: list[dict], run_dir: Path) -> QueueFile:
    """Create product_queue.txt from products."""
    path = run_dir / config.QUEUE_PRODUCT_FILENAME
    q = QueueFile(path)
    seen: set[str] = set()
    for p in products:
        pid = str(p.get("id", ""))
        url = p.get("url", "")
        if pid and url and pid not in seen:
            seen.add(pid)
            q._pending[f"prod_{pid}"] = url
    q._done = []
    q._errors = []
    await q.save()
    return q


# -----------------------------------------------------------------------------
# Listing Scraping (async, httpx, SSR)
# -----------------------------------------------------------------------------


def scrape_listing_page(html: str, category_url: str) -> list[dict]:
    """Parse one Magento listing page."""
    tree = HTMLParser(html)
    elements = tree.css(config.LISTING_SELECTORS["element"])
    products = []
    for elem in elements:
        id_el = elem.css_first(config.LISTING_SELECTORS["id"])
        pid = parse_node_attr(id_el, config.LISTING_SELECTORS["id_attr"]) if id_el else ""
        name_el = elem.css_first(config.LISTING_SELECTORS["name"])
        url = _abs_url(parse_node_attr(name_el, "href") if name_el else "")
        name = parse_node_text(name_el)
        if not pid and url:
            pid = _extract_product_id_from_url(url)
        if not pid:
            continue

        img_el = elem.css_first(config.LISTING_SELECTORS["image"])
        img_url = ""
        if img_el:
            for attr in config.LISTING_SELECTORS["image_attrs"]:
                img_url = parse_node_attr(img_el, attr)
                if img_url:
                    break
        img_url = _abs_url(img_url) if img_url else ""

        price_el = elem.css_first(config.LISTING_SELECTORS["price"])
        price = parse_node_text(price_el)
        price_num_el = elem.css_first(config.LISTING_SELECTORS["price_numeric"])
        price_attr = config.LISTING_SELECTORS.get("price_numeric_attr", "data-price-amount")
        price_numeric = parse_node_attr(price_num_el, price_attr) if price_num_el else ""
        old_price_el = elem.css_first(config.LISTING_SELECTORS["old_price"])
        old_price = parse_node_text(old_price_el)

        av_sel = config.LISTING_SELECTORS["availability"]["selector"]
        av_el = elem.css_first(av_sel)
        availability = parse_node_text(av_el)

        products.append({
            "id": pid,
            "name": name,
            "url": url,
            "category_url": category_url,
            "image": img_url,
            "price": price,
            "price_numeric": price_numeric,
            "old_price": old_price,
            "availability": availability,
        })
    return products


def _get_next_page_url(html: str, current_url: str) -> str | None:
    """Find next page link. Returns None if no more pages."""
    tree = HTMLParser(html)
    next_a = tree.css_first(config.PAGINATION_SELECTORS["next_page"])
    if not next_a:
        return None
    href = parse_node_attr(next_a, "href")
    return _abs_url(href) if href else None


async def scrape_category_listings(
    category: dict,
    queue: QueueFile,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    """Paginate through category, collect all products. Update queue (DONE/ERROR)."""
    key = f"cat_{category['id']}"
    url = category["url"]
    all_products: list[dict] = []
    try:
        while url:
            html, err = await safe_request(url, client, semaphore)
            if err or not html:
                await queue.move_to_error(key, str(err))
                return all_products
            products = scrape_listing_page(html, category["url"])
            all_products.extend(products)
            url = _get_next_page_url(html, url)
        await queue.move_to_done(key)
    except Exception as e:
        _logger.exception("Category %s failed: %s", key, e)
        await queue.move_to_error(key, str(e))
    return all_products


async def scrape_all_listings(
    categories: list[dict],
    run_dir: Path,
) -> tuple[list[dict], int]:
    """
    Scrape all categories concurrently. Save products_raw.json.
    Returns (products, error_count).
    """
    queue = await build_category_queue(categories, run_dir)
    client = create_client()
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

    all_products: list[dict] = []
    product_by_id: dict[str, dict] = {}
    tasks = [
        scrape_category_listings(cat, queue, client, semaphore)
        for cat in categories
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await client.aclose()

    for r in results:
        if isinstance(r, Exception):
            _logger.error("Category task failed: %s", r)
            continue
        for p in r:
            pid = str(p.get("id", ""))
            if pid and pid not in product_by_id:
                product_by_id[pid] = p
                all_products.append(p)

    products_list = list(product_by_id.values())
    out_path = run_dir / config.OUTPUT_PRODUCTS_RAW
    out_path.write_bytes(orjson.dumps(products_list, option=orjson.OPT_INDENT_2))

    await queue.save()
    return products_list, queue.error_count


# -----------------------------------------------------------------------------
# Detail Scraping (async, httpx, SSR)
# -----------------------------------------------------------------------------


def scrape_product_detail(html: str, url: str) -> dict:
    """Parse one Magento product detail page."""
    tree = HTMLParser(html)
    sel = config.DETAIL_SELECTORS

    def _text(css: str | None) -> str:
        if not css:
            return ""
        n = tree.css_first(css)
        return parse_node_text(n)

    def _attr(css: str | None, attr: str) -> str:
        if not css:
            return ""
        n = tree.css_first(css)
        return parse_node_attr(n, attr)

    title = _text(sel["title"])
    ref_el = tree.css_first(sel["reference"])
    reference = parse_node_attr(ref_el, sel["reference_attr"]) if ref_el else ""

    price = _text(sel["price"])
    price_num_el = tree.css_first(sel["price_numeric"])
    price_numeric = parse_node_attr(price_num_el, sel["price_numeric_attr"]) if price_num_el else ""
    old_price = _text(sel["old_price"])

    unavail_el = tree.css_first(sel["global_availability"])
    availability = parse_node_text(unavail_el) if unavail_el else ""
    in_stock_text = sel.get("availability_in_stock_text")
    fallback_scope = sel.get("availability_fallback_scope")
    if not availability and in_stock_text and fallback_scope:
        for node in tree.css(fallback_scope):
            if in_stock_text in (node.text() or ""):
                availability = in_stock_text
                break

    desc_el = tree.css_first(sel["description"])
    description = parse_node_text(desc_el) if desc_el else ""

    specs_dict: dict[str, str] = {}
    specs_container = tree.css_first(sel["specs"]["container"])
    if specs_container:
        spec = sel["specs"]
        for row in specs_container.css(spec["row"]):
            key_el = row.css_first(spec["key"])
            val_el = row.css_first(spec["value"])
            if key_el and val_el:
                specs_dict[parse_node_text(key_el)] = parse_node_text(val_el)

    imgs = tree.css(sel["images"]["main"])
    image_main = ""
    images_list: list[str] = []
    if imgs:
        for img in imgs:
            src = parse_node_attr(img, "src")
            if src:
                full = _abs_url(src)
                images_list.append(full)
                if not image_main:
                    image_main = full

    pid = _extract_product_id_from_url(url) or reference or ""

    return {
        "id": pid,
        "url": url,
        "title": title,
        "brand": None,
        "reference": reference,
        "price": price,
        "price_numeric": price_numeric,
        "old_price": old_price,
        "availability": availability,
        "description": description,
        "specs": specs_dict,
        "image_main": image_main,
        "images": images_list,
    }


async def scrape_details_for_urls(
    urls: list[str],
    semaphore: asyncio.Semaphore,
) -> tuple[dict[str, dict], int]:
    """Scrape detail pages for given URLs. Returns (details_by_id, error_count)."""
    client = create_client()
    details: dict[str, dict] = {}
    errors = 0

    async def _fetch(url: str) -> dict | None:
        nonlocal errors
        html, err = await safe_request(url, client, semaphore)
        if err or not html:
            errors += 1
            return None
        d = scrape_product_detail(html, url)
        return d

    tasks = [_fetch(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await client.aclose()

    for r in results:
        if isinstance(r, Exception):
            errors += 1
            continue
        if r and r.get("id"):
            details[str(r["id"])] = r
    return details, errors


# -----------------------------------------------------------------------------
# Incremental Diffing (multiprocessing)
# -----------------------------------------------------------------------------


def _diff_products_impl(
    current_list: list[dict], previous_list: list[dict]
) -> dict[str, Any]:
    """Compare current vs previous listings by price and availability. CPU-bound."""
    prev_by_id = {str(p["id"]): p for p in previous_list if p.get("id")}
    curr_by_id = {str(p["id"]): p for p in current_list if p.get("id")}

    new_ids = set(curr_by_id) - set(prev_by_id)
    removed_ids = set(prev_by_id) - set(curr_by_id)
    common_ids = set(curr_by_id) & set(prev_by_id)

    changed = []
    unchanged = []
    for pid in common_ids:
        curr = curr_by_id[pid]
        prev = prev_by_id[pid]
        curr_price = (curr.get("price") or "").strip()
        prev_price = (prev.get("price") or "").strip()
        curr_av = (curr.get("availability") or "").strip()
        prev_av = (prev.get("availability") or "").strip()
        if curr_price != prev_price or curr_av != prev_av:
            changed.append(curr)
        else:
            unchanged.append(curr)

    return {
        "new": [curr_by_id[pid] for pid in new_ids],
        "removed": [prev_by_id[pid] for pid in removed_ids],
        "changed": changed,
        "unchanged": unchanged,
        "removed_ids": list(removed_ids),
    }


def _patch_details_impl(
    previous_details: dict[str, dict],
    changed_details: dict[str, dict],
    removed_ids: list[str],
    new_details: dict[str, dict],
) -> dict[str, dict]:
    """Merge changed/new into previous; mark removed. CPU-bound."""
    result = deepcopy(previous_details)
    for pid, d in changed_details.items():
        result[pid] = d
    for pid, d in new_details.items():
        result[pid] = d
    for pid in removed_ids:
        if pid in result:
            result[pid] = {**result[pid], "removed": True}
    return result


async def diff_products(
    current_listings: list[dict], previous_listings: list[dict]
) -> dict[str, Any]:
    """Run diff in process pool."""
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=config.PROCESS_POOL_SIZE) as pool:
        return await loop.run_in_executor(
            pool,
            _diff_products_impl,
            current_listings,
            previous_listings,
        )


async def patch_details(
    previous_details: dict[str, dict],
    changed_details: dict[str, dict],
    removed_ids: list[str],
    new_details: dict[str, dict],
) -> dict[str, dict]:
    """Run patch in process pool."""
    loop = asyncio.get_event_loop()
    with ProcessPoolExecutor(max_workers=config.PROCESS_POOL_SIZE) as pool:
        return await loop.run_in_executor(
            pool,
            _patch_details_impl,
            previous_details,
            changed_details,
            removed_ids,
            new_details,
        )


# -----------------------------------------------------------------------------
# Change Tracking
# -----------------------------------------------------------------------------


def update_product_history(
    current_data: dict[str, dict],
    run_timestamp: str,
) -> None:
    """
    Update product_history.json. Append to history only when value actually changes.
    """
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PRODUCT_HISTORY_FILE
    if path.exists():
        raw = path.read_bytes()
        history = orjson.loads(raw)
    else:
        history = {}

    for pid, prod in current_data.items():
        if prod.get("removed"):
            if pid in history:
                history[pid]["removed_at"] = run_timestamp
            continue
        if pid not in history:
            history[pid] = {
                "first_seen": run_timestamp,
                "removed_at": None,
                "price_history": [{"value": prod.get("price"), "recorded_at": run_timestamp}],
                "availability_history": [{"value": prod.get("availability"), "recorded_at": run_timestamp}],
            }
            continue
        h = history[pid]
        h["removed_at"] = None
        last_price = h["price_history"][-1]["value"] if h["price_history"] else None
        last_av = h["availability_history"][-1]["value"] if h["availability_history"] else None
        curr_price = prod.get("price")
        curr_av = prod.get("availability")
        if curr_price != last_price:
            h["price_history"].append({"value": curr_price, "recorded_at": run_timestamp})
        if curr_av != last_av:
            h["availability_history"].append({"value": curr_av, "recorded_at": run_timestamp})

    path.write_bytes(orjson.dumps(history, option=orjson.OPT_INDENT_2))


# -----------------------------------------------------------------------------
# Summary and Cleanup
# -----------------------------------------------------------------------------


def write_summary(run_dir: Path, stats: dict) -> None:
    """Write summary.json with counts, errors, duration, timestamp."""
    path = run_dir / config.OUTPUT_SUMMARY
    path.write_bytes(orjson.dumps(stats, option=orjson.OPT_INDENT_2))


def cleanup_queues(run_dir: Path) -> None:
    """Delete queue files after run."""
    for fname in (config.QUEUE_CATEGORY_FILENAME, config.QUEUE_PRODUCT_FILENAME):
        p = run_dir / fname
        if p.exists():
            p.unlink()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


async def main() -> None:
    """Async entrypoint. Orchestrate full pipeline."""
    start = time.perf_counter()
    run_dir = setup_run_directory()
    setup_logging(run_dir)
    _logger.info("Run directory: %s", run_dir)

    stats = {
        "total_products": 0,
        "total_details": 0,
        "error_count": 0,
        "duration_seconds": 0,
        "timestamp": datetime.now().isoformat(),
        "no_changes": False,
    }

    try:
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

        # 1. Scrape categories (Playwright)
        _logger.info("Scraping categories (Playwright)...")
        categories = await scrape_categories()
        leaf_categories = get_leaf_categories(categories)
        cat_path = run_dir / config.OUTPUT_CATEGORIES
        cat_path.write_bytes(orjson.dumps(categories, option=orjson.OPT_INDENT_2))
        _logger.info("Categories: %d total, %d leaf", len(categories), len(leaf_categories))

        # 2. Scrape listings
        _logger.info("Scraping listings...")
        products, list_errors = await scrape_all_listings(leaf_categories, run_dir)
        stats["total_products"] = len(products)
        stats["error_count"] = list_errors
        _logger.info("Products: %d (errors: %d)", len(products), list_errors)

        # 3. Incremental check
        prev_run = get_previous_run()
        if prev_run and prev_run != run_dir:
            prev_products_path = prev_run / config.OUTPUT_PRODUCTS_RAW
            prev_details_path = prev_run / config.OUTPUT_DETAILS_RAW
            if prev_products_path.exists() and prev_details_path.exists():
                prev_products = orjson.loads(prev_products_path.read_bytes())
                diff_result = await diff_products(products, prev_products)
                new_list = diff_result["new"]
                changed_list = diff_result["changed"]
                removed_ids = diff_result["removed_ids"]

                if not new_list and not changed_list and not removed_ids:
                    shutil.copy(prev_details_path, run_dir / config.OUTPUT_DETAILS_RAW)
                    prev_details = orjson.loads(prev_details_path.read_bytes())
                    stats["no_changes"] = True
                    stats["total_details"] = len(prev_details)
                    _logger.info("No changes detected. Skipping detail scrape.")
                else:
                    products_to_scrape = new_list + changed_list
                    await build_product_queue(products_to_scrape, run_dir)
                    urls_to_scrape = [p["url"] for p in products_to_scrape if p.get("url")]
                    changed_ids = {str(p["id"]) for p in changed_list}
                    new_ids = {str(p["id"]) for p in new_list}
                    detail_results: dict[str, dict] = {}
                    if urls_to_scrape:
                        detail_results, det_errors = await scrape_details_for_urls(urls_to_scrape, semaphore)
                        stats["error_count"] += det_errors
                    prev_details = orjson.loads(prev_details_path.read_bytes())
                    patched = await patch_details(
                        prev_details,
                        {k: v for k, v in detail_results.items() if k in changed_ids},
                        removed_ids,
                        {k: v for k, v in detail_results.items() if k in new_ids},
                    )
                    details_path = run_dir / config.OUTPUT_DETAILS_RAW
                    details_path.write_bytes(orjson.dumps(patched, option=orjson.OPT_INDENT_2))
                    stats["total_details"] = len(patched)
            else:
                await build_product_queue(products, run_dir)
                urls = [p["url"] for p in products if p.get("url")]
                details_by_id, det_errors = await scrape_details_for_urls(urls, semaphore)
                stats["error_count"] += det_errors
                details_path = run_dir / config.OUTPUT_DETAILS_RAW
                details_path.write_bytes(orjson.dumps(details_by_id, option=orjson.OPT_INDENT_2))
                stats["total_details"] = len(details_by_id)
        else:
            await build_product_queue(products, run_dir)
            urls = [p["url"] for p in products if p.get("url")]
            details_by_id, det_errors = await scrape_details_for_urls(urls, semaphore)
            stats["error_count"] += det_errors
            details_path = run_dir / config.OUTPUT_DETAILS_RAW
            details_path.write_bytes(orjson.dumps(details_by_id, option=orjson.OPT_INDENT_2))
            stats["total_details"] = len(details_by_id)

        # 4. Change tracking
        run_ts = datetime.now().isoformat()
        details_for_history = orjson.loads((run_dir / config.OUTPUT_DETAILS_RAW).read_bytes())
        update_product_history(details_for_history, run_ts)

        stats["duration_seconds"] = round(time.perf_counter() - start, 2)
        write_summary(run_dir, stats)
        cleanup_queues(run_dir)
        _logger.info("Done. Duration: %.2fs", stats["duration_seconds"])

    except Exception as e:
        _logger.exception("Fatal error: %s", e)
        stats["duration_seconds"] = round(time.perf_counter() - start, 2)
        stats["error_count"] = stats.get("error_count", 0) + 1
        write_summary(run_dir, stats)


def run() -> None:
    """Entry point for asyncio.run."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
