import os
import requests

TAVILY_API_KEY = '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'

headers = {"Authorization": f"Bearer {TAVILY_API_KEY}", "Content-Type": "application/json"}
data = {"query": "site:news.google.com", "max_results": 10}

r = requests.post("https://api.tavily.com/search", headers=headers, json=data, timeout=30)
print("Status:", r.status_code)
print("Results:", len(r.json().get('results', [])))
print("Data:", r.json())
