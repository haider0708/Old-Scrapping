#!/usr/bin/env python3
"""
Base scraper classes and utilities.
All site-specific scrapers inherit from these base classes.

Features:
- Robust error handling with exponential backoff
- Comprehensive logging
- Configurable timeouts and retries
- Date-based data organization
"""
import asyncio
import json
import logging
import os
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urljoin, urlparse

import httpx
import yaml
from selectolax.parser import HTMLParser
from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from scraper.stealth import random_headers, random_ua, random_delay


# === Configuration ===
BASE_DIR = Path(__file__).parent.parent
CONFIGS_DIR = BASE_DIR / "configs" / "sites"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"

# Default settings (can be overridden in config)
DEFAULT_MAX_RETRIES = 5
DEFAULT_RETRY_DELAY = 2
DEFAULT_MAX_CONSECUTIVE_FAILURES = 10
DEFAULT_PAGE_TIMEOUT = 60000
DEFAULT_WAIT_AFTER_LOAD = 2
DEFAULT_REQUEST_TIMEOUT = 30


def _is_docker() -> bool:
    """Return True when running inside a Docker container."""
    return Path("/.dockerenv").exists() or os.environ.get("DOCKER_CONTAINER") == "1"


def playwright_launch_args(extra: list | None = None) -> list:
    """Return Chromium launch args, adding --no-sandbox when inside Docker.

    Use this helper in every chromium.launch() call so all scrapers
    automatically work in containers without changing individual files.
    """
    args = ["--disable-blink-features=AutomationControlled"]
    if _is_docker():
        # Chromium requires --no-sandbox when the Linux kernel
        # user-namespace creation is restricted (common in containers).
        args += ["--no-sandbox", "--disable-setuid-sandbox"]
    if extra:
        args += [a for a in extra if a not in args]
    return args


# === Tor IP Rotation (Multi-Instance Pool) ===
USE_TOR = os.environ.get("USE_TOR", "0") == "1"
TOR_SOCKS_PORT = int(os.environ.get("TOR_SOCKS_PORT", "9050"))
TOR_CONTROL_PORT = int(os.environ.get("TOR_CONTROL_PORT", "9051"))
TOR_PASSWORD = os.environ.get("TOR_PASSWORD", "retails")
TOR_INSTANCES = int(os.environ.get("TOR_INSTANCES", "8"))
TOR_ROTATE_EVERY = int(os.environ.get("TOR_ROTATE_EVERY", "50"))


