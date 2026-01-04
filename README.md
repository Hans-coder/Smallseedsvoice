# 🇹🇼 台灣免費音樂活動自動整理系統

這是一套自動化系統，目標是每週自動整理台灣的免費音樂活動，並產出可直接發布到 Threads 的貼文內容。

## 🎯 系統目標

- **自動化**：每週定時抓取、篩選、整理活動。
- **Threads 最佳化**：自動生成符合 Threads 格式的貼文，支援圖片排序與長文自動拆分。
- **雙軌策略**：
    1. **每週懶人包 (Weekly Digest)**：每週日產出下週免費活動總整理。
    2. **即時情報 (Real-time Alerts)**：(可選) 監控特定售票活動並即時通知。

## 📅 執行排程

- **頻率**：每週一次 (Default)
- **時間**：每週日 20:00 (可於 `config.yaml` 調整)
- **抓取範圍**：下週一 00:00 至 下週日 23:59

## 📊 資料來源 (目前實作狀態)

系統設計支援多層次資料來源，目前已實作與待實作清單：

| 層級 | 來源 | 狀態 | 說明 |
| :--- | :--- | :--- | :--- |
| **Tier 1 (主要)** | **KKTIX** | ✅ 已實作 (基礎) | 篩選音樂類活動 (需確認免費篩選邏輯) |
| | **Accupass** | 📝 規劃中 | 待開發 |
| **Tier 2 (官方)** | 縣市文化局 | 📝 規劃中 | 尚未接駁 |
| **Tier 3 (LiveHouse)**| Legacy, The Wall | 📝 規劃中 | 尚未接駁 |
| **社群補充** | Instagram (@livetws) | ✅ 已實作 | 作為免費活動的重要補充來源 |

## 🛠 系統架構

1. **Scraper (爬蟲)**：負責從各來源抓取原始資料。
    - 支援 Requests 與 Selenium (繞過 WAF)。
2. **Processor (處理器)**：
    - 資料清洗與標準化 (JSON 格式)。
    - **Filter**：篩選「免費」、「音樂類」、「下週活動」。
    - **DigestBuilder**：將活動組合成 Threads 貼文格式，自動處理 500 字限制與圖片分流。
3. **Database (資料庫)**：使用 SQLite 儲存活動，避免重複發布。
4. **Publisher (發布器)**：(可選) 透過 Threads API 自動發文，或僅產出文字供人工發布。

## 📝 輸出格式 (Threads)

系統會自動產出如下格式：

```
📍【台北】2024 台北爵士音樂節
🗓 09/25（三）19:00
📌 大安森林公園

(圖片 1)
```

若內容過長，系統會自動切分為：
- 主文
- 留言 1
- 留言 2 ...

---

## 🚀 如何開始與測試

### 1. 環境準備

需要 Python 3.10+。

```bash
# 安裝依賴
pip install -r requirements.txt

# (若需要爬 KKTIX 抗擋機制) 安裝 Chrome 與對應 WebDriver
```

### 2. 設定檔

請複製 `.env.example` 為 `.env` 並填入：

```ini
# (選填) 若要啟用自動發文
THREADS_ACCESS_TOKEN=your_token
THREADS_USER_ID=your_id

# (選填) 若要使用 Instagram 來源
INSTAGRAM_SESSION_ID=your_session_id
```

檢查 `config.yaml` 確認來源與排程設定。

### 3. 測試運行

**測試每週懶人包生成 (Dry Run)**
此指令會抓取資料並在 Terminal 顯示「預計發出的貼文內容」，不會真的發文。

```bash
python run_weekly_digest.py
```

**測試 KKTIX 抓取**

```bash
python src/tests/test_kktix.py
```

## 🤝 您需要提供的協助

為了讓系統完全運作，我需要您提供：

1. **Threads API Token** (若您希望從「產出文字」進階到「全自動發文」)。
2. **Instagram Session ID** (若要持續穩定抓取 IG 來源，避免被封鎖)。
3. **確認各來源優先順序**：目前系統混合了 IG 與 KKTIX，您希望以哪個為主？(目前邏輯：整合所有來源並依時間排序)。

## 📁 專案結構

- `src/scraper/`: 各網站爬蟲
- `src/processor/digest_builder.py`: 負責將資料轉為 Threads 格式 (核心邏輯)
- `src/scheduler/`: 排程器
- `data/`: 儲存資料庫與下載的圖片
