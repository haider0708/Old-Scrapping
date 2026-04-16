"""
Pharmashop e-commerce web scraper.
Fully SSR -- httpx + selectolax. MAX_CONCURRENT_REQUESTS=1 (single worker).
Platform: PrestaShop 1.7 + Leo Theme / ApMegamenu.
"""

from __future__ import annotations

import asyncio
import json
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


async def safe_request(
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
                _logger.warning(
                    "Request failed (attempt %d/%d): %s. Retrying in %.1fs",
                    attempt + 1,
                    config.MAX_RETRIES,
                    e,
                    wait,
                )
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


def _css_first_safe(node: Any, selector: str | None) -> Any:
    if not selector:
        return None
    return node.css_first(selector)


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
    parts = [p for p in url.split("/") if p and p != "content"]
    slug = "-".join(parts).lower() if parts else "unknown"
    pattern = config.URL_PATTERNS.get("slug_sanitize")
    if pattern:
        slug = re.sub(pattern, "", slug)
    return slug or "unknown"


def _extract_id_from_url(url: str) -> str | None:
    if not url:
        return None
    m = re.search(config.URL_PATTERNS.get("id_from_url", r"/(\d+)(?:-|$)"), url)
    return m.group(1) if m else None


def _is_visible(node: Any) -> bool:
    if not node:
        return True
    current = node
    while current:
        style = (current.attributes or {}).get("style") or ""
        style_lower = style.lower().replace(" ", "")
        if "display:none" in style_lower or "visibility:hidden" in style_lower:
            return False
        current = getattr(current, "parent", None)
    return True


# -----------------------------------------------------------------------------
# Categories (httpx, SSR - ApMegamenu 3-level)
# -----------------------------------------------------------------------------


async def scrape_categories(
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> list[dict]:
    html, err = await safe_request(config.BASE_URL, client, semaphore)
    if err or not html:
        _logger.error("Category fetch failed: %s", err)
        return []

    tree = HTMLParser(html)
    categories: list[dict] = []
    seen_urls: set[str] = set()
    cs = config.CATEGORY_SELECTORS
    link_fb = cs.get("link_fallback", "a[href]")

    top_items = tree.css(cs["top_items"])
    for top_idx, top_li in enumerate(top_items):
        if not _is_visible(top_li):
            continue

        top_a = top_li.css_first(cs.get("top_link")) or top_li.css_first(link_fb)
        top_name_el = _css_first_safe(top_li, cs.get("top_name"))
        top_name = parse_node_text(top_name_el) if top_name_el else (parse_node_text(top_a) if top_a else "")
        if not top_name:
            continue

        top_id = f"top_{top_idx}"
        top_url = None
        if top_a:
            top_url = _abs_url(parse_node_attr(top_a, "href"))
            if top_url:
                top_id = _extract_id_from_url(top_url) or _extract_slug_from_url(top_url)
                seen_urls.add(top_url)

        categories.append({
            "id": str(top_id),
            "name": top_name,
            "url": top_url,
            "parent_id": None,
            "level": 0,
        })

        for low_li in top_li.css("div.dropdown-menu-inner ul.row > li.col-md-4"):
            low_a = low_li.css_first("a") or low_li.css_first(link_fb)
            if not low_a:
                continue
            low_url = _abs_url(parse_node_attr(low_a, "href"))
            if not low_url or low_url in seen_urls:
                continue
            seen_urls.add(low_url)
            low_id = _extract_id_from_url(low_url) or _extract_slug_from_url(low_url)
            categories.append({
                "id": str(low_id),
                "name": parse_node_text(low_a),
                "url": low_url,
                "parent_id": str(top_id),
                "level": 1,
            })

            for sub_a in low_li.css(cs.get("sub_items", "ul > li > a")):
                if not sub_a:
                    continue
                sub_url = _abs_url(parse_node_attr(sub_a, "href"))
                if not sub_url or sub_url in seen_urls:
                    continue
                seen_urls.add(sub_url)
                sub_id = _extract_id_from_url(sub_url) or _extract_slug_from_url(sub_url)
                categories.append({
                    "id": str(sub_id),
                    "name": parse_node_text(sub_a),
                    "url": sub_url,
                    "parent_id": str(low_id),
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
# Listing Scraping (httpx, SSR - PrestaShop Leo, out_of_stock only)
# -----------------------------------------------------------------------------


def scrape_listing_page(html: str, category_url: str) -> list[dict]:
    tree = HTMLParser(html)
    ls = config.LISTING_SELECTORS
    elements = tree.css(ls["element"])
    products = []
    av_config = ls.get("availability") or {}

    for elem in elements:
        pid = parse_node_attr(elem, ls["id_attr"]) if elem else ""
        if not pid:
            continue

        name_el = elem.css_first(ls.get("name")) or elem.css_first(ls.get("url"))
        url_el = elem.css_first(ls.get("url"))
        url = _abs_url(parse_node_attr(url_el, "href")) if url_el else ""
        name = parse_node_text(name_el) if name_el else parse_node_text(url_el)

        img_el = elem.css_first(ls["image"])
        img_url = ""
        if img_el:
            for attr in ls.get("image_attrs", ["src"]):
                img_url = parse_node_attr(img_el, attr)
                if img_url:
                    break
        img_url = _abs_url(img_url) if img_url else ""

        price_el = elem.css_first(ls["price"])
        price = parse_node_text(price_el)
        price_numeric = price
        if ls.get("price_schema"):
            meta = elem.css_first("meta[itemprop='price']")
            if meta:
                price_numeric = parse_node_attr(meta, "content") or price

        old_price_el = _css_first_safe(elem, ls.get("old_price"))
        old_price = parse_node_text(old_price_el) if old_price_el else ""

        discount_el = _css_first_safe(elem, ls.get("discount"))
        discount = parse_node_text(discount_el) if discount_el else ""

        brand_el = _css_first_safe(elem, ls.get("brand"))
        brand = parse_node_text(brand_el) if brand_el else ""

        availability = ""
        if _css_first_safe(elem, av_config.get("out_of_stock_flag")):
            availability = "Rupture"

        products.append({
            "id": pid,
            "name": name,
            "url": url,
            "category_url": category_url,
            "image": img_url,
            "price": price,
            "price_numeric": price_numeric,
            "old_price": old_price,
            "discount": discount,
            "reference": "",
            "brand": brand,
            "description_short": "",
            "availability": availability,
        })
    return products


def _get_next_page_url(html: str) -> str | None:
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
            url = _get_next_page_url(html)
        await queue.move_to_done(key)
    except Exception as e:
        _logger.exception("Category %s failed: %s", key, e)
        await queue.move_to_error(key, str(e))
    return all_products


async def scrape_all_listings(
    categories: list[dict],
    run_dir: Path,
) -> tuple[list[dict], int]:
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
# Detail Scraping (httpx, SSR - JSON-primary + CSS fallback)
# -----------------------------------------------------------------------------


def _extract_images_from_json(images_data: Any) -> list[str]:
    urls: list[str] = []
    if not images_data:
        return urls
    if isinstance(images_data, list):
        for img in images_data:
            if isinstance(img, dict):
                for key in ("large", "bySize", "medium", "small"):
                    if key in img and isinstance(img[key], dict) and "url" in img[key]:
                        u = img[key]["url"]
                        if u and u not in urls:
                            urls.append(_abs_url(u))
                if "url" in img and isinstance(img.get("url"), str):
                    u = img["url"]
                    if u and u not in urls:
                        urls.append(_abs_url(u))
    elif isinstance(images_data, dict):
        for key in ("large", "bySize", "medium", "small"):
            if key in images_data and isinstance(images_data[key], dict) and "url" in images_data[key]:
                u = images_data[key]["url"]
                if u and u not in urls:
                    urls.append(_abs_url(u))
        if "url" in images_data and isinstance(images_data.get("url"), str):
            u = images_data["url"]
            if u and u not in urls:
                urls.append(_abs_url(u))
    return urls


def _extract_features_from_json(features_data: Any) -> dict[str, str]:
    specs: dict[str, str] = {}
    if not features_data or not isinstance(features_data, list):
        return specs
    for f in features_data:
        if isinstance(f, dict):
            name = f.get("name") or f.get("label") or ""
            value = f.get("value") or f.get("public_value") or ""
            if name and value:
                specs[str(name).strip()] = str(value).strip()
    return specs


def scrape_product_detail(html: str, url: str) -> dict:
    tree = HTMLParser(html)
    sel = config.DETAIL_SELECTORS

    pid = _extract_id_from_url(url) or ""
    title = ""
    price = ""
    price_numeric = ""
    old_price = ""
    discount = ""
    sku = ""
    availability = ""
    images_list: list[str] = []
    specs_dict: dict[str, str] = {}

    json_el = _css_first_safe(tree, sel.get("json_data"))
    if json_el:
        json_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
        if json_str:
            try:
                json_data = json.loads(json_str.replace("&quot;", '"'))
                jf = sel.get("json_fields", {})
                if not pid and json_data.get(jf.get("id", "id_product")):
                    pid = str(json_data.get(jf.get("id", "id_product")))

                title = json_data.get(jf.get("name", "name"), "") or title
                price = json_data.get(jf.get("price_display", "price"), "") or str(json_data.get(jf.get("price", "price_amount"), ""))
                price_numeric = str(json_data.get(jf.get("price", "price_amount"), "")) or price
                old_price = str(json_data.get(jf.get("old_price", "price_without_reduction"), "")) or old_price
                disc_val = json_data.get(jf.get("discount", "discount_amount"))
                if disc_val is not None:
                    discount = str(disc_val)
                sku = str(json_data.get(jf.get("reference", "reference"), "")) or sku

                qty = json_data.get(jf.get("quantity", "quantity"))
                avail_order = json_data.get(jf.get("available_for_order", "available_for_order"))
                if avail_order is False or (isinstance(qty, (int, float)) and qty <= 0):
                    availability = "Rupture"
                elif avail_order is True or (isinstance(qty, (int, float)) and qty > 0):
                    availability = "En stock"

                imgs_raw = json_data.get(jf.get("images", "images"))
                images_list = _extract_images_from_json(imgs_raw)

                feats_raw = json_data.get(jf.get("features", "features"))
                specs_dict = _extract_features_from_json(feats_raw)
            except json.JSONDecodeError:
                pass

    if not title:
        title_el = _css_first_safe(tree, sel.get("title"))
        title = parse_node_text(title_el) if title_el else ""
    if not price:
        price_el = _css_first_safe(tree, sel.get("price"))
        price = parse_node_attr(price_el, sel.get("price_content_attr", "content")) if price_el else ""
        price_numeric = price_numeric or price
    if not old_price:
        old_el = _css_first_safe(tree, sel.get("old_price"))
        old_price = parse_node_text(old_el) if old_el else ""
    if not discount:
        disc_el = _css_first_safe(tree, sel.get("discount"))
        discount = parse_node_text(disc_el) if disc_el else ""

    desc_el = _css_first_safe(tree, sel.get("description"))
    description = parse_node_text(desc_el) if desc_el else ""

    brand_el = _css_first_safe(tree, sel.get("brand"))
    brand = ""
    if brand_el:
        brand = parse_node_attr(brand_el, sel.get("brand_attr", "alt")) or parse_node_text(brand_el)

    if not images_list:
        for img in tree.css(sel.get("images", {}).get("thumbnails", "img.thumb") or "img.thumb"):
            u = parse_node_attr(img, "src") or parse_node_attr(img, "data-src")
            if u and u not in images_list:
                images_list.append(_abs_url(u))
        if not images_list:
            main_el = _css_first_safe(tree, sel.get("images", {}).get("main"))
            if main_el:
                u = parse_node_attr(main_el, "src")
                if u:
                    images_list.append(_abs_url(u))

    image_main = images_list[0] if images_list else ""
    if not pid:
        pid = sku or ""

    return {
        "id": pid,
        "url": url,
        "title": title,
        "brand": brand or None,
        "reference": sku,
        "sku": sku,
        "price": price,
        "price_numeric": price_numeric,
        "old_price": old_price,
        "discount": discount or None,
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
    client = create_client()
    details: dict[str, dict] = {}
    errors = 0

    async def _fetch(url: str) -> dict | None:
        nonlocal errors
        html, err = await safe_request(url, client, semaphore)
        if err or not html:
            errors += 1
            return None
        return scrape_product_detail(html, url)

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
# Incremental Diffing
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

        _logger.info("Scraping categories...")
        categories = await scrape_categories(client, semaphore)
        await client.aclose()
        leaf_categories = get_leaf_categories(categories)
        cat_path = run_dir / config.OUTPUT_CATEGORIES
        cat_path.write_bytes(orjson.dumps(categories, option=orjson.OPT_INDENT_2))
        _logger.info("Categories: %d total, %d leaf", len(categories), len(leaf_categories))

        _logger.info("Scraping listings...")
        products, list_errors = await scrape_all_listings(leaf_categories, run_dir)
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
