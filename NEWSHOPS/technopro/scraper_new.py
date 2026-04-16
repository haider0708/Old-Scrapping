"""Technopro — Shop-specific scraper. PrestaShop IQit MegaMenu. PW cats, SSR rest."""
from __future__ import annotations
import json
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, css_first_safe
from common.pipeline import BaseScraper
from . import config_new as config


class TechnoproScraper(BaseScraper):
    shop_name = "technopro"
    shop_config = config
    use_playwright_for_categories = True

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        link_fb = cs.get("link_fallback", "a[href]")
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            top_a = top_li.css_first(cs.get("top_link") or link_fb) or top_li.css_first(link_fb)
            if not top_a:
                continue
            top_name_el = top_li.css_first(cs.get("top_name"))
            top_name = parse_node_text(top_name_el) if top_name_el else parse_node_text(top_a)
            top_url = abs_url(parse_node_attr(top_a, "href"), _base)
            top_id = extract_id_from_url(top_url, _pat) or extract_slug_from_url(top_url) or f"top_{top_idx}"
            if top_url and top_url not in seen_urls:
                seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url or None, "parent_id": None, "level": "top"})

            mega_panel = top_li.css_first(cs.get("mega_panel", "div.cbp-hrsub"))
            if not mega_panel:
                continue
            for col in mega_panel.css(cs.get("low_columns", "div.cbp-menu-column")):
                low_title_link = (
                    col.css_first("p strong a")
                    or col.css_first(".menu-title a")
                )
                low_id: str | None = None
                if low_title_link:
                    low_url = abs_url(parse_node_attr(low_title_link, "href"), _base)
                    low_name = parse_node_text(low_title_link)
                    if low_url and low_url not in seen_urls:
                        seen_urls.add(low_url)
                        low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                        categories.append({"id": str(low_id), "name": low_name, "url": low_url, "parent_id": str(top_id), "level": "low"})
                for sub_a in col.css(cs.get("sub_items", "ul li > a")):
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                    if not sub_url or sub_url in seen_urls:
                        continue
                    seen_urls.add(sub_url)
                    sub_id = extract_id_from_url(sub_url, _pat) or extract_slug_from_url(sub_url)
                    categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": str(low_id) if low_id else str(top_id), "level": "sub"})
        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        products = []
        _base = config.BASE_URL
        av_cfg = ls.get("availability", {})

        for elem in tree.css(ls["element"]):
            pid = parse_node_attr(elem, ls["id_attr"])
            if not pid:
                continue
            name_el = elem.css_first(ls["name"]) or elem.css_first(ls["url"])
            url_el = elem.css_first(ls["url"])
            url = abs_url(parse_node_attr(url_el, "href"), _base) if url_el else ""
            name = parse_node_text(name_el) if name_el else ""
            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, _base) if img_url else ""
            price_el = elem.css_first(ls["price"])
            price = parse_node_text(price_el)
            price_numeric = parse_node_attr(price_el, ls.get("price_content_attr", "content")) if price_el else price
            if not price_numeric:
                price_numeric = price
            old_price = parse_node_text(elem.css_first(ls["old_price"]))
            availability = ""
            if css_first_safe(elem, av_cfg.get("in_stock")):
                availability = "En stock"
            elif css_first_safe(elem, av_cfg.get("out_of_stock")):
                availability = "Rupture"
            elif css_first_safe(elem, av_cfg.get("orderable_oos")):
                availability = "Commander (rupture)"
            products.append({"id": pid, "name": name, "url": url, "category_url": category_url, "image": img_url, "price": price, "price_numeric": price_numeric, "old_price": old_price, "availability": availability})
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        ps = config.PAGINATION_SELECTORS
        next_a = tree.css_first(ps["next_page"])
        if not next_a:
            next_a = tree.css_first(ps.get("next_page_fallback", ""))
        if not next_a:
            return None
        href = parse_node_attr(next_a, "href")
        return abs_url(href, config.BASE_URL) if href else None

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]
        pid = extract_id_from_url(url, _pat) or ""
        json_el = css_first_safe(tree, sel.get("json_data"))
        if json_el:
            j_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
            if j_str:
                try:
                    data = json.loads(j_str.replace("&quot;", '"'))
                    if not pid and data.get("id_product"):
                        pid = str(data["id_product"])
                except (json.JSONDecodeError, ValueError):
                    pass
        title = parse_node_text(tree.css_first(sel["title"]))
        brand_el = css_first_safe(tree, sel.get("brand"))
        brand = (parse_node_attr(brand_el, sel.get("brand_attr", "alt")) or parse_node_text(brand_el)) if brand_el else ""
        sku = parse_node_text(css_first_safe(tree, sel.get("reference")))
        price_el = tree.css_first(sel["price"])
        price = parse_node_text(price_el)
        price_content = parse_node_attr(price_el, sel.get("price_content_attr", "content")) if price_el else ""
        price_numeric = price_content or price
        old_price = parse_node_text(tree.css_first(sel.get("old_price", "")))
        discount = parse_node_text(css_first_safe(tree, sel.get("discount")))
        avail_el = css_first_safe(tree, sel.get("global_availability"))
        availability = parse_node_text(avail_el) if avail_el else ""
        schema_el = css_first_safe(tree, sel.get("availability_schema"))
        if schema_el:
            href = parse_node_attr(schema_el, "href")
            if "InStock" in href:
                availability = availability or "En stock"
            elif "OutOfStock" in href:
                availability = availability or "Rupture"
        description = parse_node_text(css_first_safe(tree, sel.get("description"))) or parse_node_text(css_first_safe(tree, sel.get("description_short")))
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
        main_el = css_first_safe(tree, imgs.get("main"))
        if main_el:
            for attr in imgs.get("main_attrs", ["src", "data-src"]):
                src = parse_node_attr(main_el, attr)
                if src:
                    images_list.append(abs_url(src, _base))
                    break
        for img_el in tree.css(imgs.get("gallery", "")):
            for attr in imgs.get("gallery_attrs", ["src", "data-src"]):
                src = parse_node_attr(img_el, attr)
                if src:
                    full = abs_url(src, _base)
                    if full not in images_list:
                        images_list.append(full)
                    break
        if not pid:
            pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": brand or None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "discount": discount or None, "availability": availability,
            "description": description, "specs": specs_dict,
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    TechnoproScraper().start()

if __name__ == "__main__":
    run()
