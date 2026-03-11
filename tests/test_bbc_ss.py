#!/usr/bin/env python3
"""测试BBC通过Shadowsocks SOCKS5代理"""

import requests

proxies = {
    "http": "socks5://127.0.0.1:1080",
    "https": "socks5://127.0.0.1:1080",
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

urls = [
    ("BBC英文", "https://www.bbc.com/news"),
    ("BBC中文", "https://www.bbc.com/zhongwen"),
]

print("Testing BBC via Shadowsocks (127.0.0.1:8388)...")
print("-" * 50)

for name, url in urls:
    try:
        resp = requests.get(url, timeout=20, headers=headers, proxies=proxies)
        print(f"[OK] {name}: {resp.status_code}")
    except Exception as e:
        print(f"[FAIL] {name}: {type(e).__name__}")

print("-" * 50)
print("Done!")
