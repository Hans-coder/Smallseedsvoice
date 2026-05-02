"""
Script 1: Official Ticketing Platforms Scraper
Targets: KKTIX, OPENTIX, tixCraft, etc.
Output: JSON Array
"""
import json
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime
from pathlib import Path
from src.utils.logger import setup_logger
from src.scraper.ticketing.kktix_scraper import KktixScraper
from src.scraper.ticketing.tixcraft_scraper import TixCraftScraper
from src.scraper.ticketing.ticketplus_scraper import TicketPlusScraper
from src.utils.text_cleaners import get_event_hash, refine_image_url

# Setup logger
logger = setup_logger("official_scraper")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Official Ticketing Platforms Scraper')
    parser.add_argument('--platform', type=str, choices=['kktix', 'tixcraft', 'indievox', 'ticketplus', 'all'], help='Target platform to scrape')
    parser.add_argument('--merge', action='store_true', help='Merge all platform json files into one')
    args = parser.parse_args()
    
    # If no args provided, default to old behavior (scrape all)
    if not args.platform and not args.merge:
        args.platform = 'all'

    logger.info("Starting Official Platforms Scraper...")
    
    config = {
        "request_delay": 2,
        "retry_count": 3,
        "max_pages": 1
    }
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    if args.merge:
        logger.info("Merging data files...")
        merged_events = []
        platform_files = {
            "kktix": "data/events_kktix.json",
            "opentix": "data/events_opentix.json",
            "tixcraft": "data/events_tixcraft.json",
            "indievox": "data/events_indievox.json",
            "ticketplus": "data/events_ticketplus.json"
        }
        
        for p, fpath in platform_files.items():
            if os.path.exists(fpath):
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        merged_events.extend(data)
                        logger.info(f"Loaded {len(data)} events from {p}")
                except Exception as e:
                    logger.error(f"Failed to load {fpath}: {e}")
            else:
                logger.warning(f"File not found: {fpath}")
        
        # Improved Content-Based Deduplication Logic
        unique_events = {}
        for e in merged_events:
            # Hash by cleaned content (Title, Date, Venue)
            name = e.get('name') or e.get('activity_name', 'Unknown')
            date = e.get('date', 'Unknown')
            venue = e.get('venue_name') or e.get('venue', 'Unknown')
            
            content_hash = get_event_hash(name, date, venue)
            
            if content_hash not in unique_events:
                # Refine URL quality before saving
                if e.get('image_url'):
                    e['image_url'] = refine_image_url(e['image_url'])
                unique_events[content_hash] = e
            else:
                # Prefer version with image
                if not unique_events[content_hash].get('image_url') and e.get('image_url'):
                     # Refine URL quality before saving
                    if e.get('image_url'):
                        e['image_url'] = refine_image_url(e['image_url'])
                    unique_events[content_hash] = e
        
        final_list = list(unique_events.values())
        
        # Date Filter & Negative Keyword Filter
        valid_list = []
        today = datetime.now().strftime("%Y-%m-%d")
        
        ignore_keywords = ['音樂劇', '兒童', '合唱', '交響', '室內樂', '古典', '大師班', '獨奏', '管樂', '弦樂', '國樂', '親子', '芭蕾', '舞劇', '講座', '音樂會', '讀劇', '相聲', '脫口秀']
        
        for e in final_list:
            name_check = str(e.get('name', '')).lower() + " " + str(e.get('activity_name', '')).lower()
            if any(k in name_check for k in ignore_keywords) and not 'live' in name_check and not '樂團' in name_check:
                continue # Skip non-band events
                
            if not e.get('date'):
                # Missing date, keep it for Sale Alarm to check ticket_sale_date
                valid_list.append(e)
            elif e.get('date') >= today:
                valid_list.append(e)
                
        # Save Final Output
        with open("data/official_events.json", "w", encoding="utf-8") as f:
            json.dump(valid_list, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Merged & Saved {len(valid_list)} events to data/official_events.json")
        return

    # Scraping Logic
    events = []
    platform = args.platform
    
    # 1. KKTIX
    if platform in ['kktix', 'all']:
        try:
            logger.info("Scraping KKTIX...")
            scraper = KktixScraper(config)
            kktix_events = scraper.scrape_events()
            
            if platform == 'kktix':
                with open("data/events_kktix.json", "w", encoding="utf-8") as f:
                    json.dump(kktix_events, f, indent=4, ensure_ascii=False)
                logger.info(f"Saved {len(kktix_events)} KKTIX events")
            else:
                events.extend(kktix_events)
                
        except Exception as e:
            logger.error(f"KKTIX failed: {e}")
            
    # Platform stats tracking
    platform_stats = {
        'KKTIX': {'scraped': len(kktix_events) if 'kktix_events' in locals() else 0, 'survived': 0},
        'Indievox': {'scraped': 0, 'survived': 0},
        'tixCraft': {'scraped': 0, 'survived': 0},
        'Ticket Plus': {'scraped': 0, 'survived': 0}
    }



    # 3. Indievox
    if platform in ['indievox', 'all']:
        try:
            logger.info("Scraping Indievox...")
            from src.scraper.ticketing.indievox_scraper import IndievoxScraper
            scraper = IndievoxScraper(config)
            indievox_events = scraper.scrape_events()
            
            if platform == 'indievox':
                with open("data/events_indievox.json", "w", encoding="utf-8") as f:
                    json.dump(indievox_events, f, indent=4, ensure_ascii=False)
                logger.info(f"Saved {len(indievox_events)} Indievox events")
            else:
                events.extend(indievox_events)
                platform_stats['Indievox']['scraped'] = len(indievox_events)
                
        except Exception as e:
            logger.error(f"Indievox failed: {e}")

    # 4. tixCraft
    if platform in ['tixcraft', 'all']:
        try:
            logger.info("Scraping tixCraft...")
            scraper = TixCraftScraper(config)
            tixcraft_events = scraper.scrape_events()
            
            if platform == 'tixcraft':
                with open("data/events_tixcraft.json", "w", encoding="utf-8") as f:
                    json.dump(tixcraft_events, f, indent=4, ensure_ascii=False)
                logger.info(f"Saved {len(tixcraft_events)} tixCraft events")
            else:
                events.extend(tixcraft_events)
                platform_stats['tixCraft']['scraped'] = len(tixcraft_events)
                
        except Exception as e:
            logger.error(f"tixCraft failed: {e}")

    # 5. Ticket Plus
    if platform in ['ticketplus', 'all']:
        try:
            logger.info("Scraping Ticket Plus...")
            scraper = TicketPlusScraper(config)
            tp_events = scraper.scrape_events()
            
            if platform == 'ticketplus':
                with open("data/events_ticketplus.json", "w", encoding="utf-8") as f:
                    json.dump(tp_events, f, indent=4, ensure_ascii=False)
                logger.info(f"Saved {len(tp_events)} Ticket Plus events")
            else:
                events.extend(tp_events)
                platform_stats['Ticket Plus']['scraped'] = len(tp_events)
                
        except Exception as e:
            logger.error(f"Ticket Plus failed: {e}")

    # If 'all' mode, perform legacy save to main file
    if platform == 'all':
        unique_events = {}
        for e in events:
            # Same content-based deduplication
            name = e.get('name') or e.get('activity_name', 'Unknown')
            date = e.get('date', 'Unknown')
            venue = e.get('venue_name') or e.get('venue', 'Unknown')
            content_hash = get_event_hash(name, date, venue)
            
            if content_hash not in unique_events:
                 if e.get('image_url'):
                    e['image_url'] = refine_image_url(e['image_url'])
                 unique_events[content_hash] = e
            else:
                if not unique_events[content_hash].get('image_url') and e.get('image_url'):
                    if e.get('image_url'):
                        e['image_url'] = refine_image_url(e['image_url'])
                    unique_events[content_hash] = e
        
        final_list = list(unique_events.values())
        
        valid_list = []
        today = datetime.now().strftime("%Y-%m-%d")
        ignore_keywords = ['音樂劇', '兒童', '合唱', '交響', '室內樂', '古典', '大師班', '獨奏', '管樂', '弦樂', '國樂', '親子', '芭蕾', '舞劇', '講座', '音樂會', '讀劇', '相聲', '脫口秀', '愛樂', '音樂家', '協奏曲']
        
        for e in final_list:
            name_check = str(e.get('name', '')).lower() + " " + str(e.get('activity_name', '')).lower()
            
            # Strict classical check (even if it has '樂團', we filter these out)
            strict_classical_keywords = ['交響', '管樂', '弦樂', '國樂', '愛樂', '協奏曲', '獨奏', '古典']
            is_strict_classical = any(k in name_check for k in strict_classical_keywords)
            
            if is_strict_classical:
                continue
                
            # Normal skip logic for non-band events
            if any(k in name_check for k in ignore_keywords) and not 'live' in name_check and not '樂團' in name_check:
                continue
                
            if not e.get('date'):
                valid_list.append(e)
                # Count survival
                p_name = e.get('ticket_platform')
                if p_name in platform_stats: platform_stats[p_name]['survived'] += 1
            elif e.get('date') >= today:
                valid_list.append(e)
                # Count survival
                p_name = e.get('ticket_platform')
                if p_name in platform_stats: platform_stats[p_name]['survived'] += 1

        with open("data/official_events.json", "w", encoding="utf-8") as f:
            json.dump(valid_list, f, indent=4, ensure_ascii=False)
        
        # Log Summary
        logger.info("\n--- SCRAPE SUMMARY (after date & keyword filtering) ---")
        for p, stats in platform_stats.items():
            if stats['scraped'] > 0 or stats['survived'] > 0:
                logger.info(f"[{p}] Scraped: {stats['scraped']} -> Survived Filter: {stats['survived']}")
            elif platform == 'all':
                logger.info(f"[{p}] No events scraped or scraper failed.")
        
        logger.info(f"\nDone. Saved a total of {len(valid_list)} events to data/official_events.json")

if __name__ == "__main__":
    main()
