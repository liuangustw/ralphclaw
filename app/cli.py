"""Command-line interface for Amazon Product Monitor"""

import sys
import json
import csv
import logging
from datetime import datetime, timedelta
import click

from app.config import LOG_LEVEL, LOG_FILE, PROJECT_ROOT
from app.scraper import AmazonScraper
from app.product_analyzer import TrendingDetector
from app.database import ProductDatabase

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Amazon Product Monitor - CLI tool for discovering trending products"""
    pass


@cli.command()
@click.option("--seller-url", required=False, help="Amazon seller page URL")
@click.option("--asin-list", required=False, help="File with ASIN list (one per line)")
@click.option("--output", type=click.Choice(["json", "csv"]), default="json", help="Output format")
@click.option("--max-pages", default=5, help="Max pages to scrape")
def monitor(seller_url, asin_list, output, max_pages):
    """Monitor Amazon seller page for trending products"""
    
    if not seller_url and not asin_list:
        click.echo("Error: Provide either --seller-url or --asin-list", err=True)
        sys.exit(1)
    
    scraper = AmazonScraper()
    analyzer = TrendingDetector()
    db = ProductDatabase()
    
    all_products = []
    
    # Scrape from seller URL
    if seller_url:
        click.echo(f"Scraping {seller_url}...")
        products = scraper.scrape_seller_page(seller_url, max_pages)
        all_products.extend(products)
        click.echo(f"✓ Scraped {len(products)} products")
    
    # Process and analyze
    click.echo("Analyzing trends...")
    analyzed = []
    
    for product in all_products:
        # Get previous snapshot
        prev = None
        prod_obj = db.get_product(product["asin"])
        if prod_obj:
            history = db.get_price_history(prod_obj["id"])
            prev = history[0] if history else None
        
        # Analyze
        analyzed_product = analyzer.analyze_product(product, prev)
        analyzed.append(analyzed_product)
        
        # Save to database
        product_id = db.insert_product(
            product["asin"],
            product["title"],
            product["url"]
        )
        db.insert_snapshot(
            product_id,
            analyzed_product.get("price", "N/A"),
            analyzed_product.get("rating", 0),
            analyzed_product.get("reviews", 0),
            analyzed_product.get("in_stock", True)
        )
    
    # Detect trending
    trending = analyzer.detect_trending_products(analyzed)
    
    # Output
    if output == "json":
        click.echo(json.dumps(trending[:20], indent=2, default=str))
    elif output == "csv":
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=["asin", "title", "price", "rating", "reviews", "trending_score"]
        )
        writer.writeheader()
        for p in trending[:20]:
            writer.writerow({k: p.get(k) for k in writer.fieldnames})
    
    click.echo(f"\n✓ Found {len(trending)} trending products out of {len(all_products)}")


@cli.command()
@click.option("--since", default="7 days", help="Time period (e.g. '2 days', '7 days')")
@click.option("--limit", default=20, help="Max results")
@click.option("--output", type=click.Choice(["json", "csv"]), default="json")
def trending(since, limit, output):
    """Show trending products from database"""
    
    db = ProductDatabase()
    products = db.get_trending_products(limit)
    
    if output == "json":
        click.echo(json.dumps(products, indent=2, default=str))
    elif output == "csv":
        if products:
            writer = csv.DictWriter(
                sys.stdout,
                fieldnames=["asin", "title", "trending_score", "reason"]
            )
            writer.writeheader()
            for p in products:
                writer.writerow({
                    "asin": p.get("asin"),
                    "title": p.get("title"),
                    "trending_score": p.get("trending_score"),
                    "reason": p.get("reason")
                })
    
    click.echo(f"\n✓ Showing {len(products)} trending products")


@cli.command()
@click.option("--product-id", required=True, help="Product ASIN")
@click.option("--output", type=click.Choice(["json", "csv"]), default="json")
def history(product_id, output):
    """Show price history for a product"""
    
    db = ProductDatabase()
    product = db.get_product(product_id)
    
    if not product:
        click.echo(f"Product {product_id} not found", err=True)
        sys.exit(1)
    
    history_data = db.get_price_history(product["id"])
    
    if output == "json":
        click.echo(json.dumps({
            "asin": product_id,
            "title": product["title"],
            "history": history_data
        }, indent=2, default=str))
    elif output == "csv":
        writer = csv.DictWriter(
            sys.stdout,
            fieldnames=["price", "rating", "reviews", "snapshot_date"]
        )
        writer.writeheader()
        for h in history_data:
            writer.writerow(h)
    
    click.echo(f"\n✓ Found {len(history_data)} snapshots for {product_id}")


@cli.command()
@click.option("--output", type=click.Choice(["json", "csv"]), default="json")
@click.option("--limit", default=50)
def export(output, limit):
    """Export all trending products"""
    
    db = ProductDatabase()
    
    if output == "json":
        data = db.export_trending_to_json(limit)
        click.echo(data)
    elif output == "csv":
        data = db.export_trending_to_csv(limit)
        click.echo(data)
    
    click.echo(f"\n✓ Exported trending products")


@cli.command()
def status():
    """Show monitoring status and database stats"""
    
    db = ProductDatabase()
    trending = db.get_trending_products(1)
    
    click.echo("Amazon Product Monitor Status")
    click.echo("=" * 40)
    click.echo(f"Database: {db.db_path}")
    click.echo(f"Latest trending product: {trending[0]['title'] if trending else 'None'}")
    click.echo(f"Trending score: {trending[0].get('trending_score', 0) if trending else 'N/A'}")
    click.echo("=" * 40)


def main():
    """Main entry point"""
    try:
        cli()
    except Exception as e:
        logger.error(f"CLI error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
