"""tixCraft Scraper"""
from typing import Dict, List, Optional
import time
from datetime import datetime, timedelta
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
            url = "https://tixcraft.com/activity"
            
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
        
        event_items = soup.select('.row.align-items-center')
        
        for item in event_items:
            event_data = self.parse_event(item)
            if event_data:
                # Early Date & Keyword Filter
                today_dt = datetime.now()
                today = today_dt.strftime("%Y-%m-%d")
                max_date = (today_dt + timedelta(days=14)).strftime("%Y-%m-%d")
                if event_data.get('date'):
                    if event_data['date'] < today or event_data['date'] > max_date:
                        continue
                    
                name_check = str(event_data.get('name', '')).lower()
                is_strict_classical = any(k in name_check for k in ['交響', '管樂', '弦樂', '國樂', '愛樂', '協奏曲', '獨奏', '古典'])
                if is_strict_classical: continue
                ignore_keywords = ['音樂劇', '兒童', '合唱', '室內樂', '大師班', '親子', '芭蕾', '舞劇', '講座', '音樂會', '讀劇', '相聲', '脫口秀', '音樂家']
                if any(k in name_check for k in ignore_keywords) and not 'live' in name_check and not '樂團' in name_check:
                    continue
                    
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
            
            detail = {
                "performers": [],
                "start_time": None,
                "venue_name": None
            }
            
            # Extract from table/list in tixCraft detail page
            # Labels: 演出時間, 演出地點, 售票時間, 票價
            for label in ["售票時間", "票價", "演出時間", "演出地點", "場地"]:
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
                        elif label == "演出時間":
                            import re
                            time_match = re.search(r'(\d{2}:\d{2})', value)
                            if time_match:
                                detail["start_time"] = time_match.group(1)
                        elif label in ["演出地點", "場地"] and not detail["venue_name"]:
                            detail["venue_name"] = value.split('(')[0].strip() # Clean up basic venue string

            # Extract performers from intro or description
            intro_div = soup.select_one('.activity-intro') or soup.find('div', class_='intro')
            if intro_div:
                desc_text = intro_div.get_text(separator='\n')
                import re
                match = re.search(r'(?:演出團隊|演出者|卡司|Lineup|Cast|演出陣容|共演)[:：\s]+([^\n]+)', desc_text, re.IGNORECASE)
                if match:
                    raw_performers = match.group(1).replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                    detail["performers"] = [p.strip() for p in raw_performers if p.strip()]

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
            link_tag = element.select_one('.text-bold a')
            if not link_tag: return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://tixcraft.com{event_url}"
                
            # Title
            name = link_tag.get_text(strip=True)
            
            # Date
            date_div = element.select_one('.date')
            raw_time = date_div.get_text(strip=True) if date_div else ""
            date_iso = parse_taiwan_date(raw_time)
            
            # Image
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            activity_id = f"tixcraft_{name}_{date_iso}"
            
            # Venue
            venue_div = element.select_one('.text-med-light')
            venue = venue_div.get_text(strip=True) if venue_div else "See Details"

            return {
                "activity_id": activity_id,
                "name": name,
                "activity_type": "concert",
                "performers": [], # Will be updated by detail
                "date": date_iso,
                "start_time": None, # Will be updated by detail
                "venue_name": venue, # Will be updated by detail if better one found
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
