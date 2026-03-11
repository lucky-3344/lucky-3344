import os
import sys
import requests

# Fix encoding
sys.stdout.reconfigure(encoding='utf-8')

TAVILY_API_KEY = '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'

def search_news(query, max_results=10):
    headers = {"Authorization": f"Bearer {TAVILY_API_KEY}", "Content-Type": "application/json"}
    data = {"query": query, "max_results": max_results}
    response = requests.post("https://api.tavily.com/search", headers=headers, json=data, timeout=30)
    return response.json()

# Google News - specific topics
print("=" * 60)
print("Google News - AI & Tech News")
print("=" * 60)
results = search_news("artificial intelligence news 2026", 10)
for i, item in enumerate(results.get('results', []), 1):
    print(f"{i}. {item.get('title', '')[:70]}")
    print(f"   {item.get('url', '')[:80]}\n")

# BBC Chinese - specific topics
print("=" * 60)
print("BBC Chinese - International News")
print("=" * 60)
results = search_news("国际新闻 BBC 中文 2026", 10)
for i, item in enumerate(results.get('results', []), 1):
    print(f"{i}. {item.get('title', '')[:70]}")
    print(f"   {item.get('url', '')[:80]}\n")
