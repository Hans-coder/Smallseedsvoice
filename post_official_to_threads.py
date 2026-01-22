"""
Post Official Events to Threads
Reads: data/official_events.json
Posts: To Threads via API

Usage:
  python post_official_to_threads.py          # Interactive mode
  python post_official_to_threads.py --auto   # Auto mode (no confirmation)
"""
import json
import os
import sys
import time
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger
from src.utils.ai_enricher import AIEnricher

logger = setup_logger("post_official")

def format_event(event: dict, enricher: AIEnricher = None) -> str:
    """Format official event for Threads post."""
    venue = event.get('venue_name', '待確認')
    if venue == 'Unknown':
        venue = '待確認'
    
    # Use AI to enrich caption
    hook = ""
    if enricher:
        hook = enricher.enrich_post(
            event['activity_name'], 
            event['date'], 
            venue, 
            f"售票平台：{event['ticket_platform']}"
        )

    text = f"""{hook}{event['activity_name']}

📅 日期：{event['date']}
📍 地點：{venue}
🎫 售票：{event['ticket_platform']}
🔗 {event['ticket_url']}"""
    return text

from typing import List

def format_digest(events: list, enricher: AIEnricher = None) -> List[str]:
    """Format events into digest posts (chunks to fit char limit)."""
    blocks = []
    
    # Header
    header = "🎹 新增售票活動快訊\n\n"
    current_block = header
    
    for i, event in enumerate(events, 1):
        # Concise line: "1. Name (Date) @ Venue"
        line = f"{i}. {event['activity_name']}\n   📅 {event['date']} | 📍 {event.get('venue_name', '待確認')}\n   🎫 {event['ticket_platform']}\n\n"
        
        if len(current_block) + len(line) > 450:
            blocks.append(current_block)
            current_block = line
        else:
            current_block += line
            
    if current_block:
        blocks.append(current_block)
        
    return blocks

MAX_HISTORY = 1000
POST_HISTORY_FILE = "data/posted_history.json"

def load_history():
    if os.path.exists(POST_HISTORY_FILE):
        try:
            with open(POST_HISTORY_FILE, 'r') as f:
                return set(json.load(f))
        except:
            return set()
    return set()

def save_history(history):
    # Keep size manageable
    h_list = list(history)
    if len(h_list) > MAX_HISTORY:
        h_list = h_list[-MAX_HISTORY:]
    
    with open(POST_HISTORY_FILE, 'w') as f:
        json.dump(h_list, f)

def prune_history(history):
    """Remove expired events from history."""
    today = time.strftime("%Y-%m-%d")
    pruned_history = set()
    cleaned_count = 0
    
    for event_id in history:
        # ID format check. Official: kktix_Name_DateIso
        # We need to extract DateIso. 
        # Usually format: platform_name_date. 
        # But name might contain underscores.
        # Safer: look for YYYY-MM-DD pattern at the end.
        try:
           # Assume date is the last part if split by underscore? 
           # Scraper: f"kktix_{name}_{date_iso}"
           parts = event_id.rsplit('_', 1)
           if len(parts) > 1:
               date_part = parts[-1]
               # Simple validation: length 10 and 2 dashes
               if len(date_part) == 10 and date_part.count('-') == 2:
                   if date_part >= today:
                       pruned_history.add(event_id)
                   else:
                       cleaned_count += 1
                   continue
        except:
            pass
        
        # Fallback: keep if parsing fails to stay safe
        pruned_history.add(event_id)
            
    if cleaned_count > 0:
        logger.info(f"🧹 Pruned {cleaned_count} expired events from history")
        save_history(pruned_history)
        return pruned_history
    return history

import argparse

def main():
    parser = argparse.ArgumentParser(description='Post Official Events')
    parser.add_argument('--auto', action='store_true', help='Auto mode')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    auto_mode = args.auto
    dry_run = args.dry_run

    if dry_run:
        logger.info("🔧 Dry Run Mode")
    
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
    if not os.path.exists("data/official_events.json"):
        logger.error("data/official_events.json not found")
        print("❌ 找不到 data/official_events.json，請先執行 scrape_official_platforms.py")
        return
    
    with open("data/official_events.json", 'r') as f:
        events = json.load(f)
    
    # Sort by date (and eventually ticket_sale_date if implemented)
    events.sort(key=lambda x: (x.get('ticket_sale_date') or x['date']))
    
    # Load history
    posted_history = load_history()
    
    # Prune expired history
    posted_history = prune_history(posted_history)
    
    # Filter duplicates and immediate posting (no date check)
    new_events = []
    for event in events:
        # ID: from scraper (e.g. kktix_Name_Date)
        eid = event['activity_id']
        if eid not in posted_history:
            new_events.append(event)
            
    logger.info(f"Loaded {len(events)} events, {len(new_events)} are new.")
    
    if not new_events:
        print("✅ No new official events.")
        return
        
    events_to_post = new_events # Post all new events in digest
    
    print(f"\n📊 準備發布 {len(events_to_post)} 筆新官方活動 (Digest Mode)")
    for i, event in enumerate(events_to_post, 1):
        print(f"  {i}. {event['activity_name']} @ {event.get('venue_name')}")
    
    if not auto_mode and not dry_run:
        confirm = input("\n確認發布? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消發布")
            return
    
    # Generate Digest Blocks
    blocks = format_digest(events_to_post, enricher)
    
    success_count = 0
    for i, block in enumerate(blocks, 1):
        print(f"\n📌 Posting Block {i}/{len(blocks)}...")
        
        if dry_run:
            print(f"📝 [Dry Run] Content:\n{block}")
            success_count += 1
        else:
            post_id = poster.create_post(block) # Image not supported in digest text mode easily unless cover image?
            if post_id:
                print(f"✅ Block {i} Posted: {post_id}")
                success_count += 1
                poster.random_sleep(30, 60)
            else:
                print(f"❌ Block {i} Failed")

    # Update history only if successful (or mostly)
    if success_count > 0:
        if not dry_run:
            for e in events_to_post:
                posted_history.add(e['activity_id'])
            save_history(posted_history)
        print(f"✅ History updated with {len(events_to_post)} events.")
        
    print("🎉 Done.")

if __name__ == "__main__":
    main()
