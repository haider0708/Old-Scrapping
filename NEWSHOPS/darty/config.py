"""
Configuration for Darty e-commerce scraper.
All selectors and configuration. Platform: PrestaShop + GloboMegaMenu.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://darty.tn"

# -----------------------------------------------------------------------------
# CSS Selectors (GloboMegaMenu structure)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "li.globomenu-item-level-0",
    "top_items": "ul.globomenu-tab-links > li.globomenu-tab",
    "top_link": "a.globomenu-target",
    "top_name": "span.globomenu-target-text",
    "top_id_attr": "data-id",
    "low_items": "li.globomenu-item-header",
    "low_link": "a.globomenu-target",
    "low_name": "span.globomenu-target-text",
    "sub_items": "ul.globomenu-submenu-type-stack > li.globomenu-item-normal",
    "sub_link": "a.globomenu-target",
    "sub_name": "span.globomenu-target-text",
}

# -----------------------------------------------------------------------------
# URL patterns
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
}

# -----------------------------------------------------------------------------
# Listing selectors
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": "data-id-product",
    "id_attr": None,
    "name": "h3.h3.product-title[itemprop='name'] a",
    "url": "h3.product-title a[href]",
    "image": "a.thumbnail.product-thumbnail img[src]",
    "image_attrs": ["src"],
    "image_variants": {
        "small": "img[data-catalog-small]",
        "medium": "img[data-catalog-medium]",
        "large": "img[data-catalog-large]",
        "full": "img[data-full-size-image-url]",
    },
    "price": "span.price[itemprop='price']",
    "price_attr": "content",
    "price_display": "span.money[data-currency-tnd]",
    "old_price": None,
    "category": "div.categ-product span.product-category",
    "features": "section.product-features ul.features_head li.name_value",
    "availability": {
        "schema": "link[itemprop='availability'][href]",
        "cart_button_status": "button[data-button-action='add-to-cart'][data-status]",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination",
    "load_more_button": "button.btn.btn-primary.js-pagination-top-catalogue",
    "page_list": "ul#pagination-main.page-list a.js-search-link",
    "current_page": "ul.page-list li.current a.disabled",
    "next_page": "a.next.js-search-link[rel='next']",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "div.product-name h1.h1[itemprop='name']",
    "title_parts": {
        "category": "h1.h1 span.product_category",
        "name": "h1.h1 span.product_name",
    },
    "brand": {
        "container": "a[href*='/brand/']",
        "logo": "img.manufacturer-logo",
    },
    "price": "div.product-price span[itemprop='price']",
    "old_price": "div.product-discount span.regular-price",
    "savings": "div.economisez span.economise-price",
    "promo_flag": "ul.custom_promo li.product-flag.promo",
    "global_availability": "div.product-price link[itemprop='availability']",
    "availability_per_shop": {
        "container": "div.warehouse-availability",
        "row": "div.warehouse-status-item",
        "name": "span.warehouse-name",
        "status": "span.warehouse-status",
    },
    "images": {
        "main": "#an_product-zoom img.productslider-main-image",
        "zoom": "img.productslider-main-image[data-image-zoom-src]",
        "zoom_attr": "data-image-zoom-src",
        "slider": "div.an_productpage-slider-item img",
        "main_attrs": ["src", "data-image-zoom-src"],
    },
    "features_short": "section.product-features ul.features_head li.name_value",
    "specs": {
        "container": "#product-details section.product-features",
        "row": "dl.data_sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "installment": {
        "container": "div.facility_content",
        "monthly_price": "span.facility_price",
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
# Header templates
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
]
