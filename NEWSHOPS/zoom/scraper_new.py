"""Zoom — Shop-specific scraper. PrestaShop + ETS Mega Menu. Full SSR. JSON-primary detail."""
from __future__ import annotations
import json
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible
from common.pipeline import BaseScraper
from . import config_new as config


def _extract_images_from_json(imgs_raw: Any) -> list[str]:
    if not imgs_raw: return []
    images: list[str] = []
    items = imgs_raw.values() if isinstance(imgs_raw, dict) else (imgs_raw if isinstance(imgs_raw, list) else [])
    for v in items:
        if isinstance(v, dict):
            for key in ("large", "bySize", "medium_default", "home_default"):
                if key in v:
                    target = v[key]
                    u = target.get("url", "") if isinstance(target, dict) else (target if isinstance(target, str) else "")
                    if u and u not in images:
                        images.append(u)
                    break
    return images


def _extract_features_from_json(feats_raw: Any) -> dict[str, str]:
    if not feats_raw: return {}
    specs: dict[str, str] = {}
    if isinstance(feats_raw, list):
        for f in feats_raw:
            if isinstance(f, dict):
                k, v = f.get("name", ""), f.get("value", "")
                if k and v: specs[k] = v
    return specs


class ZoomScraper(BaseScraper):
    shop_name = "zoom"
    shop_config = config

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        _base = config.BASE_URL
        _pat = config.URL_PATTERNS["id_from_url"]

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            top_a = top_li.css_first(cs.get("top_link", "a"))
            if not top_a:
                continue
            top_name = parse_node_text(top_a)
            top_url = abs_url(parse_node_attr(top_a, "href"), _base)
            top_id = extract_id_from_url(top_url, _pat) or extract_slug_from_url(top_url) or f"top_{top_idx}"
            if top_url and top_url not in seen_urls:
                seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url or None, "parent_id": None, "level": "top"})

            for low_a in top_li.css(cs["low_items"]):
                low_url = abs_url(parse_node_attr(low_a, "href"), _base)
                if not low_url or low_url in seen_urls:
                    continue
                seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

            for sub_a in top_li.css(cs["sub_items"]):
                sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                if not sub_url or sub_url in seen_urls:
                    continue
                seen_urls.add(sub_url)
                sub_id = extract_id_from_url(sub_url, _pat) or extract_slug_from_url(sub_url)
                categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": str(top_id), "level": "sub"})
        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        products = []
        _base = config.BASE_URL
        av_cfg = ls.get("availability", {})
        for elem in tree.css(ls["element"]):
            pid = parse_node_attr(elem, ls["id_attr"])
            if not pid: continue
            name_el = elem.css_first(ls["name"])
            url_el = elem.css_first(ls["url"])
            url = abs_url(parse_node_attr(url_el, "href"), _base) if url_el else ""
            name = parse_node_text(name_el) if name_el else ""
            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls["image_attrs"]:
                    img_url = parse_node_attr(img_el, attr)
                    if img_url: break
            img_url = abs_url(img_url, _base) if img_url else ""
            price = parse_node_text(elem.css_first(ls["price"]))
            old_price = parse_node_text(elem.css_first(ls.get("old_price", "")))
            availability = ""
            av_sel = av_cfg.get("selector", "")
            if av_sel:
                av_el = elem.css_first(av_sel)
                availability = parse_node_text(av_el) if av_el else ""
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
                    if disc_val is not None: discount = str(disc_val)
                    sku = str(jd.get(jf.get("reference", "reference"), ""))
                    qty = jd.get(jf.get("quantity", "quantity"))
                    avail_order = jd.get(jf.get("available_for_order", "available_for_order"))
                    if avail_order is False or (isinstance(qty, (int, float)) and qty <= 0):
                        availability = "Rupture"
                    elif avail_order is True or (isinstance(qty, (int, float)) and qty > 0):
                        availability = "En stock"
                    images_list = _extract_images_from_json(jd.get(jf.get("images", "images")))
                    specs_dict = _extract_features_from_json(jd.get(jf.get("features", "features")))
                except (json.JSONDecodeError, ValueError): pass

        oos_el = tree.css_first(sel.get("out_of_stock_notice", ""))
        if oos_el: availability = availability or "Rupture"
        if not title:
            t_el = tree.css_first(sel.get("title", ""))
            title = parse_node_text(t_el) if t_el else ""
        if not price:
            p_el = tree.css_first(sel.get("price", ""))
            price = parse_node_attr(p_el, sel.get("price_content_attr", "content")) if p_el else ""
            price_numeric = price_numeric or price
        if not availability:
            a_el = tree.css_first(sel.get("global_availability", ""))
            availability = parse_node_text(a_el) if a_el else ""
        desc_el = tree.css_first(sel.get("description", "")) or tree.css_first(sel.get("full_description", ""))
        description = parse_node_text(desc_el) if desc_el else ""
        specs_cfg = sel.get("specs")
        if specs_cfg and not specs_dict:
            sc = tree.css_first(specs_cfg["container"])
            if sc:
                for dt, dd in zip(sc.css(specs_cfg["key"]), sc.css(specs_cfg["value"])):
                    k, v = parse_node_text(dt), parse_node_text(dd)
                    if k and v: specs_dict[k] = v
        if not images_list:
            imgs = sel.get("images", {})
            main_el = tree.css_first(imgs.get("main", ""))
            if main_el:
                src = parse_node_attr(main_el, "src")
                if src: images_list.append(abs_url(src, _base))
            thumb_attr = imgs.get("thumbnail_attr", "data-zoom-image")
            for thumb in tree.css(imgs.get("thumbnails", "")):
                src = parse_node_attr(thumb, thumb_attr) or parse_node_attr(thumb, "src")
                if src:
                    full = abs_url(src, _base)
                    if full not in images_list: images_list.append(full)
        if not pid: pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "discount": discount or None,
            "availability": availability, "description": description, "specs": specs_dict,
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    ZoomScraper().start()

if __name__ == "__main__":
    run()
