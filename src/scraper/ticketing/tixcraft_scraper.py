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
            # Main list - force table view for venue info
            url = "https://tixcraft.com/activity/list/26_27#display-table"
            
        logger.info(f"Fetching tixCraft events...")
        # tixCraft is heavy on anti-bot, so we use Selenium with gentle settings
        soup = self.fetch_with_selenium(url, wait_time=5)
            
        if not soup:
            return []
            
        events = []
        # Normal list: .thumbnails > .col-md-3
        # Table list: .activity-info-box within the table structure (selenium might render different DOM)
        # In table view, it's usually rows or divs. 
        # Verified selector: .activity-info-box contains text.
        # But wait, looking at my browser agent, it clicked a button. 
        # If I append #display-table, does it render cards or list?
        # Let's assume list view structure.
        # The selector .thumbnails .col-md-3 might be for grid view.
        # Let's try to match both or specific table view selector.
        
        # In table view: <div class="table-responsive">...
        # But actually, simpler: use generic selector that catches the items.
        
        event_items = soup.select('.thumbnails .col-md-3') or soup.find_all('div', class_='activity-info-box') or soup.select('.activity .col-md-3')
        
        for item in event_items:
            event_data = self.parse_event(item)
            if event_data:
                # Detail fetch
                if event_data.get('ticket_url'):
                    detail = self._fetch_detail(event_data['ticket_url'])
                    if detail:
                        event_data.update(detail)
                events.append(event_data)
                time.sleep(1) # Polite delay
                
        logger.info(f"tixCraft: Scraped {len(events)} events")
        return events

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for price and sale time"""
        try:
            soup = self.fetch_with_selenium(url, wait_time=1)
            if not soup: return {}
            
            # TixCraft detail page varies, but usually has metadata in a list or table
            # Sale Date: <span>售票時間</span> ...
            # Price: <span>票價</span> ...
            
            detail = {}
            
            # Try to find by label text
            for label in ["售票時間", "票價"]:
                target_tag = soup.find(string=lambda t: t and label in t)
                if target_tag:
                    # Look for value in parent's sibling or next element?
                    # Structure often: <li><span class='title'>Label</span> Content</li>
                    # or <tr><th>Label</th><td>Content</td></tr>
                    
                    parent = target_tag.find_parent('li') or target_tag.find_parent('tr')
                    if parent:
                        text = parent.get_text(" ", strip=True)
                        # Remove label from text
                        value = text.replace(label, "").strip().replace(":", "").strip()
                        
                        if label == "售票時間":
                            detail["ticket_sale_date"] = value
                        elif label == "票價":
                            detail["price"] = value

            # Extract high-res image from og:image
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                detail["image_url"] = og_img.get('content')
                
            return detail
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {url}: {e}")
            return {}

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
            
            # Venue - Try to find in text for table view
            venue = "Unknown"
            full_text = element.get_text(" | ", strip=True)
            parts = full_text.split('|')
            if len(parts) >= 3:
                # Naive guess: last part or part that looks like venue
                potential_venue = parts[-1].strip()
                if len(potential_venue) > 2 and not potential_venue[0].isdigit():
                     venue = potential_venue
            
            if venue == "Unknown": 
                 venue = "See Details"

            return {
                "activity_id": activity_id,
                "activity_name": name,
                "activity_type": "concert",
                "performers": [],
                "date": date_iso,
                "start_time": None,
                "venue_name": venue,
                "city": "Unknown",
                "price": None,
                "ticket_platform": "tixCraft",
                "ticket_url": event_url,
                "image_url": image_url,
                "ticket_sale_date": None  # TODO: Implement detail scrape for sale date
            }
        except Exception as e:
            logger.error(f"Error parsing tixCraft item: {e}")
            return None
