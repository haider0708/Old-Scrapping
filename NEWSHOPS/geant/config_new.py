"""
Configuration for Geant e-commerce scraper.
Platform: PrestaShop + WB MegaMenu. No detail pages.
"""

from pathlib import Path

SHOP_NAME = "geant"
BASE_URL = "https://geantdrive.tn"

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

CATEGORY_SELECTORS = {
    "nav_container": "div#_desktop_top_menu div.wb-menu-vertical ul.menu-content.top-menu",
    "top_items": "ul.menu-content.top-menu > li.level-1",
    "top_name": "a > span",
    "top_link": "a[href]",
    "low_items": "div.wb-sub-menu li.menu-item.item-header",
    "low_link": "a.category_header",
    "link_fallback": "a[href]",
}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id_attr": "data-id-product",
    "name": "h2.h3.product-title[itemprop='name'] a",
    "url": "h2.product-title a[href]",
    "image": "a.thumbnail.product-thumbnail img.img-responsive",
    "image_attrs": ["src", "data-src", "data-full-size-image-url"],
    "price": "span.price[itemprop='price']",
    "brand": "p.manufacturer_product",
    "description_short": "div[id^='product-description-short-'][itemprop='description']",
}

PAGINATION_SELECTOR_NEXT = "a.next.js-search-link[rel='next']"

# No detail selectors — geant has no detail pages
DETAIL_SELECTORS = None
