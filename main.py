"""主程序入口"""
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv
from src.scraper.music_sites import GenericMusicScraper
from src.scraper.instagram_scraper import InstagramScraper
from src.processor.data_processor import DataProcessor
from src.processor.image_handler import ImageHandler
from src.database.db_manager import DatabaseManager
from src.threads.threads_poster import ThreadsPoster
from src.utils.logger import setup_logger

# 載入環境變數
load_dotenv()

# 設置日誌
logger = setup_logger("main", os.getenv("LOG_LEVEL", "INFO"))


def load_config() -> dict:
    """載入配置文件"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        logger.error("配置文件不存在: config.yaml")
        return {}
    
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    return config


def main():
    """主函數"""
    logger.info("=" * 50)
    logger.info("台灣音樂活動抓取與發布系統啟動")
    logger.info("=" * 50)
    
    # 載入配置
    config = load_config()
    if not config:
        logger.error("無法載入配置，程序退出")
        return
    
    # 初始化各模組
    scraper_config = config.get("scraper", {})
    # 添加Instagram配置到scraper_config
    ig_config = config.get("data_sources", {}).get("instagram", {})
    if ig_config.get("enabled"):
        scraper_config.update({
            "ig_username": ig_config.get("ig_username"),
            "ig_password": ig_config.get("ig_password")
        })
    
    processor = DataProcessor()
    image_handler = ImageHandler(
        download_path=config.get("images", {}).get("download_path", "data/images"),
        max_size_mb=config.get("images", {}).get("max_size_mb", 5),
        allowed_formats=config.get("images", {}).get("allowed_formats", ["jpg", "jpeg", "png", "webp"])
    )
    db_manager = DatabaseManager(
        db_path=config.get("database", {}).get("path", "data/events.db")
    )
    
    # 初始化Threads發布器
    access_token = os.getenv("THREADS_ACCESS_TOKEN")
    if not access_token:
        logger.warning("Threads訪問令牌未設置，將跳過發布步驟")
        threads_poster = None
    else:
        threads_poster = ThreadsPoster(
            access_token=access_token,
            app_id=os.getenv("THREADS_APP_ID"),
            app_secret=os.getenv("THREADS_APP_SECRET")
        )
    
    # 抓取活動
    logger.info("開始抓取音樂活動...")
    all_events = []
    
    # 抓取Instagram貼文（支援多個帳號）
    ig_config = config.get("data_sources", {}).get("instagram", {})
    if ig_config.get("enabled"):
        # 優先使用多帳號配置
        accounts = ig_config.get("accounts", [])
        if accounts:
            # 多帳號模式
            for account_config in accounts:
                if not account_config.get("enabled", True):
                    logger.info(f"跳過未啟用的帳號: {account_config.get('username')}")
                    continue
                
                ig_username = account_config.get("username")
                max_posts = account_config.get("max_posts", 20)
                logger.info(f"正在抓取Instagram: @{ig_username}")
                try:
                    ig_scraper = InstagramScraper(scraper_config)
                    ig_events = ig_scraper.scrape_events(ig_username, max_posts)
                    all_events.extend(ig_events)
                    logger.info(f"從 @{ig_username} 抓取到 {len(ig_events)} 個活動")
                except Exception as e:
                    logger.error(f"Instagram抓取失敗 (@{ig_username}): {str(e)}")
        else:
            # 單帳號模式（向後兼容）
            ig_username = ig_config.get("username", "livetws")
            max_posts = ig_config.get("max_posts", 20)
            logger.info(f"正在抓取Instagram: @{ig_username}")
            try:
                ig_scraper = InstagramScraper(scraper_config)
                ig_events = ig_scraper.scrape_events(ig_username, max_posts)
                all_events.extend(ig_events)
                logger.info(f"從Instagram抓取到 {len(ig_events)} 個活動")
            except Exception as e:
                logger.error(f"Instagram抓取失敗: {str(e)}")
    
    # 抓取網站
    data_sources = config.get("data_sources", {}).get("sites", [])
    for site in data_sources:
        if not site.get("enabled", False):
            logger.info(f"跳過未啟用的網站: {site.get('name')}")
            continue
        
        logger.info(f"正在抓取: {site.get('name')} - {site.get('url')}")
        scraper = GenericMusicScraper(scraper_config)
        events = scraper.scrape_events(site.get("url"))
        all_events.extend(events)
    
    logger.info(f"共抓取到 {len(all_events)} 個活動")
    
    # 時間範圍過濾
    time_filter_config = config.get("data_sources", {}).get("time_filter", {})
    if time_filter_config.get("enabled", False):
        start_date = time_filter_config.get("start_date")
        end_date = time_filter_config.get("end_date")
        logger.info(f"應用時間過濾：{start_date} 至 {end_date}")
        all_events = processor.filter_events_by_time_range(all_events, start_date, end_date)
        logger.info(f"時間過濾後剩餘 {len(all_events)} 個活動")
    
    # 處理活動數據
    logger.info("開始處理活動數據...")
    processed_events = []
    for event in all_events:
        # 清洗數據
        cleaned_event = processor.clean_event_data(event)
        if not cleaned_event:
            continue
        
        # 下載圖片
        if cleaned_event.get('image_url'):
            image_path = image_handler.get_image_path(
                cleaned_event['name'],
                cleaned_event['image_url']
            )
            
            # 嘗試下載圖片
            download_success = False
            # 如果是Instagram來源，可能需要特殊處理
            if 'instagram.com' in cleaned_event.get('source_url', ''):
                # Instagram圖片可能需要使用不同的方法
                # 先嘗試普通下載
                scraper = GenericMusicScraper(scraper_config)
                download_success = scraper.download_image(cleaned_event['image_url'], image_path)
            else:
                scraper = GenericMusicScraper(scraper_config)
                download_success = scraper.download_image(cleaned_event['image_url'], image_path)
            
            if download_success:
                if image_handler.validate_image(image_path):
                    cleaned_event['image_path'] = image_path
                else:
                    logger.warning(f"圖片驗證失敗: {image_path}")
            else:
                logger.warning(f"圖片下載失敗: {cleaned_event.get('image_url')}")
        
        processed_events.append(cleaned_event)
    
    # 保存到數據庫
    logger.info("保存活動到數據庫...")
    new_events_count = 0
    for event in processed_events:
        if db_manager.add_event(event):
            new_events_count += 1
    
    logger.info(f"新增 {new_events_count} 個活動到數據庫")
    
    # 發布到Threads
    delete_images_after_post = config.get("images", {}).get("delete_after_post", True)
    if threads_poster:
        logger.info("開始發布到Threads...")
        unposted_events = db_manager.get_unposted_events()
        post_template = config.get("threads", {}).get("post_format", {}).get("template", "")
        
        posted_count = 0
        for event in unposted_events:
            # 格式化文本
            formatted_text = processor.format_for_threads(event, post_template)
            
            # 發布
            if threads_poster.post_event(event, formatted_text):
                db_manager.mark_as_posted(event['id'])
                posted_count += 1
                logger.info(f"活動已發布: {event['name']}")
                
                # 發布成功後刪除圖片（如果啟用）
                if delete_images_after_post and event.get('image_path'):
                    image_path = Path(event['image_path'])
                    if image_path.exists():
                        try:
                            image_path.unlink()
                            logger.info(f"已刪除圖片: {image_path}")
                        except Exception as e:
                            logger.warning(f"刪除圖片失敗: {image_path} - {str(e)}")
            else:
                logger.error(f"活動發布失敗: {event['name']}")
        
        logger.info(f"共發布 {posted_count} 個活動到Threads")
    else:
        logger.info("跳過Threads發布（未配置API）")
    
    logger.info("=" * 50)
    logger.info("程序執行完成")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

