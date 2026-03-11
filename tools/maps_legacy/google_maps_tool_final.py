"""
最终版Google Maps工具 - 修复所有问题并优化
"""
import csv
import re
import sys
import time
import json
import os
import tempfile
import webbrowser
import socket
import platform
import threading
from tkinter import filedialog, messagebox, ttk, scrolledtext
from datetime import datetime
from queue import Queue
import requests
import pandas as pd
from coord_transform import CoordTransform

class GoogleMapsToolsFinal:
    def __init__(self):
        import tkinter as tk
        self.tk = tk
        self.root = tk.Tk()
        
        # 初始化
        self.transformer = CoordTransform()
        self.batch_results = []
        self.api_delay = 1.0
        self.network_ok = False
        self.log_queue = Queue()
        
        # 设置GUI
        self.setup_gui()
        
        # 异步检查网络
        threading.Thread(target=self.check_network, daemon=True).start()
        
    def setup_gui(self):
        """设置GUI界面"""
        self.root.title("Google Maps工具 - 最终版")
        self.root.geometry("750x700")
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 1. 状态栏
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding=5)
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="初始化中...", foreground="blue")
        self.status_label.pack(side=tk.LEFT)
        
        self.network_label = ttk.Label(status_frame, text="网络: 检测中...", foreground="orange")
        self.network_label.pack(side=tk.LEFT, padx=20)
        
        # 2. 搜索区域
        search_frame = ttk.LabelFrame(main_frame, text="地址搜索", padding=10)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(search_frame, text="地址:").pack(side=tk.LEFT)
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        
        self.search_btn = ttk.Button(search_frame, text="搜索", command=self.search_location)
        self.search_btn.pack(side=tk.LEFT)
        
        # 3. 坐标显示
        coord_frame = ttk.LabelFrame(main_frame, text="坐标", padding=10)
        coord_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(coord_frame, text="WGS84:").grid(row=0, column=0, sticky=tk.W)
        self.wgs84_var = tk.StringVar(value="等待输入")
        ttk.Label(coord_frame, textvariable=self.wgs84_var, foreground="blue").grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(coord_frame, text="GCJ02:").grid(row=1, column=0, sticky=tk.W)
        self.gcj02_var = tk.StringVar(value="等待输入")
        ttk.Label(coord_frame, textvariable=self.gcj02_var, foreground="green").grid(row=1, column=1, sticky=tk.W, padx=10)
        
        # 4. 地图按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        buttons = [
            ("Google地图", self.open_google_web),
            ("Google Earth", self.open_google_earth),
            ("高德地图", self.open_amap),
            ("复制KML", self.copy_kml)
        ]
        
        for text, cmd in buttons:
            ttk.Button(btn_frame, text=text, command=cmd).pack(side=tk.LEFT, padx=2)
        
        # 5. 单点分析
        analysis_frame = ttk.LabelFrame(main_frame, text="单点分析", padding=10)
        analysis_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 输入
        input_frame = ttk.Frame(analysis_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(input_frame, text="坐标 (经,纬):").pack(side=tk.LEFT)
        self.coord_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.coord_var, width=25).pack(side=tk.LEFT, padx=5)
        ttk.Button(input_frame, text="分析", command=self.analyze_area).pack(side=tk.LEFT)
        
        # 结果
        result_frame = ttk.Frame(analysis_frame)
        result_frame.pack(fill=tk.X)
        
        ttk.Label(result_frame, text="区域:").grid(row=0, column=0, sticky=tk.W)
        self.area_var = tk.StringVar(value="未分析")
        ttk.Label(result_frame, textvariable=self.area_var, foreground="blue").grid(row=0, column=1, sticky=tk.W, padx=10)
        
        ttk.Label(result_frame, text="特征:").grid(row=1, column=0, sticky=tk.W)
        self.feature_var = tk.StringVar(value="未分析")
        ttk.Label(result_frame, textvariable=self.feature_var, foreground="darkgreen").grid(row=1, column=1, sticky=tk.W, padx=10)
        
        # 6. 批量处理
        batch_frame = ttk.LabelFrame(main_frame, text="批量处理", padding=10)
        batch_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 按钮
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        batch_buttons = [
            ("导入CSV", self.import_csv),
            ("导出结果", self.export_results),
            ("生成KML", self.create_batch_kml),
            ("网络诊断", self.show_diagnostics)
        ]
        
        for text, cmd in batch_buttons:
            ttk.Button(batch_btn_frame, text=text, command=cmd).pack(side=tk.LEFT, padx=2)
        
        # 日志
        log_frame = ttk.LabelFrame(batch_frame, text="日志", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(5, 0))
        
        # 启动日志更新
        self.update_log()
        
    def check_network(self):
        """检查网络"""
        try:
            # DNS测试
            socket.gethostbyname('restapi.amap.com')
            
            # API测试
            key = self.get_amap_key()
            url = "https://restapi.amap.com/v3/geocode/regeo"
            params = {"location": "116.3974,39.9093", "key": key, "extensions": "base"}
            
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200 and resp.json().get('status') == '1':
                self.network_ok = True
                self.root.after(0, lambda: self.network_label.config(text="网络: 正常", foreground="green"))
                self.log("网络检查: 正常")
            else:
                self.root.after(0, lambda: self.network_label.config(text="网络: API错误", foreground="red"))
                self.log("网络检查: API错误")
        except Exception as e:
            self.root.after(0, lambda: self.network_label.config(text="网络: 失败", foreground="red"))
            self.log(f"网络检查失败: {e}")
        
        self.root.after(0, lambda: self.status_label.config(text="就绪"))
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}")
    
    def update_log(self):
        """更新日志显示"""
        try:
            while not self.log_queue.empty():
                msg = self.log_queue.get_nowait()
                self.log_text.insert(tk.END, msg + "\n")
                self.log_text.see(tk.END)
        except:
            pass
        self.root.after(100, self.update_log)
    
    def get_amap_key(self):
        """获取API密钥"""
        key = os.environ.get('AMAP_KEY')
        if key:
            return key
        
        try:
            if os.path.exists('amap_config.json'):
                with open('amap_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('amap_key', config.get('key', '1ba54ee0c70f50338fca9bb8b699b33c'))
        except:
            pass
        
        return '1ba54ee0c70f50338fca9bb8b699b33c'
    
    def search_location(self):
        """搜索地址"""
        if not self.network_ok:
            messagebox.showwarning("警告", "网络连接有问题，请检查网络")
            return
        
        address = self.search_var.get().strip()
        if not address:
            messagebox.showwarning("警告", "请输入地址")
            return
        
        self.log(f"搜索: {address}")
        self.search_btn.config(state='disabled')
        self.status_label.config(text="搜索中...")
        self.progress.start()
        
        def do_search():
            try:
                key = self.get_amap_key()
                url = "https://restapi.amap.com/v3/geocode/geo"
                params = {"address": address, "key": key}
                
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    if data['status'] == '1' and data['geocodes']:
                        loc = data['geocodes'][0]['location']
                        gcj_lng, gcj_lat = map(float, loc.split(','))
                        wgs_lng, wgs_lat = self.transformer.gcj02_to_wgs84(gcj_lng, gcj_lat)
                        
                        self.root.after(0, lambda: self.wgs84_var.set(f"{wgs_lng:.6f}, {wgs_lat:.6f}"))
                        self.root.after(0, lambda: self.gcj02_var.set(f"{gcj_lng:.6f}, {gcj_lat:.6f}"))
                        
                        addr = data['geocodes'][0].get('formatted_address', '')
                        self.root.after(0, lambda: self.log(f"找到: {addr}"))
                        self.root.after(0, lambda: messagebox.showinfo("成功", f"找到地址:\n{addr}"))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "未找到地址"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"请求失败: {resp.status_code}"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"搜索错误: {e}"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"搜索失败: {e}"))
            finally:
                self.root.after(0, lambda: self.search_btn.config(state='normal'))
                self.root.after(0, lambda: self.status_label.config(text="就绪"))
                self.root.after(0, lambda: self.progress.stop())
        
        threading.Thread(target=do_search, daemon=True).start()
    
    def analyze_area(self):
        """分析区域"""
        if not self.network_ok:
            messagebox.showwarning("警告", "网络连接有问题")
            return
        
        coord = self.coord_var.get().strip()
        if not coord:
            messagebox.showwarning("警告", "请输入坐标")
            return
        
        try:
            parts = coord.split(',')
            if len(parts) != 2:
                messagebox.showerror("错误", "格式: 经度,纬度")
                return
            
            lng, lat = float(parts[0]), float(parts[1])
            self.log(f"分析坐标: {lng}, {lat}")
            self.status_label.config(text="分析中...")
            self.progress.start()
            
            def do_analysis():
                try:
                    # 获取区域信息
                    area = self.get_area_info(lng, lat)
                    self.root.after(0, lambda: self.area_var.set(area))
                    
                    # 获取特征
                    features = self.get_features(lng, lat)
                    self.root.after(0, lambda: self.feature_var.set(features))
                    
                    self.root.after(0, lambda: self.log(f"分析完成: {area}"))
                except Exception as e:
                    self.root.after(0, lambda: self.log(f"分析错误: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"分析失败: {e}"))
                finally:
                    self.root.after(0, lambda: self.status_label.config(text="就绪"))
                    self.root.after(0, lambda: self.progress.stop())
            
            threading.Thread(target=do_analysis, daemon=True).start()
            
        except ValueError:
            messagebox.showerror("错误", "坐标必须是数字")
        except Exception as e:
            messagebox.showerror("错误", f"分析失败: {e}")
    
    def get_area_info(self, lng, lat):
        """获取区域信息"""
        try:
            key = self.get_amap_key()
            url = "https://restapi.amap.com/v3/geocode/regeo"
            params = {
                "location": f"{lng},{lat}",
                "key": key,
                "extensions": "all"
            }
            
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data['status'] == '1':
                    addr = data['regeocode']
                    province = addr.get('addressComponent', {}).get('province', '')
                    city = addr.get('addressComponent', {}).get('city', '')
                    district = addr.get('addressComponent', {}).get('district', '')
                    
                    # 简单分类
                    time.sleep(0.35)  # API频率控制
                    
                    # 获取POI密度
                    poi_count = self.get_poi_count(lng, lat, key)
                    
                    if poi_count >= 30:
                        area_type = "密集市区"
                    elif poi_count >= 15:
                        area_type = "市区"
                    elif poi_count >= 8:
                        area_type = "县城"
                    elif poi_count >= 3:
                        area_type = "乡镇"
                    else:
                        area_type = "农村"
                    
                    return f"{area_type} (POI:{poi_count}) - {province}{city}{district}"
            return "查询失败"
        except Exception as e:
            return f"错误: {e}"
    
    def get_poi_count(self, lng, lat, key):
        """获取POI数量"""
        try:
            url = "https://restapi.amap.com/v3/place/around"
            params = {
                "location": f"{lng},{lat}",
                "key": key,
                "radius": 1000,
                "offset": 50
            }
            
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data['status'] == '1':
                    return len(data.get('pois', []))
            return 0
        except:
            return 0
    
    def get_features(self, lng, lat):
        """获取地理特征"""
        try:
            key = self.get_amap_key()
            url = "https://restapi.amap.com/v3/geocode/regeo"
            params = {
                "location": f"{lng},{lat}",
                "key": key,
                "extensions": "all"
            }
            
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                if data['status'] == '1':
                    addr = data['regeocode'].get('formatted_address', '')
                    
                    features = []
                    if any(k in addr for k in ['路', '街', '道']):
                        features.append('路边')
                    if any(k in addr for k in ['公园', '广场', '绿地']):
                        features.append('绿地')
                    if any(k in addr for k in ['河', '湖', '海', '江']):
                        features.append('水体')
                    
                    return ' | '.join(features) if features else '无特殊特征'
            return "查询失败"
        except Exception as e:
            return f"错误: {e}"
    
    def open_google_web(self):
        """打开Google地图网页版"""
        if self.wgs84_var.get() != "等待输入":
            try:
                coords = self.wgs84_var.get().split(',')
                lat, lng = coords[1].strip(), coords[0].strip()
                webbrowser.open(f"https://www.google.com/maps?q={lat},{lng}")
            except:
                messagebox.showwarning("警告", "请先搜索位置")
    
    def open_google_earth(self):
        """打开Google Earth"""
        if self
