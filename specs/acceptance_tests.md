# Acceptance Tests - Amazon Product Monitor

## Phase 1: Foundation (Tasks amz_001, amz_002)

### Test: Basic Scraper Functionality
```bash
python3 -c "
from app.scraper import AmazonScraper
scraper = AmazonScraper()
products = scraper.parse_product_listing(sample_html)
assert len(products) > 0
assert 'title' in products[0]
assert 'price' in products[0]
"
```

### Test: Pagination Handling
```bash
# Should extract next-page URLs correctly
python3 tests/test_scraper.py::test_pagination
```

## Phase 2: Analysis (Task amz_003)

### Test: Trending Detection
```bash
python3 -c "
from app.product_analyzer import TrendingDetector
detector = TrendingDetector()

sample_product = {
    'title': 'Test Product',
    'reviews_7d': 15,
    'rating': 4.2,
    'price_change': -15,
    'in_stock': True
}

score = detector.calculate_trending_score(sample_product)
assert score > 0.6, f'Expected score > 0.6, got {score}'
"
```

## Phase 3: Storage (Task amz_004)

### Test: Database CRUD
```bash
python3 tests/test_database.py::test_save_and_retrieve_product
python3 tests/test_database.py::test_snapshot_history
```

## Phase 4: CLI (Task amz_005)

### Test: JSON Output
```bash
python3 app/cli.py --trending --output json | python3 -m json.tool
# Must produce valid JSON array
```

### Test: CSV Export
```bash
python3 app/cli.py --export --product-id B0XXXXX --output csv | head -5
# Must have CSV header and data rows
```

## Phase 5: Scheduling (Task amz_006)

### Test: Scheduler Integration
```bash
python3 tests/test_scheduler.py::test_schedule_runs
# Verify job is scheduled and executed
```

## Integration Test: End-to-End

```bash
# 1. Clear database
rm -f data/products.db

# 2. Scrape a page
python3 app/cli.py --seller-url "https://amazon.com/s?i=merchant-xxx" --output json > trending.json

# 3. Verify output
python3 -c "
import json
with open('trending.json') as f:
    data = json.load(f)
assert isinstance(data, list)
assert len(data) > 0
assert 'title' in data[0]
assert 'trending_score' in data[0]
print('✓ Integration test passed')
"
```

## Performance Targets
- Scrape 100 products: < 10 seconds
- Analyze trends: < 1 second
- Database query (trending products): < 100ms
- CLI response time: < 2 seconds
