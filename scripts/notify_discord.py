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

    # --- NEW: Check for scraping errors ---
    error_file = Path("data/scraping_errors.json")
    if error_file.exists():
        try:
            with open(error_file, 'r', encoding='utf-8') as f:
                errors = json.load(f)
            if errors:
                error_msgs = []
                for e in errors:
                    # Truncate traceback to avoid Discord 2000 char limit
                    tb = e.get('traceback', '')[-500:] 
                    error_msgs.append(f"**[{e.get('scraper')}]** {e.get('error_type')}: {e.get('message')}\n```python\n...{tb}\n```")
                
                header += "\n🚨 **系統錯誤警告** 🚨\n爬蟲在執行過程中遭遇以下錯誤：\n" + "\n".join(error_msgs) + "\n\n"
            # Cleanup so we don't alert again
            error_file.unlink()
        except Exception as e:
            logger.error(f"Failed to read or parse scraping errors: {e}")
            

    if args.type == 'digest':
        digest_file = Path("data/digest_posts.json")
        if not digest_file.exists():
            logger.warning(f"⚠️ {digest_file} not found. Skipping digest notification.")
            return
        
        with open(digest_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        
        if not posts:
            raw_event_count = 0
            raw_file = Path("data/digest_raw.json")
            if raw_file.exists():
                try:
                    with open(raw_file, 'r', encoding='utf-8') as f:
                        raw_event_count = len(json.load(f))
                except: pass
            
            logger.info(f"ℹ️ No digest posts (raw events: {raw_event_count}). Sending status to Discord.")
            msg = header + "ℹ️ **每週精選更新**\n本次搜尋沒有發現符合條件的免費活動資料。"
            if raw_event_count > 0:
                msg += f"\n(系統共抓取到 {raw_event_count} 場活動，但皆不符合免費/熱門過濾條件)"
            notifier.send_message(content=msg)
            return

        logger.info(f"📤 Found {len(posts)} digest posts. Sending to Discord...")
        # Only send the header once or with each post? 
        # Better send a summary header first, then the posts.
        notifier.send_message(content=header + f"📤 **每週精選更新**: 發現了 {len(posts)} 則貼文內容。")
        for i, post in enumerate(posts, 1):
            logger.info(f"   - Sending post #{i}...")
            notifier.send_digest_post(i, post['text'], post['images'])
        logger.info("✅ Digest notifications sent.")

    elif args.type == 'radar':
        logger.info("📡 Checking for radar events...")
        radar_file = Path("data/radar_posts.json")
        if not radar_file.exists():
            logger.warning(f"⚠️ {radar_file} not found. Skipping radar notification.")
            return
        
        with open(radar_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        
        if not posts:
            logger.info("ℹ️ No radar posts found. Sending status to Discord.")
            notifier.send_message(content=header + "ℹ️ **樂團雷達站更新**\n本次搜尋沒有發現新的活動資料。")
            return
            
        notifier.send_message(content=header + f"📡 **樂團雷達站更新**: 準備了 {len(posts)} 則貼文。")
        
        for i, post in enumerate(posts, 1):
            # Send as Post + Image
            notifier.send_radar_post(post['text'], post['images'])
            logger.info(f"✅ Radar post #{i} sent.")
        
        logger.info("✅ Radar notifications done.")

    elif args.type == 'sale':
        logger.info("🚨 Checking for sale events...")
        sale_file = Path("data/sale_posts.json")
        if not sale_file.exists():
             logger.warning(f"⚠️ {sale_file} not found. Skipping sale notification.")
             return
        
        with open(sale_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
            
        if not posts:
            logger.info("ℹ️ No sale posts found. Sending status to Discord.")
            notifier.send_message(content=header + "ℹ️ **售票情報更新**\n本次搜尋沒有發現新的售票資訊。")
            return

        notifier.send_message(content=header + f"🚨 **售票情報更新**: 準備了 {len(posts)} 則貼文。")

        for i, post in enumerate(posts, 1):
            # Send as Post + Image
            content = f"**[售票情報內文預覽]**\n```\n{post['text']}\n```"
            embeds = []
            if post.get('images'):
                 for img_url in post['images'][:10]:
                     embeds.append({"image": {"url": img_url}})
            notifier.send_message(content=content, embeds=embeds)
            logger.info(f"✅ Sale post #{i} sent.")

        logger.info("✅ Sale notifications done.")

if __name__ == "__main__":
    main()
