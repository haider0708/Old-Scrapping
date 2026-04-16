"""
Configuration for Allani e-commerce scraper.
Shop-specific selectors, URL, and overrides only.
All shared defaults come from common.config.
Platform: PrestaShop (standard dropdown menu).
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
SHOP_NAME = "allani"
BASE_URL = "https://allani.com.tn"

# ---------------------------------------------------------------------------
# Paths (auto-computed)
# ---------------------------------------------------------------------------
SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"

# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "category_id_from_li": r"category-(\d+)",
}

# ---------------------------------------------------------------------------
# Category selectors (PrestaShop standard 3-level dropdown)
# ---------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "top_items": "ul#top-menu[data-depth='0'] > li.category",
    "top_link": "a.dropdown-item[data-depth='0']",
    "low_items": "ul[data-depth='1'] > li.category",
    "low_link": "a.dropdown-item[data-depth='1']",
    "sub_items": "ul[data-depth='2'] > li.category",
    "sub_link": "a.dropdown-item[data-depth='2']",
}

# ---------------------------------------------------------------------------
# Listing selectors
# ---------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": "data-id-product",
    "name": ".product-description h3.product-title a",
    "image": ".dd-product-image a.product-thumbnail img",
    "image_attrs": ["data-src", "src"],
    "price": ".product-price-and-shipping span.price[itemprop='price']",
    "reference": ".product-reference strong",
    "ean": ".product-ean strong",
    "description_short": ".product-detail[itemprop='description']",
    "promo_flag": "ul.product-flags li.on-sale",
    "availability": {
        "selector": "span#product-availability",
        "fallback": "span.dispo",
    },
}

# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------
PAGINATION_SELECTOR_NEXT = "ul.pagination a.next.js-search-link[rel='next']"

# ---------------------------------------------------------------------------
# Detail selectors
# ---------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.h1.product[itemprop='name']",
    "brand": ".product-manufacturer a",
    "reference": ".product-reference span[itemprop='sku']",
    "ean": ".product-ean span[itemprop='sku'] b",
    "price": ".current-price span[itemprop='price']",
    "global_availability": "span#product-availability",
    "description": "[itemprop='description']",
    "images": {
        "main": "img.js-qv-product-cover",
        "main_attrs": ["src"],
        "thumbnails": "img.thumb.js-thumb",
        "thumbnail_attrs": ["data-image-large-src", "src"],
    },
    "schema_availability": "link[itemprop='availability'][href]",
}
