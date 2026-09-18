"""
Curator Formatter Module
Responsible for packaging Taiwan music events into high-engagement Threads formats:
1. Spotlight Post (單場焦點爆款 / 免費音樂祭 / 大活動) - 格式參考頂級社群帳號 (@sky_silp)
2. Curator Pick Post (小聲音私心推) - 具備樂團風格評析、個人品味與話語權
3. Conversational CTAs (社交型行動呼籲) - 觸發 Threads 演算法的「收藏」與「標記朋友」機制
"""

import random
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.utils.text_cleaners import clean_event_title


class CuratorFormatter:
    """策展人發文格式化引擎"""

    WEEKDAY_MAP = {0: "㊀", 1: "㊁", 2: "㊂", 3: "㊃", 4: "㊄", 5: "㊅", 6: "㊐"}
    WEEKDAY_ZH = {0: "週一", 1: "週二", 2: "週三", 3: "週四", 4: "週五", 5: "週六", 6: "週日"}

    # 社交型行動召喚 (CTA) 庫
    CTA_TAG_FRIEND = [
        "💬 標記那個每次都說要聽團、但最後放鳥的朋友一起衝 👥",
        "💬 這陣容太扯了吧！快 @ 你那個聽團狂魔朋友 👇",
        "💬 這場免費入場太香了，標記你想一起去吹風聽歌的人！",
        "💬 假日還不知道去哪晃？先轉發收藏起來，找朋友衝一波 🏃‍♂️",
    ]

    CTA_ENGAGEMENT_QUESTIONS = [
        "💬 這名單裡你最想在現場看誰的演出？留言告訴我 👇",
        "💬 聽過他們的舉手！你私心最推他們哪一首歌？🎧",
        "💬 週六撞場撞成這樣，如果是你，這週會選哪一場？👇",
        "💬 已經買好票的來留言區認親！現場見 🔥",
    ]

    CTA_COMMUNITY_CONTRIBUTION = [
        "💬 本週還有哪場你私心超推、但我漏掉的演出？留言區開放推坑！👇",
        "💬 大家都搶到票了嗎？留言區開放回報戰況！",
    ]

    CTA_WEB_PORTAL = (
        "🔗 全台各展演空間（Legacy / Revolver / 駁二 等）完整演出地圖與購票連結，已整理在首頁網站！"
    )

    @classmethod
    def get_weekday_icon(cls, dt: datetime) -> str:
        return cls.WEEKDAY_MAP.get(dt.weekday(), "")

    @classmethod
    def get_weekday_zh(cls, dt: datetime) -> str:
        return cls.WEEKDAY_ZH.get(dt.weekday(), "")

    @classmethod
    def parse_event_datetime(cls, event: Dict) -> Tuple[Optional[datetime], str]:
        """解析活動日期與時間字串"""
        date_str = event.get("date") or event.get("time") or ""
        time_str = event.get("start_time") or ""
        dt = None
        try:
            from dateutil import parser
            dt = parser.parse(date_str.split(" ")[0], fuzzy=True)
        except Exception:
            pass

        if not time_str and dt and " " in date_str:
            time_part = date_str.split(" ")[1]
            if ":" in time_part:
                time_str = time_part[:5]

        return dt, time_str

    @classmethod
    def format_price_badge(cls, event: Dict) -> str:
        price = str(event.get("price", "")).strip()
        if not price or price in ["0", "0元", "免費", "Free", "free"]:
            return "免費"
        return "售票"

    @classmethod
    def format_spotlight_post(
        cls,
        event: Dict,
        custom_cta: Optional[str] = None,
        tagline: Optional[str] = None
    ) -> Dict:
        """
        生成單場爆款焦點貼文 (Spotlight)
        特色：
        - Unicode 旗幟與日期標章：⚑ 2026/10/03㊅ 16:30
        - 活動大標與性質標籤：《活動名稱》（免費 / 售票）
        - 愛心卡司清單：♥︎藝人1 ♥︎藝人2
        - 地點邊框：❑ [城市] 場地名稱 ❑
        - 揪團型社交 CTA
        """
        name = clean_event_title(event.get("name") or event.get("activity_name") or "演出活動")
        dt, time_str = cls.parse_event_datetime(event)
        
        # 1. 時間標籤
        if dt:
            weekday_icon = cls.get_weekday_icon(dt)
            date_display = dt.strftime("%Y/%m/%d") + weekday_icon
            if time_str:
                date_display += f" {time_str}"
        else:
            date_display = event.get("date", "近期活動")

        # 2. 票價性質
        price_badge = cls.format_price_badge(event)

        # 3. 地點
        venue = event.get("venue_name") or event.get("location") or "全台展演空間"
        city = event.get("city") or ""
        location_display = f"[{city}] {venue}" if city and city not in venue else venue

        # 4. 卡司名單處理 (加入 ♥︎ 符號)
        performers = event.get("performers") or []
        if isinstance(performers, str):
            performers = [p.strip() for p in performers.split(",") if p.strip()]
        
        performer_text = ""
        if performers:
            heart_list = [f"♥︎{p.strip()}" for p in performers if p.strip()]
            # 如果藝人很多，適度排版
            if len(heart_list) > 6:
                performer_text = "➤ 卡司陣容：\n" + " ".join(heart_list[:12])
                if len(heart_list) > 12:
                    performer_text += f" 等 {len(heart_list)} 組藝人"
            else:
                performer_text = "➤ 卡司陣容：\n" + " ".join(heart_list)

        # 5. CTA 選擇
        if custom_cta:
            cta_text = custom_cta
        elif price_badge == "免費":
            cta_text = random.choice([
                "💬 免費入場太佛了吧！標記那個每次都喊沒錢聽團的朋友快衝 👥",
                "💬 這週末免費去處有了！轉發分享給想一起聽歌的人 🎶"
            ])
        else:
            cta_text = random.choice(cls.CTA_TAG_FRIEND + cls.CTA_ENGAGEMENT_QUESTIONS)

        # 組合內容
        lines = []
        if tagline:
            lines.append(f"✨ {tagline}\n")
        
        lines.append(f"⚑ {date_display} 《{name}》（{price_badge}）\n")
        
        if performer_text:
            lines.append(f"{performer_text}\n")
            
        lines.append(f"❑ 地點：{location_display} ❑\n")
        
        # 售票/資訊來源提示
        ticket_platform = event.get("ticket_platform") or ""
        ticket_url = event.get("ticket_url") or event.get("url") or ""
        if ticket_platform and ticket_url:
            lines.append(f"▶ 購票系統：{ticket_platform}\n")
            
        lines.append(f"{cta_text}\n")
        lines.append(f"🔗 依展演空間看全台本週演出：見首頁連結")

        post_text = "\n".join(lines).strip()

        # 圖片處理
        image_url = event.get("image_url")
        images = [image_url] if image_url and image_url.startswith("http") else []

        return {
            "type": "spotlight",
            "title": name,
            "text": post_text,
            "images": images,
            "event": event
        }

    @classmethod
    def format_curator_pick_post(
        cls,
        event: Dict,
        curator_recommendation: str,
        highlight_song: Optional[str] = None
    ) -> Dict:
        """
        生成「小聲音私心推」貼文
        特色：
        - 建立小聲音 IP 的音樂品味與話語權
        - 強調聽團感受、現場氛圍、歌曲亮點
        - 針對樂迷社群的互動設計
        """
        name = clean_event_title(event.get("name") or event.get("activity_name") or "演出")
        dt, time_str = cls.parse_event_datetime(event)
        
        date_str = dt.strftime("%m/%d") if dt else event.get("date", "")
        venue = event.get("venue_name") or event.get("location") or ""
        city = event.get("city") or ""
        location_display = f"[{city}] {venue}" if city and city not in venue else venue
        price_badge = cls.format_price_badge(event)

        lines = [
            f"【小聲音私心推 🎧】《{name}》\n",
            f"{curator_recommendation}\n",
        ]

        if highlight_song:
            lines.append(f"🎵 推薦先聽這首入坑：〈{highlight_song}〉\n")

        lines.extend([
            f"📅 時間：{date_str} {time_str}".strip(),
            f"📍 地點：{location_display}",
            f"🎫 性質：{price_badge}",
            "\n" + random.choice([
                "💬 有聽過他們的舉手！你最喜歡他們現場哪首的氛圍？👇",
                "💬 這場我真的大推！現場見，標記那個你推坑過的朋友 👥",
                "💬 這種小場地專場最容易被炸到，這週準備衝哪場？👇"
            ]),
            "🔗 完整展演空間地圖與購票：首頁網站"
        ])

        post_text = "\n".join(lines).strip()
        image_url = event.get("image_url")
        images = [image_url] if image_url and image_url.startswith("http") else []

        return {
            "type": "curator_pick",
            "title": f"小聲音私心推：{name}",
            "text": post_text,
            "images": images,
            "event": event
        }

    @classmethod
    def format_upgraded_cover_text(
        cls,
        start_date: datetime,
        end_date: datetime,
        event_count: int,
        free_count: int = 0,
        hot_count: int = 0
    ) -> str:
        """
        升級版每週週報 Cover Post（擺脫冰冷機器人感）
        """
        start_fmt = f"{start_date.strftime('%m/%d')} ({cls.get_weekday_zh(start_date)})"
        end_fmt = f"{end_date.strftime('%m/%d')} ({cls.get_weekday_zh(end_date)})"

        lines = [
            f"【全台音樂活動週報 🎸】({start_fmt} - {end_fmt})\n",
            f"下週全台共有 {event_count} 場音樂現場！",
        ]

        highlights = []
        if free_count > 0:
            highlights.append(f"✨ {free_count} 場完全免費戶外/市集活動")
        if hot_count > 0:
            highlights.append(f"🔥 {hot_count} 場焦點熱門大專場")

        if highlights:
            lines.append("、".join(highlights) + "，聽團行事曆準備排起來 🏃‍♂️\n")
        else:
            lines.append("你的聽團行事曆排滿了嗎？\n")

        lines.extend([
            "詳細每日場次請看下方串文整理 👇",
            "💬 這週你打算衝哪幾場？還是要去哪個 Livehouse 喝酒？留言區開聊！\n",
            "🗺️ 想依照「展演空間」或「縣市」秒查所有演出？首頁網站已同步更新！"
        ])

        return "\n".join(lines)
