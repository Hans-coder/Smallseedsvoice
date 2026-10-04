#!/usr/bin/env python3
"""
create_social_cards.py
全台音樂活動 / 聽團小聲音 官方社群圖卡產生器 (1080x1350, 4:5 比例)
套用日系雜誌感 Japanese Paper + 復古獨立音樂 Zine 風格雙層邊框。
可為每週 Threads 串文 (Digest Posts) 與 單場焦點爆款 (Spotlight Posts) 自動生成套框圖卡。
"""

import json
import os
import argparse
from pathlib import Path
from typing import Dict, List, Optional

def build_card_html(
    card_id: str,
    event: Dict,
    source_tag: str = "",
    spotlight_quote: str = "",
    zoom_level: str = "1.0"
) -> str:
    name = event.get('name') or event.get('title') or event.get('activity_name', "演出活動")
    date = event.get('date') or event.get('time') or "近期活動"
    
    venue = event.get('venue_name') or event.get('venue') or event.get('location') or ""
    if not venue or venue in ["Unknown", "未提供", "See Details", "場地詳見活動頁"]:
        venue = "場地資訊請見官方售票頁"
    city = event.get('city', '')
    if city and city not in venue:
        venue_display = f"[{city}] {venue}"
    else:
        venue_display = venue

    # Performers
    performers = event.get('performers', [])
    if isinstance(performers, list):
        performers_str = "、".join([p.strip() for p in performers if p.strip()])
    else:
        performers_str = str(performers).strip()

    if not performers_str and "-" in name:
        performers_str = name.split("-")[0].strip()
    elif not performers_str and "｜" in name:
        performers_str = name.split("｜")[0].strip()

    performers_html = (
        f'<div class="performers">🎤 演出：{performers_str}</div>'
        if performers_str
        else '<div class="performers">🎤 演出：詳見活動頁面</div>'
    )

    # Time handling
    exact_time = event.get('start_time') or event.get('time', '')
    if exact_time in ["Unknown", "None", None]:
        exact_time = ""
    time_html = f" ｜ ⏰ {exact_time}" if exact_time else ""

    # Image handling
    bg_image = event.get('image_url') or ""
    if bg_image and bg_image.startswith('http'):
        img_html = f"""
        <div class="img-wrapper">
            <div class="bg-blur" style="background-image:url('{bg_image}')"></div>
            <img src="{bg_image}" alt="{name}" crossorigin="anonymous" />
        </div>
        """
    else:
        img_html = """
        <div class="img-wrapper no-img">
            <div class="logo-mark">SMALLSEEDS<br/>VOICE</div>
        </div>
        """

    # Badges
    badge_html = f'<div class="source-badge">{source_tag}</div>' if source_tag else ""

    # Quote
    quote_html = ""
    if spotlight_quote:
        quote_html = f'<div class="ai-desc">💬 "{spotlight_quote}"</div>'

    card = f"""
    <div class="card" id="{card_id}">
        <div class="card-inner">
            {img_html}
            <div class="content">
                <div class="meta-row">
                    <div class="date-badge">{date}</div>
                    {badge_html}
                </div>
                <div class="title">{name}</div>
                {performers_html}
                <div class="venue">📍 {venue_display}{time_html}</div>
                {quote_html}
            </div>
            <div class="footer">
                <span class="footer-brand">SMALLSEEDS VOICE</span>
                <span class="footer-sub">TAIWAN MUSIC RADAR // @smallseedsvoice</span>
            </div>
        </div>
    </div>
    """
    return card

