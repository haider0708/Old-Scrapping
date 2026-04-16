"""Scoop Gaming — Shop-specific scraper. PrestaShop TvCMS. PW cats, SSR rest."""
from __future__ import annotations
import json
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url
from common.pipeline import BaseScraper
from . import config_new as config


class ScoopScraper(BaseScraper):
    shop_name = "scoop"
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
            if not top_a: continue
            span_el = top_li.css_first(cs.get("top_name_span", "a > span"))
            img_el = top_li.css_first(cs.get("top_name_img_alt", "a > img"))
            if span_el: top_name = parse_node_text(span_el)
            elif img_el: top_name = parse_node_attr(img_el, "alt") or parse_node_text(top_a)
            else: top_name = parse_node_text(top_a)
            top_url = abs_url(parse_node_attr(top_a, "href"), _base)
            top_id = extract_id_from_url(top_url, _pat) or extract_slug_from_url(top_url) or f"top_{top_idx}"
            if top_url and top_url not in seen_urls: seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url or None, "parent_id": None, "level": "top"})

            children_seen: set[str] = set()
            last_header_id: str | None = None
            # Pattern 1: UL dropdown
            for low_a in top_li.css(cs["low_items_dropdown"]):
                low_url = abs_url(parse_node_attr(low_a, "href"), _base)
                if not low_url or low_url in seen_urls or low_url in children_seen: continue
                children_seen.add(low_url); seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})
                last_header_id = str(low_id)
                parent_li = low_a.parent
                if parent_li:
                    pclasses = (parent_li.attributes or {}).get("class") or ""
                    if "parent" in pclasses:
                        for sub_a in parent_li.css("ul.menu-dropdown > li.level-3 > a"):
                            sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                            if not sub_url or sub_url in seen_urls or sub_url in children_seen: continue
                            children_seen.add(sub_url); seen_urls.add(sub_url)
                            sub_id = extract_id_from_url(sub_url, _pat) or extract_slug_from_url(sub_url)
                            categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": str(low_id), "level": "sub"})
            # Pattern 2: mega columns
            for mega_a in top_li.css(cs["low_items_mega"]):
                mega_url = abs_url(parse_node_attr(mega_a, "href"), _base)
                if not mega_url or mega_url in seen_urls or mega_url in children_seen: continue
                children_seen.add(mega_url); seen_urls.add(mega_url)
                mega_id = extract_id_from_url(mega_url, _pat) or extract_slug_from_url(mega_url)
                categories.append({"id": str(mega_id), "name": parse_node_text(mega_a), "url": mega_url, "parent_id": str(top_id), "level": "low"})
                last_header_id = str(mega_id)
            for line_a in top_li.css(cs["sub_items_mega"]):
                line_url = abs_url(parse_node_attr(line_a, "href"), _base)
                if not line_url or line_url in seen_urls or line_url in children_seen: continue
                children_seen.add(line_url); seen_urls.add(line_url)
                line_id = extract_id_from_url(line_url, _pat) or extract_slug_from_url(line_url)
                categories.append({"id": str(line_id), "name": parse_node_text(line_a), "url": line_url, "parent_id": last_header_id or str(top_id), "level": "sub"})
        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        products = []
        _base = config.BASE_URL
        grid_scope = ls.get("grid_scope")
        av_cfg = ls.get("availability", {})
        for elem in tree.css(ls["element"]):
            pid = parse_node_attr(elem, ls["id_attr"])
            if not pid: continue
            scope = elem.css_first(grid_scope) if grid_scope else elem
            if not scope: scope = elem
            name_el = scope.css_first(ls["name"]) or scope.css_first(ls.get("name_alt", "")) or elem.css_first(ls["url"])
            url_el = scope.css_first(ls["url"]) or elem.css_first(ls["url"])
            url = abs_url(parse_node_attr(url_el, "href"), _base) if url_el else ""
            name = parse_node_text(name_el) if name_el else ""
            img_el = scope.css_first(ls["image"]) or elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url: break
            img_url = abs_url(img_url, _base) if img_url else ""
            price = parse_node_text(scope.css_first(ls["price"]) or elem.css_first(ls["price"]))
            old_price = parse_node_text(scope.css_first(ls["old_price"]) or elem.css_first(ls["old_price"]))
            availability = ""
            oos = scope.css_first(av_cfg.get("out_of_stock_button", "")) or scope.css_first(av_cfg.get("catalog_view_oos", ""))
            ins = scope.css_first(av_cfg.get("in_stock_button", "")) or scope.css_first(av_cfg.get("catalog_view_in_stock", ""))
            if oos: availability = "Rupture"
            elif ins: availability = "En stock"
            products.append({"id": pid, "name": name, "url": url, "category_url": category_url, "image": img_url, "price": price, "old_price": old_price, "availability": availability})
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        next_a = tree.css_first(config.PAGINATION_SELECTORS["next_page"])
        if not next_a: return None
        href = parse_node_attr(next_a, "href")
        return abs_url(href, config.BASE_URL) if href else None

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]
        pid = extract_id_from_url(url, _pat) or ""
        json_el = tree.css_first(sel.get("json_data", ""))
        if json_el:
            j_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
            if j_str:
                try:
                    data = json.loads(j_str.replace("&quot;", '"'))
                    if not pid and data.get("id_product"): pid = str(data["id_product"])
                except (json.JSONDecodeError, ValueError): pass
        title = parse_node_text(tree.css_first(sel["title"]))
        brand_el = tree.css_first(sel.get("brand", ""))
        brand = abs_url(parse_node_attr(brand_el, sel.get("brand_attr", "src")), _base) if brand_el else ""
        sku = parse_node_text(tree.css_first(sel.get("reference", "")))
        price_el = tree.css_first(sel["price"])
        price = parse_node_text(price_el)
        price_content = parse_node_attr(price_el, sel.get("price_content_attr", "content")) if price_el else ""
        price_numeric = price_content or price
        old_price = parse_node_text(tree.css_first(sel.get("old_price", "")))
        avail_el = tree.css_first(sel.get("global_availability", ""))
        availability = parse_node_text(avail_el) if avail_el else ""
        schema_el = tree.css_first(sel.get("availability_schema", ""))
        if schema_el:
            href = parse_node_attr(schema_el, "href")
            if "InStock" in href: availability = availability or "En stock"
            elif "OutOfStock" in href: availability = availability or "Rupture"
        desc_el = tree.css_first(sel.get("description_fallback", ""))
        if not desc_el:
            for node in tree.css("div[id^='product-description-short-']"): desc_el = node; break
        description = parse_node_text(desc_el) if desc_el else ""
        if not description:
            full = tree.css_first(sel.get("full_description", ""))
            if full: description = parse_node_text(full)
        specs_dict: dict[str, str] = {}
        specs_cfg = sel.get("specs")
        if specs_cfg:
            sc = tree.css_first(specs_cfg["container"])
            if sc:
                for dt, dd in zip(sc.css(specs_cfg["key"]), sc.css(specs_cfg["value"])):
                    k, v = parse_node_text(dt), parse_node_text(dd)
                    if k and v: specs_dict[k] = v
        imgs = sel.get("images", {})
        images_list: list[str] = []
        for img_el in tree.css(imgs.get("main", "")):
            src = parse_node_attr(img_el, "src")
            if src: images_list.append(abs_url(src, _base))
        for thumb in tree.css(imgs.get("thumbnails", "")):
            src = parse_node_attr(thumb, "src") or parse_node_attr(thumb, "data-image-large-src")
            if src:
                full = abs_url(src, _base)
                if full not in images_list: images_list.append(full)
        if not pid: pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": brand or None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "availability": availability,
            "description": description, "specs": specs_dict,
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    ScoopScraper().start()

if __name__ == "__main__":
    run()
