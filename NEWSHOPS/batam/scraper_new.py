"""
Batam e-commerce scraper — shop-specific parsing only.
Platform: Magento 2 (Hyva + Alpine.js + Tailwind).
Categories: Playwright (CSR). Listings + Details: httpx (SSR).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from selectolax.parser import HTMLParser

_shop_dir = Path(__file__).resolve().parent
_project_root = _shop_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_shop_dir) not in sys.path:
    sys.path.insert(0, str(_shop_dir))

from common.pipeline import BaseScraper
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url
import config_new as config


class BatamScraper(BaseScraper):
    shop_name = "batam"
    shop_config = config
    use_playwright_for_categories = True

    # -- Categories (Playwright renders Alpine.js) ---------------------------

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        base = config.BASE_URL
        link_fb = cs.get("link_fallback", "a[href]")

        top_lis = tree.css(cs["top_block"])
        for top_idx, top_li in enumerate(top_lis):
            top_span = top_li.css_first(cs["top_name"])
            top_name = parse_node_text(top_span) if top_span else ""
            top_a = top_li.css_first(link_fb)
            top_url = abs_url(parse_node_attr(top_a, "href"), base) if top_a else ""
            top_id = self._slug(top_url) if top_url else f"top_{top_idx}"

            if top_url and top_url not in seen_urls:
                seen_urls.add(top_url)
            categories.append({
                "id": top_id, "name": top_name, "url": top_url or None,
                "parent_id": None, "level": "top",
            })

            for low_li in top_li.css(cs["low_block"]):
                low_a = low_li.css_first(cs["low_link"]) or low_li.css_first(link_fb)
                if not low_a:
                    continue
                low_url = abs_url(parse_node_attr(low_a, "href"), base)
                low_id = self._slug(low_url)
                if not low_url or low_url in seen_urls:
                    continue
                seen_urls.add(low_url)
                categories.append({
                    "id": low_id, "name": parse_node_text(low_a), "url": low_url,
                    "parent_id": top_id, "level": "low",
                })

                for sub_li in low_li.css(cs["sub_block"]):
                    sub_a = sub_li.css_first(cs["sub_link"]) or sub_li.css_first(link_fb)
                    if not sub_a:
                        continue
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), base)
                    sub_id = self._slug(sub_url)
                    if not sub_url or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    categories.append({
                        "id": sub_id, "name": parse_node_text(sub_a), "url": sub_url,
                        "parent_id": low_id, "level": "sub",
                    })

        return categories

    @staticmethod
    def _slug(url: str) -> str:
        return extract_slug_from_url(url, sanitize_pattern=config.URL_PATTERNS.get("slug_sanitize"))

    # -- Listings (httpx, SSR) -----------------------------------------------

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        base = config.BASE_URL
        products = []

        for elem in tree.css(ls["element"]):
            id_el = elem.css_first(ls["id_selector"])
            pid = parse_node_attr(id_el, ls["id_attr"]) if id_el else ""
            if not pid:
                continue

            name_el = elem.css_first(ls["name"])
            url = abs_url(parse_node_attr(name_el, "href"), base) if name_el else ""
            name = parse_node_text(name_el)
            if not pid and url:
                pid = extract_id_from_url(url, config.URL_PATTERNS["id_from_url"]) or ""
            if not pid:
                continue

            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, base) if img_url else ""

            price = parse_node_text(elem.css_first(ls["price"]))
            pn_el = elem.css_first(ls.get("price_numeric_selector", ""))
            price_numeric = parse_node_attr(pn_el, ls.get("price_numeric_attr", "")) if pn_el else ""
            old_price = parse_node_text(elem.css_first(ls["old_price"]))

            av_sel = ls["availability"]["selector"]
            availability = parse_node_text(elem.css_first(av_sel))

            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "price_numeric": price_numeric,
                "old_price": old_price, "availability": availability,
            })
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        next_a = tree.css_first(config.PAGINATION_SELECTOR_NEXT)
        if not next_a:
            return None
        href = parse_node_attr(next_a, "href")
        return abs_url(href, config.BASE_URL) if href else None

    # -- Detail (httpx, SSR) -------------------------------------------------

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        base = config.BASE_URL

        def _text(css: str | None) -> str:
            if not css:
                return ""
            n = tree.css_first(css)
            return parse_node_text(n)

        title = _text(sel["title"])
        ref_el = tree.css_first(sel["reference_selector"])
        reference = parse_node_attr(ref_el, sel["reference_attr"]) if ref_el else ""

        price = _text(sel["price"])
        pn_el = tree.css_first(sel.get("price_numeric_selector", ""))
        price_numeric = parse_node_attr(pn_el, sel.get("price_numeric_attr", "")) if pn_el else ""
        old_price = _text(sel.get("old_price"))

        avail_el = tree.css_first(sel["global_availability"])
        availability = parse_node_text(avail_el) if avail_el else ""
        if not availability and sel.get("availability_in_stock_text"):
            fallback = sel.get("availability_fallback_scope", "body")
            for node in tree.css(fallback):
                if sel["availability_in_stock_text"] in (node.text() or ""):
                    availability = sel["availability_in_stock_text"]
                    break

        description = _text(sel["description"])

        specs: dict[str, str] = {}
        specs_cont = tree.css_first(sel["specs"]["container"])
        if specs_cont:
            for row in specs_cont.css(sel["specs"]["row"]):
                k = parse_node_text(row.css_first(sel["specs"]["key"]))
                v = parse_node_text(row.css_first(sel["specs"]["value"]))
                if k and v:
                    specs[k] = v

        images: list[str] = []
        image_main = ""
        for img in tree.css(sel["images"]["main"]):
            for a in sel["images"]["main_attrs"]:
                src = parse_node_attr(img, a)
                if src:
                    full = abs_url(src, base)
                    images.append(full)
                    if not image_main:
                        image_main = full
                    break

        pid = extract_id_from_url(url, config.URL_PATTERNS["id_from_url"]) or reference or ""
        return {
            "id": pid, "url": url, "title": title, "brand": None,
            "reference": reference, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "availability": availability,
            "description": description, "specs": specs,
            "image_main": image_main, "images": images,
        }


def run() -> None:
    BatamScraper.create().start()


if __name__ == "__main__":
    run()
