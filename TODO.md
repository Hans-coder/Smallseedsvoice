# 📋 待辦事項清單

## 🔴 優先級高（必須完成才能使用完整功能）

### 1. 配置 Threads API（發布功能）

**狀態：** ⏳ 待完成

**步驟：**
- [ ] 前往 [Meta for Developers](https://developers.facebook.com/) 登錄
- [ ] 創建應用程式（選擇「商業」或「其他」）
- [ ] 添加「Threads API」產品
- [ ] 獲取 **THREADS_ACCESS_TOKEN**
  - 前往 [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
  - 選擇應用程式 → 選擇Threads帳號 → 產生存取權杖
  - 選擇權限：`threads_basic`、`threads_content_publish`
  - 複製Token（只顯示一次！）
- [ ] 獲取 **THREADS_APP_ID**
  - 設定 → 基本 → 應用程式編號
  - 直接複製數字
- [ ] 獲取 **THREADS_APP_SECRET**
  - 設定 → 基本 → 應用程式密鑰
  - 點擊「顯示」按鈕 → 複製密鑰（只顯示一次！）
- [ ] 創建 `.env` 文件
  ```bash
  cd /Users/hanshsieh/taiwan-music-events
  touch .env
  ```
- [ ] 編輯 `.env` 文件，填入三個參數：
  ```env
  THREADS_ACCESS_TOKEN=你的Token
  THREADS_APP_ID=你的App_ID
  THREADS_APP_SECRET=你的App_Secret
  ```

**參考文件：** `THREADS_API_SETUP.md`

---

## 🟡 優先級中（建議完成，提升系統功能）

### 2. 添加更多 Instagram 帳號

**狀態：** ⏳ 待完成

**目的：** 減少活動缺漏，抓取更多音樂活動資訊

**步驟：**
- [ ] 研究並找出其他音樂活動相關的IG帳號
  - 建議帳號類型：
    - 地區性音樂活動帳號（台北、台中、高雄等）
    - 場館官方帳號（Legacy、The Wall、河岸留言等）
    - 音樂節官方帳號
- [ ] 編輯 `config.yaml`，在 `data_sources.instagram.accounts` 中添加：
  ```yaml
  data_sources:
    instagram:
      enabled: true
      accounts:
        - username: "livetws"
          max_posts: 20
          enabled: true
        - username: "新帳號1"  # 添加這裡
          max_posts: 15
          enabled: true
        - username: "新帳號2"  # 添加這裡
          max_posts: 10
          enabled: true
  ```
- [ ] 測試每個新帳號的抓取效果
- [ ] 根據實際情況調整 `max_posts` 數量

**注意：** 不要一次添加太多帳號，避免被限流

---

### 3. 調整時間範圍過濾

**狀態：** ⏳ 待完成（可選）

**目的：** 只抓取特定時間範圍的活動，避免過多無關活動

**步驟：**
- [ ] 決定要抓取的活動時間範圍
  - 例如：只抓取未來30天的活動
  - 例如：只抓取12月的活動
- [ ] 編輯 `config.yaml`：
  ```yaml
  data_sources:
    time_filter:
      enabled: true
      start_date: "today"      # 或 "2025-12-01"
      end_date: "+30days"       # 或 "2025-12-31"
  ```
- [ ] 測試時間過濾是否正常運作

**目前預設：** 從今天開始，30天後結束

---

## 🟢 優先級低（測試和優化）

### 4. 測試系統功能

**狀態：** ⏳ 待完成

**步驟：**
- [ ] **快速測試 Instagram 爬蟲**
  ```bash
  source venv/bin/activate
  python test_instagram.py
  ```
  - 確認可以正常抓取貼文
  - 檢查活動資訊提取是否正確

- [ ] **完整流程測試（不發布）**
  ```bash
  source venv/bin/activate
  python main.py
  ```
  - 確認可以抓取活動
  - 確認圖片可以下載
  - 確認數據可以保存到數據庫

- [ ] **測試時間過濾功能**
  - 修改 `config.yaml` 中的時間範圍
  - 運行程序，檢查是否只抓取指定時間範圍的活動

- [ ] **測試多帳號功能**
  - 添加多個IG帳號
  - 運行程序，確認所有帳號都能正常抓取

- [ ] **測試 Threads 發布（如果已配置API）**
  - 確認可以成功發布到Threads
  - 確認發布後圖片會被刪除（如果啟用）

- [ ] **檢查數據庫**
  ```bash
  sqlite3 data/events.db "SELECT COUNT(*) FROM events;"
  sqlite3 data/events.db "SELECT name, location, time, is_posted FROM events ORDER BY created_at DESC LIMIT 10;"
  ```

**參考文件：** `TESTING.md`

---

### 5. 優化活動資訊提取

**狀態：** ⏳ 待完成（根據實際情況）

**目的：** 提高活動資訊提取的準確性

**步驟：**
- [ ] 檢查數據庫中的活動資訊
- [ ] 找出提取不準確的活動
- [ ] 查看對應的Instagram貼文格式
- [ ] 調整 `src/scraper/instagram_scraper.py` 中的提取邏輯
  - 調整正則表達式
  - 優化時間解析
  - 改進地點提取

---

### 6. 設置定時任務（自動運行）

**狀態：** ⏳ 待完成（可選）

**目的：** 讓系統自動定期運行，無需手動執行

**步驟（macOS）：**
- [ ] 編輯 crontab：
  ```bash
  crontab -e
  ```
- [ ] 添加定時任務（例如：每週一上午9點執行）：
  ```cron
  0 9 * * 1 cd /Users/hanshsieh/taiwan-music-events && /Users/hanshsieh/taiwan-music-events/venv/bin/python /Users/hanshsieh/taiwan-music-events/main.py >> /Users/hanshsieh/taiwan-music-events/logs/cron.log 2>&1
  ```
- [ ] 或使用 APScheduler（需要修改 `main.py`）

**參考文件：** `QUICKSTART.md`

---

## 📝 其他建議

### 7. 監控和維護

- [ ] 定期檢查日誌文件 `logs/app.log`
- [ ] 定期檢查數據庫中的活動數量
- [ ] 如果使用短期Token，記得定期更新 `.env` 中的 Token
- [ ] 監控圖片檔案數量（如果未啟用自動刪除）

### 8. 擴展功能（未來考慮）

- [ ] 添加其他數據源（網站爬蟲）
- [ ] 添加OCR功能（讀取圖片中的文字）
- [ ] 添加通知功能（發布成功/失敗時發送通知）
- [ ] 創建Web界面查看和管理活動

---

## 📚 相關文件

- `THREADS_API_SETUP.md` - Threads API 詳細設定指南
- `TESTING.md` - 測試指南
- `IMPROVEMENTS.md` - 系統改進說明
- `USAGE.md` - 使用說明
- `config.yaml` - 系統配置文件

---

## ✅ 快速檢查清單

開始工作前，確認：
- [ ] 虛擬環境已激活：`source venv/bin/activate`
- [ ] 依賴已安裝：`pip install -r requirements.txt`
- [ ] `config.yaml` 配置正確
- [ ] `.env` 文件已創建（如果要用Threads發布）

完成後，確認：
- [ ] 程序可以正常運行
- [ ] 活動可以正常抓取
- [ ] 數據可以正常保存
- [ ] Threads發布功能正常（如果已配置）

---

**最後更新：** 2025-11-23





