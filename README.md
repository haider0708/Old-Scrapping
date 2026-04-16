# RETAILS — Tunisian E-Commerce Scraper

High-performance scraping system for 21 Tunisian e-commerce websites with automated price-history and availability tracking.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Folder Structure](#folder-structure)
- [Supported Sites](#supported-sites)
- [Setup](#setup)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Output](#data-output)
- [Price-History Tracking](#price-history-tracking)
- [Docker](#docker)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│  pipeline.py  (orchestrator — runs all sites sequentially)      │
│    ├── scrape.py  run_full_scrape()  per site                   │
│    │     ├── Step 1  Download frontpage HTML                    │
│    │     ├── Step 2  Extract category hierarchy                 │
│    │     ├── Step 3  Scrape product listings (concurrent)       │
│    │     └── Step 4  Scrape product details  (batched)          │
│    └── track_history.py  per site (price + availability)        │
└──────────────────────────────────────────────────────────────────┘
```

### Scraper types

| Type | Base class | Transport | When to use |
|------|-----------|-----------|-------------|
| **SSR** | `FastScraper` | httpx + selectolax | Static HTML sites (fastest) |
| **Hybrid** | `FastScraper` + Playwright override | httpx for listings, Playwright for frontpage | JS menus, SSR listings |
| **CSR** | `BaseScraper` | Playwright (Chromium) | Fully JS-rendered sites |

### Scraping workflow (per site)

1. **Download frontpage** — fetch the site's homepage HTML (via httpx or Playwright).
2. **Extract categories** — parse the navigation menu into a 3-level hierarchy: `top → low → subcategory`. Saved to `categories.json`.
3. **Build scrape queue** — flatten the category tree to the deepest available level. Each leaf becomes a queue entry (`CategoryInfo`).
4. **Scrape product listings** — process every queue entry concurrently (bounded by `num_workers` semaphore). For SSR sites, results stream to disk as each category completes via an `on_result` callback; products are buffered in RAM (256 items) and flushed to `products.json`. For CSR sites, Playwright browser contexts are pooled.
5. **Scrape product details** — all product URLs from step 4 are scraped in batches of `DETAIL_BATCH_SIZE` (500). Each batch writes to `products_detailed.json` and then releases memory. Retry logic with exponential backoff applies to every HTTP request.

### Queue and batching details

- **Category queue**: All leaf categories are collected into a flat `List[CategoryInfo]` before scraping starts. A `Semaphore(num_workers)` limits concurrency.
- **Product write buffer**: Products are held in a 256-item RAM buffer and flushed to the open file handle via a single `write()` call when the buffer fills.
- **Detail batching**: Product URLs are split into chunks of 500. After each batch, the results dict is deleted and `gc.collect()` is called, keeping peak RAM proportional to batch size.
- **Per-category page concurrency**: Within a single category, pages 2+ are fetched concurrently with `Semaphore(4)`.
- **Connection pool**: httpx is configured with `max_connections=200`, `max_keepalive_connections=40`, `keepalive_expiry=30s`.

---

## Folder Structure

```
RETAILS/
├── scrape.py               # CLI scraper — test, full, list commands
├── pipeline.py             # Automated pipeline — runs all sites + history
├── track_history.py        # Price / availability / product-change tracking
├── requirements.txt        # Python dependencies
├── Dockerfile              # Container build
├── docker-compose.yml      # Container orchestration
├── .dockerignore           # Docker build exclusions
│
├── configs/
│   ├── pipeline_config.yaml    # Pipeline settings (sites, interval, workers)
│   └── sites/                  # Per-site YAML configs (selectors, base_url)
│       ├── mytek.yaml
│       ├── tunisianet.yaml
│       └── ...                 # 21 YAML files total
│
├── scraper/
│   ├── __init__.py
│   ├── base.py                 # FastScraper, BaseScraper, utilities
│   └── sites/
│       ├── __init__.py         # AVAILABLE_SCRAPERS registry + get_scraper()
│       ├── _template.py        # Template for new scrapers
│       ├── mytek.py
│       ├── tunisianet.py
│       └── ...                 # 21 scraper modules total
│
├── data/                       # All output (gitignored)
│   ├── {site}/
│   │   ├── html/                   # Cached frontpage HTML
│   │   └── YYYY-MM-DD_HH-MM-SS/   # Timestamped scrape run
│   │       ├── categories.json
│   │       ├── products.json
│   │       ├── products_detailed.json
│   │       ├── products_summary.json
│   │       └── products_detailed_summary.json
│   ├── price_history/          # Per-shop price history
│   ├── availability_history/   # Per-shop availability history
│   ├── products_added/         # Per-shop newly added products
│   ├── products_removed/       # Per-shop removed products
│   └── state/                  # Active product ID state files
│
├── logs/                       # Log files (per-site + pipeline)
└── old/                        # Archived unused modules
```

---

## Supported Sites

| # | Site | Module | Type | Platform |
|---|------|--------|------|----------|
| 1 | mytek.tn | `mytek` | CSR | Magento |
| 2 | tunisianet.com | `tunisianet` | SSR | PrestaShop |
| 3 | technopro.tn | `technopro` | SSR | PrestaShop |
| 4 | spacenet.tn | `spacenet` | SSR | PrestaShop |
| 5 | jumbo.tn | `jumbo` | SSR | OpenCart |
| 6 | darty.tn | `darty` | SSR | PrestaShop |
| 7 | graiet.tn | `graiet` | SSR | OpenCart |
| 8 | batam.tn | `batam` | SSR | PrestaShop |
| 9 | zoom.tn | `zoom` | SSR | PrestaShop |
| 10 | allani.tn | `allani` | SSR | PrestaShop |
| 11 | expert-gaming.tn | `expert_gaming` | Hybrid | WooCommerce |
| 12 | geant.tn | `geant` | SSR | PrestaShop |
| 13 | mapara.tn | `mapara` | SSR | PrestaShop |
| 14 | parafendri.tn | `parafendri` | SSR | PrestaShop |
| 15 | parashop.tn | `parashop` | SSR | OpenCart |
| 16 | pharmacie-plus.tn | `pharmacieplus` | CSR | Custom PHP |
| 17 | pharma-shop.tn | `pharmashop` | SSR | PrestaShop |
| 18 | sbs.tn | `sbs` | CSR | PrestaShop |
| 19 | scoop.tn | `scoop` | Hybrid | PrestaShop |
| 20 | skymill.tn | `skymill` | Hybrid | PrestaShop |
| 21 | wiki.tn | `wiki` | Hybrid | WooCommerce |

---

## Setup

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
# Clone or copy the project
cd RETAILS

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for CSR and hybrid sites)
playwright install chromium
```

### Dependencies

| Package | Purpose |
|---------|---------|
| `httpx[http2]` | Async HTTP client with HTTP/2 support |
| `selectolax` | Fast HTML parser (Modest engine) |
| `PyYAML` | YAML config loading |
| `aiofiles` | Async file I/O |
| `ujson` | Fast JSON serialization |
| `tqdm` | Progress bars |
| `playwright` | Browser automation for CSR sites |

---

## Configuration

### Pipeline config — `configs/pipeline_config.yaml`

```yaml
# Sites to scrape (in order)
sites:
  - mytek
  - tunisianet
  # ... all 21 sites

# Interval between full pipeline runs (minutes)
# 720 = 12 hours
interval_minutes: 720

data_dir: "data"

scraping:
  workers: 16           # Parallel category workers
  detail_workers: 16    # Parallel detail workers
```

### Site config — `configs/sites/{site}.yaml`

Each site has a YAML file defining its base URL, scraper settings, and CSS selectors:

```yaml
site_name: "tunisianet"
base_url: "https://www.tunisianet.com.tn"

settings:
  max_retries: 5          # Retry attempts per request
  retry_delay: 2          # Base delay (exponential backoff)
  max_consecutive_failures: 10
  request_timeout: 30     # Seconds

selectors:
  frontpage:
    top_level_blocks: "..."
    low_level_blocks: "..."
    # ...
  products:
    product_card: "..."
    product_name: "..."
    product_price: "..."
    # ...
  pagination:
    next_page: "..."
    # ...
  details:
    title: "..."
    price: "..."
    # ...
```

---

## Usage

### List available sites

```bash
python scrape.py list
```

### Test a single site (quick validation)

Scrapes a limited number of categories and products to verify selectors work:

```bash
# Default: 3 categories, 5 products each
python scrape.py test --site tunisianet

# Custom limits
python scrape.py test --site mytek --categories 5 --products 10

# Filter to a specific top-level category
python scrape.py test --site mytek --category "INFORMATIQUE"

# Test all sites sequentially
python scrape.py test --all-sites
```

### Full scrape of a single site

```bash
# Full scrape with details
python scrape.py full --site tunisianet

# Skip detail scraping (listings only)
python scrape.py full --site tunisianet --no-details

# Custom worker count
python scrape.py full --site tunisianet --workers 32 --detail-workers 32

# Filter to one category
python scrape.py full --site mytek --category "GAMING"
```

### Run the automated pipeline

The pipeline scrapes all configured sites sequentially, then runs price-history tracking for each successful site:

```bash
# Single run (scrape all sites once, then exit)
python pipeline.py run --once

# Continuous mode (repeat every 12 hours, per config)
python pipeline.py run

# Custom interval (every 6 hours)
python pipeline.py run --interval 360

# Scrape only specific sites
python pipeline.py run --once --sites mytek tunisianet spacenet
```

### Run price-history tracking manually

```bash
# Track all shops
python track_history.py

# Track specific shops
python track_history.py --shops mytek tunisianet
```

---

## Data Output

### Per-scrape output (`data/{site}/YYYY-MM-DD_HH-MM-SS/`)

| File | Contents |
|------|----------|
| `categories.json` | Full category hierarchy with URLs and stats |
| `products.json` | All product listings (id, name, price, url, image, categories) |
| `products_detailed.json` | Enriched product data (description, specs, images, availability, SKU) |
| `products_summary.json` | Scrape metadata and statistics |
| `products_detailed_summary.json` | Detail-scraping metadata |

### Product record example (`products_detailed.json`)

```json
{
  "url": "https://www.tunisianet.com.tn/...",
  "shop": "tunisianet",
  "scraped_at": "2026-04-15T10:30:00",
  "top_category": "INFORMATIQUE",
  "low_category": "PC Portable",
  "subcategory": "PC Portable Gamer",
  "product_id": "12345",
  "title": "ASUS ROG Strix G16",
  "price": 3299.0,
  "old_price": 3499.0,
  "brand": "ASUS",
  "sku": "REF-12345",
  "availability": "En stock",
  "available": true,
  "description": "...",
  "specs": {"Processeur": "Intel i7-13700H", "RAM": "16 Go"},
  "images": ["https://...jpg", "https://...jpg"]
}
```

---

## Price-History Tracking

After each scrape, `track_history.py` processes the latest `products_detailed.json` for each shop and updates three tracking systems:

### 1. Price history (`data/price_history/{shop}.json`)

Records a new entry only when the price changes:

```json
{
  "12345": [
    {"price": 3499.0, "date": "2026-04-01T10:00:00"},
    {"price": 3299.0, "date": "2026-04-15T10:30:00"}
  ]
}
```

### 2. Availability history (`data/availability_history/{shop}.json`)

Records a new entry only when availability status changes:

```json
{
  "12345": [
    {"status": "En stock", "available": true, "date": "2026-04-01T10:00:00"},
    {"status": "Rupture de stock", "available": false, "date": "2026-04-15T10:30:00"}
  ]
}
```

### 3. Product changes (`data/products_added/` and `data/products_removed/`)

Tracks which products appear or disappear between consecutive scrapes by comparing current product IDs against a saved state file (`data/state/{shop}_active.json`).

---

## Docker

### Build the image

```bash
docker build -t retails .
```

### Run a single pipeline pass

```bash
docker run --rm -v retails_data:/app/data -v retails_logs:/app/logs retails
```

### Run in continuous mode

```bash
docker run -d --name retails \
  -v retails_data:/app/data \
  -v retails_logs:/app/logs \
  retails python pipeline.py run --interval 720
```

### Run a single-site scrape

```bash
docker run --rm -v retails_data:/app/data retails python scrape.py full --site tunisianet
```

### Run a quick test inside Docker

```bash
docker run --rm retails python scrape.py test --site tunisianet --categories 2 --products 3
```

### docker-compose

The included `docker-compose.yml` provides a ready-to-use setup:

```bash
# Start the pipeline (continuous mode, detached)
docker compose up -d

# View logs
docker compose logs -f

# Run a one-off scrape
docker compose run --rm scraper python scrape.py full --site mytek

# Run tests
docker compose run --rm scraper python scrape.py test --all-sites

# Stop
docker compose down
```

#### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PIPELINE_INTERVAL` | `720` | Minutes between pipeline runs |
| `PIPELINE_WORKERS` | `16` | Parallel category scraping workers |
| `PIPELINE_DETAIL_WORKERS` | `16` | Parallel detail scraping workers |
| `PIPELINE_SITES` | *(all)* | Comma-separated list of sites to scrape |

Example:

```bash
docker compose run -e PIPELINE_SITES="mytek,tunisianet" -e PIPELINE_INTERVAL=360 scraper
```

### Volumes

| Volume | Container path | Purpose |
|--------|---------------|---------|
| `retails_data` | `/app/data` | Scraped products, history, state |
| `retails_logs` | `/app/logs` | Scraper and pipeline log files |

Data persists across container restarts. To back up:

```bash
docker cp retails:/app/data ./backup_data
```

---

## Troubleshooting

### Common issues

| Problem | Cause | Fix |
|---------|-------|-----|
| `playwright._impl._errors.Error: Executable doesn't exist` | Chromium not installed | Run `playwright install chromium` |
| `httpx.ConnectError` on many sites | Rate limiting or network issues | Reduce `workers` in pipeline config |
| Empty `products.json` | Selectors out of date (site redesign) | Check selectors in site YAML config, test with `scrape.py test --site X` |
| High memory usage | Too many concurrent workers | Lower `workers` and `detail_workers` in config |
| `TimeoutError` on CSR sites | Slow page rendering | Increase `page_timeout` in the site YAML config |

### Logs

- Per-site logs: `logs/{site}_{timestamp}.log`
- Pipeline logs: `logs/pipeline_{timestamp}.log`
- Console output includes colored progress bars and step-by-step status.

### Adding a new site

1. Create `configs/sites/{site}.yaml` with base_url and selectors.
2. Create `scraper/sites/{site}.py` extending `FastScraper` or `BaseScraper`.
3. Add entry to `AVAILABLE_SCRAPERS` in `scraper/sites/__init__.py`.
4. Add the site name to `configs/pipeline_config.yaml` under `sites:`.
5. Add the site name to the `SHOPS` list in `track_history.py`.
6. Test: `python scrape.py test --site {site}`
