from src.scraper.ticketing.kktix_scraper import KktixScraper
from src.scraper.ticketing.opentix_scraper import OpentixScraper
import logging

# Setup basic logging to stdout
logging.basicConfig(level=logging.INFO)

def debug_kktix():
    print("--- Debugging KKTIX ---")
    scraper = KktixScraper({'max_pages': 1})
    # Scrape just one page of music events
    events = scraper.scrape_events(url="https://kktix.com/events?event_tag_ids_in=13")
    for i, event in enumerate(events[:1]): # Check just 1, detailed
        print(f"[{i}] {event['name']}")
        print(f"    URL: {event['ticket_url']}")
        # We need to fetch the page again to see JSON-LD because scrape_events parses list view
        scraper._fetch_detail(event['ticket_url']) # This triggers internal fetch, but we want to see the soup
        soup = scraper.fetch_page(event['ticket_url'])
        if soup:
            # Debug HTML structure around price
            price_tag = soup.find(string=lambda t: t and ("票價" in t or "售價" in t))
            if price_tag:
                parent = price_tag.find_parent()
                print(f"    Price Tag Found: {price_tag}")
                print(f"    Parent HTML: {parent.prettify()[:500]}...")
            else:
                print("    '票價'/'售價' not found in text.")

def debug_opentix():
    print("\n--- Debugging OPENTIX ---")
    scraper = OpentixScraper({})
    events = scraper.scrape_events()
    
    print(f"Found {len(events)} OPENTIX events.")
    for i, event in enumerate(events[:1]):
        print(f"[{i}] {event['name']}")
        print(f"    URL: {event['ticket_url']}")
        
        # Fetch page with Selenium to check JSON-LD
        soup = scraper.fetch_with_selenium(event['ticket_url'])
        if soup:
             ld = soup.find('script', type='application/ld+json')
             if ld:
                 print(f"    JSON-LD: {ld.string[:500]}...")
             else:
                 print("    No JSON-LD found.")
             
             # Also debug HTML around '票價'
             price_tag = soup.find(string=lambda t: t and "票價" in t)
             if price_tag:
                 parent = price_tag.find_parent()
                 print(f"    Price Tag Found: {price_tag}")
                 print(f"    Parent HTML: {parent.prettify()[:500]}...")
             else:
                 print("    '票價' not found in text.")

if __name__ == "__main__":
    # debug_kktix()
    debug_opentix() # Uncomment if needed
