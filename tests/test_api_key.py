import os
import requests

key = os.environ.get('OPENAI_API_KEY', '')
if not key:
    print("Key not set in environment")
    exit(1)

print(f"Testing API key: {key[:10]}...")
headers = {'Authorization': f'Bearer {key}'}

try:
    r = requests.get('https://api.openai.com/v1/models', headers=headers, timeout=10)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        print("API key works!")
    else:
        print(f"API Error: {r.text[:200]}")
except Exception as e:
    print(f"Request failed: {e}")
