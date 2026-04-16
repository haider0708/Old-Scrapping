"""
Configuration for Expert Gaming e-commerce scraper.
All selectors and configuration. Platform: WooCommerce + Elementor + YITH.
CSR homepage (Playwright for categories), SSR listings/details.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://expert-gaming.tn"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR category extraction)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "ul#menu-notre-boutique > li.menu-item > a"

# -----------------------------------------------------------------------------
# CSS Selectors - WooCommerce vertical mega menu
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "nav.vertical-menu.pc-menu.ts-mega-menu-wrapper ul#menu-notre-boutique.menu",
    "top_items": "ul#menu-notre-boutique > li.menu-item",
    "top_link": "a",
    "top_name": "a > span.menu-label",
    "top_id_attr": "id",
    "sub_menu": "ul.sub-menu",
    "low_blocks": "div.ts-list-of-product-categories-wrapper",
    "low_link": "h3.heading-title a, div.elementor-heading-title a",
    "sub_items": "ul > li",
    "sub_link": "a",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "category_id_from_li": r"menu-item-(\d+)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

# -----------------------------------------------------------------------------
# Listing selectors - WooCommerce
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "section.product",
    "id": None,
    "id_attr": "data-product_id",
    "name": "h3.heading-title.product-name a",
    "url": "h3.heading-title.product-name a",
    "image": "div.thumbnail-wrapper figure img.wp-post-image",
    "image_attrs": ["src"],
    "price": "span.price span.woocommerce-Price-amount bdi",
    "old_price": "span.price del span.woocommerce-Price-amount bdi",
    "sale_price": "span.price ins span.woocommerce-Price-amount bdi",
    "currency": "span.woocommerce-Price-currencySymbol",
    "categories": "div.product-categories a[rel='tag']",
    "brands": "div.product-brands a",
    "cart_button": "a.button.add_to_cart_button.ajax_add_to_cart",
    "sku_attr": "data-product_sku",
    "availability": {
        "instock_class": "instock",
        "outofstock_class": "outofstock",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.woocommerce-pagination",
    "page_list": "ul.page-numbers a.page-numbers",
    "current_page": "ul.page-numbers span.page-numbers.current[aria-current='page']",
    "next_page": "ul.page-numbers a.next.page-numbers",
    "url_pattern": "/page/{n}/",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.product_title.entry-title",
    "breadcrumbs": None,
    "brand": "div.product-brands a",
    "sku": "div.sku-wrapper span.sku",
    "price": "p.price span.woocommerce-Price-amount bdi",
    "old_price": "p.price del span.woocommerce-Price-amount bdi",
    "sale_price": "p.price ins span.woocommerce-Price-amount bdi",
    "global_availability": "div.availability.stock span.availability-text",
    "availability_data": "div.availability.stock",
    "availability_data_attrs": ["data-original", "data-class"],
    "description": "div.woocommerce-product-details__short-description",
    "specs": {
        "container": "table.woocommerce-product-attributes.shop_attributes",
        "row": "tr.woocommerce-product-attributes-item",
        "key": "th.woocommerce-product-attributes-item__label",
        "value": "td.woocommerce-product-attributes-item__value",
    },
    "specs_alt": {
        "container": "div.ts-dimensions-content ul",
        "items": "li",
        "item_pairs": "span",
    },
    "images": {
        "main": "div.woocommerce-product-gallery__image img",
        "main_attrs": ["src"],
        "gallery": "div.woocommerce-product-gallery__image",
        "gallery_thumb_attr": "data-thumb",
        "thumbnails": "ol.flex-control-nav.flex-control-thumbs img",
    },
    "tabs": {
        "description": "li.description_tab",
        "specs": "li.additional_information_tab",
        "reviews": "li.reviews_tab",
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
