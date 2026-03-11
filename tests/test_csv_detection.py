import csv
import sys
import os
sys.path.append('.')

# 读取CSV文件
filepath = r"D:\02 软件文件夹\工作软件\小工具\google_map_tools\已知经纬度点位的格式.csv"
with open(filepath, 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    rows = list(reader)

print("CSV内容:")
for i, row in enumerate(rows):
    print(f"行{i}: {row}")

# 导入GoogleMapsTools类并测试_detect_csv_format
try:
    from google_maps_tool import GoogleMapsTools
    app = GoogleMapsTools()
    input_type = app._detect_csv_format(rows)
    print(f"\n检测到的格式: {input_type}")
    
    # 模拟处理逻辑
    print("\n模拟处理...")
    # 跳过表头
    header = rows[0]
    data_rows = rows[1:]
    print(f"表头: {header}")
    print(f"数据行数: {len(data_rows)}")
    
    for i, row in enumerate(data_rows):
        print(f"\n处理行 {i+1}: {row}")
        if input_type == 'address':
            print("格式为address，将尝试查询地址...")
        elif input_type == 'wgs84':
            print("格式为wgs84，将直接使用坐标...")
        elif input_type == 'gcj02':
            print("格式为gcj02，将直接使用坐标...")
        elif input_type == 'user_special':
            print("格式为user_special，将使用特殊处理...")
            
except Exception as e:
    print(f"导入或测试失败: {e}")
    import traceback
    traceback.print_exc()
