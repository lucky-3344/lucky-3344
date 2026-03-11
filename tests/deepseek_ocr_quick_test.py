import os
from io import BytesIO
from pathlib import Path

import fitz
from PIL import Image

from external_models_single_test import _dots_ocr_extract_text

PDF_PATH = r"E:\01 工作文件夹\001 广州无线项目组\00 日常工作记录\2026\20260103\广州天河区南铁华庭东-（物理站名：南铁华庭东，上联机房：农业干部学院宿舍微网格业务汇聚机房1）20251220\中兴【广州天河区南铁华庭东（CRAN改造）】【20251220设计图纸】【2026年极简网络改造项目】【室外】【共址】【天河区】.pdf"
OCR_URL = os.getenv("DOTS_OCR_URL", "http://172.16.159.9:47029/api/gateway_files")


def _mask_key(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 12:
        return "*" * len(key)
    return key[:6] + "..." + key[-6:]


def main() -> None:
    ocr_key = os.getenv("DOTS_OCR_KEY", "")
    prompt = os.getenv(
        "DOTS_OCR_PROMPT",
        "Return exact OCR text from the file. Do not fabricate tables or sample data. If uncertain, return empty.",
    )

    os.environ["USE_DOTS_OCR"] = "1"
    os.environ["DOTS_OCR_URL"] = OCR_URL
    if ocr_key:
        os.environ["DOTS_OCR_KEY"] = ocr_key
    os.environ["DOTS_OCR_PROMPT"] = prompt
    os.environ["DOTS_OCR_FILE_FIELD"] = "file"

    pdf = Path(PDF_PATH)
    print("PDF exists:", pdf.exists())
    print("OCR URL:", OCR_URL)
    print("OCR key:", _mask_key(ocr_key))
    print("OCR prompt:", prompt)

    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    with pdf.open("rb") as f:
        pdf_bytes = f.read()

    pdf_text = _dots_ocr_extract_text(
        pdf_bytes,
        filename=pdf.name,
        content_type="application/pdf",
        debug=True,
    )
    print("\n[PDF upload] len:", len(pdf_text or ""))
    print((pdf_text or "")[:800])

    with fitz.open(str(pdf)) as doc:
        page = doc[0]
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        img = Image.open(BytesIO(pix.tobytes("png"))).convert("RGB")
        buf = BytesIO()
        img.save(buf, format="PNG")
        page1_bytes = buf.getvalue()

    img_text = _dots_ocr_extract_text(
        page1_bytes,
        filename="page1.png",
        content_type="image/png",
        debug=True,
    )
    print("\n[Page image] len:", len(img_text or ""))
    print((img_text or "")[:800])


if __name__ == "__main__":
    main()
