"""Parafendri — Shop-specific scraper. PrestaShop + PosThemes MegaMenu. Full SSR. JSON detail."""
from __future__ import annotations
import json
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible, css_first_safe
from common.pipeline import BaseScraper
from . import config_new as config


def _extract_images_from_json(imgs_raw: Any) -> list[str]:
    if not imgs_raw: return []
    images: list[str] = []
    items = imgs_raw.values() if isinstance(imgs_raw, dict) else (imgs_raw if isinstance(imgs_raw, list) else [])
    for v in items:
        if isinstance(v, dict):
            for key in ("large", "bySize", "medium_default"):
                if key in v:
                    target = v[key]
                    u = target.get("url", "") if isinstance(target, dict) else (target if isinstance(target, str) else "")
                    if u and u not in images: images.append(u)
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


class ParafendriScraper(BaseScraper):
    shop_name = "parafendri"
    shop_config = config

    async def scrape_categories(self, html: str) -> list[dict]:
        tree = HTMLParser(html)
        categories: list[dict] = []
        seen_urls: set[str] = set()
        cs = config.CATEGORY_SELECTORS
        link_fb = cs.get("link_fallback", "a[href]")
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            if not is_visible(top_li): continue
            top_a = top_li.css_first(cs.get("top_link")) or top_li.css_first(link_fb)
            top_name_el = top_li.css_first(cs.get("top_name", ""))
            top_name = parse_node_text(top_name_el) if top_name_el else (parse_node_text(top_a) if top_a else "")
            if not top_name: continue
            top_url = abs_url(parse_node_attr(top_a, "href"), _base) if top_a else None
            top_id = (extract_id_from_url(top_url, _pat) or extract_slug_from_url(top_url)) if top_url else f"top_{top_idx}"
            if top_url: seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url, "parent_id": None, "level": "top"})

            # PosThemes dual: mega vs simple dropdown
            low_links: list[tuple[str, Any, Any]] = []
            mega_items = top_li.css("div.pos-sub-menu.menu-dropdown div.pos-menu-col ul.ul-column li.submenu-item")
            simple_items = top_li.css("div.menu-dropdown.cat-drop-menu ul.pos-sub-inner > li")
            if mega_items:
                for low_li in mega_items:
                    low_a = low_li.css_first("a") or low_li.css_first(link_fb)
                    if low_a: low_links.append(("mega", low_li, low_a))
            elif simple_items:
                for low_li in simple_items:
                    low_a = low_li.css_first("a") or low_li.css_first(link_fb)
                    if low_a: low_links.append(("simple", low_li, low_a))

            for _variant, low_li, low_a in low_links:
                if not is_visible(low_a): continue
                low_url = abs_url(parse_node_attr(low_a, "href"), _base)
                if not low_url or low_url in seen_urls: continue
                seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

                for sub_a in low_li.css(cs.get("sub_items", "ul.category-sub-menu > li > a")):
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                    if not sub_url or sub_url in seen_urls: continue
                    seen_urls.add(sub_url)
                    sub_id = extract_id_from_url(sub_url, _pat) or extract_slug_from_url(sub_url)
                    categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": str(low_id), "level": "sub"})
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
            name_el = elem.css_first(ls["name"]) or elem.css_first(ls["url"])
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
            desc_el = elem.css_first(ls.get("description_short", ""))
            desc = parse_node_text(desc_el) if desc_el else ""
            availability = ""
            if css_first_safe(elem, av_cfg.get("in_stock")): availability = "En stock"
            elif css_first_safe(elem, av_cfg.get("out_of_stock")) or css_first_safe(elem, av_cfg.get("out_of_stock_flag")): availability = "Rupture"
            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "old_price": old_price,
                "description_short": desc, "availability": availability,
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
        title = ""; price = ""; price_numeric = ""; old_price = ""; discount = ""
        sku = ""; availability = ""; images_list: list[str] = []; specs_dict: dict[str, str] = {}

        json_el = tree.css_first(sel.get("json_data", ""))
        if json_el:
            json_str = parse_node_attr(json_el, sel.get("json_data_attr", "data-product"))
            if json_str:
                try:
                    jd = json.loads(json_str.replace("&quot;", '"'))
                    jf = sel.get("json_fields", {})
                    if not pid and jd.get(jf.get("id")): pid = str(jd[jf["id"]])
                    title = jd.get(jf.get("name", "name"), "") or title
                    price = jd.get(jf.get("price_display", "price"), "") or str(jd.get(jf.get("price", "price_amount"), ""))
                    price_numeric = str(jd.get(jf.get("price", "price_amount"), "")) or price
                    old_price = str(jd.get(jf.get("old_price", "price_without_reduction"), ""))
                    disc_val = jd.get(jf.get("discount", "discount_amount"))
                    if disc_val is not None: discount = str(disc_val)
                    sku = str(jd.get(jf.get("reference", "reference"), ""))
                    qty = jd.get(jf.get("quantity", "quantity"))
                    avail = jd.get(jf.get("available_for_order", "available_for_order"))
                    if avail is False or (isinstance(qty, (int, float)) and qty <= 0): availability = "Rupture"
                    elif avail is True or (isinstance(qty, (int, float)) and qty > 0): availability = "En stock"
                    images_list = _extract_images_from_json(jd.get(jf.get("images", "images")))
                    specs_dict = _extract_features_from_json(jd.get(jf.get("features", "features")))
                except (json.JSONDecodeError, ValueError): pass

        oos_el = tree.css_first(sel.get("out_of_stock_notice", ""))
        if oos_el: availability = availability or "Rupture"
        desc_el = tree.css_first(sel.get("description", ""))
        description = parse_node_text(desc_el) if desc_el else ""
        if not pid: pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "discount": discount or None,
            "availability": availability, "description": description, "specs": specs_dict,
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    ParafendriScraper().start()

if __name__ == "__main__":
    run()
