"""
Configuration for Spacenet e-commerce scraper.
All selectors and configuration. Platform: PrestaShop + SP Mega Menu.
Fully SSR -- httpx + selectolax for all phases. No Playwright.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://spacenet.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - SP Mega Menu (3-level)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "#sp-vermegamenu ul.level-1",
    "top_items": "#sp-vermegamenu ul.level-1 > li.item-1",
    "top_link": "a",
    "top_name": "a > span.sp_megamenu_title",
    "low_items": "div.dropdown-menu ul.level-2 > li.item-2",
    "low_link": "a",
    "sub_items": "ul.level-3 > li.item-3 > a",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

# -----------------------------------------------------------------------------
# Listing selectors - PrestaShop SP theme (Spacenet variant)
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "div.field-product-item.item-inner.product-miniature.js-product-miniature",
    "id": None,
    "id_attr": "data-id-product",
    "name": "h2.product_name a",
    "url": "h2.product_name a",
    "image": "img.img-responsive.product_image",
    "image_attrs": ["src"],
    "price": ".product-price-and-shipping .price",
    "old_price": ".product-price-and-shipping .regular-price",
    "reference": ".product-reference span:nth-child(2)",
    "brand": "img.manufacturer-logo",
    "brand_attr": "alt",
    "availability": {
        "in_stock": ".product-quantities label.label",
        "in_arrivage": ".product-quantities label.label-available",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "page_list": "ul.page-list a.js-search-link",
    "current_page": "ul.page-list li.current a.disabled",
    "next_page": "ul.page-list a.next",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.h1",
    "reference": ".product-Details .product-reference span",
    "brand": ".product-Details .product-manufacturer a img",
    "brand_attr": "alt",
    "brand_link": ".product-Details .product-manufacturer a",
    "brand_link_attr": "href",
    "price": ".current-price > span",
    "price_content_attr": "content",
    "old_price": ".product-discount .regular-price",
    "description": "div.product-des",
    "description_fallback": "div[id^='product-description-short-']",
    "global_availability": ".product-quantities .label",
    "stock_quantity": ".product-quantities span[data-stock]",
    "stock_quantity_attr": "data-stock",
    "availability_schema": "link[itemprop='availability'][href]",
    "availability_per_shop": {
        "container": ".social-sharing-magasin .magasin-table",
        "row": ".table-bloc.row",
        "shop_name": ".left-side span",
        "shop_address": ".left-side p",
        "shop_status": ".right-side span",
        "shop_note": ".right-side p",
        "available_icon": ".right-side i.fa-check",
        "unavailable_icon": ".right-side i.fa-times",
    },
    "specs": {
        "container": "section.product-features dl.data-sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "images": {
        "main": "img.js-qv-product-cover",
        "main_attrs": ["src"],
        "thumbnails": "img.thumb.js-thumb",
        "thumbnail_attr": "data-image-large-src",
    },
    "json_data": "#product-details[data-product]",
    "json_data_attr": "data-product",
    "installment": {
        "container": ".social-sharing-payement .payement-table",
        "term": "li.f-date",
        "amount": "li.f-price",
    },
}

# -----------------------------------------------------------------------------
# Retry settings
# -----------------------------------------------------------------------------
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30

# -----------------------------------------------------------------------------
# Delay settings
# -----------------------------------------------------------------------------
MIN_DELAY = 1.0
MAX_DELAY = 3.0

# -----------------------------------------------------------------------------
# Concurrency limits
# -----------------------------------------------------------------------------
MAX_CONCURRENT_REQUESTS = 8
PROCESS_POOL_SIZE = 2

# -----------------------------------------------------------------------------
# httpx tuning
# -----------------------------------------------------------------------------
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
POOL_MAX_CONNECTIONS = 20
POOL_MAX_KEEPALIVE = 5

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
PRODUCT_HISTORY_FILE = DATA_DIR / "product_history.json"
QUEUE_CATEGORY_FILENAME = "category_queue.txt"
QUEUE_PRODUCT_FILENAME = "product_queue.txt"

OUTPUT_CATEGORIES = "categories.json"
OUTPUT_PRODUCTS_RAW = "products_raw.json"
OUTPUT_DETAILS_RAW = "details_raw.json"
OUTPUT_SUMMARY = "summary.json"

# -----------------------------------------------------------------------------
# User-Agent rotation
# -----------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# -----------------------------------------------------------------------------
# Header fingerprint templates
# -----------------------------------------------------------------------------
HEADER_TEMPLATES = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
]
