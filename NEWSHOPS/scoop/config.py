"""
Configuration for Scoop Gaming e-commerce scraper.
All selectors and configuration. Platform: PrestaShop + TvCMS MegaMenu.
CSR homepage (Playwright for categories), SSR listings/details.
"""

from pathlib import Path

# -----------------------------------------------------------------------------
# Base URL
# -----------------------------------------------------------------------------
BASE_URL = "https://www.scoopgaming.com.tn"

# -----------------------------------------------------------------------------
# Playwright settings (for CSR category extraction)
# -----------------------------------------------------------------------------
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "div#tvdesktop-megamenu ul.menu-content > li.level-1 > a"

# -----------------------------------------------------------------------------
# CSS Selectors - TvCMS MegaMenu (level classes + two structural patterns)
# -----------------------------------------------------------------------------
CATEGORY_SELECTORS = {
    "nav_container": "div#tvdesktop-megamenu ul.menu-content",
    "top_items": "ul.menu-content > li.level-1",
    "top_link": "a",
    "top_name_span": "a > span",
    "top_name_img_alt": "a > img",
    "low_items_dropdown": "ul.menu-dropdown > li.level-2 > a",
    "sub_items_dropdown": "li.level-2.parent > ul.menu-dropdown > li.level-3 > a",
    "low_items_mega": "div.menu-dropdown li.tvmega-menu-link.item-header > a",
    "sub_items_mega": "div.menu-dropdown li.tvmega-menu-link.item-line > a",
    "link_fallback": "a[href]",
}

# -----------------------------------------------------------------------------
# URL patterns
# -----------------------------------------------------------------------------
URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "slug_sanitize": r"[^a-z0-9\-]",
}

# -----------------------------------------------------------------------------
# Listing selectors - PrestaShop TvCMS (scope to .tvproduct-wrapper.grid)
# -----------------------------------------------------------------------------
LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": None,
    "id_attr": "data-id-product",
    "grid_scope": ".tvproduct-wrapper.grid",
    "name": "h6[itemprop='name']",
    "name_alt": "div.tvproduct-name.product-title a h6",
    "url": "div.tvproduct-name.product-title a",
    "image": "img.tvproduct-defult-img.tv-img-responsive",
    "image_attrs": ["src"],
    "price": ".product-price-and-shipping span.price",
    "old_price": ".product-price-and-shipping span.regular-price",
    "category_name": "div.tvproduct-cat-name",
    "availability": {
        "out_of_stock_button": "button.tvproduct-out-of-stock.disable[disabled]",
        "in_stock_button": "button.add-to-cart:not(.disable):not([disabled])",
        "catalog_view_oos": "div.outofstock-category",
        "catalog_view_in_stock": "div.disponible-category",
    },
}

# -----------------------------------------------------------------------------
# Pagination selectors
# -----------------------------------------------------------------------------
PAGINATION_SELECTORS = {
    "container": "nav.pagination.tvcms-all-pagination",
    "result_count": "div.tv-pagination-content",
    "page_list": "ul.page-list.tv-pagination-wrapper a.js-search-link",
    "current_page": "li.current a.disabled",
    "next_page": "a.next.js-search-link[rel='next']",
    "url_pattern": "?page={n}",
}

# -----------------------------------------------------------------------------
# Detail selectors
# -----------------------------------------------------------------------------
DETAIL_SELECTORS = {
    "title": "h1.h1[itemprop='name']",
    "breadcrumbs": None,
    "brand": "a.tvproduct-brand img",
    "brand_attr": "src",
    "reference": "div.product-reference span[itemprop='sku']",
    "price": "div.current-price span.price[itemprop='price']",
    "price_content_attr": "content",
    "old_price": "div.product-discount span.regular-price",
    "global_availability": "span#product-availability",
    "availability_schema": "link[itemprop='availability'][href]",
    "description_fallback": "div[id^='product-description-short-']",
    "full_description": "div.tab-pane#description div.product-description",
    "specs": {
        "container": "div.product-features dl.data-sheet",
        "key": "dt.name",
        "value": "dd.value",
    },
    "images": {
        "main": "div.tvproduct-image-slider img[itemprop='image']",
        "main_attrs": ["src"],
        "thumbnails": "img.thumb.js-thumb",
    },
    "json_data": "#product-details[data-product]",
    "json_data_attr": "data-product",
}

# -----------------------------------------------------------------------------
# Retry settings
# -----------------------------------------------------------------------------
MAX_RETRIES = 3
BACKOFF_BASE = 2
BACKOFF_MAX = 30

# -----------------------------------------------------------------------------
# Delay settings
# -----------------------------------------------------------------------------
MIN_DELAY = 1.0
MAX_DELAY = 3.0

# -----------------------------------------------------------------------------
# Concurrency limits
# -----------------------------------------------------------------------------
MAX_CONCURRENT_REQUESTS = 8
PROCESS_POOL_SIZE = 2

# -----------------------------------------------------------------------------
# httpx tuning
# -----------------------------------------------------------------------------
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 30
POOL_MAX_CONNECTIONS = 20
POOL_MAX_KEEPALIVE = 5

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

# -----------------------------------------------------------------------------
# User-Agent rotation
# -----------------------------------------------------------------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

# -----------------------------------------------------------------------------
# Header fingerprint templates
# -----------------------------------------------------------------------------
HEADER_TEMPLATES = [
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "fr,fr-FR;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    },
]
