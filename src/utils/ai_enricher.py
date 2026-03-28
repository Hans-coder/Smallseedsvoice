"""AI Content Enricher using Gemini"""
import os
import json
import re
from google import genai
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AIEnricher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            self.model = 'gemini-flash-latest' # Stable 1.5 model with higher availability
        else:
            self.client = None
            self.model = None
            logger.warning("GEMINI_API_KEY not found. AI enrichment will be disabled.")

    def enrich_post(self, event_name: str, date: str, venue: str, extra_info: str = "") -> str:
        """用 AI 生成吸引人的貼文前言"""
        if not self.model:
            return ""

        prompt = f"""
        你是一位台灣獨立音樂推廣者，也是超級樂迷。
        請根據以下活動資訊，寫一段「非常簡短、充滿熱情」的開場語（Hook）。
        
        活動資訊：
        - 名稱：{event_name}
        - 日期：{date}
        - 地點：{venue}
        - 特色：{extra_info}

        風格要求：
        1. 語氣要像是在跟好朋友分享好消息，溫暖、親切、有溫度。
        2. 不要用任何 Hashtag (#)。
        3. 字數控制在 30 字以內，越精簡越好。
        4. 可以適當使用 Emoji，但不要過多 (1-2個)。
        5. 不要太官方，要有「我也好想去」的感覺。

        直接輸出內容即可。
        """
        
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return response.text.strip() + "\n\n"
        except Exception as e:
            logger.error(f"AI Enrichment failed: {e}")
            return ""

    def get_performer_profile(self, performer_name: str) -> dict:
        """
        獲取表演者的簡短介紹與 Instagram 帳號。
        回傳格式: {"description": "...", "ig_handle": "..."}
        """
        if not self.model:
            return {}

        prompt = f"""
        你是一個台灣獨立音樂資料庫。
        請幫我尋找樂團/歌手「{performer_name}」的資訊。
        
        1. description: 請用「一句話」描述他們的音樂風格或代表作（15-20字內）。如果不認識或沒有特定風格，請回傳空字串。
        2. ig_handle: 如果你知道他們的 Instagram 帳號（不要加 @），請提供。如果不確定，請回傳空字串。
        
        請務必且只能回傳合法的 JSON 格式：
        {{
            "description": "...",
            "ig_handle": "..."
        }}
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            # Find JSON block in the response (Model: self.model)
            text = response.text.strip()
            logger.info(f"Gemini Profile Response for {performer_name}: {text}")
            text = response.text.strip()
            match = re.search(r'\{[^{}]*\}', text)
            if match:
                data = json.loads(match.group(0))
                return {
                    "description": data.get("description", ""),
                    "ig_handle": data.get("ig_handle", "")
                }
            return {}
        except Exception as e:
            logger.error(f"Failed to get profile for {performer_name}: {e}")
            return {}

    def generate_community_prompt(self, events: list, post_type: str = "digest") -> str:
        """
        根據活動列表與貼文類型（ digest 或 radar ），
        生成一句用於結尾的社群互動問答（CTA）。
        """
        if not self.model or not events:
            return ""

        # Extract some context
        hot_events = [e.get('name') for e in events if e.get('is_hot', False)][:3]
        total = len(events)
        
        context_str = f"本週共整理 {total} 場活動。"
        if hot_events:
            context_str += f" 其中包含熱門活動：{', '.join(hot_events)}。"
            
        prompt = f"""
        你是一位台灣獨立音樂推廣者。請根據以下本週活動脈絡，寫「1 句話」的互動問句（Call to Action），放在貼文最後面讓大家留言討論。
        
        活動脈絡：
        {context_str}
        
        要求：
        1. 語氣像朋友聊天，輕鬆自然。
        2. 如果有熱門活動，可以針對它提問（例如：有人準備衝 OOO 嗎？）。
        3. 如果沒有特別的熱門活動，可以問大家這週有沒有推薦的隱藏版好團，或最期待哪場。
        4. 絕對不可超過 30 個字。
        5. 不要使用 Hashtag。
        
        直接輸出那一句話即可。
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate community prompt: {e}")
            return ""
