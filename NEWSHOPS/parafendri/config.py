"""
Configuration for Parafendri e-commerce scraper.
Full SSR. Platform: PrestaShop + PosThemes MegaMenu.
Dual dropdown (mega + simple). Lazy images (data-src). JSON detail.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://parafendri.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - PosThemes MegaMenu (dual dropdown)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "div#_desktop_megamenu div.pos-menu-horizontal > ul.menu-content",
    "top_items": "ul.menu-content > li.menu-item",
    "top_link": "a",
    "top_name": "a > span",
    "mega_low": "div.pos-sub-menu.menu-dropdown div.pos-menu-col > ul.ul-column > li.submenu-item > a",
    "simple_low": "div.menu-dropdown.cat-drop-menu > ul.pos-sub-inner > li > a",
    "sub_items": "li.submenu-item > ul.category-sub-menu > li > a",
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
# Listing selectors - PrestaShop (lazy image data-src)
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h3[itemprop='name'] > a.product_name",
    "url": "h3[itemprop='name'] > a.product_name",
    "image": "a.thumbnail.product-thumbnail > img",
    "image_attrs": ["src", "data-src", "data-full-size-image-url"],
    "price": "span[itemprop='price'].price",
    "old_price": "span.regular-price",
    "discount": "span.discount-amount.discount-product",
    "description_short": "div.product-desc[itemprop='description']",
    "availability": {
        "in_stock": "div.availability-list.in-stock > span",
        "out_of_stock": "div.availability-list.out-of-stock > span",
        "out_of_stock_flag": "ul.product-flag > li.out_of_stock > span",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "page_list": "ul.page-list li a.js-search-link",
    "next_page": "a.next.js-search-link[rel='next']",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors - PrestaShop + JSON
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
        "quantity": "quantity",
        "available_for_order": "available_for_order",
        "images": "images",
        "features": "features",
    },
    "out_of_stock_notice": "div.product-out-of-stock",
    "title": "h1.h1.namne_details[itemprop='name']",
    "sku": "p.reference > span",
    "price": "div.current-price > span[itemprop='price']",
    "price_content_attr": "content",
    "old_price": "div.product-discount > span.regular-price",
    "discount": "span.discount.discount-amount",
    "description": "div#description div.product-description",
    "specs": None,
    "brand": "div.product-manufacturer img.manufacturer-logo",
    "brand_attr": "alt",
    "images": {
        "main": "div.product-cover.slider-for div.easyzoom img[itemprop='image']",
        "thumbnails": "ul.product-images.slider-nav img.thumb.js-thumb",
    },
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
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
]

HEADER_TEMPLATES = [
    {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
]
