"""數據庫管理模組"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseManager:
    """數據庫管理類"""
    
    def __init__(self, db_path: str):
        """
        初始化數據庫管理器
        
        Args:
            db_path: 數據庫文件路徑
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化數據庫表結構"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                location TEXT,
                time TEXT,
                price_type TEXT,
                image_url TEXT,
                image_path TEXT,
                source_url TEXT,
                created_at TEXT,
                posted_at TEXT,
                is_posted INTEGER DEFAULT 0,
                UNIQUE(name, location, time)
            )
        ''')
        
        # 創建索引
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_name_location_time 
            ON events(name, location, time)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_is_posted 
            ON events(is_posted)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"數據庫初始化完成: {self.db_path}")
    
    def add_event(self, event: Dict) -> bool:
        """
        添加活動到數據庫（如果不存在）
        
        Args:
            event: 活動數據
        
        Returns:
            是否成功添加（新活動返回True，已存在返回False）
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO events 
                (name, location, time, price_type, image_url, image_path, source_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                event.get('name'),
                event.get('location'),
                event.get('time'),
                event.get('price_type'),
                event.get('image_url'),
                event.get('image_path'),
                event.get('source_url'),
                event.get('created_at', datetime.now().isoformat())
            ))
            
            is_new = cursor.rowcount > 0
            conn.commit()
            
            if is_new:
                logger.info(f"新活動已添加: {event.get('name')}")
            else:
                logger.debug(f"活動已存在: {event.get('name')}")
            
            return is_new
        except Exception as e:
            logger.error(f"添加活動失敗: {str(e)}")
            return False
        finally:
            conn.close()
    
    def get_unposted_events(self) -> List[Dict]:
        """
        獲取未發布的活動
        
        Returns:
            未發布的活動列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM events 
            WHERE is_posted = 0 
            ORDER BY created_at DESC
        ''')
        
        rows = cursor.fetchall()
        events = [dict(row) for row in rows]
        conn.close()
        
        return events
    
    def mark_as_posted(self, event_id: int):
        """
        標記活動為已發布
        
        Args:
            event_id: 活動ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE events 
            SET is_posted = 1, posted_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), event_id))
        
        conn.commit()
        conn.close()
        logger.info(f"活動已標記為發布: ID {event_id}")
    
    def get_all_events(self, limit: Optional[int] = None) -> List[Dict]:
        """
        獲取所有活動
        
        Args:
            limit: 限制數量
        
        Returns:
            活動列表
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = 'SELECT * FROM events ORDER BY created_at DESC'
        if limit:
            query += f' LIMIT {limit}'
        
        cursor.execute(query)
        rows = cursor.fetchall()
        events = [dict(row) for row in rows]
        conn.close()
        
        return events


