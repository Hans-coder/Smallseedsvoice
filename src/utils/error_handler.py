import os
import json
import traceback
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def log_scraping_error(scraper_name: str, exception: Exception):
    """
    Appends a scraping error configuration to data/scraping_errors.json.
    This file is intended to be read by the notification script to alert administrators.
    """
    error_file = "data/scraping_errors.json"
    
    # Create data dir if not exists
    os.makedirs(os.path.dirname(error_file), exist_ok=True)
    
    errors = []
    if os.path.exists(error_file):
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
        except Exception:
            pass
            
    # Format the traceback
    tb_str = "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
    
    errors.append({
        "timestamp": datetime.now().isoformat(),
        "scraper": scraper_name,
        "error_type": type(exception).__name__,
        "message": str(exception),
        "traceback": tb_str
    })
    
    # Write back
    try:
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(errors, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Failed to write error log: {e}")
