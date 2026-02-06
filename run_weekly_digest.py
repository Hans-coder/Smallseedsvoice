import logging
import datetime
import os
import yaml
from pathlib import Path
from src.scraper.instagram_scraper import InstagramScraper
from src.processor.digest_builder import DigestBuilder
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger

logger = setup_logger("weekly_digest")

def load_config() -> dict:
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error("Config file not found: config.yaml")
        return {}
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def main():
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Weekly Digest Pipeline')
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
        # Using config values
        ig_config = config.get("pipelines", {}).get("weekly_digest", {}).get("sources", {}).get("instagram", {})
        username = ig_config.get("username", "livetws")
        max_posts = ig_config.get("max_posts", 20)
        
        logger.info(f"Scraping Instagram: @{username}")
        
        # Merge global scraper config with IG config
        scraper_config = config.get("scraper", {})
        scraper_config.update(ig_config)
        
        scraper = InstagramScraper(scraper_config)
        events = scraper.scrape_events(username, max_posts=max_posts)
        
        if not events:
            logger.warning(f"No events found from @{username}. Aborting.")
            return

        logger.info(f"Found {len(events)} raw events from Instagram.")
        
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
            
        # Process & Build Digest
        start_date = datetime.datetime.now()
        end_date = start_date + datetime.timedelta(days=7)
        
        # Initialize Builder with AI enrichment enabled
        builder = DigestBuilder(config={"ai_enrichment": True}) 
        posts = builder.build_digest(events, start_date, end_date)
        
        if not posts:
            logger.warning("No posts generated after processing.")
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
        poster.post_thread(posts)
        
        logger.info("Weekly Digest posted successfully.")

if __name__ == "__main__":
    main()
