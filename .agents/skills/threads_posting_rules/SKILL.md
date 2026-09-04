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

3. **Content Format (發文格式)**:
   - Cover post: `音樂活動懶人包 (MM/DD (週X) - MM/DD (週X))\n\n下週共有 N 場演出！\n詳細資訊請看下方整理 👇`
   - Date header: `📅 MM/DD (週X)`
   - Event line: `• [城市] 活動名稱 @ 場地名稱` — 城市放最前面用方括號，場地保留原始名稱，不刪除其中的城市字
   - Hot event prefix: `🔥 [城市] 活動名稱 @ 場地`
   - Discovery event prefix: `✨ [城市] 活動名稱 @ 場地`
   - 若無場地資訊：`• [城市] 活動名稱`（不加 @）
   
   **範例：**
   ```
   音樂活動懶人包 (09/08 (週一) - 09/14 (週日))
   
   下週共有 12 場演出！
   詳細資訊請看下方整理 👇
   
   📅 09/08 (週一)
   • [台北] 爛泥發芽 @ 河岸留言
   ✨ [台南] 新人樂團 @ 台灣好店
   
   📅 09/13 (週六)
   🔥 [台北] 大港開唱 @ Legacy Taipei
   • [高雄] 另一場演出 @ 駁二
   ```

4. **Content Organization & AI**:
   - We use Google Gemini for AI-powered content organization (e.g., extracting performers, cleaning up text).
   - Ensure the final generated threads content feels natural: strip out excessive emojis and hashtags if the source contains too many.
   - **CRITICAL**: AI polishing must NOT reduce event count. If AI output has fewer events than input, fall back to the original text.

5. **Scheduling Logic（排程邏輯）**:
   - Target: **下一個完整日曆週（週一到週日）**
   - Both workflows (StreetVoice on Mon/Thu and Supplemental on Mon/Thu) target the SAME week window, so Discord notifications are consistent.
   - Window calculation: `next Monday = today + (7 - weekday) % 7 days` (if today is Monday, use next next Monday so it's always a future full week)
   - End date: `start + 6 days 23:59:59`

6. **Radar Watchlist**:
   - `config.yaml` → `radar.watch_keywords` contains popular artists & festivals to monitor daily.
   - `detect_trending.py` reads this list and queries KKTIX search API per keyword.
   - This catches events on organizer subdomains that don't appear in the main KKTIX events page.
   - To add new artists: edit `config.yaml` `radar.watch_keywords` list.

7. **Event Coverage Sources**:
   | Platform | Purpose | Notes |
   |----------|---------|-------|
   | StreetVoice | Discovery (indie/live) | Runs first, others exclude its events |
   | KKTIX | Major concerts | Main page + keyword search for subdomains |
   | iNDIEVOX | Indie concerts | |
   | tixCraft | Large concerts | |
   | TicketPlus | Concerts | |
   | Accupass | Music festivals, concerts | URL: `?c=music` (all price types) |

8. **Deployment**:
   - Scheduled via GitHub Actions (`digest_streetvoice.yml` and `digest_supplemental.yml`).
   - If workflows change, ensure environment variables and dependencies are properly cached and maintained.
