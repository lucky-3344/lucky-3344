"""
简单批量处理工具
不使用GUI，直接处理CSV文件
"""
import csv
import json
import os
import sys
import time
import requests
from coord_transform import CoordTransform

def get_amap_key():
    """获取API密钥"""
    key = os.environ.get('AMAP_KEY')
    if key:
        return key
    
    try:
        if os.path.exists('amap_config.json'):
            with open('amap_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get('amap_key', config.get('key', '1ba54ee0c70f50338fca9bb8b699b33c'))
    except:
        pass
    
    return '1ba54ee0c70f50338fca9bb8b699b33c'

def read_csv_file(filename):
    """读取CSV文件，支持多种编码"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
    
    for encoding in encodings:
        try:
            print(f"尝试使用 {encoding} 编码读取文件...")
            with open(filename, 'r', encoding=encoding) as f:
                reader = csv.reader(f)
                header = next(reader, [])
                data_rows = list(reader)
            print(f"✅ 使用 {encoding} 编码读取成功")
            return header, data_rows
        except UnicodeDecodeError:
            continue
        except Exception:
            continue
    
    raise ValueError("无法读取CSV文件，所有编码尝试都失败")

def get_area_info(lng, lat):
    """获取区域信息"""
    try:
        key = get_amap_key()
        
        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "location": f"{lng},{lat}",
            "key": key,
            "extensions": "base"
        }
        
        print(f"  获取区域信息: {lng}, {lat}")
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data['status'] == '1':
                addr = data['regeocode']
                province = addr.get('addressComponent', {}).get('province', '')
                city = addr.get('addressComponent', {}).get('city', '')
                district = addr.get('addressComponent', {}).get('district', '')
                
                formatted_addr = addr.get('formatted_address', '')
                print(f"  地址: {formatted_addr}")
                
                return f"{province}{city}{district}"
            else:
                error_msg = data.get('info', '未知错误')
                print(f"  API返回错误: {error_msg}")
                return f"API错误: {error_msg}"
        else:
            print(f"  HTTP错误 {resp.status_code}")
            return f"HTTP错误: {resp.status_code}"
            
    except Exception as e:
        print(f"  获取区域信息失败: {e}")
        return f"错误: {str(e)[:50]}"

def get_features(lng, lat):
    """获取地理特征"""
    try:
        key = get_amap_key()
        
        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "location": f"{lng},{lat}",
            "key": key,
            "extensions": "base"
        }
        
        print(f"  获取地理特征: {lng}, {lat}")
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if data['status'] == '1':
                addr = data['regeocode'].get('formatted_address', '')
                print(f"  分析地址: {addr}")
                
                features = []
                if any(k in addr for k in ['路', '街', '道', '大道', '公路']):
                    features.append('路边')
                if any(k in addr for k in ['公园', '广场', '绿地', '花园', '草坪']):
                    features.append('绿地')
                if any(k in addr for k in ['河', '湖', '海', '江', '溪', '水']):
                    features.append('水体')
                if any(k in addr for k in ['山', '峰', '岭', '丘']):
                    features.append('山地')
                if any(k in addr for k in ['楼', '大厦', '写字楼', '办公楼']):
                    features.append('建筑')
                
                result = ' | '.join(features) if features else '无特殊特征'
                print(f"  地理特征: {result}")
                return result
            else:
                error_msg = data.get('info', '未知错误')
                print(f"  API返回错误: {error_msg}")
                return f"API错误: {error_msg}"
        else:
            print(f"  HTTP错误 {resp.status_code}")
            return f"HTTP错误: {resp.status_code}"
            
    except Exception as e:
        print(f"  获取地理特征失败: {e}")
        return f"错误: {str(e)[:50]}"

def process_csv(input_file, output_file=None, delay=1.0):
    """处理CSV文件"""
    print("=" * 60)
    print("简单批量处理工具")
    print("=" * 60)
    
    if not os.path.exists(input_file):
        print(f"文件不存在: {input_file}")
        return
    
    try:
        # 读取CSV文件
        header, data_rows = read_csv_file(input_file)
        total_rows = len(data_rows)
        
        print(f"总行数: {total_rows}")
        print("")
        
        results = []
        success_rows = 0
        failed_rows = 0
        
        transformer = CoordTransform()
        
        # 处理每一行
        for i, row in enumerate(data_rows):
            if not row or len(row) < 2:
                continue
            
            try:
                # 获取行标识
                row_id = f"行{i+1}"
                if len(row) > 0 and row[0].strip():
                    row_id = row[0].strip()
                
                print(f"处理第{i+1}行: {row_id}")
                
                # 解析坐标（假设前两列是经度和纬度）
                try:
                    lng = float(row[1].strip()) if len(row) > 1 else None
                    lat = float(row[2].strip()) if len(row) > 2 else None
                    
                    if lng is None or lat is None:
                        print(f"  坐标格式错误")
                        failed_rows += 1
                        continue
                    
                    print(f"  坐标: WGS84({lng:.6f}, {lat:.6f})")
                    
                    # 转换到GCJ02
                    gcj_lng, gcj_lat = transformer.wgs84_to_gcj02(lng, lat)
                    print(f"  转换: GCJ02({gcj_lng:.6f}, {gcj_lat:.6f})")
                    
                except (ValueError, IndexError):
                    print(f"  坐标解析失败")
                    failed_rows += 1
                    continue
                
                # 获取区域属性
                print("  获取区域属性...")
                area_info = get_area_info(lng, lat)
                
                # 获取地理特征
                print("  获取地理特征...")
                features_info = get_features(lng, lat)
                
                # 构建结果
                result = {
                    '名称': row_id,
                    'WGS84经度': round(lng, 6),
                    'WGS84纬度': round(lat, 6),
                    'GCJ02经度': round(gcj_lng, 6),
                    'GCJ02纬度': round(gcj_lat, 6),
                    '区域属性': area_info,
                    '地理特征': features_info,
                    '状态': '成功'
                }
                
                # 添加备注（如果有）
                if len(row) > 3 and row[3].strip():
                    result['备注'] = row[3].strip()
                
                results.append(result)
                success_rows += 1
                
                print(f"  完成")
                print(f"    区域: {area_info}")
                print(f"    特征: {features_info}")
                print("")
                
                # API频率控制
                time.sleep(delay)
                
            except Exception as e:
                print(f"  处理失败: {e}")
                failed_rows += 1
                print("")
        
        # 输出结果
        print("=" * 60)
        print("处理完成!")
        print(f"成功: {success_rows} 行")
        print(f"失败: {failed_rows} 行")
        print(f"总计: {total_rows} 行")
        
        # 保存结果
        if output_file and results:
            save_results(results, output_file)
            print(f"结果已保存到: {output_file}")
        
        return results
            
    except Exception as e:
        print(f"处理失败: {e}")
        import traceback
        traceback.print_exc()

def save_results(results, output_file):
    """保存结果到文件"""
    try:
        # 确定字段顺序
        field_order = ['名称', 'WGS84经度', 'WGS84纬度', 'GCJ02经度', 'GCJ02纬度', 
                      '区域属性', '地理特征', '状态', '备注']
        
        # 只保留实际存在的字段
        actual_fields = []
        for field in field_order:
            if any(field in result for result in results):
                actual_fields.append(field)
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=actual_fields)
            writer.writeheader()
            for result in results:
                # 只写入实际存在的字段
                row = {field: result.get(field, '') for field in actual_fields}
                writer.writerow(row)
                
    except Exception as e:
        print(f"保存结果失败: {e}")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='简单批量处理CSV文件')
    parser.add_argument('input', help='输入CSV文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（可选）', default=None)
    parser.add_argument('-d', '--delay', type=float, help='API调用延迟（秒）', default=1.0)
    
    args = parser.parse_args()
    
    print("开始批量处理...")
    print(f"输入文件: {args.input}")
    if args.output:
        print(f"输出文件: {args.output}")
    print(f"API延迟: {args.delay}秒")
    print("")
    
    results = process_csv(args.input, args.output, args.delay)
    
    if results:
        print("\n批量处理完成!")
        if args.output:
            print(f"结果已保存到: {args.output}")
            print("可以使用以下命令查看结果:")
            print(f"  type {args.output} (Windows)")
            print(f"  cat {args.output} (Linux/Mac)")
    else:
        print("\n批量处理失败或没有结果")

if __name__ == "__main__":
    main()
