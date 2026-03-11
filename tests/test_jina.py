import requests

def jina_read(url):
    """Use Jina Reader to fetch any webpage"""
    try:
        r = requests.get(f'https://r.jina.ai/{url}', timeout=30)
        if r.status_code == 200:
            return r.text
        return None
    except Exception as e:
        return str(e)

# Test various sources
tests = [
    'http://news.ycombinator.com',
    'https://techcrunch.com',
    'https://www.theverge.com',
    'https://36kr.com/p/48221'
]

print("="*60)
print("Jina Reader Test - Fetching Web Pages")
print("="*60)

for url in tests:
    print(f"\n{url}")
    print("-"*40)
    content = jina_read(url)
    if content and not content.startswith('Error'):
        # Extract title and first few paragraphs
        lines = content.split('\n')
        title = lines[0] if lines else "No title"
        print(f"Title: {title[:60]}")
        # Show first few content lines
        content_lines = [l for l in lines[1:10] if l.strip() and not l.startswith('==')]
        for l in content_lines[:3]:
            print(f"  {l[:70]}")
    else:
        print(f"Error: {content[:60] if content else 'No content'}")
