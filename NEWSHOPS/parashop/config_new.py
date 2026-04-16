"""Parashop — Shop-specific config. OpenCart 3.x + Journal 3. Full SSR."""
from pathlib import Path

BASE_URL = "https://www.parashop.tn"

CATEGORY_SELECTORS = {
    "nav_container": "div.desktop-main-menu-wrapper div#main-menu > ul.j-menu",
    "top_items": "ul.j-menu > li.menu-item.main-menu-item.dropdown.mega-menu",
    "top_link": "a.dropdown-toggle", "top_name": "a.dropdown-toggle > span.links-text",
    "low_items": "div.dropdown-menu.j-dropdown div.module-item > div.item-content > a.catalog-title",
    "sub_items": "div.item-assets > div.subitems > div.subitem > a",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"product_id=(\d+)|/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "div.product-layout.has-extra-button",
    "id_input": "input[type='hidden'][name='product_id']", "id_attr": "value",
    "name": "div.caption > div.name > a", "url": "div.caption > div.name > a",
    "image": "a.product-img img.img-first",
    "image_attrs": ["src", "data-src", "data-largeimg"],
    "price": "span.price-new", "old_price": "span.price-old",
    "discount": "div.product-labels span.product-label.product-label-28 b",
    "description_short": "div.caption > div.description",
    "brand": "div.caption > div.stats span.stat-1 span a",
}

PAGINATION_SELECTORS = {"next_page": "li > a.next"}

DETAIL_SELECTORS = {
    "title": "div.product-details > div.title.page-title",
    "sku": "li.product-model > span",
    "price": "div.product-price-group div.product-price-new",
    "old_price": "div.product-price-group div.product-price-old",
    "availability_in_stock": "li.product-stock.in-stock > span",
    "availability_out_of_stock": "li.product-stock.out-of-stock > span",
    "brand": "div.brand-image.product-manufacturer a span",
    "description": "div.tabs-container.product_tabs div.tab-pane.active",
    "lightgallery": "div.lightgallery.lightgallery-product-images",
    "lightgallery_attr": "data-images",
    "images_main": "div.swiper.main-image div.swiper-slide img",
    "images_main_attr": "data-largeimg",
}

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