class TorPool:
    """Pool of N Tor SOCKS5 proxies for parallel anonymous scraping.

    Each Tor daemon runs on its own SOCKS/control port pair (spaced by 2):
        Instance 0  →  SOCKS 9050, Control 9051
        Instance 1  →  SOCKS 9052, Control 9053
        ...
    Workers are round-robin assigned to instances so concurrent requests
    exit through different IPs.  Every TOR_ROTATE_EVERY requests the
    instance's circuit is rotated via NEWNYM.

    Per-site control: call ``activate(True/False)`` before scraping each
    site.  When deactivated, proxy helpers return None (direct connection).
    """

    _instance: Optional["TorPool"] = None

    def __init__(self):
        self.size = TOR_INSTANCES if USE_TOR else 0
        self._counter = 0
        self._lock = asyncio.Lock()
        self._req_counts = [0] * max(self.size, 1)
        self._active = False  # per-site toggle

    @classmethod
    def get(cls) -> "TorPool":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def activate(self, on: bool):
        """Enable/disable Tor for the current site."""
        self._active = on and USE_TOR and self.size > 0

    @property
    def active(self) -> bool:
        return self._active

    def socks_port(self, slot: int) -> int:
        return TOR_SOCKS_PORT + (slot % self.size) * 2

    def control_port(self, slot: int) -> int:
        return TOR_CONTROL_PORT + (slot % self.size) * 2

    def proxy_url(self, slot: int) -> Optional[str]:
        if not self._active:
            return None
        return f"socks5://127.0.0.1:{self.socks_port(slot)}"

    def pw_proxy(self, slot: int) -> Optional[dict]:
        if not self._active:
            return None
        return {"server": f"socks5://127.0.0.1:{self.socks_port(slot)}"}

    async def next_slot(self) -> int:
        async with self._lock:
            slot = self._counter % max(self.size, 1)
            self._counter += 1
        return slot

    async def track_request(self, slot: int, logger: logging.Logger = None):
        """Increment counter for *slot*; rotate its circuit at threshold."""
        if not self._active:
            return
        idx = slot % self.size
        self._req_counts[idx] += 1
        if self._req_counts[idx] >= TOR_ROTATE_EVERY:
            self._req_counts[idx] = 0
            await self._send_newnym(idx, logger)

    async def rotate_all(self, logger: logging.Logger = None):
        """Rotate every Tor instance to a fresh circuit."""
        if not USE_TOR or self.size == 0:
            return
        for i in range(self.size):
            await self._send_newnym(i, logger)
        if logger:
            logger.info(f"\U0001f504 All {self.size} Tor circuits rotated")
        await asyncio.sleep(5)

    async def _send_newnym(self, idx: int, logger: logging.Logger = None):
        import socket as _socket
        port = self.control_port(idx)
        try:
            with _socket.create_connection(("127.0.0.1", port), timeout=10) as sock:
                sock.recv(1024)
                sock.sendall(f'AUTHENTICATE "{TOR_PASSWORD}"\r\n'.encode())
                resp = sock.recv(1024).decode()
                if "250" not in resp:
                    raise RuntimeError(f"Tor auth failed on port {port}: {resp.strip()}")
                sock.sendall(b"SIGNAL NEWNYM\r\n")
                resp = sock.recv(1024).decode()
                if "250" not in resp:
                    raise RuntimeError(f"NEWNYM failed on port {port}: {resp.strip()}")
                sock.sendall(b"QUIT\r\n")
            if logger:
                logger.debug(f"Tor instance {idx} (:{port}) rotated")
        except Exception as e:
            if logger:
                logger.warning(f"Tor rotation failed for instance {idx}: {e}")


# ── Thin wrappers kept for backwards compatibility with site scrapers ─
def get_tor_proxy_url() -> Optional[str]:
    """Return a SOCKS5 proxy URL (slot 0) if Tor is active for current site."""
    return TorPool.get().proxy_url(0)


def get_playwright_proxy() -> Optional[dict]:
    """Return Playwright proxy dict (slot 0) if Tor is active for current site."""
    return TorPool.get().pw_proxy(0)


async def rotate_tor_ip(logger: logging.Logger = None):
    """Rotate all Tor instances — called between sites by pipeline."""
    await TorPool.get().rotate_all(logger)


@dataclass
class ScrapeStats:
    """Track scraping statistics."""
    site: str = ""
    start_time: str = ""
    end_time: str = ""
    duration_seconds: float = 0
    total_categories: int = 0
    categories_scraped: int = 0
    categories_skipped: int = 0
    categories_failed: int = 0
    total_products: int = 0
    total_pages: int = 0
    retries_total: int = 0
    workers_used: int = 1
    errors: List[Dict] = field(default_factory=list)
    skipped: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CategoryInfo:
    """Information about a category to scrape."""
    url: str
    name: str
    location: Tuple[int, ...]  # Index path in hierarchy
    level: str  # 'top', 'low', 'subcategory'
    parent_names: List[str] = field(default_factory=list)


@dataclass 
class ProductInfo:
    """Basic product information."""
    id: Optional[str] = None
    url: Optional[str] = None
    title: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)


