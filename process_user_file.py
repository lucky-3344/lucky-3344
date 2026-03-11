"""
处理用户提供的CSV文件
专门处理 '已知经纬度点位的格式.csv' 的特殊格式
"""
import csv
import argparse
import json
import os
import sys
import time
import requests
import socket
import tempfile
import webbrowser
import ipaddress
from urllib.parse import urlparse, urlunparse
try:
    import pandas as pd
except Exception:
    pd = None
from coord_transform import CoordTransform

# 默认使用系统网络设置（与之前可用的 process 行为一致）
FORCE_DIRECT_AMAP = False
FORCE_NO_PROXY = False
AMAP_IP_OVERRIDE = None
AMAP_IP_OVERRIDES = []
DEFAULT_AMAP_IPS = [
    "106.11.28.122",
    "106.11.28.33"
]
NO_PROXY_SETTINGS = {"http": None, "https": None}
DNS_FAILURE_KEYWORDS = (
    "failed to resolve",
    "name resolution",
    "getaddrinfo failed",
    "temporary failure in name resolution",
    "name or service not known",
    "nodename nor servname provided",
    "nxdomain",
    "resolver error",
    "nameresolutionerror"
)

def _load_amap_settings():
    """从环境变量/配置文件读取高德连接策略"""
    global FORCE_DIRECT_AMAP, FORCE_NO_PROXY, AMAP_IP_OVERRIDE, AMAP_IP_OVERRIDES
    env_force_direct = os.environ.get("AMAP_FORCE_DIRECT")
    env_force_no_proxy = os.environ.get("AMAP_FORCE_NO_PROXY")
    if env_force_direct is not None:
        FORCE_DIRECT_AMAP = env_force_direct.strip() in ("1", "true", "True", "YES", "yes")
    if env_force_no_proxy is not None:
        FORCE_NO_PROXY = env_force_no_proxy.strip() in ("1", "true", "True", "YES", "yes")

    AMAP_IP_OVERRIDE = os.environ.get('AMAP_IP_OVERRIDE')
    env_overrides = os.environ.get('AMAP_IP_OVERRIDES')
    if env_overrides:
        AMAP_IP_OVERRIDES = [x.strip() for x in env_overrides.split(',') if x.strip()]

    try:
        cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'amap_config.json')
        if os.path.exists(cfg_path):
            with open(cfg_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if env_force_direct is None:
                FORCE_DIRECT_AMAP = bool(config.get("force_direct_amap", FORCE_DIRECT_AMAP))
            if env_force_no_proxy is None:
                FORCE_NO_PROXY = bool(config.get("force_no_proxy", FORCE_NO_PROXY))
            if not AMAP_IP_OVERRIDE:
                AMAP_IP_OVERRIDE = config.get("amap_ip_override")
            if not AMAP_IP_OVERRIDES:
                cfg_list = config.get("amap_ip_overrides")
                if isinstance(cfg_list, list):
                    AMAP_IP_OVERRIDES = [str(x).strip() for x in cfg_list if str(x).strip()]
    except Exception:
        pass

_load_amap_settings()

def _amap_endpoint(path):
    """根据可选的 IP 覆盖构造高德请求 endpoint 和 headers"""
    headers = None
    ip_override = AMAP_IP_OVERRIDE or (AMAP_IP_OVERRIDES[0] if AMAP_IP_OVERRIDES else None)
    if ip_override:
        ip_override = ip_override.strip()
        if ip_override.startswith("http://") or ip_override.startswith("https://"):
            ip_override = ip_override.split("//", 1)[-1]
        ip_override = ip_override.rstrip("/")
        if ip_override:
            return f"https://{ip_override}{path}", {"Host": "restapi.amap.com"}
    if FORCE_DIRECT_AMAP:
        return f"https://restapi.amap.com{path}", headers
    return f"https://restapi.amap.com{path}", headers

def _is_dns_error(exc):
    """判断是否与 DNS 解析有关"""
    if not exc:
        return False
    cause = getattr(exc, '__cause__', None) or getattr(exc, '__context__', None)
    if isinstance(cause, socket.gaierror):
        return True
    text = str(exc).lower()
    return any(keyword in text for keyword in DNS_FAILURE_KEYWORDS)

def _is_ip_host(hostname):
    if not hostname:
        return False
    try:
        ipaddress.ip_address(hostname)
        return True
    except Exception:
        return False

def _to_amap_hostname_url(url):
    parsed = urlparse(url)
    if not parsed.hostname:
        return url
    return urlunparse(parsed._replace(netloc="restapi.amap.com"))

def _try_direct_ip_requests(url, params, timeout, headers, proxies):
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return None, None
    candidate_ips = AMAP_IP_OVERRIDES or DEFAULT_AMAP_IPS
    if not candidate_ips:
        return None, None
    last_exc = None
    for ip in candidate_ips:
        ip_headers = dict(headers or {})
        ip_headers['Host'] = host
        ip_url = urlunparse(parsed._replace(netloc=ip))
        proxy_options = [proxies]
        if proxies != NO_PROXY_SETTINGS:
            proxy_options.append(NO_PROXY_SETTINGS)
        for ip_proxies in proxy_options:
            try:
                resp = requests.get(ip_url, params=params, timeout=timeout, headers=ip_headers, proxies=ip_proxies)
                if resp.status_code == 200:
                    return resp.json(), None
                last_exc = Exception(f"HTTP错误: {resp.status_code}")
            except Exception as exc:
                last_exc = exc
    return None, last_exc

def _get_json_with_retry(url, params, retries=2, timeout=10, headers=None):
    """GET 请求（禁用代理，减少解析失败）"""
    last_exc = None
    proxy_modes = [None]
    if FORCE_NO_PROXY:
        proxy_modes = [{"http": None, "https": None}, None]
    for _ in range(max(1, retries)):
        for proxies in proxy_modes:
            try:
                resp = requests.get(url, params=params, timeout=timeout, headers=headers, proxies=proxies)
                if resp.status_code != 200:
                    raise Exception(f"HTTP错误: {resp.status_code}")
                return resp.json()
            except Exception as exc:
                last_exc = exc
                try:
                    parsed = urlparse(url)
                    if _is_ip_host(parsed.hostname) and _is_dns_error(exc):
                        host_url = _to_amap_hostname_url(url)
                        host_headers = dict(headers or {})
                        host_headers.pop("Host", None)
                        resp = requests.get(host_url, params=params, timeout=timeout, headers=host_headers, proxies=proxies)
                        if resp.status_code == 200:
                            return resp.json()
                        last_exc = Exception(f"HTTP错误: {resp.status_code}")
                except Exception as exc_host:
                    last_exc = exc_host
                time.sleep(0.3)
                if url.startswith("https://"):
                    try:
                        http_url = "http://" + url.split("https://", 1)[-1]
                        resp = requests.get(http_url, params=params, timeout=timeout, headers=headers, proxies=proxies)
                        if resp.status_code != 200:
                            raise Exception(f"HTTP错误: {resp.status_code}")
                        return resp.json()
                    except Exception as exc2:
                        last_exc = exc2
                        time.sleep(0.3)
                        if _is_dns_error(exc2):
                            ip_data, ip_exc = _try_direct_ip_requests(url, params, timeout, headers, proxies)
                            if ip_data is not None:
                                return ip_data
                            if ip_exc is not None:
                                last_exc = ip_exc
                    if "NameResolutionError" in str(exc) or "Failed to resolve" in str(exc):
                        try:
                            ip_data, ip_exc = _try_direct_ip_requests(url, params, timeout, headers, proxies)
                            if ip_data is not None:
                                return ip_data
                            if ip_exc is not None:
                                last_exc = ip_exc
                        except Exception as exc3:
                            last_exc = exc3
                    elif _is_dns_error(exc):
                        ip_data, ip_exc = _try_direct_ip_requests(url, params, timeout, headers, proxies)
                        if ip_data is not None:
                            return ip_data
                        if ip_exc is not None:
                            last_exc = ip_exc
        raise Exception(str(last_exc) if last_exc else "未知错误")

def _is_error_result(text):
    if not text:
        return True
    return any(k in text for k in ["网络错误", "HTTP错误", "API错误", "查询失败", "分析出错", "请求超时", "错误"])

def _log(message, log_content=None):
    if log_content is not None:
        log_content.append(message)
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def _log_network_info(log_content=None):
    _log(f"网络配置: FORCE_DIRECT_AMAP={FORCE_DIRECT_AMAP}, FORCE_NO_PROXY={FORCE_NO_PROXY}, AMAP_IP_OVERRIDE={AMAP_IP_OVERRIDE}", log_content)
    if AMAP_IP_OVERRIDES:
        _log(f"IP直连候选: {', '.join(AMAP_IP_OVERRIDES)}", log_content)
    try:
        ips = {item[4][0] for item in socket.getaddrinfo("restapi.amap.com", None)}
        _log(f"DNS解析: restapi.amap.com -> {', '.join(sorted(ips))}", log_content)
    except Exception as e:
        _log(f"DNS解析失败: {e}", log_content)
        if not (AMAP_IP_OVERRIDE or AMAP_IP_OVERRIDES):
            _log("提示: 可在 amap_config.json 中配置 amap_ip_override 或 amap_ip_overrides 绕过DNS", log_content)

def _auto_save_batch_results(results, source_filename):
    """自动保存批量结果到同目录（优先xlsx，其次csv）"""
    if not results:
        return None
    output_dir = os.path.dirname(source_filename)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    base_name = f"batch_results_{timestamp}"
    candidates = [
        os.path.join(output_dir, f"{base_name}.xlsx"),
        os.path.join(output_dir, f"{base_name}.csv")
    ]
    for idx in range(5):
        for candidate in candidates:
            target = candidate if idx == 0 else candidate.replace(base_name, f"{base_name}_{idx}")
            try:
                if pd is not None and target.endswith(".xlsx"):
                    df = pd.DataFrame(results)
                    df.columns = [
                        (str(c).strip() if str(c).strip() not in ("", "None", "nan") else f"列{i+1}")
                        for i, c in enumerate(df.columns)
                    ]
                    preferred = [
                        "名称", "地址", "WGS84经度", "WGS84纬度", "GCJ02经度", "GCJ02纬度",
                        "区域属性", "地理特征", "POI", "到道路距离", "商圈", "地址标准化",
                        "状态", "备注", "原始数据"
                    ]
                    cols = [c for c in preferred if c in df.columns] + [c for c in df.columns if c not in preferred]
                    df = df[cols]
                    df.to_excel(target, index=False)
                    return target
                else:
                    field_order = [
                        '名称', '地址', 'WGS84经度', 'WGS84纬度', 'GCJ02经度', 'GCJ02纬度',
                        '区域属性', '地理特征', 'POI', '到道路距离', '商圈', '地址标准化',
                        '状态', '原始数据'
                    ]
                    with open(target, 'w', encoding='utf-8-sig', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=field_order)
                        writer.writeheader()
                        for result in results:
                            writer.writerow(result)
                    return target
            except Exception:
                continue
    return None

def _create_batch_kml(results, source_filename):
    """生成批量KML文件（WGS84坐标）"""
    if not results:
        return None
    output_dir = os.path.dirname(source_filename)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"batch_results_{timestamp}.kml")
    kml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<kml xmlns="http://www.opengis.net/kml/2.2">',
           '<Document>']
    for result in results:
        if result.get('状态') != '成功':
            continue
        name = result.get("地址") or result.get("名称") or "点位"
        kml.extend([
            '  <Placemark>',
            f'    <name>{name}</name>',
            '    <Point>',
            f'      <coordinates>{result["WGS84经度"]},{result["WGS84纬度"]},0</coordinates>',
            '    </Point>',
            '  </Placemark>'
        ])
    kml.extend(['</Document>', '</kml>'])
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(kml))
    return filename

