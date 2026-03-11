import requests

# Try Weibo hot search
try:
    r = requests.get('https://weibo.com/ajax/side/hotSearch', timeout=10)
    data = r.json()
    print('Weibo Hot Search:')
    print('='*50)
    for i, item in enumerate(data['data']['realtime'][:15], 1):
        word = item['word']
        num = item['num']
        print(f"{i:2}. {num:>8}  {word}")
except Exception as e:
    print(f"Weibo error: {e}")

# Try Zhihu hot
try:
    r = requests.get('https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total', timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
    data = r.json()
    print('\nZhihu Hot:')
    print('='*50)
    for i, item in enumerate(data['data'][:10], 1):
        title = item['target']['title'][:50]
        print(f"{i:2}. {title}")
except Exception as e:
    print(f"Zhihu error: {e}")
