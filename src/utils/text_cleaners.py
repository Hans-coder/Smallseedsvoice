"""文字清理工具"""
import re
from datetime import datetime

def clean_event_title(title: str) -> str:
    """清理活動標題，移除贅字"""
    if not title:
        return ""
    
    # 1. 移除年份 (2024, 2025, 2026)
    title = re.sub(r'202[4-6][\s\-/]*', '', title)
    
    # 2. 移除 "台灣"、"TAIWAN"、"Taiwan"
    title = re.sub(r'(台灣|TAIWAN|Taiwan)[\s\-]*', '', title)
    
    # 3. 移除常見的括號備註 (如 [KKTIX], (已完售) 等)
    title = re.sub(r'[\[\(【].*?[\]\)】]', '', title)
    
    # 4. 移除多餘空格
    title = title.strip()
    
    return title

def format_short_date(date_str: str) -> str:
    """將 ISO 日期 (YYYY-MM-DD) 轉換為 MM/DD 格式"""
    if not date_str:
        return "時間待定"
    
    try:
        # 如果包含時間，只取日期部分
        date_part = date_str.split(' ')[0]
        dt = datetime.strptime(date_part, "%Y-%m-%d")
        return dt.strftime("%m/%d")
    except Exception:
        # 如果解析失敗，嘗試正則表達式提取 MM-DD 並轉換
        match = re.search(r'(\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            return f"{match.group(1).zfill(2)}/{match.group(2).zfill(2)}"
        return date_str

def refine_image_url(url: str) -> str:
    """優化圖片 URL，獲取更高清版本並去除冗餘參數"""
    if not url or not url.startswith('http'):
        return url
    
    # 1. 處理 StreetVoice 的縮圖參數
    if 'streetvoice.com' in url and '?x-oss-process=' in url:
        # 移除 resize 參數，獲取原始大圖
        url = url.split('?x-oss-process=')[0]
    
    # 2. 處理 KKTIX/Indievox 等常見的查詢參數（有時候會造成重複下載）
    # 但要注意 Instagram 的 URL 參數有時包含簽名，不能隨便刪除
    if 'instagram.com' not in url and '?' in url:
        url = url.split('?')[0]
        
    return url

def normalize_venue_name(venue: str) -> str:
    """正規化常見展演空間名稱，消除跨平台寫法差異"""
    if not venue:
        return ""
    v = str(venue).strip()
    # 移除括號備註 (如 "(台北場)", "（Legacy Taipei）" 等)
    v = re.sub(r'[\[\(（【].*?[\]\)）】]', '', v).strip()
    v_lower = v.lower()
    
    if "legacy" in v_lower:
        if "taichung" in v_lower or "台中" in v:
            return "Legacy Taichung"
        return "Legacy Taipei"
    if "revolver" in v_lower:
        return "Revolver"
    if "the wall" in v_lower or "這牆" in v:
        return "The Wall"
    if "女巫店" in v or "witch house" in v_lower:
        return "女巫店"
    if "pipe" in v_lower:
        return "PIPE Live Music"
    if "河岸留言" in v:
        if "西門" in v or "紅樓" in v:
            return "西門紅樓河岸留言"
        return "公館河岸留言"
    if "zepp" in v_lower:
        return "Zepp New Taipei"
    if "warehouse" in v_lower or "駁二" in v or "高流" in v:
        return "LIVE WAREHOUSE"
    if "小巨蛋" in v:
        if "高雄" in v:
            return "高雄巨蛋"
        return "台北小巨蛋"
    if "流行音樂中心" in v or "北流" in v or "高流" in v:
        if "高雄" in v:
            return "高雄流行音樂中心"
        return "台北流行音樂中心"
    
    return v

def normalize_title_for_matching(title: str) -> str:
    """專為比對設計的極簡標題標準化"""
    cleaned = clean_event_title(title or "")
    # 移除非中英文字元與數字
    cleaned = re.sub(r'[^\w\u4e00-\u9fff]+', '', cleaned.lower())
    return cleaned

def get_event_hash(name: str, date: str, venue: str) -> str:
    """生成活動內容的唯一雜湊值，用於跨平台去重"""
    clean_n = normalize_title_for_matching(name or "Unknown")
    clean_v = normalize_venue_name(venue or "Venue").lower()
    clean_d = format_short_date(date or "0000-00-00")
    
    import hashlib
    content = f"{clean_n}|{clean_d}|{clean_v}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def is_same_event(e1: dict, e2: dict) -> bool:
    """
    判斷兩個活動物件是否為同一場活動（跨平台模糊去重）。
    判定條件：
      1. 日期必須一致（以 MM/DD 判定）
      2. 滿足下列其一：
         a. 標題標準化後完全相同
         b. 場地正規化後相同，且標題核心詞互相包含（長度>=3）或標題字元重疊率高
         c. 兩者演出者名單有共同樂團/歌手，且場地或日期相同
    """
    d1 = format_short_date(e1.get('date') or e1.get('time') or "")
    d2 = format_short_date(e2.get('date') or e2.get('time') or "")
    if d1 != d2 or d1 == "時間待定" or not d1:
        return False
    
    t1 = normalize_title_for_matching(e1.get('name') or e1.get('activity_name') or "")
    t2 = normalize_title_for_matching(e2.get('name') or e2.get('activity_name') or "")
    if not t1 or not t2:
        return False
        
    # 標題完全一致
    if t1 == t2:
        return True

    v1 = normalize_venue_name(e1.get('venue_name') or e1.get('location') or e1.get('venue') or "")
    v2 = normalize_venue_name(e2.get('venue_name') or e2.get('location') or e2.get('venue') or "")

    # 場地相同（非空且非 Unknown）
    has_valid_venue = bool(v1 and v2 and v1.lower() not in ["unknown", "venue", "未提供", "場地詳見官網"] and v1 == v2)
    
    # 標題子字串包含（較短長度需 >= 3，如 "爛泥發芽" in "爛泥發芽台北場"）
    min_len = min(len(t1), len(t2))
    if min_len >= 3 and (t1 in t2 or t2 in t1):
        if has_valid_venue or min_len >= 5:
            return True

    # 演出者重疊比對
    p1 = set(e1.get('performers') or [])
    p2 = set(e2.get('performers') or [])
    if p1 and p2 and (p1 & p2):
        if has_valid_venue or (min_len >= 2 and (t1 in t2 or t2 in t1)):
            return True

    # 標題雙向字元 Jaccard 相似度
    set1, set2 = set(t1), set(t2)
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    if union > 0 and (intersection / union) >= 0.75:
        if has_valid_venue or (intersection >= 4):
            return True

    return False

def merge_event_details(base_event: dict, incoming_event: dict) -> dict:
    """
    智慧融合兩個相同活動的資訊（Best-of-both-worlds）：
    - 保留 StreetVoice 的演出者（performers）與音樂探索詳情
    - 補齊售票平台的購票連結（ticket_url）、平台名（ticket_platform）、票價（price）
    - 採用更高清晰度的大圖
    - 補齊遺漏的場地（venue_name）
    - 若任一標記為 is_hot，則維持 is_hot
    """
    # 1. 演出者名單融合
    base_perfs = base_event.get('performers') or []
    inc_perfs = incoming_event.get('performers') or []
    if not base_perfs and inc_perfs:
        base_event['performers'] = inc_perfs
    elif base_perfs and inc_perfs:
        # 合併去重並保持順序
        merged_perfs = list(dict.fromkeys(base_perfs + inc_perfs))
        base_event['performers'] = merged_perfs

    # 2. 售票連結與平台
    base_ticket = base_event.get('ticket_url') or ""
    inc_ticket = incoming_event.get('ticket_url') or ""
    # 若 base 沒有售票連結，或 base 是 StreetVoice 介紹頁而 incoming 是專業售票頁 (KKTIX/iNDIEVOX/tixCraft/TicketPlus)
    ticketing_domains = ["kktix.com", "kktix.cc", "indievox.com", "tixcraft.com", "ticketplus.com"]
    inc_is_ticketing = any(d in inc_ticket for d in ticketing_domains)
    base_is_ticketing = any(d in base_ticket for d in ticketing_domains)
    
    if (not base_ticket and inc_ticket) or (not base_is_ticketing and inc_is_ticketing):
        base_event['ticket_url'] = inc_ticket
        if incoming_event.get('ticket_platform'):
            base_event['ticket_platform'] = incoming_event['ticket_platform']

    # 3. 票價
    if not base_event.get('price') and incoming_event.get('price'):
        base_event['price'] = incoming_event['price']

    # 4. 場地正規化與補齊
    base_venue = base_event.get('venue_name') or base_event.get('location') or ""
    inc_venue = incoming_event.get('venue_name') or incoming_event.get('location') or ""
    if (not base_venue or base_venue.lower() in ["unknown", "未提供", "場地詳見官網"]) and inc_venue:
        base_event['venue_name'] = inc_venue
        base_event['location'] = inc_venue

    # 5. 圖片優先度（若 base 沒有圖，或 incoming 是更高清的售票海報）
    if not base_event.get('image_url') and incoming_event.get('image_url'):
        base_event['image_url'] = refine_image_url(incoming_event['image_url'])

    # 6. 熱門活動標記
    if incoming_event.get('is_hot'):
        base_event['is_hot'] = True

    return base_event

