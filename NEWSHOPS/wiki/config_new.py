"""
Wiki — Shop-specific configuration.
Platform: WordPress + Bricks Builder + WooCommerce + WP Grid Builder. PW cats, SSR rest.
"""

from pathlib import Path

BASE_URL = "https://wiki.tn"

PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "nav.desktop-nav ul.categories-menu"

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

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

LISTING_SELECTORS = {
    "element": "div.product-card--grid",
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

PAGINATION_SELECTORS = {
    "next_page": "li.wpgb-page-next a",
}

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

# ── httpx / concurrency ──────────────────────────────────────────────────────
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30
MIN_DELAY = 1.0
MAX_DELAY = 3.0
MAX_CONCURRENT_REQUESTS = 8
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
POOL_MAX_CONNECTIONS = 20
POOL_MAX_KEEPALIVE = 5

# ── Paths ─────────────────────────────────────────────────────────────────────
SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
PRODUCT_HISTORY_FILE = DATA_DIR / "product_history.json"
