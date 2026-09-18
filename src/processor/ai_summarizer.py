import os
import logging
import json
from typing import List, Dict, Optional
import google.generativeai as genai
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AISummarizer:
    """AI-based content organizer for Taiwan Music Events"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.enabled = False
        
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.enabled = True
                logger.info("Gemini AI Summarizer initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini AI: {e}")
        else:
            logger.warning("No GEMINI_API_KEY found. AI Summarizer will be disabled.")

    def organize_digest(self, events: List[Dict], start_date_str: str, end_date_str: str) -> Optional[List[Dict]]:
        """
        Organize events into a natural thread structure using AI.
        
        Returns:
            List of thread blocks: [{'text': '...', 'image_paths': [...]}, ...]
        """
        if not self.enabled or not events:
            return None

        # Prepare context for AI
        events_context = []
        for i, e in enumerate(events):
            events_context.append({
                "id": i,
                "name": e.get('name'),
                "time": e.get('time'),
                "location": e.get('location'),
                "platform": e.get('platform')
            })

    def generate_curator_note(self, event: Dict) -> Optional[str]:
        """
        為特定樂團/專場生成熱血、有溫度的「小聲音私心推」短評（50-100字），建立 IP 話語權。
        """
        if not self.enabled or not event:
            return None

        event_name = event.get('name') or event.get('activity_name', '')
        performers = ", ".join(event.get('performers', [])) or event_name
        venue = event.get('venue_name') or event.get('location', '')
        desc = str(event.get('description', ''))[:300]

        prompt = f"""
你是一位熱愛台灣獨立音樂、懂聽團文化的音樂策展人（帳號：你的聽團小聲音）。
請為以下這場演出撰寫一段短小精悍（約 60-100 字）、極具感染力與品味的「私心推薦短評」。

演出名稱：{event_name}
演出者/樂團：{performers}
展演場地：{venue}
活動簡介：{desc}

### 撰寫指引：
1. **口吻**：真誠熱血、像樂迷私下在 Livehouse 吧台推坑朋友，不要官方新聞稿腔，不要 AI 機器人感。
2. **切入點**：聚焦在現場渲染力、音樂風格氛圍（如：吉他破音、主唱嗓音、微醺後搖、直球龐克、爽度），點出「為什麼這場一定要去」。
3. **禁止**：過度誇張的老套成語、虛假宣傳詞。
4. **輸出**：直接輸出推薦短評純文字，不要包含任何標籤或多餘前言。
"""
        try:
            response = self.model.generate_content(prompt)
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate curator note: {e}")
        return None

    def organize_digest(self, events: List[Dict], start_date_str: str, end_date_str: str) -> Optional[List[Dict]]:
        """
        Organize events into a natural thread structure using AI.
        
        Returns:
            List of thread blocks: [{'text': '...', 'image_paths': [...]}, ...]
        """
        if not self.enabled or not events:
            return None

        # Prepare context for AI
        events_context = []
        for i, e in enumerate(events):
            events_context.append({
                "id": i,
                "name": e.get('name'),
                "time": e.get('time'),
                "location": e.get('location'),
                "platform": e.get('platform'),
                "is_hot": e.get('is_hot', False),
                "price": e.get('price', '')
            })

        prompt = f"""
你是一位深耕台灣獨立音樂與現場演出的音樂策展人（帳號：你的聽團小聲音）。
請將以下提供的音樂活動整理成適合發布在 Threads 上的「每週活動懶人包」。

日期範圍：{start_date_str} 至 {end_date_str}
活動數量：{len(events)} 場

### 撰寫規範：
1. **口吻自然且有溫度**：像真實音樂愛好者在分享這週去哪聽歌，排版乾淨、節奏明快。
2. **吸引人的互動設計**：第一則貼文請附帶一句引發留言討論的問句（例如：「這週你最想衝哪一場？」、「標記那個說好要聽團的朋友！」）。
3. **適度表情符號**：可適當使用簡潔有質感的 Emoji（如 🎸、🔥、✨、📍），但切勿過度泛濫。禁止使用 Hashtag (#)。
4. **字數限制**：Threads 每則貼文上限為 500 字。請將內容拆分成多個區塊（Thread Blocks）。
5. **結構建議**：
   - 第一則貼文（Block 1）：熱門活動精選／免費場提要 + 前幾天活動。
   - 後續貼文（Replies）：依日期排列之其餘活動，末尾提醒大家「依照展演空間完整地圖可看首頁連結」。
6. **格式**：
   每個活動請包含：名稱、地點，若為免費場或熱門場請予以標註。
   範例格式：
   • [台北] 活動名稱 @ Legacy Taipei (免費)

7. **輸出要求**：
   請以 JSON 陣列格式輸出，每個元素代表一則貼文。
   格式範例：[ {{"text": "貼文內容", "event_ids": [0, 1]}}, ... ]
   請確保內容完整，不要遺漏任何活動。

活動列表：
{json.dumps(events_context, ensure_ascii=False, indent=2)}
"""

        try:
            # Retry logic for 503/429
            response = None
            max_retries = 3
            for i in range(max_retries):
                try:
                    response = self.model.generate_content(prompt)
                    break
                except Exception as e:
                    err_msg = str(e)
                    if "503" in err_msg or "429" in err_msg or "UNAVAILABLE" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                        wait_time = (i + 1) * 30
                        logger.warning(f"AI Summarizer Error ({err_msg}). Retrying in {wait_time}s... ({i+1}/{max_retries})")
                        import time
                        time.sleep(wait_time)
                    else:
                        raise e
            
            if not response:
                return None

            # Find JSON in response (Gemini sometimes adds markdown codes blocks)
            raw_text = response.text
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[-1].split("```")[0]
            elif "```" in raw_text:
                 raw_text = raw_text.split("```")[-1].split("```")[0]
            
            blocks = json.loads(raw_text.strip())
            
            # Map back images
            final_thread = []
            for block in blocks:
                text = block.get('text', '')
                event_ids = block.get('event_ids', [])
                images = []
                for eid in event_ids:
                    if 0 <= eid < len(events):
                        # Use image_url (public) for Threads API
                        # image_path is kept in events dict for local backup but Threads needs URL
                        img_url = events[eid].get('image_url')
                        if img_url:
                            images.append(img_url)
                
                final_thread.append({
                    'text': text,
                    'images': images 
                })
            
            return final_thread

        except Exception as e:
            logger.error(f"AI summarization failed: {e}")
            return None
