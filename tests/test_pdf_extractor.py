"""
测试 pdf图纸名称提取.py 的基本功能
"""
import sys
from pathlib import Path

def test_imports():
    """测试所有导入是否正常"""
    print("测试导入模块...")
    try:
        import pdfplumber
        print("✓ pdfplumber")
    except ImportError as e:
        print(f"✗ pdfplumber: {e}")
        
    try:
        import fitz
        print("✓ PyMuPDF (fitz)")
    except ImportError as e:
        print(f"✗ PyMuPDF: {e}")
        
    try:
        import cv2
        print("✓ OpenCV (cv2)")
    except ImportError as e:
        print(f"✗ OpenCV: {e}")
        
    try:
        from PIL import Image
        print("✓ PIL (Pillow)")
    except ImportError as e:
        print(f"✗ PIL: {e}")
        
    try:
        import pandas as pd
        print("✓ pandas")
    except ImportError as e:
        print(f"✗ pandas: {e}")

def test_ocr_response_parser():
    """测试OCR响应解析函数"""
    print("\n测试OCR响应解析...")
    
    # 导入修复后的函数
    sys.path.insert(0, str(Path(__file__).parent))
    from pdf图纸名称提取 import _extract_text_from_ocr_response
    
    # 测试用例1: 正常的contents结构
    test_obj1 = {
        "contents": [
            {"content": "图纸名称：测试图纸"},
            {"content": ""}
        ]
    }
    result1 = _extract_text_from_ocr_response(test_obj1)
    assert "测试图纸" in result1, f"测试1失败: {result1}"
    print(f"✓ 测试1通过: {result1}")
    
    # 测试用例2: None对象
    test_obj2 = None
    result2 = _extract_text_from_ocr_response(test_obj2)
    assert result2 == "", f"测试2失败: {result2}"
    print("✓ 测试2通过: None对象返回空字符串")
    
    # 测试用例3: 空dict
    test_obj3 = {}
    result3 = _extract_text_from_ocr_response(test_obj3)
    assert result3 == "", f"测试3失败: {result3}"
    print("✓ 测试3通过: 空字典返回空字符串")
    
    # 测试用例4: DotsOCR格式
    test_obj4 = {
        "results": [
            {
                "full_layout_info": [
                    {"text": "设备布置平面图"},
                    {"text": "CBN-001"}
                ]
            }
        ]
    }
    result4 = _extract_text_from_ocr_response(test_obj4)
    assert "设备布置平面图" in result4, f"测试4失败: {result4}"
    print(f"✓ 测试4通过: {result4}")
    
    # 测试用例5: 简单text字段
    test_obj5 = {"text": "GPS馈线路由图"}
    result5 = _extract_text_from_ocr_response(test_obj5)
    assert result5 == "GPS馈线路由图", f"测试5失败: {result5}"
    print(f"✓ 测试5通过: {result5}")
    
    print("\n所有OCR响应解析测试通过！✓")

def test_drawing_name_extraction():
    """测试图名提取逻辑"""
    print("\n测试图名提取...")
    
    sys.path.insert(0, str(Path(__file__).parent))
    from pdf图纸名称提取 import _extract_drawing_name_from_ocr_text
    
    # 测试用例1: 标准格式
    text1 = "工程名称：广州南沙区\n图纸名称：设备布置平面图\n比例：1:100"
    result1 = _extract_drawing_name_from_ocr_text(text1)
    assert "设备布置平面图" in result1, f"测试1失败: {result1}"
    print(f"✓ 测试1通过: {result1}")
    
    # 测试用例2: 无标签格式
    text2 = "某某工程\nGPS馈线路由图\n出图日期：2024-01-01"
    result2 = _extract_drawing_name_from_ocr_text(text2)
    assert "GPS" in result2 or "馈线" in result2, f"测试2失败: {result2}"
    print(f"✓ 测试2通过: {result2}")
    
    print("\n所有图名提取测试通过！✓")

if __name__ == "__main__":
    print("=" * 60)
    print("PDF图纸名称提取工具 - 功能测试")
    print("=" * 60)
    
    try:
        test_imports()
        test_ocr_response_parser()
        test_drawing_name_extraction()
        
        print("\n" + "=" * 60)
        print("✓ 所有测试通过！程序已修复成功。")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
