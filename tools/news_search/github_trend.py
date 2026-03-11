import requests
from datetime import datetime

r = requests.get('https://api.github.com/search/repositories?q=created:>2026-02-19&sort=stars&order=desc&per_page=20', timeout=20)
data = r.json()
items = data.get('items', [])[:20]

for i, x in enumerate(items, 1):
    name = x['full_name']
    stars = x['stargazers_count']
    lang = x.get('language', '') or '?'
    print(f"{i:2}. {name} | {stars:,} stars | {lang}")
