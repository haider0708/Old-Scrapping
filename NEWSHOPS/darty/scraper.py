"""
Darty e-commerce web scraper.
PrestaShop + GloboMegaMenu. All selectors from config.
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
from selectolax.parser import HTMLParser

_shop_dir = Path(__file__).resolve().parent
if str(_shop_dir) not in sys.path:
    sys.path.insert(0, str(_shop_dir))
import config

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


def create_client() -> httpx.AsyncClient:
    headers = dict(random.choice(config.HEADER_TEMPLATES))
    headers["User-Agent"] = random.choice(config.USER_AGENTS)
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
                _logger.warning("Request failed (attempt %d/%d): %s. Retrying in %.1fs", attempt + 1, config.MAX_RETRIES, e, wait)
                await asyncio.sleep(wait)
        return None, last_error


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


def _extract_id_from_url(url: str) -> str | None:
    if not url:
        return None
    pattern = config.URL_PATTERNS.get("id_from_url")
    if not pattern:
        return None
    m = re.search(pattern, url)
    return m.group(1) if m else None


async def scrape_categories(client: httpx.AsyncClient, semaphore: asyncio.Semaphore) -> list[dict]:
    html, err = await safe_request(config.BASE_URL, client, semaphore)
    if err or not html:
        _logger.error("Failed to fetch categories: %s", err)
        return []

    tree = HTMLParser(html)
    categories: list[dict] = []
    seen_urls: set[str] = set()
    cs = config.CATEGORY_SELECTORS

    nav_items = tree.css(cs["nav_container"])
    for nav_li in nav_items:
        top_tabs = nav_li.css(cs["top_items"])
        first_top_id = None
        for top_li in top_tabs:
            top_a = top_li.css_first(cs["top_link"])
            if not top_a:
                continue
            top_id_attr = cs.get("top_id_attr")
            top_id = parse_node_attr(top_li, top_id_attr) if top_id_attr else None
            if not top_id:
                top_id = _extract_id_from_url(parse_node_attr(top_a, "href"))
            if not top_id:
                continue
            if first_top_id is None:
                first_top_id = top_id
            top_url = _abs_url(parse_node_attr(top_a, "href"))
            top_name_sel = cs.get("top_name")
            top_name = parse_node_text(top_li.css_first(top_name_sel)) if top_name_sel else parse_node_text(top_a)
            if top_url in seen_urls:
                continue
            seen_urls.add(top_url)
            categories.append({"id": top_id, "name": top_name, "url": top_url, "parent_id": None, "level": 0})

        low_headers = nav_li.css(cs["low_items"])
        for low_li in low_headers:
            low_a = low_li.css_first(cs["low_link"])
            if not low_a:
                continue
            low_url = _abs_url(parse_node_attr(low_a, "href"))
            low_id = _extract_id_from_url(low_url)
            if not low_id or low_url in seen_urls:
                continue
            seen_urls.add(low_url)
            categories.append({
                "id": low_id,
                "name": parse_node_text(low_a),
                "url": low_url,
                "parent_id": first_top_id,
                "level": 1,
            })

            sub_items = low_li.css(cs["sub_items"])
            for sub_li in sub_items:
                sub_a = sub_li.css_first(cs["sub_link"])
                if not sub_a:
                    continue
                sub_url = _abs_url(parse_node_attr(sub_a, "href"))
                sub_id = _extract_id_from_url(sub_url)
                if not sub_id or sub_url in seen_urls:
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
    parent_ids = {c["parent_id"] for c in categories if c.get("parent_id")}
    return [c for c in categories if c.get("url") and c["id"] not in parent_ids]


class QueueFile:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = asyncio.Lock()
        self._pending: dict[str, str] = {}
        self._done: list[str] = []
        self._errors: list[tuple[str, str]] = []

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
        q._pending[f"cat_{cat['id']}"] = cat["url"]
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


def scrape_listing_page(html: str, category_url: str) -> list[dict]:
    tree = HTMLParser(html)
    ls = config.LISTING_SELECTORS
    articles = tree.css(ls["element"])
    products = []
    for art in articles:
        pid = parse_node_attr(art, ls["id"])
        if not pid:
            pid = _extract_id_from_url(parse_node_attr(art.css_first(ls["url"]), "href") if art.css_first(ls["url"]) else "")
        if not pid:
            continue
        name_el = art.css_first(ls["name"])
        url = _abs_url(parse_node_attr(name_el, "href") if name_el else "")
        name = parse_node_text(name_el)

        img_el = art.css_first(ls["image"])
        img_url = ""
        if img_el:
            for attr in ls.get("image_attrs", ["src"]):
                img_url = parse_node_attr(img_el, attr)
                if img_url:
                    break
        img_url = _abs_url(img_url) if img_url else ""

        price_el = art.css_first(ls["price"])
        price = parse_node_text(price_el)
        if not price and ls.get("price_attr"):
            price = parse_node_attr(price_el, ls["price_attr"])
        price_display_el = art.css_first(ls.get("price_display"))
        price_display = parse_node_text(price_display_el) if price_display_el else ""

        av = ls.get("availability", {})
        availability = ""
        schema_el = art.css_first(av.get("schema"))
        if schema_el:
            availability = parse_node_attr(schema_el, "href")
        cart_el = art.css_first(av.get("cart_button_status"))
        if cart_el:
            status = parse_node_attr(cart_el, "data-status")
            if status:
                availability = availability or status

        category_el = art.css_first(ls.get("category"))
        category = parse_node_text(category_el) if category_el else ""

        features_els = art.css(ls.get("features", ""))
        features = [parse_node_text(f) for f in features_els] if features_els else []

        products.append({
            "id": pid,
            "name": name,
            "url": url,
            "category_url": category_url,
            "image": img_url,
            "price": price or price_display,
            "price_display": price_display,
            "category": category,
            "features": features,
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
    run_dir: Path,
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
    tasks = [scrape_category_listings(cat, queue, client, semaphore, run_dir) for cat in categories]
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
    (run_dir / config.OUTPUT_PRODUCTS_RAW).write_bytes(orjson.dumps(products_list, option=orjson.OPT_INDENT_2))
    await queue.save()
    return products_list, queue.error_count


def scrape_product_detail(html: str, url: str) -> dict:
    tree = HTMLParser(html)
    sel = config.DETAIL_SELECTORS

    def _text(css: str | None) -> str:
        if not css:
            return ""
        n = tree.css_first(css)
        return parse_node_text(n)

    title = _text(sel["title"])
    title_parts = sel.get("title_parts")
    category_part = ""
    name_part = ""
    if title_parts:
        category_part = _text(title_parts.get("category"))
        name_part = _text(title_parts.get("name"))

    brand_conf = sel.get("brand")
    brand = ""
    if isinstance(brand_conf, dict):
        brand_cont = tree.css_first(brand_conf.get("container"))
        brand = parse_node_text(brand_cont) if brand_cont else ""
    else:
        brand = _text(brand_conf)

    price = _text(sel["price"])
    old_price = _text(sel.get("old_price"))
    savings = _text(sel.get("savings"))
    promo_flag_el = tree.css_first(sel.get("promo_flag"))
    promo_flag = bool(promo_flag_el)

    avail_el = tree.css_first(sel.get("global_availability"))
    availability = parse_node_attr(avail_el, "href") if avail_el else ""

    avail_per_shop = sel.get("availability_per_shop")
    availability_per_shop = []
    if avail_per_shop:
        container = tree.css_first(avail_per_shop.get("container"))
        if container:
            for row in container.css(avail_per_shop.get("row", "")):
                name_el = row.css_first(avail_per_shop.get("name"))
                status_el = row.css_first(avail_per_shop.get("status"))
                availability_per_shop.append({
                    "name": parse_node_text(name_el),
                    "status": parse_node_text(status_el),
                })

    imgs_conf = sel.get("images", {})
    main_imgs = tree.css(imgs_conf.get("main", ""))
    image_main = ""
    images_list: list[str] = []
    main_attrs = imgs_conf.get("main_attrs", ["src"])
    zoom_attr = imgs_conf.get("zoom_attr", "data-image-zoom-src")
    for img in main_imgs:
        src = ""
        for attr in main_attrs:
            src = parse_node_attr(img, attr)
            if src:
                break
        if src:
            full = _abs_url(src)
            images_list.append(full)
            if not image_main:
                image_main = full

    features_els = tree.css(sel.get("features_short", ""))
    features_short = [parse_node_text(f) for f in features_els] if features_els else []

    specs_dict: dict[str, str] = {}
    specs_conf = sel.get("specs")
    if specs_conf:
        container = tree.css_first(specs_conf.get("container"))
        if container:
            for row in container.css(specs_conf.get("row", "")):
                key_el = row.css_first(specs_conf.get("key"))
                val_el = row.css_first(specs_conf.get("value"))
                if key_el and val_el:
                    specs_dict[parse_node_text(key_el)] = parse_node_text(val_el)

    installment_conf = sel.get("installment")
    monthly_price = ""
    if installment_conf:
        cont = tree.css_first(installment_conf.get("container"))
        if cont:
            mp_el = cont.css_first(installment_conf.get("monthly_price"))
            monthly_price = parse_node_text(mp_el) if mp_el else ""

    schema_el = tree.css_first(sel.get("schema_availability"))
    schema_availability = parse_node_attr(schema_el, "href") if schema_el else ""

    pid = _extract_id_from_url(url) or ""

    return {
        "id": pid,
        "url": url,
        "title": title or name_part,
        "title_category": category_part,
        "title_name": name_part,
        "brand": brand,
        "price": price,
        "old_price": old_price,
        "savings": savings,
        "promo_flag": promo_flag,
        "availability": availability,
        "availability_per_shop": availability_per_shop,
        "image_main": image_main,
        "images": images_list,
        "features_short": features_short,
        "specs": specs_dict,
        "installment_monthly_price": monthly_price,
        "schema_availability": schema_availability,
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

    tasks = [_fetch(u) for u in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    await client.aclose()
    for r in results:
        if isinstance(r, Exception):
            errors += 1
            continue
        if r and r.get("id"):
            details[str(r["id"])] = r
    return details, errors


def _diff_products_impl(current_list: list[dict], previous_list: list[dict]) -> dict[str, Any]:
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
        if (curr.get("price") or "").strip() != (prev.get("price") or "").strip() or (curr.get("availability") or "").strip() != (prev.get("availability") or "").strip():
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


async def diff_products(current_listings: list[dict], previous_listings: list[dict]) -> dict[str, Any]:
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


def update_product_history(current_data: dict[str, dict], run_timestamp: str) -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = config.PRODUCT_HISTORY_FILE
    if path.exists():
        history = orjson.loads(path.read_bytes())
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
        if prod.get("price") != last_price:
            h["price_history"].append({"value": prod.get("price"), "recorded_at": run_timestamp})
        if prod.get("availability") != last_av:
            h["availability_history"].append({"value": prod.get("availability"), "recorded_at": run_timestamp})
    path.write_bytes(orjson.dumps(history, option=orjson.OPT_INDENT_2))


def write_summary(run_dir: Path, stats: dict) -> None:
    (run_dir / config.OUTPUT_SUMMARY).write_bytes(orjson.dumps(stats, option=orjson.OPT_INDENT_2))


def cleanup_queues(run_dir: Path) -> None:
    for fname in (config.QUEUE_CATEGORY_FILENAME, config.QUEUE_PRODUCT_FILENAME):
        p = run_dir / fname
        if p.exists():
            p.unlink()


async def main() -> None:
    start = time.perf_counter()
    run_dir = setup_run_directory()
    setup_logging(run_dir)
    _logger.info("Run directory: %s", run_dir)
    stats = {"total_products": 0, "total_details": 0, "error_count": 0, "duration_seconds": 0, "timestamp": datetime.now().isoformat(), "no_changes": False}
    try:
        client = create_client()
        semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_REQUESTS)
        _logger.info("Scraping categories...")
        categories = await scrape_categories(client, semaphore)
        leaf_categories = get_leaf_categories(categories)
        (run_dir / config.OUTPUT_CATEGORIES).write_bytes(orjson.dumps(categories, option=orjson.OPT_INDENT_2))
        _logger.info("Categories: %d total, %d leaf", len(categories), len(leaf_categories))
        _logger.info("Scraping listings...")
        products, list_errors = await scrape_all_listings(leaf_categories, run_dir)
        stats["total_products"] = len(products)
        stats["error_count"] = list_errors
        _logger.info("Products: %d (errors: %d)", len(products), list_errors)
        await client.aclose()

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
                    (run_dir / config.OUTPUT_DETAILS_RAW).write_bytes(orjson.dumps(patched, option=orjson.OPT_INDENT_2))
                    stats["total_details"] = len(patched)
            else:
                await build_product_queue(products, run_dir)
                urls = [p["url"] for p in products if p.get("url")]
                details_by_id, det_errors = await scrape_details_for_urls(urls, semaphore)
                stats["error_count"] += det_errors
                (run_dir / config.OUTPUT_DETAILS_RAW).write_bytes(orjson.dumps(details_by_id, option=orjson.OPT_INDENT_2))
                stats["total_details"] = len(details_by_id)
        else:
            await build_product_queue(products, run_dir)
            urls = [p["url"] for p in products if p.get("url")]
            details_by_id, det_errors = await scrape_details_for_urls(urls, semaphore)
            stats["error_count"] += det_errors
            (run_dir / config.OUTPUT_DETAILS_RAW).write_bytes(orjson.dumps(details_by_id, option=orjson.OPT_INDENT_2))
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