def _open_batch_in_google_maps(results):
    points = [r for r in results if r.get('状态') == '成功']
    if not points:
        return
    if len(points) > 20:
        points = points[:20]
    import webbrowser
    for result in points:
        try:
            lng = result["WGS84经度"]
            lat = result["WGS84纬度"]
            url = f"https://www.google.com/maps?q={lat},{lng}"
            webbrowser.open(url)
            time.sleep(0.2)
        except Exception:
            continue

def _open_batch_in_amap(results):
    html_file = _create_amap_html(results, "")
    if html_file:
        try:
            os.startfile(html_file)
        except Exception:
            pass

def _haversine_meters(lng1, lat1, lng2, lat2):
    """计算两点距离（米）"""
    try:
        import math
        r = 6371000.0
        rad = math.radians
        dlat = rad(lat2 - lat1)
        dlng = rad(lng2 - lng1)
        a = math.sin(dlat / 2) ** 2 + math.cos(rad(lat1)) * math.cos(rad(lat2)) * math.sin(dlng / 2) ** 2
        c = 2 * math.asin(min(1.0, math.sqrt(a)))
        return r * c
    except Exception:
        return None

def _geocode_address(address):
    """用高德地址解析获取坐标（GCJ02）"""
    if not address:
        return None, None, None
    try:
        url, headers = _amap_endpoint("/v3/geocode/geo")
        params = {
            "address": address,
            "key": get_amap_key(),
            "city": "",
            "output": "json"
        }
        data = _get_json_with_retry(url, params, retries=2, timeout=10, headers=headers)
        if data.get('status') == '1' and data.get('geocodes'):
            geo = data['geocodes'][0]
            location = geo.get('location', '')
            if ',' in location:
                gcj_lng, gcj_lat = map(float, location.split(','))
                return gcj_lng, gcj_lat, geo.get('formatted_address', '')
        return None, None, None
    except Exception:
        return None, None, None

