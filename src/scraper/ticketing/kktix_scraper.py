"""KKTIX Scraper"""
from typing import Dict, List, Optional
import time
from datetime import datetime
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date, parse_time
from src.utils.text_cleaners import refine_image_url, clean_event_title

logger = setup_logger(__name__)

class KktixScraper(BaseScraper):
    """KKTIX Event Scraper"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape KKTIX music events.
        """
        if not url:
            from datetime import timedelta
            today_dt = datetime.now()
            today_str = today_dt.strftime("%Y/%m/%d")
            max_date_str = (today_dt + timedelta(days=14)).strftime("%Y/%m/%d")
            import urllib.parse
            # URL encode the dates
            start_at = urllib.parse.quote(today_str)
            end_at = urllib.parse.quote(max_date_str)
            
            # Default behavior: Search for Concerts within next 14 days
            target_url = f"https://kktix.com/events?utf8=%E2%9C%93&search=https%3A%2F%2Fkktix.com%2F&max_price=&min_price=&start_at={start_at}&end_at={end_at}&event_tag_ids_in=1"
            urls_to_scrape = [
                (target_url, True)
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
                
                soup = self.fetch_with_selenium(page_url, wait_time=3)
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
                        # Early Date & Keyword Filter
                        from datetime import timedelta
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
        """Fetch detail page for venue and sale time using requests"""
        try:
            # Use Selenium for detail page to avoid request blocks
            soup = self.fetch_with_selenium(url, wait_time=1)
            if not soup: return {}
            
            venue = "Unknown"
            sale_date = None
            price = None
            start_time = None
            performers = []
            
            # 1. Best effort: Extract from JSON-LD structured data first!
            import json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    ld_data = json.loads(script.string)
                    if isinstance(ld_data, list):
                        ld_data = ld_data[0]
                    if ld_data.get('@type') == 'Event':
                        if 'location' in ld_data and 'name' in ld_data['location']:
                            venue = ld_data['location']['name']
                        if 'startDate' in ld_data:
                            # Format is "2026-05-09T18:00:00.000+08:00"
                            start_time_str = ld_data['startDate']
                            import re
                            t_match = re.search(r'T(\d{2}:\d{2})', start_time_str)
                            if t_match:
                                start_time = t_match.group(1)
                except:
                    pass

            # Fallback 1: Venue and Start Time Extraction via Table
            if venue == "Unknown" or not start_time:
                table_info = soup.find(class_='info')
                if table_info:
                    for row in table_info.find_all('tr'):
                        th = row.find('th')
                        td = row.find('td')
                        if th and td:
                            th_text = th.get_text(strip=True)
                            if "地點" in th_text and venue == "Unknown":
                                venue = td.get_text(strip=True).split(maxsplit=1)[0]
                            elif "時間" in th_text and not start_time:
                                time_text = td.get_text(strip=True)
                                import re
                                time_match = re.search(r'(\d{2}:\d{2})', time_text)
                                if time_match:
                                    start_time = time_match.group(1)
            tables = soup.find_all('table')
            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all('th')]
                
                # Check typical header names
                if any("販售時間" in h for h in headers) or any("報名時間" in h for h in headers):
                    # Determine column index
                    target_header = next((h for h in headers if "販售時間" in h or "報名時間" in h), None)
                    if target_header:
                        idx = headers.index(target_header)
                        
                        tbody = table.find('tbody')
                        if tbody:
                            # Iterate rows to find first valid date
                            for row in tbody.find_all('tr'):
                                cols = row.find_all('td')
                                if len(cols) > idx:
                                    sale_text = cols[idx].get_text(strip=True)
                                    if sale_text:
                                        # Data often like: "2026/01/26 00:00(+0800) ~ 2026/01/31 19:00(+0800)"
                                        # Or: "2026/01/26 12:00"
                                        clean_date = sale_text.split('~')[0].strip()
                                        clean_date = clean_date.split('(')[0].strip()
                                        
                                        # Basic validation: looks like a date?
                                        if len(clean_date) > 5:
                                            sale_date = clean_date
                                            break
                    if sale_date:
                        break
            
            # Strategy B: Fallback to old "報名開始" logic
            if not sale_date:
                 sale_tag = soup.find(string=lambda t: t and ("報名開始" in t or "報名時間" in t))
                 if sale_tag:
                    row = sale_tag.find_parent('tr')
                    if row and row.find('td'):
                        sale_date = row.find('td').get_text(strip=True)

            # 3. Price Extraction
            # Look for "售價" or "票價" header
            price_header = soup.find(lambda tag: tag.name in ['th', 'div', 'span', 'strong'] and any(k in tag.get_text() for k in ["售價", "票價"]))
            if price_header:
                 # Check if it's a table header
                 table = price_header.find_parent('table')
                 if table:
                    headers = [th.get_text(strip=True) for th in table.find_all('th')]
                    target_h = next((h for h in headers if "售價" in h or "票價" in h), None)
                    if target_h:
                        idx = headers.index(target_h)
                        tbody = table.find('tbody')
                        if tbody:
                            rows = tbody.find_all('tr')
                            if rows:
                                cols = rows[0].find_all('td')
                                if len(cols) > idx:
                                    price = cols[idx].get_text(strip=True)
                 else:
                     # Maybe it's a list item or div?
                     parent = price_header.find_parent()
                     if parent:
                         # Return the full text to ensure we capture the values
                         # e.g. "票價： 免費"
                         price = parent.get_text(strip=True)

            # Global "Free" check if price is still None
            if not price:
                full_text = soup.get_text()
                free_keywords = ["此活動為免費", "本活動免費", "免費入場", "無需購票", "自由入場", "0元"]
                if any(k in full_text for k in free_keywords):
                    price = "0"
            
            # Extract high-res image from og:image
            og_img = soup.find('meta', property='og:image')
            detail_image = refine_image_url(og_img.get('content')) if og_img else None

            # 4. Performers Extraction from Description
            description_div = soup.find('div', class_='description')
            if description_div:
                desc_text = description_div.get_text(separator='\n')
                import re
                # Look for common performer keywords
                match = re.search(r'(?:演出者|卡司|Lineup|Cast|演出陣容|共演)[:：\s]+([^\n]+)', desc_text, re.IGNORECASE)
                if match:
                    raw_performers = match.group(1).replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                    performers = [p.strip() for p in raw_performers if p.strip()]

            return {
                "venue_name": venue, 
                "ticket_sale_date": sale_date, 
                "price": price, 
                "image_url": detail_image,
                "start_time": start_time,
                "performers": performers
            }
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
            raw_title = title_container.find('h2').get_text(strip=True) if title_container else "Unknown"
            name = clean_event_title(raw_title)
            
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
                "name": name,
                "activity_type": "concert", # Default for music tag
                "performers": [], # Will be updated by detail fetch
                "date": date_iso,
                "start_time": start_time,
                "location": location,
                "city": city,
                "price": None, # Needs detail
                "ticket_platform": "KKTIX",
                "ticket_url": event_url,
                "image_url": image_url,
                "ticket_sale_date": None  # Will be updated by detail fetch
            }
        except Exception as e:
            logger.error(f"Error parsing KKTIX item: {e}")
            return None
