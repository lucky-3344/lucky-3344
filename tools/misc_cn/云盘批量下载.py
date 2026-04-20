from pywinauto import Desktop
from pywinauto.application import Application
import pandas as pd
import time
import os
import subprocess
from datetime import datetime
import pyautogui
import pyperclip
import logging
from pathlib import Path

class MobileCloudDownloader:
    def __init__(self, fast_mode=False):
        self.fast_mode = fast_mode
        self.main_window = None
        self.download_dir = r"C:\Users\lucky\Desktop\移动云盘批量下载"
        self.excel_path = r"C:\Users\lucky\Desktop\云盘待搜索文件名.xlsx"
        self.not_found = []
        # 云盘内目录路径（从根目录开始的层级列表）
        # 例如: ["工作文件", "2024项目", "图纸"] 表示进入 工作文件/2024项目/图纸
        self.cloud_folder_path = []  # 空列表表示在根目录搜索
        # 记录搜索框位置（第一次搜索时记录，后续复用）
        self.search_box_pos = None
        # 配置文件路径（保存搜索框位置）
        self.config_file = Path(r"C:\Users\lucky\projects\my_project\cloud_downloader\search_box_pos.txt")
        # 更新资源目录路径
        self.resource_path = Path(r"C:\Users\lucky\projects\my_project\cloud_downloader\resources\images")
        self.download_btn_path = self.resource_path / "download_btn.png"
        self.confirm_btn_path = self.resource_path / "confirm_btn.png"
        # 调试截图目录
        self.debug_dir = Path(r"C:\Users\lucky\projects\my_project\cloud_downloader\debug")
        self.debug_dir.mkdir(parents=True, exist_ok=True)
        
        # 设置日志 - 只添加一次 handler，避免重复输出
        log_file = self.debug_dir / f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        root_logger = logging.getLogger()
        # 清空所有 handler，防止重复
        for h in root_logger.handlers[:]:
            root_logger.removeHandler(h)
        logging.basicConfig(
            filename=str(log_file),
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            encoding='utf-8'
        )
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
        root_logger.addHandler(console_handler)
        print(f"日志文件: {log_file}")

    def take_debug_screenshot(self, name):
        """保存调试截图"""
        try:
            timestamp = datetime.now().strftime('%H%M%S')
            screenshot_path = self.debug_dir / f"{timestamp}_{name}.png"
            pyautogui.screenshot(str(screenshot_path))
            logging.debug(f"截图已保存: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            logging.warning(f"截图失败: {str(e)}")
            return None

    def log_step(self, step_name, details=""):
        """记录操作步骤"""
        mouse_pos = pyautogui.position()
        msg = f"[步骤] {step_name}"
        if details:
            msg += f" | {details}"
        msg += f" | 鼠标位置: {mouse_pos}"
        logging.info(msg)
        print(f"  → {step_name}")
    
    def save_search_box_pos(self, pos):
        """保存搜索框位置到配置文件"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                f.write(f"{pos[0]},{pos[1]}")
            logging.info(f"搜索框位置已保存: {pos}")
        except Exception as e:
            logging.warning(f"保存搜索框位置失败: {e}")
    
    def load_search_box_pos(self):
        """从配置文件加载搜索框位置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    x, y = f.read().strip().split(',')
                    return (int(x), int(y))
        except Exception as e:
            logging.warning(f"加载搜索框位置失败: {e}")
        return None
    
    def get_existing_files(self):
        """获取下载目录中已存在的文件列表"""
        try:
            if os.path.exists(self.download_dir):
                return os.listdir(self.download_dir)
            return []
        except Exception as e:
            logging.warning(f"获取已存在文件列表失败: {e}")
            return []
    
    def verify_download(self, filename, files_before, timeout=60):
        """验证文件是否下载成功
        
        Args:
            filename: 搜索的文件名
            files_before: 下载前的文件列表
            timeout: 超时时间（秒）
        
        Returns:
            (success, downloaded_name): 是否成功，下载的文件名
        """
        self.log_step("验证下载", f"文件名: {filename}, 超时: {timeout}秒")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                current_files = self.get_existing_files()
                # 查找新增的文件
                new_files = [f for f in current_files if f not in files_before]
                
                if new_files:
                    # 检查是否有匹配的文件（忽略扩展名）
                    for new_file in new_files:
                        # 移除扩展名进行比较
                        new_name = os.path.splitext(new_file)[0]
                        if filename.lower() in new_name.lower():
                            self.log_step("下载验证成功", f"新文件: {new_file}")
                            return True, new_file
                    
                    # 如果有新文件但不匹配，可能是正在下载中
                    # 检查是否有 .downloading 或临时文件
                    downloading = any('.downloading' in f or '.tmp' in f or '.part' in f for f in new_files)
                    if downloading:
                        self.log_step("下载进行中", "检测到临时文件")
                        time.sleep(2)
                        continue
                    
                    # 如果有新文件但都不匹配，返回第一个（可能是重命名的文件）
                    if new_files:
                        self.log_step("下载完成", f"新文件: {new_files[0]}")
                        return True, new_files[0]
                
                # 检查是否有正在下载的临时文件
                for f in current_files:
                    if '.downloading' in f or '.tmp' in f or '.part' in f:
                        self.log_step("下载进行中", f"临时文件: {f}")
                        time.sleep(2)
                        break
                else:
                    time.sleep(1)
                    
            except Exception as e:
                logging.warning(f"验证下载时出错: {e}")
                time.sleep(1)
        
        self.log_step("下载验证超时", f"等待了 {timeout} 秒")
        return False, None
    
    def find_by_icon(self, file_extension):
        """使用图标模板识别文件
        
        Args:
            file_extension: 文件扩展名，如 ".dwg" 或 ".dxf"
        
        Returns:
            匹配的文件项，或 None
        """
        try:
            # 图标文件路径（相对于脚本目录）
            icon_files = {
                ".vsd": "cloud_downloader/resources/images/vsd_icon.png",
                ".vsdx": "cloud_downloader/resources/images/vsd_icon.png",
                ".dwg": "cloud_downloader/resources/images/cad_icon.png",
                ".pdf": "cloud_downloader/resources/images/pdf_icon.png",
                ".doc": "cloud_downloader/resources/images/word_icon.png",
                ".docx": "cloud_downloader/resources/images/word_icon.png",
                "folder": "cloud_downloader/resources/images/folder_icon.png",
            }
            
            icon_path = icon_files.get(file_extension.lower())
            if not icon_path:
                return None
            
            # 获取完整路径
            script_dir = os.path.dirname(os.path.abspath(__file__))
            full_icon_path = os.path.join(script_dir, icon_path)
            
            if not os.path.exists(full_icon_path):
                logging.warning(f"图标文件不存在: {full_icon_path}")
                return None
            
            self.log_step("使用图标识别", f"文件类型: {file_extension}, 图标: {icon_path}")
            
            # 获取窗口位置，限制搜索区域
            try:
                if self.main_window is not None:
                    win_rect = self.main_window.rectangle()
                    win_left = win_rect.left
                    win_top = win_rect.top
                    win_width = win_rect.width()
                    win_height = win_rect.height()
                    # 只在搜索结果区域查找（窗口中部）
                    search_region = (win_left + 50, win_top + 200, win_width - 100, win_height - 300)
                else:
                    search_region = None
            except Exception:
                search_region = None  # 如果获取窗口失败，全屏搜索
            
            # VSD和PDF图标相似，都使用更高精度
            confidence = 0.9 if file_extension.lower() in [".pdf", ".vsd", ".vsdx"] else 0.8
            
            # 在屏幕上查找所有匹配的图标
            if search_region:
                locations = list(pyautogui.locateAllOnScreen(full_icon_path, confidence=confidence, region=search_region))
            else:
                locations = list(pyautogui.locateAllOnScreen(full_icon_path, confidence=confidence))
            
            if locations:
                self.log_step("找到图标", f"数量: {len(locations)}")
                
                # 如果找到太多匹配（可能是误判），添加额外过滤
                if len(locations) > 10:
                    # 过滤掉太靠上或太靠下的（界面装饰元素）
                    try:
                        if self.main_window is not None:
                            win_rect = self.main_window.rectangle()
                            win_top = win_rect.top
                            win_height = win_rect.height()
                            # 只保留在窗口中间70%区域的图标
                            middle_start = win_top + int(win_height * 0.2)
                            middle_end = win_top + int(win_height * 0.9)
                            filtered = [loc for loc in locations if middle_start <= loc.top <= middle_end]
                            if filtered:
                                locations = filtered
                                self.log_step("过滤后的图标", f"数量: {len(locations)}")
                    except Exception:
                        pass
                
                # 选择最靠上的图标（第一个搜索结果）
                locations.sort(key=lambda loc: loc.top)
                
                # 【颜色二次验证】防止图标混淆
                # 定义各文件类型的颜色特征
                color_checks = {
                    ".vsd": {"name": "紫色", "check": lambda r,g,b: 120 <= r <= 190 and b >= 200 and b > g + 60},
                    ".vsdx": {"name": "紫色", "check": lambda r,g,b: 120 <= r <= 190 and b >= 200 and b > g + 60},
                    ".pdf": {"name": "红色", "check": lambda r,g,b: r >= 150 and g < 120 and b < 120 and r > g + 50},
                    ".dwg": {"name": "灰色", "check": lambda r,g,b: 80 <= r <= 220 and abs(r-g) < 40 and abs(r-b) < 40},
                    ".doc": {"name": "蓝色", "check": lambda r,g,b: b >= 150 and b > r + 50},
                    ".docx": {"name": "蓝色", "check": lambda r,g,b: b >= 150 and b > r + 50},
                    "folder": {"name": "黄色", "check": lambda r,g,b: r >= 220 and 140 <= g <= 230 and b <= 140},
                }
                
                verified_icon = None
                for icon in locations:
                    icon_x = icon.left + icon.width // 2
                    icon_y = icon.top + icon.height // 2
                    
                    # 检查图标位置的颜色
                    try:
                        pixel = pyautogui.pixel(icon_x, icon_y)
                        r, g, b = pixel[:3]
                        
                        # 如果有颜色检查器，验证颜色
                        if file_extension.lower() in color_checks:
                            color_check = color_checks[file_extension.lower()]
                            if color_check["check"](r, g, b):
                                self.log_step("颜色验证通过", f"{color_check['name']} RGB=({r},{g},{b})")
                                verified_icon = icon
                                break
                            else:
                                logging.debug(f"颜色验证失败: 期望{color_check['name']}, 实际RGB=({r},{g},{b})")
                        else:
                            # 没有颜色验证器，直接使用
                            verified_icon = icon
                            break
                    except:
                        pass
                
                # 如果没有通过验证的图标，使用第一个（保持向后兼容）
                if verified_icon is None:
                    self.log_step("警告：颜色验证都失败，使用第一个图标")
                    verified_icon = locations[0]
                
                first_icon = verified_icon
                
                # 点击图标右侧的文件名区域
                click_x = first_icon.left + first_icon.width + 50
                click_y = first_icon.top + first_icon.height // 2
                
                self.log_step("找到文件(图标)", f"坐标: ({click_x}, {click_y})")
                
                class FakeFileItem:
                    def __init__(self, x, y):
                        self.x = x
                        self.y = y
                    def click_input(self, button='left'):
                        pyautogui.click(self.x, self.y, button=button)
                    def double_click_input(self):
                        pyautogui.doubleClick(self.x, self.y)
                    def window_text(self):
                        return f"{file_extension}文件"
                
                return FakeFileItem(click_x, click_y)
            else:
                self.log_step("未找到匹配图标")
                return None
                
        except Exception as e:
            logging.warning(f"图标识别失败: {str(e)}")
            return None

    def connect_to_client(self):
        """连接到移动云盘客户端"""
        client_path = r"C:\yidongyunpan\mCloud\mCloud.exe"
        try:
            # 尝试连接到已运行的云盘客户端
            self.app = Application(backend='uia').connect(
                path=client_path,
                timeout=5
            )
            self.main_window = self.app.window(title_re='.*移动云.*')
            self.main_window.wait('exists ready', timeout=8)
            print("已成功连接到移动云盘客户端")
            logging.info("已连接到云盘客户端")
            return True
        except Exception as e:
            logging.warning(f"首次连接云盘客户端失败: {str(e)}")

            if not os.path.exists(client_path):
                print(f"连接云盘客户端失败: {str(e)}")
                logging.error(f"客户端路径不存在: {client_path}")
                print("请检查客户端是否已安装，或修正脚本中的客户端路径")
                return False

            print("未检测到正在运行的客户端，正在尝试自动启动...")
            logging.info("尝试自动启动移动云盘客户端")

            try:
                subprocess.Popen([client_path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as start_err:
                print(f"自动启动客户端失败: {start_err}")
                logging.error(f"自动启动客户端失败: {start_err}")
                return False

            for _ in range(20):
                time.sleep(1)
                try:
                    self.app = Application(backend='uia').connect(path=client_path, timeout=2)
                    self.main_window = self.app.window(title_re='.*移动云.*')
                    self.main_window.wait('exists ready', timeout=5)
                    print("已自动启动并连接到移动云盘客户端")
                    logging.info("自动启动后连接成功")
                    return True
                except Exception:
                    continue

            print("连接云盘客户端失败：请确认客户端已登录并处于可操作界面")
            logging.error("自动启动后仍无法连接云盘客户端")
            return False

    def navigate_to_folder(self):
        """导航到指定的云盘目录"""
        if not self.cloud_folder_path:
            print("未设置云盘目录路径，在当前位置搜索")
            return True
        
        try:
            print(f"正在导航到云盘目录: {'/'.join(self.cloud_folder_path)}")
            
            for folder_name in self.cloud_folder_path:
                print(f"  进入文件夹: {folder_name}")
                
                # 方式1: 尝试在文件列表中找到文件夹并双击
                folder_found = False
                try:
                    # 等待列表加载
                    time.sleep(1)
                    
                    # 尝试找到List或DataGrid控件
                    file_list = None
                    if self.main_window is not None:
                        for ctrl_type in ["List", "DataGrid", "Table"]:
                            try:
                                file_list = self.main_window.child_window(auto_id="file_list", control_type=ctrl_type)
                                if file_list.exists():
                                    break
                            except Exception:
                                continue
                    
                    if file_list and file_list.exists():
                        # 在列表中查找文件夹
                        for item in file_list.children():
                            try:
                                item_name = item.window_text()
                                if folder_name in item_name:
                                    item.double_click_input()
                                    folder_found = True
                                    break
                            except Exception:
                                continue
                except Exception as e:
                    logging.debug(f"方式1查找文件夹失败: {e}")
                
                # 方式2: 使用搜索功能
                if not folder_found:
                    try:
                        # 点击搜索框
                        if self.search_box_pos:
                            pyautogui.click(self.search_box_pos[0], self.search_box_pos[1])
                        else:
                            # 尝试使用快捷键 Ctrl+F
                            pyautogui.hotkey('ctrl', 'f')
                        time.sleep(0.5)
                        
                        # 输入文件夹名
                        pyperclip.copy(folder_name)
                        pyautogui.hotkey('ctrl', 'v')
                        time.sleep(1)
                        pyautogui.press('enter')
                        time.sleep(2)
                        
                        # 查找文件夹图标
                        folder_item = self.find_by_icon("folder")
                        if folder_item:
                            folder_item.double_click_input()
                            folder_found = True
                    except Exception as e:
                        logging.debug(f"方式2查找文件夹失败: {e}")
                
                if not folder_found:
                    print(f"  警告: 未找到文件夹 '{folder_name}'")
                    logging.warning(f"未找到文件夹: {folder_name}")
                    return False
                
                time.sleep(1)
            
            print("已成功导航到目标目录")
            logging.info("导航到目标目录成功")
            return True
            
        except Exception as e:
            logging.error(f"导航到目录失败: {str(e)}")
            print(f"导航到目录失败: {str(e)}")
            return False

    def dismiss_interfering_dialogs(self):
        """清理干扰弹窗"""
        closed_count = 0
        try:
            # 尝试按 ESC 关闭可能的弹窗
            for _ in range(3):
                pyautogui.press('esc')
                time.sleep(0.3)
                closed_count += 1
        except Exception as e:
            logging.debug(f"清理弹窗失败: {e}")

        if closed_count:
            self.log_step("已清理干扰弹窗", f"数量: {closed_count}")

    def search_file(self, filename):
        """搜索文件 - 在当前鼠标位置直接输入"""
        try:
            self.dismiss_interfering_dialogs()
            self.log_step("开始搜索", f"文件名: {filename}")
            
            # 如果已记录搜索框位置，直接移动
            if self.search_box_pos:
                pyautogui.moveTo(self.search_box_pos[0], self.search_box_pos[1], duration=0.3)
                time.sleep(0.2)
                self.log_step("移动到搜索框", str(self.search_box_pos))
            else:
                # 第一次搜索，尝试从配置文件加载
                saved_pos = self.load_search_box_pos()
                if saved_pos:
                    print(f"\n检测到上次保存的搜索框位置: ({saved_pos[0]}, {saved_pos[1]})")
                    use_saved = input("是否使用？(Y/n，默认Y): ").strip().lower()
                    if use_saved != 'n':
                        self.search_box_pos = saved_pos
                        self.log_step("使用已保存位置", str(self.search_box_pos))
                        pyautogui.moveTo(self.search_box_pos[0], self.search_box_pos[1], duration=0.3)
                        time.sleep(0.2)
                    else:
                        # 用户选择重新定位
                        print("\n★★★ 请将鼠标移动到搜索输入框内，然后按回车继续 ★★★")
                        input("准备好后按回车...")
                        current_pos = pyautogui.position()
                        self.search_box_pos = (current_pos.x, current_pos.y)
                        self.save_search_box_pos(self.search_box_pos)
                        self.log_step("记录新搜索框位置", str(self.search_box_pos))
                else:
                    # 首次使用，提示用户定位
                    print("\n★★★ 请将鼠标移动到搜索输入框内，然后按回车继续 ★★★")
                    input("准备好后按回车...")
                    current_pos = pyautogui.position()
                    self.search_box_pos = (current_pos.x, current_pos.y)
                    self.save_search_box_pos(self.search_box_pos)
                    self.log_step("记录搜索框位置", str(self.search_box_pos))
            
            # 点击当前位置激活输入框
            pyautogui.click()
            time.sleep(0.5)
            
            # 三击全选，清空原有内容
            pyautogui.click(clicks=3)
            time.sleep(0.3)
            
            # 先复制到剪贴板
            pyperclip.copy(filename)
            time.sleep(0.5)  # 等待剪贴板就绪
            
            # 确认剪贴板内容
            clipboard_content = pyperclip.paste()
            self.log_step("剪贴板内容", f"'{clipboard_content}'")
            
            # 粘贴
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1.0)  # 等待粘贴完成
            
            # 截图确认输入内容
            self.take_debug_screenshot("after_paste")
            
            # 按回车搜索
            pyautogui.press('enter')
            time.sleep(3)  # 等待搜索结果
            
            print(f"已搜索: {filename}")
            logging.info(f"搜索完成: {filename}")
            return True
                
        except Exception as e:
            logging.error(f"搜索文件失败 {filename}: {str(e)}")
            print(f"搜索失败: {str(e)}")
            return False

    def get_file_list(self, target_filename=None, file_extension=".vsd"):
        """获取文件列表 - 支持自动滚动查找文件图标
        Args:
            target_filename: 要匹配的文件名关键词（模糊匹配）
            file_extension: 要匹配的文件扩展名，如 ".vsd" 或 ".vsdx"
        Returns:
            匹配的文件项，或 None
        """
        self.log_step("开始获取文件列表", f"目标扩展名: {file_extension}")
        time.sleep(2)  # 等待搜索结果加载
        # 截图记录搜索结果状态
        self.take_debug_screenshot("search_result")

        # 自动滚动查找（滚轮前先移动鼠标到文件列表区域，最多3次，每次缓冲1秒）
        max_scroll = 3
        scroll_count = 0
        icon_result = None
        # 获取窗口中部区域坐标
        try:
            if self.main_window is not None:
                win_rect = self.main_window.rectangle()
                list_x = win_rect.left + win_rect.width() // 2
                list_y = win_rect.top + win_rect.height() // 2
            else:
                raise Exception("main_window is None")
        except Exception:
            # 兜底用屏幕中心
            screen_width, screen_height = pyautogui.size()
            list_x = screen_width // 2
            list_y = screen_height // 2

        while scroll_count < max_scroll:
            # 1. 图标识别
            icon_result = self.find_by_icon(file_extension)
            if icon_result:
                if scroll_count > 0:
                    self.log_step("滚动后找到图标", f"滚动次数: {scroll_count}")
                return icon_result
            # 2. 颜色识别
            color_result = self._find_by_color(file_extension)
            if color_result:
                self.log_step("滚动后颜色识别成功", f"滚动次数: {scroll_count}")
                return color_result
            self.log_step("未找到图标，鼠标移动到文件列表并滚轮下滑一页", f"第{scroll_count+1}次")
            # 鼠标先移动到文件列表区域
            pyautogui.moveTo(list_x, list_y, duration=0.2)
            time.sleep(0.2)
            pyautogui.scroll(-120)
            time.sleep(3.0)
            # 滚轮后再次比对
            icon_result = self.find_by_icon(file_extension)
            if icon_result:
                self.log_step("滚轮后立即找到图标", f"滚动次数: {scroll_count+1}")
                return icon_result
            color_result = self._find_by_color(file_extension)
            if color_result:
                self.log_step("滚轮后颜色识别成功", f"滚动次数: {scroll_count+1}")
                return color_result
            # 再用 pagedown 兜底
            pyautogui.press('pagedown')
            time.sleep(3.0)
            # pagedown后再次比对
            icon_result = self.find_by_icon(file_extension)
            if icon_result:
                self.log_step("pagedown后立即找到图标", f"滚动次数: {scroll_count+1}")
                return icon_result
            color_result = self._find_by_color(file_extension)
            if color_result:
                self.log_step("pagedown后颜色识别成功", f"滚动次数: {scroll_count+1}")
                return color_result
            scroll_count += 1
        return None

    def _find_by_color(self, file_extension):
        """单独暴露颜色识别逻辑，供滚动循环调用"""
        try:
            screen_width, screen_height = pyautogui.size()
            screenshot = pyautogui.screenshot()
            try:
                if self.main_window is not None:
                    win_rect = self.main_window.rectangle()
                    win_left = win_rect.left
                    win_top = win_rect.top
                    win_width = win_rect.width()
                    win_height = win_rect.height()
                else:
                    raise Exception("main_window is None")
            except Exception:
                win_left = 0
                win_top = 0
                win_width = screen_width // 2
                win_height = screen_height
            search_left = win_left + 50
            search_right = win_left + win_width - 50
            search_top = win_top + 150
            search_bottom = win_top + win_height - 100
            color_ranges = {
                ".vsd": {"name": "紫色(Visio)", "r": (120, 190), "g": (0, 145), "b": (200, 255), "b_g_diff": 60, "r_min_check": 120},
                ".vsdx": {"name": "紫色(Visio)", "r": (120, 190), "g": (0, 145), "b": (200, 255), "b_g_diff": 60, "r_min_check": 120},
                ".pdf": {"name": "红色(PDF)", "r": (150, 255), "g": (0, 120), "b": (0, 120), "r_g_diff": 50},
                ".doc": {"name": "蓝色(Word)", "r": (0, 100), "g": (0, 150), "b": (150, 255), "b_r_diff": 50},
                ".docx": {"name": "蓝色(Word)", "r": (0, 100), "g": (0, 150), "b": (150, 255), "b_r_diff": 50},
                ".xls": {"name": "绿色(Excel)", "r": (0, 100), "g": (150, 255), "b": (0, 100), "g_b_diff": 50},
                ".xlsx": {"name": "绿色(Excel)", "r": (0, 100), "g": (150, 255), "b": (0, 100), "g_b_diff": 50},
                ".dwg": {"name": "灰色(CAD)", "r": (80, 220), "g": (80, 220), "b": (80, 220), "gray": True},
                ".dxf": {"name": "灰色(CAD)", "r": (80, 220), "g": (80, 220), "b": (80, 220), "gray": True},
                "folder": {"name": "黄色(文件夹)", "r": (220, 255), "g": (140, 230), "b": (0, 140)},
            }
            color_config = color_ranges.get(file_extension.lower(), color_ranges[".vsd"])
            step_size = 5
            matched_pixels = []
            for y in range(search_top, search_bottom, step_size):
                for x in range(search_left, search_right, step_size):
                    try:
                        pixel = screenshot.getpixel((x, y))
                        # 检查像素类型，必须为 tuple 且长度>=3
                        if pixel is None or not isinstance(pixel, tuple) or len(pixel) < 3:
                            continue
                        r, g, b = pixel[:3]
                        r_min, r_max = color_config["r"]
                        g_min, g_max = color_config["g"]
                        b_min, b_max = color_config["b"]
                        if r_min <= r <= r_max and g_min <= g <= g_max and b_min <= b <= b_max:
                            if "gray" in color_config:
                                if abs(r - g) < 40 and abs(r - b) < 40 and abs(g - b) < 40:
                                    matched_pixels.append((x, y, pixel))
                            elif "b_g_diff" in color_config:
                                if b > g + color_config["b_g_diff"]:
                                    if "r_min_check" in color_config:
                                        if r >= color_config["r_min_check"]:
                                            matched_pixels.append((x, y, pixel))
                                    else:
                                        matched_pixels.append((x, y, pixel))
                            elif "r_g_diff" in color_config and r > g + color_config["r_g_diff"]:
                                matched_pixels.append((x, y, pixel))
                            elif "g_b_diff" in color_config and g > b + color_config["g_b_diff"]:
                                matched_pixels.append((x, y, pixel))
                            elif "b_r_diff" in color_config and b > r + color_config["b_r_diff"]:
                                matched_pixels.append((x, y, pixel))
                            elif "b_g_diff" not in color_config and "r_g_diff" not in color_config and "g_b_diff" not in color_config and "b_r_diff" not in color_config and "gray" not in color_config:
                                matched_pixels.append((x, y, pixel))
                    except Exception:
                        continue
            if matched_pixels:
                matched_pixels.sort(key=lambda p: p[1])
                first_match = matched_pixels[0]
                click_x, click_y = first_match[0] + 50, first_match[1]
                class FakeFileItem:
                    def __init__(self, x, y):
                        self.x = x
                        self.y = y
                    def click_input(self, button='left'):
                        pyautogui.click(self.x, self.y, button=button)
                    def double_click_input(self):
                        pyautogui.doubleClick(self.x, self.y)
                    def window_text(self):
                        return f"{file_extension}文件"
                return FakeFileItem(click_x, click_y)
            return None
        except Exception as e:
            logging.error(f"颜色识别失败: {str(e)}")
            return None

    def download_file(self, file_item):
        """下载文件 - 使用图片识别下载和确认按钮"""
        try:
            self.dismiss_interfering_dialogs()
            self.log_step("开始下载流程")

            # 直接右键，避免单击触发文件预览/打开提示
            self.log_step("右键点击文件")
            file_item.click_input(button='right')
            time.sleep(1)
            
            # 图片识别"下载"菜单项
            if self.download_btn_path.exists():
                self.log_step("识别下载按钮")
                download_button = pyautogui.locateOnScreen(
                    str(self.download_btn_path), 
                    confidence=0.8
                )
                if download_button:
                    self.log_step("找到下载按钮", f"位置: {download_button}")
                    pyautogui.click(download_button)
                else:
                    # 下载按钮识别失败时，先清理可能弹窗再用键盘选择
                    self.dismiss_interfering_dialogs()
                    self.log_step("使用键盘选择下载")
                    pyautogui.press('down')
                    time.sleep(0.3)
                    pyautogui.press('enter')
            else:
                # 用键盘选择
                self.dismiss_interfering_dialogs()
                pyautogui.press('down')
                time.sleep(0.3)
                pyautogui.press('enter')
            
            # 等待确认对话框
            self.log_step("等待确认对话框", "等待1.5秒")
            time.sleep(1.5)
            
            # 图片识别"确认"按钮
            if self.confirm_btn_path.exists():
                self.log_step("识别确认按钮")
                confirm_button = pyautogui.locateOnScreen(
                    str(self.confirm_btn_path), 
                    confidence=0.8
                )
                if confirm_button:
                    self.log_step("找到确认按钮", f"位置: {confirm_button}")
                    pyautogui.click(confirm_button)
                else:
                    # 按回车确认
                    pyautogui.press('enter')
            else:
                # 按回车确认
                pyautogui.press('enter')

            self.dismiss_interfering_dialogs()
            
            self.log_step("下载命令已发送")
            return True
            
        except Exception as e:
            logging.error(f"下载文件失败: {str(e)}")
            print(f"下载文件失败: {str(e)}")
            return False

    def process_files(self, priority_extensions=None):
        """处理文件列表
        
        Args:
            priority_extensions: 文件扩展名优先级列表，如 [".vsd", ".dwg"] 或 ["folder"]
        """
        if priority_extensions is None:
            priority_extensions = [".vsd", ".vsdx", ".dwg", ".dxf"]  # 默认优先级
        
        try:
            # 读取Excel文件
            df = pd.read_excel(self.excel_path)
            filenames = [
                str(x).strip()
                for x in df.iloc[:, 0].tolist()
                if pd.notna(x) and str(x).strip()
            ]
            
            print(f"\n开始处理 {len(filenames)} 个文件...")
            print(f"文件类型优先级: {' → '.join(priority_extensions)}")
            
            # 连接客户端
            if not self.connect_to_client():
                return
            
            # 导航到指定目录
            if not self.navigate_to_folder():
                print("无法进入指定目录，程序终止")
                return
            
            # 记录成功下载的文件
            downloaded_files = []
            skipped_files = []
            processed_search_terms = set()
            
            for i, filename in enumerate(filenames, 1):
                print(f"\n[{i}/{len(filenames)}] 正在搜索: {filename}")
                logging.info(f"开始搜索: {filename}")

                # 同一批次内，跳过重复搜索词，避免重复下载
                if filename in processed_search_terms:
                    print(f"- 跳过重复项: {filename}")
                    logging.info(f"跳过重复搜索词: {filename}")
                    skipped_files.append({"文件名": filename, "原因": "Excel中重复"})
                    continue
                processed_search_terms.add(filename)

                # 下载目录中已存在同名文件时跳过，避免重复下载
                existing_files = self.get_existing_files()
                if any(filename.lower() in f.lower() for f in existing_files):
                    print(f"- 已存在，跳过下载: {filename}")
                    logging.info(f"跳过已存在文件: {filename}")
                    skipped_files.append({"文件名": filename, "原因": "下载目录已存在"})
                    continue
                
                # 记录下载前的文件列表
                files_before = existing_files
                
                if self.search_file(filename):
                    time.sleep(1)
                    
                    # 按用户指定的优先级查找文件
                    file_item = None
                    found_extension = None
                    
                    # 检查是否包含文件夹选项
                    if "folder" in priority_extensions:
                        # 文件夹模式：先尝试其他文件类型，没有才下载文件夹
                        file_extensions = [ext for ext in priority_extensions if ext != "folder"]
                        
                        if file_extensions:
                            for ext in file_extensions:
                                self.log_step("尝试查找文件类型", ext)
                                file_item = self.get_file_list(target_filename=filename, file_extension=ext)
                                if file_item:
                                    found_extension = ext
                                    print(f"  ✓ 找到{ext}文件")
                                    break
                            
                            if not file_item:
                                print("  未找到指定类型文件，将下载第一个搜索结果（可能是文件夹）")
                                # 这里可以添加下载第一个结果的逻辑
                                # 暂时跳过
                                self.not_found.append(filename)
                                print(f"✗ 未找到匹配文件: {filename}")
                                logging.warning(f"未找到匹配文件: {filename}")
                                continue
                        else:
                            # 仅选择文件夹：尝试直接下载文件夹
                            self.log_step("尝试查找文件夹", "folder")
                            file_item = self.get_file_list(target_filename=filename, file_extension="folder")
                            if file_item:
                                found_extension = "folder"
                                print("  ✓ 找到文件夹")
                            else:
                                print("  ✗ 未找到匹配的文件夹")
                                self.not_found.append(filename)
                                continue
                    else:
                        # 普通文件模式：按优先级查找
                        for ext in priority_extensions:
                            self.log_step("尝试查找文件类型", ext)
                            file_item = self.get_file_list(target_filename=filename, file_extension=ext)
                            if file_item:
                                found_extension = ext
                                print(f"  ✓ 找到{ext}文件")
                                break
                    
                    if file_item:
                        # 发送下载命令
                        if self.download_file(file_item):
                            # 验证下载是否成功
                            success, downloaded_name = self.verify_download(
                                filename, files_before, timeout=60
                            )
                            if success:
                                downloaded_files.append({
                                    "搜索词": filename,
                                    "下载文件": downloaded_name,
                                    "文件类型": found_extension
                                })
                                print(f"✓ 下载完成: {filename}")
                                logging.info(f"下载成功: {filename} -> {downloaded_name} ({found_extension})")
                            else:
                                self.not_found.append(filename)
                                print(f"✗ 下载验证失败: {filename}")
                                logging.error(f"下载验证失败: {filename}")
                        else:
                            self.not_found.append(filename)
                            print(f"✗ 下载命令失败: {filename}")
                            logging.error(f"下载命令失败: {filename}")
                    else:
                        self.not_found.append(filename)
                        print(f"✗ 未找到文件: {filename}")
                        logging.warning(f"未找到文件: {filename}")
                else:
                    self.not_found.append(filename)
                    print(f"✗ 搜索失败: {filename}")
                    logging.error(f"搜索失败: {filename}")
                
                time.sleep(1)

            # 输出统计信息
            print(f"\n{'='*50}")
            print(f"下载完成统计:")
            print(f"  成功: {len(downloaded_files)} 个")
            print(f"  跳过: {len(skipped_files)} 个")
            print(f"  失败: {len(self.not_found)} 个")
            print(f"{'='*50}")
            
            # 保存成功下载的文件列表
            if downloaded_files:
                success_df = pd.DataFrame(downloaded_files)
                success_path = "已下载的文件.xlsx"
                success_df.to_excel(success_path, index=False)
                print(f"已下载文件列表保存到: {success_path}")

            # 保存未找到或下载失败的文件列表
            if self.not_found:
                not_found_df = pd.DataFrame({"未下载的文件": self.not_found})
                not_found_path = "未下载的文件.xlsx"
                not_found_df.to_excel(not_found_path, index=False)
                print(f"\n有 {len(self.not_found)} 个文件未下载，已保存到: {not_found_path}")
                logging.info(f"有 {len(self.not_found)} 个文件未下载，已保存到: {not_found_path}")
            else:
                print("\n所有文件都已成功下载！")
                logging.info("所有文件下载完成")

            if skipped_files:
                skipped_df = pd.DataFrame(skipped_files)
                skipped_path = "跳过的文件.xlsx"
                skipped_df.to_excel(skipped_path, index=False)
                print(f"跳过文件列表保存到: {skipped_path}")

        except Exception as e:
            logging.error(f"处理文件时出错: {str(e)}")
            print(f"处理文件时出错: {str(e)}")

def main():
    """主程序入口"""
    try:
        # 创建下载器实例
        downloader = MobileCloudDownloader()
        
        # ============ 配置云盘目录路径 ============
        # 设置要进入的云盘目录层级（从根目录开始）
        # 例如要进入 "工作文件/2024项目/图纸" 目录，设置为：
        # downloader.cloud_folder_path = ["工作文件", "2024项目", "图纸"]
        # 留空则在当前位置搜索：
        downloader.cloud_folder_path = []
        # ==========================================
        
        # 确保资源目录存在
        if not downloader.resource_path.exists():
            print("警告: 未找到资源目录，将使用键盘快捷键方式下载")
            print(f"如需图片识别，请创建目录: {downloader.resource_path}")
            # 不再强制退出，改为继续执行
            downloader.resource_path.mkdir(parents=True, exist_ok=True)
            
        # 检查按钮图片是否存在（改为警告而非错误）
        if not downloader.download_btn_path.exists():
            print("警告: 未找到下载按钮截图，将使用键盘快捷键")
            print(f"如需图片识别，请保存截图到: {downloader.download_btn_path}")
            
        if not downloader.confirm_btn_path.exists():
            print("警告: 未找到确认按钮截图，将使用键盘快捷键")
            print(f"如需图片识别，请保存截图到: {downloader.confirm_btn_path}")
            
        # 检查Excel文件是否存在
        if not Path(downloader.excel_path).exists():
            print("错误: 未找到Excel文件！")
            print(f"请确保文件存在: {downloader.excel_path}")
            return
            
        # 检查下载目录是否存在
        if not Path(downloader.download_dir).exists():
            print(f"创建下载目录: {downloader.download_dir}")
            Path(downloader.download_dir).mkdir(parents=True, exist_ok=True)
        
        print("\n" + "="*50)
        print("批量下载程序配置:")
        print("="*50)
        print(f"Excel文件: {downloader.excel_path}")
        print(f"下载目录:  {downloader.download_dir}")
        if downloader.cloud_folder_path:
            print(f"云盘目录:  {'/'.join(downloader.cloud_folder_path)}")
        else:
            print("云盘目录:  根目录/当前位置")
        print("="*50)
        
        print("\n重要提示:")
        print("1. 请确保移动云盘客户端已启动并登录")
        print("2. 请确保云盘客户端的下载目录已设置为上述下载目录")
        print("3. 开始处理时会提示定位搜索框（首次使用或需要时）")
        
        # 让用户选择要下载的文件类型
        print("\n" + "="*50)
        print("请选择要下载的文件类型:")
        print("="*50)
        print("1. VSD文件 (.vsd)")
        print("2. VSDX文件 (.vsdx)")
        print("3. CAD文件 (.dwg)")
        print("4. DXF文件 (.dxf)")
        print("5. PDF文件 (.pdf)")
        print("6. 文件夹")
        print("7. 自定义优先级（输入多个数字，用逗号分隔，如：1,3 表示先找VSD，没有则找CAD）")
        print("8. Word文件 (.doc/.docx)")
        print("="*50)
        
        choice = input("\n请输入选项（默认：1,2,3,4 即VSD→VSDX→CAD→DXF）: ").strip()
        
        # 解析用户选择
        file_type_map = {
            "1": [".vsd"],
            "2": [".vsdx"],
            "3": [".dwg"],
            "4": [".dxf"],
            "5": [".pdf"],
            "6": ["folder"],  # 特殊标记表示文件夹
            "8": [".doc", ".docx"],
        }
        
        # 支持两种自定义输入方式：
        # 1) 先输入 7 再输入优先级；2) 直接在首个提示输入 1,2,5 这样的列表
        if not choice or choice == "7" or "," in choice:
            if choice == "7":
                choice = input("请输入优先级（如：1,3,6 表示VSD→CAD→文件夹）: ").strip()

            if not choice:
                # 默认优先级
                priority_extensions = [".vsd", ".vsdx", ".dwg", ".dxf"]
                print("使用默认优先级: VSD → VSDX → CAD → DXF")
            else:
                # 自定义优先级
                selected = [s.strip() for s in choice.split(",") if s.strip()]
                priority_extensions = []
                for sel in selected:
                    if sel in file_type_map:
                        priority_extensions.extend(file_type_map[sel])

                if not priority_extensions:
                    print("无效选择，使用默认优先级")
                    priority_extensions = [".vsd", ".vsdx", ".dwg", ".dxf"]
                else:
                    print(f"使用自定义优先级: {' → '.join(priority_extensions)}")
        else:
            # 单个选择
            if choice in file_type_map:
                priority_extensions = file_type_map[choice]
                print(f"已选择: {priority_extensions[0]}")
            else:
                print("无效选择，使用默认优先级")
                priority_extensions = [".vsd", ".vsdx", ".dwg", ".dxf"]
        
        input("\n鼠标已放到搜索框后，按回车键开始...")
        
        # 开始处理文件
        downloader.process_files(priority_extensions=priority_extensions)
        
    except Exception as e:
        print(f"程序运行出错: {str(e)}")
    finally:
        print("\n程序运行完成！")
        input("按回车键退出...")

if __name__ == "__main__":
    main()
