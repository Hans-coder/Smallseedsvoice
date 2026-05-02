import json
from bs4 import BeautifulSoup
import requests

url = "https://seasnow.kktix.cc/events/20260509"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
soup = BeautifulSoup(r.text, 'html.parser')

venue = "Unknown"
start_time = None
for script in soup.find_all('script', type='application/ld+json'):
    try:
        ld_data = json.loads(script.string)
        if isinstance(ld_data, list):
            ld_data = ld_data[0]
        if ld_data.get('@type') == 'Event':
            if 'location' in ld_data and 'name' in ld_data['location']:
                venue = ld_data['location']['name']
            if 'startDate' in ld_data:
                start_time_str = ld_data['startDate']
                import re
                t_match = re.search(r'T(\d{2}:\d{2})', start_time_str)
                if t_match:
                    start_time = t_match.group(1)
        print("DEBUG JSON-LD PARSED:", venue, start_time)
    except Exception as e:
        print("DEBUG EXCEPTION:", e)

print("FINAL:", venue, start_time)
