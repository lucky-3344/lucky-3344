import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
    'Accept': 'application/json',
}

# Bilibili trending
try:
    r = requests.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=web', timeout=10, headers=headers)
    data = r.json()
    if data['code'] == 0:
        print('Bilibili Hot:')
        print('='*50)
        for i, item in enumerate(data['data']['list'][:10], 1):
            title = item['title'][:45]
            view = item['stat']['view']
            print(f"{i:2}. [{view:>10}] {title}")
    else:
        print(f"Bilibili error: {data}")
except Exception as e:
    print(f"Bilibili exception: {e}")

# Baidu hot search
try:
    r = requests.get('https://top.baidu.com/board?tab=realtime', timeout=10, headers=headers)
    print('\nBaidu Hot:')
    print('='*50)
    print("Status:", r.status_code)
except Exception as e:
    print(f"Baidu error: {e}")
