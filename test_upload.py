import requests
import json
import os

webhook_url = "https://discord.com/api/webhooks/1500194960455237834/yG_ljYOXQ60Z7ulATuo-3O2Md4HLQ1OsfQde5XmO4s6Cs4KX0t2p3c-FsnlosFOoc4um"

# Create a dummy image
os.system("echo 'fake image data' > dummy.jpg")

file_path = "dummy.jpg"

payload_dict = {
    "embeds": [{
        "color": 15258703,
        "image": {"url": f"attachment://{os.path.basename(file_path)}"}
    }],
    "content": "📸 展演圖卡 Test Upload"
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
    print("Response:", response.text)
except Exception as e:
    print("Error:", e)
