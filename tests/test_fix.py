"""
测试修复后的本地图片生成器
"""

import os
import sys
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'image_gen'))

from simple_image_gen import generate_image_from_text

def test_fixed_generator():
    """测试修复后的生成器"""
    print("[TEST] 测试修复后的本地图片生成器")
    print("="*50)
    
    # 测试不同类型的图片生成
    test_cases = [
        {"prompt": "abstract colorful shapes", "width": 512, "height": 512},
        {"prompt": "gradient background with geometric patterns", "width": 768, "height": 512},
        {"prompt": "pattern design with circles and rectangles", "width": 600, "height": 600},
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n测试 {i}: {case['prompt']}")
        
        try:
            result = generate_image_from_text(
                prompt=case['prompt'],
                width=case['width'],
                height=case['height']
            )
            
            if result['success']:
                print(f"   [SUCCESS] 成功: {os.path.basename(result['image_path'])}")
                print(f"   [SIZE] 尺寸: {case['width']}x{case['height']}")
            else:
                print(f"   [FAILED] 失败: {result['message']}")
                
        except Exception as e:
            print(f"   [ERROR] 错误: {str(e)}")
    
    print(f"\n{'='*50}")
    print("[COMPLETE] 测试完成！修复后的生成器应该解决了椭圆坐标问题。")

if __name__ == "__main__":
    test_fixed_generator()