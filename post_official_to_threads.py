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
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger

logger = setup_logger("post_official")

def format_event(event: dict) -> str:
    """Format official event for Threads post."""
    text = f"""🎵 {event['activity_name']}

📅 {event['date']}
📍 {event['venue_name']}
🎫 {event['ticket_platform']}

購票連結: {event['ticket_url']}

#台灣音樂 #演唱會 #{event['ticket_platform']}"""
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
    
    # Initialize poster
    poster = ThreadsPoster(access_token)
    
    # Load events
    if not os.path.exists("data/official_events.json"):
        logger.error("data/official_events.json not found")
        print("❌ 找不到 data/official_events.json，請先執行 scrape_official_platforms.py")
        return
    
    with open("data/official_events.json", 'r') as f:
        events = json.load(f)
    
    logger.info(f"Loaded {len(events)} official events")
    
    # Post first 5 events as demo
    events_to_post = events[:5]
    
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
        
        text = format_event(event)
        image_url = event.get('image_url')
        
        post_id = poster.create_post(text, image_url)
        
        if post_id:
            print(f"✅ 發布成功! Post ID: {post_id}")
            success_count += 1
        else:
            print(f"❌ 發布失敗")
    
    print(f"\n📊 發布完成: {success_count}/{len(events_to_post)} 成功")

if __name__ == "__main__":
    main()
