"""Indievox Scraper"""
from typing import Dict, List, Optional
import re
from datetime import datetime, timedelta
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.text_cleaners import refine_image_url, clean_event_title

logger = setup_logger(__name__)

class IndievoxScraper(BaseScraper):
    """Indievox Event Scraper"""
    
    def scrape_events(self, url: str = "https://www.indievox.com/activity", with_details: bool = True) -> List[Dict]:
        """
        Scrape Indievox events from the main activity page.
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
            
            # Find event items in thumbnail view
            event_rows = soup.select('.thumbnails.activity') or soup.select('.thumbnails .col-md-3')
            
            page_events = []
            for row in event_rows:
                event_data = self.parse_event(row)
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

                    # Fetch detail to get image if requested
                    if with_details and event_data.get('ticket_url'):
                        detail = self._fetch_detail(event_data['ticket_url'])
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
        """Fetch detail page for high-res image, performers, and more."""
        try:
            # Detail pages are usually less protected than list pages, but fetch_page might still get 403.
            # Using fetch_with_selenium ensures we get the image.
            soup = self.fetch_with_selenium(url, wait_time=1)
            if not soup: return {}
            
            detail = {
                "performers": [],
                "start_time": None,
                "price": None,
                "ticket_sale_date": None
            }

            # Extract high-res image from og:image
            og_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
            detail["image_url"] = refine_image_url(og_img.get('content')) if og_img else None

            # Indievox detail often has a paragraph inside #intro
            intro_div = soup.find('div', id='intro')
            if intro_div:
                intro_text = intro_div.get_text(separator='\n')
                for line in intro_text.split('\n'):
                    line = line.strip()
                    if "演出日期及時間" in line or "演出時間" in line:
                        import re
                        time_match = re.search(r'(\d{2}:\d{2})', line)
                        if time_match:
                            detail["start_time"] = time_match.group(1)
                    elif "票價" in line:
                        detail["price"] = line.replace("票價：", "").replace("票價:", "").strip()
                    elif "售票時間" in line or "啟售時間" in line:
                        detail["ticket_sale_date"] = line.replace("售票時間：", "").replace("售票時間:", "").strip()
                    elif "演出地點" in line:
                        venue = line.replace("演出地點：", "").replace("演出地點:", "").strip()
                        detail["venue_name"] = venue.split('（')[0].split('(')[0].strip()
                    elif "演出者" in line:
                        raw_performers = line.replace("演出者：", "").replace("演出者:", "").strip()
                        raw_performers = raw_performers.replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                        detail["performers"] = [p.strip() for p in raw_performers if p.strip()]

            # Performers fallback in description
            if not detail["performers"]:
                desc_div = soup.find('div', class_='event-desc') or soup.find('div', class_='description')
                if desc_div:
                    desc_text = desc_div.get_text(separator='\n')
                    import re
                    match = re.search(r'(?:演出者|卡司|Lineup|Cast|演出陣容|共演|演出團隊)[:：\s]+([^\n]+)', desc_text, re.IGNORECASE)
                    if match:
                        raw_performers = match.group(1).replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                        detail["performers"] = [p.strip() for p in raw_performers if p.strip()]

            return detail
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {url}: {e}")
            return {}

    def parse_event(self, element) -> Optional[Dict]:
        """Parse Indievox event element"""
        try:
            # 1. Title & Link
            link = element.find('a')
            if not link: return None
            
            title_div = element.find(class_='multi_ellipsis')
            name = clean_event_title(title_div.get_text(strip=True)) if title_div else clean_event_title(link.get_text(strip=True))
            
            event_url = link['href']
            if not event_url.startswith('http'):
                event_url = f"https://www.indievox.com{event_url}"
                
            # 2. Date
            date_div = element.find(class_='date')
            date_str = date_div.get_text(strip=True) if date_div else ""
            date_match = re.search(r'(\d{4}[/-]\d{1,2}[/-]\d{1,2})', date_str)
            date = date_match.group(1).replace('/', '-') if date_match else None
            
            # 3. Venue
            # Main view usually doesn't have venue, will fetch from detail
            venue = "Live House"
            
            # 4. Image
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            # ID: Platform + Name + Date
            activity_id = f"indievox_{name}_{date}"
            
            return {
                "activity_id": activity_id,
                "name": name,
                "performers": [], # Will be updated by detail
                "date": date,
                "start_time": None, # Standardized key, updated by detail
                "time": "Unknown", # Keep for backwards compatibility
                "venue_name": venue,
                "city": "Unknown",
                "price": None, # Will be updated by detail
                "ticket_sale_date": None, # Will be updated by detail
                "is_free": "unknown",
                "ticket_platform": "Indievox",
                "ticket_url": event_url,
                "image_url": image_url,
                "note": "Scraped from Indievox (Table View)",
                "reliability": "official"
            }
        except Exception as e:
            logger.warning(f"Error parsing Indievox event: {e}")
            return None
