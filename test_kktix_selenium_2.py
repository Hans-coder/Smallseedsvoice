import json
from src.scraper.ticketing.kktix_scraper import KktixScraper

scraper = KktixScraper({})
soup = scraper.fetch_with_selenium("https://seasnow.kktix.cc/events/20260509", wait_time=1)

for script in soup.find_all('script', type='application/ld+json'):
    print("STRING LENGTH:", len(str(script.string)))
    print("CONTENT:", str(script.string)[:100])
