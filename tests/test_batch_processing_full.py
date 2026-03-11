import sys
import os
sys.path.append('.')

# 模拟文件对话框
class MockFileDialog:
    @staticmethod
    def askopenfilename(**kwargs):
        # 直接返回测试文件路径
        return r"D:\02 软件文件夹\工作软件\小工具\google_map_tools\已知经纬度点位的格式.csv"

# 替换filedialog
import tkinter.filedialog as filedialog
original_askopenfilename = filedialog.askopenfilename
filedialog.askopenfilename = MockFileDialog.askopenfilename

try:
    from google_maps_tool import GoogleMapsTools
    
    # 创建应用实例，但不显示GUI
    app = GoogleMapsTools()
    # 隐藏主窗口
    app.root.withdraw()
    
    # 调用导入CSV方法
    print("开始测试批量处理...")
    app.import_csv()
    
    # 检查处理结果
    if app.batch_results:
        print(f"\n处理完成，共处理 {len(app.batch_results)} 条记录")
        for i, result in enumerate(app.batch_results[:3]):  # 只显示前3条
            print(f"\n记录 {i+1}:")
            for key, value in result.items():
                print(f"  {key}: {value}")
    else:
        print("没有处理结果")
        
except Exception as e:
    print(f"测试过程中出现错误: {e}")
    import traceback
    traceback.print_exc()
finally:
    # 恢复原始函数
    filedialog.askopenfilename = original_askopenfilename
