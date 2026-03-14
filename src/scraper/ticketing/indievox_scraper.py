"""Indievox Scraper"""
from typing import Dict, List, Optional
import re
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class IndievoxScraper(BaseScraper):
    """Indievox Event Scraper"""
    
    def scrape_events(self, url: str = "https://www.indievox.com/activity/list?type=table") -> List[Dict]:
        """
        Scrape Indievox events.
        Default to activity list page (Table View).
        """
        all_events = []
        
        # Scrape first few pages (e.g., 3 pages for radar)
        max_pages = self.config.get('max_pages', 3)
        
        logger.info(f"Scraping Indievox: {url}")

        for page in range(1, max_pages + 1):
            if page > 1:
                page_url = f"{url}&page={page}"
            else:
                page_url = url
            
            logger.info(f"Fetching Indievox page {page}...")
            # Use Selenium for Indievox as well to bypass potential bot detection and handle dynamics
            soup = self.fetch_with_selenium(page_url, wait_time=3)
            if not soup: break
            
            # Find event items in Table View
            event_rows = soup.select('tr.fcTxt')
            
            page_events = []
            for row in event_rows:
                event_data = self.parse_event(row)
                if event_data:
                    # Fetch detail to get image since table view lacks images
                    if event_data.get('source'):
                        detail = self._fetch_detail(event_data['source'])
                        if detail:
                            event_data.update(detail)
                    page_events.append(event_data)
            
            if not page_events:
                logger.info("No events found on page. Stopping.")
                break
                
            all_events.extend(page_events)
            
        logger.info(f"Indievox: Scraped {len(all_events)} events")
        return all_events

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for high-res image."""
        try:
            # Usually detail page is easily accessible
            soup = self.fetch_page(url)
            if not soup: return {}
            
            detail = {}
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                detail["image_url"] = og_img.get('content')
                
            return detail
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {url}: {e}")
            return {}

    def parse_event(self, element) -> Optional[Dict]:
        """Parse Indievox event element (Table View Row)"""
        try:
            # 1. Title & Link
            link = element.select_one('a.fcLightBlue')
            if not link: return None
            
            name = link.get_text(strip=True)
            event_url = link['href']
            if not event_url.startswith('http'):
                event_url = f"https://www.indievox.com{event_url}"
                
            # 2. Date
            # Table View: date is usually in first td
            tds = element.find_all('td')
            date_str = tds[0].get_text(strip=True) if tds else ""
            date_match = re.search(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', date_str)
            date = date_match.group(1).replace('/', '-') if date_match else None
            
            # 3. Venue
            # Table View: venue is usually in 3rd td
            venue = tds[2].get_text(strip=True) if len(tds) >= 3 else "Live House (Indievox)"
            
            # 4. Image
            # Note: Table View doesn't show images. 
            # Images are typically needed for Threads. 
            # We can either fetch detail or use a placeholder/default if needed.
            # For now, stick with what we can get or leave None.
            image_url = None 
            
            return {
                "activity_name": name,
                "performers": [],
                "date": date,
                "time": "Unknown",
                "venue": venue,
                "city": "Unknown",
                "is_free": "unknown",
                "source": event_url,
                "image_url": image_url,
                "note": "Scraped from Indievox (Table View)",
                "reliability": "official"
            }
        except Exception as e:
            logger.warning(f"Error parsing Indievox event: {e}")
            return None
