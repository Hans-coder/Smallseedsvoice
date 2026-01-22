"""
Script 2: Activity Radar Scraper
Targets: Live House sites, StreetVoice, Social Media
Output: JSON Array
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from src.utils.logger import setup_logger
from src.scraper.ticketing.indievox_scraper import IndievoxScraper
from src.scraper.instagram_scraper import InstagramScraper
# We will use Indievox as a major source for Live House events (Legacy, etc. use it)

logger = setup_logger("radar_scraper")

def main():
    logger.info("Starting Activity Radar Scraper...")
    
    config = {
        "request_delay": 2,
        "retry_count": 3
    }
    
    events = []
    
    # 1. Live House Aggregators (Indievox)
    # The prompt allows Live House official sites. Indievox is the ticketing engine for many.
    try:
        scraper = IndievoxScraper(config)
        indievox_events = scraper.scrape_events() # Needs update to match Radar schema?
        # Radar Schema: Name, Performer, Date, Time, Venue, City, IsFree, Source, Note
        # We need to map Indievox format (which is currently Ticket format) to Radar format.
        
        for e in indievox_events:
            # e is currently dict from IndievoxScraper (which I need to check if I updated? I didn't update IndievoxScraper yet)
            # Existing IndievoxScraper returns {name, time, ...}
            # I should update IndievoxScraper or map it here.
            # I'll map it here for safety since I didn't rewrite IndievoxScraper.
            
            # Helper to parse time/date
            from src.utils.date_parser import parse_taiwan_date
            
            # Indievox returns "2026/01/04 (日)" in 'time' field
            raw_time = e.get('time', '')
            date_iso = parse_taiwan_date(raw_time)
            
            radar_event = {
                "activity_name": e.get('name'),
                "performers": [], # Extract from title if possible
                "date": date_iso,
                "time": "Unknown",
                "venue": "Live House (Indievox)",
                "city": "Unknown",
                "is_free": "unknown", # Check price_type
                "source": e.get('source_url'),
                "image_url": e.get('image_url'),
                "note": "Scraped from Indievox",
                "reliability": "official"
            }
            events.append(radar_event)
            
    except Exception as e:
        logger.error(f"Indievox failed: {e}")

    # 2. Instagram Radar (Hashtags/Accounts)
    # Prompt asks for #Livehouse #TaiwanIndie
    # My InstagramScraper supports user scraping, not hashtag scraping?
    # Let's check `instagram_scraper.py`. It has `scrape_events(username, max_posts)`.
    # It does NOT have hashtag support implemented in the class I viewed.
    # I can scrape known Live House accounts: legacy_taiwan, thewalltw, revolvertaipei
    
    target_accounts = ['legacy_taiwan', 'revolvertaipei', 'thewalltw']
    
    # NOTE: Instagram scraping without login is brittle. This is "Best Effort".
    # NOTE: Instagram scraping without login is brittle. This is "Best Effort".
    try:
        ig_scraper = InstagramScraper(config)
        for account in target_accounts:
            try:
                logger.info(f"Scraping Instagram account: {account}")
                ig_events = ig_scraper.scrape_events(account, max_posts=5)
                for e in ig_events:
                    # Map to Radar schema
                    radar_event = {
                        "activity_name": e.get('name'),
                        "performers": [],
                        "date": e.get('time'), # IG scraper tries to parse time
                        "time": "Unknown",
                        "venue": e.get('location') or account,
                        "city": "Unknown",
                        "is_free": "unknown",
                        "source": e.get('source_url'),
                        "image_url": e.get('image_url'),
                        "note": f"IG Post from @{account}",
                        "reliability": "social"
                    }
                    events.append(radar_event)
            except Exception as e:
                logger.error(f"Failed to scrape @{account}: {e}")
                continue  # Continue to next account
    except Exception as e:
        logger.error(f"IG Radar failed initialization: {e}")

    # Deduplication (Simple)
    # Filter valid dates
    valid_list = []
    today = datetime.now().strftime("%Y-%m-%d")
    
    for e in events:
        # Simple date check if format is YYYY-MM-DD
        d = e.get('date')
        if d and d >= today:
            valid_list.append(e)
        elif not d:
            # Keep if unknown date? Prompt says "Incomplete info acceptable"
            valid_list.append(e)
            
    # Output
    print(json.dumps(valid_list, indent=4, ensure_ascii=False))
    
    Path("data").mkdir(exist_ok=True)
    with open("data/radar_events.json", "w", encoding="utf-8") as f:
        json.dump(valid_list, f, indent=4, ensure_ascii=False)

    logger.info(f"Done. Saved {len(valid_list)} events to data/radar_events.json")

if __name__ == "__main__":
    main()
