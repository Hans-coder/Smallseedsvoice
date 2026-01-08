"""KKTIX Scraper"""
from typing import Dict, List, Optional
import time
from datetime import datetime
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date, parse_time

logger = setup_logger(__name__)

class KktixScraper(BaseScraper):
    """KKTIX Event Scraper"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape KKTIX music events.
        """
        # Strict Music only (tag 13)
        if not url:
            url = "https://kktix.com/events?event_tag_ids_in=13"
            
        all_events = []
        max_pages = self.config.get('max_pages', 5)
        
        for page in range(1, max_pages + 1):
            page_url = f"{url}&page={page}"
            logger.info(f"Fetching KKTIX page {page}: {page_url}...")
            
            soup = self.fetch_with_selenium(page_url, wait_time=2)
            if not soup: break
            
            event_items = soup.select('ul.events > li')
            if not event_items:
                logger.info(f"No more events found on page {page}")
                break
                
            page_events = []
            for item in event_items:
                event_data = self.parse_event(item)
                if event_data:
                    page_events.append(event_data)
            
            all_events.extend(page_events)
            time.sleep(1)
            
        logger.info(f"KKTIX: Scraped {len(all_events)} events")
        return all_events

    def parse_event(self, element) -> Optional[Dict]:
        try:
            link_tag = element.find('a', class_='cover') or element.find('a')
            if not link_tag: return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://kktix.com{event_url}"
                
            # Basic Info
            title_container = element.find(class_='event-title')
            name = title_container.find('h2').get_text(strip=True) if title_container else "Unknown"
            
            # Time & Date
            # Format: 2025/11/11(二)
            time_tag = element.find(class_='date')
            raw_time = time_tag.get_text(strip=True) if time_tag else ""
            
            date_iso = parse_taiwan_date(raw_time)
            # KKTIX list view doesn't show specific start time usually, mostly date
            # We might need to fetch detail page for strict time, but for now leave null or scrape from detail if needed
            start_time = None 
            
            # Location
            # Often in .vcard text or description
            location = "Unknown" 
            city = "Unknown"
            # KKTIX list doesn't show venue clearly, usually needs detail scrape. 
            # For "Official Platform" script, accuracy is key?
            # User said "Fields (if available)". 
            # Let's keep it simple for now or fetch detail if mandated.
            
            # Image
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            # ID: Platform + Name + Date
            activity_id = f"kktix_{name}_{date_iso}"
            
            return {
                "activity_id": activity_id,
                "activity_name": name,
                "activity_type": "concert", # Default for music tag
                "performers": [], # Hard to extract from list
                "date": date_iso,
                "start_time": start_time,
                "venue_name": location,
                "city": city,
                "price": None, # Needs detail
                "ticket_platform": "KKTIX",
                "ticket_url": event_url,
                "image_url": image_url
            }
        except Exception as e:
            logger.error(f"Error parsing KKTIX item: {e}")
            return None
