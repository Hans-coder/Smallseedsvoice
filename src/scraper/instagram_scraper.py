"""Instagram爬蟲模組"""
import re
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import instaloader
from abc import ABC
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class InstagramScraper:
    """Instagram爬蟲，用於抓取特定帳號的貼文"""
    
    def __init__(self, config: Dict):
        """
        初始化Instagram爬蟲
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.request_delay = config.get("request_delay", 2)
        self.timeout = config.get("timeout", 30)
        self.retry_count = config.get("retry_count", 3)
        self.headers = {
            "User-Agent": config.get("user_agent", 
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        }
        
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            max_connection_attempts=1,  # Fail fast on 403/Connection errors
            request_timeout=10.0,       # Short timeout
        )
        # 如果需要登錄（抓取私人帳號或避免限流）
        self.ig_username = config.get("ig_username")
        self.ig_password = config.get("ig_password")
        if self.ig_username and self.ig_password:
            try:
                self.loader.login(self.ig_username, self.ig_password)
                logger.info("Instagram登錄成功")
            except Exception as e:
                logger.warning(f"Instagram登錄失敗，將以訪客模式運行: {str(e)}")
    
    def download_image(self, image_url: str, save_path: str) -> bool:
        """
        下載圖片（從BaseScraper複製的方法）
        
        Args:
            image_url: 圖片URL
            save_path: 保存路徑
        
        Returns:
            是否成功
        """
        import time
        import requests
        
        for attempt in range(self.retry_count):
            try:
                time.sleep(self.request_delay)
                response = requests.get(image_url, headers=self.headers, timeout=self.timeout)
                response.raise_for_status()
                
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                
                logger.info(f"圖片下載成功: {save_path}")
                return True
            except Exception as e:
                logger.warning(f"圖片下載失敗 (嘗試 {attempt + 1}/{self.retry_count}): {str(e)}")
                if attempt == self.retry_count - 1:
                    logger.error(f"無法下載圖片: {image_url}")
                    return False
                time.sleep(self.request_delay * (attempt + 1))
        
        return False
    
    def scrape_events(self, username: str, max_posts: int = 20) -> List[Dict]:
        """
        抓取指定Instagram帳號的貼文
        
        Args:
            username: Instagram用戶名（不含@）
            max_posts: 最多抓取的貼文數量
        
        Returns:
            活動列表
        """
        events = []
        try:
            profile = instaloader.Profile.from_username(self.loader.context, username)
            logger.info(f"開始抓取 @{username} 的貼文...")
            
            post_count = 0
            for post in profile.get_posts():
                if post_count >= max_posts:
                    break
                
                event = self.parse_post(post, username)
                if event:
                    events.append(event)
                    post_count += 1
                
                # 避免請求過快
                import time
                time.sleep(self.request_delay)
            
            logger.info(f"從 @{username} 抓取到 {len(events)} 個活動")
        except Exception as e:
            logger.error(f"抓取Instagram貼文失敗: {str(e)}")
        
        return events
    
    def parse_post(self, post, username: str) -> Optional[Dict]:
        """
        解析單個Instagram貼文
        
        Args:
            post: Instaloader Post對象
            username: 用戶名
        
        Returns:
            活動字典或None
        """
        try:
            # 獲取貼文文字
            caption = post.caption or ""
            
            # 檢查是否包含活動相關關鍵字
            if not self._is_event_post(caption):
                return None
            
            # 提取活動資訊
            event = self._extract_event_info(caption, post, username)
            
            return event
        except Exception as e:
            logger.error(f"解析Instagram貼文失敗: {str(e)}")
            return None
    
    def _is_event_post(self, caption: str) -> bool:
        """
        判斷貼文是否為活動相關
        
        Args:
            caption: 貼文文字
        
        Returns:
            是否為活動貼文
        """
        # 活動相關關鍵字
        event_keywords = [
            '音樂', '演出', '演唱會', 'live', 'concert', 'show',
            '活動', 'event', '表演', '演出', '場地', 'venue',
            '免費', '付費', '票價', '時間', '地點', 'location'
        ]
        
        caption_lower = caption.lower()
        # 如果包含至少2個關鍵字，認為是活動貼文
        keyword_count = sum(1 for keyword in event_keywords if keyword in caption_lower)
        return keyword_count >= 2
    
    def _extract_event_info(self, caption: str, post, username: str) -> Dict:
        """
        從貼文文字中提取活動資訊
        
        Args:
            caption: 貼文文字
            post: Post對象
            username: 用戶名
        
        Returns:
            活動字典
        """
        time_str = self._extract_time(caption, post)
        price_type = self._extract_price_type(caption)
        
        # 嘗試從時間字串中提取日期 (YYYY-MM-DD)
        event_date = None
        date_match = re.search(r'(\d{4})[/-](\d{1,2})[/-](\d{1,2})', time_str)
        if date_match:
            event_date = f"{date_match.group(1)}-{date_match.group(2).zfill(2)}-{date_match.group(3).zfill(2)}"
        else:
            # 嘗試找沒有年份的日期 (MM/DD)，假設是今年或明年
            # 這裡簡化處理，如果不確定年份，就用貼文發布時間的年份，或者直接用貼文時間
            short_date_match = re.search(r'(\d{1,2})[/-](\d{1,2})', time_str)
            if short_date_match:
                # 這裡比較難猜年份，先使用貼文時間當作 fallback，或者不做處理
                pass

        # Fallback: 使用貼文發布時間
        if not event_date and post.date_local:
            event_date = post.date_local.strftime("%Y-%m-%d")
            
        # 處理價格
        price = None
        if price_type == '免費':
            price = '0'
        elif price_type == '付費':
            price = '付費' # 用於後續過濾

        event = {
            'name': self._extract_event_name(caption),
            'location': self._extract_location(caption),
            'time': time_str,
            'date': event_date, # 新增 date 欄位
            'price': price,     # 新增 price 欄位
            'price_type': price_type,
            'image_url': None,
            'source_url': f"https://www.instagram.com/p/{post.shortcode}/",
            'caption': caption[:500],
        }
        
        # 獲取圖片URL
        try:
            # instaloader的Post對象，嘗試多種方式獲取圖片URL
            if hasattr(post, 'url'):
                event['image_url'] = post.url
            elif hasattr(post, 'display_url'):
                event['image_url'] = post.display_url
            elif hasattr(post, 'typename') and post.typename == 'GraphImage':
                # 單圖貼文
                if hasattr(post, 'display_url'):
                    event['image_url'] = post.display_url
            elif hasattr(post, 'typename') and post.typename == 'GraphSidecar':
                # 多圖貼文，取第一張
                sidecar_nodes = post.get_sidecar_nodes()
                if sidecar_nodes:
                    event['image_url'] = sidecar_nodes[0].display_url
            
            # 如果還是沒有，嘗試構建URL
            if not event['image_url'] and hasattr(post, 'shortcode'):
                event['image_url'] = f"https://www.instagram.com/p/{post.shortcode}/media/?size=l"
        except Exception as e:
            logger.warning(f"獲取圖片URL失敗: {str(e)}")
        
        return event
    
    def _extract_event_name(self, caption: str) -> str:
        """提取活動名稱"""
        # 嘗試從文字中提取活動名稱
        # 通常活動名稱會在開頭或特定格式中
        lines = caption.split('\n')
        for line in lines[:5]:  # 檢查前5行
            line = line.strip()
            if line and len(line) > 5 and len(line) < 100:
                # 如果這行看起來像標題（沒有太多標點符號）
                if not re.search(r'[📍🕐💰🎵🎤🎸]', line):
                    return line
        
        # 如果找不到，返回前50個字符
        return caption[:50].strip() or "音樂活動"
    
    def _extract_location(self, caption: str) -> str:
        """提取地點"""
        # 尋找地點相關的關鍵字（livetws常用格式：✦ 地點｜...）
        location_patterns = [
            r'[📍✦][：:]\s*地點[｜|]\s*(.+?)(?:\n|$)',
            r'地點[｜|：:]\s*(.+?)(?:\n|$)',
            r'Location[：:]\s*(.+?)(?:\n|$)',
            r'📍\s*(.+?)(?:\n|$)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, caption, re.IGNORECASE)
            if match:
                location = match.group(1).strip()
                # 過濾掉@標記和常見的無用文字
                location = re.sub(r'@\w+', '', location).strip()
                if location and len(location) < 100 and location not in ['livetws', 'metwfoodie']:
                    return location
        
        # 嘗試從文字中找常見場地名稱
        venues = [
            'Legacy', 'The Wall', '河岸留言', '女巫店', '海邊的卡夫卡',
            'Revolver', 'Pipe', 'PIPE', 'Brown Sugar', 'Blue Note',
            '金門', '台北', 'Taipei', '台中', 'Taichung', '高雄', 'Kaohsiung',
            '艋舺', '青山宮', '直興市場', '內湖', '金城鎮'
        ]
        
        for venue in venues:
            if venue in caption:
                return venue
        
        return "未提供"
    
    def _extract_time(self, caption: str, post) -> str:
        """提取時間"""
        # 尋找時間相關的關鍵字（livetws常用格式：✦ 時間｜...）
        time_patterns = [
            r'[🕐✦][：:]\s*時間[｜|]\s*(.+?)(?:\n|$)',
            r'時間[｜|：:]\s*(.+?)(?:\n|$)',
            r'Time[：:]\s*(.+?)(?:\n|$)',
            r'🕐\s*(.+?)(?:\n|$)',
            r'(\d{4}[年/]\d{1,2}[月/]\d{1,2}[日/])\s*(?:\([^)]+\))?\s*(?:PM|AM)?\d{0,2}[：:]\d{0,2}',  # 完整日期時間格式
            r'(\d{1,2}[月/]\d{1,2}[日/])',  # 日期格式
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, caption, re.IGNORECASE)
            if match:
                time_str = match.group(1).strip()
                if time_str and len(time_str) < 100:
                    return time_str
        
        # 如果找不到，使用貼文發布時間
        if post.date_utc:
            return post.date_utc.strftime("%Y年%m月%d日")
        
        return "未提供"
    
    def _extract_price_type(self, caption: str) -> str:
        """提取價格類型"""
        caption_lower = caption.lower()
        
        # 檢查免費相關關鍵字
        free_keywords = ['免費', 'free', '入場免費', '免門票', '0元']
        if any(keyword in caption_lower for keyword in free_keywords):
            return '免費'
        
        # 檢查付費相關關鍵字
        paid_keywords = ['票價', 'ticket', '門票', '入場費', 'NT$', '$', '元']
        if any(keyword in caption_lower for keyword in paid_keywords):
            return '付費'
        
        return '未知'
    
    def download_post_image(self, post, save_path: str) -> bool:
        """
        下載貼文圖片
        
        Args:
            post: Post對象
            save_path: 保存路徑
        
        Returns:
            是否成功
        """
        try:
            # 獲取圖片URL
            image_url = None
            try:
                # instaloader的Post對象，嘗試多種方式獲取圖片URL
                if hasattr(post, 'url'):
                    image_url = post.url
                elif hasattr(post, 'display_url'):
                    image_url = post.display_url
                elif hasattr(post, 'typename') and post.typename == 'GraphImage':
                    # 單圖貼文
                    if hasattr(post, 'display_url'):
                        image_url = post.display_url
                elif hasattr(post, 'typename') and post.typename == 'GraphSidecar':
                    # 多圖貼文，取第一張
                    sidecar_nodes = post.get_sidecar_nodes()
                    if sidecar_nodes:
                        image_url = sidecar_nodes[0].display_url
                
                # 如果還是沒有，嘗試構建URL
                if not image_url and hasattr(post, 'shortcode'):
                    image_url = f"https://www.instagram.com/p/{post.shortcode}/media/?size=l"
            except Exception as e:
                logger.warning(f"獲取圖片URL時出錯: {str(e)}")
            
            if image_url:
                return super().download_image(image_url, save_path)
            return False
        except Exception as e:
            logger.error(f"下載Instagram圖片失敗: {str(e)}")
            return False

