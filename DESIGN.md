# 系統設計文檔

## 整體架構設計

### 1. 系統流程圖

```
┌─────────────┐
│  配置載入    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  網站抓取    │──┐
└──────┬──────┘  │
       │         │
       ▼         │
┌─────────────┐  │
│  數據清洗    │  │
└──────┬──────┘  │
       │         │
       ▼         │
┌─────────────┐  │
│  圖片下載    │  │
└──────┬──────┘  │
       │         │
       ▼         │
┌─────────────┐  │
│  去重檢查    │◄─┘
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  數據存儲    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  內容格式化  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Threads發布 │
└─────────────┘
```

## 模組設計詳解

### 1. Scraper (爬蟲模組)

#### 設計理念
- **基礎類模式**: `BaseScraper` 提供通用功能（請求、重試、圖片下載）
- **繼承擴展**: 各網站專用爬蟲繼承基礎類，實現特定解析邏輯
- **可擴展性**: 易於添加新網站爬蟲

#### 關鍵功能
- 請求管理（延遲、超時、重試）
- HTML解析（BeautifulSoup）
- 圖片下載
- 錯誤處理和日誌記錄

#### 使用示例
```python
# 創建通用爬蟲
scraper = GenericMusicScraper(config)
events = scraper.scrape_events("https://example.com/events")

# 創建特定網站爬蟲（需要實現）
legacy_scraper = LegacyScraper(config)
events = legacy_scraper.scrape_events("https://legacy.com/events")
```

### 2. Processor (處理模組)

#### DataProcessor (數據處理)
- **數據清洗**: 驗證必要字段、清理格式
- **內容格式化**: 將活動數據轉換為Threads發布格式
- **時間過濾**: 過濾本週活動（需根據實際時間格式實現）

#### ImageHandler (圖片處理)
- **圖片驗證**: 檢查格式、大小
- **圖片優化**: 壓縮、調整大小
- **路徑管理**: 生成安全的文件路徑

### 3. Database (數據庫模組)

#### 設計特點
- **SQLite**: 輕量級，無需額外服務
- **去重機制**: 基於活動名稱、地點、時間的唯一性
- **發布狀態**: 追蹤哪些活動已發布

#### 表結構
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    location TEXT,
    time TEXT,
    price_type TEXT,
    image_url TEXT,
    image_path TEXT,
    source_url TEXT,
    created_at TEXT,
    posted_at TEXT,
    is_posted INTEGER DEFAULT 0,
    UNIQUE(name, location, time)
)
```

### 4. Threads Poster (發布模組)

#### API整合
- **認證**: 使用Access Token
- **媒體上傳**: 支持圖片上傳
- **帖子創建**: 發布文本和圖片

#### 注意事項
- 需要Meta開發者帳號
- 需要申請Threads API權限
- 遵守API使用限制

## 配置管理

### config.yaml
- 抓取設定（延遲、超時等）
- 數據源列表
- 數據庫配置
- 圖片配置
- Threads發布格式模板
- 排程設定

### .env
- API憑證（敏感信息）
- 調試設定

## 數據流程詳解

### 1. 抓取階段
```
網站URL → 發送請求 → 解析HTML → 提取活動信息 → 返回活動列表
```

### 2. 處理階段
```
原始活動數據 → 清洗驗證 → 下載圖片 → 優化圖片 → 處理後數據
```

### 3. 存儲階段
```
處理後數據 → 檢查是否已存在 → 新活動存入數據庫 → 返回新活動數量
```

### 4. 發布階段
```
未發布活動 → 格式化文本 → 上傳圖片 → 創建帖子 → 標記為已發布
```

## 擴展建議

### 1. 添加新網站爬蟲
1. 在 `src/scraper/music_sites.py` 創建新類
2. 繼承 `BaseScraper`
3. 實現 `scrape_events()` 和 `parse_event()` 方法
4. 在 `config.yaml` 中添加網站配置

### 2. 添加排程功能
可以使用 `APScheduler` 實現定時執行：
```python
from apscheduler.schedulers.blocking import BlockingScheduler

scheduler = BlockingScheduler()
scheduler.add_job(main, 'cron', day_of_week=0, hour=9)
scheduler.start()
```

### 3. 添加更多發布平台
- 創建新的發布模組（如 `twitter_poster.py`）
- 實現類似的接口
- 在主程序中添加發布邏輯

### 4. 數據源建議
需要根據實際情況添加的網站：
- Legacy Taipei 官方網站
- The Wall 官方網站
- 河岸留言
- 各音樂節官方網站
- 活動聚合平台（如KKTIX、Accupass等）

## 注意事項

### 法律和倫理
1. **遵守robots.txt**: 檢查網站的爬蟲規則
2. **合理請求頻率**: 避免對服務器造成負擔
3. **版權問題**: 圖片使用需注意版權
4. **數據使用**: 遵守網站的使用條款

### 技術注意
1. **錯誤處理**: 網絡請求可能失敗，需要重試機制
2. **數據驗證**: 確保抓取的數據完整有效
3. **API限制**: Threads API可能有速率限制
4. **日誌記錄**: 記錄重要操作以便調試

## 下一步行動

1. **確定數據源**: 列出要抓取的具體網站
2. **實現爬蟲**: 根據實際網站結構實現解析邏輯
3. **申請API**: 申請Meta Threads API權限
4. **測試運行**: 在小範圍內測試整個流程
5. **部署運行**: 設置定時任務自動執行


