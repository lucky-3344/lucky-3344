import pdfplumber
import logging
import warnings
import pandas as pd
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
import re
import os
import fitz  # PyMuPDF
import numpy as np
import cv2
from PIL import Image
from io import BytesIO
import base64
import json
import urllib.request
import urllib.error
import argparse
import time
import sys
from glob import glob

# 使用更强的本地 PaddleOCR（PP-OCRv4），Tesseract 作为回退
try:
    from paddleocr import PaddleOCR
    ocr_engine = PaddleOCR(
        use_angle_cls=True,
        lang="ch",
        use_gpu=False,
        show_log=False,
        # 更适合细字/小字体的检测参数
        det_limit_side_len=4096,
        det_db_box_thresh=0.15,
        det_db_unclip_ratio=2.5
    )
    OCR_ENGINE_TYPE = 'paddle'
except Exception:
    try:
        import pytesseract
        OCR_ENGINE_TYPE = 'tesseract'
    except ImportError:
        OCR_ENGINE_TYPE = None

# 按需禁用本地 OCR（优先使用 DeepSeek OCR 网关）
# 设为 False 以启用本地 PaddleOCR
DISABLE_LOCAL_OCR = False
if DISABLE_LOCAL_OCR:
    OCR_ENGINE_TYPE = None

# 暂时禁用 OCR（仅用视觉模型做整页识别）
USE_OCR = os.getenv("USE_OCR", "1").strip().lower() in ("1", "true", "yes", "y")

# 抑制来自 pdfminer/pdfplumber 的 CropBox 警告
logging.getLogger('pdfminer').setLevel(logging.ERROR)
logging.getLogger('pdfplumber').setLevel(logging.ERROR)
warnings.filterwarnings("ignore", message=r"CropBox missing from /Page.*")

# 外部视觉模型配置（优先本地 VLLM 网关，其次 DeepSeek）
VISION_API_BASE = os.getenv("VISION_API_BASE")
VISION_API_KEY = os.getenv("VISION_API_KEY")
VISION_MODEL = os.getenv("VISION_MODEL")

DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
DEEPSEEK_OCR_URL = os.getenv("DEEPSEEK_OCR_URL", "http://172.16.159.9:47029/api/gateway_files")
DEEPSEEK_OCR_KEY = os.getenv("DEEPSEEK_OCR_KEY", "")
DEEPSEEK_OCR_MODEL = os.getenv("DEEPSEEK_OCR_MODEL", "DeepSeek-OCR")
DEEPSEEK_OCR_FILE_FIELD = os.getenv("DEEPSEEK_OCR_FILE_FIELD", "file")
DEEPSEEK_OCR_PROMPT = os.getenv(
    "DEEPSEEK_OCR_PROMPT",
    "<image>\n<|grounding|>Convert the document to markdown.",
)

# DotsOCR 网关配置
DOTS_OCR_URL = os.getenv("DOTS_OCR_URL", "")
DOTS_OCR_KEY = os.getenv("DOTS_OCR_KEY", "")
DOTS_OCR_FILE_FIELD = os.getenv("DOTS_OCR_FILE_FIELD", "file")
USE_DOTS_OCR = os.getenv("USE_DOTS_OCR", "1").strip().lower() in ("1", "true", "yes", "y")
DOTS_OCR_DEBUG = os.getenv("DOTS_OCR_DEBUG", "0").strip().lower() in ("1", "true", "yes", "y")
DEBUG_FIRST_PDF = os.getenv("DEBUG_FIRST_PDF", "0").strip().lower() in ("1", "true", "yes", "y")
ALLOW_DEEPSEEK_OCR_FALLBACK = os.getenv("ALLOW_DEEPSEEK_OCR_FALLBACK", "0").strip().lower() in ("1", "true", "yes", "y")
FAST_OCR = os.getenv("FAST_OCR", "1").strip().lower() in ("1", "true", "yes", "y")  # 默认启用快速模式
_DOTS_OCR_AUTH_WARNED = False
_DOTS_OCR_LAST_TS = 0.0
DOTS_OCR_MAX_TRIES = int(os.getenv("DOTS_OCR_MAX_TRIES", "8"))

def _encode_multipart_form(fields, files):
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    lines = [] 
    for key, value in (fields or {}).items():
        lines.append(f"--{boundary}")
        lines.append(f"Content-Disposition: form-data; name=\"{key}\"")
        lines.append("")
        lines.append(str(value))
    for key, filename, content_type, data in (files or []):
        lines.append(f"--{boundary}")
        lines.append(f"Content-Disposition: form-data; name=\"{key}\"; filename=\"{filename}\"")
        lines.append(f"Content-Type: {content_type}")
        lines.append("")
        lines.append(data)
    lines.append(f"--{boundary}--")
    body = b""
    for item in lines:
        if isinstance(item, bytes):
            body += item + b"\r\n"
        else:
            body += str(item).encode("utf-8") + b"\r\n"
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type

def _extract_text_from_ocr_response(obj):
    if not obj:
        return ""
    if isinstance(obj, dict):
        contents = obj.get("contents")
        if isinstance(contents, list):
            parts = []
            for item in contents:
                if isinstance(item, dict):
                    content = item.get("content")
                    if isinstance(content, str) and content.strip():
                        parts.append(content.strip())
            if parts:
                return "\n".join(parts)
    for key in ["text", "result", "data", "message", "content"]:
        val = obj.get(key) if isinstance(obj, dict) else None
        if isinstance(val, str) and val.strip():
            return val.strip()
    # DotsOCR: results -> full_layout_info -> text
    if isinstance(obj, dict):
        results = obj.get("results")
        if isinstance(results, list):
            parts = []
            for res in results:
                if isinstance(res, dict):
                    full_layout_info = res.get("full_layout_info")
                    if isinstance(full_layout_info, list):
                        for item in full_layout_info:
                            if isinstance(item, dict):
                                text = item.get("text")
                                if isinstance(text, str) and text.strip():
                                    parts.append(text.strip())
            if parts:
                return "\n".join(parts)
    if isinstance(obj, dict):
        for key in ["data", "result", "output"]:
            val = obj.get(key)
            if isinstance(val, dict):
                inner = _extract_text_from_ocr_response(val)
                if inner:
                    return inner
            if isinstance(val, list) and val:
                for item in val:
                    if isinstance(item, dict):
                        inner = _extract_text_from_ocr_response(item)
                        if inner:
                            return inner
    return ""

def _strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?[^>]+>", "", text)
    return text

def _extract_drawing_name_from_ocr_text(text: str) -> str:
    if not text:
        return ""
    cleaned = _strip_html(text)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    noise_keywords = [
        "说明", "注意", "要求", "规范", "措施", "施工", "安全", "防疫", "禁止", "未经",
        "损坏", "责任", "中断", "操作", "电源", "线缆", "防护", "管理", "批准"
    ]
    def _is_notice(line: str) -> bool:
        return any(k in line for k in noise_keywords)

    # 1) 标签行优先
    for line in lines:
        m = re.search(r"(图纸名称|图纸名|图名)[:：]?(.*)", line)
        if m and m.group(2).strip():
            return m.group(2).strip()

    # 2) 正则匹配图名关键词（优先取最后一次出现）
    compact = re.sub(r"\s+", "", cleaned)
    pattern = r".{2,60}(GPS馈线路由图|馈线路由图|设备布置平面|设备分布|面板图|布置平面图|布置平面|平面图|立面图|剖面图|系统图|原理图|基站天馈线新增示意图|天馈线新增示意图|示意图|安装示意图|天馈线系统安装|设备安装|路由图|布线表|工程量表|材料表|明细表).{0,20}"
    matches = re.findall(pattern, compact)
    if matches:
        # 取最后一个匹配的完整片段
        last = None
        for m in re.finditer(pattern, compact):
            last = m.group(0)
        if last:
            # 去掉尾部字段
            last = re.split(r"出图日期|比例|图号|描图|单位|审核|校对", last)[0]
            # 若原文包含 CBN- 但片段缺失，尝试补全
            if "CBN-" in compact and "CBN-" not in last:
                cbn_idx = compact.find("CBN-")
                if cbn_idx != -1:
                    last = compact[cbn_idx:cbn_idx + len(last) + 20]
            return last

    # 3) 关键词行匹配
    keywords = [
        "GPS馈线路由图", "馈线路由图", "设备布置平面", "设备分布", "面板图", "布置平面", "平面图", "立面图", "剖面图", "系统图", "原理图", "基站天馈线新增示意图", "天馈线新增示意图", "示意图",
        "安装示意图", "天馈线系统安装", "设备安装", "路由图", "布线表", "工程量表", "材料表", "明细表"
    ]
    for line in lines:
        if any(k in line for k in keywords) and 4 <= len(line) <= 80 and not _is_notice(line):
            line = re.split(r"出图日期|比例|图号|描图|单位|审核|校对", line)[0]
            return line

    # 4) 兜底：包含“图/表/示意”的短行（排除安全/说明类）
    candidates = [
        line for line in lines
        if any(k in line for k in ["图", "表", "示意"]) and 4 <= len(line) <= 80 and not _is_notice(line)
    ]
    if candidates:
        return candidates[-1]

    return ""

