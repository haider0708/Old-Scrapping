"""
Configuration for Batam e-commerce scraper.
Shop-specific selectors, URL, and overrides only.
Platform: Magento 2 (Hyva + Alpine.js + Tailwind).
"""

from pathlib import Path

SHOP_NAME = "batam"
BASE_URL = "https://batam.com.tn"

SHOP_DIR = Path(__file__).resolve().parent
DATA_DIR = SHOP_DIR / "data"

# Playwright for CSR category extraction only
PLAYWRIGHT_TIMEOUT = 15000
PLAYWRIGHT_HEADLESS = True
PLAYWRIGHT_WAIT_SELECTOR = "ul.level-0 > li.parent-ul-list"

URL_PATTERNS = {
    "id_from_url": r"-(\d+)\.html",
    "slug_sanitize": r"[^a-z0-9\-]",
}

CATEGORY_SELECTORS = {
    "top_block": "ul.level-0 > li.parent-ul-list",
    "top_name": "span.text-left",
    "low_block": "ul.level-1 > li",
    "low_link": "ul.level-1 > li a",
    "sub_block": "ul.level-2 > li",
    "sub_link": "ul.level-2 > li a",
    "link_fallback": "a[href]",
}

LISTING_SELECTORS = {
    "element": "form.item.product.product-item.product_addtocart_form",
    "id_selector": "input[name='product']",
    "id_attr": "value",
    "name": "a.product-item-link",
    "image": "a.product.photo.product-item-photo img.product-image-photo",
    "image_attrs": ["src"],
    "price": "span[data-price-type='finalPrice'] span.price",
    "price_numeric_selector": "span[data-price-type='finalPrice'][data-price-amount]",
    "price_numeric_attr": "data-price-amount",
    "old_price": "span[data-price-type='oldPrice'] span.price",
    "availability": {
        "selector": "span.text-green-500, span.text-blue",
    },
}

PAGINATION_SELECTOR_NEXT = "li.pages-item-next a.action.next"

DETAIL_SELECTORS = {
    "title": "h1.page-title span.base[itemprop='name']",
    "reference_selector": "input[name='product']",
    "reference_attr": "value",
    "price": "div.price-container .final-price .price",
    "price_numeric_selector": "meta[itemprop='price']",
    "price_numeric_attr": "content",
    "old_price": "div.price-container .old-price .price",
    "global_availability": "p.unavailable.stock span",
    "availability_in_stock_text": "En stock",
    "availability_fallback_scope": "body",
    "description": "div.product-description",
    "specs": {
        "container": "#product-attribute-specs-table, table.additional-attributes",
        "row": "tr",
        "key": "th.col.label, td.col.label",
        "value": "td.col.data",
    },
    "images": {
        "main": "div#gallery img",
        "main_attrs": ["src"],
    },
}
