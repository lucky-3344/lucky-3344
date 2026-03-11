import requests

key = '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'

# 搜索具体的文献 DOI
queries = [
    "10.1182/blood.2022016785 TGF-beta bone marrow fibrosis",
    "TGF-beta Inhibition Reverses Bone Marrow Fibrosis Preclinical Models abstract"
]

for query in queries:
    print(f"\n=== 搜索: {query} ===")
    r = requests.post('https://api.tavily.com/search', 
        json={'api_key': key, 'query': query, 'max_results': 3},
        timeout=20)
    
    if r.status_code == 200:
        data = r.json()
        results = data.get('results', [])
        for i, item in enumerate(results):
            print(f"\n{i+1}. {item.get('title', 'N/A')}")
            print(f"   {item.get('url', 'N/A')}")
            print(f"   {item.get('content', 'N/A')[:500]}")
