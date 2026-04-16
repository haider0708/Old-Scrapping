"""
Technopro — Shop-specific configuration.
Platform: PrestaShop + IQit MegaMenu. PW cats, SSR rest.
"""

from pathlib import Path

BASE_URL = "https://www.technopro-online.com"

PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "nav#cbp-hrmenu ul > li.cbp-hrmenu-tab > a.nav-link"

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

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

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

PAGINATION_SELECTORS = {
    "next_page": "a#infinity-url-next",
    "next_page_fallback": "ul.page-list a.next",
}

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
