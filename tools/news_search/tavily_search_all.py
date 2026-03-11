import requests

key = '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'

# 搜索4篇文献
queries = [
    "Deep Learning Automated Diagnosis Myelodysplastic Syndromes Bone Marrow Blood Advances 2023 abstract",
    "TGF-beta Inhibition Reverses Bone Marrow Fibrosis Blood 2023 abstract",
    "Exosome Drug Resistance Multiple Myeloma Bone Marrow JCO 2023 abstract",
    "WHO Classification Myeloid Neoplasms Blood 2023 bone marrow pathology abstract"
]

for query in queries:
    print(f"\n=== 搜索: {query[:50]}... ===")
    r = requests.post('https://api.tavily.com/search', 
        json={'api_key': key, 'query': query, 'max_results': 3},
        timeout=20)
    
    if r.status_code == 200:
        data = r.json()
        results = data.get('results', [])
        for i, item in enumerate(results):
            print(f"{i+1}. {item.get('title', 'N/A')}")
            print(f"   {item.get('url', 'N/A')}")
            print(f"   摘要: {item.get('content', 'N/A')[:200]}...")
            print()
