"""
Configuration for Batam e-commerce scraper.
All selectors, URLs, delays, paths, and concurrency limits.
Nothing is hardcoded in scraper.py — everything comes from here.
Platform: Magento 2 (Hyva + Alpine.js + Tailwind)
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://batam.com.tn"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR category extraction)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 15000  # ms to wait for Alpine.js hydration
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "ul.level-0 > li.parent-ul-list"

# -----------------------------------------------------------------------------
# CSS Selectors (from meta spec)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "top_block": "ul.level-0 > li.parent-ul-list",
    "top_name": "span.text-left",
    "low_block": "ul.level-1 > li",
    "low_name": "ul.level-1 > li a, ul.level-1 > li button",
    "low_link": "ul.level-1 > li a",
    "sub_block": "ul.level-2 > li",
    "sub_name": "ul.level-2 > li a",
    "sub_link": "ul.level-2 > li a",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns (regex for extracting IDs)
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"-(\d+)\.html",
    "slug_sanitize": r"[^a-z0-9\-]",
}

LISTING_SELECTORS = {
    "element": "form.item.product.product-item.product_addtocart_form",
    "id": "input[name='product']",
    "id_attr": "value",
    "name": "a.product-item-link",
    "url": "a.product-item-link",
    "image": "a.product.photo.product-item-photo img.product-image-photo",
    "image_attrs": ["src"],
    "price": "span[data-price-type='finalPrice'] span.price",
    "price_numeric": "span[data-price-type='finalPrice'][data-price-amount]",
    "price_numeric_attr": "data-price-amount",
    "old_price": "span[data-price-type='oldPrice'] span.price",
    "old_price_numeric": "span[data-price-type='oldPrice'][data-price-amount]",
    "availability": {
        "selector": "span.text-green-500, span.text-blue",
    },
}

PAGINATION_SELECTORS = {
    "container": "div.toolbar.toolbar-products",
    "page_list": "ol.pages-items a.page",
    "current_page": "ol.pages-items a.page.active[aria-current='page']",
    "next_page": "li.pages-item-next a.action.next",
    "previous_page": "li.pages-item-previous a.previous",
    "total_info": "p.toolbar-amount#toolbar-amount",
    "per_page_selector": "select[data-role='limiter'].limiter-options",
    "no_more_pages": "li.pages-item-next",
    "url_pattern": "?p={n}",
}

DETAIL_SELECTORS = {
    "title": "h1.page-title span.base[itemprop='name']",
    "breadcrumbs": None,
    "brand": None,
    "reference": "input[name='product']",
    "reference_attr": "value",
    "price": "div.price-container .final-price .price",
    "price_numeric": "meta[itemprop='price']",
    "price_numeric_attr": "content",
    "old_price": "div.price-container .old-price .price",
    "global_availability": "p.unavailable.stock span",
    "availability_in_stock_text": "En stock",
    "availability_fallback_scope": "body",
    "availability_per_shop": None,
    "description": "div.product-description",
    "specs": {
        "container": "#product-attribute-specs-table, table.additional-attributes",
        "row": "tr",
        "key": "th.col.label, td.col.label",
        "value": "td.col.data",
    },
    "images": {
        "main": "div#gallery img",
        "main_attrs": ["src"],
        "thumbnails": None,
    },
}

# -----------------------------------------------------------------------------
# Retry settings
# -----------------------------------------------------------------------------
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30

# -----------------------------------------------------------------------------
# Delay settings (seconds between requests)
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
# Paths (relative to project root)
# -----------------------------------------------------------------------------
SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
PRODUCT_HISTORY_FILE = DATA_DIR / "product_history.json"

# Queue files live in run directory; paths are built at runtime
QUEUE_CATEGORY_FILENAME = "category_queue.txt"
QUEUE_PRODUCT_FILENAME = "product_queue.txt"

# Output filenames per run
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
# Header fingerprint templates (keys that vary; values randomized at runtime)
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
