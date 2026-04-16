"""
Skymill Informatique — Shop-specific configuration.
Platform: PrestaShop + SP Mega Menu. PW cats, SSR rest.
"""

from pathlib import Path

BASE_URL = "https://skymil-informatique.com"

PLAYWRIGHT_TIMEOUT = 30000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "div#spverticalmenu_1 ul.level-1 > li.item-1 > a"

CATEGORY_SELECTORS = {
    "nav_container": "div#spverticalmenu_1 ul.level-1",
    "top_items": "ul.level-1 > li.item-1",
    "top_link": "a",
    "low_items": "div.dropdown-menu ul.level-2 > li.item-2 > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature.sp-product-style1",
    "id": None,
    "id_attr": "data-id-product",
    "name": "h2.h3.product-title a",
    "url": "h2.h3.product-title a",
    "image": ".product-image img[itemprop='image']",
    "image_attrs": ["src"],
    "price": "span.price[aria-label='Prix']",
    "price_meta": "meta[itemprop='price']",
    "price_meta_attr": "content",
    "old_price": "span.regular-price[aria-label='Prix de base']",
    "discount": "span.discount-amount.discount-product",
    "description_short": ".product-description-short[itemprop='description']",
}

PAGINATION_SELECTORS = {
    "next_page": "a.next.js-search-link",
}

DETAIL_SELECTORS = {
    "title": "h1.product-name[itemprop='name']",
    "brand": "img.manufacturer-logo",
    "brand_attr": "src",
    "reference": ".product-reference span[itemprop='sku']",
    "price": ".product-price span[itemprop='price']",
    "price_content_attr": "content",
    "old_price": ".regular-price",
    "global_availability": "span#product-availability",
    "availability_schema": "link[itemprop='availability'][href]",
    "delivery_info": "span.delivery-information",
    "description": ".product-short-description",
    "specs": {
        "container": "section.product-features dl.data-sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "images": {
        "main": "img.js-qv-product-cover",
        "main_attrs": ["src"],
        "thumbnails": "img.thumb.js-thumb",
        "thumbnail_attr": "data-image-large-src",
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
