"""
Configuration for Mapara e-commerce scraper.
Full SSR. Platform: WooCommerce + Flatsome/UX Builder.
Dual dropdown (mega + simple). Class-based availability. Pagination /page/{n}/.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://www.maparatunisie.tn"

# -----------------------------------------------------------------------------
# CSS Selectors - Flatsome dual dropdown (mega + simple)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "ul.nav.header-nav.header-bottom-nav",
    "top_items": "ul.header-nav.header-bottom-nav > li.menu-item.has-dropdown",
    "top_link": "a.nav-top-link",
    "top_name": "a.nav-top-link",
    "mega_low": "div.sub-menu.nav-dropdown div.text.text-mega p > a",
    "simple_low": "ul.sub-menu.nav-dropdown.nav-dropdown-simple > li.menu-item > a",
    "sub_items": "div.ux-menu div.ux-menu-link a.ux-menu-link__link",
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
# Listing selectors - WooCommerce Flatsome
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "div.product-small.col",
    "id_attr": "data-product_id",
    "id_selector": "a.add_to_cart_button",
    "name": "p.name.product-title a.woocommerce-LoopProduct-link",
    "url": "a.woocommerce-LoopProduct-link",
    "image": "div.image-fade_in_back picture img",
    "image_attrs": ["src", "data-src"],
    "price": "ins span.woocommerce-Price-amount bdi",
    "old_price": "del span.woocommerce-Price-amount bdi",
    "discount": "div.badge-inner.secondary.on-sale span.onsale",
    "availability": {
        "instock_class": "instock",
        "outofstock_class": "outofstock",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors (WooCommerce /page/{n}/)
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.woocommerce-pagination",
    "page_list": "ul.page-numbers a.page-number",
    "next_page": "a.next.page-number",
    "url_pattern": "/page/{n}/",
}

# -----------------------------------------------------------------------------
# Detail selectors - WooCommerce
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.product-title.product_title.entry-title",
    "price": "p.price ins span.woocommerce-Price-amount bdi",
    "old_price": "p.price del span.woocommerce-Price-amount bdi",
    "discount": "div.badge-inner.secondary.on-sale span.onsale",
    "availability_add_to_cart": "form.cart button[name='add-to-cart']",
    "brand": "a[href*='/nos-marques/'] img",
    "brand_attr": "alt",
    "description": "div.woocommerce-Tabs-panel--description",
    "specs": None,
    "images": {
        "main": "div.woocommerce-product-gallery__image.slide.first img.wp-post-image",
        "gallery": "div.woocommerce-product-gallery__image.slide a",
    },
}

# -----------------------------------------------------------------------------
# Retry settings
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
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

HEADER_TEMPLATES = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
    },
]
