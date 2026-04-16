"""Parashop — Shop-specific scraper. OpenCart 3.x + Journal 3. Full SSR. Lightgallery images."""
from __future__ import annotations
import json
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, is_visible, css_first_safe
from common.pipeline import BaseScraper
from . import config_new as config


def _extract_images_from_lightgallery(data_images: str) -> list[str]:
    if not data_images: return []
    images: list[str] = []
    try:
        items = json.loads(data_images.replace("&quot;", '"'))
        if isinstance(items, list):
            for item in items:
                src = item.get("src") or item.get("thumb") or ""
                if src and src not in images:
                    images.append(src)
    except (json.JSONDecodeError, ValueError):
        pass
    return images


class ParashopScraper(BaseScraper):
    shop_name = "parashop"
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

            dropdown_menu = top_li.css_first("div.dropdown-menu")
            if not dropdown_menu: continue
            for module_item in dropdown_menu.css("div.module-item"):
                if not is_visible(module_item): continue
                low_a = module_item.css_first("a.catalog-title") or module_item.css_first(link_fb)
                if not low_a: continue
                low_url = abs_url(parse_node_attr(low_a, "href"), _base)
                if not low_url or low_url in seen_urls: continue
                seen_urls.add(low_url)
                low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                categories.append({"id": str(low_id), "name": parse_node_text(low_a), "url": low_url, "parent_id": str(top_id), "level": "low"})

                for sub_a in module_item.css("div.item-assets div.subitems div.subitem a"):
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
        for elem in tree.css(ls["element"]):
            id_input = elem.css_first("input[name='product_id']")
            pid = parse_node_attr(id_input, "value") if id_input else ""
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
            brand_el = elem.css_first(ls.get("brand", ""))
            brand = parse_node_attr(brand_el, "alt") or parse_node_text(brand_el) if brand_el else ""
            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "old_price": old_price,
                "brand": brand, "availability": "",
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
        title = parse_node_text(tree.css_first(sel.get("title", "")))
        price = parse_node_text(tree.css_first(sel.get("price", "")))
        old_price = parse_node_text(tree.css_first(sel.get("old_price", "")))
        sku_el = tree.css_first(sel.get("sku", ""))
        sku = parse_node_text(sku_el) if sku_el else ""
        stock_el = tree.css_first("li.product-stock.in-stock")
        if stock_el: availability = parse_node_text(stock_el) or "En stock"
        else:
            stock_el = tree.css_first("li.product-stock.out-of-stock")
            availability = (parse_node_text(stock_el) or "Rupture") if stock_el else ""
        desc_el = tree.css_first(sel.get("description", ""))
        description = parse_node_text(desc_el) if desc_el else ""
        brand_el = tree.css_first(sel.get("brand", ""))
        brand = parse_node_text(brand_el) if brand_el else None
        images_list: list[str] = []
        lg_el = tree.css_first(sel.get("lightgallery", ""))
        if lg_el:
            images_list = _extract_images_from_lightgallery(parse_node_attr(lg_el, sel.get("lightgallery_attr", "data-images")))
        if not images_list:
            for img in tree.css(sel.get("images_main", "")):
                src = parse_node_attr(img, sel.get("images_main_attr", "data-largeimg")) or parse_node_attr(img, "src")
                if src:
                    full = abs_url(src, _base)
                    if full not in images_list: images_list.append(full)
        if not pid: pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": brand,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price,
            "old_price": old_price, "availability": availability,
            "description": description, "specs": {},
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    ParashopScraper().start()

if __name__ == "__main__":
    run()
