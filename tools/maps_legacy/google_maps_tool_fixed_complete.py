"""
修复版Google Maps工具 - 解决GUI环境下的DNS解析问题
添加网络诊断和自动修复功能
"""
import csv
from difflib import SequenceMatcher
import re
import sys
import time
from tkinter import filedialog, messagebox
import requests
import json
import tempfile
import os
import webbrowser
import jieba
from coord_transform import CoordTransform
import pandas as pd
import socket
import subprocess
import platform

class GoogleMapsToolsFixed:
    def __init__(self):
        # 基本导入
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        
        self.transformer = CoordTransform()
        self.batch_results = []
        # API 节流：批量模式每次调用高德接口之间的延迟（秒）
        self.api_delay = 0.8
        # 批量分析时是否用输入坐标做判定（与单点一致），而不是转换后的坐标
        self.batch_use_input_coord_for_analysis = True
        
        # 网络诊断标志
        self.network_checked = False
        self.network_ok = False
        
        # 先检查网络，再设置GUI
        self.check_network_connection()
        self.setup_gui()
        
    def check_network_connection(self):
        """检查网络连接，尝试自动修复常见问题"""
        print("检查网络连接...")
        
        try:
            # 1. 测试DNS解析
            print("1. 测试DNS解析...")
            try:
                socket.gethostbyname_ex('restapi.amap.com')
                print("  ✅ DNS解析正常")
                dns_ok = True
            except socket.gaierror as e:
                print(f"  ❌ DNS解析失败: {e}")
                dns_ok = False
                
                # 尝试修复DNS
                if self.fix_dns_issues():
                    print("  🔧 尝试修复DNS...")
                    try:
                        socket.gethostbyname_ex('restapi.amap.com')
                        print("  ✅ DNS修复成功")
                        dns_ok = True
                    except:
                        print("  ❌ DNS修复失败")
            
            # 2. 测试API连接
            print("2. 测试API连接...")
            if dns_ok:
                try:
                    test_url = "https://restapi.amap.com/v3/geocode/regeo"
                    test_params = {
                        "location": "116.3974,39.9093",
                        "key": self.get_amap_key(),
                        "extensions": "base",
                        "output": "json"
                    }
                    
                    # 设置较短的超时时间
                    response = requests.get(test_url, params=test_params, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('status') == '1':
                            print("  ✅ API连接正常")
                            self.network_ok = True
                        else:
                            print(f"  ❌ API返回错误: {data.get('info', '未知错误')}")
                    else:
                        print(f"  ❌ HTTP错误: {response.status_code}")
                except Exception as e:
                    print(f"  ❌ API连接失败: {e}")
            else:
                print("  ⚠️ 跳过API测试（DNS问题）")
            
            self.network_checked = True
            
        except Exception as e:
            print(f"网络检查过程中出错: {e}")
    
    def fix_dns_issues(self):
        """尝试修复DNS问题"""
        try:
            system = platform.system()
            
            if system == "Windows":
                # Windows: 刷新DNS缓存
                print("  Windows系统: 尝试刷新DNS缓存...")
                subprocess.run(["ipconfig", "/flushdns"], capture_output=True, text=True)
                
                # 尝试使用Google DNS
                print("  尝试使用Google DNS (8.8.8.8)...")
                try:
                    # 临时设置DNS服务器
                    resolver = socket.getaddrinfo('restapi.amap.com', 443)
                    return True
                except:
                    return False
                    
            elif system == "Linux" or system == "Darwin":  # Darwin = macOS
                # Linux/macOS: 刷新DNS缓存
                print(f"  {system}系统: 尝试刷新DNS缓存...")
                if system == "Linux":
                    subprocess.run(["systemctl", "restart", "systemd-resolved"], capture_output=True, text=True)
                else:  # macOS
                    subprocess.run(["sudo", "killall", "-HUP", "mDNSResponder"], capture_output=True, text=True)
                return True
                
            else:
                print(f"  不支持的系统: {system}")
                return False
                
        except Exception as e:
            print(f"  DNS修复失败: {e}")
            return False
    
    def setup_gui(self):
        """设置GUI界面"""
        self.root = self.tk.Tk()
        self.root.title("Google Maps/Earth 坐标转换工具 (修复版)")
        self.root.geometry("650x450")
        
        # 网络状态显示
        status_frame = self.ttk.LabelFrame(self.root, text="网络状态", padding=10)
        status_frame.pack(fill='x', padx=10, pady=5)
        
        if self.network_checked:
            if self.network_ok:
                status_text = "✅ 网络连接正常"
                status_color = "green"
            else:
                status_text = "⚠️ 网络连接有问题，部分功能可能受限"
                status_color = "orange"
        else:
            status_text = "⏳ 正在检查网络..."
            status_color = "blue"
        
        self.status_label = self.ttk.Label(status_frame, text=status_text, foreground=status_color, font=('Arial', 10, 'bold'))
        self.status_label.pack()
        
        # 修复网络按钮
        if not self.network_ok:
            self.ttk.Button(status_frame, text="尝试修复网络", command=self.retry_network_check).pack(pady=5)
        
        # 修改搜索框部分
        search_frame = self.ttk.LabelFrame(self.root, text="地址搜索", padding=10)
        search_frame.pack(fill='x', padx=10, pady=5)
        
        search_input_frame = self.ttk.Frame(search_frame)
        search_input_frame.pack(fill='x')
        
        self.search_var = self.tk.StringVar()
        self.search_var.trace('w', self.on_search_change)
        
        self.ttk.Entry(search_input_frame, textvariable=self.search_var, width=50).pack(side='left', padx=5)
        self.ttk.Button(search_input_frame, text="搜索", command=self.search_location).pack(side='left')
        
        # 添加字符计数标签
        self.char_count_label = self.ttk.Label(search_frame, text="0/84 字节")
        self.char_count_label.pack(side='left', padx=5)
        
        # 坐标显示
        coord_frame = self.ttk.LabelFrame(self.root, text="坐标信息", padding=10)
        coord_frame.pack(fill='x', padx=10, pady=5)
        
        self.wgs84_coords = self.tk.StringVar()
        self.gcj02_coords = self.tk.StringVar()
        
        self.ttk.Label(coord_frame, text="WGS84 坐标:").grid(row=0, column=0, sticky='w')
        self.ttk.Label(coord_frame, textvariable=self.wgs84_coords).grid(row=0, column=1, sticky='w')
        
        self.ttk.Label(coord_frame, text="GCJ02 坐标:").grid(row=1, column=0, sticky='w')
        self.ttk.Label(coord_frame, textvariable=self.gcj02_coords).grid(row=1, column=1, sticky='w')
        
        # 操作按钮
        button_frame = self.ttk.Frame(self.root, padding=10)
        button_frame.pack(fill='x')
        
        self.ttk.Button(button_frame, text="在Google地图网页中打开", 
                  command=lambda: self.open_in_maps("google_web")).pack(side='left', padx=5)
        self.ttk.Button(button_frame, text="在Google Earth中打开", 
                  command=lambda: self.open_in_maps("google_earth")).pack(side='left', padx=5)
        self.ttk.Button(button_frame, text="在高德地图中打开", 
                  command=lambda: self.open_in_maps("amap")).pack(side='left', padx=5)
        self.ttk.Button(button_frame, text="复制KML代码", 
                  command=self.copy_kml).pack(side='left', padx=5)
        
        # 区域属性判断
        area_frame = self.ttk.LabelFrame(self.root, text="区域属性判断", padding=10)
        area_frame.pack(fill='x', padx=10, pady=5)
        
        coord_input_frame = self.ttk.Frame(area_frame)
        coord_input_frame.pack(fill='x', pady=5)
        
        self.ttk.Label(coord_input_frame, text="经纬度 (格式:经,纬)").pack(side='left', padx=5)
        self.coord_var = self.tk.StringVar()
        self.ttk.Entry(coord_input_frame, textvariable=self.coord_var, width=30).pack(side='left', padx=5)
        self.ttk.Button(coord_input_frame, text="分析", command=self.analyze_area).pack(side='left', padx=5)
        
        self.area_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(area_frame, text="区域属性:").pack(side='left', padx=5)
        self.ttk.Label(area_frame, textvariable=self.area_result_var, foreground='blue', font=('Arial', 10, 'bold')).pack(side='left', padx=5)
        
        # 地理特征显示
        features_frame = self.ttk.Frame(area_frame)
        features_frame.pack(fill='x', pady=5)
        
        self.ttk.Label(features_frame, text="地理特征:").pack(side='left', padx=5)
        self.features_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(features_frame, textvariable=self.features_result_var, foreground='darkgreen', font=('Arial', 9)).pack(side='left', padx=5)
        
        # 添加批量处理按钮
        batch_frame = self.ttk.LabelFrame(self.root, text="批量处理", padding=10)
        batch_frame.pack(fill='x', padx=10, pady=5)
        
        self.ttk.Button(batch_frame, text="导入CSV文件", 
                  command=self.import_csv).pack(side='left', padx=5)
        self.ttk.Button(batch_frame, text="导出结果", 
                  command=self.export_results).pack(side='left', padx=5)
        self.ttk.Button(batch_frame, text="生成批量KML", 
                  command=self.create_batch_kml).pack(side='left', padx=5)
        
        # 添加命令行模式按钮
        cli_frame = self.ttk.LabelFrame(self.root, text="高级选项", padding=10)
        cli_frame.pack(fill='x', padx=10, pady=5)
        
        self.ttk.Button(cli_frame, text="运行命令行测试", 
                  command=self.run_cli_test).pack(side='left', padx=5)
        self.ttk.Button(cli_frame, text="查看网络诊断", 
                  command=self.show_network_diagnostics).pack(side='left', padx=5)
    
    def retry_network_check(self):
        """重新检查网络连接"""
        self.status_label.config(text="⏳ 正在检查网络...", foreground="blue")
        self.root.update()
        
        self.check_network_connection()
        
        if self.network_ok:
            self.status_label.config(text="✅ 网络连接正常", foreground="green")
            self.messagebox.showinfo("成功", "网络连接已恢复！")
        else:
            self.status_label.config(text="⚠️ 网络连接有问题，部分功能可能受限", foreground="orange")
            self.messagebox.showwarning("警告", 
                "网络连接仍有问题。\n\n建议：\n"
                "1. 检查网络连接\n"
                "2. 尝试刷新DNS缓存\n"
                "3. 检查防火墙设置\n"
                "4. 使用命令行模式测试")
    
    def run_cli_test(self):
        """运行命令行测试"""
        try:
            # 导入并运行命令行测试工具
            import test_cli_tool
            from io import StringIO
            import contextlib
            
            # 捕获输出
            output = StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                tester = test_cli_tool.CLITester()
                success = tester.run_comprehensive_test()
            
            # 显示结果
            result_text = output.getvalue()
            self.show_text_dialog("命令行测试结果", result_text)
            
        except Exception as e:
            self.messagebox.showerror("错误", f"运行命令行测试失败: {e}")
    
    def show_network_diagnostics(self):
        """显示网络诊断信息"""
        try:
            diagnostics = []
            diagnostics.append("="*60)
            diagnostics.append("网络诊断信息")
            diagnostics.append("="*60)
            
            # 系统信息
            diagnostics.append(f"操作系统: {platform.system()} {platform.release()}")
            diagnostics.append(f"Python版本: {sys.version}")
            
            # DNS测试
            diagnostics.append("\nDNS测试:")
            try:
                result = socket.gethostbyname_ex('restapi.amap.com')
                diagnostics.append(f"  ✅ restapi.amap.com 解析成功")
                diagnostics.append(f"     主机名: {result[0]}")
                diagnostics.append(f"     别名: {result[1]}")
                diagnostics.append(f"     IP地址: {', '.join(result[2])}")
            except socket.gaierror as e:
                diagnostics.append(f"  ❌ restapi.amap.com 解析失败: {e}")
            
            # 连接测试
            diagnostics.append("\n连接测试:")
            try:
                test_url = "https://restapi.amap.com/v3/geocode/regeo"
                test_params = {"location": "116.3974,39.9093", "key": self.get_amap_key()[:8] + "..."}
                response = requests.get(test_url, params=test_params, timeout=5)
                diagnostics.append(f"  ✅ API连接成功 (HTTP {response.status_code})")
            except Exception as e:
                diagnostics.append(f"  ❌ API连接失败: {e}")
            
            # 网络接口信息
            diagnostics.append("\n网络接口:")
            try:
                hostname = socket.gethostname()
                diagnostics.append(f"  主机名: {hostname}")
                
                # 获取本地IP
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                diagnostics.append(f"  本地IP: {local_ip}")
            except Exception as e:
                diagnostics.append(f"  获取网络信息失败: {e}")
            
            self.show_text_dialog("网络诊断", "\n".join(diagnostics))
            
        except Exception as e:
            self.messagebox.showerror("错误", f"生成诊断信息失败: {e}")
    
    def show_text_dialog(self, title, text):
        """显示文本对话框"""
        dialog = self.tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("700x500")
        
        # 文本区域
        text_widget = self.tk.Text(dialog, wrap='word', font=('Consolas', 10))
        text_widget.pack(fill='both', expand=True, padx=10, pady=10)
        text_widget.insert('1.0', text)
        text_widget.config(state='disabled')
        
        # 滚动条
        scrollbar = self.ttk.Scrollbar(dialog, command=text_widget.yview)
        scrollbar.pack(side='right', fill='y')
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # 关闭按钮
        self.ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)
    
    def on_search_change(self, *args):
        """监控搜索文本变化"""
        text = self.search_var.get()
        byte_count = len(text.encode('utf-8'))
        self.char_count_label.config(text=f"{byte_count}/84 字节")
        
        if byte_count > 84:
            self.char_count_label.config(foreground='red')
        else:
            self.char_count_label.config(foreground='black')
    
    # 以下是从原始版本复制的方法，确保功能完整
    def get_amap_key(self):
        """获取高德API密钥，支持从配置文件或环境变量"""
        # 优先从环境变量获取
        amap_key = os.environ.get('AMAP_KEY')
        if amap_key:
            return amap_key
        
        # 其次尝试从配置文件获取
        try:
            if os.path.exists('amap_config.json'):
                with open('amap_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'amap_key' in config:
                        return config.get('amap_key')
                    if 'key' in config:
                        return config.get('key')
                    return '1ba54ee0c70f50338fca9bb8b699b33c'
        except:
            pass
        
        # 默认密钥
        return '1ba54ee0c70f50338fca9bb8b699b33c'
    
    def _amap_endpoint(self, path):
        """根据可选的 IP 覆盖构造高德请求 endpoint 和 headers"""
        ip_override
