"""
Geant e-commerce scraper — shop-specific parsing only.
Platform: PrestaShop + WB MegaMenu. NO detail pages — listing data used directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

from selectolax.parser import HTMLParser

_shop_dir = Path(__file__).resolve().parent
_project_root = _shop_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_shop_dir) not in sys.path:
    sys.path.insert(0, str(_shop_dir))

from common.pipeline import BaseScraper
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible, css_first_safe
import config_new as config


class GeantScraper(BaseScraper):
    shop_name = "geant"
    shop_config = config
    skip_details = True  # No detail page — listing data becomes details

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        base = config.BASE_URL
        id_pat = config.URL_PATTERNS["id_from_url"]
        link_fb = cs.get("link_fallback", "a[href]")

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            if not is_visible(top_li):
                continue
            name_el = css_first_safe(top_li, cs.get("top_name"))
            top_name = parse_node_text(name_el) if name_el else ""
            if not top_name:
                continue

            top_id = f"top_{top_idx}"
            top_url = None
            if cs.get("top_link"):
                top_a = top_li.css_first(cs["top_link"]) or top_li.css_first(link_fb)
                if top_a:
                    top_url = abs_url(parse_node_attr(top_a, "href"), base)
                    if top_url:
                        top_id = extract_id_from_url(top_url, id_pat) or extract_slug_from_url(top_url, sanitize_pattern=config.URL_PATTERNS.get("slug_sanitize"))
                        seen_urls.add(top_url)

            categories.append({"id": str(top_id), "name": top_name, "url": top_url, "parent_id": None, "level": "top"})

            for low_li in top_li.css(cs["low_items"]):
                if not is_visible(low_li):
                    continue
                low_a = low_li.css_first(cs.get("low_link", "")) or low_li.css_first(link_fb)
                if not low_a:
                    continue
                low_url = abs_url(parse_node_attr(low_a, "href"), base)
                if not low_url or low_url in seen_urls:
                    continue
                seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, id_pat) or extract_slug_from_url(low_url, sanitize_pattern=config.URL_PATTERNS.get("slug_sanitize"))
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

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

            name_el = elem.css_first(ls.get("name", "")) or elem.css_first(ls.get("url", ""))
            url_el = elem.css_first(ls.get("url", ""))
            url = abs_url(parse_node_attr(url_el, "href"), base) if url_el else ""
            name = parse_node_text(name_el) if name_el else ""

            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls.get("image_attrs", ["src"]):
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, base) if img_url else ""

            price = parse_node_text(elem.css_first(ls["price"]))
            brand = parse_node_text(css_first_safe(elem, ls.get("brand")))
            desc = parse_node_text(css_first_safe(elem, ls.get("description_short")))

            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "brand": brand,
                "description_short": desc, "availability": "",
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
        raise NotImplementedError("Geant has no detail pages")


def run() -> None:
    GeantScraper.create().start()

if __name__ == "__main__":
    run()