def _pick_drawing_name_simple(text: str, tail_lines: int = 6) -> str:
    """简化版图名选择：尽量贴近测试脚本逻辑"""
    if not text:
        return ""
    cleaned = _strip_html(text)
    all_lines = [l.strip() for l in cleaned.splitlines() if l.strip()]

    def _try_pick(lines: list[str]) -> str:
        if not lines:
            return ""
        # 1) 标签行优先
        for line in lines:
            m = re.search(r"(图纸名称|图纸名|图名)[:：]?(.*)", line)
            if m and m.group(2).strip():
                return m.group(2).strip()
        # 2) 含图名关键词的行
        keywords = [
            "GPS馈线路由图", "馈线路由图", "设备布置平面图", "设备布置平面", "设备分布", "面板图", "布置平面图", "布置平面",
            "平面图", "立面图", "剖面图", "系统图", "原理图", "基站天馈线新增示意图", "天馈线新增示意图", "示意图", "安装示意图", "天馈线系统安装",
            "路由图", "布线表", "工程量表", "明细表"
        ]
        # 2.1 行内优先：截取含关键词的片段（到“出图日期/比例/图号”等字段前为止）
        candidates: list[str] = []
        for line in lines:
            if "设备安装" in line and not re.search(r"图|示意|路由|布线|平面|系统|原理|表", line):
                continue
            if _is_materials_like(line):
                continue
            compact_line = re.sub(r"\s+", "", line)
            for kw in keywords:
                if kw in compact_line:
                    candidate = _extract_title_by_keywords(compact_line, keywords)
                    if candidate:
                        candidates.append(candidate)
            # 允许“设备安装图/示意图”等
            if re.search(r"设备安装.*(图|示意|平面|路由|表)", compact_line):
                m = re.search(r"[^,，;；。]{0,40}设备安装[^,，;；。]{0,40}(图|示意|平面|路由|表)", compact_line)
                if m:
                    candidates.append(m.group(0))
        # 3) 整段兜底：关键词正则提取片段
        compact = re.sub(r"\s+", "", "\n".join(lines))
        candidate = _extract_title_by_keywords(compact, keywords)
        if candidate:
            candidates.append(candidate)
        if candidates:
            candidates = list(dict.fromkeys(candidates))
            candidates.sort(key=lambda t: (_score_title(t), len(t)), reverse=True)
            return candidates[0]
        return ""

    # 以“工程名称”为锚点，优先从该行开始截取标题块
    anchor_idx = None
    for i, line in enumerate(all_lines):
        if "工程名称" in line:
            anchor_idx = i

    if anchor_idx is not None:
        anchor_lines = all_lines[anchor_idx:]
        head_slice = anchor_lines[:tail_lines] if tail_lines else anchor_lines
        picked = _try_pick(head_slice)
        if picked:
            return picked
        # 回退：扩大到工程名称后更长窗口
        picked = _try_pick(anchor_lines[:20])
        if picked:
            return picked
        # 锚点策略失败，尝试后N行策略作为兜底（适用于图名在底部的情况）
        if tail_lines and len(all_lines) > tail_lines:
            picked = _try_pick(all_lines[-tail_lines:])
            if picked:
                return picked

    # 无锚点：默认取后6行
    if tail_lines and len(all_lines) > tail_lines:
        all_lines = all_lines[-tail_lines:]
    return _try_pick(all_lines)

def _extract_title_by_keywords(compact: str, keywords: list[str]) -> str:
    if not compact:
        return ""
    # 边界词：用于截断前后的无关内容
    boundaries = ["出图日期", "比例", "图号", "描图", "审核", "校对", "单位", "总负责", "单项负责", "设计", "U-Z5H", "CBN-"]
    # 前置边界词：用于截断前面的公司名称等噪音（只影响 start 计算）
    prefix_boundaries = ["公司", "有限公司", "设计院", "研究院"]
    candidates = []
    for kw in keywords:
        for m in re.finditer(re.escape(kw), compact):
            kw_start = m.start()
            kw_end = m.end()
            # 检查关键词后是否有序号 （一）（二）(1)(2)(1-1) 等（扩大字符限制）
            suffix_match = re.match(r"(\([^)]{1,6}\)|（[^）]{1,6}）|[一二三四五六七八九十]+)", compact[kw_end:])
            if suffix_match:
                kw_end += suffix_match.end()
            start = 0
            for b in boundaries + prefix_boundaries:
                idx = compact.rfind(b, 0, kw_start)
                if idx != -1:
                    idx = idx + len(b)
                    if b == "比例":
                        while idx < len(compact) and compact[idx] in "0123456789:：.":
                            idx += 1
                    if idx > start:
                        start = idx
            end = len(compact)
            for b in boundaries:
                idx = compact.find(b, kw_end)
                if idx != -1 and idx < end:
                    end = idx
            candidate = compact[start:end].strip(" :：-—·")
            if 4 <= len(candidate) <= 80:
                candidates.append(candidate)
    if not candidates:
        return ""
    # 选择最短的候选，避免夹带过多字段
    candidates.sort(key=len)
    return candidates[0]

def _score_title(title: str) -> int:
    if not title:
        return -999
    score = 0
    if "设备布置平面" in title:
        score += 100
    if "布置平面" in title:
        score += 90
    if "平面图" in title:
        score += 80
    if "安装示意图" in title:
        score += 70
    if "示意图" in title:
        score += 50
    if "路由图" in title:
        score += 40
    if "布线表" in title:
        score += 40
    if "工程量表" in title or "材料表" in title:
        score -= 20
    if "板位示意图" in title:
        score -= 30
    return score

def _trim_drawing_name(name: str) -> str:
    if not name:
        return name
    # 优先从混杂长串中抽取包含图名关键词的片段，避免被“比例/出图日期”等字段截断
    compact = re.sub(r"\s+", "", name)
    keywords = [
        "GPS馈线路由图", "馈线路由图", "设备布置平面图", "设备布置平面", "设备分布", "面板图", "布置平面图", "布置平面",
        "平面图", "立面图", "剖面图", "系统图", "原理图", "基站天馈线新增示意图", "天馈线新增示意图", "示意图", "安装示意图", "天馈线系统安装",
        "路由图", "布线表", "工程量表", "明细表"
    ]
    candidate = _extract_title_by_keywords(compact, keywords)
    matched_kw = False
    if candidate:
        name = candidate
        matched_kw = True
    # 若包含站点前缀，优先剥离到图名相关关键词或“基站/无线”等前导词
    if "CBN-" in name:
        name = re.sub(r"^CBN-.*?(?=基站|无线|设备|机房|天馈线|馈线|GPS|分波|布置|安装|路由|布线|平面|示意)", "", name)
        if "U-Z5H" in name:
            name = name.split("U-Z5H", 1)[1].strip()
    # 若命中图名关键词，优先截取从“基站/天馈线/机房/设备”开始的片段
    if matched_kw:
        m = re.search(r"(基站|天馈线|机房|设备|GPS).*?(设备布置平面图|设备布置平面|设备分布|面板图|布置平面图|布置平面|平面图|示意图|立面图|剖面图|系统图|原理图|路由图|布线表|工程量表|明细表)((?:[\(（][^)\）]{1,6}[\)）]|[一二三四五六七八九十]+))?", name)
        if m:
            name = m.group(0)
    else:
        m = re.search(r"(基站|天馈线|机房|设备|GPS).*?(设备布置平面图|设备布置平面|设备分布|面板图|布置平面图|布置平面|平面图|示意图|立面图|剖面图|系统图|原理图|路由图|布线表|工程量表|明细表)((?:[\(（][^)\）]{1,6}[\)）]|[一二三四五六七八九十]+))?", name)
        if m:
            name = m.group(0)
    # 去掉前置站点名称（如 CBN-...U-Z5H）
    if not matched_kw:
        name = re.split(r"出图日期|比例|图号|描图|审核|校对|单位|总负责|单项负责|设计|插图", name)[0].strip()
    name = re.split(r"。|；|，|,|必须|要求|注意|未经", name)[0].strip()
    # 去掉前置日期
    name = re.sub(r"^\d{4}[./\-]?\d{2}[./\-]?\d{2}", "", name).strip()
    # 去掉前置序号（仅在有分隔符时移除，保留如“12波”）
    name = re.sub(r"^[0-9]+[\s\-、.]+", "", name).strip()
    # 去掉前缀“机房1/机房2”等
    name = re.sub(r"^机房\s*\d+\s*", "", name).strip()
    # 去掉图名后的人员姓名尾巴（含(一)(二)等）（扩大序号字符限制）
    name = re.sub(r"(示意图|平面图|立面图|剖面图|系统图|原理图|路由图|布线表|工程量表|明细表|图|表)([\(（][^)\）]{1,6}[\)）])?([\u4e00-\u9fa5]{2,4})$", r"\1\2", name).strip()
    name = re.sub(r"[\s]+是$", "", name)
    name = re.sub(r"建设$", "", name).strip()
    # 过滤掉非图名的"表"（如"安装工作量表"、"拆除工作量表"）
    if re.search(r"^(安装|拆除)?工作量表[：:]?$", name):
        return ""
    # 若缺少图名特征，视为无效
    if not re.search(r"图|表|示意|路由|平面|原理|分布|面板", name):
        return ""
    return name