def generate_social_cards_html(cards_data: List[Dict], zoom_level: str = "1.0") -> str:
    cards_html = "\n".join([c["html"] for c in cards_data])
    return f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>聽團小聲音 | 官方社群圖卡預覽庫</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@500;700;900&family=Space+Grotesk:wght@700;800&display=swap" rel="stylesheet">
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}
    body {{
        background: #18191f;
        margin: 0;
        padding: 40px 20px;
        display: flex;
        flex-wrap: wrap;
        gap: 40px;
        font-family: 'Noto Sans TC', -apple-system, sans-serif;
        justify-content: center;
    }}
    /* IG & Threads 4:5 Aspect Ratio (1080x1350) */
    .card {{
        width: 1080px;
        height: 1350px;
        background: #F8F5F0; /* Japanese Paper Base */
        position: relative;
        box-sizing: border-box;
        border: 2px solid #C4B9A7;
        transform-origin: top left;
        zoom: {zoom_level};
        box-shadow: 0 20px 40px rgba(0,0,0,0.5);
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
        background: #14161d;
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
    /* 前景主視覺（完整顯示，不破壞排版） */
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
        background: #1f222e;
    }}
    .logo-mark {{
        font-family: 'Space Grotesk', sans-serif;
        font-size: 72px;
        font-weight: 800;
        color: #C4B9A7;
        letter-spacing: 12px;
        text-align: center;
        opacity: 0.6;
        line-height: 1.1;
    }}
    .content {{
        padding: 46px 54px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
    }}
    .meta-row {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 24px;
    }}
    .date-badge {{
        display: inline-block;
        background: #C83220; /* Kurenai 紅 */
        color: #F8F5F0;
        font-size: 32px;
        font-weight: 900;
        padding: 8px 22px;
        letter-spacing: 1px;
    }}
    .source-badge {{
        display: inline-block;
        background: #1B4F8B; /* 琉璃藍 */
        color: #F8F5F0;
        font-size: 26px;
        font-weight: 800;
        padding: 8px 18px;
        letter-spacing: 1px;
    }}
    .title {{
        font-size: 58px;
        font-weight: 900;
        color: #2E2724; /* 深墨黑 */
        line-height: 1.25;
        word-wrap: break-word;
        margin-bottom: 20px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }}
    .performers {{
        font-size: 34px;
        font-weight: 700;
        color: #7A5B44; /* 沉穩暖木棕 */
        margin-bottom: 18px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }}
    .venue {{
        font-size: 36px;
        font-weight: 700;
        color: #1B4F8B; /* 琉璃藍 */
        margin-bottom: 24px;
    }}
    .ai-desc {{
        background: #EBE4D5;
        border-left: 8px solid #D68516; /* 山吹黃 */
        padding: 20px 26px;
        font-size: 30px;
        font-weight: 700;
        color: #5B483A;
        line-height: 1.45;
        margin-top: auto;
        margin-bottom: 16px;
    }}
    .footer {{
        position: absolute;
        bottom: 24px;
        left: 40px;
        right: 40px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 20px;
        font-weight: 800;
        color: #9A8B78;
        letter-spacing: 2px;
        opacity: 0.85;
    }}
    .footer-brand {{
        font-family: 'Space Grotesk', sans-serif;
        color: #1B4F8B;
        font-weight: 900;
        letter-spacing: 3px;
    }}
</style>
</head>
<body>
    {cards_html}

