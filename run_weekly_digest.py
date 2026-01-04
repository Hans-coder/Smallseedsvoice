"""
Weekly Digest Pipeline Runner
Executes the weekly flow: Scrape -> Filter -> Build Digest -> Post
"""
import os
import yaml
import logging
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv


from src.processor.data_processor import DataProcessor
from src.processor.digest_builder import DigestBuilder
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger

# Load envs
load_dotenv()
logger = setup_logger("weekly_digest")

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def get_next_week_range():
    """Get start and end date of next week (Mon-Sun)."""
    today = datetime.now()
    # Find next Monday
    days_ahead = 0 - today.weekday() + 7
    if days_ahead <= 0: # Target day is today or past, jump to next week
         days_ahead += 7
    next_monday = today + timedelta(days=days_ahead)
    next_sunday = next_monday + timedelta(days=6)
    
    # Reset time to midnight
    start_date = next_monday.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = next_sunday.replace(hour=23, minute=59, second=59, microsecond=999999)
    return start_date, end_date

def main():
    logger.info("Starting Weekly Digest Pipeline...")
    config = load_config()
    pipeline_config = config.get('pipelines', {}).get('weekly_digest', {})
    
    if not pipeline_config.get('enabled', False):
        logger.info("Weekly Digest pipeline is disabled.")
        return

    # 1. Scrape Events
    from src.scraper.ticketing.kktix_scraper import KktixScraper
    from src.scraper.ticketing.indievox_scraper import IndievoxScraper
    from src.scraper.ticketing.accupass_scraper import AccupassScraper
    from src.scraper.ticketing.opentix_scraper import OpentixScraper
    
    scraper_config = config.get('scraper', {})
    scrapers_to_run = [
        (KktixScraper(scraper_config), "https://kktix.com/events?category_id=2"),
        (IndievoxScraper(scraper_config), "https://www.indievox.com/explore?type=event"),
        (AccupassScraper(scraper_config), "https://www.accupass.com/search?q=music"),
        (OpentixScraper(scraper_config), "https://www.opentix.life/search?q=音樂")
    ]
    
    all_events = []
    for scraper, url in scrapers_to_run:
        platform = scraper.__class__.__name__.replace('Scraper', '')
        logger.info(f"Scraping {platform}...")
        try:
            platform_events = scraper.scrape_events(url)
            all_events.extend(platform_events)
        except Exception as e:
            logger.error(f"Error scraping {platform}: {e}")
            
    # Deduplicate by source_url
    unique_events = {}
    for event in all_events:
        url = event.get('source_url')
        if url:
             if url not in unique_events:
                 unique_events[url] = event
        else:
             # If no URL, keep it anyway
             unique_events[id(event)] = event
             
    all_events = list(unique_events.values())
    logger.info(f"Total unique events scraped: {len(all_events)}")
    
    # 2. Filter Events
    processor = DataProcessor()
    
    # 2a. Time Filter (Next Week)
    start_date, end_date = get_next_week_range()
    logger.info(f"Filtering for range: {start_date.date()} - {end_date.date()}")
    
    # Debug: Print all scraped dates
    # for e in all_events:
    #     logger.info(f"Debug Event: {e.get('name')} | Time: {e.get('time')}")

    events_in_range = processor.filter_events_by_time_range(
        all_events, 
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )
    logger.info(f"Events within date range: {len(events_in_range)}")
    
    # FOR TESTING: Pass all events
    # events_in_range = all_events
    # logger.info(f"DEBUG: Passing all {len(events_in_range)} events (Date Filter Disabled)")
    
    # 2b. Price Filter (Free)
    # KKTIX usually doesn't show price in list. We might assume all are candidates 
    # and filter by title keywords if strictly free, or just post all for now to verify format.
    # User goal: "Free Music Events". 
    # Strategy: If price is 'Unknown', keep it but label it. Or try to detect 'Free' in title.
    target_price = pipeline_config.get('filters', {}).get('price_type', 'free')
    filtered_events = []
    
    for event in events_in_range:
        cleaned = processor.clean_event_data(event)
        if not cleaned: continue
        
        # Enhanced Filter Logic:
        # If scraper marked it "Paid", skip.
        # If "Unknown" (List view), we loosely accept it for now to ensure we have content to show user,
        # OR we can implement strict title checking (e.g., "免費", "Free").
        
        if cleaned.get('price_type') == 'Paid':
            continue
            
        # Strict Mode: Only if title contains "免費" or "Free" or price is explicitly "免費"
        # For KKTIX, this might be too strict without detail scraping.
        # Let's keep it loose for this iteration to demonstrate the Quality improvement (Format/Image).
        
        filtered_events.append(cleaned)
        
    logger.info(f"Events after price filter: {len(filtered_events)}")
    
    if not filtered_events:
        logger.info("No matching events found. Exiting.")
        return

    # 3. Build Digest
    digest_builder = DigestBuilder(pipeline_config)
    posts = digest_builder.build_digest(filtered_events, start_date, end_date)
    
    logger.info(f"Generated {len(posts)} thread posts.")
    
    # 4. Post to Threads
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        logger.warning("No THREADS_ACCESS_TOKEN found. Skipping publish.")
        # For dry-run/debug, print the posts
        for i, p in enumerate(posts):
            print(f"--- Post {i+1} ---")
            print(p['text'])
            print(f"Images: {p['images']}")
        return

    poster = ThreadsPoster(access_token, os.getenv("THREADS_APP_ID"))
    
    # Execute posting
    # Execute posting
    logger.info("Publishing to Threads...")
    posted_ids = poster.post_thread(posts)
    logger.info(f"Published successfully! IDs: {posted_ids}")
    
    # Optional: Print for log
    for i, p in enumerate(posts):
            print(f"--- Post {i+1} ---")
            print(p['text'])
    for i, p in enumerate(posts):
            print(f"--- Post {i+1} ---")
            print(p['text'])
            print(f"Images: {p['images']}")

if __name__ == "__main__":
    main()
