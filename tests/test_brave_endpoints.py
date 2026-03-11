import requests

headers = {
    'X-Subscription-Token': 'BSAYjjPJEzfKfEDtGQKxFivR6RbIEqk',
    'Accept': 'application/json'
}

endpoints = [
    'https://api.search.brave.com/res/v1/search?q=test',
]

for url in endpoints:
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f'Status: {r.status_code}')
        print(f'Content-Type: {r.headers.get("Content-Type", "N/A")}')
        print(f'Response: {r.text[:500]}')
    except Exception as e:
        print(f'Error: {e}')
