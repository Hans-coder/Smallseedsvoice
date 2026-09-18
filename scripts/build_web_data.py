#!/usr/bin/env python3
"""
build_web_data.py
將爬蟲蒐集的全台音樂活動資料（data/digest_raw.json）清洗、標準化，
並依照「展演空間」、「縣市區域」、「免費/售票」進行多維度彙整，
輸出成靜態前端可直接調用的 web/data/events.json。
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 知名展演空間正規化對照表 (Venue Mapping)
KNOWN_VENUES = [
    {"id": "legacy_tpe", "name": "Legacy Taipei", "keywords": ["legacy taipei", "傳 音樂展演空間", "華山legacy"], "city": "台北市"},
    {"id": "legacy_mini", "name": "Legacy mini", "keywords": ["legacy mini"], "city": "台北市"},
    {"id": "legacy_tc", "name": "Legacy Taichung", "keywords": ["legacy taichung", "台中legacy", "傳 音樂展演空間 台中"], "city": "台中市"},
    {"id": "the_wall", "name": "The Wall Live House", "keywords": ["the wall", "這牆"], "city": "台北市"},
    {"id": "revolver", "name": "Revolver", "keywords": ["revolver"], "city": "台北市"},
    {"id": "riverside", "name": "河岸留言", "keywords": ["河岸留言", "西門紅樓展演館", "公館河岸"], "city": "台北市"},
    {"id": "pipe", "name": "PIPE Live Music", "keywords": ["pipe live music", "水管音樂"], "city": "台北市"},
    {"id": "zepp", "name": "Zepp New Taipei", "keywords": ["zepp new taipei", "zepp"], "city": "新北市"},
    {"id": "live_warehouse", "name": "駁二 LIVE WAREHOUSE", "keywords": ["live warehouse", "駁二"], "city": "高雄市"},
    {"id": "paramount", "name": "百樂門酒館", "keywords": ["百樂門酒館", "paramount bar"], "city": "高雄市"},
    {"id": "kpm", "name": "高流 (高雄流行音樂中心)", "keywords": ["高流", "高雄流行音樂中心", "鯨魚堤岸", "海音館"], "city": "高雄市"},
    {"id": "taipei_arena", "name": "台北小巨蛋 / 北流", "keywords": ["小巨蛋", "北流", "臺北流行音樂中心", "台北流行音樂中心"], "city": "台北市"},
    {"id": "clapper", "name": "Clapper Studio", "keywords": ["clapper studio", "三創"], "city": "台北市"},
    {"id": "corridor", "name": "迴響音樂藝文展演空間", "keywords": ["迴響音樂", "sound live house"], "city": "台中市"},
    {"id": "tiehua", "name": "鐵花村", "keywords": ["鐵花村"], "city": "台東縣"},
]

def normalize_venue(venue_raw: str, location_raw: str) -> Dict[str, str]:
    combined = f"{venue_raw} {location_raw}".lower()
    for v in KNOWN_VENUES:
        for kw in v["keywords"]:
            if kw.lower() in combined:
                return {"venue_id": v["id"], "venue_display": v["name"], "city": v["city"]}
    
    # 預設提取
    clean_v = venue_raw.strip() if venue_raw and venue_raw not in ["Unknown", "See Details", "未提供"] else location_raw.strip()
    return {"venue_id": "other", "venue_display": clean_v or "全台展演空間", "city": ""}

def get_region(city: str) -> str:
    if any(c in city for c in ["台北", "新北", "基隆", "桃園", "宜蘭"]):
        return "雙北與北部"
    elif any(c in city for c in ["台中", "彰化", "南投", "苗栗", "雲林"]):
        return "中部"
    elif any(c in city for c in ["台南", "高雄", "屏東", "嘉義"]):
        return "南部"
    elif any(c in city for c in ["花蓮", "台東"]):
        return "東部"
    return "全台其他"

def is_free_event(price_str: str) -> bool:
    if not price_str:
        return True
    p = str(price_str).lower().strip()
    if p in ["0", "0元", "免費", "free", "免費入場", "free entry"]:
        return True
    return False

def clean_title(title: str) -> str:
    if not title:
        return "音樂演出活動"
    # 移除常見多餘前綴
    t = re.sub(r"^\s*【[^】]+】\s*", "", title)
    t = re.sub(r"^\s*\[[^\]]+\]\s*", "", t)
    return t.strip()

def build_data():
    raw_path = Path("data/digest_raw.json")
    out_dir = Path("web/data")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "events.json"

    if not raw_path.exists():
        print(f"找不到 {raw_path}，產生示範資料...")
        events_raw = []
    else:
        try:
            with open(raw_path, "r", encoding="utf-8") as f:
                events_raw = json.load(f)
        except Exception as e:
            print(f"讀取 {raw_path} 錯誤: {e}")
            events_raw = []

    print(f"讀取原始資料共 {len(events_raw)} 筆...")

    normalized_events = []
    venues_counter: Dict[str, Dict] = {}

    for idx, e in enumerate(events_raw):
        title = clean_title(e.get("name") or e.get("activity_name") or "")
        date_str = e.get("date") or e.get("time") or ""
        # 排除無效標題或過往無效資料
        if not title or title.startswith("http"):
            continue

        venue_info = normalize_venue(e.get("venue_name", ""), e.get("location", ""))
        city = e.get("city") or venue_info["city"] or "台灣"
        region = get_region(city)
        price = str(e.get("price", "")).strip()
        is_free = is_free_event(price)

        performers = e.get("performers") or []
        if isinstance(performers, str):
            performers = [p.strip() for p in performers.split(",") if p.strip()]

        # 整理單筆活動物件
        ev_item = {
            "id": e.get("activity_id") or f"ev_{idx}",
            "title": title,
            "date": date_str.split(" ")[0] if date_str else "",
            "time": e.get("start_time") or (date_str.split(" ")[1][:5] if " " in date_str else ""),
            "venue": venue_info["venue_display"],
            "venue_id": venue_info["venue_id"],
            "location": e.get("location") or venue_info["venue_display"],
            "city": city,
            "region": region,
            "price": "免費" if is_free else (price if price else "售票"),
            "is_free": is_free,
            "is_hot": e.get("is_hot", False) or ("音樂祭" in title or "音樂節" in title),
            "performers": performers,
            "ticket_platform": e.get("ticket_platform") or e.get("platform") or "官方售票",
            "ticket_url": e.get("ticket_url") or e.get("url") or "",
            "image_url": e.get("image_url") or ""
        }
        normalized_events.append(ev_item)

        # 累加展演空間計數
        vid = venue_info["venue_id"]
        vname = venue_info["venue_display"]
        if vid != "other":
            if vid not in venues_counter:
                venues_counter[vid] = {"id": vid, "name": vname, "city": city, "count": 0}
            venues_counter[vid]["count"] += 1

    # 排序：優先由近到遠
    normalized_events.sort(key=lambda x: x["date"] or "9999-99-99")

    # 排序熱門展演空間
    top_venues = sorted(list(venues_counter.values()), key=lambda x: x["count"], reverse=True)

    payload = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_events": len(normalized_events),
        "total_free": sum(1 for e in normalized_events if e["is_free"]),
        "total_hot": sum(1 for e in normalized_events if e["is_hot"]),
        "top_venues": top_venues,
        "events": normalized_events
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"成功輸出 Web 資料庫: {out_file} (共 {len(normalized_events)} 場活動，{len(top_venues)} 個知名展演空間)")

if __name__ == "__main__":
    build_data()
