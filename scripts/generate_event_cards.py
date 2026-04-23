import json
import os
import hashlib
import requests
import re
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

CACHE_DIR = "data/preview_cache"
OUTPUT_DIR = "data/event_cards"
RADAR_FILE = "data/radar_events.json"

FONT_BOLD = "/System/Library/Fonts/STHeiti Medium.ttc"
FONT_REGULAR = "/System/Library/Fonts/STHeiti Light.ttc"
# For English/Numbers minimalist aesthetic, you can also use Helvetica, if preferred, but we will stick to STHeiti for mixed text.

# 台灣常見展演空間 / 音樂祭 關鍵字對照表
COMMON_VENUES = {
    "Legacy Taipei": ["legacy taipei", "legacy"],
    "Legacy Taichung": ["legacy taichung", "台中 legacy"],
    "The Wall": ["the wall", "這牆"],
    "Revolver": ["revolver"],
    "LIVE WAREHOUSE": ["live warehouse", "高流"],
    "迴響音樂藝文展演空間": ["迴響", "sound live house"],
    "PIPE Live Music": ["pipe", "水管"],
    "女巫店": ["女巫店"],
    "海邊的卡夫卡": ["卡夫卡", "kafka"],
    "SUB": [" sub", "sub ", "sub台北"],
    "百樂門酒館": ["paramount bar", "百樂門"],
    "樂悠悠之口": ["樂悠悠之口"],
    "台灣祭": ["台灣祭", "taiwan music", "taiwan festival"],
    "大港開唱": ["大港", "megaport"],
    "浮現祭": ["浮現祭"]
}

def guess_venue(title: str, current_venue: str):
    """如果場地是 Unknown，根據活動標題特徵做推論"""
    if current_venue and current_venue.lower() != "unknown":
        return current_venue
        
    t_lower = title.lower()
    for official_name, keywords in COMMON_VENUES.items():
        for kw in keywords:
            if kw in t_lower:
                # 再次透過城市的關鍵字判斷Legacy到底是台北還是台中
                if "legacy" in kw:
                    if "台中" in t_lower or "taichung" in t_lower:
                        return "Legacy Taichung"
                    else:
                        return "Legacy Taipei"
                return official_name
    
    # 簡單用正則抓取常見的 @ 或 in 後面的地名
    match = re.search(r'[@|＠|in|於]\s*([^\s\]】。]+)', title, re.IGNORECASE)
    if match:
        extracted = match.group(1).strip()
        if len(extracted) >= 2 and len(extracted) < 15:
            return extracted
            
    return "Secret Venue"

def ensure_dirs():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

def download_image(url: str) -> str:
    if not url: return None
    clean_url = url.split('?')[0]
    ext = clean_url.split('.')[-1]
    if len(ext) > 4 or not ext: ext = "jpg"
        
    filename = hashlib.md5(clean_url.encode('utf-8')).hexdigest() + f".{ext}"
    local_path = os.path.join(CACHE_DIR, filename)
    if os.path.exists(local_path): return local_path
        
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(clean_url, headers=headers, timeout=10)
        if resp.status_code == 200:
            with open(local_path, "wb") as f: f.write(resp.content)
            return local_path
    except Exception as e:
        print(f"Error downloading {clean_url}: {e}")
    return None

def wrap_text(text, font, max_width, draw):
    lines = []
    if hasattr(font, 'getlength'):
        def get_width(t): return font.getlength(t)
    else:
        def get_width(t): return draw.textlength(t, font=font)
        
    for paragraph in text.split('\n'):
        line = ''
        for char in paragraph:
            if get_width(line + char) <= max_width:
                line += char
            else:
                lines.append(line)
                line = char
        if line: lines.append(line)
    return lines

