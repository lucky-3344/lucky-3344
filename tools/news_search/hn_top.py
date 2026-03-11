import requests
import re

# Get Hacker News
r = requests.get('https://r.jina.ai/https://news.ycombinator.com', timeout=20)
text = r.text

# Find all story links (pattern: number. [title](url))
pattern = r'\d+\.\s*\[([^\]]+)\]\(([^)]+)\)'
matches = re.findall(pattern, text)

print("Hacker News Top Stories:")
print("="*60)
for i, (title, url) in enumerate(matches[:15], 1):
    print(f"{i:2}. {title[:55]}")
    print(f"    {url}")
