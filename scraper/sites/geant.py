#!/usr/bin/env python3
"""
Geant Drive (geantdrive.tn) specific scraper implementation.
"""
import logging
import re
from typing import List, Dict, Any
from urllib.parse import urljoin

from selectolax.parser import HTMLParser

from scraper.base import FastScraper


class GeantScraper(FastScraper):
    """HTTPX/selectolax-based scraper for geantdrive.tn (PrestaShop + WB MegaMenu). No detail pages."""

    def __init__(self, logger: logging.Logger):
        super().__init__("geant", logger)

    def build_page_url(self, base_url: str, page_num: int) -> str:
        if "?" in base_url:
            return f"{base_url}&page={page_num}"
        return f"{base_url}?page={page_num}"

    def extract_categories_from_html(self, html: str) -> dict:
        """Extract 2-level category hierarchy from geantdrive.tn frontpage (top + low, no subcategories)."""
        tree = HTMLParser(html)
        fp = self.selectors.get("frontpage", {})
        categories = []

        top_blocks = tree.css(fp.get("top_level_blocks", "ul.menu-content.top-menu > li.level-1"))
        self.logger.info(f"Found {len(top_blocks)} top-level category blocks")

        for top_block in top_blocks:
            top_link = top_block.css_first(fp.get("top_level_link", "a[href]"))
            if not top_link:
                continue

            # Name from nested span
            name_el = top_block.css_first(fp.get("top_level_name", "a > span"))
            top_name = name_el.text(strip=True) if name_el else top_link.text(strip=True)
            top_url = top_link.attributes.get("href", "")
            if top_url and not top_url.startswith("http"):
                top_url = urljoin(self.base_url, top_url)

            top_cat = {
                "name": top_name,
                "url": top_url,
                "level": "top",
                "low_level_categories": [],
            }

            # Low-level: WB sub-menu headers
            low_blocks = top_block.css(fp.get("low_level_blocks", "div.wb-sub-menu li.menu-item.item-header"))
            for low_block in low_blocks:
                low_link = low_block.css_first(fp.get("low_level_link", "a.category_header"))
                if not low_link:
                    continue

                low_name = low_link.text(strip=True)
                low_url = low_link.attributes.get("href", "")
                if not low_name:
                    continue
                if low_url and not low_url.startswith("http"):
                    low_url = urljoin(self.base_url, low_url)

                top_cat["low_level_categories"].append({
                    "name": low_name,
                    "url": low_url,
                    "level": "low",
                    "subcategories": [],
                })

            categories.append(top_cat)

        stats = {"top_level": 0, "low_level": 0, "subcategory": 0, "total_urls": 0}
        for top in categories:
            stats["top_level"] += 1
            if top.get("url"):
                stats["total_urls"] += 1
            for low in top.get("low_level_categories", []):
                stats["low_level"] += 1
                if low.get("url"):
                    stats["total_urls"] += 1

        self.logger.info(
            f"Extracted {stats['top_level']} top, {stats['low_level']} low categories ({stats['total_urls']} URLs)"
        )

        return {"categories": categories, "stats": stats}

    def extract_products_from_html(self, html: str) -> List[Dict[str, Any]]:
        tree = HTMLParser(html)
        cp = self.selectors.get("category_page", {})
        products = []

        items = tree.css(cp.get("item_selector", "article.product-miniature.js-product-miniature"))

        for item in items:
            product_id = item.attributes.get(cp.get("item_id_attr", "data-id-product"))

            name_el = item.css_first(cp.get("item_name", "h2.h3.product-title[itemprop='name'] a"))
            if not name_el:
                continue
            product_name = name_el.text(strip=True)

            url_el = item.css_first(cp.get("item_url", "h2.product-title a[href]"))
            product_url = url_el.attributes.get("href", "") if url_el else ""
            if not product_url:
                continue
            if not product_url.startswith("http"):
                product_url = urljoin(self.base_url, product_url)

            product_data: Dict[str, Any] = {
                "id": product_id,
                "url": product_url,
                "name": product_name,
            }

            # Price
            price_el = item.css_first(cp.get("item_price", "span.price[itemprop='price']"))
            if price_el:
                price_content = price_el.attributes.get("content")
                if price_content:
                    try:
                        product_data["price"] = float(price_content)
                    except ValueError:
                        product_data["price"] = None
                else:
                    price_text = re.sub(r"[^\d.,]", "", price_el.text()).replace(",", ".")
                    try:
                        product_data["price"] = float(price_text) if price_text else None
                    except ValueError:
                        product_data["price"] = None
            else:
                product_data["price"] = None

            # Old price
            old_price_el = item.css_first(".regular-price")
            if old_price_el:
                old_text = re.sub(r"[^\d.,]", "", old_price_el.text()).replace(",", ".")
                try:
                    product_data["old_price"] = float(old_text) if old_text else None
                except ValueError:
                    product_data["old_price"] = None

            # Brand
            brand_el = item.css_first(cp.get("item_brand", "p.manufacturer_product"))
            if brand_el:
                product_data["brand"] = brand_el.text(strip=True)

            # Image
            img_el = item.css_first(cp.get("item_image", "a.thumbnail.product-thumbnail img.img-responsive"))
            if img_el:
                image_url = None
                for attr in cp.get("item_image_attrs", ["src", "data-src", "data-full-size-image-url"]):
                    image_url = img_el.attributes.get(attr)
                    if image_url and not image_url.startswith("data:"):
                        break
                if image_url:
                    if image_url.startswith("//"):
                        image_url = "https:" + image_url
                    elif image_url.startswith("/"):
                        image_url = urljoin(self.base_url, image_url)
                    if not image_url.startswith("data:"):
                        product_data["image"] = image_url

            # Availability from listing (structured data)
            avail_link = item.css_first('link[itemprop="availability"]')
            if avail_link:
                avail_href = avail_link.attributes.get("href", "")
                if "InStock" in avail_href:
                    product_data["availability"] = "En stock"
                    product_data["available"] = True
                elif "OutOfStock" in avail_href:
                    product_data["availability"] = "En rupture"
                    product_data["available"] = False

            products.append(product_data)

        return products

    def extract_pagination_from_html(self, html: str) -> dict:
        tree = HTMLParser(html)
        cp = self.selectors.get("category_page", {})

        current_page = 1
        total_pages = 1
        has_next = False

        page_links = tree.css(cp.get("pagination_pages", "ul.page-list a.js-search-link"))
        for el in page_links:
            classes = el.attributes.get("class", "")
            try:
                num = int(el.text(strip=True))
                if num > total_pages:
                    total_pages = num
                if "disabled" in classes or "current" in classes:
                    current_page = num
            except (ValueError, TypeError):
                continue

        next_link = tree.css_first(cp.get("pagination_next", "a.next.js-search-link[rel='next']"))
        if next_link and "disabled" not in next_link.attributes.get("class", ""):
            has_next = True

        return {
            "current_page": current_page,
            "total_pages": total_pages,
            "has_next": has_next,
        }

    async def scrape_product_details(self, url: str) -> dict:
        """No detail pages for Geant — return listing data directly."""
        return {
            "url": url,
            "title": None,
            "product_id": None,
            "price": None,
            "availability": None,
            "available": None,
            "images": None,
            "note": "No detail pages — use listing data",
        }


def get_scraper(logger: logging.Logger) -> GeantScraper:
    return GeantScraper(logger)
