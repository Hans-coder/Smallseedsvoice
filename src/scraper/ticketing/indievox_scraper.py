from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class IndievoxScraper(BaseScraper):
    """iNDIEVOX Scraper"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape iNDIEVOX music events.
        """
        if not url:
            url = "https://www.indievox.com/activity/list"
            
        # iNDIEVOX is usually static friendly, but check request headers
        soup = self.fetch_page(url)
        if not soup:
            logger.error(f"Failed to fetch iNDIEVOX page: {url}")
            return []
            
        events = []
        # Structure: <div class="thumbnails activity"> ...
        event_items = soup.find_all('div', class_='thumbnails activity')
        
        for item in event_items:
            event_data = self.parse_event(item)
            if event_data:
                events.append(event_data)
                
        logger.info(f"iNDIEVOX: Scraped {len(events)} events from {url}")
        return events

    def parse_event(self, element) -> Optional[Dict]:
        try:
            # Check if this is wrapped in an <a> tag directly or if a is inside
            # In dump: <a href="..."><div class="col-md-12 ..."> ... </a>
            # The 'element' is the div.thumbnails.activity.
            # Usually the <a> is the immediate child or the wrapper.
            # In dump: <div class="thumbnails activity"><a href="...">...</a></div>
            
            link_tag = element.find('a')
            if not link_tag:
                return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://www.indievox.com{event_url}"
                
            # Title
            # <div class="multi_ellipsis">Title</div>
            title_div = element.find(class_='multi_ellipsis')
            name = title_div.get_text(strip=True) if title_div else "Unknown"
            
            # Date
            # <div class="date">2026/01/04 (日) </div>
            date_div = element.find(class_='date')
            time_str = date_div.get_text(strip=True) if date_div else "Unknown"
            
            # Image
            # <div class="wrap"><img src="..."></div>
            # Note: The img might have onerror attribute
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            # iNDIEVOX usually shows specific music events
            return {
                'name': name,
                'location': 'See Details', # Location specific usually in detail page
                'time': time_str,
                'price_type': 'Unknown', # Need detail page for price or interpret 'Free' keyword
                'image_url': image_url,
                'source_url': event_url,
                'platform': 'indievox'
            }
            
        except Exception as e:
            logger.error(f"Error parsing iNDIEVOX item: {e}")
            return None
