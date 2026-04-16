"""Pharmashop — Shop-specific config. PrestaShop 1.7 + Leo Theme. Full SSR."""
from pathlib import Path

BASE_URL = "https://pharma-shop.tn"

CATEGORY_SELECTORS = {
    "nav_container": "nav.leo-megamenu ul.nav.navbar-nav.megamenu.horizontal",
    "top_items": "ul.megamenu.horizontal > li.nav-item.parent.dropdown",
    "top_link": "a.nav-link.dropdown-toggle",
    "top_name": "a.nav-link span.menu-title",
    "low_items": "div.dropdown-menu-inner ul.row > li.col-md-4",
    "sub_items": "ul > li > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h2.h3.product-title[itemprop='name'] a", "url": "h2.product-title a",
    "image": "a.thumbnail.product-thumbnail img",
    "image_attrs": ["src", "data-src", "data-full-size-image-url"],
    "price": "span.price[aria-label='Prix']",
    "price_schema": "meta[itemprop='price'][content]",
    "old_price": "span.regular-price[aria-label='Prix de base']",
    "discount": "span.discount-percentage.discount-product",
    "brand": "div.text-center.txt-marque a",
    "availability": {"out_of_stock_flag": "ul.product-flags > li.product-flag.out_of_stock"},
}

PAGINATION_SELECTORS = {"next_page": "a.next.js-search-link[rel='next']"}

DETAIL_SELECTORS = {
    "json_data": "div.tab-pane#product-details[data-product]", "json_data_attr": "data-product",
    "json_fields": {
        "id": "id_product", "name": "name", "price": "price_amount",
        "price_display": "price", "old_price": "price_without_reduction",
        "discount": "discount_amount", "reference": "reference",
        "quantity": "quantity", "available_for_order": "available_for_order",
        "images": "images", "features": "features",
    },
    "title": "h1.h1[itemprop='name']",
    "price": "div.current-price span[itemprop='price']", "price_content_attr": "content",
    "old_price": "div.product-discount span.regular-price",
    "discount": "div.product-discount span.discount-percentage",
    "description": "div.product-description[itemprop='description']",
    "brand": "div.product-manufacturer img.manufacturer-logo", "brand_attr": "alt",
    "images": {"main": "div.product-cover img.js-qv-product-cover", "thumbnails": "ul.product-images.js-qv-product-images img.thumb"},
}

MAX_CONCURRENT_REQUESTS = 1
POOL_MAX_CONNECTIONS = 5
POOL_MAX_KEEPALIVE = 2

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
