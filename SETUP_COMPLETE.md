# 🎉 系統設置完成！

## ✅ 已完成的工作

### 1. 專案架構
- ✅ 完整的模組化架構
- ✅ 配置文件設置
- ✅ 虛擬環境配置

### 2. Instagram爬蟲
- ✅ 成功實現Instagram爬蟲
- ✅ 自動抓取 @livetws 的活動貼文
- ✅ 智能提取活動資訊（名稱、地點、時間、價格類型）
- ✅ 自動下載活動圖片

### 3. 數據處理
- ✅ 數據清洗和驗證
- ✅ 圖片下載和保存
- ✅ SQLite數據庫存儲
- ✅ 自動去重機制

### 4. 測試結果
- ✅ 成功抓取20個活動
- ✅ 活動資訊提取準確
- ✅ 圖片下載成功
- ✅ 數據庫保存正常

## 📊 當前系統狀態

### 數據庫統計
- 總活動數：20個
- 數據來源：@livetws Instagram
- 圖片存儲：`data/images/`
- 數據庫位置：`data/events.db`

### 配置狀態
- Instagram爬蟲：✅ 已啟用
- Threads發布：⏸️ 待配置（需要API憑證）
- 定時任務：⏸️ 待設置

## 🚀 如何使用

### 方法1：使用運行腳本（推薦）
```bash
chmod +x run.sh
./run.sh
```

### 方法2：手動運行
```bash
source venv/bin/activate
python main.py
```

### 方法3：測試Instagram爬蟲
```bash
source venv/bin/activate
python test_instagram.py
```

## 📝 查看數據

### 查看數據庫中的活動
```bash
source venv/bin/activate
python -c "
from src.database.db_manager import DatabaseManager
db = DatabaseManager('data/events.db')
events = db.get_all_events()
print(f'共有 {len(events)} 個活動')
for i, e in enumerate(events[:10], 1):
    print(f\"\n{i}. {e['name']}\")
    print(f\"   地點: {e['location']}\")
    print(f\"   時間: {e['time']}\")
    print(f\"   價格: {e['price_type']}\")
"
```

### 查看日誌
```bash
tail -f logs/app.log
```

## 🔧 下一步配置（可選）

### 1. 配置Threads API自動發布

#### 步驟1：申請Meta開發者帳號
1. 前往 [Meta for Developers](https://developers.facebook.com/)
2. 創建應用程式
3. 添加 Threads API 產品
4. 獲取 Access Token

#### 步驟2：配置環境變數
```bash
cp .env.example .env
# 編輯 .env 文件，填入以下資訊：
# THREADS_ACCESS_TOKEN=your_access_token_here
# THREADS_APP_ID=your_app_id_here
# THREADS_APP_SECRET=your_app_secret_here
```

#### 步驟3：測試發布
運行程序後，系統會自動發布未發布的活動到Threads。

### 2. 設置定時任務（自動運行）

#### macOS/Linux (crontab)
```bash
crontab -e
# 添加以下行（每週一上午9點執行）
0 9 * * 1 cd /Users/hanshsieh/taiwan-music-events && /Users/hanshsieh/taiwan-music-events/venv/bin/python /Users/hanshsieh/taiwan-music-events/main.py >> /Users/hanshsieh/taiwan-music-events/logs/cron.log 2>&1
```

#### 使用APScheduler（已在代碼中）
可以修改 `main.py` 添加定時任務功能。

### 3. 調整抓取設置

編輯 `config.yaml`：
```yaml
data_sources:
  instagram:
    enabled: true
    username: "livetws"  # 可以改為其他IG帳號
    max_posts: 20        # 調整每次抓取的貼文數量
```

## 📁 專案結構

```
taiwan-music-events/
├── run.sh                 # 運行腳本
├── main.py                # 主程序
├── test_instagram.py      # 測試腳本
├── config.yaml            # 配置文件
├── .env                   # 環境變數（需創建）
├── requirements.txt       # Python依賴
├── data/
│   ├── events.db         # SQLite數據庫
│   └── images/           # 下載的圖片
├── logs/
│   └── app.log           # 日誌文件
└── src/                   # 源代碼
    ├── scraper/          # 爬蟲模組
    ├── processor/        # 處理模組
    ├── database/         # 數據庫模組
    ├── threads/          # Threads發布模組
    └── utils/            # 工具模組
```

## 🎯 功能說明

### 當前功能
1. **自動抓取**：從 @livetws 抓取最新活動貼文
2. **智能提取**：自動提取活動名稱、地點、時間、價格類型
3. **圖片下載**：自動下載活動圖片
4. **數據存儲**：保存到SQLite數據庫，自動去重
5. **準備發布**：數據已準備好，等待Threads API配置

### 待擴展功能
1. **Threads自動發布**：需要配置API
2. **多數據源**：可以添加更多IG帳號或網站
3. **OCR功能**：讀取圖片中的文字（如果活動資訊在圖片中）
4. **Web界面**：查看和管理活動
5. **通知功能**：發布成功/失敗時發送通知

## ⚠️ 注意事項

1. **遵守使用條款**：
   - 不要過度請求Instagram
   - 遵守robots.txt規則
   - 合理設置請求間隔

2. **數據準確性**：
   - 自動提取的資訊可能不完全準確
   - 建議定期檢查數據庫中的活動
   - 可以根據實際情況調整提取邏輯

3. **版權問題**：
   - 使用圖片時注意版權
   - 發布時註明來源

4. **API限制**：
   - Threads API可能有速率限制
   - Instagram可能會有請求限制

## 📞 問題排查

### 問題：抓取失敗
- 檢查網絡連接
- 查看日誌文件 `logs/app.log`
- 嘗試使用Instagram帳號登錄（在config.yaml中設置）

### 問題：資訊提取不準確
- 查看日誌了解提取過程
- 根據實際貼文格式調整 `src/scraper/instagram_scraper.py` 中的正則表達式

### 問題：圖片下載失敗
- 檢查 `data/images/` 目錄權限
- 查看日誌了解具體錯誤

## 🎊 恭喜！

系統已經完全設置好並可以正常運行！您可以：

1. **立即使用**：運行 `./run.sh` 或 `python main.py`
2. **查看數據**：檢查數據庫中的活動
3. **配置發布**：設置Threads API後自動發布
4. **持續優化**：根據實際需求調整配置

祝您使用愉快！🎵


