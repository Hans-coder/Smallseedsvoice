"""
post_radar_manual.py
讀取 data/radar_manual.json（手動確認的活動清單），
格式化後發文到 Threads。

用法：
  python scripts/post_radar_manual.py --dry-run   # 預覽，不發文
  python scripts/post_radar_manual.py             # 正式發文（需 THREADS_ACCESS_TOKEN）
"""
import sys
import os
import json
import argparse
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logger import setup_logger

logger = setup_logger("post_radar_manual")

RADAR_MANUAL_PATH = Path("data/radar_manual.json")


def load_entries() -> list:
    if not RADAR_MANUAL_PATH.exists():
        logger.error(f"找不到 {RADAR_MANUAL_PATH}，請先填寫活動資料。")
        return []
    try:
        data = json.loads(RADAR_MANUAL_PATH.read_text(encoding="utf-8"))
        # 過濾掉範例記錄
        return [e for e in data if "_comment" not in e and e.get("name")]
    except Exception as ex:
        logger.error(f"讀取 {RADAR_MANUAL_PATH} 失敗：{ex}")
        return []


def format_threads_posts(entries: list) -> list:
    """
    將確認活動列表格式化為 Threads 貼文串。
    若活動太多，拆成多則貼文（每則最多 5 場）。
    """
    if not entries:
        return []

    BATCH_SIZE = 5
    posts = []

    for batch_start in range(0, len(entries), BATCH_SIZE):
        batch = entries[batch_start: batch_start + BATCH_SIZE]
        total_batches = (len(entries) + BATCH_SIZE - 1) // BATCH_SIZE
        batch_num = batch_start // BATCH_SIZE + 1

        lines = []

        # Header
        if total_batches > 1:
            lines.append(f"⏰ 雷達快訊 — 近期搶票提醒（{batch_num}/{total_batches}）")
        else:
            lines.append("⏰ 雷達快訊 — 近期搶票提醒")
        lines.append("")

        for e in batch:
            name = e.get("name", "未知活動")
            artist = e.get("artist", "")
            sale_date = e.get("sale_date", "")
            sale_time = e.get("sale_time", "")
            event_date = e.get("event_date", "")
            venue = e.get("venue", "")
            ticket_url = e.get("ticket_url", "")
            note = e.get("note", "")

            # 日期格式美化
            sale_str = _format_date_display(sale_date)
            if sale_time:
                sale_str += f" {sale_time}"
            event_str = _format_date_display(event_date) if event_date else ""

            lines.append(f"🎫 {name}")
            if artist:
                lines.append(f"🎤 {artist}")
            if event_str and venue:
                lines.append(f"📅 {event_str}　🏟 {venue}")
            elif event_str:
                lines.append(f"📅 演出：{event_str}")
            elif venue:
                lines.append(f"🏟 {venue}")
            lines.append(f"⏰ 開賣：{sale_str}")
            if note:
                lines.append(f"📝 {note}")
            if ticket_url:
                lines.append(f"🔗 {ticket_url}")
            lines.append("")

        lines.append("設好鬧鐘，祝大家搶票順利！🎉")

        # 收集圖片（每則貼文最多取第一張）
        images = []
        for e in batch:
            img = e.get("image_url", "")
            if img and img.startswith("http"):
                images.append(img)

        posts.append({
            "text": "\n".join(lines),
            "images": images[:10],
        })

    return posts


def _format_date_display(date_str: str) -> str:
    """將 YYYY-MM-DD 轉成 M/D（週X）的格式"""
    if not date_str:
        return date_str
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        return f"{dt.month}/{dt.day}（週{weekdays[dt.weekday()]}）"
    except ValueError:
        return date_str


def main():
    parser = argparse.ArgumentParser(description="雷達快訊手動發文")
    parser.add_argument("--dry-run", action="store_true", help="預覽發文內容，不實際送出")
    args = parser.parse_args()

    entries = load_entries()
    if not entries:
        logger.warning("沒有確認的活動，結束。")
        return

    logger.info(f"讀取到 {len(entries)} 筆確認活動")

    posts = format_threads_posts(entries)
    if not posts:
        logger.warning("沒有生成任何貼文。")
        return

    # 儲存貼文資料（供 Discord 通知腳本使用）
    Path("data").mkdir(exist_ok=True)
    with open("data/radar_posts.json", "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=4, ensure_ascii=False)
    logger.info("已儲存 data/radar_posts.json")

    if args.dry_run:
        print("\n" + "="*60)
        print(f"📝 [Dry Run] 共 {len(posts)} 則貼文：")
        print("="*60)
        for i, p in enumerate(posts, 1):
            print(f"\n--- 貼文 {i} ---")
            print(p["text"])
            if p.get("images"):
                print(f"🖼 圖片：{len(p['images'])} 張")
        print("="*60)
        return

    # 正式發文
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        logger.error("THREADS_ACCESS_TOKEN 未設定，無法發文。")
        sys.exit(1)

    from src.threads.threads_poster import ThreadsPoster
    poster = ThreadsPoster(access_token)

    created_ids = poster.post_thread(posts)

    if created_ids:
        logger.info(f"✅ 雷達快訊發文成功！IDs: {created_ids}")
    else:
        logger.error("❌ 發文失敗")
        sys.exit(1)


if __name__ == "__main__":
    main()
