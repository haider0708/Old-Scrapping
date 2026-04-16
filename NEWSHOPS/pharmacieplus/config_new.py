"""Pharmacieplus — Shop-specific config. Custom PHP + Bootstrap 4. Full CSR (Playwright)."""
from pathlib import Path

BASE_URL = "https://parapharmacieplus.tn"
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "ul.navbar-nav.u-header__navbar-nav"
PLAYWRIGHT_LISTING_WAIT = "li.col-md-mc-5.col-fix.item-prod"
PLAYWRIGHT_DETAIL_WAIT = "h1.font-size-25"
BROWSER_POOL_SIZE = 3

CATEGORY_SELECTORS = {
    "nav_container": "ul.navbar-nav.u-header__navbar-nav",
    "top_items": "ul.navbar-nav.u-header__navbar-nav > li.nav-item.hs-has-mega-menu",
    "top_link": "a#basicMegaMenu, a.nav-link",
    "top_name": "a",
    "low_name": "span.u-header__sub-menu-title",
    "sub_items": "ul.u-header__sub-menu-nav-group > li > a.u-header__sub-menu-nav-link",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "cat_id_from_url": r"categorie=(\d+)|/categorie[/-](\d+)|/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

LISTING_SELECTORS = {
    "element": "li.col-md-mc-5.col-fix.item-prod",
    "name": "div.text-truncate.name-prod-card",
    "url": "a.text-gray-100.justify-content-around",
    "image": "div.product-item__inner.position-relative img",
    "image_attrs": ["src", "data-src"],
    "price": "div.info-ligne-card div.text-red",
    "old_price": "del.font-size-12",
}

PAGINATION_SELECTORS = {
    "next_page": "li.page-item a.page-link i.fa.fa-angle-right",
    "url_pattern": "?mayor=offre&mayor=shop&categorie={cat_id}&perpage=20&page={n}",
}

DETAIL_SELECTORS = {
    "title": "h1.font-size-25.text-lh-1dot2",
    "price": "ins.font-size-36.text-decoration-none",
    "price_schema": "meta[itemprop='price'][content]",
    "old_price": "del.font-size-20.ml-2.text-gray-6",
    "description": "div#tab-description",
    "images": {"gallery": "div.fotorama", "all": "div.fotorama img.fotorama__img"},
}

MAX_CONCURRENT_REQUESTS = 4

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
