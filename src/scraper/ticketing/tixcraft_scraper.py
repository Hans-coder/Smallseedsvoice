"""tixCraft Scraper — 改良版：更精準的 selector + 音樂分類 URL"""
from typing import Dict, List, Optional
import re
import time
from datetime import datetime, timedelta
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger(__name__)

# 音樂活動關鍵字（含其中一個才保留）
MUSIC_KEYWORDS = [
    '演唱會', '音樂祭', '音樂節', '演出', 'live', '樂團', '樂手',
    '開演', '巡迴', 'concert', 'tour', '表演', '祭', 'festival',
    '電音', 'dj', 'hip-hop', 'hiphop', '嘻哈',
]

# 明確排除清單
IGNORE_KEYWORDS = [
    '音樂劇', '兒童', '親子', '芭蕾', '舞劇', '講座', '大師班',
    '讀劇', '相聲', '脫口秀', '合唱', '室內樂', '古典', '交響',
    '弦樂', '管樂', '國樂', '愛樂', '協奏曲', '獨奏', '音樂家',
    '音樂會',  # 「音樂會」通常指古典，但含 live/樂團 則保留
]


class TixCraftScraper(BaseScraper):
    """tixCraft Event Scraper — 改良版"""

    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape tixCraft events.
        預設抓取活動總覽頁（含音樂/演唱會），不再僅抓 /activity 大類。
        """
        if not url:
            url = "https://tixcraft.com/activity"

        logger.info(f"Fetching tixCraft events from {url}...")
        soup = self.fetch_with_selenium(url, wait_time=5)

        if not soup:
            return []

        events = []
        today_dt = datetime.now()
        today = today_dt.strftime("%Y-%m-%d")
        max_date = (today_dt + timedelta(days=180)).strftime("%Y-%m-%d")

        # ── Selector 策略（精準 > 泛用）────────────────────────────
        # tixCraft 列表頁結構（2024~2026 觀察）：
        #   <div class="col-md-3 col-sm-4 col-xs-6"> <- 格狀卡片
        #     <div class="activity-item">
        #       <a href="/activity/detail/XXXXX" class="text-bold">標題</a>
        #       <span class="date">日期</span>
        #       <span class="text-med-light">場地</span>
        # 先試精準 selector，失敗再用備用
        event_items = (
            soup.select('div.col-xs-6.col-sm-4.col-md-3')  # 格狀卡片
            or soup.select('li.activity-list-item')          # 列表模式
            or soup.select('.activity-item')                  # 通用
        )

        # 若以上全失敗，退回到有 .text-bold a 的父容器（舊備用邏輯）
        if not event_items:
            logger.warning("TixCraft: 無法找到活動卡片，使用備用 selector")
            event_items = [
                tag.find_parent('div')
                for tag in soup.select('.text-bold a')
                if tag.find_parent('div')
            ]
            # 去重
            seen_ids = set()
            deduped = []
            for item in event_items:
                item_id = id(item)
                if item_id not in seen_ids:
                    seen_ids.add(item_id)
                    deduped.append(item)
            event_items = deduped

        logger.info(f"TixCraft: 找到 {len(event_items)} 個候選卡片")

        for item in event_items:
            event_data = self.parse_event(item)
            if not event_data:
                continue

            # ── 日期過濾 ────────────────────────────────────────────
            if event_data.get('date'):
                if event_data['date'] < today or event_data['date'] > max_date:
                    continue

            # ── 關鍵字過濾 ─────────────────────────────────────────
            name_lower = str(event_data.get('name', '')).lower()

            is_strict_ignore = any(k in name_lower for k in IGNORE_KEYWORDS)
            has_music_kw = any(k in name_lower for k in MUSIC_KEYWORDS)

            # 排除非音樂（但若含 live / 樂團則保留）
            if is_strict_ignore and 'live' not in name_lower and '樂團' not in name_lower:
                continue

            # 若不含任何音樂關鍵字，略過
            if not has_music_kw and not is_strict_ignore:
                continue

            # ── 抓詳細頁（補場地/票價/演出者）──────────────────────
            if event_data.get('ticket_url'):
                detail = self._fetch_detail(event_data['ticket_url'])
                if detail:
                    event_data.update(detail)

            events.append(event_data)
            time.sleep(1.5)  # 禮貌延遲，避免被封

        logger.info(f"TixCraft: 過濾後保留 {len(events)} 場音樂活動")
        return events

    def _fetch_detail(self, url: str) -> Dict:
        """從詳細頁補充場地、票價、演出者、圖片"""
        try:
            soup = self.fetch_with_selenium(url, wait_time=2)
            if not soup:
                return {}

            detail = {"performers": [], "start_time": None, "venue_name": None}

            # 從 meta og:title / og:image 快速取得圖片
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                detail["image_url"] = og_img.get('content')

            # 從結構化資訊列取得欄位
            for label in ["售票時間", "票價", "演出時間", "演出地點", "場地"]:
                target_tag = soup.find(string=lambda t: t and label in t)
                if not target_tag:
                    continue
                parent = target_tag.find_parent('li') or target_tag.find_parent('tr')
                if not parent:
                    continue
                value = parent.get_text(" ", strip=True).replace(label, "").strip(" :：")
                if label == "售票時間":
                    detail["ticket_sale_date"] = value
                elif label == "票價":
                    detail["price"] = value
                elif label == "演出時間":
                    m = re.search(r'(\d{2}:\d{2})', value)
                    if m:
                        detail["start_time"] = m.group(1)
                elif label in ["演出地點", "場地"] and not detail["venue_name"]:
                    detail["venue_name"] = value.split('(')[0].strip()

            # 從介紹文字提取演出者
            intro_div = (
                soup.select_one('.activity-intro')
                or soup.find('div', class_='intro')
                or soup.select_one('.content-main')
            )
            if intro_div:
                desc_text = intro_div.get_text(separator='\n')
                m = re.search(
                    r'(?:演出團隊|演出者|卡司|Lineup|Cast|演出陣容|共演)[:：\s]+([^\n]+)',
                    desc_text, re.IGNORECASE
                )
                if m:
                    raw = m.group(1).replace('、', ',').replace('｜', ',').replace('|', ',')
                    detail["performers"] = [p.strip() for p in raw.split(',') if p.strip()]

            return detail
        except Exception as e:
            logger.warning(f"TixCraft detail fetch failed for {url}: {e}")
            return {}

    def parse_event(self, element) -> Optional[Dict]:
        try:
            # ── 連結 ────────────────────────────────────────────────
            link_tag = (
                element.select_one('.text-bold a')
                or element.select_one('a.activity-title')
                or element.select_one('a[href*="/activity/detail/"]')
                or element.find('a', href=True)
            )
            if not link_tag:
                return None

            event_url = link_tag.get('href', '')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://tixcraft.com{event_url}"

            name = link_tag.get_text(strip=True)
            if not name:
                return None

            # ── 日期 ─────────────────────────────────────────────────
            date_tag = element.select_one('.date') or element.select_one('.activity-date')
            raw_time = date_tag.get_text(strip=True) if date_tag else ""
            date_iso = parse_taiwan_date(raw_time)

            # ── 場地 ─────────────────────────────────────────────────
            venue_tag = (
                element.select_one('.text-med-light')
                or element.select_one('.activity-venue')
            )
            venue = venue_tag.get_text(strip=True) if venue_tag else "See Details"

            # ── 圖片 ─────────────────────────────────────────────────
            img_tag = element.find('img')
            image_url = img_tag.get('src') or img_tag.get('data-src', '') if img_tag else None
            if image_url and not image_url.startswith('http'):
                image_url = None

            activity_id = f"tixcraft_{name}_{date_iso}"

            return {
                "activity_id": activity_id,
                "name": name,
                "performers": [],
                "date": date_iso,
                "start_time": None,
                "venue_name": venue,
                "location": venue,
                "city": "Unknown",
                "price": None,
                "ticket_platform": "tixCraft",
                "ticket_url": event_url,
                "source_url": event_url,
                "image_url": image_url,
                "ticket_sale_date": None,
            }
        except Exception as e:
            logger.error(f"Error parsing tixCraft item: {e}")
            return None
