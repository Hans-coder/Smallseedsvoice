"""
Radar Activity Scraper
Targets: 
1. Indievox (Live House events)
2. Instagram (Selected accounts like Legacy, Revolver)

Output: data/radar_events.json
"""
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

from src.utils.logger import setup_logger
from src.scraper.ticketing.indievox_scraper import IndievoxScraper
from src.scraper.instagram_scraper import InstagramScraper

logger = setup_logger("radar_scraper")

def main():
    logger.info("Starting Radar Activity Scraper...")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    radar_events = []
    
    # 1. Indievox
    try:
        logger.info("Scraping Indievox...")
        # Config options can include max_pages
        iv_scraper = IndievoxScraper({"max_pages": 3})
        # Scrape "Live House" category if URL structure allows, e.g. ?type=livehouse
        # For now, use default list
        iv_events = iv_scraper.scrape_events("https://www.indievox.com/activity/list")
        
        # Transform keys to match expected output schema if needed
        # IndievoxScraper already returns compatible dicts (activity_name, date, etc.)
        radar_events.extend(iv_events)
        logger.info(f"Added {len(iv_events)} events from Indievox.")
    except Exception as e:
        logger.error(f"Indievox scrape failed: {e}")

#    # 2. Instagram
#    # Target Accounts: legacy_taiwan, revolvertaipei
#    ig_accounts = [
#        "legacy_taiwan",
#        "revolvertaipei",
#        "thewalllivehouse",
#        "witchhouse.tw"
#    ]
#    
#    try:
#        logger.info("Scraping Instagram Accounts...")
#        # Use existing InstagramScraper
#        # It needs config with optional login
#        config = {
#            "retry_count": 3,
#            "request_delay": 5, # Slower for IG
#            # Add credentials if available in env, else guest mode (might be limited)
#            "ig_username": os.getenv("IG_USERNAME"),
#            "ig_password": os.getenv("IG_PASSWORD")
#        }
#        
#        ig_scraper = InstagramScraper(config)
#        
#        for account in ig_accounts:
#            try:
#                logger.info(f"Fetching @{account}...")
#                events = ig_scraper.scrape_events(account, max_posts=5)
#                
#                # Transform IG events to Radar schema
#                for e in events:
#                    radar_event = {
#                        "activity_name": e['name'],
#                        "performers": [],
#                        "date": e['date'] or e['time'], # Fallback
#                        "time": "Unknown",
#                        "venue": e['location'] if e['location'] != "未提供" else account,
#                        "city": "Unknown",
#                        "is_free": "unknown",
#                        "source": e['source_url'],
#                        "image_url": e['image_url'],
#                        "note": f"IG Post from @{account}",
#                        "reliability": "social"
#                    }
#                    radar_events.append(radar_event)
#                
#                logger.info(f"Added {len(events)} events from @{account}")
#            except Exception as e:
#                error_msg = str(e)
#                if "401" in error_msg or "Unauthorized" in error_msg:
#                    logger.warning(f"Skipping @{account} due to Private/Restricted access (401): {error_msg}")
#                else:
#                    logger.error(f"Failed to scrape @{account}: {e}")
#                
#    except Exception as e:
#        logger.error(f"Instagram scraping section failed: {e}")

    # Deduplication (by source URL)
    unique_events = {}
    for e in radar_events:
        if e.get('source'):
            unique_events[e['source']] = e
        else:
            # Fallback dedup key
            key = f"{e['activity_name']}_{e['date']}"
            unique_events[key] = e
            
    final_list = list(unique_events.values())
    
    # Save Output
    output_path = "data/radar_events.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Done. Saved {len(final_list)} radar events to {output_path}")

if __name__ == "__main__":
    main()
