"""
Darty e-commerce scraper — shop-specific parsing only.
Platform: PrestaShop + GloboMegaMenu. Fully SSR.
"""

from __future__ import annotations

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
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url
import config_new as config


class DartyScraper(BaseScraper):
    shop_name = "darty"
    shop_config = config

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        base = config.BASE_URL
        id_pat = config.URL_PATTERNS["id_from_url"]

        for nav_li in tree.css(cs["nav_container"]):
            first_top_id = None
            for top_li in nav_li.css(cs["top_items"]):
                top_a = top_li.css_first(cs["top_link"])
                if not top_a:
                    continue
                id_attr = cs.get("top_id_attr")
                top_id = parse_node_attr(top_li, id_attr) if id_attr else None
                if not top_id:
                    top_id = extract_id_from_url(parse_node_attr(top_a, "href"), id_pat)
                if not top_id:
                    continue
                if first_top_id is None:
                    first_top_id = top_id
                top_url = abs_url(parse_node_attr(top_a, "href"), base)
                name_el = top_li.css_first(cs.get("top_name", ""))
                top_name = parse_node_text(name_el) if name_el else parse_node_text(top_a)
                if top_url in seen_urls:
                    continue
                seen_urls.add(top_url)
                categories.append({"id": top_id, "name": top_name, "url": top_url, "parent_id": None, "level": "top"})

            for low_li in nav_li.css(cs["low_items"]):
                low_a = low_li.css_first(cs["low_link"])
                if not low_a:
                    continue
                low_url = abs_url(parse_node_attr(low_a, "href"), base)
                low_id = extract_id_from_url(low_url, id_pat)
                if not low_id or low_url in seen_urls:
                    continue
                seen_urls.add(low_url)
                categories.append({"id": low_id, "name": parse_node_text(low_a), "url": low_url, "parent_id": first_top_id, "level": "low"})

                for sub_li in low_li.css(cs["sub_items"]):
                    sub_a = sub_li.css_first(cs["sub_link"])
                    if not sub_a:
                        continue
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), base)
                    sub_id = extract_id_from_url(sub_url, id_pat)
                    if not sub_id or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    categories.append({"id": sub_id, "name": parse_node_text(sub_a), "url": sub_url, "parent_id": low_id, "level": "sub"})

        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        base = config.BASE_URL
        id_pat = config.URL_PATTERNS["id_from_url"]
        products = []

        for art in tree.css(ls["element"]):
            pid = parse_node_attr(art, ls["id"])
            if not pid:
                url_el = art.css_first(ls["url"])
                pid = extract_id_from_url(parse_node_attr(url_el, "href"), id_pat) if url_el else ""
            if not pid:
                continue

            name_el = art.css_first(ls["name"])
            url = abs_url(parse_node_attr(name_el, "href"), base) if name_el else ""
            name = parse_node_text(name_el)

            img_el = art.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls.get("image_attrs", ["src"]):
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, base) if img_url else ""

            price_el = art.css_first(ls["price"])
            price = parse_node_text(price_el)
            if not price and ls.get("price_attr"):
                price = parse_node_attr(price_el, ls["price_attr"])
            pd_el = art.css_first(ls.get("price_display", ""))
            price_display = parse_node_text(pd_el) if pd_el else ""

            av = ls.get("availability", {})
            availability = ""
            schema_el = art.css_first(av.get("schema", ""))
            if schema_el:
                availability = parse_node_attr(schema_el, "href")
            cart_el = art.css_first(av.get("cart_button_status", ""))
            if cart_el:
                status = parse_node_attr(cart_el, "data-status")
                if status:
                    availability = availability or status

            cat_el = art.css_first(ls.get("category", ""))
            category = parse_node_text(cat_el) if cat_el else ""
            features = [parse_node_text(f) for f in art.css(ls.get("features", ""))]

            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price or price_display, "price_display": price_display,
                "category": category, "features": features, "availability": availability,
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
        id_pat = config.URL_PATTERNS["id_from_url"]

        def _text(css):
            if not css:
                return ""
            n = tree.css_first(css)
            return parse_node_text(n)

        title = _text(sel["title"])
        tp = sel.get("title_parts", {})
        cat_part = _text(tp.get("category"))
        name_part = _text(tp.get("name"))

        brand_conf = sel.get("brand")
        brand = ""
        if isinstance(brand_conf, dict):
            bc = tree.css_first(brand_conf.get("container", ""))
            brand = parse_node_text(bc) if bc else ""
        elif brand_conf:
            brand = _text(brand_conf)

        price = _text(sel["price"])
        old_price = _text(sel.get("old_price"))
        savings = _text(sel.get("savings"))
        promo = bool(tree.css_first(sel.get("promo_flag", "")))

        avail_el = tree.css_first(sel.get("global_availability", ""))
        availability = parse_node_attr(avail_el, "href") if avail_el else ""

        aps = sel.get("availability_per_shop", {})
        availability_per_shop = []
        if aps:
            cont = tree.css_first(aps.get("container", ""))
            if cont:
                for row in cont.css(aps.get("row", "")):
                    n_el = row.css_first(aps.get("name", ""))
                    s_el = row.css_first(aps.get("status", ""))
                    availability_per_shop.append({"name": parse_node_text(n_el), "status": parse_node_text(s_el)})

        imgs = sel.get("images", {})
        image_main = ""
        images_list: list[str] = []
        for img in tree.css(imgs.get("main", "")):
            for a in imgs.get("main_attrs", ["src"]):
                src = parse_node_attr(img, a)
                if src:
                    full = abs_url(src, base)
                    images_list.append(full)
                    if not image_main:
                        image_main = full
                    break

        features_short = [parse_node_text(f) for f in tree.css(sel.get("features_short", ""))]

        specs: dict[str, str] = {}
        sc = sel.get("specs", {})
        if sc:
            cont = tree.css_first(sc.get("container", ""))
            if cont:
                for row in cont.css(sc.get("row", "")):
                    k = parse_node_text(row.css_first(sc.get("key", "")))
                    v = parse_node_text(row.css_first(sc.get("value", "")))
                    if k and v:
                        specs[k] = v

        inst = sel.get("installment", {})
        monthly_price = ""
        if inst:
            ic = tree.css_first(inst.get("container", ""))
            if ic:
                mp = ic.css_first(inst.get("monthly_price", ""))
                monthly_price = parse_node_text(mp) if mp else ""

        schema_el = tree.css_first(sel.get("schema_availability", ""))
        schema_av = parse_node_attr(schema_el, "href") if schema_el else ""
        pid = extract_id_from_url(url, id_pat) or ""

        return {
            "id": pid, "url": url, "title": title or name_part,
            "title_category": cat_part, "title_name": name_part,
            "brand": brand, "price": price, "old_price": old_price,
            "savings": savings, "promo_flag": promo, "availability": availability,
            "availability_per_shop": availability_per_shop,
            "image_main": image_main, "images": images_list,
            "features_short": features_short, "specs": specs,
            "installment_monthly_price": monthly_price, "schema_availability": schema_av,
        }


def run() -> None:
    DartyScraper.create().start()

if __name__ == "__main__":
    run()
