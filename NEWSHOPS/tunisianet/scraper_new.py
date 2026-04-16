"""Tunisianet — Shop-specific scraper. PrestaShop + WB MegaMenu. Full SSR. JSON-primary detail."""
from __future__ import annotations
import json
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible
from common.pipeline import BaseScraper
from . import config_new as config


def _extract_images_from_json(imgs_raw: Any) -> list[str]:
    if not imgs_raw:
        return []
    images: list[str] = []
    if isinstance(imgs_raw, dict):
        for v in imgs_raw.values():
            if isinstance(v, dict):
                for key in ("large", "bySize", "medium_default", "home_default"):
                    if key in v:
                        target = v[key]
                        if isinstance(target, dict):
                            u = target.get("url", "")
                        elif isinstance(target, str):
                            u = target
                        else:
                            continue
                        if u and u not in images:
                            images.append(u)
                        break
    elif isinstance(imgs_raw, list):
        for item in imgs_raw:
            if isinstance(item, dict):
                for key in ("large", "bySize", "medium_default"):
                    if key in item:
                        target = item[key]
                        u = target.get("url", "") if isinstance(target, dict) else (target if isinstance(target, str) else "")
                        if u and u not in images:
                            images.append(u)
                        break
    return images


def _extract_features_from_json(feats_raw: Any) -> dict[str, str]:
    if not feats_raw:
        return {}
    specs: dict[str, str] = {}
    if isinstance(feats_raw, list):
        for f in feats_raw:
            if isinstance(f, dict):
                k = f.get("name", "")
                v = f.get("value", "")
                if k and v:
                    specs[k] = v
    return specs


class TunisianetScraper(BaseScraper):
    shop_name = "tunisianet"
    shop_config = config

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        link_fb = cs.get("link_fallback", "a[href]")
        _base = config.BASE_URL
        _pat = config.URL_PATTERNS["id_from_url"]

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            if not is_visible(top_li):
                continue
            top_name_el = top_li.css_first(cs.get("top_name", ""))
            top_name = parse_node_text(top_name_el) if top_name_el else ""
            if not top_name:
                continue
            top_id = f"top_{top_idx}"
            top_url = None
            categories.append({"id": str(top_id), "name": top_name, "url": top_url, "parent_id": None, "level": "top"})

            last_header_id: str | None = None
            for item_li in top_li.css(cs["low_items"]):
                item_a = item_li.css_first("a") or item_li.css_first(link_fb)
                if not item_a:
                    continue
                item_url = abs_url(parse_node_attr(item_a, "href"), _base)
                if not item_url or item_url in seen_urls:
                    continue
                seen_urls.add(item_url)
                item_id = extract_id_from_url(item_url, _pat) or extract_slug_from_url(item_url)
                item_class = (item_li.attributes or {}).get("class") or ""
                if "item-header" in item_class:
                    categories.append({"id": str(item_id), "name": parse_node_text(item_a), "url": item_url, "parent_id": str(top_id), "level": "low"})
                    last_header_id = str(item_id)

            for sub_a in top_li.css(cs["sub_items"]):
                sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                if not sub_url or sub_url in seen_urls:
                    continue
                seen_urls.add(sub_url)
                sub_id = extract_id_from_url(sub_url, _pat) or extract_slug_from_url(sub_url)
                categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": last_header_id or str(top_id), "level": "sub"})
        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        products = []
        _base = config.BASE_URL
        for elem in tree.css(ls["element"]):
            pid = parse_node_attr(elem, ls["id_attr"])
            if not pid:
                continue
            name_el = elem.css_first(ls["name"])
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
            price = parse_node_text(elem.css_first(ls["price"]))
            old_price = parse_node_text(elem.css_first(ls.get("old_price", "")))
            ref_el = elem.css_first(ls.get("reference", ""))
            reference = parse_node_text(ref_el) if ref_el else ""
            brand_el = elem.css_first(ls.get("brand", ""))
            brand = parse_node_attr(brand_el, ls.get("brand_attr", "alt")) if brand_el else ""
            desc_el = elem.css_first(ls.get("description_short", "")) or elem.css_first(ls.get("description_short_fallback", ""))
            desc = parse_node_text(desc_el) if desc_el else ""
            av = ls.get("availability", {})
            availability = ""
            if av.get("in_stock") and elem.css_first(av["in_stock"]):
                availability = parse_node_text(elem.css_first(av["in_stock"])) or "En stock"
            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "price_numeric": price,
                "old_price": old_price, "reference": reference, "brand": brand,
                "description_short": desc, "availability": availability,
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
        pid = extract_id_from_url(url, _pat) or ""
        title = ""; price = ""; price_numeric = ""; old_price = ""; discount = ""
        sku = ""; availability = ""; images_list: list[str] = []; specs_dict: dict[str, str] = {}

        json_el = tree.css_first(sel.get("json_data", ""))
        if json_el:
            json_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
            if json_str:
                try:
                    jd = json.loads(json_str.replace("&quot;", '"'))
                    jf = sel.get("json_fields", {})
                    if not pid and jd.get(jf.get("id", "id_product")):
                        pid = str(jd[jf["id"]])
                    title = jd.get(jf.get("name", "name"), "") or title
                    price = jd.get(jf.get("price_display", "price"), "") or str(jd.get(jf.get("price", "price_amount"), ""))
                    price_numeric = str(jd.get(jf.get("price", "price_amount"), "")) or price
                    old_price = str(jd.get(jf.get("old_price", "price_without_reduction"), ""))
                    disc_val = jd.get(jf.get("discount", "discount_amount"))
                    if disc_val is not None:
                        discount = str(disc_val)
                    sku = str(jd.get(jf.get("reference", "reference"), ""))
                    qty = jd.get(jf.get("quantity", "quantity"))
                    avail_order = jd.get(jf.get("available_for_order", "available_for_order"))
                    if avail_order is False or (isinstance(qty, (int, float)) and qty <= 0):
                        availability = "Rupture"
                    elif avail_order is True or (isinstance(qty, (int, float)) and qty > 0):
                        availability = "En stock"
                    images_list = _extract_images_from_json(jd.get(jf.get("images", "images")))
                    specs_dict = _extract_features_from_json(jd.get(jf.get("features", "features")))
                except (json.JSONDecodeError, ValueError):
                    pass

        oos_el = tree.css_first(sel.get("out_of_stock_notice", ""))
        if oos_el:
            availability = availability or "Rupture"
        desc_el = tree.css_first(sel.get("description", ""))
        description = parse_node_text(desc_el) if desc_el else ""
        specs_cfg = sel.get("specs")
        if specs_cfg and not specs_dict:
            sc = tree.css_first(specs_cfg["container"])
            if sc:
                for dt, dd in zip(sc.css(specs_cfg["key"]), sc.css(specs_cfg["value"])):
                    k, v = parse_node_text(dt), parse_node_text(dd)
                    if k and v:
                        specs_dict[k] = v
        if not pid:
            pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "discount": discount or None,
            "availability": availability, "description": description, "specs": specs_dict,
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    TunisianetScraper().start()

if __name__ == "__main__":
    run()
