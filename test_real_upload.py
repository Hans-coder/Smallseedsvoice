import requests
import json
import os
import time

webhook_url = "https://discord.com/api/webhooks/1500194960455237834/yG_ljYOXQ60Z7ulATuo-3O2Md4HLQ1OsfQde5XmO4s6Cs4KX0t2p3c-FsnlosFOoc4um"

for i in range(1, 3):
    file_path = f"artifacts/card_{i}.jpg"

    payload_dict = {
        "embeds": [{
            "color": 15258703,
            "image": {"url": f"attachment://{os.path.basename(file_path)}"}
        }],
        "content": f"📸 展演圖卡 修正後最新版測試 ({i}/2)"
    }

    payload = {"payload_json": json.dumps(payload_dict)}

    try:
        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'image/jpeg')
            }
            response = requests.post(
                webhook_url,
                data=payload,
                files=files,
                timeout=30
            )
        print("Status:", response.status_code)
        time.sleep(2)
    except Exception as e:
        print("Error:", e)
