import requests
import json
url = "https://discord.com/api/webhooks/1500194960455237834/yG_ljYOXQ60Z7ulATuo-3O2Md4HLQ1OsfQde5XmO4s6Cs4KX0t2p3c-FsnlosFOoc4um"

with open("artifacts/card_1.jpg", "rb") as f:
    files = {
        "file": ("card_1.jpg", f, "image/jpeg")
    }
    payload = {
        "content": "TEST PAYLOAD: Are performers present?"
    }
    res = requests.post(url, data=payload, files=files)
    print(res.status_code, res.text)
