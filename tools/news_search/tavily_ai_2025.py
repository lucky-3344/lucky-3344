import requests

key = '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'

# 搜索2025年最新AI骨髓病理研究
queries = [
    "deep learning bone marrow biopsy diagnosis 2024 2025",
    "AI myelodysplastic syndromes diagnosis 2024 2025",
    "artificial intelligence bone marrow pathology 2025 research"
]

for query in queries:
    print(f"\n=== 搜索: {query} ===")
    r = requests.post('https://api.tavily.com/search', 
        json={'api_key': key, 'query': query, 'max_results': 5},
        timeout=20)
    
    if r.status_code == 200:
        data = r.json()
        results = data.get('results', [])
        for i, item in enumerate(results):
            print(f"\n{i+1}. {item.get('title', 'N/A')}")
            print(f"   {item.get('url', 'N/A')}")
            print(f"   {item.get('content', 'N/A')[:400]}")
