# Smallseedsvoice — 你的聽團小聲音 🎧

全台音樂演出自動化策展與展演空間探索系統。整合多平台爬蟲（KKTIX、iNDIEVOX、tixCraft、TicketPlus、StreetVoice），透過 AI 與品味策展轉化為高互動社群貼文，並提供專屬的「全台 Livehouse 展演空間探索地圖網站」。

---

## 🌟 核心特色與架構

```
                               ┌──► 模式 A：單場爆款焦點（愛心卡司、免費標籤、揪團 CTA）
                               ├──► 模式 B：小聲音私心推（樂團短評、品味推薦、話語權 IP）
全台爬蟲引擎 ──► 策展格式引擎 ──┤
(KKTIX, iNDIEVOX,              └──► 模式 C：升級版每週週報（亮點統計、日曆、導流至網站）
 StreetVoice, tixCraft)                   │
         │                                ▼
         └─────────────► 展演空間 Web 探索地圖 (web/index.html)
                         (依 Legacy / Revolver / 駁二 等空間與免費快篩)
```

1. **爆款社群貼文引擎 (`src/processor/curator_formatter.py`)**：
   - **單場爆款焦點 (Spotlight)**：主打免費音樂祭與熱門大卡司，採用 Unicode 粗體、愛心卡司 (`♥︎藝人`)、地點方框與社交揪團 CTA（促發 Threads 收藏與標記好友演算法）。
   - **小聲音私心推 (Curator Pick)**：結合 Gemini AI 與獨立樂團策展口吻，專門推坑 Livehouse 特色專場與聲音風格，建立帳號專業度與話語權。
   - **升級版每週週報 (Smart Digest)**：整合全台演出日曆，精準提煉免費場與焦點大場，引導讀者至網站查閱地圖。

2. **全台 Livehouse 展演空間地圖網站 (`web/index.html`)**：
   - 現代深色毛玻璃美學設計（純 Vanilla CSS + JS，極速載入、支援離線與 GitHub Pages 託管）。
   - **空間分類檢索**：一鍵快速切換查看 Legacy Taipei、The Wall、Revolver、河岸留言、Zepp New Taipei、駁二 LIVE WAREHOUSE 等指標性場地之所有場次。
   - **智慧篩選器**：支援「✨ 完全免費」、「🔥 熱門焦點」、「雙北 / 中部 / 南部」與全文關鍵字即時搜尋。
   - **一鍵複製與購票**：卡片內建直達購票連結與一鍵複製 Threads 揪團格式。

3. **進階預覽與編輯伺服器 (`scripts/digest_server.py`)**：
   - 支援電腦與手機（同 WiFi）開啟 `http://localhost:5055`。
   - 頂部一鍵切換預覽「每週週報串」、「單場爆款候選」與「小聲音私心推」。
   - 內建字數計量器、增刪圖片、即時編輯草稿，確認後可一鍵發布至 Threads。
   - 整合 `/web/` 路由直接預覽展演空間網站。

---

## 🚀 快速上手

### 1. 安裝環境
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 本地產生 Web 資料庫與啟動網站
```bash
# 1. 彙整目前演出資料至 web/data/events.json
python scripts/build_web_data.py

# 2. 啟動管理與預覽伺服器（同時支援 Web 網站與貼文編輯）
python scripts/digest_server.py
```
- 開啟貼文管理後台：`http://localhost:5055`
- 開啟展演空間地圖網站：`http://localhost:5055/web/`

### 3. 執行全平台每週抓取與處理
```bash
# 抓取並自動生成週報、單場焦點候選及 Web 資料庫
python run_weekly_digest.py --step all
```

---

## 📁 目錄結構

```
.
├── web/                     # 全台 Livehouse 展演空間網站
│   ├── index.html           # 響應式質感探索前端 (Vanilla CSS+JS)
│   └── data/events.json     # 前端靜態活動資料庫
├── scripts/
│   ├── build_web_data.py    # Web 活動資料庫建置腳本
│   ├── digest_server.py     # 本地進階預覽伺服器（支援三模式與網站預覽）
│   ├── detect_trending.py   # 每日熱門活動偵測
│   └── create_social_cards.py # 社群視覺圖產生
├── src/
│   ├── processor/
│   │   ├── curator_formatter.py # 爆款焦點、私心推與社交 CTA 格式化引擎
│   │   ├── digest_builder.py    # 演出排序、分篇與候選篩選
│   │   └── ai_summarizer.py     # Gemini AI 策展人短評與週報統整
│   ├── scraper/             # KKTIX / iNDIEVOX / StreetVoice / tixCraft 爬蟲
│   ├── threads/             # Threads API 發布模組
│   └── utils/               # 日期處理、文本清理與記錄器
├── data/
│   ├── digest_raw.json      # 抓取暫存原始資料
│   ├── digest_posts.json    # 產生的每週週報貼文串
│   └── spotlight_posts.json # 自動篩選之單場焦點爆款貼文
├── run_weekly_digest.py     # 整合排程主程式
└── config.yaml              # 系統配置
```

---

## 🧪 測試驗證

```bash
# 執行所有單元測試（包含策展格式化器測試）
./venv/bin/python -m unittest discover -s src/tests
```
