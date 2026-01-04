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
        
        Args:
            text: 帖子文本
            image_url: 圖片URL (必須是公開可訪問的URL)
            reply_to_id: 回覆的帖子ID (用於串聯貼文)
        
        Returns:
            創建的帖子ID或None
        """
        if not self.user_id:
            logger.error("用戶ID未設置，無法發布")
            return None
        
        try:
            # 1. 創建媒體容器
            container_id = self._create_container(text, image_url, reply_to_id)
            if not container_id:
                return None
            
            # 等待容器準備就緒
            self._wait_for_container(container_id)
            
            # 2. 發布容器
            post_id = self._publish_container(container_id)
            return post_id
            
        except Exception as e:
            logger.error(f"發布Threads帖子失敗: {str(e)}")
            return None

    def post_thread(self, posts: List[Dict]) -> List[str]:
        """
        發布一串貼文 (Threaded Posts)
        
        Args:
            posts: 貼文列表，每個元素包含 {'text': str, 'image_url': str}
            
        Returns:
            發布成功的帖子ID列表
        """
        created_ids = []
        parent_id = None
        
        for i, post in enumerate(posts):
            logger.info(f"正在發布第 {i+1}/{len(posts)} 則貼文...")
            text = post.get('text')
            image_url = post.get('image_url') # Dictionary key should match what DigestBuilder produces
            
            # 如果 DigestBuilder 用 'images' 列表，我們這裡只取第一個 (目前 API 限制單圖或 Carousel，這裡先簡化為單圖)
            # 或者如果需要 Carousel，需要不同的 Container 創建方式
            # 這裡簡單處理：如果有多圖，這個函數需要修改。目前的 DigestBuilder 產生 {'images': []}
            # 我們假設 post['image_url'] 是單張圖片。如果 DigestBuilder 給的是 list，我們取第一個。
            if not image_url and post.get('images'):
                 # 簡單取第一張圖作為代表
                 # 注意：這裡需要是 URL，不能是 local path。
                 # 如果是 local path，這裡會失敗。我們需要確保 DigestBuilder 保留 URL。
                 images = post.get('images', [])
                 if images:
                     # 檢查是否為 URL
                     if images[0].startswith('http'):
                         image_url = images[0]
            
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
            response.raise_for_status()
            result = response.json()
            return result.get('id')
        except Exception as e:
            logger.error(f"創建容器失敗: {str(e)} - Data: {data}")
            return None

    def _wait_for_container(self, container_id: str, timeout: int = 60):
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
                    return
                elif status == 'ERROR':
                    logger.error(f"容器狀態錯誤: {data.get('error_message')}")
                    return
                
                time.sleep(2)
            except Exception as e:
                logger.warning(f"檢查容器狀態失敗: {str(e)}")
                time.sleep(2)
                
        logger.warning(f"等待容器就緒超時: {container_id}")

    def _publish_container(self, container_id: str) -> Optional[str]:
        """發布容器"""
        url = f"{self.api_url}/{self.user_id}/threads_publish"
        data = {
            'access_token': self.access_token,
            'creation_id': container_id
        }
        
        try:
            response = requests.post(url, data=data)
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



