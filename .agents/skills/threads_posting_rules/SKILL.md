---
name: Taiwan Music Events Automation Rules
description: Context and rules for the Taiwan Music Events automation project, including scraper logic and Threads integration.
---

# Taiwan Music Events Automation

## Project Context
This project automates the curation and posting of Taiwan music event information to Threads. It utilizes multiple data pipelines (KKTIX, iNDIEVOX, tixCraft, TicketPlus, StreetVoice) and runs on GitHub Actions.

## Key Rules & Guidelines

1. **Scraping Frameworks**:
   - Use Playwright/Selenium for scraping dynamic platforms.
   - Always consider bot detection bypass logic.
   - Use robust, flexible CSS selectors to handle dynamic structural changes on ticket platforms.

2. **Threads API Constraints**:
   - **Image URLs**: Images posted to the Threads API **must** be publicly accessible URLs. Do not attempt to use local file paths, as the API will reject them.
   - **Splitting**: Threads have character limits. Implement and maintain optimized thread splitting logic (~500 characters per post, grouped logically without cutting off sentences).

3. **Content Organization & AI**:
   - We use Google Gemini for AI-powered content organization (e.g., extracting performers, cleaning up text).
   - Ensure the final generated threads content feels natural: strip out excessive emojis and hashtags if the source contains too many.

4. **Date & Scheduling Logic**:
   - We target events for the **next week** (adding 8 days from the cron execution date) rather than the current week. This gives users more lead time to plan.
   - Date parsing must handle multiple formats robustly.

5. **Deployment**:
   - Scheduled via GitHub Actions (`digest_streetvoice.yml` and `digest_supplemental.yml`).
   - If workflows change, ensure environment variables and dependencies are properly cached and maintained.
