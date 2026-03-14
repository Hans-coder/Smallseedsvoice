"""
Post Radar Events to Threads
Reads: data/radar_events.json
Posts: Upcoming events summary
"""
import json
import os
import sys
import logging
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Add project root to path
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# Load environment variables
load_dotenv()

from src.utils.logger import setup_logger
from src.threads.threads_poster import ThreadsPoster
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger("radar_poster")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true', help='Auto posting mode')
    parser.add_argument('--dry-run', action='store_true', help='Dry run only')
    args = parser.parse_args()
    
    logger.info("Starting Radar Poster...")
    
    # 1. Load Data
    data_path = "data/radar_events.json"
    if not os.path.exists(data_path):
        logger.error(f"{data_path} not found.")
        return
        
    with open(data_path, 'r', encoding='utf-8') as f:
        events = json.load(f)
        
    if not events:
        logger.warning("No radar events found.")
        return

    # 2. Filter Logic
    # Radar is typically "What's cool recently?" or "Upcoming Live House gigs"
    # Workflow runs Tue, Thu, Sat.
    # Maybe pick 5 random upcoming events? Or upcoming 3-7 days?
    
    # Let's filter for events in next 7 days
    upcoming = []
    today = datetime.now().date()
    end_date = today + timedelta(days=14) # 2 weeks window
    
    for e in events:
        raw_date = e.get('date')
        if not raw_date: continue
        
        # Parse date
        try:
             # Indievox: YYYY-MM-DD
             # IG: YYYY-MM-DD or partial
             d_obj = datetime.strptime(str(raw_date), "%Y-%m-%d").date()
             
             if today <= d_obj <= end_date:
                 upcoming.append(e)
        except Exception:
            continue
            
    # Sort by date
    upcoming.sort(key=lambda x: x.get('date'))
    
    if not upcoming:
        logger.info("No upcoming radar events found in window.")
        return

    # Limit to top 5-7 to avoid huge posts
    selected = upcoming[:7]
    
    # 3. Format Post
    # Header
    today_str = today.strftime("%m/%d")
    lines = [f"📡 樂團雷達站 ({today_str})", "挖掘近期 Live House 現場與獨立音樂資訊！\n"]
    
    image_urls = []
    
    for i, e in enumerate(selected, 1):
        # Format:
        # 1. Band Name/Event
        # 🗓 Date @ Venue
        name = e['activity_name']
        date = e['date']
        venue = e['venue']
        
        lines.append(f"{i}. {name}")
        lines.append(f"   🗓 {date} @ {venue}")
        if e.get('source'):
             lines.append(f"   🔗 {e['source']}")
        lines.append("") # Empty line
        
        # Images
        if len(image_urls) < 10 and e.get('image_url'):
            if e['image_url'].startswith('http'):
                image_urls.append(e['image_url'])

    # Append AI Community Prompt
    try:
        from src.utils.ai_enricher import AIEnricher
        enricher = AIEnricher()
        if enricher.model:
            cta = enricher.generate_community_prompt(selected, post_type="radar")
            if cta:
                lines.append(f"\n{cta}")
    except Exception as e:
        logger.warning(f"Could not generate community prompt: {e}")

    lines.append("#獨立音樂 #LiveHouse #樂團")
    post_text = "\n".join(lines)
    
    if args.dry_run:
        print("--- Dry Run Output ---")
        print(post_text)
        print(f"Images: {len(image_urls)}")
        return

    # 4. Post
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        logger.error("No THREADS_ACCESS_TOKEN found.")
        return
        
    poster = ThreadsPoster(access_token)
    
    if image_urls:
         # Use Carousel if multiple
         if len(image_urls) > 1:
             post_id = poster.create_carousel_post(post_text, image_urls)
         else:
             post_id = poster.create_post(post_text, image_urls[0])
    else:
        post_id = poster.create_post(post_text)
        
    if post_id:
        logger.info(f"Radar posted successfully: {post_id}")
    else:
        logger.error("Failed to post radar.")

if __name__ == "__main__":
    main()
