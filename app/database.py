"""SQLite database operations for product monitoring"""

import sqlite3
import json
import logging
from datetime import datetime
from pathlib import Path
from app.config import DB_PATH

logger = logging.getLogger(__name__)


class ProductDatabase:
    """SQLite database for products and history"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DB_PATH)
        self.init_schema()
    
    def init_schema(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Products table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                category TEXT,
                url TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Snapshots table (time-series data)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                price TEXT,
                rating REAL,
                reviews INTEGER,
                in_stock BOOLEAN,
                snapshot_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id),
                UNIQUE(product_id, snapshot_date)
            )
        """)
        
        # Trending events table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trending_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                trending_score REAL,
                reason TEXT,
                review_delta INTEGER,
                price_drop_pct REAL,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"Database initialized: {self.db_path}")
    
    def insert_product(self, asin: str, title: str, url: str, category: str = None) -> int:
        """Insert or update a product"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO products (asin, title, url, category)
                VALUES (?, ?, ?, ?)
            """, (asin, title, url, category))
            
            cursor.execute("SELECT id FROM products WHERE asin = ?", (asin,))
            product_id = cursor.fetchone()[0]
            
            conn.commit()
            return product_id
        finally:
            conn.close()
    
    def insert_snapshot(self, product_id: int, price: str, rating: float, 
                       reviews: int, in_stock: bool) -> bool:
        """Insert a product snapshot"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO snapshots 
                (product_id, price, rating, reviews, in_stock)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, price, rating, reviews, in_stock))
            
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.debug(f"Snapshot already exists for product {product_id}")
            return False
        finally:
            conn.close()
    
    def record_trending_event(self, product_id: int, score: float, reason: str,
                             review_delta: int = 0, price_drop_pct: float = 0) -> bool:
        """Record a trending event"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO trending_events 
                (product_id, trending_score, reason, review_delta, price_drop_pct)
                VALUES (?, ?, ?, ?, ?)
            """, (product_id, score, reason, review_delta, price_drop_pct))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def get_product(self, asin: str) -> dict:
        """Get product by ASIN"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT * FROM products WHERE asin = ?", (asin,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_trending_products(self, limit: int = 20) -> list:
        """Get top trending products from last 7 days"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT p.*, te.trending_score, te.reason,
                       MAX(te.detected_at) as last_detected
                FROM products p
                JOIN trending_events te ON p.id = te.product_id
                WHERE te.detected_at > datetime('now', '-7 days')
                GROUP BY p.id
                ORDER BY te.trending_score DESC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def get_price_history(self, product_id: int) -> list:
        """Get price history for a product"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT price, rating, reviews, snapshot_date
                FROM snapshots
                WHERE product_id = ?
                ORDER BY snapshot_date DESC
                LIMIT 30
            """, (product_id,))
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def export_trending_to_json(self, limit: int = 50) -> str:
        """Export trending products as JSON"""
        products = self.get_trending_products(limit)
        return json.dumps(products, indent=2, default=str)
    
    def export_trending_to_csv(self, limit: int = 50) -> str:
        """Export trending products as CSV"""
        products = self.get_trending_products(limit)
        
        if not products:
            return "asin,title,price,trending_score,reason\n"
        
        lines = ["asin,title,price,trending_score,reason"]
        for p in products:
            line = f"{p['asin']},{p['title']},{p.get('price', 'N/A')},{p['trending_score']},{p['reason']}"
            lines.append(line)
        
        return "\n".join(lines)
    
    def clear_old_snapshots(self, days: int = 90) -> int:
        """Delete snapshots older than N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                DELETE FROM snapshots
                WHERE snapshot_date < datetime('now', ? || ' days')
            """, (f"-{days}",))
            
            rows_deleted = cursor.rowcount
            conn.commit()
            return rows_deleted
        finally:
            conn.close()
