"""
Configuration for Mytek e-commerce scraper.
Platform: Magento 2 (Rootways Megamenu).
Categories: SSR. Listings + Details: CSR (Playwright BrowserPool).
"""

from pathlib import Path

SHOP_NAME = "mytek"
BASE_URL = "https://www.mytek.tn"

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"

PLAYWRIGHT_TIMEOUT = 20000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_LISTING_WAIT = "div.product-container[data-product-id]"
PLAYWRIGHT_DETAIL_WAIT = "div.product-info-price"
BROWSER_POOL_SIZE = 4

MAX_CONCURRENT_REQUESTS = 4  # lower concurrency for Playwright

URL_PATTERNS = {
    "category_id_from_pagination": r"[?&]id=(\d+)",
    "id_from_url": r"-(\d+)\.html",
    "slug_sanitize": r"[^a-z0-9\-]",
}

CATEGORY_SELECTORS = {
    "nav_container": "ul.vertical-list",
    "top_items": "li.rootverticalnav.category-item",
    "top_name": "a span.main-category-name em",
    "children_container": "div.vertical_fullwidthmenu",
    "low_blocks": "div.title_normal",
    "low_link": "a",
    "sub_lists": "ul.level3-popup, ul.level4-popup",
    "sub_items": "li.category-item > a",
    "sub_name": "span.level3-name, span.level4-name",
    "link_fallback": "a[href]",
}

LISTING_SELECTORS = {
    "element": "div.product-container",
    "id_attr": "data-product-id",
    "name": "h1.product-item-name a.product-item-link",
    "image": "img[id^='seImgProduct_']",
    "image_attrs": ["src"],
    "price": "span.final-price",
    "old_price": "span.original-price",
    "sku_selector": "div.sku",
    "brand_selector": "div.brand a img",
    "brand_attr": "src",
    "availability": {
        "container": "div.availability",
        "status": "div.stock",
    },
}

PAGINATION_SELECTORS = {
    "page_items": "ul.pagination li.page-item",
    "page_link": "a.page-link",
    "disabled_class": "disabled",
}

DETAIL_SELECTORS = {
    "title": "h1.page-title span.base",
    "sku": "div.product.attribute.sku div.value[itemprop='sku']",
    "price": "div.product-info-price span.price",
    "old_price": "span.old-price span.price",
    "special_price": "span.special-price span.price",
    "discount": "span.discount-price",
    "global_availability": "div.product-info-stock-sku div.stock[itemprop='availability']",
    "availability_per_shop": {
        "container": "#block_synchronizestok #shop_container table.tab_retrait_mag",
        "in_stock_class": "enStock",
        "on_order_class": "erpCommande",
        "incoming_class": "erpArivage",
    },
    "description": "#description",
    "specs": {
        "container": "#product-attribute-specs-table",
        "row": "tr",
        "key": "th.col.label",
        "value": "td.col.data",
    },
    "images": {
        "main": "div.product-cover img, div#gallery-container img",
        "main_attrs": ["src"],
        "thumbnails": "div.product-images img.thumb",
    },
}
