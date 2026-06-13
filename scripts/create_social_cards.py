import json
import os
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Generate Social Media Cards for Events")
    parser.add_argument('--source', type=str, choices=['radar', 'digest', 'sale'], default='digest', help='Source data to use')
    parser.add_argument('--render', action='store_true', help='Render HTML to JPG using Playwright')
    args = parser.parse_args()

    # Load Data
    data_file = f"data/radar_events.json" if args.source == 'radar' else (f"data/sale_events.json" if args.source == 'sale' else f"data/digest_raw.json")
    if not os.path.exists(data_file):
        print(f"File not found: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        events = json.load(f)

    if not events:
        print("No events found to generate cards.")
        return

    # Radar: no date filtering (already limited to 12 items upstream)
    # Sale: no date filtering here either
    # Filter by date range for digest to align with run_weekly_digest.py
    if args.source == 'digest':
        import datetime
        from dateutil import parser as date_parser
        start_date = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + datetime.timedelta(days=3, hours=23, minutes=59, seconds=59)
        
        filtered = []
        for e in events:
            date_str = e.get('date') or e.get('time')
            if not date_str or date_str == "Unknown":
                continue
            try:
                dt = date_parser.parse(date_str)
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                if start_date <= dt <= end_date:
                    filtered.append(e)
            except:
                continue
        filtered.sort(key=lambda x: x.get('date', ''))
        events = filtered

    if not events:
        print("No events left after date filtering to generate cards.")
        return

    # Generate cards for all events
    # events = events[:6]

    # Generate HTML
    html_cards = ""
    for e in events:
        name = e.get('name') or e.get('activity_name', "Unknown Event")
        date = e.get('date')
        if not date or date == "Unknown":
            date = e.get('time')
        if not date or date == "Unknown":
            date = "TBA"

        venue = e.get('venue_name') or e.get('venue') or e.get('location')
        if not venue or venue in ["Unknown", "未提供", "See Details", "場地詳見活動頁"]:
            venue = "場地資訊請見官網"
        
        # Spotlight Description if available
        ai_desc = ""
        if e.get('spotlight'):
            desc = e['spotlight'].get('description', '')
            if desc:
                ai_desc = f'<div class="ai-desc">💬 "{desc}"</div>'
        
        # Performers handling
        performers = e.get('performers', [])
        performers_str = ", ".join(performers) if isinstance(performers, list) else str(performers)
        # Fallback: if no performers, maybe the first part of the name before a dash is the performer
        if not performers_str and "-" in name:
            performers_str = name.split("-")[0].strip()
        elif not performers_str and "｜" in name:
            performers_str = name.split("｜")[0].strip()
            
        performers_html = f'<div class="performers">🎤 演出：{performers_str}</div>' if performers_str else '<div class="performers">🎤 演出：詳見活動頁面</div>'
        
        # Platform handling (Removed as per user request)
        platform_html = ''
        
        # Detail link handling (Removed as per user request)
        detail_html = ''

        # Time handling
        exact_time = e.get('time', '')
        if exact_time == "Unknown" or exact_time is None:
            exact_time = ""
        time_html = f" ｜ ⏰ {exact_time}" if exact_time else ""

        # Image handling
        bg_image = e.get('image_url')
        img_html = ""
        if bg_image:
             img_html = (
                 f'<div class="img-wrapper">'
                 f'<div class="bg-blur" style="background-image:url(\'{bg_image}\')"></div>'
                 f'<img src="{bg_image}" alt="{name}"/>'
                 f'</div>'
             )
        else:
             img_html = f'<div class="img-wrapper no-img"><div class="logo-mark">SMALLSEEDS<br/>VOICE</div></div>'

        # Source badge (for radar cards)
        source_badge = ""
        if args.source == 'radar':
            source_label = e.get('source', '')
            if source_label:
                source_badge = f'<div class="source-badge">{source_label}</div>'

        card = f"""
        <div class="card">
            <div class="card-inner">
                {img_html}
                <div class="content">
                    <div class="meta-row">
                        <div class="date-badge">{date}</div>
                        {source_badge if args.source == 'radar' else platform_html}
                    </div>
                    <div class="title">{name}</div>
                    {performers_html}
                    <div class="venue">📍 {venue}{time_html}</div>
                    {ai_desc}
                </div>
                <div class="footer">
                    TAIWAN MUSIC RADAR // smallseedsvoice 
                </div>
                {detail_html}
            </div>
        </div>
        """
        html_cards += card

    zoom_level = "1.0" if args.render else "0.4"
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh-TW">
    <head>
    <meta charset="UTF-8">
    <title>Social Media Cards</title>
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;700;900&display=swap" rel="stylesheet">
    <style>
        body {{
            background: #2C2C2C;
            margin: 0;
            padding: 40px;
            display: flex;
            flex-wrap: wrap;
            gap: 40px;
            font-family: 'Noto Sans TC', sans-serif;
            justify-content: center;
        }}
        /* IG Post Frame (1080x1350 scaled down for preview, 4:5 ratio) */
        .card {{
            width: 1080px;
            height: 1350px;
            background: #F8F5F0; /* Japanese Paper Base */
            position: relative;
            box-sizing: border-box;
            border: 2px solid #C4B9A7;
            transform-origin: top left;
            zoom: {zoom_level}; /* Scale for browser viewing or full for rendering */
            box-shadow: 0 20px 40px rgba(0,0,0,0.4);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        .card-inner {{
            border: 3px solid #EBE4D5;
            margin: 24px;
            height: calc(100% - 48px);
            position: relative;
            display: flex;
            flex-direction: column;
        }}
        .img-wrapper {{
            width: 100%;
            height: 700px;
            overflow: hidden;
            border-bottom: 4px solid #1B4F8B;
            background: #1a1a1a;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        /* 模糊背景層（放大的相同圖片） */
        .img-wrapper .bg-blur {{
            position: absolute;
            inset: -30px;
            background-size: cover;
            background-position: center;
            filter: blur(24px) brightness(0.55) saturate(1.4);
            transform: scale(1.1);
        }}
        /* 前景主圖（完整顯示，不切版） */
        .img-wrapper img {{
            position: relative;
            z-index: 1;
            max-width: 100%;
            max-height: 700px;
            width: auto;
            height: auto;
            object-fit: contain;
            display: block;
        }}
        .no-img {{
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .logo-mark {{
            font-size: 80px;
            font-weight: 900;
            color: #C4B9A7;
            letter-spacing: 15px;
            text-align: center;
            opacity: 0.5;
        }}
        .content {{
            padding: 50px 60px;
            display: flex;
            flex-direction: column;
            flex-grow: 1;
        }}
        .meta-row {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 30px;
        }}
        .date-badge {{
            display: inline-block;
            background: #C83220; /* Kurenai Red */
            color: #F8F5F0;
            font-size: 36px;
            font-weight: 900;
            padding: 10px 24px;
        }}
        .platform-badge {{ display: none; }}
        .title {{
            font-size: 64px;
            font-weight: 900;
            color: #2E2724; /* Dark Ink */
            line-height: 1.2;
            word-wrap: break-word;
            margin-bottom: 24px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        .venue {{
            font-size: 38px;
            font-weight: 700;
            color: #1B4F8B; /* Ruri Blue */
            margin-bottom: 40px;
        }}
        .performers {{
            font-size: 34px;
            font-weight: 700;
            color: #7A5B44; /* Muted brown */
            margin-bottom: 24px;
        }}
        .ai-desc {{
            background: #EBE4D5;
            border-left: 8px solid #D68516; /* Yamabuki */
            padding: 24px 30px;
            font-size: 34px;
            font-weight: 700;
            color: #5B483A;
            line-height: 1.5;
            margin-top: auto;
            margin-bottom: 20px;
        }}
        .footer {{
            position: absolute;
            bottom: 30px;
            left: 40px;
            font-size: 20px;
            font-weight: 900;
            color: #9A8B78;
            letter-spacing: 4px;
            opacity: 0.7;
        }}
        .platform-tag {{ display: none; }}
        .detail-link {{ display: none; }}
        .source-badge {{
            display: inline-block;
            background: #1B4F8B;
            color: #F8F5F0;
            font-size: 28px;
            font-weight: 900;
            padding: 10px 20px;
            letter-spacing: 2px;
        }}
    </style>
    </head>
    <body>
        {html_cards}
    </body>
    </html>
    """

    out_path = "artifacts/social_cards.html"
    os.makedirs("artifacts", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_template)
    print(f"✅ Generated {len(events)} fixed-design event cards.")
    print(f"👉 Open {out_path} in your browser and screenshot them for 1080x1350 (4:5) Instagram/Threads posts!")
    
    if args.render:
        from playwright.sync_api import sync_playwright
        import urllib.parse
        print("📸 Rendering images with Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(device_scale_factor=2)
            
            abs_path = os.path.abspath(out_path)
            file_url = 'file://' + urllib.parse.quote(abs_path)
            
            page.goto(file_url, wait_until='networkidle')
            # Add a tiny wait for image loads and animations
            page.wait_for_timeout(1000)
            
            cards = page.locator('.card').all()
            print(f"🔍 Found {len(cards)} card elements in the DOM.")
            for i, card in enumerate(cards, 1):
                img_path = f"artifacts/card_{i}.jpg"
                try:
                    # Use a 5s timeout and disable animations for stability
                    card.screenshot(path=img_path, type="jpeg", quality=95, timeout=5000, animations="disabled")
                    print(f"   -> Saved {img_path}")
                except Exception as e:
                    print(f"   -> Warning: Failed to screenshot card {i} (timed out/error): {e}")
                    # Fallback with scroll_into_view=False to avoid scroll wait issues
                    try:
                        card.screenshot(path=img_path, type="jpeg", quality=95, timeout=2000, scroll_into_view=False, animations="disabled")
                        print(f"   -> Saved {img_path} (fallback)")
                    except Exception as e2:
                        print(f"   -> Error: Fallback also failed for card {i}: {e2}")
            browser.close()
            print(f"✅ Rendered {len(cards)} JPG images.")

if __name__ == "__main__":
    main()
