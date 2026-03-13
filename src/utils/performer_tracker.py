"""Performer History Tracking Utility"""
import sqlite3
import os
from datetime import datetime
from typing import List, Set, Dict
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

class PerformerTracker:
    def __init__(self, db_path: str = "data/events.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Ensure the table exists"""
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS performer_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                last_seen_at DATETIME,
                first_seen_at DATETIME
            )
        """)
        conn.commit()
        conn.close()

    def get_new_blood(self, performers: List[str]) -> List[str]:
        """
        Takes a list of performer names and returns those that have NEVER been seen before.
        """
        if not performers:
            return []
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        placeholders = ', '.join(['?'] * len(performers))
        query = f"SELECT name FROM performer_history WHERE LOWER(name) IN ({placeholders})"
        
        # Normalize input to lower for comparison
        lower_performers = [p.lower() for p in performers]
        
        try:
            cursor.execute(query, lower_performers)
            db_results = {row[0].lower() for row in cursor.fetchall()}
            
            new_blood = [p for p in performers if p.lower() not in db_results]
            return new_blood
        except Exception as e:
            logger.error(f"Error checking new blood: {e}")
            return []
        finally:
            conn.close()

    def update_history(self, performers: List[str]):
        """
        Updates the last_seen_at date for performers, or creates new entries.
        """
        if not performers:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for name in performers:
            try:
                # Upsert logic
                cursor.execute("""
                    INSERT INTO performer_history (name, first_seen_at, last_seen_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(name) DO UPDATE SET last_seen_at = excluded.last_seen_at
                """, (name, now, now))
            except Exception as e:
                logger.error(f"Error updating performer history for {name}: {e}")
                
        conn.commit()
        conn.close()
