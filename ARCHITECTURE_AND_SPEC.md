# Taiwan Music Events Automation - System Architecture & Spec

本文件記錄了小草之聲 (Smallseedsvoice) 台灣音樂祭 / 獨立音樂活動爬蟲與社群自動化專案的核心邏輯、技術應用與開發準則。**任何對程式碼或排程的更動前，皆須詳閱此文檔，並於更動後同步更新此文件。**

## 1. 核心專案架構

本專案主要包含三個自動化流程 (Pipeline)，皆部署於 GitHub Actions，透過 Cron Job 腳本定期執行：

1. **Weekly Digest (半週報精選)** 
   - **排程**：每週一、週四 10:00 (台灣時間)。
   - **功能**：統整未來 3~4 天內的獨立音樂活動，抓取來源包含 KKTIX, OPENTIX, Indievox, StreetVoice 與 IG。
   - **產出**：
     - Discord 通知（供內部確認）。
     - `artifacts/social_cards.html` (社群發文用固定版型圖片)。
     - 供 Threads 發文用的格式化純文字。
   - **備註**：目前 Threads **自動發文功能被刻意關閉**，由人工收到 Discord 通知或下載 Artifact 後，手動進行社群發布。

2. **Radar Events (樂團雷達站/Spotlight)**
   - **排程**：每週二、四、六 09:00 (台灣時間)。
   - **功能**：深入抓取 Indievox 與 StreetVoice 等 Live House 活動，旨在發掘「無名氣但具潛力」的獨立樂團。
   - **AI Spotlight 機制**：
     - 程式會使用 `PerformerTracker` 比對歷史紀錄。若發現從未出現過的「新血樂團 (New Blood)」，會觸發 `AIEnricher`。
     - AIEnricher 會透過 Google Gemini 快速生成該樂團的「極短、無 AI 感、具樂迷偏見與熱情」的推薦短評，並搜尋其 IG 帳號。
     - 短評會被附加在活動卡片或文字上，達到我們「推廣小團」的初衷。

3. **Sale Alarm (售票情報鬧鐘)**
   - **排程**：每天 20:00 (台灣時間)。
   - **功能**：抓取售票網，檢查是否有在未來 3 天內或「明天」即將開賣的熱門活動。
   - **備註**：Threads 的自發文邏輯一樣可手動於腳本中選擇是否開啟。

## 2. 爬蟲與資料處理技術

- **動態爬蟲**：主要仰賴 BeautifulSoup4 與部分 API Reverse Engineering。
- **去重機制 (Deduplication)**：跨平台抓取容易產生重複活動。我們透過 `get_event_hash(name, date, venue)` 來進行比對，並優先保留附有高解析度票圖或完整描述的紀錄。
- **資料儲存**：採用輕量化 `.json` 落地儲存（如 `digest_raw.json`），並利用 GitHub Actions Cache 機制保留 `events.db` 追蹤樂團歷史。

## 3. 社群圖文生成原則 (重要)

為降低一人單兵作戰的維護成本，我們**不開發、不維護 Web Dashboard**。

- **靜態社群卡片 (`create_social_cards.py`)**：
  - 週報或雷達產生資料後，會透過純 HTML/CSS 演算法生成固定尺寸 (1080x1080) 的日式和風音樂祭設計卡片。
  - 設計嚴格固定（溫和底色、深色字體、高對比度、無螢光霓虹），減少視覺疲勞。使用者只需開啟 HTML 並截圖即可發布至 IG / Threads，實現零維護成本的美學輸出。
- **AI 撰稿語氣 (AI Tone Protocol)**：
  - 絕對禁止使用 Emoji (🫠, ✨, 🎸 等)。
  - 絕對禁止使用常見套路開場白 ("這是一個...", "他們的特色在於...")。
  - 必須模擬台灣獨立音樂圈資深樂迷口吻，強烈主觀，可使用黑話 (例如：暈船、炸爛、又躁又頂)。

## 4. 維護與修改準則

1. **不要隨意開啟 Threads 自動發文**：由於 Threads API 時常變動且可能有不可控的風險，目前我們採「半自動」模式（系統整理資料、生成卡片、發送 Discord 通知 $\rightarrow$ 人工複製審核後發布）。這能有效避免意外與版面災難。
2. **遵守半週報的時間邏輯**：Digest 的時間切割為「週一負責週一到週三，週四負責週四到週日」。若需更改，須至 `run_weekly_digest.py` 同步調整 `end_date` 運算邏輯。
3. **新增資料來源**：若需新增售票網或 Live House 網站，請至 `src/scraper/` 下新增對應的 Script，並確認拋出的 JSON 格式統一 (包含 date, venue, name, image_url)。

*(Last Updated: 2026-04)*
