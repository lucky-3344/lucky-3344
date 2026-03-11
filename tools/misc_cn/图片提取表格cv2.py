import cv2
import numpy as np
import pytesseract
from PIL import Image
import pandas as pd
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

class TableExtractor:
    def __init__(self):
        # 添加 Tesseract 路径检查
        self.check_tesseract()
        self.setup_gui()
        
    def check_tesseract(self):
        """检查 Tesseract 是否正确配置"""
        tesseract_path = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        if not Path(tesseract_path).exists():
            raise Exception(
                "未找到 Tesseract-OCR，请确保已安装并配置正确的路径\n"
                "下载地址：https://github.com/UB-Mannheim/tesseract/wiki"
            )
        pytesseract.pytesseract.tesseract_cmd = tesseract_path
        
        # 检查语言包
        try:
            languages = pytesseract.get_languages()
            if 'chi_sim' not in languages:
                raise Exception("未找到中文语言包，请安装中文语言支持")
        except Exception as e:
            raise Exception(f"检查语言包失败: {str(e)}")
        
    def setup_gui(self):
        """设置GUI界面"""
        self.root = tk.Tk()
        self.root.title("表格提取工具")
        self.root.geometry("400x200")
        
        # 设置样式
        self.root.configure(bg='#f0f0f0')
        button_style = {'font': ('微软雅黑', 10), 'bg': '#4CAF50', 'fg': 'white', 
                       'padx': 20, 'pady': 10, 'relief': tk.RAISED}
        
        # 创建按钮
        tk.Button(self.root, text="选择图片", command=self.select_image, **button_style).pack(pady=20)
        tk.Label(self.root, text="支持格式: PNG, JPG, JPEG", bg='#f0f0f0', 
                font=('微软雅黑', 9)).pack()
        
        self.status_label = tk.Label(self.root, text="", bg='#f0f0f0', 
                                   font=('微软雅黑', 9))
        self.status_label.pack(pady=10)
        
    def select_image(self):
        """选择图片文件"""
        file_path = filedialog.askopenfilename(
            title="选择表格图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg"),
                ("所有文件", "*.*")
            ]
        )
        
        if file_path:
            try:
                # 选择保存Excel的位置
                output_path = filedialog.asksaveasfilename(
                    defaultextension=".xlsx",
                    filetypes=[("Excel文件", "*.xlsx")],
                    title="保存Excel文件"
                )
                
                if output_path:
                    self.status_label.config(text="正在处理中...", fg='blue')
                    self.root.update()
                    
                    # 处理图片
                    self.extract_table_from_image(file_path, output_path)
                    
                    messagebox.showinfo("成功", f"表格数据已保存到:\n{output_path}")
                    self.status_label.config(text="处理完成", fg='green')
            except Exception as e:
                messagebox.showerror("错误", f"处理失败: {str(e)}")
                self.status_label.config(text="处理失败", fg='red')
    
    def extract_table_from_image(self, image_path, output_path):
        """从图片中提取表格数据"""
        try:
            # 处理中文路径问题
            img_path = str(Path(image_path))
            img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
            if img is None:
                raise Exception("无法读取图片文件")
                
            # 图像预处理
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # 使用自适应阈值处理
            thresh = cv2.adaptiveThreshold(
                gray, 
                255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY_INV, 
                11, 
                2
            )

            # 添加图像增强
            kernel = np.ones((2,2), np.uint8)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
            
            # 查找轮廓
            contours, _ = cv2.findContours(
                thresh, 
                cv2.RETR_TREE, 
                cv2.CHAIN_APPROX_SIMPLE
            )
            
            # 存储单元格坐标
            cells = []
            for cnt in contours:
                x, y, w, h = cv2.boundingRect(cnt)
                if w > 50 and h > 15:  # 可调整阈值
                    cells.append([x, y, w, h])
            
            # 按位置排序（先按y后按x）
            cells.sort(key=lambda x: (x[1], x[0]))
            
            # 提取文本
            data = []
            row = []
            last_y = cells[0][1] if cells else 0
            
            for cell in cells:
                x, y, w, h = cell
                
                if abs(y - last_y) > 10:  # 新行阈值
                    if row:
                        data.append(row)
                    row = []
                    last_y = y
                
                roi = gray[y:y+h, x:x+w]
                try:
                    text = pytesseract.image_to_string(
                        roi, 
                        lang='chi_sim+eng',
                        config='--psm 6'  # 假设是统一的文本块
                    )
                    row.append(text.strip())
                except Exception as e:
                    print(f"警告：单元格文字识别失败: {str(e)}")
                    row.append("")  # 添加空字符串作为占位符
            
            if row:
                data.append(row)
            
            # 保存为Excel
            df = pd.DataFrame(data)
            df.to_excel(output_path, index=False)
        
        except Exception as e:
            raise Exception(f"处理图片失败: {str(e)}")
    
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
        print("\n请确保:")
        print("1. 已安装 Tesseract-OCR")
        print("2. 安装路径正确")
        print("3. 已添加到系统环境变量")
        print("4. 已安装中文语言包")
        input("\n按回车键退出...")