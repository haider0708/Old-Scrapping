#!/usr/bin/env python3
"""
Pharmacie Plus (parapharmacieplus.tn) specific scraper implementation.

Full CSR: Playwright for all phases — frontpage, listing pages, and product details.
Platform: Custom PHP + Bootstrap 4 + Htmlstream MegaMenu + Fotorama gallery.
"""
import asyncio
import json
import logging
import re
from typing import List, Optional
from urllib.parse import urljoin, urlparse, parse_qs

from selectolax.parser import HTMLParser
from playwright.async_api import Page

from scraper.base import BaseScraper, CategoryInfo


class PharmaciePlusScraper(BaseScraper):
    """Full-CSR Playwright scraper for parapharmacieplus.tn."""

    def __init__(self, logger: logging.Logger):
        super().__init__("pharmacieplus", logger)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
        return re.sub(r"\s+", " ", text).strip()

    def _make_absolute_url(self, url: str) -> Optional[str]:
        if not url:
            return None
        if url.startswith("http"):
            return url
        if url.startswith("//"):
            return "https:" + url
        if url.startswith("/"):
            return f"{self.base_url}{url}"
        return f"{self.base_url}/{url}"

    def _parse_price(self, text: str) -> Optional[float]:
        """Extract numeric price from text like '12,500 DT' or '1 234.500'."""
        if not text:
            return None
        cleaned = re.sub(r"[^\d.,]", "", text)
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(",", "")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            return float(cleaned) if cleaned else None
        except ValueError:
            return None

    # ------------------------------------------------------------------
    # Abstract implementations
    # ------------------------------------------------------------------

    def get_wait_selector(self) -> str:
        return self.selectors.get("category_page", {}).get(
            "wait_selector",
            "li.col-md-mc-5.col-fix.item-prod",
        )

    def build_page_url(self, base_url: str, page_num: int) -> str:
        """Pagination via ?page={n} query parameter."""
        base = re.sub(r"[?&]page=\d+", "", base_url)
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}page={page_num}"

    # ------------------------------------------------------------------
    # Frontpage — Playwright override (CSR mega-menu)
    # ------------------------------------------------------------------

    async def download_frontpage(self):
        """Download frontpage using Playwright (Htmlstream MegaMenu requires JS)."""
        output_path = self.html_dir / "frontpage.html"
        self.logger.info(f"📥 Downloading (Playwright): {self.base_url}")

        fp = self.selectors.get("frontpage", {})
        wait_sel = fp.get("wait_selector", "ul.navbar-nav.u-header__navbar-nav")

        from playwright.async_api import async_playwright

        async with async_playwright() as pw:
            from scraper.base import playwright_launch_args, get_playwright_proxy
            browser = await pw.chromium.launch(headless=True, args=playwright_launch_args())
            page = await browser.new_page(proxy=get_playwright_proxy())
            try:
                await page.goto(self.base_url, wait_until="networkidle", timeout=30000)
                try:
                    await page.wait_for_selector(wait_sel, timeout=10000)
                except Exception:
                    self.logger.warning(f"Wait selector '{wait_sel}' not found, continuing")
                await asyncio.sleep(self.wait_after_load)
                html = await page.content()
            finally:
                await page.close()
                await browser.close()

        output_path.write_text(html, encoding="utf-8")
        self.logger.info(f"✓ Saved: {output_path} ({len(html):,} bytes)")
        return output_path

    # ------------------------------------------------------------------
    # Categories — Htmlstream MegaMenu
    # ------------------------------------------------------------------

    def extract_categories_from_html(self, html: str) -> dict:
        """
        Extract category hierarchy from Htmlstream MegaMenu.

        Structure:
        - top: li.nav-item.hs-has-mega-menu > a.nav-link
        - low: div.hs-mega-menu div.col-3 > a  (with span.u-header__sub-menu-title)
        - sub: ul.u-header__sub-menu-nav-group > li > a.u-header__sub-menu-nav-link
        """
        tree = HTMLParser(html)
        fp = self.selectors.get("frontpage", {})
        categories = []

        top_sel = fp.get(
            "top_level_blocks",
            "ul.navbar-nav.u-header__navbar-nav > li.nav-item.hs-has-mega-menu",
        )
        top_blocks = tree.css(top_sel)
        self.logger.info(f"Found {len(top_blocks)} top-level categories")

        for top_block in top_blocks:
            top_link = top_block.css_first(
                fp.get("top_level_link", "a.nav-link")
            )
            if not top_link:
                continue

            top_name = self._clean_text(top_link.text(strip=True))
            top_url = self._make_absolute_url(top_link.attributes.get("href"))

            if not top_name:
                continue

            top_cat = {
                "name": top_name,
                "url": top_url,
                "level": "top",
                "low_level_categories": [],
            }

            # Low-level categories
            low_sel = fp.get(
                "low_level_items",
                "div.hs-mega-menu.u-header__sub-menu div.col-3 > a",
            )
            low_items = top_block.css(low_sel)

            for low_link in low_items:
                # Name from nested span or direct text
                name_span = low_link.css_first(
                    fp.get("low_level_name", "span.u-header__sub-menu-title")
                )
                low_name = self._clean_text(
                    name_span.text(strip=True) if name_span else low_link.text(strip=True)
                )
                low_url = self._make_absolute_url(low_link.attributes.get("href"))

                if not low_name:
                    continue

                low_cat = {
                    "name": low_name,
                    "url": low_url,
                    "level": "low",
                    "subcategories": [],
                }

                # Subcategories: sibling ul after this anchor
                parent = low_link.parent
                if parent:
                    sub_sel = fp.get(
                        "subcategory_items",
                        "ul.u-header__sub-menu-nav-group > li > a.u-header__sub-menu-nav-link",
                    )
                    sub_links = parent.css(sub_sel)
                    for sub_link in sub_links:
                        sub_name = self._clean_text(sub_link.text(strip=True))
                        sub_url = self._make_absolute_url(sub_link.attributes.get("href"))
                        if sub_name and sub_url:
                            low_cat["subcategories"].append({
                                "name": sub_name,
                                "url": sub_url,
                                "level": "subcategory",
                            })

                top_cat["low_level_categories"].append(low_cat)

            categories.append(top_cat)

        # Stats
        stats = {"top_level": 0, "low_level": 0, "subcategory": 0, "total_urls": 0}
        for top in categories:
            stats["top_level"] += 1
            if top.get("url"):
                stats["total_urls"] += 1
            for low in top.get("low_level_categories", []):
                stats["low_level"] += 1
                if low.get("url"):
                    stats["total_urls"] += 1
                for sub in low.get("subcategories", []):
                    stats["subcategory"] += 1
                    if sub.get("url"):
                        stats["total_urls"] += 1

        return {"categories": categories, "stats": stats}

    # ------------------------------------------------------------------
    # Products — listing page (Playwright page.evaluate)
    # ------------------------------------------------------------------

    async def extract_products_from_page(self, page: Page) -> List[dict]:
        """Extract products from a loaded category page via JS evaluation."""
        cp = self.selectors.get("category_page", {})
        item_selector = cp.get("item_selector", "li.col-md-mc-5.col-fix.item-prod")

        products = await page.evaluate(
            """(selector) => {
                const items = document.querySelectorAll(selector);
                const products = [];

                const parsePrice = (text) => {
                    if (!text) return null;
                    const cleaned = text.replace(/[^\\d.,]/g, '');
                    let normalized = cleaned;
                    if (normalized.includes(',') && normalized.includes('.')) {
                        normalized = normalized.replace(',', '');
                    } else if (normalized.includes(',')) {
                        normalized = normalized.replace(',', '.');
                    }
                    const num = parseFloat(normalized);
                    return isNaN(num) ? null : num;
                };

                items.forEach(item => {
                    // URL
                    const linkEl = item.querySelector(
                        'a.text-gray-100.justify-content-around, a[href]'
                    );
                    const url = linkEl ? linkEl.getAttribute('href') : null;

                    // Product ID from data attribute or URL
                    let productId = item.getAttribute('data-id')
                        || item.querySelector('[data-id]')?.getAttribute('data-id');
                    if (!productId && url) {
                        const m = url.match(/[?&]id=(\\d+)/);
                        if (m) productId = m[1];
                    }

                    // Name
                    const nameEl = item.querySelector(
                        'div.text-truncate.name-prod-card, div.product_name, h3.product_title'
                    );
                    const name = nameEl ? nameEl.innerText.trim() : '';

                    // Image
                    const imgEl = item.querySelector(
                        'div.product-item__inner.position-relative img, img.product_img, img'
                    );
                    let image = null;
                    if (imgEl) {
                        image = imgEl.getAttribute('src')
                            || imgEl.getAttribute('data-src');
                    }

                    // Price
                    const priceEl = item.querySelector(
                        'div.info-ligne-card div.text-red, div.product_price, span.prix'
                    );
                    const price = parsePrice(priceEl ? priceEl.innerText : null);

                    // Old price
                    const oldPriceEl = item.querySelector(
                        'del.font-size-12, span.ancien_prix, del'
                    );
                    const oldPrice = parsePrice(oldPriceEl ? oldPriceEl.innerText : null);

                    // Availability
                    const availEl = item.querySelector(
                        'span.stock_status, div.disponibilite, .availability'
                    );
                    const availability = availEl ? availEl.innerText.trim() : null;

                    if (productId || url) {
                        const p = {
                            id: productId || null,
                            url: url,
                            name: name,
                            price: price,
                            old_price: oldPrice || null,
                        };
                        if (image) p.image = image;
                        if (availability) p.availability = availability;
                        if (oldPrice && price) {
                            p.discount_percent = Math.round((1 - price / oldPrice) * 100);
                        }
                        products.push(p);
                    }
                });

                return products;
            }""",
            item_selector,
        )

        return products

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    async def extract_pagination_info(self, page: Page) -> dict:
        """Extract pagination info from the loaded page."""
        cp = self.selectors.get("category_page", {})
        next_icon_sel = cp.get(
            "pagination_next_icon",
            "li.page-item a.page-link i.fa.fa-angle-right",
        )

        pagination = await page.evaluate(
            """(nextIconSel) => {
                let maxPage = 1;
                let currentPage = 1;

                // Current page from active item
                const activeEl = document.querySelector(
                    'li.page-item.active a.page-link, li.page-item.active span.page-link'
                );
                if (activeEl) {
                    const n = parseInt(activeEl.innerText);
                    if (!isNaN(n)) currentPage = n;
                }

                // Max page from all page links
                document.querySelectorAll('li.page-item a.page-link').forEach(el => {
                    const href = el.getAttribute('href') || '';
                    // Try ?page=N in URL
                    const m = href.match(/[?&]page=(\\d+)/);
                    if (m) {
                        const n = parseInt(m[1]);
                        if (n > maxPage) maxPage = n;
                    }
                    // Try text content
                    const n = parseInt(el.innerText);
                    if (!isNaN(n) && n > maxPage) maxPage = n;
                });

                // Detect if next button exists
                const nextIcon = document.querySelector(nextIconSel);
                const hasNext = !!nextIcon;

                return {
                    current_page: currentPage,
                    total_pages: Math.max(maxPage, currentPage),
                    has_next: hasNext,
                };
            }""",
            next_icon_sel,
        )

        return pagination

    # ------------------------------------------------------------------
    # Product details (Playwright)
    # ------------------------------------------------------------------

    async def scrape_product_details(self, page: Page, product_url: str) -> dict:
        """Scrape a single product detail page with Fotorama gallery support."""
        pp = self.selectors.get("product_page", {})

        wait_sel = pp.get("wait_selector", "h1.font-size-25")

        try:
            await page.goto(product_url, wait_until="networkidle", timeout=30000)
            try:
                await page.wait_for_selector(wait_sel, timeout=10000)
            except Exception:
                pass
            await asyncio.sleep(self.wait_after_load)
        except Exception as e:
            return {"url": product_url, "error": str(e)}

        # Extract via JS for reliability on CSR page
        data = await page.evaluate(
            """(selectors) => {
                const data = {url: window.location.href};

                const cleanText = (el) => el ? el.innerText.replace(/\\s+/g, ' ').trim() : null;

                const parsePrice = (text) => {
                    if (!text) return null;
                    const cleaned = text.replace(/[^\\d.,]/g, '');
                    let n = cleaned;
                    if (n.includes(',') && n.includes('.')) n = n.replace(',', '');
                    else if (n.includes(',')) n = n.replace(',', '.');
                    const v = parseFloat(n);
                    return isNaN(v) ? null : v;
                };

                // Title
                const titleEl = document.querySelector(
                    selectors.title || 'h1.font-size-25.text-lh-1dot2'
                ) || document.querySelector('h1.font-size-25, h1.product_title, div.product_name h1');
                data.title = cleanText(titleEl);

                // Price — prefer schema meta, fall back to visible element
                const priceMeta = document.querySelector(
                    selectors.price_schema || "meta[itemprop='price'][content]"
                );
                if (priceMeta) {
                    data.price = parseFloat(priceMeta.getAttribute('content')) || null;
                }
                if (!data.price) {
                    const priceEl = document.querySelector(
                        selectors.price || 'ins.font-size-36.text-decoration-none'
                    );
                    data.price = parsePrice(priceEl ? priceEl.innerText : null);
                }

                // Old price
                const oldPriceEl = document.querySelector(
                    selectors.old_price || 'del.font-size-20.ml-2.text-gray-6'
                ) || document.querySelector('del, span.ancien_prix');
                data.old_price = parsePrice(oldPriceEl ? oldPriceEl.innerText : null);
                if (data.old_price && data.price) {
                    data.discount_percent = Math.round((1 - data.price / data.old_price) * 100);
                }

                // Availability
                const availSchema = document.querySelector(
                    selectors.availability_schema
                    || "link[itemprop='availability'][href*='schema.org/InStock']"
                );
                if (availSchema) {
                    const href = availSchema.getAttribute('href') || '';
                    if (href.includes('InStock')) {
                        data.availability = 'En stock';
                        data.available = true;
                    } else if (href.includes('OutOfStock')) {
                        data.availability = 'Rupture de stock';
                        data.available = false;
                    }
                }
                if (!data.availability) {
                    const stockEl = document.querySelector(
                        'span.stock_status, div.disponibilite, div.availability'
                    );
                    if (stockEl) {
                        const txt = stockEl.innerText.trim();
                        data.availability = txt;
                        const lower = txt.toLowerCase();
                        data.available = (lower.includes('stock') || lower.includes('disponible'))
                            && !lower.includes('rupture') && !lower.includes('indisponible');
                    }
                }

                // Brand
                const brandEl = document.querySelector('span.marque, div.brand, div.product-manufacturer');
                data.brand = cleanText(brandEl);

                // Description
                const descEl = document.querySelector(
                    selectors.description || 'div#tab-description'
                ) || document.querySelector('div.product_description, div.description');
                data.description = cleanText(descEl);

                // Product ID from URL
                const urlMatch = window.location.href.match(/[?&]id=(\\d+)/);
                data.product_id = urlMatch ? urlMatch[1] : null;

                // Specifications
                const specs = {};
                const specContainer = document.querySelector(
                    'div.product_specs, table.product_attributes'
                );
                if (specContainer) {
                    specContainer.querySelectorAll('tr').forEach(row => {
                        const th = row.querySelector('th, td:first-child');
                        const td = row.querySelector('td:last-child');
                        if (th && td && th !== td) {
                            const k = th.innerText.trim();
                            const v = td.innerText.trim();
                            if (k && v) specs[k] = v;
                        }
                    });
                }
                // Also try dt/dd pairs
                document.querySelectorAll('div.product-features dt, div.product_specs dt').forEach(dt => {
                    let dd = dt.nextElementSibling;
                    while (dd && dd.tagName !== 'DD') dd = dd.nextElementSibling;
                    if (dd) {
                        const k = dt.innerText.trim();
                        const v = dd.innerText.trim();
                        if (k && v) specs[k] = v;
                    }
                });
                data.specifications = specs;

                // Images — Fotorama gallery
                const images = [];
                const fotorama = document.querySelector(
                    selectors.image_gallery || 'div.fotorama'
                );
                if (fotorama) {
                    // data-img attribute on inner divs
                    fotorama.querySelectorAll('div[data-img]').forEach(div => {
                        const src = div.getAttribute('data-img');
                        if (src && !images.includes(src)) images.push(src);
                    });
                    // <a href> inside fotorama
                    fotorama.querySelectorAll('a[href]').forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && /\\.(jpe?g|png|webp)/i.test(href) && !images.includes(href)) {
                            images.push(href);
                        }
                    });
                    // img tags inside fotorama
                    fotorama.querySelectorAll('img').forEach(img => {
                        const src = img.getAttribute('src') || img.getAttribute('data-src');
                        if (src && !images.includes(src)) images.push(src);
                    });
                }

                // Fallback: main product image
                if (images.length === 0) {
                    const mainImg = document.querySelector(
                        selectors.image_main
                        || 'div.fotorama__stage__frame.fotorama__active img.fotorama__img'
                    ) || document.querySelector(
                        'img.product_main_image, div.product_image img, img.product-main-image'
                    );
                    if (mainImg) {
                        const src = mainImg.getAttribute('src') || mainImg.getAttribute('data-src');
                        if (src) images.push(src);
                    }
                }

                // Also grab all fotorama img tags for thumbnails
                if (images.length === 0) {
                    document.querySelectorAll(
                        selectors.image_all || 'div.fotorama img.fotorama__img'
                    ).forEach(img => {
                        const src = img.getAttribute('src');
                        if (src && !images.includes(src)) images.push(src);
                    });
                }

                data.images = images;

                return data;
            }""",
            pp,
        )

        return data


# Factory function — required
def get_scraper(logger: logging.Logger) -> PharmaciePlusScraper:
    """Factory function to create scraper instance."""
    return PharmaciePlusScraper(logger)
