#!/usr/bin/env python3
"""测试BBC访问"""

import requests

urls = [
    ("BBC中文", "https://www.bbc.com/zhongwen"),
    ("BBC英文", "https://www.bbc.com/news"),
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence"),
]

for name, url in urls:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        print(f"[OK] {name}: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}")
