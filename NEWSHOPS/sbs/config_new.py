"""SBS — Shop-specific config. PrestaShop + TvCMS MegaMenu. Full CSR (BrowserPool)."""
from pathlib import Path

BASE_URL = "https://www.sbsinformatique.com"
PLAYWRIGHT_TIMEOUT = 30000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_CATEGORY_WAIT = "div.block-categories ul.category-top-menu"
PLAYWRIGHT_LISTING_WAIT = "article.product-miniature.js-product-miniature"
PLAYWRIGHT_DETAIL_WAIT = "div.current-price span.price"
BROWSER_POOL_SIZE = 4

CATEGORY_SELECTORS = {
    "nav_container": "div.block-categories ul.category-top-menu",
    "top_items": "li[data-depth='0'] > a",
    "low_items": "li[data-depth='1'] > a.category-sub-link",
    "sub_items": "li[data-depth='2'] > a.category-sub-link, li[data-depth='3'] > a.category-sub-link",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {"id_from_url": r"/(\d+)(?:-|$)", "slug_sanitize": r"[^a-z0-9\-]"}

LISTING_SELECTORS = {
    "element": "article.product-miniature.js-product-miniature",
    "id": None, "id_attr": "data-id-product",
    "grid_scope": ".tvproduct-wrapper.grid",
    "name": "h6[itemprop='name']", "name_alt": "div.tvproduct-name.product-title a h6",
    "url": "div.tvproduct-name.product-title a",
    "image": "img.tvproduct-defult-img.tv-img-responsive", "image_attrs": ["src"],
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

PAGINATION_SELECTORS = {"next_page": "a.next.js-search-link[rel='next']"}

DETAIL_SELECTORS = {
    "title": "h1.h1[itemprop='name']",
    "brand": "a.tvproduct-brand img", "brand_attr": "src",
    "reference": "div.product-reference span[itemprop='sku']",
    "price": "div.current-price span.price[itemprop='price']", "price_content_attr": "content",
    "old_price": "div.product-discount span.regular-price",
    "global_availability": "span#product-availability",
    "availability_schema": "link[itemprop='availability'][href]",
    "stock_bar": "div.dispo-haut-bar div.tv-inner",
    "stock_bar_classes": ["tv-lvl-0", "tv-lvl-1", "tv-lvl-2", "tv-lvl-3", "tv-lvl-4"],
    "description_fallback": "div[id^='product-description-short-']",
    "full_description": "div.tab-pane#description div.product-description",
    "specs": {"container": "div.product-features dl.data-sheet", "key": "dt.name", "value": "dd.value"},
    "images": {"main": "div.tvproduct-image-slider img[itemprop='image']", "main_attrs": ["src"], "thumbnails": "img.thumb.js-thumb"},
    "json_data": "#product-details[data-product]", "json_data_attr": "data-product",
}

MAX_CONCURRENT_REQUESTS = 4

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"
