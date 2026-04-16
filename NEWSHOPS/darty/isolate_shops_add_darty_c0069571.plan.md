---
name: Isolate shops add Darty
overview: Ensure each shop (allani, batam, darty) is a fully independent project with zero shared structure. Fix hardcoded selectors in existing scrapers so they load everything from their own config, then create the darty shop from the provided selectors.
todos:
  - id: rules
    content: Create .cursor/rules/shop-isolation.mdc and no-hardcoded-selectors.mdc
    status: pending
  - id: allani-config
    content: Flatten allani CATEGORY_SELECTORS, add URL_PATTERNS to allani/config.py
    status: pending
  - id: allani-scraper
    content: Replace 9 hardcoded selectors/regex in allani/scraper.py with config.* references
    status: pending
  - id: batam-config
    content: Add missing config keys to batam/config.py (PLAYWRIGHT_WAIT_SELECTOR, URL_PATTERNS, price_numeric_attr, availability text, specs selectors, link_fallback)
    status: pending
  - id: batam-scraper
    content: Replace 13 hardcoded selectors/regex in batam/scraper.py with config.* references
    status: pending
  - id: darty-config
    content: Create darty/config.py from user-provided YAML selectors
    status: pending
  - id: darty-scraper
    content: Create darty/scraper.py as independent PrestaShop+GloboMegaMenu scraper
    status: pending
isProject: false
---

# Isolate Shops, Remove Hardcodes, Add Darty

Each shop is its own independent project. No shared base, no forced unified config structure, no cross-shop imports. Each shop's `config.py` is shaped by what that specific site needs, and its `scraper.py` reads exclusively from that config.

## What needs fixing

### allani/scraper.py -- 9 hardcoded items

All in [allani/scraper.py](allani/scraper.py), currently NOT using config:

- **Line 177**: regex `r"/(\d+)(?:-|$)"` for ID extraction
- **Line 191**: regex `r"category-(\d+)"` for category ID from `li[id]`
- **Lines 210, 212**: `"ul#top-menu[data-depth='0'] > li.category"`, `"a.dropdown-item[data-depth='0']"`
- **Lines 232, 234**: `"ul[data-depth='1'] > li.category"`, `"a.dropdown-item[data-depth='1']"`
- **Lines 251, 253**: `"ul[data-depth='2'] > li.category"`, `"a.dropdown-item[data-depth='2']"`

The [allani/config.py](allani/config.py) `CATEGORY_SELECTORS` already defines these values -- just not in a shape the scraper actually uses. Restructure the config so the scraper can consume it, then replace all 9 hardcoded strings.

### batam/scraper.py -- 13 hardcoded items

All in [batam/scraper.py](batam/scraper.py), currently NOT using config:

- **Line 187**: regex `r"[^a-z0-9\-]"` for slug sanitize
- **Line 194**: regex `r"-(\d+)\.html"` for product ID
- **Line 215**: `"ul.level-0 > li.parent-ul-list"` in Playwright wait_for_selector
- **Line 236**: `"span.text-left"` for top category name
- **Lines 238, 255, 275**: `"a[href]"` fallback link selector
- **Line 450**: `"data-price-amount"` attribute name
- **Line 455**: `"span.text-green-500"` / `"span.text-blue"` instead of using `config.LISTING_SELECTORS["availability"]["selector"]`
- **Lines 581-583**: `"body"` scope + `"En stock"` literal
- **Lines 593-594**: `"th.col.label"`, `"td.col.label"`, `"td.col.data"` for specs

The [batam/config.py](batam/config.py) already has most of these values defined but the scraper ignores them. Add the missing ones and wire the scraper to use them.

## Step 1 -- Cursor rules

Create two rule files enforcing shop isolation and no-hardcode policy.

`**.cursor/rules/shop-isolation.mdc`** (alwaysApply: true):

- Each shop is a separate, self-contained project under its own folder
- No shared imports, no shared base classes, no cross-shop dependencies
- Each shop has `config.py` + `scraper.py` + `data/`
- Scrapers output raw data only -- no normalization

`**.cursor/rules/no-hardcoded-selectors.mdc**` (globs: `*/scraper.py`):

- All CSS selectors, regex patterns, and scraping-related literals must live in `config.py`
- `scraper.py` reads them via `config.*` -- never inline strings

## Step 2 -- Fix allani/config.py

