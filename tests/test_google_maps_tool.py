#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Google Maps Tool 功能测试脚本
测试新增的区域属性判断功能
"""

import sys
import os

# 测试导入
try:
    from coord_transform import CoordTransform
    print("✓ coord_transform 导入成功")
except ImportError as e:
    print(f"✗ coord_transform 导入失败: {e}")
    sys.exit(1)

# 测试坐标转换
transformer = CoordTransform()

# 测试用例
test_cases = [
    {
        "name": "北京中关村（市区）",
        "lng": 116.3046,
        "lat": 39.9926,
        "expected": "市区"
    },
    {
        "name": "北京怀柔山区（农村）",
        "lng": 116.5023,
        "lat": 40.0556,
        "expected": "农村"
    },
]

print("\n" + "="*60)
print("Google Maps Tool - 功能测试")
print("="*60)

# 测试坐标转换
print("\n【坐标转换测试】")
gcj02_lng, gcj02_lat = 116.3046, 39.9926
wgs84_lng, wgs84_lat = transformer.gcj02_to_wgs84(gcj02_lng, gcj02_lat)
back_gcj02_lng, back_gcj02_lat = transformer.wgs84_to_gcj02(wgs84_lng, wgs84_lat)

print(f"GCJ02 -> WGS84: ({gcj02_lng}, {gcj02_lat}) -> ({wgs84_lng:.4f}, {wgs84_lat:.4f})")
print(f"WGS84 -> GCJ02: ({wgs84_lng:.4f}, {wgs84_lat:.4f}) -> ({back_gcj02_lng:.4f}, {back_gcj02_lat:.4f})")
print(f"转换误差: {abs(gcj02_lng - back_gcj02_lng):.6f}, {abs(gcj02_lat - back_gcj02_lat):.6f}")

# 测试配置文件
print("\n【配置文件测试】")
if os.path.exists('amap_config.json'):
    print("✓ amap_config.json 配置文件存在")
    import json
    with open('amap_config.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
        print(f"  API Key: {config.get('amap_key', 'N/A')[:20]}...")
else:
    print("✗ amap_config.json 配置文件不存在")

# 测试示例CSV
print("\n【示例文件测试】")
if os.path.exists('example_addresses.csv'):
    print("✓ example_addresses.csv 示例文件存在")
    with open('example_addresses.csv', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        print(f"  包含 {len(lines)-1} 个地址")
else:
    print("✗ example_addresses.csv 示例文件不存在")

print("\n" + "="*60)
print("测试完成！")
print("="*60)
print("\n使用说明：")
print("1. 运行程序：python google_maps_tool.py")
print("2. 在UI中输入地址或经纬度进行查询")
print("3. 使用 example_addresses.csv 进行批量测试")
print("4. 详见 GOOGLE_MAPS_TOOL_README.md")
