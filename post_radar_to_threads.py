"""
Post Radar Events to Threads
Reads: data/radar_events.json
Posts: To Threads via API

Usage:
  python post_radar_to_threads.py          # Interactive mode
  python post_radar_to_threads.py --auto   # Auto mode (no confirmation)
"""
import json
import os
import sys
import time
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger
from src.utils.ai_enricher import AIEnricher
import argparse
from pathlib import Path

POST_HISTORY_FILE = "data/posted_history.json"

logger = setup_logger("post_radar")

def format_event(event: dict, enricher: AIEnricher = None) -> str:
    """Format radar event for Threads post."""
    venue = event.get('venue', '待確認')
    date = event.get('date', '待確認')
    
    # Use AI to enrich caption
    hook = ""
    if enricher:
        hook = enricher.enrich_post(
            event['activity_name'], 
            date, 
            venue, 
            "免費活動" if event.get('is_free') == 'true' else ""
        )

    # Build post text
    text = f"""{hook}{event['activity_name']}

📅 日期：{date}
📍 地點：{venue}"""
    
    # Add free admission note if applicable
    if event.get('is_free') == 'true':
        text += "\n✨ 免費入場"
    
    text += f"\n\n🔗 {event['source']}"
    
    return text

    return text

from typing import List

def format_digest(events: list, enricher: AIEnricher = None) -> List[str]:
    """Format radar events into digest posts."""
    blocks = []
    
    # Header
    header = "📡 獨立音樂雷達快訊\n\n"
    current_block = header
    
    for i, event in enumerate(events, 1):
        # Concise line
        note = f" ({event['note']})" if event.get('note') else ""
        line = f"{i}. {event['activity_name']}\n   📅 {event['date']} | 📍 {event.get('venue', '待確認')}\n   🔗 {event['source']}\n\n"
        
        if len(current_block) + len(line) > 450:
            blocks.append(current_block)
            current_block = line
        else:
            current_block += line
            
    if current_block:
        blocks.append(current_block)
        
    return blocks

def load_history():
    if os.path.exists(POST_HISTORY_FILE):
        try:
            with open(POST_HISTORY_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

    with open(POST_HISTORY_FILE, 'w') as f:
        json.dump(list(history), f)

def prune_history(history):
    """Remove expired events from history."""
    today = time.strftime("%Y-%m-%d")
    pruned_history = set()
    cleaned_count = 0
    
    for event_id in history:
        # ID: Name_Date_Venue
        # Try to find date in the middle?
        # Strategy: Search for YYYY-MM-DD regex or split by underscores and find valid date.
        # Simpler: Iterate parts.
        parts = event_id.split('_')
        keep = True
        for part in parts:
            if len(part) == 10 and part.count('-') == 2:
                if part < today:
                    keep = False
                break
        
        if keep:
            pruned_history.add(event_id)
        else:
            cleaned_count += 1
            
    if cleaned_count > 0:
        logger.info(f"🧹 Pruned {cleaned_count} expired events from history")
        save_history(pruned_history)
        return pruned_history
    return history

def main():
    parser = argparse.ArgumentParser(description='Post Radar Events to Threads')
    parser.add_argument('--auto', action='store_true', help='Auto mode (no confirmation)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no actual posting)')
    args = parser.parse_args()
    
    auto_mode = args.auto
    dry_run = args.dry_run

    if dry_run:
        logger.info("🔧 Dry Run Mode Enabled")
    
    # Load credentials
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token and not dry_run:
        logger.error("THREADS_ACCESS_TOKEN not found in environment")
        print("❌ 請設定 THREADS_ACCESS_TOKEN 環境變數")
        return
    
    # Initialize poster and enricher
    poster = ThreadsPoster(access_token) if not dry_run else None
    enricher = AIEnricher()
    
    # Load events
    if not os.path.exists("data/radar_events.json"):
        logger.error("data/radar_events.json not found")
        print("❌ 找不到 data/radar_events.json，請先執行 scrape_activity_radar.py")
        return
    
    with open("data/radar_events.json", 'r') as f:
        events = json.load(f)
    
    # Load history
    posted_history = load_history()
    
    # Prune expired history
    posted_history = prune_history(posted_history)
    
    logger.info(f"Loaded {len(events)} radar events")
    
    # Filter duplicates
    new_events = []
    for event in events:
        # Create a unique ID for the event
        event_id = f"{event['activity_name']}_{event['date']}_{event['venue']}"
        if event_id not in posted_history:
            new_events.append(event)
    
    print(f"🔍 Found {len(events)} events, {len(new_events)} are new.")
    
    if not new_events:
        print("✅ No new events to post.")
        return

    # Post new events (Digest)
    events_to_post = new_events
    
    print(f"\n📊 準備發布 {len(events_to_post)} 筆新雷達活動 (Digest Mode)")
    for i, event in enumerate(events_to_post, 1):
        print(f"  {i}. {event['activity_name']} ({event['date']})")
    
    if not auto_mode and not dry_run:
        confirm = input("\n確認發布? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消發布")
            return
    
    # Batch events into carousels (Max 10 per post)
    chunk_size = 10
    chunks = [events_to_post[i:i + chunk_size] for i in range(0, len(events_to_post), chunk_size)]
    
    success_count = 0
    # Radar events usually have source URL, but image might be tricky.
    # Scraper tries to fetch og:image. If missing, use default.
    DEFAULT_IMAGE = "https://images.unsplash.com/photo-1493225255756-d9584f8606e9?w=800&q=80" # Indie band image
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n📌 Posting Carousel {i}/{len(chunks)} ({len(chunk)} events)...")
        
        # 1. Prepare Text
        text_lines = ["📡 音樂快訊雷達\n"]
        image_urls = []
        
        for idx, event in enumerate(chunk, 1):
            # Text Line
            # Text Line
            # 1. Name (Date) | Venue (if known)
            clean_venue = event.get('venue', 'Unknown').replace('Unknown', '').replace('待確認', '').strip()
            
            line = f"{idx}. {event['activity_name']}\n   📅 {event['date']}"
            if clean_venue:
                line += f" | 📍 {clean_venue}"
                
            text_lines.append(line)
            
            # Image URL
            url = event.get('image_url')
            if not url or not url.startswith('http'):
                url = DEFAULT_IMAGE
            image_urls.append(url)

        text_lines.append("\n🔗 活動詳情與連結請見圖片說明或留言")
        post_text = "\n".join(text_lines)
        
        if dry_run:
            print(f"📝 [Dry Run] Content:\n{post_text}")
            print(f"🖼️ Images ({len(image_urls)}):")
            for url in image_urls:
                print(f"  - {url[:50]}...")
            success_count += len(chunk)
        else:
            post_id = poster.create_carousel_post(post_text, image_urls)
            if post_id:
                print(f"✅ Carousel {i} Posted: {post_id}")
                success_count += len(chunk)
                poster.random_sleep(60, 120)
            else:
                print(f"❌ Carousel {i} Failed")

    # Update history
    if success_count > 0:
        if not dry_run:
            for event in events_to_post:
                event_id = f"{event['activity_name']}_{event['date']}_{event['venue']}"
                posted_history.add(event_id)
            save_history(posted_history)
        print(f"✅ History updated with {len(events_to_post)} events.")

    # Update history
    if success_count > 0:
        if not dry_run:
            for event in events_to_post:
                event_id = f"{event['activity_name']}_{event['date']}_{event['venue']}"
                posted_history.add(event_id)
            save_history(posted_history)
        print(f"✅ History updated with {len(events_to_post)} events.")
    
    print("🎉 Done.")

if __name__ == "__main__":
    main()
