"""Ticket Plus (遠大售票) Scraper"""
from typing import Dict, List, Optional
import re
from datetime import datetime, timedelta
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.text_cleaners import refine_image_url, clean_event_title
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger(__name__)

class TicketPlusScraper(BaseScraper):
    """Ticket Plus Event Scraper"""
    
    def scrape_events(self, url: str = "https://ticketplus.com.tw/") -> List[Dict]:
        """
        Scrape Ticket Plus activities.
        """
        logger.info(f"Scraping Ticket Plus: {url}")
        
        # Ticket Plus uses Vuetify/Vue, needs Selenium and potentially multiple scrolls
        soup = self.fetch_with_selenium(url, wait_time=5)
        if not soup: return []
        
        event_cards = soup.select('div.v-card.v-card--link')
        logger.info(f"Ticket Plus: Found {len(event_cards)} potential cards")
        
        all_events = []
        for card in event_cards:
            event_data = self.parse_event(card)
            if event_data:
                # Early Date & Keyword Filter
                today_dt = datetime.now()
                today = today_dt.strftime("%Y-%m-%d")
                max_date = (today_dt + timedelta(days=5)).strftime("%Y-%m-%d")
                if event_data.get('date'):
                    if event_data['date'] < today or event_data['date'] > max_date:
                        continue
                    
                name_check = str(event_data.get('name', '')).lower()
                is_strict_classical = any(k in name_check for k in ['交響', '管樂', '弦樂', '國樂', '愛樂', '協奏曲', '獨奏', '古典'])
                if is_strict_classical: continue
                ignore_keywords = ['音樂劇', '兒童', '合唱', '室內樂', '大師班', '親子', '芭蕾', '舞劇', '講座', '音樂會', '讀劇', '相聲', '脫口秀', '音樂家']
                if any(k in name_check for k in ignore_keywords) and not 'live' in name_check and not '樂團' in name_check:
                    continue
                    
                if event_data.get('ticket_url'):
                    detail = self._fetch_detail(event_data['ticket_url'])
                    if detail:
                        event_data.update(detail)
                all_events.append(event_data)
                
        logger.info(f"Ticket Plus: Scraped {len(all_events)} events")
        return all_events

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for performers and start time."""
        if not url: return {}
        try:
            soup = self.fetch_with_selenium(url, wait_time=3)
            if not soup: return {}
            
            detail = {
                "performers": [],
                "start_time": None,
                "price": None,
                "ticket_sale_date": None
            }

            # Ticket Plus structure: look for text containing 演出時間, 演出者
            full_text = soup.get_text(separator='\n')
            import re
            
            # Start time extraction
            time_match = re.search(r'演出時間.*?(?:[:：\s]+)?(\d{2}:\d{2})', full_text)
            if time_match:
                detail["start_time"] = time_match.group(1)

            # Performers extraction
            match = re.search(r'(?:演出團隊|演出者|卡司|Lineup|Cast|演出陣容|共演)[:：\s]+([^\n]+)', full_text, re.IGNORECASE)
            if match:
                raw_performers = match.group(1).replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                detail["performers"] = [p.strip() for p in raw_performers if p.strip()]

            # Price extraction
            price_match = re.search(r'(?:票價|售價)[:：\s]+([^\n]+)', full_text)
            if price_match:
                detail["price"] = price_match.group(1)[:50].strip()

            # Sale date extraction
            sale_match = re.search(r'(?:啟售時間|售票時間)[:：\s]+([^\n]+)', full_text)
            if sale_match:
                detail["ticket_sale_date"] = sale_match.group(1)[:50].strip()

            return detail
        except Exception as e:
            logger.warning(f"Failed to fetch detail for Ticket Plus {url}: {e}")
            return {}

    def parse_event(self, element) -> Optional[Dict]:
        """Parse Ticket Plus event card"""
        try:
            # 1. Title
            title_tag = element.select_one('.v-card__title')
            if not title_tag: return None
            raw_title = title_tag.get_text(strip=True)
            name = clean_event_title(raw_title)
            
            # 2. Link
            # The card itself might be a link or have a data attribute
            # But usually it's wrapped or the whole div is clickable. 
            # If we are in the list, we might need to find the link.
            # In many Vuetify setups, it's just a div with a click listener. 
            # However, for SEO they often have a hidden 'a' or use role="link"
            link_tag = element.find('a')
            if link_tag and link_tag.get('href'):
                event_url = link_tag['href']
            else:
                # If no direct link, we might need to construct it or skip.
                # Actually, many modern cards use a hidden anchor for accessibility.
                # Let's try to find any link inside.
                link = element.get('href') # If it's an 'a' tag itself
                if not link:
                     # Check if it has a specific path we can guess
                     # E.g. /activity/XXXXX
                     # Let's look for any ID-like string
                     img_div = element.select_one('.v-image')
                     if img_div and img_div.get('id'):
                         # Fallback guess if link not found
                         pass
                event_url = link or ""
            
            if event_url and not event_url.startswith('http'):
                event_url = f"https://ticketplus.com.tw{event_url}"

            # 3. Date
            date_tag = element.select_one('.mdi-calendar')
            date_str = ""
            if date_tag:
                parent_span = date_tag.find_parent('span') or date_tag.find_next('span')
                if parent_span:
                    date_str = parent_span.get_text(strip=True)
            
            date_iso = parse_taiwan_date(date_str)
            
            # 4. Image
            img_div = element.select_one('.v-image__image')
            image_url = None
            if img_div and img_div.get('style'):
                style = img_div['style']
                # extract url("...")
                match = re.search(r'url\("?(.+?)"?\)', style)
                if match:
                    image_url = refine_image_url(match.group(1))

            # 5. Venue
            # Often venue is in the title or follows a specific icon (mdi-map-marker)
            venue = "See Details"
            loc_tag = element.select_one('.mdi-map-marker')
            if loc_tag:
                parent_span = loc_tag.find_parent('span') or loc_tag.find_next('span')
                if parent_span:
                    venue = parent_span.get_text(strip=True)

            activity_id = f"ticketplus_{name}_{date_iso}"
            
            return {
                "activity_id": activity_id,
                "name": name,
                "activity_type": "concert",
                "performers": [], # Will be updated by detail
                "date": date_iso,
                "start_time": None, # Will be updated by detail
                "venue_name": venue,
                "city": "Unknown",
                "price": None, # Will be updated by detail
                "ticket_sale_date": None, # Will be updated by detail
                "ticket_platform": "Ticket Plus",
                "ticket_url": event_url,
                "image_url": image_url,
                "note": "Scraped from Ticket Plus"
            }
        except Exception as e:
            logger.warning(f"Error parsing Ticket Plus card: {e}")
            return None
