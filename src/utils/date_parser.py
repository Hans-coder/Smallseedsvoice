import re
from datetime import datetime
from typing import Optional

def parse_taiwan_date(date_str: str) -> Optional[str]:
    """
    Parse date strings common in Taiwan ticketing sites to ISO format (YYYY-MM-DD).
    Supported formats:
    - 2025/11/11(二)
    - 2025/11/11
    - 2025.11.11
    - 2025年11月11日
    """
    if not date_str:
        return None
        
    try:
        # Remove whitespace
        clean_str = date_str.strip()
        
        # Remove day of week like (二) or (Tue)
        clean_str = re.sub(r'\(.*?\)', '', clean_str).strip()
        
        # Normalize separators
        clean_str = clean_str.replace('.', '/').replace('-', '/').replace('年', '/').replace('月', '/').replace('日', '')
        
        # Parse
        dt = datetime.strptime(clean_str, "%Y/%m/%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        return None

def parse_time(time_str: str) -> Optional[str]:
    """
    Parse time string to HH:MM format.
    """
    if not time_str:
        return None
    try:
        clean_str = time_str.strip().replace('：', ':')
        # Handle 19:30 cases
        match = re.search(r'(\d{1,2}:\d{2})', clean_str)
        if match:
            return match.group(1)
        return None
    except:
        return None
