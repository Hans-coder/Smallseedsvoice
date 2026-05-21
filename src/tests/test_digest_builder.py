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
        event_date = self.start_date + timedelta(days=1)
        events = [
            {
                'name': 'Event 1', 
                'location': '台北 Loc 1', 
                'date': event_date.strftime('%Y-%m-%d'),
                'time': event_date.strftime('%Y-%m-%d %H:%M'), 
                'image_url': 'http://example.com/img1.jpg'
            }
        ]
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        # Should have 1 post because cover and event are small enough to merge
        self.assertEqual(len(posts), 1)
        self.assertIn('Event 1', posts[0]['text'])
        self.assertIn('http://example.com/img1.jpg', posts[0]['images'])

    def test_image_url_usage(self):
        event_date = self.start_date + timedelta(days=1)
        events = [
            {
                'name': 'Event 1', 
                'location': '台北 Loc 1', 
                'date': event_date.strftime('%Y-%m-%d'),
                'time': event_date.strftime('%Y-%m-%d %H:%M'), 
                'image_url': 'http://example.com/url.jpg', 
                'image_path': 'local/path.jpg'
            }
        ]
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        # Should prioritize image_url for Threads API
        self.assertIn('http://example.com/url.jpg', posts[0]['images'])
        self.assertNotIn('local/path.jpg', posts[0]['images'])

    def test_text_split(self):
        # Create enough events to trigger split
        events = []
        event_date = self.start_date + timedelta(days=1)
        for i in range(10):
            events.append({
                'name': f'Long Event Name To Take Up Space {i}', 
                'location': '台北 Location', 
                'date': event_date.strftime('%Y-%m-%d'),
                'time': event_date.strftime('%Y-%m-%d %H:%M'), 
                'image_path': None
            })
        
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        # Check if text length is respected
        for post in posts:
            self.assertTrue(len(post['text']) <= 500)

    def test_community_prompt_integration(self):
        from unittest.mock import MagicMock
        mock_enricher = MagicMock()
        mock_enricher.generate_community_prompt.return_value = "Test CTA Prompt"
        self.builder.enricher = mock_enricher
        
        event_date = self.start_date + timedelta(days=1)
        events = [
            {
                'name': 'Event 1', 
                'location': '台北 Loc 1', 
                'date': event_date.strftime('%Y-%m-%d'),
                'time': event_date.strftime('%Y-%m-%d %H:%M')
            }
        ]
        posts = self.builder.build_digest(events, self.start_date, self.end_date)
        self.assertIn("Test CTA Prompt", posts[-1]['text'])

if __name__ == '__main__':
    unittest.main()
