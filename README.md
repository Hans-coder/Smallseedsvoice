# Taiwan Music Events Scraper

台灣音樂活動自動化爬蟲與發文系統

## 系統架構

本專案採用**雙管道架構**，兩個獨立的爬蟲與發文流程：

### 1️⃣ 官方售票平台管道
- **來源**: KKTIX, OPENTIX, 拓元售票
- **特色**: 高準確度、結構化資料
- **排程**: 每週一、三、五 早上 9:00
- **腳本**: `scrape_official_platforms.py` → `post_official_to_threads.py`

### 2️⃣ 活動雷達管道
- **來源**: Indievox, Instagram (Live House 帳號)
- **特色**: 高覆蓋率、地下音樂
- **排程**: 每週二、四、六 早上 9:00
- **腳本**: `scrape_activity_radar.py` → `post_radar_to_threads.py`

## 本地使用

### 官方平台管道
```bash
# 1. 爬取資料
./venv/bin/python scrape_official_platforms.py

# 2. 生成預覽
./venv/bin/python preview_generator.py
open preview.html

# 3. 發文到 Threads
source .env
./venv/bin/python post_official_to_threads.py
```

### 活動雷達管道
```bash
# 1. 爬取資料
./venv/bin/python scrape_activity_radar.py

# 2. 生成預覽
./venv/bin/python preview_generator.py
open preview.html

# 3. 發文到 Threads
source .env
./venv/bin/python post_radar_to_threads.py
```

## GitHub Actions 設定

### 必要的 Secrets
在 GitHub Repository Settings → Secrets 中設定：
- `THREADS_ACCESS_TOKEN`: Threads API Token

### 手動觸發
1. 進入 Actions 頁面
2. 選擇 "Official Events Pipeline" 或 "Radar Events Pipeline"
3. 點擊 "Run workflow"

### 自動排程
- **官方平台**: 每週一、三、五 早上 9:00 自動執行
- **活動雷達**: 每週二、四、六 早上 9:00 自動執行

## 檔案結構

```
taiwan-music-events/
├── scrape_official_platforms.py    # 官方平台爬蟲
├── scrape_activity_radar.py        # 活動雷達爬蟲
├── post_official_to_threads.py     # 官方平台發文
├── post_radar_to_threads.py        # 雷達活動發文
├── preview_generator.py            # 預覽生成器
├── .github/workflows/
│   ├── official_events.yml         # 官方平台 workflow
│   └── radar_events.yml            # 活動雷達 workflow
├── data/
│   ├── official_events.json        # 官方活動資料
│   └── radar_events.json           # 雷達活動資料
└── ARCHITECTURE.md                 # 系統架構文件
```

## 詳細文件

- [ARCHITECTURE.md](ARCHITECTURE.md) - 系統架構說明
- [QUICKSTART.md](QUICKSTART.md) - 快速開始指南
- [THREADS_API_SETUP.md](THREADS_API_SETUP.md) - Threads API 設定
