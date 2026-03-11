from PIL import Image
import tkinter as tk
from tkinter import filedialog, messagebox

def convert_png_to_ico(png_path, ico_path):
    try:
        image = Image.open(png_path)
        image.save(ico_path, format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        messagebox.showinfo("成功", f"成功将 {png_path} 转换为 {ico_path}")
    except Exception as e:
        messagebox.showerror("错误", f"转换时出现错误: {e}")

def select_input_file():
    file_path = filedialog.askopenfilename(
        title="选择PNG图片",
        filetypes=[("PNG图片", "*.png"), ("所有文件", "*.*")]
    )
    if file_path:
        input_entry.delete(0, tk.END)
        input_entry.insert(0, file_path)

def select_output_file():
    file_path = filedialog.asksaveasfilename(
        title="保存ICO文件",
        defaultextension=".ico",
        filetypes=[("ICO图标", "*.ico"), ("所有文件", "*.*")]
    )
    if file_path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, file_path)

def start_conversion():
    png_file = input_entry.get()
    ico_file = output_entry.get()
    if not png_file or not ico_file:
        messagebox.showwarning("警告", "请先选择输入和输出文件")
        return
    convert_png_to_ico(png_file, ico_file)

# 创建主窗口
root = tk.Tk()
root.title("PNG转ICO工具")

# 输入文件选择
tk.Label(root, text="输入PNG文件:").grid(row=0, column=0, padx=5, pady=5)
input_entry = tk.Entry(root, width=40)
input_entry.grid(row=0, column=1, padx=5, pady=5)
tk.Button(root, text="浏览...", command=select_input_file).grid(row=0, column=2, padx=5, pady=5)

# 输出文件选择
tk.Label(root, text="输出ICO文件:").grid(row=1, column=0, padx=5, pady=5)
output_entry = tk.Entry(root, width=40)
output_entry.grid(row=1, column=1, padx=5, pady=5)
tk.Button(root, text="浏览...", command=select_output_file).grid(row=1, column=2, padx=5, pady=5)

# 转换按钮
tk.Button(root, text="开始转换", command=start_conversion).grid(row=2, column=1, pady=10)

root.mainloop()