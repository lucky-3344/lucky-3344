#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
地理特征识别功能测试脚本
Version: 2.2.0
Purpose: 快速验证新增的地理特征识别功能是否正常工作
"""

import json
import os
import sys
from pathlib import Path

# 配置路径
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

# 导入主程序
try:
    from google_maps_tool import GoogleMapsTools
    print("✅ 成功导入 GoogleMapsTools")
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    sys.exit(1)


class GeoFeaturesTestSuite:
    """地理特征识别测试套件"""
    
    def __init__(self):
        self.tool = GoogleMapsTools()
        self.results = []
        self.test_count = 0
        self.pass_count = 0
        self.fail_count = 0
        
        # 测试坐标库
        self.test_coords = {
            "北京西二旗": {"lng": 116.3974, "lat": 39.9093, "expected": ["路边", "十字路口"]},
            "北京怀柔": {"lng": 116.5023, "lat": 40.0556, "expected": ["高山"]},
            "北京朝阳区": {"lng": 116.4669, "lat": 39.9726, "expected": ["路边"]},
            "北京水立方": {"lng": 116.4084, "lat": 39.9902, "expected": ["水体", "绿地"]},
        }
    
    def print_header(self, text):
        """打印测试标题"""
        print("\n" + "="*60)
        print(f"  {text}")
        print("="*60)
    
    def print_success(self, text):
        """打印成功信息"""
        print(f"✅ {text}")
        self.pass_count += 1
    
    def print_error(self, text):
        """打印错误信息"""
        print(f"❌ {text}")
        self.fail_count += 1
    
    def print_info(self, text):
        """打印信息"""
        print(f"ℹ️  {text}")
    
    def print_warning(self, text):
        """打印警告"""
        print(f"⚠️  {text}")
    
    def test_method_existence(self):
        """测试：确认新增方法存在"""
        self.print_header("测试1: 确认新增方法存在")
        
        methods = [
            'get_geo_features',
            '_get_nearby_pois',
            '_analyze_poi_directions',
            '_is_high_altitude_area',
            '_format_features',
        ]
        
        for method_name in methods:
            self.test_count += 1
            if hasattr(self.tool, method_name):
                self.print_success(f"方法 {method_name}() 存在")
            else:
                self.print_error(f"方法 {method_name}() 不存在")
    
    def test_single_point_analysis(self):
        """测试：单点地理特征分析"""
        self.print_header("测试2: 单点地理特征分析")
        
        for location, coords in self.test_coords.items():
            self.test_count += 1
            lng = coords['lng']
            lat = coords['lat']
            
            try:
                self.print_info(f"分析位置: {location} ({lng}, {lat})")
                
                features = self.tool.get_geo_features(lng, lat)
                
                if features and isinstance(features, dict):
                    self.print_success(f"{location} 特征识别成功")
                    
                    # 显示识别结果
                    detected_features = [f for f, detected in features.items() if detected]
                    if detected_features:
                        self.print_info(f"  发现特征: {', '.join(detected_features)}")
                    else:
                        self.print_info(f"  无特殊特征")
                else:
                    self.print_error(f"{location} 返回数据格式异常: {features}")
            
            except Exception as e:
                self.print_error(f"{location} 分析失败: {str(e)}")
    
    def test_format_features(self):
        """测试：特征格式化"""
        self.print_header("测试3: 特征格式化")
        
        test_features = [
            {"路边": True, "十字路口": False, "高山": False, "屋面": False, "水体": False, "绿地": False},
            {"路边": False, "十字路口": True, "高山": False, "屋面": False, "水体": False, "绿地": False},
            {"路边": False, "十字路口": False, "高山": False, "屋面": False, "水体": True, "绿地": True},
            {"路边": False, "十字路口": False, "高山": False, "屋面": False, "水体": False, "绿地": False},
        ]
        
        for i, features in enumerate(test_features):
            self.test_count += 1
            try:
                formatted = self.tool._format_features(features)
                self.print_success(f"格式化用例 {i+1}: {formatted}")
            except Exception as e:
                self.print_error(f"格式化用例 {i+1} 失败: {str(e)}")
    
    def test_csv_export_structure(self):
        """测试：CSV导出结构"""
        self.print_header("测试4: 检查CSV导出结构")
        
        self.test_count += 1
        
        # 检查导入方法是否包含地理特征处理
        import inspect
        import_csv_source = inspect.getsource(self.tool.import_csv)
        
        if 'get_geo_features' in import_csv_source:
            self.print_success("import_csv() 包含地理特征处理")
        else:
            self.print_warning("import_csv() 可能缺少地理特征处理")
        
        if '地理特征' in import_csv_source:
            self.print_success("CSV导出包含'地理特征'字段")
        else:
            self.print_warning("CSV导出可能缺少'地理特征'字段")
    
    def test_ui_components(self):
        """测试：UI组件"""
        self.print_header("测试5: 检查UI组件")
        
        self.test_count += 1
        
        # 检查UI中是否包含地理特征显示
        import inspect
        try:
            source = inspect.getsource(self.tool.setup_ui)
            
            if 'features_frame' in source or 'features_result' in source:
                self.print_success("UI包含地理特征显示组件")
            else:
                self.print_warning("UI可能缺少地理特征显示组件")
        except Exception as e:
            self.print_error(f"UI检查失败: {str(e)}")
    
    def test_api_configuration(self):
        """测试：API配置"""
        self.print_header("测试6: API配置检查")
        
        self.test_count += 1
        
        # 检查API密钥 (程序使用AMAP_KEY)
        api_key = os.getenv('AMAP_KEY')
        if api_key:
            self.print_success(f"环境变量 AMAP_KEY 已设置 (前4位: {api_key[:4]}...)")
        else:
            self.print_warning("环境变量 AMAP_KEY 未设置，尝试读取配置文件")
            
            config_file = PROJECT_ROOT / 'amap_config.json'
            if config_file.exists():
                try:
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    if 'api_key' in config and config['api_key']:
                        self.print_success(f"配置文件中已设置API密钥 (前4位: {config['api_key'][:4]}...)")
                    else:
                        self.print_error("配置文件中API密钥为空")
                except Exception as e:
                    self.print_error(f"读取配置文件失败: {str(e)}")
            else:
                self.print_warning("配置文件 amap_config.json 不存在")
    
    def print_summary(self):
        """打印测试总结"""
        self.print_header("测试总结")
        
        print(f"\n📊 测试统计:")
        print(f"   总测试数: {self.test_count}")
        print(f"   通过: {self.pass_count} ✅")
        print(f"   失败: {self.fail_count} ❌")
        
        if self.fail_count == 0:
            print(f"\n🎉 所有测试都通过了！新功能已准备就绪。")
        else:
            print(f"\n⚠️  有 {self.fail_count} 个测试失败，请检查上方错误信息。")
        
        print("\n" + "="*60)
    
    def run_all_tests(self):
        """运行所有测试"""
        print("\n")
        print("╔" + "="*58 + "╗")
        print("║" + " " * 58 + "║")
        print("║" + "  🧪 地理特征识别功能测试 v2.2.0".center(58) + "║")
        print("║" + " " * 58 + "║")
        print("╚" + "="*58 + "╝")
        
        self.test_method_existence()
        self.test_api_configuration()
        self.test_format_features()
        self.test_csv_export_structure()
        self.test_ui_components()
        
        # 只有配置了API密钥才进行单点分析
        if os.getenv('AMAP_KEY') or (Path(PROJECT_ROOT / 'amap_config.json')).exists():
            try:
                self.test_single_point_analysis()
            except Exception as e:
                self.print_warning(f"单点分析测试跳过: {str(e)}")
        else:
            self.print_warning("跳过单点分析测试 (未配置API密钥)")
        
        self.print_summary()


def main():
    """主函数"""
    try:
        suite = GeoFeaturesTestSuite()
        suite.run_all_tests()
        
        # 返回状态码
        sys.exit(0 if suite.fail_count == 0 else 1)
    
    except Exception as e:
        print(f"\n❌ 测试执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
