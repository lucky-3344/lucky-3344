import speedtest
import subprocess
import socket
import platform
import time
from datetime import datetime
import pandas as pd
from pathlib import Path

class NetworkSpeedTest:
    def __init__(self):
        self.results = []
        self.local_ip = self.get_local_ip()
        self.network_info = {}
        
    def get_local_ip(self):
        """获取本机IP地址"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
        
    def get_network_adapter_info(self):
        """获取网络适配器信息"""
        try:
            result = subprocess.run(
                'wmic nic where "NetEnabled=true" get Name,Speed /value', 
                capture_output=True, 
                text=True
            )
            info = {}
            for line in result.stdout.split('\n'):
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    if value:
                        info[key] = value
            return info
        except Exception as e:
            return {"错误": str(e)}

    def scan_local_network(self):
        """扫描局域网设备"""
        base_ip = '.'.join(self.local_ip.split('.')[:-1])
        active_hosts = []
        
        print(f"\n正在扫描局域网 ({base_ip}.0/24)...")
        for i in range(1, 255):
            ip = f"{base_ip}.{i}"
            try:
                # 使用更快的连接超时
                result = subprocess.run(
                    ['ping', '-n', '1', '-w', '100', ip],
                    capture_output=True,
                    text=True
                )
                if "TTL=" in result.stdout:
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        hostname = "未知设备"
                    active_hosts.append({
                        'IP': ip,
                        '设备名': hostname,
                        '延迟': result.stdout.split('时间=')[-1].split('ms')[0] + 'ms' if '时间=' in result.stdout else 'N/A'
                    })
                    print(f"发现设备: {ip} ({hostname})")
            except:
                continue
        
        return active_hosts

    def test_local_speed(self, target_ip):
        """测试局域网速度"""
        try:
            # 使用iperf3测试局域网速度
            result = subprocess.run(
                ['iperf3', '-c', target_ip],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return True, result.stdout
            return False, "iperf3测试失败"
        except:
            # 如果没有iperf3，使用简单的ping测试
            result = subprocess.run(
                ['ping', '-n', '10', target_ip],
                capture_output=True,
                text=True
            )
            return True, result.stdout

    def test_internet_speed(self):
        """测试互联网速度"""
        print("\n测试互联网速度中...")
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            
            print("测试下载速度...")
            download_speed = st.download() / 1_000_000  # Mbps
            
            print("测试上传速度...")
            upload_speed = st.upload() / 1_000_000  # Mbps
            
            return True, {
                '下载速度': f"{round(download_speed, 2)} Mbps",
                '上传速度': f"{round(upload_speed, 2)} Mbps"
            }
        except Exception as e:
            return False, f"速度测试失败: {str(e)}"

    def run_full_test(self):
        """运行完整测试"""
        print(f"=== 网络诊断报告 ===")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"本机IP: {self.local_ip}")
        
        # 获取网络适配器信息
        print("\n[网络适配器信息]")
        adapter_info = self.get_network_adapter_info()
        for key, value in adapter_info.items():
            print(f"{key}: {value}")
            
        # 扫描局域网
        active_hosts = self.scan_local_network()
        
        # 测试互联网速度
        print("\n[互联网速度测试]")
        status, speed_info = self.test_internet_speed()
        if status:
            for key, value in speed_info.items():
                print(f"{key}: {value}")
        
        # 保存报告
        report_path = Path.home() / 'Desktop' / '网络诊断报告.xlsx'
        with pd.ExcelWriter(report_path) as writer:
            # 活动设备表
            df_hosts = pd.DataFrame(active_hosts)
            df_hosts.to_excel(writer, sheet_name='局域网设备', index=False)
            
            # 速度测试结果
            if status:
                df_speed = pd.DataFrame([speed_info])
                df_speed.to_excel(writer, sheet_name='速度测试', index=False)
        
        print(f"\n报告已保存到: {report_path}")

if __name__ == "__main__":
    try:
        tester = NetworkSpeedTest()
        tester.run_full_test()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"测试失败: {str(e)}")
    finally:
        input("\n按回车键退出...")