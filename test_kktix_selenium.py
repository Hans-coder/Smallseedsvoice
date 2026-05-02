import json
from src.scraper.ticketing.kktix_scraper import KktixScraper

scraper = KktixScraper({})
soup = scraper.fetch_with_selenium("https://seasnow.kktix.cc/events/20260509", wait_time=1)

venue = "Unknown"
start_time = None
for script in soup.find_all('script', type='application/ld+json'):
    print("Found JSON-LD script tag!")
    try:
        ld_data = json.loads(script.string)
        if isinstance(ld_data, list):
            ld_data = ld_data[0]
        print("@type:", ld_data.get('@type'))
    except Exception as e:
        print("EXCEPTION:", e)

