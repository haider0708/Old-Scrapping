"""
Configuration for Pharmacie+ e-commerce scraper.
Full CSR - Playwright for categories, listings, and details.
Platform: Custom PHP + Bootstrap 4 + Htmlstream MegaMenu + Fotorama.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://parapharmacieplus.tn"

# -----------------------------------------------------------------------------
# Playwright settings (all phases use Playwright)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True

# -----------------------------------------------------------------------------
# CSS Selectors - Htmlstream MegaMenu
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "ul.navbar-nav.u-header__navbar-nav",
    "top_items": "ul.navbar-nav.u-header__navbar-nav > li.nav-item.hs-has-mega-menu",
    "top_link": "a#basicMegaMenu, a.nav-link",
    "top_name": "a",
    "low_items": "div.hs-mega-menu.u-header__sub-menu div.col-3 > a",
    "low_name": "span.u-header__sub-menu-title",
    "sub_items": "ul.u-header__sub-menu-nav-group > li > a.u-header__sub-menu-nav-link",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns - extract cat_id from category URL for pagination
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "id_from_path": r"/a/(\d+)/",
    "cat_id_from_url": r"categorie=(\d+)|/categorie[/-](\d+)|/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

# -----------------------------------------------------------------------------
# Listing selectors (Playwright - CSR)
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "li.col-md-mc-5.col-fix.item-prod",
    "name": "div.text-truncate.name-prod-card",
    "url": "a.text-gray-100.justify-content-around",
    "image": "div.product-item__inner.position-relative img",
    "image_attrs": ["src", "data-src"],
    "price": "div.info-ligne-card div.text-red",
    "old_price": "del.font-size-12",
    "discount": "div.position-absolute.info-offer-card div.position-relative",
    "availability_in_stock": "div.badge-stock i.fa.fa-check",
    "availability_out_of_stock": "div.badge-stock i.fa.fa-ban",
}

# -----------------------------------------------------------------------------
# Pagination (requires cat_id - extract from category URL)
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "next_page": "li.page-item a.page-link i.fa.fa-angle-right",
    "next_page_parent": "li.page-item a.page-link",
    "url_pattern": "?mayor=offre&mayor=shop&categorie={cat_id}&perpage=20&page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors (Playwright - CSR)
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.font-size-25.text-lh-1dot2",
    "price": "ins.font-size-36.text-decoration-none",
    "price_schema": "meta[itemprop='price'][content]",
    "old_price": "del.font-size-20.ml-2.text-gray-6",
    "discount": "div.text-red",
    "availability_schema": "link[itemprop='availability'][href*='schema.org/InStock']",
    "description": "div#tab-description",
    "reference_paragraph": "p:has(strong:contains('Référence'))",
    "images": {
        "gallery": "div.fotorama",
        "main": "div.fotorama__stage__frame.fotorama__active img.fotorama__img",
        "all": "div.fotorama img.fotorama__img",
    },
}

# -----------------------------------------------------------------------------
# Retry / Delay / Concurrency
# -----------------------------------------------------------------------------
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30
MIN_DELAY = 1.0
MAX_DELAY = 3.0
MAX_CONCURRENT_REQUESTS = 4
PROCESS_POOL_SIZE = 2

# -----------------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------------
SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
PRODUCT_HISTORY_FILE = DATA_DIR / "product_history.json"
QUEUE_CATEGORY_FILENAME = "category_queue.txt"
QUEUE_PRODUCT_FILENAME = "product_queue.txt"

OUTPUT_CATEGORIES = "categories.json"
OUTPUT_PRODUCTS_RAW = "products_raw.json"
OUTPUT_DETAILS_RAW = "details_raw.json"
OUTPUT_SUMMARY = "summary.json"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
]