class RetryConfig:
    """Configuration for retry behavior with exponential backoff."""
    
    def __init__(
        self,
        max_retries: int = DEFAULT_MAX_RETRIES,
        base_delay: float = DEFAULT_RETRY_DELAY,
        max_delay: float = 60,
        exponential_base: float = 2,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter."""
        delay = min(
            self.base_delay * (self.exponential_base ** (attempt - 1)),
            self.max_delay
        )
        if self.jitter:
            delay *= (0.5 + random.random())
        return delay


# === Utility Functions ===

def load_site_config(site_name: str) -> dict:
    """Load site-specific YAML configuration."""
    config_path = CONFIGS_DIR / f"{site_name}.yaml"
    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_date_folder() -> str:
    """Get current date+timestamp as folder name (YYYY-MM-DD_HH-MM-SS) for time series tracking."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def save_json(data: dict, path: Path, logger: logging.Logger = None):
    """Save data to JSON file with atomic write."""
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file first, then rename (atomic)
    temp_path = path.with_suffix('.json.tmp')
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(str(temp_path), str(path))
        if logger:
            logger.info(f"✓ Saved: {path}")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise


def load_json(path: Path) -> dict:
    """Load JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_jsonl(data: List[dict], path: Path, logger: logging.Logger = None):
    """Save data to JSON Stream file with atomic write."""
    import os
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temp file first, then rename (atomic)
    temp_path = path.with_suffix('.jsonl.tmp')
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            for item in data:
                # Write pretty-printed object followed by a newline
                f.write(json.dumps(item, ensure_ascii=False, indent=2) + "\n")
        os.replace(str(temp_path), str(path))
        if logger:
            logger.info(f"✓ Saved: {path}")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise


def load_jsonl(path: Path) -> List[dict]:
    """Load JSON Stream file (NDJSON or Pretty Stream)."""
    data = []
    if not path.exists():
        return data
        
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        decoder = json.JSONDecoder()
        pos = 0
        length = len(content)
        
        while pos < length:
            # Skip whitespace
            while pos < length and content[pos].isspace():
                pos += 1
            
            if pos >= length:
                break
                
            obj, end = decoder.raw_decode(content, idx=pos)
            data.append(obj)
            pos = end
            
    except Exception as e:
        # Fallback to line-based parsing if raw_decode fails totally
        # (Though raw_decode is usually superior)
        if hasattr(path, "name") and logger: 
             # logger might not be available here directly if passed as None, but standard logging is imported
             logging.getLogger(__name__).warning(f"Stream parsing failed for {path}: {e}")
        return []

    return data


def format_duration(seconds: float) -> str:
    """Format duration nicely."""
    if seconds < 0:
        return "0s"
    td = timedelta(seconds=int(seconds))
    parts = []
    hours, remainder = divmod(td.seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if td.days:
        parts.append(f"{td.days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


async def retry_async(
    func,
    retry_config: RetryConfig,
    logger: logging.Logger = None,
    operation_name: str = "operation"
):
    """
    Execute async function with retry logic.
    
    Args:
        func: Async callable to execute
        retry_config: Retry configuration
        logger: Logger for debug messages
        operation_name: Name for logging
        
    Returns:
        Result of func
        
    Raises:
        Last exception if all retries fail
    """
    last_exception = None
    
    for attempt in range(1, retry_config.max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < retry_config.max_retries:
                delay = retry_config.get_delay(attempt)
                if logger:
                    logger.debug(
                        f"  {operation_name} attempt {attempt}/{retry_config.max_retries} "
                        f"failed: {e}. Retrying in {delay:.1f}s..."
                    )
                await asyncio.sleep(delay)
            else:
                if logger:
                    logger.warning(
                        f"  {operation_name} failed after {retry_config.max_retries} attempts: {e}"
                    )
    
    raise last_exception


class BaseScraper(ABC):
    """
    Abstract base class for Playwright-based scrapers.
    Use this for sites that require JavaScript rendering (e.g., Mytek).
    """
    
    def __init__(self, site_name: str, logger: logging.Logger):
        self.site_name = site_name
        self.logger = logger
        self.config = load_site_config(site_name)
        
        # Load settings from config or use defaults
        settings = self.config.get("settings", {})
        self.retry_config = RetryConfig(
            max_retries=settings.get("max_retries", DEFAULT_MAX_RETRIES),
            base_delay=settings.get("retry_delay", DEFAULT_RETRY_DELAY),
        )
        self.max_consecutive_failures = settings.get(
            "max_consecutive_failures", DEFAULT_MAX_CONSECUTIVE_FAILURES
        )
        self.page_timeout = settings.get("page_timeout", DEFAULT_PAGE_TIMEOUT)
        self.wait_after_load = settings.get("wait_after_load", DEFAULT_WAIT_AFTER_LOAD)
        self.request_timeout = settings.get("request_timeout", DEFAULT_REQUEST_TIMEOUT)
        
        # For backwards compatibility
        self.max_retries = self.retry_config.max_retries
        self.retry_delay = self.retry_config.base_delay
        
        # Base data directory (not date-specific)
        self._base_data_dir = DATA_DIR / site_name
        self._base_data_dir.mkdir(parents=True, exist_ok=True)
        self._current_data_dir = None  # Can be set to use specific folder
    
    @property
    def data_dir(self) -> Path:
        """Get date-specific data directory."""
        # If _current_data_dir is set (from scrape_product_details), use it
        if self._current_data_dir:
            return self._current_data_dir
        date_dir = self._base_data_dir / get_date_folder()
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    @property
    def html_dir(self) -> Path:
        """Get HTML storage directory (not date-specific)."""
        html_dir = self._base_data_dir / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        return html_dir
    
    @property
    def base_url(self) -> str:
        return self.config.get("base_url", f"https://www.{self.site_name}.tn")
    
    @property
    def selectors(self) -> dict:
        return self.config.get("selectors", {})
    
    # === Abstract Methods ===
    
    @abstractmethod
    def extract_categories_from_html(self, html: str) -> dict:
        """Parse the frontpage HTML and extract category hierarchy."""
        pass
    
    @abstractmethod
    async def extract_products_from_page(self, page: Page) -> List[dict]:
        """Extract product data from a loaded category page."""
        pass
    
    @abstractmethod
    async def extract_pagination_info(self, page: Page) -> dict:
        """Extract pagination information from category page."""
        pass
    
    @abstractmethod
    def build_page_url(self, base_url: str, page_num: int) -> str:
        """Build URL for a specific page number."""
        pass
    
    @abstractmethod
    def get_wait_selector(self) -> str:
        """Return CSS selector to wait for after page load."""
        pass
    
    # === Implemented Methods ===
    
    async def download_frontpage(self) -> Path:
        """Download frontpage HTML with retry logic."""
        output_path = self.html_dir / "frontpage.html"
        
        headers = random_headers()
        
        self.logger.info(f"📥 Downloading: {self.base_url}")
        
        # Create the client once outside the retry closure so the same TCP
        # connection is reused across retries rather than reconnecting each time.
        pool = TorPool.get()
        slot = await pool.next_slot() if pool.active else 0
        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=self.request_timeout,
            proxy=pool.proxy_url(slot),
        ) as client:
            async def fetch():
                response = await client.get(self.base_url)
                response.raise_for_status()
                return response.text

            html = await retry_async(
                fetch,
                self.retry_config,
                self.logger,
                "Download frontpage"
            )
        
        output_path.write_text(html, encoding="utf-8")
        self.logger.info(f"✓ Saved: {output_path} ({len(html):,} bytes)")
        return output_path
    
    def extract_categories(self) -> Path:
        """Extract categories from downloaded frontpage."""
        html_path = self.html_dir / "frontpage.html"
        output_path = self.data_dir / "categories.json"
        
        if not html_path.exists():
            raise FileNotFoundError(f"Frontpage not found: {html_path}")
        
        self.logger.info(f"📂 Extracting categories from: {html_path}")
        
        html = html_path.read_text(encoding="utf-8")
        data = self.extract_categories_from_html(html)
        
        # Add metadata
        data["site"] = self.site_name
        data["shop"] = self.site_name  # Alias for consistency
        data["base_url"] = self.base_url
        data["extracted_at"] = datetime.now().isoformat()
        data["date"] = get_date_folder()
        
        
        save_json(data, output_path, self.logger)
        
        stats = data.get("stats", {})
        self.logger.info(f"  Categories: {stats}")
        
        return output_path
    
    def build_scrape_queue(self, categories_data: dict) -> List[CategoryInfo]:
        """Build flat list of categories to scrape from hierarchy.

        Fallback hierarchy:
        1. Subcategories (if they exist)
        2. Low categories (if no subcategories)
        3. Top categories (if no low categories)
        """
        queue = []
        
        for top_idx, top in enumerate(categories_data.get("categories", [])):
            top_name = top.get("name", "")
            has_low_categories = bool(top.get("low_level_categories"))
            
            if has_low_categories:
                # Process low-level categories
                for low_idx, low in enumerate(top["low_level_categories"]):
                    low_name = low.get("name", "")
                    has_subcategories = bool(low.get("subcategories"))

                    if has_subcategories:
                        # Add all subcategories
                        for sub_idx, sub in enumerate(low["subcategories"]):
                            if sub.get("url"):
                                queue.append(CategoryInfo(
                                url=sub["url"],
                                name=sub["name"],
                                location=(top_idx, low_idx, sub_idx),
                                level="subcategory",
                                parent_names=[top_name, low_name]
                            ))
                    elif low.get("url"):
                        # No subcategories, use low category URL
                        queue.append(CategoryInfo(
                        url=low["url"],
                        name=low_name,
                        location=(top_idx, low_idx),
                        level="low",
                        parent_names=[top_name]
                        ))
            elif top.get("url"):
                # No low categories, use top category URL
                queue.append(CategoryInfo(
                    url=top["url"],
                    name=top_name,
                    location=(top_idx,),
                    level="top",
                    parent_names=[]
                    ))
        
        return queue
    
    async def scrape_single_page(self, page: Page, url: str) -> dict:
        """Scrape a single category page with timeout handling."""
        try:
            await page.goto(url, wait_until="networkidle", timeout=self.page_timeout)
            await page.wait_for_selector(self.get_wait_selector(), timeout=30000)
            await asyncio.sleep(self.wait_after_load)
        except asyncio.TimeoutError:
            return {"url": url, "products": [], "error": "Page load timeout"}
        except Exception as e:
            return {"url": url, "products": [], "error": str(e)}
        
        products = await self.extract_products_from_page(page)
        pagination = await self.extract_pagination_info(page)
        
        return {
            "url": url,
            "products": products,
            "product_count": len(products),
            "pagination": pagination
        }
    
    async def scrape_category_all_pages(
        self, 
        context: BrowserContext,
        category: CategoryInfo,
        stats: ScrapeStats
    ) -> List[dict]:
        """Scrape all pages of a category with retry logic."""
        all_products = []
        page = await context.new_page()
        consecutive_failures = 0
        
        try:
            # First page with retries
            result = None
            for attempt in range(1, self.retry_config.max_retries + 1):
                try:
                    result = await self.scrape_single_page(page, category.url)
                    if not result.get("error"):
                        consecutive_failures = 0
                        break
                    raise Exception(result["error"])
                except Exception as e:
                    consecutive_failures += 1
                    stats.retries_total += 1
                    if attempt < self.retry_config.max_retries:
                        delay = self.retry_config.get_delay(attempt)
                        self.logger.debug(f"    Retry {attempt}: {e}. Waiting {delay:.1f}s")
                        await asyncio.sleep(delay)
                    else:
                        self.logger.warning(f"    Failed after {self.retry_config.max_retries} retries")
                        return []
            
            if not result or result.get("error"):
                return []
            
            all_products.extend(result["products"])
            total_pages = result.get("pagination", {}).get("total_pages", 1)
            stats.total_pages += 1
            
            # Remaining pages with failure threshold
            for page_num in range(2, total_pages + 1):
                if consecutive_failures >= self.max_consecutive_failures:
                    self.logger.warning(
                        f"    Stopping: {consecutive_failures} consecutive failures"
                    )
                    break
                
                page_url = self.build_page_url(category.url, page_num)
                
                for attempt in range(1, self.retry_config.max_retries + 1):
                    try:
                        result = await self.scrape_single_page(page, page_url)
                        if not result.get("error"):
                            consecutive_failures = 0
                            break
                        raise Exception(result["error"])
                    except Exception as e:
                        consecutive_failures += 1
                        stats.retries_total += 1
                        if attempt < self.retry_config.max_retries:
                            delay = self.retry_config.get_delay(attempt)
                            await asyncio.sleep(delay)
                        else:
                            result = {"products": []}
                            break
                
                if result and not result.get("error"):
                    all_products.extend(result["products"])
                    stats.total_pages += 1
                    
        finally:
            await page.close()
        
        return all_products


class FastScraper(ABC):
    """
    Fast HTTP-based scraper using httpx + selectolax.
    Use this for sites that don't require JavaScript rendering.
    """
    
    def __init__(self, site_name: str, logger: logging.Logger):
        self.site_name = site_name
        self.logger = logger
        self.config = load_site_config(site_name)
        
        # Load settings
        settings = self.config.get("settings", {})
        self.retry_config = RetryConfig(
            max_retries=settings.get("max_retries", DEFAULT_MAX_RETRIES),
            base_delay=settings.get("retry_delay", DEFAULT_RETRY_DELAY),
        )
        self.max_consecutive_failures = settings.get(
            "max_consecutive_failures", DEFAULT_MAX_CONSECUTIVE_FAILURES
        )
        self.request_timeout = settings.get("request_timeout", DEFAULT_REQUEST_TIMEOUT)
        
        # For backwards compatibility
        self.max_retries = self.retry_config.max_retries
        self.retry_delay = self.retry_config.base_delay
        
        # HTTP client headers — randomised per session to avoid fingerprinting
        self.headers = random_headers()
        
        # Base data directory
        self._base_data_dir = DATA_DIR / site_name
        self._base_data_dir.mkdir(parents=True, exist_ok=True)
        self._current_data_dir = None  # Can be set to use specific folder
        
        # HTTP clients — one per Tor instance (or a single direct client)
        self._clients: Dict[int, httpx.AsyncClient] = {}
    
    @property
    def data_dir(self) -> Path:
        """Get date-specific data directory."""
        # If _current_data_dir is set (from scrape_product_details), use it
        if self._current_data_dir:
            return self._current_data_dir
        date_dir = self._base_data_dir / get_date_folder()
        date_dir.mkdir(parents=True, exist_ok=True)
        return date_dir
    
    @property
    def html_dir(self) -> Path:
        """Get HTML storage directory (not date-specific)."""
        html_dir = self._base_data_dir / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        return html_dir
    
    @property
    def base_url(self) -> str:
        return self.config.get("base_url", f"https://www.{self.site_name}.tn")
    
    @property
    def selectors(self) -> dict:
        return self.config.get("selectors", {})
    
    async def get_client(self, slot: int = 0) -> httpx.AsyncClient:
        """Get or create HTTP client for a given Tor slot."""
        pool = TorPool.get()
        proxy = pool.proxy_url(slot)
        key = slot if pool.active else -1
        if key not in self._clients or self._clients[key].is_closed:
            self._clients[key] = httpx.AsyncClient(
                headers=self.headers,
                follow_redirects=True,
                timeout=httpx.Timeout(self.request_timeout, connect=10.0),
                limits=httpx.Limits(
                    max_connections=200,
                    max_keepalive_connections=40,
                    keepalive_expiry=30.0,
                ),
                proxy=proxy,
            )
        return self._clients[key]
    
    async def close(self):
        """Close all HTTP clients gracefully."""
        for client in self._clients.values():
            if client and not client.is_closed:
                try:
                    await client.aclose()
                except Exception:
                    pass
        self._clients.clear()
    
    async def fetch_html(self, url: str, raise_on_error: bool = False) -> Optional[str]:
        """
        Fetch HTML content from URL with retry logic.
        Each call is routed through a different Tor instance (round-robin).
        
        Args:
            url: URL to fetch
            raise_on_error: If True, raise exception on failure; else return None
            
        Returns:
            HTML content or None on failure
        """
        pool = TorPool.get()
        slot = await pool.next_slot() if pool.active else 0
        client = await self.get_client(slot)
        # Auto-rotate circuit after every TOR_ROTATE_EVERY requests
        await pool.track_request(slot, self.logger)
        # Human-like delay between requests to avoid rate-limiting
        await asyncio.sleep(random_delay(0.3, 1.5))
        last_exception = None
        
        for attempt in range(1, self.retry_config.max_retries + 1):
            try:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
            except httpx.TimeoutException as e:
                last_exception = e
                self.logger.debug(f"  Timeout fetching {url} (attempt {attempt})")
            except httpx.HTTPStatusError as e:
                last_exception = e
                if e.response.status_code in (404, 410):
                    # Don't retry for not found
                    break
                self.logger.debug(f"  HTTP {e.response.status_code} for {url} (attempt {attempt})")
            except Exception as e:
                last_exception = e
                self.logger.debug(f"  Error fetching {url}: {e} (attempt {attempt})")
            
            if attempt < self.retry_config.max_retries:
                delay = self.retry_config.get_delay(attempt)
                await asyncio.sleep(delay)
        
        if raise_on_error and last_exception:
            raise last_exception
        
        self.logger.warning(f"Failed to fetch {url}: {last_exception}")
        return None
    
    # === Abstract Methods ===
    
    @abstractmethod
    def extract_categories_from_html(self, html: str) -> dict:
        """Parse frontpage HTML and extract category hierarchy."""
        pass
    
    @abstractmethod
    def extract_products_from_html(self, html: str) -> List[dict]:
        """Extract products from category page HTML."""
        pass
    
    @abstractmethod
    def extract_pagination_from_html(self, html: str) -> dict:
        """Extract pagination info from category page HTML."""
        pass
    
    @abstractmethod
    def build_page_url(self, base_url: str, page_num: int) -> str:
        """Build URL for specific page number."""
        pass
    
    @abstractmethod
    async def scrape_product_details(self, url: str) -> dict:
        """Scrape detailed product information from product page."""
        pass
    
    # === Implemented Methods ===
    
    async def download_frontpage(self) -> Path:
        """Download frontpage HTML."""
        output_path = self.html_dir / "frontpage.html"
        
        self.logger.info(f"📥 Downloading: {self.base_url}")
        
        html = await self.fetch_html(self.base_url, raise_on_error=True)
        
        output_path.write_text(html, encoding="utf-8")
        self.logger.info(f"✓ Saved: {output_path} ({len(html):,} bytes)")
        return output_path
    
    def extract_categories(self) -> Path:
        """Extract categories from downloaded frontpage."""
        html_path = self.html_dir / "frontpage.html"
        output_path = self.data_dir / "categories.json"
        
        if not html_path.exists():
            raise FileNotFoundError(f"Frontpage not found: {html_path}")
        
        self.logger.info(f"📂 Extracting categories from: {html_path}")
        
        html = html_path.read_text(encoding="utf-8")
        data = self.extract_categories_from_html(html)
        
        data["site"] = self.site_name
        data["shop"] = self.site_name  # Alias for consistency
        data["base_url"] = self.base_url
        data["extracted_at"] = datetime.now().isoformat()
        data["date"] = get_date_folder()
        
        
        save_json(data, output_path, self.logger)
        return output_path
    
    async def scrape_category_page(self, url: str) -> dict:
        """Scrape a single category page."""
        html = await self.fetch_html(url)
        
        if not html:
            return {
                "products": [], 
                "pagination": {"total_pages": 1}, 
                "error": "Failed to fetch"
            }
        
        try:
            products = self.extract_products_from_html(html)
            pagination = self.extract_pagination_from_html(html)
        except Exception as e:
            self.logger.debug(f"Error parsing {url}: {e}")
            return {
                "products": [], 
                "pagination": {"total_pages": 1}, 
                "error": str(e)
            }
        
        return {
            "products": products,
            "pagination": pagination
        }
    
    async def scrape_all_pages(
        self,
        category_url: str,
        limit: int = None,
    ) -> List[dict]:
        """Scrape all pages of a category.

        Page 1 is fetched first to discover ``total_pages``.  All remaining
        pages are then fetched **concurrently** (bounded by a per-category
        semaphore of 4) so multi-page categories are scraped much faster.
        """
        all_products = []

        # Page 1 — required to know total_pages
        result = await self.scrape_category_page(category_url)
        if result.get("error"):
            return []

        all_products.extend(result["products"])
        total_pages = result.get("pagination", {}).get("total_pages", 1)

        if total_pages <= 1:
            return all_products[:limit] if limit else all_products

        # Pages 2+ — concurrent, at most 4 in-flight per category
        page_sem = asyncio.Semaphore(4)

        async def _fetch_page(page_num: int) -> List[dict]:
            async with page_sem:
                url = self.build_page_url(category_url, page_num)
                res = await self.scrape_category_page(url)
                if res.get("error"):
                    self.logger.debug(
                        f"  Page {page_num} failed ({category_url}): {res['error']}"
                    )
                    return []
                return res["products"]

        page_results = await asyncio.gather(
            *[_fetch_page(p) for p in range(2, total_pages + 1)],
            return_exceptions=True,
        )
        for page_result in page_results:
            if isinstance(page_result, Exception):
                self.logger.debug(f"  Page fetch error: {page_result}")
            else:
                all_products.extend(page_result)

        return all_products[:limit] if limit else all_products
    
    def build_scrape_queue(self, categories_data: dict) -> List[CategoryInfo]:
        """Build flat list of categories to scrape from hierarchy.

            Fallback hierarchy:
            1. Subcategories (if they exist)
            2. Low categories (if no subcategories)
            3. Top categories (if no low categories)
        """
        queue = []
        
        for top_idx, top in enumerate(categories_data.get("categories", [])):
            top_name = top.get("name", "")
            # Always get a list, even if empty
            low_level_categories = top.get("low_level_categories") or []
            has_low_categories = len(low_level_categories) > 0
            
            if has_low_categories:
                # Process low-level categories
                for low_idx, low in enumerate(low_level_categories):
                    low_name = low.get("name", "")
                    subcategories = low.get("subcategories") or []
                    has_subcategories = len(subcategories) > 0

                    if has_subcategories:
                        # Add all subcategories
                        for sub_idx, sub in enumerate(subcategories):
                            if sub.get("url"):
                                queue.append(CategoryInfo(
                                    url=sub.get("url", ""),
                                    name=sub.get("name", ""),
                                    location=(top_idx, low_idx, sub_idx),
                                    level="subcategory",
                                    parent_names=[top_name, low_name]
                                ))
                    elif low.get("url"):
                        # No subcategories, use low category URL
                        queue.append(CategoryInfo(
                            url=low.get("url", ""),
                            name=low_name,
                            location=(top_idx, low_idx),
                            level="low",
                            parent_names=[top_name]
                        ))
            elif top.get("url"):
                # No low categories, use top category URL
                queue.append(CategoryInfo(
                    url=top.get("url", ""),
                    name=top_name,
                    location=(top_idx,),
                    level="top",
                    parent_names=[]
                ))
        
        return queue

