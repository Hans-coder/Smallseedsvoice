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
                events.append(event_data)
                
        logger.info(f"OPENTIX: Scraped {len(events)} events")
        return events

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
                "activity_name": name,
                "activity_type": "concert",
                "performers": [],
                "date": date_iso,
                "start_time": None,
                "venue_name": venue,
                "city": city,
                "price": None,
                "ticket_platform": "OPENTIX",
                "ticket_url": event_url,
                "image_url": image_url,
                "ticket_sale_date": None  # TODO: Implement detail scrape for sale date
            }
        except Exception as e:
            logger.error(f"Error parsing OPENTIX item: {e}")
            return None
