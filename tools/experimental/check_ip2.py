#!/usr/bin/env python3
"""获取IP地址和位置 - 通过代理"""

import requests

proxies = {
    "http": "socks5://127.0.0.1:8388",
    "https": "socks5://127.0.0.1:8388",
}

try:
    # 获取公网IP
    resp = requests.get("https://api.ipify.org?format=json", timeout=15, proxies=proxies)
    data = resp.json()
    ip = data.get("ip", "Unknown")
    print(f"IP Address: {ip}")

    # 获取IP位置
    resp2 = requests.get(f"https://ipinfo.io/{ip}/json", timeout=15, proxies=proxies)
    data2 = resp2.json()

    print(f"Country: {data2.get('country', 'Unknown')}")
    print(f"Region: {data2.get('region', 'Unknown')}")
    print(f"City: {data2.get('city', 'Unknown')}")
    print(f"ISP: {data2.get('org', 'Unknown')}")

except Exception as e:
    print(f"Error via proxy: {e}")

    print("\n--- Without proxy ---")
    try:
        resp = requests.get("https://api.ipify.org?format=json", timeout=15)
        print(f"IP: {resp.json().get('ip', 'Unknown')}")
    except Exception as e2:
        print(f"Error without proxy: {e2}")
