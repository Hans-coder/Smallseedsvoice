"""
Script 1: Official Ticketing Platforms Scraper
Targets: KKTIX, OPENTIX, tixCraft, etc.
Output: JSON Array
"""
import json
import logging
import sys
from datetime import datetime
from src.utils.logger import setup_logger
from src.scraper.ticketing.kktix_scraper import KktixScraper
from src.scraper.ticketing.opentix_scraper import OpentixScraper
from src.scraper.ticketing.tixcraft_scraper import TixCraftScraper

# Setup logger
logger = setup_logger("official_scraper")

def main():
    logger.info("Starting Official Platforms Scraper...")
    
    config = {
        "request_delay": 2,
        "retry_count": 3
    }
    
    events = []
    
    # 1. KKTIX
    try:
        scraper = KktixScraper(config)
        kktix_events = scraper.scrape_events()
        events.extend(kktix_events)
    except Exception as e:
        logger.error(f"KKTIX failed: {e}")

    # 2. OPENTIX
    try:
        scraper = OpentixScraper(config)
        opentix_events = scraper.scrape_events()
        events.extend(opentix_events)
    except Exception as e:
        logger.error(f"OPENTIX failed: {e}")

    # 3. tixCraft
    try:
        scraper = TixCraftScraper(config)
        tixcraft_events = scraper.scrape_events()
        events.extend(tixcraft_events)
    except Exception as e:
        logger.error(f"tixCraft failed: {e}")

    # 4. Other Platforms (Placeholders)
    # The user requested 9 platforms. Implementing all in one go is complex without DOM info.
    # Future work: Implement TicketPlus, Kham, Ibon, FamiTicket, Era, Udn
    logger.info("Other platforms (TicketPlus, Kham, etc.) pending implementation.")

    # Deduplication
    unique_events = {}
    for e in events:
        # Key: ID
        if e['activity_id'] not in unique_events:
            unique_events[e['activity_id']] = e
        else:
            # Merge logic if needed (e.g. multiple sources?)
            # Prompt says "If same activity on different platforms, keep multi-platform links"
            # Current ID logic includes platform name prefix, so they WON'T dedup across platforms automatically.
            # ID = "kktix_Name_Date". 
            # If we want to dedup across platforms, we need a platform-agnostic key.
            # But prompt says "Included activity_id (Platform + Name + Date)". 
            # "Within same platform, no duplicates". My scraper logic handles list iteration, but sets/dict ensures it.
            # "If different platform, keep multi-platform links" -> this implies we keep them as separate entries OR merge them?
            # "Retain multi-platform links" usually means one object with ["kktix.com", "tixcraft.com"].
            # But the accepted schema has "ticket_platform" (single string) and "ticket_url" (single string).
            # This contradicts "Keep multi-platform links" inside one object unless "ticket_url" is an array?
            # Prompt says "ticket_url" (singular).
            # Re-reading: "ticket_platform name", "ticket_url", "source_platform".
            # "If different platform, keep multi-platform links" might mean "Keep both entries" or "Merge"?
            # Prompt says "Output Format: JSON Array".
            # Given the schema "activity_id" includes Platform, they are distinct rows.
            pass

    final_list = list(unique_events.values())
    
    # Validation filters
    # "Only output not expired or about to sell"
    # Basic date filter
    valid_list = []
    today = datetime.now().strftime("%Y-%m-%d")
    for e in final_list:
        if e['date'] and e['date'] >= today:
            valid_list.append(e)
    
    # Output
    print(json.dumps(valid_list, indent=4, ensure_ascii=False))
    
    # Save to file
    with open("data/official_events.json", "w", encoding="utf-8") as f:
        json.dump(valid_list, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Done. Saved {len(valid_list)} events to data/official_events.json")

if __name__ == "__main__":
    main()
