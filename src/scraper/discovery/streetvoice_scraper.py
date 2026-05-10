"""StreetVoice Discovery Scraper"""
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class StreetVoiceScraper(BaseScraper):
    """StreetVoice Activity Scraper for discovering independent music events"""
    
    def scrape_events(self, url: str = "https://streetvoice.com/gigs/all/0/", with_details: bool = True) -> List[Dict]:
        """
        Scrape StreetVoice activities.
        """
        logger.info(f"Scraping StreetVoice activities: {url}")
        soup = self.fetch_with_selenium(url, wait_time=5)
        
        if not soup:
            return []
            
        all_events = []
        # Each day is grouped in a verified container
        date_blocks = soup.select('.date-block.item_box')
        
        for block in date_blocks:
            # 1. Extract Date from the block header (subagent verified)
            current_date_str = None
            month_tag = block.select_one('.bg-red')
            day_tag = block.select_one('h1')
            
            if month_tag and day_tag:
                # Format: "3 月" -> 03, "14" -> 14
                month_text = month_tag.get_text(strip=True)
                day_text = day_tag.get_text(strip=True)
                
                # Extract digits for month
                m_match = re.search(r'(\d+)', month_text)
                if not m_match:
                    # Fallback for English months if needed
                    months_en = {'JAN': '01', 'FEB': '02', 'MAR': '03', 'APR': '04', 'MAY': '05', 'JUN': '06',
                                 'JUL': '07', 'AUG': '08', 'SEP': '09', 'OCT': '10', 'NOV': '11', 'DEC': '12'}
                    m_val = months_en.get(month_text.upper(), '01')
                else:
                    m_val = m_match.group(1).zfill(2)
                
                current_year = datetime.now().year
                # Extract digits for day
                day_match = re.search(r'(\d+)', day_text)
                day_val = day_match.group(1).zfill(2) if day_match else "01"
                
                current_date_str = f"{current_year}-{m_val}-{day_val}"

            # 2. Extract Events within this container's right column
            # They are in li.list-group-item
            items = block.select('li.list-group-item')
            for item in items:
                event_data = self.parse_event(item, current_date_str)
                if event_data:
                    # Date Filter: Only next 4 days (half-week)
                    if event_data.get('date'):
                        today = datetime.now().strftime("%Y-%m-%d")
                        max_date = (datetime.now() + timedelta(days=4)).strftime("%Y-%m-%d")
                        if event_data['date'] < today or event_data['date'] > max_date:
                            continue

                    # Fetch high-res image from detail page only if requested
                    if with_details and event_data.get('source_url'):
                        detail = self._fetch_detail(event_data['source_url'])
                        if detail:
                            event_data.update(detail)
                    all_events.append(event_data)
                
        logger.info(f"StreetVoice: Scraped {len(all_events)} events")
        return all_events

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for high-res image."""
        try:
            # StreetVoice activity page is usually simple and has og:image in source
            soup = self.fetch_page(url)
            if not soup: return {}
            
            detail = {}
            og_img = soup.find('meta', property='og:image')
            if og_img and og_img.get('content'):
                detail["image_url"] = og_img.get('content')
                
            return detail
        except Exception as e:
            logger.warning(f"Failed to fetch StreetVoice detail for {url}: {e}")
            return {}

    def parse_event(self, element, date_str: Optional[str]) -> Optional[Dict]:
        """Parse a single StreetVoice activity item"""
        try:
            title_tag = element.select_one('h3.text-break a')
            if not title_tag:
                title_tag = element.select_one('h4 a') # Fallback
            
            if not title_tag:
                return None
                
            name = title_tag.get_text(strip=True)
            link = "https://streetvoice.com" + title_tag.get('href', '')
            
            # Info string format: "00:00・臺北市・Pipe Live Music"
            info_tag = element.select_one('h4') or element.select_one('.info-block p') or element.select_one('p.text-muted')
            
            info_text = info_tag.get_text(strip=True) if info_tag else ""
            
            time_val = "Unknown"
            venue = "Unknown"
            city = "Unknown"
            
            if "・" in info_text or "．" in info_text:
                parts = [p.strip() for p in re.split(r'[・．.]', info_text)]
                if len(parts) == 1:
                    time_val = parts[0]
                elif len(parts) == 2:
                    time_val = parts[0]
                    venue = parts[1]
                elif len(parts) >= 3:
                    time_val = parts[0]
                    city = parts[1]
                    venue = parts[2]

            # Performers
            performers = [a.get_text(strip=True) for a in element.select('.btn-artist')]
            
            # Image - StreetVoice list uses delayed loading, look for background image in .cover-block or real src
            image_url = None
            cover_block = element.select_one('.cover-block')
            if cover_block and cover_block.get('style'):
                bg_match = re.search(r'url\("?(.+?)"?\)', cover_block.get('style'))
                if bg_match:
                    image_url = bg_match.group(1)
            
            if not image_url:
                img_tag = element.select_one('img')
                if img_tag:
                    image_url = img_tag.get('src')
                    # Avoid 1x1 placeholder
                    if '1x1.jpg' in (image_url or ''):
                        image_url = img_tag.get('data-src') or img_tag.get('lazy-src')

            return {
                'name': name,
                'date': date_str,
                'time': time_val,
                'venue_name': venue,
                'city': city,
                'performers': performers,
                'source_url': link,
                'ticket_url': link,
                'image_url': image_url.split('?x-oss-process=')[0] if image_url else None,
                'source': 'StreetVoice',
                'is_free': 'unknown'
            }
        except Exception as e:
            logger.error(f"Error parsing StreetVoice event: {e}")
            return None

if __name__ == "__main__":
    # Quick test
    scraper = StreetVoiceScraper({})
    events = scraper.scrape_events()
    import json
    print(json.dumps(events[:3], indent=4, ensure_ascii=False))
