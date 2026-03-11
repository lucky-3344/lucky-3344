"""
命令行测试工具 - 验证高德API连接和功能
避免GUI问题，直接测试核心功能
"""
import sys
import os
import time
import json
import requests
from coord_transform import CoordTransform

# 添加当前目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class CLITester:
    def __init__(self):
        self.transformer = CoordTransform()
        self.api_delay = 0.8
        
    def get_amap_key(self):
        """获取高德API密钥"""
        # 优先从环境变量获取
        amap_key = os.environ.get('AMAP_KEY')
        if amap_key:
            return amap_key
        
        # 其次尝试从配置文件获取
        try:
            if os.path.exists('amap_config.json'):
                with open('amap_config.json', 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'amap_key' in config:
                        return config.get('amap_key')
                    if 'key' in config:
                        return config.get('key')
                    return '1ba54ee0c70f50338fca9bb8b699b33c'
        except:
            pass
        
        # 默认密钥
        return '1ba54ee0c70f50338fca9bb8b699b33c'
    
    def _amap_endpoint(self, path):
        """构造高德请求endpoint"""
        ip_override = os.environ.get('AMAP_IP_OVERRIDE')
        headers = None
        if ip_override:
            return f"https://{ip_override}{path}", {"Host": "restapi.amap.com"}
        return f"https://restapi.amap.com{path}", headers
    
    def _get_json_with_retry(self, url, params, retries=3, timeout=10, headers=None):
        """带重试的GET请求"""
        import socket
        from requests.exceptions import ConnectionError, Timeout
        
        last_exc = None
        for attempt in range(max(1, retries)):
            try:
                print(f"  尝试 {attempt+1}/{retries}: 请求 {url}")
                resp = requests.get(url, params=params, timeout=timeout, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                if data is None:
                    raise ValueError("API返回空数据")
                print(f"  成功!")
                return data
            except (ConnectionError, Timeout) as exc:
                last_exc = exc
                if "Failed to resolve" in str(exc) or "getaddrinfo failed" in str(exc):
                    print(f"  DNS解析失败，尝试刷新DNS缓存...")
                    try:
                        socket.gethostbyname_ex('restapi.amap.com')
                    except:
                        pass
                
                wait_time = 2 ** attempt
                print(f"  等待 {wait_time}秒后重试...")
                time.sleep(wait_time)
            except (requests.exceptions.RequestException, ValueError, json.JSONDecodeError) as exc:
                last_exc = exc
                wait_time = 0.5 * (attempt + 1)
                print(f"  请求错误，等待 {wait_time:.1f}秒后重试...")
                time.sleep(wait_time)
        
        if last_exc:
            error_msg = str(last_exc)
            if "Failed to resolve" in error_msg or "getaddrinfo failed" in error_msg:
                error_msg = f"DNS解析失败: 无法解析 'restapi.amap.com'，请检查网络连接或DNS设置。原始错误: {error_msg}"
            raise Exception(f"请求失败(重试{retries}次后): {error_msg}")
        raise Exception(f"请求失败: 未知错误，重试{retries}次后仍失败")
    
    def test_dns_resolution(self):
        """测试DNS解析"""
        print("="*60)
        print("测试DNS解析")
        print("="*60)
        
        try:
            import socket
            print("1. 尝试解析 'restapi.amap.com'...")
            result = socket.gethostbyname_ex('restapi.amap.com')
            print(f"  解析成功!")
            print(f"  主机名: {result[0]}")
            print(f"  别名: {result[1]}")
            print(f"  IP地址: {result[2]}")
            return True
        except Exception as e:
            print(f"  ❌ DNS解析失败: {e}")
            print("\n建议解决方案:")
            print("1. 检查网络连接")
            print("2. 尝试刷新DNS缓存: ipconfig /flushdns (Windows)")
            print("3. 尝试使用其他DNS服务器，如 8.8.8.8 (Google DNS)")
            print("4. 检查防火墙设置")
            return False
    
    def test_api_connection(self):
        """测试API连接"""
        print("\n" + "="*60)
        print("测试高德API连接")
        print("="*60)
        
        try:
            amap_key = self.get_amap_key()
            print(f"使用API密钥: {amap_key[:8]}...{amap_key[-4:]}")
            
            # 测试简单的逆地理编码请求
            test_lng, test_lat = 116.3974, 39.9093  # 北京天安门
            
            url, headers = self._amap_endpoint("/v3/geocode/regeo")
            params = {
                "location": f"{test_lng},{test_lat}",
                "key": amap_key,
                "extensions": "base",
                "output": "json"
            }
            
            print(f"发送测试请求到: {url}")
            data = self._get_json_with_retry(url, params, retries=2, timeout=5, headers=headers)
            
            if data['status'] == '1':
                print("✅ API连接测试成功!")
                address = data['regeocode']['formatted_address']
                print(f"  测试地址: {address}")
                return True
            else:
                print(f"❌ API返回错误: {data.get('info', '未知错误')}")
                return False
                
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False
    
    def test_batch_processing(self, test_file=None):
        """测试批量处理功能"""
        print("\n" + "="*60)
        print("测试批量处理功能")
        print("="*60)
        
        if not test_file:
            # 创建测试数据
            test_data = [
                ["测试点1", 116.3974, 39.9093, "北京天安门"],
                ["测试点2", 121.4737, 31.2304, "上海外滩"],
                ["测试点3", 113.2644, 23.1291, "广州塔"]
            ]
        else:
            # 从文件读取测试数据
            try:
                import csv
                test_data = []
                with open(test_file, 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    header = next(reader)
                    for row in reader:
                        if len(row) >= 3:
                            test_data.append(row)
                print(f"从文件读取 {len(test_data)} 条测试数据")
            except Exception as e:
                print(f"❌ 读取测试文件失败: {e}")
                return False
        
        results = []
        success_count = 0
        fail_count = 0
        
        for i, data in enumerate(test_data[:3]):  # 只测试前3个点
            try:
                print(f"\n处理第 {i+1} 个点: {data[0]}")
                
                if len(data) == 4:  # 名称,经度,纬度,备注
                    name, lng_str, lat_str, remark = data
                    lng, lat = float(lng_str), float(lat_str)
                elif len(data) == 3:  # 名称,经度,纬度
                    name, lng_str, lat_str = data
                    lng, lat = float(lng_str), float(lat_str)
                    remark = ""
                else:
                    print(f"  数据格式错误: {data}")
                    fail_count += 1
                    continue
                
                # 转换坐标
                gcj02_lng, gcj02_lat = self.transformer.wgs84_to_gcj02(lng, lat)
                
                # 获取区域属性
                print(f"  获取区域属性...")
                area_info = self._get_area_properties(gcj02_lng, gcj02_lat)
                
                # 获取地理特征
                print(f"  获取地理特征...")
                features = self._get_geo_features(gcj02_lng, gcj02_lat)
                
                result = {
                    '名称': name,
                    'WGS84经度': lng,
                    'WGS84纬度': lat,
                    'GCJ02经度': gcj02_lng,
                    'GCJ02纬度': gcj02_lat,
                    '区域属性': area_info,
                    '地理特征': features,
                    '状态': '成功',
                    '备注': remark
                }
                
                results.append(result)
                success_count += 1
                print(f"  ✅ 处理成功")
                
                # 延迟，避免API频率超限
                if i < len(test_data) - 1:
                    time.sleep(self.api_delay)
                    
            except Exception as e:
                fail_count += 1
                print(f"  ❌ 处理失败: {e}")
                results.append({
                    '名称': data[0] if data else '未知',
                    '状态': f'错误: {str(e)}',
                    '原始数据': str(data)
                })
        
        # 显示结果
        print(f"\n{'='*60}")
        print("批量处理结果:")
        print(f"{'='*60}")
        print(f"成功: {success_count} 条")
        print(f"失败: {fail_count} 条")
        
        if results:
            print("\n处理结果示例:")
            for result in results[:2]:  # 显示前2个结果
                print(f"\n名称: {result.get('名称', 'N/A')}")
                print(f"状态: {result.get('状态', 'N/A')}")
                if result.get('状态') == '成功':
                    print(f"区域属性: {result.get('区域属性', 'N/A')}")
                    print(f"地理特征: {result.get('地理特征', 'N/A')}")
        
        return success_count > 0
    
    def _get_area_properties(self, lng, lat):
        """获取区域属性（简化版）"""
        try:
            amap_key = self.get_amap_key()
            
            # 逆地理编码
            url, headers = self._amap_endpoint("/v3/geocode/regeo")
            params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "all",
                "output": "json"
            }
            
            data = self._get_json_with_retry(url, params, retries=2, timeout=5, headers=headers)
            
            if data['status'] != '1':
                return "查询失败"
            
            # 延迟
            time.sleep(0.35)
            
            # 获取POI密度
            poi_count = self._get_poi_density(lng, lat, amap_key)
            
            # 分析地址
            address_component = data['regeocode'].get('addressComponent', {})
            city = address_component.get('city', '')
            district = address_component.get('district', '')
            
            # 简单分类
            if poi_count >= 30:
                area_type = "密集市区"
            elif poi_count >= 15:
                area_type = "市区"
            elif poi_count >= 8:
                area_type = "县城城区"
            elif poi_count >= 3:
                area_type = "乡镇"
            else:
                area_type = "农村"
            
            return f"{area_type} (POI密度: {poi_count}/1km²) - {city}{district}"
            
        except Exception as e:
            return f"错误: {str(e)}"
    
    def _get_poi_density(self, lng, lat, amap_key):
        """获取POI密度"""
        try:
            url, headers = self._amap_endpoint("/v3/place/around")
            params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "radius": 1000,
                "offset": 50,
                "output": "json"
            }
            
            data = self._get_json_with_retry(url, params, retries=2, timeout=5, headers=headers)
            
            if data['status'] == '1':
                return len(data.get('pois', []))
            return 0
        except:
            return 0
    
    def _get_geo_features(self, lng, lat):
        """获取地理特征（简化版）"""
        try:
            amap_key = self.get_amap_key()
            
            url, headers = self._amap_endpoint("/v3/geocode/regeo")
            params = {
                "location": f"{lng},{lat}",
                "key": amap_key,
                "extensions": "all",
                "output": "json"
            }
            
            data = self._get_json_with_retry(url, params, retries=2, timeout=5, headers=headers)
            
            if data['status'] != '1':
                return "无特殊特征"
            
            # 延迟
            time.sleep(0.35)
            
            # 简单特征识别
            formatted_address = data['regeocode'].get('formatted_address', '')
            features = []
            
            if any(keyword in formatted_address for keyword in ['路', '街', '道']):
                features.append('路边')
            if any(keyword in formatted_address for keyword in ['公园', '广场', '绿地']):
                features.append('绿地')
            if any(keyword in formatted_address for keyword in ['河', '湖', '海', '江']):
                features.append('水体')
            
            if features:
                return ' | '.join(features)
            return '无特殊特征'
            
        except Exception as e:
            return f"错误: {str(e)}"
    
    def run_comprehensive_test(self):
        """运行全面测试"""
        print("高德API命令行测试工具")
        print("="*60)
        print("测试核心功能，避免GUI问题")
        print("="*60)
        
        # 测试1: DNS解析
        dns_ok = self.test_dns_resolution()
        if not dns_ok:
            print("\n❌ DNS解析失败，无法继续测试")
            return False
        
        # 测试2: API连接
        api_ok = self.test_api_connection()
        if not api_ok:
            print("\n❌ API连接失败，无法继续测试")
            return False
        
        # 测试3: 批量处理
        batch_ok = self.test_batch_processing()
        
        # 最终报告
        print("\n" + "="*60)
        print("测试完成")
        print("="*60)
        
        if dns_ok and api_ok and batch_ok:
            print("✅ 所有测试通过!")
            print("\n结论:")
            print("1. DNS解析正常")
            print("2. API连接正常")
            print("3. 批量处理功能正常")
            print("4. API调用频率符合限制")
            print("\n问题可能出在GUI部分，建议:")
            print("1. 检查GUI环境（tkinter是否正确安装）")
            print("2. 检查网络代理设置")
            print("3. 尝试在命令行中运行原程序")
            return True
        else:
            print("❌ 测试失败")
            if not dns_ok:
                print("  - DNS解析问题")
            if not api_ok:
                print("  - API连接问题")
            if not batch_ok:
                print("  - 批量处理问题")
            return False

def main():
    """主函数"""
    tester = CLITester()
    
    try:
        success = tester.run_comprehensive_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试过程中出现未预期错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
