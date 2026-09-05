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
from src.utils.text_cleaners import get_event_hash, refine_image_url, is_same_event, merge_event_details
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
    parser.add_argument('--source', type=str, choices=['instagram', 'kktix', 'indievox', 'ticketplus', 'tixcraft', 'streetvoice', 'all'], default='all', help='Specific source to scrape')
    parser.add_argument('--append', action='store_true', help='Append results to existing digest_raw.json instead of overwriting (for multi-scraper supplemental runs)')
    parser.add_argument('--exclude-streetvoice', action='store_true', help='Filter out events already captured by StreetVoice (reads data/streetvoice_raw.json)')
    args = parser.parse_args()
    
    logger.info(f"Starting Weekly Digest Pipeline (Step: {args.step}, Source: {args.source})...")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    # 1. Load Config
    config = load_config()
    if not config:
        return

    # --- Step 1: Scrape ---
    if args.step in ['scrape', 'all']:
        # 0. Clean up stale data (skip if --append to accumulate multiple scraper runs)
        raw_data_path = Path("data/digest_raw.json")
        if raw_data_path.exists() and not args.append:
            raw_data_path.unlink()
            logger.info("Removed stale data/digest_raw.json")
        elif args.append and raw_data_path.exists():
            logger.info("--append mode: keeping existing data/digest_raw.json and adding to it")

        # Load existing events if in append mode
        events = []
        if args.append and raw_data_path.exists():
            try:
                with open(raw_data_path, 'r', encoding='utf-8') as f:
                    events = json.load(f)
                logger.info(f"--append mode: loaded {len(events)} existing events")
            except Exception:
                events = []
        
        # 1. StreetVoice Scraper (Discovery base - runs first to capture indie performers)
        if args.source in ['streetvoice', 'all']:
            try:
                logger.info("Scraping StreetVoice (Discovery)...")
                from src.scraper.discovery.streetvoice_scraper import StreetVoiceScraper
                sv_scraper = StreetVoiceScraper(config.get("scraper", {}))
                sv_events = sv_scraper.scrape_events()
                events.extend(sv_events)
                logger.info(f"StreetVoice: Added {len(sv_events)} discovery events.")
            except Exception as e:
                logger.error(f"StreetVoice scrape failed: {e}")
                log_scraping_error("StreetVoice", e)

        # Save StreetVoice events separately for backward compatibility
        _sv_events_to_save = locals().get('sv_events', [])
        if args.source in ['streetvoice', 'all'] and _sv_events_to_save:
            sv_raw_path = Path("data/streetvoice_raw.json")
            with open(sv_raw_path, 'w', encoding='utf-8') as f:
                json.dump(_sv_events_to_save, f, indent=4, ensure_ascii=False)
            logger.info(f"Saved {len(_sv_events_to_save)} StreetVoice events to data/streetvoice_raw.json")

        # 2. KKTIX Scraper (Official Atom feed + Keywords)
        if args.source in ['kktix', 'all']:
            try:
                logger.info("Scraping KKTIX (Atom feeds & Keywords)...")
                kktix_scraper = KktixScraper(config.get("scraper", {}))
                kktix_events = kktix_scraper.scrape_events()
                
                relevant_kktix = []
                for e in kktix_events:
                    e['is_hot'] = is_hot_event(e)
                    relevant_kktix.append(e)
                
                events.extend(relevant_kktix)
                logger.info(f"KKTIX: Found {len(relevant_kktix)} relevant events.")
            except Exception as e:
                logger.error(f"KKTIX scrape failed: {e}")
                log_scraping_error("KKTIX", e)

        # 3. Indievox Scraper
        if args.source in ['indievox', 'all']:
            try:
                logger.info("Scraping Indievox (Table View)...")
                from src.scraper.ticketing.indievox_scraper import IndievoxScraper
                indievox_scraper = IndievoxScraper(config.get("scraper", {}))
                indievox_events = indievox_scraper.scrape_events()
                
                relevant_indievox = []
                for e in indievox_events:
                    e['is_hot'] = is_hot_event(e)
                    relevant_indievox.append(e)
                
                events.extend(relevant_indievox)
                logger.info(f"Indievox: Found {len(relevant_indievox)} relevant events.")
            except Exception as e:
                logger.error(f"Indievox scrape failed: {e}")
                log_scraping_error("Indievox", e)

        # 4. tixCraft Scraper
        if args.source in ['tixcraft', 'all']:
            try:
                logger.info("Scraping tixCraft...")
                from src.scraper.ticketing.tixcraft_scraper import TixCraftScraper
                scraper = TixCraftScraper(config.get("scraper", {}))
                tix_events = scraper.scrape_events()
                events.extend(tix_events)
                logger.info(f"tixCraft: Found {len(tix_events)} events.")
            except Exception as e:
                logger.error(f"tixCraft scrape failed: {e}")
                log_scraping_error("tixCraft", e)

        # 5. Ticket Plus Scraper
        if args.source in ['ticketplus', 'all']:
            try:
                logger.info("Scraping Ticket Plus...")
                from src.scraper.ticketing.ticketplus_scraper import TicketPlusScraper
                scraper = TicketPlusScraper(config.get("scraper", {}))
                tp_events = scraper.scrape_events()
                events.extend(tp_events)
                logger.info(f"Ticket Plus: Found {len(tp_events)} events.")
            except Exception as e:
                logger.error(f"Ticket Plus scrape failed: {e}")
                log_scraping_error("Ticket Plus", e)

        # 6. Instagram Scraper (Optional)
        if args.source in ['instagram', 'all']:
            try:
                ig_config = config.get("pipelines", {}).get("weekly_digest", {}).get("sources", {}).get("instagram", {})
                if ig_config.get("enabled", False):
                    usernames = ig_config.get("usernames", ["livetws"])
                    max_posts = ig_config.get("max_posts", 20)
                    
                    logger.info(f"Scraping Instagram accounts: {usernames}")
                    scraper_config = config.get("scraper", {})
                    scraper_config.update(ig_config)
                    
                    ig_scraper = InstagramScraper(scraper_config)
                    ig_events = ig_scraper.scrape_multiple_accounts(usernames, max_posts=max_posts)
                    for e in ig_events:
                        e['is_hot'] = is_hot_event(e)
                    events.extend(ig_events)
                    logger.info(f"Found {len(ig_events)} events from Instagram.")
            except Exception as e:
                logger.error(f"Instagram scrape failed: {e}")
                log_scraping_error("Instagram", e)

        if not events:
            logger.warning(f"No events found from any source. Writing empty list to prevent stale data usage.")
            with open("data/digest_raw.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            return

        # 7. Improved Cross-Platform Deduplication & Smart Detail Merging
        deduplicated_events = []
        hash_to_idx = {}

        for e in events:
            # Refine image quality
            if e.get('image_url'):
                e['image_url'] = refine_image_url(e['image_url'])
            
            name = e.get('name') or e.get('activity_name', '')
            date = e.get('date') or e.get('time', '')
            venue = e.get('venue_name') or e.get('location') or e.get('venue', '')
            
            content_hash = get_event_hash(name, date, venue)
            
            matched_idx = -1
            if content_hash in hash_to_idx:
                matched_idx = hash_to_idx[content_hash]
            else:
                # Fuzzy matching across existing events
                for idx, existing in enumerate(deduplicated_events):
                    if is_same_event(existing, e):
                        matched_idx = idx
                        break

            if matched_idx >= 0:
                # Merge details into existing event (performers + ticket info + poster)
                deduplicated_events[matched_idx] = merge_event_details(deduplicated_events[matched_idx], e)
                hash_to_idx[content_hash] = matched_idx
            else:
                new_idx = len(deduplicated_events)
                deduplicated_events.append(e)
                hash_to_idx[content_hash] = new_idx

        final_events = deduplicated_events
        logger.info(f"Total Events: {len(events)} -> Deduplicated & Merged: {len(final_events)}")
        
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
        # 固定「下一個完整日曆週」（週一到週日），讓週一與週四兩個 workflow 看同一窗口。
        # 例如：週一跑 → 下週一到週日；週四跑 → 同一個下週一到週日。
        today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days_until_next_monday = (7 - today.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7  # 今天就是週一，則取「下下週一」
        start_date = today + datetime.timedelta(days=days_until_next_monday)
        end_date = start_date + datetime.timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        # --- Exclude StreetVoice duplicates if requested ---
        if args.exclude_streetvoice:
            sv_raw_path = Path("data/streetvoice_raw.json")
            if sv_raw_path.exists():
                try:
                    with open(sv_raw_path, 'r', encoding='utf-8') as f:
                        sv_events_cached = json.load(f)
                    sv_hashes = set()
                    for e in sv_events_cached:
                        sv_name = e.get('name') or e.get('activity_name')
                        sv_date = e.get('date') or e.get('time')
                        sv_venue = e.get('venue_name') or e.get('location') or e.get('venue')
                        sv_hashes.add(get_event_hash(sv_name, sv_date, sv_venue))
                    before_count = len(events)
                    events = [
                        e for e in events
                        if get_event_hash(
                            e.get('name') or e.get('activity_name'),
                            e.get('date') or e.get('time'),
                            e.get('venue_name') or e.get('location') or e.get('venue')
                        ) not in sv_hashes and not any(is_same_event(sv_e, e) for sv_e in sv_events_cached)
                    ]
                    logger.info(f"--exclude-streetvoice: removed {before_count - len(events)} duplicates already on StreetVoice. Remaining: {len(events)}")
                except Exception as ex:
                    logger.warning(f"Could not load StreetVoice cache for dedup: {ex}")
            else:
                logger.warning("--exclude-streetvoice set but data/streetvoice_raw.json not found. Skipping dedup.")
        
        if not events:
            logger.warning("No events to process after filtering (possibly all were StreetVoice duplicates).")
            with open("data/digest_posts.json", "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            return
        
        
        # Initialize Builder with AI enrichment enabled
        builder = DigestBuilder(config={"ai_enrichment": True}) 
        try:
            posts = builder.build_digest(events, start_date, end_date)
        except Exception as e:
            logger.error(f"DigestBuilder failed: {e}", exc_info=True)
            return
        
        # Save updated raw events back (now containing AI-extracted performers)
        with open("data/digest_raw.json", "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)

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
