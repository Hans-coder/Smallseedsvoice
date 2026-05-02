import json
from src.scraper.ticketing.kktix_scraper import KktixScraper

scraper = KktixScraper({})
detail = scraper._fetch_detail("https://lingchenpai.kktix.cc/events/318c376e")
print(json.dumps(detail, indent=2, ensure_ascii=False))

detail2 = scraper._fetch_detail("https://seasnow.kktix.cc/events/20260509")
print(json.dumps(detail2, indent=2, ensure_ascii=False))
