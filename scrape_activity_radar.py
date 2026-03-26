"""
Radar Activity Scraper
Targets: 
1. Indievox (Live House events)
2. Instagram (Selected accounts like Legacy, Revolver)

Output: data/radar_events.json
"""
import json
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from src.utils.performer_tracker import PerformerTracker
from src.utils.error_handler import log_scraping_error
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

from src.utils.logger import setup_logger
from src.scraper.ticketing.indievox_scraper import IndievoxScraper
from src.scraper.instagram_scraper import InstagramScraper
from src.scraper.discovery.streetvoice_scraper import StreetVoiceScraper

logger = setup_logger("radar_scraper")

def main():
    logger.info("Starting Radar Activity Scraper...")
    
    # Ensure data directory exists
    Path("data").mkdir(exist_ok=True)
    
    radar_events = []
    
    # 1. Indievox
    try:
        logger.info("Scraping Indievox...")
        iv_scraper = IndievoxScraper({"max_pages": 3})
        # Use table view for easier parsing
        iv_events = iv_scraper.scrape_events("https://www.indievox.com/activity/list?type=table")
        
        radar_events.extend(iv_events)
        logger.info(f"Added {len(iv_events)} events from Indievox.")
    except Exception as e:
        logger.error(f"Indievox scrape failed: {e}")
        log_scraping_error("Radar-Indievox", e)

    # 2. StreetVoice (Discovery)
    try:
        logger.info("Scraping StreetVoice for Discovery Radar...")
        sv_scraper = StreetVoiceScraper({"timeout": 30})
        sv_events = sv_scraper.scrape_events()
        
        # Transform SV events to Radar schema (SV already has compatible keys)
        radar_events.extend(sv_events)
        logger.info(f"Added {len(sv_events)} events from StreetVoice.")
    except Exception as e:
        logger.error(f"StreetVoice radar scrape failed: {e}")
        log_scraping_error("Radar-StreetVoice", e)

#    # 2. Instagram
#    # Target Accounts: legacy_taiwan, revolvertaipei
#    ig_accounts = [
#        "legacy_taiwan",
#        "revolvertaipei",
#        "thewalllivehouse",
#        "witchhouse.tw"
#    ]
#    
#    try:
#        logger.info("Scraping Instagram Accounts...")
#        # Use existing InstagramScraper
#        # It needs config with optional login
#        config = {
#            "retry_count": 3,
#            "request_delay": 5, # Slower for IG
#            # Add credentials if available in env, else guest mode (might be limited)
#            "ig_username": os.getenv("IG_USERNAME"),
#            "ig_password": os.getenv("IG_PASSWORD")
#        }
#        
#        ig_scraper = InstagramScraper(config)
#        
#        for account in ig_accounts:
#            try:
#                logger.info(f"Fetching @{account}...")
#                events = ig_scraper.scrape_events(account, max_posts=5)
#                
#                # Transform IG events to Radar schema
#                for e in events:
#                    radar_event = {
#                        "activity_name": e['name'],
#                        "performers": [],
#                        "date": e['date'] or e['time'], # Fallback
#                        "time": "Unknown",
#                        "venue": e['location'] if e['location'] != "未提供" else account,
#                        "city": "Unknown",
#                        "is_free": "unknown",
#                        "source": e['source_url'],
#                        "image_url": e['image_url'],
#                        "note": f"IG Post from @{account}",
#                        "reliability": "social"
#                    }
#                    radar_events.append(radar_event)
#                
#                logger.info(f"Added {len(events)} events from @{account}")
#            except Exception as e:
#                error_msg = str(e)
#                if "401" in error_msg or "Unauthorized" in error_msg:
#                    logger.warning(f"Skipping @{account} due to Private/Restricted access (401): {error_msg}")
#                else:
#                    logger.error(f"Failed to scrape @{account}: {e}")
#                
#    except Exception as e:
#        logger.error(f"Instagram scraping section failed: {e}")

    # Deduplication (by URL or Name+Date+Venue)
    unique_events = {}
    for e in radar_events:
        # Use URL if available
        url = e.get('ticket_url') or e.get('source_url') or e.get('source')
        if url and str(url).startswith('http'):
            unique_events[url] = e
        else:
            name = e.get('name') or e.get('activity_name', 'Unknown')
            date = e.get('date', 'Unknown')
            venue = e.get('venue_name') or e.get('venue', 'Unknown')
            key = f"{name}_{date}_{venue}"
            unique_events[key] = e
            
    final_list = list(unique_events.values())
    
    # 3. AI Enrichment (Spotlight recent performers)
    logger.info("Enriching radar events with AI Spotlight...")
    try:
        from src.utils.ai_enricher import AIEnricher
        from src.utils.performer_tracker import PerformerTracker
        
        enricher = AIEnricher()
        tracker = PerformerTracker()
        
        # Sort by date
        sorted_events = sorted(final_list, key=lambda x: x.get('date') or '9999-99-99')
        
        # Filter for future events starting from today
        today = datetime.now().strftime("%Y-%m-%d")
        upcoming = [e for e in sorted_events if e.get('date') and e['date'] >= today][:10]
        
        spotlight_count = 0
        for e in upcoming:
            if spotlight_count >= 3: break
            
            # Extract performers
            # SV has performers list, Indievox might have it in name
            performers = e.get('performers', [])
            if not performers:
                name = e.get('name') or e.get('activity_name', '')
                if '：' in name: performers = [name.split('：')[1].strip()]
                elif '｜' in name: performers = [name.split('｜')[0].strip()]
                elif ' w/ ' in name: performers = [p.strip() for p in name.split(' w/ ')]
                else: performers = [name]
            
            if performers:
                artist = performers[0]
                # Avoid generic titles
                if len(artist) > 20 or artist in ["BTC 蛻變密碼"]: continue
                
                # Check tracker (cache)
                profiles = tracker.get_profiles([artist])
                profile = profiles.get(artist.lower())
                
                if not profile or not profile.get('description'):
                    # Fetch from AI
                    logger.info(f"Fetching AI profile for: {artist}")
                    profile = enricher.get_performer_profile(artist)
                    if profile and profile.get('description'):
                        tracker.update_history([artist])
                        tracker.update_profile(artist, description=profile['description'], ig_handle=profile.get('ig_handle'))
                
                if profile and profile.get('description'):
                    e['spotlight'] = {
                        "performer": artist,
                        "description": profile['description'],
                        "ig_handle": profile.get('ig_handle')
                    }
                    spotlight_count += 1
                    logger.info(f"Added spotlight for {artist}")
                    
    except Exception as e:
        logger.warning(f"AI Spotlight enrichment failed: {e}")

    # Save Output
    output_path = "data/radar_events.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_list, f, indent=4, ensure_ascii=False)
        
    logger.info(f"Done. Saved {len(final_list)} radar events to {output_path}")

if __name__ == "__main__":
    main()
