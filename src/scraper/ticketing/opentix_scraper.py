"""OPENTIX Scraper"""
from typing import Dict, List, Optional
import time
from datetime import datetime
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger(__name__)

class OpentixScraper(BaseScraper):
    """OPENTIX Scraper"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape OPENTIX music events.
        """
        if not url:
            # Comprehensive music categories
            url = "https://www.opentix.life/search/%20/ABOUT_TO_BEGIN?category=%E9%9F%B3%E6%A8%82-%E7%AE%A1%E7%B5%83%E6%A8%82%E5%9C%98&category=%E9%9F%B3%E6%A8%82-%E7%AE%A1%E6%A8%82%E5%9C%98&category=%E9%9F%B3%E6%A8%82-%E7%B5%83%E6%A8%82%E5%9C%98&category=%E9%9F%B3%E6%A8%82-%E5%AE%A4%E5%85%A7%E6%A8%82&category=%E9%9F%B3%E6%A8%82-%E5%90%88%E5%94%B1&category=%E9%9F%B3%E6%A8%82-%E7%8D%A8%E5%94%B1&category=%E9%9F%B3%E6%A8%82-%E7%8D%A8%E5%A5%8F&category=%E9%9F%B3%E6%A8%82-%E5%9C%8B%E6%A8%82&category=%E9%9F%B3%E6%A8%82-%E5%8B%95%E6%BC%AB%2F%E9%9B%BB%E5%BD%B1%E9%9F%B3%E6%A8%82%E6%9C%83&category=%E9%9F%B3%E6%A8%82-%E6%AD%8C%E5%8A%87&category=%E9%9F%B3%E6%A8%82-%E7%88%B5%E5%A3%AB%E6%A8%82&category=%E9%9F%B3%E6%A8%82-%E4%B8%96%E7%95%8C%2F%E6%B0%91%E6%97%8F&category=%E9%9F%B3%E6%A8%82-%E6%89%93%E6%93%8A%E6%A8%82&category=%E9%9F%B3%E6%A8%82-%E7%8F%BE%E4%BB%A3%E9%9F%B3%E6%A8%82&category=%E9%9F%B3%E6%A8%82-%E9%9F%B3%E6%A8%82%E5%8A%87%E5%A0%B4&category=%E9%9F%B3%E6%A8%82-%E6%B5%81%E8%A1%8C%E9%9F%B3%E6%A8%82&type=programs"
            
        logger.info(f"Fetching OPENTIX events...")
        soup = self.fetch_with_selenium(url, scroll=True, scroll_count=10, wait_time=5)
            
        if not soup:
            return []
            
        events = []
        event_items = soup.select('a.oa-card-program-with-info')
        
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
                
        logger.info(f"OPENTIX: Scraped {len(events)} events")
        return events

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for price and sale time"""
        try:
            soup = self.fetch_with_selenium(url, wait_time=2)
            if not soup: return {}
            
            detail = {
                "performers": [],
                "start_time": None,
                "venue_name": None
            }
            
            # OPENTIX JSON-LD provides highly structured data
            import json
            json_ld_tags = soup.find_all('script', type='application/ld+json')
            for tag in json_ld_tags:
                try:
                    data = json.loads(tag.string)
                    # Sometime it's a single object, sometimes it's a list. Find the Event object.
                    if isinstance(data, dict) and data.get('@type') == 'Event':
                        # Start time and Date
                        start_date_str = data.get('startDate')
                        if start_date_str and 'T' in start_date_str:
                            detail["date"] = start_date_str.split('T')[0]
                            detail["start_time"] = start_date_str.split('T')[1][:5]
                            
                        # Venue
                        location = data.get('location', {})
                        if isinstance(location, dict) and location.get('name'):
                            detail["venue_name"] = location.get('name').replace("：", "").strip()
                            
                        # Performers (often embedded in description)
                        desc_text = data.get('description', '')
                        if desc_text:
                            import re
                            # Common prefix for performers in OPENTIX description
                            match = re.search(r'(?:演出人員|演出團隊|演出者|卡司|Lineup|Cast|演出陣容)[:：\s]+(.*?)(?:【|$)', desc_text, re.IGNORECASE | re.DOTALL)
                            if match:
                                raw_perf = match.group(1).strip()
                                # Split by common separators and clean up
                                import re
                                items = re.split(r'[、｜|,|\n]', raw_perf)
                                detail["performers"] = [p.strip() for p in items if p.strip() and len(p.strip()) < 30]
                        
                        break # Found Event schema, no need to check other json-ld tags
                except Exception as e:
                    logger.debug(f"Error parsing JSON-LD: {e}")

            # Fallback for performers if JSON-LD parsing didn't catch them
            if not detail["performers"]:
                info_elements = soup.find_all(string=lambda t: t and any(k in t for k in ["演出團隊", "團隊", "演出者"]))
                for el in info_elements:
                    parent = el.find_parent('div') or el.find_parent('li')
                    if parent:
                        text = parent.get_text(" ", strip=True)
                        cleaned_perf = text.replace("演出團隊", "").replace("團隊", "").replace("演出者", "").replace("：", "").strip()
                        if cleaned_perf:
                            raw_performers = cleaned_perf.replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                            detail["performers"] = [p.strip() for p in raw_performers if p.strip() and len(p.strip()) < 30]
                            break

            # Fallback for start_time / venue from DOM if JSON-LD missing
            if not detail["start_time"] or not detail["venue_name"]:
                info_elements = soup.find_all(string=lambda t: t and any(k in t for k in ["演出時間", "時間", "地點", "場地"]))
                for el in info_elements:
                    parent = el.find_parent('div') or el.find_parent('li')
                    if parent:
                        text = parent.get_text(" ", strip=True)
                        if "時間" in el and detail["start_time"] is None:
                            import re
                            time_match = re.search(r'(\d{2}:\d{2})', text)
                            if time_match:
                                detail["start_time"] = time_match.group(1)
                        elif ("地點" in el or "場地" in el) and detail["venue_name"] is None:
                            cleaned_venue = text.replace("演出地點", "").replace("地點", "").replace("：", "").strip()
                            if cleaned_venue:
                                 detail["venue_name"] = cleaned_venue.split(" ")[0]

            # Also check the description content for performers if STILL not found
            if not detail["performers"]:
                description_div = soup.select_one('.content-wrapper') or soup.find('div', class_='content')
                if description_div:
                    desc_text = description_div.get_text(separator='\n')
                    import re
                    match = re.search(r'(?:演出團隊|演出者|卡司|Lineup|Cast|演出陣容|共演)[:：\s]+([^\n]+)', desc_text, re.IGNORECASE)
                    if match:
                        raw_performers = match.group(1).replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                        detail["performers"] = [p.strip() for p in raw_performers if p.strip()]
            
            # Sale Date
            # OPENTIX: "啟售時間" or similar
            # Often in <div class="side-bar"> ... <span class="label">啟售時間</span><span class="value">...</span>
            sale_label = soup.find(string=lambda t: t and ("啟售" in t or "開賣" in t))
            if sale_label:
                parent = sale_label.find_parent('div') or sale_label.find_parent('li')
                if parent:
                    # Try to find sibling text or child value
                    text = parent.get_text(" ", strip=True)
                    # Extract date part? Usually simple text cleaning.
                    # Example: "啟售時間：2025/11/11 12:00"
                    if "：" in text:
                        detail["ticket_sale_date"] = text.split("：")[-1].strip()
                    else:
                        detail["ticket_sale_date"] = text

            # Price
            # <div class="price-list"> or text "$300, $500..."
            # Simpler: Search for "$" or "票價"
            # OPENTIX prices area often listed as buttons or text
            price_container = soup.select_one('.price-list') or soup.find(string=lambda t: t and "票價" in t)
            if price_container:
                if hasattr(price_container, 'get_text'):
                   detail["price"] = price_container.get_text(strip=True)[:50] # Limit length
                else: 
                   # It was a NavString, find parent
                   parent = price_container.find_parent()
                   text = parent.get_text(strip=True)
                   # If text is just "票價" or "票價：", go up one more level
                   if len(text) < 5 and parent.parent:
                       text = parent.parent.get_text(strip=True)
                   detail["price"] = text[:50]
                   
            # Global "Free" check
            if not detail.get("price"):
                full_text = soup.get_text()
                free_keywords = ["免費", "Free", "0元", "無需購票", "自由入場"]
                if any(k in full_text for k in free_keywords):
                    detail["price"] = "0"
            
            # Extract high-res image from og:image
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                detail['image_url'] = og_img.get('content')
                   
            return detail
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {url}: {e}")
            return {}

    def parse_event(self, element) -> Optional[Dict]:
        try:
            event_url = element.get('href')
            if not event_url: return None
            
            if not event_url.startswith('http'):
                event_url = f"https://www.opentix.life{event_url}"
                
            title_tag = element.find('span', class_='info-title') or element.find('h3')
            name = title_tag.get_text(strip=True) if title_tag else "Unknown"
            
            infos_div = element.find('div', class_='infos')
            p_tags = infos_div.find_all('p') if infos_div else element.find_all('p')
            
            # Usually: Time / Venue / Valid Date
            raw_time_range = p_tags[0].get_text(strip=True) if len(p_tags) >= 1 else ""
            venue = p_tags[1].get_text(strip=True) if len(p_tags) >= 2 else "Unknown"
            
            # Simple date extraction (first part of range)
            date_part = raw_time_range.split('-')[0].strip() if '-' in raw_time_range else raw_time_range
            date_iso = parse_taiwan_date(date_part)
            
            # City guess
            city_map = {'台北': 'Taipei', 'Taipei': 'Taipei', '台中': 'Taichung', '高雄': 'Kaohsiung'}
            city = next((v for k, v in city_map.items() if k in venue), "Unknown")

            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            activity_id = f"opentix_{name}_{date_iso}"
            
            return {
                "activity_id": activity_id,
                "name": name,
                "activity_type": "concert",
                "performers": [], # Will be updated by detail
                "date": date_iso,
                "start_time": None, # Will be updated by detail
                "location": venue,
                "city": city,
                "price": None,
                "ticket_platform": "OPENTIX",
                "ticket_url": event_url,
                "image_url": image_url,
                "ticket_sale_date": None  # Will be updated by detail
            }
        except Exception as e:
            logger.error(f"Error parsing OPENTIX item: {e}")
            return None
