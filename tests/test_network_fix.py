"""
测试网络修复功能
验证代理支持和备用端点
"""
import socket
import requests
import os

def test_dns():
    """测试DNS解析"""
    print("=" * 60)
    print("测试DNS解析")
    print("=" * 60)
    
    hosts = ['restapi.amap.com', '223.6.6.6', '8.8.8.8']
    
    for host in hosts:
        try:
            ip = socket.gethostbyname(host)
            print(f"✅ {host} -> {ip}")
        except socket.gaierror as e:
            print(f"❌ {host}: {e}")

def test_api_endpoints():
    """测试API端点"""
    print("\n" + "=" * 60)
    print("测试API端点")
    print("=" * 60)
    
    key = '1ba54ee0c70f50338fca9bb8b699b33c'  # 默认密钥
    endpoints = [
        "https://restapi.amap.com/v3/geocode/regeo",
        "http://restapi.amap.com/v3/geocode/regeo"
    ]
    
    params = {"location": "116.3974,39.9093", "key": key, "extensions": "base"}
    
    for url in endpoints:
        try:
            print(f"\n测试: {url}")
            
            # 检查代理设置
            proxies = {}
            if os.environ.get('HTTP_PROXY'):
                proxies['http'] = os.environ.get('HTTP_PROXY')
                print(f"  使用HTTP代理: {proxies['http']}")
            if os.environ.get('HTTPS_PROXY'):
                proxies['https'] = os.environ.get('HTTPS_PROXY')
                print(f"  使用HTTPS代理: {proxies['https']}")
            
            resp = requests.get(url, params=params, timeout=10, 
                              proxies=proxies if proxies else None)
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == '1':
                    print(f"  ✅ 成功 (HTTP {resp.status_code})")
                    print(f"    地址: {data.get('regeocode', {}).get('formatted_address', 'N/A')}")
                else:
                    print(f"  ❌ API错误: {data.get('info', '未知错误')}")
            else:
                print(f"  ❌ HTTP错误: {resp.status_code}")
                
        except requests.exceptions.Timeout:
            print(f"  ❌ 超时")
        except requests.exceptions.ConnectionError as e:
            print(f"  ❌ 连接错误: {e}")
        except Exception as e:
            print(f"  ❌ 异常: {e}")

def test_proxy_settings():
    """测试代理设置"""
    print("\n" + "=" * 60)
    print("测试代理设置")
    print("=" * 60)
    
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    
    for var in proxy_vars:
        value = os.environ.get(var)
        if value:
            print(f"✅ {var} = {value}")
        else:
            print(f"❌ {var} = 未设置")

def main():
    print("网络连接问题诊断")
    print("=" * 60)
    
    test_dns()
    test_api_endpoints()
    test_proxy_settings()
    
    print("\n" + "=" * 60)
    print("解决方案:")
    print("=" * 60)
    print("1. 如果DNS解析失败:")
    print("   - 检查网络连接")
    print("   - 尝试使用代理")
    print("   - 修改hosts文件")
    
    print("\n2. 如果API连接失败:")
    print("   - 检查API密钥")
    print("   - 尝试HTTP备用端点")
    print("   - 设置代理环境变量")
    
    print("\n3. 设置代理的方法:")
    print("   Windows:")
    print("     set HTTP_PROXY=http://proxy.example.com:8080")
    print("     set HTTPS_PROXY=http://proxy.example.com:8080")
    print("   Linux/Mac:")
    print("     export HTTP_PROXY=http://proxy.example.com:8080")
    print("     export HTTPS_PROXY=http://proxy.example.com:8080")
    
    print("\n4. 在程序中:")
    print("   - 使用'网络诊断'功能")
    print("   - 查看详细错误信息")
    print("   - 尝试多个API端点")

if __name__ == "__main__":
    main()
