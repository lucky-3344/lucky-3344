import csv
from difflib import SequenceMatcher
import re
import sys
import time
from tkinter import filedialog, messagebox
from turtle import pd
import requests
import json
import tempfile
import os
import webbrowser
import jieba
from coord_transform import CoordTransform
import pandas as pd

class GoogleMapsTools:
    def __init__(self):
        # 基本导入
        import tkinter as tk
        from tkinter import ttk
        self.tk = tk
        self.ttk = ttk
        self.messagebox = messagebox
        
        self.transformer = CoordTransform()
        self.setup_gui()
        self.batch_results = []
        # API 节流：批量模式每次调用高德接口之间的延迟（秒）
        self.api_delay = 0.8
            # 强制直连高德域名（默认关闭，走系统网络设置）
        self.force_direct_amap = False
        # 强制禁用系统代理（默认关闭）
        self.force_no_proxy = False
        # 可选：IP直连
        self.amap_ip_override = None
        self._load_amap_settings()
        # 批量分析时是否用输入坐标做判定（与单点一致），而不是转换后的坐标
        self.batch_use_input_coord_for_analysis = True
        
    def setup_gui(self):
        self.root = self.tk.Tk()
        self.root.title("Google Maps/Earth 坐标转换工具")
        self.root.geometry("600x600")
        
        # 修改搜索框部分
        search_frame = self.ttk.LabelFrame(self.root, text="地址搜索", padding=10)
        search_frame.pack(fill='x', padx=10, pady=5)
        
        search_input_frame = self.ttk.Frame(search_frame)
        search_input_frame.pack(fill='x')
        
        self.search_var = self.tk.StringVar()
        self.search_var.trace('w', self.on_search_change)  # 添加输入监听
        
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
        self.ttk.Button(batch_frame, text="批量在谷歌地图显示", 
                  command=self.open_batch_in_google_maps).pack(side='left', padx=5)
        self.ttk.Button(batch_frame, text="批量在高德地图显示", 
                  command=self.open_batch_in_amap).pack(side='left', padx=5)

        progress_frame = self.ttk.Frame(batch_frame)
        progress_frame.pack(fill='x', pady=5)
        self.batch_progress = self.ttk.Progressbar(progress_frame, orient='horizontal', mode='determinate')
        self.batch_progress.pack(fill='x', expand=True)

        log_frame = self.ttk.LabelFrame(self.root, text="运行日志", padding=10)
        log_frame.pack(fill='both', padx=10, pady=5, expand=True)
        self.log_text = self.tk.Text(log_frame, height=10, wrap='word')
        log_scroll = self.ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')
    
    def _log(self, message, log_content=None):
        if log_content is not None:
            log_content.append(message)
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        try:
            if hasattr(self, "log_text"):
                self.log_text.insert("end", line + "\n")
                self.log_text.see("end")
        except Exception:
            pass
        print(line)

    def on_search_change(self, *args):
        """监控搜索文本变化"""
        text = self.search_var.get()
        # 计算字节数（中文占3字节，英文占1字节）
        byte_count = len(text.encode('utf-8'))
        self.char_count_label.config(text=f"{byte_count}/84 字节")
        
        # 如果超过限制，显示警告颜色
        if byte_count > 84:
            self.char_count_label.config(foreground='red')
        else:
            self.char_count_label.config(foreground='black')

    def show_address_selection(self, addresses):
        """显示地址选择对话框"""
        select_window = self.tk.Toplevel(self.root)
        select_window.title("选择地址")
        select_window.geometry("600x400")
        
        # 使用 Frame 进行整体布局管理
        main_frame = self.ttk.Frame(select_window)
        main_frame.pack(fill='both', expand=True)
        
        # 创建说明标签
        self.ttk.Label(main_frame, text="找到以下匹配地址，请选择：", padding=10).pack()
        
        # 创建列表框 - 使用权重分配空间
        list_frame = self.ttk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 配置主框架的网格
        main_frame.grid_rowconfigure(1, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        
        # 使用 Treeview 替代 Listbox
        tree = self.ttk.Treeview(list_frame, columns=('地址', '省市区', '匹配度'), show='headings')
        tree.heading('地址', text='地址')
        tree.heading('省市区', text='省市区')
        tree.heading('匹配度', text='匹配度')
        
        # 设置列宽
        tree.column('地址', width=300)
        tree.column('省市区', width=150)
        tree.column('匹配度', width=100)
        
        # 添加滚动条
        scrollbar = self.ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        
        # 添加地址选项
        for addr in addresses:
            formatted_addr = addr['formatted_address']
            province = addr.get('province', '')
            city = addr.get('city', '')
            district = addr.get('district', '')
            
            tree.insert('', 'end', values=(
                formatted_addr,
                f"{province} {city} {district}".strip(),
                "√" if self.search_var.get() in formatted_addr else "模糊匹配"
            ))
    
        def on_select():
            selection = tree.selection()
            if selection:
                index = tree.index(selection[0])
                select_window.selected_address = addresses[index]
                select_window.destroy()
    
        def on_cancel():
            select_window.selected_address = None
            select_window.destroy()
    
        # 使用Frame固定在底部的按钮
        button_frame = self.ttk.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)
    
        # 按钮靠右对齐
        cancel_btn = self.ttk.Button(button_frame, text="取消", command=on_cancel)
        cancel_btn.pack(side='right', padx=5)
    
        ok_btn = self.ttk.Button(button_frame, text="确定", command=on_select)
        ok_btn.pack(side='right', padx=5)
    
        # 设置最小窗口大小
        select_window.update()
        min_width = 600
        min_height = 400
        select_window.minsize(min_width, min_height)
    
        # 将窗口位置设置为主窗口中心
        select_window.transient(self.root)
        select_window.grab_set()
    
        # 计算窗口位置使其居中
        x = self.root.winfo_x() + (self.root.winfo_width() - select_window.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - select_window.winfo_height()) // 2
        select_window.geometry(f"+{x}+{y}")
    
        # 等待用户选择
        self.root.wait_window(select_window)
        return getattr(select_window, 'selected_address', None)

    def search_location(self):
        """搜索地址获取坐标"""
        address = self.search_var.get()
        if not address:
            self.messagebox.showwarning("警告", "请输入搜索地址")
            return

        try:
            # 1. 首先通过AI进行模糊匹配
            possible_addresses = self.ai_suggest_addresses(address)
            
            # 2. 如果有多个建议结果，让用户选择
            if len(possible_addresses) > 1:
                selected = self.show_suggestions(possible_addresses)
                if not selected:
                    return
                search_address = selected
            else:
                search_address = possible_addresses[0] if possible_addresses else address
            
            # 3. 使用选定的地址调用高德API
            result = self._do_search(search_address)
            
            if result:
                self._update_coords(result)
            else:
                self.messagebox.showerror("错误", "未找到该地址，请尝试：\n1. 使用更准确的地址\n2. 减少地址关键词")

        except Exception as e:
            self.messagebox.showerror("错误", f"搜索失败: {str(e)}")

    def ai_suggest_addresses(self, query):
        """使用AI生成地址建议"""
        # 定义常见地址模式
        address_patterns = [
            r"(.+[市区县])",
            r"(.+[镇乡路街道])",
            r"(.+[号楼栋])",
            r"(.+[园区广场])",
            r"(.+[商场中心])",
        ]
        
        # 智能分词
        segments = list(jieba.cut_for_search(query))
        
        # 生成可能的地址组合
        possible_addresses = []
        temp_addr = ""
        
        for seg in segments:
            temp_addr += seg
            # 检查是否匹配地址模式
            for pattern in address_patterns:
                if re.match(pattern, temp_addr):
                    possible_addresses.append(temp_addr)
        
        # 添加原始查询
        if query not in possible_addresses:
            possible_addresses.append(query)
        
        # 使用相似度算法排序
        scored_addresses = []
        for addr in possible_addresses:
            score = SequenceMatcher(None, query, addr).ratio()
            scored_addresses.append((addr, score))
        
        # 按相似度排序并返回前两个最佳匹配
        scored_addresses.sort(key=lambda x: x[1], reverse=True)
        return [addr for addr, score in scored_addresses[:2]]

    def show_suggestions(self, suggestions):
        """显示地址建议选择对话框"""
        select_window = self.tk.Toplevel(self.root)
        select_window.title("选择最接近的地址")
        select_window.minsize(500, 300)  # 设置最小窗口大小
        
        # 使用 ttk.Frame 作为主容器
        main_frame = self.ttk.Frame(select_window)
        main_frame.pack(fill='both', expand=True)
        
        # 标题标签
        self.ttk.Label(main_frame, text="请选择最接近的地址：", padding=10).pack()
        
        # 列表框架 - 设置权重使其自动调整大小
        list_frame = self.ttk.Frame(main_frame)
        list_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        # 使用 Treeview 显示建议
        tree = self.ttk.Treeview(list_frame, columns=('地址', '匹配度'), show='headings', height=8)
        tree.heading('地址', text='地址')
        tree.heading('匹配度', text='匹配度')
        
        # 设置列宽
        tree.column('地址', width=350, minwidth=200)
        tree.column('匹配度', width=100, minwidth=80)
        
        # 添加建议
        for i, addr in enumerate(suggestions, 1):
            tree.insert('', 'end', values=(
                addr,
                f"建议 {i}"
            ))
        
        # 添加垂直滚动条
        scrollbar = self.ttk.Scrollbar(list_frame, orient="vertical", command=tree.yview)
        scrollbar.pack(side='right', fill='y')
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        
        def on_select():
            if tree.selection():
                index = tree.index(tree.selection()[0])
                select_window.selected = suggestions[index]
                select_window.destroy()
        
        def on_cancel():
            select_window.selected = None
            select_window.destroy()
        
        # 按钮框架 - 固定在底部
        button_frame = self.ttk.Frame(main_frame)
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        
        # 使用 pack_forget 和 pack 确保按钮总是在最后显示
        button_frame.pack_forget()
        button_frame.pack(side='bottom', fill='x', padx=10, pady=10)
        
        # 按钮靠右对齐
        self.ttk.Button(button_frame, text="取消", command=on_cancel).pack(side='right', padx=5)
        self.ttk.Button(button_frame, text="确定", command=on_select).pack(side='right', padx=5)
        
        # 窗口管理
        select_window.transient(self.root)  # 将窗口设置为模态
        select_window.grab_set()  # 阻止与其他窗口的交互
        
        # 居中显示
        select_window.update_idletasks()  # 更新窗口大小
        width = 500
        height = 300
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        select_window.geometry(f"{width}x{height}+{x}+{y}")
        
        # 等待窗口关闭
        self.root.wait_window(select_window)
        
        return getattr(select_window, 'selected', None)

    def _do_search(self, address):
        """执行实际的搜索请求"""
        AMAP_KEY = self.get_amap_key()
        url, headers = self._amap_endpoint("/v3/geocode/geo")
        params = {
            "address": address,
            "key": AMAP_KEY,
            "city": "",
            "output": "json"
        }
        
        data = self._get_json_with_retry(url, params, retries=2, timeout=5, headers=headers)
        
        if data['status'] == '1' and data['geocodes']:
            # 使用模糊搜索处理结果
            fuzzy_results = self.fuzzy_search(address, data['geocodes'])
            
            if len(fuzzy_results) > 1:
                # 如果找到多个匹配结果，显示选择对话框
                return self.show_address_selection(fuzzy_results)
            elif len(fuzzy_results) == 1:
                return fuzzy_results[0]
        return None

    def _amap_endpoint(self, path):
        """根据可选的 IP 覆盖构造高德请求 endpoint 和 headers"""
        headers = None
        ip_override = os.environ.get('AMAP_IP_OVERRIDE') or self.amap_ip_override
        if ip_override:
            ip_override = ip_override.strip()
            if ip_override.startswith("http://") or ip_override.startswith("https://"):
                ip_override = ip_override.split("//", 1)[-1]
            ip_override = ip_override.rstrip("/")
            if ip_override:
                return f"https://{ip_override}{path}", {"Host": "restapi.amap.com"}
        if self.force_direct_amap:
            return f"https://restapi.amap.com{path}", headers
        return f"https://restapi.amap.com{path}", headers

    def _load_amap_settings(self):
        """从环境变量/配置文件读取高德连接策略"""
        env_force_direct = os.environ.get("AMAP_FORCE_DIRECT")
        env_force_no_proxy = os.environ.get("AMAP_FORCE_NO_PROXY")
        if env_force_direct is not None:
            self.force_direct_amap = env_force_direct.strip() in ("1", "true", "True", "YES", "yes")
        if env_force_no_proxy is not None:
            self.force_no_proxy = env_force_no_proxy.strip() in ("1", "true", "True", "YES", "yes")

        try:
            cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'amap_config.json')
            if os.path.exists(cfg_path):
                with open(cfg_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                if env_force_direct is None:
                    self.force_direct_amap = bool(config.get("force_direct_amap", self.force_direct_amap))
                if env_force_no_proxy is None:
                    self.force_no_proxy = bool(config.get("force_no_proxy", self.force_no_proxy))
                if not self.amap_ip_override:
                    self.amap_ip_override = config.get("amap_ip_override")
        except Exception:
            pass

    def _get_json_with_retry(self, url, params, retries=3, timeout=10, headers=None):
        """GET请求（带重试，禁用代理）"""
        last_exc = None
        proxy_modes = [None]
        if self.force_no_proxy:
            proxy_modes = [{"http": None, "https": None}, None]
        for _ in range(max(1, retries)):
            for proxies in proxy_modes:
                try:
                    resp = requests.get(url, params=params, timeout=timeout, headers=headers, proxies=proxies)
                    if resp.status_code != 200:
                        raise Exception(f"HTTP错误: {resp.status_code}")
                    return resp.json()
                except Exception as exc:
                    last_exc = exc
                    time.sleep(0.3)
                    if url.startswith("https://"):
                        try:
                            http_url = "http://" + url.split("https://", 1)[-1]
                            resp = requests.get(http_url, params=params, timeout=timeout, headers=headers, proxies=proxies)
                            if resp.status_code != 200:
                                raise Exception(f"HTTP错误: {resp.status_code}")
                            return resp.json()
                        except Exception as exc2:
                            last_exc = exc2
                            time.sleep(0.3)
        raise Exception(str(last_exc) if last_exc else "未知错误")

    def get_area_info_simple(self, lng, lat):
        """简化区域信息（与process_user_file_fixed一致）"""
        try:
            amap_key = self.get_amap_key()
            regeo_url, regeo_headers = self._amap_endpoint("/v3/geocode/regeo")
            params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "base",
                "output": "json"
            }
            data = self._get_json_with_retry(regeo_url, params, timeout=10, headers=regeo_headers)
            if data.get("status") != "1":
                return f"API错误: {data.get('info', '未知错误')}"
            regeocode = data.get("regeocode", {})
            formatted_addr = regeocode.get("formatted_address", "")
            address_component = regeocode.get("addressComponent", {})
            poi_count = self._get_poi_density(lng, lat, amap_key)
            return self._classify_area(
                {"regeocode": {"formatted_address": formatted_addr, "addressComponent": address_component}},
                poi_count
            )
        except Exception as e:
            return f"错误: {repr(e)}"

    def get_features_simple(self, lng, lat):
        """简化地理特征（与process_user_file_fixed一致）"""
        try:
            amap_key = self.get_amap_key()
            regeo_url, regeo_headers = self._amap_endpoint("/v3/geocode/regeo")
            params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "base",
                "output": "json"
            }
            data = self._get_json_with_retry(regeo_url, params, timeout=10, headers=regeo_headers)
            if data.get("status") != "1":
                return f"API错误: {data.get('info', '未知错误')}"
            addr = data.get("regeocode", {}).get("formatted_address", "")
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
            if any(k in addr for k in ['高速公路', '高速路', '高速']):
                features.append('高速公路')
            if any(k in addr for k in ['铁路', '高铁', '轨道', '火车站']):
                features.append('铁路')
            if any(k in addr for k in ['商场', '广场', '车站', '机场', '学校', '医院', '市场', '景区', '体育馆', '公园']):
                features.append('人员密集处')
            if any(k in addr for k in ['路口', '交叉口', '十字路口']):
                features.append('城镇交叉路口')
            if any(k in addr for k in ['拐角', '转角', '街角', '巷口']):
                features.append('街巷拐角处')
            if any(k in addr for k in ['野外', '郊外', '田野', '荒野', '山野', '林场']):
                features.append('野外')
            if any(k in addr for k in ['厂区', '工厂', '厂房', '工业区', '工业园']):
                features.append('厂区')
            if any(k in addr for k in ['园区', '产业园', '科技园', '园']):
                features.append('园区')
            return ' | '.join(features) if features else '无特殊特征'
        except Exception as e:
            return f"错误: {repr(e)}"

    def get_amap_key(self):
        """获取高德API密钥，支持从配置文件或环境变量"""
        # 优先从环境变量获取
        amap_key = os.environ.get('AMAP_KEY')
        if amap_key:
            return amap_key
        
        # 其次尝试从配置文件获取
        try:
            config_candidates = []
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_candidates.append(os.path.join(script_dir, 'amap_config.json'))
            config_candidates.append(os.path.join(os.getcwd(), 'amap_config.json'))
            for cfg_path in config_candidates:
                if os.path.exists(cfg_path):
                    with open(cfg_path, 'r', encoding='utf-8') as f:
                        config = json.load(f)
                        # 兼容两种字段：amap_key 或 key
                        if 'amap_key' in config:
                            return config.get('amap_key')
                        if 'key' in config:
                            return config.get('key')
                        # 如果缺少字段，退回默认
                        return '1ba54ee0c70f50338fca9bb8b699b33c'
        except:
            pass
        
        # 默认密钥
        return '1ba54ee0c70f50338fca9bb8b699b33c'

    def analyze_area(self):
        """分析坐标点的区域属性"""
        coord_str = self.coord_var.get().strip()
        if not coord_str:
            self.messagebox.showwarning("警告", "请输入经纬度信息")
            return
        
        try:
            # 解析坐标
            parts = coord_str.split(',')
            if len(parts) != 2:
                self.messagebox.showerror("错误", "坐标格式错误，请使用 经,纬 格式")
                return
            
            lng, lat = float(parts[0].strip()), float(parts[1].strip())
            
            # 获取区域属性
            area_info = self.get_area_properties(lng, lat)
            self.area_result_var.set(area_info)
            
            # 获取地理特征
            geo_features = self.get_geo_features(lng, lat)
            features_str = self._format_features(geo_features)
            self.features_result_var.set(features_str)
            
        except ValueError:
            self.messagebox.showerror("错误", "坐标格式错误，请输入有效的数字")
        except Exception as e:
            self.messagebox.showerror("错误", f"分析失败: {str(e)}")
    def get_area_properties(self, lng, lat):
        """获取坐标的区域属性
        
        返回格式: "密集市区" | "市区" | "县城城区" | "乡镇" | "农村" | "郊区"
        """
        try:
            amap_key = self.get_amap_key()
            
            # 1. 使用逆地理编码获取地址信息
            regeo_url, regeo_headers = self._amap_endpoint("/v3/geocode/regeo")
            regeo_params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "all",
                "output": "json"
            }
            
            try:
                try:
                    regeo_data = self._get_json_with_retry(regeo_url, regeo_params, retries=2, timeout=5, headers=regeo_headers)
                except Exception as e:
                    return f"网络错误: {e}"
            except requests.exceptions.RequestException as e:
                return f"网络错误: {e}"
            
            if regeo_data['status'] != '1':
                return "查询失败"
            
            # 在API调用之间添加延迟，确保不超过3次/秒限制
            time.sleep(0.35)  # 约2.86次/秒，留有余量
            
            # 2. 获取周边POI统计信息
            poi_count = self._get_poi_density(lng, lat, amap_key)
            
            # 3. 分析地址结构判断区域属性
            area_type = self._classify_area(regeo_data, poi_count)
            
            # 4. 获取详细的行政区划信息
            address_component = regeo_data['regeocode'].get('addressComponent', {})
            province = address_component.get('province', '')
            city = address_component.get('city', '')
            district = address_component.get('district', '')
            township = address_component.get('township', '')
            
            # 构建返回信息
            location_info = f"{city}{district}"
            if township and township != district:
                location_info += township
            
            result = f"{area_type} (POI密度: {poi_count}/1km²) - {location_info}"
            return result
            
        except requests.Timeout:
            return "请求超时，请检查网络连接"
        except Exception as e:
            return f"分析出错: {str(e)}"

    def _get_poi_density(self, lng, lat, amap_key):
        """获取指定坐标周边的POI密度
        
        返回：1km范围内的POI数量
        """
        try:
            poi_url, poi_headers = self._amap_endpoint("/v3/place/around")
            poi_params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "radius": 1000,  # 1km范围
                "offset": 50,    # 最多返回50个结果
                "output": "json"
            }
            
            poi_data = self._get_json_with_retry(poi_url, poi_params, retries=2, timeout=5, headers=poi_headers)
            
            if poi_data['status'] == '1':
                # 返回实际的POI数量
                return len(poi_data.get('pois', []))
            return 0
            
        except:
            return 0

    def _classify_area(self, regeo_data, poi_count):
        """根据地址信息和POI密度分类区域属性
        
        返回：市区、城区、郊区、县城、农村
        """
        try:
            address_component = regeo_data['regeocode'].get('addressComponent', {})
            formatted_address = regeo_data['regeocode'].get('formatted_address', '')
            township = address_component.get('township', '')
            district = address_component.get('district', '')
            
            # 构建完整地址用于关键词匹配
            full_address = formatted_address + district + township
            
            # 规则1：优先基于地址关键词分类
            # 市区/城区关键词
            urban_keywords = ['市辖区', '城市', '城中', '中心', '街道', '居委会', '社区', '商圈', '商业区']
            # 郊区关键词
            suburban_keywords = ['开发区', '工业区', '高新区', '科技园', '产业园', '保税区']
            # 县城关键词
            county_keywords = ['县城', '县', '县级市', '自治县']
            # 农村关键词
            rural_keywords = ['村', '农村', '乡村', '屯', '寨', '庄', '大队']
            
            # 检查郊区关键词（优先级最高）
            for keyword in suburban_keywords:
                if keyword in full_address:
                    return "郊区"
            
            # 检查农村关键词
            for keyword in rural_keywords:
                if keyword in full_address:
                    return "农村"
            
            # 检查县城关键词
            for keyword in county_keywords:
                if keyword in full_address:
                    # 如果是县城，但POI密度很高，可能是县城城区
                    if poi_count >= 10:
                        return "县城"
                    else:
                        return "县城"  # 统一返回县城
            
            # 检查市区/城区关键词
            for keyword in urban_keywords:
                if keyword in full_address:
                    # 如果包含市区关键词，根据POI密度区分市区/城区
                    if poi_count >= 20:
                        return "市区"
                    else:
                        return "城区"
            
            # 规则2：没有明确关键词时，基于POI密度分类
            if poi_count >= 25:
                return "市区"
            elif poi_count >= 15:
                return "城区"
            elif poi_count >= 8:
                # 中等POI密度，可能是县城或郊区
                if '县' in full_address:
                    return "县城"
                else:
                    return "郊区"
            elif poi_count >= 3:
                # 低POI密度，可能是郊区或农村
                if '镇' in full_address or '乡' in full_address:
                    return "郊区"  # 乡镇归为郊区
                else:
                    return "农村"
            else:
                # 极低POI密度
                return "农村"
                
        except Exception as e:
            return f"分类失败: {str(e)}"

    def get_geo_features(self, lng, lat):
        """获取坐标的地理特征
        
        返回：路边状态、十字路口、高山、屋面等特征
        """
        try:
            amap_key = self.get_amap_key()
            features = {
                '路边': False,
                '十字路口': False,
                '高山': False,
                '屋面': False,
                '水体': False,
                '绿地': False,
                '高速公路': False,
                '铁路': False,
                '人员密集处': False,
                '城镇交叉路口': False,
                '街巷拐角处': False,
                '野外': False,
                '厂区': False,
                '园区': False
            }
            
            # 1. 调用逆地理编码获取周边POI和地物
            regeo_url, regeo_headers = self._amap_endpoint("/v3/geocode/regeo")
            regeo_params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "all",
                "output": "json"
            }
            
            try:
                try:
                    regeo_data = self._get_json_with_retry(regeo_url, regeo_params, retries=2, timeout=5, headers=regeo_headers)
                except Exception:
                    return features
            except requests.exceptions.RequestException:
                return features
            
            if regeo_data['status'] != '1':
                return features
            
            # 在API调用之间添加延迟，确保不超过3次/秒限制
            time.sleep(0.35)  # 约2.86次/秒，留有余量
            
            # 2. 分析地址特征识别路边
            formatted_address = regeo_data['regeocode'].get('formatted_address', '')
            address_component = regeo_data['regeocode'].get('addressComponent', {})
            
            # 路边识别
            road_keywords = ['路', '街', '道', '林荫道', '环路', '高速', '快速']
            for keyword in road_keywords:
                if keyword in formatted_address:
                    features['路边'] = True
                    break

            # 高速公路识别
            highway_keywords = ['高速公路', '高速路', '高速']
            if any(k in formatted_address for k in highway_keywords):
                features['高速公路'] = True

            # 铁路识别
            railway_keywords = ['铁路', '高铁', '轨道', '火车站']
            if any(k in formatted_address for k in railway_keywords):
                features['铁路'] = True

            # 人员密集处识别
            crowd_keywords = ['商场', '广场', '车站', '机场', '学校', '医院', '市场', '景区', '体育馆', '公园']
            if any(k in formatted_address for k in crowd_keywords):
                features['人员密集处'] = True

            # 城镇交叉路口识别
            intersection_keywords = ['路口', '交叉口', '十字路口']
            if any(k in formatted_address for k in intersection_keywords):
                features['城镇交叉路口'] = True

            # 街巷拐角处识别
            corner_keywords = ['拐角', '转角', '街角', '巷口']
            if any(k in formatted_address for k in corner_keywords):
                features['街巷拐角处'] = True

            # 野外识别
            wild_keywords = ['野外', '郊外', '田野', '荒野', '山野', '林场']
            if any(k in formatted_address for k in wild_keywords):
                features['野外'] = True

            # 厂区识别
            factory_keywords = ['厂区', '工厂', '厂房', '工业区', '工业园']
            if any(k in formatted_address for k in factory_keywords):
                features['厂区'] = True

            # 园区识别
            park_keywords = ['园区', '产业园', '科技园', '园']
            if any(k in formatted_address for k in park_keywords):
                features['园区'] = True
            
            # 3. 获取周边POI分析十字路口
            pois_near = self._get_nearby_pois(lng, lat, amap_key, 200)  # 200米范围
            
            # 统计周边不同方向的POI数量
            directions = self._analyze_poi_directions(lng, lat, pois_near)
            if len(directions) >= 3:  # 至少3个方向有POI
                features['十字路口'] = True
            
            # 4. 检测高山特征
            if self._is_high_altitude_area(formatted_address, address_component):
                features['高山'] = True
            
            # 5. 检测屋面特征（通过地址关键词）
            roof_keywords = ['楼顶', '屋顶', '天台', '屋面', '大厦顶', '高楼']
            for keyword in roof_keywords:
                if keyword in formatted_address:
                    features['屋面'] = True
                    break
            
            # 6. 检测水体特征
            water_keywords = ['河', '湖', '海', '江', '溪', '港', '滩', '水']
            for keyword in water_keywords:
                if keyword in formatted_address:
                    features['水体'] = True
                    break
            
            # 7. 检测绿地特征
            green_keywords = ['公园', '广场', '绿地', '花园', '林地', '草坪', '森林']
            for keyword in green_keywords:
                if keyword in formatted_address:
                    features['绿地'] = True
                    break
            
            return features
            
        except Exception as e:
            return {'错误': str(e)}

    def _get_nearby_pois(self, lng, lat, amap_key, radius=500):
        """获取周边POI列表"""
        try:
            poi_url, poi_headers = self._amap_endpoint("/v3/place/around")
            poi_params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "radius": radius,
                "offset": 50,
                "output": "json"
            }
            
            poi_data = self._get_json_with_retry(poi_url, poi_params, retries=2, timeout=5, headers=poi_headers)
            
            if poi_data['status'] == '1':
                return poi_data.get('pois', [])
            return []
        except:
            return []

    def _analyze_poi_directions(self, center_lng, center_lat, pois):
        """分析POI分布方向"""
        directions = set()
        
        for poi in pois:
            try:
                poi_lng = float(poi['location'].split(',')[0])
                poi_lat = float(poi['location'].split(',')[1])
                
                # 计算方向（简化版）
                lng_diff = poi_lng - center_lng
                lat_diff = poi_lat - center_lat
                
                if abs(lng_diff) < 0.0001 and abs(lat_diff) < 0.0001:
                    continue
                
                # 确定方向（8个方向）
                angle = __import__('math').atan2(lat_diff, lng_diff) * 180 / __import__('math').pi
                if angle < 0:
                    angle += 360
                
                if angle < 22.5 or angle >= 337.5:
                    directions.add('东')
                elif angle < 67.5:
                    directions.add('东北')
                elif angle < 112.5:
                    directions.add('北')
                elif angle < 157.5:
                    directions.add('西北')
                elif angle < 202.5:
                    directions.add('西')
                elif angle < 247.5:
                    directions.add('西南')
                elif angle < 292.5:
                    directions.add('南')
                else:
                    directions.add('东南')
            except:
                continue
        
        return directions

    def _is_high_altitude_area(self, formatted_address, address_component):
        """检测是否为高山地区"""
        high_altitude_keywords = ['山', '峰', '岭', '岳', '山区', '高原', '台地', '爬山']
        
        full_text = formatted_address + str(address_component)
        for keyword in high_altitude_keywords:
            if keyword in full_text:
                return True
        return False

    def _format_features(self, features):
        """格式化地理特征为字符串"""
        if isinstance(features, dict) and '错误' in features:
            return features['错误']
        
        result = []
        feature_names = {
            '路边': '🛣️ 路边',
            '十字路口': '✔️ 十字路口',
            '高山': '⛰️ 高山',
            '屋面': '🏠 屋面',
            '水体': '💧 水体',
            '绿地': '🌳 绿地',
            '高速公路': '🛣️ 高速公路',
            '铁路': '🚆 铁路',
            '人员密集处': '👥 人员密集处',
            '城镇交叉路口': '✔️ 城镇交叉路口',
            '街巷拐角处': '↩️ 街巷拐角处',
            '野外': '🌾 野外',
            '厂区': '🏭 厂区',
            '园区': '🏢 园区'
        }
        
        for key, label in feature_names.items():
            if features.get(key, False):
                result.append(label)
        
        if not result:
            return '无特殊特征'
        return ' | '.join(result)

    def _is_error_result(self, text):
        if not text:
            return True
        return any(k in text for k in ["网络错误", "HTTP错误", "API错误", "查询失败", "分析出错", "请求超时", "错误"])

    def _infer_features_from_text(self, text):
        if not text:
            return "无特殊特征"
        features = []
        if any(k in text for k in ['路', '街', '道', '大道', '公路']):
            features.append('路边')
        if any(k in text for k in ['公园', '广场', '绿地', '花园', '草坪']):
            features.append('绿地')
        if any(k in text for k in ['河', '湖', '海', '江', '溪', '水']):
            features.append('水体')
        if any(k in text for k in ['山', '峰', '岭', '丘']):
            features.append('山地')
        if any(k in text for k in ['楼', '大厦', '写字楼', '办公楼']):
            features.append('建筑')
        if any(k in text for k in ['高速公路', '高速路', '高速']):
            features.append('高速公路')
        if any(k in text for k in ['铁路', '高铁', '轨道', '火车站']):
            features.append('铁路')
        if any(k in text for k in ['商场', '广场', '车站', '机场', '学校', '医院', '市场', '景区', '体育馆', '公园']):
            features.append('人员密集处')
        if any(k in text for k in ['路口', '交叉口', '十字路口']):
            features.append('城镇交叉路口')
        if any(k in text for k in ['拐角', '转角', '街角', '巷口']):
            features.append('街巷拐角处')
        if any(k in text for k in ['野外', '郊外', '田野', '荒野', '山野', '林场']):
            features.append('野外')
        if any(k in text for k in ['厂区', '工厂', '厂房', '工业区', '工业园']):
            features.append('厂区')
        if any(k in text for k in ['园区', '产业园', '科技园', '园']):
            features.append('园区')
        return ' | '.join(features) if features else "无特殊特征"

    def _infer_area_from_text(self, text):
        if not text:
            return "未知"
        suburban_keywords = ['开发区', '工业区', '高新区', '科技园', '产业园', '保税区']
        rural_keywords = ['村', '农村', '乡村', '屯', '寨', '庄', '大队']
        county_keywords = ['县城', '县', '县级市', '自治县']
        urban_keywords = ['市辖区', '城市', '城中', '中心', '街道', '居委会', '社区', '商圈', '商业区']
        for keyword in suburban_keywords:
            if keyword in text:
                return "郊区"
        for keyword in rural_keywords:
            if keyword in text:
                return "农村"
        for keyword in county_keywords:
            if keyword in text:
                return "县城"
        for keyword in urban_keywords:
            if keyword in text:
                return "市区"
        return "城区"

    def _detect_csv_format(self, rows):
        """自动检测CSV文件格式
        
        支持格式：
        1. 用户特殊格式：名称,序号,经度,纬度,坐标字符串
        2. 地址格式：地址,... 
        3. WGS84坐标：名称,经度,纬度,...
        4. GCJ02坐标：名称,经度,纬度,...
        """
        if not rows or len(rows) < 2:
            return None
        
        # 检查表头
        first_row = rows[0]
        header_str = ''.join(first_row).lower()
        
        # 检测表头关键词
        has_coord_header = any(keyword in header_str for keyword in ['经度', '纬度', 'longitude', 'latitude'])
        has_name_header = any(keyword in header_str for keyword in ['名称', 'name', '地址', 'address'])
        
        # 如果有明确的坐标表头，优先识别为坐标格式
        if has_coord_header:
            coord_header = rows[0]
            lng_idx = None
            lat_idx = None
            for i, col in enumerate(coord_header):
                col_lower = str(col).lower()
                if '经度' in col_lower or 'longitude' in col_lower:
                    lng_idx = i
                if '纬度' in col_lower or 'latitude' in col_lower:
                    lat_idx = i
            # 检查数据行（跳过表头）
            if lng_idx is not None and lat_idx is not None and len(rows) > 1:
                data_rows = rows[1:min(5, len(rows))]
                for row in data_rows:
                    if len(row) > max(lng_idx, lat_idx):
                        try:
                            lng = float(row[lng_idx].strip())
                            lat = float(row[lat_idx].strip())
                            if 70 < lng < 140 and 10 < lat < 55:
                                return 'wgs84'
                        except (ValueError, IndexError):
                            pass
        
        # 取前几行数据进行分析（跳过可能存在的表头）
        sample_rows = rows[:min(5, len(rows))]
        
        # 检查是否包含表头
        has_header = False
        first_row = sample_rows[0]
        header_str = ''.join(first_row).lower()
        header_keywords = ['名称', '地址', '经度', '纬度', '备注', 'name', 'address', 'longitude', 'latitude']
        
        if any(keyword in header_str for keyword in header_keywords):
            has_header = True
            sample_rows = sample_rows[1:] if len(sample_rows) > 1 else []
        
        if not sample_rows:
            return None
        
        # 分析数据行格式
        for row in sample_rows:
            if not row or len(row) < 3:
                continue
            
            # 检查是否为用户特殊格式：名称,序号,经度,纬度,坐标字符串
            # 条件：至少有5列，第3、4列可能是数字，第5列包含逗号分隔的坐标
            if len(row) >= 5:
                # 检查第3、4列是否为数字
                try:
                    float(row[2].strip())
                    float(row[3].strip())
                    # 检查第5列是否包含逗号分隔的坐标
                    if ',' in row[4].strip():
                        return 'user_special'
                except (ValueError, IndexError):
                    pass
            
            # 检查是否为地址格式：如果包含中文地址关键词
            address_keywords = ['省', '市', '区', '县', '镇', '乡', '村', '路', '街', '道', '号']
            row_text = ''.join(row)
            chinese_chars = sum(1 for c in row_text if '\u4e00' <= c <= '\u9fff')
            # 如果包含中文地址关键词，且不是明显的坐标行
            if chinese_chars > 2:
                # 检查是否可能是坐标行（前几列为数字）
                try:
                    # 跳过可能的中文名称列
                    start_idx = 0
                    if has_name_header or any(keyword in row_text for keyword in address_keywords):
                        # 如果第一列包含地址关键词，可能第一列是名称，从第二列开始检查
                        start_idx = 1
                    
                    if len(row) > start_idx + 1:
                        lng = float(row[start_idx].strip())
                        lat = float(row[start_idx + 1].strip())
                        # 如果是有效坐标范围，则不是地址格式
                        if not (70 < lng < 140 and 10 < lat < 55):
                            return 'address'
                except (ValueError, IndexError):
                    # 如果不能解析为坐标，则可能是地址格式
                    return 'address'
            
            # 检查是否为坐标格式：前几列可能是数字
            try:
                # 尝试解析为WGS84坐标
                if len(row) >= 3:
                    # 尝试不同的列组合
                    for lng_idx, lat_idx in [(0, 1), (1, 2), (0, 2)]:
                        if lng_idx < len(row) and lat_idx < len(row):
                            lng = float(row[lng_idx].strip())
                            lat = float(row[lat_idx].strip())
                            # 检查坐标范围（中国大致范围）
                            if 70 < lng < 140 and 10 < lat < 55:
                                return 'wgs84'
            except (ValueError, IndexError):
                pass
            
            try:
                # 尝试解析为GCJ02坐标（范围与WGS84类似）
                if len(row) >= 3:
                    for lng_idx, lat_idx in [(0, 1), (1, 2), (0, 2)]:
                        if lng_idx < len(row) and lat_idx < len(row):
                            lng = float(row[lng_idx].strip())
                            lat = float(row[lat_idx].strip())
                            if 70 < lng < 140 and 10 < lat < 55:
                                return 'gcj02'
            except (ValueError, IndexError):
                pass
        
        # 默认返回WGS84格式
        return 'wgs84'

    def get_keywords(self, text):
        """提取关键词"""
        # 扩展特殊词列表
        special_words = [
            "有限公司", "股份公司", "商贸公司", "食品公司", 
            "科技公司", "制造公司", "酒店", "餐厅",
            "广场", "中心", "大厦", "商场", "超市"
        ]
        
        # 地址关键词
        location_words = ["半岛", "园区", "小区", "街道", "广场"]
        
        temp = text
        preserved = []
        
        # 1. 保存完整的特殊词
        for word in special_words + location_words:
            if word in text:
                preserved.append(word)
                # 只替换一次，避免过度分割
                temp = temp.replace(word, " ", 1)
        
        # 2. 处理地址部分
        address_parts = []
        patterns = [
            (r'(.+?省)', 'province'),
            (r'(.+?市)', 'city'),
            (r'(.+?区|.+?县)', 'district'),
            (r'(.+?路|.+?街|.+?道)', 'street')
        ]
        
        for pattern, key in patterns:
            match = re.search(pattern, temp)
            if match:
                address_parts.append(match.group(1))
                temp = temp.replace(match.group(1), ' ')
        
        # 3. 分词处理剩余文本
        segments = list(jieba.cut_for_search(temp))
        
        # 4. 组合所有关键词
        keywords = preserved + address_parts + [s.strip() for s in segments if len(s.strip()) > 1]
        
        # 5. 去重并保持顺序
        seen = set()
        return [x for x in keywords if not (x in seen or seen.add(x))]

    def fuzzy_search(self, query, address_list):
        """改进的模糊匹配"""
        # 获取查询关键词
        query_keywords = self.get_keywords(query)
        
        results = []
        for addr in address_list:
            addr_text = addr['formatted_address']
            addr_keywords = self.get_keywords(addr_text)
            
            # 计算匹配分数
            keyword_matches = 0
            matched_keywords = []
            
            for qk in query_keywords:
                best_match = 0
                for ak in addr_keywords:
                    sim = SequenceMatcher(None, qk, ak).ratio()
                    if sim > 0.8:  # 提高匹配阈值
                        best_match = max(best_match, sim)
                        if qk not in matched_keywords:
                            matched_keywords.append(qk)
                keyword_matches += best_match
            
            # 计算总体相似度
            if len(query_keywords) > 0:
                match_ratio = len(matched_keywords) / len(query_keywords)
                total_score = match_ratio * 0.7 + (keyword_matches / len(query_keywords)) * 0.3
                
                if total_score > 0.3:  # 降低阈值以显示更多结果
                    results.append({
                        'address': addr,
                        'score': total_score,
                        'matched_keywords': matched_keywords,
                        'total_matches': len(matched_keywords)
                    })
        
        # 按匹配度排序
        results.sort(key=lambda x: (x['total_matches'], x['score']), reverse=True)
        return [r['address'] for r in results]

    def _update_coords(self, location_data):
        """更新坐标显示"""
        try:
            location = location_data['location']
            gcj02_lng, gcj02_lat = map(float, location.split(','))
            wgs84_lng, wgs84_lat = self.transformer.gcj02_to_wgs84(gcj02_lng, gcj02_lat)
            
            # 更新显示
            self.wgs84_coords.set(f"{wgs84_lng}, {wgs84_lat}")
            self.gcj02_coords.set(f"{gcj02_lng}, {gcj02_lat}")
            
            # 显示完整地址
            formatted_address = location_data.get('formatted_address', '')
            if formatted_address:
                self.messagebox.showinfo("搜索结果", f"找到地址：\n{formatted_address}")
                
        except Exception as e:
            raise Exception(f"更新坐标失败: {str(e)}")

    def create_kml(self, lat, lng, address):
        """创建KML格式的位置标记"""
        kml = f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>{address}</name>
    <Point>
      <coordinates>{lng},{lat},0</coordinates>
    </Point>
  </Placemark>
