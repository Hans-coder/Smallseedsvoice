"""
Preview Generator
Reads: data/official_events.json, data/radar_events.json, data/digest_posts.json
Outputs: preview.html
"""
import json
import os
import hashlib
import requests
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger("preview_generator")

CACHE_DIR = "data/preview_cache"
OFFICIAL_FILE = "data/official_events.json"
RADAR_FILE = "data/radar_events.json"
DIGEST_FILE = "data/digest_posts.json"

def ensure_cache_dir():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(exist_ok=True)

def download_image(url: str) -> str:
    """Download image and return local path (relative to preview.html)."""
    if not url:
        return "https://placehold.co/600x400?text=No+Image"
        
    try:
        # Avoid local paths from ThreadsPoster logic if any
        if not url.startswith('http'):
            return url

        # Hash URL for filename
        ext = url.split('.')[-1].split('?')[0]
        if len(ext) > 4 or not ext:
            ext = "jpg"
        
        filename = hashlib.md5(url.encode('utf-8')).hexdigest() + f".{ext}"
        local_path = os.path.join(CACHE_DIR, filename)
        
        if os.path.exists(local_path):
            return local_path
            
        # Download
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
        else:
            logger.warning(f"Failed to download {url}: Status {resp.status_code}")
            return url # Return original URL as fallback
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
        return url

