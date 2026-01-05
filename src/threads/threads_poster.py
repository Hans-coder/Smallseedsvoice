"""Threads發布模組"""
import os
import requests
import time
from typing import Dict, Optional, List
from pathlib import Path
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ThreadsPoster:
    """Threads發布類 (基於 Meta Graph API)"""
    
    def __init__(self, access_token: str, app_id: str = None, app_secret: str = None):
        """
        初始化Threads發布器
        
        Args:
            access_token: Threads API訪問令牌
            app_id: 應用ID（可選）
            app_secret: 應用密鑰（可選）
        """
        self.access_token = access_token
        self.app_id = app_id
        self.app_secret = app_secret
        self.api_url = "https://graph.threads.net/v1.0"
        self.user_id = None
        self._get_user_id()
    
    def _get_user_id(self):
        """獲取用戶ID"""
        try:
            url = f"{self.api_url}/me"
            params = {
                "access_token": self.access_token,
                "fields": "id,username"
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            self.user_id = data.get("id")
            logger.info(f"Threads用戶ID獲取成功: {self.user_id} (@{data.get('username')})")
        except Exception as e:
            logger.error(f"獲取Threads用戶ID失敗: {str(e)}")
    
    def create_post(self, text: str, image_url: Optional[str] = None, reply_to_id: Optional[str] = None) -> Optional[str]:
        """
        創建並發布Threads帖子 (Container -> Publish)
        """
        if not self.user_id:
            logger.error("用戶ID未設置，無法發布")
            return None
        
        try:
            # 1. 創建媒體容器
            container_id = self._create_container(text, image_url, reply_to_id)
            if not container_id:
                return None
            
            # 等待容器準備就緒 (如果是純文字通常不需等待，但API習慣一致較安全)
            if not self._wait_for_container(container_id):
                logger.error(f"容器未就緒，無法發布: {container_id}")
                return None
            
            # 2. 發布容器
            post_id = self._publish_container(container_id)
            return post_id
            
        except Exception as e:
            logger.error(f"發布Threads帖子失敗: {str(e)}")
            return None

    def post_thread(self, posts: List[Dict]) -> List[str]:
        """
        發布一串貼文 (Threaded Posts)。支援單張圖片。
        
        Args:
            posts: 貼文列表，每個元素包含 {'text': str, 'images': List[str]}
            
        Returns:
            發布成功的帖子ID列表
        """
        created_ids = []
        parent_id = None
        
        for i, post in enumerate(posts):
            logger.info(f"正在發布第 {i+1}/{len(posts)} 則貼文...")
            text = post.get('text')
            images = post.get('images', [])
            
            # Threads API 為單張圖片或 Carousel。這裡我們先實作單張圖片。
            # 必須是公開可訪問的 URL。
            image_url = None
            for img in images:
                if img.startswith('http'):
                    image_url = img
                    break
            
            post_id = self.create_post(text, image_url, reply_to_id=parent_id)
            
            if post_id:
                created_ids.append(post_id)
                parent_id = post_id
                # 稍微等待一下，避免速率限制
                time.sleep(5) 
            else:
                logger.error(f"第 {i+1} 則貼文發布失敗，停止後續發布")
                break
                
        return created_ids

    def _create_container(self, text: str, image_url: Optional[str] = None, reply_to_id: Optional[str] = None) -> Optional[str]:
        """創建媒體容器"""
        url = f"{self.api_url}/{self.user_id}/threads"
        data = {
            'access_token': self.access_token,
            'media_type': 'IMAGE' if image_url else 'TEXT',
            'text': text
        }
        
        if image_url:
            data['image_url'] = image_url
            
        if reply_to_id:
            data['reply_to_id'] = reply_to_id
            
        try:
            response = requests.post(url, data=data)
            if not response.ok:
                logger.error(f"創建容器 API 報錯: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result.get('id')
        except Exception as e:
            logger.error(f"創建容器失敗: {str(e)}")
            return None

    def _wait_for_container(self, container_id: str, timeout: int = 60) -> bool:
        """等待容器就緒"""
        start_time = time.time()
        url = f"{self.api_url}/{container_id}"
        params = {
            'access_token': self.access_token,
            'fields': 'status,error_message'
        }
        
        while time.time() - start_time < timeout:
            try:
                response = requests.get(url, params=params)
                data = response.json()
                status = data.get('status')
                
                if status == 'FINISHED':
                    return True
                elif status == 'ERROR':
                    logger.error(f"容器狀態錯誤: {data.get('error_message')}")
                    return False
                
                time.sleep(2)
            except Exception as e:
                logger.warning(f"檢查容器狀態失敗: {str(e)}")
                time.sleep(2)
                
        logger.warning(f"等待容器就緒超時: {container_id}")
        return False

    def _publish_container(self, container_id: str) -> Optional[str]:
        """發布容器"""
        url = f"{self.api_url}/{self.user_id}/threads_publish"
        data = {
            'access_token': self.access_token,
            'creation_id': container_id
        }
        
        try:
            response = requests.post(url, data=data)
            if not response.ok:
                logger.error(f"發布容器 API 報錯: {response.text}")
            response.raise_for_status()
            result = response.json()
            return result.get('id')
        except Exception as e:
            logger.error(f"發布容器失敗: {str(e)}")
            return None
    
    def post_event(self, event: Dict, formatted_text: str) -> bool:
        """發布單個活動 (兼容舊接口)"""
        # 注意: 這裡需要 image_url 而不是 path
        image_url = event.get('image_url')
        post_id = self.create_post(formatted_text, image_url)
        return post_id is not None



