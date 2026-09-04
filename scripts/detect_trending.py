"""
detect_trending.py
偵測目前台灣音樂圈最受關注的演唱會 / 即將開賣的活動。
來源：
  1. KKTIX 最新音樂活動（含即將開賣）
  2. KKTIX 關鍵字搜尋（watchlist，含子域名活動如 xxx.kktix.cc）
  3. StreetVoice 近期活動（從快取或現場抓）
  4. Instagram 指定帳號最新貼文（演唱會/開賣相關）

輸出：data/trending_concerts.json + Discord 通知（簡潔清單，供人工查核）

用法：
  python scripts/detect_trending.py
  python scripts/detect_trending.py --dry-run   (只印出，不送 Discord)
"""
import sys
import os
import json
import re
import argparse
import datetime
import random
import time
from pathlib import Path
from typing import List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.logger import setup_logger

logger = setup_logger("detect_trending")

# ─────────────────────────────────────────────────────────────
# 設定
# ─────────────────────────────────────────────────────────────

# IG 帳號清單：用於掃描近期有無演唱會/開賣貼文
IG_ACCOUNTS_TO_SCAN = [
    "emerge_fest",     # 浮現祭
    "megaportfest",    # 大港開唱
    "kktix",           # KKTIX 官方
    "indievox",        # iNDIEVOX
]

# IG 貼文過濾關鍵字（含其中一個才保留）
IG_CONCERT_KEYWORDS = [
    "演唱會", "開賣", "售票", "搶票", "巡迴", "livehouse", "live house",
    "音樂祭", "festival", "公演", "加場", "presale", "pre-sale",
    "concert", "tour", "開票", "早鳥", "一般票",
]

# ─────────────────────────────────────────────────────────────
# 1. KKTIX 新活動抓取
# ─────────────────────────────────────────────────────────────

def scrape_kktix_new() -> List[Dict]:
    """
    抓取 KKTIX 音樂分類頁最新活動。
    使用既有的 KktixScraper（Playwright + stealth）繞過 bot 防護。
    """
    try:
        from src.scraper.ticketing.kktix_scraper import KktixScraper
        scraper = KktixScraper({})
        events = scraper.scrape_events()
        logger.info(f"KKTIX: 抓到 {len(events)} 筆活動")

        results = []
        seen = set()
        for e in events:
            name = e.get("name") or e.get("activity_name", "")
            if not name or name in seen:
                continue
            seen.add(name)

            # 取得票務連結
            ticket_url = e.get("ticket_url") or e.get("source_url", "")
            if ticket_url and not ticket_url.startswith("http"):
                ticket_url = "https://kktix.com" + ticket_url

            # 顯示日期（演出日 or 開賣日）
            date_display = e.get("date") or e.get("ticket_sale_date", "")

            results.append({
                "name": name,
                "source": "KKTIX",
                "date_display": date_display,
                "ticket_url": ticket_url,
                "image_url": e.get("image_url", ""),
            })

        return results[:20]

    except Exception as ex:
        logger.warning(f"KKTIX 抓取失敗: {ex}")
        return []


# ─────────────────────────────────────────────────────────────
# 1b. KKTIX 關鍵字 Watchlist 搜尋（補抓子域名活動）
# ─────────────────────────────────────────────────────────────

