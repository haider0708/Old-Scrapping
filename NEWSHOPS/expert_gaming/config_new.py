"""
Configuration for Expert Gaming e-commerce scraper.
Platform: WooCommerce + Elementor + YITH.
"""

from pathlib import Path

SHOP_NAME = "expert_gaming"
BASE_URL = "https://expert-gaming.tn"

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"

PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "ul#menu-notre-boutique > li.menu-item > a"

URL_PATTERNS = {
    "category_id_from_li": r"menu-item-(\d+)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

CATEGORY_SELECTORS = {
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

LISTING_SELECTORS = {
    "element": "section.product",
    "id_attr": "data-product_id",
    "name": "h3.heading-title.product-name a",
    "image": "div.thumbnail-wrapper figure img.wp-post-image",
    "image_attrs": ["src"],
    "price": "span.price span.woocommerce-Price-amount bdi",
    "old_price": "span.price del span.woocommerce-Price-amount bdi",
    "sale_price": "span.price ins span.woocommerce-Price-amount bdi",
    "categories_selector": "div.product-categories a[rel='tag']",
    "brands_selector": "div.product-brands a",
    "cart_button": "a.button.add_to_cart_button.ajax_add_to_cart",
    "sku_attr": "data-product_sku",
    "availability": {
        "instock_class": "instock",
        "outofstock_class": "outofstock",
    },
}

PAGINATION_SELECTOR_NEXT = "ul.page-numbers a.next.page-numbers"

DETAIL_SELECTORS = {
    "title": "h1.product_title.entry-title",
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
    },
    "images": {
        "main": "div.woocommerce-product-gallery__image img",
        "main_attrs": ["src"],
    },
}
