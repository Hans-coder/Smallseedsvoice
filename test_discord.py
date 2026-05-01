import requests
import json
import sys

webhook_url = sys.argv[1]

# Try sending a file using exactly the logic we have
with open("data/digest_raw.json", "wb") as f:
    f.write(b"fake image data")

payload = {}
files = {'file': ('fake.jpg', open("data/digest_raw.json", "rb"))}

response = requests.post(webhook_url, data=payload, files=files)
print(response.status_code, response.text)
