"""
Spacenet — Shop-specific configuration.
Platform: PrestaShop + SP Mega Menu. Full SSR.
"""

from pathlib import Path

BASE_URL = "https://spacenet.tn"

CATEGORY_SELECTORS = {
    "nav_container": "#sp-vermegamenu ul.level-1",
    "top_items": "#sp-vermegamenu ul.level-1 > li.item-1",
    "top_link": "a",
    "top_name": "a > span.sp_megamenu_title",
    "low_items": "div.dropdown-menu ul.level-2 > li.item-2",
    "low_link": "a",
    "sub_items": "ul.level-3 > li.item-3 > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

LISTING_SELECTORS = {
    "element": "div.field-product-item.item-inner.product-miniature.js-product-miniature",
    "id": None,
    "id_attr": "data-id-product",
    "name": "h2.product_name a",
    "url": "h2.product_name a",
    "image": "img.img-responsive.product_image",
    "image_attrs": ["src"],
    "price": ".product-price-and-shipping .price",
    "old_price": ".product-price-and-shipping .regular-price",
    "reference": ".product-reference span:nth-child(2)",
    "brand": "img.manufacturer-logo",
    "brand_attr": "alt",
    "availability": {
        "in_stock": ".product-quantities label.label",
        "in_arrivage": ".product-quantities label.label-available",
    },
}

PAGINATION_SELECTORS = {
    "next_page": "ul.page-list a.next",
}

DETAIL_SELECTORS = {
    "title": "h1.h1",
    "reference": ".product-Details .product-reference span",
    "brand": ".product-Details .product-manufacturer a img",
    "brand_attr": "alt",
    "brand_link": ".product-Details .product-manufacturer a",
    "brand_link_attr": "href",
    "price": ".current-price > span",
    "price_content_attr": "content",
    "old_price": ".product-discount .regular-price",
    "description": "div.product-des",
    "description_fallback": "div[id^='product-description-short-']",
    "global_availability": ".product-quantities .label",
    "stock_quantity": ".product-quantities span[data-stock]",
    "stock_quantity_attr": "data-stock",
    "availability_schema": "link[itemprop='availability'][href]",
    "availability_per_shop": {
        "container": ".social-sharing-magasin .magasin-table",
        "row": ".table-bloc.row",
        "shop_name": ".left-side span",
        "shop_address": ".left-side p",
        "shop_status": ".right-side span",
        "shop_note": ".right-side p",
        "available_icon": ".right-side i.fa-check",
        "unavailable_icon": ".right-side i.fa-times",
    },
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
    "json_data": "#product-details[data-product]",
    "json_data_attr": "data-product",
    "installment": {
        "container": ".social-sharing-payement .payement-table",
        "term": "li.f-date",
        "amount": "li.f-price",
    },
}

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
