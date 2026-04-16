"""
Configuration for Mytek e-commerce scraper.
All selectors and configuration. Platform: Magento 2 (Rootways Megamenu).
Categories: SSR (httpx). Listings and details: CSR (Playwright browser pool).
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://www.mytek.tn"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR listings and details)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 20000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_LISTING_WAIT = "div.product-container[data-product-id]"
PLAYWRIGHT_DETAIL_WAIT = "div.product-info-price"
BROWSER_POOL_SIZE = 4

# -----------------------------------------------------------------------------
# CSS Selectors - Rootways Megamenu (SSR on homepage)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "ul.vertical-list",
    "top_items": "li.rootverticalnav.category-item",
    "top_name": "a span.main-category-name em",
    "children_container": "div.vertical_fullwidthmenu",
    "low_blocks": "div.title_normal",
    "low_link": "a",
    "sub_lists": "ul.level3-popup, ul.level4-popup",
    "sub_items": "li.category-item > a",
    "sub_name": "span.level3-name, span.level4-name",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "category_id_from_pagination": r"[?&]id=(\d+)",
    "id_from_url": r"-(\d+)\.html",
    "slug_sanitize": r"[^a-z0-9\-]",
}

# -----------------------------------------------------------------------------
# Listing selectors - Magento 2 CSR
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "div.product-container",
    "id": None,
    "id_attr": "data-product-id",
    "name": "h1.product-item-name a.product-item-link",
    "url": "a.product-item-link",
    "image": "img[id^='seImgProduct_']",
    "image_attrs": ["src"],
    "price": "span.final-price",
    "old_price": "span.original-price",
    "sku": "div.sku",
    "description_short": "div.search-short-description",
    "brand": "div.brand a img",
    "brand_attr": "src",
    "availability": {
        "container": "div.availability",
        "status": "div.stock",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.custom-pagination",
    "page_list": "ul.pagination li.page-item a.page-link",
    "current_page": "li.page-item.active a.page-link",
    "next_page": "li.page-item:last-child a.page-link",
    "previous_page": "li.page-item:first-child a.page-link",
    "disabled_indicator": "li.page-item.disabled",
    "url_pattern": "?id={cat_id}&p={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.page-title span.base",
    "breadcrumbs": None,
    "sku": "div.product.attribute.sku div.value[itemprop='sku']",
    "price": "div.product-info-price span.price",
    "old_price": "span.old-price span.price",
    "special_price": "span.special-price span.price",
    "discount": "span.discount-price",
    "global_availability": "div.product-info-stock-sku div.stock[itemprop='availability']",
    "availability_per_shop": {
        "container": "#block_synchronizestok #shop_container table.tab_retrait_mag",
        "in_stock_class": "enStock",
        "on_order_class": "erpCommande",
        "incoming_class": "erpArivage",
    },
    "description": "#description",
    "specs": {
        "container": "#product-attribute-specs-table",
        "row": "tr",
        "key": "th.col.label",
        "value": "td.col.data",
    },
    "images": {
        "main": "div.product-cover img, div#gallery-container img",
        "main_attrs": ["src"],
        "thumbnails": "div.product-images img.thumb",
    },
    "installment": {
        "container": "#synchronizestock_block_paiement",
        "table": "._payment_cheque .facilitePaiement",
        "no_interest_flag": ".facilite-text-sans, .Sansinter",
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
MAX_CONCURRENT_REQUESTS = 4
PROCESS_POOL_SIZE = 2

# -----------------------------------------------------------------------------
# httpx tuning (for categories only)
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
