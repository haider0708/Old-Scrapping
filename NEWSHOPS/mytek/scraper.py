"""
Mytek e-commerce web scraper.
Categories: SSR (httpx). Listings and details: CSR (Playwright browser pool).
Platform: Magento 2 (Rootways Megamenu)
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
from playwright.async_api import async_playwright, Page
from selectolax.parser import HTMLParser

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
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    run_dir = config.DATA_DIR / timestamp
    run_dir.mkdir(parents=True, exist_ok=True)
    global _run_dir
    _run_dir = run_dir
    return run_dir


def setup_logging(run_dir: Path) -> None:
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
# Browser Pool
# -----------------------------------------------------------------------------


class BrowserPool:
    """Async pool of Playwright pages. Acquire/release for concurrent CSR scraping."""

    def __init__(self, size: int) -> None:
        self._size = size
        self._queue: asyncio.Queue[Page] = asyncio.Queue()
        self._pages: list[Page] = []
        self._browser = None
        self._playwright = None

    async def __aenter__(self) -> "BrowserPool":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=config.PLAYWRIGHT_HEADLESS)
        for _ in range(self._size):
            page = await self._browser.new_page()
            self._pages.append(page)
            await self._queue.put(page)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def acquire(self) -> Page:
        return await self._queue.get()

    async def release(self, page: Page) -> None:
        await self._queue.put(page)


# -----------------------------------------------------------------------------
# Anti-Detection / HTTP
# -----------------------------------------------------------------------------


def create_client() -> httpx.AsyncClient:
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
    await asyncio.sleep(random.uniform(config.MIN_DELAY, config.MAX_DELAY))


async def safe_http_request(
    url: str, client: httpx.AsyncClient, semaphore: asyncio.Semaphore
) -> tuple[str | None, Exception | None]:
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
# HTML Parsing
# -----------------------------------------------------------------------------


def parse_node_text(node: Any) -> str:
    if node is None:
        return ""
    return (node.text(strip=True) or "").strip()


def parse_node_attr(node: Any, attr: str) -> str:
    if node is None:
        return ""
    attrs = node.attributes or {}
    return (attrs.get(attr) or "").strip()


def _abs_url(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http"):
        return url
    base = config.BASE_URL.rstrip("/")
    path = url if url.startswith("/") else "/" + url
    return base + path


def _extract_slug_from_url(url: str) -> str:
    if not url:
        return ""
    if "://" in url:
        parts = url.split("/", 3)
        url = "/" + parts[-1] if len(parts) > 3 else ""
    url = url.split("?")[0].rstrip("/")
    url = url.strip("/")
    parts = [p for p in url.split("/") if p and p != "catalog"]
    slug = "-".join(parts).lower() if parts else "unknown"
    pattern = config.URL_PATTERNS.get("slug_sanitize")
    if pattern:
        slug = re.sub(pattern, "", slug)
    return slug or "unknown"


def _extract_category_id_from_href(href: str) -> str | None:
    if not href:
        return None
    pattern = config.URL_PATTERNS.get("category_id_from_pagination")
    if not pattern:
        return None
    m = re.search(pattern, href)
    return m.group(1) if m else None


# -----------------------------------------------------------------------------
# Categories (httpx, SSR)
# -----------------------------------------------------------------------------


async def scrape_categories(client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> list[dict]:
    html, err = await safe_http_request(config.BASE_URL, client, semaphore)
    if err or not html:
        _logger.error("Category fetch failed: %s", err)
        return []

    tree = HTMLParser(html)
    categories: list[dict] = []
    seen_urls: set[str] = set()
    cs = config.CATEGORY_SELECTORS
    link_fb = cs.get("link_fallback", "a[href]")

    nav = tree.css_first(cs["nav_container"])
    if not nav:
        _logger.warning("Nav container not found: %s", cs["nav_container"])
        return []

    top_items = nav.css(cs["top_items"])
    for top_idx, top_li in enumerate(top_items):
        top_name_el = top_li.css_first(cs["top_name"])
        top_name = parse_node_text(top_name_el) if top_name_el else ""
        top_id = f"top_{top_idx}"
        categories.append({
            "id": top_id,
            "name": top_name,
            "url": None,
            "parent_id": None,
            "level": 0,
        })

        children = top_li.css_first(cs["children_container"])
        if not children:
            continue

        low_blocks = children.css(cs["low_blocks"])
        lows_in_this_top: list[tuple[str, str, str]] = []
        for low_block in low_blocks:
            low_a = low_block.css_first(cs["low_link"]) or low_block.css_first(link_fb)
            if not low_a:
                continue
            low_url = _abs_url(parse_node_attr(low_a, "href"))
            low_id = _extract_slug_from_url(low_url)
            low_name = parse_node_text(low_a)
            if low_url and low_url not in seen_urls:
                seen_urls.add(low_url)
                categories.append({
                    "id": low_id,
                    "name": low_name,
                    "url": low_url,
                    "parent_id": top_id,
                    "level": 1,
                })
                lows_in_this_top.append((low_id, low_url, low_name))

        sub_lists = children.css(cs["sub_lists"])
        for sub_ul in sub_lists:
            for sub_a in sub_ul.css(cs["sub_items"]):
                sub_url = _abs_url(parse_node_attr(sub_a, "href"))
                sub_id = _extract_slug_from_url(sub_url)
                if not sub_url or sub_url in seen_urls:
                    continue
                seen_urls.add(sub_url)
                sub_name_el = sub_a.css_first(cs.get("sub_name"))
                sub_name = parse_node_text(sub_name_el) if sub_name_el else parse_node_text(sub_a)
                parent_id = top_id
                for lid, lurl, _ in lows_in_this_top:
                    lb = lurl.replace(".html", "").rstrip("/")
                    if sub_url.startswith(lb + "/") or sub_url == lb:
                        parent_id = lid
                        break
                categories.append({
                    "id": sub_id,
                    "name": sub_name,
                    "url": sub_url,
                    "parent_id": parent_id,
                    "level": 2,
                })

    return categories


def get_leaf_categories(categories: list[dict]) -> list[dict]:
    parent_ids = {c["parent_id"] for c in categories if c.get("parent_id")}
    return [c for c in categories if c.get("url") and c["id"] not in parent_ids]


# -----------------------------------------------------------------------------
# Queue Management
# -----------------------------------------------------------------------------


class QueueFile:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._pending: dict[str, str] = {}
        self._done: list[str] = []
        self._errors: list[tuple[str, str]] = []

    async def load(self) -> None:
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
        async with self._lock:
            if key in self._pending:
                del self._pending[key]
                self._done.append(key)

    async def move_to_error(self, key: str, msg: str = "") -> None:
        async with self._lock:
            if key in self._pending:
                del self._pending[key]
                self._errors.append((key, msg))

    @property
    def error_count(self) -> int:
        return len(self._errors)


async def build_category_queue(leaf_categories: list[dict], run_dir: Path) -> QueueFile:
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
# Listing Scraping (Playwright, CSR)
# -----------------------------------------------------------------------------


def scrape_listing_page(html: str, category_url: str) -> list[dict]:
    tree = HTMLParser(html)
    ls = config.LISTING_SELECTORS
    elements = tree.css(ls["element"])
    products = []
    for elem in elements:
        id_el = elem if ls.get("id") is None else elem.css_first(ls["id"])
        pid = parse_node_attr(id_el, ls["id_attr"]) if id_el else ""
        if not pid:
            continue

        name_el = elem.css_first(ls.get("name") or ls.get("url"))
        url = _abs_url(parse_node_attr(name_el, "href")) if name_el else ""
        name = parse_node_text(name_el)

        img_el = elem.css_first(ls["image"])
        img_url = ""
        if img_el:
            for attr in ls["image_attrs"]:
                img_url = parse_node_attr(img_el, attr)
                if img_url:
                    break
        img_url = _abs_url(img_url) if img_url else ""

        price_el = elem.css_first(ls["price"])
        price = parse_node_text(price_el)
        old_price_el = elem.css_first(ls["old_price"])
        old_price = parse_node_text(old_price_el)

        av_container = elem.css_first(ls["availability"].get("container", ""))
        availability = ""
        if av_container:
            status_el = av_container.css_first(ls["availability"].get("status", "div.stock"))
            availability = parse_node_text(status_el) if status_el else ""

        sku_el = elem.css_first(ls.get("sku", ""))
        sku = parse_node_text(sku_el) if sku_el else ""

        brand_el = elem.css_first(ls.get("brand", ""))
        brand = ""
        if brand_el:
            brand = parse_node_attr(brand_el, ls.get("brand_attr", "src"))
            brand = _abs_url(brand) if brand else ""

        products.append({
            "id": pid,
            "name": name,
            "url": url,
            "category_url": category_url,
            "image": img_url,
            "price": price,
            "price_numeric": price,
            "old_price": old_price,
            "availability": availability,
            "sku": sku,
            "brand": brand or None,
        })
    return products


def _extract_category_id_and_next_url(html: str, current_url: str) -> tuple[str | None, str | None]:
    tree = HTMLParser(html)
    ps = config.PAGINATION_SELECTORS
    cat_id: str | None = None
    next_url: str | None = None

    page_items = tree.css("ul.pagination li.page-item")
    for li in page_items:
        a_el = li.css_first("a.page-link")
        if not a_el:
            continue
        href = parse_node_attr(a_el, "href")
        if not href:
            continue
        cid = _extract_category_id_from_href(href)
        if cid and not cat_id:
            cat_id = cid

    last_li = page_items[-1] if page_items else None
    disabled_sel = ps.get("disabled_indicator", "li.page-item.disabled")
    if last_li:
        li_classes = (last_li.attributes or {}).get("class") or ""
        if "disabled" not in li_classes:
            next_a = last_li.css_first("a.page-link")
            if next_a:
                next_url = _abs_url(parse_node_attr(next_a, "href"))

    return cat_id, next_url


def _build_paginated_url(base_url: str, cat_id: str, page_num: int) -> str:
    sep = "&" if "?" in base_url else "?"
    return f"{base_url}{sep}id={cat_id}&p={page_num}"


async def scrape_category_listings(
    category: dict,
    queue: QueueFile,
    pool: BrowserPool,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    key = f"cat_{category['id']}"
    url = category["url"]
    all_products: list[dict] = []
    cat_id: str | None = None

    try:
        page = await pool.acquire()
        try:
            while url:
                async with semaphore:
                    await random_delay()
                    await page.goto(url, wait_until="domcontentloaded", timeout=config.PLAYWRIGHT_TIMEOUT)
                    await page.wait_for_selector(
                        config.PLAYWRIGHT_LISTING_WAIT,
                        timeout=config.PLAYWRIGHT_TIMEOUT,
                        state="attached",
                    )
                    await asyncio.sleep(1)
                    html = await page.content()

                cid, next_url = _extract_category_id_and_next_url(html, url)
                if cid and not cat_id:
                    cat_id = cid

                products = scrape_listing_page(html, category["url"])
                all_products.extend(products)

                if not next_url:
                    break
                url = next_url

            await queue.move_to_done(key)
        finally:
            await pool.release(page)
    except Exception as e:
        _logger.exception("Category %s failed: %s", key, e)
        await queue.move_to_error(key, str(e))

    return all_products


async def scrape_all_listings(
    categories: list[dict],
    run_dir: Path,
    pool: BrowserPool,
) -> tuple[list[dict], int]:
    queue = await build_category_queue(categories, run_dir)
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)

    all_products: list[dict] = []
    product_by_id: dict[str, dict] = {}
    tasks = [
        scrape_category_listings(cat, queue, pool, semaphore)
        for cat in categories
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

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
# Detail Scraping (Playwright, CSR)
# -----------------------------------------------------------------------------


def scrape_product_detail(html: str, url: str) -> dict:
    tree = HTMLParser(html)
    sel = config.DETAIL_SELECTORS

    def _text(css: str | None) -> str:
        if not css:
            return ""
        n = tree.css_first(css)
        return parse_node_text(n)

    title = _text(sel["title"])
    sku_el = tree.css_first(sel.get("sku", ""))
    sku = parse_node_text(sku_el) if sku_el else ""

    price = _text(sel["price"])
    old_price = _text(sel["old_price"])
    special_price = _text(sel["special_price"])
    discount = _text(sel.get("discount", ""))
    price_numeric = special_price or price

    avail_el = tree.css_first(sel.get("global_availability", ""))
    availability = parse_node_text(avail_el) if avail_el else ""

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

    availability_per_shop: list[dict] = []
    av_shop = sel.get("availability_per_shop")
    if av_shop:
        container = tree.css_first(av_shop.get("container", ""))
        if container:
            for row in container.css("tr"):
                cells = row.css("td")
                if len(cells) >= 2:
                    shop_name = parse_node_text(cells[0])
                    status_el = cells[1]
                    status_classes = (status_el.attributes or {}).get("class") or ""
                    if av_shop.get("in_stock_class") in status_classes:
                        status = "En stock"
                    elif av_shop.get("on_order_class") in status_classes:
                        status = "Sur commande"
                    elif av_shop.get("incoming_class") in status_classes:
                        status = "En arrivage"
                    else:
                        status = parse_node_text(status_el)
                    availability_per_shop.append({"shop": shop_name, "status": status})

    imgs_config = sel["images"]
    images_list: list[str] = []
    image_main = ""
    for img_el in tree.css(imgs_config["main"]):
        src = parse_node_attr(img_el, "src") or parse_node_attr(img_el, "data-src")
        if src:
            full = _abs_url(src)
            images_list.append(full)
            if not image_main:
                image_main = full
    for thumb in tree.css(imgs_config.get("thumbnails", "")):
        src = parse_node_attr(thumb, "src") or parse_node_attr(thumb, "data-src")
        if src:
            full = _abs_url(src)
            if full not in images_list:
                images_list.append(full)

    installment_text = ""
    inst_config = sel.get("installment")
    if inst_config:
        container = tree.css_first(inst_config.get("container", ""))
        if container:
            installment_text = parse_node_text(container)

    pid = ""
    for prod in tree.css("div.product-container[data-product-id], [data-product-id]"):
        pid = parse_node_attr(prod, "data-product-id")
        if pid:
            break
    if not pid and url:
        m = re.search(config.URL_PATTERNS.get("id_from_url", r"-(\d+)\.html"), url)
        pid = m.group(1) if m else ""
    if not pid:
        pid = sku or ""

    return {
        "id": pid,
        "url": url,
        "title": title,
        "brand": None,
        "reference": sku,
        "sku": sku,
        "price": price,
        "price_numeric": price_numeric,
        "old_price": old_price,
        "special_price": special_price,
        "discount": discount,
        "availability": availability,
        "availability_per_shop": availability_per_shop if availability_per_shop else None,
        "description": description,
        "specs": specs_dict,
        "installment": installment_text or None,
        "image_main": image_main,
        "images": images_list,
    }


async def scrape_details_for_urls(
    urls: list[str],
    pool: BrowserPool,
    semaphore: asyncio.Semaphore,
) -> tuple[dict[str, dict], int]:
    details: dict[str, dict] = {}
    errors = 0

    async def _fetch(url: str) -> dict | None:
        nonlocal errors
        page = await pool.acquire()
        try:
            async with semaphore:
                await random_delay()
                await page.goto(url, wait_until="domcontentloaded", timeout=config.PLAYWRIGHT_TIMEOUT)
                await page.wait_for_selector(
                    config.PLAYWRIGHT_DETAIL_WAIT,
                    timeout=config.PLAYWRIGHT_TIMEOUT,
                    state="attached",
                )
                await asyncio.sleep(1)
                html = await page.content()
            return scrape_product_detail(html, url)
        except Exception:
            errors += 1
            return None
        finally:
            await pool.release(page)

    tasks = [_fetch(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

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
    path = run_dir / config.OUTPUT_SUMMARY
    path.write_bytes(orjson.dumps(stats, option=orjson.OPT_INDENT_2))


def cleanup_queues(run_dir: Path) -> None:
    for fname in (config.QUEUE_CATEGORY_FILENAME, config.QUEUE_PRODUCT_FILENAME):
        p = run_dir / fname
        if p.exists():
            p.unlink()


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


async def main() -> None:
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
        client = create_client()

        _logger.info("Scraping categories (httpx SSR)...")
        categories = await scrape_categories(client, semaphore)
        await client.aclose()
        leaf_categories = get_leaf_categories(categories)
        cat_path = run_dir / config.OUTPUT_CATEGORIES
        cat_path.write_bytes(orjson.dumps(categories, option=orjson.OPT_INDENT_2))
        _logger.info("Categories: %d total, %d leaf", len(categories), len(leaf_categories))

        _logger.info("Scraping listings (Playwright)...")
        async with BrowserPool(config.BROWSER_POOL_SIZE) as pool:
            products, list_errors = await scrape_all_listings(leaf_categories, run_dir, pool)
            stats["total_products"] = len(products)
            stats["error_count"] = list_errors
            _logger.info("Products: %d (errors: %d)", len(products), list_errors)

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
                            detail_results, det_errors = await scrape_details_for_urls(
                                urls_to_scrape, pool, semaphore
                            )
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
                    details_by_id, det_errors = await scrape_details_for_urls(urls, pool, semaphore)
                    stats["error_count"] += det_errors
                    details_path = run_dir / config.OUTPUT_DETAILS_RAW
                    details_path.write_bytes(orjson.dumps(details_by_id, option=orjson.OPT_INDENT_2))
                    stats["total_details"] = len(details_by_id)
            else:
                await build_product_queue(products, run_dir)
                urls = [p["url"] for p in products if p.get("url")]
                details_by_id, det_errors = await scrape_details_for_urls(urls, pool, semaphore)
                stats["error_count"] += det_errors
                details_path = run_dir / config.OUTPUT_DETAILS_RAW
                details_path.write_bytes(orjson.dumps(details_by_id, option=orjson.OPT_INDENT_2))
                stats["total_details"] = len(details_by_id)

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
    asyncio.run(main())


if __name__ == "__main__":
    run()