def _extract_title_loose(text: str) -> str:
    if not text:
        return ""
    compact = re.sub(r"\s+", "", text)
    m = re.search(r"(基站|天馈线|机房|设备|GPS)[^，,。;；]{0,60}?(设备布置平面图|设备布置平面|设备分布|面板图|布置平面图|布置平面|平面图|基站天馈线新增示意图|天馈线新增示意图|示意图|路由图|布线表|系统图|原理图)((?:[\(（][^)\）]{1,6}[\)）]|[一二三四五六七八九十]+))?", compact)
    if m:
        return m.group(0)
    return ""

def _downscale_to_max_pixels(img: np.ndarray, max_pixels: int = 160_000_000) -> np.ndarray:
    try:
        h, w = img.shape[:2]
        if h * w <= max_pixels:
            return img
        scale = (max_pixels / float(h * w)) ** 0.5
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        return cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
    except Exception:
        return img

def _find_latest_result_excel(output_dir: str) -> str | None:
    if not output_dir or not os.path.isdir(output_dir):
        return None
    candidates = glob(os.path.join(output_dir, "图纸名称提取结果_*.xlsx"))
    if not candidates:
        return None
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return candidates[0]

def _load_existing_results(excel_path: str) -> dict:
    if not excel_path or not os.path.isfile(excel_path):
        return {}
    try:
        df = pd.read_excel(excel_path, sheet_name="原始提取")
    except Exception:
        try:
            df = pd.read_excel(excel_path)
        except Exception:
            return {}
    existing = {}
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        key = (str(row_dict.get("文件名", "")).strip(), str(row_dict.get("文件路径", "")).strip())
        existing[key] = row_dict
    return existing

def _row_extracted_count(row: dict) -> int:
    if not row:
        return 0
    val = row.get("图纸数量")
    try:
        if pd.notna(val):
            return int(val)
    except Exception:
        pass
    count = 0
    for k, v in row.items():
        if isinstance(k, str) and k.startswith("图纸") and k.endswith("名称"):
            if v is not None and str(v).strip():
                count += 1
    return count

def _row_has_missing(row: dict) -> bool:
    if not row:
        return True
    for k, v in row.items():
        if isinstance(k, str) and k.startswith("图纸") and k.endswith("名称"):
            if v is None:
                return True
            if isinstance(v, str) and "未找到图纸名称" in v:
                return True
    return False

def _is_materials_like(text: str) -> bool:
    if not text:
        return False
    keywords = ["图", "表", "示意", "路由", "布置", "安装", "系统", "原理", "分布", "面板"]
    if any(k in text for k in keywords):
        return False
    if re.search(r"(mm|kV|RVV|×|米|条|个|m)", text, flags=re.IGNORECASE) and re.search(r"\d", text):
        return True
    if len(re.findall(r"\d", text)) >= 5:
        return True
    return False

def _needs_forced_ocr(name: str) -> bool:
    if not name:
        return True
    noise_patterns = [
        "系统中断", "机房设备安装", "风险", "安全", "施工说明", "注意事项",
        "导线明细表", "工作量表", "安装/拆除工作量表"
    ]
    if any(p in name for p in noise_patterns):
        return True
    # 若缺少核心图名特征，认为可疑（图、示意、路由、平面、原理、系统、表）
    if not re.search(r"图|示意|路由|平面|原理|系统|分布|布线表|工程量表|材料表|明细表", name):
        return True
    return False

def _deepseek_ocr_extract_text(image_bytes: bytes, debug: bool = False) -> str:
    if not DEEPSEEK_OCR_URL:
        return ""
    token = DEEPSEEK_OCR_KEY or DEEPSEEK_API_KEY
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    fields = {}
    if DEEPSEEK_OCR_MODEL:
        fields["model"] = DEEPSEEK_OCR_MODEL
    if DEEPSEEK_OCR_PROMPT:
        fields["prompt"] = DEEPSEEK_OCR_PROMPT
    files = [
        (DEEPSEEK_OCR_FILE_FIELD, "image.png", "image/png", image_bytes)
    ]
    body, content_type = _encode_multipart_form(fields, files)
    headers["Content-Type"] = content_type
    url = DEEPSEEK_OCR_URL
    resp_data = ""
    max_redirects = 3
    for _ in range(max_redirects + 1):
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status = resp.status
                location = resp.getheader("Location")
                resp_data = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            status = e.code
            location = e.headers.get("Location")
            resp_data = e.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if debug:
                print(f"DeepSeek OCR 请求失败: {e}")
            return ""

        if status in (301, 302, 307, 308) and location:
            url = location
            continue
        break
    try:
        obj = json.loads(resp_data)
        if debug:
            print("DeepSeek OCR raw response:")
            print(resp_data)
        text = _extract_text_from_ocr_response(obj)
        return _strip_html(text)
    except Exception:
        if debug:
            print("DeepSeek OCR raw response (non-JSON):")
            print(resp_data)
        return _strip_html(resp_data)


def _dots_ocr_extract_text(image_bytes: bytes, filename: str = "image.png", content_type: str = "image/png", debug: bool = False) -> str:
    if not DOTS_OCR_URL:
        return ""
    global _DOTS_OCR_AUTH_WARNED, _DOTS_OCR_LAST_TS
    # 服务器限速：<=30次/分钟，做简单节流（每次至少2.2秒）
    now = time.monotonic()
    wait_s = 2.2 - (now - _DOTS_OCR_LAST_TS)
    if wait_s > 0:
        time.sleep(wait_s)
    _DOTS_OCR_LAST_TS = time.monotonic()
    headers = {}
    if DOTS_OCR_KEY:
        headers["Authorization"] = f"Bearer {DOTS_OCR_KEY}"
    files = [
        (DOTS_OCR_FILE_FIELD, filename, content_type, image_bytes)
    ]
    body, content_type = _encode_multipart_form({}, files)
    headers["Content-Type"] = content_type

    url = DOTS_OCR_URL.rstrip("/")
    resp_data = ""
    max_redirects = 3
    for _ in range(max_redirects + 1):
        req = urllib.request.Request(
            url,
            data=body,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                status = resp.status
                location = resp.getheader("Location")
                resp_data = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            status = e.code
            location = e.headers.get("Location")
            resp_data = e.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if debug:
                print(f"DotsOCR 请求失败: {e}")
            return ""

        if status in (301, 302, 307, 308) and location:
            url = location
            continue
        break

    try:
        obj = json.loads(resp_data)
        if debug:
            print("DotsOCR raw response:")
            print(resp_data)
        if isinstance(obj, dict) and "detail" in obj:
            detail = str(obj.get("detail", ""))
            if "未授权" in detail and not _DOTS_OCR_AUTH_WARNED:
                print("DotsOCR 鉴权失败：请检查 DOTS_OCR_KEY 是否正确")
                _DOTS_OCR_AUTH_WARNED = True
        text = _extract_text_from_ocr_response(obj)
        return _strip_html(text)
    except Exception:
        if debug:
            print("DotsOCR raw response (non-JSON):")
            print(resp_data)
        return _strip_html(resp_data)

def run_single_image_external(image_path: str):
    """单图测试：优先 DeepSeek OCR 网关，否则外部视觉模型"""
    print("----------- 单图测试（外部OCR）-----------")
    print(f"图片: {image_path}")
    try:
        img = Image.open(image_path)
        print(f"大小: {img.size}")
    except Exception as e:
        print(f"打开失败: {e}")
        return

    buf = BytesIO()
    img.save(buf, format="PNG")
    image_bytes = buf.getvalue()

    text = ""
    if DEEPSEEK_OCR_URL:
        text = _deepseek_ocr_extract_text(image_bytes, debug=True)
    elif VISION_API_KEY or DEEPSEEK_API_KEY:
        text = _vision_extract_title_from_image(image_bytes)

    if not text:
        print("OCR 结果为空")
        return

    extractor = PdfDrawingExtractor()
    try:
        lines = extractor._clean_lines(text)
        drawing_name = extractor._find_drawing_name_from_lines(lines)
        if not drawing_name:
            drawing_name = extractor._extract_name_from_text_blob(text)
        if not drawing_name:
            drawing_name = _extract_drawing_name_from_ocr_text(text)
        print("OCR 原文:")
        print(text)
        print("图纸名称:", drawing_name or "未识别")
    finally:
        try:
            extractor.root.destroy()
        except Exception:
            pass

def _vision_extract_title_from_image(image_bytes: bytes) -> str:
    """调用外部视觉模型从图片中提取图纸名称（返回纯标题或空串）"""
    # 优先使用本地 VLLM 网关
    if VISION_API_BASE and VISION_API_KEY and VISION_MODEL:
        base_url = VISION_API_BASE
        api_key = VISION_API_KEY
        model = VISION_MODEL
    elif DEEPSEEK_API_KEY:
        base_url = DEEPSEEK_API_BASE
        api_key = DEEPSEEK_API_KEY
        model = DEEPSEEK_MODEL
    else:
        return ""

    # 构造请求
    url = f"{base_url.rstrip('/')}/v1/chat/completions"
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "你是OCR后处理助手，只返回图纸名称本身，不要解释。无法识别则返回空字符串。"
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请从图中找到图纸名称/图名（通常在右下角标题栏）。只输出图纸名称，不要多余文字。"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        }
                    }
                ]
            }
        ],
        "temperature": 0
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = resp.read().decode("utf-8")
        obj = json.loads(resp_data)
        content = obj["choices"][0]["message"]["content"].strip()
        return content
    except Exception:
        return ""

