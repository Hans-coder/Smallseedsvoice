"""
Real-time Alerts Pipeline Runner
Executes: Scrape Ticketing Sites -> Check DB (Dedup) -> Post New Events
"""
import os
import yaml
import time
from dotenv import load_dotenv

from src.scraper.ticketing.kktix_scraper import KktixScraper
from src.database.db_manager import DatabaseManager
from src.processor.data_processor import DataProcessor
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger

load_dotenv()
logger = setup_logger("realtime_alerts")

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def main():
    logger.info("Starting Real-time Alerts Pipeline...")
    config = load_config()
    pipeline_config = config.get('pipelines', {}).get('realtime_alerts', {})
    
    if not pipeline_config.get('enabled', False):
        logger.info("Real-time Alerts pipeline is disabled.")
        return

    # 1. Initialize Components
    db_manager = DatabaseManager(config['database']['path'])
    processor = DataProcessor()
    
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    poster = None
    if access_token:
        poster = ThreadsPoster(access_token, os.getenv("THREADS_APP_ID"))
    else:
        logger.warning("No THREADS_ACCESS_TOKEN. Will skip posting.")
        
    scraper_config = config.get('scraper', {})
        
    # 2. Scrape Sources
    sources = pipeline_config.get('sources', {}).get('sites', [])
    new_events = []
    
    for source in sources:
        if not source.get('enabled', False): continue
        
        name = source.get('name')
        url = source.get('url')
        logger.info(f"Checking {name} at {url}...")
        
        events = []
        if name == 'kktix':
            scraper = KktixScraper(scraper_config)
            events = scraper.scrape_events(url)
        # Add other scrapers here
        
        # 3. Process & Dedup
        for event in events:
            # Clean
            cleaned = processor.clean_event_data(event)
            if not cleaned: continue
            
            # Check DB (add_event returns True if new)
            # Note: We add to DB immediately. 
            # If posting fails, we might want to track 'is_posted' separately.
            # DBManager sets is_posted=0 by default.
            
            # We first check if it exists to know if we should alert
            # But add_event does "INSERT OR IGNORE". 
            # If it returns True, it's new.
            if db_manager.add_event(cleaned):
                logger.info(f"New Event Found: {cleaned['name']}")
                new_events.append(cleaned)
    
    logger.info(f"Found {len(new_events)} new events.")
    
    # 4. Post New Events
    template = pipeline_config.get('publishing', {}).get('template')
    
    for event in new_events:
        # Format text
        formatted_text = processor.format_for_threads(event, template)
        
        # Check if we should post (e.g. valid price, not passed time)
        # Assuming scraper only fetched valid future events.
        
        if poster:
            # Real-time alert: Single post
            logger.info(f"Posting alert for: {event['name']}")
            if poster.post_event(event, formatted_text):
                # Mark as posted
                # We need the ID. add_event doesn't return ID easily unless we query.
                # But we can query by unique constraint (name, location, time)
                # Or simplisticly: query list of unposted and match.
                
                # Let's find the event ID to mark as posted
                # Since we just added it, it's unposted.
                # db_manager.mark_as_posted(...)
                pass
                # To properly mark logic, we might need DBManager to return ID on add.
        else:
            logger.info(f"DRY RUN: Would post:\n{formatted_text}")

if __name__ == "__main__":
    main()
