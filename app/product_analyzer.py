"""Product trend analysis module"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)


class TrendingDetector:
    """Detect trending products based on sales signals"""
    
    # Thresholds for trending
    MIN_REVIEWS_7D = 10
    MIN_RATING = 3.5
    MIN_PRICE_DROP_PCT = 10
    
    def __init__(self):
        self.weights = {
            "reviews_7d": 0.4,
            "rating_momentum": 0.3,
            "price_drop": 0.2,
            "stock_status": 0.1
        }
    
    def calculate_trending_score(self, product: Dict) -> float:
        """Calculate trending score (0.0 - 1.0)"""
        score = 0.0
        
        # Reviews in last 7 days (normalized)
        reviews_7d = product.get("reviews_7d", 0)
        reviews_score = min(reviews_7d / self.MIN_REVIEWS_7D, 1.0)
        score += reviews_score * self.weights["reviews_7d"]
        
        # Rating momentum
        rating = product.get("rating", 0)
        rating_score = max(0, (rating - self.MIN_RATING) / (5.0 - self.MIN_RATING))
        score += rating_score * self.weights["rating_momentum"]
        
        # Price drop
        price_drop_pct = product.get("price_drop_pct", 0)
        price_score = min(abs(price_drop_pct) / self.MIN_PRICE_DROP_PCT, 1.0) if price_drop_pct < 0 else 0
        score += price_score * self.weights["price_drop"]
        
        # Stock status (bonus for limited stock)
        in_stock = product.get("in_stock", True)
        stock_score = 1.0 if in_stock else 0.5
        score += stock_score * self.weights["stock_status"]
        
        return min(score, 1.0)
    
    def detect_trending_products(self, products: List[Dict], 
                                  min_score: float = 0.6) -> List[Dict]:
        """Detect trending products from a list"""
        trending = []
        
        for product in products:
            score = self.calculate_trending_score(product)
            
            if score >= min_score:
                product_with_score = product.copy()
                product_with_score["trending_score"] = round(score, 3)
                product_with_score["trending_reason"] = self._get_trending_reason(product)
                trending.append(product_with_score)
        
        # Sort by trending score descending
        trending.sort(key=lambda x: x.get("trending_score", 0), reverse=True)
        return trending
    
    def _get_trending_reason(self, product: Dict) -> str:
        """Generate human-readable trending reason"""
        reasons = []
        
        if product.get("reviews_7d", 0) >= self.MIN_REVIEWS_7D:
            reasons.append(f"{product['reviews_7d']} reviews in 7d")
        
        if product.get("rating", 0) >= self.MIN_RATING:
            reasons.append(f"High rating: {product['rating']}")
        
        if product.get("price_drop_pct", 0) <= -self.MIN_PRICE_DROP_PCT:
            reasons.append(f"Price down {abs(product['price_drop_pct'])}%")
        
        if product.get("in_stock"):
            reasons.append("In stock")
        
        return " • ".join(reasons) if reasons else "Emerging product"
    
    def analyze_product(self, product: Dict, previous_snapshot: Dict = None) -> Dict:
        """Analyze single product with history comparison"""
        analysis = product.copy()
        
        # Calculate price drop if history available
        if previous_snapshot:
            prev_price = float(previous_snapshot.get("price", 0).replace("$", "").replace(",", ""))
            curr_price = float(product.get("price", 0).replace("$", "").replace(",", ""))
            
            if prev_price > 0:
                price_change_pct = ((curr_price - prev_price) / prev_price) * 100
                analysis["price_drop_pct"] = round(price_change_pct, 2)
            else:
                analysis["price_drop_pct"] = 0
            
            # Calculate review velocity
            review_delta = product.get("reviews", 0) - previous_snapshot.get("reviews", 0)
            analysis["review_delta"] = review_delta
            analysis["reviews_7d"] = review_delta  # Simplified: assume delta is per 7 days
        else:
            analysis["reviews_7d"] = product.get("reviews", 0)
            analysis["price_drop_pct"] = 0
            analysis["review_delta"] = 0
        
        # Add trending score
        analysis["trending_score"] = self.calculate_trending_score(analysis)
        
        return analysis
