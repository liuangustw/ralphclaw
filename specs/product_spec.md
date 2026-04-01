# Amazon Product Monitor - Product Specification

## Overview
A command-line tool to monitor Amazon marketplace seller pages and identify trending products based on:
- Recent review velocity
- Price drops
- New listings with high engagement
- Rating momentum

## Core Features

### 1. Web Scraping
- **Input**: Amazon seller page URL or ASIN list
- **Output**: Product data (title, price, ratings, reviews, availability)
- **Constraint**: Respect robots.txt, rate limiting (5 req/min max)
- **Note**: Use requests + BeautifulSoup, no Selenium (lighter)

### 2. Trending Detection
**Metrics for "Trending":**
- Reviews in last 7 days: >= 10
- Rating avg: >= 3.5
- Price change: >= -10% or new stock (availability change)
- Available: In stock or Very Limited Stock

**Scoring**: 
```
trending_score = (reviews_7d * 0.4) + (rating_momentum * 0.3) + (price_drop * 0.2) + (stock_status * 0.1)
```

### 3. Data Storage
**SQLite schema:**
- `products` — product master data (ASIN, title, category, URL)
- `snapshots` — time-series snapshots (product_id, timestamp, price, reviews, rating)
- `trending_events` — detected trending items with score & reason

### 4. CLI Interface
```bash
# Monitor a seller page
amazon-monitor --seller-url "https://amazon.com/s?i=merchant-id-xxx" --output json

# Check trending products
amazon-monitor --trending --since "2 days" --output csv

# Export history
amazon-monitor --export --product-id "B0XXXXXX" --format csv
```

**Output Formats:**
- JSON: array of trending products with full metadata
- CSV: product_title, price, reviews_7d, trending_score, url

### 5. Scheduler (Optional)
- Run monitoring every 6 hours
- Store snapshots automatically
- Alert on high-trending products (future feature)

## Technical Stack
- **Language**: Python 3.10+
- **Web scraping**: requests + beautifulsoup4
- **Database**: SQLite with proper schema
- **CLI**: Click or argparse
- **Scheduling**: APScheduler (optional)
- **Testing**: pytest

## Non-Goals
- GUI interface (CLI only)
- Real-time alerts (batch processing)
- Machine learning predictions
- Multi-account management
- Proxy rotation (simple implementation)

## Success Criteria
- Can scrape and parse Amazon seller pages without errors
- Correctly identifies trending products with >=3 metrics
- CLI works with multiple output formats
- Database persists data across runs
- Scheduled monitoring runs without manual intervention
- All tests pass with >80% code coverage