</kml>"""
        return kml

    def copy_kml(self):
        """复制KML代码到剪贴板"""
        if not self.wgs84_coords.get():
            self.messagebox.showwarning("警告", "请先搜索位置")
            return
            
        try:
            lng, lat = map(float, self.wgs84_coords.get().split(','))
            address = self.search_var.get()
            kml = self.create_kml(lat, lng, address)
            
            # 复制到剪贴板
            self.root.clipboard_clear()
            self.root.clipboard_append(kml)
            self.messagebox.showinfo("成功", "KML代码已复制到剪贴板，可以在Google Earth中粘贴使用")
        except Exception as e:
            self.messagebox.showerror("错误", f"生成KML失败: {str(e)}")

    def open_in_maps(self, map_type):
        """在地图中打开位置"""
        if not self.wgs84_coords.get():
            self.messagebox.showwarning("警告", "请先搜索位置")
            return
            
        try:
            lng, lat = map(float, self.wgs84_coords.get().split(','))
            address = self.search_var.get()
            
            if map_type == "google_web":
                # 使用WGS84坐标打开网页版Google地图
                url = f"https://www.google.com/maps?q={lat},{lng}"
                webbrowser.open(url)
            elif map_type == "google_earth":
                # 创建临时KML文件并在Google Earth中打开
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml', mode='w', encoding='utf-8') as f:
                    kml = self.create_kml(lat, lng, address)
                    f.write(kml)
                    kml_path = f.name
                
                try:
                    # 尝试使用Google Earth Pro打开
                    os.startfile(kml_path)
                except Exception:
                    self.messagebox.showinfo("提示", 
                        "无法直接打开Google Earth。\n"
                        "1. 请先打开Google Earth\n"
                        "2. 选择'文件' -> '导入'\n"
                        "3. 选择以下文件：\n"
                             + kml_path)
            else:
                # 使用GCJ02坐标打开高德地图
                gcj02_lng, gcj02_lat = self.transformer.wgs84_to_gcj02(lng, lat)
                url = f"https://uri.amap.com/marker?position={gcj02_lng},{gcj02_lat}"
                webbrowser.open(url)
                
        except Exception as e:
            self.messagebox.showerror("错误", f"打开地图失败: {str(e)}")

    def _read_user_csv_file(self, filename):
        """读取CSV文件，支持多种编码"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
        for encoding in encodings:
            try:
                with open(filename, 'r', encoding=encoding) as f:
                    lines = f.readlines()
                data_rows = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    reader = csv.reader([line])
                    row = next(reader, [])
                    if row:
                        data_rows.append(row)
                return data_rows
            except UnicodeDecodeError:
                continue
            except Exception:
                continue
        raise ValueError("无法读取CSV文件，所有编码尝试都失败")

    def _parse_user_row(self, row):
        """解析用户CSV文件的行数据（兼容空首列与坐标串）"""
        if not row:
            return None, None, None
        name = None
        lng = None
        lat = None
        if len(row) >= 6:
            if row[0] == '' and row[1]:
                name = row[1].strip()
                try:
                    lng = float(row[3].strip()) if len(row) > 3 else None
                    lat = float(row[4].strip()) if len(row) > 4 else None
                except (ValueError, IndexError):
                    pass
        elif len(row) >= 5:
            name = row[0].strip()
            try:
                lng = float(row[2].strip()) if len(row) > 2 else None
                lat = float(row[3].strip()) if len(row) > 3 else None
            except (ValueError, IndexError):
                pass
        if (lng is None or lat is None) and len(row) >= 5:
            coord_str = row[-1].strip() if row[-1] else ''
            if ',' in coord_str:
                try:
                    parts = coord_str.split(',')
                    if len(parts) >= 2:
                        lng = float(parts[0].strip())
                        lat = float(parts[1].strip())
                except (ValueError, IndexError):
                    pass
        return name, lng, lat
    
    def import_csv(self):
        """导入CSV文件进行批量处理（完全复刻 process_user_file_fixed）"""
        try:
            filename = filedialog.askopenfilename(
                title="选择CSV文件",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            if not filename:
                return

            if hasattr(self, "log_text"):
                self.log_text.delete("1.0", "end")

            self.batch_results = []
            processed = 0
            failed = 0

            log_content = []
            self._log(f"开始处理CSV文件: {filename}", log_content)
            self._log(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", log_content)

            rows = self._read_user_csv_file(filename)
            total_rows = len(rows)
            if not rows:
                self.messagebox.showwarning("警告", "CSV文件为空")
                return
            self._log(f"总行数: {total_rows}", log_content)

            if hasattr(self, "batch_progress"):
                self.batch_progress["maximum"] = total_rows
                self.batch_progress["value"] = 0

            for i, row in enumerate(rows):
                if hasattr(self, "batch_progress"):
                    self.batch_progress["value"] = i + 1
                    self.root.update_idletasks()

                if not row:
                    continue

                # 跳过表头行
                if i == 0:
                    row_str = ''.join(row).lower()
                    if any(keyword in row_str for keyword in ['名称', '地址', '经度', '纬度', '备注']):
                        self._log(f"跳过表头行: {row}", log_content)
                        continue

                try:
                    name, lng, lat = self._parse_user_row(row)
                    if name is None:
                        name = f"行{i}"
                    self._log(f"处理第{i}行: {name}", log_content)

                    if isinstance(lng, str) and lng.strip().isdigit():
                        lng = float(lng)
                    if isinstance(lat, str) and lat.strip().isdigit():
                        lat = float(lat)

                    if lng is None or lat is None:
                        failed += 1
                        self._log("坐标解析失败", log_content)
                        continue

                    gcj_lng, gcj_lat = self.transformer.wgs84_to_gcj02(lng, lat)

                    area_info = self.get_area_info_simple(lng, lat)
                    features_info = self.get_features_simple(lng, lat)

                    status_text = '成功'
                    if self._is_error_result(area_info) or self._is_error_result(features_info):
                        status_text = '网络错误'
                        self._log(f"行{i}: 区域属性={area_info} | 地理特征={features_info}", log_content)

                    result = {
                        '名称': name,
                        '地址': name,
                        'WGS84经度': round(float(lng), 6),
                        'WGS84纬度': round(float(lat), 6),
                        'GCJ02经度': round(gcj_lng, 6),
                        'GCJ02纬度': round(gcj_lat, 6),
                        '区域属性': area_info,
                        '地理特征': features_info,
                        '状态': status_text,
                        '原始数据': str(row)
                    }

                    self.batch_results.append(result)
                    processed += 1
                    self._log(f"行{i}: 完成", log_content)

                    time.sleep(self.api_delay)

                except Exception as e:
                    failed += 1
                    self._log(f"行{i}: 处理失败 - {e}", log_content)

            log_filename = f"batch_processing_log_{int(time.time())}.txt"
            with open(log_filename, 'w', encoding='utf-8') as log_file:
                log_file.write('\n'.join(log_content))

            output_file = self._auto_save_batch_results(filename)

            if output_file:
                result_msg = (
                    f"成功处理: {processed}条数据\n处理失败: {failed}条数据\n\n"
                    f"结果已保存到: {output_file}\n"
                    f"日志已保存到: {log_filename}"
                )
            else:
                result_msg = f"成功处理: {processed}条数据\n处理失败: {failed}条数据\n\n日志已保存到: {log_filename}"
            self.messagebox.showinfo("处理完成", result_msg)

        except Exception as e:
            error_msg = f"导入失败: {str(e)}"
            self.messagebox.showerror("错误", error_msg)
            self._log(f"导入失败: {e}", None)
    
    def _ask_input_type(self):
        """弹出对话框询问输入类型"""
        from tkinter import simpledialog
        
        dialog = self.tk.Toplevel(self.root)
        dialog.title("选择数据格式")
        dialog.geometry("500x350")
        dialog.resizable(False, False)
        
        # 使dialog成为模态窗口
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 使用列表作为可变容器来避免类型推断问题
        result_container = [None]  # 使用列表，第一个元素存储结果
        
        # 标题
        title_label = self.ttk.Label(dialog, text="请选择CSV文件中的数据格式:", 
                                      font=('Microsoft YaHei', 12, 'bold'))
        title_label.pack(pady=15)
        
        # 选项框架
        frame = self.ttk.Frame(dialog)
        frame.pack(pady=10, padx=20, fill='both', expand=True)
        
        # 选项1: 地址
        def select_address():
            result_container[0] = 'address'
            dialog.destroy()
        
        btn1 = self.ttk.Button(frame, text="📍 地址格式\n\n格式：[名称/ID] [地址] [其他]\n示例：西二旗,北京市海淀区中关村,民居", 
                              command=select_address)
        btn1.pack(fill='x', pady=5)
        
        # 选项2: WGS84坐标
        def select_wgs84():
            result_container[0] = 'wgs84'
            dialog.destroy()
        
        btn2 = self.ttk.Button(frame, text="🧭 WGS84坐标（名称+坐标）\n\n格式：[名称/ID] [经度] [纬度] [其他]\n示例：西二旗,116.3974,39.9093,民居", 
                              command=select_wgs84)
        btn2.pack(fill='x', pady=5)
        
        # 选项3: GCJ02坐标
        def select_gcj02():
            result_container[0] = 'gcj02'
            dialog.destroy()
        
        btn3 = self.ttk.Button(frame, text="🗺️ GCJ02坐标（名称+坐标）\n\n格式：[名称/ID] [经度] [纬度] [其他]\n示例：西二旗,116.40,39.91,民居", 
                              command=select_gcj02)
        btn3.pack(fill='x', pady=5)
        
        # 取消按钮
        def cancel():
            dialog.destroy()
        
        btn_cancel = self.ttk.Button(frame, text="❌ 取消", command=cancel)
        btn_cancel.pack(fill='x', pady=5)
        
        # 说明信息
        info_label = self.ttk.Label(dialog, text="💡 第一列为名称/标识，坐标格式第2、3列为经纬度 | GPS通常是WGS84，高德API返回GCJ02", 
                                    font=('Microsoft YaHei', 8), foreground='gray')
        info_label.pack(pady=10)
        
        # 等待对话框关闭
        dialog.wait_window()
        
        return result_container[0]
            
    def export_results(self):
        """导出处理结果"""
        if not self.batch_results:
            self.messagebox.showwarning("警告", "没有可导出的结果")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                title="保存结果",
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
            )
            if not filename:
                return
                
            df = pd.DataFrame(self.batch_results)
            if filename.endswith('.xlsx'):
                df.to_excel(filename, index=False)
            else:
                df.to_csv(filename, index=False)
                
            self.messagebox.showinfo("成功", f"结果已保存至:\n{filename}")
            
        except Exception as e:
            self.messagebox.showerror("错误", f"导出失败: {str(e)}")
            
    def create_batch_kml(self):
        """生成批量KML文件"""
        if not self.batch_results:
            self.messagebox.showwarning("警告", "没有可导出的数据")
            return
            
        try:
            filename = filedialog.asksaveasfilename(
                title="保存KML文件",
                defaultextension=".kml",
                filetypes=[("KML文件", "*.kml")]
            )
            if not filename:
                return
                
            kml = ['<?xml version="1.0" encoding="UTF-8"?>',
                   '<kml xmlns="http://www.opengis.net/kml/2.2">',
                   '<Document>']
                   
            for result in self.batch_results:
                if '状态' in result and result['状态'] == '成功':
                    name = result.get("地址") or result.get("名称") or "点位"
                    kml.extend([
                        '  <Placemark>',
                        f'    <name>{name}</name>',
                        '    <Point>',
                        f'      <coordinates>{result["WGS84经度"]},{result["WGS84纬度"]},0</coordinates>',
                        '    </Point>',
                        '  </Placemark>'
                    ])
                    
            kml.extend(['</Document>', '</kml>'])
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('\n'.join(kml))
                
            self.messagebox.showinfo("成功", 
                f"KML文件已保存至:\n{filename}\n"
                "可以直接在Google Earth中打开")
                
        except Exception as e:
            self.messagebox.showerror("错误", f"生成KML失败: {str(e)}")

    def open_batch_in_google_maps(self):
        """批量在Google地图中打开（逐点新标签页）"""
        if not self.batch_results:
            self.messagebox.showwarning("警告", "没有可用的批量结果")
            return
        points = [r for r in self.batch_results if r.get('状态') == '成功']
        if not points:
            self.messagebox.showwarning("警告", "没有成功的点位可打开")
            return
        if len(points) > 20:
            if not self.messagebox.askyesno("提示", f"将打开 {len(points)} 个标签页，是否继续？"):
                return
        for result in points:
            try:
                lng = result["WGS84经度"]
                lat = result["WGS84纬度"]
                url = f"https://www.google.com/maps?q={lat},{lng}"
                webbrowser.open(url)
                time.sleep(0.2)
            except Exception:
                continue

    def open_batch_in_amap(self):
        """批量在高德地图中打开（逐点新标签页）"""
        if not self.batch_results:
            self.messagebox.showwarning("警告", "没有可用的批量结果")
            return
        points = [r for r in self.batch_results if r.get('状态') == '成功']
        if not points:
            self.messagebox.showwarning("警告", "没有成功的点位可打开")
            return
        if len(points) > 20:
            if not self.messagebox.askyesno("提示", f"将打开 {len(points)} 个标签页，是否继续？"):
                return
        for result in points:
            try:
                lng = result["GCJ02经度"]
                lat = result["GCJ02纬度"]
                url = f"https://uri.amap.com/marker?position={lng},{lat}"
                webbrowser.open(url)
                time.sleep(0.2)
            except Exception:
                continue

    def _auto_save_batch_results(self, source_filename):
        """自动保存批量结果到同目录"""
        if not self.batch_results:
            return None
        output_dir = os.path.dirname(source_filename)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        base_name = f"batch_results_{timestamp}"
        candidates = [
            os.path.join(output_dir, f"{base_name}.xlsx"),
            os.path.join(output_dir, f"{base_name}.csv")
        ]
        for idx in range(5):
            for candidate in candidates:
                target = candidate if idx == 0 else candidate.replace(base_name, f"{base_name}_{idx}")
                try:
                    df = pd.DataFrame(self.batch_results)
                    df.columns = [
                        (str(c).strip() if str(c).strip() not in ("", "None", "nan") else f"列{i+1}")
                        for i, c in enumerate(df.columns)
                    ]
                    preferred = [
                        "名称", "地址", "WGS84经度", "WGS84纬度", "GCJ02经度", "GCJ02纬度",
                        "区域属性", "地理特征", "状态", "备注", "原始数据"
                    ]
                    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
                    df = df[cols]
                    if target.endswith(".xlsx"):
                        df.to_excel(target, index=False)
                    else:
                        df.to_csv(target, index=False, encoding="utf-8-sig")
                    return target
                except Exception:
                    continue
        return None
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    import os
    import sys
    
    # 设置环境变量加速启动
    os.environ['PYTHONOPTIMIZE'] = '1'
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    
    # 禁用不必要的功能
    is_frozen = getattr(sys, 'frozen', False)
    
    app = GoogleMapsTools()
    app.run()
