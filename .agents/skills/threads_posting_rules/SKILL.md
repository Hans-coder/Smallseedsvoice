---
name: Taiwan Music Events Automation Rules
description: Context and rules for the Taiwan Music Events automation project, including scraper logic and Threads integration.
---

# Taiwan Music Events Automation

## Project Context
This project automates the curation and posting of Taiwan music event information to Threads. It utilizes multiple data pipelines (KKTIX, iNDIEVOX, tixCraft, TicketPlus, Accupass, StreetVoice) and runs on GitHub Actions.

## Key Rules & Guidelines

1. **Scraping Frameworks**:
   - Use Playwright/Selenium for scraping dynamic platforms.
   - Always consider bot detection bypass logic.
   - Use robust, flexible CSS selectors to handle dynamic structural changes on ticket platforms.
   - **KKTIX Subdomain**: Many events are hosted on organizer subdomains (e.g., `binliveco.kktix.cc`). Use both the main events page AND keyword search API to catch them.

2. **Threads API Constraints**:
   - **Image URLs**: Images posted to the Threads API **must** be publicly accessible URLs. Do not attempt to use local file paths, as the API will reject them.
   - **Splitting**: Threads have character limits. Implement and maintain optimized thread splitting logic (~500 characters per post, grouped logically without cutting off sentences).

3. **Content Format & Curation Modes (發文模式與格式)**:
   專案擺脫冰冷機器人純文字流水帳，採用**三維策展發文矩陣**：

   - **模式 A：單場爆款焦點 (Spotlight Post)**（重點衝流量與收藏數）：
     針對「免費音樂祭」、「大型焦點演出」發布單篇精緻圖文（參考 `@sky_silp` 格式）。
     ```text
     ⚑ 2026/10/02㊄ 18:00 《浪人祭前夜祭》（免費）

     ➤ 卡司陣容：
     ♥︎美秀集團 ♥︎怕胖團 ♥︎芒果醬

     ❑ 地點：[台南市] 安平觀夕平台 ❑

     ▶ 購票系統：KKTIX

     💬 免費入場太佛了吧！標記那個每次都喊沒錢聽團的朋友快衝 👥
     🔗 依展演空間看全台本週演出：見首頁連結
     ```

   - **模式 B：小聲音私心推 (Curator Pick)**（建立 IP 話語權與音樂品味）：
     挑選 1~2 組特色獨立樂團或 Livehouse 專場，撰寫真誠、懂聽團文化的推薦短評。
     ```text
     【小聲音私心推 🎧】《樂團名稱 專場巡演》

     現場吉他音牆壓迫感十足，主唱撕裂嗓音無可取代，今年必看的搖滾專場。
     🎵 推薦先聽這首入坑：〈歌曲名〉

     📅 時間：10/15 19:30
     📍 地點：[台北市] Legacy Taipei
     🎫 性質：售票

     💬 有聽過他們的舉手！你最喜歡他們現場哪首的氛圍？👇
     🔗 完整展演空間地圖與購票：首頁網站
     ```

   - **模式 C：升級版每週週報 (Smart Digest)**（資訊整合日曆）：
     Cover Post 包含亮點統計、引發討論之問句，並導流至展演空間網站：
     ```text
     【全台音樂活動週報 🎸】(09/21 (週一) - 09/27 (週日))

     下週全台共有 45 場音樂現場！
     ✨ 8 場完全免費戶外/市集活動、🔥 3 場焦點熱門大專場，聽團行事曆準備排起來 🏃‍♂️

     詳細每日場次請看下方串文整理 👇
     💬 這週你打算衝哪幾場？還是要去哪個 Livehouse 喝酒？留言區開聊！

     🗺️ 想依照「展演空間」或「縣市」秒查所有演出？首頁網站已同步更新！
     ```

4. **Threads 演算法與 CTA 準則 (Algorithm & Engagement Rules)**:
   - **拒絕生硬廣告詞**：嚴禁「歡迎按讚追蹤分享」，改為**「標記朋友（Tagging）」**、**「二選一表態」**或**「留言補遺推薦」**。
   - **發揮愛心符號效應**：演出者統一使用 `♥︎藝人名稱`，增加視覺辨識度與親和力。
   - **收藏數驅動**：明確標記「免費」或「售票」，高實用度促成讀者主動點擊儲存/收藏。

5. **產品分工：Threads 社群引流 ➡️ 展演空間網站沉澱**:
   - Threads 負責傳播話題與情緒發現。
   - 展演空間網站 (`web/index.html`) 提供依 Legacy、Revolver、The Wall、駁二等空間快速檢索，放置於個人簡介 (Link in Bio)。
   - 透過 `python scripts/build_web_data.py` 自動同步最新活動資料庫至 `web/data/events.json`。

6. **Scheduling Logic（排程邏輯）**:
   - Target: **下一個完整日曆週（週一到週日）**
   - 統一排程: `digest_weekly.yml`（每週一 10:00 執行，UTC 02:00），覆蓋同一完整週。
   - 同步產出 `data/digest_posts.json`、`data/spotlight_posts.json` 與 `web/data/events.json`。

7. **Event Coverage Sources**:
   | Platform | Purpose | Notes |
   |----------|---------|-------|
   | StreetVoice | Discovery (indie/live) | Runs first to capture indie performers & details |
   | KKTIX | Major concerts & subdomains | Official Atom feed (fast & Cloudflare-immune) |
   | iNDIEVOX | Indie concerts | Table view scraping |
   | tixCraft | Large concerts | Strict music filtering |
   | TicketPlus | Concerts | |

8. **Deployment & Transition**:
   - 核心排程: `digest_weekly.yml`（單一工作流程整合全平台，天然去重與資料融合）。
   - 管理伺服器: `python scripts/digest_server.py` 支援每週週報、單場焦點與私心推三種模式預覽、即時編輯與一鍵發布。

