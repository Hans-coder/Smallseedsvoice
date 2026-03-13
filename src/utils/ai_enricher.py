"""AI Content Enricher using Gemini"""
import os
import google.generativeai as genai
from typing import Optional
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AIEnricher:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
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
            response = self.model.generate_content(prompt)
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
            response = self.model.generate_content(prompt)
            import json
            import re
            
            # Find JSON block in the response
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
