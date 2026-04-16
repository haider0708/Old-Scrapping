"""
Configuration for Zoom e-commerce scraper.
Full SSR. Platform: PrestaShop + ETS Mega Menu.
Lazy-loaded images (data-original). Text-based availability.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://zoom.com.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - ETS Mega Menu (3-level)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "li.mm_menus_li",
    "top_items": "li.mm_tabs_li",
    "top_link": ".mm_tab_toggle_title a",
    "top_name": ".mm_tab_toggle_title a",
    "low_items": ".ets_mm_block .h4 a, .ets_mm_block span.h4 a",
    "low_link": "a",
    "sub_items": ".ets_mm_categories > li > a",
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
# Listing selectors - PrestaShop (lazy image data-original)
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "div.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h5.product-name > a",
    "url": "h5.product-name > a",
    "image": ".product-cover-link img.img-fluid",
    "image_attrs": ["src", "data-original"],
    "price": "span.price.product-price",
    "old_price": "span.regular-price",
    "discount": "span.product-flag.discount",
    "description_short": ".product-description-short",
    "availability": {
        "selector": ".product-availability span",
        "status_from_text": True,
        "in_stock_text": "En stock",
        "out_of_stock_text": "Hors stock",
        "in_commande_text": "Sur Commande",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "page_list": "ul.page-list a.js-search-link",
    "next_page": "a.next.js-search-link",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors - PrestaShop + JSON fallback
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "json_data": "#product-details[data-product]",
    "json_data_attr": "data-product",
    "out_of_stock_notice": "div.product-out-of-stock",
    "json_fields": {
        "id": "id_product",
        "name": "name",
        "price": "price_amount",
        "price_display": "price",
        "old_price": "price_without_reduction",
        "discount": "discount_amount",
        "reference": "reference",
        "quantity": "quantity",
        "available_for_order": "available_for_order",
        "images": "images",
        "features": "features",
    },
    "title": "h1.page-heading",
    "brand": ".attribute-item.product-manufacturer a span",
    "reference": ".attribute-item.product-reference span",
    "price": "span.price.product-price.current-price-value",
    "price_content_attr": "content",
    "old_price": "p.previous-price span.regular-price",
    "discount": "p.previous-price span.discount-amount",
    "global_availability": "#product-availability span",
    "description": "div[id^='product-description-short-']",
    "full_description": "#description",
    "specs": {
        "container": ".product-features dl.data-sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "images": {
        "main": ".product-cover img.js-qv-product-cover",
        "main_attrs": ["src"],
        "thumbnails": ".thumb.js-thumb",
        "thumbnail_attr": "data-zoom-image",
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

HEADER_TEMPLATES = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
]
