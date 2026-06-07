"""
radar_form_server.py
本地 Web 表單服務：方便在手機或電腦瀏覽器填寫雷達快訊的活動資料。

用法：
  python scripts/radar_form_server.py
  然後用手機開啟 http://[你的電腦IP]:5050
  （電腦和手機需在同一個 WiFi 網路）

功能：
  - 顯示 data/trending_concerts.json 的候選清單供參考
  - 提供表單新增 / 編輯 / 刪除 data/radar_manual.json 中的確認活動
  - 預覽最終 Threads 發文內容
"""
import sys
import os
import json
import socket
from datetime import datetime
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 載入 .env（讓 THREADS_ACCESS_TOKEN 在本地可用）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 沒有 dotenv 也無妨，可用環境變數直接設定



try:
    from flask import Flask, request, jsonify, redirect, url_for
except ImportError:
    print("Flask 未安裝，正在安裝...")
    os.system(f"{sys.executable} -m pip install flask")
    from flask import Flask, request, jsonify, redirect, url_for

app = Flask(__name__)

RADAR_MANUAL_PATH = Path("data/radar_manual.json")
TRENDING_PATH = Path("data/trending_concerts.json")


def load_radar_manual() -> list:
    if RADAR_MANUAL_PATH.exists():
        try:
            data = json.loads(RADAR_MANUAL_PATH.read_text(encoding="utf-8"))
            # 過濾掉範例記錄（含 _comment 的）
            return [e for e in data if "_comment" not in e]
        except Exception:
            return []
    return []


