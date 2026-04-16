"""
Configuration for Technopro e-commerce scraper.
All selectors and configuration. Platform: PrestaShop + IQit MegaMenu.
CSR homepage (Playwright for categories), SSR listings/details.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://www.technopro-online.com"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR category extraction)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "nav#cbp-hrmenu ul > li.cbp-hrmenu-tab > a.nav-link"

# -----------------------------------------------------------------------------
# CSS Selectors - IQit MegaMenu (column-based + recursive nested UL)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "nav#cbp-hrmenu > ul",
    "top_items": "nav#cbp-hrmenu > ul > li.cbp-hrmenu-tab",
    "top_link": "a.nav-link",
    "top_name": "span.cbp-tab-title",
    "mega_panel": "div.cbp-hrsub",
    "low_columns": "div.cbp-menu-column",
    "low_title": ".menu-title, p strong a, p strong",
    "low_title_link": "p strong a, .menu-title a",
    "sub_items": "ul li > a",
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
# Listing selectors - PrestaShop IQit theme
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": None,
    "id_attr": "data-id-product",
    "name": "h2.product-title a",
    "url": "h2.product-title a",
    "image": "img.product-thumbnail-first",
    "image_attrs": ["src", "data-src"],
    "price": "span.product-price",
    "price_content_attr": "content",
    "old_price": "span.regular-price",
    "discount": "ul.product-flags li.product-flag.discount",
    "reference": "div.product-reference",
    "brand": "div.product-brand a",
    "description_short": ".product-description-short",
    "availability": {
        "in_stock": ".badge.badge-success.product-available",
        "out_of_stock": ".badge.badge-danger.product-unavailable",
        "orderable_oos": ".badge.product-unavailable-allow-oosp",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "div.pagination-wrapper.pagination-wrapper-bottom nav.pagination",
    "page_list": "ul.page-list a.js-search-link",
    "current_page": "li.current a.disabled",
    "next_page": "a#infinity-url-next",
    "next_page_fallback": "ul.page-list a.next",
    "result_count": "span.showing",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.page-title span",
    "reference": ".product-reference span:nth-of-type(2)",
    "brand": ".product-manufacturer img",
    "brand_attr": "alt",
    "price": ".current-price .product-price",
    "price_content_attr": "content",
    "old_price": ".product-discount .regular-price",
    "discount": ".badge.badge-discount.discount-amount",
    "global_availability": "#product-availability",
    "availability_schema": "link[itemprop='availability'][href]",
    "description": ".product-description .rte-content",
    "description_short": ".product-description-short .rte-content",
    "specs": {
        "container": "section.product-features dl.data-sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "images": {
        "main": ".product-image-large img",
        "main_attrs": ["src"],
        "gallery": "div.product-images-large .swiper-slide img",
        "gallery_attrs": ["src", "data-src"],
    },
    "json_data": "#product-details[data-product]",
    "json_data_attr": "data-product",
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
