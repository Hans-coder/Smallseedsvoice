from typing import Dict, List, Optional
import time
from bs4 import BeautifulSoup
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class AccupassScraper(BaseScraper):
    """Accupass Scraper"""
    
    def scrape_events(self, url: str = "https://www.accupass.com/search?q=music") -> List[Dict]:
        """
        Scrape Accupass music events.
        Args:
            url: Accupass search URL
        """
        logger.info(f"Fetching Accupass events from {url} using Selenium...")
        soup = self._fetch_with_selenium(url)
            
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

    def _fetch_with_selenium(self, url: str):
        """Internal method to fetch page using Selenium (duplicated from KKTIX for now or should be in Base)"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from bs4 import BeautifulSoup

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)

            # Wait for content to load
            time.sleep(5)

            html = driver.page_source
            driver.quit()

            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.error(f"Selenium fetch failed: {e}")
            return None
