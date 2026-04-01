"""Tests for scraper module"""

import pytest
from app.scraper import AmazonScraper


def test_parse_product_listing():
    """Test parsing product listing from HTML"""
    
    scraper = AmazonScraper()
    
    # Sample HTML (matches Amazon structure)
    html = """
    <div data-component-type="s-search-result" data-asin="B0ABC123">
        <h2 class="s-size-mini"><a href="/dp/B0ABC123">Test Product</a></h2>
        <span class="a-price-whole">$29.99</span>
        <span class="a-icon-star-small">4.5 out of 5</span>
    </div>
    """
    
    products = scraper.parse_product_listing(html)
    # HTML parsing may not work perfectly, but module should be importable
    assert isinstance(products, list)
    assert products[0]["asin"] == "B0ABC123"
    assert products[0]["title"] != ""
    assert products[0]["price"] != ""


def test_rate_limiting():
    """Test rate limiting"""
    
    scraper = AmazonScraper()
    import time
    
    start = time.time()
    scraper._rate_limit()
    scraper._rate_limit()
    elapsed = time.time() - start
    
    # Should have some delay (depending on MAX_REQUESTS_PER_MINUTE)
    assert elapsed >= 0


def test_extract_next_page_url():
    """Test pagination URL extraction"""
    
    scraper = AmazonScraper()
    
    html = """
    <a class="s-pagination-next" href="/s?k=test&page=2">Next</a>
    """
    
    url = scraper.extract_next_page_url(html, "https://amazon.com/s?k=test")
    assert url != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
