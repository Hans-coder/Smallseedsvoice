import os
import json
import argparse
import sys
import datetime
import re
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.discord_notifier import DiscordNotifier
from src.utils.logger import setup_logger

logger = setup_logger("discord_notification")

VERCEL_ADMIN_URL = "https://smallseedsvoice.vercel.app/admin.html#smallseeds2026"
VERCEL_WEB_URL = "https://smallseedsvoice.vercel.app"
GH_PAGES_ADMIN_URL = "https://hans-coder.github.io/Smallseedsvoice/admin.html#smallseeds2026"

def get_taipei_time():
    """獲取台北時間 (UTC+8)"""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    taipei_now = utc_now + datetime.timedelta(hours=8)
    return taipei_now.strftime('%Y-%m-%d %H:%M:%S')

def main():
    parser = argparse.ArgumentParser(description='Send notifications to Discord')
    parser.add_argument('--type', type=str, choices=['digest', 'radar', 'sale'], required=True)
    parser.add_argument('--name', type=str, default='全台音樂活動自動更新', help='排程名稱')
    parser.add_argument('--full', action='store_true', help='是否發送完整貼文全文 (預設為精簡通知模式)')
    args = parser.parse_args()

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("❌ DISCORD_WEBHOOK_URL environment variable not set. Cannot send notification.")
        sys.exit(1)

    notifier = DiscordNotifier(webhook_url)
    exec_time = get_taipei_time()

    # --- 1. Check for scraping errors ---
    error_msgs = []
    error_file = Path("data/scraping_errors.json")
    if error_file.exists():
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
            if errors:
                for e in errors:
                    error_msgs.append(f"• **[{e.get('scraper', '未知來源')}]** {e.get('message', '未知錯誤')}")
            error_file.unlink()
        except Exception as ex:
            logger.warning(f"Error reading scraping_errors.json: {ex}")

    # --- 2. Load Data for Digest Alert ---
    if args.type == 'digest':
        # Load web events
        events_file = Path("web/data/events.json")
        events_data = {}
        if events_file.exists():
            try:
                with open(events_file, 'r', encoding='utf-8') as f:
                    events_data = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {events_file}: {e}")

        total_events = events_data.get('total_events', len(events_data.get('events', [])))
        total_free = events_data.get('total_free', sum(1 for e in events_data.get('events', []) if e.get('is_free')))
        total_hot = events_data.get('total_hot', sum(1 for e in events_data.get('events', []) if e.get('is_hot')))
        top_venues = events_data.get('top_venues', [])
        venue_count = len(top_venues)

        # Load digest posts
        posts_file = Path("web/data/digest_posts.json")
        posts = []
        if posts_file.exists():
            try:
                with open(posts_file, 'r', encoding='utf-8') as f:
                    posts = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {posts_file}: {e}")

        date_window = ""
        if posts and isinstance(posts, list) and len(posts) > 0 and 'text' in posts[0]:
            first_line = posts[0]['text'].split('\n')[0]
            if '(' in first_line and ')' in first_line:
                start_idx = first_line.find('(')
                end_idx = first_line.rfind(')')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    date_window = first_line[start_idx+1:end_idx].strip()

        # Load spotlight posts
        spotlights_file = Path("web/data/spotlight_posts.json")
        spotlights = []
        if spotlights_file.exists():
            try:
                with open(spotlights_file, 'r', encoding='utf-8') as f:
                    spotlights = json.load(f)
            except Exception as e:
                logger.warning(f"Error loading {spotlights_file}: {e}")

        # Top venue preview
        top_venue_names = ", ".join([v.get('name', '') for v in top_venues[:4] if v.get('name')])

        embed = {
            "title": "🎧 【聽團小聲音】活動資料庫與發文後台已更新",
            "description": "全台最新 Livehouse 音樂演出與 Threads 策展文案已完成同步，隨時可前往後台挑選發布！",
            "color": 0xf59e0b if error_msgs else 0x10b981, # 綠色正常，橘色警示
            "fields": [
                {
                    "name": "📊 活動資料庫狀態",
                    "value": f"• 最新在線演出：`{total_events} 場` (含 {total_free} 場免費 / {total_hot} 場熱門)\n• 知名展演空間：`{venue_count} 個場館`" + (f" ({top_venue_names} 等)" if top_venue_names else ""),
                    "inline": False
                },
                {
                    "name": "📝 Threads 策展庫",
                    "value": f"• 每週精選週報：`{len(posts)} 則串文草稿`" + (f" ({date_window})" if date_window else "") + f"\n• 單場爆款候選：`{len(spotlights)} 場焦點演出`",
                    "inline": False
                },
                {
                    "name": "⚡ 快速操作入口",
                    "value": f"👉 [**開啟行動發文管理後台 (免密直達)**]({VERCEL_ADMIN_URL})\n🌐 [**查看前台活動地圖指南**]({VERCEL_WEB_URL})",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"排程：{args.name} | 台北時間 {exec_time}"
            }
        }

        if error_msgs:
            embed["fields"].append({
                "name": "⚠️ 爬蟲錯誤提醒",
                "value": "\n".join(error_msgs[:5]),
                "inline": False
            })

        success = notifier.send_message(embeds=[embed])
        if success:
            logger.info("✅ Discord clean alert notification sent successfully.")
        else:
            logger.error("❌ Failed to send Discord alert notification.")

    else:
        # Fallback or generic handling for other types (radar / sale)
        embed = {
            "title": f"🔔 【聽團小聲音】{args.name}更新通知",
            "color": 0x10b981,
            "description": f"已完成 `{args.type}` 排程資料更新！",
            "fields": [
                {
                    "name": "📱 管理後台",
                    "value": f"👉 [點此查看最新資料]({VERCEL_ADMIN_URL})",
                    "inline": False
                }
            ],
            "footer": {
                "text": f"排程：{args.name} | 台北時間 {exec_time}"
            }
        }
        notifier.send_message(embeds=[embed])
        logger.info(f"✅ Discord {args.type} alert sent.")

if __name__ == "__main__":
    main()