def scrape_kktix_watchlist() -> List[Dict]:
    """
    用 config.yaml 中的 radar.watch_keywords 對 KKTIX 搜尋 API 批次查詢。
    這樣可以找到掛在主辦方子域名（如 binliveco.kktix.cc）的活動。
    每個關鍵字只抓第一頁（輕量），並做去重。
    """
    import urllib.parse
    import yaml
    from pathlib import Path

    # 讀取關鍵字清單
    config_path = Path("config.yaml")
    watch_keywords = []
    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            watch_keywords = cfg.get("radar", {}).get("watch_keywords", [])
        except Exception as ex:
            logger.warning(f"讀取 config.yaml watch_keywords 失敗: {ex}")

    if not watch_keywords:
        logger.info("watchlist 為空，跳過關鍵字搜尋")
        return []

    logger.info(f"KKTIX Watchlist: 搜尋 {len(watch_keywords)} 個關鍵字...")

    try:
        from src.scraper.ticketing.kktix_scraper import KktixScraper
        from datetime import timedelta

        scraper = KktixScraper({})
        today_dt = datetime.datetime.now()
        today_str = today_dt.strftime("%Y/%m/%d")
        max_date_str = (today_dt + timedelta(days=180)).strftime("%Y/%m/%d")
        start_at = urllib.parse.quote(today_str)
        end_at = urllib.parse.quote(max_date_str)

        all_found = []
        seen_names = set()

        for kw in watch_keywords:
            _random_sleep(1, 3)  # 關鍵字間延遲，避免被封
            kw_encoded = urllib.parse.quote(kw)
            search_url = (
                f"https://kktix.com/events?utf8=%E2%9C%93&search={kw_encoded}"
                f"&start_at={start_at}&end_at={end_at}"
            )
            try:
                events = scraper.scrape_events(url=search_url)
                for e in events:
                    name = e.get("name") or e.get("activity_name", "")
                    if not name or name in seen_names:
                        continue
                    seen_names.add(name)

                    ticket_url = e.get("ticket_url") or ""
                    date_display = e.get("date") or e.get("ticket_sale_date", "")

                    all_found.append({
                        "name": name,
                        "source": f"KKTIX Watchlist [{kw}]",
                        "date_display": date_display,
                        "ticket_url": ticket_url,
                        "image_url": e.get("image_url", ""),
                        "matched_keyword": kw,
                    })
                if events:
                    logger.info(f"  [{kw}] 找到 {len(events)} 筆")
            except Exception as ex:
                logger.warning(f"  [{kw}] 搜尋失敗: {ex}")

        logger.info(f"KKTIX Watchlist 完成：共 {len(all_found)} 筆新活動")
        return all_found

    except Exception as ex:
        logger.warning(f"KKTIX Watchlist 整體失敗: {ex}")
        return []


# ─────────────────────────────────────────────────────────────
# 2. StreetVoice 近期活動
# ─────────────────────────────────────────────────────────────

