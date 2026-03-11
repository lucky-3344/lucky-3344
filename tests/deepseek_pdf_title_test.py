import os
from io import BytesIO
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image

import re

from external_models_single_test import (
    _deepseek_ocr_extract_title,
    _deepseek_extract_title_from_image,
    _dots_ocr_extract_text,
)


def _pick_drawing_name(text: str) -> str:
    if not text:
        return ""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    # 优先包含“图纸名称/图名”的行
    for line in lines:
        m = re.search(r"(图纸名称|图纸名|图名)[:：]?(.*)", line)
        if m and m.group(2).strip():
            return m.group(2).strip()
    # 其次包含图名特征关键词
    keywords = ["平面图", "立面图", "剖面图", "系统图", "原理图", "示意图", "布置", "安装", "路由", "布线"]
    for line in lines:
        if any(k in line for k in keywords):
            return line
    # 兜底：返回最长一行
    return max(lines, key=len) if lines else ""


def _call_deepseek_ocr(image_bytes: bytes, debug: bool = False) -> str:
    use_dots = os.getenv("USE_DOTS_OCR", "1").strip().lower() in ("1", "true", "yes", "y")
    if use_dots and os.getenv("DOTS_OCR_URL"):
        return _dots_ocr_extract_text(image_bytes, debug=debug)
    if os.getenv("DEEPSEEK_OCR_URL"):
        return _deepseek_ocr_extract_title(image_bytes, debug=debug)
    return _deepseek_extract_title_from_image(image_bytes)


def extract_drawing_name_from_pdf(pdf_path: str, debug: bool = True) -> str:
    doc = fitz.open(pdf_path)
    try:
        page = doc[0]
        rect = page.rect
        clip_rects = [
            fitz.Rect(rect.width * 0.45, rect.height * 0.70, rect.width, rect.height),
            fitz.Rect(rect.width * 0.35, rect.height * 0.65, rect.width, rect.height),
            fitz.Rect(0, rect.height * 0.72, rect.width, rect.height),
            fitz.Rect(rect.width * 0.55, rect.height * 0.60, rect.width, rect.height),
        ]

        debug_dir = Path(os.getcwd()) / "deepseek_ocr_debug"
        if debug:
            debug_dir.mkdir(parents=True, exist_ok=True)

        for idx, clip_rect in enumerate(clip_rects, 1):
            pix = page.get_pixmap(matrix=fitz.Matrix(3, 3), clip=clip_rect)
            img = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
            buf = BytesIO()
            img.save(buf, format="PNG")
            image_bytes = buf.getvalue()

            if debug:
                img_path = debug_dir / f"clip_{idx}.png"
                img.save(img_path)

            raw_text = _call_deepseek_ocr(image_bytes, debug=debug)
            if debug:
                print(f"--- Clip {idx} raw OCR ---")
                print(raw_text)

            name = _pick_drawing_name(raw_text)
            if name:
                return name

        # 兜底：整页截图
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        if debug:
            img.save(debug_dir / "full_page.png")
        raw_text = _call_deepseek_ocr(buf.getvalue(), debug=debug)
        if debug:
            print("--- Full page raw OCR ---")
            print(raw_text)
        return _pick_drawing_name(raw_text)
    finally:
        doc.close()


def main():
    pdf_path = r"E:\01 工作文件夹\001 广州无线项目组\00 日常工作记录\2026\20260113\新建文件夹\001CBN-大婆份微网格业务汇聚机房3（广州南沙区西樵樵兴南街）U-Z5H.pdf"
    print("DotsOCR URL:", os.getenv("DOTS_OCR_URL"))
    print("DotsOCR Key configured:", bool(os.getenv("DOTS_OCR_KEY")))
    print("DeepSeek OCR URL:", os.getenv("DEEPSEEK_OCR_URL"))
    use_dots = os.getenv("USE_DOTS_OCR", "1").strip().lower() in ("1", "true", "yes", "y")
    if use_dots and os.getenv("DOTS_OCR_URL"):
        # 仅在 DotsOCR 模式下测试 PDF 原文件上传
        try:
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            pdf_raw_text = _dots_ocr_extract_text(
                pdf_bytes,
                filename=Path(pdf_path).name,
                content_type="application/pdf",
                debug=True,
            )
            print("--- PDF raw OCR ---")
            print(pdf_raw_text)
        except Exception as e:
            print(f"PDF原文件上传测试失败: {e}")

    title = extract_drawing_name_from_pdf(pdf_path)
    print(f"PDF: {Path(pdf_path).name}")
    print(f"Drawing name: {title}")


if __name__ == "__main__":
    main()
