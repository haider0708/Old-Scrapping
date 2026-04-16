"""Tunisianet — Shop-specific config. Platform: PrestaShop + WB MegaMenu. Full SSR."""
from pathlib import Path

BASE_URL = "https://www.tunisianet.com.tn"

CATEGORY_SELECTORS = {
    "nav_container": "div#_desktop_top_menu div.wb-menu-vertical ul.menu-content.top-menu",
    "top_items": "ul.menu-content.top-menu > li.level-1",
    "top_name": "div.icon-drop-mobile > span",
    "top_link": None,
    "low_items": "li.menu-item.item-header",
    "low_link": "a",
    "sub_items": "li.menu-item.item-line > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": None, "id_attr": "data-id-product",
    "name": "h2.product-title a", "url": "h2.product-title a",
    "image": "a.thumbnail.product-thumbnail img.center-block",
    "image_attrs": ["src", "data-full-size-image-url"],
    "price": "span.price[itemprop='price']", "old_price": "span.regular-price",
    "discount": "span.discount-amount.discount-product",
    "reference": "span.product-reference",
    "brand": "div.product-manufacturer img.manufacturer-logo", "brand_attr": "alt",
    "description_short": "div.listds a",
    "description_short_fallback": "div[id^='product-description-short-']",
    "availability": {"in_stock": "#stock_availability span.in-stock"},
}

PAGINATION_SELECTORS = {"next_page": "a.next.js-search-link"}

DETAIL_SELECTORS = {
    "json_data": "#product-details[data-product]", "json_data_attr": "data-product",
    "json_fields": {
        "id": "id_product", "name": "name", "price": "price_amount",
        "price_display": "price", "old_price": "price_without_reduction",
        "discount": "discount_amount", "reference": "reference", "url": "link",
        "quantity": "quantity", "available_for_order": "available_for_order",
        "images": "images", "features": "features",
    },
    "out_of_stock_notice": "div.product-out-of-stock",
    "description": "div#description div.product-d",
    "specs": {"container": "dl.data-sheet", "key": "dt.name", "value": "dd.value"},
}

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
