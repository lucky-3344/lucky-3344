import requests
import re

r = requests.get('https://r.jina.ai/https://news.ycombinator.com', timeout=25)
text = r.text

# Pattern: number. [title](url) ... X points
pattern = r'(\d+)\.\s*\[([^\]]+)\]\(([^)]+)\).*?(\d+)\s*points'

matches = re.findall(pattern, text)

print('Hacker News Top 20:')
print('='*60)

ai_keywords = ['AI', 'GPT', 'Claude', 'OpenAI', 'Anthropic', 'Google', 'model', 'LLM', 'DeepSeek', 'agent']

for num, title, url, points in matches[:20]:
    is_ai = any(k.lower() in title.lower() for k in ai_keywords)
    prefix = '[AI]' if is_ai else '   '
    print(prefix + ' ' + str(int(points)).rjust(4) + ' pts | ' + title[:50])
