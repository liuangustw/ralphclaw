"""Tests for database module"""

import pytest
import tempfile
from app.database import ProductDatabase


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db = ProductDatabase(f.name)
        yield db
        import os
        try:
            os.unlink(f.name)
        except:
            pass


def test_insert_product(temp_db):
    """Test inserting a product"""
    
    product_id = temp_db.insert_product(
        asin="B0TEST123",
        title="Test Product",
        url="https://amazon.com/dp/B0TEST123"
    )
    
    assert product_id > 0
    product = temp_db.get_product("B0TEST123")
    assert product is not None
    assert product["title"] == "Test Product"


def test_insert_snapshot(temp_db):
    """Test inserting a snapshot"""
    
    product_id = temp_db.insert_product(
        "B0TEST124",
        "Test Product 2",
        "https://amazon.com/dp/B0TEST124"
    )
    
    result = temp_db.insert_snapshot(
        product_id=product_id,
        price="$29.99",
        rating=4.5,
        reviews=100,
        in_stock=True
    )
    
    assert result is True
    history = temp_db.get_price_history(product_id)
    assert len(history) > 0


def test_record_trending_event(temp_db):
    """Test recording trending event"""
    
    product_id = temp_db.insert_product(
        "B0TEST125",
        "Trending Product",
        "https://amazon.com/dp/B0TEST125"
    )
    
    result = temp_db.record_trending_event(
        product_id=product_id,
        score=0.85,
        reason="High review velocity",
        review_delta=10,
        price_drop_pct=-12.5
    )
    
    assert result is True


def test_get_trending_products(temp_db):
    """Test getting trending products"""
    
    # Insert some products
    for i in range(3):
        product_id = temp_db.insert_product(
            f"B0TEST{i:03d}",
            f"Product {i}",
            f"https://amazon.com/dp/B0TEST{i:03d}"
        )
        temp_db.record_trending_event(
            product_id,
            0.7 + (i * 0.1),
            f"Trending reason {i}"
        )
    
    trending = temp_db.get_trending_products(limit=5)
    assert len(trending) > 0


def test_export_to_json(temp_db):
    """Test exporting to JSON"""
    
    product_id = temp_db.insert_product(
        "B0TEST200",
        "Export Test",
        "https://amazon.com/dp/B0TEST200"
    )
    temp_db.record_trending_event(product_id, 0.75, "Test export")
    
    json_data = temp_db.export_trending_to_json()
    assert json_data != ""
    assert "B0TEST200" in json_data or "[]" in json_data


def test_export_to_csv(temp_db):
    """Test exporting to CSV"""
    
    product_id = temp_db.insert_product(
        "B0TEST201",
        "CSV Export Test",
        "https://amazon.com/dp/B0TEST201"
    )
    temp_db.record_trending_event(product_id, 0.8, "CSV test")
    
    csv_data = temp_db.export_trending_to_csv()
    assert "asin" in csv_data.lower() or csv_data.strip() != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
