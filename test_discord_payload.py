import requests
import json
import os

webhook_url = os.environ.get('DISCORD_WEBHOOK_URL')
print("Webhook URL starts with:", webhook_url[:10] if webhook_url else "None")
