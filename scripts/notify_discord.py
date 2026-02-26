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
        logger.error("DISCORD_WEBHOOK_URL environment variable not set.")
        return

    notifier = DiscordNotifier(webhook_url)

    if args.type == 'digest':
        digest_file = Path("data/digest_posts.json")
        if not digest_file.exists():
            logger.error(f"{digest_file} not found.")
            return
        
        with open(digest_file, 'r', encoding='utf-8') as f:
            posts = json.load(f)
        
        if not posts:
            logger.info("No digest posts to send.")
            return

        for i, post in enumerate(posts, 1):
            logger.info(f"Sending digest post #{i} to Discord...")
            notifier.send_digest_post(i, post['text'], post['images'])

    elif args.type == 'radar':
        # For radar, we might need a custom formatting or just reuse the logic
        # Radar data is usually merged into radar_events.json but post_radar_to_threads.py 
        # generates the final text. We might need to adjust how radar text is captured.
        # For now, let's assume we want to send a summary.
        # Actually, let's simplify and have this script handle the formatting if needed, 
        # or read a pre-formatted file.
        # Given the current structure, let's just send a notification that radar events are ready
        # and include the preview link if possible, or just the raw data summary.
        logger.info("Radar notification - sending data summary...")
        radar_file = Path("data/radar_events.json")
        if not radar_file.exists():
            logger.error(f"{radar_file} not found.")
            return
        
        with open(radar_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
        
        if not events:
            logger.info("No radar events to notify.")
            return
            
        # Basic summary for radar
        summary = f"📡 **樂團雷達站更新**\n發現了 {len(events)} 場新的活動！請查看 GitHub Artifacts 中的 `preview.html` 進行手動發布。"
        notifier.send_message(content=summary)

    elif args.type == 'sale':
        # Similar to radar
        sale_file = Path("data/official_events.json")
        if not sale_file.exists():
             logger.error(f"{sale_file} not found.")
             return
        
        with open(sale_file, 'r', encoding='utf-8') as f:
            events = json.load(f)
            
        if not events:
            logger.info("No sale events to notify.")
            return

        summary = f"🚨 **售票情報更新**\n發現了 {len(events)} 筆售票資訊！詳情請見預覽檔。"
        notifier.send_message(content=summary)

if __name__ == "__main__":
    main()
