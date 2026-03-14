from typing import Dict, List, Optional
import time
from bs4 import BeautifulSoup
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AccupassScraper(BaseScraper):
    """Accupass Scraper"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape Accupass music events.
        """
        if not url:
            url = "https://www.accupass.com/search?c=music&p=free"
            
        logger.info(f"Fetching Accupass events from {url} using Selenium...")
        # Increase scrolls for Accupass since it uses infinite scroll
        soup = self.fetch_with_selenium(url, scroll=True, scroll_count=20)
            
        if not soup:
            return []
            
        events = []
        # Accupass Card Selector
        event_items = soup.select('div[class*="EventCard_home-event-card"]')
        
        if not event_items:
            # Try alternate selector for search results
            event_items = soup.select('div[class*="EventCard_event-card"]')

        for item in event_items:
            event_data = self.parse_event(item)
            if event_data:
                events.append(event_data)
                
        logger.info(f"Accupass: Scraped {len(events)} events from {url}")
        return events

    def parse_event(self, element) -> Optional[Dict]:
        try:
            # Link
            link_tag = element.find('a', href=True)
            if not link_tag: return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://www.accupass.com{event_url}"
                
            # Title: EventCard_event-name__...
            title_tag = element.find('p', class_=lambda x: x and 'event-name' in x.lower())
            if not title_tag:
                title_tag = element.find('p', class_=lambda x: x and 'event-title' in x.lower())
            
            name = title_tag.get_text(strip=True) if title_tag else "Unknown"
            
            # Time: EventCard_event-time__...
            time_tag = element.find('p', class_=lambda x: x and 'event-time' in x.lower())
            time_str = time_tag.get_text(strip=True) if time_tag else "Unknown"
            
            # Location
            location_tag = element.find(class_=lambda x: x and 'event-location' in x.lower())
            if not location_tag:
                 location_tag = element.find(class_=lambda x: x and 'event-location-type' in x.lower())
            
            location = "See Details"
            if location_tag:
                span = location_tag.find('span')
                location = span.get_text(strip=True) if span else location_tag.get_text(strip=True)

            # Image
            img_tag = element.find('img', class_=lambda x: x and 'event-photo-img' in x.lower())
            if not img_tag:
                img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            # Remove query parameters from thumbnail URLs to get high-res original
            if image_url and '?' in image_url:
                image_url = image_url.split('?')[0]
            
            return {
                'name': name,
                'location': location,
                'time': time_str,
                'price_type': 'Unknown',
                'image_url': image_url,
                'source_url': event_url,
                'platform': 'accupass'
            }
        except Exception as e:
            logger.error(f"Error parsing Accupass item: {e}")
            return None
