#!/usr/bin/env python3
"""测试网络访问"""

import requests

urls = [
    ("BBC", "https://www.bbc.com/zhongwen"),
    ("CNN", "https://edition.cnn.com/world"),
    ("GitHub", "https://github.com/trending"),
    ("Brave API", "https://api.search.brave.com/v1/search"),
]

for name, url in urls:
    try:
        resp = requests.get(url, timeout=10)
        print(f"[OK] {name}: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}")
