"""
Simple Brave Search (Web Scraping)
"""
import os
import sys
import requests
from bs4 import BeautifulSoup

PROXY = {'http': 'socks5://127.0.0.1:1080', 'https': 'socks5://127.0.0.1:1080'}

def brave_search(query, num_results=10):
    """Search using Brave web search via proxy"""
    url = f"https://search.brave.com/search?q={requests.utils.quote(query)}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        r = requests.get(url, headers=headers, proxies=PROXY, timeout=30)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        for item in soup.select('.result')[:num_results]:
            title = item.select_one('.title')
            url_elem = item.select_one('.url')
            desc = item.select_one('.description')
            
            if title:
                results.append({
                    'title': title.get_text(strip=True),
                    'url': url_elem.get_text(strip=True) if url_elem else '',
                    'description': desc.get_text(strip=True) if desc else ''
                })
        
        return results
    except Exception as e:
        print(f"Error: {e}")
        return []

if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "OpenAI GPT-5"
    print(f"Searching: {query}")
    results = brave_search(query, 5)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['title']}")
        print(f"   URL: {r['url']}")
        print(f"   {r['description'][:100]}...")
