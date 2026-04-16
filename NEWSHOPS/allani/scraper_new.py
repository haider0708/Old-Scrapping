"""
Allani e-commerce scraper — shop-specific parsing only.
Platform: PrestaShop (standard dropdown menu).
All pipeline logic comes from common.pipeline.BaseScraper.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

from selectolax.parser import HTMLParser

# Allow importing config_new as config
_shop_dir = Path(__file__).resolve().parent
_project_root = _shop_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_shop_dir) not in sys.path:
    sys.path.insert(0, str(_shop_dir))

from common.pipeline import BaseScraper
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url
import config_new as config


class AllaniScraper(BaseScraper):
    shop_name = "allani"
    shop_config = config

    # -- Categories ----------------------------------------------------------

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        base = config.BASE_URL

        top_lis = tree.css(cs["top_items"])
        for top_li in top_lis:
            top_a = top_li.css_first(cs["top_link"])
            if not top_a:
                continue

            # ID from li[id="category-{N}"] or from URL
            top_id = self._cat_id_from_li(top_li) or extract_id_from_url(
                parse_node_attr(top_a, "href"),
                config.URL_PATTERNS["id_from_url"],
            )
            if not top_id:
                continue

            top_url = abs_url(parse_node_attr(top_a, "href"), base)
            if top_url in seen_urls:
                continue
            seen_urls.add(top_url)

            categories.append({
                "id": top_id,
                "name": parse_node_text(top_a),
                "url": top_url,
                "parent_id": None,
                "level": "top",
            })

            for low_li in top_li.css(cs["low_items"]):
                low_a = low_li.css_first(cs["low_link"])
                if not low_a:
                    continue
                low_url = abs_url(parse_node_attr(low_a, "href"), base)
                low_id = extract_id_from_url(low_url, config.URL_PATTERNS["id_from_url"])
                if not low_id or low_url in seen_urls:
                    continue
                seen_urls.add(low_url)
                categories.append({
                    "id": low_id,
                    "name": parse_node_text(low_a),
                    "url": low_url,
                    "parent_id": top_id,
                    "level": "low",
                })

                for sub_li in low_li.css(cs["sub_items"]):
                    sub_a = sub_li.css_first(cs["sub_link"])
                    if not sub_a:
                        continue
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), base)
                    sub_id = extract_id_from_url(sub_url, config.URL_PATTERNS["id_from_url"])
                    if not sub_id or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    categories.append({
                        "id": sub_id,
                        "name": parse_node_text(sub_a),
                        "url": sub_url,
                        "parent_id": low_id,
                        "level": "sub",
                    })

        return categories

    @staticmethod
    def _cat_id_from_li(li_node: Any) -> str | None:
        lid = (li_node.attributes or {}).get("id") or ""
        m = re.search(config.URL_PATTERNS["category_id_from_li"], lid)
        return m.group(1) if m else None

    # -- Listings ------------------------------------------------------------

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        base = config.BASE_URL
        products = []

        for art in tree.css(ls["element"]):
            pid = parse_node_attr(art, ls["id"])
            if not pid:
                continue

            name_el = art.css_first(ls["name"])
            url = abs_url(parse_node_attr(name_el, "href"), base) if name_el else ""
            name = parse_node_text(name_el)

            img_el = art.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, base) if img_url else ""

            price = parse_node_text(art.css_first(ls["price"]))
            ref = parse_node_text(art.css_first(ls["reference"]))
            ean = parse_node_text(art.css_first(ls["ean"]))
            desc = parse_node_text(art.css_first(ls["description_short"]))
            promo = bool(art.css_first(ls["promo_flag"]))

            av_conf = ls["availability"]
            av_el = art.css_first(av_conf["selector"]) or art.css_first(av_conf.get("fallback", ""))
            availability = parse_node_text(av_el)

            products.append({
                "id": pid,
                "name": name,
                "url": url,
                "category_url": category_url,
                "image": img_url,
                "price": price,
                "reference": ref,
                "ean": ean,
                "description_short": desc,
                "promo_flag": promo,
                "availability": availability,
            })
        return products

    # -- Pagination ----------------------------------------------------------

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        next_a = tree.css_first(config.PAGINATION_SELECTOR_NEXT)
        if not next_a:
            return None
        href = parse_node_attr(next_a, "href")
        return abs_url(href, config.BASE_URL) if href else None

    # -- Detail --------------------------------------------------------------

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
        brand = _text(sel.get("brand"))
        price = _text(sel["price"])
        availability = _text(sel["global_availability"])
        reference = _text(sel["reference"])
        ean = _text(sel.get("ean"))
        description = _text(sel["description"])

        imgs = sel["images"]
        main_img = tree.css_first(imgs["main"])
        main_src = ""
        if main_img:
            for a in imgs["main_attrs"]:
                main_src = parse_node_attr(main_img, a)
                if main_src:
                    break
        main_src = abs_url(main_src, base) if main_src else ""

        thumb_urls = []
        for t in tree.css(imgs["thumbnails"]):
            for a in imgs["thumbnail_attrs"]:
                u = parse_node_attr(t, a)
                if u:
                    thumb_urls.append(abs_url(u, base))
                    break

        schema_el = tree.css_first(sel.get("schema_availability", ""))
        schema_av = parse_node_attr(schema_el, "href") if schema_el else ""

        pid = extract_id_from_url(url, config.URL_PATTERNS["id_from_url"]) or ""
        return {
            "id": pid,
            "url": url,
            "title": title,
            "brand": brand,
            "reference": reference,
            "ean": ean,
            "price": price,
            "availability": availability,
            "description": description,
            "image_main": main_src,
            "images_thumbnails": thumb_urls,
            "schema_availability": schema_av,
        }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run() -> None:
    AllaniScraper.create().start()


if __name__ == "__main__":
    run()
