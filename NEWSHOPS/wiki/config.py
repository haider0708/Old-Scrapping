"""
Configuration for Wiki e-commerce scraper.
CSR front page (Playwright for categories), SSR listings/details.
Platform: WordPress + Bricks Builder + WooCommerce + WP Grid Builder.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://wiki.tn"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR category extraction)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "nav.desktop-nav ul.categories-menu"

# -----------------------------------------------------------------------------
# CSS Selectors - Bricks 3-level nav (top label-only, low/sub with links)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "nav.desktop-nav ul.categories-menu",
    "top_items": "nav.desktop-nav ul.categories-menu > li.drop-down-category",
    "top_name": "div.brx-submenu-toggle > span",
    "top_link": None,
    "low_items": "ul.drop-down-subcategories > li.menu-item",
    "low_heading": "h6.subcategory-heading",
    "low_link": "h6.subcategory-heading a",
    "sub_items": "div.subcategories-div a",
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
# Listing selectors - WooCommerce product cards (WP Grid Builder)
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "div.product-card--grid",
    "id_from": "data-product_id",
    "id_selector": "a.add_to_cart_button",
    "id_attr": "data-product_id",
    "id_attr_alt": "data-product_sku",
    "name": "h3.product-card__title a",
    "url": "h3.product-card__title a",
    "image": "figure.product-card__image img",
    "image_attrs": ["src", "data-src"],
    "price": ".product-card__price .woocommerce-Price-amount bdi",
    "old_price": ".product-card__price del .woocommerce-Price-amount bdi",
    "brand": ".product-card__brand-logo img",
    "brand_attr": "alt",
    "sku": ".product-card__sku .sku",
    "availability_selector": ".product-availability .brxe-shortcode-dispo",
    "availability_attr": "data-stock-status",
}

# -----------------------------------------------------------------------------
# Pagination selectors (WP Grid Builder)
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.wpgb-pagination-facet",
    "page_list": "ul.wpgb-pagination li.wpgb-page a",
    "next_page": "li.wpgb-page-next a",
    "url_pattern": "?_pagination={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors - WooCommerce
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.brxe-product-title, .product-top__title",
    "sku": ".product_meta .sku",
    "brand": ".product-card__logo-wrapper--big .product-card__brand-logo img",
    "brand_attr": "alt",
    "price_regular": ".product-card__price-new .price > .woocommerce-Price-amount bdi",
    "price_sale": ".product-card__price-new .price ins .woocommerce-Price-amount bdi",
    "price_original": ".product-card__price-new .price del .woocommerce-Price-amount bdi",
    "availability_badge": ".stock-status-badge[data-stock-status]",
    "availability_woo": ".stock.in-stock, .stock.available-on-backorder",
    "description": ".woocommerce-product-details__short-description",
    "full_description": "#tab-description",
    "specs": {
        "container": "table.shop_attributes",
        "key": "th.woocommerce-product-attributes-item__label",
        "value": "td.woocommerce-product-attributes-item__value",
    },
    "images": {
        "main": ".woocommerce-product-gallery__image img.wp-post-image",
        "gallery": ".woocommerce-product-gallery__image a",
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
