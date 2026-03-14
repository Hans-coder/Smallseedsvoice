# Phase 3 功能更新與使用指南

這次 Phase 3 的主軸是 **「自動化（Automation）」** 與 **「社群成長（Growth）」**，我們替專案引進了能增加互動的 AI 功能，並且加入了視覺化的成效監控面板。

以下是新功能的運作邏輯以及觀看教學：

---

## 1. 自動化社群互動 (AI Community Interaction)

過去我們的貼文（包含週間回顧與雷達推薦）在列完活動列表後，只會單純地加上 Hashtags，看起來比較像無情的發布機器器。

### 新邏輯
現在在 `post_radar_to_threads.py` 和 `src/processor/digest_builder.py` 之中，會在發文的最後一步呼叫 `src/utils/ai_enricher.py` 裡的 `generate_community_prompt`。
- **作法**：程式會把這週抓下來的「所有活動數量」以及「被標記為熱門的活動名稱」交給 Gemini 2.5 Flash 模型。
- **產出**：AI 會隨機生成「一句話」的社群問答（Call to Action），例如：「這週的活動滿滿，有人準備衝 大港開唱 嗎？」或「這週衝哪場？有推薦的隱藏好團嗎？」。
- **結果**：藉此引導 Threads 上的粉絲留言回覆，提升帳號的觸及率跟活絡度。

### 如何單獨測試？
如果你想在不發文的情況下，先看看 AI 今天會幫你配什麼梗，可以在終端機執行 dry-run（模擬執行）模式：
```bash
# 確保環境變數已載入，且 .env 內有正確的 GEMINI_API_KEY
source .env
./venv/bin/python post_radar_to_threads.py --dry-run
```
這只會在畫面印出排版結果，**不會**真的推播到 Threads 上！

---

## 2. 成效追蹤儀表板 (Performance Tracking Dashboard)

爬蟲系統每週在 GitHub Actions 上自動跑，有時候我們不會知道「今天 KKTIX 抓了幾筆？」或是「哪邊發生了因為網頁改版導致的錯誤？」。

### 新邏輯
我們新增了一支負責統計的程式：`scripts/generate_dashboard.py`。
- **觸發時機**：在每週的 `Weekly Digest` (一/三/五) 以及 `Radar Events` (二/四/六) 的 GitHub Actions 流程跑到**最後一步**時自動執行。
- **統整資料**：它會把當天搜集到的 `digest_raw.json`、`radar_events.json` 數量，以及 `scraping_errors.json` (如果爬蟲有報錯的話) 全部統計起來。
- **產出結果**：生成一份精美的網頁檔案 `dashboard.html`，並打包上傳成 GitHub Actions 的 Artifacts。

### 如何觀看 Dashboard？
要在雲端查看你專案的健康度與活動數量比例，請依照以下步驟：

1. 打開瀏覽器，進入你的 GitHub 專案頁面：`https://github.com/Hans-coder/Smallseedsvoice`
2. 點擊上方的 **Actions** 頁籤。
3. 在左側列表中選擇你剛跑完的 Workflow（例如 `Weekly Digest (Free)` 或 `Radar Events Pipeline`）。
4. 點開最上面（最新）的一筆成功或失敗的執行紀錄。
5. 滑到頁面最下方的 **Artifacts** 區塊。
6. 你會看到一個名為 `weekly-digest-manual-guide` 或 `radar-manual-guide` 的壓縮檔，點擊下載它。
7. 解壓縮後，裡面會有一個 **`dashboard.html`**，雙擊用 Chrome 或 Safari 打開，就能看到視覺化的儀表板了！

### 面板功能
- **總計區塊**：一眼看出今天抓了幾場官方活動與雷達活動。
- **平台比例**：可以看到 KKTIX、OPENTIX、Indievox 等各個來源分別貢獻了多少場次。
- **錯誤紀錄 (Error Log)**：如果某個平台的爬蟲壞掉了（例如 Selenium 被官方阻擋），這裡會亮紅燈並附上錯誤訊息，方便你第一時間知道要來修復爬蟲。
