import requests
import json

# Tavily API key from TOOLS.md
API_KEY = "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"

# 使用POST请求
url = "https://api.tavily.com/search"

headers = {
    "Content-Type": "application/json"
}

# 搜索今日国际新闻
queries = [
    "world news March 3 2026",
    "AI artificial intelligence breakthrough 2026",
    "tech industry news today"
]

for query in queries:
    payload = {
        "api_key": API_KEY,
        "query": query,
        "search_depth": "advanced",
        "include_answer": True,
        "max_results": 5
    }
    
    try:
        print(f"\nSearching: {query}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Results: {len(data.get('results', []))}")
            
            # 打印结果
            if data.get('results'):
                print("\nTop results:")
                for i, result in enumerate(data['results'][:3], 1):
                    print(f"{i}. {result.get('title', 'N/A')[:80]}")
                    print(f"   {result.get('url', 'N/A')[:60]}...")
            
            if data.get('answer'):
                print(f"\nAnswer: {data['answer'][:200]}...")
    except Exception as e:
        print(f"Error: {e}")

print("\nDone!")
