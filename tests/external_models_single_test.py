import argparse
import base64
import json
import os
import urllib.request
import urllib.error
from io import BytesIO
from PIL import Image
import uuid

# DeepSeek 外部模型配置（从环境变量读取）
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-reasoner")
DEEPSEEK_OCR_URL = os.getenv("DEEPSEEK_OCR_URL", "")
DEEPSEEK_OCR_KEY = os.getenv("DEEPSEEK_OCR_KEY", "")
DEEPSEEK_OCR_MODEL = os.getenv("DEEPSEEK_OCR_MODEL", "")
DEEPSEEK_OCR_FILE_FIELD = os.getenv("DEEPSEEK_OCR_FILE_FIELD", "file")
DEEPSEEK_OCR_PROMPT = os.getenv(
    "DEEPSEEK_OCR_PROMPT",
    "<image>\n<|grounding|>Convert the document to markdown.",
)

# DotsOCR 网关配置
DOTS_OCR_URL = os.getenv("DOTS_OCR_URL", "")
DOTS_OCR_KEY = os.getenv("DOTS_OCR_KEY", "")
DOTS_OCR_FILE_FIELD = os.getenv("DOTS_OCR_FILE_FIELD", "file")
DOTS_OCR_MODEL = os.getenv("DOTS_OCR_MODEL", "")
DOTS_OCR_PROMPT = os.getenv(
    "DOTS_OCR_PROMPT",
    "<image>\n<|grounding|>Convert the document to markdown.",
)

def _normalize_base_url(raw: str) -> str:
    if not raw:
        return ""
    base = raw.strip()
    if "---" in base:
        base = base.split("---")[-1].strip()
    return base.rstrip("/")

def _normalize_model_name(raw: str) -> str:
    if not raw:
        return ""
    name = raw.strip()
    if "(" in name and ")" in name:
        inside = name.split("(")[-1].split(")")[0].strip()
        if inside:
            return inside
    return name

# 阿里外部模型配置（DashScope / OpenAI 兼容）
ALI_API_BASE = _normalize_base_url(os.getenv("ALI_API_BASE", "https://dashscope.aliyuncs.com/api/v1"))
ALI_API_KEY = os.getenv("ALI_API_KEY")
ALI_MODEL = _normalize_model_name(os.getenv("ALI_MODEL", "qwen-vl-plus"))
ALI_API_COMPAT = os.getenv("ALI_API_COMPAT", "auto")


def _deepseek_extract_title_from_image(image_bytes: bytes) -> str:
    if not DEEPSEEK_API_KEY:
        return ""

    url = f"{DEEPSEEK_API_BASE.rstrip('/')}/v1/chat/completions"
    img_b64 = base64.b64encode(image_bytes).decode("utf-8")
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是OCR后处理助手，只返回图纸名称本身，不要解释。无法识别则返回空字符串。",
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "请从图中找到图纸名称/图名（通常在右下角标题栏）。只输出图纸名称，不要多余文字。",
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{img_b64}"},
                    },
                ],
            },
        ],
        "temperature": 0,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = resp.read().decode("utf-8")
        obj = json.loads(resp_data)
        content = obj["choices"][0]["message"]["content"].strip()
        return content
    except Exception:
        return ""

def _encode_multipart_form(fields, files):
    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    boundary_bytes = boundary.encode("utf-8")
    body = b""

    for key, value in (fields or {}).items():
        body += b"--" + boundary_bytes + b"\r\n"
        body += f"Content-Disposition: form-data; name=\"{key}\"".encode("utf-8") + b"\r\n"
        body += b"\r\n"
        body += str(value).encode("utf-8") + b"\r\n"

    for key, filename, content_type, data in (files or []):
        body += b"--" + boundary_bytes + b"\r\n"
        body += (
            f"Content-Disposition: form-data; name=\"{key}\"; filename=\"{filename}\"".encode("utf-8")
            + b"\r\n"
        )
        body += f"Content-Type: {content_type}".encode("utf-8") + b"\r\n"
        body += b"\r\n"
        body += data + b"\r\n"

    body += b"--" + boundary_bytes + b"--\r\n"
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type

