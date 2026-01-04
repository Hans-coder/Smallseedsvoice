from typing import Dict, List, Optional
import time
from bs4 import BeautifulSoup
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class OpentixScraper(BaseScraper):
    """OPENTIX Scraper"""
    
    def scrape_events(self, url: str = "https://www.opentix.life/search?q=音樂") -> List[Dict]:
        """
        Scrape OPENTIX music events.
        Args:
            url: OPENTIX search URL
        """
        logger.info(f"Fetching OPENTIX events from {url} using Selenium...")
        soup = self._fetch_with_selenium(url)
            
        if not soup:
            return []
            
        events = []
        # OPENTIX Card Selector
        event_items = soup.select('a.oa-card-program-with-info')
        
        for item in event_items:
            event_data = self.parse_event(item)
            if event_data:
                events.append(event_data)
                
        logger.info(f"OPENTIX: Scraped {len(events)} events from {url}")
        return events

    def parse_event(self, element) -> Optional[Dict]:
        try:
            # Link is the element itself
            event_url = element.get('href')
            if not event_url: return None
            
            if not event_url.startswith('http'):
                event_url = f"https://www.opentix.life{event_url}"
                
            # Title: span.info-title
            title_tag = element.find('span', class_='info-title')
            if not title_tag:
                 title_tag = element.find('h3')
            name = title_tag.get_text(strip=True) if title_tag else "Unknown"
            
            # Time: p inside infos
            infos_div = element.find('div', class_='infos')
            p_tags = infos_div.find_all('p') if infos_div else element.find_all('p')
            
            time_str = "Unknown"
            location = "See Details"
            
            # Usually first p is time, second might be location if present
            if len(p_tags) >= 1:
                time_str = p_tags[0].get_text(strip=True)
            if len(p_tags) >= 2:
                location = p_tags[1].get_text(strip=True)
            
            # Image: img inside oa-card-img
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            if image_url and not image_url.startswith('http'):
                image_url = f"https://www.opentix.life{image_url}"
            
            return {
                'name': name,
                'location': location,
                'time': time_str,
                'price_type': 'Unknown',
                'image_url': image_url,
                'source_url': event_url,
                'platform': 'opentix'
            }
        except Exception as e:
            logger.error(f"Error parsing OPENTIX item: {e}")
            return None

    def _fetch_with_selenium(self, url: str):
        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC

            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")

            driver = webdriver.Chrome(options=chrome_options)
            driver.get(url)

            # Wait for at least one card to appear
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.oa-card-program-with-info"))
                )
                # Extra wait for dynamic content
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Wait for OPENTIX cards timed out: {e}")

            html = driver.page_source
            driver.quit()

            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.error(f"Selenium fetch failed: {e}")
            return None
