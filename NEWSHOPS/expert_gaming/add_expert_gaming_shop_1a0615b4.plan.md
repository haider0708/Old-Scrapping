---
name: Add Expert Gaming shop
overview: Create a new `expert_gaming/` folder with `config.py` and `scraper.py` for the Expert Gaming WooCommerce shop. Playwright for CSR category extraction, httpx+selectolax for SSR listings/details -- same architecture as the batam scraper.
todos:
  - id: eg-config
    content: Create expert_gaming/config.py with WooCommerce+Elementor selectors from user YAML
    status: completed
  - id: eg-scraper
    content: "Create expert_gaming/scraper.py: Playwright for CSR categories, httpx+selectolax for WooCommerce listings/details"
    status: completed
isProject: false
---

# Add Expert Gaming Shop Scraper

New shop: `expert_gaming/` following the same isolated-shop rules as allani, batam, darty. CSR homepage (Playwright for categories), SSR listings and details (httpx + selectolax).

## Key differences from batam

- **Platform**: WooCommerce + Elementor + YITH (not Magento)
- **Categories**: Vertical mega menu (`ul#menu-notre-boutique`), 3 levels with different selector patterns per level. Category IDs extracted from `li[id]` attribute (`menu-item-{id}`)
- **Listings**: `section.product[data-product_id]` -- availability is CSS-class-based (`instock`/`outofstock` class on the element), not text. Has categories and brands per product. SKU from cart button `data-product_sku`
- **Pagination**: WooCommerce `/page/{n}/` URL pattern (not query string)
- **Details**: WooCommerce gallery with `data-thumb`, two specs sources (table + alt `ts-dimensions-content`), tabs structure, `data-original`/`data-class` on availability

## Files to create

### `expert_gaming/config.py`

Translate the user-provided YAML selectors directly:

- `BASE_URL = "https://expert-gaming.tn"`
- `PLAYWRIGHT_TIMEOUT = 15000`, `PLAYWRIGHT_HEADLESS = True`
- `PLAYWRIGHT_WAIT_SELECTOR = "ul#menu-notre-boutique > li.menu-item > a"` (wait for mega menu hydration)
- `CATEGORY_SELECTORS` -- shaped for the WooCommerce+Elementor mega menu:
  - `top_items`: `ul#menu-notre-boutique > li.menu-item`
  - `top_link`: `> a` (direct child link)
  - `top_name`: `a > span.menu-label`
  - `top_id_attr`: `id` (then regex `menu-item-(\d+)`)
  - `low_items`: two selector patterns (`div.ts-list-of-product-categories-wrapper h3.heading-title a` and `div.elementor-heading-title a`)
  - `sub_items`: `div.ts-list-of-product-categories-wrapper ul > li`
  - `sub_link`: `a`
- `URL_PATTERNS` -- `id_from_url` for WooCommerce (slug-based, no numeric ID in URL -- use `data-product_id` instead), `category_id_from_li` regex `menu-item-(\d+)`
- `LISTING_SELECTORS` -- element, id from `data-product_id` attr, price/old_price/sale_price, availability via CSS class check (`instock`/`outofstock`), categories, brands, SKU from cart button
- `PAGINATION_SELECTORS` -- WooCommerce `/page/{n}/` pattern
- `DETAIL_SELECTORS` -- title, brand, SKU, price/old_price/sale_price, availability (text + data attrs), description, two specs sources (table + alt), images (main + gallery `data-thumb` + thumbnails), tabs

Standard retry/delay/concurrency/httpx/paths/UA/header sections (same values as other shops).

### `expert_gaming/scraper.py`

Based on [batam/scraper.py](batam/scraper.py) architecture (Playwright categories + httpx SSR), adapted for WooCommerce:

- **Categories (Playwright)**: Launch browser, navigate to `BASE_URL`, wait for mega menu, extract rendered HTML. Parse top items from `ul#menu-notre-boutique > li.menu-item`, extract ID from `li[id]` via config regex. Low categories come from elementor heading links inside sub-menus. Sub categories from `ts-list-of-product-categories-wrapper ul > li > a`
- **Listings (httpx)**: Product ID from `section.product[data-product_id]`. Availability from CSS class on the element (`instock`/`outofstock`) -- check `class` attribute. Price from `bdi` elements. Categories and brands as arrays. SKU from cart button `data-product_sku`
- **Pagination**: Follow `a.next.page-numbers` href, stop when absent
- **Details (httpx)**: Title, brand, SKU, price triplet (regular/old/sale), availability text + data attrs, description, specs from table + alt specs from `ts-dimensions-content`, images from gallery + thumbnails
- **Queue/diff/patch/history/summary/cleanup**: Same self-contained logic as all other shops

## Project structure

```
expert_gaming/
    __init__.py
    config.py
    scraper.py
    data/          (created at runtime)
```

Run with: `python -m expert_gaming.scraper`
