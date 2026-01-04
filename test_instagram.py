"""測試Instagram爬蟲"""
import yaml
from pathlib import Path
from src.scraper.instagram_scraper import InstagramScraper
from src.utils.logger import setup_logger

logger = setup_logger("test", "DEBUG")


def test_instagram_scraper():
    """測試Instagram爬蟲"""
    # 載入配置
    config_path = Path("config.yaml")
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    scraper_config = config.get("scraper", {})
    ig_config = config.get("data_sources", {}).get("instagram", {})
    
    # 添加Instagram配置
    if ig_config.get("enabled"):
        scraper_config.update({
            "ig_username": ig_config.get("ig_username"),
            "ig_password": ig_config.get("ig_password")
        })
    
    # 創建爬蟲
    scraper = InstagramScraper(scraper_config)
    
    # 測試抓取
    username = ig_config.get("username", "livetws")
    max_posts = 3  # 測試時只抓取3個貼文
    
    logger.info(f"開始測試抓取 @{username} 的貼文...")
    events = scraper.scrape_events(username, max_posts)
    
    # 顯示結果
    logger.info(f"\n共抓取到 {len(events)} 個活動：")
    for i, event in enumerate(events, 1):
        logger.info(f"\n活動 {i}:")
        logger.info(f"  名稱: {event.get('name')}")
        logger.info(f"  地點: {event.get('location')}")
        logger.info(f"  時間: {event.get('time')}")
        logger.info(f"  價格類型: {event.get('price_type')}")
        logger.info(f"  圖片URL: {event.get('image_url', '無')}")
        logger.info(f"  來源: {event.get('source_url')}")
        if event.get('caption'):
            logger.info(f"  貼文內容（前100字）: {event.get('caption')[:100]}...")


if __name__ == "__main__":
    test_instagram_scraper()