def generate_card(event, index):
    """
    極簡日系高質感排版 (Smallseedsvoice 品牌風格)
    - 色調: 侘寂風深灰、奶油白字、莫蘭迪大地色/金色點綴
    - 排版: 乾淨俐落，大量的呼吸空間 (Negative Space)
    """
    WIDTH, HEIGHT = 1080, 1350
    # 色彩計畫 (High-Saturation & Texture Palette)
    BG_COLOR = '#0A0A0B'        # 極深曜石黑 (Deep Obsidian)
    TEXT_MAIN = '#FFFFFF'       # 純白 (Pure White)
    TEXT_SUB = '#A0A0A0'        # 銀灰 (Silver Grey)
    ACCENT_COLOR = '#FF5500'    # 高飽和亮橘/燈管橘 (Neon Orange)
    
    img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ==========================
    # 增加質感與圖騰 (Texture & Totems)
    # ==========================
    # 1. 繪製低調的網格底圖 (Grid Pattern)
    for x in range(0, WIDTH, 90):
        draw.line([(x, 0), (x, HEIGHT)], fill="#141414", width=1)
    for y in range(0, HEIGHT, 90):
        draw.line([(0, y), (WIDTH, y)], fill="#141414", width=1)

    # 2. 繪製四角對位標記 (Crosshairs / Streetwear aesthetic)
    def draw_crosshair(cx, cy):
        draw.line([(cx-15, cy), (cx+15, cy)], fill=ACCENT_COLOR, width=2)
        draw.line([(cx, cy-15), (cx, cy+15)], fill=ACCENT_COLOR, width=2)
    
    margin_x = 90
    draw_crosshair(margin_x, 80)
    draw_crosshair(WIDTH - margin_x, 80)
    draw_crosshair(margin_x, HEIGHT - 80)
    draw_crosshair(WIDTH - margin_x, HEIGHT - 80)
    
    try:
        font_logo   = ImageFont.truetype(FONT_REGULAR, 22, index=0)
        font_title  = ImageFont.truetype(FONT_BOLD, 64, index=0)
        font_meta_h = ImageFont.truetype(FONT_BOLD, 28, index=0)
        font_meta_v = ImageFont.truetype(FONT_REGULAR, 36, index=0)
    except IOError:
        font_logo = font_title = font_meta_h = font_meta_v = ImageFont.load_default()

    # 1. Background Texture/Blur handling
    content_start_y = 500
    cover_path = download_image(event.get('image_url'))
    
    # 頂部裝飾列 (Header branding)
    # 不寫小草之聲，單純保留 SMALLSEEDSVOICE
    draw.text((margin_x + 30, 68), "SMALLSEEDSVOICE", font=font_logo, fill=TEXT_MAIN)
    draw.text((WIDTH - margin_x - 120, 68), f"VOL. {index:03d}", font=font_logo, fill=ACCENT_COLOR)
    
    # 繪製音波圖騰 (Soundwave Totem) 在右上角作為點綴
    wave_x = WIDTH - margin_x - 180
    wave_heights = [8, 16, 24, 12, 20, 10, 28, 14]
    for i, h in enumerate(wave_heights):
        draw.rectangle([wave_x + i*6, 70 + (28-h)//2, wave_x + i*6 + 3, 70 + (28-h)//2 + h], fill=ACCENT_COLOR)

    draw.line([(0, 120), (WIDTH, 120)], fill="#222222", width=1)
    
    if cover_path:
        try:
            poster = Image.open(cover_path).convert('RGB')
            # 簡約置中裁切的海報框
            target_poster_w = 900
            target_poster_h = int(target_poster_w * poster.height / poster.width)
            if target_poster_h > 650:
                target_poster_h = 650
                target_poster_w = int(target_poster_h * poster.width / poster.height)

            poster_resized = poster.resize((target_poster_w, target_poster_h), Image.Resampling.LANCZOS)
            x_offset = (WIDTH - target_poster_w) // 2
            y_offset = 180
            
            # 海報增加高飽和螢光色邊框或點綴
            draw.rectangle(
                [(x_offset-2, y_offset-2), (x_offset+target_poster_w+1, y_offset+target_poster_h+1)], 
                outline=ACCENT_COLOR, width=2
            )
            img.paste(poster_resized, (x_offset, y_offset))
            
            content_start_y = y_offset + target_poster_h + 80
        except Exception as e:
            print(f"Error drawing image: {e}")
            content_start_y = 200
    else:
        # 無圖片時的日系留白排版
        content_start_y = 350
        draw.text((WIDTH//2 - 60, 250), "NO IMAGE", font=font_meta_h, fill="#3A3A3A")

    # 2. 標題處理
    title = event.get('name', '活動名稱未定')
    wrapped_title = wrap_text(title, font_title, 900, draw)
    title_y = content_start_y
    for line in wrapped_title[:2]:
        draw.text((margin_x, title_y), line, font=font_title, fill=TEXT_MAIN)
        title_y += 85
    
    if len(wrapped_title) > 2:
        draw.text((margin_x, title_y - 20), "...", font=font_title, fill=TEXT_MAIN)
        title_y += 40

    # 3. 中段分隔線
    divider_y = title_y + 30
    draw.line([(margin_x, divider_y), (WIDTH - margin_x, divider_y)], fill="#333333", width=1)

    # 4. 日期、場地與陣容 (推論邏輯)
    info_y = divider_y + 40
    
    date_str = event.get('date', 'TBA')
    time_str = event.get('time', '')
    if time_str and time_str != "Unknown":
        date_str += f" {time_str}"
        
    raw_venue = event.get('venue_name', 'Unknown')
    final_venue = guess_venue(title, raw_venue)
    
    performers = event.get('performers', [])
    
    # 使用表格狀的嚴謹對齊方式 (Data Grid Layout)
    col1_x = margin_x
    col2_x = margin_x + 180
    
    # Date
    draw.text((col1_x, info_y), "DATE /", font=font_meta_h, fill=ACCENT_COLOR)
    draw.text((col2_x, info_y - 4), date_str, font=font_meta_v, fill=TEXT_MAIN)
    
    # Venue
    info_y += 65
    draw.text((col1_x, info_y), "VENUE /", font=font_meta_h, fill=ACCENT_COLOR)
    draw.text((col2_x, info_y - 4), final_venue, font=font_meta_v, fill=TEXT_MAIN)
    
    # Lineup
    if performers:
        info_y += 65
        perf_text = " · ".join(performers)
        if len(perf_text) > 28: perf_text = perf_text[:27] + "..."
        draw.text((col1_x, info_y), "LINEUP /", font=font_meta_h, fill=ACCENT_COLOR)
        draw.text((col2_x, info_y - 4), perf_text, font=font_meta_v, fill=TEXT_SUB)
        
    # 5. Bottom Watermark / Branding
    footer_y = HEIGHT - 80
    draw.text((margin_x + 30, footer_y - 12), "TAIWAN MUSIC CURATOR.", font=font_logo, fill=TEXT_SUB)
    draw.text((WIDTH - margin_x - 140, footer_y - 12), "EST. 2026", font=font_logo, fill=TEXT_SUB)

    # Save
    safe_title = "".join([c for c in title if c.isalnum() or c in [' ', '-']]).strip()[:20]
    out_path = os.path.join(OUTPUT_DIR, f"{index:02d}_{safe_title}.png")
    img.save(out_path, quality=95)
    print(f"Generated: {out_path}")

def main():
    ensure_dirs()
    if not os.path.exists(RADAR_FILE):
        print(f"Data file not found: {RADAR_FILE}")
        return
        
    with open(RADAR_FILE, 'r', encoding='utf-8') as f:
        events = json.load(f)
        
    print(f"Loaded {len(events)} events. Generating cards for the first 10...")
    valid_events = [e for e in events if e.get('image_url')]
    
    for i, event in enumerate(valid_events[:10]):
        generate_card(event, i+1)

if __name__ == "__main__":
    main()
