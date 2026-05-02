import json
from src.utils.ai_enricher import AIEnricher
with open('data/digest_raw.json', 'r') as f:
    events = json.load(f)

events_needing = []
for e in events:
    if e.get('ticket_platform') == 'KKTIX':
        desc = str(e.get('price', ''))[:300] if e.get('price') else ""
        events_needing.append({
            "activity_id": e.get('activity_id'),
            "title": e.get('name') or e.get('activity_name', ''),
            "description": desc
        })

enricher = AIEnricher()
res = enricher.extract_performers_batch(events_needing[:3])
print(json.dumps(res, indent=2, ensure_ascii=False))
