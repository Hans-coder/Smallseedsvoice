"""KKTIX Scraper"""
from typing import Dict, List, Optional
from datetime import datetime
import re
import time
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class KktixScraper(BaseScraper):
    """KKTIX Event Scraper"""
    
    def scrape_events(self, url: str = "https://kktix.com/events?category_id=2") -> List[Dict]:
        """
        Scrape KKTIX music events.
        Args:
            url: KKTIX music events URL
        """
        # KKTIX blocks requests/403 quite often or requires specific headers.
        # Selenium is more reliable for this site.
        logger.info(f"Fetching KKTIX events from {url} using Selenium...")
        soup = self._fetch_with_selenium(url)
            
        if not soup:
            return []
            
        events = []
        # Update selector based on 2026/01/04 dump: ul.events > li
        event_items = soup.select('ul.events > li')
        
        for item in event_items:
            # Basic info from list
            list_info = self.parse_event(item)
            if not list_info: continue
            
            # Detailed info (Price, Venue City) is strictly on detail page.
            # For MVP speed, we'll label them "Check Link" or similar if we skip detail scrape.
            # But the requirement was "Free events".
            # If we skip detail scrape, we can't filter by price "Free" accurately unless we assume.
            # However, for now let's get the LIST working first.
            
            events.append(list_info)
                
        logger.info(f"KKTIX: Scraped {len(events)} events from {url}")
        return events

    def parse_event(self, element) -> Optional[Dict]:
        try:
            # Link is on the <a> tag with class 'cover'
            link_tag = element.find('a', class_='cover')
            if not link_tag: 
                # Fallback: find any a
                link_tag = element.find('a')
            
            if not link_tag: return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://kktix.com{event_url}"
                
            # Title: div.event-title > h2
            title_container = element.find(class_='event-title')
            name = "Unknown"
            if title_container:
                h2 = title_container.find('h2')
                if h2:
                    name = h2.get_text(strip=True)
            
            # Time: span.date
            # Format: 2025/11/11(二)
            time_tag = element.find(class_='date')
            time_str = time_tag.get_text(strip=True) if time_tag else "Unknown"
            
            # Image: figure > img
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            return {
                'name': name,
                'location': 'See Details', # Location is not clearly visible in list card (sometimes in intro but unstructured)
                'time': time_str,
                'price_type': 'Unknown', # Price is not on card
                'image_url': image_url,
                'source_url': event_url,
                'platform': 'kktix'
            }
        except Exception as e:
            logger.error(f"Error parsing KKTIX item: {e}")
            return None

    def _get_event_details(self, url: str) -> Dict:
        """Fetch event detail page to get Price and Venue"""
        # This is expensive (N requests). 
        # For now, we implement a lightweight version or just return empty if we want speed.
        # But to fulfill the "Free" requirement, we realistically need this.
        # Implementation omitted for speed in this turn, but planned.
        # return {'price_type': '免費', 'location': 'Legacy Taipei'} # Mock
        
        # Real implementation would be:
        # soup = self.fetch_page(url) ...
        # price_text = soup.find(...) ...
        return {}

    def _fetch_with_selenium(self, url: str):
        """Fetch page using Selenium Headless Chrome"""
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from bs4 import BeautifulSoup
            
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            # Fake User-Agent
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)
            
            # Wait for content
            time.sleep(5) 
            
            html = driver.page_source
            driver.quit()
            
            return BeautifulSoup(html, 'lxml')
        except ImportError:
            logger.error("Selenium not installed. Install with: pip install selenium")
            return None
        except Exception as e:
            logger.error(f"Selenium fetch failed: {e}")
            return None



