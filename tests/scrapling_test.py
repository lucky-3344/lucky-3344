from scrapling import Fetcher

# 测试 Scrapling
fetcher = Fetcher()
response = fetcher.get('https://github.com/D4Vinci/Scrapling')

print('=' * 50)
print('Scrapling 测试成功!')
print('=' * 50)
print(f'标题: {response.title}')
print(f'描述: {response.meta.get("description", "N/A")}')
print(f'链接数: {len(response.links)}')
print('=' * 50)
