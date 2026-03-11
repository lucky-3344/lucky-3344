import requests

r = requests.get('https://www.reddit.com/r/popular/hot.json?limit=25', timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
data = r.json()

print('Reddit Popular Posts (Hot):')
print('='*50)
for i, post in enumerate(data['data']['children'][:15], 1):
    title = post['data']['title'][:65]
    score = post['data']['score']
    comments = post['data']['num_comments']
    print(f"{i:2}. [{score:>5}  {comments:>4}] {title}")
