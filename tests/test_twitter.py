import requests

# Twitter alternative via Nitter (no auth needed)
print("Testing Twitter alternatives...")

# Try alternative Twitter frontends
urls = [
    ('Nitter', 'https://nitter.net'),
    ('Twitter', 'https://twitter.com'),
    ('Fxtwitter', 'https://fxtwitter.com'),
]

for name, url in urls:
    try:
        r = requests.get(url, timeout=30)
        print(f"{name}: {r.status_code}")
    except Exception as e:
        print(f"{name}: Error - {str(e)[:30]}")
