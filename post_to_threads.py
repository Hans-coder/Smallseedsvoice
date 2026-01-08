"""
Post to Threads
Reads: data/official_events.json, data/radar_events.json
Posts: To Threads via API
"""
import json
import os
from pathlib import Path
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger

logger = setup_logger("post_to_threads")

def format_official_event(event: dict) -> str:
    """Format official event for Threads post."""
    text = f"""🎵 {event['activity_name']}

📅 {event['date']}
📍 {event['venue_name']}
🎫 {event['ticket_platform']}

購票連結: {event['ticket_url']}

#台灣音樂 #演唱會 #{event['ticket_platform']}"""
    return text

def format_radar_event(event: dict) -> str:
    """Format radar event for Threads post."""
    free_tag = "免費入場" if event.get('is_free') == 'true' else ""
    text = f"""🎸 {event['activity_name']}

📅 {event['date']}
📍 {event['venue']}
{free_tag}

詳情: {event['source']}

#台灣音樂 #LiveHouse #獨立音樂"""
    return text

def main():
    # Load credentials
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        logger.error("THREADS_ACCESS_TOKEN not found in environment")
        print("❌ 請設定 THREADS_ACCESS_TOKEN 環境變數")
        return
    
    # Initialize poster
    poster = ThreadsPoster(access_token)
    
    # Load events
    official_events = []
    radar_events = []
    
    if os.path.exists("data/official_events.json"):
        with open("data/official_events.json", 'r') as f:
            official_events = json.load(f)
    
    if os.path.exists("data/radar_events.json"):
        with open("data/radar_events.json", 'r') as f:
            radar_events = json.load(f)
    
    logger.info(f"Loaded {len(official_events)} official events and {len(radar_events)} radar events")
    
    # Ask user which events to post
    print(f"\n📊 總共有 {len(official_events)} 筆官方活動 和 {len(radar_events)} 筆雷達活動")
    print("\n請選擇要發布的活動類型:")
    print("1. 官方活動 (Official)")
    print("2. 雷達活動 (Radar)")
    print("3. 兩者都發 (Both)")
    
    choice = input("\n請輸入選項 (1/2/3): ").strip()
    
    events_to_post = []
    
    if choice == "1":
        # Post first 5 official events as demo
        events_to_post = [(e, 'official') for e in official_events[:5]]
    elif choice == "2":
        # Post first 5 radar events as demo
        events_to_post = [(e, 'radar') for e in radar_events[:5]]
    elif choice == "3":
        # Mix: 3 official + 2 radar
        events_to_post = [(e, 'official') for e in official_events[:3]]
        events_to_post += [(e, 'radar') for e in radar_events[:2]]
    else:
        print("❌ 無效選項")
        return
    
    print(f"\n準備發布 {len(events_to_post)} 筆活動...")
    confirm = input("確認發布? (y/n): ").strip().lower()
    
    if confirm != 'y':
        print("❌ 取消發布")
        return
    
    # Post events
    success_count = 0
    for i, (event, event_type) in enumerate(events_to_post, 1):
        print(f"\n[{i}/{len(events_to_post)}] 發布中: {event.get('activity_name', 'Unknown')}")
        
        # Format text
        if event_type == 'official':
            text = format_official_event(event)
        else:
            text = format_radar_event(event)
        
        # Get image URL
        image_url = event.get('image_url')
        
        # Post
        post_id = poster.create_post(text, image_url)
        
        if post_id:
            print(f"✅ 發布成功! Post ID: {post_id}")
            success_count += 1
        else:
            print(f"❌ 發布失敗")
    
    print(f"\n📊 發布完成: {success_count}/{len(events_to_post)} 成功")
    
    # Cleanup cache
    cleanup = input("\n是否清理圖片快取? (y/n): ").strip().lower()
    if cleanup == 'y':
        import shutil
        if os.path.exists("data/preview_cache"):
            shutil.rmtree("data/preview_cache")
            print("✅ 快取已清理")

if __name__ == "__main__":
    main()
