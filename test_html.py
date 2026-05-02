from bs4 import BeautifulSoup
import requests

url = "https://seasnow.kktix.cc/events/20260509"
headers = {"User-Agent": "Mozilla/5.0"}
r = requests.get(url, headers=headers)
soup = BeautifulSoup(r.text, 'html.parser')

print("--- TEXT ---")
print(soup.get_text()[:1000])

print("--- META TAGS ---")
for meta in soup.find_all('meta'):
    print(meta.get('property'), meta.get('name'), meta.get('content'))

print("--- SCRIPT JSON-LD ---")
for script in soup.find_all('script', type='application/ld+json'):
    print(script.string)

