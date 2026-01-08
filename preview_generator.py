"""
Preview Generator
Reads: data/official_events.json, data/radar_events.json
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

def ensure_cache_dir():
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

def download_image(url: str) -> str:
    """Download image and return local path (relative to preview.html)."""
    if not url:
        return "https://placehold.co/600x400?text=No+Image"
        
    try:
        # Hash URL for filename
        ext = url.split('.')[-1].split('?')[0]
        if len(ext) > 4 or not ext:
            ext = "jpg"
        
        filename = hashlib.md5(url.encode('utf-8')).hexdigest() + f".{ext}"
        local_path = os.path.join(CACHE_DIR, filename)
        
        if os.path.exists(local_path):
            return local_path
            
        # Download
        # Some sites block requests without User-Agent
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            with open(local_path, "wb") as f:
                f.write(resp.content)
            return local_path
        else:
            logger.warning(f"Failed to download {url}: Status {resp.status_code}")
            return "https://placehold.co/600x400?text=Error"
    except Exception as e:
        logger.warning(f"Error downloading {url}: {e}")
        return "https://placehold.co/600x400?text=Error"

def generate_html(official, radar):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Music Events Preview</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f0f2f5; padding: 20px; }
            h1 { text-align: center; color: #1a1a1a; }
            h2 { color: #444; border-bottom: 2px solid #ddd; padding-bottom: 10px; margin-top: 40px; }
            .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
            .card { background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); transition: transform 0.2s; }
            .card:hover { transform: translateY(-5px); }
            .card-img { width: 100%; height: 200px; object-fit: cover; background: #eee; }
            .card-body { padding: 15px; }
            .tag { display: inline-block; padding: 4px 8px; border-radius: 4px; font-size: 12px; font-weight: bold; margin-bottom: 8px; }
            .tag-official { background: #e3f2fd; color: #1565c0; }
            .tag-radar { background: #f3e5f5; color: #7b1fa2; }
            .title { font-size: 16px; font-weight: bold; margin: 0 0 8px 0; line-height: 1.4; }
            .info { font-size: 14px; color: #666; margin-bottom: 4px; }
            .source { font-size: 12px; color: #999; margin-top: 10px; display: block; }
            .missing-img { border: 2px solid red; }
        </style>
    </head>
    <body>
        <h1>Music Events Preview</h1>
    """
    
    # Official Section
    html += f"<h2>Official Platforms ({len(official)})</h2><div class='grid'>"
    for e in official:
        img_src = download_image(e.get('image_url'))
        img_class = "card-img" if e.get('image_url') else "card-img missing-img"
        
        html += f"""
        <div class="card">
            <img src="{img_src}" class="{img_class}" loading="lazy">
            <div class="card-body">
                <span class="tag tag-official">{e.get('ticket_platform')}</span>
                <div class="title">{e.get('activity_name')}</div>
                <div class="info">📅 {e.get('date')}</div>
                <div class="info">📍 {e.get('venue_name')}</div>
                <a href="{e.get('ticket_url')}" class="source" target="_blank">Ticket Link ↗</a>
            </div>
        </div>
        """
    html += "</div>"

    # Radar Section
    html += f"<h2>Activity Radar ({len(radar)})</h2><div class='grid'>"
    for e in radar:
        img_src = download_image(e.get('image_url'))
        img_class = "card-img" if e.get('image_url') else "card-img missing-img"
        
        html += f"""
        <div class="card">
            <img src="{img_src}" class="{img_class}" loading="lazy">
            <div class="card-body">
                <span class="tag tag-radar">{e.get('venue')}</span>
                <div class="title">{e.get('activity_name')}</div>
                <div class="info">📅 {e.get('date')}</div>
                <div class="info">💰 {e.get('is_free')}</div>
                <a href="{e.get('source')}" class="source" target="_blank">Source Link ↗</a>
            </div>
        </div>
        """
    html += "</div></body></html>"
    
    with open("preview.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    return os.path.abspath("preview.html")

def main():
    ensure_cache_dir()
    
    official = []
    radar = []
    
    if os.path.exists(OFFICIAL_FILE):
        with open(OFFICIAL_FILE, 'r') as f:
            official = json.load(f)
            
    if os.path.exists(RADAR_FILE):
        with open(RADAR_FILE, 'r') as f:
            radar = json.load(f)
            
    logger.info(f"Generating preview for {len(official)} official events and {len(radar)} radar events...")
    path = generate_html(official, radar)
    logger.info(f"Preview generated at: {path}")
    print(f"Preview generated: {path}")

if __name__ == "__main__":
    main()
