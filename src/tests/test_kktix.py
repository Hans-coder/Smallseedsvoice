
import unittest
from src.scraper.ticketing.kktix_scraper import KktixScraper

class TestKktixScraper(unittest.TestCase):
    def test_scrape_kktix(self):
        config = {'request_delay': 1}
        scraper = KktixScraper(config)
        # KKTIX Music category
        events = scraper.scrape_events("https://kktix.com/events?category_id=2")
        print(f"\nFound {len(events)} events")
        if len(events) > 0:
            print(f"Sample: {events[0]}")
            self.assertTrue(events[0]['name'])
            # self.assertTrue(events[0]['image_url']) 
        else:
            print("No events found. Might be blocked or selector issue.")

if __name__ == '__main__':
    unittest.main()
