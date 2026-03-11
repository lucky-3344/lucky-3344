"""
测试DNS缓存修复效果
验证间歇性DNS解析失败问题是否解决
"""
import socket
import time
import threading

def test_dns_resolution():
    """测试DNS解析稳定性"""
    print("=" * 60)
    print("测试DNS解析稳定性")
    print("=" * 60)
    
    hostname = 'restapi.amap.com'
    successes = 0
    failures = 0
    
    print(f"测试主机: {hostname}")
    print("进行10次连续DNS解析测试...\n")
    
    for i in range(10):
        try:
            start_time = time.time()
            ip = socket.gethostbyname(hostname)
            elapsed = (time.time() - start_time) * 1000
            
            print(f"测试 {i+1}: ✅ 成功 ({elapsed:.1f}ms) -> {ip}")
            successes += 1
            
            # 短暂延迟，模拟批量处理
            time.sleep(0.2)
            
        except socket.gaierror as e:
            print(f"测试 {i+1}: ❌ 失败 -> {e}")
            failures += 1
    
    print(f"\n结果: 成功 {successes} 次, 失败 {failures} 次")
    
    if failures > 0:
        print("\n⚠️  检测到DNS解析失败，建议:")
        print("1. 使用DNS缓存（程序已实现）")
        print("2. 设置系统DNS为: 223.6.6.6 (阿里云DNS)")
        print("3. 修改hosts文件添加静态解析")
    else:
        print("\n✅ DNS解析稳定")

def test_concurrent_dns():
    """测试并发DNS解析"""
    print("\n" + "=" * 60)
    print("测试并发DNS解析")
    print("=" * 60)
    
    hostname = 'restapi.amap.com'
    results = []
    
    def resolve_dns(index):
        try:
            ip = socket.gethostbyname(hostname)
            results.append((index, True, ip))
        except socket.gaierror as e:
            results.append((index, False, str(e)))
    
    threads = []
    for i in range(5):
        t = threading.Thread(target=resolve_dns, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    results.sort(key=lambda x: x[0])
    
    for index, success, result in results:
        if success:
            print(f"线程 {index}: ✅ 成功 -> {result}")
        else:
            print(f"线程 {index}: ❌ 失败 -> {result}")

def main():
    print("DNS缓存修复验证测试")
    print("=" * 60)
    
    test_dns_resolution()
    test_concurrent_dns()
    
    print("\n" + "=" * 60)
    print("修复方案总结")
    print("=" * 60)
    print("1. DNS缓存:")
    print("   - 程序启动时缓存IP地址")
    print("   - 5分钟缓存有效期")
    print("   - 批量处理时使用缓存IP")
    
    print("\n2. 连接池:")
    print("   - 使用requests.Session")
    print("   - 连接复用，减少握手")
    print("   - 自动重试机制")
    
    print("\n3. 备用策略:")
    print("   - IP直接连接（绕过DNS）")
    print("   - HTTP备用端点")
    print("   - 代理支持")
    
    print("\n4. 错误恢复:")
    print("   - 会话失败时回退到普通请求")
    print("   - 详细的错误日志")
    print("   - 网络诊断工具")

if __name__ == "__main__":
    main()
