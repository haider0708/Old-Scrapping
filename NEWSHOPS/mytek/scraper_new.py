"""
Mytek e-commerce scraper — shop-specific parsing only.
Platform: Magento 2 (Rootways Megamenu).
Categories: httpx (SSR). Listings + Details: Playwright (CSR BrowserPool).
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


class MytekScraper(BaseScraper):
    shop_name = "mytek"
    shop_config = config
    use_playwright_for_listings = True
    use_playwright_for_details = True

    @staticmethod
    def _slug(url: str) -> str:
        return extract_slug_from_url(url, strip_segments=("catalog",), sanitize_pattern=config.URL_PATTERNS.get("slug_sanitize"))

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        base = config.BASE_URL
        link_fb = cs.get("link_fallback", "a[href]")

        nav = tree.css_first(cs["nav_container"])
        if not nav:
            self.log.warning("Nav container not found")
            return []

        for top_idx, top_li in enumerate(nav.css(cs["top_items"])):
            name_el = top_li.css_first(cs["top_name"])
            top_name = parse_node_text(name_el) if name_el else ""
            top_id = f"top_{top_idx}"
            categories.append({"id": top_id, "name": top_name, "url": None, "parent_id": None, "level": "top"})

            children = top_li.css_first(cs["children_container"])
            if not children:
                continue

            lows: list[tuple[str, str]] = []
            for low_block in children.css(cs["low_blocks"]):
                low_a = low_block.css_first(cs["low_link"]) or low_block.css_first(link_fb)
                if not low_a:
                    continue
                low_url = abs_url(parse_node_attr(low_a, "href"), base)
                low_id = self._slug(low_url)
                if low_url and low_url not in seen_urls:
                    seen_urls.add(low_url)
                    categories.append({"id": low_id, "name": parse_node_text(low_a), "url": low_url, "parent_id": top_id, "level": "low"})
                    lows.append((low_id, low_url))

            for sub_ul in children.css(cs["sub_lists"]):
                for sub_a in sub_ul.css(cs["sub_items"]):
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), base)
                    sub_id = self._slug(sub_url)
                    if not sub_url or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    sub_name_el = sub_a.css_first(cs.get("sub_name", ""))
                    sub_name = parse_node_text(sub_name_el) if sub_name_el else parse_node_text(sub_a)
                    parent_id = top_id
                    for lid, lurl in lows:
                        lb = lurl.replace(".html", "").rstrip("/")
                        if sub_url.startswith(lb + "/") or sub_url == lb:
                            parent_id = lid
                            break
                    categories.append({"id": sub_id, "name": sub_name, "url": sub_url, "parent_id": parent_id, "level": "sub"})

        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        base = config.BASE_URL
        products = []

        for elem in tree.css(ls["element"]):
            pid = parse_node_attr(elem, ls["id_attr"])
            if not pid:
                continue

            name_el = elem.css_first(ls["name"])
            url = abs_url(parse_node_attr(name_el, "href"), base) if name_el else ""
            name = parse_node_text(name_el)

            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for a in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, a)
                    if img_url:
                        break
            img_url = abs_url(img_url, base) if img_url else ""

            price = parse_node_text(elem.css_first(ls["price"]))
            old_price = parse_node_text(elem.css_first(ls["old_price"]))

            av_cont = elem.css_first(ls["availability"].get("container", ""))
            availability = ""
            if av_cont:
                st = av_cont.css_first(ls["availability"].get("status", ""))
                availability = parse_node_text(st) if st else ""

            sku = parse_node_text(elem.css_first(ls.get("sku_selector", "")))

            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "old_price": old_price,
                "availability": availability, "sku": sku,
            })
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        """Mytek uses a custom pagination: check if last page-item is not disabled."""
        tree = HTMLParser(html)
        ps = config.PAGINATION_SELECTORS
        page_items = tree.css(ps["page_items"])
        if not page_items:
            return None
        last_li = page_items[-1]
        li_classes = (last_li.attributes or {}).get("class") or ""
        if ps.get("disabled_class", "disabled") in li_classes:
            return None
        next_a = last_li.css_first(ps["page_link"])
        if not next_a:
            return None
        href = parse_node_attr(next_a, "href")
        return abs_url(href, config.BASE_URL) if href else None

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        base = config.BASE_URL

        def _text(css):
            if not css:
                return ""
            n = tree.css_first(css)
            return parse_node_text(n)

        title = _text(sel["title"])
        sku = _text(sel.get("sku"))
        price = _text(sel["price"])
        old_price = _text(sel["old_price"])
        special_price = _text(sel.get("special_price"))
        discount = _text(sel.get("discount"))

        avail_el = tree.css_first(sel.get("global_availability", ""))
        availability = parse_node_text(avail_el) if avail_el else ""

        description = _text(sel["description"])

        specs: dict[str, str] = {}
        sc = sel.get("specs", {})
        cont = tree.css_first(sc.get("container", ""))
        if cont:
            for row in cont.css(sc.get("row", "")):
                k = parse_node_text(row.css_first(sc.get("key", "")))
                v = parse_node_text(row.css_first(sc.get("value", "")))
                if k and v:
                    specs[k] = v

        aps = sel.get("availability_per_shop", {})
        availability_per_shop: list[dict] = []
        if aps:
            cont = tree.css_first(aps.get("container", ""))
            if cont:
                for row in cont.css("tr"):
                    cells = row.css("td")
                    if len(cells) >= 2:
                        shop_name = parse_node_text(cells[0])
                        cls = (cells[1].attributes or {}).get("class") or ""
                        if aps.get("in_stock_class") in cls:
                            status = "En stock"
                        elif aps.get("on_order_class") in cls:
                            status = "Sur commande"
                        elif aps.get("incoming_class") in cls:
                            status = "En arrivage"
                        else:
                            status = parse_node_text(cells[1])
                        availability_per_shop.append({"shop": shop_name, "status": status})

        images: list[str] = []
        image_main = ""
        ic = sel.get("images", {})
        for img in tree.css(ic.get("main", "")):
            src = parse_node_attr(img, "src") or parse_node_attr(img, "data-src")
            if src:
                full = abs_url(src, base)
                images.append(full)
                if not image_main:
                    image_main = full
        for thumb in tree.css(ic.get("thumbnails", "")):
            src = parse_node_attr(thumb, "src") or parse_node_attr(thumb, "data-src")
            if src:
                full = abs_url(src, base)
                if full not in images:
                    images.append(full)

        pid = ""
        for el in tree.css("[data-product-id]"):
            pid = parse_node_attr(el, "data-product-id")
            if pid:
                break
        if not pid:
            pid = extract_id_from_url(url, config.URL_PATTERNS.get("id_from_url", "")) or sku or ""

        return {
            "id": pid, "url": url, "title": title, "brand": None,
            "sku": sku, "reference": sku, "price": price,
            "price_numeric": special_price or price, "old_price": old_price,
            "special_price": special_price, "discount": discount,
            "availability": availability,
            "availability_per_shop": availability_per_shop or None,
            "description": description, "specs": specs,
            "image_main": image_main, "images": images,
        }


def run() -> None:
    MytekScraper.create().start()

if __name__ == "__main__":
    run()
