# Smallseedsvoice — 台灣音樂活動自動化系統

自動偵測、整理並發佈台灣音樂演出資訊到 [Threads](https://threads.net) 的自動化工具。

---

## 系統架構

```
主線 A：StreetVoice 每週精選
  digest_streetvoice.yml（週一、週四）
    └─► run_weekly_digest.py
    └─► Threads 發文（免費 / 付費活動懶人包）

主線 B：雷達快訊（人工確認發文）
  radar_detect.yml（每天 09:00）
    └─► detect_trending.py
    └─► Discord 候選清單通知
         ↓ 確認後本地填表
  radar_form_server.py（手機可操作，http://[IP]:5050）
         ↓ git push
  radar_post.yml（GitHub Actions 手動觸發）
    └─► Threads 發文

補充 Job（每週一、週四）：
  digest_supplemental.yml
    └─► KKTIX / iNDIEVOX / tixCraft / TicketPlus 比對去重
    └─► Discord 通知（不自動發 Threads）
```

---

## Workflows

| 名稱 | 排程 | 說明 |
|------|------|------|
| `digest_streetvoice.yml` | 週一、週四 10:00 | StreetVoice 主力抓取 → Threads |
| `radar_detect.yml` | 每天 09:00（+隨機延遲）| 偵測熱門活動候選 → Discord |
| `radar_post.yml` | 手動觸發 | 讀取確認清單 → Threads（含 Dry Run 模式）|
| `digest_supplemental.yml` | 週一、週四 10:30 | 補充平台比對去重 → Discord |

---

## 目錄結構

```
.
├── .github/workflows/       # GitHub Actions workflows
├── scripts/
│   ├── detect_trending.py   # 每日熱門活動偵測（KKTIX + SV + IG）
│   ├── radar_form_server.py # 本地 web 表單（Flask，手機可操作）
│   ├── post_radar_manual.py # 雷達快訊發文腳本
│   ├── notify_discord.py    # Discord 通知
│   └── create_social_cards.py # 社群卡片產生
├── src/
│   ├── scraper/
│   │   ├── discovery/
│   │   │   └── streetvoice_scraper.py
│   │   ├── ticketing/
│   │   │   ├── kktix_scraper.py
│   │   │   ├── indievox_scraper.py
│   │   │   ├── tixcraft_scraper.py
│   │   │   └── ticketplus_scraper.py
│   │   └── instagram_scraper.py
│   ├── processor/
│   │   ├── digest_builder.py
│   │   ├── ai_summarizer.py
│   │   └── image_handler.py
│   ├── threads/
│   │   └── threads_poster.py
│   └── utils/
│       ├── discord_notifier.py
│       ├── text_cleaners.py
│       ├── date_parser.py
│       └── logger.py
├── data/
│   ├── radar_manual.json    # 手動確認的雷達快訊活動
│   ├── trending_concerts.json # 每日偵測結果
│   ├── streetvoice_raw.json # SV 快取（每日更新）
│   ├── digest_raw.json      # 懶人包暫存
│   └── events.db            # SQLite 演出者追蹤
├── run_weekly_digest.py     # 每週懶人包主程式
├── requirements.txt
└── config.yaml
```

---

## 雷達快訊操作流程

1. 每天早上收到 **Discord 通知**（KKTIX + StreetVoice + IG 候選清單）
2. 自行至官方平台確認**正確售票日期與資訊**
3. 本機執行 `python3 scripts/radar_form_server.py`
4. 用**手機或電腦**開啟 `http://[電腦IP]:5050`，填入確認的活動
5. `git add data/radar_manual.json && git commit -m "update radar" && git push`
6. 到 **GitHub Actions → Radar - 手動發文**：
   - 先勾選 `dry_run = true` 預覽
   - 確認無誤後取消勾選正式發文

---

## 環境變數（GitHub Secrets）

| Secret | 用途 |
|--------|------|
| `THREADS_ACCESS_TOKEN` | Threads Graph API 發文 |
| `DISCORD_WEBHOOK_URL` | Discord 通知 |
| `GEMINI_API_KEY` | AI 摘要生成（懶人包）|
