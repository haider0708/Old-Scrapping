"""SBS — Shop-specific scraper. PrestaShop + TvCMS MegaMenu. Full CSR (BrowserPool)."""
from __future__ import annotations
import json
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url
from common.pipeline import BaseScraper
from . import config_new as config


class SbsScraper(BaseScraper):
    shop_name = "sbs"
    shop_config = config
    use_playwright_for_categories = True
    use_playwright_for_listings = True
    use_playwright_for_details = True

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]
        nav = tree.css_first(cs["nav_container"])
        if not nav:
            self.log.warning("Nav container not found")
            return []
        last_parent_by_depth: dict[int, str] = {}
        _depth_to_level = {0: "top", 1: "low"}
        for li in nav.css("li[data-depth]"):
            depth_str = parse_node_attr(li, "data-depth")
            try: depth = int(depth_str)
            except (ValueError, TypeError): continue
            a_el = li.css_first("a")
            if not a_el: continue
            cat_url = abs_url(parse_node_attr(a_el, "href"), _base)
            cat_name = parse_node_text(a_el)
            cat_id = extract_id_from_url(cat_url, _pat) or extract_slug_from_url(cat_url) or f"cat_{len(categories)}"
            if not cat_url or cat_url in seen_urls: continue
            seen_urls.add(cat_url)
            parent_id = last_parent_by_depth.get(depth - 1) if depth > 0 else None
            level = _depth_to_level.get(depth, "sub")
            categories.append({"id": str(cat_id), "name": cat_name, "url": cat_url, "parent_id": parent_id, "level": level})
            last_parent_by_depth[depth] = str(cat_id)
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
            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "old_price": old_price,
                "availability": availability,
            })
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
            json_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
            if json_str:
                try:
                    data = json.loads(json_str.replace("&quot;", '"'))
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
        stock_level = ""
        stock_bar = tree.css_first(sel.get("stock_bar", ""))
        if stock_bar:
            classes = (stock_bar.attributes or {}).get("class") or ""
            for lvl in sel.get("stock_bar_classes", []):
                if lvl in classes: stock_level = lvl; break
        desc_el = tree.css_first(sel.get("description_fallback", ""))
        if not desc_el:
            for node in tree.css("div[id^='product-description-short-']"):
                desc_el = node; break
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
            "stock_level": stock_level or None, "description": description,
            "specs": specs_dict, "image_main": images_list[0] if images_list else "",
            "images": images_list,
        }


def run():
    SbsScraper().start()

if __name__ == "__main__":
    run()
