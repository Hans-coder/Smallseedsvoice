# 專案檔案結構說明 (REPO_MAP)

這份文件活描述了目前 `taiwan-music-events` 專案中的主要檔案及其功能，幫助您快速了解整個系統的運作方式。

## 根目錄核心腳本

| 檔案名稱 | 功能說明 |
| :--- | :--- |
| `main.py` | 專案的主入口，可透過此腳本執行完整的流程。 |
| `scrape_official_platforms.py` | **官方售票平台爬蟲**：從 KKTIX, OPENTIX, tixCraft 抓取演出資訊。 |
| `scrape_activity_radar.py` | **活動雷達爬蟲**：從指定的雷達來源抓取音樂活動資訊。 |
| `post_official_to_threads.py` | **官方活動發布器**：將抓取到的官方售票資訊發布至 Threads。 |
| `post_radar_to_threads.py` | **雷達活動發布器**：將抓取到的雷達活動資訊發布至 Threads。 |
| `preview_generator.py` | **預覽產生器**：生成 HTML 頁面以預覽抓取到的活動內容。 |
| `requirements.txt` | 專案所需的 Python 依賴套件清單。 |
| `.env` | 環境變數設定檔（包含 API Keys, Tokens 等敏感資訊）。 |

## 核心原始碼 (`src/`)

### 爬蟲模組 (`src/scraper/`)
- `base_scraper.py`: 爬蟲的基礎類別，定義了通用邏輯。
- `ticketing/`: 存放各售票平台的專用爬蟲（KKTIX, OPENTIX, tixCraft 等）。
- `activity_radar/`: 存放活動雷達相關的抓取邏輯。

### 發布模組 (`src/threads/`)
- `threads_poster.py`: 核心發布邏輯，處理 Meta API 容器創建、延遲發布及狀態檢查。

### 工具模組 (`src/utils/`)
- `ai_enricher.py`: **[新]** 呼叫 Gemini AI 為貼文生成吸引人的前言。
- `logger.py`: 系統日誌記錄器。
- `date_parser.py`: 處理台灣日期格式的轉換。

## 數據與日誌
- `data/`: 存放抓取後的 JSON 檔案（如 `official_events.json`, `radar_events.json`）。
- `logs/`: 執行過程中的詳細日誌紀錄。

## 說明文件
- `README.md`: 專案基本介紹與安裝說明。
- `ARCHITECTURE.md`: 系統架構詳細說明。
- `USAGE.md`: 各腳本的使用方法。
- `THREADS_API_SETUP.md`: Threads API 的申請與設定教學。
