#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速功能验证 - 地理特征识别v2.2.0
Quick Feature Verification Script
"""

import sys
from pathlib import Path

# 配置
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    """测试导入"""
    print("="*70)
    print("  🧪 快速功能验证 - v2.2.0")
    print("="*70)
    print("\n[1/3] 测试导入...\n")
    
    try:
        from google_maps_tool import GoogleMapsTools
        print("✅ GoogleMapsTools 导入成功")
        
        tool = GoogleMapsTools()
        print("✅ GoogleMapsTools 实例化成功")
        
        return tool
    except Exception as e:
        print(f"❌ 导入失败: {e}")
        sys.exit(1)


def test_methods(tool):
    """测试方法存在性"""
    print("\n[2/3] 测试新增方法...\n")
    
    methods = [
        'get_geo_features',
        '_get_nearby_pois',
        '_analyze_poi_directions',
        '_is_high_altitude_area',
        '_format_features',
    ]
    
    all_exist = True
    for method_name in methods:
        if hasattr(tool, method_name):
            print(f"✅ 方法存在: {method_name}()")
        else:
            print(f"❌ 方法缺失: {method_name}()")
            all_exist = False
    
    return all_exist


def test_feature_format(tool):
    """测试特征格式化"""
    print("\n[3/3] 测试特征格式化...\n")
    
    test_cases = [
        {"路边": True, "十字路口": False, "高山": False, "屋面": False, "水体": False, "绿地": False},
        {"路边": False, "十字路口": True, "高山": False, "屋面": False, "水体": False, "绿地": False},
        {"路边": False, "十字路口": False, "高山": False, "屋面": False, "水体": True, "绿地": True},
    ]
    
    for i, features in enumerate(test_cases, 1):
        try:
            formatted = tool._format_features(features)
            print(f"✅ 用例{i}: {formatted}")
        except Exception as e:
            print(f"❌ 用例{i}失败: {e}")
            return False
    
    return True


def print_summary(results):
    """打印总结"""
    print("\n" + "="*70)
    print("  📊 验证结果")
    print("="*70)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    print(f"\n验证项: {total}")
    for name, result in results.items():
        icon = "✅" if result else "❌"
        print(f"  {icon} {name}")
    
    print(f"\n通过率: {passed}/{total} ({100*passed//total}%)")
    
    if passed == total:
        print("\n🎉 所有快速验证通过！")
        print("\n后续步骤:")
        print("  1. 配置高德API密钥")
        print("  2. 运行: python test_geo_features.py (完整测试)")
        print("  3. 运行: python google_maps_tool.py (启动GUI)")
        return True
    else:
        print("\n⚠️ 存在验证失败，请检查错误信息")
        return False


def main():
    try:
        tool = test_imports()
        methods_ok = test_methods(tool)
        format_ok = test_feature_format(tool)
        
        results = {
            "导入": True,
            "新增方法": methods_ok,
            "特征格式化": format_ok,
        }
        
        success = print_summary(results)
        
        print("\n" + "="*70 + "\n")
        
        sys.exit(0 if success else 1)
    
    except Exception as e:
        print(f"\n❌ 验证出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
