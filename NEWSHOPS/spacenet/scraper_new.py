"""
Spacenet — Shop-specific scraper.
Platform: PrestaShop + SP Mega Menu. Full SSR.
"""

from __future__ import annotations

import json
from typing import Any

from selectolax.parser import HTMLParser

from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible
from common.pipeline import BaseScraper
from . import config_new as config


class SpacenetScraper(BaseScraper):
    shop_name = "spacenet"
    shop_config = config

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        link_fb = cs.get("link_fallback", "a[href]")

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            if not is_visible(top_li):
                continue
            top_a = top_li.css_first(cs.get("top_link") or link_fb) or top_li.css_first(link_fb)
            if not top_a:
                continue
            top_name_el = top_li.css_first(cs.get("top_name", ""))
            top_name = parse_node_text(top_name_el) if top_name_el else parse_node_text(top_a)
            top_url = abs_url(parse_node_attr(top_a, "href"), config.BASE_URL)
            top_id = extract_id_from_url(top_url, config.URL_PATTERNS["id_from_url"]) or extract_slug_from_url(top_url) or f"top_{top_idx}"
            if top_url and top_url not in seen_urls:
                seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url or None, "parent_id": None, "level": "top"})

            for low_li in top_li.css(cs["low_items"]):
                if not is_visible(low_li):
                    continue
                low_a = low_li.css_first(cs.get("low_link") or link_fb) or low_li.css_first(link_fb)
                if not low_a:
                    continue
                low_url = abs_url(parse_node_attr(low_a, "href"), config.BASE_URL)
                if not low_url or low_url in seen_urls:
                    continue
                seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, config.URL_PATTERNS["id_from_url"]) or extract_slug_from_url(low_url)
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

                for sub_a in low_li.css(cs["sub_items"]):
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), config.BASE_URL)
                    if not sub_url or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    sub_id = extract_id_from_url(sub_url, config.URL_PATTERNS["id_from_url"]) or extract_slug_from_url(sub_url)
                    categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": str(low_id), "level": "sub"})

        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        products = []
        for elem in tree.css(ls["element"]):
            pid = parse_node_attr(elem, ls["id_attr"])
            if not pid:
                continue
            name_el = elem.css_first(ls["name"]) or elem.css_first(ls["url"])
            url_el = elem.css_first(ls["url"])
            url = abs_url(parse_node_attr(url_el, "href"), config.BASE_URL) if url_el else ""
            name = parse_node_text(name_el) if name_el else ""
            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, config.BASE_URL) if img_url else ""
            price = parse_node_text(elem.css_first(ls["price"]))
            old_price = parse_node_text(elem.css_first(ls["old_price"]))
            ref_el = elem.css_first(ls.get("reference", ""))
            reference = parse_node_text(ref_el) if ref_el else ""
            brand_el = elem.css_first(ls.get("brand", ""))
            brand = parse_node_attr(brand_el, ls.get("brand_attr", "alt")) if brand_el else ""
            av_config = ls.get("availability", {})
            availability = ""
            if av_config:
                in_stock = elem.css_first(av_config.get("in_stock", ""))
                in_arrivage = elem.css_first(av_config.get("in_arrivage", ""))
                if in_stock:
                    availability = parse_node_text(in_stock) or "En stock"
                elif in_arrivage:
                    availability = parse_node_text(in_arrivage) or "En arrivage"
            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "price_numeric": price,
                "old_price": old_price, "reference": reference, "brand": brand,
                "availability": availability,
            })
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        next_a = tree.css_first(config.PAGINATION_SELECTORS["next_page"])
        if not next_a:
            return None
        href = parse_node_attr(next_a, "href")
        return abs_url(href, config.BASE_URL) if href else None

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        _base = config.BASE_URL
        _pat = config.URL_PATTERNS["id_from_url"]

        def _text(css):
            if not css: return ""
            n = tree.css_first(css)
            return parse_node_text(n)

        def _attr(css, attr):
            if not css: return ""
            n = tree.css_first(css)
            return parse_node_attr(n, attr)

        pid = extract_id_from_url(url, _pat) or ""
        json_el = tree.css_first(sel.get("json_data", ""))
        if json_el:
            json_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
            if json_str:
                try:
                    data = json.loads(json_str.replace("&quot;", '"'))
                    if not pid and data.get("id_product"):
                        pid = str(data["id_product"])
                except (json.JSONDecodeError, ValueError):
                    pass

        title = _text(sel["title"])
        brand_el = tree.css_first(sel.get("brand", ""))
        brand = parse_node_attr(brand_el, sel.get("brand_attr", "alt")) if brand_el else ""
        sku = _text(sel.get("reference", ""))
        price_el = tree.css_first(sel["price"])
        price = parse_node_text(price_el)
        price_content = parse_node_attr(price_el, sel.get("price_content_attr", "content")) if price_el else ""
        price_numeric = price_content or price
        old_price = _text(sel.get("old_price", ""))
        avail_el = tree.css_first(sel.get("global_availability", ""))
        availability = parse_node_text(avail_el) if avail_el else ""
        schema_el = tree.css_first(sel.get("availability_schema", ""))
        if schema_el:
            href = parse_node_attr(schema_el, "href")
            if "InStock" in href:
                availability = availability or "En stock"
            elif "OutOfStock" in href:
                availability = availability or "Rupture"
        # Per-shop availability
        per_shop: list[dict] = []
        ps_cfg = sel.get("availability_per_shop")
        if ps_cfg:
            container = tree.css_first(ps_cfg.get("container", ""))
            if container:
                for row in container.css(ps_cfg.get("row", "")):
                    shop_name = parse_node_text(row.css_first(ps_cfg.get("shop_name", "")))
                    status = parse_node_text(row.css_first(ps_cfg.get("shop_status", "")))
                    if shop_name:
                        per_shop.append({"shop": shop_name, "status": status})
        description = _text(sel.get("description", "")) or _text(sel.get("description_fallback", ""))
        specs_dict: dict[str, str] = {}
        specs_cfg = sel.get("specs")
        if specs_cfg:
            sc = tree.css_first(specs_cfg["container"])
            if sc:
                for dt, dd in zip(sc.css(specs_cfg["key"]), sc.css(specs_cfg["value"])):
                    k, v = parse_node_text(dt), parse_node_text(dd)
                    if k and v:
                        specs_dict[k] = v
        imgs = sel.get("images", {})
        images_list: list[str] = []
        main_el = tree.css_first(imgs.get("main", ""))
        if main_el:
            src = parse_node_attr(main_el, "src")
            if src:
                images_list.append(abs_url(src, _base))
        thumb_attr = imgs.get("thumbnail_attr", "data-image-large-src")
        for thumb in tree.css(imgs.get("thumbnails", "")):
            src = parse_node_attr(thumb, thumb_attr) or parse_node_attr(thumb, "src")
            if src:
                full = abs_url(src, _base)
                if full not in images_list:
                    images_list.append(full)
        if not pid:
            pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": brand or None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "availability": availability,
            "availability_per_shop": per_shop or None, "description": description,
            "specs": specs_dict, "image_main": images_list[0] if images_list else "",
            "images": images_list,
        }


def run():
    SpacenetScraper().start()

if __name__ == "__main__":
    run()
