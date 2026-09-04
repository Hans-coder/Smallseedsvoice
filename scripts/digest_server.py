"""
digest_server.py (進階版)
本地預覽與編輯伺服器：在發布到 Threads 之前，用手機或電腦瀏覽器預覽、自由編輯每篇貼文與圖片，
支援單篇複製、新增/刪除篇數、自動存草稿、確認後一鍵排程發布到 Threads。

用法：
  python scripts/digest_server.py
  手機/電腦開啟 http://[你的電腦IP]:5055（同 WiFi）
  或 http://localhost:5055（本機）
"""
import os
import sys
import json
import time
import socket
from pathlib import Path
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from flask import Flask, request, jsonify
except ImportError:
    print("安裝 Flask 中...")
    os.system(f"{sys.executable} -m pip install flask")
    from flask import Flask, request, jsonify

app = Flask(__name__)
PORT = 5055
POSTS_FILE = Path("data/digest_posts.json")
DRAFT_FILE = Path("data/digest_draft.json")


def load_posts() -> list:
    """優先載入本地草稿，若無草稿則載入原始 digest_posts.json"""
    for f in [DRAFT_FILE, POSTS_FILE]:
        if f.exists():
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, list) and data:
                    return data
            except Exception:
                pass
    return []


def save_draft(posts: list):
    DRAFT_FILE.parent.mkdir(exist_ok=True)
    DRAFT_FILE.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")


