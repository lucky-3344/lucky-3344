import requests

key = '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'

# 精确搜索
query = '"TGF-β Inhibition" "bone marrow fibrosis" blood 2022 2023 doi:10.1182'

r = requests.post('https://api.tavily.com/search', 
    json={'api_key': key, 'query': query, 'max_results': 5},
    timeout=20)

print("Status:", r.status_code)
if r.status_code == 200:
    data = r.json()
    results = data.get('results', [])
    for i, item in enumerate(results):
        print(f"\n=== 结果 {i+1} ===")
        print(f"标题: {item.get('title', 'N/A')}")
        print(f"链接: {item.get('url', 'N/A')}")
        print(f"内容: {item.get('content', 'N/A')}")
