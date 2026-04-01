"""Task scheduling for continuous monitoring"""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.scraper import AmazonScraper
from app.product_analyzer import TrendingDetector
from app.database import ProductDatabase

logger = logging.getLogger(__name__)


class MonitoringScheduler:
    """Schedule periodic monitoring tasks"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scraper = AmazonScraper()
        self.analyzer = TrendingDetector()
        self.db = ProductDatabase()
    
    def monitor_seller(self, seller_url: str, interval_hours: int = 6):
        """Schedule periodic monitoring of a seller page"""
        
        def job():
            logger.info(f"Starting scheduled monitoring of {seller_url}")
            try:
                products = self.scraper.scrape_seller_page(seller_url)
                
                for product in products:
                    # Get previous snapshot
                    prev = None
                    prod_obj = self.db.get_product(product["asin"])
                    if prod_obj:
                        history = self.db.get_price_history(prod_obj["id"])
                        prev = history[0] if history else None
                    
                    # Analyze
                    analyzed = self.analyzer.analyze_product(product, prev)
                    
                    # Save to database
                    product_id = self.db.insert_product(
                        product["asin"],
                        product["title"],
                        product["url"]
                    )
                    self.db.insert_snapshot(
                        product_id,
                        analyzed.get("price", "N/A"),
                        analyzed.get("rating", 0),
                        analyzed.get("reviews", 0),
                        analyzed.get("in_stock", True)
                    )
                    
                    # Record trending events
                    if analyzed.get("trending_score", 0) >= 0.6:
                        self.db.record_trending_event(
                            product_id,
                            analyzed["trending_score"],
                            analyzed.get("trending_reason", "Trending product"),
                            analyzed.get("review_delta", 0),
                            analyzed.get("price_drop_pct", 0)
                        )
                
                logger.info(f"Finished monitoring: {len(products)} products")
            
            except Exception as e:
                logger.error(f"Monitoring job failed: {e}")
        
        # Add job to scheduler
        trigger = IntervalTrigger(hours=interval_hours)
        self.scheduler.add_job(
            job,
            trigger=trigger,
            id=f"monitor_{seller_url.replace('/', '_')}",
            name=f"Monitor {seller_url}",
            replace_existing=True
        )
        logger.info(f"Scheduled monitoring every {interval_hours} hours: {seller_url}")
    
    def cleanup_old_data(self, interval_hours: int = 24, keep_days: int = 90):
        """Schedule periodic cleanup of old data"""
        
        def cleanup_job():
            logger.info("Starting cleanup of old snapshots")
            try:
                deleted = self.db.clear_old_snapshots(keep_days)
                logger.info(f"Deleted {deleted} old snapshots")
            except Exception as e:
                logger.error(f"Cleanup job failed: {e}")
        
        trigger = IntervalTrigger(hours=interval_hours)
        self.scheduler.add_job(
            cleanup_job,
            trigger=trigger,
            id="cleanup_old_data",
            name="Cleanup old snapshots",
            replace_existing=True
        )
        logger.info(f"Scheduled cleanup every {interval_hours} hours")
    
    def start(self):
        """Start the scheduler"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")
    
    def get_jobs(self):
        """Get list of scheduled jobs"""
        return self.scheduler.get_jobs()
    
    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        self.scheduler.remove_job(job_id)
        logger.info(f"Removed job: {job_id}")


# Example usage
if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    
    scheduler = MonitoringScheduler()
    
    # Example: Monitor a seller page every 6 hours
    scheduler.monitor_seller("https://amazon.com/s?i=merchant-XXXXX")
    
    # Cleanup every 24 hours
    scheduler.cleanup_old_data()
    
    # Start scheduler
    scheduler.start()
    
    try:
        print("Scheduler running. Press Ctrl+C to stop.")
        while True:
            pass
    except KeyboardInterrupt:
        scheduler.stop()
