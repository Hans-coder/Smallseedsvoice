"""
Dashboard Generator
Reads JSON data files and generates a simple HTML dashboard.
"""
import json
import os
from datetime import datetime
from pathlib import Path

def generate_dashboard():
    print("Generating Performance Tracking Dashboard...")
    
    # Paths
    data_dir = Path("data")
    raw_path = data_dir / "digest_raw.json"
    posts_path = data_dir / "digest_posts.json"
    radar_path = data_dir / "radar_events.json"
    errors_path = data_dir / "scraping_errors.json"
    
    # Metrics
    stats = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S+08:00"),
        "raw_events_count": 0,
        "processed_posts_count": 0,
        "radar_events_count": 0,
        "platform_breakdown": {},
        "errors": []
    }
    
    # 1. Raw Events
    if raw_path.exists():
        try:
            with open(raw_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
                stats["raw_events_count"] = len(raw_data)
                
                # Platform breakdown
                for event in raw_data:
                    platform = event.get('ticket_platform') or event.get('platform') or event.get('source_account') or 'Unknown'
                    stats["platform_breakdown"][platform] = stats["platform_breakdown"].get(platform, 0) + 1
        except Exception as e:
            print(f"Error reading raw events: {e}")
            
    # 2. Processed Posts
    if posts_path.exists():
        try:
             with open(posts_path, 'r', encoding='utf-8') as f:
                 posts_data = json.load(f)
                 stats["processed_posts_count"] = len(posts_data)
        except Exception as e:
             print(f"Error reading processed posts: {e}")
             
    # 3. Radar Events
    if radar_path.exists():
        try:
            with open(radar_path, 'r', encoding='utf-8') as f:
                radar_data = json.load(f)
                stats["radar_events_count"] = len(radar_data)
        except Exception as e:
            print(f"Error reading radar events: {e}")
            
    # 4. Errors
    if errors_path.exists():
        try:
             with open(errors_path, 'r', encoding='utf-8') as f:
                 stats["errors"] = json.load(f)
        except Exception as e:
            print(f"Error reading errors log: {e}")

    # Build HTML
    html_content = f"""<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Taiwan Music Events Pipeline - Dashboard</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f6f8fa;
            color: #24292f;
            line-height: 1.5;
            padding: 40px;
            max-width: 900px;
            margin: 0 auto;
        }}
        h1 {{
            font-size: 2em;
            margin-bottom: 24px;
            padding-bottom: 8px;
            border-bottom: 1px solid #d0d7de;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: white;
            padding: 24px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            border: 1px solid #d0d7de;
        }}
        .card-title {{
            font-size: 14px;
            color: #57606a;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .card-value {{
            font-size: 32px;
            font-weight: 600;
            color: #0969da;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.12);
            border: 1px solid #d0d7de;
        }}
        th, td {{
            padding: 12px 16px;
            text-align: left;
            border-bottom: 1px solid #d0d7de;
        }}
        th {{
            background-color: #f6f8fa;
            font-weight: 600;
        }}
        .error-log {{
            background: #ffebe9;
            border: 1px solid #ff8182;
            padding: 20px;
            border-radius: 8px;
            margin-top: 30px;
        }}
        .error-title {{
            color: #cf222e;
            font-weight: 600;
            font-size: 18px;
            margin-bottom: 12px;
        }}
        pre {{
            background: white;
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            font-size: 12px;
            border: 1px solid #d0d7de;
        }}
        .footer {{
            margin-top: 40px;
            text-align: center;
            color: #57606a;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <h1>🌟 Taiwan Music Events Pipeline - Health Dashboard</h1>
    
    <div class="grid">
        <div class="card">
            <div class="card-title">Official Raw Events (All)</div>
            <div class="card-value">{stats['raw_events_count']}</div>
        </div>
        <div class="card">
            <div class="card-title">Official Ready Posts</div>
            <div class="card-value">{stats['processed_posts_count']}</div>
        </div>
        <div class="card">
            <div class="card-title">Radar Upcoming Events</div>
            <div class="card-value">{stats['radar_events_count']}</div>
        </div>
    </div>
    
    <h3>Official Platform Breakdown (Last Run)</h3>
    <table>
        <thead>
            <tr>
                <th>Platform / Source</th>
                <th>Events Extracted</th>
            </tr>
        </thead>
        <tbody>
"""
    
    for platform, count in sorted(stats['platform_breakdown'].items(), key=lambda item: item[1], reverse=True):
        html_content += f"""
            <tr>
                <td>{platform}</td>
                <td>{count}</td>
            </tr>"""

    html_content += """
        </tbody>
    </table>
"""

    if stats['errors']:
        html_content += f"""
    <div class="error-log">
        <div class="error-title">🚨 Recent Scraping Errors ({len(stats['errors'])})</div>
"""
        for err in stats['errors'][-5:]: # Show last 5
            err_time = err.get('timestamp', 'Unknown')
            err_src = err.get('scraper', 'Unknown')
            err_msg = err.get('error', '')
            html_content += f"""
        <p><strong>[{err_time}] {err_src}</strong></p>
        <pre>{err_msg}</pre>
"""
        html_content += """
    </div>
"""

    html_content += f"""
    <div class="footer">
        Generated at {stats['timestamp']}
    </div>
</body>
</html>
"""

    out_path = data_dir / "dashboard.html"
    with open(out_path, "w", encoding='utf-8') as f:
        f.write(html_content)
        
    print(f"Dashboard generated successfully at: {out_path}")

if __name__ == "__main__":
    generate_dashboard()
