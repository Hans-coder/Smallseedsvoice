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
            return f"🎵 {event_name}\n\n"

        prompt = f"""
        你是一位台灣音樂活動推廣小助手，正在為 Threads 社群撰寫貼文。
        請根據以下活動資訊，寫一段 30-60 字的吸引人前言（Hook），要帶點情感、活潑且口語化。
        
        活動名稱：{event_name}
        日期：{date}
        地點：{venue}
        其餘資訊：{extra_info}
        
        請直接輸出這段文字，不要有引號或額外說明。
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip() + "\n\n"
        except Exception as e:
            logger.error(f"AI Enrichment failed: {e}")
            return f"🎵 {event_name}\n\n"