def _extract_text_from_ocr_response(obj):
    if not obj:
        return ""
    if isinstance(obj, dict) and isinstance(obj.get("contents"), list):
        status = None
        resp_data = ""
        resp_headers = None
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
                    resp_headers = dict(resp.headers)
                    resp_data = resp.read().decode("utf-8", errors="ignore")
            except urllib.error.HTTPError as e:
                status = e.code
                resp_headers = dict(e.headers)
                resp_data = e.read().decode("utf-8", errors="ignore")
            except Exception as e:
                if debug:
                    print(f"DeepSeek OCR request error: {e}")
                return ""

            location = None
            if resp_headers:
                location = resp_headers.get("Location") or resp_headers.get("location")
            if status in (301, 302, 307, 308) and location:
                url = location
                continue
            break
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

def _deepseek_ocr_extract_title(image_bytes: bytes, debug: bool = False) -> str:
    if not DEEPSEEK_OCR_URL:
        return ""

    token = DEEPSEEK_OCR_KEY or DEEPSEEK_API_KEY
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    # JSON 请求（prompt + file: base64）
    payload = {}
    if DEEPSEEK_OCR_PROMPT:
        payload["prompt"] = DEEPSEEK_OCR_PROMPT
    payload[DEEPSEEK_OCR_FILE_FIELD] = base64.b64encode(image_bytes).decode("utf-8")
    body = json.dumps(payload).encode("utf-8")
    headers["Content-Type"] = "application/json"

    url = DEEPSEEK_OCR_URL.rstrip("/")
    status = None
    resp_data = ""
    resp_headers = None
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
                resp_headers = dict(resp.headers)
                location = resp.getheader("Location")
                resp_data = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            status = e.code
            resp_headers = dict(e.headers)
            location = e.headers.get("Location")
            try:
                resp_data = e.read().decode("utf-8", errors="ignore")
            except Exception:
                resp_data = ""
        except Exception:
            return ""

        if status in (301, 302, 307, 308) and location:
            url = location
            continue
        break

    if debug:
        print(f"DeepSeek OCR URL: {url}")
        print(f"DeepSeek OCR Content-Type: {headers.get('Content-Type')}")
        print(f"DeepSeek OCR HTTP status: {status}")
        print(f"DeepSeek OCR response headers: {resp_headers}")
        if status in (301, 302, 307, 308):
            print(f"DeepSeek OCR redirect to: {url}")
        print("DeepSeek OCR raw response:")
        print(resp_data)

    try:
        obj = json.loads(resp_data)
        text = _extract_text_from_ocr_response(obj)
        return text
    except Exception:
        return resp_data.strip()


def _dots_ocr_extract_text(image_bytes: bytes, filename: str = "image.png", content_type: str = "image/png", debug: bool = False) -> str:
    url_env = os.getenv("DOTS_OCR_URL", DOTS_OCR_URL)
    key_env = os.getenv("DOTS_OCR_KEY", DOTS_OCR_KEY)
    prompt_env = os.getenv("DOTS_OCR_PROMPT", DOTS_OCR_PROMPT)
    model_env = os.getenv("DOTS_OCR_MODEL", DOTS_OCR_MODEL)
    if not url_env:
        return ""

    headers = {}
    if key_env:
        headers["Authorization"] = f"Bearer {key_env}"

    fields = {}
    if prompt_env:
        fields["prompt"] = prompt_env
    if model_env:
        fields["model"] = model_env
    files = [
        (DOTS_OCR_FILE_FIELD, filename, content_type, image_bytes)
    ]
    body, content_type = _encode_multipart_form(fields, files)
    headers["Content-Type"] = content_type

    url = url_env.rstrip("/")
    status = None
    resp_data = ""
    resp_headers = None
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
                resp_headers = dict(resp.headers)
                resp_data = resp.read().decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            status = e.code
            resp_headers = dict(e.headers)
            resp_data = e.read().decode("utf-8", errors="ignore")
        except Exception as e:
            if debug:
                print(f"DotsOCR request error: {e}")
            return ""

        location = None
        if resp_headers:
            location = resp_headers.get("Location") or resp_headers.get("location")
        if status in (301, 302, 307, 308) and location:
            url = location
            continue
        break

    if debug:
        print(f"DotsOCR URL: {url}")
        print(f"DotsOCR Content-Type: {headers.get('Content-Type')}")
        print(f"DotsOCR HTTP status: {status}")
        print(f"DotsOCR response headers: {resp_headers}")
        print("DotsOCR raw response:")
        print(resp_data)

    try:
        obj = json.loads(resp_data)
        text = _extract_text_from_ocr_response(obj)
        return text
    except Exception:
        return resp_data.strip()


