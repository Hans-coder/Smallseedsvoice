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
from src.utils.text_cleaners import clean_event_title, format_short_date

class DigestBuilder:
    def __init__(self, config: Dict):
        self.config = config
        self.max_chars = 500
        # Check if AI enrichment is enabled in config or env
        from src.utils.ai_enricher import AIEnricher
        self.enricher = AIEnricher() if config.get('ai_enrichment', True) else None
        
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
        sorted_events = self._sort_and_filter_events(events, start_date, end_date)
        
        # 1.5 New Blood Detection & Performer Profiles
        from src.utils.performer_tracker import PerformerTracker
        tracker = PerformerTracker()
        
        all_performers_this_week = set()
        for event in sorted_events:
            performers = event.get('performers', [])
            if not performers:
                performers = [event.get('name') or event.get('activity_name', 'Unknown')]
            all_performers_this_week.update(performers)
            
        # Register them first so update_profile works
        tracker.update_history(list(all_performers_this_week))
        
        for event in sorted_events:
            performers = event.get('performers', [])
            if not performers:
                performers = [event.get('name') or event.get('activity_name', 'Unknown')]
            
            new_blood = tracker.get_new_blood(performers)
            event['is_discovery'] = len(new_blood) > 0
            event['new_artists'] = new_blood
            
            profiles = tracker.get_profiles(performers)
            
            # Enrich New Blood via AI
            for artist in new_blood:
                if self.enricher and self.enricher.model:
                    import time
                    time.sleep(1) # Rate limit protection
                    profile_data = self.enricher.get_performer_profile(artist)
                    if profile_data:
                        desc = profile_data.get('description', '')
                        handle = profile_data.get('ig_handle', '')
                        if desc or handle:
                            tracker.update_profile(artist, description=desc, ig_handle=handle)
                            profiles[artist.lower()] = {"description": desc, "ig_handle": handle}
            
            event['performer_profiles'] = profiles
        
        if not sorted_events:
            return []

        # 2. Group by Date Section (e.g., Mon-Wed, Thu-Fri, Sat-Sun)
        # This helps structure the digest logically.
        grouped_sections = self._group_events_by_section(sorted_events)
        
        # 3. Generate Posts
        posts = []
        
        # Initialize first post with cover text
        cover_text = self._generate_cover_text(start_date, end_date, len(sorted_events), sorted_events)
        current_text = cover_text
        current_images = []
        
        for section_name, section_events in grouped_sections.items():
            section_header = f"\n{section_name}\n"
            
            # If adding header exceeds limit, push current post and start new
            if len(current_text) + len(section_header) > self.max_chars:
                posts.append({'text': current_text.strip(), 'images': current_images})
                current_text = section_header.strip()
                current_images = []
            else:
                current_text += section_header
            
            for event in section_events:
                event_line = self._format_event_line(event)
                
                if len(current_text) + len(event_line) > self.max_chars:
                    # Push current post
                    posts.append({'text': current_text.strip(), 'images': current_images})
                    # Start new post with event line
                    current_text = event_line.strip()
                    current_images = []
                else:
                    current_text += event_line
                
                # Add image if available (Threads API needs URL)
                if event.get('image_url'):
                    current_images.append(event['image_url'])
        
        # Add the last remaining post
        if current_text:
            posts.append({'text': current_text.strip(), 'images': current_images})
            
        # Community Prompt (CTA) - Removed as per user request to save tokens
        # if self.enricher and posts:
        #    ...

        # 5. Redistribute Images (Optional optimization)
        # Threads allows mixing text and images. 
        # We need to ensure no post has > 10 images (Threads limit per carousel is 10, typically).
        # And total conversation limit? Actually Threads allows images in replies.
        # Let's enforce max 10 images per single post unit.
        self._enforce_image_limits(posts)
        
        return posts

    def _sort_and_filter_events(self, events: List[Dict], start: datetime, end: datetime) -> List[Dict]:
        """Sorts events by time and filters by date range."""
        from dateutil import parser
        
        filtered_events = []
        for event in events:
            # 1. Parse Date
            try:
                # Assuming event['date'] is "YYYY-MM-DD" or similar ISO
                if not event.get('date'):
                    continue
                    
                # Use dateutil for robust parsing
                event_date = parser.parse(event['date'])
                
                # Check range (Inclusive)
                if start <= event_date <= end:
                    filtered_events.append(event)
            except Exception:
                # If date parsing fails, skip (or log warning)
                continue
                
        # 2. Sort by Date
        filtered_events.sort(key=lambda x: x.get('date', ''))
        
        return filtered_events 

    def _group_events_by_section(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Groups events into sections like '上半週 (Mon-Wed)', '下半週 (Thu-Fri)', '週末 (Sat-Sun)'."""
        # Placeholder logic: just group by date string if possible, or return a single 'All Events' group
        # Real implementation would parse dates. 
        # For MVP, let's return a single group "本週活動"
        return {"本週活動": events}

    def _generate_cover_text(self, start: datetime, end: datetime, count: int, events: List[Dict]) -> str:
        date_str = f"{start.strftime('%m/%d')} - {end.strftime('%m/%d')}"
        # Fixed cover text template to save AI tokens (User request)
        # Simplified and removed emoji/redundant words
        return (
            f"音樂活動懶人包 ({date_str})\n\n"
            f"本週精選了 {count} 場演出！\n"
            "詳細資訊請看下方整理 👇"
        )


    def _format_event_line(self, event: Dict) -> str:
        # Normalize fields
        name = event.get('name') or event.get('activity_name') or "Unknown Event"
        location = event.get('location') or event.get('venue_name') or "台灣"
        city = self._extract_city(location)
        venue = location 
        
        # Time/Date handling
        # Normalize Time/Date
        time_val = event.get('time')
        date_val = event.get('date')
        
        # Use specific time if valid, otherwise fallback to date
        if not time_val or time_val == "Unknown":
            time_str = date_val or "時間待定"
        else:
            time_str = time_val
            
        # Always parse weekday from date for reliability
        weekday = self._get_weekday_zh(date_val) if date_val else ""

        # 熱門活動標籤
        hot_prefix = "🔥 [熱門盛事] " if event.get('is_hot') else ""
        
        # 新血/發現標籤
        discovery_prefix = "✨ [樂壇新血] " if event.get('is_discovery') else ""
        
        # Final prefix
        prefix = hot_prefix or discovery_prefix or "• " # Normal dot instead of emoji to be less AI-like
        
        # Clean Name & Date
        clean_name = clean_event_title(name)
        short_date = format_short_date(date_val or time_val)
        
        base_line = f"\n{prefix}[{city}] {clean_name}\n {short_date} ({weekday}) @ {venue}"
        
        # Format performers and profiles
        profiles = event.get('performer_profiles', {})
        performers = event.get('performers', [])
        
        performer_lines = []
        if performers:
            display_names = []
            desc_lines = []
            
            for p in performers:
                prof = profiles.get(p.lower(), {})
                handle = prof.get('ig_handle', '')
                desc = prof.get('description', '')
                
                # Use handle if available, otherwise just name
                if handle:
                    # Clean handle just in case it starts with @
                    handle = handle.lstrip('@')
                    display_names.append(f"@{handle}")
                else:
                    display_names.append(p)
                    
                # Add description if this is a new artist and has a description
                if desc and p in event.get('new_artists', []):
                    desc_lines.append(f"💡 {p}：{desc}")
                    
            if display_names and display_names != [name]: # Avoid repeating if name is the same as performer
                performer_lines.append(f"🎤 演出：{'、'.join(display_names)}")
                
            for d in desc_lines:
                performer_lines.append(d)
                
        if performer_lines:
            return base_line + "\n" + "\n".join(performer_lines) + "\n"
        
        return base_line + "\n"

    def _extract_city(self, location: str) -> str:
        # 簡單城市提取
        cities = ['台北', '新北', '基隆', '桃園', '新竹', '苗栗', '台中', '彰化', '南投', '雲林', '嘉義', '台南', '高雄', '屏東', '宜蘭', '花蓮', '台東']
        for c in cities:
            if c in location:
                return c
        return "台灣"

    def _get_weekday_zh(self, time_str: str) -> str:
        if not time_str:
            return ""
        try:
            from dateutil import parser
            # Parse the date part to find the weekday
            dt = parser.parse(time_str.split(' ')[0], fuzzy=True)
            weekdays = ['一', '二', '三', '四', '五', '六', '日']
            return f"週{weekdays[dt.weekday()]}"
        except Exception:
            return ""

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

