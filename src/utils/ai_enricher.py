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
