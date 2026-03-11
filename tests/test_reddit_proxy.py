import requests
import os

# Set proxy from environment
os.environ['HTTP_PROXY'] = 'socks5://127.0.0.1:1080'
os.environ['HTTPS_PROXY'] = 'socks5://127.0.0.1:1080'

proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

print('Testing Reddit via proxy...')
try:
    r = requests.get('https://www.reddit.com/r/all/hot.json?limit=25', timeout=60, proxies=proxies, headers={'User-Agent': 'Mozilla/5.0'})
    print('Status:', r.status_code)
    if r.status_code == 200:
        data = r.json()
        print('\nReddit Hot Posts:')
        print('='*50)
        for i, post in enumerate(data['data']['children'][:15], 1):
            title = post['data']['title'][:55]
            score = post['data']['score']
            print(f"{i:2}. [{score:>5}] {title}")
except Exception as e:
    print(f'Error: {str(e)[:80]}')
