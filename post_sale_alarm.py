"""
Post On-Sale Alarm to Threads
Checks official_events.json for events going on sale TOMORROW.
"""
import json
import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger("post_sale_alarm")

def parse_sale_date_str(date_str: str) -> str:
    """
    Parse generic sale date string to YYYY-MM-DD.
    Examples: "2026/02/01 12:00", "2026-02-01", "2026/02/01"
    Returns YYYY-MM-DD or None
    """
    if not date_str or date_str in ["Unknown", "待確認"]:
        return None
    
    # Try using existing parser first (handles Twan chars if any)
    # But clean time part first
    clean = date_str.split(' ')[0] # Split "2026/02/01 12:00" -> "2026/02/01"
    return parse_taiwan_date(clean)

def main():
    parser = argparse.ArgumentParser(description='Post Sale Alarm')
    parser.add_argument('--auto', action='store_true', help='Auto mode')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    args = parser.parse_args()
    
    auto_mode = args.auto
    dry_run = args.dry_run

    if dry_run:
        logger.info("🔧 Dry Run Mode")

    # Access Token check
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token and not dry_run:
        logger.error("THREADS_ACCESS_TOKEN not found")
        return

    poster = ThreadsPoster(access_token) if not dry_run else None

    # Load events
    if not os.path.exists("data/official_events.json"):
        logger.warning("data/official_events.json not found")
        return

    with open("data/official_events.json", 'r') as f:
        events = json.load(f)

    # Calculate Tomorrow
    # In production (GitHub actions), ensure timezone is correct (Taiwan UTC+8)
    # Python datetime.now() depends on system. Github ubuntu is UTC.
    # We should offset to Taiwan time.
    from datetime import timezone
    tz_taiwan = timezone(timedelta(hours=8))
    now_taiwan = datetime.now(tz_taiwan)
    tomorrow_taiwan = now_taiwan + timedelta(days=1)
    tomorrow_str = tomorrow_taiwan.strftime("%Y-%m-%d")
    
    logger.info(f"Checking for sales on: {tomorrow_str} (Taiwan Time)")

    alarm_events = []
    for event in events:
        sale_date_raw = event.get('ticket_sale_date')
        if not sale_date_raw:
            continue
            
        sale_date_iso = parse_sale_date_str(sale_date_raw)
        if sale_date_iso == tomorrow_str:
            alarm_events.append(event)

    if not alarm_events:
        logger.info("No events found going on sale tomorrow.")
        return

    logger.info(f"Found {len(alarm_events)} events for alarm.")

    # Format Post
    # Limit to top 5-10 to avoid huge lists? Alarm is specific.
    # User said: "⏰ 搶票預告：明天有 X 場活動開賣！"
    
    header = f"⏰ 搶票鬧鐘：明天 ({tomorrow_str}) 有 {len(alarm_events)} 場活動開賣！\n\n"
    
    lines = []
    image_urls = []
    DEFAULT_IMAGE = "https://images.unsplash.com/photo-1550973886-add4529b57e4?w=800&q=80" # Alarm clock / ticket vibe

    for i, event in enumerate(alarm_events, 1):
        # Format: 1. Name (Time)
        sale_time = event['ticket_sale_date'].split(' ')[-1] if ' ' in event['ticket_sale_date'] else "時間待定"
        line = f"{i}. {event['activity_name']}\n   ⏰ 開賣時間：{sale_time}\n   🔗 {event['ticket_url']}"
        lines.append(line)
        
        url = event.get('image_url')
        if not url or not url.startswith('http'):
            url = DEFAULT_IMAGE
        image_urls.append(url)
    
    # If too many, maybe just list text?
    # Or use carousel if supported (up to 10).
    # If > 10, maybe just list top 10.
    if len(lines) > 10:
        lines = lines[:10]
        image_urls = image_urls[:10]
        lines.append(f"\n...還有更多，請查看售票平台！")

    post_text = header + "\n\n".join(lines)
    post_text += "\n\n💪 祝大家搶票順利！Tag 你的搶票戰友！"

    if dry_run:
        print(f"📝 [Dry Run] Alarm Post:\n{post_text}")
        print(f"🖼️ Images: {len(image_urls)}")
    else:
        # Use Carousel if multiple images, else single post?
        # ThreadsPoster supports carousel.
        if len(image_urls) > 1:
            post_id = poster.create_carousel_post(post_text, image_urls)
        else:
            post_id = poster.create_post(post_text, image_urls[0]) if image_urls else poster.create_post(post_text)
            
        if post_id:
            logger.info(f"✅ Alarm Posted: {post_id}")
        else:
            logger.error("❌ Alarm Post Failed")

if __name__ == "__main__":
    main()