def generate_html(official, radar, digest):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Manual Posting Guide</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; padding: 20px; max-width: 1200px; margin: 0 auto; }
            h1 { text-align: center; color: #1a1a1a; margin-bottom: 40px; }
            h2 { color: #444; border-bottom: 2px solid #333; padding-bottom: 10px; margin-top: 50px; background: #fff; padding: 15px; border-radius: 8px 8px 0 0; margin-bottom: 0; }
            .section { background: white; padding: 20px; border-radius: 0 0 8px 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); margin-bottom: 30px; }
            .post-container { border: 1px solid #ddd; border-radius: 12px; margin-bottom: 30px; overflow: hidden; background: #fff; }
            .post-header { background: #f8f9fa; padding: 15px; border-bottom: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
            .post-body { padding: 20px; }
            .post-text { background: #fff; border: 1px solid #eee; padding: 15px; border-radius: 8px; white-space: pre-wrap; font-family: inherit; margin-bottom: 20px; position: relative; }
            .copy-btn { background: #000; color: #fff; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-size: 14px; transition: opacity 0.2s; }
            .copy-btn:hover { opacity: 0.8; }
            .copy-btn.copied { background: #28a745; }
            .image-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 15px; margin-top: 15px; }
            .image-item { border-radius: 8px; overflow: hidden; border: 1px solid #eee; position: relative; cursor: pointer; }
            .image-item img { width: 100%; height: 150px; object-fit: cover; transition: transform 0.2s; }
            .image-item:hover img { transform: scale(1.05); }
            .image-url { font-size: 11px; color: #666; word-break: break-all; padding: 5px; background: rgba(255,255,255,0.9); position: absolute; bottom: 0; width: 100%; box-sizing: border-box; }
            
            .event-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px; margin-top: 20px; }
            .card { background: white; border: 1px solid #eee; border-radius: 12px; overflow: hidden; transition: transform 0.2s; }
            .card:hover { transform: translateY(-5px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
            .card-img { width: 100%; height: 180px; object-fit: cover; background: #f0f0f0; }
            .card-content { padding: 15px; }
            .tag { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; margin-bottom: 8px; }
            .tag-official { background: #e3f2fd; color: #1565c0; }
            .tag-radar { background: #f3e5f5; color: #7b1fa2; }
            .title { font-size: 15px; font-weight: bold; margin: 0 0 8px 0; line-height: 1.4; color: #1a1a1a; }
            .info { font-size: 13px; color: #555; margin-bottom: 4px; }
            .link-btn { display: inline-block; margin-top: 10px; color: #0066cc; text-decoration: none; font-size: 13px; }
            .link-btn:hover { text-decoration: underline; }
            
            #toast { position: fixed; bottom: 30px; left: 50%; transform: translateX(-50%); background: #333; color: #fff; padding: 12px 24px; border-radius: 30px; display: none; z-index: 1000; box-shadow: 0 4px 12px rgba(0,0,0,0.2); }
        </style>
        <script>
            function copyText(btn, text) {
                navigator.clipboard.writeText(text).then(() => {
                    const originalText = btn.innerText;
                    btn.innerText = 'Copied!';
                    btn.classList.add('copied');
                    showToast('Text copied to clipboard');
                    setTimeout(() => {
                        btn.innerText = originalText;
                        btn.classList.remove('copied');
                    }, 2000);
                });
            }
            function showToast(msg) {
                const toast = document.getElementById('toast');
                toast.innerText = msg;
                toast.style.display = 'block';
                setTimeout(() => { toast.style.display = 'none'; }, 2000);
            }
            function openImage(url) {
                window.open(url, '_blank');
            }
        </script>
    </head>
    <body>
        <h1>Manual Posting Guide ✍️</h1>
        <div id="toast"></div>
    """
    
    # 1. Weekly Digest Section
    if digest:
        html += "<h2>Weekly Digest Posts (本週懶人包)</h2><div class='section'>"
        for idx, post in enumerate(digest):
            post_id = f"digest-{idx}"
            display_text = post['text']
            
            html += f"""
            <div class="post-container">
                <div class="post-header">
                    <strong>Post #{idx + 1}</strong>
                    <button class="copy-btn" onclick="copyText(this, `{display_text.replace('`','\\`')}`)">Copy Text</button>
                </div>
                <div class="post-body">
                    <div class="post-text" id="{post_id}">{display_text}</div>
                    <strong>Images ({len(post['images'])}):</strong>
                    <div class="image-grid">
            """
            for img_url in post['images']:
                local_img = download_image(img_url)
                html += f"""
                <div class="image-item" onclick="openImage('{img_url}')">
                    <img src="{local_img}" loading="lazy">
                    <div class="image-url">{img_url}</div>
                </div>
                """
            html += "</div></div></div>"
        html += "</div>"

    # 2. Official Events Section
    if official:
        html += f"<h2>Official Platform Events (剩餘售票資訊)</h2><div class='section'><div class='event-grid'>"
        for e in official:
            img_src = download_image(e.get('image_url'))
            html += f"""
            <div class="card">
                <img src="{img_src}" class="card-img" loading="lazy">
                <div class="card-content">
                    <span class="tag tag-official">{e.get('ticket_platform')}</span>
                    <div class="title">{e.get('activity_name')}</div>
                    <div class="info">📅 {e.get('date')}</div>
                    <div class="info">📍 {e.get('venue_name')}</div>
                    <a href="{e.get('ticket_url')}" class="link-btn" target="_blank">View Site ↗</a>
                </div>
            </div>
            """
        html += "</div></div>"

    # 3. Radar Events Section
    if radar:
        html += f"<h2>Radar Events (最新探索)</h2><div class='section'><div class='event-grid'>"
        for e in radar:
            img_src = download_image(e.get('image_url'))
            html += f"""
            <div class="card">
                <img src="{img_src}" class="card-img" loading="lazy">
                <div class="card-content">
                    <span class="tag tag-radar">{e.get('venue')}</span>
                    <div class="title">{e.get('activity_name')}</div>
                    <div class="info">📅 {e.get('date')}</div>
                    <div class="info">💰 {e.get('is_free')}</div>
                    <a href="{e.get('source')}" class="link-btn" target="_blank">Source Link ↗</a>
                </div>
            </div>
            """
        html += "</div></div>"
        
    if not (digest or official or radar):
        html += "<p style='text-align:center;'>No data found. Please run scrapers first.</p>"

    html += "</body></html>"
    
    with open("preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    return os.path.abspath("preview.html")

def main():
    ensure_cache_dir()
    
    official = []
    radar = []
    digest = []
    
    if os.path.exists(OFFICIAL_FILE):
        with open(OFFICIAL_FILE, 'r') as f:
            official = json.load(f)
            
    if os.path.exists(RADAR_FILE):
        with open(RADAR_FILE, 'r') as f:
            radar = json.load(f)

    if os.path.exists(DIGEST_FILE):
        with open(DIGEST_FILE, 'r') as f:
            digest = json.load(f)
            
    logger.info(f"Generating guide for {len(digest)} digest posts, {len(official)} official events, and {len(radar)} radar events...")
    path = generate_html(official, radar, digest)
    logger.info(f"Guide generated at: {path}")
    print(f"Guide generated: {path}")

if __name__ == "__main__":
    main()

