import logging
import datetime
import os
import yaml
from pathlib import Path
from src.scraper.instagram_scraper import InstagramScraper
from src.scraper.ticketing.kktix_scraper import KktixScraper
from src.scraper.ticketing.opentix_scraper import OpentixScraper
from src.processor.digest_builder import DigestBuilder
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = setup_logger("weekly_digest")

def load_config() -> dict:
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error("Config file not found: config.yaml")
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def is_free_event(event: dict) -> bool:
    """Check if event is free based on price field."""
    price = event.get('price')
    if not price:
        return False # Strict checking
        
    price_str = str(price).lower().strip()
    
    # 1. Exact "0" check
    if price_str == '0':
        return True
    
    # 2. Explicit free keywords
    free_keywords = ['免費', 'free', '0元', '無需購票', '自由入場']
    if any(k in price_str for k in free_keywords):
        return True
    
    # 3. Check for specific paid patterns if no free keyword found
    # e.g. "$100", "NT$300", "300元"
    # We want to AVOID incorrectly matching "2026" (year) as a price
    import re
    # Look for $ or NT$ followed by digits, OR digits followed by 元
    paid_pattern = r'(?:nt\$|\$|twd\$?)\s*(\d+(?:,\d+)*)|(\d+(?:,\d+)*)\s*元'
    matches = re.findall(paid_pattern, price_str)
    
    for match in matches:
        for group in match:
            if group and group.replace(',', '').isdigit():
                 val = int(group.replace(',', ''))
                 if val > 0:
                     return False # Found a positive price -> Paid
    
    # If we have text but no free keywords and no currency symbols, 
    # and it's not "0", assume paid/unknown -> False (Strict)
    return False

def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Weekly Digest Pipeline (Free)')
    parser.add_argument('--step', type=str, choices=['scrape', 'process', 'post', 'all'], default='all', help='Pipeline step to execute')
    args = parser.parse_args()
    
    logger.info(f"Starting Weekly Digest Pipeline (Step: {args.step})...")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # 1. Load Config
    config = load_config()
    if not config:
        return

    # --- Step 1: Scrape ---
    if args.step in ['scrape', 'all']:
        # 0. Clean up stale data
        raw_data_path = Path("data/digest_raw.json")
        if raw_data_path.exists():
            raw_data_path.unlink()
            logger.info("Removed stale data/digest_raw.json")

        events = []
        
        # 1. Instagram Scraper
        # 1. Instagram Scraper
#        try:
#            ig_config = config.get("pipelines", {}).get("weekly_digest", {}).get("sources", {}).get("instagram", {})
#            username = ig_config.get("username", "livetws")
#            max_posts = ig_config.get("max_posts", 20)
#            
#            logger.info(f"Scraping Instagram: @{username}")
#            
#            # Merge global scraper config with IG config
#            scraper_config = config.get("scraper", {})
#            scraper_config.update(ig_config)
#            
#            ig_scraper = InstagramScraper(scraper_config)
#            ig_events = ig_scraper.scrape_events(username, max_posts=max_posts)
#            events.extend(ig_events)
#            logger.info(f"Found {len(ig_events)} events from Instagram.")
#        except Exception as e:
#            logger.error(f"Instagram scrape failed: {e}")

        # 2. KKTIX Scraper (Music Tag)
        try:
            logger.info("Scraping KKTIX (Music)...")
            kktix_scraper = KktixScraper(config.get("scraper", {}))
            # Just scrape music tag page
            kktix_events = kktix_scraper.scrape_events(url="https://kktix.com/events?event_tag_ids_in=13")
            
            # Filter Free
            free_kktix = [e for e in kktix_events if is_free_event(e)]
            events.extend(free_kktix)
            logger.info(f"Found {len(free_kktix)} free events from KKTIX (Total: {len(kktix_events)}).")
        except Exception as e:
            logger.error(f"KKTIX scrape failed: {e}")

        # 3. OPENTIX Scraper
        try:
            logger.info("Scraping OPENTIX (Music)...")
            opentix_scraper = OpentixScraper(config.get("scraper", {}))
            opentix_events = opentix_scraper.scrape_events()
            
            # Filter Free
            free_opentix = [e for e in opentix_events if is_free_event(e)]
            events.extend(free_opentix)
            logger.info(f"Found {len(free_opentix)} free events from OPENTIX (Total: {len(opentix_events)}).")
        except Exception as e:
            logger.error(f"OPENTIX scrape failed: {e}")

        if not events:
            logger.warning(f"No events found from any source. Writing empty list to prevent stale data usage.")
            # Write empty list so subsequent steps know there is no data
            with open("data/digest_raw.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            return

        logger.info(f"Total Unique Events Found: {len(events)}")
        
        # Save raw events
        with open("data/digest_raw.json", "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)
        logger.info("Saved raw events to data/digest_raw.json")
        
    # --- Step 2: Process ---
    if args.step in ['process', 'all']:
        # Load raw events
        if not os.path.exists("data/digest_raw.json"):
            logger.error("data/digest_raw.json not found. Run --step scrape first.")
            return
            
        with open("data/digest_raw.json", "r", encoding="utf-8") as f:
            events = json.load(f)
            
        if not events:
            logger.warning("No events to process (list is empty).")
            # Create empty posts file to be safe
            with open("data/digest_posts.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            return

        # Process & Build Digest
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=7)
        
        # Initialize Builder with AI enrichment enabled
        builder = DigestBuilder(config={"ai_enrichment": True}) 
        try:
            posts = builder.build_digest(events, start_date, end_date)
        except Exception as e:
            logger.error(f"DigestBuilder failed: {e}", exc_info=True)
            return
        
        if not posts:
            logger.warning("No posts generated after processing.")
            # Ensure we don't leave stale posts file
            with open("data/digest_posts.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            return

        logger.info(f"Generated {len(posts)} threads posts.")
        
        # Save processed posts
        with open("data/digest_posts.json", "w", encoding="utf-8") as f:
            json.dump(posts, f, indent=4, ensure_ascii=False)
        logger.info("Saved posts to data/digest_posts.json")

    # --- Step 3: Post ---
    if args.step in ['post', 'all']:
        # Load posts
        if not os.path.exists("data/digest_posts.json"):
            logger.error("data/digest_posts.json not found. Run --step process first.")
            return
            
        with open("data/digest_posts.json", "r", encoding="utf-8") as f:
            posts = json.load(f)

        if not posts:
            logger.info("No posts to publish.")
            return

        # Post to Threads
        access_token = os.getenv("THREADS_ACCESS_TOKEN")
        if not access_token:
            logger.error("THREADS_ACCESS_TOKEN not found. Skipping post.")
            # Print preview for debugging
            for i, post in enumerate(posts):
                print(f"--- Post {i+1} ---")
                print(post['text'])
            return

        poster = ThreadsPoster(access_token)
        created_ids = poster.post_thread(posts)
        
        if not created_ids:
            logger.error("Failed to create any threads posts. Exiting with error.")
            import sys
            sys.exit(1)
            
        logger.info(f"Weekly Digest posted successfully. IDs: {created_ids}")

if __name__ == "__main__":
    main()
