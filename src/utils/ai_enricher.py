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
            self.model = 'gemini-2.0-flash-lite' # Lighter model with separate/better quota
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
        1. 語氣要像是在跟好朋友分享好消息，溫暖、親切、自然。
        2. 不要用任何 Hashtag (#)。
        3. 字數控制在 30 字以內，越精簡越好。
        4. **絕對不要使用任何 Emoji**。
        5. 不要太官方，語氣要真誠。
        6. 標題不需要重複「台灣」或是日期年份，AI 不需要加上這些贅詞。

        直接輸出內容即可。
        """
        
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            if hasattr(response, 'usage_metadata'):
                logger.info(f"AI Enrichment Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
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
        你是一位在台灣獨立音樂圈打滾多年的資深樂迷，說話語氣自然、專業、帶點誠懇的熱情。
        請幫我尋找樂團/歌手「{performer_name}」的資訊。
        
        1. description: 請用「真人的推薦語」描述他們必聽的理由或音樂魅力（20字內）。
           「禁忌」：絕對不要用「這是一個...的樂團」、「結合了...元素」等機器人感重的廢話。
           「語氣」：像是在 Live House 門口跟朋友說話那樣，完全不要用 Emoji。
        2. ig_handle: 如果你知道 Instagram 帳號（不加 @），請提供。
        
        JSON 格式：
        {{
            "description": "...",
            "ig_handle": "..."
        }}
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            if hasattr(response, 'usage_metadata'):
                logger.debug(f"AI Profile Token Usage ({performer_name}): {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            # Find JSON block in the response (Model: self.model)
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

    def get_batch_profiles(self, performers: list) -> dict:
        """
        批次獲取多位表演者的簡短介紹與 Instagram 帳號。
        """
        if not self.model or not performers:
            return {}
            
        # 移除重複與過長的名稱
        unique_names = list(set([p for p in performers if p and len(p) < 40]))
        if not unique_names:
            return {}
            
        prompt = f"""
        你是一位在台灣獨立音樂圈打滾多年的博學樂迷，熱愛推薦好團。
        請幫我整理以下 {len(unique_names)} 個表演者的資訊。
        
        名單：{", ".join(unique_names)}
        
        要求：
        1. description: 用「極其短促、像真人的推薦語」，帶出他們的現場魅力或必聽點（20字內）。
           「禁忌」：**絕對不要使用 Emoji**，不要像 AI 生成的。
           「範例」：
           - 曲風迷幻到不行，適合深夜一個人的時候聽。
           - 現場爆發力強，一定要去一次。
        2. ig_handle: Instagram 帳號（不要加 @）。
        
        回傳 JSON（以團名標籤為 Key）：
        {{ "團名": {{ "description": "...", "ig_handle": "..." }} }}
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            if hasattr(response, 'usage_metadata'):
                logger.info(f"AI Batch Profile Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            text = response.text.strip()
            # 尋找 JSON 區塊
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                logger.info(f"Successfully batch fetched {len(data)} AI profiles.")
                return data
            return {}
        except Exception as e:
            logger.error(f"Batch AI enrichment failed: {e}")
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
        3. 如果沒有特別的熱門活動，可以問大家這週有沒有推薦的隱藏版好團。
        4. 絕對不可超過 30 個字。
        5. 不要使用 Hashtag。
        6. **絕對不要使用 Emoji**。
        
        直接輸出那一句話即可。
        """
        try:
            response = self.client.models.generate_content(model=self.model, contents=prompt)
            if hasattr(response, 'usage_metadata'):
                logger.info(f"AI CTA Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            return response.text.strip()
        except Exception as e:
            logger.error(f"Failed to generate community prompt: {e}")
            return ""

