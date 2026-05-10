"""數據處理模組"""
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from src.utils.logger import setup_logger
from src.utils.ai_enricher import AIEnricher

logger = setup_logger(__name__)


class DataProcessor:
    """數據處理類"""
    
    def __init__(self, ai_enricher: Optional[AIEnricher] = None):
        """初始化數據處理器"""
        self.exclude_keywords = ['Talk', '講座', '工作坊', '課程', '分享會']
        self.priority_keywords = ['Live', 'Concert', '專場', '發片', '巡迴']
        self.ai_enricher = ai_enricher

    
    def filter_by_keywords(self, events: List[Dict]) -> List[Dict]:
        """
        根據關鍵字過濾活動
        """
        filtered = []
        for event in events:
            name = event.get('name', '').lower()
            if any(k.lower() in name for k in self.exclude_keywords):
                logger.debug(f"過濾排除關鍵字活動: {name}")
                continue
            filtered.append(event)
        return filtered

    def clean_event_data(self, event: Dict) -> Optional[Dict]:
        """
        清洗活動數據
        
        Args:
            event: 原始活動數據
        
        Returns:
            清洗後的活動數據或None
        """
        try:
            # 驗證必要字段
            if not event.get('name'):
                logger.warning("活動缺少名稱，跳過")
                return None
            
            # 清理和標準化數據
            cleaned = {
                'name': event['name'].strip(),
                'location': event.get('location', '未提供').strip(),
                'time': event.get('time', '未提供').strip(),
                'price_type': event.get('price_type', '未知'),
                'image_url': event.get('image_url'),
                'source_url': event.get('source_url', ''),
                'created_at': datetime.now().isoformat(),
            }
            
            # 驗證價格類型
            if cleaned['price_type'] not in ['免費', '付費', '未知']:
                cleaned['price_type'] = '未知'
            
            return cleaned
        except Exception as e:
            logger.error(f"數據清洗失敗: {str(e)}")
            return None

    def enrich_locations_batch(self, events: List[Dict]) -> List[Dict]:
        """
        批次修復遺失的地點資訊
        """
        if not self.ai_enricher:
            return events

        for event in events:
            venue = event.get('venue_name') or event.get('venue') or event.get('location')
            if not venue or venue in ['Unknown', '未提供', 'See Details', '場地詳見活動頁']:
                # 嘗試修復
                recovered = self.ai_enricher.recover_missing_venue(
                    event.get('name', ''), 
                    event.get('description', '')
                )
                if recovered:
                    logger.info(f"AI 修復地點: {event.get('name')} -> {recovered}")
                    event['location'] = recovered
                    event['venue_name'] = recovered
        
        return events
    
    def format_for_threads(self, event: Dict, template: str) -> str:
        """
        格式化活動數據為Threads發布格式
        
        Args:
            event: 活動數據
            template: 模板字符串
        
        Returns:
            格式化後的文本
        """
        try:
            # 提取地點標籤（用於hashtag）
            location_tag = self._extract_location_tag(event.get('location', ''))
            
            formatted = template.format(
                event_name=event['name'],
                location=event['location'],
                time=event['time'],
                price_type=event['price_type'],
                location_tag=location_tag
            )
            
            return formatted
        except Exception as e:
            logger.error(f"格式化失敗: {str(e)}")
            return f"🎵 {event.get('name', '音樂活動')}\n\n📍 {event.get('location', '未提供')}\n🕐 {event.get('time', '未提供')}"
    
    def _extract_location_tag(self, location: str) -> str:
        """
        從地點提取hashtag標籤
        
        Args:
            location: 地點字符串
        
        Returns:
            hashtag標籤
        """
        # 簡單的提取邏輯，可以根據需要改進
        if '台北' in location or 'Taipei' in location or 'Legacy' in location or 'Revolver' in location:
            return '台北音樂'
        elif '台中' in location or 'Taichung' in location:
            return '台中音樂'
        elif '高雄' in location or 'Kaohsiung' in location or '駁二' in location:
            return '高雄音樂'
        elif '台南' in location or 'Tainan' in location or 'TCRC' in location:
            return '台南音樂'
        else:
            return '台灣音樂'
    
    def filter_events_by_time_range(self, events: List[Dict], start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        根據時間範圍過濾活動
        
        Args:
            events: 活動列表
            start_date: 開始日期（格式：YYYY-MM-DD 或 "today" 或 "+Ndays"）
            end_date: 結束日期（格式：YYYY-MM-DD 或 "+Ndays"）
        
        Returns:
            過濾後的活動列表
        """
        if not start_date and not end_date:
            return events
        
        # 解析開始日期
        if start_date == "today" or start_date is None:
            start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        elif start_date.startswith("+"):
            # 格式：+Ndays
            days = int(start_date.replace("days", "").replace("+", "").replace("day", ""))
            start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=days)
        else:
            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            except:
                start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 解析結束日期
        if end_date is None:
            end_dt = start_dt + timedelta(days=30)  # 預設30天
        elif end_date.startswith("+"):
            # 格式：+Ndays（相對於開始日期）
            days = int(end_date.replace("days", "").replace("+", "").replace("day", ""))
            end_dt = start_dt + timedelta(days=days)
        else:
            try:
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            except:
                end_dt = start_dt + timedelta(days=30)
        
        filtered_events = []
        for event in events:
            event_time_str = event.get('time', '')
            if not event_time_str or event_time_str == '未提供':
                # 如果沒有時間資訊，保留該活動
                filtered_events.append(event)
                continue
            
            # 嘗試解析活動時間
            event_date = self._parse_event_date(event_time_str)
            if event_date:
                # 若解析出的時間帶有時區，則移除時區資訊以便與 start_dt/end_dt (naive) 比較
                if event_date.tzinfo is not None:
                    event_date = event_date.replace(tzinfo=None)
                    
                # 檢查是否在時間範圍內
                if start_dt <= event_date <= end_dt:
                    filtered_events.append(event)
                else:
                    logger.debug(f"活動時間不在範圍內，已過濾: {event.get('name')} ({event_time_str})")
            else:
                # 無法解析時間，保留該活動
                filtered_events.append(event)
        
        logger.info(f"時間過濾：{len(events)} -> {len(filtered_events)} 個活動")
        return filtered_events
    
    def _parse_event_date(self, time_str: str) -> Optional[datetime]:
        """
        解析活動時間字符串為datetime對象
        
        Args:
            time_str: 時間字符串（如 "2025/12/25 PM18:00"）
        
        Returns:
            datetime對象或None
        """
        if not time_str or time_str == '未提供':
            return None
        
        # 常見的時間格式模式
        patterns = [
            r'(\d{4})[年/](\d{1,2})[月/](\d{1,2})[日/]',  # 2025/12/25 或 2025年12月25日
            r'(\d{4})\.(\d{1,2})\.(\d{1,2})',  # 2025.12.25
            r'(\d{1,2})[月/](\d{1,2})[日/]',  # 12/25 或 12月25日
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # 2025-12-25
        ]
        
        for pattern in patterns:
            match = re.search(pattern, time_str)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 3:
                        year, month, day = groups
                        year = int(year)
                        month = int(month)
                        day = int(day)
                        # 如果年份只有2位數，假設是20xx年
                        if year < 100:
                            year += 2000
                        return datetime(year, month, day)
                    elif len(groups) == 2:
                        # 只有月日，使用當前年份
                        month, day = groups
                        year = datetime.now().year
                        return datetime(year, int(month), int(day))
                except (ValueError, TypeError) as e:
                    logger.debug(f"解析時間失敗: {time_str} - {str(e)}")
                    continue
        
        # 嘗試使用dateutil解析
        try:
            # 移除常見的中文字符和符號
            clean_str = time_str.replace('年', '-').replace('月', '-').replace('日', '').replace('/', '-')
            return date_parser.parse(clean_str, fuzzy=True)
        except:
            pass
        
        return None
    
    def filter_events_by_week(self, events: List[Dict]) -> List[Dict]:
        """
        過濾出本週的活動（已棄用，請使用 filter_events_by_time_range）
        
        Args:
            events: 活動列表
        
        Returns:
            本週的活動列表
        """
        today = datetime.now()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        return self.filter_events_by_time_range(
            events, 
            start_date=week_start.strftime("%Y-%m-%d"),
            end_date=week_end.strftime("%Y-%m-%d")
        )


