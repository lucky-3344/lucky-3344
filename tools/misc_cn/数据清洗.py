from pathlib import Path
import re
import pdfplumber
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
import os
from transformers import AutoTokenizer, AutoModelForTokenClassification
import torch
from sentence_transformers import SentenceTransformer
import logging

from path.to.使用pypdfAI提取 import extract_pdf_text

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='telecom_pdf_analyzer.log',
    filemode='a'
)
logger = logging.getLogger('telecom_pdf_analyzer')
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
logger.addHandler(console_handler)

# 通信领域常见术语和参数模式
TELECOM_PATTERNS = {
    "基站信息": {
        "基站名称": r"(?:基站名称|站名)[:：]?\s*([^\n,，;；]{2,30})",
        "站址编码": r"(?:站址编码|站址码|站址代码)[:：]?\s*([A-Za-z0-9-]{5,20})",
        "经度": r"(?:东经|经度)[:：]?\s*(\d{1,3}°\d{1,2}′\d{1,2}(?:\.\d+)?″|(?<!年)\d{1,3}\.\d{6,})",
        "纬度": r"(?:北纬|纬度)[:：]?\s*(\d{1,2}°\d{1,2}′\d{1,2}(?:\.\d+)?″|(?<!年)\d{1,2}\.\d{6,})"
    },
    "天线参数": {
        "天线挂高": r"(?:天线挂高|天馈挂高)[:：]?\s*(\d+(?:\.\d+)?)\s*[米mM]",
        "天线方位角": r"(?:天线方位角|方位角)[:：]?\s*(?:(\d+°(?:/\d+°){0,2})|(?:A:)?(\d+)[°度](?:[，,](?:B:)?(\d+)[°度])?(?:[，,](?:C:)?(\d+)[°度])?)",
        "天线下倾角": r"(?:下倾角|机械下倾)[:：]?\s*(?:(\d+(?:\.\d+)?°(?:/\d+(?:\.\d+)?°){0,2})|(?:(\d+(?:\.\d+)?)[°度](?:[，,](\d+(?:\.\d+)?)[°度])?(?:[，,](\d+(?:\.\d+)?)[°度])?))",
        "天线型号": r"(?:天线型号|天馈型号)[:：]?\s*([A-Za-z0-9-]{3,25})"
    },
    "设备参数": {
        "功率": r"(?:功率|发射功率)[:：]?\s*(\d+(?:\.\d+)?)\s*[wWdD]{1,2}",
        "频段": r"(?:频段|工作频段)[:：]?\s*([A-Za-z0-9/]{1,10})",
        "频率": r"(?:频率|中心频率)[:：]?\s*(\d+(?:\.\d+)?)\s*[MmGg][Hh][Zz]"
    },
    "系统规格": {
        "室分系统": r"(室内分布系统|室分系统|室分)",
        "5G": r"(?<!\w)(5G|N[Rr]|SA|NSA|Sub-6G|毫米波)(?!\w)",
        "4G": r"(?<!\w)(4G|LTE|LTE\-A|VoLTE)(?!\w)",
        "3G": r"(?<!\w)(3G|WCDMA|TD\-SCDMA|EVDO)(?!\w)",
        "2G": r"(?<!\w)(2G|GSM)(?!\w)"
    }
}

def generate_structured_report(pdf_path):
    """生成PDF的结构化分析报告"""
    # 步骤1: 提取文本
    text_by_page = extract_pdf_text(pdf_path)
    
    # 步骤2: 分段处理
    all_text = "\n".join([page["content"] for page in text_by_page])
    paragraphs = re.split(r'\n{2,}', all_text)
    
    # 步骤3: 提取表格
    tables = extract_tables_from_pdf(pdf_path)
    
    # 步骤4: 提取通信术语
    telecom_terms = {}
    for paragraph in paragraphs:
        chunk_terms = extract_parameters(paragraph)
        for category, cat_terms in chunk_terms.items():
            if category not in telecom_terms:
                telecom_terms[category] = {}
            for param_name, values in cat_terms.items():
                if param_name not in telecom_terms[category]:
                    telecom_terms[category][param_name] = []
                telecom_terms[category][param_name].extend(values)
    
    # 整合结果
    report = {
        "filename": Path(pdf_path).name,
        "page_count": len(text_by_page),
        "technical_terms": telecom_terms,
        "tables_count": len(tables),
        "diagrams_count": 0,  # 这里可以实现检测图表的功能
        "tables": tables
    }
    
    return report

def extract_tables_from_pdf(pdf_path):
    """从PDF中提取表格"""
    tables_data = []
    
    try:
        # 尝试用pdfplumber提取
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                tables = page.extract_tables()
                for j, table in enumerate(tables):
                    if table and any(table):  # 确保表格不为空
                        tables_data.append({
                            "page": i+1,
                            "table_id": f"P{i+1}_T{j+1}",
                            "extraction_method": "pdfplumber",
                            "data": table
                        })
        
        return tables_data
    except Exception as e:
        print(f"表格提取过程中出错: {str(e)}")
        return []

