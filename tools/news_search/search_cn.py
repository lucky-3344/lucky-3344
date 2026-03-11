import requests

# Bilibili trending
try:
    r = requests.get('https://api.bilibili.com/x/web-interface/ranking/v2?rid=0&type=web', timeout=10)
    data = r.json()
    if data['code'] == 0:
        print('Bilibili Hot:')
        print('='*50)
        for i, item in enumerate(data['data']['list'][:10], 1):
            title = item['title'][:45]
            view = item['stat']['view']
            print(f"{i:2}. [{view:>10}] {title}")
except Exception as e:
    print(f"Error: {e}")

# Douyin trending
try:
    r = requests.get('https://www.douyin.com/aweme/v1/web/hot/search/list/', timeout=10)
    data = r.json()
    if data['code'] == 0:
        print('\nDouyin (TikTok China) Hot:')
        print('='*50)
        for i, item in enumerate(data['data']['word_list'][:10], 1):
            word = item['word']
            print(f"{i:2}. {word}")
except Exception as e:
    print(f"Douyin error: {e}")
