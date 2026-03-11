"""
Brave Search API Wrapper
"""
import os
import requests

BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY', '')
if not BRAVE_API_KEY:
    print("Error: BRAVE_API_KEY not set")
    exit(1)

BASE_URL = "https://api.search.brave.com/res/v1"

def search(query, count=10):
    """Search using Brave Search API"""
    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": BRAVE_API_KEY
    }
    params = {
        "q": query,
        "count": min(count, 20)
    }
    
    response = requests.get(f"{BASE_URL}/search", headers=headers, params=params, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Content: {response.text[:500]}")
    return response

if __name__ == "__main__":
    import sys
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "test query"
    print(f"Searching: {query}")
    search(query, 5)
