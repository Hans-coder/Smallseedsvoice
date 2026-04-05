"""Ticket Plus (遠大售票) Scraper"""
from typing import Dict, List, Optional
import re
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.text_cleaners import refine_image_url, clean_event_title
from src.utils.date_parser import parse_taiwan_date

logger = setup_logger(__name__)

class TicketPlusScraper(BaseScraper):
    """Ticket Plus Event Scraper"""
    
    def scrape_events(self, url: str = "https://ticketplus.com.tw/search?q=") -> List[Dict]:
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
                # Optional: fetch detail if venue is missing
                # detail = self._fetch_detail(event_data['ticket_url'])
                all_events.append(event_data)
                
        logger.info(f"Ticket Plus: Scraped {len(all_events)} events")
        return all_events

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
                "performers": [],
                "date": date_iso,
                "start_time": None,
                "venue_name": venue,
                "city": "Unknown",
                "price": None,
                "ticket_platform": "Ticket Plus",
                "ticket_url": event_url,
                "image_url": image_url,
                "note": "Scraped from Ticket Plus"
            }
        except Exception as e:
            logger.warning(f"Error parsing Ticket Plus card: {e}")
            return None
