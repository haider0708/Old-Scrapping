"""Zoom — Shop-specific config. Platform: PrestaShop + ETS Mega Menu. Full SSR."""
from pathlib import Path

BASE_URL = "https://zoom.com.tn"

CATEGORY_SELECTORS = {
    "nav_container": "li.mm_menus_li",
    "top_items": "li.mm_tabs_li",
    "top_link": ".mm_tab_toggle_title a",
    "top_name": ".mm_tab_toggle_title a",
    "low_items": ".ets_mm_block .h4 a, .ets_mm_block span.h4 a",
    "low_link": "a",
    "sub_items": ".ets_mm_categories > li > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "div.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h5.product-name > a", "url": "h5.product-name > a",
    "image": ".product-cover-link img.img-fluid",
    "image_attrs": ["src", "data-original"],
    "price": "span.price.product-price", "old_price": "span.regular-price",
    "discount": "span.product-flag.discount",
    "description_short": ".product-description-short",
    "availability": {
        "selector": ".product-availability span", "status_from_text": True,
        "in_stock_text": "En stock", "out_of_stock_text": "Hors stock",
        "in_commande_text": "Sur Commande",
    },
}

PAGINATION_SELECTORS = {"next_page": "a.next.js-search-link"}

DETAIL_SELECTORS = {
    "json_data": "#product-details[data-product]", "json_data_attr": "data-product",
    "out_of_stock_notice": "div.product-out-of-stock",
    "json_fields": {
        "id": "id_product", "name": "name", "price": "price_amount",
        "price_display": "price", "old_price": "price_without_reduction",
        "discount": "discount_amount", "reference": "reference",
        "quantity": "quantity", "available_for_order": "available_for_order",
        "images": "images", "features": "features",
    },
    "title": "h1.page-heading",
    "brand": ".attribute-item.product-manufacturer a span",
    "reference": ".attribute-item.product-reference span",
    "price": "span.price.product-price.current-price-value",
    "price_content_attr": "content",
    "old_price": "p.previous-price span.regular-price",
    "discount": "p.previous-price span.discount-amount",
    "global_availability": "#product-availability span",
    "description": "div[id^='product-description-short-']",
    "full_description": "#description",
    "specs": {"container": ".product-features dl.data-sheet", "key": "dt.name", "value": "dd.value"},
    "images": {"main": ".product-cover img.js-qv-product-cover", "main_attrs": ["src"], "thumbnails": ".thumb.js-thumb", "thumbnail_attr": "data-zoom-image"},
}

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
