import requests

key = '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'

r = requests.post('https://api.tavily.com/search', 
    json={'api_key': key, 'query': 'Deep Learning Myelodysplastic Syndromes Bone Marrow 2023', 'max_results': 5},
    timeout=20)

if r.status_code == 200:
    data = r.json()
    results = data.get('results', [])
    for i, item in enumerate(results):
        print(f"{i+1}. {item.get('title', 'N/A')}")
        print(f"   {item.get('url', 'N/A')}")
        print()
else:
    print('Error:', r.status_code, r.text[:200])
