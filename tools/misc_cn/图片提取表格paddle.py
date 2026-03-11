import cv2
import numpy as np
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from paddleocr import PaddleOCR
import warnings
warnings.filterwarnings('ignore')

class TableExtractor:
    def __init__(self):
        self.setup_ocr()
        self.setup_gui()
        
    def setup_ocr(self):
        """初始化 PaddleOCR"""
        try:
            self.ocr = PaddleOCR(
                use_angle_cls=True,  # 文字方向检测
                lang="ch",           # 中文模型
                show_log=False,      # 不显示日志
                use_gpu=False        # 使用CPU推理
            )
        except Exception as e:
            raise Exception(f"初始化 PaddleOCR 失败: {str(e)}")
    
    def detect_table_structure(self, image):
        """检测表格结构"""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 自适应二值化
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # 腐蚀和膨胀操作来清理噪声
        kernel = np.ones((2, 2), np.uint8)
        binary = cv2.erode(binary, kernel, iterations=1)
        binary = cv2.dilate(binary, kernel, iterations=1)
        
        # 检测横线和竖线
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        horizontal_lines = cv2.erode(binary, horizontal_kernel, iterations=1)
        vertical_lines = cv2.erode(binary, vertical_kernel, iterations=1)
        
        table_structure = cv2.add(horizontal_lines, vertical_lines)
        
        # 查找单元格轮廓
        contours, _ = cv2.findContours(
            table_structure, 
            cv2.RETR_TREE, 
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # 过滤和排序单元格
        cells = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            if w > 30 and h > 20:  # 过滤太小的区域
                cells.append([x, y, w, h])
        
        # 按行列排序
        cells.sort(key=lambda x: (x[1] // 30, x[0]))  # 30是行高阈值
        return cells, image.copy()
    
    def extract_table_from_image(self, image_path, output_path):
        """从图片中提取表格数据"""
        try:
            # 读取图片
            img_path = str(Path(image_path))
            image = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if image is None:
                raise Exception("无法读取图片文件")
            
            # 检测表格结构
            cells, debug_image = self.detect_table_structure(image)
            if not cells:
                raise Exception("未检测到表格结构")
            
            # 组织数据
            current_row = []
            all_rows = []
            last_y = cells[0][1]
            row_height_threshold = 20
            
            for cell in cells:
                x, y, w, h = cell
                
                # 判断是否是新行
                if abs(y - last_y) > row_height_threshold:
                    if current_row:
                        all_rows.append(current_row)
                    current_row = []
                    last_y = y
                
                # 提取当前单元格的文字
                roi = image[y:y+h, x:x+w]
                result = self.ocr.ocr(roi, cls=False)
                
                # 提取文字内容
                if result and result[0]:
                    text = result[0][0][1][0]  # 获取识别的文字
                else:
                    text = ""
                
                current_row.append(text)
                
                # 在调试图像上绘制边界框
                cv2.rectangle(debug_image, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # 添加最后一行
            if current_row:
                all_rows.append(current_row)
            
            # 标准化数据
            max_cols = max(len(row) for row in all_rows)
            standardized_rows = [row + [''] * (max_cols - len(row)) for row in all_rows]
            
            # 保存为Excel
            df = pd.DataFrame(standardized_rows)
            df.to_excel(output_path, index=False, header=False)
            
            # 保存调试图像
            debug_path = str(Path(output_path).with_suffix('.debug.jpg'))
            cv2.imencode('.jpg', debug_image)[1].tofile(debug_path)
            
            return True
            
        except Exception as e:
            raise Exception(f"处理图片失败: {str(e)}")

    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("表格提取工具")
        self.root.geometry("400x300")
        
        # 设置样式
        self.root.configure(bg='#f0f0f0')
        button_style = {'font': ('微软雅黑', 10), 'bg': '#4CAF50', 'fg': 'white', 
                       'padx': 20, 'pady': 10, 'relief': tk.RAISED}
        
        # 创建按钮
        tk.Button(self.root, text="选择图片", command=self.select_image, 
                  **button_style).pack(pady=20)
        
        # 状态标签
        self.status_label = tk.Label(self.root, text="等待选择图片...", 
                                    bg='#f0f0f0', font=('微软雅黑', 9))
        self.status_label.pack(pady=10)
        
        # 提示信息
        tk.Label(self.root, text="支持格式: PNG, JPG, JPEG", 
                bg='#f0f0f0', font=('微软雅黑', 9)).pack()

    def select_image(self):
        """选择图片文件并处理"""
        file_path = filedialog.askopenfilename(
            title="选择表格图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                self.status_label.config(text="正在处理中...", fg='blue')
                self.root.update()
                
                # 选择保存位置
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel文件", "*.xlsx")],
                    title="保存Excel文件"
                )
                
                if output_path:
                    if self.extract_table_from_image(file_path, output_path):
                        messagebox.showinfo("成功", f"表格数据已保存到:\n{output_path}")
                        self.status_label.config(text="处理完成", fg='green')
                    
            except Exception as e:
                messagebox.showerror("错误", f"处理失败: {str(e)}")
                self.status_label.config(text="处理失败", fg='red')

    def run(self):
        """运行程序"""
        self.root.mainloop()

if __name__ == "__main__":
    try:
        app = TableExtractor()
        app.run()
    except Exception as e:
        print("程序初始化失败:")
        print(f"错误信息: {str(e)}")
        print("\n请确保已安装所需库:")
        print("1. pip install paddlepaddle")
        print("2. pip install paddleocr")
        print("3. pip install opencv-python")
        print("4. pip install pandas")
        print("5. pip install openpyxl")
        input("\n按回车键退出...")