def save_radar_manual(entries: list):
    RADAR_MANUAL_PATH.parent.mkdir(exist_ok=True)
    RADAR_MANUAL_PATH.write_text(
        json.dumps(entries, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_trending() -> dict:
    if TRENDING_PATH.exists():
        try:
            return json.loads(TRENDING_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def format_preview_text(entries: list) -> str:
    """模擬 Threads 發文格式預覽"""
    if not entries:
        return "（尚未填入任何活動）"

    lines = ["⏰ 雷達快訊 — 近期開賣提醒", ""]
    for i, e in enumerate(entries, 1):
        name = e.get("name", "?")
        artist = f"｜{e['artist']}" if e.get("artist") else ""
        sale_date = e.get("sale_date", "?")
        sale_time = e.get("sale_time", "")
        sale_str = f"{sale_date} {sale_time}".strip()
        event_date = e.get("event_date", "")
        venue = e.get("venue", "")
        url = e.get("ticket_url", "")
        note = e.get("note", "")

        lines.append(f"🎫 {name}{artist}")
        lines.append(f"   📅 演出：{event_date}　🏟 {venue}" if event_date or venue else "")
        lines.append(f"   ⏰ 開賣：{sale_str}")
        if note:
            lines.append(f"   📝 {note}")
        lines.append(f"   🔗 {url}")
        lines.append("")

    lines.append("設好鬧鐘，祝大家搶票順利！🎉")
    return "\n".join(l for l in lines if l is not None)


# ─────────────────────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
<title>🎵 雷達快訊管理</title>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --surface2: #252836;
    --accent: #7c6af7;
    --accent2: #a78bfa;
    --green: #34d399;
    --red: #f87171;
    --yellow: #fbbf24;
    --text: #e2e8f0;
    --muted: #94a3b8;
    --border: #2d3148;
    --radius: 12px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    min-height: 100vh;
    padding: 0;
  }}
  .header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
    padding: 20px 16px 16px;
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
  }}
  .header h1 {{ font-size: 1.3rem; font-weight: 700; }}
  .header p {{ font-size: 0.75rem; color: var(--accent2); margin-top: 2px; }}
  .tabs {{
    display: flex; gap: 4px;
    background: var(--surface);
    padding: 8px;
    overflow-x: auto;
  }}
  .tab {{
    flex: 1; min-width: 80px;
    padding: 8px 6px;
    border: none; border-radius: 8px;
    background: transparent; color: var(--muted);
    font-size: 0.8rem; cursor: pointer; font-weight: 500;
    transition: all 0.2s; white-space: nowrap;
  }}
  .tab.active {{ background: var(--accent); color: white; }}
  .section {{ display: none; padding: 12px; }}
  .section.active {{ display: block; }}
  /* Cards */
  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 14px;
    margin-bottom: 10px;
  }}
  .card-title {{ font-weight: 600; font-size: 0.95rem; margin-bottom: 6px; }}
  .card-meta {{ font-size: 0.78rem; color: var(--muted); line-height: 1.6; }}
  .badge {{
    display: inline-block;
    padding: 2px 8px; border-radius: 20px;
    font-size: 0.7rem; font-weight: 600;
    margin-right: 4px; margin-bottom: 4px;
  }}
  .badge-kktix {{ background: #7c3aed33; color: #a78bfa; }}
  .badge-sv {{ background: #065f4633; color: #34d399; }}
  .badge-ptt {{ background: #7c2d1233; color: #fb923c; }}
  .badge-push {{ background: #78350f33; color: #fbbf24; }}
  /* Form */
  .form-group {{ margin-bottom: 14px; }}
  label {{ display: block; font-size: 0.8rem; color: var(--muted); margin-bottom: 4px; font-weight: 500; }}
  input, textarea, select {{
    width: 100%;
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px 12px;
    color: var(--text);
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
    -webkit-appearance: none;
  }}
  input:focus, textarea:focus {{ border-color: var(--accent); }}
  textarea {{ min-height: 60px; resize: vertical; }}
  .btn {{
    display: block; width: 100%;
    padding: 13px;
    border: none; border-radius: 10px;
    font-size: 0.95rem; font-weight: 600;
    cursor: pointer; transition: all 0.2s;
  }}
  .btn-primary {{ background: var(--accent); color: white; }}
  .btn-primary:hover {{ background: var(--accent2); }}
  .btn-danger {{ background: #7f1d1d; color: var(--red); margin-top: 6px; }}
  .btn-sm {{
    display: inline-block; width: auto;
    padding: 6px 14px; font-size: 0.8rem; border-radius: 8px;
    margin-top: 8px; margin-right: 6px;
  }}
  /* Confirmed entries */
  .entry-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 14px;
    margin-bottom: 10px;
  }}
  .entry-name {{ font-weight: 700; font-size: 1rem; margin-bottom: 6px; }}
  .entry-info {{ font-size: 0.82rem; color: var(--muted); line-height: 1.8; }}
  .entry-actions {{ display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }}
  /* Preview */
  .preview-box {{
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    font-size: 0.85rem;
    line-height: 1.7;
    white-space: pre-wrap;
    font-family: monospace;
  }}
  .empty-state {{
    text-align: center;
    color: var(--muted);
    padding: 40px 20px;
    font-size: 0.9rem;
  }}
  .alert {{
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 12px;
    font-size: 0.85rem;
  }}
  .alert-success {{ background: #064e3b33; color: var(--green); border: 1px solid #064e3b; }}
  .alert-info {{ background: #1e3a5f33; color: #93c5fd; border: 1px solid #1e3a5f; }}
  .section-title {{
    font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1px;
    color: var(--muted); font-weight: 600;
    margin-bottom: 10px; padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
  }}
  a {{ color: var(--accent2); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="header">
  <h1>🎵 雷達快訊管理</h1>
  <p>Smallseedsvoice 內部工具</p>
</div>

<div class="tabs">
  <button class="tab active" onclick="switchTab('trending')">📡 候選清單</button>
  <button class="tab" onclick="switchTab('confirmed')">✅ 已確認 ({confirmed_count})</button>
  <button class="tab" onclick="switchTab('add')">➕ 新增活動</button>
  <button class="tab" onclick="switchTab('preview')">👁 預覽發文</button>
</div>

<!-- Tab 1: 候選清單 -->
<div id="tab-trending" class="section active">
  {trending_content}
</div>

<!-- Tab 2: 已確認活動 -->
<div id="tab-confirmed" class="section">
  <p class="section-title">已確認的活動 — 將出現在 Threads 發文中</p>
  {confirmed_content}
</div>

<!-- Tab 3: 新增活動 -->
<div id="tab-add" class="section">
  <p class="section-title">手動新增活動</p>
  {add_form}
</div>

<!-- Tab 4: 預覽 -->
<div id="tab-preview" class="section">
  <p class="section-title">Threads 發文預覽</p>
  <div class="preview-box">{preview_text}</div>
  <br>
  <div id="post-result"></div>
  <button id="btn-post" class="btn btn-primary" onclick="postToThreads(false)" {has_entries}style="margin-bottom:10px">
    🚀 發文到 Threads
  </button>
  <button class="btn" onclick="postToThreads(true)" {has_entries}style="background:#252836;color:#94a3b8;margin-bottom:10px">
    👁 Dry Run（只預覽，不發出）
  </button>
  {no_token_warning}
</div>

<script>
function switchTab(name) {{
  document.querySelectorAll('.tab').forEach((t, i) => {{
    t.classList.toggle('active', ['trending','confirmed','add','preview'][i] === name);
  }});
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
}}

function deleteEntry(idx) {{
  if (!confirm('確定要刪除這筆活動嗎？')) return;
  fetch('/delete/' + idx, {{method: 'POST'}})
    .then(r => r.json())
    .then(d => {{ if (d.ok) location.reload(); }});
}}

function fillForm(data) {{
  switchTab('add');
  Object.keys(data).forEach(k => {{
    const el = document.getElementById('field-' + k);
    if (el) el.value = data[k] || '';
  }});
}}

function postToThreads(dryRun) {{
  const btn = document.getElementById('btn-post');
  const resultDiv = document.getElementById('post-result');
  const url = dryRun ? '/post/dry-run' : '/post';
  const label = dryRun ? 'Dry Run' : '發文';

  if (!dryRun && !confirm('確定要發文到 Threads 嗎？')) return;

  btn.disabled = true;
  btn.textContent = `⏳ ${{label}}中...`;
  resultDiv.innerHTML = '';

  fetch(url, {{method: 'POST'}})
    .then(r => r.json())
    .then(d => {{
      btn.disabled = false;
      btn.textContent = '🚀 發文到 Threads';
      if (d.ok) {{
        resultDiv.innerHTML = `<div class="alert alert-success">✅ ${{d.message}}</div>`;
      }} else {{
        resultDiv.innerHTML = `<div class="alert" style="background:#7f1d1d33;color:#f87171;border:1px solid #7f1d1d">❌ ${{d.error}}</div>`;
      }}
    }})
    .catch(e => {{
      btn.disabled = false;
      btn.textContent = '🚀 發文到 Threads';
      resultDiv.innerHTML = `<div class="alert" style="background:#7f1d1d33;color:#f87171;border:1px solid #7f1d1d">❌ 網路錯誤：${{e}}</div>`;
    }});
}}
</script>
</body>
</html>"""


def render_trending_section(trending: dict) -> str:
    if not trending:
        return '<div class="empty-state">⚠️ 尚未執行偵測。請先執行：<br><code>python scripts/detect_trending.py</code></div>'

    generated = trending.get("generated_at", "")[:16].replace("T", " ")
    html = [f'<div class="alert alert-info">📊 資料時間：{generated}</div>']

    # KKTIX
    kktix = trending.get("kktix_new", [])
    if kktix:
        html.append('<p class="section-title">🎫 KKTIX 最新音樂活動</p>')
        for e in kktix[:12]:
            date_str = e.get("date_display", "")
            date_label = f"　{date_str}" if date_str else ""
            fill_data = json.dumps({
                "name": e.get("name", ""),
                "ticket_url": e.get("ticket_url", ""),
                "image_url": e.get("image_url", ""),
                "platform": "KKTIX",
            }, ensure_ascii=False)
            html.append(f'''<div class="card">
              <div class="card-title">{e.get("name","")}{date_label}</div>
              <div class="card-meta">
                <span class="badge badge-kktix">KKTIX</span><br>
                <a href="{e.get("ticket_url","")}" target="_blank">🔗 查看票務（請確認正確售票日期）</a>
              </div>
              <button class="btn btn-primary btn-sm" onclick='fillForm({fill_data})'>➕ 加入確認清單</button>
            </div>''')

    # StreetVoice
    sv = trending.get("streetvoice_upcoming", [])
    if sv:
        html.append('<p class="section-title">🎸 StreetVoice 近期演出</p>')
        for e in sv[:10]:
            performers = "、".join(e.get("performers", [])[:3])
            fill_data = json.dumps({
                "name": e.get("name", ""),
                "event_date": e.get("date_display", ""),
                "venue": e.get("venue", ""),
                "ticket_url": e.get("ticket_url", ""),
                "image_url": e.get("image_url", ""),
                "platform": "StreetVoice",
            }, ensure_ascii=False)
            html.append(f'''<div class="card">
              <div class="card-title">{e.get("name","")}</div>
              <div class="card-meta">
                <span class="badge badge-sv">StreetVoice</span>
                {e.get("date_display","")} @ {e.get("venue","")}<br>
                {performers}
              </div>
              <button class="btn btn-primary btn-sm" onclick='fillForm({fill_data})'>➕ 加入確認清單</button>
            </div>''')

    # Instagram
    ig = trending.get("ig_posts", [])
    if ig:
        html.append('<p class="section-title">📸 Instagram 相關貼文</p>')
        for e in ig[:8]:
            source = e.get("source", "IG")
            caption = e.get("caption_preview", "")
            fill_data = json.dumps({
                "name": e.get("name", ""),
                "ticket_url": e.get("ticket_url", ""),
                "image_url": e.get("image_url", ""),
                "platform": source,
            }, ensure_ascii=False)
            html.append(f'''<div class="card">
              <div class="card-title">{e.get("name","")}</div>
              <div class="card-meta">
                <span class="badge badge-ptt">{source}</span>
                {e.get("date_display","")}<br>
                {f'💬 {caption[:80]}...' if caption else ''}
                <br><a href="{e.get("ticket_url","")}" target="_blank">🔗 查看貼文</a>
              </div>
              <button class="btn btn-primary btn-sm" onclick='fillForm({fill_data})'>➕ 加入確認清單</button>
            </div>''')

    return "\n".join(html)



def render_confirmed_section(entries: list) -> str:
    if not entries:
        return '<div class="empty-state">尚未確認任何活動<br>請從候選清單挑選或手動新增</div>'

    html = []
    for i, e in enumerate(entries):
        html.append(f'''<div class="entry-card">
          <div class="entry-name">🎫 {e.get("name","（未命名）")}</div>
          <div class="entry-info">
            {"🎤 " + e["artist"] + "<br>" if e.get("artist") else ""}
            {"📅 演出：" + e["event_date"] + "<br>" if e.get("event_date") else ""}
            {"🏟 " + e["venue"] + "<br>" if e.get("venue") else ""}
            ⏰ 開賣：{e.get("sale_date","?")} {e.get("sale_time","")}
            {"<br>📝 " + e["note"] if e.get("note") else ""}
            {"<br>🔗 <a href='" + e["ticket_url"] + "' target='_blank'>" + e["ticket_url"] + "</a>" if e.get("ticket_url") else ""}
          </div>
          <div class="entry-actions">
            <button class="btn btn-danger btn-sm" onclick="deleteEntry({i})">🗑 刪除</button>
          </div>
        </div>''')

    return "\n".join(html)


def render_add_form() -> str:
    return '''<form method="POST" action="/add">
      <div class="form-group">
        <label>演唱會名稱 *</label>
        <input id="field-name" name="name" required placeholder="例：五月天 突然好想你演唱會">
      </div>
      <div class="form-group">
        <label>演出者 / 樂團</label>
        <input id="field-artist" name="artist" placeholder="例：五月天">
      </div>
      <div class="form-group">
        <label>售票開賣日期 *</label>
        <input id="field-sale_date" name="sale_date" type="date" required>
      </div>
      <div class="form-group">
        <label>開賣時間</label>
        <input id="field-sale_time" name="sale_time" type="time" placeholder="例：12:00">
      </div>
      <div class="form-group">
        <label>演出日期</label>
        <input id="field-event_date" name="event_date" type="date">
      </div>
      <div class="form-group">
        <label>演出場地</label>
        <input id="field-venue" name="venue" placeholder="例：台北小巨蛋">
      </div>
      <div class="form-group">
        <label>售票連結 *</label>
        <input id="field-ticket_url" name="ticket_url" type="url" required placeholder="https://kktix.com/events/...">
      </div>
      <div class="form-group">
        <label>封面圖片網址（選填）</label>
        <input id="field-image_url" name="image_url" type="url" placeholder="https://...">
      </div>
      <div class="form-group">
        <label>平台</label>
        <select id="field-platform" name="platform">
          <option value="KKTIX">KKTIX</option>
          <option value="StreetVoice">StreetVoice</option>
          <option value="tixCraft">tixCraft</option>
          <option value="iNDIEVOX">iNDIEVOX</option>
          <option value="TicketPlus">TicketPlus</option>
          <option value="其他">其他</option>
        </select>
      </div>
      <div class="form-group">
        <label>備註（選填）</label>
        <textarea id="field-note" name="note" placeholder="例：分兩波開賣，第一波限會員"></textarea>
      </div>
      <button type="submit" class="btn btn-primary">✅ 加入確認清單</button>
    </form>'''


# ─────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────
@app.route("/")
def index():
    entries = load_radar_manual()
    trending = load_trending()
    preview = format_preview_text(entries)

    has_token = bool(os.getenv("THREADS_ACCESS_TOKEN"))
    has_entries = "" if entries else "disabled "
    no_token_warning = (
        '<div class="alert" style="background:#78350f33;color:#fbbf24;border:1px solid #78350f">'
        '⚠️ <strong>THREADS_ACCESS_TOKEN</strong> 未設定。'
        '請在 .env 中加入後重啟伺服器才能發文。</div>'
        if not has_token else ""
    )

    html = HTML_TEMPLATE.format(
        confirmed_count=len(entries),
        trending_content=render_trending_section(trending),
        confirmed_content=render_confirmed_section(entries),
        add_form=render_add_form(),
        preview_text=preview,
        has_entries=has_entries,
        no_token_warning=no_token_warning,
    )
    return html


@app.route("/add", methods=["POST"])
def add_entry():
    entries = load_radar_manual()
    new_entry = {
        "name": request.form.get("name", "").strip(),
        "artist": request.form.get("artist", "").strip(),
        "sale_date": request.form.get("sale_date", "").strip(),
        "sale_time": request.form.get("sale_time", "").strip(),
        "event_date": request.form.get("event_date", "").strip(),
        "venue": request.form.get("venue", "").strip(),
        "ticket_url": request.form.get("ticket_url", "").strip(),
        "image_url": request.form.get("image_url", "").strip(),
        "platform": request.form.get("platform", "").strip(),
        "note": request.form.get("note", "").strip(),
    }
    # Remove empty fields
    new_entry = {k: v for k, v in new_entry.items() if v}
    entries.append(new_entry)
    save_radar_manual(entries)
    return redirect("/#confirmed")


@app.route("/delete/<int:idx>", methods=["POST"])
def delete_entry(idx: int):
    entries = load_radar_manual()
    if 0 <= idx < len(entries):
        entries.pop(idx)
        save_radar_manual(entries)
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "Index out of range"}), 400


@app.route("/api/entries")
def api_entries():
    return jsonify(load_radar_manual())


@app.route("/post", methods=["POST"])
def post_to_threads():
    return _do_post(dry_run=False)


@app.route("/post/dry-run", methods=["POST"])
def post_dry_run():
    return _do_post(dry_run=True)


def _do_post(dry_run: bool):
    """直接呼叫 Threads API 發文（或 dry-run 只回傳預覽）"""
    entries = load_radar_manual()
    if not entries:
        return jsonify({"ok": False, "error": "沒有確認的活動，請先新增活動。"})

    # 引入發文邏輯（和 post_radar_manual.py 共用）
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from post_radar_manual import format_threads_posts
        posts = format_threads_posts(entries)
    except Exception as ex:
        return jsonify({"ok": False, "error": f"格式化失敗：{ex}"})

    if dry_run:
        previews = [p["text"] for p in posts]
        return jsonify({"ok": True, "message": f"Dry Run 完成，共 {len(posts)} 則貼文。", "previews": previews})

    # 正式發文
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        return jsonify({"ok": False, "error": "THREADS_ACCESS_TOKEN 未設定，無法發文。請在 .env 設定後重啟伺服器。"})

    try:
        from src.threads.threads_poster import ThreadsPoster
        poster = ThreadsPoster(access_token)
        created_ids = poster.post_thread(posts)
        if created_ids:
            # 發文成功後清空清單
            save_radar_manual([])
            return jsonify({"ok": True, "message": f"發文成功！共 {len(posts)} 則貼文已發出。已清空確認清單。", "ids": created_ids})
        else:
            return jsonify({"ok": False, "error": "發文失敗，請確認 THREADS_ACCESS_TOKEN 是否有效。"})
    except Exception as ex:
        return jsonify({"ok": False, "error": f"發文錯誤：{ex}"})


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="雷達快訊表單服務")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--host", type=str, default="0.0.0.0", help="綁定 IP（0.0.0.0 表示允許區域網路連線）")
    a = parser.parse_args()

    local_ip = get_local_ip()
    print(f"\n{'='*50}")
    print(f"🎵 雷達快訊管理介面啟動中...")
    print(f"{'='*50}")
    print(f"💻 電腦瀏覽器：http://localhost:{a.port}")
    print(f"📱 手機（同 WiFi）：http://{local_ip}:{a.port}")
    print(f"{'='*50}\n")

    app.run(host=a.host, port=a.port, debug=False)
