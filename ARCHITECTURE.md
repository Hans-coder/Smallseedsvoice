# 系統架構：台灣音樂活動爬蟲

## 概述
本系統旨在聚合台灣官方售票平台與地下/社群來源的音樂活動資訊。採用**雙腳本架構**以平衡資料可靠性與覆蓋率。

## 資料流程圖

```mermaid
graph TD
    subgraph "腳本 1: 官方售票平台"
        A[官方爬蟲] -->|抓取| B(KKTIX)
        A -->|抓取| C(OPENTIX)
        A -->|抓取| D(拓元售票)
        B -->|解析| E{統一 Schema}
        C -->|解析| E
        D -->|解析| E
        E -->|過濾| F[過濾: 僅音樂類, 未來日期]
        F -->|輸出| G[data/official_events.json]
    end

    subgraph "腳本 2: 活動雷達"
        H[雷達爬蟲] -->|抓取| I(Indievox Live Houses)
        H -->|抓取| J(Instagram 帳號)
        I -->|解析| K{雷達 Schema}
        J -->|解析| K
        K -->|過濾| L[過濾: 去重, 未來日期]
        L -->|輸出| M[data/radar_events.json]
    end

    subgraph "預覽與發布"
        G --> N[預覽生成器]
        M --> N
        N -->|下載| O(圖片快取)
        N -->|生成| P[preview.html]
        P -->|使用者審核| Q{通過?}
        Q -->|是| R[Threads 發文工具]
        Q -->|否| S[手動編輯 / 重新執行]
        R -->|發文後| T[清理圖片快取]
    end
```

## 元件邏輯

### 1. 官方售票爬蟲 (`scrape_official_platforms.py`)
- **目標**: 高準確度、結構化資料
- **來源**:
  - **KKTIX**: 爬取「音樂」分類 (Tag 13)
  - **OPENTIX**: 爬取完整音樂子分類
  - **拓元售票**: 爬取主要活動列表
- **核心邏輯**:
  - **嚴格過濾**: 僅明確標示為「音樂」或「演唱會」類型的活動
  - **Schema**:
    - `activity_id`: 唯一 ID (平台 + 名稱 + 日期)
    - `image_url`: 視覺化貼文必要欄位
    - `ticket_url`: 購票連結

### 2. 活動雷達爬蟲 (`scrape_activity_radar.py`)
- **目標**: 高覆蓋率，特別是主流平台未收錄的活動
- **來源**:
  - **Indievox**: 作為多數 Live House 的售票引擎代理 (Legacy, The Wall 等)
  - **Instagram**: 直接監控場地官方帳號的傳單/貼文
- **核心邏輯**:
  - **盡力而為**: 接受不完整資料 (例如未知票價)
  - **日期解析**: 從社群貼文文字啟發式解析日期

### 3. 預覽生成器 (`preview_generator.py`)
- **目標**: 發文前視覺化驗證
- **流程**:
  1. 讀取 JSON 輸出
  2. 下載圖片至本地快取 (`data/preview_cache/`)
  3. 生成響應式 HTML 檔案 (`preview.html`)
  4. 允許使用者驗證內容與圖片

### 4. Threads 發文工具 (`post_to_threads.py`)
- **目標**: 自動發布活動資訊至 Threads
- **流程**:
  1. 讀取已驗證的 JSON 資料
  2. 格式化貼文文字
  3. 上傳圖片至 Threads
  4. 發布貼文
  5. 清理圖片快取