def scrape_streetvoice_upcoming() -> List[Dict]:
    """
    讀取 data/streetvoice_raw.json 快取，或現場抓取。
    擴大時間窗到 14 天（讓更多近期活動出現在候選清單）。
    """
    sv_cache = Path("data/streetvoice_raw.json")

    # 嘗試讀取今日快取（檔案在 6 小時內就算新鮮）
    if sv_cache.exists():
        age_hours = (time.time() - sv_cache.stat().st_mtime) / 3600
        if age_hours < 6:
            try:
                with open(sv_cache, "r", encoding="utf-8") as f:
                    events = json.load(f)
                logger.info(f"StreetVoice: 讀取快取 {len(events)} 筆（{age_hours:.1f}h 前）")
                return _normalize_sv(events)
            except Exception as ex:
                logger.warning(f"讀取快取失敗: {ex}")

    # 現場抓（放寬到 14 天）
    _random_sleep(2, 5)
    try:
        from src.scraper.discovery.streetvoice_scraper import StreetVoiceScraper

        # 暫時 monkey-patch 時間窗
        import src.scraper.discovery.streetvoice_scraper as sv_mod
        original_scrape = StreetVoiceScraper.scrape_events

        def scrape_wider(self, url="https://streetvoice.com/gigs/all/0/", with_details=False):
            """抓取更寬的時間窗（14天）"""
            from src.scraper.base_scraper import BaseScraper
            from datetime import datetime, timedelta
            import re

            soup = self.fetch_with_selenium(url, wait_time=5)
            if not soup:
                return []

            all_events = []
            date_blocks = soup.select('.date-block.item_box')
            today = datetime.now().strftime("%Y-%m-%d")
            max_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")

            for block in date_blocks:
                month_tag = block.select_one('.bg-red')
                day_tag = block.select_one('h1')
                current_date_str = None

                if month_tag and day_tag:
                    m_match = re.search(r'(\d+)', month_tag.get_text(strip=True))
                    d_match = re.search(r'(\d+)', day_tag.get_text(strip=True))
                    if m_match and d_match:
                        current_date_str = f"{datetime.now().year}-{m_match.group(1).zfill(2)}-{d_match.group(1).zfill(2)}"

                for item in block.select('li.list-group-item'):
                    event_data = self.parse_event(item, current_date_str)
                    if event_data and event_data.get('date'):
                        if today <= event_data['date'] <= max_date:
                            all_events.append(event_data)

            return all_events

        scraper = StreetVoiceScraper({})
        events = scrape_wider(scraper)
        logger.info(f"StreetVoice: 現場抓取 {len(events)} 筆（14天窗）")

        # 更新快取
        with open(sv_cache, "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)

        return _normalize_sv(events)

    except Exception as ex:
        logger.error(f"StreetVoice 抓取失敗: {ex}")
        return []


def _normalize_sv(events: list) -> List[Dict]:
    return [
        {
            "name": e.get("name", ""),
            "source": "StreetVoice",
            "date_display": e.get("date", ""),
            "ticket_url": e.get("ticket_url") or e.get("source_url", ""),
            "image_url": e.get("image_url", ""),
            "venue": e.get("venue_name", ""),
            "performers": e.get("performers", []),
        }
        for e in events if e.get("name")
    ]


# ─────────────────────────────────────────────────────────────
# 3. Instagram 掃描
# ─────────────────────────────────────────────────────────────

def scrape_ig_trending() -> List[Dict]:
    """
    用 instaloader 掃描指定 IG 帳號，
    找出最新（7天內）含演唱會關鍵字的貼文。
    """
    try:
        import instaloader
    except ImportError:
        logger.warning("instaloader 未安裝，跳過 IG 掃描")
        return []

    results = []
    loader = instaloader.Instaloader(
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        max_connection_attempts=1,
        request_timeout=15.0,
        quiet=True,
    )

    cutoff = datetime.datetime.now() - datetime.timedelta(days=7)

    for username in IG_ACCOUNTS_TO_SCAN:
        _random_sleep(3, 8)  # 帳號間大幅隨機延遲
        try:
            logger.info(f"掃描 IG @{username}...")
            profile = instaloader.Profile.from_username(loader.context, username)

            post_count = 0
            for post in profile.get_posts():
                if post_count >= 10:
                    break
                if post.date_local < cutoff:
                    break  # 超過 7 天就停止（貼文是倒序）

                caption = post.caption or ""
                caption_lower = caption.lower()

                # 過濾：必須包含至少一個演唱會關鍵字
                if not any(k in caption_lower for k in IG_CONCERT_KEYWORDS):
                    post_count += 1
                    continue

                # 提取標題（第一行非空白行）
                title = _extract_ig_title(caption, username)
                ig_url = f"https://www.instagram.com/p/{post.shortcode}/"

                results.append({
                    "name": title,
                    "source": f"IG @{username}",
                    "date_display": post.date_local.strftime("%Y-%m-%d"),
                    "ticket_url": ig_url,
                    "image_url": getattr(post, "display_url", ""),
                    "caption_preview": caption[:120].replace("\n", " "),
                })

                post_count += 1
                _random_sleep(2, 5)  # 貼文間延遲

        except Exception as ex:
            err = str(ex)
            if "429" in err or "Too Many Requests" in err:
                logger.warning(f"IG @{username}: 被限速 (429)，停止掃描")
                break
            elif "401" in err or "LoginRequired" in err:
                logger.warning(f"IG @{username}: 需要登入，跳過")
            else:
                logger.warning(f"IG @{username}: 抓取失敗 — {err[:100]}")

    logger.info(f"IG 掃描完成：找到 {len(results)} 則相關貼文")
    return results


def _extract_ig_title(caption: str, username: str) -> str:
    """從 IG 貼文取出最像標題的第一行"""
    for line in caption.split("\n"):
        line = line.strip()
        if line and len(line) > 4 and len(line) < 80:
            # 跳過純 emoji 行或 hashtag 行
            if not re.match(r'^[#@\s\U0001F300-\U0001FFFF]+$', line):
                return line
    return caption[:50].strip() or f"@{username} 貼文"


# ─────────────────────────────────────────────────────────────
# 工具函式
# ─────────────────────────────────────────────────────────────

_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

def _random_user_agent() -> str:
    return random.choice(_USER_AGENTS)

def _random_sleep(min_sec: float, max_sec: float):
    delay = random.uniform(min_sec, max_sec)
    logger.debug(f"  隨機延遲 {delay:.1f}s...")
    time.sleep(delay)


# ─────────────────────────────────────────────────────────────
# Discord 通知（精簡版，只告知活動名稱讓人工查核）
# ─────────────────────────────────────────────────────────────

def build_discord_message(kktix: List[Dict], watchlist: List[Dict], sv: List[Dict], ig: List[Dict]) -> str:
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"## 🔍 雷達快訊候選清單",
        f"**偵測時間**：{now_str}（台灣時間）",
        f"以下為今日偵測到的活動，**請自行至官方平台確認正確售票資訊後發文**。",
        "",
    ]

    if kktix:
        lines.append(f"### 🎫 KKTIX 最新音樂活動（{len(kktix)} 筆）")
        for i, e in enumerate(kktix[:12], 1):
            date_str = f"  `{e['date_display']}`" if e.get("date_display") else ""
            lines.append(f"{i}. **{e['name']}**{date_str}")
            lines.append(f"   {e['ticket_url']}")
        lines.append("")

    if watchlist:
        lines.append(f"### 🎯 熱門活動 Watchlist（{len(watchlist)} 筆，含子域名）")
        for i, e in enumerate(watchlist[:15], 1):
            date_str = f"  `{e['date_display']}`" if e.get("date_display") else ""
            kw_str = f"  🔑_{e.get('matched_keyword', '')}_" if e.get("matched_keyword") else ""
            lines.append(f"{i}. **{e['name']}**{date_str}{kw_str}")
            lines.append(f"   {e['ticket_url']}")
        lines.append("")

    if sv:
        lines.append(f"### 🎸 StreetVoice 近期演出（{len(sv)} 筆）")
        for i, e in enumerate(sv[:10], 1):
            date_str = f"  `{e['date_display']}`" if e.get("date_display") else ""
            venue_str = f"  @ {e['venue']}" if e.get("venue") else ""
            performers = "、".join(e.get("performers", [])[:3])
            performers_str = f"  🎤 {performers}" if performers else ""
            lines.append(f"{i}. **{e['name']}**{date_str}{venue_str}{performers_str}")
            lines.append(f"   {e['ticket_url']}")
        lines.append("")

    if ig:
        lines.append(f"### 📸 Instagram 相關貼文（{len(ig)} 則）")
        for i, e in enumerate(ig[:8], 1):
            lines.append(f"{i}. **{e['name']}**  _{e.get('source', '')}_")
            if e.get("caption_preview"):
                lines.append(f"   💬 {e['caption_preview'][:80]}...")
            lines.append(f"   {e['ticket_url']}")
        lines.append("")

    if not kktix and not watchlist and not sv and not ig:
        lines.append("⚠️ 本次未偵測到新活動。")

    lines.append("---")
    lines.append("👆 確認後請開本地表單：`python3 scripts/radar_form_server.py`")

    return "\n".join(lines)


