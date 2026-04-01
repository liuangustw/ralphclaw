"""Flask web interface for Amazon Product Monitor"""

import json
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from app.scraper import AmazonScraper
from app.product_analyzer import TrendingDetector
from app.database import ProductDatabase
from app.config import PROJECT_ROOT, LOG_LEVEL

logger = logging.getLogger(__name__)

app = Flask(__name__, template_folder=str(PROJECT_ROOT / "templates"))
app.config['JSON_SORT_KEYS'] = False

# Initialize components
db = ProductDatabase()
analyzer = TrendingDetector()
scraper = AmazonScraper()


@app.route('/')
def index():
    """Home page with HTML dashboard"""
    from flask import send_from_directory
    try:
        return send_from_directory(str(PROJECT_ROOT / "templates"), "index.html")
    except:
        # Fallback to JSON
        trending = db.get_trending_products(limit=10)
        return jsonify({
            "status": "running",
            "app": "Amazon Product Monitor",
            "version": "1.0",
            "trending_products": trending[:5] if trending else [],
            "endpoints": {
                "trending": "/api/trending?limit=20",
                "monitor": "/api/monitor?url=<seller_url>",
                "history": "/api/history?asin=<asin>",
                "export": "/api/export?format=json&limit=50",
                "status": "/api/status"
            }
        })


@app.route('/api/trending')
def api_trending():
    """Get trending products"""
    limit = request.args.get('limit', 20, type=int)
    trending = db.get_trending_products(limit=min(limit, 100))
    
    return jsonify({
        "status": "success",
        "count": len(trending),
        "products": trending,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/monitor', methods=['POST', 'GET'])
def api_monitor():
    """Monitor a seller page"""
    
    if request.method == 'GET':
        seller_url = request.args.get('url', '')
    else:
        data = request.get_json()
        seller_url = data.get('url', '')
    
    if not seller_url:
        return jsonify({
            "status": "error",
            "message": "Missing seller URL",
            "example": "POST /api/monitor with {\"url\": \"https://amazon.com/s?i=merchant-XXX\"}"
        }), 400
    
    try:
        logger.info(f"Monitoring: {seller_url}")
        
        # Scrape
        products = scraper.scrape_seller_page(seller_url, max_pages=3)
        logger.info(f"Scraped {len(products)} products")
        
        # Analyze and save
        analyzed = []
        for product in products:
            prev = None
            prod_obj = db.get_product(product["asin"])
            if prod_obj:
                history = db.get_price_history(prod_obj["id"])
                prev = history[0] if history else None
            
            analyzed_product = analyzer.analyze_product(product, prev)
            analyzed.append(analyzed_product)
            
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
        
        return jsonify({
            "status": "success",
            "scraped": len(products),
            "trending_count": len(trending),
            "trending": trending[:20],
            "timestamp": datetime.utcnow().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route('/api/history')
def api_history():
    """Get product price history"""
    asin = request.args.get('asin', '')
    
    if not asin:
        return jsonify({
            "status": "error",
            "message": "Missing ASIN parameter"
        }), 400
    
    product = db.get_product(asin)
    if not product:
        return jsonify({
            "status": "error",
            "message": f"Product {asin} not found"
        }), 404
    
    history = db.get_price_history(product["id"])
    
    return jsonify({
        "status": "success",
        "asin": asin,
        "title": product["title"],
        "history_count": len(history),
        "history": history,
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/export')
def api_export():
    """Export trending products"""
    fmt = request.args.get('format', 'json')
    limit = request.args.get('limit', 50, type=int)
    
    if fmt == 'json':
        return jsonify({
            "status": "success",
            "data": db.export_trending_to_json(limit=limit),
            "format": "json"
        })
    elif fmt == 'csv':
        return {
            "status": "success",
            "data": db.export_trending_to_csv(limit=limit),
            "format": "csv",
            "content-type": "text/csv"
        }
    else:
        return jsonify({
            "status": "error",
            "message": "Unsupported format. Use 'json' or 'csv'"
        }), 400


@app.route('/api/status')
def api_status():
    """Server status and database stats"""
    trending = db.get_trending_products(1)
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "Amazon Product Monitor API",
        "version": "1.0.0",
        "database": {
            "path": db.db_path,
            "connected": True
        },
        "latest_trending": trending[0] if trending else None,
        "api_endpoints": [
            "GET  /api/trending",
            "POST /api/monitor",
            "GET  /api/history?asin=<asin>",
            "GET  /api/export?format=json|csv&limit=50",
            "GET  /api/status"
        ]
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "status": "error",
        "message": "Endpoint not found",
        "available_endpoints": [
            "/",
            "/api/trending",
            "/api/monitor",
            "/api/history",
            "/api/export",
            "/api/status"
        ]
    }), 404


@app.errorhandler(500)
def server_error(error):
    return jsonify({
        "status": "error",
        "message": "Internal server error"
    }), 500


def create_app():
    """Create Flask app"""
    return app


if __name__ == "__main__":
    logging.basicConfig(level=getattr(logging, LOG_LEVEL))
    app.run(host="0.0.0.0", port=5000, debug=False)
