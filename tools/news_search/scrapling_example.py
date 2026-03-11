# Scrapling 使用示例

Scrapling 是一个强大的自适应 Web 爬虫框架。

## 基本用法

### 1. 简单爬取 - 自动提取页面主要内容
```python
from scrapling import Fetcher

fetcher = Fetcher()
response = fetcher.get('https://example.com')

# 获取页面标题
print(response.title)

# 获取所有段落文本
print(response.texts)

# 获取所有链接
print(response.links)
```

### 2. 自定义提取 - 使用 CSS 选择器
```python
from scrapling import Fetcher

fetcher = Fetcher()
response = fetcher.get('https://github.com/D4Vinci/Scrapling')

# 提取特定元素
stars = response.css('.social-count')[0].text
print(f"Stars: {stars}")

# 提取所有标题
headers = response.css('h1, h2, h3')
for h in headers:
    print(h.text)
```

### 3. 处理 JSON 响应
```python
from scrapling import Fetcher

fetcher = Fetcher()
response = fetcher.get('https://api.github.com/users/D4Vinci')

# 直接获取 JSON
print(response.json)
```

### 4. 处理动态内容 (JavaScript 渲染的页面)
```python
from scrapling import Fetcher

# 启用浏览器渲染 (需要安装 playwright)
fetcher = Fetcher().adjust_headers(user_agent='Mozilla/5.0...')
response = fetcher.get('https://example-spa.com', engine='playwright')
```

### 5. 爬取列表页面
```python
from scrapling import Fetcher

fetcher = Fetcher()
response = fetcher.get('https://github.com/trending')

# 提取所有趋势项目
repos = response.css('article.box-shadow-card')
for repo in repos:
    name = repo.css('h2 a')[0].text.strip()
    stars = repo.css('.d-inline-block')[0].text.strip()
    print(f"{name} - {stars}")
```

## 运行示例

```bash
cd C:\Users\lucky\projects\my_project

# 运行示例脚本
py -c "
from scrapling import Fetcher

# 简单测试
fetcher = Fetcher()
response = fetcher.get('https://github.com/D4Vinci/Scrapling')
print('标题:', response.title)
print('描述:', response.meta.get('description', 'N/A'))
"
```

## 更多资源

- GitHub: https://github.com/D4Vinci/Scrapling
- 文档: 查看源码中的 docstring
