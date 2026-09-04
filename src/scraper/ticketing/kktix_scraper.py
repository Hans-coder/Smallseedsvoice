"""KKTIX Scraper with Atom feed engine and Playwright fallback"""
from typing import Dict, List, Optional
import time
import re
import json
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from src.scraper.base_scraper import BaseScraper
from src.utils.logger import setup_logger
from src.utils.date_parser import parse_taiwan_date, parse_time
from src.utils.text_cleaners import refine_image_url, clean_event_title

logger = setup_logger(__name__)

class KktixScraper(BaseScraper):
    """KKTIX Event Scraper supporting Atom XML feeds and HTML fallback"""
    
    def scrape_events(self, url: str = None) -> List[Dict]:
        """
        Scrape KKTIX music events.
        Uses fast, Cloudflare-immune Atom feed by default, with graceful fallback to Playwright.
        """
        try:
            logger.info("Scraping KKTIX via Atom feeds...")
            events = self.scrape_events_atom(url)
            if events:
                return events
            logger.warning("KKTIX Atom feed returned no events, falling back to HTML scraping...")
        except Exception as e:
            logger.warning(f"KKTIX Atom scraper error: {e}, falling back to HTML scraping...")

        # Fallback to HTML scraping
        try:
            return self.scrape_events_html(url)
        except Exception as e:
            logger.error(f"KKTIX HTML scraping also failed: {e}")
            return []

    def scrape_events_atom(self, url: str = None) -> List[Dict]:
        """
        Scrape KKTIX music events via official Atom XML feeds.
        Bypasses Cloudflare anti-bot checks and runs 10x faster.
        """
        today_dt = datetime.now()
        today = today_dt.strftime("%Y-%m-%d")
        max_date = (today_dt + timedelta(days=180)).strftime("%Y-%m-%d")

        if not url:
            # 1. Main music tag feed (contains up to 100 events per page)
            # 2. Key search queries across subdomains (e.g. binliveco.kktix.cc)
            search_keywords = ["演唱會", "音樂祭", "巡迴", "livehouse", "live house", "流浪祭", "爛泥發芽", "Atarayo"]
            
            feeds_to_scrape = [
                ("https://kktix.com/events.atom?event_tag_ids_in=1", True)
            ]
            for kw in search_keywords:
                kw_encoded = urllib.parse.quote(kw)
                feeds_to_scrape.append(
                    (f"https://kktix.com/events.atom?search={kw_encoded}", False)
                )
        else:
            # Map HTML listing URL to Atom feed
            atom_url = url
            if ".atom" not in atom_url:
                if "/events?" in atom_url:
                    atom_url = atom_url.replace("/events?", "/events.atom?")
                elif "/events" in atom_url:
                    atom_url = atom_url.replace("/events", "/events.atom")
            feeds_to_scrape = [(atom_url, True)]

        all_events = []
        seen_urls = set()
        max_pages = self.config.get('max_pages', 3)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        for base_feed_url, do_pagination in feeds_to_scrape:
            current_max = max_pages if do_pagination else 1
            for page in range(1, current_max + 1):
                if do_pagination and page > 1:
                    delim = '&' if '?' in base_feed_url else '?'
                    page_url = f"{base_feed_url}{delim}page={page}"
                else:
                    page_url = base_feed_url

                logger.info(f"Fetching KKTIX Atom feed: {page_url}...")
                try:
                    resp = self.session.get(page_url, timeout=self.timeout)
                    if resp.status_code != 200:
                        logger.warning(f"KKTIX Atom feed returned status {resp.status_code} for {page_url}")
                        break
                    root = ET.fromstring(resp.content)
                    entries = root.findall('atom:entry', ns)
                    if not entries:
                        break
                except Exception as ex:
                    logger.warning(f"Failed to fetch/parse KKTIX Atom feed {page_url}: {ex}")
                    break

                for entry in entries:
                    event_data = self.parse_atom_entry(entry, ns)
                    if not event_data:
                        continue

                    # Date filter
                    if event_data.get('date'):
                        if event_data['date'] < today or event_data['date'] > max_date:
                            continue

                    # Negative keyword filter (classical / lectures / kids)
                    name_check = str(event_data.get('name', '')).lower()
                    is_strict_classical = any(k in name_check for k in ['交響', '管樂', '弦樂', '國樂', '愛樂', '協奏曲', '獨奏', '古典'])
                    if is_strict_classical:
                        continue
                    ignore_keywords = ['音樂劇', '兒童', '合唱', '室內樂', '大師班', '親子', '芭蕾', '舞劇', '講座', '讀劇', '相聲', '脫口秀', '音樂家']
                    if any(k in name_check for k in ignore_keywords) and not 'live' in name_check and not '樂團' in name_check:
                        continue

                    # Dedup within this run
                    ticket_url = event_data['ticket_url']
                    if ticket_url in seen_urls:
                        continue
                    seen_urls.add(ticket_url)

                    # Detail enrichment (poster image, ticket sale date, price, performers)
                    detail = self._fetch_detail(ticket_url)
                    if detail:
                        event_data.update(detail)

                    all_events.append(event_data)
                    time.sleep(0.05)

                if not do_pagination:
                    break

        logger.info(f"KKTIX Atom: Scraped {len(all_events)} events")
        return all_events

    def parse_atom_entry(self, entry, ns: Dict[str, str]) -> Optional[Dict]:
        """Parse an <atom:entry> element into an event dictionary"""
        try:
            title = entry.find('atom:title', ns).text or ''
            link_el = entry.find('atom:link', ns)
            event_url = link_el.attrib.get('href') if link_el is not None else ''
            pub_el = entry.find('atom:published', ns)
            pub_text = pub_el.text if pub_el is not None else ''
            content_el = entry.find('atom:content', ns)
            content = content_el.text if content_el is not None else ''
            summary_el = entry.find('atom:summary', ns)
            summary = summary_el.text if summary_el is not None else ''

            if not event_url:
                return None

            name = clean_event_title(title)

            # Date & Time from published (ISO format: 2026-09-04T14:00:00+08:00)
            date_iso = pub_text[:10] if pub_text else None
            start_time = pub_text[11:16] if len(pub_text) >= 16 else None

            # Fallback to content parsing for time
            if not date_iso or not start_time:
                time_match = re.search(r'時間：([^\n]+)', content)
                if time_match:
                    time_str = time_match.group(1)
                    if not date_iso:
                        date_iso = parse_taiwan_date(time_str)
                    if not start_time:
                        t_match = re.search(r'(\d{2}:\d{2})', time_str)
                        if t_match:
                            start_time = t_match.group(1)

            # Location & Venue Name from content
            location = "Unknown"
            venue_name = "Unknown"
            loc_match = re.search(r'地點：([^\n]+)', content)
            if loc_match:
                location = loc_match.group(1).strip()
                venue_name = location.split('/')[0].strip() if '/' in location else location

            # City detection
            city = "Unknown"
            for c in ['台北', '臺北', '新北', '桃園', '台中', '臺中', '台南', '臺南', '高雄', '宜蘭', '新竹', '嘉義', '花蓮', '台東', '臺東', '屏東', '基隆', '苗栗', '彰化', '南投', '雲林']:
                if c in location:
                    city = f"{c}市" if not c.endswith(('市', '縣')) else c
                    break

            activity_id = f"kktix_{name}_{date_iso}"

            return {
                "activity_id": activity_id,
                "name": name,
                "activity_type": "concert",
                "performers": [],
                "date": date_iso,
                "start_time": start_time,
                "location": venue_name if venue_name != "Unknown" else location,
                "venue_name": venue_name,
                "city": city,
                "price": None,
                "ticket_platform": "KKTIX",
                "ticket_url": event_url,
                "image_url": None,
                "ticket_sale_date": None,
            }
        except Exception as e:
            logger.debug(f"Error parsing Atom entry: {e}")
            return None

    def _fetch_detail(self, url: str) -> Dict:
        """Fetch detail page for venue, price, sale time, and poster image"""
        try:
            soup = None
            # Fast path: try requests first (0.2s, avoids Playwright overhead and timeouts)
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200 and len(resp.text) > 500:
                    soup = BeautifulSoup(resp.text, 'lxml')
            except Exception as req_err:
                logger.debug(f"Direct request failed for {url}: {req_err}")

            # Fallback path: Playwright if requests failed
            if not soup:
                soup = self.fetch_with_selenium(url, wait_time=1)
                
            if not soup:
                return {}
            
            venue = "Unknown"
            sale_date = None
            price = None
            start_time = None
            performers = []
            
            # 1. Best effort: Extract from JSON-LD structured data first!
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    ld_data = json.loads(script.string)
                    if isinstance(ld_data, list):
                        ld_data = ld_data[0]
                    if ld_data.get('@type') == 'Event':
                        if 'location' in ld_data and 'name' in ld_data['location']:
                            venue = ld_data['location']['name']
                        if 'startDate' in ld_data:
                            start_time_str = ld_data['startDate']
                            t_match = re.search(r'T(\d{2}:\d{2})', start_time_str)
                            if t_match:
                                start_time = t_match.group(1)
                except Exception:
                    pass

            # Fallback 1: Venue and Start Time Extraction via Table info
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
                                time_match = re.search(r'(\d{2}:\d{2})', time_text)
                                if time_match:
                                    start_time = time_match.group(1)

            # 2. Sale time from tables
            tables = soup.find_all('table')
            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all('th')]
                if any("販售時間" in h for h in headers) or any("報名時間" in h for h in headers):
                    target_header = next((h for h in headers if "販售時間" in h or "報名時間" in h), None)
                    if target_header:
                        idx = headers.index(target_header)
                        tbody = table.find('tbody')
                        if tbody:
                            for row in tbody.find_all('tr'):
                                cols = row.find_all('td')
                                if len(cols) > idx:
                                    sale_text = cols[idx].get_text(strip=True)
                                    if sale_text:
                                        clean_date = sale_text.split('~')[0].strip()
                                        clean_date = clean_date.split('(')[0].strip()
                                        if len(clean_date) > 5:
                                            sale_date = clean_date
                                            break
                    if sale_date:
                        break
            
            # Fallback to old "報名開始" logic
            if not sale_date:
                sale_tag = soup.find(string=lambda t: t and ("報名開始" in t or "報名時間" in t))
                if sale_tag:
                    row = sale_tag.find_parent('tr')
                    if row and row.find('td'):
                        sale_date = row.find('td').get_text(strip=True)

            # 3. Price Extraction
            tables = soup.find_all('table')
            for table in tables:
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
                                raw_p = cols[idx].get_text(strip=True)
                                if raw_p and len(raw_p) < 60:
                                    price = raw_p
                                    break

            if not price:
                full_text = soup.get_text()
                free_keywords = ["此活動為免費", "本活動免費", "免費入場", "無需購票", "自由入場", "0元"]
                if any(k in full_text for k in free_keywords):
                    price = "0"
                else:
                    match_p = re.search(r'(?:票價|售價)[:：\s]+(TWD\$?[\d,]+|\$[\d,]+|\d+\s*元|免費)', full_text)
                    if match_p:
                        price = match_p.group(1).strip()
            
            # Extract high-res image from og:image
            og_img = soup.find('meta', property='og:image')
            detail_image = refine_image_url(og_img.get('content')) if og_img else None

            # 4. Performers Extraction from Description
            description_div = soup.find('div', class_='description')
            if description_div:
                desc_text = description_div.get_text(separator='\n')
                match = re.search(r'(?:演出者|卡司|Lineup|Cast|演出陣容|共演)[:：\s]+([^\n]+)', desc_text, re.IGNORECASE)
                if match:
                    raw_performers = match.group(1).replace('、', ',').replace('｜', ',').replace('|', ',').split(',')
                    performers = [p.strip() for p in raw_performers if p.strip()]

            res = {
                "venue_name": venue, 
                "ticket_sale_date": sale_date, 
                "price": price, 
                "image_url": detail_image,
                "start_time": start_time,
                "performers": performers
            }
            # Only return keys that are not None or 'Unknown'
            return {k: v for k, v in res.items() if v is not None and v != "Unknown"}
        except Exception as e:
            logger.warning(f"Failed to fetch detail for {url}: {e}")
            return {}

    def scrape_events_html(self, url: str = None) -> List[Dict]:
        """Fallback method: scrape KKTIX events from HTML pages via Playwright"""
        if not url:
            today_dt = datetime.now()
            today_str = today_dt.strftime("%Y/%m/%d")
            max_date_str = (today_dt + timedelta(days=180)).strftime("%Y/%m/%d")
            start_at = urllib.parse.quote(today_str)
            end_at = urllib.parse.quote(max_date_str)

            main_url = (
                f"https://kktix.com/events?utf8=%E2%9C%93&search=&max_price=&min_price="
                f"&start_at={start_at}&end_at={end_at}&event_tag_ids_in=1"
            )
            search_keywords = ["演唱會", "音樂祭", "巡迴", "livehouse", "live house"]
            search_urls = []
            for kw in search_keywords:
                kw_encoded = urllib.parse.quote(kw)
                search_url = (
                    f"https://kktix.com/events?utf8=%E2%9C%93&search={kw_encoded}"
                    f"&start_at={start_at}&end_at={end_at}"
                )
                search_urls.append((search_url, False))

            urls_to_scrape = [(main_url, True)] + search_urls
        else:
            urls_to_scrape = [(url, True)]
            
        all_events = []
        max_pages = self.config.get('max_pages', 3)
        seen_urls = set()

        for target_url, do_pagination in urls_to_scrape:
            current_max = max_pages if do_pagination else 1
            base_url = target_url
            
            logger.info(f"Scraping KKTIX HTML: {target_url} (Pagination: {do_pagination})")

            for page in range(1, current_max + 1):
                if do_pagination and page > 1:
                    page_url = f"{base_url}&page={page}"
                else:
                    page_url = base_url
                
                logger.info(f"Fetching KKTIX HTML page {page}: {page_url}...")
                try:
                    soup = self.fetch_with_selenium(page_url, wait_time=3)
                except Exception as e:
                    logger.warning(f"Error fetching {page_url}: {e}")
                    soup = None

                if not soup:
                    break
                
                event_items = soup.select('ul.events > li')
                if not event_items:
                    logger.info(f"No more events found on page {page}")
                    break
                    
                page_events = []
                for item in event_items:
                    event_data = self.parse_event(item)
                    if event_data:
                        today_dt = datetime.now()
                        today = today_dt.strftime("%Y-%m-%d")
                        max_date = (today_dt + timedelta(days=180)).strftime("%Y-%m-%d")
                        if event_data.get('date'):
                            if event_data['date'] < today or event_data['date'] > max_date:
                                continue
                            
                        name_check = str(event_data.get('name', '')).lower()
                        is_strict_classical = any(k in name_check for k in ['交響', '管樂', '弦樂', '國樂', '愛樂', '協奏曲', '獨奏', '古典'])
                        if is_strict_classical:
                            continue
                        ignore_keywords = ['音樂劇', '兒童', '合唱', '室內樂', '大師班', '親子', '芭蕾', '舞劇', '講座', '音樂會', '讀劇', '相聲', '脫口秀', '音樂家']
                        if any(k in name_check for k in ignore_keywords) and not 'live' in name_check and not '樂團' in name_check:
                            continue

                        if event_data['ticket_url'] in seen_urls:
                            continue
                        seen_urls.add(event_data['ticket_url'])
                        
                        if event_data.get('ticket_url'):
                            detail = self._fetch_detail(event_data['ticket_url'])
                            if detail:
                                event_data.update(detail)
                        page_events.append(event_data)
                        time.sleep(0.5)
                
                all_events.extend(page_events)
                time.sleep(1)
                
                if not do_pagination:
                    break
            
        logger.info(f"KKTIX HTML: Scraped {len(all_events)} events")
        return all_events

    def parse_event(self, element) -> Optional[Dict]:
        """Parse an HTML event element (used by scrape_events_html)"""
        try:
            link_tag = element.find('a', class_='cover') or element.find('a')
            if not link_tag:
                return None
            
            event_url = link_tag.get('href')
            if event_url and not event_url.startswith('http'):
                event_url = f"https://kktix.com{event_url}"
                
            # Basic Info
            title_container = element.find(class_='event-title')
            raw_title = title_container.find('h2').get_text(strip=True) if title_container else "Unknown"
            name = clean_event_title(raw_title)
            
            # Time & Date (Format: 2025/11/11(二))
            time_tag = element.find(class_='date')
            raw_time = time_tag.get_text(strip=True) if time_tag else ""
            date_iso = parse_taiwan_date(raw_time)
            
            location = "Unknown" 
            city = "Unknown"
            
            img_tag = element.find('img')
            image_url = img_tag.get('src') if img_tag else None
            
            activity_id = f"kktix_{name}_{date_iso}"
            
            return {
                "activity_id": activity_id,
                "name": name,
                "activity_type": "concert",
                "performers": [],
                "date": date_iso,
                "start_time": None,
                "location": location,
                "city": city,
                "price": None,
                "ticket_platform": "KKTIX",
                "ticket_url": event_url,
                "image_url": image_url,
                "ticket_sale_date": None
            }
        except Exception as e:
            logger.error(f"Error parsing KKTIX HTML item: {e}")
            return None
