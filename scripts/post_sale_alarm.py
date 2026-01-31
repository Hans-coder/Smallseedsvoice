"""
Post On-Sale Alarm to Threads
Checks official_events.json for events going on sale TOMORROW.
"""
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import json
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
    today_taiwan = now_taiwan.date()
    tomorrow_taiwan = today_taiwan + timedelta(days=1)
    three_days_taiwan = today_taiwan + timedelta(days=3)
    
    tomorrow_str = tomorrow_taiwan.strftime("%Y-%m-%d")
    
    logger.info(f"Checking for sales between {tomorrow_str} and {three_days_taiwan}")

    urgent_events = []
    upcoming_events = []

    for event in events:
        sale_date_raw = event.get('ticket_sale_date')
        if not sale_date_raw:
            continue
            
        sale_date_iso = parse_sale_date_str(sale_date_raw)
        if not sale_date_iso:
            continue

        sale_date_obj = datetime.strptime(sale_date_iso, "%Y-%m-%d").date()
        
        if sale_date_obj == tomorrow_taiwan:
            urgent_events.append(event)
        elif tomorrow_taiwan < sale_date_obj <= three_days_taiwan:
            upcoming_events.append(event)

    if not urgent_events and not upcoming_events:
        logger.info("No events found going on sale in the next 3 days.")
        return

    logger.info(f"Found {len(urgent_events)} urgent and {len(upcoming_events)} upcoming events.")

    # Format Post
    # Logic: 
    # If Urgent exists: "🚨 明天開賣！" + list
    # If Upcoming exists: "📅 近期預告" + list
    
    lines = []
    image_urls = []
    DEFAULT_IMAGE = "https://images.unsplash.com/photo-1550973886-add4529b57e4?w=800&q=80"

    # Header
    total_count = len(urgent_events) + len(upcoming_events)
    header = f"⏰ 搶票鬧鐘：未來 3 天有 {total_count} 場活動開賣！\n"
    lines.append(header)

    if urgent_events:
        lines.append(f"🔥 **明天 ({tomorrow_str}) 開賣：**")
        for i, event in enumerate(urgent_events, 1):
            sale_time = event['ticket_sale_date'].split(' ')[-1] if ' ' in event['ticket_sale_date'] else "時間待定"
            line = f"{i}. {event['activity_name']}\n   ⏰ {sale_time} | 🔗 {event['ticket_url']}"
            lines.append(line)
            
            # Images (Prioritize urgent)
            url = event.get('image_url')
            if not url or not url.startswith('http'):
                url = DEFAULT_IMAGE
            if len(image_urls) < 10:
                image_urls.append(url)

    if upcoming_events:
        if urgent_events:
            lines.append("\n-------------------\n")
        lines.append(f"📅 **近期預告 (後天 ~ 3天後)：**")
        for i, event in enumerate(upcoming_events, 1):
            date_short = event['ticket_sale_date'].split(' ')[0]
            line = f"• {date_short}: {event['activity_name']}"
            lines.append(line)
            
            # Images (Only if space)
            if not urgent_events and len(image_urls) < 10:
                 url = event.get('image_url')
                 if url and url.startswith('http'):
                     image_urls.append(url)

    post_text = "\n".join(lines)
    post_text += "\n\n💪 設好鬧鐘，祝大家搶票順利！"

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
