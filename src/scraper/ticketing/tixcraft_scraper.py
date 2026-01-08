"""tixCraft Scraper"""
from typing import Dict, List, Optional
import time
from datetime import datetime
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger(__name__)

class TixCraftScraper(BaseScraper):
    """tixCraft Event Scraper"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape tixCraft events.
        """
        if not url:
            # Main list
            url = "https://tixcraft.com/activity/list/26_27"
            
        logger.info(f"Fetching tixCraft events...")
        # tixCraft is heavy on anti-bot, so we use Selenium with gentle settings
        soup = self.fetch_with_selenium(url, wait_time=5)
            
        if not soup:
            return []
            
        events = []
        # Normal list: .thumbnails > .col-md-3
        event_items = soup.select('.thumbnails .col-md-3') or soup.select('.activity .col-md-3')
        
        for item in event_items:
            event_data = self.parse_event(item)
            if event_data:
                events.append(event_data)
                
        logger.info(f"tixCraft: Scraped {len(events)} events")
        return events

    def parse_event(self, element) -> Optional[Dict]:
        try:
            link_tag = element.find('a')
            if not link_tag: return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://tixcraft.com{event_url}"
                
            # Title
            title_div = element.find(class_='multi_ellipsis')
            name = title_div.get_text(strip=True) if title_div else "Unknown"
            
            # Date
            date_div = element.find(class_='date')
            raw_time = date_div.get_text(strip=True) if date_div else ""
            date_iso = parse_taiwan_date(raw_time)
            
            # Image
            # <div class="thumbnails ..."><img src="..."></div>
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            activity_id = f"tixcraft_{name}_{date_iso}"
            
            return {
                "activity_id": activity_id,
                "activity_name": name,
                "activity_type": "concert",
                "performers": [],
                "date": date_iso,
                "start_time": None,
                "venue_name": "See Details",
                "city": "Unknown",
                "price": None,
                "ticket_platform": "tixCraft",
                "ticket_url": event_url,
                "image_url": image_url
            }
        except Exception as e:
            logger.error(f"Error parsing tixCraft item: {e}")
            return None
