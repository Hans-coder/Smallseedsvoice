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

def main():
    # Check for auto mode
    auto_mode = '--auto' in sys.argv
    
    # Load credentials
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        logger.error("THREADS_ACCESS_TOKEN not found in environment")
        print("❌ 請設定 THREADS_ACCESS_TOKEN 環境變數")
        return
    
    # Initialize poster and enricher
    poster = ThreadsPoster(access_token)
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
    
    logger.info(f"Loaded {len(events)} official events")
    
    # Post first 5 events as demo or all in auto mode
    events_to_post = events[:10] if not auto_mode else events
    
    print(f"\n📊 準備發布 {len(events_to_post)} 筆官方活動")
    for i, event in enumerate(events_to_post, 1):
        print(f"  {i}. {event['activity_name']} ({event['date']})")
    
    if not auto_mode:
        confirm = input("\n確認發布? (y/n): ").strip().lower()
        if confirm != 'y':
            print("❌ 取消發布")
            return
    else:
        print("\n🤖 自動模式：開始發布...")
    
    # Post events
    success_count = 0
    for i, event in enumerate(events_to_post, 1):
        print(f"\n[{i}/{len(events_to_post)}] 發布中: {event['activity_name']}")
        
        text = format_event(event, enricher)
        image_url = event.get('image_url')
        
        post_id = poster.create_post(text, image_url)
        
        if post_id:
            print(f"✅ 發布成功! Post ID: {post_id}")
            success_count += 1
            # Delay if not the last item
            if i < len(events_to_post):
                poster.random_sleep(60, 120)
        else:
            print(f"❌ 發布失敗")
    
    print(f"\n📊 發布完成: {success_count}/{len(events_to_post)} 成功")

if __name__ == "__main__":
    main()
