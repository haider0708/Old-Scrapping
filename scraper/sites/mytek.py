#!/usr/bin/env python3
"""
Mytek.tn specific scraper implementation.
"""
import logging
from typing import List
from selectolax.parser import HTMLParser
from playwright.async_api import Page

from scraper.base import BaseScraper


class MytekScraper(BaseScraper):
    """Scraper for mytek.tn e-commerce site."""
    
    def __init__(self, logger: logging.Logger):
        super().__init__("mytek", logger)
    
    def get_wait_selector(self) -> str:
        """Selector to wait for after page load."""
        return self.selectors.get("category_page", {}).get(
            "wait_selector", 
            ".product-container"
        )
    
    def build_page_url(self, base_url: str, page_num: int) -> str:
        """Build paginated URL for mytek."""
        if "?" in base_url:
            return f"{base_url}&p={page_num}"
        return f"{base_url}?p={page_num}"
    
    def extract_categories_from_html(self, html: str) -> dict:
        """
        Extract 3-level category hierarchy from mytek.tn frontpage.
        
        Structure:
        - Top-level (14): li.rootverticalnav.category-item
        - Low-level: .grid-item-6.clearfix
        - Subcategory: .level3-popup li.category-item
        """
        tree = HTMLParser(html)
        fp = self.selectors.get("frontpage", {})
        
        categories = []
        
        # Top-level categories
        top_sel = fp.get("top_level_blocks", "li.rootverticalnav.category-item")
        top_blocks = tree.css(top_sel)
        
        self.logger.info(f"Found {len(top_blocks)} top-level categories")
        
        for top_block in top_blocks:
            # Get top-level title
            top_title = None
            for child in top_block.iter():
                if child.tag == "a":
                    text = child.text(strip=True)
                    if text and not text.startswith("javascript"):
                        top_title = text
                        break
            
            if not top_title:
                continue
            
            top_cat = {
                "name": top_title,
                "level": "top",
                "low_level_categories": []
            }
            
            # Low-level categories
            low_sel = fp.get("low_level_blocks", ".grid-item-6.clearfix")
            low_blocks = top_block.css(low_sel)
            
            for low_block in low_blocks:
                low_link_sel = fp.get("low_level_link", ".title_normal > a")
                low_link_node = low_block.css_first(low_link_sel)
                
                if not low_link_node:
                    continue
                
                low_title = low_link_node.text(strip=True)
                low_href = low_link_node.attributes.get("href", "")
                
                if low_href.startswith("javascript:"):
                    continue
                
                low_cat = {
                    "name": low_title,
                    "url": low_href,
                    "level": "low",
                    "subcategories": []
                }
                
                # Subcategories
                sub_sel = fp.get("subcategory_blocks", ".level3-popup li.category-item")
                sub_blocks = low_block.css(sub_sel)
                
                for sub_block in sub_blocks:
                    sub_link_node = sub_block.css_first("a.clearfix") or sub_block.css_first("a")
                    if not sub_link_node:
                        continue
                    
                    sub_title_sel = fp.get("subcategory_title", ".level3-name")
                    sub_title_node = sub_block.css_first(sub_title_sel)
                    sub_title = sub_title_node.text(strip=True) if sub_title_node else sub_link_node.text(strip=True)
                    sub_href = sub_link_node.attributes.get("href", "")
                    
                    if sub_href and not sub_href.startswith("javascript:"):
                        low_cat["subcategories"].append({
                            "name": sub_title,
                            "url": sub_href,
                            "level": "subcategory"
                        })
                
                top_cat["low_level_categories"].append(low_cat)
            
            categories.append(top_cat)
        
        # Calculate stats
        stats = {"top_level": 0, "low_level": 0, "subcategory": 0, "total_urls": 0}
        for top in categories:
            stats["top_level"] += 1
            for low in top.get("low_level_categories", []):
                stats["low_level"] += 1
                if low.get("url"):
                    stats["total_urls"] += 1
                for sub in low.get("subcategories", []):
                    stats["subcategory"] += 1
                    if sub.get("url"):
                        stats["total_urls"] += 1
        
        return {
            "categories": categories,
            "stats": stats
        }
    
    async def extract_products_from_page(self, page: Page) -> List[dict]:
        """Extract products from a mytek category page."""
        cp = self.selectors.get("category_page", {})
        item_selector = cp.get("item_selector", 
            ".d-flex.justify-content-center.col-lg-3.col-md-4.col-sm-6.col-12.mb-4")
        
        products = await page.evaluate(f"""
            (selector) => {{
                const items = document.querySelectorAll(selector);
                const products = [];
                
                items.forEach(item => {{
                    const container = item.querySelector('.product-container');
                    if (!container) return;
                    
                    // Product ID
                    const productId = container.getAttribute('data-product-id') || 
                                      item.querySelector('[data-product-id]')?.getAttribute('data-product-id');
                    
                    // Product URL
                    let productUrl = null;
                    const links = item.querySelectorAll('a[href]');
                    for (const link of links) {{
                        const href = link.getAttribute('href');
                        const style = link.getAttribute('style') || '';
                        if (style.includes('display: flex') || 
                            (href && href.includes('.html') && !href.includes('?'))) {{
                            productUrl = href;
                            break;
                        }}
                    }}
                    
                    // Product title - try multiple selectors
                    const titleEl = item.querySelector('.product-item-link, .product-item-name a, .product-title-text, .product-name, h1 a, h2 a');
                    const productName = titleEl?.innerText?.trim() || '';
                    
                    // Availability status from listing page
                    // Structure: <div class="availability"><div class="stock availables" title="En stock"><span>En stock</span></div></div>
                    const availabilityEl = item.querySelector('.availability .stock');
                    const availabilityStatus = availabilityEl ? (availabilityEl.getAttribute('title') || availabilityEl.querySelector('span')?.innerText?.trim()) : null;
                    const isAvailable = availabilityEl ? availabilityEl.classList.contains('availables') : null;
                    
                    // Price from listing page
                    // Structure: <div class="price-box"><span class="final-price">1 259,000 DT</span><span class="original-price">1 459,000 DT</span></div>
                    const parsePrice = (text) => {{
                        if (!text) return null;
                        // Remove "DT", spaces, and convert comma to dot: "1 259,000 DT" -> 1259.0
                        const cleaned = text.replace(/DT/gi, '').replace(/\\s/g, '').replace(',', '.');
                        const num = parseFloat(cleaned);
                        return isNaN(num) ? null : num;
                    }};
                    
                    const priceBox = item.querySelector('.price-box');
                    const finalPriceEl = priceBox?.querySelector('.final-price');
                    const originalPriceEl = priceBox?.querySelector('.original-price');
                    
                    const price = parsePrice(finalPriceEl?.innerText);
                    const oldPrice = parsePrice(originalPriceEl?.innerText);
                    
                    if (productId || productUrl) {{
                        products.push({{
                            id: productId,
                            url: productUrl,
                            name: productName,
                            price: price,
                            old_price: oldPrice,
                            availability: availabilityStatus,
                            available: isAvailable
                        }});
                    }}
                }});
                
                return products;
            }}
        """, item_selector)
        
        return products
    
    async def extract_pagination_info(self, page: Page) -> dict:
        """Extract pagination from mytek category page."""
        pagination = await page.evaluate("""
            () => {
                const currentPage = document.querySelector('.page-item.active .page-link, .current');
                const pageLinks = document.querySelectorAll('.page-item .page-link, .pages li a');
                let maxPage = 1;
                
                pageLinks.forEach(el => {
                    const num = parseInt(el.innerText);
                    if (!isNaN(num) && num > maxPage) maxPage = num;
                });
                
                return {
                    current_page: parseInt(currentPage?.innerText) || 1,
                    total_pages: maxPage
                };
            }
        """)
        
        return pagination
    
    async def scrape_product_details(self, page: Page, product_url: str) -> dict:
        """
        Scrape detailed product information from a mytek.tn product page.

        Extracts:
        - title, sku, brand, overview/description
        - price, old_price, discount
        - specifications table
        - images, stock status, store availability
        """
        # Retry logic for product pages (some may fail to load)
        max_retries = 2
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                # Faster but more reliable loading - wait for networkidle
                await page.goto(product_url, wait_until="networkidle", timeout=20000)

                # Quick wait for critical elements to appear
                try:
                    await page.wait_for_selector('.page-title-wrapper h1, [data-product-id]', timeout=5000)
                except:
                    pass  # Continue even if title doesn't load immediately

                # Wait for price data to load
                try:
                    await page.wait_for_selector('meta[itemprop="price"], [data-price-type]', timeout=3000)
                except:
                    pass

                # Wait for stock status (critical for availability)
                try:
                    await page.wait_for_selector('[data-role="stockStatus"], .stock.available, .stock.unavailable, [itemprop="availability"]',
                                                 timeout=4000, state='attached')
                except:
                    pass

                # Wait for store availability table (optional, don't wait too long)
                try:
                    await page.wait_for_selector('.tab_retrait_mag', timeout=3000, state='attached')
                    await page.wait_for_timeout(500)  # Brief wait for AJAX content
                except:
                    pass

                # If we get here, page loaded successfully
                break

            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    await page.wait_for_timeout(1000)  # Brief wait before retry
                    continue
                else:
                    # All retries failed
                    return {
                        "url": product_url,
                        "error": f"Page load failed after {max_retries + 1} attempts: {last_error}",
                        "title": None,
                        "price": None,
                        "availability": None,
                        "available": None,
                        "sku": None,
                        "brand": None,
                        "overview": None,
                        "specifications": {},
                        "images": [],
                        "store_availability": None
                    }
        
        details = await page.evaluate('''() => {
            const data = {url: window.location.href};
            
            // 1. Title - page-title-wrapper
            const titleEl = document.querySelector('.page-title-wrapper h1 span.base');
            data.title = titleEl ? titleEl.textContent.trim() : null;
            
            // 2. Product ID from data attribute
            const priceBox = document.querySelector('[data-product-id]');
            data.product_id = priceBox ? priceBox.getAttribute('data-product-id') : null;
            
            // 3. SKU - product attribute sku
            const skuEl = document.querySelector('.product.attribute.sku .value');
            data.sku = skuEl ? skuEl.textContent.trim() : null;
            
            // 4. Overview/Description - try multiple selectors
            let overviewEl = document.querySelector('.product.attribute.overview .value');
            if (!overviewEl || !overviewEl.textContent.trim()) {
                // Try description selector
                overviewEl = document.querySelector('#description .product-description') ||
                            document.querySelector('.product-description');
            }
            if (!overviewEl || !overviewEl.textContent.trim()) {
                // Try general description areas
                overviewEl = document.querySelector('.product-details .description') ||
                            document.querySelector('[data-role="description"]') ||
                            document.querySelector('.tab-content .description');
            }
            data.overview = overviewEl ? overviewEl.textContent.trim() : null;
            
            // 5. Brand from logo (removed in_stock/stock_status - use store_availability instead)
            const brandImg = document.querySelector('.product-info-stock-sku a img');
            if (brandImg) {
                data.brand_logo = brandImg.getAttribute('src');
                data.brand = brandImg.getAttribute('alt') || 
                             brandImg.getAttribute('src').split('/').pop().replace('.jpg', '').replace('.png', '');
            }
            
            // 7. PRICES - IMPORTANT: Use meta[itemprop="price"] which is unique to main product
            // The page has multiple price-boxes (for similar products) but only ONE meta itemprop="price"
            // Structure: <span itemprop="offers"><meta itemprop="price" content="789">...</span>
            
            // PRIMARY: Use meta itemprop="price" (only 1 on page, always correct)
            const metaPrice = document.querySelector('meta[itemprop="price"]');
            if (metaPrice) {
                data.price = parseFloat(metaPrice.getAttribute('content')) || null;
            }
            
            // OLD PRICE: Find the container with itemprop="offers" and look for old-price sibling
            // The old-price is a sibling of special-price (which contains itemprop="offers")
            const offersContainer = document.querySelector('[itemprop="offers"]');
            if (offersContainer) {
                // Navigate up to find the price-box that contains both special-price and old-price
                let priceBox = offersContainer.closest('.price-box');
                if (priceBox) {
                    const oldPriceEl = priceBox.querySelector('.old-price [data-price-type="oldPrice"]');
                    if (oldPriceEl) {
                        const oldPrice = parseFloat(oldPriceEl.getAttribute('data-price-amount'));
                        if (oldPrice && oldPrice !== data.price) {
                            data.old_price = oldPrice;
                            data.discount_percent = Math.round((1 - data.price / oldPrice) * 100);
                        }
                    }
                }
            }
            
            // 8. Specifications - product info detailed (excluding DISPONIBILITÉ - use store_availability instead)
            const specsTable = document.querySelector('#product-attribute-specs-table');
            if (specsTable) {
                const specs = {};
                const rows = specsTable.querySelectorAll('tbody tr');
                rows.forEach(row => {
                    const label = row.querySelector('th.label');
                    const value = row.querySelector('td.data');
                    if (label && value) {
                        const labelText = label.textContent.trim();
                        // Skip DISPONIBILITÉ - we get this from store_availability
                        if (labelText.toUpperCase() !== 'DISPONIBILITÉ') {
                            specs[labelText] = value.textContent.trim();
                        }
                    }
                });
                data.specifications = specs;
            }
            
            // 9. Images - try multiple selectors to handle single and multi-image products
            const images = [];
            
            // First try: carousel images (for multi-image products)
            document.querySelectorAll('#gallery-container .carousel-item img').forEach(img => {
                const src = img.getAttribute('src');
                if (src && !src.includes('placeholder') && !images.includes(src)) {
                    images.push(src);
                }
            });
            
            // Second try: direct img with itemprop="image" (for single-image products)
            if (images.length === 0) {
                document.querySelectorAll('img[itemprop="image"]').forEach(img => {
                    const src = img.getAttribute('src');
                    if (src && !src.includes('placeholder') && !images.includes(src)) {
                        images.push(src);
                    }
                });
            }
            
            // Third try: any image in gallery-container
            if (images.length === 0) {
                document.querySelectorAll('#gallery-container img, .product-media-gallery img').forEach(img => {
                    const src = img.getAttribute('src');
                    if (src && !src.includes('placeholder') && !images.includes(src)) {
                        images.push(src);
                    }
                });
            }
            
            // Fourth try: main product image
            if (images.length === 0) {
                const mainImg = document.querySelector('.product.media img, .fotorama__stage img, .product-image-container img');
                if (mainImg) {
                    const src = mainImg.getAttribute('src');
                    if (src && !src.includes('placeholder')) {
                        images.push(src);
                    }
                }
            }
            
            data.images = images;
            
            // 10. Main availability - extract from stock div
            // Structure:
            //   <div class="stock available" itemprop="availability" href="https://schema.org/InStock" title="En stock"><span>En stock</span></div>
            //   <div class="stock unavailable" itemprop="availability" href="https://schema.org/OutOfStock" title="Epuisé"><span>Epuisé</span></div>
            //   <div class="stock unavailable_backorder" itemprop="availability" href="https://schema.org/BackOrder" title="En arrivage"><span>En arrivage</span></div>
            
            // Try multiple selectors to find the stock div
            let stockDiv = document.querySelector('[data-role="stockStatus"]');
            if (!stockDiv) {
                stockDiv = document.querySelector('.stock.available');
            }
            if (!stockDiv) {
                stockDiv = document.querySelector('.stock.unavailable');
            }
            if (!stockDiv) {
                stockDiv = document.querySelector('.stock.unavailable_backorder');
            }
            if (!stockDiv) {
                stockDiv = document.querySelector('[itemprop="availability"]');
            }
            
            if (stockDiv) {
                // Get text from span inside or directly from div - clean whitespace
                const spanEl = stockDiv.querySelector('span');
                let availabilityText = spanEl ? spanEl.textContent : stockDiv.textContent;
                // Clean up whitespace, newlines, and normalize
                data.availability = availabilityText ? availabilityText.replace(/\\s+/g, ' ').trim() : null;
                
                // Determine availability based on TEXT (most reliable)
                const textLower = (data.availability || '').toLowerCase();
                
                // Check if in stock based on text content
                const inStockKeywords = ['en stock', 'disponible', 'in stock'];
                const outOfStockKeywords = ['epuisé', 'épuisé', 'rupture', 'indisponible', 'out of stock', 'non disponible'];
                const backorderKeywords = ['arrivage', 'commande', 'backorder', 'sur commande'];
                
                const textIndicatesInStock = inStockKeywords.some(kw => textLower.includes(kw));
                const textIndicatesOutOfStock = outOfStockKeywords.some(kw => textLower.includes(kw));
                const textIndicatesBackorder = backorderKeywords.some(kw => textLower.includes(kw));
                
                // Also check classes as backup
                const hasAvailableClass = stockDiv.classList && stockDiv.classList.contains('available');
                const hasUnavailableClass = stockDiv.classList && stockDiv.classList.contains('unavailable');
                
                // Also check href for schema.org values as backup
                const href = stockDiv.getAttribute('href') || '';
                const hrefInStock = href.includes('InStock');
                const hrefOutOfStock = href.includes('OutOfStock');
                
                // Simplified availability determination - prioritize classes, then text
                if (hasAvailableClass && !hasUnavailableClass) {
                    data.available = true;
                } else if (hasUnavailableClass) {
                    data.available = false;
                } else {
                    // Fallback to text analysis
                    const hasInStockText = ['en stock', 'disponible', 'in stock', 'available'].some(kw => textLower.includes(kw));
                    const hasOutOfStockText = ['epuisé', 'épuisé', 'rupture', 'indisponible', 'out of stock'].some(kw => textLower.includes(kw));

                    if (hasInStockText && !hasOutOfStockText) {
                        data.available = true;
                    } else if (hasOutOfStockText) {
                        data.available = false;
                    } else if (['arrivage', 'commande', 'sur commande'].some(kw => textLower.includes(kw))) {
                        data.available = false;  // Backorder = not immediately available
                    } else if (data.availability && data.availability.trim()) {
                        // Default to available if we have some text
                        data.available = true;
                    } else {
                        data.available = null;
                    }
                }
            } else {
                data.availability = null;
                data.available = null;
            }
            
            // 11. Store availability - simplified extraction from .tab_retrait_mag table
            const storeAvailability = [];

            // Find the store availability table
            const table = document.querySelector('.tab_retrait_mag') ||
                         document.querySelector('table.tab_retrait_mag');
            
            if (table) {
                const tbody = table.querySelector('tbody');
                if (tbody) {
                    const rows = tbody.querySelectorAll('tr');

                    rows.forEach(row => {
                        const cells = row.querySelectorAll('td');
                        if (cells.length < 2) return;

                        let storeName = null;
                        let statusText = null;
                        let isAvailable = false;

                        const firstCell = cells[0];
                        const secondCell = cells[1];

                        // Extract store name
                        if (firstCell.hasAttribute('colspan')) {
                            // "Achat En Ligne" row
                            storeName = firstCell.textContent.trim() || 'Achat En Ligne';
                        } else if (firstCell.classList && firstCell.classList.contains('mag_name')) {
                            // Regular store row
                            const link = firstCell.querySelector('a');
                            storeName = link ? link.textContent.trim() : firstCell.textContent.trim();
                        } else {
                            // Fallback
                            storeName = firstCell.textContent.trim();
                        }

                        // Clean store name
                        storeName = storeName.replace(/[:;]+/g, '').trim();

                        // Extract status
                        const statusSpan = secondCell.querySelector('span');
                        if (statusSpan) {
                            statusText = statusSpan.textContent.trim();
                            const statusClass = statusSpan.className || '';
                            isAvailable = statusClass.includes('enStock') ||
                                        statusText.toLowerCase().includes('en stock') ||
                                        statusText.toLowerCase().includes('disponible');
                        } else {
                            statusText = secondCell.textContent.trim();
                            const textLower = statusText.toLowerCase();
                            isAvailable = textLower.includes('stock') || textLower.includes('disponible');
                        }

                        // Only add valid entries
                        if (storeName && statusText) {
                            storeAvailability.push({
                                store: storeName,
                                status: statusText,
                                available: isAvailable
                            });
                        }
                    });
                }
            }
            
            // Always set store_availability array (even if empty) to distinguish from null
            // But only if we found at least one store, otherwise null means "not found"
            if (storeAvailability.length > 0) {
                data.store_availability = storeAvailability;
            } else {
                data.store_availability = null;
            }
            
            return data;
        }''')
        
        return details


# Factory function to get scraper
def get_scraper(logger: logging.Logger) -> MytekScraper:
    return MytekScraper(logger)
