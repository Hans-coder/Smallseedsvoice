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

def get_event_hash(name: str, date: str, venue: str) -> str:
    """生成活動內容的唯一雜湊值，用於跨平台去重"""
    # 1. 標題清理 (關鍵字提取)
    clean_n = clean_event_title(name or "Unknown")
    # 2. 地點清理 (只保留重要部分)
    clean_v = (venue or "Venue").split('(')[0].split('（')[0].strip()
    # 3. 日期格式化
    clean_d = date or "0000-00-00"
    
    import hashlib
    content = f"{clean_n}|{clean_d}|{clean_v}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()
