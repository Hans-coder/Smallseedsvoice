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
            self.model = 'gemini-flash-latest'
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
        你是一位在台灣獨立音樂圈打滾多年的資深樂迷，平常最愛挖掘「沒有名氣但音樂極具潛力的小團」。
        請幫我寫樂團/歌手「{performer_name}」的一句短評介紹介紹。
        
        1. description: 請用「真人的主觀心得」描述他們必聽的理由。字數 20 字以內，越口語越好。
           「絕對禁忌」：禁止任何 AI 常見開場白（例如：「這是一個...」、「為大家介紹...」、「他們的特色在於...」），完全禁止使用 Emoji，禁止過度華麗的讚美。
           「推薦語氣」：可以帶點黑話或個人情感（例如：「聽現場保證把煩惱炸爛」、「很像早期的透明雜誌，破音超對味」）。
        2. ig_handle: 如果你知道 IG 帳號（不加 @），請提供。
        
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
        你是一位台灣獨立音樂圈的挖寶達人，熱愛推薦沒什麼流量但超級好聽的小團。
        請幫我整理以下 {len(unique_names)} 個表演者的資訊。
        
        名單：{", ".join(unique_names)}
        
        要求：
        1. description: 寫出一嘴「這團真的很虧賊」的極短語氣心得（20字內）。
           「絕對禁忌」：絕對不可使用 Emoji，禁止使用 AI 套路句型（「特色是...」、「融合了...」）。
           「範本參考」：
           - 曲風迷幻到不行，適合深夜直接暈船。
           - 現場滿滿爆發力，去一次就被圈粉。
           - 編曲極致細膩，可惜一直沒紅。
        2. ig_handle: Instagram 帳號（不加 @）。
        
        回傳 JSON（以團名為 Key）：
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
            logger.error(f"Failed to get batch profiles: {e}")
            return {}

    def extract_details_batch(self, events: list) -> dict:
        """
        批次從混亂的活動標題與介紹中萃取真正的演出者名稱與演出場地。
        """
        if not self.model or not events:
            return {}
            
        prompt = f"""
        你是一位精準的資料萃取助理。請幫我從以下 {len(events)} 個活動資訊中，精準提取出「真正的表演者/樂團/歌手/DJ」名稱，以及「活動舉辦的場地/地點」。
        
        活動名單（包含活動 ID、標題、內文片段）：
        {json.dumps(events, ensure_ascii=False)}
        
        要求：
        1. performers: 只要回傳「真正的表演者名稱」陣列（例如 ["deca joins", "傷心欲絕"]）。不要包含主辦單位。如果看不出來請回傳空陣列 []。
        2. venue: 提取真正的「演出場地」（例如 "Legacy Taipei", "女巫店", "Zepp New Taipei"）。如果完全看不出地點，請回傳 null。
        3. 你的回傳格式必須是嚴格的 JSON Object，Key 是 activity_id，Value 是一個包含 performers 和 venue 的 Object。
        
        回傳範例：
        {{
            "kktix_event_1": {{ "performers": ["血肉果汁機", "滅火器"], "venue": "Legacy Taipei" }},
            "kktix_event_2": {{ "performers": [], "venue": null }}
        }}
        """
        try:
            try:
                response = self.client.models.generate_content(model=self.model, contents=prompt)
            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    logger.warning("AI Rate limit hit, sleeping for 40 seconds before retry...")
                    import time
                    time.sleep(40)
                    response = self.client.models.generate_content(model=self.model, contents=prompt)
                else:
                    logger.error(f"AI Batch Extract failed with: {e}")
                    return {}
                    
            if hasattr(response, 'usage_metadata'):
                logger.info(f"AI Batch Extract Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            text = response.text.strip()
            # 尋找 JSON 區塊
            match = re.search(r'\{.*\}', text, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                logger.info(f"Successfully extracted performers for {len(data)} events.")
                return data
            return {}
        except Exception as e:
            logger.error(f"Failed to batch extract performers: {e}")
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

