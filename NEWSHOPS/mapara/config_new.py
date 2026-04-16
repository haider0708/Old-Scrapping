"""Mapara — Shop-specific config. WooCommerce + Flatsome. Full SSR."""
from pathlib import Path

BASE_URL = "https://www.maparatunisie.tn"

CATEGORY_SELECTORS = {
    "nav_container": "ul.nav.header-nav.header-bottom-nav",
    "top_items": "ul.header-nav.header-bottom-nav > li.menu-item.has-dropdown",
    "top_link": "a.nav-top-link", "top_name": "a.nav-top-link",
    "mega_low": "div.sub-menu.nav-dropdown div.text.text-mega p > a",
    "simple_low": "ul.sub-menu.nav-dropdown.nav-dropdown-simple > li.menu-item > a",
    "sub_items": "div.ux-menu div.ux-menu-link a.ux-menu-link__link",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "div.product-small.col",
    "id_attr": "data-product_id", "id_selector": "a.add_to_cart_button",
    "name": "p.name.product-title a.woocommerce-LoopProduct-link",
    "url": "a.woocommerce-LoopProduct-link",
    "image": "div.image-fade_in_back picture img",
    "image_attrs": ["src", "data-src"],
    "price": "ins span.woocommerce-Price-amount bdi",
    "old_price": "del span.woocommerce-Price-amount bdi",
    "availability": {"instock_class": "instock", "outofstock_class": "outofstock"},
}

PAGINATION_SELECTORS = {"next_page": "a.next.page-number"}

DETAIL_SELECTORS = {
    "title": "h1.product-title.product_title.entry-title",
    "price": "p.price ins span.woocommerce-Price-amount bdi",
    "old_price": "p.price del span.woocommerce-Price-amount bdi",
    "availability_add_to_cart": "form.cart button[name='add-to-cart']",
    "brand": "a[href*='/nos-marques/'] img", "brand_attr": "alt",
    "description": "div.woocommerce-Tabs-panel--description",
    "images": {
        "main": "div.woocommerce-product-gallery__image.slide.first img.wp-post-image",
        "gallery": "div.woocommerce-product-gallery__image.slide a",
    },
}

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
