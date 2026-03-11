import requests

r = requests.get('https://api.github.com/search/repositories?q=created:>2026-02-20&sort=stars&order=desc', timeout=15)
data = r.json()
items = data.get('items', [])[:10]

for i, x in enumerate(items):
    print(f"{i+1}. {x['full_name']} - {x['stargazers_count']} stars")
    desc = x.get('description', 'N/A')
    if desc:
        print(f"   {desc[:70]}")
    print()
