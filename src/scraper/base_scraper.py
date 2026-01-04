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


