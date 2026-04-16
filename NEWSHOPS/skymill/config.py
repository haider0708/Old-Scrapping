"""
Configuration for Skymill Informatique e-commerce scraper.
All selectors and configuration. Platform: PrestaShop + SP Mega Menu.
CSR homepage (Playwright for categories), SSR listings/details.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://skymil-informatique.com"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR category extraction)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 30000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "div#spverticalmenu_1 ul.level-1 > li.item-1 > a"

# -----------------------------------------------------------------------------
# CSS Selectors - SP Mega Menu (simple 2-level)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "div#spverticalmenu_1 ul.level-1",
    "top_items": "ul.level-1 > li.item-1",
    "top_link": "a",
    "low_items": "div.dropdown-menu ul.level-2 > li.item-2 > a",
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
# Listing selectors - PrestaShop SP theme
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature.sp-product-style1",
    "id": None,
    "id_attr": "data-id-product",
    "name": "h2.h3.product-title a",
    "url": "h2.h3.product-title a",
    "image": ".product-image img[itemprop='image']",
    "image_attrs": ["src"],
    "price": "span.price[aria-label='Prix']",
    "price_meta": "meta[itemprop='price']",
    "price_meta_attr": "content",
    "old_price": "span.regular-price[aria-label='Prix de base']",
    "discount": "span.discount-amount.discount-product",
    "description_short": ".product-description-short[itemprop='description']",
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "div#js-product-list-bottom nav.pagination",
    "result_count": "div.catproductcounter",
    "page_list": "ul.page-list a.js-search-link",
    "current_page": "li.current a.disabled",
    "next_page": "a.next.js-search-link",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.product-name[itemprop='name']",
    "breadcrumbs": None,
    "brand": "img.manufacturer-logo",
    "brand_attr": "src",
    "brand_link": "a:has(img.manufacturer-logo)",
    "brand_link_attr": "href",
    "reference": ".product-reference span[itemprop='sku']",
    "price": ".product-price span[itemprop='price']",
    "price_content_attr": "content",
    "old_price": ".regular-price",
    "global_availability": "span#product-availability",
    "availability_schema": "link[itemprop='availability'][href]",
    "delivery_info": "span.delivery-information",
    "description": ".product-short-description",
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
