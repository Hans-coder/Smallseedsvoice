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
        # Strict Music only (tag 13)
        if not url:
            # Default behavior: Scrape Homepage AND Music Tag
            urls_to_scrape = [
                ("https://kktix.com", False), # Homepage, no pagination
                ("https://kktix.com/events?event_tag_ids_in=13", True) # Music Tag, with pagination
            ]
        else:
            urls_to_scrape = [(url, True)]
            
        all_events = []
        max_pages = self.config.get('max_pages', 5)
        
        seen_urls = set()

        for target_url, do_pagination in urls_to_scrape:
            current_max = max_pages if do_pagination else 1
            base_url = target_url # Simplify logic for paging
            
            logger.info(f"Scraping KKTIX: {target_url} (Pagination: {do_pagination})")

            for page in range(1, current_max + 1):
                if do_pagination and page > 1:
                    page_url = f"{base_url}&page={page}"
                else:
                    page_url = base_url
                
                logger.info(f"Fetching KKTIX page {page}: {page_url}...")
                
                soup = self.fetch_with_selenium(page_url, wait_time=2)
                if not soup: break
                
                # Homepage might use different tabs, but checks confirmed ul.events > li works
                event_items = soup.select('ul.events > li')
                if not event_items:
                    logger.info(f"No more events found on page {page}")
                    break
                    
                page_events = []
                for item in event_items:
                    event_data = self.parse_event(item)
                    if event_data:
                        # Dedup within this run
                        if event_data['ticket_url'] in seen_urls:
                            continue
                        seen_urls.add(event_data['ticket_url'])
                        
                        # Detail fetch for Venue
                        if event_data.get('ticket_url'):
                            detail = self._fetch_detail(event_data['ticket_url'])
                            if detail:
                                event_data.update(detail)
                        page_events.append(event_data)
                        time.sleep(1) # Polite delay
                
                all_events.extend(page_events)
                time.sleep(1)
                
                if not do_pagination:
                    break
            
        logger.info(f"KKTIX: Scraped {len(all_events)} events")
        return all_events

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for venue and sale time"""
        try:
            soup = self.fetch_with_selenium(url, wait_time=2)
            if not soup: return {}
            
            venue = "Unknown"
            sale_date = None
            price = None
            
            # Venue Extraction
            venue_tag = soup.find(string="地點")
            if venue_tag:
                row = venue_tag.find_parent('tr')
                if row:
                    td = row.find('td')
                    if td:
                        venue = td.get_text(strip=True).split(maxsplit=1)[0]
            
            # Ticket Table Parsing (New Logic)
            # Table headers usually: 票種, 販售時間, 售價
            # We look for a table containing "販售時間"
            tables = soup.find_all('table')
            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all('th')]
                if "販售時間" in headers:
                    # Found ticket table. Iterate rows.
                    rows = table.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        if not cols: continue
                        
                        # Assuming Order: Name, Time, Price (based on debug output)
                        # We need to map header index to be safe
                        try:
                            time_idx = headers.index("販售時間")
                            price_idx = headers.index("售價") if "售價" in headers else -1
                            
                            # Extract Time
                            if len(cols) > time_idx:
                                time_text = cols[time_idx].get_text(strip=True)
                                # Format: 2026/01/07 12:00(+0800)~...
                                # Take the part before "~"
                                start_str = time_text.split('~')[0].strip()
                                # Clean "(+0800)"
                                start_str = start_str.split('(')[0].strip()
                                
                                # Set as sale_date if not set (first row is usually main)
                                if not sale_date:
                                    sale_date = start_str
                                    
                            # Extract Price
                            if price_idx != -1 and len(cols) > price_idx:
                                price_text = cols[price_idx].get_text(strip=True)
                                if not price: # Take first price found
                                    price = price_text
                        except:
                            continue
                            
                    if sale_date:
                        break # Found our data

            # Fallback for old partial logic (if table not found)
            if not sale_date:
                 sale_tag = soup.find(string="報名開始") or soup.find(string="報名時間")
                 if sale_tag:
                    row = sale_tag.find_parent('tr')
                    if row and row.find('td'):
                        sale_date = row.find('td').get_text(strip=True)

            return {"venue_name": venue, "ticket_sale_date": sale_date, "price": price}
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {url}: {e}")
            return {}

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
                "image_url": image_url,
                "ticket_sale_date": None  # TODO: Implement detail scrape for sale date
            }
        except Exception as e:
            logger.error(f"Error parsing KKTIX item: {e}")
            return None
