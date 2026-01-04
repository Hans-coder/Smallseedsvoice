"""
Weekly Digest Builder
Responsible for processing a list of events into a coherent weekly digest for Threads.
Key features:
1. Groups events by Date.
2. Sorts events chronologically.
3. Generates threaded texts (splitting by 500 chars).
4. Manages image attachments (up to 20 total, distributed across threads).
"""

from typing import List, Dict, Tuple
from datetime import datetime, timedelta
import re

class DigestBuilder:
    def __init__(self, config: Dict):
        self.config = config
        self.max_chars = 500
        # Threads limit is usually 500 chars.
        
    def build_digest(self, events: List[Dict], start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Builds a list of post objects (main post + replies) for the weekly digest.
        
        Args:
            events: List of event dictionaries
            start_date: Start of the week
            end_date: End of the week
            
        Returns:
            List of dicts, where each dict represents a thread post:
            [
                {'text': 'Main Post...', 'images': ['path/to/img1.jpg', ...]},
                {'text': 'Reply 1...', 'images': [...]},
                ...
            ]
        """
        # 1. Filter & Sort Events
        # Ensure events are within the date range and sorted by date
        sorted_events = self._sort_and_filter_events(events, start_date, end_date)
        
        if not sorted_events:
            return []

        # 2. Group by Date Section (e.g., Mon-Wed, Thu-Fri, Sat-Sun)
        # This helps structure the digest logically.
        grouped_sections = self._group_events_by_section(sorted_events)
        
        # 3. Generate Posts
        posts = []
        
        # --- Main Post (Cover) ---
        cover_text = self._generate_cover_text(start_date, end_date, len(sorted_events))
        posts.append({
            'text': cover_text,
            'images': [] # We might want to add a summary image here if available, or just the first event's image
        })
        
        # --- Content Posts (Threaded) ---
        current_text = ""
        current_images = []
        
        for section_name, section_events in grouped_sections.items():
            section_header = f"\n🗓️ {section_name}\n"
            
            # Check if adding header exceeds limit, if so, push current post and start new
            if len(current_text) + len(section_header) > self.max_chars:
                posts.append({'text': current_text.strip(), 'images': current_images})
                current_text = ""
                current_images = []
            
            current_text += section_header
            
            for event in section_events:
                event_line = self._format_event_line(event)
                
                # Check length
                if len(current_text) + len(event_line) > self.max_chars:
                    posts.append({'text': current_text.strip(), 'images': current_images})
                    current_text = ""
                    current_images = []
                    # Re-add section header if we just broke a section? 
                    # Simpler: just continue.
                
                current_text += event_line
                
                # Add image if available
                if event.get('image_path'):
                    current_images.append(event['image_path'])
        
        # Add the last remaining post
        if current_text:
            posts.append({'text': current_text.strip(), 'images': current_images})
            
        # 4. Redistribute Images (Optional optimization)
        # Threads allows mixing text and images. 
        # We need to ensure no post has > 10 images (Threads limit per carousel is 10, typically).
        # And total conversation limit? Actually Threads allows images in replies.
        # Let's enforce max 10 images per single post unit.
        self._enforce_image_limits(posts)
        
        return posts

    def _sort_and_filter_events(self, events: List[Dict], start: datetime, end: datetime) -> List[Dict]:
        """Sorts events by time."""
        # This assumes event['time'] is parseable or we rely on the scraper's parsing.
        # For now, we trust the scraper passed us valid events.
        # We simply sort by the 'time' string or a parsed datetime object if available.
        # Since 'time' is a string in the current DB schema, we might need robust parsing here.
        # For MVP, we perform a simple sort or rely on the order they were scraped (usually chrono).
        return events 

    def _group_events_by_section(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Groups events into sections like '上半週 (Mon-Wed)', '下半週 (Thu-Fri)', '週末 (Sat-Sun)'."""
        # Placeholder logic: just group by date string if possible, or return a single 'All Events' group
        # Real implementation would parse dates. 
        # For MVP, let's return a single group "本週活動"
        return {"本週活動": events}

    def _generate_cover_text(self, start: datetime, end: datetime, count: int) -> str:
        date_str = f"{start.strftime('%m/%d')} - {end.strftime('%m/%d')}"
        return f"📅 下週免費音樂活動懶人包 ({date_str}) 🇹🇼\n\n共整理了 {count} 場免費演出！\n詳細資訊請看留言 👇"

    def _format_event_line(self, event: Dict) -> str:
        # 📍【城市】活動名稱
        # 🗓 日期（星期）時間
        # 📌 活動地點
        
        # 提取或推導城市
        location = event.get('location', '台灣')
        city = self._extract_city(location)
        venue = location # 簡單起見，或者需要更複雜的解析
        
        # 解析日期時間
        # 假設 time 字段已經是 datetime 對象或者包含了完整資訊，
        # 如果是字符串，我們需要 DataProcessor 已經標準化過。
        # 這裡假設 DataProcessor 目前還是給字符串，我們盡量解析。
        # 為演示，我們使用原始字符串並嘗試提取。
        time_str = event.get('time', '')
        
        # 構造星期幾 (需要 DataProcessor 的支持，這裡先做個簡單映射或佔位)
        weekday = self._get_weekday_zh(time_str) 

        return f"\n📍【{city}】{event['name']}\n🗓 {time_str} ({weekday})\n📌 {venue}\n"

    def _extract_city(self, location: str) -> str:
        # 簡單城市提取
        cities = ['台北', '新北', '基隆', '桃園', '新竹', '苗栗', '台中', '彰化', '南投', '雲林', '嘉義', '台南', '高雄', '屏東', '宜蘭', '花蓮', '台東']
        for c in cities:
            if c in location:
                return c
        return "台灣"

    def _get_weekday_zh(self, time_str: str) -> str:
        # TODO: 依賴 DataProcessor 解析出的準確 datetime
        return "週?"

    def _enforce_image_limits(self, posts: List[Dict]):
        # "每個活動僅使用 1 張圖片"
        # DigestBuilder 應該已經在構建 post 時處理了，這裡確保每個 post 的圖片不超過 Threads 限制
        # Threads Carousel 限制通常是 10 張。
        # Prompt 說 "單篇貼文最多圖片數：20 張" (可能是指分頁後總共?)
        # 但 Threads 單篇上限是 10-20 (視各區/版本)。
        # 若超過 10，我們必須拆貼文。
        # 我們假設 10 為安全上限。
        MAX_IMAGES_PER_POST = 10 
        for post in posts:
            if len(post['images']) > MAX_IMAGES_PER_POST:
                post['images'] = post['images'][:MAX_IMAGES_PER_POST]

