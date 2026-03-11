import requests
import os

# 设置代理
proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

# 尝试获取新闻
urls = [
    ('CNN World', 'https://edition.cnn.com/world'),
    ('Reuters', 'https://www.reuters.com/world/'),
    ('Hacker News', 'https://news.ycombinator.com/'),
    ('GitHub Trending', 'https://github.com/trending'),
]

print("Testing proxy connectivity...\n")

for name, url in urls:
    try:
        print(f'Testing {name} ({url})...')
        response = requests.get(url, timeout=15, proxies=proxies)
        print(f'  Status: {response.status_code}')
        if response.status_code == 200:
            print(f'  OK! Length: {len(response.text)}')
    except Exception as e:
        print(f'  Error: {str(e)[:100]}')

print("\nDone.")
