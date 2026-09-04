"""基礎爬蟲類"""
import time
import requests
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class BaseScraper(ABC):
    """基礎爬蟲類，定義通用方法"""
    
    def __init__(self, config: Dict):
        """
        初始化爬蟲
        
        Args:
            config: 配置字典，包含request_delay, timeout, retry_count, user_agent等
        """
        self.config = config
        self.request_delay = config.get("request_delay", 2)
        self.timeout = config.get("timeout", 30)
        self.retry_count = config.get("retry_count", 3)
        self.headers = {
            "User-Agent": config.get("user_agent", 
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """
        獲取網頁內容
        
        Args:
            url: 目標URL
        
        Returns:
            BeautifulSoup對象或None
        """
        for attempt in range(self.retry_count):
            try:
                time.sleep(self.request_delay)
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                return BeautifulSoup(response.text, 'lxml')
            except requests.RequestException as e:
                logger.warning(f"請求失敗 (嘗試 {attempt + 1}/{self.retry_count}): {url} - {str(e)}")
                if attempt == self.retry_count - 1:
                    logger.error(f"無法獲取頁面: {url}")
                    return None
                time.sleep(self.request_delay * (attempt + 1))
        
        return None
    
    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        下載圖片
        
        Args:
            image_url: 圖片URL
            save_path: 保存路徑
        
        Returns:
            是否成功
        """
        if os.path.exists(save_path):
            logger.info(f"圖片已存在，跳過下載: {save_path}")
            return True

        try:
            response = self.session.get(image_url, timeout=self.timeout)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"圖片下載成功: {save_path}")
            return True
        except Exception as e:
            logger.error(f"圖片下載失敗: {image_url} - {str(e)}")
            return False
    
    @abstractmethod
    def scrape_events(self, url: str) -> List[Dict]:
        """
        抓取活動列表（抽象方法，需子類實現）
        
        Args:
            url: 目標URL
        
        Returns:
            活動列表，每個活動包含：
            - name: 活動名稱
            - location: 地點
            - time: 時間
            - price_type: 免費/付費
            - image_url: 節目表圖片URL
            - source_url: 來源URL
        """
        pass
    
    @abstractmethod
    def parse_event(self, element) -> Optional[Dict]:
        """
        解析單個活動元素（抽象方法，需子類實現）
        
        Args:
            element: BeautifulSoup元素
        
        Returns:
            活動字典或None
        """
        pass

    def fetch_with_selenium(self, url: str, wait_time: int = 3, scroll: bool = False, scroll_count: int = 3) -> Optional[BeautifulSoup]:
        """
        Fetch page using Playwright Headless Chromium with optional scrolling.
        (Kept method name fetch_with_selenium for backward compatibility)
        """
        try:
            from playwright.sync_api import sync_playwright
            from bs4 import BeautifulSoup

            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                    ]
                )
                context = browser.new_context(
                    user_agent=self.headers.get(
                        "User-Agent",
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                    ),
                    viewport={"width": 1920, "height": 1080},
                    locale="zh-TW",
                    timezone_id="Asia/Taipei",
                )
                page = context.new_page()
                
                # Mask webdriver flag
                page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

                try:
                    from playwright_stealth import stealth_sync
                    stealth_sync(page)
                except Exception:
                    pass
                
                page.set_default_timeout(20000)
                
                try:
                    page.goto(url, wait_until="domcontentloaded")
                except Exception as nav_err:
                    logger.warning(f"Playwright navigation warning for {url}: {nav_err}")

                import time
                time.sleep(wait_time)
                
                if scroll:
                    for _ in range(scroll_count):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
                        time.sleep(1)
                        
                html = page.content()
                browser.close()
                
                # Genuine Cloudflare challenge indicators
                cf_indicators = [
                    "<title>Just a moment...</title>",
                    "cf-browser-verification",
                    "challenge-platform",
                    "Attention Required! | Cloudflare",
                    "cf-turnstile",
                    "id=\"challenge-running\"",
                    "id=\"challenge-stage\"",
                ]
                if any(ind in html for ind in cf_indicators):
                    logger.warning(f"Scraper blocked by Cloudflare or anti-bot challenge: {url}")
                    return None
                    
                if not html or len(html) < 200:
                    logger.warning(f"Received empty or too small response ({len(html)} bytes) from {url}")
                    return None

            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.error(f"Failed to fetch {url} using Playwright: {e}")
            return None
