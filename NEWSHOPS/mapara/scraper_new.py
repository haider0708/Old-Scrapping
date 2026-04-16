"""Mapara — Shop-specific scraper. WooCommerce + Flatsome. Full SSR."""
from __future__ import annotations
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible, css_first_safe
from common.pipeline import BaseScraper
from . import config_new as config


class MaparaScraper(BaseScraper):
    shop_name = "mapara"
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
            top_name_el = top_li.css_first(cs.get("top_name"))
            top_name = parse_node_text(top_name_el) if top_name_el else ""
            if not top_name: continue
            top_url = None; top_id = f"top_{top_idx}"
            if cs.get("top_link"):
                top_a = top_li.css_first(cs["top_link"]) or top_li.css_first(link_fb)
                if top_a:
                    top_url = abs_url(parse_node_attr(top_a, "href"), _base)
                    if top_url:
                        top_id = extract_id_from_url(top_url, _pat) or extract_slug_from_url(top_url)
                        seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url, "parent_id": None, "level": "top"})

            # Flatsome dual dropdown
            mega_low = top_li.css(cs.get("mega_low", ""))
            simple_low = top_li.css(cs.get("simple_low", ""))
            low_links = mega_low if mega_low else [li.css_first(link_fb) for li in simple_low if li.css_first(link_fb)]
            low_links = [a for a in low_links if a]

            last_low_id: str | None = None
            for low_a in low_links:
                if not is_visible(low_a): continue
                low_url = abs_url(parse_node_attr(low_a, "href"), _base)
                if not low_url or low_url in seen_urls: continue
                seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                last_low_id = str(low_id)
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

            for sub_a in top_li.css(cs.get("sub_items", "")):
                if not sub_a or not is_visible(sub_a): continue
                sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                if not sub_url or sub_url in seen_urls: continue
                seen_urls.add(sub_url)
                sub_id = extract_id_from_url(sub_url, _pat) or extract_slug_from_url(sub_url)
                categories.append({"id": str(sub_id), "name": parse_node_text(sub_a), "url": sub_url, "parent_id": last_low_id or str(top_id), "level": "sub"})
        return categories

    def scrape_listing_page(self, html: str, category_url: str) -> list[dict]:
        tree = HTMLParser(html)
        ls = config.LISTING_SELECTORS
        products = []
        _base = config.BASE_URL
        av_cfg = ls.get("availability", {})
        for elem in tree.css(ls["element"]):
            id_el = elem.css_first("a[data-product_id]") or elem.css_first(ls.get("id_selector", "a.add_to_cart_button"))
            pid = parse_node_attr(id_el, ls.get("id_attr", "data-product_id")) if id_el else ""
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
            class_attr = ((elem.attributes or {}).get("class") or "").lower()
            availability = ""
            if av_cfg.get("instock_class", "instock") in class_attr: availability = "En stock"
            elif av_cfg.get("outofstock_class", "outofstock") in class_attr: availability = "Rupture"
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
        if not pid:
            add_input = tree.css_first("form.cart input[name='add-to-cart']")
            if add_input: pid = parse_node_attr(add_input, "value")
            if not pid:
                add_btn = tree.css_first("form.cart button[name='add-to-cart']")
                if add_btn: pid = parse_node_attr(add_btn, "data-product_id") or parse_node_attr(add_btn, "value")
        title_el = tree.css_first(sel.get("title", ""))
        title = parse_node_text(title_el) if title_el else ""
        price = parse_node_text(tree.css_first(sel.get("price", "")))
        old_price = parse_node_text(tree.css_first(sel.get("old_price", "")))
        add_btn = css_first_safe(tree, sel.get("availability_add_to_cart"))
        availability = "En stock" if add_btn else "Rupture"
        images_list: list[str] = []
        imgs = sel.get("images", {})
        for a in tree.css(imgs.get("gallery", "")):
            href = parse_node_attr(a, "href")
            if href:
                full = abs_url(href, _base)
                if full not in images_list: images_list.append(full)
        if not images_list:
            main_el = tree.css_first(imgs.get("main", ""))
            if main_el:
                src = parse_node_attr(main_el, "src") or parse_node_attr(main_el, "data-src")
                if src: images_list.append(abs_url(src, _base))
        desc_el = tree.css_first(sel.get("description", ""))
        description = parse_node_text(desc_el) if desc_el else ""
        brand_el = tree.css_first(sel.get("brand", ""))
        brand = parse_node_attr(brand_el, sel.get("brand_attr", "alt")) if brand_el else ""
        if not pid: pid = ""
        return {
            "id": pid, "url": url, "title": title, "brand": brand or None,
            "reference": "", "sku": "", "price": price, "price_numeric": price,
            "old_price": old_price, "availability": availability,
            "description": description, "specs": {},
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    MaparaScraper().start()

if __name__ == "__main__":
    run()
