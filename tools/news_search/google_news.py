import os
import sys
import requests

TAVILY_API_KEY = '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'

def search_news(query, max_results=10):
    headers = {"Authorization": f"Bearer {TAVILY_API_KEY}", "Content-Type": "application/json"}
    data = {"query": query, "max_results": max_results}
    response = requests.post("https://api.tavily.com/search", headers=headers, json=data, timeout=30)
    return response.json()

# Google News
results = search_news("site:news.google.com", 10)
print("Google News Results:")
for i, item in enumerate(results.get('results', []), 1):
    print(f"{i}. {item.get('title', '')[:70]}")
