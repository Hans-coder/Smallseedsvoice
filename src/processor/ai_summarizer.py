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

        prompt = f"""
你是一位專業的台灣音樂活動策展人，擅長在 Threads 上撰寫親切、自然且吸引人的活動介紹。
請根據以下提供的活動列表，整理成適合發布在 Threads 上的「每週活動懶人包」。

日期範圍：{start_date_str} 至 {end_date_str}
活動數量：{len(events)} 場

### 撰寫規範：
1. **口吻自然**：聽起來像真人在推薦，不要有 AI 感。避免使用過度浮誇的形容詞。
2. **禁止標籤與表情符號**：嚴格禁止使用任何 Hashtag (#) 以及任何 Emoji (表情符號)。
3. **字數限制**：Threads 每則貼文上限為 500 字。請將內容拆分成多個區塊（Thread Blocks）。
4. **結構建議**：
   - 第一則貼文（Block 1）：吸引人的引言 + 前幾場活動。盡量在第一則貼文多放一點內容，不要只放引言。
   - 後續貼文（Replies）：剩餘的活動列表，按日期排序。
5. **格式**：
   每個活動請包含：名稱、日期、地點。
   範例格式：
   [台北] 活動名稱
   日期：2026.01.09
   地點：Legacy Taipei

6. **輸出要求**：
   請以 JSON 陣列格式輸出，每個元素代表一則貼文。
   格式範例：[ {{"text": "貼文內容", "event_ids": [0, 1]}}, ... ]
   請確保內容完整，不要遺漏任何活動。

活動列表：
{json.dumps(events_context, ensure_ascii=False, indent=2)}
"""

        try:
            response = self.model.generate_content(prompt)
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