def _create_amap_html(results, source_filename):
    """生成高德单页地图HTML（GCJ02坐标）"""
    if not results:
        return None
    amap_key = get_amap_key()
    points = [r for r in results if r.get('状态') == '成功']
    if not points:
        return None

    output_dir = os.path.dirname(source_filename) if source_filename else os.getcwd()
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(output_dir, f"batch_results_{timestamp}_amap.html")

    coords = []
    for r in points:
        try:
            lng = float(r["GCJ02经度"])
            lat = float(r["GCJ02纬度"])
            coords.append((lng, lat, r.get("名称") or r.get("地址") or "点位"))
        except Exception:
            continue
    if not coords:
        return None

    center_lng = sum(c[0] for c in coords) / len(coords)
    center_lat = sum(c[1] for c in coords) / len(coords)

    markers_js = "\n".join([
        f"new AMap.Marker({{position: [{lng}, {lat}], title: {json.dumps(name, ensure_ascii=False)}}}).setMap(map);"
        for lng, lat, name in coords
    ])

    html = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1.0\" />
  <title>高德地图批量点位</title>
  <style>html,body,#map{{width:100%;height:100%;margin:0;padding:0;}}</style>
  <script src=\"https://webapi.amap.com/maps?v=2.0&key={amap_key}\"></script>
</head>
<body>
  <div id=\"map\"></div>
  <script>
    var map = new AMap.Map('map', {{
      zoom: 12,
      center: [{center_lng}, {center_lat}]
    }});
    {markers_js}
    map.setFitView();
  </script>
</body>
</html>"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    return filename

def _create_amap_uri(results, max_points=200):
    """生成高德URI多点链接"""
    points = [r for r in results if r.get('状态') == '成功']
    if not points:
        return None
    markers = []
    for r in points[:max_points]:
        try:
            lng = float(r["GCJ02经度"])
            lat = float(r["GCJ02纬度"])
            name = r.get("名称") or r.get("地址") or "点位"
            markers.append(f"{lng},{lat},{name}")
        except Exception:
            continue
    if not markers:
        return None
    import urllib.parse
    marker_str = "|".join(markers)
    return "https://uri.amap.com/marker?markers=" + urllib.parse.quote(marker_str, safe=",")

