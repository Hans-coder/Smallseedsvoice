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
from src.scraper.ticketing.opentix_scraper import OpentixScraper
from src.scraper.ticketing.tixcraft_scraper import TixCraftScraper
from src.scraper.ticketing.ticketplus_scraper import TicketPlusScraper
from src.utils.text_cleaners import get_event_hash, refine_image_url

# Setup logger
logger = setup_logger("official_scraper")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Official Ticketing Platforms Scraper')
    parser.add_argument('--platform', type=str, choices=['kktix', 'opentix', 'tixcraft', 'indievox', 'ticketplus', 'all'], help='Target platform to scrape')
    parser.add_argument('--merge', action='store_true', help='Merge all platform json files into one')
    args = parser.parse_args()
    
    # If no args provided, default to old behavior (scrape all)
    if not args.platform and not args.merge:
        args.platform = 'all'

    logger.info("Starting Official Platforms Scraper...")
    
    config = {
        "request_delay": 2,
        "retry_count": 3,
        "max_pages": 30
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
        
        # Date Filter: Only drop if we are SURE it's in the past. Keep if 'date' is missing/null.
        valid_list = []
        today = datetime.now().strftime("%Y-%m-%d")
        for e in final_list:
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

    # 2. OPENTIX
    if platform in ['opentix', 'all']:
        try:
            logger.info("Scraping OPENTIX...")
            scraper = OpentixScraper(config)
            opentix_events = scraper.scrape_events()
            
            if platform == 'opentix':
                with open("data/events_opentix.json", "w", encoding="utf-8") as f:
                    json.dump(opentix_events, f, indent=4, ensure_ascii=False)
                logger.info(f"Saved {len(opentix_events)} OPENTIX events")
            else:
                events.extend(opentix_events)
                
        except Exception as e:
            logger.error(f"OPENTIX failed: {e}")

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
        for e in final_list:
            if not e.get('date'):
                valid_list.append(e)
            elif e.get('date') >= today:
                valid_list.append(e)

        with open("data/official_events.json", "w", encoding="utf-8") as f:
            json.dump(valid_list, f, indent=4, ensure_ascii=False)
        logger.info(f"Done. Saved {len(valid_list)} events to data/official_events.json")

if __name__ == "__main__":
    main()
