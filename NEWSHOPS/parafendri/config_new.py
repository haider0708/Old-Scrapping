"""Parafendri — Shop-specific config. PrestaShop + PosThemes MegaMenu. Full SSR."""
from pathlib import Path

BASE_URL = "https://parafendri.tn"

CATEGORY_SELECTORS = {
    "nav_container": "div#_desktop_megamenu div.pos-menu-horizontal > ul.menu-content",
    "top_items": "ul.menu-content > li.menu-item",
    "top_link": "a", "top_name": "a > span",
    "mega_low": "div.pos-sub-menu.menu-dropdown div.pos-menu-col > ul.ul-column > li.submenu-item",
    "simple_low": "div.menu-dropdown.cat-drop-menu > ul.pos-sub-inner > li",
    "sub_items": "ul.category-sub-menu > li > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h3[itemprop='name'] > a.product_name", "url": "h3[itemprop='name'] > a.product_name",
    "image": "a.thumbnail.product-thumbnail > img",
    "image_attrs": ["src", "data-src", "data-full-size-image-url"],
    "price": "span[itemprop='price'].price", "old_price": "span.regular-price",
    "discount": "span.discount-amount.discount-product",
    "description_short": "div.product-desc[itemprop='description']",
    "availability": {
        "in_stock": "div.availability-list.in-stock > span",
        "out_of_stock": "div.availability-list.out-of-stock > span",
        "out_of_stock_flag": "ul.product-flag > li.out_of_stock > span",
    },
}

PAGINATION_SELECTORS = {"next_page": "a.next.js-search-link[rel='next']"}

DETAIL_SELECTORS = {
    "json_data": "#product-details[data-product]", "json_data_attr": "data-product",
    "json_fields": {
        "id": "id_product", "name": "name", "price": "price_amount",
        "price_display": "price", "old_price": "price_without_reduction",
        "discount": "discount_amount", "reference": "reference",
        "quantity": "quantity", "available_for_order": "available_for_order",
        "images": "images", "features": "features",
    },
    "out_of_stock_notice": "div.product-out-of-stock",
    "title": "h1.h1.namne_details[itemprop='name']", "sku": "p.reference > span",
    "price": "div.current-price > span[itemprop='price']", "price_content_attr": "content",
    "old_price": "div.product-discount > span.regular-price",
    "discount": "span.discount.discount-amount",
    "description": "div#description div.product-description",
    "brand": "div.product-manufacturer img.manufacturer-logo", "brand_attr": "alt",
    "images": {"main": "div.product-cover.slider-for div.easyzoom img[itemprop='image']", "thumbnails": "ul.product-images.slider-nav img.thumb.js-thumb"},
}

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
