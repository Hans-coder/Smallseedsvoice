# 系統改進說明

## 🎯 本次更新內容

### 1. ✅ 時間範圍過濾功能

**問題：** 之前系統會抓取所有活動，無法過濾特定時間範圍的活動。

**解決方案：**
- 在 `config.yaml` 中添加了 `time_filter` 配置區塊
- 實作了 `filter_events_by_time_range()` 方法
- 支援多種日期格式：
  - `"today"` - 從今天開始
  - `"2025-12-01"` - 具體日期
  - `"+30days"` - 相對日期（相對於開始日期）

**使用方式：**
```yaml
data_sources:
  time_filter:
    enabled: true
    start_date: "today"      # 從今天開始
    end_date: "+30days"       # 30天後
```

**範例配置：**
```yaml
# 只抓取12月的活動
time_filter:
  enabled: true
  start_date: "2025-12-01"
  end_date: "2025-12-31"
```

### 2. ✅ 支援多個Instagram帳號

**問題：** 只抓取一個IG帳號（@livetws）會有活動缺漏。

**解決方案：**
- 支援配置多個Instagram帳號
- 每個帳號可以獨立設置 `max_posts` 和 `enabled`
- 向後兼容：仍支援單帳號配置

**使用方式：**
```yaml
data_sources:
  instagram:
    enabled: true
    accounts:
      - username: "livetws"
        max_posts: 20
        enabled: true
      - username: "another_music_account"
        max_posts: 15
        enabled: true
      - username: "taipei_events"
        max_posts: 10
        enabled: false  # 暫時停用
```

**建議添加的帳號：**
- 各地區的音樂活動帳號
- 場館官方帳號（如 Legacy、The Wall）
- 音樂節官方帳號

### 3. ✅ 發布後自動刪除圖片

**問題：** 圖片檔案會越來越多，占用儲存空間。

**解決方案：**
- 在 `config.yaml` 中添加 `delete_after_post` 選項
- 發布成功後自動刪除對應圖片
- 發布失敗的圖片會保留

**配置：**
```yaml
images:
  delete_after_post: true  # 發布後刪除圖片
```

### 4. ✅ 更新Threads API設定說明

**問題：** 不清楚如何在開發者工具中找到API參數。

**解決方案：**
- 更新了 `THREADS_API_SETUP.md`
- 提供詳細的步驟說明和視覺指引
- 明確說明每個參數在開發者工具中的位置

**需要的參數：**
1. **THREADS_ACCESS_TOKEN**
   - 位置：Graph API Explorer → 存取權杖欄位
   - 獲取方式：選擇應用程式 → 選擇Threads帳號 → 產生存取權杖

2. **THREADS_APP_ID**
   - 位置：設定 → 基本 → 應用程式編號
   - 直接複製即可

3. **THREADS_APP_SECRET**
   - 位置：設定 → 基本 → 應用程式密鑰
   - 需要點擊「顯示」按鈕

## 📊 資料源建議

### 目前狀態
- ✅ Instagram (@livetws) - 已啟用

### 建議添加的資料源

#### Instagram帳號（推薦）
1. **地區性音樂活動帳號**
   - 台北：@taipei_music_events
   - 台中：@taichung_live
   - 高雄：@kaohsiung_music

2. **場館官方帳號**
   - Legacy Taipei
   - The Wall Live House
   - 河岸留言

3. **音樂節官方帳號**
   - 各音樂節的官方Instagram

#### 網站爬蟲（需要實作）
1. **活動聚合平台**
   - KKTIX
   - Accupass
   - Citytalk

2. **場館官方網站**
   - Legacy 官方網站
   - The Wall 官方網站

## 🔧 配置範例

### 完整配置範例（多帳號 + 時間過濾）

```yaml
data_sources:
  instagram:
    enabled: true
    accounts:
      - username: "livetws"
        max_posts: 20
        enabled: true
      - username: "taipei_music"
        max_posts: 15
        enabled: true
  
  time_filter:
    enabled: true
    start_date: "today"
    end_date: "+30days"
```

## 🚀 下一步建議

1. **添加更多IG帳號**
   - 在 `config.yaml` 中添加更多音樂活動相關的IG帳號
   - 測試每個帳號的抓取效果

2. **調整時間範圍**
   - 根據需求調整 `start_date` 和 `end_date`
   - 例如：只抓取未來一週的活動

3. **配置Threads API**
   - 按照 `THREADS_API_SETUP.md` 的步驟獲取API參數
   - 創建 `.env` 文件並填入參數

4. **監控和優化**
   - 定期檢查抓取的活動數量
   - 根據實際情況調整 `max_posts` 和時間範圍

## ⚠️ 注意事項

1. **時間解析**
   - 系統會嘗試解析活動時間字符串
   - 如果無法解析，該活動仍會被保留（避免誤刪）
   - 可以根據實際貼文格式優化時間解析邏輯

2. **多帳號抓取**
   - 每個帳號都會有請求間隔（`request_delay`）
   - 建議不要同時啟用太多帳號，避免被限流

3. **圖片刪除**
   - 只有發布成功的活動圖片會被刪除
   - 發布失敗的圖片會保留，方便排查問題

## 📝 相關文件

- `config.yaml` - 系統配置
- `THREADS_API_SETUP.md` - Threads API設定指南
- `TESTING.md` - 測試指南
- `USAGE.md` - 使用說明





