import requests
from datetime import datetime
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("GitHub Trending - HOT Projects")
print("=" * 60)

url = 'https://api.github.com/search/repositories?q=created:>2026-02-19&sort=stars&order=desc&per_page=30'
r = requests.get(url, timeout=20)
data = r.json()
items = data.get('items', [])[:20]

print("\n[HOT] TOP 20 Projects\n")

for i, item in enumerate(items, 1):
    name = item['full_name']
    stars = item['stargazers_count']
    desc = (item.get('description') or '')[:60] or 'No description'
    lang = item.get('language', '')
    
    print(f"{i:2}. {name}")
    print(f"    * {stars:,} | {lang if lang else '?'} | {desc}")
    print()

print("=" * 60)
print("Generated:", datetime.now().strftime("%Y-%m-%d %H:%M"))
print("=" * 60)
