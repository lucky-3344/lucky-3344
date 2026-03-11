# PDF图纸名称提取工具 - 修复说明

## 修复内容

### 1. 类型检查错误修复 ✅

**问题：** 在 `_extract_text_from_ocr_response` 函数中，对 `obj.get()` 返回的 None 值进行迭代导致类型检查错误。

**修复：**

- 在迭代前添加显式的类型检查
- 分步验证 `contents` 和 `results` 是否为 list 类型
- 避免对 None 值进行迭代操作

**修复位置：** 第 113-148 行

```python
# 修复前（会报错）:
if isinstance(obj, dict) and isinstance(obj.get("contents"), list):
    for item in obj.get("contents"):  # 这里可能迭代 None
        ...

# 修复后:
if isinstance(obj, dict):
    contents = obj.get("contents")
    if isinstance(contents, list):
        for item in contents:  # 安全的迭代
            ...
```

### 2. PyMuPDF 类型注解问题修复 ✅

**问题：** VSCode 的 Pylance 类型检查器误报 `fitz.open` 不是已知属性。

**修复：**

- 在两处 `fitz.open()` 调用后添加 `# type: ignore` 注释
- 这是 PyMuPDF 库的类型注解问题，不影响实际运行

**修复位置：** 第 903、1132 行

```python
doc = fitz.open(pdf_path)  # type: ignore
```

## 测试结果

所有测试通过 ✅：

- ✓ 模块导入测试
- ✓ OCR响应解析测试（5个用例）
- ✓ 图名提取逻辑测试

## 使用方法

### 基本用法

```bash
# 单张图片测试
python pdf图纸名称提取.py --single-image "path/to/image.png"

# 单个PDF测试
python pdf图纸名称提取.py --single-pdf "path/to/file.pdf"

# 批量处理PDF目录
python pdf图纸名称提取.py --pdf-dir "input_dir" --output-dir "output_dir"

# GUI模式（不带参数）
python pdf图纸名称提取.py
```

### 依赖安装

```bash
pip install pdfplumber PyMuPDF opencv-python pillow pandas numpy
```

可选依赖（用于OCR）:

```bash
# PaddleOCR（推荐）
pip install paddleocr paddlepaddle

# 或使用 Tesseract
pip install pytesseract
```

## 功能特性

1. **多OCR引擎支持**
   - PaddleOCR（优先，精度高）
   - Tesseract（回退方案）
   - DeepSeek OCR 网关（可选）
   - DotsOCR 网关（可选）

2. **智能图名提取**
   - 标签行优先识别（"图纸名称："）
   - 关键词匹配（GPS馈线路由图、设备布置平面图等）
   - 多区域裁剪识别（右下角标题栏）
   - 页面旋转识别（适配横向图纸）

3. **批量处理**
   - 支持目录批量处理
   - 自动生成Excel报告
   - 调试模式保存裁剪图片

## 环境变量配置

可选的环境变量：

```bash
# OCR开关
USE_OCR=1                    # 启用OCR（默认开启）
FAST_OCR=0                   # 快速OCR模式（减少裁剪区域）

# DeepSeek OCR网关
DEEPSEEK_OCR_URL=http://...
DEEPSEEK_OCR_KEY=your_key

# DotsOCR网关
DOTS_OCR_URL=http://...
DOTS_OCR_KEY=your_key
USE_DOTS_OCR=1
DOTS_OCR_DEBUG=0
DOTS_OCR_MAX_TRIES=8

# 调试选项
DEBUG_FIRST_PDF=0            # 只处理第一个PDF
```

## 输出文件

- **Excel报告**: `{output_dir}/pdf_drawing_names_*.xlsx`
  - 列：PDF文件名、页码、图纸名称
  
- **调试图片**（如果启用）: `{output_dir}/ocr_debug/`
  - 每个裁剪区域的原图和二值化图

## 常见问题

### Q1: 提示 "未找到有效的OCR引擎"

**解决：** 安装至少一个OCR引擎

```bash
pip install paddleocr paddlepaddle
```

### Q2: 识别不到图纸名称

**解决：**

1. 检查PDF是否为扫描件（需要OCR）
2. 启用调试模式查看裁剪区域：设置环境变量 `DOTS_OCR_DEBUG=1`
3. 尝试调整裁剪区域参数（第906-944行）

### Q3: 处理速度慢

**解决：**

1. 启用快速模式：`FAST_OCR=1`
2. 使用外部OCR网关（DotsOCR/DeepSeek）
3. 减少裁剪区域数量

### Q4: 类型检查警告

**解决：** 已修复，如果仍有警告请更新代码

## 技术细节

### OCR引擎优先级

1. DotsOCR 网关（如果配置）
2. DeepSeek OCR 网关（如果配置）
3. PaddleOCR（本地）
4. Tesseract（本地回退）

### 图名提取策略

1. **标签行匹配**：匹配"图纸名称："等标签
2. **关键词正则**：提取包含"平面图/路由图"等关键词的片段
3. **锚点定位**：以"工程名称"为锚点向后搜索
4. **多区域OCR**：对右下角标题栏进行多区域裁剪识别

### 性能优化

- 多裁剪区域并行识别
- 二值化预处理提高OCR精度
- 页面旋转识别（90度逆时针）
- 智能降采样（避免图片过大）

## 贡献者

如有问题或建议，欢迎提交Issue。

## 更新日志

### 2026-01-22

- ✅ 修复类型检查错误（`obj.get()` 返回 None 迭代问题）
- ✅ 修复 PyMuPDF 类型注解警告
- ✅ 添加完整的单元测试
- ✅ 改进错误处理和日志输出
