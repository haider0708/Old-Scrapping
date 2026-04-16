"""
Configuration for Parashop e-commerce scraper.
Full SSR. Platform: OpenCart 3.x + Journal 3 Theme.
Lazy images. Lightgallery data-images JSON for detail images.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://www.parashop.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - Journal 3 j-menu
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "div.desktop-main-menu-wrapper div#main-menu > ul.j-menu",
    "top_items": "ul.j-menu > li.menu-item.main-menu-item.dropdown.mega-menu",
    "top_link": "a.dropdown-toggle",
    "top_name": "a.dropdown-toggle > span.links-text",
    "low_items": "div.dropdown-menu.j-dropdown div.module-item > div.item-content > a.catalog-title",
    "low_link": "a.catalog-title",
    "sub_items": "div.item-assets > div.subitems > div.subitem > a",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"product_id=(\d+)|/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

# -----------------------------------------------------------------------------
# Listing selectors - OpenCart Journal 3
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "div.product-layout.has-extra-button",
    "id_input": "input[type='hidden'][name='product_id']",
    "id_attr": "value",
    "name": "div.caption > div.name > a",
    "url": "div.caption > div.name > a",
    "image": "a.product-img img.img-first",
    "image_attrs": ["src", "data-src", "data-largeimg"],
    "price": "span.price-new",
    "old_price": "span.price-old",
    "discount": "div.product-labels span.product-label.product-label-28 b",
    "description_short": "div.caption > div.description",
    "brand": "div.caption > div.stats span.stat-1 span a",
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "div.row.pagination-results ul.pagination",
    "next_page": "li > a.next",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors - OpenCart, lightgallery data-images
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "div.product-details > div.title.page-title",
    "sku": "li.product-model > span",
    "price": "div.product-price-group div.product-price-new",
    "old_price": "div.product-price-group div.product-price-old",
    "availability_in_stock": "li.product-stock.in-stock > span",
    "availability_out_of_stock": "li.product-stock.out-of-stock > span",
    "brand": "div.brand-image.product-manufacturer a span",
    "description": "div.tabs-container.product_tabs div.tab-pane.active",
    "lightgallery": "div.lightgallery.lightgallery-product-images",
    "lightgallery_attr": "data-images",
    "images_main": "div.swiper.main-image div.swiper-slide img",
    "images_main_attr": "data-largeimg",
}

# -----------------------------------------------------------------------------
# Retry / Delay / Concurrency
# -----------------------------------------------------------------------------
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30
MIN_DELAY = 1.0
MAX_DELAY = 3.0
MAX_CONCURRENT_REQUESTS = 8
PROCESS_POOL_SIZE = 2

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

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]

HEADER_TEMPLATES = [
    {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
]
