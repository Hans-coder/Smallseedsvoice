"""AI Content Enricher using Gemini"""
import os
import json
import re
import time
from google import genai
from typing import Optional, Any
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

    def _safe_generate(self, prompt: str, max_retries: int = 3) -> Optional[Any]:
        """安全呼叫 AI，處理 429 與 503 錯誤"""
        if not self.model or not self.client:
            return None

        for i in range(max_retries):
            try:
                response = self.client.models.generate_content(model=self.model, contents=prompt)
                return response
            except Exception as e:
                err_msg = str(e)
                # 處理 429 (Rate Limit) 與 503 (Service Unavailable)
                if "429" in err_msg or "503" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "UNAVAILABLE" in err_msg:
                    wait_time = (i + 1) * 30 # 指數型增加等待時間
                    logger.warning(f"AI Service Error ({err_msg}). Retrying in {wait_time}s... (Attempt {i+1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    logger.error(f"AI Unexpected Error: {e}")
                    break
        return None

    def enrich_post(self, event_name: str, date: str, venue: str, extra_info: str = "") -> str:
        """用 AI 生成吸引人的貼文前言"""
        if not self.model:
            return ""

        prompt = f"""
        你是一位在台灣獨立音樂圈打滾多年的資深樂迷，講話風格酷酷的、很真誠，像是大家的大哥哥/大姊姊。
        請根據以下活動資訊，寫一段「非常簡短、充滿渲染力」的推薦引言。
        
        活動資訊：
        - 名稱：{event_name}
        - 日期：{date}
        - 地點：{venue}
        - 特色：{extra_info}

        風格要求：
        1. 語氣要像是在 Live House 門口跟朋友說：「這場真的不能錯過」。
        2. 絕對禁忌：禁止使用「為大家推薦」、「這是一個...」、「活動將於...」等 AI 機器人口吻。
        3. 絕對禁忌：禁止使用 Hashtag (#) 以及任何 Emoji。
        4. 字數控制在 25 字以內。
        5. 不要重複日期年份，聚焦在「為什麼要去」的情緒。
        6. 直接輸出內容，不要加引號。
        """
        
        try:
            response = self._safe_generate(prompt)
            if response and hasattr(response, 'usage_metadata'):
                logger.info(f"AI Enrichment Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            return response.text.strip() + "\n\n" if response else ""
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
            response = self._safe_generate(prompt)
            if response and hasattr(response, 'usage_metadata'):
                logger.debug(f"AI Profile Token Usage ({performer_name}): {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            if not response: return {}
            
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
            response = self._safe_generate(prompt)
            if response and hasattr(response, 'usage_metadata'):
                logger.info(f"AI Batch Profile Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            if not response: return {}
            
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
            response = self._safe_generate(prompt)
                    
            if response and hasattr(response, 'usage_metadata'):
                logger.info(f"AI Batch Extract Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            if not response: return {}
            
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
            response = self._safe_generate(prompt)
            if response and hasattr(response, 'usage_metadata'):
                logger.info(f"AI CTA Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            return response.text.strip() if response else ""
        except Exception as e:
            logger.error(f"Failed to generate community prompt: {e}")
            return ""

    def recover_missing_venue(self, event_name: str, event_desc: str = "") -> Optional[str]:
        """
        嘗試從活動名稱或描述中找出遺失的場地資訊。
        """
        if not self.model:
            return None

        prompt = f"""
        請根據以下活動標題與描述，判斷該活動舉辦的「演出場地/地點」名稱。
        只要回傳場地名稱（例如：Legacy Taipei, Zepp New Taipei, 女巫店, Revolver）。
        如果完全找不到，請回傳 "Unknown"。
        不要回傳任何其他解釋。

        活動名稱：{event_name}
        活動描述片段：{event_desc[:500]}
        """
        try:
            response = self._safe_generate(prompt)
            if not response: return None
            result = response.text.strip()
            if result.lower() == "unknown" or len(result) > 50:
                return None
            return result
        except Exception as e:
            logger.error(f"Failed to recover venue for {event_name}: {e}")
            return None

    def polish_digest_post(self, raw_text: str) -> str:
        """
        讓 Gemini 潤飾已經組裝好的 Thread 貼文，使其排版更像真人且易讀，並控制字數。
        """
        if not self.model:
            return raw_text

        prompt = f"""
        你是一位在台灣獨立音樂圈打滾多年的資深樂迷。
        請幫我將以下這段系統自動生成的音樂活動清單重新排版潤飾，讓它看起來像是一個熱心樂迷的手打分享。
        
        原始文字：
        {raw_text}
        
        要求：
        1. 乾淨、易讀，可以適度使用項目符號或分隔線。
        2. 絕對禁止使用 AI 罐頭用語（例如：「為您整理」、「這是一個」、「結論是」）。
        3. 絕對保留「所有」的活動名稱、日期與地點，不可隨意刪減任何一場活動。
        4. 因為 Threads 字數限制，總字數務必嚴格控制在 450 字以內。
        5. 不要使用過多的 Emoji，保持俐落自然。
        
        請直接回傳潤飾後的文字，不需加引號或其他廢話。
        """
        try:
            response = self._safe_generate(prompt)
            if response and hasattr(response, 'usage_metadata'):
                logger.info(f"AI Polish Token Usage: {response.usage_metadata.prompt_token_count} prompt, {response.usage_metadata.candidates_token_count} candidates")
            
            if response and response.text:
                polished_text = response.text.strip()
                # 簡單防禦：如果 AI 產生的字數反而爆滿（超過 490），就退回使用原文字
                if len(polished_text) > 490:
                    logger.warning(f"AI Polished text is too long ({len(polished_text)} chars), falling back to raw text.")
                    return raw_text
                return polished_text
            return raw_text
        except Exception as e:
            logger.error(f"Failed to polish digest post: {e}")
            return raw_text