def extract_parameters(text, patterns=None):
    """从文本中提取参数"""
    if patterns is None:
        # 通信领域常见术语和参数模式
        patterns = {
            "基站信息": {
                "基站名称": r"(?:基站名称|站名)[:：]?\s*([^\n,，;；]{2,30})",
                "站址编码": r"(?:站址编码|站址码|站址代码)[:：]?\s*([A-Za-z0-9-]{5,20})",
                "经度": r"(?:东经|经度)[:：]?\s*(\d{1,3}°\d{1,2}′\d{1,2}(?:\.\d+)?″|(?<!年)\d{1,3}\.\d{6,})",
                "纬度": r"(?:北纬|纬度)[:：]?\s*(\d{1,2}°\d{1,2}′\d{1,2}(?:\.\d+)?″|(?<!年)\d{1,2}\.\d{6,})"
            },
            "天线参数": {
                "天线挂高": r"(?:天线挂高|天馈挂高)[:：]?\s*(\d+(?:\.\d+)?)\s*[米mM]",
                "天线方位角": r"(?:天线方位角|方位角)[:：]?\s*(?:(\d+°(?:/\d+°){0,2})|(?:A:)?(\d+)[°度](?:[，,](?:B:)?(\d+)[°度])?(?:[，,](?:C:)?(\d+)[°度])?)",
                "天线下倾角": r"(?:下倾角|机械下倾)[:：]?\s*(?:(\d+(?:\.\d+)?°(?:/\d+(?:\.\d+)?°){0,2})|(?:(\d+(?:\.\d+)?)[°度](?:[，,](\d+(?:\.\d+)?)[°度])?(?:[，,](\d+(?:\.\d+)?)[°度])?))",
                "天线型号": r"(?:天线型号|天馈型号)[:：]?\s*([A-Za-z0-9-]{3,25})"
            },
            "设备参数": {
                "功率": r"(?:功率|发射功率)[:：]?\s*(\d+(?:\.\d+)?)\s*[wWdD]{1,2}",
                "频段": r"(?:频段|工作频段)[:：]?\s*([A-Za-z0-9/]{1,10})",
                "频率": r"(?:频率|中心频率)[:：]?\s*(\d+(?:\.\d+)?)\s*[MmGg][Hh][Zz]"
            },
            "系统规格": {
                "室分系统": r"(室内分布系统|室分系统|室分)",
                "5G": r"(?<!\w)(5G|N[Rr]|SA|NSA|Sub-6G|毫米波)(?!\w)",
                "4G": r"(?<!\w)(4G|LTE|LTE\-A|VoLTE)(?!\w)",
                "3G": r"(?<!\w)(3G|WCDMA|TD\-SCDMA|EVDO)(?!\w)",
                "2G": r"(?<!\w)(2G|GSM)(?!\w)"
            }
        }
    
    results = {}
    
    for category, pattern_dict in patterns.items():
        cat_results = {}
        for param_name, pattern in pattern_dict.items():
            matches = re.findall(pattern, text)
            if matches:
                # 处理不同类型的匹配结果
                if isinstance(matches[0], tuple):
                    # 过滤掉空值，选择第一个非空值
                    filtered_matches = []
                    for match in matches:
                        valid_values = [v for v in match if v]
                        if valid_values:
                            filtered_matches.append(valid_values[0])
                    if filtered_matches:
                        cat_results[param_name] = filtered_matches
                else:
                    cat_results[param_name] = matches
        
        if cat_results:
            results[category] = cat_results
    
    return results

def apply_telecom_rules(report):
    """应用通信行业专用规则增强结果"""
    enhanced_report = report.copy()
    
    # 规则1: 频段识别和分类
    if "技术参数" not in enhanced_report:
        enhanced_report["技术参数"] = {}
    
    frequency_params = []
    # 查找设备参数中的频率
    if "设备参数" in report and "频率" in report["设备参数"]:
        frequency_params.extend(report["设备参数"]["频率"])
    
    if frequency_params:
        # 频段分类
        freq_bands = {
            "低频": [],
            "中频": [],
            "高频": [],
            "毫米波": []
        }
        
        for freq in frequency_params:
            try:
                value = float(freq.split()[0])  # 提取数值部分
                if value < 1:
                    freq_bands["低频"].append(f"{value}GHz")
                elif value < 6:
                    freq_bands["中频"].append(f"{value}GHz")
                elif value < 30:
                    freq_bands["高频"].append(f"{value}GHz")
                else:
                    freq_bands["毫米波"].append(f"{value}GHz")
            except (ValueError, IndexError):
                pass
        
        enhanced_report["技术参数"]["频段分布"] = freq_bands
    
    # 规则2: 识别通信协议栈
    protocols = []
    
    # 查找系统规格中的协议
    if "系统规格" in report:
        for tech_type, values in report["系统规格"].items():
            if tech_type in ["5G", "4G", "3G", "2G"]:
                protocols.extend(values)
    
    if protocols:
        enhanced_report["通信协议"] = list(set(protocols))
    
    return enhanced_report

def generate_excel_report(params, output_path):
    """生成Excel报告"""
    try:
        import pandas as pd
        
        # 创建一个Excel写入器
        with pd.ExcelWriter(output_path) as writer:
            # 参数汇总表
            all_params = []
            for category, params_dict in params.items():
                for param_name, values in params_dict.items():
                    for value in values:
                        all_params.append({
                            "参数类别": category,
                            "参数名称": param_name,
                            "参数值": value
                        })
            
            if all_params:
                pd.DataFrame(all_params).to_excel(writer, sheet_name="参数汇总", index=False)
            
            # 为每个类别创建单独的表
            for category, params_dict in params.items():
                category_params = []
                for param_name, values in params_dict.items():
                    for i, value in enumerate(values):
                        if i == 0:  # 第一个值使用参数名
                            category_params.append({
                                "参数名称": param_name,
                                "参数值": value
                            })
                        else:  # 其他值使用空字符串作为参数名
                            category_params.append({
                                "参数名称": "",  # 或用 f"{param_name} ({i+1})"
                                "参数值": value
                            })
                
                if category_params:
                    sheet_name = category[:31]  # Excel sheet名最大31字符
                    pd.DataFrame(category_params).to_excel(writer, sheet_name=sheet_name, index=False)
        
        logger.info(f"成功生成Excel报告：{output_path}")
        return True
    except Exception as e:
        logger.error(f"生成Excel报告时出错: {str(e)}")
        return False