def get_amap_key():
    """获取API密钥"""
    key = os.environ.get('AMAP_KEY')
    if key:
        return key
    
    try:
        if os.path.exists('amap_config.json'):
            with open('amap_config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                cfg_key = config.get('amap_key') or config.get('key')
                if cfg_key:
                    return cfg_key
    except:
        pass

    # 不再内置默认密钥，避免将敏感信息写入代码仓库
    return 'YOUR_AMAP_KEY'

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

def _build_header_map(header_row):
    """构建表头到索引的映射"""
    header_map = {}
    for i, col in enumerate(header_row):
        name = str(col).strip().lstrip('\ufeff')
        if name:
            header_map[name] = i
    return header_map

def _get_float_from_row(row, idx):
    try:
        return float(str(row[idx]).strip())
    except Exception:
        return None

def parse_user_row(row):
    """解析用户CSV文件的行数据"""
    if not row:
        return None, None, None
    
    print(f"原始行数据: {row}")
    
    # 用户文件格式分析:
    # 格式1: ['', 'XX会议中心', '1', '113.41547', '23.23962', '113.41547,23.23962']
    # 格式2: ['XX会议中心', '1', '113.41547', '23.23962', '113.41547,23.23962']
    
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
        regeo_url, regeo_headers = _amap_endpoint("/v3/geocode/regeo")
        params = {
            "location": f"{lng},{lat}",
            "key": key,
            "extensions": "base",
            "output": "json"
        }

        print(f"  获取区域信息: {lng}, {lat}")
        data = _get_json_with_retry(regeo_url, params, retries=2, timeout=10, headers=regeo_headers)

        if data.get('status') != '1':
            error_msg = data.get('info', '未知错误')
            print(f"  API返回错误: {error_msg}")
            return f"API错误: {error_msg}"

        regeocode = data.get('regeocode', {})
        formatted_addr = regeocode.get('formatted_address', '')
        address_component = regeocode.get('addressComponent', {})

        print(f"  地址: {formatted_addr}")

        poi_count = _get_poi_density(lng, lat, key)
        area_type = _classify_area(formatted_addr, address_component, poi_count)
        return area_type

    except Exception as e:
        print(f"  获取区域信息失败: {e}")
        return f"错误: {str(e)[:50]}"

def _get_poi_density(lng, lat, amap_key):
    """获取指定坐标周边的POI密度（1km范围内）"""
    try:
        poi_url, poi_headers = _amap_endpoint("/v3/place/around")
        params = {
            "location": f"{lng},{lat}",
            "key": amap_key,
            "radius": 1000,
            "offset": 50,
            "output": "json"
        }
        data = _get_json_with_retry(poi_url, params, retries=2, timeout=5, headers=poi_headers)
        if data.get('status') == '1':
            return len(data.get('pois', []))
        return 0
    except Exception:
        return 0

def _classify_area(formatted_address, address_component, poi_count):
    """根据地址信息和POI密度分类区域属性"""
    try:
        township = address_component.get('township', '')
        district = address_component.get('district', '')
        full_address = formatted_address + district + township

        urban_keywords = ['市辖区', '城市', '城中', '中心', '街道', '居委会', '社区', '商圈', '商业区']
        suburban_keywords = ['开发区', '工业区', '高新区', '科技园', '产业园', '保税区']
        county_keywords = ['县城', '县', '县级市', '自治县']
        rural_keywords = ['村', '农村', '乡村', '屯', '寨', '庄', '大队']

        for keyword in suburban_keywords:
            if keyword in full_address:
                return "郊区"

        for keyword in rural_keywords:
            if keyword in full_address:
                return "农村"

        for keyword in county_keywords:
            if keyword in full_address:
                return "县城"

        for keyword in urban_keywords:
            if keyword in full_address:
                if poi_count >= 20:
                    return "市区"
                return "城区"

        if poi_count >= 25:
            return "市区"
        if poi_count >= 15:
            return "城区"
        if poi_count >= 8:
            return "县城" if '县' in full_address else "郊区"
        if poi_count >= 3:
            return "郊区" if ('镇' in full_address or '乡' in full_address) else "农村"
        return "农村"
    except Exception as e:
        return f"分类失败: {str(e)}"

def get_features(lng, lat, return_addr=False):
    """获取地理特征"""
    try:
        key = get_amap_key()
        regeo_url, regeo_headers = _amap_endpoint("/v3/geocode/regeo")
        params = {
            "location": f"{lng},{lat}",
            "key": key,
            "extensions": "base",
            "output": "json"
        }

        print(f"  获取地理特征: {lng}, {lat}")
        data = _get_json_with_retry(regeo_url, params, retries=2, timeout=10, headers=regeo_headers)

        if data.get('status') != '1':
            error_msg = data.get('info', '未知错误')
            print(f"  API返回错误: {error_msg}")
            return f"API错误: {error_msg}"

        addr = data.get('regeocode', {}).get('formatted_address', '')
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
        if return_addr:
            return result, addr
        return result

    except Exception as e:
        print(f"  获取地理特征失败: {e}")
        if return_addr:
            return f"错误: {str(e)[:50]}", ""
        return f"错误: {str(e)[:50]}"

def _get_regeo_details(lng, lat, amap_key=None):
    """获取POI/道路距离/商圈/标准化地址"""
    amap_key = amap_key or get_amap_key()
    regeo_url, regeo_headers = _amap_endpoint("/v3/geocode/regeo")
    params = {
        "location": f"{lng},{lat}",
        "key": amap_key,
        "extensions": "all",
        "output": "json"
    }
    data = _get_json_with_retry(regeo_url, params, retries=2, timeout=10, headers=regeo_headers)
    if data.get('status') != '1':
        error_msg = data.get('info', '未知错误')
        raise Exception(f"API错误: {error_msg}")

    regeocode = data.get('regeocode', {})
    formatted_addr = regeocode.get('formatted_address', '')
    pois = regeocode.get('pois', []) or []
    roads = regeocode.get('roads', []) or []
    business_areas = regeocode.get('addressComponent', {}).get('businessAreas', []) or []

    poi_names = [p.get('name') for p in pois if p.get('name')]
    poi_text = "、".join(poi_names[:3]) if poi_names else "无"

    road_distance = "无"
    for road in roads:
        dist = road.get('distance')
        if dist is not None:
            road_distance = str(dist)
            break

    biz_names = [b.get('name') for b in business_areas if b.get('name')]
    biz_text = "、".join(biz_names[:3]) if biz_names else "无"

    return {
        "poi": poi_text,
        "distance_to_road": road_distance,
        "business_area": biz_text,
        "standard_address": formatted_addr
    }

def process_user_file(input_file, output_file=None, delay=1.0):
    """处理用户CSV文件"""
    print("=" * 60)
    print("处理用户CSV文件")
    print("=" * 60)
    
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return
    
    return process_user_file_batch(input_file, output_file=output_file, delay=delay)

def process_user_file_batch(input_file, output_file=None, delay=1.0, open_google=False, open_amap=False):
    """批量处理用户CSV文件（带日志与自动保存）"""
    if not os.path.exists(input_file):
        print(f"❌ 文件不存在: {input_file}")
        return
    try:
        log_content = []
        _log(f"开始处理CSV文件: {input_file}", log_content)
        _log(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}", log_content)
        _log_network_info(log_content)

        data_rows = read_user_csv_file(input_file)
        total_rows = len(data_rows)
        _log(f"总行数: {total_rows}", log_content)
        if not data_rows:
            print("⚠️ CSV文件为空")
            return

        results = []
        success_rows = 0
        failed_rows = 0
        transformer = CoordTransform()

        header_map = None
        if data_rows:
            header_map = _build_header_map(data_rows[0])

        for i, row in enumerate(data_rows):
            if not row:
                continue
            if i == 0:
                row_str = ''.join(row).lower()
                if any(keyword in row_str for keyword in ['名称', '地址', '经度', '纬度', '备注']):
                    _log(f"跳过表头行: {row}", log_content)
                    continue
            try:
                name = None
                lng = None
                lat = None

                if header_map:
                    name_idx = header_map.get('名称')
                    addr_idx = header_map.get('地址')
                    if name_idx is not None and name_idx < len(row):
                        name = str(row[name_idx]).strip()
                    if (not name) and addr_idx is not None and addr_idx < len(row):
                        name = str(row[addr_idx]).strip()

                    wgs_lng_idx = header_map.get('WGS84经度') or header_map.get('经度')
                    wgs_lat_idx = header_map.get('WGS84纬度') or header_map.get('纬度')
                    if wgs_lng_idx is not None and wgs_lat_idx is not None:
                        if wgs_lng_idx < len(row) and wgs_lat_idx < len(row):
                            lng = _get_float_from_row(row, wgs_lng_idx)
                            lat = _get_float_from_row(row, wgs_lat_idx)

                if lng is None or lat is None:
                    parsed_name, parsed_lng, parsed_lat = parse_user_row(row)
                    if not name and parsed_name:
                        name = parsed_name
                    if parsed_lng is not None and parsed_lat is not None:
                        lng, lat = parsed_lng, parsed_lat
                if name is None:
                    name = f"行{i}"

                _log(f"处理第{i}行: {name}", log_content)

                filled_from_address = False
                if lng is None or lat is None:
                    geo_gcj_lng, geo_gcj_lat, geo_addr = _geocode_address(name)
                    if geo_gcj_lng is not None and geo_gcj_lat is not None:
                        lng, lat = transformer.gcj02_to_wgs84(geo_gcj_lng, geo_gcj_lat)
                        gcj_lng, gcj_lat = geo_gcj_lng, geo_gcj_lat
                        filled_from_address = True
                        _log("未提供坐标，已通过高德地址解析补齐坐标", log_content)
                    else:
                        failed_rows += 1
                        _log("坐标解析失败，且地址解析无法补齐", log_content)
                        continue
                else:
                    gcj_lng, gcj_lat = transformer.wgs84_to_gcj02(lng, lat)
                    geo_gcj_lng, geo_gcj_lat, geo_addr = _geocode_address(name)

                geo_wgs_lng = geo_wgs_lat = None
                diff_m = None
                analysis_source = "原始坐标"
                if filled_from_address:
                    analysis_lng, analysis_lat = lng, lat
                    analysis_source = "地址解析(补坐标)"
                    geo_wgs_lng, geo_wgs_lat = lng, lat
                elif geo_gcj_lng is not None and geo_gcj_lat is not None:
                    geo_wgs_lng, geo_wgs_lat = transformer.gcj02_to_wgs84(geo_gcj_lng, geo_gcj_lat)
                    diff_m = _haversine_meters(float(lng), float(lat), float(geo_wgs_lng), float(geo_wgs_lat))
                    analysis_lng, analysis_lat = geo_wgs_lng, geo_wgs_lat
                    analysis_source = "地址解析"
                else:
                    analysis_lng, analysis_lat = lng, lat

                area_info = get_area_info(analysis_lng, analysis_lat)
                features_info, regeo_addr = get_features(analysis_lng, analysis_lat, return_addr=True)
                try:
                    details = _get_regeo_details(analysis_lng, analysis_lat)
                except Exception as detail_err:
                    details = {
                        "poi": f"错误: {str(detail_err)[:50]}",
                        "distance_to_road": "错误",
                        "business_area": "错误",
                        "standard_address": ""
                    }

                status_text = '成功'
                if _is_error_result(area_info) or _is_error_result(features_info):
                    status_text = '网络错误'
                    _log(f"行{i}: 区域属性={area_info} | 地理特征={features_info}", log_content)

                result = {
                    '名称': name,
                    '地址': name,
                    'WGS84经度': round(float(lng), 6),
                    'WGS84纬度': round(float(lat), 6),
                    'GCJ02经度': round(gcj_lng, 6),
                    'GCJ02纬度': round(gcj_lat, 6),
                    '逆地理地址': regeo_addr,
                    '地址解析地址': geo_addr,
                    '地址解析GCJ02经度': round(geo_gcj_lng, 6) if geo_gcj_lng is not None else '',
                    '地址解析GCJ02纬度': round(geo_gcj_lat, 6) if geo_gcj_lat is not None else '',
                    '地址解析WGS84经度': round(geo_wgs_lng, 6) if geo_wgs_lng is not None else '',
                    '地址解析WGS84纬度': round(geo_wgs_lat, 6) if geo_wgs_lat is not None else '',
                    '坐标差异米': f"{diff_m:.1f}" if diff_m is not None else '',
                    '区域属性': area_info,
                    '地理特征': features_info,
                    'POI': details.get('poi'),
                    '到道路距离': details.get('distance_to_road'),
                    '商圈': details.get('business_area'),
                    '地址标准化': details.get('standard_address'),
                    '分析坐标来源': analysis_source,
                    '状态': status_text,
                    '原始数据': str(row)
                }

                results.append(result)
                success_rows += 1
                _log(f"行{i}: 完成", log_content)

                time.sleep(delay)

            except Exception as e:
                failed_rows += 1
        def process_user_file_batch(input_file, output_file=None, delay=1.0, open_google=False, open_amap=False):
                _log(f"行{i}: 处理失败 - {e}", log_content)

        log_filename = f"batch_processing_log_{int(time.time())}.txt"
        with open(log_filename, 'w', encoding='utf-8') as log_file:
            log_file.write('\n'.join(log_content))

        if output_file and results:
            save_results(results, output_file)
            _log(f"结果已保存到: {output_file}", log_content)

        auto_file = _auto_save_batch_results(results, input_file)
        if auto_file:
            _log(f"自动保存结果: {auto_file}", log_content)

        kml_file = _create_batch_kml(results, input_file)
        if kml_file:
            _log(f"自动生成KML: {kml_file}", log_content)

        if open_google:
            _open_batch_in_google_maps(results)
        if open_amap:
            _open_batch_in_amap(results)

        print("=" * 60)
        print("处理完成!")
        print(f"✅ 成功: {success_rows} 行")
        print(f"❌ 失败: {failed_rows} 行")
        print(f"📊 总计: {total_rows} 行")
        print(f"🧾 日志: {log_filename}")

        return results
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()

def save_results(results, output_file):
    """保存结果到文件"""
    try:
        # 确定字段顺序
        field_order = ['名称', 'WGS84经度', 'WGS84纬度', 'GCJ02经度', 'GCJ02纬度', 
                      '区域属性', '地理特征', '状态', '原始数据']
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=field_order)
            writer.writeheader()
            for result in results:
                writer.writerow(result)
                
    except Exception as e:
        print(f"❌ 保存结果失败: {e}")