def run_ocr_self_check(image_paths):
    """OCR自检：对比PaddleOCR与Tesseract识别结果"""
    print("----------- OCR 自检对比 -----------")
    if not image_paths:
        print("未提供图片路径")
        return

    # PaddleOCR
    if OCR_ENGINE_TYPE == 'paddle':
        print("PaddleOCR: 可用")
    else:
        print("PaddleOCR: 不可用")

    # Tesseract
    try:
        import pytesseract
        tesseract_ok = True
    except Exception:
        tesseract_ok = False
    print(f"Tesseract: {'可用' if tesseract_ok else '不可用'}")

    for p in image_paths:
        print(f"\n>>> 图片: {p}")
        try:
            img = Image.open(p)
            print(f"大小: {img.size}")
        except Exception as e:
            print(f"打开失败: {e}")
            continue

        if OCR_ENGINE_TYPE == 'paddle':
            try:
                res = ocr_engine.ocr(p, cls=True)
                print("PaddleOCR result:", res)
            except Exception as e:
                print("PaddleOCR failed:", e)

        if tesseract_ok:
            try:
                txt = pytesseract.image_to_string(img, lang='chi_sim')
                print("Tesseract text:", txt[:200])
            except Exception as e:
                print("Tesseract failed:", e)

def run_ocr_single_test(image_path: str):
    """单图OCR能力测试（不写入调试图）"""
    print("----------- OCR 单图测试 -----------")
    print(f"图片: {image_path}")
    try:
        img = Image.open(image_path)
        print(f"大小: {img.size}")
    except Exception as e:
        print(f"打开失败: {e}")
        return

    if OCR_ENGINE_TYPE == 'paddle':
        try:
            res = ocr_engine.ocr(image_path, cls=True)
            print("PaddleOCR result:", res)
        except Exception as e:
            print("PaddleOCR failed:", e)

    try:
        import pytesseract
        txt = pytesseract.image_to_string(img, lang='chi_sim')
        print("Tesseract text:", txt[:300])
    except Exception as e:
        print("Tesseract failed:", e)

    # 外部视觉模型测试（若配置了API）
    if VISION_API_KEY or DEEPSEEK_API_KEY:
        try:
            buf = BytesIO()
            img.save(buf, format="PNG")
            title = _vision_extract_title_from_image(buf.getvalue())
            print("Vision title:", title)
        except Exception as e:
            print("Vision failed:", e)