def send_discord(message: str, webhook_url: str) -> bool:
    from src.utils.discord_notifier import DiscordNotifier
    notifier = DiscordNotifier(webhook_url)

    # 分段送（避免超過 2000 字元限制）
    chunks, current, current_len = [], [], 0
    for line in message.split("\n"):
        if current_len + len(line) + 1 > 1900:
            chunks.append("\n".join(current))
            current, current_len = [line], len(line)
        else:
            current.append(line)
            current_len += len(line) + 1
    if current:
        chunks.append("\n".join(current))

    ok = True
    for chunk in chunks:
        if not notifier.send_message(content=chunk):
            ok = False
    return ok


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="偵測熱門演唱會候選清單")
    parser.add_argument("--dry-run", action="store_true", help="只印出結果，不送 Discord")
    parser.add_argument("--skip-ig", action="store_true", help="跳過 IG 掃描（較慢，有時被擋）")
    args = parser.parse_args()

    Path("data").mkdir(exist_ok=True)

    logger.info("=== 開始偵測熱門活動 ===")

    # 各平台抓取
    kktix_events = scrape_kktix_new()
    _random_sleep(2, 4)

    # Watchlist 搜尋（補抓子域名活動）
    watchlist_events = scrape_kktix_watchlist()
    _random_sleep(2, 4)

    sv_events = scrape_streetvoice_upcoming()
    _random_sleep(2, 4)

    ig_events = []
    if not args.skip_ig:
        ig_events = scrape_ig_trending()

    # 儲存結果（原始分類格式）
    result = {
        "generated_at": datetime.datetime.now().isoformat(),
        "kktix_new": kktix_events,
        "kktix_watchlist": watchlist_events,
        "streetvoice_upcoming": sv_events,
        "ig_posts": ig_events,
    }
    output_path = Path("data/trending_concerts.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4, ensure_ascii=False)
    logger.info(f"已儲存 {output_path}（KKTIX:{len(kktix_events)} Watchlist:{len(watchlist_events)} SV:{len(sv_events)} IG:{len(ig_events)}）")

    # ── 同時輸出扁平化的 radar_events.json 供圖卡生成使用 ──────
    flat_events = []
    # KKTIX 優先（有圖片的放前面）
    for e in kktix_events:
        flat_events.append({
            "name": e.get("name", ""),
            "date": e.get("date_display", ""),
            "venue": "",
            "image_url": e.get("image_url", ""),
            "ticket_url": e.get("ticket_url", ""),
            "source": "KKTIX",
        })
    for e in sv_events:
        flat_events.append({
            "name": e.get("name", ""),
            "date": e.get("date_display", ""),
            "venue": e.get("venue", ""),
            "image_url": e.get("image_url", ""),
            "ticket_url": e.get("ticket_url", ""),
            "source": "StreetVoice",
        })
    # 有圖片的排前面，最多取 12 筆
    flat_events.sort(key=lambda x: (0 if x.get("image_url") else 1))
    flat_events = flat_events[:12]
    radar_path = Path("data/radar_events.json")
    with open(radar_path, "w", encoding="utf-8") as f:
        json.dump(flat_events, f, indent=4, ensure_ascii=False)
    logger.info(f"已輸出圖卡用資料 {radar_path}（{len(flat_events)} 筆）")

    # 組合通知
    message = build_discord_message(kktix_events, watchlist_events, sv_events, ig_events)

    if args.dry_run:
        print("\n" + "=" * 60)
        print(message)
        print("=" * 60)
        logger.info("Dry run 完成。")
        return

    # Discord 通知改由 notify_discord.py 統一處理（含圖卡附件）
    # 這裡只在有 DISCORD_WEBHOOK_URL 且沒有渲染圖卡時才發純文字版
    import glob
    has_rendered_cards = bool(glob.glob("artifacts/card_*.jpg"))
    if not has_rendered_cards:
        webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            logger.error("DISCORD_WEBHOOK_URL 未設定，無法送通知。")
            print(message)
            return
        ok = send_discord(message, webhook_url)
        logger.info("✅ Discord 通知已送出（純文字版）" if ok else "❌ Discord 通知失敗")
    else:
        logger.info("📸 偵測到已渲染圖卡，跳過純文字通知（由 notify_discord.py 發送）")


if __name__ == "__main__":
    main()
