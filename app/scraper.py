"""Amazon seller page scraper module"""

import requests
from bs4 import BeautifulSoup
import time
import logging
from urllib.parse import urljoin, urlparse, parse_qs
from app.config import REQUEST_TIMEOUT, MAX_REQUESTS_PER_MINUTE, USER_AGENT

logger = logging.getLogger(__name__)


class AmazonScraper:
    """Scrape Amazon seller pages for product data"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.request_count = 0
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        min_interval = 60 / MAX_REQUESTS_PER_MINUTE
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
        self.last_request_time = time.time()
    
    def fetch_page(self, url: str) -> str:
        """Fetch page with rate limiting"""
        self._rate_limit()
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return ""
    
    def parse_product_listing(self, html: str) -> list:
        """Parse product listing from HTML"""
        soup = BeautifulSoup(html, "html.parser")
        products = []
        
        # Find all product containers (Amazon uses h2 or div.s-result-item)
        product_items = soup.find_all("div", {"data-component-type": "s-search-result"})
        
        for item in product_items:
            try:
                # Extract ASIN
                asin = item.get("data-asin", "")
                if not asin:
                    continue
                
                # Extract title
                title_elem = item.find("h2", {"class": "s-size-mini"})
                title = title_elem.get_text(strip=True) if title_elem else ""
                
                # Extract price
                price_elem = item.find("span", {"class": "a-price-whole"})
                price = price_elem.get_text(strip=True) if price_elem else ""
                
                # Extract rating
                rating_elem = item.find("span", {"class": "a-icon-star-small"})
                rating = rating_elem.get_text(strip=True).split()[0] if rating_elem else ""
                
                # Extract review count
                review_elem = item.find("span", {"class": "a-size-base"})
                reviews = 0
                if review_elem:
                    text = review_elem.get_text(strip=True)
                    if "," in text:
                        reviews = int(text.replace(",", ""))
                
                # Extract product URL
                link_elem = item.find("h2").find("a") if item.find("h2") else None
                url = link_elem.get("href", "") if link_elem else ""
                url = urljoin("https://www.amazon.com", url)
                
                # Check availability
                avail_elem = item.find("span", {"class": "a-size-base"})
                in_stock = True
                if avail_elem:
                    avail_text = avail_elem.get_text(strip=True).lower()
                    in_stock = "out of stock" not in avail_text
                
                product = {
                    "asin": asin,
                    "title": title,
                    "price": price,
                    "rating": float(rating) if rating else 0.0,
                    "reviews": reviews,
                    "url": url,
                    "in_stock": in_stock
                }
                products.append(product)
            
            except Exception as e:
                logger.warning(f"Error parsing product item: {e}")
                continue
        
        return products
    
    def extract_next_page_url(self, html: str, current_url: str) -> str:
        """Extract next page URL from pagination"""
        soup = BeautifulSoup(html, "html.parser")
        
        # Find next button
        next_btn = soup.find("a", {"class": "s-pagination-next"})
        if next_btn and next_btn.get("href"):
            next_url = next_btn.get("href")
            return urljoin(current_url, next_url)
        
        return ""
    
    def scrape_seller_page(self, seller_url: str, max_pages: int = 5) -> list:
        """Scrape entire seller page with pagination"""
        all_products = []
        current_url = seller_url
        page_count = 0
        
        while current_url and page_count < max_pages:
            logger.info(f"Scraping page {page_count + 1}: {current_url}")
            
            html = self.fetch_page(current_url)
            if not html:
                break
            
            products = self.parse_product_listing(html)
            all_products.extend(products)
            logger.info(f"Found {len(products)} products on page {page_count + 1}")
            
            # Get next page URL
            current_url = self.extract_next_page_url(html, current_url)
            page_count += 1
        
        logger.info(f"Total products scraped: {len(all_products)}")
        return all_products
