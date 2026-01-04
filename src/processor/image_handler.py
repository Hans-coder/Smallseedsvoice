"""圖片處理模組"""
import os
from pathlib import Path
from typing import Optional
from PIL import Image
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageHandler:
    """圖片處理類"""
    
    def __init__(self, download_path: str, max_size_mb: int = 5, allowed_formats: List[str] = None):
        """
        初始化圖片處理器
        
        Args:
            download_path: 圖片下載路徑
            max_size_mb: 最大文件大小（MB）
            allowed_formats: 允許的圖片格式
        """
        self.download_path = Path(download_path)
        self.download_path.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.allowed_formats = allowed_formats or ["jpg", "jpeg", "png", "webp"]
    
    def validate_image(self, image_path: str) -> bool:
        """
        驗證圖片文件
        
        Args:
            image_path: 圖片路徑
        
        Returns:
            是否有效
        """
        try:
            # 檢查文件大小
            file_size = os.path.getsize(image_path)
            if file_size > self.max_size_bytes:
                logger.warning(f"圖片文件過大: {image_path} ({file_size / 1024 / 1024:.2f} MB)")
                return False
            
            # 檢查文件格式
            ext = Path(image_path).suffix.lower().lstrip('.')
            if ext not in self.allowed_formats:
                logger.warning(f"不支持的圖片格式: {image_path}")
                return False
            
            # 嘗試打開圖片
            with Image.open(image_path) as img:
                img.verify()
            
            return True
        except Exception as e:
            logger.error(f"圖片驗證失敗: {image_path} - {str(e)}")
            return False
    
    def optimize_image(self, image_path: str, max_width: int = 1920, quality: int = 85) -> Optional[str]:
        """
        優化圖片（壓縮和調整大小）
        
        Args:
            image_path: 原始圖片路徑
            max_width: 最大寬度
            quality: JPEG質量（1-100）
        
        Returns:
            優化後的圖片路徑或None
        """
        try:
            with Image.open(image_path) as img:
                # 調整大小
                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                # 保存優化後的圖片
                output_path = image_path.replace('.', '_optimized.')
                if img.format == 'JPEG' or img.format == 'JPG':
                    img.save(output_path, 'JPEG', quality=quality, optimize=True)
                else:
                    img.save(output_path, format=img.format, optimize=True)
                
                logger.info(f"圖片優化完成: {output_path}")
                return output_path
        except Exception as e:
            logger.error(f"圖片優化失敗: {image_path} - {str(e)}")
            return None
    
    def get_image_path(self, event_name: str, image_url: str) -> str:
        """
        生成圖片保存路徑
        
        Args:
            event_name: 活動名稱
            image_url: 圖片URL
        
        Returns:
            保存路徑
        """
        # 清理活動名稱作為文件名
        safe_name = "".join(c for c in event_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_name = safe_name.replace(' ', '_')[:50]  # 限制長度
        
        # 從URL獲取擴展名（只取問號前的部分）
        url_path = image_url.split('?')[0]  # 移除查詢參數
        ext = Path(url_path).suffix
        
        # 如果沒有擴展名或擴展名太長，使用默認的jpg
        if not ext or len(ext) > 5:
            ext = '.jpg'
        
        # 確保擴展名是支持的格式
        ext_lower = ext.lower()
        if ext_lower not in ['.jpg', '.jpeg', '.png', '.webp', '.gif']:
            ext = '.jpg'
        
        filename = f"{safe_name}{ext}"
        return str(self.download_path / filename)

