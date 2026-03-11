import requests

print('Testing Reddit with longer timeout...')
try:
    r = requests.get('https://www.reddit.com/r/all/hot.json?limit=25', timeout=60, headers={'User-Agent': 'Mozilla/5.0'})
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
    print(f'Error: {e}')
