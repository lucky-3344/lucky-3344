import requests
from agent_reach.config import Config

config = Config()
proxy = config.get('reddit_proxy')
print(f"Proxy: {proxy}")

proxies = {
    'http': proxy,
    'https': proxy
}

print("Testing Reddit via proxy...")
try:
    r = requests.get('https://www.reddit.com/r/popular/hot.json?limit=10', 
                    proxies=proxies, 
                    headers={'User-Agent': 'Mozilla/5.0'}, 
                    timeout=30)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print("Success!")
        for post in data['data']['children'][:5]:
            title = post['data']['title']
            print(f"  - {title[:50]}")
except Exception as e:
    print(f"Error: {e}")
