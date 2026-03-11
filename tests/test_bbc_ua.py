#!/usr/bin/env python3
"""测试BBC访问 - 模拟浏览器"""

import requests

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

urls = [
    ("BBC英文", "https://www.bbc.com/news"),
    ("BBC中文", "https://www.bbc.com/zhongwen"),
]

for name, url in urls:
    try:
        resp = requests.get(url, timeout=15, headers=headers)
        print(f"[OK] {name}: {resp.status_code} - {len(resp.text)} bytes")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}")
