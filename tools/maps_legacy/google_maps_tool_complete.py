"""
Google Maps工具 - 增强网络版
修复间歇性DNS解析失败问题，添加DNS缓存和连接池
"""
import csv
import json
import os
import sys
import time
import tempfile
import webbrowser
import socket
import threading
from datetime import datetime
from queue import Queue
from tkinter import filedialog, messagebox, ttk, scrolledtext, StringVar, Tk
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pandas as pd
from coord_transform import CoordTransform

class GoogleMapsToolsComplete:
    def __init__(self):
        self.root = Tk()
        self.root.title("Google Maps工具 v3.0 - 增强网络版")
        self.root.geometry("750x700")
        
        # 初始化
        self.transformer = CoordTransform()
        self.batch_results = []
        self.api_delay = 1.0
        self.network_ok = False
        self.log_queue = Queue()
        
        # DNS缓存
        self.dns_cache = {}
        self.cached_ip = None
        
        # 连接池
        self.session = None
        self.init_session()
        
        # 设置GUI
        self.setup_gui()
        
        # 异步检查网络并缓存DNS
        threading.Thread(target=self.check_and_cache_network, daemon=True).start()
    
    def init_session(self):
        """初始化连接会话"""
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        
        # 配置适配器
        adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=10, pool_maxsize=10)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 直接写入日志队列，避免调用log方法
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] 连接会话初始化完成")
    
    def session_get(self, url, **kwargs):
        """使用会话的GET请求，带默认超时"""
        if self.session is None:
            self.init_session()
        
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 15
        
        try:
            return self.session.get(url, **kwargs)
        except Exception as e:
            # 如果session有问题，回退到普通requests
            self.log(f"会话请求失败，使用普通请求: {e}")
            return requests.get(url, timeout=15, **kwargs)
    
    def resolve_dns_with_cache(self, hostname):
        """带缓存的DNS解析"""
        if hostname in self.dns_cache:
            cached_time, ip = self.dns_cache[hostname]
            if time.time() - cached_time < 300:  # 5分钟缓存
                self.log(f"使用DNS缓存: {hostname} -> {ip}")
                return ip
        
        try:
            self.log(f"解析DNS: {hostname}")
            ip = socket.gethostbyname(hostname)
            self.dns_cache[hostname] = (time.time(), ip)
            self.log(f"DNS解析成功: {hostname} -> {ip}")
            return ip
        except socket.gaierror as e:
            self.log(f"DNS解析失败: {hostname} - {e}")
            return None
    
    def get_url_with_ip(self, url):
        """使用IP地址替换主机名构建URL"""
        if self.cached_ip:
            # 替换URL中的主机名为IP
            if "restapi.amap.com" in url:
                new_url = url.replace("restapi.amap.com", self.cached_ip)
                # 添加Host头
                return new_url, {"Host": "restapi.amap.com"}
        return url, None
        
    def setup_gui(self):
        """设置GUI界面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        # 1. 状态栏
        status_frame = ttk.LabelFrame(main_frame, text="状态", padding=5)
        status_frame.pack(fill='x', pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="初始化中...", foreground="blue")
        self.status_label.pack(side='left')
        
        self.network_label = ttk.Label(status_frame, text="网络: 检测中...", foreground="orange")
        self.network_label.pack(side='left', padx=20)
        
        # 2. 搜索区域
        search_frame = ttk.LabelFrame(main_frame, text="地址搜索", padding=10)
        search_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(search_frame, text="地址:").pack(side='left')
        self.search_var = StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=40)
        self.search_entry.pack(side='left', padx=5)
        
        self.search_btn = ttk.Button(search_frame, text="搜索", command=self.search_location)
        self.search_btn.pack(side='left')
        
        # 3. 坐标显示
        coord_frame = ttk.LabelFrame(main_frame, text="坐标", padding=10)
        coord_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(coord_frame, text="WGS84:").grid(row=0, column=0, sticky='w')
        self.wgs84_var = StringVar(value="等待输入")
        ttk.Label(coord_frame, textvariable=self.wgs84_var, foreground="blue").grid(row=0, column=1, sticky='w', padx=10)
        
        ttk.Label(coord_frame, text="GCJ02:").grid(row=1, column=0, sticky='w')
        self.gcj02_var = StringVar(value="等待输入")
        ttk.Label(coord_frame, textvariable=self.gcj02_var, foreground="green").grid(row=1, column=1, sticky='w', padx=10)
        
        # 4. 地图按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(0, 10))
        
        buttons = [
            ("Google地图", self.open_google_web),
            ("Google Earth", self.open_google_earth),
            ("高德地图", self.open_amap),
            ("复制KML", self.copy_kml)
        ]
        
        for text, cmd in buttons:
            ttk.Button(btn_frame, text=text, command=cmd).pack(side='left', padx=2)
        
        # 5. 单点分析
        analysis_frame = ttk.LabelFrame(main_frame, text="单点分析", padding=10)
        analysis_frame.pack(fill='x', pady=(0, 10))
        
        # 输入
        input_frame = ttk.Frame(analysis_frame)
        input_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(input_frame, text="坐标 (经,纬):").pack(side='left')
        self.coord_var = StringVar()
        ttk.Entry(input_frame, textvariable=self.coord_var, width=25).pack(side='left', padx=5)
        ttk.Button(input_frame, text="分析", command=self.analyze_area).pack(side='left')
        
        # 结果
        result_frame = ttk.Frame(analysis_frame)
        result_frame.pack(fill='x')
        
        ttk.Label(result_frame, text="区域:").grid(row=0, column=0, sticky='w')
        self.area_var = StringVar(value="未分析")
        ttk.Label(result_frame, textvariable=self.area_var, foreground="blue").grid(row=0, column=1, sticky='w', padx=10)
        
        ttk.Label(result_frame, text="特征:").grid(row=1, column=0, sticky='w')
        self.feature_var = StringVar(value="未分析")
        ttk.Label(result_frame, textvariable=self.feature_var, foreground="darkgreen").grid(row=1, column=1, sticky='w', padx=10)
        
        # 6. 批量处理
        batch_frame = ttk.LabelFrame(main_frame, text="批量处理", padding=10)
        batch_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 按钮
        batch_btn_frame = ttk.Frame(batch_frame)
        batch_btn_frame.pack(fill='x', pady=(0, 10))
        
        batch_buttons = [
            ("导入CSV", self.import_csv),
            ("导出结果", self.export_results),
            ("生成KML", self.create_batch_kml),
            ("网络诊断", self.show_diagnostics)
        ]
        
        for text, cmd in batch_buttons:
            ttk.Button(batch_btn_frame, text=text, command=cmd).pack(side='left', padx=2)
        
        # 日志
        log_frame = ttk.LabelFrame(batch_frame, text="日志", padding=5)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, wrap='word')
        self.log_text.pack(fill='both', expand=True)
        
        # 进度条
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill='x', pady=(5, 0))
        
        # 启动日志更新
        self.update_log()
    
    def check_and_cache_network(self):
        """检查网络并缓存DNS"""
        try:
            self.log("开始网络检查和DNS缓存...")
            
            # 解析并缓存DNS
            ip = self.resolve_dns_with_cache('restapi.amap.com')
            if ip:
                self.cached_ip = ip
                self.log(f"已缓存IP: {ip}")
            
            # 测试API连接
            key = self.get_amap_key()
            success = False
            
            # 测试使用IP直接连接
            if self.cached_ip:
                try:
                    self.log(f"测试使用IP连接: {self.cached_ip}")
                    # 使用IP直接连接
                    url = f"https://{self.cached_ip}/v3/geocode/regeo"
                    params = {"location": "116.3974,39.9093", "key": key, "extensions": "base"}
                    headers = {"Host": "restapi.amap.com"}
                    
                    resp = self.session_get(url, params=params, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get('status') == '1':
                            success = True
                            self.log(f"IP直接连接成功: {self.cached_ip}")
                except Exception as e:
                    self.log(f"IP直接连接失败: {e}")
            
            # 如果IP连接失败，尝试域名连接
            if not success:
                endpoints = [
                    "https://restapi.amap.com/v3/geocode/regeo",
                    "http://restapi.amap.com/v3/geocode/regeo"
                ]
                
                for url in endpoints:
                    try:
                        self.log(f"测试API端点: {url}")
                        params = {"location": "116.3974,39.9093", "key": key, "extensions": "base"}
                        
                        resp = self.session_get(url, params=params)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get('status') == '1':
                                success = True
                                self.log(f"API端点 {url} 测试成功")
                                break
                            else:
                                self.log(f"API返回错误: {data.get('info', '未知错误')}")
                        else:
                            self.log(f"HTTP错误 {resp.status_code}: {url}")
                    except Exception as e:
                        self.log(f"端点 {url} 失败: {e}")
            
            if success:
                self.network_ok = True
                self.root.after(0, lambda: self.network_label.config(text="网络: 正常(缓存)", foreground="green"))
                self.log("网络检查: 正常 (DNS已缓存)")
            else:
                self.root.after(0, lambda: self.network_label.config(text="网络: 连接失败", foreground="red"))
                self.log("网络检查: 所有连接方式都失败")
                
        except Exception as e:
            self.root.after(0, lambda: self.network_label.config(text="网络: 检查失败", foreground="red"))
            self.log(f"网络检查异常: {e}")
        
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
                self.log_text.insert('end', msg + "\n")
                self.log_text.see('end')
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
            
            # 尝试多个端点
            endpoints = [
                "https://restapi.amap.com/v3/geocode/regeo",
                "http://restapi.amap.com/v3/geocode/regeo"
            ]
            
            self.log(f"获取区域信息: {lng}, {lat}")
            
            for url in endpoints:
                try:
                    params = {
                        "location": f"{lng},{lat}",
                        "key": key,
                        "extensions": "all"
                    }
                    
                    # 设置代理
                    proxies = {}
                    if os.environ.get('HTTP_PROXY'):
                        proxies['http'] = os.environ.get('HTTP_PROXY')
                    if os.environ.get('HTTPS_PROXY'):
                        proxies['https'] = os.environ.get('HTTPS_PROXY')
                    
                    self.log(f"尝试端点: {url}")
                    resp = requests.get(url, params=params, timeout=15, 
                                      proxies=proxies if proxies else None)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data['status'] == '1':
                            addr = data['regeocode']
                            province = addr.get('addressComponent', {}).get('province', '')
                            city = addr.get('addressComponent', {}).get('city', '')
                            district = addr.get('addressComponent', {}).get('district', '')
                            
                            # 在日志中显示地址信息
                            formatted_addr = addr.get('formatted_address', '')
                            self.log(f"地址: {formatted_addr}")
                            
                            # API频率控制
                            time.sleep(0.5)
                            
                            # 获取POI密度
                            poi_count = self.get_poi_count(lng, lat, key)
                            self.log(f"POI密度: {poi_count}")
                            
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
                            
                            result = f"{area_type} (POI:{poi_count}) - {province}{city}{district}"
                            self.log(f"区域属性: {result}")
                            return result
                        else:
                            error_msg = data.get('info', '未知错误')
                            self.log(f"API返回错误: {error_msg}")
                            continue  # 尝试下一个端点
                    else:
                        self.log(f"HTTP错误 {resp.status_code}: {url}")
                        continue  # 尝试下一个端点
                        
                except requests.exceptions.Timeout:
                    self.log(f"端点 {url} 超时")
                    continue
                except requests.exceptions.ConnectionError as e:
                    self.log(f"端点 {url} 连接错误: {e}")
                    continue
                except Exception as e:
                    self.log(f"端点 {url} 异常: {e}")
                    continue
            
            # 所有端点都失败
            self.log("所有API端点都失败")
            return "网络错误: 无法连接到高德API"
            
        except Exception as e:
            self.log(f"获取区域信息失败: {e}")
            return f"错误: {str(e)[:50]}..."
    
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
            
            # 尝试多个端点
            endpoints = [
                "https://restapi.amap.com/v3/geocode/regeo",
                "http://restapi.amap.com/v3/geocode/regeo"
            ]
            
            self.log(f"获取地理特征: {lng}, {lat}")
            
            for url in endpoints:
                try:
                    params = {
                        "location": f"{lng},{lat}",
                        "key": key,
                        "extensions": "all"
                    }
                    
                    # 设置代理
                    proxies = {}
                    if os.environ.get('HTTP_PROXY'):
                        proxies['http'] = os.environ.get('HTTP_PROXY')
                    if os.environ.get('HTTPS_PROXY'):
                        proxies['https'] = os.environ.get('HTTPS_PROXY')
                    
                    self.log(f"尝试端点: {url}")
                    resp = requests.get(url, params=params, timeout=15,
                                      proxies=proxies if proxies else None)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data['status'] == '1':
                            addr = data['regeocode'].get('formatted_address', '')
                            self.log(f"分析地址: {addr}")
                            
                            features = []
                            if any(k in addr for k in ['路', '街', '道', '大道', '公路']):
                                features.append('路边')
                                self.log("特征: 路边")
                            if any(k in addr for k in ['公园', '广场', '绿地', '花园', '草坪']):
                                features.append('绿地')
                                self.log("特征: 绿地")
                            if any(k in addr for k in ['河', '湖', '海', '江', '溪', '水']):
                                features.append('水体')
                                self.log("特征: 水体")
                            if any(k in addr for k in ['山', '峰', '岭', '丘']):
                                features.append('山地')
                                self.log("特征: 山地")
                            if any(k in addr for k in ['楼', '大厦', '写字楼', '办公楼']):
                                features.append('建筑')
                                self.log("特征: 建筑")
                            
                            result = ' | '.join(features) if features else '无特殊特征'
                            self.log(f"地理特征结果: {result}")
                            return result
                        else:
                            error_msg = data.get('info', '未知错误')
                            self.log(f"API返回错误: {error_msg}")
                            continue  # 尝试下一个端点
                    else:
                        self.log(f"HTTP错误 {resp.status_code}: {url}")
                        continue  # 尝试下一个端点
                        
                except requests.exceptions.Timeout:
                    self.log(f"端点 {url} 超时")
                    continue
                except requests.exceptions.ConnectionError as e:
                    self.log(f"端点 {url} 连接错误: {e}")
                    continue
                except Exception as e:
                    self.log(f"端点 {url} 异常: {e}")
                    continue
            
            # 所有端点都失败
            self.log("所有API端点都失败")
            return "网络错误: 无法连接到高德API"
            
        except Exception as e:
            self.log(f"获取地理特征失败: {e}")
            return f"错误: {str(e)[:50]}..."
    
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
        if self.wgs84_var.get() != "等待输入":
            try:
                coords = self.wgs84_var.get().split(',')
                lat, lng = coords[1].strip(), coords[0].strip()
                address = self.search_var.get() or "位置"
                
                # 创建KML文件
                kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>{address}</name>
    <Point>
      <coordinates>{lng},{lat},0</coordinates>
    </Point>
  </Placemark>
</kml>'''
                
                # 保存临时文件
                with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.kml', encoding='utf-8') as f:
                    f.write(kml)
                    temp_file = f.name
                
                # 尝试打开
                try:
                    os.startfile(temp_file)
                except:
                    messagebox.showinfo("提示", 
                        f"KML文件已保存到:\n{temp_file}\n"
                        "请手动在Google Earth中打开")
                
            except Exception as e:
                messagebox.showerror("错误", f"打开Google Earth失败: {e}")
        else:
            messagebox.showwarning("警告", "请先搜索位置")
    
    def open_amap(self):
        """打开高德地图"""
        if self.wgs84_var.get() != "等待输入":
            try:
                coords = self.wgs84_var.get().split(',')
                lng, lat = coords[0].strip(), coords[1].strip()
                
                # 转换到GCJ02
                gcj_lng, gcj_lat = self.transformer.wgs84_to_gcj02(float(lng), float(lat))
                webbrowser.open(f"https://uri.amap.com/marker?position={gcj_lng},{gcj_lat}")
            except:
                messagebox.showwarning("警告", "请先搜索位置")
    
    def copy_kml(self):
        """复制KML到剪贴板"""
        if self.wgs84_var.get() != "等待输入":
            try:
                coords = self.wgs84_var.get().split(',')
                lat, lng = coords[1].strip(), coords[0].strip()
                address = self.search_var.get() or "位置"
                
                kml = f'''<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>{address}</name>
    <Point>
      <coordinates>{lng},{lat},0</coordinates>
    </Point>
  </Placemark>
</kml>'''
                
                self.root.clipboard_clear()
                self.root.clipboard_append(kml)
                messagebox.showinfo("成功", "KML代码已复制到剪贴板")
            except Exception as e:
                messagebox.showerror("错误", f"复制失败: {e}")
        else:
            messagebox.showwarning("警告", "请先搜索位置")
    
    def import_csv(self):
        """导入CSV文件 - 简化版：按单点处理"""
        if not self.network_ok:
            messagebox.showwarning("警告", "网络连接有问题，请先使用网络诊断功能")
            return
        
        filename = filedialog.askopenfilename(
            title="选择CSV文件",
            filetypes=[("CSV文件", "*.csv"), ("Excel文件", "*.xlsx"), ("所有文件", "*.*")]
        )
        
        if not filename:
            return
        
        self.log(f"开始导入文件: {filename}")
        self.log("=" * 50)
        self.status_label.config(text="处理中...")
        self.progress.start()
        
        def do_import():
            try:
                results = []
                total_rows = 0
                success_rows = 0
                failed_rows = 0
                
                # 读取文件
                if filename.endswith('.xlsx'):
                    df = pd.read_excel(filename)
                    data_rows = df.values.tolist()
                    header = df.columns.tolist()
                else:
                    # 尝试多种编码读取CSV文件
                    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
                    data_rows = None
                    header = None
                    
                    for encoding in encodings:
                        try:
                            self.log(f"尝试使用 {encoding} 编码读取文件...")
                            with open(filename, 'r', encoding=encoding) as f:
                                reader = csv.reader(f)
                                header = next(reader, [])
                                data_rows = list(reader)
                            self.log(f"✅ 使用 {encoding} 编码读取成功")
                            break
                        except UnicodeDecodeError as e:
                            self.log(f"❌ {encoding} 编码失败: {e}")
                            continue
                        except Exception as e:
                            self.log(f"❌ {encoding} 编码读取异常: {e}")
                            continue
                    
                    if data_rows is None:
                        self.log("❌ 所有编码尝试都失败")
                        self.root.after(0, lambda: messagebox.showerror("错误", 
                            "无法读取CSV文件，请检查文件编码。\n"
                            "支持的编码: UTF-8, GBK, GB2312, UTF-8-SIG"))
                        return
                
                total_rows = len(data_rows)
                self.log(f"总行数: {total_rows}")
                self.log("")
                
                for i, row in enumerate(data_rows):
                    if not row:
                        continue
                    
                    try:
                        # 解析行数据
                        row_data = self.parse_row_data(row, header)
                        if not row_data:
                            failed_rows += 1
                            continue
                        
                        name = row_data.get('名称', f'行{i+1}')
                        self.log(f"处理第{i+1}行: {name}")
                        
                        # 获取坐标
                        coord_data = self.get_coordinates(row_data)
                        if not coord_data:
                            self.log(f"  获取坐标失败")
                            failed_rows += 1
                            continue
                        
                        lng, lat, gcj_lng, gcj_lat = coord_data
                        self.log(f"  坐标: WGS84({lng:.6f}, {lat:.6f})")
                        self.log(f"  转换: GCJ02({gcj_lng:.6f}, {gcj_lat:.6f})")
                        
                        # 获取区域属性（使用与单点分析完全相同的方法和坐标）
                        # 重要：使用输入的WGS84坐标，而不是转换后的GCJ02坐标
                        self.log("  获取区域属性...")
                        area_info = self.get_area_info(lng, lat)  # 使用WGS84坐标，不是GCJ02
                        
                        # 获取地理特征（使用与单点分析完全相同的方法和坐标）
                        self.log("  获取地理特征...")
                        features_info = self.get_features(lng, lat)  # 使用WGS84坐标，不是GCJ02
                        
                        # 构建结果
                        result = {
                            '名称': name,
                            'WGS84经度': round(lng, 6),
                            'WGS84纬度': round(lat, 6),
                            'GCJ02经度': round(gcj_lng, 6),
                            'GCJ02纬度': round(gcj_lat, 6),
                            '区域属性': area_info,
                            '地理特征': features_info,
                            '状态': '成功'
                        }
                        
                        # 添加原始数据中的其他列
                        for key, value in row_data.items():
                            if key not in result:
                                result[key] = value
                        
                        results.append(result)
                        success_rows += 1
                        
                        self.log(f"  ✓ 完成")
                        self.log(f"    区域: {area_info}")
                        self.log(f"    特征: {features_info}")
                        self.log("")
                        
                        # 简单延迟，避免请求过快
                        time.sleep(0.5)
                        
                    except Exception as e:
                        self.log(f"  ✗ 处理失败: {e}")
                        failed_rows += 1
                        self.log("")
                
                self.batch_results = results
                self.log("=" * 50)
                self.log(f"导入完成!")
                self.log(f"成功: {success_rows} 行")
                self.log(f"失败: {failed_rows} 行")
                self.log(f"总计: {total_rows} 行")
                
                summary = f"导入完成!\n成功: {success_rows} 行\n失败: {failed_rows} 行\n总计: {total_rows} 行"
                self.root.after(0, lambda: messagebox.showinfo("处理完成", summary))
                
            except Exception as e:
                self.root.after(0, lambda: self.log(f"导入失败: {e}"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"导入失败: {e}"))
            finally:
                self.root.after(0, lambda: self.status_label.config(text="就绪"))
                self.root.after(0, lambda: self.progress.stop())
        
        threading.Thread(target=do_import, daemon=True).start()
    
    def parse_row_data(self, row, header):
        """解析行数据"""
        if not row:
            return None
        
        row_data = {}
        for i, value in enumerate(row):
            if i < len(header):
                key = header[i]
            else:
                key = f'列{i+1}'
            
            if isinstance(value, str):
                row_data[key] = value.strip()
            else:
                row_data[key] = str(value).strip() if value is not None else ''
        
        return row_data
    
    def get_coordinates(self, row_data):
        """获取坐标 - 支持地址和坐标两种格式（使用与单点搜索相同的方法）"""
        try:
            # 尝试从坐标列获取
            coord_keys = ['经度', '纬度', 'longitude', 'latitude', 'lng', 'lat']
            lng_key = None
            lat_key = None
            
            for key in row_data:
                key_lower = key.lower()
                if any(k in key_lower for k in ['经', 'long', 'lng']):
                    lng_key = key
                elif any(k in key_lower for k in ['纬', 'lat']):
                    lat_key = key
            
            if lng_key and lat_key:
                try:
                    lng = float(row_data[lng_key])
                    lat = float(row_data[lat_key])
                    gcj_lng, gcj_lat = self.transformer.wgs84_to_gcj02(lng, lat)
                    return lng, lat, gcj_lng, gcj_lat
                except (ValueError, TypeError):
                    pass
            
            # 尝试从地址获取（使用与单点搜索相同的方法）
            address_keys = ['地址', 'address', '位置', 'location']
            for key in address_keys:
                if key in row_data and row_data[key]:
                    address = row_data[key]
                    self.log(f"  搜索地址: {address}")
                    
                    key = self.get_amap_key()
                    url = "https://restapi.amap.com/v3/geocode/geo"
                    params = {"address": address, "key": key}
                    
                    try:
                        # 使用简单的requests.get()，与单点搜索保持一致
                        resp = requests.get(url, params=params, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data['status'] == '1' and data['geocodes']:
                                loc = data['geocodes'][0]['location']
                                gcj_lng, gcj_lat = map(float, loc.split(','))
                                lng, lat = self.transformer.gcj02_to_wgs84(gcj_lng, gcj_lat)
                                formatted_addr = data['geocodes'][0].get('formatted_address', '')
                                self.log(f"  找到地址: {formatted_addr}")
                                return lng, lat, gcj_lng, gcj_lat
                            else:
                                self.log(f"  API返回错误: {data.get('info', '未找到地址')}")
                        else:
                            self.log(f"  HTTP错误 {resp.status_code}")
                    except requests.exceptions.Timeout:
                        self.log(f"  请求超时")
                    except requests.exceptions.ConnectionError as e:
                        self.log(f"  连接错误: {e}")
                    except Exception as e:
                        self.log(f"  请求异常: {e}")
            
            return None
            
        except Exception as e:
            self.log(f"  获取坐标错误: {e}")
            return None
    
    def get_area_info_simple(self, lng, lat):
        """获取区域信息 - 简化版（使用优化网络连接）"""
        try:
            key = self.get_amap_key()
            
            # 尝试多个端点
            endpoints = [
                "https://restapi.amap.com/v3/geocode/regeo",
                "http://restapi.amap.com/v3/geocode/regeo"
            ]
            
            for url in endpoints:
                try:
                    params = {
                        "location": f"{lng},{lat}",
                        "key": key,
                        "extensions": "base"
                    }
                    
                    # 尝试使用IP直连
                    if self.cached_ip and "restapi.amap.com" in url:
                        ip_url = url.replace("restapi.amap.com", self.cached_ip)
                        headers = {"Host": "restapi.amap.com"}
                        self.log(f"  尝试IP直连: {self.cached_ip}")
                        resp = self.session_get(ip_url, params=params, headers=headers, timeout=10)
                    else:
                        resp = self.session_get(url, params=params, timeout=10)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data['status'] == '1':
                            addr = data['regeocode']
                            province = addr.get('addressComponent', {}).get('province', '')
                            city = addr.get('addressComponent', {}).get('city', '')
                            district = addr.get('addressComponent', {}).get('district', '')
                            
                            # 简单分类
                            if city and '市' in city:
                                return f"市区 - {province}{city}{district}"
                            elif district and ('区' in district or '县' in district):
                                return f"县城 - {province}{city}{district}"
                            else:
                                return f"其他 - {province}{city}{district}"
                        else:
                            error_msg = data.get('info', '未知错误')
                            self.log(f"  API返回错误: {error_msg}")
                            continue
                    else:
                        self.log(f"  HTTP错误 {resp.status_code}: {url}")
                        continue
                        
                except requests.exceptions.Timeout:
                    self.log(f"  端点 {url} 超时")
                    continue
                except requests.exceptions.ConnectionError as e:
                    self.log(f"  端点 {url} 连接错误: {e}")
                    continue
                except Exception as e:
                    self.log(f"  端点 {url} 异常: {e}")
                    continue
            
            # 所有端点都失败
            return "网络错误: 无法连接到高德API"
            
        except Exception as e:
            error_msg = str(e)
            # 显示完整错误信息，但限制长度
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            self.log(f"  区域属性获取错误: {error_msg}")
            return f"错误: {error_msg}"
    
    def get_features_simple(self, lng, lat):
        """获取地理特征 - 简化版（使用优化网络连接）"""
        try:
            key = self.get_amap_key()
            
            # 尝试多个端点
            endpoints = [
                "https://restapi.amap.com/v3/geocode/regeo",
                "http://restapi.amap.com/v3/geocode/regeo"
            ]
            
            for url in endpoints:
                try:
                    params = {
                        "location": f"{lng},{lat}",
                        "key": key,
                        "extensions": "base"
                    }
                    
                    # 尝试使用IP直连
                    if self.cached_ip and "restapi.amap.com" in url:
                        ip_url = url.replace("restapi.amap.com", self.cached_ip)
                        headers = {"Host": "restapi.amap.com"}
                        self.log(f"  尝试IP直连: {self.cached_ip}")
                        resp = self.session_get(ip_url, params=params, headers=headers, timeout=10)
                    else:
                        resp = self.session_get(url, params=params, timeout=10)
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        if data['status'] == '1':
                            addr = data['regeocode'].get('formatted_address', '')
                            
                            features = []
                            if any(k in addr for k in ['路', '街', '道', '大道', '公路']):
                                features.append('路边')
                            if any(k in addr for k in ['公园', '广场', '绿地', '花园', '草坪']):
                                features.append('绿地')
                            if any(k in addr for k in ['河', '湖', '海', '江', '溪', '水']):
                                features.append('水体')
                            if any(k in addr for k in ['山', '峰', '岭', '丘']):
                                features.append('山地')
                            if any(k in addr for k in ['楼', '大厦', '写字楼', '办公楼']):
                                features.append('建筑')
                            
                            return ' | '.join(features) if features else '无特殊特征'
                        else:
                            error_msg = data.get('info', '未知错误')
                            self.log(f"  API返回错误: {error_msg}")
                            continue
                    else:
                        self.log(f"  HTTP错误 {resp.status_code}: {url}")
                        continue
                        
                except requests.exceptions.Timeout:
                    self.log(f"  端点 {url} 超时")
                    continue
                except requests.exceptions.ConnectionError as e:
                    self.log(f"  端点 {url} 连接错误: {e}")
                    continue
                except Exception as e:
                    self.log(f"  端点 {url} 异常: {e}")
                    continue
            
            # 所有端点都失败
            return "网络错误: 无法连接到高德API"
            
        except Exception as e:
            error_msg = str(e)
            # 显示完整错误信息，但限制长度
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            self.log(f"  地理特征获取错误: {error_msg}")
            return f"错误: {error_msg}"
    
    def export_results(self):
        """导出结果"""
        if not self.batch_results:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存结果",
            defaultextension=".xlsx",
            filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
        )
        
        if not filename:
            return
        
        try:
            df = pd.DataFrame(self.batch_results)
            
            if filename.endswith('.xlsx'):
                df.to_excel(filename, index=False)
            else:
                df.to_csv(filename, index=False, encoding='utf-8-sig')
            
            self.log(f"导出完成: {filename}")
            messagebox.showinfo("成功", f"导出完成: {filename}")
            
        except Exception as e:
            self.log(f"导出失败: {e}")
            messagebox.showerror("错误", f"导出失败: {e}")
    
    def create_batch_kml(self):
        """生成批量KML"""
        if not self.batch_results:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        filename = filedialog.asksaveasfilename(
            title="保存KML文件",
            defaultextension=".kml",
            filetypes=[("KML文件", "*.kml")]
        )
        
        if not filename:
            return
        
        try:
            kml_lines = [
                '<?xml version="1.0" encoding="UTF-8"?>',
                '<kml xmlns="http://www.opengis.net/kml/2.2">',
                '<Document>'
            ]
            
            for result in self.batch_results:
                if result.get('状态') == '成功':
                    name = result.get('名称', '未命名')
                    lng = result.get('WGS84经度', 0)
                    lat = result.get('WGS84纬度', 0)
                    
                    kml_lines.extend([
                        '  <Placemark>',
                        f'    <name>{name}</name>',
                        '    <Point>',
                        f'      <coordinates>{lng},{lat},0</coordinates>',
                        '    </Point>',
                        '  </Placemark>'
                    ])
            
            kml_lines.extend(['</Document>', '</kml>'])
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(kml_lines))
            
            self.log(f"KML文件已保存: {filename}")
            messagebox.showinfo("成功", f"KML文件已保存: {filename}")
            
        except Exception as e:
            self.log(f"生成KML失败: {e}")
            messagebox.showerror("错误", f"生成KML失败: {e}")
    
    def show_diagnostics(self):
        """显示网络诊断"""
        try:
            import platform
            import subprocess
            
            diagnostics = []
            diagnostics.append("="*60)
            diagnostics.append("网络诊断信息")
            diagnostics.append("="*60)
            
            # 系统信息
            diagnostics.append(f"操作系统: {platform.system()} {platform.release()}")
            diagnostics.append(f"Python版本: {sys.version.split()[0]}")
            
            # DNS测试
            diagnostics.append("\nDNS测试:")
            try:
                result = socket.gethostbyname_ex('restapi.amap.com')
                diagnostics.append(f"  ✅ restapi.amap.com 解析成功")
                diagnostics.append(f"     IP地址: {', '.join(result[2])}")
            except socket.gaierror as e:
                diagnostics.append(f"  ❌ restapi.amap.com 解析失败: {e}")
            
            # 连接测试
            diagnostics.append("\n连接测试:")
            try:
                key = self.get_amap_key()
                url = "https://restapi.amap.com/v3/geocode/regeo"
                params = {"location": "116.3974,39.9093", "key": key}
                
                resp = requests.get(url, params=params, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('status') == '1':
                        diagnostics.append(f"  ✅ API连接成功 (HTTP {resp.status_code})")
                    else:
                        diagnostics.append(f"  ❌ API返回错误: {data.get('info', '未知错误')}")
                else:
                    diagnostics.append(f"  ❌ HTTP错误: {resp.status_code}")
            except Exception as e:
                diagnostics.append(f"  ❌ API连接失败: {e}")
            
            # 显示对话框
            dialog = Tk()
            dialog.title("网络诊断")
            dialog.geometry("600x400")
            
            text = scrolledtext.ScrolledText(dialog, wrap='word')
            text.pack(fill='both', expand=True, padx=10, pady=10)
            text.insert('1.0', '\n'.join(diagnostics))
            text.config(state='disabled')
            
            ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=10)
            
            dialog.mainloop()
            
        except Exception as e:
            messagebox.showerror("错误", f"诊断失败: {e}")
    
    def run(self):
        """运行程序"""
        self.root.mainloop()

if __name__ == "__main__":
    app = GoogleMapsToolsComplete()
    app.run()
