"""Configuration management for Amazon Product Monitor"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DB_PATH = DATA_DIR / "products.db"

# Scraping settings
REQUEST_TIMEOUT = 10
MAX_REQUESTS_PER_MINUTE = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# API keys (from environment)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = DATA_DIR / "amazon_monitor.log"