def reset_draft():
    if DRAFT_FILE.exists():
        DRAFT_FILE.unlink()


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def post_to_threads(posts: list) -> dict:
    """透過 ThreadsPoster 發布所有貼文"""
    token = os.getenv("THREADS_ACCESS_TOKEN")
    if not token:
        return {"ok": False, "error": "環境變數中未設定 THREADS_ACCESS_TOKEN"}

    try:
        from src.poster.threads_poster import ThreadsPoster
        poster = ThreadsPoster(access_token=token)
        results = []
        for i, post in enumerate(posts):
            text = (post.get("text") or "").strip()
            images = post.get("images") or []
            if not text:
                results.append({"index": i + 1, "ok": False, "error": "空白貼文已跳過"})
                continue

            success = poster.post(text=text, image_urls=images)
            results.append({"index": i + 1, "ok": success})
            if i < len(posts) - 1:
                time.sleep(5)  # Threads API 呼叫安全間隔

        ok_count = sum(1 for r in results if r.get("ok"))
        return {
            "ok": ok_count > 0,
            "results": results,
            "message": f"成功發布 {ok_count}/{len(posts)} 則貼文到 Threads！",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────
# API Routes
# ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    posts = load_posts()
    has_draft = DRAFT_FILE.exists()
    source = "草稿（已編輯）" if has_draft else "原始資料"
    return HTML_PAGE.format(
        posts_json=json.dumps(posts, ensure_ascii=False),
        post_count=len(posts),
        source=source,
        generated_time=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )


@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    return jsonify(load_posts())


@app.route("/api/posts", methods=["POST"])
def api_save_posts():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list):
            return jsonify({"ok": False, "error": "資料格式錯誤"}), 400
        save_draft(data)
        return jsonify({"ok": True, "message": f"草稿已儲存（共 {len(data)} 則）"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/reset", methods=["POST"])
def api_reset():
    reset_draft()
    return jsonify({"ok": True, "message": "已還原為原始貼文資料"})


@app.route("/api/post_to_threads", methods=["POST"])
def api_post_to_threads():
    posts = load_posts()
    if not posts:
        return jsonify({"ok": False, "error": "目前沒有任何貼文內容"}), 400
    result = post_to_threads(posts)
    return jsonify(result)


@app.route("/api/status")
def api_status():
    posts = load_posts()
    has_token = bool(os.getenv("THREADS_ACCESS_TOKEN"))
    return jsonify({
        "post_count": len(posts),
        "has_draft": DRAFT_FILE.exists(),
        "has_threads_token": has_token,
        "posts_file_exists": POSTS_FILE.exists(),
    })


# ─────────────────────────────────────────────────────────────
# Advanced HTML Template
# ─────────────────────────────────────────────────────────────

HTML_PAGE = """<!DOCTYPE html>
<html lang="zh-TW">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Smallseeds Digest 貼文管理</title>
<style>
  :root {{
    --bg: #0b0e17;
    --surface: #131726;
    --surface2: #1b2034;
    --card: #191e30;
    --accent: #6366f1;
    --accent-hover: #4f46e5;
    --accent2: #818cf8;
    --green: #10b981;
    --green-bg: rgba(16, 185, 129, 0.15);
    --red: #f43f5e;
    --red-bg: rgba(244, 63, 94, 0.15);
    --yellow: #f59e0b;
    --yellow-bg: rgba(245, 158, 11, 0.15);
    --text: #f1f5f9;
    --muted: #94a3b8;
    --border: #262c45;
    --radius: 12px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: var(--bg);
    color: var(--text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    min-height: 100vh;
    padding-bottom: 110px;
    -webkit-font-smoothing: antialiased;
  }}

  /* Header */
  .header {{
    background: linear-gradient(135deg, #1e1b4b 0%, #172554 100%);
    padding: 16px;
    position: sticky; top: 0; z-index: 100;
    box-shadow: 0 4px 20px rgba(0,0,0,0.5);
    border-bottom: 1px solid var(--border);
  }}
  .header-top {{ display: flex; align-items: center; justify-content: space-between; }}
  .header h1 {{ font-size: 1.15rem; font-weight: 700; }}
  .header .meta {{ font-size: 0.72rem; color: var(--accent2); margin-top: 4px; }}
  .badge {{
    background: var(--accent); color: white;
    font-size: 0.72rem; font-weight: 600;
    padding: 3px 10px; border-radius: 20px;
  }}

  /* Status Bar */
  .status-bar {{
    display: flex; gap: 8px; flex-wrap: wrap;
    padding: 10px 16px;
    background: var(--surface);
    border-bottom: 1px solid var(--border);
  }}
  .chip {{
    font-size: 0.72rem; padding: 4px 10px;
    border-radius: 20px; font-weight: 500;
    background: var(--surface2); color: var(--muted);
  }}
  .chip.ok {{ background: var(--green-bg); color: var(--green); }}
  .chip.warn {{ background: var(--yellow-bg); color: var(--yellow); }}

  /* Posts Container */
  .posts-container {{
    padding: 14px 16px;
    display: flex; flex-direction: column; gap: 16px;
    max-width: 800px; margin: 0 auto;
  }}

  /* Post Card */
  .post-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    overflow: hidden;
    transition: transform 0.15s, border-color 0.2s;
  }}
  .post-card:focus-within {{
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
  }}

  .card-top {{
    display: flex; align-items: center; justify-content: space-between;
    padding: 10px 14px;
    background: var(--surface2);
    border-bottom: 1px solid var(--border);
  }}
  .post-tag {{
    font-size: 0.75rem; font-weight: 700;
    color: var(--accent2);
    background: rgba(99, 102, 241, 0.15);
    padding: 3px 8px; border-radius: 6px;
  }}
  .card-actions {{ display: flex; align-items: center; gap: 6px; }}
  
  .btn-icon {{
    background: transparent; border: 1px solid var(--border);
    color: var(--muted); padding: 4px 8px; border-radius: 6px;
    font-size: 0.72rem; cursor: pointer; transition: all 0.15s;
  }}
  .btn-icon:hover {{ color: var(--text); border-color: var(--accent); background: var(--surface); }}
  .btn-icon.del:hover {{ color: var(--red); border-color: var(--red); background: var(--red-bg); }}

  .char-meter {{
    font-size: 0.72rem; font-weight: 600;
    color: var(--muted);
  }}
  .char-meter.warn {{ color: var(--yellow); }}
  .char-meter.over {{ color: var(--red); font-weight: 700; }}

  .post-textarea {{
    width: 100%; min-height: 220px;
    background: transparent; color: var(--text);
    border: none; outline: none; resize: vertical;
    padding: 14px; font-size: 0.9rem; line-height: 1.65;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  }}

  /* Images Drawer */
  .images-sec {{
    border-top: 1px solid var(--border);
    padding: 10px 14px;
    background: var(--surface2);
  }}
  .images-header {{
    display: flex; justify-content: space-between; align-items: center;
    font-size: 0.72rem; color: var(--muted); margin-bottom: 8px;
  }}
  .img-list {{
    display: flex; gap: 8px; overflow-x: auto; padding-bottom: 4px;
  }}
  .img-item {{
    position: relative; width: 72px; height: 72px; flex-shrink: 0;
    border-radius: 8px; overflow: hidden; border: 1px solid var(--border);
  }}
  .img-item img {{
    width: 100%; height: 100%; object-fit: cover;
  }}
  .img-del {{
    position: absolute; top: 2px; right: 2px;
    background: rgba(0,0,0,0.7); color: white;
    border: none; border-radius: 50%; width: 18px; height: 18px;
    font-size: 10px; cursor: pointer; display: flex; align-items: center; justify-content: center;
  }}
  .btn-add-img {{
    width: 72px; height: 72px; flex-shrink: 0;
    border: 1px dashed var(--border); border-radius: 8px;
    background: transparent; color: var(--muted);
    font-size: 0.72rem; cursor: pointer; display: flex; flex-direction: column;
    align-items: center; justify-content: center; gap: 2px;
  }}
  .btn-add-img:hover {{ border-color: var(--accent); color: var(--text); }}

  /* Add Post Button */
  .add-post-wrapper {{
    max-width: 800px; margin: 10px auto; padding: 0 16px;
    text-align: center;
  }}
  .btn-add-post {{
    width: 100%; padding: 14px;
    background: var(--surface2); border: 1px dashed var(--border);
    color: var(--muted); font-size: 0.88rem; font-weight: 600;
    border-radius: var(--radius); cursor: pointer; transition: all 0.2s;
  }}
  .btn-add-post:hover {{ border-color: var(--accent); color: var(--accent2); background: var(--surface); }}

  /* Fixed Bottom Bar */
  .bottom-bar {{
    position: fixed; bottom: 0; left: 0; right: 0;
    background: rgba(11, 14, 23, 0.95);
    backdrop-filter: blur(12px);
    border-top: 1px solid var(--border);
    padding: 12px 16px;
    display: flex; gap: 8px; z-index: 200;
    max-width: 800px; margin: 0 auto;
  }}
  .btn {{
    padding: 12px 14px; border: none; border-radius: 10px;
    font-size: 0.88rem; font-weight: 600; cursor: pointer;
    transition: all 0.15s; display: flex; align-items: center; justify-content: center; gap: 6px;
  }}
  .btn:active {{ transform: scale(0.97); }}
  .btn-subtle {{ background: var(--surface2); color: var(--text); }}
  .btn-subtle:hover {{ background: var(--surface); }}
  .btn-save {{ background: var(--accent); color: white; flex: 1; }}
  .btn-save:hover {{ background: var(--accent-hover); }}
  .btn-publish {{ background: linear-gradient(135deg, #059669 0%, #10b981 100%); color: white; flex: 1.5; }}

  /* Toast Notification */
  .toast {{
    position: fixed; top: 75px; left: 50%; transform: translateX(-50%) translateY(-20px);
    background: var(--surface2); border: 1px solid var(--border);
    color: var(--text); padding: 8px 16px; border-radius: 30px;
    font-size: 0.82rem; font-weight: 500;
    opacity: 0; transition: all 0.25s; pointer-events: none;
    z-index: 999; box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  }}
  .toast.show {{ opacity: 1; transform: translateX(-50%) translateY(0); }}
  .toast.ok {{ border-color: var(--green); color: var(--green); }}
  .toast.err {{ border-color: var(--red); color: var(--red); }}

  /* Modal */
  .overlay {{
    display: none; position: fixed; inset: 0;
    background: rgba(0,0,0,0.75); z-index: 300;
    align-items: center; justify-content: center; padding: 20px;
  }}
  .overlay.show {{ display: flex; }}
  .modal {{
    background: var(--card); border: 1px solid var(--border);
    border-radius: var(--radius); padding: 20px; max-width: 400px; width: 100%;
  }}
  .modal h2 {{ font-size: 1.05rem; margin-bottom: 8px; }}
  .modal p {{ font-size: 0.82rem; color: var(--muted); line-height: 1.6; margin-bottom: 18px; }}
  .modal-actions {{ display: flex; gap: 8px; justify-content: flex-end; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <h1>🎵 Smallseeds Digest 貼文管理</h1>
    <span class="badge" id="postCountBadge">{post_count} 篇</span>
  </div>
  <div class="meta">資料來源：{source} ｜ 更新時間：{generated_time}</div>
</div>

<div class="status-bar">
  <span class="chip" id="chipToken">⏳ 檢查 Threads 金鑰...</span>
  <span class="chip" id="chipDraft">⏳ 檢查草稿...</span>
</div>

<div class="posts-container" id="postsContainer"></div>

<div class="add-post-wrapper">
  <button class="btn-add-post" onclick="addNewPost()">➕ 新增一則貼文區塊</button>
</div>

<div class="bottom-bar">
  <button class="btn btn-subtle" onclick="resetToOriginal()" title="丟棄所有編輯，還原為原始資料">↩ 還原</button>
  <button class="btn btn-save" onclick="saveDraftManual()">💾 儲存草稿</button>
  <button class="btn btn-publish" onclick="openPublishModal()">🚀 發布 Threads</button>
</div>

<div class="toast" id="toast"></div>

<!-- 發布確認 Modal -->
<div class="overlay" id="publishModal">
  <div class="modal">
    <h2>確認發布到 Threads？</h2>
    <p id="publishDesc">即將把編輯後的貼文發布至 Threads。每篇貼文間隔 5 秒以符合 API 限制。</p>
    <div class="modal-actions">
      <button class="btn btn-subtle" onclick="closePublishModal()">取消</button>
      <button class="btn btn-publish" onclick="executePublish()">確認發布</button>
    </div>
  </div>
</div>

<script>
let posts = {posts_json};
let autoSaveTimeout = null;

function render() {{
  const container = document.getElementById('postsContainer');
  container.innerHTML = '';
  document.getElementById('postCountBadge').textContent = posts.length + ' 篇';

  if (!posts || posts.length === 0) {{
    container.innerHTML = '<div style="text-align:center;padding:50px 0;color:var(--muted)">暫無貼文<br><small>可點選下方「新增一則貼文區塊」手動建立</small></div>';
    return;
  }}

  posts.forEach((post, idx) => {{
    const text = post.text || '';
    const images = post.images || [];
    const len = text.length;
    let meterClass = '';
    if (len > 500) meterClass = 'over';
    else if (len > 450) meterClass = 'warn';

    const card = document.createElement('div');
    card.className = 'post-card';
    card.id = 'card-' + idx;

    const imgItemsHtml = images.map((img, imgIdx) => `
      <div class="img-item">
        <img src="${{img}}" loading="lazy" onerror="this.src='https://placehold.co/100?text=Error'"/>
        <button class="img-del" onclick="removeImage(${{idx}}, ${{imgIdx}})" title="刪除圖片">×</button>
      </div>
    `).join('');

    card.innerHTML = `
      <div class="card-top">
        <div style="display:flex;align-items:center;gap:8px;">
          <span class="post-tag">No.${{idx + 1}}</span>
          <span class="char-meter ${{meterClass}}" id="meter-${{idx}}">${{len}} / 500 字</span>
        </div>
        <div class="card-actions">
          <button class="btn-icon" onclick="copyPostText(${{idx}})" title="複製整篇文字">📋 複製</button>
          <button class="btn-icon del" onclick="deletePost(${{idx}})" title="刪除此篇">🗑 刪除</button>
        </div>
      </div>
      <textarea class="post-textarea" id="ta-${{idx}}" oninput="handleInput(${{idx}})" placeholder="輸入貼文內容...">${{escapeHtml(text)}}</textarea>
      <div class="images-sec">
        <div class="images-header">
          <span>附圖 (${{images.length}} 張)</span>
        </div>
        <div class="img-list">
          ${{imgItemsHtml}}
          <button class="btn-add-img" onclick="addImagePrompt(${{idx}})">
            <span>＋</span>
            <span>加圖片</span>
          </button>
        </div>
      </div>
    `;
    container.appendChild(card);
  }});
}}

function escapeHtml(str) {{
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}}

function handleInput(idx) {{
  const ta = document.getElementById('ta-' + idx);
  const meter = document.getElementById('meter-' + idx);
  const text = ta.value;
  posts[idx].text = text;

  const len = text.length;
  meter.textContent = len + ' / 500 字';
  meter.className = 'char-meter' + (len > 500 ? ' over' : (len > 450 ? ' warn' : ''));

  // Debounced auto-save to draft
  clearTimeout(autoSaveTimeout);
  autoSaveTimeout = setTimeout(() => {{
    saveDraftSilent();
  }}, 1500);
}}

function copyPostText(idx) {{
  const text = posts[idx].text || '';
  navigator.clipboard.writeText(text).then(() => {{
    showToast('📋 已複製第 ' + (idx + 1) + ' 篇文字', 'ok');
  }}).catch(() => {{
    showToast('複製失敗，請手動選取', 'err');
  }});
}}

function deletePost(idx) {{
  if (!confirm('確定要刪除第 ' + (idx + 1) + ' 篇嗎？')) return;
  posts.splice(idx, 1);
  render();
  saveDraftSilent();
  showToast('已刪除貼文', 'ok');
}}

function addNewPost() {{
  posts.push({{ text: '', images: [] }});
  render();
  saveDraftSilent();
  // Scroll to bottom
  window.scrollTo({{ top: document.body.scrollHeight, behavior: 'smooth' }});
}}

function removeImage(postIdx, imgIdx) {{
  posts[postIdx].images.splice(imgIdx, 1);
  render();
  saveDraftSilent();
}}

function addImagePrompt(postIdx) {{
  const url = prompt('請輸入圖片公開 URL (http/https):');
  if (url && url.trim().startsWith('http')) {{
    if (!posts[postIdx].images) posts[postIdx].images = [];
    posts[postIdx].images.push(url.trim());
    render();
    saveDraftSilent();
  }} else if (url) {{
    alert('URL 格式不正確，必須以 http:// 或 https:// 開頭');
  }}
}}

async function saveDraftSilent() {{
  try {{
    await fetch('/api/posts', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(posts),
    }});
  }} catch(e) {{}}
}}

async function saveDraftManual() {{
  try {{
    const r = await fetch('/api/posts', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(posts),
    }});
    const d = await r.json();
    showToast(d.ok ? '💾 ' + d.message : '❌ ' + d.error, d.ok ? 'ok' : 'err');
  }} catch(e) {{
    showToast('❌ 儲存失敗: ' + e, 'err');
  }}
}}

async function resetToOriginal() {{
  if (!confirm('確定放棄目前的編輯，還原為 digest_posts.json 的原始內容？')) return;
  try {{
    await fetch('/api/reset', {{ method: 'POST' }});
    const r = await fetch('/api/posts');
    posts = await r.json();
    render();
    showToast('↩ 已還原為原始貼文', 'ok');
  }} catch(e) {{
    showToast('❌ 還原失敗', 'err');
  }}
}}

function openPublishModal() {{
  // 檢查是否超過 500 字
  const overPosts = posts.filter(p => (p.text || '').length > 500);
  if (overPosts.length > 0) {{
    if (!confirm('警告：有貼文字數超過 500 字，可能被 Threads API 拒絕。仍要繼續發布嗎？')) {{
      return;
    }}
  }}
  document.getElementById('publishDesc').textContent = '即將發布共 ' + posts.length + ' 則貼文到 Threads。';
  document.getElementById('publishModal').classList.add('show');
}}

function closePublishModal() {{
  document.getElementById('publishModal').classList.remove('show');
}}

async function executePublish() {{
  closePublishModal();
  showToast('⏳ 正在逐篇發布至 Threads，請稍候...', '');
  await saveDraftSilent();

  try {{
    const r = await fetch('/api/post_to_threads', {{ method: 'POST' }});
    const d = await r.json();
    if (d.ok) {{
      showToast('🎉 ' + d.message, 'ok');
    }} else {{
      showToast('❌ 發布失敗: ' + (d.error || '未知錯誤'), 'err');
    }}
  }} catch(e) {{
    showToast('❌ 發布連線失敗: ' + e, 'err');
  }}
}}

function showToast(msg, type) {{
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'toast show ' + (type || '');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {{ el.className = 'toast'; }}, 3200);
}}

async function checkStatus() {{
  try {{
    const r = await fetch('/api/status');
    const d = await r.json();
    const chipToken = document.getElementById('chipToken');
    const chipDraft = document.getElementById('chipDraft');
    chipToken.textContent = d.has_threads_token ? '✅ Threads 金鑰正常' : '⚠️ 未設定 THREADS_ACCESS_TOKEN';
    chipToken.className = 'chip ' + (d.has_threads_token ? 'ok' : 'warn');
    chipDraft.textContent = d.has_draft ? '📝 使用草稿中' : '📄 原始資料';
    chipDraft.className = 'chip ' + (d.has_draft ? 'warn' : 'ok');
  }} catch(e) {{}}
}}

render();
checkStatus();
</script>
</body>
</html>"""


if __name__ == "__main__":
    local_ip = get_local_ip()
    posts = load_posts()
    has_token = bool(os.getenv("THREADS_ACCESS_TOKEN"))

    print("\n" + "=" * 54)
    print("  🎵  Smallseeds Digest 進階預覽與編輯伺服器")
    print("=" * 54)
    print(f"  電腦瀏覽： http://localhost:{PORT}")
    print(f"  手機瀏覽： http://{local_ip}:{PORT}  （需在同個 Wi-Fi）")
    print(f"  目前篇數： {len(posts)} 篇")
    print(f"  資料狀態： {'草稿 (data/digest_draft.json)' if DRAFT_FILE.exists() else '原始檔案 (data/digest_posts.json)'}")
    print(f"  Threads 金鑰： {'✅ 已設定' if has_token else '⚠️  未設定（僅能預覽與編輯，無法自動發布）'}")
    print("=" * 54)
    print("  隨時在網頁上編輯文字、增刪圖片，按 Ctrl+C 可停止伺服器。\n")

    app.run(host="0.0.0.0", port=PORT, debug=False)
