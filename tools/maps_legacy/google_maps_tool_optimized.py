"""
优化版Google Maps工具 - 修复网络问题并优化用户体验
"""
import csv
from difflib import SequenceMatcher
import re
import sys
import time
from tkinter import filedialog, messagebox, ttk, scrolledtext
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
import threading
from queue import Queue
from datetime import datetime

class GoogleMapsToolsOptimized:
    def __init__(self):
        # 基本导入
        import tkinter as tk
        self.tk = tk
        self.root = tk.Tk()
        
        # 网络状态
        self.network_ok = False
        self.network_checked = False
        
        # 批量处理相关
        self.transformer = CoordTransform()
        self.batch_results = []
        self.api_delay = 1.0  # 更保守的延迟
        self.batch_use_input_coord_for_analysis = True
        
        # 线程安全队列
        self.log_queue = Queue()
        
        # 设置GUI
        self.setup_gui()
        
        # 启动网络检查（非阻塞）
        self.check_network_async()
        
    def setup_gui(self):
        """设置优化后的GUI界面"""
        self.root.title("Google Maps/Earth 坐标转换工具 (优化版)")
        self.root.geometry("800x600")
        
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(self.tk.W, self.tk.E, self.tk.N, self.tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        
        # 1. 状态栏
        status_frame = ttk.LabelFrame(main_frame, text="系统状态", padding="5")
        status_frame.grid(row=0, column=0, sticky=(self.tk.W, self.tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="正在初始化...", foreground="blue")
        self.status_label.pack(side=self.tk.LEFT)
        
        self.network_status = ttk.Label(status_frame, text="网络: 检测中...", foreground="orange")
        self.network_status.pack(side=self.tk.LEFT, padx=(20, 0))
        
        # 2. 搜索区域
        search_frame = ttk.LabelFrame(main_frame, text="地址搜索", padding="10")
        search_frame.grid(row=1, column=0, sticky=(self.tk.W, self.tk.E), pady=(0, 10))
        
        # 搜索输入
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=self.tk.X)
        
        ttk.Label(search_input_frame, text="地址:").pack(side=self.tk.LEFT)
        self.search_var = self.tk.StringVar()
        self.search_entry = ttk.Entry(search_input_frame, textvariable=self.search_var, width=50)
        self.search_entry.pack(side=self.tk.LEFT, padx=5)
        
        self.search_btn = ttk.Button(search_input_frame, text="搜索", command=self.search_location)
        self.search_btn.pack(side=self.tk.LEFT)
        
        # 字符计数
        self.char_count_label = ttk.Label(search_input_frame, text="0/84 字节")
        self.char_count_label.pack(side=self.tk.LEFT, padx=10)
        
        # 3. 坐标显示区域
        coord_frame = ttk.LabelFrame(main_frame, text="坐标信息", padding="10")
        coord_frame.grid(row=2, column=0, sticky=(self.tk.W, self.tk.E), pady=(0, 10))
        
        # 使用网格布局
        ttk.Label(coord_frame, text="WGS84 坐标:").grid(row=0, column=0, sticky=self.tk.W)
        self.wgs84_coords = self.tk.StringVar(value="未获取")
        ttk.Label(coord_frame, textvariable=self.wgs84_coords, foreground="blue").grid(row=0, column=1, sticky=self.tk.W, padx=10)
        
        ttk.Label(coord_frame, text="GCJ02 坐标:").grid(row=1, column=0, sticky=self.tk.W)
        self.gcj02_coords = self.tk.StringVar(value="未获取")
        ttk.Label(coord_frame, textvariable=self.gcj02_coords, foreground="green").grid(row=1, column=1, sticky=self.tk.W, padx=10)
        
        # 4. 地图操作按钮
        map_frame = ttk.Frame(main_frame)
        map_frame.grid(row=3, column=0, sticky=(self.tk.W, self.tk.E), pady=(0, 10))
        
        buttons = [
            ("🌐 Google地图", lambda: self.open_in_maps("google_web")),
            ("🛰️ Google Earth", lambda: self.open_in_maps("google_earth")),
            ("🗺️ 高德地图", lambda: self.open_in_maps("amap")),
            ("📋 复制KML", self.copy_kml)
        ]
        
        for text, command in buttons:
            btn = ttk.Button(map_frame, text=text, command=command)
            btn.pack(side=self.tk.LEFT, padx=2)
        
        # 5. 单点分析区域
        analysis_frame = ttk.LabelFrame(main_frame, text="单点分析", padding="10")
        analysis_frame.grid(row=4, column=0, sticky=(self.tk.W, self.tk.E), pady=(0, 10))
        
        # 坐标输入
        input_frame = ttk.Frame(analysis_frame)
        input_frame.pack(fill=self.tk.X, pady=(0, 10))
        
        ttk.Label(input_frame, text="经纬度 (格式: 经度,纬度):").pack(side=self.tk.LEFT)
        self.coord_var = self.tk.StringVar()
        coord_entry = ttk.Entry(input_frame, textvariable=self.coord_var, width=30)
        coord_entry.pack(side=self.tk.LEFT, padx=5)
        
        self.analyze_btn = ttk.Button(input_frame, text="分析", command=self.analyze_area)
        self.analyze_btn.pack(side=self.tk.LEFT)
        
        # 结果显示
        result_frame = ttk.Frame(analysis_frame)
        result_frame.pack(fill=self.tk.X)
        
        ttk.Label(result_frame, text="区域属性:").grid(row=0, column=0, sticky=self.tk.W)
        self.area_result_var = self.tk.StringVar(value="未分析")
        ttk.Label(result_frame, textvariable=self.area_result_var, foreground="blue", 
                 font=('Arial', 10, 'bold')).grid(row=0, column=1, sticky=self.tk.W, padx=10)
        
        ttk.Label(result_frame, text="地理特征:").grid(row=1, column=0, sticky=self.tk.W)
        self.features_result_var = self.tk.StringVar(value="未分析")
        ttk.Label(result_frame, textvariable=self.features_result_var, foreground="darkgreen").grid(row=1, column=1, sticky=self.tk.W, padx=10)
        
        # 6. 批量处理区域
        batch_frame = ttk.LabelFrame(main_frame, text="批量处理", padding="10")
        batch_frame.grid(row=5, column=0, sticky=(self.tk.W, self.tk.E), pady=(0, 10))
        
        # 批量处理按钮
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill=self.tk.X, pady=(0, 10))
        
        batch_buttons = [
            ("📁 导入CSV", self.import_csv),
            ("💾 导出结果", self.export_results),
            ("🗺️ 生成KML", self.create_batch_kml),
            ("🔧 网络诊断", self.show_network_diagnostics)
        ]
        
        for text, command in batch_buttons:
            btn = ttk.Button(batch_btn_frame, text=text, command=command)
            btn.pack(side=self.tk.LEFT, padx=2)
        
        # 日志区域
        log_frame = ttk.LabelFrame(batch_frame, text="处理日志", padding="5")
        log_frame.pack(fill=self.tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=self.tk.WORD)
        self.log_text.pack(fill=self.tk.BOTH, expand=True)
        
        # 7. 进度条
        self.progress_var = self.tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=6, column=0, sticky=(self.tk.W, self.tk.E), pady=(10, 0))
        
        # 绑定事件
        self.search_var.trace('w', self.on_search_change)
        
        # 启动日志更新
        self.update_log()
        
    def check_network_async(self):
        """异步检查网络连接"""
        def check():
            try:
                # 测试DNS解析
                socket.gethostbyname_ex('restapi.amap.com')
                
                # 测试API连接
                test_url = "https://restapi.amap.com/v3/geocode/regeo"
                test_params = {
                    "location": "116.3974,39.9093",
                    "key": self.get_amap_key(),
                    "extensions": "base",
                    "output": "json"
                }
                
                response = requests.get(test_url, params=test_params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data.get('status') == '1':
                        self.network_ok = True
                        self.root.after(0, lambda: self.network_status.config(
                            text="网络: 正常", foreground="green"))
                    else:
                        self.root.after(0, lambda: self.network_status.config(
                            text="网络: API错误", foreground="red"))
                else:
                    self.root.after(0, lambda: self.network_status.config(
                        text="网络: 连接失败", foreground="red"))
                        
            except Exception as e:
                self.root.after(0, lambda: self.network_status.config(
                    text="网络: 检测失败", foreground="red"))
                self.log_message(f"网络检测失败: {e}")
            
            self.network_checked = True
            self.root.after(0, lambda: self.status_label.config(text="就绪"))
        
        # 在新线程中检查网络
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
    
    def log_message(self, message):
        """添加日志消息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        self.log_queue.put(full_message)
    
    def update_log(self):
        """更新日志显示"""
        try:
            while not self.log_queue.empty():
                message = self.log_queue.get_nowait()
                self.log_text.insert(self.tk.END, message + "\n")
                self.log_text.see(self.tk.END)
        except:
            pass
        
        # 每100ms检查一次新消息
        self.root.after(100, self.update_log)
    
    def on_search_change(self, *args):
        """监控搜索文本变化"""
        text = self.search_var.get()
        byte_count = len(text.encode('utf-8'))
        self.char_count_label.config(text=f"{byte_count}/84 字节")
        
        if byte_count > 84:
            self.char_count_label.config(foreground='red')
        else:
            self.char_count_label.config(foreground='black')
    
    def search_location(self):
        """搜索地址获取坐标"""
        if not self.network_checked:
            messagebox.showwarning("警告", "正在检查网络，请稍后...")
            return
            
        if not self.network_ok:
            messagebox.showwarning("网络警告", 
                "网络连接可能有问题。\n请先使用'网络诊断'功能检查网络状态。")
            return
        
        address = self.search_var.get().strip()
        if not address:
            messagebox.showwarning("警告", "请输入搜索地址")
            return
        
        self.log_message(f"搜索地址: {address}")
        self.status_label.config(text="搜索中...")
        self.search_btn.config(state='disabled')
        
        # 在新线程中执行搜索
        def do_search():
            try:
                # 使用高德API搜索
                amap_key = self.get_amap_key()
                url = "https://restapi.amap.com/v3/geocode/geo"
                params = {
                    "address": address,
                    "key": amap_key,
                    "output": "json"
                }
                
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    if data['status'] == '1' and data['geocodes']:
                        location = data['geocodes'][0]['location']
                        gcj02_lng, gcj02_lat = map(float, location.split(','))
                        wgs84_lng, wgs84_lat = self.transformer.gcj02_to_wgs84(gcj02_lng, gcj02_lat)
                        
                        # 更新UI
                        self.root.after(0, lambda: self.wgs84_coords.set(f"{wgs84_lng:.6f}, {wgs84_lat:.6f}"))
                        self.root.after(0, lambda: self.gcj02_coords.set(f"{gcj02_lng:.6f}, {gcj02_lat:.6f}"))
                        
                        formatted_address = data['geocodes'][0].get('formatted_address', '')
                        self.root.after(0, lambda: self.log_message(f"找到地址: {formatted_address}"))
                        self.root.after(0, lambda: messagebox.showinfo("成功", f"找到地址:\n{formatted_address}"))
                    else:
                        self.root.after(0, lambda: messagebox.showerror("错误", "未找到该地址"))
                else:
                    self.root.after(0, lambda: messagebox.showerror("错误", f"API请求失败: {response.status_code}"))
                    
            except Exception as e:
                self.root.after(0, lambda: self.log_message(f"搜索失败: {e}"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"搜索失败: {str(e)}"))
            finally:
                self.root.after(0, lambda: self.status_label.config(text="就绪"))
                self.root.after(0, lambda: self.search_btn.config(state='normal'))
        
        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()
    
    def analyze_area(self):
        """分析坐标点的区域属性"""
        if not self.network_ok:
            messagebox.showwarning("网络警告", "网络连接可能有问题")
            return
        
        coord_str = self.coord_var.get().strip()
        if not coord_str:
            messagebox.showwarning("警告", "请输入经纬度信息")
            return
        
        try:
            # 解析坐标
            parts = coord_str.split(',')
            if len(parts) != 2:
                messagebox.showerror("错误", "坐标格式错误，请使用 经度,纬度 格式")
                return
            
            lng, lat = float(parts[0].strip()), float(parts[1].strip())
            
            self.log_message(f"分析坐标: {lng}, {lat}")
            self.status_label.config(text="分析中...")
            self.analyze_btn.config(state='disabled')
            
            # 在新线程中执行分析
            def do_analysis():
                try:
                    # 获取区域属性
                    area_info = self.get_area_properties(lng, lat)
                    self.root.after(0, lambda: self.area_result_var.set(area_info))
                    
                    # 获取地理特征
                    geo_features = self.get_geo_features(lng, lat)
                    features_str = self._format_features(geo_features)
                    self.root.after(0, lambda: self.features_result_var.set(features_str))
                    
                    self.root.after(0, lambda: self.log_message(f"分析完成: {area_info}"))
                    
                except Exception as e:
                    self.root.after(0, lambda: self.log_message(f"分析失败: {e}"))
                    self.root.after(0, lambda: messagebox.showerror("错误", f"分析失败: {str(e)}"))
                finally:
                    self.root.after(0, lambda: self.status_label.config(text="就绪"))
                    self.root.after(0, lambda: self.analyze_btn.config(state='normal'))
            
            thread = threading.Thread(target=do_analysis, daemon=True)
            thread.start()
            
        except ValueError:
            messagebox.showerror("错误", "坐标格式错误，请输入有效的数字")
        except Exception as e:
            messagebox.showerror("错误", f"分析失败: {str(e)}")
    
    def get_area_properties(self, lng, lat):
        """获取坐标的区域属性"""
        try:
            amap_key = self.get_amap_key()
            
            # 逆地理编码
            url = "https://restapi.amap.com/v3/geocode/regeo"
            params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "all",
                "output": "json"
            }
            
            response = requests.get(url, params=params,
