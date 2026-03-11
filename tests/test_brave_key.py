import os
import sys
import requests

# Force UTF-8 encoding
sys.stdout.reconfigure(encoding='utf-8')

key = os.environ.get('BRAVE_API_KEY', '')
if not key:
    print("BRAVE_API_KEY not set")
    exit(1)

print(f"Testing Brave API key: {key[:10]}...")

headers = {
    'Accept': 'application/json',
    'X-Subscription-Token': key
}

try:
    r = requests.get('https://api.search.brave.com/res/v1/credits', headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        try:
            data = r.json()
            print(f"Account Type: {data.get('account_type', 'N/A')}")
            print(f"Searches Remaining: {data.get('searches_remaining', 'N/A')}")
        except:
            print(f"Response: {r.text[:200]}")
        print("Brave API key works!")
    else:
        print(f"Error: {r.status_code} - {r.text[:200]}")
except Exception as e:
    print(f"Request failed: {e}")
