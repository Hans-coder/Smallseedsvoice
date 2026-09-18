import unittest
from datetime import datetime
from src.processor.curator_formatter import CuratorFormatter

class TestCuratorFormatter(unittest.TestCase):
    def setUp(self):
        self.sample_free_event = {
            "name": "2026 浪人祭前夜祭",
            "date": "2026-10-02",
            "start_time": "18:00",
            "venue_name": "安平觀夕平台",
            "city": "台南市",
            "price": "免費",
            "performers": ["美秀集團", "怕胖團", "芒果醬"],
            "image_url": "https://example.com/poster.jpg",
            "ticket_platform": "KKTIX",
            "ticket_url": "https://kktix.com/events/sample"
        }

        self.sample_ticketed_event = {
            "name": "草東沒有派對 專場巡演",
            "date": "2026-10-15",
            "start_time": "19:30",
            "venue_name": "Legacy Taipei",
            "city": "台北市",
            "price": "1200",
            "performers": ["草東沒有派對"],
            "image_url": "https://example.com/cd.jpg"
        }

    def test_format_price_badge(self):
        self.assertEqual(CuratorFormatter.format_price_badge(self.sample_free_event), "免費")
        self.assertEqual(CuratorFormatter.format_price_badge(self.sample_ticketed_event), "售票")
        self.assertEqual(CuratorFormatter.format_price_badge({"price": "0"}), "免費")
        self.assertEqual(CuratorFormatter.format_price_badge({"price": ""}), "免費")

    def test_format_spotlight_post(self):
        post = CuratorFormatter.format_spotlight_post(self.sample_free_event)
        self.assertEqual(post["type"], "spotlight")
        self.assertIn("《浪人祭前夜祭》（免費）", post["text"])
        self.assertIn("♥︎美秀集團", post["text"])
        self.assertIn("♥︎怕胖團", post["text"])
        self.assertIn("❑ 地點：[台南市] 安平觀夕平台 ❑", post["text"])
        self.assertIn("💬", post["text"])
        self.assertEqual(post["images"], ["https://example.com/poster.jpg"])

    def test_format_curator_pick_post(self):
        note = "現場吉他音牆壓迫感十足，主唱撕裂嗓音無可取代，今年必看的搖滾專場。"
        post = CuratorFormatter.format_curator_pick_post(
            self.sample_ticketed_event,
            curator_recommendation=note,
            highlight_song="大風吹"
        )
        self.assertEqual(post["type"], "curator_pick")
        self.assertIn("【小聲音私心推 🎧】《草東沒有派對 專場巡演》", post["text"])
        self.assertIn(note, post["text"])
        self.assertIn("〈大風吹〉", post["text"])
        self.assertIn("Legacy Taipei", post["text"])
        self.assertIn("售票", post["text"])

    def test_format_upgraded_cover_text(self):
        cover = CuratorFormatter.format_upgraded_cover_text(
            start_date=datetime(2026, 9, 21),
            end_date=datetime(2026, 9, 27),
            event_count=45,
            free_count=8,
            hot_count=3
        )
        self.assertIn("【全台音樂活動週報 🎸】", cover)
        self.assertIn("45 場音樂現場", cover)
        self.assertIn("8 場完全免費戶外/市集活動", cover)
        self.assertIn("展演空間", cover)

if __name__ == '__main__':
    unittest.main()