def _ali_extract_title_from_image(image_bytes: bytes) -> str:
    if not ALI_API_KEY:
        return ""

    base = _normalize_base_url(ALI_API_BASE)
    use_openai = (
        ALI_API_COMPAT.lower() == "openai"
        or (ALI_API_COMPAT.lower() == "auto" and (base.endswith("/v1") or "/v1" in base))
    )

    img_b64 = base64.b64encode(image_bytes).decode("utf-8")

    if use_openai:
        url = f"{base}/chat/completions"
        payload = {
            "model": ALI_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": "你是OCR后处理助手，只返回图纸名称本身，不要解释。无法识别则返回空字符串。",
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "请从图中找到图纸名称/图名（通常在右下角标题栏）。只输出图纸名称，不要多余文字。",
                        },
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_b64}"}},
                    ],
                },
            ],
            "temperature": 0,
        }
    else:
        url = f"{base}/services/aigc/multimodal-generation/generation"
        payload = {
            "model": ALI_MODEL,
            "input": {
                "prompt": [
                    {
                        "role": "system",
                        "content": [
                            {"text": "你是OCR后处理助手，只返回图纸名称本身，不要解释。无法识别则返回空字符串。"}
                        ],
                    },
                    {
                        "role": "user",
                        "content": [
                            {"text": "请从图中找到图纸名称/图名（通常在右下角标题栏）。只输出图纸名称，不要多余文字。"},
                            {"image": f"data:image/png;base64,{img_b64}"},
                        ],
                    },
                ]
            },
            "parameters": {"temperature": 0},
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {ALI_API_KEY}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = resp.read().decode("utf-8")
        obj = json.loads(resp_data)
        if use_openai:
            content = obj.get("choices", [{}])[0].get("message", {}).get("content", "")
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
                return "".join(text_parts).strip()
            return str(content).strip()
        output = obj.get("output", {})
        choices = output.get("choices") or []
        if not choices:
            return ""
        content = choices[0].get("message", {}).get("content") or []
        text_parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        return "".join(text_parts).strip()
    except Exception:
        return ""


def run_single_test(image_path: str, debug: bool = False):
    print("----------- 外部模型单图测试 -----------")
    print(f"图片: {image_path}")

    try:
        img = Image.open(image_path)
        print(f"大小: {img.size}")
    except Exception as e:
        print(f"打开失败: {e}")
        return

    buf = BytesIO()
    img.save(buf, format="PNG")
    img_bytes = buf.getvalue()

    if DEEPSEEK_OCR_URL:
        title = _deepseek_ocr_extract_title(img_bytes, debug=debug)
        print("DeepSeek OCR title:", title)
    elif DEEPSEEK_API_KEY:
        title = _deepseek_extract_title_from_image(img_bytes)
        print("DeepSeek title:", title)
    else:
        print("DeepSeek 未配置 API Key（环境变量 DEEPSEEK_API_KEY）")

    if ALI_API_KEY:
        title = _ali_extract_title_from_image(img_bytes)
        print("Ali title:", title)
    else:
        print("Ali 未配置 API Key（环境变量 ALI_API_KEY）")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="外部模型单图测试（DeepSeek + 阿里）")
    parser.add_argument("--image", "-i", required=True, help="图片路径")
    parser.add_argument("--debug", action="store_true", help="打印 OCR 原始响应")
    args = parser.parse_args()

    run_single_test(args.image, debug=args.debug)
