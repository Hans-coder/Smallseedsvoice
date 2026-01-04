# 快速開始指南

## 安裝步驟

### 1. 安裝Python依賴
```bash
cd taiwan-music-events
pip install -r requirements.txt
```

### 2. 配置環境變數
```bash
cp .env.example .env
# 編輯 .env 文件，填入Threads API相關憑證
```

### 3. 配置數據源
編輯 `config.yaml`，添加要抓取的網站：
```yaml
data_sources:
  sites:
    - name: "your_site_name"
      url: "https://your-site.com/events"
      enabled: true
      type: "both"  # free, paid, or both
```

## Threads API 申請步驟

1. 前往 [Meta for Developers](https://developers.facebook.com/)
2. 創建應用程式
3. 添加 Threads API 產品
4. 獲取 Access Token
5. 將憑證填入 `.env` 文件

## 運行程序

### 手動運行
```bash
python main.py
```

### 設置定時任務（macOS）
使用 `crontab`：
```bash
crontab -e
# 添加以下行（每週一上午9點執行）
0 9 * * 1 cd /path/to/taiwan-music-events && /usr/bin/python3 main.py
```

## 自定義爬蟲

### 步驟1: 分析目標網站
使用瀏覽器開發者工具檢查網頁結構，找到：
- 活動列表的容器元素
- 活動名稱、地點、時間的選擇器
- 圖片URL的位置

### 步驟2: 創建專用爬蟲類
在 `src/scraper/music_sites.py` 中添加：

```python
class YourSiteScraper(BaseScraper):
    """您的網站專用爬蟲"""
    
    def scrape_events(self, url: str) -> List[Dict]:
        soup = self.fetch_page(url)
        if not soup:
            return []
        
        events = []
        # 根據實際網站結構修改選擇器
        event_elements = soup.find_all('div', class_='your-event-class')
        
        for element in event_elements:
            event = self.parse_event(element)
            if event:
                event['source_url'] = url
                events.append(event)
        
        return events
    
    def parse_event(self, element) -> Optional[Dict]:
        # 根據實際網站結構解析
        name = element.find('h2', class_='event-title')
        # ... 其他字段
        
        return {
            'name': name.get_text(strip=True) if name else '',
            'location': ...,
            'time': ...,
            'price_type': ...,
            'image_url': ...,
        }
```

### 步驟3: 在主程序中使用
修改 `main.py`，根據網站類型選擇對應的爬蟲類。

## 常見問題

### Q: 如何處理需要登錄的網站？
A: 可以在 `BaseScraper` 的 `__init__` 中添加登錄邏輯，或使用 Selenium 處理動態內容。

### Q: 圖片下載失敗怎麼辦？
A: 檢查圖片URL是否有效，網絡連接是否正常，文件路徑是否有寫入權限。

### Q: Threads API 發布失敗？
A: 檢查：
- Access Token 是否有效
- API權限是否正確
- 發布內容是否符合Threads規範

### Q: 如何過濾特定類型的活動？
A: 在 `DataProcessor.clean_event_data()` 中添加過濾邏輯。

## 調試技巧

1. **啟用詳細日誌**: 在 `.env` 中設置 `LOG_LEVEL=DEBUG`
2. **檢查數據庫**: 使用SQLite工具查看 `data/events.db`
3. **測試單個模組**: 可以單獨運行各個模組進行測試
4. **查看日誌文件**: 檢查 `logs/app.log`

## 下一步

1. 根據實際需求調整爬蟲邏輯
2. 優化發布格式和內容
3. 添加錯誤通知機制（如郵件、Telegram等）
4. 考慮添加Web界面查看和管理活動