class ProcessUserGUI:
    """基于 process_user_file 的GUI（单点+批量）"""
    def __init__(self):
        import tkinter as tk
        from tkinter import ttk, filedialog, messagebox, simpledialog
        self.tk = tk
        self.ttk = ttk
        self.filedialog = filedialog
        self.messagebox = messagebox
        self.simpledialog = simpledialog

        self.transformer = CoordTransform()
        self.batch_results = []
        self.api_delay = 0.8
        self._setup_gui()

    def _setup_gui(self):
        self.root = self.tk.Tk()
        self.root.title("坐标转换与区域分析（process版）")
        self.root.geometry("640x650")

        # 地址搜索
        search_frame = self.ttk.LabelFrame(self.root, text="地址搜索", padding=10)
        search_frame.pack(fill='x', padx=10, pady=5)

        self.search_var = self.tk.StringVar()
        self.ttk.Entry(search_frame, textvariable=self.search_var, width=55).pack(side='left', padx=5)
        self.ttk.Button(search_frame, text="搜索", command=self.search_location).pack(side='left')

        # 坐标显示
        coord_frame = self.ttk.LabelFrame(self.root, text="坐标信息", padding=10)
        coord_frame.pack(fill='x', padx=10, pady=5)

        self.wgs84_coords = self.tk.StringVar()
        self.gcj02_coords = self.tk.StringVar()

        self.ttk.Label(coord_frame, text="WGS84 坐标:").grid(row=0, column=0, sticky='w')
        self.ttk.Label(coord_frame, textvariable=self.wgs84_coords).grid(row=0, column=1, sticky='w')

        self.ttk.Label(coord_frame, text="GCJ02 坐标:").grid(row=1, column=0, sticky='w')
        self.ttk.Label(coord_frame, textvariable=self.gcj02_coords).grid(row=1, column=1, sticky='w')

        # 操作按钮
        button_frame = self.ttk.Frame(self.root, padding=10)
        button_frame.pack(fill='x')

        self.ttk.Button(button_frame, text="在Google地图网页中打开",
                        command=lambda: self.open_in_maps("google_web")).pack(side='left', padx=5)
        self.ttk.Button(button_frame, text="在Google Earth中打开",
                        command=lambda: self.open_in_maps("google_earth")).pack(side='left', padx=5)
        self.ttk.Button(button_frame, text="在高德地图中打开",
                        command=lambda: self.open_in_maps("amap")).pack(side='left', padx=5)
        self.ttk.Button(button_frame, text="复制KML代码",
                        command=self.copy_kml).pack(side='left', padx=5)

        # 区域属性判断
        area_frame = self.ttk.LabelFrame(self.root, text="区域属性判断", padding=10)
        area_frame.pack(fill='x', padx=10, pady=5)

        coord_input_frame = self.ttk.Frame(area_frame)
        coord_input_frame.pack(fill='x', pady=5)

        self.ttk.Label(coord_input_frame, text="经纬度 (格式:经,纬)").pack(side='left', padx=5)
        self.coord_var = self.tk.StringVar()
        self.ttk.Entry(coord_input_frame, textvariable=self.coord_var, width=30).pack(side='left', padx=5)
        self.ttk.Button(coord_input_frame, text="分析", command=self.analyze_area).pack(side='left', padx=5)
        self.ttk.Button(coord_input_frame, text="Google导航", command=lambda: self.open_coord_navigation("google")).pack(side='left', padx=5)
        self.ttk.Button(coord_input_frame, text="高德导航", command=lambda: self.open_coord_navigation("amap")).pack(side='left', padx=5)
        self.ttk.Button(coord_input_frame, text="Google Earth", command=self.open_coord_google_earth).pack(side='left', padx=5)

        self.area_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(area_frame, text="区域属性:").pack(side='left', padx=5)
        self.ttk.Label(area_frame, textvariable=self.area_result_var, foreground='blue').pack(side='left', padx=5)

        self.features_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(area_frame, text="地理特征:").pack(side='left', padx=5)
        self.ttk.Label(area_frame, textvariable=self.features_result_var, foreground='darkgreen').pack(side='left', padx=5)

        details_frame = self.ttk.Frame(area_frame)
        details_frame.pack(fill='x', pady=5)

        self.poi_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(details_frame, text="POI:").grid(row=0, column=0, sticky='w', padx=5)
        self.ttk.Label(details_frame, textvariable=self.poi_result_var).grid(row=0, column=1, sticky='w')

        self.distance_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(details_frame, text="到道路距离:").grid(row=1, column=0, sticky='w', padx=5)
        self.ttk.Label(details_frame, textvariable=self.distance_result_var).grid(row=1, column=1, sticky='w')

        self.business_result_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(details_frame, text="商圈:").grid(row=2, column=0, sticky='w', padx=5)
        self.ttk.Label(details_frame, textvariable=self.business_result_var).grid(row=2, column=1, sticky='w')

        self.standard_addr_var = self.tk.StringVar(value="未分析")
        self.ttk.Label(details_frame, text="地址标准化:").grid(row=3, column=0, sticky='w', padx=5)
        self.ttk.Label(details_frame, textvariable=self.standard_addr_var).grid(row=3, column=1, sticky='w')

        # 批量处理
        batch_frame = self.ttk.LabelFrame(self.root, text="批量处理", padding=10)
        batch_frame.pack(fill='x', padx=10, pady=5)

        self.ttk.Button(batch_frame, text="选择CSV并运行(BAT)", command=self.run_cli_bat).pack(side='left', padx=5)
        self.ttk.Button(batch_frame, text="生成KML并打开(Google Earth)", command=self.generate_kml_from_file).pack(side='left', padx=5)
        self.ttk.Button(batch_frame, text="高德地图一图打开", command=self.open_amap_from_file).pack(side='left', padx=5)

        # 网络设置
        net_frame = self.ttk.LabelFrame(self.root, text="网络设置", padding=10)
        net_frame.pack(fill='x', padx=10, pady=5)

        self.force_direct_var = self.tk.BooleanVar(value=FORCE_DIRECT_AMAP)
        self.no_proxy_var = self.tk.BooleanVar(value=FORCE_NO_PROXY)
        self.ip_override_var = self.tk.StringVar(value=AMAP_IP_OVERRIDE or "")

        self.ttk.Checkbutton(net_frame, text="强制直连", variable=self.force_direct_var).pack(side='left', padx=5)
        self.ttk.Checkbutton(net_frame, text="禁用代理", variable=self.no_proxy_var).pack(side='left', padx=5)
        self.ttk.Label(net_frame, text="IP直连:").pack(side='left', padx=5)
        self.ttk.Entry(net_frame, textvariable=self.ip_override_var, width=24).pack(side='left', padx=5)
        self.ttk.Button(net_frame, text="应用", command=self.apply_network_settings).pack(side='left', padx=5)
        self.ttk.Button(net_frame, text="诊断DNS", command=self.diagnose_dns).pack(side='left', padx=5)

        log_frame = self.ttk.LabelFrame(self.root, text="运行日志", padding=10)
        log_frame.pack(fill='both', padx=10, pady=5, expand=True)
        self.log_text = self.tk.Text(log_frame, height=10, wrap='word')
        log_scroll = self.ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side='left', fill='both', expand=True)
        log_scroll.pack(side='right', fill='y')

    def _log(self, message, log_content=None):
        if log_content is not None:
            log_content.append(message)
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        try:
            self.log_text.insert("end", line + "\n")
            self.log_text.see("end")
        except Exception:
            pass
        print(line)

    def apply_network_settings(self):
        global FORCE_DIRECT_AMAP, FORCE_NO_PROXY, AMAP_IP_OVERRIDE
        FORCE_DIRECT_AMAP = bool(self.force_direct_var.get())
        FORCE_NO_PROXY = bool(self.no_proxy_var.get())
        AMAP_IP_OVERRIDE = self.ip_override_var.get().strip() or None
        self._log(f"已应用网络设置: FORCE_DIRECT_AMAP={FORCE_DIRECT_AMAP}, FORCE_NO_PROXY={FORCE_NO_PROXY}, AMAP_IP_OVERRIDE={AMAP_IP_OVERRIDE}")

    def diagnose_dns(self):
        log_content = []
        _log_network_info(log_content)
        self._log("DNS诊断完成，详情见日志。")

    def search_location(self):
        """搜索地址获取坐标"""
        address = self.search_var.get().strip()
        if not address:
            self.messagebox.showwarning("警告", "请输入搜索地址")
            return
        try:
            location_data = self._do_search(address)
            if location_data:
                self._update_coords(location_data)
            else:
                self.messagebox.showerror("错误", "未找到该地址，请尝试更准确的关键词")
        except Exception as e:
            self.messagebox.showerror("错误", f"搜索失败: {str(e)}")

    def _do_search(self, address):
        amap_key = get_amap_key()
        url, headers = _amap_endpoint("/v3/geocode/geo")
        params = {
            "address": address,
            "key": amap_key,
            "city": "",
            "output": "json"
        }
        data = _get_json_with_retry(url, params, retries=2, timeout=10, headers=headers)
        if data.get('status') == '1' and data.get('geocodes'):
            geocodes = data['geocodes']
            if len(geocodes) == 1:
                return geocodes[0]
            return self._select_geocode(geocodes)
        return None

    def _select_geocode(self, geocodes, max_items=3):
        options = geocodes[:max_items]
        lines = []
        for idx, item in enumerate(options, start=1):
            name = item.get('formatted_address') or item.get('address') or "未知地址"
            location = item.get('location', '')
            lines.append(f"{idx}. {name} ({location})")
        hint = "\n".join(lines)
        prompt = f"找到多个地址，请输入序号选择(1-{len(options)}):\n{hint}"
        choice = self.simpledialog.askinteger("选择地址", prompt, minvalue=1, maxvalue=len(options))
        if not choice:
            return None
        return options[choice - 1]

    def _update_coords(self, location_data):
        location = location_data['location']
        gcj02_lng, gcj02_lat = map(float, location.split(','))
        wgs84_lng, wgs84_lat = self.transformer.gcj02_to_wgs84(gcj02_lng, gcj02_lat)
        self.wgs84_coords.set(f"{wgs84_lng}, {wgs84_lat}")
        self.gcj02_coords.set(f"{gcj02_lng}, {gcj02_lat}")
        formatted_address = location_data.get('formatted_address', '')
        if formatted_address:
            self.messagebox.showinfo("搜索结果", f"找到地址：\n{formatted_address}")

    def create_kml(self, lat, lng, address):
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Placemark>
    <name>{address}</name>
    <Point>
      <coordinates>{lng},{lat},0</coordinates>
    </Point>
  </Placemark>
