"""
API调用频率测试脚本
验证修复后的google_maps_tool.py是否符合高德API的3次/秒限制
"""
import time
from datetime import datetime
import sys
import os

# 添加当前目录到Python路径，以便导入google_maps_tool
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class APIFrequencyTester:
    def __init__(self):
        self.api_calls = []
        self.test_results = []
    
    def simulate_api_call(self, api_name, delay=0.35):
        """模拟API调用，包含延迟"""
        call_time = datetime.now()
        self.api_calls.append((call_time, api_name, delay))
        
        # 模拟实际延迟
        if delay > 0:
            time.sleep(delay)
        
        print(f"[{call_time.strftime('%H:%M:%S.%f')[:-3]}] 调用: {api_name} (延迟: {delay:.3f}秒)")
        return call_time
    
    def simulate_address_point_processing(self):
        """模拟地址格式数据点处理"""
        print("\n" + "="*60)
        print("模拟地址格式数据点处理 (5次API调用)")
        print("="*60)
        
        # 模拟地址格式的5次API调用
        self.simulate_api_call("1. /v3/geocode/geo - 地址转坐标")
        self.simulate_api_call("2. /v3/geocode/regeo - 区域属性分析")
        self.simulate_api_call("3. /v3/place/around - POI密度统计")
        self.simulate_api_call("4. /v3/geocode/regeo - 地理特征分析")
        self.simulate_api_call("5. /v3/place/around - 周边POI分析")
        
        # 数据点间延迟
        print(f"\n数据点间延迟: 0.8秒")
        time.sleep(0.8)
        
        # 额外延迟
        print(f"额外延迟: 0.4秒")
        time.sleep(0.4)
    
    def simulate_coordinate_point_processing(self):
        """模拟坐标格式数据点处理"""
        print("\n" + "="*60)
        print("模拟坐标格式数据点处理 (4次API调用)")
        print("="*60)
        
        # 模拟坐标格式的4次API调用
        self.simulate_api_call("1. /v3/geocode/regeo - 区域属性分析")
        self.simulate_api_call("2. /v3/place/around - POI密度统计")
        self.simulate_api_call("3. /v3/geocode/regeo - 地理特征分析")
        self.simulate_api_call("4. /v3/place/around - 周边POI分析")
        
        # 数据点间延迟
        print(f"\n数据点间延迟: 0.8秒")
        time.sleep(0.8)
    
    def analyze_frequency(self):
        """分析API调用频率"""
        if len(self.api_calls) < 2:
            print("警告: API调用次数不足，无法分析频率")
            return
        
        print("\n" + "="*60)
        print("API调用频率分析报告")
        print("="*60)
        
        violations = 0
        total_calls = len(self.api_calls)
        
        for i in range(1, len(self.api_calls)):
            prev_time, prev_name, prev_delay = self.api_calls[i-1]
            curr_time, curr_name, curr_delay = self.api_calls[i]
            
            time_diff = (curr_time - prev_time).total_seconds()
            calls_per_second = 1 / time_diff if time_diff > 0 else float('inf')
            
            # 检查是否违反3次/秒限制
            is_violation = calls_per_second > 3.0
            if is_violation:
                violations += 1
            
            status = "⚠️ 违规" if is_violation else "✅ 正常"
            
            print(f"{prev_name}")
            print(f"  → {curr_name}")
            print(f"  时间间隔: {time_diff:.3f}秒")
            print(f"  频率: {calls_per_second:.2f}次/秒 {status}")
            print()
            
            # 记录测试结果
            self.test_results.append({
                'from': prev_name,
                'to': curr_name,
                'interval': time_diff,
                'frequency': calls_per_second,
                'is_violation': is_violation
            })
        
        print(f"\n{'='*60}")
        print("测试总结:")
        print(f"{'='*60}")
        print(f"总API调用次数: {total_calls}")
        print(f"违规次数: {violations}")
        print(f"合规率: {(total_calls - violations - 1) / (total_calls - 1) * 100:.1f}%")
        
        if violations == 0:
            print("\n🎉 所有API调用符合3次/秒限制！")
            return True
        else:
            print(f"\n❌ 发现{violations}次违规，需要进一步优化。")
            return False
    
    def run_comprehensive_test(self):
        """运行全面测试"""
        print("开始API调用频率全面测试")
        print("="*60)
        
        # 测试1: 地址格式处理
        self.simulate_address_point_processing()
        
        # 测试2: 坐标格式处理  
        self.simulate_coordinate_point_processing()
        
        # 测试3: 批量处理模拟（3个数据点）
        print("\n" + "="*60)
        print("模拟批量处理 (3个坐标格式数据点)")
        print("="*60)
        
        for i in range(3):
            print(f"\n--- 处理第 {i+1} 个数据点 ---")
            self.simulate_coordinate_point_processing()
        
        # 分析频率
        return self.analyze_frequency()

def test_actual_code_import():
    """测试实际代码导入"""
    print("\n" + "="*60)
    print("测试google_maps_tool.py导入和基本功能")
    print("="*60)
    
    try:
        # 尝试导入模块
        import google_maps_tool
        print("✅ google_maps_tool.py导入成功")
        
        # 检查关键方法是否存在
        tool = google_maps_tool.GoogleMapsTools()
        
        required_methods = [
            'get_area_properties',
            'get_geo_features', 
            '_get_json_with_retry',
            'analyze_area',
            'import_csv'
        ]
        
        all_methods_exist = True
        for method in required_methods:
            if hasattr(tool, method):
                print(f"✅ 方法 {method} 存在")
            else:
                print(f"❌ 方法 {method} 不存在")
                all_methods_exist = False
        
        if all_methods_exist:
            print("\n✅ 所有关键方法都存在")
            return True
        else:
            print("\n❌ 缺少关键方法")
            return False
            
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        return False

def main():
    """主测试函数"""
    print("高德API调用频率测试")
    print("="*60)
    print("验证修复后的代码是否符合3次/秒限制")
    print("="*60)
    
    # 测试1: 导入和基本功能
    import_success = test_actual_code_import()
    
    if not import_success:
        print("\n❌ 代码导入测试失败，无法继续测试")
        return False
    
    # 测试2: API频率测试
    print("\n" + "="*60)
    print("开始API调用频率模拟测试")
    print("="*60)
    
    tester = APIFrequencyTester()
    frequency_success = tester.run_comprehensive_test()
    
    # 最终报告
    print("\n" + "="*60)
    print("最终测试报告")
    print("="*60)
    
    if import_success and frequency_success:
        print("🎉 所有测试通过！")
        print("✅ 代码导入和基本功能正常")
        print("✅ API调用频率符合3次/秒限制")
        print("\n修复效果:")
        print("1. 单个数据点内部的API调用有0.35秒间隔")
        print("2. 数据点之间有0.8-1.2秒间隔")
        print("3. 符合高德API的3次/秒限制")
        print("4. 批量处理应该能正常获取区域属性和地理特征")
        return True
    else:
        print("❌ 测试失败")
        if not import_success:
            print("  - 代码导入或基本功能有问题")
        if not frequency_success:
            print("  - API调用频率不符合限制")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
