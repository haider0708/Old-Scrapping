"""
Expert Gaming e-commerce scraper — shop-specific parsing only.
Platform: WooCommerce + Elementor + YITH.
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
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_slug_from_url
import config_new as config


class ExpertGamingScraper(BaseScraper):
    shop_name = "expert_gaming"
    shop_config = config
    use_playwright_for_categories = True

    @staticmethod
    def _cat_id_from_li(li_node: Any) -> str | None:
        id_attr = parse_node_attr(li_node, "id") if li_node else ""
        pat = config.URL_PATTERNS.get("category_id_from_li")
        if not pat or not id_attr:
            return None
        m = re.search(pat, id_attr)
        return m.group(1) if m else None

    @staticmethod
    def _slug(url: str) -> str:
        return extract_slug_from_url(url, strip_segments=("product-category",), sanitize_pattern=config.URL_PATTERNS.get("slug_sanitize"))

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        base = config.BASE_URL
        link_fb = cs.get("link_fallback", "a[href]")

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            top_a = top_li.css_first(cs.get("top_link") or link_fb) or top_li.css_first(link_fb)
            name_el = top_li.css_first(cs.get("top_name", ""))
            top_name = parse_node_text(name_el) if name_el else parse_node_text(top_a)
            top_url = abs_url(parse_node_attr(top_a, "href"), base) if top_a else ""
            top_id = self._cat_id_from_li(top_li) or self._slug(top_url) or f"top_{top_idx}"

            if top_url and top_url not in seen_urls:
                seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url or None, "parent_id": None, "level": "top"})

            sub_menu = top_li.css_first(cs.get("sub_menu", ""))
            if not sub_menu:
                continue

            for block in sub_menu.css(cs["low_blocks"]):
                low_a = block.css_first(cs["low_link"]) or block.css_first(link_fb)
                if low_a:
                    low_url = abs_url(parse_node_attr(low_a, "href"), base)
                    low_id = self._slug(low_url)
                    if low_url and low_url not in seen_urls:
                        seen_urls.add(low_url)
                        categories.append({"id": low_id, "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

                for sub_li in block.css(cs["sub_items"]):
                    sub_a = sub_li.css_first(cs["sub_link"]) or sub_li.css_first(link_fb)
                    if not sub_a:
                        continue
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), base)
                    sub_id = self._slug(sub_url)
                    if not sub_url or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    parent = self._slug(parse_node_attr(low_a, "href")) if low_a else str(top_id)
                    categories.append({"id": sub_id, "name": parse_node_text(sub_a), "url": sub_url, "parent_id": parent, "level": "sub"})

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
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, base) if img_url else ""

            price_el = elem.css_first(ls.get("sale_price", "")) or elem.css_first(ls["price"])
            price = parse_node_text(price_el)
            old_price = parse_node_text(elem.css_first(ls["old_price"]))

            elem_classes = (elem.attributes or {}).get("class") or ""
            av = ls["availability"]
            if av.get("instock_class") and av["instock_class"] in elem_classes:
                availability = "En stock"
            elif av.get("outofstock_class") and av["outofstock_class"] in elem_classes:
                availability = "Rupture"
            else:
                availability = ""

            cats = [parse_node_text(a) for a in elem.css(ls.get("categories_selector", "")) if parse_node_text(a)]
            brands = [parse_node_text(a) for a in elem.css(ls.get("brands_selector", "")) if parse_node_text(a)]
            cart_btn = elem.css_first(ls.get("cart_button", ""))
            sku = parse_node_attr(cart_btn, ls.get("sku_attr", "")) if cart_btn else ""

            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "old_price": old_price,
                "availability": availability, "categories": cats, "brands": brands, "sku": sku,
            })
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        next_a = tree.css_first(config.PAGINATION_SELECTOR_NEXT)
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
        brand = _text(sel.get("brand"))
        sku = _text(sel.get("sku"))
        price = _text(sel.get("sale_price")) or _text(sel["price"])
        old_price = _text(sel["old_price"])

        avail_el = tree.css_first(sel.get("global_availability", ""))
        availability = parse_node_text(avail_el) if avail_el else ""
        if not availability:
            ad_el = tree.css_first(sel.get("availability_data", ""))
            if ad_el:
                for attr in sel.get("availability_data_attrs", []):
                    val = parse_node_attr(ad_el, attr)
                    if val:
                        availability = val
                        break

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
        sa = sel.get("specs_alt", {})
        if sa:
            alt_cont = tree.css_first(sa.get("container", ""))
            if alt_cont:
                for li in alt_cont.css(sa.get("items", "li")):
                    spans = li.css("span")
                    if len(spans) >= 2:
                        k, v = parse_node_text(spans[0]), parse_node_text(spans[1])
                        if k and v:
                            specs[k] = v

        images: list[str] = []
        image_main = ""
        ic = sel.get("images", {})
        for img in tree.css(ic.get("main", "")):
            for a in ic.get("main_attrs", ["src"]):
                src = parse_node_attr(img, a)
                if src:
                    full = abs_url(src, base)
                    images.append(full)
                    if not image_main:
                        image_main = full
                    break

        pid = parse_node_attr(tree.css_first(f"[data-product_id]"), "data-product_id") if tree.css_first("[data-product_id]") else sku
        return {
            "id": pid or sku, "url": url, "title": title, "brand": brand,
            "sku": sku, "price": price, "old_price": old_price,
            "availability": availability, "description": description,
            "specs": specs, "image_main": image_main, "images": images,
        }


def run() -> None:
    ExpertGamingScraper.create().start()

if __name__ == "__main__":
    run()
