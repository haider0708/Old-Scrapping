"""
Configuration for Pharmashop e-commerce scraper.
Full SSR. Platform: PrestaShop 1.7 + Leo Theme / ApMegamenu.
MAX_CONCURRENT_REQUESTS = 1 (single worker as requested).
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://pharma-shop.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - ApMegamenu (3-level)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "nav.leo-megamenu ul.nav.navbar-nav.megamenu.horizontal",
    "top_items": "ul.megamenu.horizontal > li.nav-item.parent.dropdown",
    "top_link": "a.nav-link.dropdown-toggle",
    "top_name": "a.nav-link span.menu-title",
    "low_items": "div.dropdown-menu-inner ul.row > li.col-md-4 > a",
    "low_link": "a",
    "sub_items": "ul.row > li.col-md-4 > ul > li > a",
    "has_children": "a.sf-with-ul",
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
# Listing selectors - PrestaShop Leo
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h2.h3.product-title[itemprop='name'] a",
    "url": "h2.product-title a",
    "image": "a.thumbnail.product-thumbnail img",
    "image_attrs": ["src", "data-src", "data-full-size-image-url"],
    "price": "span.price[aria-label='Prix']",
    "price_schema": "meta[itemprop='price'][content]",
    "old_price": "span.regular-price[aria-label='Prix de base']",
    "discount": "span.discount-percentage.discount-product",
    "brand": "div.text-center.txt-marque a",
    "availability": {
        "out_of_stock_flag": "ul.product-flags > li.product-flag.out_of_stock",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "next_page": "a.next.js-search-link[rel='next']",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors - PrestaShop + JSON
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "json_data": "div.tab-pane#product-details[data-product]",
    "json_data_attr": "data-product",
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
    "title": "h1.h1[itemprop='name']",
    "price": "div.current-price span[itemprop='price']",
    "price_content_attr": "content",
    "old_price": "div.product-discount span.regular-price",
    "discount": "div.product-discount span.discount-percentage",
    "description": "div.product-description[itemprop='description']",
    "brand": "div.product-manufacturer img.manufacturer-logo",
    "brand_attr": "alt",
    "images": {
        "main": "div.product-cover img.js-qv-product-cover",
        "thumbnails": "ul.product-images.js-qv-product-images img.thumb",
    },
}

# -----------------------------------------------------------------------------
# Retry / Delay / Concurrency - 1 WORKER
# -----------------------------------------------------------------------------
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30
MIN_DELAY = 1.0
MAX_DELAY = 3.0
MAX_CONCURRENT_REQUESTS = 1
PROCESS_POOL_SIZE = 2

CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
POOL_MAX_CONNECTIONS = 5
POOL_MAX_KEEPALIVE = 2

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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

HEADER_TEMPLATES = [
    {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
]
