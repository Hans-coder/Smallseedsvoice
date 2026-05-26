import unittest
from datetime import datetime, timedelta
from src.processor.digest_builder import DigestBuilder

class TestDigestBuilder(unittest.TestCase):
    def setUp(self):
        self.config = {'publishing': {'split_text': True}}
        self.builder = DigestBuilder(self.config)
        self.next_week = datetime.now() + timedelta(days=7)
        self.start_date = self.next_week
        self.end_date = self.next_week + timedelta(days=7)

    def test_build_digest_single_post_merged(self):
        event_date = (self.start_date + timedelta(days=1)).strftime("%Y-%m-%d")
        events = [
            {'name': 'Event 1', 'location': 'Loc 1', 'date': event_date, 'time': f'{event_date} 19:00', 'image_url': 'http://example.com/img1.jpg'}
        ]
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        # Should have 1 post because cover and event are small enough to merge
        self.assertEqual(len(posts), 1)
        self.assertIn('Event 1', posts[0]['text'])
        self.assertIn('http://example.com/img1.jpg', posts[0]['images'])

    def test_image_url_usage(self):
        event_date = (self.start_date + timedelta(days=1)).strftime("%Y-%m-%d")
        events = [
            {'name': 'Event 1', 'location': 'Loc 1', 'date': event_date, 'time': 'Time', 'image_url': 'http://example.com/url.jpg', 'image_path': 'local/path.jpg'}
        ]
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        # Should prioritize image_url for Threads API
        self.assertIn('http://example.com/url.jpg', posts[0]['images'])
        self.assertNotIn('local/path.jpg', posts[0]['images'])

    def test_text_split(self):
        # Create enough events to trigger split
        events = []
        event_date = (self.start_date + timedelta(days=1)).strftime("%Y-%m-%d")
        for i in range(10):
            events.append({
                'name': f'Long Event Name To Take Up Space {i}', 
                'location': 'Location', 
                'date': event_date,
                'time': 'Time', 
                'image_path': None
            })
        
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        # Check if text length is respected
        for post in posts:
            self.assertTrue(len(post['text']) <= 500)

    def test_build_digest_date_grouping_and_city_prefix(self):
        event_date_1 = (self.start_date + timedelta(days=1)).strftime("%Y-%m-%d")
        event_date_2 = (self.start_date + timedelta(days=2)).strftime("%Y-%m-%d")
        
        events = [
            {
                'name': 'Band Concert A',
                'location': 'The Wall 台北市',
                'date': event_date_1,
                'time': '19:00',
                'image_url': 'http://example.com/a.jpg'
            },
            {
                'name': 'Festival B',
                'location': '駁二藝術特區 高雄市',
                'date': event_date_2,
                'time': '15:00',
                'image_url': 'http://example.com/b.jpg'
            }
        ]
        
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        self.assertEqual(len(posts), 1)
        text = posts[0]['text']
        
        from src.utils.text_cleaners import format_short_date
        short_date_1 = format_short_date(event_date_1)
        short_date_2 = format_short_date(event_date_2)
        
        self.assertIn(f"📅 {short_date_1}", text)
        self.assertIn(f"📅 {short_date_2}", text)
        self.assertIn("[台北] Band Concert A", text)
        self.assertIn("[高雄] Festival B", text)

if __name__ == '__main__':
    unittest.main()
