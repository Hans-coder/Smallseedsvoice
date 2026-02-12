"""Indievox Scraper"""
from typing import Dict, List, Optional
import re
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class IndievoxScraper(BaseScraper):
    """Indievox Event Scraper"""
    
    def scrape_events(self, url: str = "https://www.indievox.com/activity/list") -> List[Dict]:
        """
        Scrape Indievox events.
        Default to activity list page.
        """
        all_events = []
        
        # Scrape first few pages (e.g., 3 pages for radar)
        max_pages = self.config.get('max_pages', 3)
        
        logger.info(f"Scraping Indievox: {url}")

        for page in range(1, max_pages + 1):
            if page > 1:
                # Indievox pagination might be different, but typically ?page=N
                # Need to verify if this works, otherwise just page 1 for now
                page_url = f"{url}?page={page}"
            else:
                page_url = url
            
            logger.info(f"Fetching Indievox page {page}...")
            soup = self.fetch_page(page_url)
            if not soup: break
            
            # Find event items
            # Based on typical bootstrap structure or similar
            # Need to be robust. Look for common containers.
            # Indievox usually has a table or grid. 
            # Trying to find by class containing 'event' or 'activity'
            
            # Strategy: Look for specific structure seen in data/radar_events.json images
            # Images are like: https://indievox.static.tixcraft.com/images/activity/...
            
            # Let's look for known structure (from prior knowledge or guess)
            # Usually: <div class="table-responsive">...
            
            event_rows = soup.find_all('tr')
            # If standard table not found, try card style
            if not event_rows or len(event_rows) < 5:
                 event_cards = soup.find_all('div', class_=lambda c: c and ('card' in c or 'col-' in c))
                 # This is risky without seeing HTML.
                 # Let's assume table for activity/list if it exists.
                 pass

            # Fallback to scraping whatever looks like an event
            # Look for links containing '/activity/detail/'
            links = soup.find_all('a', href=lambda h: h and '/activity/detail/' in h)
            
            seen_links = set()
            page_events = []
            
            for link in links:
                href = link['href']
                if href in seen_links: continue
                seen_links.add(href)
                
                # Usually the link wraps the whole item or title
                # Try to parse the parent container
                container = link.find_parent('tr') or link.find_parent('div', class_=lambda c: c and 'col' in c)
                
                if container:
                    event_data = self.parse_event(container)
                    if event_data:
                        page_events.append(event_data)
            
            if not page_events:
                logger.info("No events found on page. Stopping.")
                break
                
            all_events.extend(page_events)
            
        logger.info(f"Indievox: Scraped {len(all_events)} events")
        return all_events

    def parse_event(self, element) -> Optional[Dict]:
        """Parse Indievox event element"""
        try:
            # Try to find title
            title_tag = element.find(['h4', 'h5', 'h3', 'a'], class_=lambda c: c and ('title' in c or 'name' in c))
            # If failing, find the link with text
            link = element.find('a', href=lambda h: h and '/activity/detail/' in h)
            
            if not link: return None
            
            name = link.get_text(strip=True)
            if not name and title_tag:
                name = title_tag.get_text(strip=True)
            
            if not name: return None # Skip empty names
            
            event_url = link['href']
            if not event_url.startswith('http'):
                event_url = f"https://www.indievox.com{event_url}"
                
            # Date Parsing
            # Look for 2026/01/23 type text
            text_content = element.get_text()
            date_match = re.search(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', text_content)
            date = date_match.group(1).replace('/', '-') if date_match else None
            
            # Image
            img = element.find('img')
            image_url = img['src'] if img else None
            
            # Venue
            # Often near date
            # Hard to parse strictly without specific selector
            venue = "Live House (Indievox)" # Default
            
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
                "note": "Scraped from Indievox",
                "reliability": "official"
            }
        except Exception as e:
            logger.warning(f"Error parsing Indievox event: {e}")
            return None
