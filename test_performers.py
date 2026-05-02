import json
with open('data/digest_raw.json', 'r') as f:
    events = json.load(f)
for e in events:
    print(f"Title: {e.get('name')}")
    print(f"Performers: {e.get('performers')}")
    print("-" * 20)
