"""Tests for product analyzer module"""

import pytest
from app.product_analyzer import TrendingDetector


def test_detect_trending():
    """Test trending product detection"""
    
    detector = TrendingDetector()
    
    # High-trending product
    product = {
        "title": "Trending Product",
        "price": "$29.99",
        "rating": 4.7,
        "reviews": 15,
        "reviews_7d": 12,
        "price_drop_pct": -15,
        "in_stock": True
    }
    
    score = detector.calculate_trending_score(product)
    assert score > 0.6
    assert score <= 1.0


def test_low_trending_product():
    """Test low-trending product detection"""
    
    detector = TrendingDetector()
    
    # Low-trending product
    product = {
        "title": "Not Trending",
        "price": "$9.99",
        "rating": 2.0,
        "reviews": 2,
        "reviews_7d": 0,
        "price_drop_pct": 0,
        "in_stock": False
    }
    
    score = detector.calculate_trending_score(product)
    assert score < 0.6


def test_detect_trending_products():
    """Test detecting multiple trending products"""
    
    detector = TrendingDetector()
    
    products = [
        {
            "title": "Product A",
            "reviews_7d": 15,
            "rating": 4.5,
            "price_drop_pct": -10,
            "in_stock": True
        },
        {
            "title": "Product B",
            "reviews_7d": 2,
            "rating": 3.0,
            "price_drop_pct": 0,
            "in_stock": False
        }
    ]
    
    trending = detector.detect_trending_products(products)
    assert len(trending) >= 1
    assert trending[0]["trending_score"] >= trending[-1]["trending_score"]


def test_trending_reason():
    """Test generating trending reason"""
    
    detector = TrendingDetector()
    
    product = {
        "reviews_7d": 15,
        "rating": 4.5,
        "price_drop_pct": -12,
        "in_stock": True
    }
    
    reason = detector._get_trending_reason(product)
    assert "reviews" in reason.lower() or "rating" in reason.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
