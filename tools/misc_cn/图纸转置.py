import pandas as pd
import tkinter as tk
from tkinter import filedialog

# 隐藏主窗口
root = tk.Tk()
root.withdraw()

# 选择输入文件
input_path = filedialog.askopenfilename(title="请选择输入Excel文件", filetypes=[("Excel files", "*.xlsx;*.xls")])
if not input_path:
    print("未选择输入文件，程序退出。")
    exit()

# 选择输出文件夹
output_dir = filedialog.askdirectory(title="请选择输出文件夹")
if not output_dir:
    print("未选择输出文件夹，程序退出。")
    exit()

output_path = output_dir + "/output.xlsx"

df = pd.read_excel(input_path, header=0)

result = []

for idx, row in df.iterrows():
    base_name = str(row[0]).strip()
    for col in row.index[1:]:
        drawing_name = str(row[col]).strip()
        if drawing_name and drawing_name != 'nan':
            result.append(base_name + drawing_name)

df_out = pd.DataFrame(result, columns=['合并后图纸名称'])
df_out.to_excel(output_path, index=False)
print(f"已输出到：{output_path}")