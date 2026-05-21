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
        
        # 1.1 AI Batch Extraction for missing details (performers or venue)
        events_needing_extraction = []
        for e in sorted_events:
            needs_perf = not e.get('performers')
            needs_venue = not e.get('venue_name') or e.get('venue_name') == "Unknown"
            
            if (needs_perf or needs_venue):
                # Use description or price field for context
                desc = str(e.get('description', e.get('price', '')))[:300]
                events_needing_extraction.append({
                    "activity_id": e.get('activity_id', e.get('source_url', e.get('name'))),
                    "title": e.get('name') or e.get('activity_name', ''),
                    "description": desc
                })
        
        if events_needing_extraction and self.enricher:
            import time
            batch_size = 20
            for i in range(0, len(events_needing_extraction), batch_size):
                batch = events_needing_extraction[i:i+batch_size]
                extracted = self.enricher.extract_details_batch(batch)
                if extracted:
                    for e in sorted_events:
                        eid = e.get('activity_id', e.get('source_url', e.get('name')))
                        if eid in extracted:
                            res = extracted[eid]
                            if isinstance(res, dict):
                                perfs = res.get('performers')
                                venue = res.get('venue')
                                if perfs and isinstance(perfs, list) and not e.get('performers'):
                                    e['performers'] = perfs
                                if venue and (not e.get('venue_name') or e.get('venue_name') in ["Unknown", "See Details", "未提供"]):
                                    e['venue_name'] = venue
                                    e['location'] = venue
                if i + batch_size < len(events_needing_extraction):
                    time.sleep(4.5)
        
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
        
        # --- GLOBAL AI CAP TO AVOID TOKEN BURN ---
        max_ai_calls = 5
        ai_calls_made = 0
        
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
                if self.enricher and self.enricher.model and ai_calls_made < max_ai_calls:
                    import time
                    time.sleep(4.5) # Rate limit protection (Free tier 15 RPM)
                    profile_data = self.enricher.get_performer_profile(artist)
                    ai_calls_made += 1
                    
                    if profile_data:
                        desc = profile_data.get('description', '')
                        handle = profile_data.get('ig_handle', '')
                        if desc or handle:
                            tracker.update_profile(artist, description=desc, ig_handle=handle)
                            profiles[artist.lower()] = {"description": desc, "ig_handle": handle}
            
            event['performer_profiles'] = profiles
            
            # Simple Genre Classification
            event['genre'] = self._classify_genre(event)
        
        if not sorted_events:
            date_str = f"{start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')}"
            return [{
                'text': f"音樂活動懶人包 ({date_str})\n\n這兩週暫無推薦活動，大家可以先休息一下，或是去看看之前存下來的場次！",
                'images': []
            }]

        # 2. Group by City/Region
        grouped_sections = self._group_events_by_city(sorted_events)
        
        # 3. Generate Posts
        posts = []
        
        # Initialize first post with cover text
        cover_text = self._generate_cover_text(start_date, end_date, len(sorted_events), sorted_events)
        current_text = cover_text
        current_images = []
        
        # Threads limit enforcement
        for city, city_events in grouped_sections.items():
            section_header = f"\n📍 {city}\n"
            
            # If adding header exceeds limit, push current post and start new
            if len(current_text) + len(section_header) > self.max_chars:
                posts.append({'text': current_text.strip(), 'images': current_images})
                current_text = section_header.strip()
                current_images = []
            else:
                current_text += section_header
            
            for event in city_events:
                event_line = self._format_event_line_concise(event)
                
                if len(current_text) + len(event_line) > self.max_chars:
                    # Push current post
                    posts.append({'text': current_text.strip(), 'images': current_images})
                    current_text = event_line.strip()
                    current_images = []
                else:
                    current_text += event_line
                
                if event.get('image_url'):
                    current_images.append(event['image_url'])
        
        if current_text:
            posts.append({'text': current_text.strip(), 'images': current_images})
            
        # Append AI Community Prompt (CTA) to the end of the last post if available
        if self.enricher and sorted_events and posts:
            try:
                cta_prompt = self.enricher.generate_community_prompt(sorted_events)
                if cta_prompt:
                    last_post = posts[-1]
                    combined_text = last_post['text'] + "\n\n" + cta_prompt.strip()
                    if len(combined_text) <= self.max_chars:
                        last_post['text'] = combined_text
                    else:
                        posts.append({'text': cta_prompt.strip(), 'images': []})
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to append community prompt: {e}")
            
        self._enforce_image_limits(posts)
        return posts

    def _sort_and_filter_events(self, events: List[Dict], start: datetime, end: datetime) -> List[Dict]:
        """Sorts events by time and filters by date range."""
        if not events:
            return []
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

    def _group_events_by_city(self, events: List[Dict]) -> Dict[str, List[Dict]]:
        """Groups events into regional sections (Taipei, Taichung, Kaohsiung, etc.)"""
        from collections import defaultdict
        grouped = defaultdict(list)
        
        # Priority cities
        target_cities = ['台北', '新北', '桃園', '新竹', '台中', '嘉義', '台南', '高雄', '宜蘭', '花蓮', '台東']
        
        for event in events:
            location = event.get('location') or event.get('venue_name') or "台灣"
            found_city = "其他地區"
            for city in target_cities:
                if city in location:
                    found_city = city
                    break
            grouped[found_city].append(event)
            
        # Sort keys: Priority cities first, then others
        sorted_grouped = {}
        for city in target_cities:
            if city in grouped:
                sorted_grouped[city] = grouped[city]
        if "其他地區" in grouped:
            sorted_grouped["其他地區"] = grouped["其他地區"]
            
        return sorted_grouped

    def _generate_cover_text(self, start: datetime, end: datetime, count: int, events: List[Dict]) -> str:
        date_str = f"{start.strftime('%m/%d')} - {end.strftime('%m/%d')}"
        # Fixed cover text template to save AI tokens (User request)
        # Simplified and removed emoji/redundant words
        return (
            f"音樂活動懶人包 ({date_str})\n\n"
            f"接下來半週為您整理了 {count} 場演出！\n"
            "詳細資訊請看下方整理 👇"
        )


    def _format_event_line_concise(self, event: Dict) -> str:
        """鏡像使用者手動發文風格：強調 地點、時間、標題，不列出過多表演者細節"""
        name = clean_event_title(event.get('name') or event.get('activity_name') or "Unknown Event")
        venue = event.get('venue_name') or event.get('location') or "Venue"
        # 移除地點中重複的城市名
        venue = venue.replace('台北', '').replace('台中', '').replace('高雄', '').strip(' |·-')
        
        date_iso = event.get('date') or event.get('time')
        short_date = format_short_date(date_iso)
        weekday = self._get_weekday_zh(date_iso) if date_iso else ""
        
        prefix = "• "
        if event.get('is_hot'): prefix = "🔥 "
        elif event.get('is_discovery'): prefix = "✨ "
        
        return f"{prefix}{short_date}({weekday}) {name} @ {venue}\n"

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

    def _classify_genre(self, event: Dict) -> str:
        """Classify event genre based on keywords in name or caption."""
        content = (str(event.get('name', '')) + " " + str(event.get('caption', ''))).lower()
        
        genre_map = {
            'Hip-Hop / Rap': ['hip hop', 'hip-hop', '饒舌', 'rap', '嘻哈', '陷阱'],
            'Electronic / Dance': ['電子', 'edm', 'techno', 'house', 'dance', 'dj', '派對', 'party', '銳舞', 'rave'],
            'Rock / Indie': ['搖滾', 'rock', '獨立', 'indie', '樂團', 'band', '後搖', 'post rock', '瞪鞋', 'shoegaze'],
            'Jazz / Soul': ['爵士', 'jazz', '靈魂', 'soul', 'funk', '放克', '節奏藍調', 'r&b'],
            'Pop / Chill': ['流行', 'pop', '民謠', 'folk', '不插電', 'acoustic', '抒情', 'chill'],
            'C-Pop / J-Pop / K-Pop': ['華語', '日系', 'k-pop', 'j-pop', '偶像', 'idol', '動漫']
        }
        
        for genre, keywords in genre_map.items():
            if any(k in content for k in keywords):
                return genre
        return "Other"

