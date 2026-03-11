import requests

proxies = {
    'http': 'socks5://127.0.0.1:1080',
    'https': 'socks5://127.0.0.1:1080'
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Try to get Twitter trending via free API
print('Testing Twitter via proxy...')

# Method 1: Get tweets from some public account
try:
    r = requests.get(
        'https://api.twitter.com/2/users/783214/tweets?tweet.fields=created_at,public_metrics&max_results=20',
        proxies=proxies,
        headers=headers,
        timeout=30
    )
    print(f'Twitter API Status: {r.status_code}')
    if r.status_code == 200:
        data = r.json()
        print('Success! Recent Tweets:')
        for tweet in data.get('data', [])[:10]:
            text = tweet.get('text', '')[:60]
            print(f"  - {text}")
except Exception as e:
    print(f'Error: {str(e)[:60]}')

# Method 2: Try to get trending via Google
print('\nTesting Google trends...')
try:
    r = requests.get('https://trends.google.com/trends/hottrends/atom/feed', proxies=proxies, timeout=30)
    print(f'Google Trends Status: {r.status_code}')
except Exception as e:
    print(f'Error: {str(e)[:60]}')
