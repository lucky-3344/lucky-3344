"""
处理用户提供的CSV文件 - 修复版本
专门处理 '已知经纬度点位的格式.csv' 的特殊格式
修复了文件保存问题
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

def read_user_csv_file(filename):
    """读取用户CSV文件，支持多种编码和特殊格式"""
    encodings = ['utf-8', 'gbk', 'gb2312', 'utf-8-sig', 'latin1']
    
    for encoding in encodings:
        try:
            print(f"尝试使用 {encoding} 编码读取文件...")
            with open(filename, 'r', encoding=encoding) as f:
                # 读取所有行
                lines = f.readlines()
                
            print(f"✅ 使用 {encoding} 编码读取成功")
            print(f"文件内容预览:")
            for i, line in enumerate(lines[:5]):  # 显示前5行
                print(f"  行{i+1}: {line.strip()}")
            
            # 解析CSV内容
            data_rows = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # 使用csv.reader解析每行
                reader = csv.reader([line])
                row = next(reader, [])
                if row:
                    data_rows.append(row)
            
            return data_rows
            
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"❌ {encoding} 编码读取异常: {e}")
            continue
    
    raise ValueError("无法读取CSV文件，所有编码尝试都失败")

def parse_user_row(row):
    """解析用户CSV文件的行数据"""
    if not row:
        return None, None, None
    
    print(f"原始行数据: {row}")
    
    # 用户文件格式分析:
    # 格式1: ['', '广州黄埔区WJ会议中心', '1', '113.41547', '23.23962', '113.41547,23.23962']
    # 格式2: ['广州黄埔区WJ会议中心', '1', '113.41547', '23.23962', '113.41547,23.23962']
    
    name = None
    lng = None
    lat = None
    
    # 尝试不同格式
    if len(row) >= 6:
        # 格式1: 第一列为空
        if row[0] == '' and row[1]:
            name = row[1].strip()
            try:
                lng = float(row[3].strip()) if len(row) > 3 else None
                lat = float(row[4].strip()) if len(row) > 4 else None
            except (ValueError, IndexError):
                pass
    elif len(row) >= 5:
        # 格式2: 没有空列
        name = row[0].strip()
        try:
            lng = float(row[2].strip()) if len(row) > 2 else None
            lat = float(row[3].strip()) if len(row) > 3 else None
        except (ValueError, IndexError):
            pass
    
    # 如果从数字列解析失败，尝试从坐标字符串解析
    if (lng is None or lat is None) and len(row) >= 5:
        # 尝试从最后一个列解析坐标字符串
        coord_str = row[-1].strip() if row[-1] else ''
        if ',' in coord_str:
            try:
                parts = coord_str.split(',')
                if len(parts) >= 2:
                    lng = float(parts[0].strip())
                    lat = float(parts[1].strip())
            except (ValueError, IndexError):
                pass
    
    return name, lng, lat

def get_area_info(lng, lat):
    """获取区域信息 - 返回市区、城区、郊区、县城、农村等类型"""
    try:
        key = get_amap_key()
        
        # 1. 使用逆地理编码获取地址信息
        url = "https://restapi.amap.com/v3/geocode/regeo"
        params = {
            "location": f"{lng},{lat}",
            "key": key,
            "extensions": "base",
            "output": "json"
        }
        
        print(f"  获取区域信息: {lng}, {lat}")
        resp = requests.get(url, params=params, timeout=10)
        
        if resp.status_code != 200:
            print(f"  HTTP错误 {resp.status_code}")
            return f"HTTP错误: {resp.status_code}"
        
        data = resp.json()
        if data['status'] != '1':
            error_msg = data.get('info', '未知错误')
            print(f"  API返回错误: {error_msg}")
            return f"API错误: {error_msg}"
        
        # 获取地址信息
        regeocode = data['regeocode']
        formatted_addr = regeocode.get('formatted_address', '')
        address_component = regeocode.get('addressComponent', {})
        province = address_component.get('province', '')
        city = address_component.get('city', '')
        district = address_component.get('district', '')
        township = address_component.get('township', '')
        
        print(f"  地址: {formatted_addr}")
        
        # 2. 获取周边POI密度
        poi_count = _get_poi_density(lng, lat, key)
        
        # 3. 分类区域类型
        area_type = _classify_area(formatted_addr, address_component, poi_count)
        
        # 4. 只返回区域类型（市区、郊区、县城、农村等）
        return area_type
            
    except Exception as e:
        print(f"  获取区域信息失败: {e}")
        return f"错误: {str(e)[:50]}"

def _get_poi_density(lng, lat, amap_key):
    """获取指定坐标周边的POI密度
    
    返回：1km范围内的POI数量
    """
    try:
        url = "https://restapi.amap.com/v3/place/around"
        params = {
            "location": f"{lng},{lat}",
            "key": amap_key,
            "radius": 1000,  # 1km范围
            "offset": 50,    # 最多返回50个结果
            "output": "json"
        }
        
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data['status'] == '1':
                return len(data.get('pois', []))
        return 0
    except:
        return 0

def _classify_area(formatted_address, address_component, poi_count):
    """根据地址信息和POI密度分类区域属性
    
    返回：市区、城区、郊区、县城、农村
    """
    try:
        township = address_component.get('township', '')
        district = address_component.get('district', '')
        
        # 构建完整地址用于关键词匹配
        full_address = formatted_address + district + township
        
        # 规则1：优先基于地址关键词分类
        # 市区/城区关键词
        urban_keywords = ['市辖区', '城市', '城中', '中心', '街道', '居委会', '社区', '商圈', '商业区']
        # 郊区关键词
        suburban_keywords = ['开发区', '工业区', '高新区', '科技园', '产业园', '保税区']
        # 县城关键词
        county_keywords = ['县城', '县', '县级市', '自治县']
        # 农村关键词
        rural_keywords = ['村', '农村', '乡村', '屯', '寨', '庄', '大队']
        
        # 检查郊区关键词（优先级最高）
        for keyword in suburban_keywords:
            if keyword in full_address:
                return "郊区"
        
        # 检查农村关键词
        for keyword in rural_keywords:
            if keyword in full_address:
                return "农村"
        
        # 检查县城关键词
        for keyword in county_keywords:
            if keyword in full_address:
                # 如果是县城，但POI密度很高，可能是县城城区
                if poi_count >= 10:
                    return "县城"
                else:
                    return "县城"  # 统一返回县城
        
        # 检查市区/城区关键词
        for keyword in urban_keywords:
            if keyword in full_address:
                # 如果包含市区关键词，根据POI密度区分市区/城区
                if poi_count >= 20:
                    return "市区"
                else:
                    return "城区"
        
        # 规则2：没有明确关键词时，基于POI密度分类
        if poi_count >= 25:
            return "市区"
        elif poi_count >= 15:
            return "城区"
        elif poi_count >= 8:
            # 中等POI密度，可能是县城或郊区
            if '县' in full_address:
                return "县城"
            else:
                return "郊区"
        elif poi_count >= 3:
            # 低POI密度，可能是郊区或农村
            if '镇' in full_address or '乡' in full_address:
                return "郊区"  # 乡镇归为郊区
            else:
                return "农村"
        else:
            # 极低POI密度
            return "农村"
            
    except Exception as e:
        return f"分类失败: {str(e)}"

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
                if any(k in addr for k in ['高速公路', '高速路', '高速']):
                    features.append('高速公路')
                if any(k in addr for k in ['铁路', '高铁', '轨道', '火车站']):
                    features.append('铁路')
                if any(k in addr for k in ['商场', '广场', '车站', '机场', '学校', '医院', '市场', '景区', '体育馆', '公园']):
                    features.append('人员密集处')
                if any(k in addr for k in ['路口', '交叉口', '十字路口']):
                    features.append('城镇交叉路口')
                if any(k in addr for k in ['拐角', '转角', '街角', '巷口']):
                    features.append('街巷拐角处')
                if any(k in addr for k in ['野外', '郊外', '田野', '荒野', '山野', '林场']):
                    features.append('野外')
                if any(k in addr for k in ['厂区', '工厂', '厂房', '工业区', '工业园']):
                    features.append('厂区')
                if any(k in addr for k in ['园区', '产业园', '科技园', '园']):
                    features.append('园区')
                
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

def process_user_file(input_file, output_file=None, delay=1.0):
    """处理用户CSV文件"""
    print("=" * 60)
    print("处理用户CSV文件 - 修复版本")
    print("=" * 60)
    
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return
    
    try:
        # 读取CSV文件
        data_rows = read_user_csv_file(input_file)
        total_rows = len(data_rows)
        
        print(f"📊 总行数: {total_rows}")
        print("")
        
        results = []
        success_rows = 0
        failed_rows = 0
        
        transformer = CoordTransform()
        
        # 处理每一行，跳过表头（第一行）
        for i, row in enumerate(data_rows):
            if not row:
                continue
            
            # 跳过表头行（通常第一行包含列名）
            if i == 0:
                # 检查是否包含表头关键词
                row_str = ''.join(row).lower()
                if any(keyword in row_str for keyword in ['名称', '地址', '经度', '纬度', '备注']):
                    print(f"跳过表头行: {row}")
                    continue
            
            try:
                # 解析行数据
                name, lng, lat = parse_user_row(row)
                
                if name is None:
                    name = f"行{i}"
                
                print(f"🔍 处理第{i}行: {name}")
                
                if lng is None or lat is None:
                    print(f"  ❌ 坐标解析失败")
                    failed_rows += 1
                    continue
                
                print(f"  坐标: WGS84({lng:.6f}, {lat:.6f})")
                
                # 转换到GCJ02
                gcj_lng, gcj_lat = transformer.wgs84_to_gcj02(lng, lat)
                print(f"  转换: GCJ02({gcj_lng:.6f}, {gcj_lat:.6f})")
                
                # 获取区域属性
                print("  获取区域属性...")
                area_info = get_area_info(lng, lat)
                
                # 获取地理特征
                print("  获取地理特征...")
                features_info = get_features(lng, lat)
                
                # 构建结果
                result = {
                    '名称': name,
                    'WGS84经度': round(lng, 6),
                    'WGS84纬度': round(lat, 6),
                    'GCJ02经度': round(gcj_lng, 6),
                    'GCJ02纬度': round(gcj_lat, 6),
                    '区域属性': area_info,
                    '地理特征': features_info,
                    '状态': '成功'
                }
                
                # 添加原始行数据（用于调试）
                result['原始数据'] = str(row)
                
                results.append(result)
                success_rows += 1
                
                print(f"  ✅ 完成")
                print(f"    区域: {area_info}")
                print(f"    特征: {features_info}")
                print("")
                
                # API频率控制
                time.sleep(delay)
                
            except Exception as e:
                print(f"  ❌ 处理失败: {e}")
                failed_rows += 1
                print("")
        
        # 输出结果
        print("=" * 60)
        print("处理完成!")
        print(f"✅ 成功: {success_rows} 行")
        print(f"❌ 失败: {failed_rows} 行")
        print(f"📊 总计: {total_rows} 行")
        
        # 保存结果
        if output_file and results:
            saved_file = save_results(results, output_file)
            if saved_file:
                print(f"💾 结果已保存到: {saved_file}")
                # 显示结果预览
                print("\n📊 结果预览:")
                for i, result in enumerate(results[:3]):  # 显示前3行
                    print(f"  第{i+1}行: {result['名称']}")
                    print(f"    区域: {result['区域属性']}")
                    print(f"    特征: {result['地理特征']}")
            else:
                print("❌ 结果保存失败，但处理数据已生成")
        else:
            print("⚠️  没有结果需要保存")
        
        return results
            
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

def save_results(results, output_file):
    """保存结果到文件 - 修复版本，处理文件被占用问题"""
    try:
        # 获取备用文件名
        base_name, ext = os.path.splitext(output_file)
        if not ext:
            ext = '.csv'
        
        # 尝试不同的文件名
        attempt = 0
        while attempt < 10:  # 最多尝试10个不同的文件名
            current_file = output_file if attempt == 0 else f"{base_name}_{attempt}{ext}"
            
            try:
                # 尝试打开文件写入
                with open(current_file, 'w', encoding='utf-8-sig', newline='') as f:
                    # 确定字段顺序
                    field_order = ['名称', 'WGS84经度', 'WGS84纬度', 'GCJ02经度', 'GCJ02纬度', 
                                  '区域属性', '地理特征', '状态', '原始数据']
                    
                    writer = csv.DictWriter(f, fieldnames=field_order)
                    writer.writeheader()
                    for result in results:
                        writer.writerow(result)
                
                print(f"✅ 成功保存到文件: {current_file}")
                return current_file
                
            except PermissionError:
                print(f"⚠️  文件被占用，尝试下一个文件名: {current_file}")
                attempt += 1
            except Exception as e:
                print(f"❌ 保存到 {current_file} 失败: {e}")
                attempt += 1
        
        # 所有尝试都失败，使用简单格式保存
        print("⚠️  所有文件名尝试都失败，使用简单文本格式保存")
        simple_file = "results_simple.txt"
        try:
            with open(simple_file, 'w', encoding='utf-8') as f:
                f.write("批量处理结果\n")
                f.write("=" * 50 + "\n")
                for result in results:
                    f.write(f"名称: {result['名称']}\n")
                    f.write(f"  坐标: {result['WGS84经度']}, {result['WGS84纬度']}\n")
                    f.write(f"  区域: {result['区域属性']}\n")
                    f.write(f"  特征: {result['地理特征']}\n")
                    f.write("-" * 30 + "\n")
            print(f"✅ 简单结果已保存到: {simple_file}")
            return simple_file
        except Exception as e:
            print(f"❌ 简单保存也失败: {e}")
            return None
            
    except Exception as e:
        print(f"❌ 保存结果过程中发生错误: {e}")
        return None

def main():
    """主函数"""
    input_file = r"D:\02 软件文件夹\工作软件\小工具\google_map_tools\已知经纬度点位的格式.csv"
    output_file = "user_file_results_fixed.csv"  # 使用不同的文件名避免冲突
    delay = 1.0
    
    print("🚀 开始处理用户文件 - 修复版本")
    print(f"输入文件: {input_file}")
    print(f"输出文件: {output_file} (如果被占用会自动使用备用名)")
    print(f"API延迟: {delay}秒")
    print("")
    
    results = process_user_file(input_file, output_file, delay)
    
    if results:
        print("\n🎉 处理完成!")
        print("可以使用以下命令查看结果:")
        print(f"  type user_file_results*.csv (Windows)")
        print(f"  cat user_file_results*.csv (Linux/Mac)")
    else:
        print("\n⚠️  处理失败或没有结果")

if __name__ == "__main__":
    main()
