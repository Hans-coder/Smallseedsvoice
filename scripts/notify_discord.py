import os
import json
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.discord_notifier import DiscordNotifier
from src.utils.logger import setup_logger

logger = setup_logger("discord_notification")

def main():
    parser = argparse.ArgumentParser(description='Send notifications to Discord')
    parser.add_argument('--type', type=str, choices=['digest', 'radar', 'sale'], required=True)
    args = parser.parse_args()

    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.error("❌ DISCORD_WEBHOOK_URL environment variable not set. Cannot send notification.")
        sys.exit(1)

    notifier = DiscordNotifier(webhook_url)

    if args.type == 'digest':
        digest_file = Path("data/digest_posts.json")
        if not digest_file.exists():
            logger.warning(f"⚠️ {digest_file} not found. Skipping digest notification.")
            return
        
        with open(digest_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        
        if not posts:
            logger.info("ℹ️ No digest posts to send (empty list). Sending status to Discord.")
            notifier.send_message(content="ℹ️ **每週精選更新**\n本次搜尋沒有發現符合條件的免費活動資料。")
            return

        logger.info(f"📤 Found {len(posts)} digest posts. Sending to Discord...")
        for i, post in enumerate(posts, 1):
            logger.info(f"   - Sending post #{i}...")
            notifier.send_digest_post(i, post['text'], post['images'])
        logger.info("✅ Digest notifications sent.")

    elif args.type == 'radar':
        logger.info("📡 Checking for radar events...")
        radar_file = Path("data/radar_events.json")
        if not radar_file.exists():
            logger.warning(f"⚠️ {radar_file} not found. Skipping radar notification.")
            return
        
        with open(radar_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        if not events:
            logger.info("ℹ️ No radar events found. Sending status to Discord.")
            notifier.send_message(content="ℹ️ **樂團雷達站更新**\n本次搜尋沒有發現新的活動資料。")
            return
            
        summary = f"📡 **樂團雷達站更新**\n發現了 {len(events)} 場新的活動！請查看 GitHub Artifacts 中的 `preview.html` 進行手動發布。"
        if notifier.send_message(content=summary):
            logger.info("✅ Radar notification sent.")
        else:
            logger.error("❌ Failed to send radar notification.")

    elif args.type == 'sale':
        logger.info("🚨 Checking for sale events...")
        sale_file = Path("data/official_events.json")
        if not sale_file.exists():
             logger.warning(f"⚠️ {sale_file} not found. Skipping sale notification.")
             return
        
        with open(sale_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
            
        if not events:
            logger.info("ℹ️ No sale events found. Sending status to Discord.")
            notifier.send_message(content="ℹ️ **售票情報更新**\n本次搜尋沒有發現新的售票資訊。")
            return

        summary = f"🚨 **售票情報更新**\n發現了 {len(events)} 筆售票資訊！詳情請見預覽檔。"
        if notifier.send_message(content=summary):
            logger.info("✅ Sale notification sent.")
        else:
            logger.error("❌ Failed to send sale notification.")

if __name__ == "__main__":
    main()
