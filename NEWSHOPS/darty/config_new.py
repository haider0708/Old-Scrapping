"""
Configuration for Darty e-commerce scraper.
Platform: PrestaShop + GloboMegaMenu.
"""

from pathlib import Path

SHOP_NAME = "darty"
BASE_URL = "https://darty.tn"

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
}

CATEGORY_SELECTORS = {
    "nav_container": "li.globomenu-item-level-0",
    "top_items": "ul.globomenu-tab-links > li.globomenu-tab",
    "top_link": "a.globomenu-target",
    "top_name": "span.globomenu-target-text",
    "top_id_attr": "data-id",
    "low_items": "li.globomenu-item-header",
    "low_link": "a.globomenu-target",
    "sub_items": "ul.globomenu-submenu-type-stack > li.globomenu-item-normal",
    "sub_link": "a.globomenu-target",
}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": "data-id-product",
    "name": "h3.h3.product-title[itemprop='name'] a",
    "url": "h3.product-title a[href]",
    "image": "a.thumbnail.product-thumbnail img[src]",
    "image_attrs": ["src"],
    "price": "span.price[itemprop='price']",
    "price_attr": "content",
    "price_display": "span.money[data-currency-tnd]",
    "category": "div.categ-product span.product-category",
    "features": "section.product-features ul.features_head li.name_value",
    "availability": {
        "schema": "link[itemprop='availability'][href]",
        "cart_button_status": "button[data-button-action='add-to-cart'][data-status]",
    },
}

PAGINATION_SELECTOR_NEXT = "a.next.js-search-link[rel='next']"

DETAIL_SELECTORS = {
    "title": "div.product-name h1.h1[itemprop='name']",
    "title_parts": {
        "category": "h1.h1 span.product_category",
        "name": "h1.h1 span.product_name",
    },
    "brand": {
        "container": "a[href*='/brand/']",
        "logo": "img.manufacturer-logo",
    },
    "price": "div.product-price span[itemprop='price']",
    "old_price": "div.product-discount span.regular-price",
    "savings": "div.economisez span.economise-price",
    "promo_flag": "ul.custom_promo li.product-flag.promo",
    "global_availability": "div.product-price link[itemprop='availability']",
    "availability_per_shop": {
        "container": "div.warehouse-availability",
        "row": "div.warehouse-status-item",
        "name": "span.warehouse-name",
        "status": "span.warehouse-status",
    },
    "images": {
        "main": "#an_product-zoom img.productslider-main-image",
        "main_attrs": ["src", "data-image-zoom-src"],
        "slider": "div.an_productpage-slider-item img",
    },
    "features_short": "section.product-features ul.features_head li.name_value",
    "specs": {
        "container": "#product-details section.product-features",
        "row": "dl.data_sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "installment": {
        "container": "div.facility_content",
        "monthly_price": "span.facility_price",
    },
    "schema_availability": "link[itemprop='availability'][href]",
}
