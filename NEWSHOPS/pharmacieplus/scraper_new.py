"""Pharmacieplus — Shop-specific scraper. Custom PHP. Full CSR (Playwright all phases)."""
from __future__ import annotations
import re
from typing import Any
from selectolax.parser import HTMLParser
from common.parsing import parse_node_text, parse_node_attr, abs_url, extract_id_from_url, extract_slug_from_url
from common.pipeline import BaseScraper
from . import config_new as config


def _strip_dt(text: str) -> str:
    """Strip 'DT' suffix from price text."""
    return re.sub(r"\s*DT\s*$", "", text.strip(), flags=re.IGNORECASE) if text else ""


def _extract_cat_id(url: str) -> str | None:
    """Extract category ID from URL."""
    pat = config.URL_PATTERNS.get("cat_id_from_url", "")
    if not pat or not url:
        return None
    m = re.search(pat, url)
    if m:
        return next((g for g in m.groups() if g), None)
    return None


class PharmacieplusScraper(BaseScraper):
    shop_name = "pharmacieplus"
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

        for top_idx, top_li in enumerate(tree.css(cs["top_items"])):
            top_a = top_li.css_first(cs.get("top_link") or "a") or top_li.css_first("a")
            top_name = parse_node_text(top_a) if top_a else ""
            if not top_name: continue
            top_url = abs_url(parse_node_attr(top_a, "href"), _base) if top_a else ""
            top_id = extract_id_from_url(top_url, _pat) or extract_slug_from_url(top_url) or f"top_{top_idx}"
            if top_url: seen_urls.add(top_url)
            categories.append({"id": str(top_id), "name": top_name, "url": top_url or None, "parent_id": None, "level": "top"})

            mega_panel = top_li.css_first("div.hs-mega-menu.u-header__sub-menu")
            if not mega_panel: continue
            for col in mega_panel.css("div.col-3"):
                low_a = col.css_first("a")
                if not low_a: continue
                low_url = abs_url(parse_node_attr(low_a, "href"), _base)
                if not low_url or low_url in seen_urls: continue
                seen_urls.add(low_url)
                low_name_el = low_a.css_first(cs.get("low_name", "span"))
                low_name = parse_node_text(low_name_el) if low_name_el else parse_node_text(low_a)
                low_id = extract_id_from_url(low_url, _pat) or extract_slug_from_url(low_url)
                categories.append({"id": str(low_id), "name": low_name, "url": low_url, "parent_id": str(top_id), "level": "low"})

                for sub_a in col.css(cs.get("sub_items", "ul li a")):
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
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]
        for elem in tree.css(ls["element"]):
            url_el = elem.css_first(ls.get("url")) or elem.css_first("a[href*='/a/']")
            url = abs_url(parse_node_attr(url_el, "href"), _base) if url_el else ""
            pid = extract_id_from_url(url, _pat)
            if not pid: continue
            name_el = elem.css_first(ls.get("name")) or url_el
            name = parse_node_text(name_el) if name_el else ""
            img_el = elem.css_first(ls.get("image")) or elem.css_first("img")
            img_url = ""
            if img_el:
                for attr in ls.get("image_attrs", ["src"]):
                    img_url = parse_node_attr(img_el, attr)
                    if img_url: break
            img_url = abs_url(img_url, _base) if img_url else ""
            price_raw = parse_node_text(elem.css_first(ls.get("price", "")))
            price = _strip_dt(price_raw) or price_raw
            old_price = _strip_dt(parse_node_text(elem.css_first(ls.get("old_price", ""))))
            availability = ""
            badge_stock = elem.css_first("div.badge-stock")
            if badge_stock:
                if badge_stock.css_first("i.fa-check"): availability = "En stock"
                elif badge_stock.css_first("i.fa-ban"): availability = "Rupture de stock"
            products.append({
                "id": pid, "name": name, "url": url, "category_url": category_url,
                "image": img_url, "price": price, "old_price": old_price,
                "availability": availability,
            })
        return products

    def get_next_page_url(self, html: str, current_url: str) -> str | None:
        tree = HTMLParser(html)
        # Look for next arrow icon
        next_icon = tree.css_first("li.page-item a.page-link i.fa.fa-angle-right") or tree.css_first("i.fa-angle-right")
        if not next_icon: return None
        parent_a = next_icon.parent
        while parent_a and getattr(parent_a, "tag", None) != "a":
            parent_a = getattr(parent_a, "parent", None)
        if parent_a and getattr(parent_a, "tag", None) == "a":
            href = parse_node_attr(parent_a, "href")
            if href: return abs_url(href, config.BASE_URL)
        # Fallback: compute next page from URL pattern
        cat_id = _extract_cat_id(current_url)
        if not cat_id: return None
        base_url = current_url.split("?")[0]
        m = re.search(r"[?&]page=(\d+)", current_url)
        current_page = int(m.group(1)) if m else 1
        url_pattern = config.PAGINATION_SELECTORS.get("url_pattern", "?page={n}")
        return f"{base_url}{url_pattern.format(cat_id=cat_id, n=current_page + 1)}"

    def scrape_product_detail(self, html: str, url: str) -> dict:
        tree = HTMLParser(html)
        sel = config.DETAIL_SELECTORS
        _base, _pat = config.BASE_URL, config.URL_PATTERNS["id_from_url"]
        pid = extract_id_from_url(url, _pat) or ""
        title = parse_node_text(tree.css_first(sel.get("title", "")))
        price_el = tree.css_first(sel.get("price", ""))
        price_raw = parse_node_text(price_el)
        price = _strip_dt(price_raw) or price_raw
        schema_price = parse_node_attr(tree.css_first(sel.get("price_schema", "")), "content")
        price_numeric = _strip_dt(schema_price) or price
        old_price = _strip_dt(parse_node_text(tree.css_first(sel.get("old_price", ""))))
        availability = ""
        schema_el = tree.css_first("link[itemprop='availability']")
        if schema_el:
            href = parse_node_attr(schema_el, "href")
            if "InStock" in href: availability = "En stock"
            elif "OutOfStock" in href: availability = "Rupture de stock"
        desc_el = tree.css_first(sel.get("description", ""))
        description = parse_node_text(desc_el) if desc_el else ""
        images_list: list[str] = []
        imgs = sel.get("images", {})
        for img_el in tree.css(imgs.get("all", "div.fotorama img")):
            src = parse_node_attr(img_el, "src") or parse_node_attr(img_el, "data-src")
            if src:
                full = abs_url(src, _base)
                if full not in images_list: images_list.append(full)
        return {
            "id": pid, "url": url, "title": title, "brand": None,
            "reference": "", "sku": "", "price": price, "price_numeric": price_numeric,
            "old_price": old_price, "availability": availability,
            "description": description, "specs": {},
            "image_main": images_list[0] if images_list else "", "images": images_list,
        }


def run():
    PharmacieplusScraper().start()

if __name__ == "__main__":
    run()
