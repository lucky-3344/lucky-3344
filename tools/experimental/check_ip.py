#!/usr/bin/env python3
"""获取IP地址和位置"""

import requests
import json

try:
    # 获取公网IP
    resp = requests.get("https://api.ipify.org?format=json", timeout=10)
    data = resp.json()
    ip = data.get("ip", "Unknown")
    print(f"IP Address: {ip}")

    # 获取IP位置
    resp2 = requests.get(f"https://ipinfo.io/{ip}/json", timeout=10)
    data2 = resp2.json()

    print(f"Country: {data2.get('country', 'Unknown')}")
    print(f"Region: {data2.get('region', 'Unknown')}")
    print(f"City: {data2.get('city', 'Unknown')}")
    print(f"ISP: {data2.get('org', 'Unknown')}")

except Exception as e:
    print(f"Error: {e}")
