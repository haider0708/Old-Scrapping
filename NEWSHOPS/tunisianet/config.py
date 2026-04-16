"""
Configuration for Tunisianet e-commerce scraper.
All selectors and configuration. Platform: PrestaShop + WB MegaMenu.
Fully SSR -- httpx + selectolax for all phases. No Playwright.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://www.tunisianet.com.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - WB Mega Menu (3-level, label-only top)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "div#_desktop_top_menu div.wb-menu-vertical ul.menu-content.top-menu",
    "top_items": "ul.menu-content.top-menu > li.level-1",
    "top_name": "div.icon-drop-mobile > span",
    "top_link": None,  # label-only, no URL on top categories
    "low_items": "li.menu-item.item-header",
    "low_link": "a",
    "sub_items": "li.menu-item.item-line > a",
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
# Listing selectors - PrestaShop WB theme
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": None,
    "id_attr": "data-id-product",
    "name": "h2.product-title a",
    "url": "h2.product-title a",
    "image": "a.thumbnail.product-thumbnail img.center-block",
    "image_attrs": ["src", "data-full-size-image-url"],
    "price": "span.price[itemprop='price']",
    "old_price": "span.regular-price",
    "discount": "span.discount-amount.discount-product",
    "reference": "span.product-reference",
    "brand": "div.product-manufacturer img.manufacturer-logo",
    "brand_attr": "alt",
    "description_short": "div.listds a",
    "description_short_fallback": "div[id^='product-description-short-']",
    "availability": {
        "in_stock": "#stock_availability span.in-stock",
    },
    "store_availability": {
        "in_stock_store": "div.store-availability-list.stock",
        "out_of_stock_store": "div.store-availability-list.hstock",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "page_list": "ul.page-list a.js-search-link",
    "current_page": "li.current a.disabled.js-search-link",
    "next_page": "a.next.js-search-link",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors - JSON-primary model
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "json_data": "#product-details[data-product]",
    "json_data_attr": "data-product",
    "json_fields": {
        "id": "id_product",
        "name": "name",
        "price": "price_amount",
        "price_display": "price",
        "old_price": "price_without_reduction",
        "discount": "discount_amount",
        "reference": "reference",
        "url": "link",
        "quantity": "quantity",
        "available_for_order": "available_for_order",
        "images": "images",
        "features": "features",
    },
    "out_of_stock_notice": "div.product-out-of-stock",
    "description": "div#description div.product-d",
    "specs": {
        "container": "dl.data-sheet",
        "key": "dt.name",
        "value": "dd.value",
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