<script>
window.addEventListener('load', function() {{
    document.querySelectorAll('.img-wrapper img').forEach(function(img) {{
        function applyLayout() {{
            var w = img.naturalWidth, h = img.naturalHeight;
            if (!w || !h) return;
            if (h >= w) {{
                // 直幅主視覺：滿版填滿寬度，保留上半視覺重點
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'cover';
                img.style.objectPosition = 'center top';
                var blur = img.parentElement.querySelector('.bg-blur');
                if (blur) blur.style.opacity = '0';
            }}
        }}
        if (img.complete && img.naturalWidth) {{
            applyLayout();
        }} else {{
            img.addEventListener('load', applyLayout);
        }}
    }});
}});
</script>
</body>
</html>
"""

def generate_cards(
    source: str = 'all',
    render: bool = False,
    output_dir: str = 'web/cards',
    quality: int = 88,
    scale: float = 1.0
):
    out_dir_path = Path(output_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)

    cards_to_generate = []

    # 1. 處理每週音樂週報 (Digest Posts)
    digest_posts_file = Path("data/digest_posts.json")
    digest_posts = []
    if digest_posts_file.exists() and source in ['digest', 'all']:
        try:
            with open(digest_posts_file, 'r', encoding='utf-8') as f:
                digest_posts = json.load(f)
        except Exception as e:
            print(f"Error loading {digest_posts_file}: {e}")

    card_seq = 1
    for p_idx, post in enumerate(digest_posts):
        events = post.get('events', [])
        # 若 post 沒有 events 陣列但有 images，嘗試從 data/digest_raw.json 匹配
        if not events and post.get('images'):
            events = [{'name': f"本週精選場次 #{i+1}", 'image_url': img, 'date': '本週演出'} for i, img in enumerate(post['images'])]

        post_card_paths = []
        for e_idx, ev in enumerate(events):
            card_id = f"card-digest-{p_idx}-{e_idx}"
            file_name = f"card_{card_seq}.jpg"
            rel_card_url = f"cards/{file_name}"
            out_file_path = out_dir_path / file_name

            ev['card_url'] = rel_card_url
            post_card_paths.append(rel_card_url)

            card_html = build_card_html(
                card_id=card_id,
                event=ev,
                source_tag=ev.get('city') or ev.get('ticket_platform') or "LIVE",
                zoom_level="1.0" if render else "0.4"
            )

            cards_to_generate.append({
                "id": card_id,
                "file_name": file_name,
                "out_path": str(out_file_path),
                "html": card_html
            })
            card_seq += 1

        post['cards'] = post_card_paths

    # 2. 處理單場焦點爆款 (Spotlight Posts)
    spotlight_file = Path("data/spotlight_posts.json")
    spotlights = []
    if spotlight_file.exists() and source in ['spotlight', 'all']:
        try:
            with open(spotlight_file, 'r', encoding='utf-8') as f:
                spotlights = json.load(f)
        except Exception as e:
            print(f"Error loading {spotlight_file}: {e}")

    for s_idx, sp in enumerate(spotlights):
        ev = sp.get('event') or {}
        card_id = f"card-spotlight-{s_idx}"
        file_name = f"spotlight_{s_idx + 1}.jpg"
        rel_card_url = f"cards/{file_name}"
        out_file_path = out_dir_path / file_name

        sp['card_url'] = rel_card_url
        if ev:
            ev['card_url'] = rel_card_url

        card_html = build_card_html(
            card_id=card_id,
            event=ev or {'name': sp.get('title'), 'image_url': (sp.get('images') or [''])[0]},
            source_tag="🔥 SPOTLIGHT",
            spotlight_quote="現場音浪與精采卡司不容錯過",
            zoom_level="1.0" if render else "0.4"
        )

        cards_to_generate.append({
            "id": card_id,
            "file_name": file_name,
            "out_path": str(out_file_path),
            "html": card_html
        })

    if not cards_to_generate:
        print("沒有找到需要產生社群圖卡的活動場次。")
        return

    # 輸出預覽 HTML 頁面
    html_preview_path = out_dir_path / "social_cards.html"
    full_html = generate_social_cards_html(cards_to_generate, zoom_level="1.0" if render else "0.4")
    with open(html_preview_path, 'w', encoding='utf-8') as f:
        f.write(full_html)
    print(f"✅ 已輸出社群圖卡 HTML 預覽: {html_preview_path} (共 {len(cards_to_generate)} 張)")

    # 渲染為實際 JPG 圖片 (Playwright)
    if render:
        try:
            from playwright.sync_api import sync_playwright
            import urllib.parse
            print(f"📸 正在使用 Playwright 渲染 {len(cards_to_generate)} 張 4:5 官方社群圖卡...")
            
            with sync_playwright() as p:
                browser = p.chromium.launch()
                page = browser.new_page(
                    viewport={"width": 1280, "height": 1800},
                    device_scale_factor=scale
                )
                abs_path = os.path.abspath(str(html_preview_path))
                file_url = 'file://' + urllib.parse.quote(abs_path)
                page.goto(file_url, wait_until='networkidle')
                page.wait_for_timeout(2000)

                for item in cards_to_generate:
                    loc = page.locator(f"#{item['id']}")
                    if loc.count() > 0:
                        try:
                            loc.screenshot(
                                path=item['out_path'],
                                type="jpeg",
                                quality=quality,
                                timeout=6000,
                                animations="disabled"
                            )
                            print(f"   -> 產生成功: {item['file_name']}")
                        except Exception as e:
                            print(f"   -> 警告: {item['file_name']} 截圖逾時，使用備用截圖: {e}")
                            loc.screenshot(
                                path=item['out_path'],
                                type="jpeg",
                                quality=quality,
                                timeout=3000,
                                scroll_into_view=False,
                                animations="disabled"
                            )
                browser.close()
                print(f"🎉 成功完成全部 {len(cards_to_generate)} 張社群圖卡生成！輸出目錄: {output_dir}")
        except Exception as e:
            print(f"Playwright 渲染過程發生錯誤: {e}")

    # 同步更新 JSON 資料庫以供行動後台與 Web 調用
    if digest_posts:
        with open("data/digest_posts.json", "w", encoding="utf-8") as f:
            json.dump(digest_posts, f, ensure_ascii=False, indent=2)
        web_digest_path = Path("web/data/digest_posts.json")
        if web_digest_path.parent.exists():
            with open(web_digest_path, "w", encoding="utf-8") as f:
                json.dump(digest_posts, f, ensure_ascii=False, indent=2)

    if spotlights:
        with open("data/spotlight_posts.json", "w", encoding="utf-8") as f:
            json.dump(spotlights, f, ensure_ascii=False, indent=2)
        web_spotlight_path = Path("web/data/spotlight_posts.json")
        if web_spotlight_path.parent.exists():
            with open(web_spotlight_path, "w", encoding="utf-8") as f:
                json.dump(spotlights, f, ensure_ascii=False, indent=2)

    print("✅ 已同步更新 post 資料庫中的 card_url 關聯。")

def main():
    parser = argparse.ArgumentParser(description="Generate Social Media Cards for Taiwan Music Events")
    parser.add_argument('--source', type=str, choices=['digest', 'spotlight', 'all', 'radar', 'sale'], default='all', help='Source data to use')
    parser.add_argument('--render', action='store_true', help='Render HTML to JPG using Playwright')
    parser.add_argument('--output-dir', type=str, default='web/cards', help='Output directory for JPG cards')
    parser.add_argument('--quality', type=int, default=88, help='JPEG quality (default 88)')
    parser.add_argument('--scale', type=float, default=1.0, help='Device scale factor (default 1.0 = 1080x1350)')
    args = parser.parse_args()

    generate_cards(
        source=args.source,
        render=args.render,
        output_dir=args.output_dir,
        quality=args.quality,
        scale=args.scale
    )

if __name__ == "__main__":
    main()
