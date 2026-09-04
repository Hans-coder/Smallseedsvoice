"""Accupass Scraper — 音樂活動（含付費）"""
from typing import Dict, List, Optional
import re
import time
from datetime import datetime, timedelta
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.text_cleaners import refine_image_url, clean_event_title

logger = setup_logger(__name__)

# 音樂祭 / 演唱會相關關鍵字（含其中一個才保留）
MUSIC_KEYWORDS = [
    '演唱會', '音樂祭', '音樂節', '演出', 'live', '樂團', '樂手',
    '開演', '巡迴', 'concert', 'tour', '音樂', '表演', '祭', 'festival',
]

# 明確要排除的非音樂類別
IGNORE_KEYWORDS = [
    '音樂劇', '兒童', '親子', '芭蕾', '舞劇', '講座', '大師班',
    '讀劇', '相聲', '脫口秀', '合唱團', '室內樂', '古典', '交響',
    '弦樂', '管樂', '國樂', '愛樂', '協奏曲',
]


class AccupassScraper(BaseScraper):
    """Accupass 音樂活動 Scraper"""

    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape Accupass music events.
        預設抓取音樂分類（含付費）。
        """
        if not url:
            url = "https://www.accupass.com/search?c=music"

        logger.info(f"Fetching Accupass events from {url} using Selenium...")
        # Accupass 使用無限捲動，scroll=True 確保載入更多活動
        soup = self.fetch_with_selenium(url, scroll=True, scroll_count=10)

        if not soup:
            return []

        events = []
        today_dt = datetime.now()
        today = today_dt.strftime("%Y-%m-%d")
        max_date = (today_dt + timedelta(days=180)).strftime("%Y-%m-%d")

        # Accupass 搜尋結果卡片 selector（CSS module class name 有動態 hash，用 contains 匹配）
        event_items = (
            soup.select('div[class*="EventCard_home-event-card"]')
            or soup.select('div[class*="EventCard_event-card"]')
            or soup.select('div[class*="event-card"]')
        )

        logger.info(f"Accupass: 找到 {len(event_items)} 個候選卡片")

        for item in event_items:
            event_data = self.parse_event(item)
            if not event_data:
                continue

            # ── 日期過濾 ───────────────────────────────────────────
            date_val = event_data.get('date')
            if date_val:
                if date_val < today or date_val > max_date:
                    continue
            # 無日期的活動略過（資料不完整）
            else:
                continue

            # ── 關鍵字過濾 ─────────────────────────────────────────
            name_lower = str(event_data.get('name', '')).lower()

            is_strict_ignore = any(k in name_lower for k in IGNORE_KEYWORDS)
            has_music_kw = any(k in name_lower for k in MUSIC_KEYWORDS)

            # 排除非音樂類（但若含 live / 樂團則保留）
            if is_strict_ignore and 'live' not in name_lower and '樂團' not in name_lower:
                continue

            # 若不含任何音樂關鍵字，也略過（減少誤抓）
            if not has_music_kw and not is_strict_ignore:
                # 放寬：只要有「演出」相關詞就留下
                if not any(k in name_lower for k in ['演', '樂', 'music', 'sound']):
                    continue

            events.append(event_data)
            time.sleep(0.3)

        logger.info(f"Accupass: 過濾後保留 {len(events)} 場音樂活動")
        return events

    def parse_event(self, element) -> Optional[Dict]:
        """Parse Accupass event card element"""
        try:
            # ── 連結 ────────────────────────────────────────────
            link_tag = element.find('a', href=True)
            if not link_tag:
                return None

            event_url = link_tag.get('href', '')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://www.accupass.com{event_url}"

            # ── 標題 ────────────────────────────────────────────
            title_tag = (
                element.find('p', class_=lambda x: x and 'event-name' in x.lower())
                or element.find('p', class_=lambda x: x and 'event-title' in x.lower())
                or element.find('h2')
                or element.find('h3')
            )
            raw_name = title_tag.get_text(strip=True) if title_tag else ""
            if not raw_name:
                return None
            name = clean_event_title(raw_name)

            # ── 時間（解析為 date ISO 格式）──────────────────────
            time_tag = element.find('p', class_=lambda x: x and 'event-time' in x.lower())
            time_str = time_tag.get_text(strip=True) if time_tag else ""

            date_iso = self._parse_date(time_str)
            start_time = self._parse_time(time_str)

            # ── 地點 ────────────────────────────────────────────
            location_tag = (
                element.find(class_=lambda x: x and 'event-location' in x.lower())
                or element.find(class_=lambda x: x and 'event-location-type' in x.lower())
            )
            location = "場地詳見官網"
            venue_name = "場地詳見官網"
            if location_tag:
                spans = location_tag.find_all('span')
                if spans:
                    parts = [s.get_text(strip=True) for s in spans if s.get_text(strip=True)]
                    location = " ".join(parts)
                    # Accupass 通常：第一個 span = 城市, 第二個 = 場地名
                    venue_name = parts[-1] if parts else location
                else:
                    location = location_tag.get_text(strip=True)
                    venue_name = location

            # ── 圖片 ────────────────────────────────────────────
            img_tag = (
                element.find('img', class_=lambda x: x and 'event-photo-img' in x.lower())
                or element.find('img')
            )
            image_url = None
            if img_tag:
                raw_url = img_tag.get('src') or img_tag.get('data-src', '')
                if raw_url and '?' in raw_url:
                    raw_url = raw_url.split('?')[0]
                image_url = refine_image_url(raw_url) if raw_url else None

            activity_id = f"accupass_{name}_{date_iso}"

            return {
                'activity_id': activity_id,
                'name': name,
                'performers': [],
                'date': date_iso,
                'start_time': start_time,
                'time': time_str,
                'venue_name': venue_name,
                'location': location,
                'city': 'Unknown',
                'price': None,
                'ticket_platform': 'Accupass',
                'ticket_url': event_url,
                'source_url': event_url,
                'image_url': image_url,
                'ticket_sale_date': None,
            }
        except Exception as e:
            logger.error(f"Error parsing Accupass item: {e}")
            return None

    def _parse_date(self, time_str: str) -> Optional[str]:
        """從 Accupass 時間字串解析出 YYYY-MM-DD"""
        if not time_str:
            return None
        try:
            from src.utils.date_parser import parse_taiwan_date
            result = parse_taiwan_date(time_str)
            if result:
                return result
        except Exception:
            pass

        # Fallback: 正則搜尋
        # 常見格式：「2026/09/05」「2026.09.05」「Sep 05, 2026」「09/05」
        patterns = [
            r'(\d{4})[/.\-](\d{1,2})[/.\-](\d{1,2})',   # 2026/09/05
            r'(\d{1,2})[/.](\d{1,2})\s*\(.*?\)',            # 09/05 (六)
        ]
        for pat in patterns:
            m = re.search(pat, time_str)
            if m:
                groups = m.groups()
                if len(groups) == 3:
                    try:
                        return f"{int(groups[0]):04d}-{int(groups[1]):02d}-{int(groups[2]):02d}"
                    except Exception:
                        pass
                elif len(groups) == 2:
                    year = datetime.now().year
                    try:
                        return f"{year}-{int(groups[0]):02d}-{int(groups[1]):02d}"
                    except Exception:
                        pass
        return None

    def _parse_time(self, time_str: str) -> Optional[str]:
        """從時間字串提取 HH:MM"""
        if not time_str:
            return None
        m = re.search(r'(\d{1,2}):(\d{2})', time_str)
        if m:
            return f"{int(m.group(1)):02d}:{m.group(2)}"
        return None
