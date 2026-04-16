"""Wiki — Shop-specific scraper. WordPress Bricks + WooCommerce + WP Grid Builder. PW cats, SSR rest."""
from __future__ import annotations
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url, css_first_safe, is_visible
from common.pipeline import BaseScraper
from . import config_new as config


class WikiScraper(BaseScraper):
    shop_name = "wiki"
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
            if not is_visible(top_li):
                continue
            top_name_el = css_first_safe(top_li, cs.get("top_name"))
            top_name = parse_node_text(top_name_el) if top_name_el else ""
            if not top_name:
                continue
            top_id = f"top_{top_idx}"
            categories.append({"id": str(top_id), "name": top_name, "url": None, "parent_id": None, "level": "top"})

            for low_li in top_li.css(cs["low_items"]):
                if not is_visible(low_li):
                    continue
                low_a = low_li.css_first(cs.get("low_link")) or low_li.css_first(link_fb)
                low_heading = low_li.css_first(cs.get("low_heading"))
                low_name = parse_node_text(low_a) if low_a else (parse_node_text(low_heading) if low_heading else "")
                low_url = abs_url(parse_node_attr(low_a, "href"), _base) if low_a else ""
                if low_url and low_url in seen_urls:
                    continue
                if low_url:
                    seen_urls.add(low_url)
                low_id = (extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)) if low_url else f"low_{top_idx}_{len(categories)}"
                categories.append({"id": str(low_id), "name": low_name, "url": low_url or None, "parent_id": str(top_id), "level": "low"})

                for sub_a in low_li.css(cs["sub_items"]):
                    sub_url = abs_url(parse_node_attr(sub_a, "href"), _base)
                    if not sub_url or sub_url in seen_urls:
                        continue
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
            id_el = css_first_safe(elem, ls.get("id_selector"))
            pid = parse_node_attr(id_el, ls.get("id_attr")) if id_el else ""
            if not pid:
                pid = parse_node_attr(id_el, ls.get("id_attr_alt")) if id_el else ""
            if not pid:
                continue
            name_el = elem.css_first(ls["name"]) or elem.css_first(ls["url"])
            url_el = elem.css_first(ls["url"])
            url = abs_url(parse_node_attr(url_el, "href"), _base) if url_el else ""
            name = parse_node_text(name_el) if name_el else ""
            img_el = elem.css_first(ls["image"])
            img_url = ""
            if img_el:
                for attr in ls.get("image_attrs", ["src"]):
                    img_url = parse_node_attr(img_el, attr)
                    if img_url:
                        break
            img_url = abs_url(img_url, _base) if img_url else ""
            price = parse_node_text(elem.css_first(ls["price"]))
            old_price = parse_node_text(css_first_safe(elem, ls.get("old_price")))
            brand_el = css_first_safe(elem, ls.get("brand"))
            brand = (parse_node_attr(brand_el, ls.get("brand_attr", "alt")) or parse_node_text(brand_el)) if brand_el else ""
            sku = parse_node_text(css_first_safe(elem, ls.get("sku")))
            availability = ""
            av_el = css_first_safe(elem, ls.get("availability_selector"))
            if av_el:
                availability = parse_node_attr(av_el, ls.get("availability_attr", "data-stock-status"))
            products.append({"id": pid, "name": name, "url": url, "category_url": category_url, "image": img_url, "price": price, "old_price": old_price, "brand": brand, "reference": sku, "availability": availability})
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        next_a = tree.css_first(config.PAGINATION_SELECTORS["next_page"])
        if not next_a:
            return None
        href = parse_node_attr(next_a, "href")
        if href:
            return abs_url(href, config.BASE_URL)
        data_page = parse_node_attr(next_a, "data-page")
        if data_page and data_page.isdigit():
            parsed = urlparse(current_url)
            params = parse_qs(parsed.query)
            params["_pagination"] = [data_page]
            new_query = urlencode(params, doseq=True)
            return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment))
        return None

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]
        pid = extract_id_from_url(url, _pat) or ""
        title = parse_node_text(css_first_safe(tree, sel.get("title")))
        sku = parse_node_text(css_first_safe(tree, sel.get("sku")))
        brand_el = css_first_safe(tree, sel.get("brand"))
        brand = (parse_node_attr(brand_el, sel.get("brand_attr", "alt")) or parse_node_text(brand_el)) if brand_el else ""
        price_el = css_first_safe(tree, sel.get("price_sale")) or css_first_safe(tree, sel.get("price_regular"))
        price = parse_node_text(price_el) if price_el else ""
        old_price = parse_node_text(css_first_safe(tree, sel.get("price_original")))
        availability = ""
        if css_first_safe(tree, sel.get("availability_woo")):
            availability = "En stock"
        av_badge = css_first_safe(tree, sel.get("availability_badge"))
        if av_badge:
            av_val = parse_node_attr(av_badge, "data-stock-status")
            if av_val:
                availability = av_val
        description = parse_node_text(css_first_safe(tree, sel.get("description"))) or parse_node_text(css_first_safe(tree, sel.get("full_description")))
        specs_dict: dict[str, str] = {}
        specs_cfg = sel.get("specs")
        if specs_cfg:
            sc = tree.css_first(specs_cfg["container"])
            if sc:
                for row in sc.css("tr"):
                    th = row.css_first(specs_cfg["key"])
                    td = row.css_first(specs_cfg["value"])
                    if th and td:
                        k, v = parse_node_text(th), parse_node_text(td)
                        if k and v:
                            specs_dict[k] = v
        imgs = sel.get("images", {})
        images_list: list[str] = []
        main_el = css_first_safe(tree, imgs.get("main"))
        if main_el:
            src = parse_node_attr(main_el, "src")
            if src:
                images_list.append(abs_url(src, _base))
        for a_el in tree.css(imgs.get("gallery", "")):
            href = parse_node_attr(a_el, "href")
            if href:
                full = abs_url(href, _base)
                if full not in images_list:
                    images_list.append(full)
        if not pid:
            pid = sku or ""
        return {
            "id": pid, "url": url, "title": title, "brand": brand or None,
            "reference": sku, "sku": sku, "price": price, "price_numeric": price,
            "old_price": old_price, "availability": availability,
            "description": description, "specs": specs_dict,
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    WikiScraper().start()

if __name__ == "__main__":
    run()
