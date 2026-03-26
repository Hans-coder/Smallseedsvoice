import os
import json
import argparse
import sys
import datetime
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.discord_notifier import DiscordNotifier
from src.utils.logger import setup_logger

logger = setup_logger("discord_notification")

def get_taipei_time():
    """獲取台北時間 (UTC+8)"""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    taipei_now = utc_now + datetime.timedelta(hours=8)
    return taipei_now.strftime('%Y-%m-%d %H:%M:%S')

def parse_iso_date(date_str):
    """Simple date string to weekday"""
    if not date_str or date_str == "Unknown": return ""
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ['一', '二', '三', '四', '五', '六', '日']
        return f" (週{weekdays[dt.weekday()]})"
    except: return ""

def format_raw_events_to_text(events, type_name):
    """將原始活動資料轉換為簡體易讀的文字列表"""
    if not events:
        return "本次無抓取到符合條件的活動。"
    
    # 提取有 Spotlight 的活動
    spotlights = [e.get('spotlight') for e in events if e.get('spotlight')]
    
    lines = [f"【{type_name} - 原始資料摘要】", ""]
    
    if spotlights:
        lines.append("✨ **演出者特別介紹** ✨")
        for s in spotlights:
            performer = s.get('performer')
            desc = s.get('description')
            ig = s.get('ig_handle')
            ig_str = f" (IG: @{ig})" if ig else ""
            lines.append(f"🎸 **{performer}**{ig_str}")
            lines.append(f"   💡 {desc}")
        lines.append("-" * 20)
        lines.append("")

    lines.append("📅 **活動列表**")
    for i, e in enumerate(events[:15], 1): # Limit to 15
        name = e.get('activity_name') or e.get('name') or "未知活動"
        date = e.get('date') or e.get('time') or "時間待定"
        venue = e.get('venue') or e.get('venue_name') or "地點待定"
        wd = parse_iso_date(e.get('date'))
        lines.append(f"{i}. {name}\n   🗓 {date}{wd} @ {venue}")
    
    if len(events) > 15:
        lines.append(f"\n...以及其他 {len(events)-15} 場活動。")
    
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description='Send notifications to Discord')
    parser.add_argument('--type', type=str, choices=['digest', 'radar', 'sale'], required=True)
    parser.add_argument('--name', type=str, default='未定義排程', help='排程名稱')
    args = parser.parse_args()

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("❌ DISCORD_WEBHOOK_URL environment variable not set. Cannot send notification.")
        sys.exit(1)

    notifier = DiscordNotifier(webhook_url)
    exec_time = get_taipei_time()
    header = f"🕒 **執行時間**: `{exec_time}` (台北)\n📋 **排程名稱**: `{args.name}`\n"

    # --- Check for scraping errors ---
    error_file = Path("data/scraping_errors.json")
    if error_file.exists():
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
            if errors:
                error_msgs = []
                for e in errors:
                    # Truncate traceback to avoid Discord 2000 char limit
                    tb = e.get('traceback', '')[-300:] 
                    error_msgs.append(f"**[{e.get('scraper')}]** {e.get('message')}\n```\n...{tb}\n```")
                
                header += "\n🚨 **系統爬蟲錯誤報告** 🚨\n" + "\n".join(error_msgs) + "\n"
            # Cleanup
            error_file.unlink()
        except: pass

    # --- Determine Files and Source ---
    posts = []
    source_type = "post" # "post" or "raw"
    
    if args.type == 'digest':
        post_file = Path("data/digest_posts.json")
        raw_file = Path("data/digest_raw.json")
        title_prefix = "每週精選摘要"
    elif args.type == 'radar':
        post_file = Path("data/radar_posts.json")
        raw_file = Path("data/radar_events.json")
        title_prefix = "樂團雷達站情報"
    else: # sale
        post_file = Path("data/sale_posts.json")
        raw_file = Path("data/official_events.json")
        title_prefix = "售票情報鬧鐘"

    # 優先使用處理後的貼文資料
    if post_file.exists():
        try:
            with open(post_file, 'r', encoding='utf-8') as f:
                posts = json.load(f)
            if posts:
                source_type = "post"
        except Exception as e:
            logger.error(f"Error reading {post_file}: {e}")

    # 若無貼文資料，則使用原始資料回退
    if not posts and raw_file.exists():
        try:
            with open(raw_file, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
            if raw_data:
                # 特別處理 Sale，只顯示未來 3 天開賣的
                if args.type == 'sale':
                    from datetime import timedelta
                    today = datetime.datetime.now() + datetime.timedelta(hours=8)
                    upcoming = []
                    for e in raw_data:
                        try:
                            sale_date = e.get('ticket_sale_date', '').split(' ')[0].replace('/', '-')
                            if sale_date:
                                sd = datetime.datetime.strptime(sale_date, "%Y-%m-%d")
                                if today <= sd <= today + timedelta(days=3):
                                    upcoming.append(e)
                        except: continue
                    raw_data = upcoming

                summary_text = format_raw_events_to_text(raw_data, title_prefix)
                # 取得前幾張圖片作為預覽 (最多 5 張)
                images = []
                for e in raw_data:
                    url = e.get('image_url')
                    if url and url.startswith('http') and url not in images:
                        images.append(url)
                    if len(images) >= 5:
                        break
                
                posts = [{"text": summary_text, "images": images}]
                source_type = "raw"
        except Exception as e:
            logger.error(f"Error reading {raw_file}: {e}")

    # --- Sending Stage ---
    if not posts:
        logger.info(f"ℹ️ No data for {args.type}. Sending empty status.")
        notifier.send_message(content=header + f"ℹ️ **更新報告**: 本次搜尋沒有發現新的活動資料。")
        return

    # Send Header first
    status_label = "Threads 貼文草稿" if source_type == "post" else "原始資料摘要"
    notifier.send_message(content=header + f"📦 **更新報告**: 準備了 {len(posts)} 則{status_label}。")

    # Send Posts
    for i, post in enumerate(posts, 1):
        # 統一使用 send_standard_post
        display_title = f"{title_prefix} - No.{i}" if len(posts) > 1 else title_prefix
        notifier.send_standard_post(
            title=display_title,
            text=post.get('text', ''),
            images=post.get('images', [])
        )
        logger.info(f"✅ {args.type} notification {i} sent.")

    logger.info(f"✅ {args.type} notifications complete.")

if __name__ == "__main__":
    main()
