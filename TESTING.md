# 測試指南

## 📊 目前資料源

### 已啟用的資料源

1. **Instagram (@livetws)**
   - 狀態：✅ 已啟用
   - 配置位置：`config.yaml` → `data_sources.instagram`
   - 每次抓取：最多 20 個貼文
   - 功能：自動提取活動名稱、地點、時間、價格類型、圖片

### 未啟用的資料源

2. **網站爬蟲 (example_site)**
   - 狀態：❌ 已停用
   - 配置位置：`config.yaml` → `data_sources.sites[0]`
   - 說明：這是範例配置，目前未啟用

## 🧪 測試方法

### 方法 1：快速測試 Instagram 爬蟲（推薦）

只測試抓取功能，不保存到數據庫：

```bash
# 激活虛擬環境
source venv/bin/activate

# 運行測試腳本（只抓取 3 個貼文）
python test_instagram.py
```

**預期結果：**
- 顯示抓取到的活動資訊
- 包含活動名稱、地點、時間、價格類型
- 顯示圖片 URL 和貼文內容預覽

### 方法 2：完整流程測試（不發布）

測試完整流程但不發布到 Threads：

```bash
# 激活虛擬環境
source venv/bin/activate

# 運行主程序
python main.py
```

**預期結果：**
- 抓取 Instagram 貼文
- 下載圖片到 `data/images/`
- 保存活動到數據庫 `data/events.db`
- 跳過 Threads 發布（因為未配置 API）

### 方法 3：完整測試（包含發布）

需要先配置 Threads API（參考 `THREADS_API_SETUP.md`）：

```bash
# 1. 創建 .env 文件並填入 API 憑證
# 2. 運行主程序
source venv/bin/activate
python main.py
```

**預期結果：**
- 完成方法 2 的所有步驟
- 發布活動到 Threads
- 發布成功後自動刪除圖片（如果 `delete_after_post: true`）

### 方法 4：使用運行腳本

```bash
# 確保腳本有執行權限
chmod +x run.sh

# 運行
./run.sh
```

## 🔍 檢查測試結果

### 查看數據庫中的活動

```bash
# 使用 SQLite 命令行工具
sqlite3 data/events.db

# 在 SQLite 中執行查詢
SELECT COUNT(*) as total FROM events;
SELECT name, location, time, is_posted FROM events ORDER BY created_at DESC LIMIT 10;
.exit
```

或使用 Python：

```bash
python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager('data/events.db')
events = db.get_all_events(limit=10)
print(f'共有 {len(events)} 個活動')
for i, e in enumerate(events[:5], 1):
    print(f\"\n{i}. {e['name']}\")
    print(f\"   地點: {e['location']}\")
    print(f\"   時間: {e['time']}\")
    print(f\"   已發布: {'是' if e['is_posted'] else '否'}\")
"
```

### 查看下載的圖片

```bash
# 列出所有圖片
ls -lh data/images/

# 統計圖片數量
ls data/images/ | wc -l
```

### 查看日誌

```bash
# 查看最新日誌
tail -20 logs/app.log

# 查看錯誤日誌
grep ERROR logs/app.log

# 即時監控日誌
tail -f logs/app.log
```

## ⚙️ 測試配置調整

### 調整抓取數量（測試用）

編輯 `config.yaml`：

```yaml
data_sources:
  instagram:
    enabled: true
    username: "livetws"
    max_posts: 5  # 改為 5 個貼文（測試用）
```

### 測試圖片刪除功能

1. 確保 `config.yaml` 中設置：
   ```yaml
   images:
     delete_after_post: true
   ```

2. 配置 Threads API 並運行程序

3. 發布成功後檢查圖片是否被刪除：
   ```bash
   ls data/images/ | wc -l
   ```

### 停用圖片刪除（保留圖片）

編輯 `config.yaml`：

```yaml
images:
  delete_after_post: false  # 改為 false
```

## 🐛 常見測試問題

### 問題 1：Instagram 抓取失敗

**可能原因：**
- Instagram 限流
- 網絡連接問題
- 帳號不存在

**解決方法：**
- 在 `config.yaml` 中設置 Instagram 登錄資訊：
  ```yaml
  data_sources:
    instagram:
      ig_username: "your_username"
      ig_password: "your_password"
  ```
- 增加請求間隔時間（`request_delay`）

### 問題 2：圖片下載失敗

**檢查：**
- `data/images/` 目錄權限
- 網絡連接
- 圖片 URL 是否有效

**查看日誌：**
```bash
grep "圖片下載失敗" logs/app.log
```

### 問題 3：數據庫錯誤

**檢查數據庫：**
```bash
sqlite3 data/events.db ".schema"
```

**重建數據庫（會清空所有數據）：**
```bash
rm data/events.db
python main.py  # 會自動重建
```

## 📝 測試檢查清單

- [ ] Instagram 爬蟲可以正常抓取貼文
- [ ] 活動資訊提取正確（名稱、地點、時間、價格）
- [ ] 圖片可以正常下載
- [ ] 活動可以保存到數據庫
- [ ] 數據庫去重功能正常
- [ ] Threads 發布功能正常（如果配置了 API）
- [ ] 發布後圖片自動刪除（如果啟用）

## 🎯 下一步

1. **測試通過後**：可以設置定時任務自動運行
2. **添加更多資料源**：在 `config.yaml` 中添加更多網站
3. **優化提取邏輯**：根據實際貼文格式調整資訊提取





