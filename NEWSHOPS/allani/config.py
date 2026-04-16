"""
Configuration for Allani e-commerce scraper.
All selectors, URLs, delays, paths, and concurrency limits.
Nothing is hardcoded in scraper.py — everything comes from here.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://allani.com.tn"

# -----------------------------------------------------------------------------
# CSS Selectors (from meta spec)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "top_items": "ul#top-menu[data-depth='0'] > li.category",
    "top_link": "a.dropdown-item[data-depth='0']",
    "low_items": "ul[data-depth='1'] > li.category",
    "low_link": "a.dropdown-item[data-depth='1']",
    "sub_items": "ul[data-depth='2'] > li.category",
    "sub_link": "a.dropdown-item[data-depth='2']",
}

# -----------------------------------------------------------------------------
# URL patterns (regex for extracting IDs)
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "category_id_from_li": r"category-(\d+)",
}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": "data-id-product",  # article[data-id-product]
    "name": ".product-description h3.product-title a",
    "url": ".product-description h3.product-title a",
    "image": ".dd-product-image a.product-thumbnail img",
    "image_attrs": ["data-src", "src"],  # lazy-loaded: data-src first, then src
    "price": ".product-price-and-shipping span.price[itemprop='price']",
    "old_price": None,
    "reference": ".product-reference strong",
    "ean": ".product-ean strong",
    "description_short": ".product-detail[itemprop='description']",
    "promo_flag": "ul.product-flags li.on-sale",
    "availability": {
        "selector": "span#product-availability",
        "fallback": "span.dispo",
    },
}

PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "page_list": "ul.page-list li a.js-search-link",
    "current_page": "ul.page-list li.current a",
    "next_page": "ul.pagination a.next.js-search-link[rel='next']",
    "total_info": "nav.pagination > div:first-child",
    "no_more_pages": "a.next.js-search-link",  # absence = no more pages
    "url_pattern": "?page={n}",
}

DETAIL_SELECTORS = {
    "title": "h1.h1.product[itemprop='name']",
    "breadcrumbs": None,
    "brand": ".product-manufacturer a",
    "reference": ".product-reference span[itemprop='sku']",
    "ean": ".product-ean span[itemprop='sku'] b",
    "price": ".current-price span[itemprop='price']",
    "old_price": None,
    "global_availability": "span#product-availability",
    "availability_per_shop": None,
    "description": "[itemprop='description']",  # inside product-description-short
    "specs": None,
    "images": {
        "main": "img.js-qv-product-cover",
        "main_attrs": ["src"],
        "thumbnails": "img.thumb.js-thumb",
        "thumbnail_attrs": ["data-image-large-src", "src"],
    },
    "schema_availability": "link[itemprop='availability'][href]",
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
