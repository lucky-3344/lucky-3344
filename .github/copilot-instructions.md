<!-- Copilot / AI agent 指南（基于仓库现状提炼） -->
# my_project — Copilot 编码指引

## 大局观（入口与数据流）
- 通信 PDF 参数分析（CLI）：
  - 标准入口：[telecom_analyzer.py](telecom_analyzer.py)（基于规则/正则/表格提取），稳定可靠，对应 [models.py](models.py)。
  - 实验入口：[telecom_pdf_analyzer.py](telecom_pdf_analyzer.py)（尝试引入 BERT NLP 模型），依赖 transformers，有回退机制。
  - 核心流：`PDFExtractor` (OCR/Text) -> `clean_extracted_data` -> `TelecomAnalyzer`/`BERTExtractor` -> `ExcelReporter`。
- OFD 转换（GUI/CLI/POC）：目录 [ofd_poc/](ofd_poc/README.md)。GUI 用 [ofd_poc/pdf_to_ofd_gui.py](ofd_poc/pdf_to_ofd_gui.py)；CLI 用 [ofd_poc/run_pdf_to_ofd.py](ofd_poc/run_pdf_to_ofd.py)；厂商 CLI 包装用 [ofd_poc/foxit_poc.py](ofd_poc/foxit_poc.py) 等。
- Windows 清理工具：入口 [clean_c_drive.py](clean_c_drive.py)，配置 [clean_config.yaml](clean_config.yaml)，支持 PyInstaller 单文件打包。
- 爬虫子项目：目录 [telecom_spider/](telecom_spider/README.md)（Scrapy）。
- 辅助工具集：
  - [visio_to_pdf.py](visio_to_pdf.py)：调用本地 Visio 组件批量转 PDF。
  - [docx_image_change.py](docx_image_change.py)：文图片加噪/裁剪/替换（PIL + numpy）。

## 常用工作流（可直接运行）
- 安装依赖：`pip install -r requirements.txt`
- 运行通信 PDF 分析：
  - 规则版：`python telecom_analyzer.py -i <输入> -o <输出> --ocr --extract-images`
  - BERT版：`python telecom_pdf_analyzer.py -i <输入> ...`
- 运行 OFD GUI：`python ofd_poc/pdf_to_ofd_gui.py`（依赖 Java）。
  - **关键配置**：Jar 包路径硬编码在 [ofd_poc/ofdrw_poc/target/ofdrw-poc-1.0-jar-with-dependencies.jar](ofd_poc/ofdrw_poc/target/ofdrw-poc-1.0-jar-with-dependencies.jar)。修改 GUI 代码前需确认 Jar 位置。
- 运行爬虫：`cd telecom_spider` -> `scrapy crawl huawei_products`。
- 打包清理工具：使用 VS Code Task `Build clean_c_drive.exe (PyInstaller)`。

## 本仓库关键约定（改代码时务必遵守）
- PyInstaller 资源定位：使用 `getattr(sys, "_MEIPASS", ...)`/`sys.frozen` 模式（见 [clean_c_drive.py](clean_c_drive.py)、[ofd_poc/run_pdf_to_ofd.py](ofd_poc/run_pdf_to_ofd.py)、[ofd_poc/pdf_to_ofd_gui.py](ofd_poc/pdf_to_ofd_gui.py)），不要改成“相对路径读取资源”。
- OFD GUI 进程内桥接：GUI 通过 `runpy.run_path()` 调用 `ofd_poc/ofd_image_poc/extract_images.py` 的 `render_pdf_to_images`，避免递归启动打包 exe；中间图片必须写到工作目录下的 `ofd_tmp_images/`（不要写入 `_MEIPASS`）。
- 外部命令实时输出：GUI 用 `subprocess.Popen(..., stdout=PIPE, stderr=STDOUT, text=True, encoding='utf-8', errors='ignore')` 实时刷日志；POC 包装脚本把命令与返回码写入 `ofd_poc/convert.log`。

## 外部依赖与可选能力（按代码实际分支）
- OCR：`pdf_extractor.py` 优先 PaddleOCR（存在则初始化），否则退回 `pytesseract`；当使用 Tesseract 时需要本机安装 `tesseract-ocr` 与中文语言包。
- 表格提取：可选 `camelot`/`tabula`/`pdfplumber`（代码里用 `*_AVAILABLE` 进行能力探测）。
- Windows 专用：清理工具依赖 `winshell`（可选，失败则走 `ctypes.shell32` 回退）、`win32com`、`psutil`。

## 正式文档交付约定（标书、可研、报告、方案等）
- 当用户请求"标书""可研""可行性研究""项目建议书""研究报告""项目方案""方案""技术应答""Word 版""送审版""仿宋排版""院标格式""增加配图""表格检查""图片出框""统一版式"等任务时，优先使用 `.github/skills/tender-doc-delivery/SKILL.md` 中定义的标准和检查流程。
- 对这类任务，完成标准不是“脚本成功运行”或“docx 能打开”，而是：正文、目录、页眉页脚、图题表题、表格重复标题行、配图嵌入、图片实际观感检查全部完成。
- 对生成的图片，不得只依赖日志判断，必须查看实际 png 或最终 Word 效果，确认文字在框内居中且没有出框、贴边、压边。
- 输出 Word 时，优先使用递增版本文件名，避免覆盖用户正在打开的文件。
## 公司 PPT 生成约定（汇报、提案、投标演示）
- 当用户请求"生成PPT""生成演示文稿""生成汇报""工作汇报PPT""项目汇报PPT""技术方案PPT""投标PPT""年度报告PPT""GPDI风格"等任务时，优先读取并遵循 `.github/skills/company-pptx/SKILL.md`。
- 视觉底座：`C:\Users\lucky\Desktop\附件1：2026年GPDI工作报告PPT模板.pptx`（红色系 #CC0000，微软雅黑，28.22×15.88cm）。
- 禁止使用旧样例（岭南蓝色系 #1E2761）的配色方案，除非用户明确要求。
- 输出前必须运行 skill 中的代码检查清单，并完成人工目检 7 项。
- 输出文件命名：`{项目名}_{文档类型}_{日期}_v{版本}.pptx`。