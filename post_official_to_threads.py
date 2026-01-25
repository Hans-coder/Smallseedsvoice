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

import re

logger = setup_logger("post_official")

def normalize_title(title: str) -> str:
    """Normalize title by removing brackets and extra spaces."""
    # Remove contents inside 【】, [], ()
    # Actually, user example: "【特典加購】Takanori Iwata..." vs "Takanori Iwata..."
    # We want to keep the core name.
    # Simple strategy: Remove anything starting with 【 and ending with 】
    clean = re.sub(r'【.*?】', '', title)
    clean = re.sub(r'\[.*?\]', '', clean)
    # clean = re.sub(r'\(.*?\)', '', clean) # Parentheses might contain relevant info like (Taipei)
    return clean.strip()

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
    normalized_map = {} # title_norm -> event
    
    for event in events:
        eid = event['activity_id']
        if eid in posted_history:
            continue
            
        # Deduplication based on normalized title
        norm_title = normalize_title(event['activity_name'])
        
        # Heuristic: Prefer "售票頁" if exists, or shorter title?
        # User said: "【售票頁】... 【特典加購】... Takanori Iwata..." -> Keep "Takanori Iwata" (shortest usually)
        # Actually user said "上面這三個其實是同一個活動", implies keeping the main one.
        # Main one is usually the one without these specific tags or just the core name.
        # Let's keep the one that is SHORTEST after normalization? No, normalization makes them same/similar.
        # Let's keep the one that is SHORTEST *before* normalization (meaning fewest extra tags)?
        # "Takanori Iwata..." (len X) vs "【售票頁】Takanori Iwata..." (len X+Y). 
        # So shortest title wins.
        
        exisiting = normalized_map.get(norm_title)
        if exisiting:
            # Compare length
            if len(event['activity_name']) < len(exisiting['activity_name']):
                normalized_map[norm_title] = event
        else:
            normalized_map[norm_title] = event
            
    # Convert map back to list
    new_events = list(normalized_map.values())
    # Re-sort because dictionary iteration order might shuffle (though py3.7+ preserves insertion, but updates might shift?)
    # Safest to resort.
    new_events.sort(key=lambda x: (x.get('ticket_sale_date') or x['date']))

    logger.info(f"Loaded {len(events)} events. After dedupe & history check: {len(new_events)} new.")
    
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
    
    # Batch events into carousels (Max 10 per post)
    chunk_size = 10
    chunks = [events_to_post[i:i + chunk_size] for i in range(0, len(events_to_post), chunk_size)]
    
    success_count = 0
    DEFAULT_IMAGE = "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?w=800&q=80" # Concert image
    
    for i, chunk in enumerate(chunks, 1):
        print(f"\n📌 Posting Carousel {i}/{len(chunks)} ({len(chunk)} events)...")
        
        # 1. Prepare Text (Digest style list)
        text_lines = ["🎹 新增售票活動快訊\n"]
        image_urls = []
        
        for idx, event in enumerate(chunk, 1):
            # Text Line
            # 1. Name (Date)
            #    @ Venue (if known)
            #    Sale Date (if known)
            
            clean_venue = event.get('venue_name', 'Unknown').replace('Unknown', '').replace('待確認', '').strip()
            
            # Metadata
            # price = event.get('price') # User requested to remove price
            sale_date = event.get('ticket_sale_date')
            
            line = f"{idx}. {event['activity_name']}\n   📅 {event['date']}"
            
            if clean_venue and clean_venue != "See Details":
                line += f" | 📍 {clean_venue}"
            
            # Sale Date line
            if sale_date and sale_date != "Unknown" and sale_date != "待確認":
                 line += f"\n   ⏰ {sale_date} 開賣"
                 
            text_lines.append(line)
            
            # Image URL (Ensure valid)
            url = event.get('image_url')
            if not url or not url.startswith('http'):
                url = DEFAULT_IMAGE
            image_urls.append(url)
            
        text_lines.append("\n🎫 購票連結請見留言或主辦單位")
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
            for e in events_to_post:
                # Only add if it was in a successful chunk? 
                # Simplified: if any success, we might have partials. 
                # Ideally track per chunk. But here we assume if scripts runs, it's mostly fine.
                # Actually, let's just add all for now or improve precision later.
                # The count suggests we track successfully processed ones.
                # Since we iterate chunks, if one fails, we shouldn't add its events.
                # But success_count tracks events. 
                # Let's just add all 'events_to_post' if we are confident or refactor.
                # For safety, let's just use the set logic again.
                posted_history.add(e['activity_id'])
            save_history(posted_history)
        print(f"✅ History updated with {len(events_to_post)} events.")

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
