import logging
import datetime
import os
import yaml
from pathlib import Path
from src.scraper.instagram_scraper import InstagramScraper
from src.scraper.ticketing.kktix_scraper import KktixScraper
from src.processor.digest_builder import DigestBuilder
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger
from src.utils.error_handler import log_scraping_error
from src.utils.text_cleaners import get_event_hash, refine_image_url
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

def is_hot_event(event: dict) -> bool:
    """判斷是否為熱門大型活動 (如音樂祭)"""
    name = str(event.get('name', '')).lower()
    caption = str(event.get('caption', '')).lower()
    
    # 常見大型祭典關鍵字
    hot_keywords = ['祭', '音樂節', 'festival', '大港開唱', '浮現祭', '浪人祭', '春浪', 'ultra']
    
    if any(k in name for k in hot_keywords) or any(k in caption for k in hot_keywords):
        return True
        
    # 如果是從 IG 抓的，檢查來源帳號是否為知名音樂節
    source_account = event.get('source_account')
    if source_account in ['emerge_fest', 'megaportfest', 'ultrataiwan', 'springwave_asia']:
        return True
        
    return False

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
        # 0. Clean up stale data
        raw_data_path = Path("data/digest_raw.json")
        if raw_data_path.exists():
            raw_data_path.unlink()
            logger.info("Removed stale data/digest_raw.json")

        events = []
        
        # 1. Instagram Scraper
        try:
            ig_config = config.get("pipelines", {}).get("weekly_digest", {}).get("sources", {}).get("instagram", {})
            if ig_config.get("enabled", True):
                usernames = ig_config.get("usernames", ["livetws"])
                max_posts = ig_config.get("max_posts", 20)
                
                logger.info(f"Scraping Instagram accounts: {usernames}")
                
                # Merge global scraper config with IG config
                scraper_config = config.get("scraper", {})
                scraper_config.update(ig_config)
                
                ig_scraper = InstagramScraper(scraper_config)
                # 使用新開發的批量抓取方法
                ig_events = ig_scraper.scrape_multiple_accounts(usernames, max_posts=max_posts)
                
                # 標註熱門活動
                for e in ig_events:
                    e['is_hot'] = is_hot_event(e)
                
                events.extend(ig_events)
                logger.info(f"Found {len(ig_events)} events from Instagram.")
        except Exception as e:
            logger.error(f"Instagram scrape failed: {e}")
            log_scraping_error("Instagram", e)

        # 2. KKTIX Scraper (Music Tag + Keywords)
        try:
            logger.info("Scraping KKTIX (Music & Keywords)...")
            kktix_scraper = KktixScraper(config.get("scraper", {}))
            # 腳本內部已更新，會自動抓取 Music Tag + 關鍵字搜尋
            kktix_events = kktix_scraper.scrape_events()
            
            # 過濾條件：免費 OR 大型熱門活動
            relevant_kktix = []
            skipped_count = 0
            for e in kktix_events:
                e['is_hot'] = is_hot_event(e)
                # Take all events as requested
                relevant_kktix.append(e)
            
            events.extend(relevant_kktix)
            logger.info(f"KKTIX: Found {len(relevant_kktix)} relevant events.")
        except Exception as e:
            logger.error(f"KKTIX scrape failed: {e}")
            log_scraping_error("KKTIX", e)


        # 4. Indievox Scraper
        try:
            logger.info("Scraping Indievox (Table View)...")
            from src.scraper.ticketing.indievox_scraper import IndievoxScraper
            indievox_scraper = IndievoxScraper(config.get("scraper", {}))
            indievox_events = indievox_scraper.scrape_events()
            
            relevant_indievox = []
            skipped_count = 0
            for e in indievox_events:
                e['is_hot'] = is_hot_event(e)
                # Take all events as requested
                relevant_indievox.append(e)
            
            events.extend(relevant_indievox)
            logger.info(f"Indievox: Found {len(relevant_indievox)} relevant events.")
        except Exception as e:
            logger.error(f"Indievox scrape failed: {e}")
            log_scraping_error("Indievox", e)
            
        # 5. StreetVoice Scraper (Discovery)
        try:
            logger.info("Scraping StreetVoice (Discovery)...")
            from src.scraper.discovery.streetvoice_scraper import StreetVoiceScraper
            sv_scraper = StreetVoiceScraper(config.get("scraper", {}))
            sv_events = sv_scraper.scrape_events()
            
            # For StreetVoice, we take everything for now as it's targeted discovery
            events.extend(sv_events)
            logger.info(f"StreetVoice: Added {len(sv_events)} discovery events.")
        except Exception as e:
            logger.error(f"StreetVoice scrape failed: {e}")
            log_scraping_error("StreetVoice", e)

        if not events:
            logger.warning(f"No events found from any source. Writing empty list to prevent stale data usage.")
            # Write empty list so subsequent steps know there is no data
            with open("data/digest_raw.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            return

        # 6. Improved Cross-Platform Deduplication
        unique_events = {}
        for e in events:
            # 1. Refine image quality
            if e.get('image_url'):
                e['image_url'] = refine_image_url(e['image_url'])
            
            # 2. Content-based deduplication
            name = e.get('name') or e.get('activity_name')
            date = e.get('date') or e.get('time')
            venue = e.get('venue_name') or e.get('location') or e.get('venue')
            
            content_hash = get_event_hash(name, date, venue)
            
            # If already exists, keep the one with a better image or more detail? 
            # Current logic: first one found (Instagram > KKTIX > Others usually)
            if content_hash not in unique_events:
                unique_events[content_hash] = e
            else:
                # Prefer events with images
                if not unique_events[content_hash].get('image_url') and e.get('image_url'):
                    unique_events[content_hash] = e

        final_events = list(unique_events.values())
        logger.info(f"Total Events: {len(events)} -> Deduplicated: {len(final_events)}")
        
        # Save raw events
        with open("data/digest_raw.json", "w", encoding="utf-8") as f:
            json.dump(final_events, f, indent=4, ensure_ascii=False)
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
        start_date = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_wd = start_date.weekday()
        
        # Semi-weekly logic: 
        # Monday (0) covers Mon, Tue, Wed (3 days limit)
        # Thursday (3) covers Thu, Fri, Sat, Sun (4 days limit)
        if today_wd == 0:
            end_date = start_date + datetime.timedelta(days=2, hours=23, minutes=59, seconds=59)
        elif today_wd == 3:
            end_date = start_date + datetime.timedelta(days=3, hours=23, minutes=59, seconds=59)
        else:
            end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        
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
        
        # Save updated raw events back (now containing AI-extracted performers)
        with open("data/digest_raw.json", "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)
        
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
