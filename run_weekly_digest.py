import logging
import datetime
from src.scraper.music_sites import GenericMusicScraper
from src.processor.digest_builder import DigestBuilder
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger("weekly_digest")

def main():
    logger.info("Starting Weekly Digest Pipeline...")
    
    # Configuration
    # In a real scenario, load from config.yaml
    target_url = "https://example.com/free-events" # Placeholder for the site we were scraping
    # Previously 'scrape_activity_radar.py' was used.
    # We should use a real URL or restore the specific scraper logic.
    # For now, this connects the scheduler to a functional script.
    
    # 1. Scrape
    scraper = GenericMusicScraper(config={"request_delay": 2})
    events = scraper.scrape_events(target_url)
    
    if not events:
        logger.warning("No free events found. Aborting digest.")
        return

    # 2. Process
    start_date = datetime.datetime.now()
    end_date = start_date + datetime.timedelta(days=7)
    builder = DigestBuilder(config={"ai_enrichment": True})
    posts = builder.build_digest(events, start_date, end_date)
    
    # 3. Post
    # Access Token would be loaded from env
    # poster = ThreadsPoster(...)
    # poster.post_thread(posts)
    
    logger.info(f"Weekly Digest run complete. Prepared {len(posts)} posts.")

if __name__ == "__main__":
    main()