Restructure `CATEGORY_SELECTORS` from the current nested format into flat keys the scraper can directly use. Add `URL_PATTERNS` for the two regex patterns. No other sections change (listings, pagination, detail already work via config).

```python
CATEGORY_SELECTORS = {
    "top_items": "ul#top-menu[data-depth='0'] > li.category",
    "top_link": "a.dropdown-item[data-depth='0']",
    "low_items": "ul[data-depth='1'] > li.category",
    "low_link": "a.dropdown-item[data-depth='1']",
    "sub_items": "ul[data-depth='2'] > li.category",
    "sub_link": "a.dropdown-item[data-depth='2']",
}

URL_PATTERNS = {
    "id_from_url": r"/(\d+)(?:-|$)",
    "category_id_from_li": r"category-(\d+)",
}
```

## Step 3 -- Fix allani/scraper.py

- `_extract_id_from_url()`: use `config.URL_PATTERNS["id_from_url"]`
- `extract_category_id_from_li()`: use `config.URL_PATTERNS["category_id_from_li"]`
- `scrape_categories()`: replace 6 hardcoded CSS selectors with `config.CATEGORY_SELECTORS[...]`

## Step 4 -- Fix batam/config.py

Add missing config entries for the 13 hardcoded values:

```python
PLAYWRIGHT_WAIT_SELECTOR = "ul.level-0 > li.parent-ul-list"

CATEGORY_SELECTORS = {
    ...existing keys...,
    "top_name": "span.text-left",
    "link_fallback": "a[href]",
}

URL_PATTERNS = {
    "id_from_url": r"-(\d+)\.html",
    "slug_sanitize": r"[^a-z0-9\-]",
}
```

In `LISTING_SELECTORS`, add `"price_numeric_attr": "data-price-amount"`.

In `DETAIL_SELECTORS`, add `"availability_in_stock_text": "En stock"`, `"availability_fallback_scope": "body"`, and ensure `specs.key` / `specs.value` are present.

## Step 5 -- Fix batam/scraper.py

Replace all 13 hardcoded items with their `config.*` equivalents.

## Step 6 -- Create darty/config.py

Standalone config shaped by Darty's PrestaShop + GloboMegaMenu structure. Directly translates the user-provided YAML selectors into Python dicts. Key sections:

- `BASE_URL`, `PLAYWRIGHT_*` (None -- SSR)
- `CATEGORY_SELECTORS` -- GloboMegaMenu: `top_items`, `top_link`, `top_name`, `top_id_attr`, `low_items`, `low_link`, `sub_items`, `sub_link`
- `URL_PATTERNS` -- PrestaShop ID regex
- `LISTING_SELECTORS` -- element, id (article attr), name, url, image + variants, price (attr-based), category, features, availability (schema + cart button)
- `PAGINATION_SELECTORS` -- next_page, load_more_button, page_list
- `DETAIL_SELECTORS` -- title + title_parts, brand (container + logo), price, old_price, savings, promo_flag, global_availability, availability_per_shop (container/row/name/status), images (main + zoom + slider), features_short, specs (dl-based), installment, schema_availability

## Step 7 -- Create darty/scraper.py

Independent scraper. Same overall flow as allani (both PrestaShop SSR), but all logic reads from darty's own config. Key adaptations:

- Categories: GloboMegaMenu uses `data-id` attribute for category IDs (not URL-based)
- Listings: product ID from `article[data-id-product]` attribute; price from `span[content]` attribute; availability from schema link + cart button status
- Details: title_parts (category + name spans), per-shop availability table, installment section, image zoom/slider
- All queue/diff/patch/history/summary logic is self-contained

## Files touched


| File                                       | Action                                             |
| ------------------------------------------ | -------------------------------------------------- |
| `.cursor/rules/shop-isolation.mdc`         | Create                                             |
| `.cursor/rules/no-hardcoded-selectors.mdc` | Create                                             |
| `allani/config.py`                         | Edit: flatten CATEGORY_SELECTORS, add URL_PATTERNS |
| `allani/scraper.py`                        | Edit: replace 9 hardcoded items with config refs   |
| `batam/config.py`                          | Edit: add missing keys for 13 hardcoded values     |
| `batam/scraper.py`                         | Edit: replace 13 hardcoded items with config refs  |
| `darty/__init__.py`                        | Create (empty)                                     |
| `darty/config.py`                          | Create                                             |
| `darty/scraper.py`                         | Create                                             |