class PdfDrawingExtractor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.pdf_dir = ""       # PDF文件目录
        self.output_dir = ""    # 输出目录
        # 收紧匹配模式，防止误判
        self.drawing_patterns = [
            r'.*基站天馈线新增示意图.*',
            r'.*天馈线新增示意图.*',
            r'.*布置平面图.*',
            r'.*布置平面.*',
            r'.*设备布置.*',
            r'.*设备分布.*',
            r'.*面板图.*',
            r'.*平面图.*',
            r'.*立面图.*',
            r'.*剖面图.*',
            r'.*系统图.*',
            r'.*原理图.*',
            r'.*天馈线安装示意图.*',
            r'.*天馈线系统安装.*',
            r'.*设备安装.*',
            r'.*无线机房远端.*',
            r'.*拆除示意图.*',        # 修正：加“示意图”或“图”后缀
            r'.*拆除图.*',
            r'.*路由图.*',
            r'.*GPS示意图.*',
            r'.*GPS馈线路由图.*',
            r'.*GPS.*安装.*',        # 修正：加“安装”限定
            r'.*GPS无源分路.*',
            r'.*分波器.*',
            r'.*波分.*',
            r'.*布线表.*',
            r'.*工程量表.*',
            r'.*明细表.*'
        ]

    def _clean_lines(self, text: str):
        """清理提取文本为行列表"""
        if not text:
            return []
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines

    def _normalize_line(self, line: str) -> str:
        """规范化文本，用于更鲁棒的模式匹配"""
        return re.sub(r"\s+", "", line or "")

    def _is_noise(self, line: str) -> bool:
        """判断是否为噪声行（页码、日期、说明等）"""
        if not line:
            return True
        
        # 归一化
        norm = line.strip()
        
        # 1. 纯数字或极短字符 (可能是页码或乱码)
        if re.match(r'^[0-9\-\.\/]{1,10}$', norm):
            return True
        if len(norm) < 2:
            return True

        # 1.1 过长或包含大量型号/规格字符（如RVVZ-1kV）
        if len(norm) > 60:
            # 若包含图名关键词，允许通过
            if any(k in norm for k in ["图", "示意", "平面", "立面", "剖面", "系统", "原理", "布置", "安装", "路由", "布线", "工程量表", "明细表", "馈线路由图", "GPS", "分布", "面板"]):
                return False
            return True
        if re.search(r"[A-Z]{2,}|\d{3,}|[A-Z]+-?\d+", norm):
            # 若含型号且不含图名关键词，认为噪声
            if not any(k in norm for k in ["图", "示意", "平面", "立面", "剖面", "系统", "原理", "布置", "安装", "路由", "馈线路由图", "GPS"]):
                return True
            
        # 2. 包含特定排除词 (施工说明、图框标签等)
        exclude_keywords = [
            "说明", "注意", "要求", "规范", "日期", "Date", 
            "比例", "Scale", "设计", "Desig", "校对", "Check", 
            "审核", "Approv", "图号", "Drawing No", "版本", "Rev",
            "单位", "Unit", "第", "页", "共", "Page",
            "措施", "洗手", "消毒", "操作", "安全", "禁止", "未经", "许可", 
            "启动", "关停", "拆除", "中断", "损坏", "责任" 
        ]
        # 如果已包含图名关键词，直接放行（包括"表"类图名）
        if any(k in norm for k in ["图", "示意", "平面", "立面", "剖面", "系统", "原理", "布置", "安装", "路由", "馈线路由图", "GPS", "布线表", "工程量表", "明细表", "分布", "面板"]):
            return False

        if any(k in norm for k in exclude_keywords):
            # 特例：如果有“图纸名称”或“图名”标签，可能是包含标签的行，需要特殊处理，
            # 但通常我们要提取的是值而不是标签行。这里先暂定为噪声，
            # 除非它同时包含强关键字（如“平面图”）。
            # 如果行里包含“说明”但结尾是“图”，可能是“说明图”，需谨慎。
            # 这里简单处理：如果包含这些词，且不以“图”结尾，则认为是噪声。
            if not norm.endswith("图") and not norm.endswith("表"):
                return True
                
        return False

    def _ocr_bottom_right(self, pdf_path, page_num, save_debug: bool = False):
        """对页面右下角进行OCR识别"""
        if not USE_OCR:
            return []
        if not OCR_ENGINE_TYPE and not DEEPSEEK_OCR_URL and not DOTS_OCR_URL:
            return []

        doc = None
        try:
            doc = fitz.open(pdf_path)  # type: ignore
            page = doc[page_num]
            rect = page.rect
            # 多裁剪区域（标题栏更偏右 + 底部条带 + 更宽底部）
            # 增加旋转内容裁剪区域（内容逆时针旋转90度时，标题栏在左侧下方）
            rotated_content_clips = [
                # 左侧下半部分（旋转内容的标题栏位置）- 精简为1个最有效区域
                fitz.Rect(0, rect.height * 0.45, rect.width * 0.28, rect.height),
            ]
            if FAST_OCR:
                clip_rects = [
                    # 极速模式：优先旋转内容区域（对无文本层PDF最有效）
                    fitz.Rect(0, rect.height * 0.45, rect.width * 0.28, rect.height),  # 旋转内容
                    # 右下角标题栏 - 覆盖最底部区域（图名通常在底部15%内）
                    fitz.Rect(rect.width * 0.50, rect.height * 0.80, rect.width, rect.height),
                    # 右下角稍大范围（底部25%）
                    fitz.Rect(rect.width * 0.45, rect.height * 0.75, rect.width, rect.height),
                ]
                rotated_content_clips = [clip_rects[0]]  # 第一个是旋转内容区域
            else:
                clip_rects = [
                    # 中右标题栏聚焦（优先捕捉右侧图名列）
                    fitz.Rect(rect.width * 0.55, rect.height * 0.35, rect.width, rect.height * 0.78),
                    fitz.Rect(rect.width * 0.60, rect.height * 0.30, rect.width, rect.height * 0.70),
                    # 底部大条带兜底（适配A3/旋转后标题栏偏中下）
                    fitz.Rect(rect.width * 0.00, rect.height * 0.55, rect.width, rect.height * 0.98),
                    fitz.Rect(rect.width * 0.00, rect.height * 0.45, rect.width, rect.height * 0.95),
                    # 中右标题栏带（覆盖标题块偏中位置）
                    fitz.Rect(rect.width * 0.35, rect.height * 0.40, rect.width, rect.height * 0.78),
                    fitz.Rect(rect.width * 0.20, rect.height * 0.40, rect.width, rect.height * 0.78),
                    # 标题栏底部右侧（优先，避免上方干扰）
                    fitz.Rect(rect.width * 0.30, rect.height * 0.75, rect.width, rect.height * 0.98),
                    fitz.Rect(rect.width * 0.40, rect.height * 0.75, rect.width, rect.height * 0.95),
                    fitz.Rect(rect.width * 0.55, rect.height * 0.75, rect.width, rect.height * 0.92),
                    fitz.Rect(rect.width * 0.70, rect.height * 0.74, rect.width, rect.height * 0.92),
                    # 标题栏中右区（兜底）
                    fitz.Rect(rect.width * 0.45, rect.height * 0.68, rect.width, rect.height * 0.88),
                    fitz.Rect(rect.width * 0.60, rect.height * 0.62, rect.width, rect.height * 0.80),
                    # 稍大一点的兜底，覆盖标题行完整高度
                    fitz.Rect(rect.width * 0.58, rect.height * 0.60, rect.width, rect.height * 0.98),
                    # 标题栏整体右半区域兜底
                    fitz.Rect(rect.width * 0.35, rect.height * 0.62, rect.width, rect.height * 0.95),
                    # A3/旋转后更大范围兜底（更靠中下部）
                    fitz.Rect(rect.width * 0.20, rect.height * 0.70, rect.width, rect.height * 0.98),
                    fitz.Rect(rect.width * 0.15, rect.height * 0.62, rect.width, rect.height * 0.95),
                    fitz.Rect(rect.width * 0.10, rect.height * 0.58, rect.width, rect.height * 0.92)
                ]

            debug_dir = None
            if save_debug:
                debug_dir = Path(self.output_dir or os.getcwd()) / "ocr_debug"
                debug_dir.mkdir(parents=True, exist_ok=True)

            dots_calls = 0
            best_lines = None
            best_score = -999
            for idx, clip_rect in enumerate(clip_rects, 1):
                # 提高分辨率以提升OCR准确率（加速模式用更低分辨率）
                scale = 2 if FAST_OCR else 5
                pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip_rect)
                img_data = pix.tobytes("png")

                # 转为 PIL 图像并预处理
                img = Image.open(BytesIO(img_data)).convert("RGB")
                img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

                # 预处理：放大 + 锐化 + OTSU（FAST模式用更小的放大倍数）
                resize_factor = 1.5 if FAST_OCR else 2.5
                img_bgr = cv2.resize(img_bgr, None, fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_CUBIC)
                kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], dtype=np.float32)
                img_sharp = cv2.filter2D(img_bgr, -1, kernel)
                img_gray = cv2.cvtColor(img_sharp, cv2.COLOR_BGR2GRAY)
                img_gray_eq = cv2.equalizeHist(img_gray)
                _, img_bin = cv2.threshold(img_gray_eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                # 轻度膨胀，增强细字
                img_bin_dilate = cv2.dilate(img_bin, np.ones((2, 2), np.uint8), iterations=1)

                # 额外裁剪：只保留右侧标题栏，去掉左侧蓝色印章
                h, w = img_bgr.shape[:2]
                right_start = int(w * 0.30)
                right_start2 = int(w * 0.55)
                img_bgr_right = img_bgr[:, right_start:]
                img_bin_right = img_bin[:, right_start:]
                img_bgr_right2 = img_bgr[:, right_start2:]
                img_bin_right2 = img_bin[:, right_start2:]

                # 逆旋转 90 度（处理横竖方向异常的标题栏）
                img_bgr_rot90 = cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE)
                img_bin_rot90 = cv2.rotate(img_bin, cv2.ROTATE_90_COUNTERCLOCKWISE)
                img_bgr_right_rot90 = cv2.rotate(img_bgr_right, cv2.ROTATE_90_COUNTERCLOCKWISE)
                img_bin_right_rot90 = cv2.rotate(img_bin_right, cv2.ROTATE_90_COUNTERCLOCKWISE)
                img_bgr_right2_rot90 = cv2.rotate(img_bgr_right2, cv2.ROTATE_90_COUNTERCLOCKWISE)
                img_bin_right2_rot90 = cv2.rotate(img_bin_right2, cv2.ROTATE_90_COUNTERCLOCKWISE)

                if FAST_OCR:
                    # 极速模式：只用锐化后的原图，不做额外裁剪和旋转变体
                    variants = [
                        ("full", img_sharp, img_bin),
                    ]
                else:
                    variants = [
                        ("full", img_sharp, img_bin),
                        ("right", img_bgr_right, img_bin_right),
                        ("right2", img_bgr_right2, img_bin_right2),
                        ("full_ccw90", img_bgr_rot90, img_bin_rot90),
                        ("right_ccw90", img_bgr_right_rot90, img_bin_right_rot90),
                        ("right2_ccw90", img_bgr_right2_rot90, img_bin_right2_rot90),
                    ]

                dots_tried = False
                for vname, v_bgr, v_bin in variants:
                    lines = []
                    # 保存调试图（原图 & 预处理图）
                    if save_debug and debug_dir:
                        debug_path = debug_dir / f"page_{page_num+1}_clip_{idx}_{vname}.png"
                        debug_bin_path = debug_dir / f"page_{page_num+1}_clip_{idx}_{vname}_bin.png"
                        try:
                            ok_color, buf_color = cv2.imencode(".png", v_bgr)
                            if ok_color:
                                with open(debug_path, "wb") as f:
                                    f.write(buf_color.tobytes())
                            ok, buf = cv2.imencode(".png", v_bin)
                            if ok:
                                with open(debug_bin_path, "wb") as f:
                                    f.write(buf.tobytes())
                            print(f"  > OCR调试图已保存: {debug_path}")
                        except Exception as e:
                            print(f"  > OCR调试图保存失败: {e}")
                    else:
                        debug_path = None
                        debug_bin_path = None

                    if OCR_ENGINE_TYPE == 'paddle':
                        target_path = str(debug_path) if debug_path else None
                        if target_path:
                            result = ocr_engine.ocr(target_path, cls=True)
                        else:
                            result = ocr_engine.ocr(v_bgr, cls=True)
                        if result and result[0]:
                            lines = [line[1][0] for line in result[0]]

                        if not lines:
                            if debug_bin_path:
                                result = ocr_engine.ocr(str(debug_bin_path), cls=True)
                            else:
                                result = ocr_engine.ocr(v_bin, cls=True)
                            if result and result[0]:
                                lines = [line[1][0] for line in result[0]]

                    elif OCR_ENGINE_TYPE == 'tesseract':
                        if debug_path:
                            text = pytesseract.image_to_string(Image.open(str(debug_path)), lang='chi_sim')
                            if not text.strip() and debug_bin_path:
                                text = pytesseract.image_to_string(Image.open(str(debug_bin_path)), lang='chi_sim')
                        else:
                            text = pytesseract.image_to_string(Image.fromarray(v_bgr[:, :, ::-1]), lang='chi_sim')
                        lines = text.split('\n')

                    # 若本地OCR无结果，优先尝试 DotsOCR，其次 DeepSeek OCR
                    if not lines and DOTS_OCR_URL and USE_DOTS_OCR and not dots_tried:
                        try:
                            if DOTS_OCR_MAX_TRIES > 0 and dots_calls >= DOTS_OCR_MAX_TRIES:
                                break
                            # DotsOCR 优先使用灰度二值图（full 变体更贴近标题栏清晰文字）
                            send_img = v_bin if vname.startswith("full") else v_bgr
                            send_img = _downscale_to_max_pixels(send_img)
                            ok_img, buf_img = cv2.imencode(".png", send_img)
                            if ok_img:
                                ocr_text = _dots_ocr_extract_text(buf_img.tobytes(), debug=DOTS_OCR_DEBUG)
                                if ocr_text:
                                    lines = self._clean_lines(ocr_text)
                                    if hasattr(self, "_trace_logs") and isinstance(self._trace_logs, list):
                                        sample = ocr_text.replace("\n", " ")[:200]
                                        self._trace_logs.append(f"[页 {page_num + 1}] DotsOCR片段命中: {sample}")
                                else:
                                    if hasattr(self, "_trace_logs") and isinstance(self._trace_logs, list):
                                        self._trace_logs.append(f"[页 {page_num + 1}] DotsOCR片段无结果")
                            dots_calls += 1
                        except Exception:
                            pass
                        dots_tried = True
                    if not lines and DEEPSEEK_OCR_URL and (ALLOW_DEEPSEEK_OCR_FALLBACK or not (DOTS_OCR_URL and USE_DOTS_OCR)):
                        try:
                            ok_img, buf_img = cv2.imencode(".png", v_bgr)
                            if ok_img:
                                ocr_text = _deepseek_ocr_extract_text(buf_img.tobytes())
                                if ocr_text:
                                    lines = self._clean_lines(ocr_text)
                        except Exception:
                            pass

                    # 若仍无结果，尝试外部视觉模型（加速模式下跳过）
                    if not lines and (VISION_API_KEY or DEEPSEEK_API_KEY) and not FAST_OCR:
                        try:
                            ok_img, buf_img = cv2.imencode(".png", v_bgr)
                            if ok_img:
                                title = _vision_extract_title_from_image(buf_img.tobytes())
                                if title:
                                    lines = [title]
                        except Exception:
                            pass

                    if lines:
                        # 若未包含标题特征，继续尝试下一裁剪/变体
                        joined = "".join(lines)
                        if ("工程名称" not in joined) and not re.search(r"图|表|示意|路由|布线|平面|原理|系统", joined):
                            lines = []
                            continue
                        candidate = _pick_drawing_name_simple("\n".join(lines))
                        score = _score_title(candidate) if candidate else -999
                        if vname == "full" and idx == 2:
                            score += 15
                        if score > best_score:
                            best_score = score
                            best_lines = lines
                        # FAST_OCR模式：找到有效结果（包含图名特征）立即返回
                        if FAST_OCR and candidate and score > 0:
                            return best_lines

            return best_lines or []
        except Exception as e:
            print(f"OCR识别失败 (Page {page_num}): {e}")
            return []
        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass

    def _ocr_full_page(self, pdf_path, page_num, save_debug: bool = False):
        """对整页进行OCR识别（仅在局部裁剪失败时兜底）"""
        if not USE_OCR:
            return []
        if not OCR_ENGINE_TYPE and not DEEPSEEK_OCR_URL and not DOTS_OCR_URL:
            return []

        doc = None
        try:
            doc = fitz.open(pdf_path)  # type: ignore
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3))
            img_data = pix.tobytes("png")

            img = Image.open(BytesIO(img_data)).convert("RGB")
            img_bgr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
            img_bgr = cv2.resize(img_bgr, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
            img_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
            img_gray_eq = cv2.equalizeHist(img_gray)
            _, img_bin = cv2.threshold(img_gray_eq, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            variants = [
                ("full", img_bgr, img_bin),
                ("full_ccw90", cv2.rotate(img_bgr, cv2.ROTATE_90_COUNTERCLOCKWISE), cv2.rotate(img_bin, cv2.ROTATE_90_COUNTERCLOCKWISE)),
            ]

            debug_dir = None
            if save_debug:
                debug_dir = Path(self.output_dir or os.getcwd()) / "ocr_debug"
                debug_dir.mkdir(parents=True, exist_ok=True)

            for vname, v_bgr, v_bin in variants:
                if save_debug and debug_dir:
                    debug_path = debug_dir / f"page_{page_num+1}_full_{vname}.png"
                    debug_bin_path = debug_dir / f"page_{page_num+1}_full_{vname}_bin.png"
                    try:
                        ok_color, buf_color = cv2.imencode(".png", v_bgr)
                        if ok_color:
                            with open(debug_path, "wb") as f:
                                f.write(buf_color.tobytes())
                        ok_bin, buf_bin = cv2.imencode(".png", v_bin)
                        if ok_bin:
                            with open(debug_bin_path, "wb") as f:
                                f.write(buf_bin.tobytes())
                    except Exception:
                        pass

                if DOTS_OCR_URL and USE_DOTS_OCR:
                    # 先灰度二值，再彩色兜底
                    for img_to_send in (v_bin, v_bgr):
                        img_to_send = _downscale_to_max_pixels(img_to_send)
                        ok_img, buf_img = cv2.imencode(".png", img_to_send)
                        if ok_img:
                            ocr_text = _dots_ocr_extract_text(buf_img.tobytes(), debug=DOTS_OCR_DEBUG)
                            if ocr_text:
                                lines = self._clean_lines(ocr_text)
                                if lines:
                                    return lines
            return []
        except Exception as e:
            print(f"整页OCR失败 (Page {page_num}): {e}")
            return []
        finally:
            if doc:
                try:
                    doc.close()
                except Exception:
                    pass

    def _find_drawing_name_from_lines(self, lines):
        """从行列表中匹配图纸名称"""
        if not lines:
            return None

        clean_lines = [line.strip() for line in lines if line.strip()]

        # 0) GPS/馈线路由图优先（避免被安全说明误判）
        for line in clean_lines:
            if "GPS" in line and ("馈线路由图" in line or "路由图" in line):
                candidate = re.split(r"出图日期|比例|图号|描图|单位|审核|校对", line)[0]
                return candidate.strip()
            if "馈线路由图" in line:
                candidate = re.split(r"出图日期|比例|图号|描图|单位|审核|校对", line)[0]
                return candidate.strip()
        
        # 策略1：优先正则匹配（强规则）
        has_layout_title = any(("平面图" in l) or ("设备布置平面" in l) for l in clean_lines)
        for line in clean_lines:
            normalized = self._normalize_line(line)
            for pattern in self.drawing_patterns:
                if re.search(pattern, normalized):
                    # 过滤明显噪声
                    if not self._is_noise(line):
                        # 避免“DCPD10B面板图”等型号面板图抢占“设备布置平面图”结果
                        if "面板图" in line:
                            if has_layout_title:
                                continue
                            if not re.search(r"基站|无线|机房|设备|天馈线", line):
                                continue
                        # 若仅命中“设备安装”等弱词，要求同时包含强图名特征
                        if re.search(r"设备安装", line) and not re.search(r"图|示意|路由|布线|平面|系统|原理|表", line):
                            continue
                        # 对于"材料表"和"设备分布"，不需要前缀清理，直接返回
                        if re.search(r"材料表|设备分布", line):
                            return line
                        # 清理前置噪声词（如"系统中断"等），保留从"基站/天馈线/机房/设备/无线"开始的部分
                        # 注意：序号括号可能是混合形式，如 （一) 或 (一），需要兼容
                        clean_m = re.search(r"(基站|天馈线|机房|设备|无线)[^，,。;；\n]*?(示意图|平面图|立面图|剖面图|系统图|原理图|路由图|布线表|工程量表|明细表|馈线路由图)((?:[\(（][^\)）]{1,6}[\)）]|[一二三四五六七八九十]+))?", line)
                        if clean_m:
                            return clean_m.group(0)
                        return line

        # 策略2：倒序查找具备“图名特征”的行（弱规则）
        # 图名通常在最后几行，且通常以“图”、“表”、“示意”结尾
        for line in reversed(clean_lines):
            # 先过滤明显噪声
            if self._is_noise(line):
                continue

            # 优先截取包含图名关键词的子串（允许较长行）
            # 注意：每个分支都要带上可选的序号后缀 ([\(（][^\)）]{1,3}[\)）])?
            paren_suffix = r"(?:[\(（][^\)）]{1,6}[\)）]|[一二三四五六七八九十]+)?"
            m = re.search(
                rf"(基站[^，,。;；\n]{{0,50}}?(?:GPS)?馈线路由图{paren_suffix}|基站[^，,。;；\n]{{0,50}}?布线表{paren_suffix}|基站[^，,。;；\n]{{0,50}}?工程量表{paren_suffix}|基站[^，,。;；\n]{{0,50}}?材料表{paren_suffix}|基站[^，,。;；\n]{{0,50}}?明细表{paren_suffix}|[^，,。;；\n]*?馈线路由图{paren_suffix}|[^，,。;；\n]*?路由图{paren_suffix}|[^，,。;；\n]*?安装示意图{paren_suffix}|[^，,。;；\n]*?设备分布{paren_suffix}|[^，,。;；\n]*?平面图{paren_suffix}|[^，,。;；\n]*?示意图{paren_suffix}|[^，,。;；\n]*?布线表{paren_suffix}|[^，,。;；\n]*?工程量表{paren_suffix}|[^，,。;；\n]*?材料表{paren_suffix}|[^，,。;；\n]*?明细表{paren_suffix})",
                line
            )
            if m:
                candidate = re.split(r"出图日期|比例|图号|描图|单位|审核|校对", m.group(0))[0]
                # 对于"材料表"和"设备分布"，不需要前缀清理，直接返回
                if re.search(r"材料表|设备分布", candidate):
                    if 4 <= len(candidate) <= 80:
                        return candidate.strip()
                # 清理前置噪声词（如"系统中断"等），保留从"基站/天馈线/机房/设备/无线"开始的部分
                # 注意：序号括号可能是混合形式，如 （一) 或 (一），需要兼容
                clean_m = re.search(r"(基站|天馈线|机房|设备|无线)[^，,。;；\n]*?(示意图|平面图|立面图|剖面图|系统图|原理图|路由图|布线表|工程量表|明细表|馈线路由图)((?:[\(（][^)\）]{1,6}[\)）]|[一二三四五六七八九十]+))?", candidate)
                if clean_m:
                    candidate = clean_m.group(0)
                if 4 <= len(candidate) <= 80:
                    return candidate.strip()
                
            # 检查是否包含核心图名特征
            # 特征1：以特定后缀结尾
            if line.endswith(("图", "表", "示意", "系统", "大样", "分布", "面板图", "(一)", "(二)", "(三)", "（一）", "（二）", "（三）")):
                return line
                
            # 特征2：包含核心词汇
            strong_keywords = ["平面", "立面", "剖面", "系统", "原理", "布置", "安装", "走向", "路由", "配置", "清单", "示意", "馈线路由", "分布", "面板"]
            if any(k in line for k in strong_keywords):
                # 需要包含图名特征词，避免“系统中断”等误判
                if not re.search(r"图|表|示意|路由|平面|原理|分布|面板", line):
                    continue
                # 行长度约束，避免把说明性长句当图名
                if 4 <= len(line) <= 80:
                    return line

        return None

    def _extract_name_from_text_blob(self, text: str):
        """从OCR合并文本中用正则二次提取图纸名称"""
        if not text:
            return None

        compact = re.sub(r"\s+", "", text)

        # 1) 优先从“图纸名称/图名”标签后抽取
        label_match = re.search(r"(图纸名称|图纸名|图名)[:：]?(.*?)(?=图号|比例|日期|设计|审核|审查|校对|$)", compact)
        if label_match:
            candidate = label_match.group(2)
            if candidate:
                return candidate

        # 2) 从整段文本中直接抓取带“图/示意图/平面图”等关键词的片段
        # 注意：在关键词后加上可选的序号后缀
        keyword_pattern = r"[^,，;；。]{2,160}(GPS馈线路由图|馈线路由图|设备分布|面板图|布置平面图|平面图|立面图|剖面图|系统图|原理图|基站天馈线新增示意图|天馈线新增示意图|示意图|安装示意图|路由图|布线表|工程量表|明细表)((?:[\(（][^\)）]{1,6}[\)）]|[一二三四五六七八九十]+))?[^,，;；。]{0,60}"
        m = re.search(keyword_pattern, compact)
        if m:
            candidate = m.group(0)
            # 去掉开头的序号
            candidate = re.sub(r"^[0-9A-Za-z]+", "", candidate)
            if 4 <= len(candidate) <= 80:
                return candidate

        # 3) 回退到现有正则模式
        for pattern in self.drawing_patterns:
            m2 = re.search(pattern, compact)
            if m2:
                candidate = m2.group(0)
                if 4 <= len(candidate) <= 80:
                    return candidate

        return None

    def _extract_text_by_boxes(self, page, boxes):
        """按多个裁剪区域尝试提取文本"""
        for box in boxes:
            try:
                cropped_page = page.crop(box)
                text = cropped_page.extract_text() if cropped_page else ""
                if text and text.strip():
                    return text
            except Exception:
                continue
        return ""

    def select_directories(self):
        """选择输入和输出目录"""
        # 选择PDF文件目录
        self.pdf_dir = filedialog.askdirectory(
            title="选择PDF文件所在目录"
        )
        if not self.pdf_dir:
            return False

        # 选择输出目录
        self.output_dir = filedialog.askdirectory(
            title="选择结果输出目录"
        )
        if not self.output_dir:
            return False

        return True

    def get_pdf_files(self):
        """获取目录中的所有PDF文件"""
        pdf_files = []
        for root, _, files in os.walk(self.pdf_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        return pdf_files

    def process_pdfs(self):
        """处理PDF文件"""
        # 打印当前 OCR 引擎状态
        print(f"----------- OCR 状态检查 -----------")
        if OCR_ENGINE_TYPE == 'paddle':
            print(f"Current OCR Engine: PaddleOCR (已启用)")
        elif OCR_ENGINE_TYPE == 'tesseract':
            print(f"Current OCR Engine: Tesseract (已启用)")
        else:
            print(f"Current OCR Engine: 无 (未检测到 PaddleOCR 或 Tesseract)")
            print(f"提示: 如果需要提取扫描件或图片中的文字，请安装 PaddleOCR 或 Tesseract OCR")
        if DOTS_OCR_URL and USE_DOTS_OCR:
            print("DotsOCR: 已配置")
        print(f"------------------------------------")

        # 选择目录（若已指定则跳过对话框）
        if not self.pdf_dir or not self.output_dir:
            if not self.select_directories():
                messagebox.showinfo("提示", "未选择目录")
                return

        # 获取所有PDF文件
        pdf_files = self.get_pdf_files()
        if not pdf_files:
            messagebox.showinfo("提示", f"在 {self.pdf_dir} 中未找到PDF文件")
            return

        if DEBUG_FIRST_PDF:
            pdf_files = pdf_files[:1]
            print("[调测] 仅处理首个PDF文件")

        results = []
        trace_logs = []
        total_files = len(pdf_files)

        # 读取最近一次结果，避免重复识别已成功的文件
        latest_excel = _find_latest_result_excel(self.output_dir)
        existing_rows = _load_existing_results(latest_excel) if latest_excel else {}
        if latest_excel and existing_rows:
            trace_logs.append(f"[跳过策略] 读取历史结果: {latest_excel}")

        # 处理每个PDF文件
        for i, pdf_path in enumerate(pdf_files, 1):
            print(f"正在处理 {Path(pdf_path).name} ({i}/{total_files})")
            trace_logs.append(f"===== 文件开始: {Path(pdf_path).name} =====")
            rel_path = str(Path(pdf_path).relative_to(self.pdf_dir))
            key = (Path(pdf_path).name, rel_path)
            # 若历史结果没有“未找到图纸名称”，则跳过
            if key in existing_rows:
                if not _row_has_missing(existing_rows[key]):
                    results.append(existing_rows[key])
                    trace_logs.append(f"[跳过] 已完成: {Path(pdf_path).name}")
                    trace_logs.append(f"===== 文件结束: {Path(pdf_path).name} =====\n")
                    continue

            drawing_names = self.extract_drawing_names(pdf_path, trace_logs)
            trace_logs.append(f"===== 文件结束: {Path(pdf_path).name} =====\n")
            
            if drawing_names:
                row = {
                    '文件名': Path(pdf_path).name,
                    '文件路径': rel_path,
                    '图纸数量': len(drawing_names)
                }
                for j, name in enumerate(drawing_names, 1):
                    row[f'图纸{j}名称'] = name
                
                # 智能合并：如果历史结果存在，用新的成功结果替换旧结果中失败的页面
                if key in existing_rows:
                    old_row = existing_rows[key]
                    old_count = _row_extracted_count(old_row)
                    new_count = len(drawing_names)
                    # 页数相同时，逐页合并
                    if old_count == new_count:
                        for j in range(1, new_count + 1):
                            col = f'图纸{j}名称'
                            old_val = str(old_row.get(col, '')).strip()
                            new_val = str(row.get(col, '')).strip()
                            # 如果旧值是"未找到"，用新值替换
                            if '未找到图纸名称' in old_val and new_val and '未找到图纸名称' not in new_val:
                                row[col] = new_val
                                trace_logs.append(f"[合并] 页{j} 用新结果替换旧失败: {new_val}")
                            # 如果新值是"未找到"但旧值有效，保留旧值
                            elif '未找到图纸名称' in new_val and old_val and '未找到图纸名称' not in old_val:
                                row[col] = old_val
                                trace_logs.append(f"[合并] 页{j} 保留旧成功结果: {old_val}")
                
                results.append(row)
            elif key in existing_rows:
                # 若本次未提取到，但历史有结果，保留历史
                results.append(existing_rows[key])
                trace_logs.append(f"[保留] 使用历史结果: {Path(pdf_path).name}")

        if results:
            # 生成输出文件路径
            timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(
                self.output_dir, 
                f'图纸名称提取结果_{timestamp}.xlsx'
            )

            # 保存结果到 Excel 的两个 sheet：原始提取 + 合并后名称
            df = pd.DataFrame(results)

            # 构建合并后名称列表
            combined_rows = []
            for row in results:
                base_name = Path(row['文件名']).stem.strip()  # 去掉扩展名作为基名
                count = int(row.get('图纸数量', 0))
                for j in range(1, count + 1):
                    key = f'图纸{j}名称'
                    name = row.get(key, '')
                    if name and str(name).strip():
                        clean_name = str(name).strip()
                        # 防止图纸名称中误带文件后缀（如 .pdf/.dwg）
                        clean_name = re.sub(r'\.(pdf|dwg|dxf|jpg|jpeg|png|tif|tiff)$', '', clean_name, flags=re.IGNORECASE)
                        combined_name = base_name + clean_name
                        combined_rows.append({
                            '文件名': base_name,
                            '原图纸名称': clean_name,
                            '合并后名称': combined_name
                        })

            # 使用 ExcelWriter 写入多个 sheet（需要 openpyxl）
            try:
                with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='原始提取', index=False)
                    # 即便 combined_rows 为空也写入一个空表，便于查看
                    pd.DataFrame(combined_rows).to_excel(writer, sheet_name='合并后名称', index=False)
            except Exception as e:
                # 回退：若 openpyxl 不可用，仍保存单个 sheet 并告知用户
                df.to_excel(output_file, index=False)
                messagebox.showwarning("警告", f"保存为多 sheet 失败（{e}），已保存单表：{output_file}")
            
            # 在输出目录创建日志文件
            log_file = os.path.join(
                self.output_dir, 
                f'处理日志_{timestamp}.txt'
            )
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"处理时间: {timestamp}\n")
                f.write(f"PDF文件目录: {self.pdf_dir}\n")
                f.write(f"总文件数: {total_files}\n")
                f.write(f"成功提取: {len(results)}\n")
                f.write(f"结果文件: {output_file}\n\n")
                if trace_logs:
                    f.write("--------- 详细过程日志 ---------\n")
                    f.write("\n".join(trace_logs))

            messagebox.showinfo(
                "完成", 
                f"已处理 {total_files} 个文件\n"
                f"成功提取 {len(results)} 个文件的图纸名称\n"
                f"结果已保存到：\n{output_file}"
            )
        else:
            messagebox.showwarning("警告", "未提取到任何图纸名称")

    def extract_drawing_names(self, pdf_path, trace_logs=None):
        """提取单个PDF文件中的图纸名称"""
        drawing_names = []
        text_layer_unreliable = False
        if trace_logs is None:
            trace_logs = []
        self._trace_logs = trace_logs

        try:
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)

                for page_num in range(total_pages):
                    page = pdf.pages[page_num]
                    drawing_name = None
                    
                    # 1. 尝试直接文本提取（多区域覆盖）
                    width = page.width
                    height = page.height
                    crop_boxes = [
                        (width * 0.55, height * 0.78, width, height),      # 右下角
                        (width * 0.45, height * 0.72, width, height),      # 右下角扩展
                        (width * 0.35, height * 0.70, width, height),      # 右下角更大范围
                        (width * 0.55, height * 0.30, width, height * 0.70),  # 右侧中部（新增：覆盖图名在中上的情况）
                        (width * 0.60, height * 0.35, width, height * 0.65),  # 右侧中部窄区域
                    ]
                    
                    text_lines = []
                    # 1.1 尝试右下角区域
                    raw_text = self._extract_text_by_boxes(page, crop_boxes)
                    text_lines = self._clean_lines(raw_text)
                    drawing_name = self._find_drawing_name_from_lines(text_lines)
                    if drawing_name:
                        trace_logs.append(f"[页 {page_num + 1}] 文本层右下角命中: {drawing_name}")
                        trimmed = _trim_drawing_name(drawing_name)
                        if not trimmed:
                            drawing_name = None
                            text_layer_unreliable = True
                            trace_logs.append(f"[页 {page_num + 1}] 文本层命中但判定无效")
                        else:
                            drawing_name = trimmed

                    # 1.2 尝试整页文本
                    if not drawing_name:
                        full_text = page.extract_text() or ""
                        text_lines = self._clean_lines(full_text)
                        drawing_name = self._find_drawing_name_from_lines(text_lines)
                        if drawing_name:
                            trace_logs.append(f"[页 {page_num + 1}] 文本层全页命中: {drawing_name}")
                            trimmed = _trim_drawing_name(drawing_name)
                            if not trimmed:
                                drawing_name = None
                                text_layer_unreliable = True
                                trace_logs.append(f"[页 {page_num + 1}] 文本层命中但判定无效")
                            else:
                                drawing_name = trimmed

                    # 只要有任一页文本层失败，就标记整份文件不可靠
                    if not drawing_name:
                        text_layer_unreliable = True
                        trace_logs.append(f"[页 {page_num + 1}] 文本层未命中")

                    # 2. 如果文本提取失败或看起来有问题，且允许OCR时尝试OCR
                    if (not drawing_name or _needs_forced_ocr(drawing_name)) and USE_OCR:
                        if OCR_ENGINE_TYPE or DEEPSEEK_OCR_URL or (DOTS_OCR_URL and USE_DOTS_OCR):
                            engine_label = OCR_ENGINE_TYPE or ("DotsOCR" if (DOTS_OCR_URL and USE_DOTS_OCR) else "DeepSeek-OCR")
                            print(f"  > 页面 {page_num+1} 文本层未匹配到图名，尝试 OCR ({engine_label})...")
                            ocr_lines = self._ocr_bottom_right(pdf_path, page_num, save_debug=DOTS_OCR_DEBUG)
                            if not ocr_lines and not FAST_OCR:
                                # 局部裁剪失败时尝试整页最大提取
                                ocr_lines = self._ocr_full_page(pdf_path, page_num, save_debug=DOTS_OCR_DEBUG)
                                if ocr_lines:
                                    trace_logs.append(f"[页 {page_num + 1}] 整页OCR命中")
                            
                            # OCR后再次清洗与查找
                            if ocr_lines:
                                tail_lines = 6
                                tail_preview = ocr_lines[-tail_lines:] if len(ocr_lines) > tail_lines else ocr_lines
                                print(f"    OCR 原始结果 (后{tail_lines}行): {tail_preview}")
                                blob_text = "\n".join(ocr_lines)
                                # 优先基于 OCR 文本直接抽取图名片段（仅看后6行）
                                drawing_name = _pick_drawing_name_simple(blob_text, tail_lines=tail_lines)
                                if not drawing_name:
                                    clean_ocr_lines = self._clean_lines(blob_text)
                                    drawing_name = self._find_drawing_name_from_lines(clean_ocr_lines)
                                if not drawing_name:
                                    drawing_name = self._extract_name_from_text_blob(blob_text)
                                # 仍未命中：启用“最大提取”（不截尾，保留完整文本）
                                if not drawing_name:
                                    drawing_name = _pick_drawing_name_simple(blob_text, tail_lines=0)
                                if not drawing_name:
                                    drawing_name = _extract_title_loose(blob_text)

                                if drawing_name and _is_materials_like(drawing_name):
                                    drawing_name = None
                                if drawing_name and not re.search(r"(图|表|示意|安装|路由|布线|平面|系统|原理|分布|面板)", drawing_name):
                                    drawing_name = None

                                if drawing_name:
                                    trimmed = _trim_drawing_name(drawing_name)
                                    if trimmed:
                                        drawing_name = trimmed
                                        print(f"  > OCR 成功提取: {drawing_name}")
                                        trace_logs.append(f"[页 {page_num + 1}] OCR命中: {drawing_name}")
                                    else:
                                        # 宽松兜底尝试
                                        loose = _extract_title_loose(blob_text)
                                        if loose:
                                            drawing_name = loose
                                            print(f"  > OCR 成功提取: {drawing_name}")
                                            trace_logs.append(f"[页 {page_num + 1}] OCR命中(宽松): {drawing_name}")
                                        else:
                                            drawing_name = None
                                            print(f"  > OCR 命中但判定无效")
                                            trace_logs.append(f"[页 {page_num + 1}] OCR命中但判定无效")
                                else:
                                    print(f"  > OCR 提取了内容但未匹配到图名特征")
                                    trace_logs.append(f"[页 {page_num + 1}] OCR有内容但未匹配到图名特征")
                            else:
                                print(f"  > OCR 未识别到有效文字")
                                trace_logs.append(f"[页 {page_num + 1}] OCR无有效文字")
                        else:
                            print(f"  > 页面 {page_num+1} 未找到图名且 OCR 不可用，跳过")

                    if drawing_name:
                        drawing_names.append(drawing_name)
                    else:
                        drawing_names.append(f"页面 {page_num + 1} - 未找到图纸名称")
                        trace_logs.append(f"[页 {page_num + 1}] 最终未找到图纸名称")

            # 不再使用整页识别，避免漏掉右下角图名

        except Exception as e:
            print(f"处理文件 {Path(pdf_path).name} 时出错：{str(e)}")
            return []
            
        self._trace_logs = None
        return drawing_names

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF图纸名称提取")
    parser.add_argument("--single-image", "-i", help="单图测试：传入图片路径")
    parser.add_argument("--single-pdf", help="单个PDF测试：传入PDF路径")
    parser.add_argument("--pdf-dir", help="批量处理输入PDF目录")
    parser.add_argument("--output-dir", help="批量处理输出目录")
    args = parser.parse_args()

    if args.single_image:
        run_single_image_external(args.single_image)
        sys.exit(0)

    if args.single_pdf:
        extractor = PdfDrawingExtractor()
        try:
            names = extractor.extract_drawing_names(args.single_pdf)
            print("PDF:", Path(args.single_pdf).name)
            for idx, name in enumerate(names, 1):
                print(f"Page {idx}: {name}")
        finally:
            try:
                extractor.root.destroy()
            except Exception:
                pass
        sys.exit(0)

    extractor = PdfDrawingExtractor()
    if args.pdf_dir and args.output_dir:
        extractor.pdf_dir = args.pdf_dir
        extractor.output_dir = args.output_dir
        extractor.process_pdfs()
    else:
        extractor.process_pdfs()