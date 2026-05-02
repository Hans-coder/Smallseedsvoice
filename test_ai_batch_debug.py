import json, os, re
from google import genai

client = genai.Client(api_key=os.environ['GEMINI_API_KEY'])
events = [
  {"activity_id": "1", "title": "黑鹿季雪 LIVE", "description": "【一鹿向光2】黑鹿季雪 2026 LIVE"},
  {"activity_id": "2", "title": "2am Concert in Hong Kong", "description": "2am live"}
]
prompt = f"""
你是一位精準的資料萃取助理。請幫我從以下 {len(events)} 個活動資訊中，精準提取出「真正的表演者/樂團/歌手/DJ」名稱。

活動名單（包含活動 ID、標題、內文片段）：
{json.dumps(events, ensure_ascii=False)}

要求：
1. 只要回傳「真正的表演者名稱」陣列（例如 ["deca joins", "傷心欲絕"]）。
2. 不要包含「主辦單位」、「贊助商」、「售票平台」等無關實體。
3. 如果從文字中完全看不出誰是表演者，請回傳空陣列 []。
4. 你的回傳格式必須是嚴格的 JSON Object，Key 是 activity_id，Value 是 performers 陣列。

回傳範例：
{{
    "kktix_event_1": ["血肉果汁機", "滅火器"],
    "kktix_event_2": []
}}
"""

try:
    response = client.models.generate_content(model="gemini-2.0-flash-lite", contents=prompt)
    text = response.text.strip()
    print("RAW TEXT:")
    print(text)
except Exception as e:
    print(e)
