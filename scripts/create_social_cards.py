import json
import os
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="Generate Social Media Cards for Events")
    parser.add_argument('--source', type=str, choices=['radar', 'digest'], default='digest', help='Source data to use')
    args = parser.parse_args()

    # Load Data
    data_file = f"data/radar_events.json" if args.source == 'radar' else f"data/digest_raw.json"
    if not os.path.exists(data_file):
        print(f"File not found: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        events = json.load(f)

    if not events:
        print("No events found to generate cards.")
        return

    # Generate cards for all events
    # events = events[:6]

    # Generate HTML
    html_cards = ""
    for e in events:
        name = e.get('name') or e.get('activity_name', "Unknown Event")
        date = e.get('date') or e.get('time', "TBA")
        venue = e.get('venue_name') or e.get('venue') or e.get('location', "場地未定")
        
        # Spotlight Description if available
        ai_desc = ""
        if e.get('spotlight'):
            desc = e['spotlight'].get('description', '')
            if desc:
                ai_desc = f'<div class="ai-desc">💬 "{desc}"</div>'
        
        # Image handling
        bg_image = e.get('image_url')
        img_html = ""
        if bg_image:
             img_html = f'<div class="img-wrapper"><img src="{bg_image}" alt="{name}"/></div>'
        else:
             img_html = f'<div class="img-wrapper no-img"><div class="logo-mark">SMALLSEEDS<br/>VOICE</div></div>'

        card = f"""
        <div class="card">
            <div class="card-inner">
                {img_html}
                <div class="content">
                    <div class="date-badge">{date}</div>
                    <div class="title">{name}</div>
                    <div class="venue">📍 {venue}</div>
                    {ai_desc}
                </div>
                <div class="footer">
                    TAIWAN MUSIC RADAR // smallseedsvoice 
                </div>
            </div>
        </div>
        """
        html_cards += card

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
            zoom: 0.4; /* Scale for browser viewing */
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
            background: #E4DDD0;
        }}
        .img-wrapper img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            filter: grayscale(20%) contrast(1.1);
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
        .date-badge {{
            display: inline-block;
            background: #C83220; /* Kurenai Red */
            color: #F8F5F0;
            font-size: 36px;
            font-weight: 900;
            padding: 10px 24px;
            align-self: flex-start;
            margin-bottom: 30px;
        }}
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
            right: 40px;
            font-size: 24px;
            font-weight: 900;
            color: #9A8B78;
            letter-spacing: 4px;
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

if __name__ == "__main__":
    main()
