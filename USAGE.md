# 使用說明

## 快速開始

### 1. 安裝依賴
```bash
pip install -r requirements.txt
```

### 2. 配置系統

#### 基本配置（已預設）
系統已預設配置抓取 @livetws 的Instagram貼文，可以直接運行測試。

#### 可選：配置Threads API
如果需要自動發布到Threads：
```bash
cp .env.example .env
# 編輯 .env 文件，填入Threads API憑證
```

### 3. 測試Instagram爬蟲
```bash
python test_instagram.py
```

這會測試抓取 @livetws 的最新3個貼文，並顯示提取的活動資訊。

### 4. 完整運行
```bash
python main.py
```

這會：
1. 抓取Instagram貼文
2. 提取活動資訊
3. 下載圖片
4. 保存到數據庫
5. 發布到Threads（如果已配置API）

## 工作流程

```
1. 抓取 @livetws 的Instagram貼文
   ↓
2. 識別活動相關貼文（包含音樂、演出等關鍵字）
   ↓
3. 從貼文文字中提取：
   - 活動名稱
   - 地點
   - 時間
   - 價格類型（免費/付費）
   ↓
4. 下載貼文中的圖片
   ↓
5. 保存到SQLite數據庫（自動去重）
   ↓
6. 格式化內容並發布到Threads
```

## 配置選項

### config.yaml 主要配置

```yaml
# Instagram配置
data_sources:
  instagram:
    enabled: true              # 是否啟用
    username: "livetws"        # IG帳號（不含@）
    max_posts: 20              # 每次抓取最多貼文數

# 抓取設定
scraper:
  request_delay: 2            # 請求間隔（秒）
  timeout: 30                 # 超時時間（秒）
  retry_count: 3              # 重試次數

# Threads發布格式
threads:
  post_format:
    template: |
      🎵 {event_name}
      📍 地點：{location}
      🕐 時間：{time}
      💰 {price_type}
      #台灣音樂 #音樂活動 #{location_tag}
```

## 常見使用場景

### 場景1：每日自動抓取並發布
設置定時任務（crontab）：
```bash
# 每天上午9點執行
0 9 * * * cd /path/to/taiwan-music-events && /usr/bin/python3 main.py
```

### 場景2：只抓取不發布
在 `config.yaml` 中不設置Threads API，或移除 `.env` 中的 `THREADS_ACCESS_TOKEN`。

### 場景3：調整抓取數量
修改 `config.yaml` 中的 `max_posts` 值：
```yaml
max_posts: 10  # 只抓取最新10個貼文
```

### 場景4：添加更多IG帳號
可以修改 `main.py`，循環抓取多個帳號：
```python
ig_accounts = ["livetws", "another_account"]
for account in ig_accounts:
    events = ig_scraper.scrape_events(account, max_posts)
    # ...
```

## 數據查看

### 查看數據庫中的活動
可以使用SQLite工具查看：
```bash
sqlite3 data/events.db
```

常用查詢：
```sql
-- 查看所有活動
SELECT * FROM events ORDER BY created_at DESC;

-- 查看未發布的活動
SELECT * FROM events WHERE is_posted = 0;

-- 查看本週活動
SELECT * FROM events WHERE created_at >= date('now', '-7 days');
```

## 問題排查

### 問題1：抓取失敗
**可能原因**：
- Instagram限流
- 網絡連接問題
- 帳號不存在或為私人帳號

**解決方法**：
- 使用Instagram帳號登錄（在config.yaml中設置）
- 增加請求間隔時間
- 檢查網絡連接

### 問題2：資訊提取不準確
**可能原因**：
- 貼文格式不一致
- 正則表達式需要調整

**解決方法**：
- 查看日誌文件 `logs/app.log`
- 根據實際貼文格式調整 `src/scraper/instagram_scraper.py` 中的提取邏輯

### 問題3：圖片下載失敗
**可能原因**：
- 圖片URL無效
- 網絡問題
- 權限問題

**解決方法**：
- 檢查 `data/images/` 目錄權限
- 查看日誌了解具體錯誤
- 嘗試手動訪問圖片URL

### 問題4：Threads發布失敗
**可能原因**：
- API憑證無效
- API權限不足
- 內容格式問題

**解決方法**：
- 檢查 `.env` 中的API憑證
- 確認已申請Threads API權限
- 查看日誌了解具體錯誤

## 日誌查看

日誌文件位置：`logs/app.log`

查看最新日誌：
```bash
tail -f logs/app.log
```

查看錯誤日誌：
```bash
grep ERROR logs/app.log
```

## 下一步建議

1. **添加OCR功能**：如果活動資訊主要在圖片中，可以添加OCR來讀取圖片文字
2. **擴展數據源**：添加其他網站或IG帳號
3. **優化提取邏輯**：根據實際貼文格式持續優化資訊提取
4. **添加通知**：發布成功/失敗時發送通知（郵件、Telegram等）
5. **Web界面**：創建簡單的Web界面查看和管理活動

## 注意事項

1. **遵守使用條款**：不要過度請求，遵守Instagram的使用條款
2. **數據準確性**：自動提取的資訊可能不完全準確，建議定期檢查
3. **版權問題**：使用圖片時注意版權
4. **API限制**：注意Threads API的速率限制