</kml>"""

    def copy_kml(self):
        if not self.wgs84_coords.get():
            self.messagebox.showwarning("警告", "请先搜索位置")
            return
        try:
            lng, lat = map(float, self.wgs84_coords.get().split(','))
            address = self.search_var.get()
            kml = self.create_kml(lat, lng, address)
            self.root.clipboard_clear()
            self.root.clipboard_append(kml)
            self.messagebox.showinfo("成功", "KML代码已复制到剪贴板")
        except Exception as e:
            self.messagebox.showerror("错误", f"生成KML失败: {str(e)}")

    def open_in_maps(self, map_type):
        if not self.wgs84_coords.get():
            self.messagebox.showwarning("警告", "请先搜索位置")
            return
        try:
            lng, lat = map(float, self.wgs84_coords.get().split(','))
            address = self.search_var.get() or "点位"
            if map_type == "google_web":
                webbrowser.open(f"https://www.google.com/maps?q={lat},{lng}")
            elif map_type == "google_earth":
                with tempfile.NamedTemporaryFile(delete=False, suffix='.kml', mode='w', encoding='utf-8') as tmp:
                    tmp.write(self.create_kml(lat, lng, address))
                    kml_path = tmp.name
                try:
                    os.startfile(kml_path)
                except Exception:
                    self.messagebox.showinfo(
                        "提示",
                        f"无法自动打开 Google Earth，请手动导入以下文件：\n{kml_path}"
                    )
            else:
                gcj_lng, gcj_lat = self.transformer.wgs84_to_gcj02(lng, lat)
                webbrowser.open(f"https://uri.amap.com/marker?position={gcj_lng},{gcj_lat}")
        except Exception as e:
            self.messagebox.showerror("错误", f"打开地图失败: {str(e)}")

    def analyze_area(self):
        try:
            coord = self._parse_coord_input()
            if not coord:
                return
            lng, lat = coord
            area_info = get_area_info(lng, lat)
            features_info = get_features(lng, lat)
            try:
                details = _get_regeo_details(lng, lat)
                self.poi_result_var.set(details.get("poi", "无"))
                self.distance_result_var.set(details.get("distance_to_road", "无"))
                self.business_result_var.set(details.get("business_area", "无"))
                self.standard_addr_var.set(details.get("standard_address", ""))
            except Exception as detail_err:
                self.poi_result_var.set(f"错误: {str(detail_err)[:50]}")
                self.distance_result_var.set("错误")
                self.business_result_var.set("错误")
                self.standard_addr_var.set("错误")
            self.area_result_var.set(area_info)
            self.features_result_var.set(features_info)
        except Exception as e:
            self.messagebox.showerror("错误", f"分析失败: {str(e)}")

    def _parse_coord_input(self):
        coord_str = self.coord_var.get().strip()
        if not coord_str:
            return None
        parts = coord_str.split(',')
        if len(parts) != 2:
            self.messagebox.showerror("错误", "坐标格式错误，请使用 经,纬 格式")
            return None
        try:
            lng = float(parts[0].strip())
            lat = float(parts[1].strip())
            return lng, lat
        except Exception:
            self.messagebox.showerror("错误", "坐标格式错误，请使用数字格式")
            return None

    def _get_coord_for_navigation(self):
        coord = self._parse_coord_input()
        if coord:
            return coord
        if self.wgs84_coords.get():
            try:
                lng, lat = map(float, self.wgs84_coords.get().split(','))
                return lng, lat
            except Exception:
                return None
        return None

    def open_coord_navigation(self, map_type):
        coord = self._get_coord_for_navigation()
        if not coord:
            self.messagebox.showwarning("警告", "请输入经纬度信息")
            return
        lng, lat = coord
        try:
            if map_type == "google":
                webbrowser.open(
                    f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}&travelmode=driving"
                )
            else:
                gcj_lng, gcj_lat = self.transformer.wgs84_to_gcj02(lng, lat)
                webbrowser.open(f"https://uri.amap.com/marker?position={gcj_lng},{gcj_lat}")
        except Exception as e:
            self.messagebox.showerror("错误", f"打开导航失败: {str(e)}")

    def open_coord_google_earth(self):
        coord = self._get_coord_for_navigation()
        if not coord:
            self.messagebox.showwarning("警告", "请输入经纬度信息")
            return
        lng, lat = coord
        address = self.search_var.get() or "点位"
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.kml', mode='w', encoding='utf-8') as tmp:
                tmp.write(self.create_kml(lat, lng, address))
                kml_path = tmp.name
            try:
                os.startfile(kml_path)
            except Exception:
                self.messagebox.showinfo(
                    "提示",
                    f"无法自动打开 Google Earth，请手动导入以下文件：\n{kml_path}"
                )
        except Exception as e:
            self.messagebox.showerror("错误", f"打开Google Earth失败: {str(e)}")

    def run_cli_bat(self):
        try:
            bat_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "run_process_cli.bat")
            if not os.path.exists(bat_path):
                self.messagebox.showerror("错误", f"找不到脚本: {bat_path}")
                return
            filename = self.filedialog.askopenfilename(
                title="选择CSV文件",
                filetypes=[("CSV文件", "*.csv"), ("所有文件", "*.*")]
            )
            if not filename:
                return
            import subprocess
            subprocess.Popen([bat_path, filename, "--cli"], shell=False)
        except Exception as e:
            self.messagebox.showerror("错误", f"调用失败: {str(e)}")

    def generate_kml_from_file(self):
        try:
            filename = self.filedialog.askopenfilename(
                title="选择结果文件（CSV/XLSX）",
                filetypes=[("结果文件", "*.xlsx;*.csv"), ("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
            )
            if not filename:
                return

            results = []
            if filename.lower().endswith(".xlsx"):
                if pd is None:
                    self.messagebox.showerror("错误", "缺少pandas，无法读取xlsx，请选择CSV结果文件")
                    return
                df = pd.read_excel(filename)
                results = df.to_dict(orient="records")
            else:
                with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
                    reader = csv.DictReader(f)
                    results = list(reader)

            if not results:
                self.messagebox.showwarning("警告", "结果文件为空")
                return

            kml_file = _create_batch_kml(results, filename)
            if not kml_file:
                self.messagebox.showerror("错误", "生成KML失败")
                return
            self.messagebox.showinfo("成功", f"KML已生成:\n{kml_file}")
            try:
                os.startfile(kml_file)
            except Exception:
                pass
        except Exception as e:
            self.messagebox.showerror("错误", f"生成KML失败: {str(e)}")

    def open_amap_from_file(self):
        try:
            filename = self.filedialog.askopenfilename(
                title="选择结果文件（CSV/XLSX）",
                filetypes=[("结果文件", "*.xlsx;*.csv"), ("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
            )
            if not filename:
                return

            results = []
            if filename.lower().endswith(".xlsx"):
                if pd is None:
                    self.messagebox.showerror("错误", "缺少pandas，无法读取xlsx，请选择CSV结果文件")
                    return
                df = pd.read_excel(filename)
                results = df.to_dict(orient="records")
            else:
                with open(filename, 'r', encoding='utf-8-sig', newline='') as f:
                    reader = csv.DictReader(f)
                    results = list(reader)

            if not results:
                self.messagebox.showwarning("警告", "结果文件为空")
                return

            amap_uri = _create_amap_uri(results)
            if not amap_uri:
                self.messagebox.showerror("错误", "生成高德地图链接失败")
                return
            self.messagebox.showinfo("成功", "已生成高德地图链接，将在浏览器打开")
            try:
                os.startfile(amap_uri)
            except Exception:
                pass
        except Exception as e:
            self.messagebox.showerror("错误", f"打开高德地图失败: {str(e)}")

    def export_results(self):
        if not self.batch_results:
            self.messagebox.showwarning("警告", "没有可导出的结果")
            return
        try:
            filename = self.filedialog.asksaveasfilename(
                title="保存结果",
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("CSV文件", "*.csv")]
            )
            if not filename:
                return
            if pd is not None and filename.endswith('.xlsx'):
                df = pd.DataFrame(self.batch_results)
                df.to_excel(filename, index=False)
            else:
                field_order = [
                    '名称', '地址', 'WGS84经度', 'WGS84纬度', 'GCJ02经度', 'GCJ02纬度',
                    '区域属性', '地理特征', 'POI', '到道路距离', '商圈', '地址标准化',
                    '状态', '原始数据'
                ]
                with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=field_order)
                    writer.writeheader()
                    for result in self.batch_results:
                        writer.writerow(result)
            self.messagebox.showinfo("成功", f"结果已保存至:\n{filename}")
        except Exception as e:
            self.messagebox.showerror("错误", f"导出失败: {str(e)}")

    def run(self):
        self.root.mainloop()

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="CSV批量解析（process版）")
    parser.add_argument("--cli", action="store_true", help="使用命令行模式")
    parser.add_argument("--input", "-i", help="CSV文件路径")
    parser.add_argument("--output", "-o", help="输出CSV路径（可选）")
    parser.add_argument("--delay", type=float, default=1.0, help="API延迟秒数")
    parser.add_argument("--input-dir", help="目录模式：处理目录下所有CSV")
    parser.add_argument("--list", help="列表模式：文本文件，每行一个CSV路径")
    parser.add_argument("--single", help="单点分析：传入 经度,纬度")
    parser.add_argument("--address", help="地址解析：传入地址字符串")
    parser.add_argument("--open-google", action="store_true", help="批量完成后打开Google地图")
    parser.add_argument("--open-amap", action="store_true", help="批量完成后打开高德地图")

    args, unknown = parser.parse_known_args()
    if not args.cli:
        ProcessUserGUI().run()
        return

    input_file = args.input
    if not input_file and unknown:
        for arg in unknown:
            if not arg.startswith("-"):
                input_file = arg
                break
    if not input_file and not args.input_dir and not args.list:
        print("❌ 未提供输入文件。请使用 --input 指定CSV路径，或使用 --input-dir / --list。")
        return

    def run_one(path):
        print("🚀 开始处理用户文件...")
        print(f"输入文件: {path}")
        print(f"输出文件: {args.output or '自动保存'}")
        print(f"API延迟: {args.delay}秒")
        print("")
        return process_user_file_batch(path, args.output, args.delay, open_google=args.open_google, open_amap=args.open_amap)

    if args.single:
        try:
            parts = args.single.split(',')
            if len(parts) != 2:
                print("❌ 单点格式错误，请使用 经度,纬度")
                return
            lng, lat = float(parts[0].strip()), float(parts[1].strip())
            analysis_lng, analysis_lat = lng, lat
            analysis_source = "原始坐标"
            geo_gcj_lng, geo_gcj_lat, geo_addr = _geocode_address(args.address) if args.address else (None, None, None)
            if geo_gcj_lng is not None and geo_gcj_lat is not None:
                analysis_lng, analysis_lat = CoordTransform().gcj02_to_wgs84(geo_gcj_lng, geo_gcj_lat)
                analysis_source = "地址解析"

            area_info = get_area_info(analysis_lng, analysis_lat)
            features_info, regeo_addr = get_features(analysis_lng, analysis_lat, return_addr=True)
            try:
                details = _get_regeo_details(analysis_lng, analysis_lat)
            except Exception as detail_err:
                details = {
                    "poi": f"错误: {str(detail_err)[:50]}",
                    "distance_to_road": "错误",
                    "business_area": "错误",
                    "standard_address": ""
                }
            gcj_lng, gcj_lat = CoordTransform().wgs84_to_gcj02(lng, lat)
            if geo_gcj_lng is not None and geo_gcj_lat is not None:
                geo_wgs_lng, geo_wgs_lat = CoordTransform().gcj02_to_wgs84(geo_gcj_lng, geo_gcj_lat)
                diff_m = _haversine_meters(float(lng), float(lat), float(geo_wgs_lng), float(geo_wgs_lat))
            else:
                geo_wgs_lng = geo_wgs_lat = diff_m = None
            print(f"WGS84: {lng}, {lat}")
            print(f"GCJ02: {gcj_lng}, {gcj_lat}")
            print(f"区域属性: {area_info}")
            print(f"地理特征: {features_info}")
            print(f"逆地理地址: {regeo_addr}")
            print(f"POI: {details.get('poi')}")
            print(f"到道路距离: {details.get('distance_to_road')}")
            print(f"商圈: {details.get('business_area')}")
            print(f"地址标准化: {details.get('standard_address')}")
            if geo_addr:
                print(f"地址解析地址: {geo_addr}")
            if diff_m is not None:
                print(f"坐标差异米: {diff_m:.1f}")
            print(f"分析坐标来源: {analysis_source}")
        except Exception as e:
            print(f"❌ 单点分析失败: {e}")
        return

    if args.address:
        try:
            url, headers = _amap_endpoint("/v3/geocode/geo")
            params = {
                "address": args.address,
                "key": get_amap_key(),
                "city": "",
                "output": "json"
            }
            data = _get_json_with_retry(url, params, retries=2, timeout=10, headers=headers)
            if data.get('status') == '1' and data.get('geocodes'):
                location = data['geocodes'][0]['location']
                gcj_lng, gcj_lat = map(float, location.split(','))
                wgs_lng, wgs_lat = CoordTransform().gcj02_to_wgs84(gcj_lng, gcj_lat)
                print(f"地址: {args.address}")
                print(f"GCJ02: {gcj_lng}, {gcj_lat}")
                print(f"WGS84: {wgs_lng}, {wgs_lat}")
            else:
                print(f"❌ 地址解析失败: {data.get('info', '未知错误')}")
        except Exception as e:
            print(f"❌ 地址解析失败: {e}")
        return

    if args.input_dir:
        csv_files = [
            os.path.join(args.input_dir, f)
            for f in os.listdir(args.input_dir)
            if f.lower().endswith(".csv")
        ]
        for path in csv_files:
            run_one(path)
        return

    if args.list:
        with open(args.list, "r", encoding="utf-8") as f:
            paths = [line.strip() for line in f if line.strip()]
        for path in paths:
            run_one(path)
        return

    results = run_one(input_file)

    if results:
        print("\n🎉 处理完成!")
        if args.output:
            print(f"结果已保存到: {args.output}")
        print("已自动保存批量结果与日志，请在输入文件目录查看 batch_results_*.xlsx/csv 与 batch_processing_log_*.txt")
    else:
        print("\n⚠️  处理失败或没有结果")

if __name__ == "__main__":
    main()
