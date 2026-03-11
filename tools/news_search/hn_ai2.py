import requests
import re

r = requests.get('https://r.jina.ai/https://news.ycombinator.com', timeout=25)
text = r.text

# The format is: number. [](url)[title](url) ... X points
# Better pattern: find all "X points" occurrences and get context before it

ai_keywords = ['AI', 'GPT', 'Claude', 'OpenAI', 'Anthropic', 'Google', 'model', 'LLM', 'DeepSeek', 'agent', 'machine', 'neural']

print('Hacker News Top Posts - AI Related:')
print('='*60)

# Find all point occurrences
for match in re.finditer(r'(\d+)\s+points', text):
    # Get 200 chars before the "X points"
    start = max(0, match.start() - 200)
    context = text[start:match.end()]
    
    # Extract title from the context
    title_match = re.search(r'\[([^\]]+)\]\(https?://[^\)]+\)', context)
    if title_match:
        title = title_match.group(1)
        points = match.group(1)
        
        # Check if AI related
        if any(k.lower() in title.lower() for k in ai_keywords):
            print(f"[AI] {points.rjust(4)} pts | {title[:55]}")
