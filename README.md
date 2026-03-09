# 项目工具集合

## 📦 工具列表

### 1. 云盘批量下载工具 `云盘批量下载.py` ⭐ 主工具

自动从移动云盘下载指定文件列表的批量下载工具。

**功能**:
- ✅ 支持VSD、VSDX、CAD、DXF、PDF、Word等多种格式
- ✅ 支持文件夹下载
- ✅ 智能图标识别 + 颜色二次验证
- ✅ 搜索框位置自动保存
- ✅ 批量处理多个文件

**快速开始**:
```bash
python 云盘批量下载.py
```

**详细文档**: 见下方"云盘批量下载工具"章节

### 2. 通信PDF参数提取分析工具

从通信领域PDF文档中提取和分析参数。

---

# 云盘批量下载工具

## 功能介绍
自动从移动云盘下载指定文件列表，支持VSD、VSDX、CAD、PDF、Word等多种格式，以及文件夹下载。

## 安装指南

### 1. 环境要求
- **Python**: 3.8+
- **操作系统**: Windows
- **移动云盘**: 需要已安装并登录

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

**关键依赖**:
- pywinauto: UI自动化
- pandas: Excel处理
- pyautogui: 屏幕控制
- pyperclip: 剪贴板操作

### 3. 安装资源文件
确保以下图标文件存在于 `cloud_downloader/resources/images/` 目录：
- `vsd_icon.png` - VSD文件图标
- `cad_icon.png` - CAD文件图标
- `pdf_icon.png` - PDF文件图标
- `word_icon.png` - Word文件图标
- `folder_icon.png` - 文件夹图标

## 使用步骤

### 第一次使用

1. **编辑配置文件**
```bash
# 复制模板
copy config_template.json config.json

# 编辑 config.json，修改以下项目：
# - download_dir: 下载目录
# - excel_path: 含有文件名的Excel文件
# - cloud_client_path: 移动云盘安装路径
```

2. **准备Excel文件**
在 `config.json` 中指定的 Excel 文件的**第一列**写入要下载的文件名，例如：
```
广州黄埔区奥园香雪公馆6栋
广州黄埔区WJ会议中心
广州黄埔区华港大酒店
```

3. **启动云盘客户端**
确保移动云盘已启动并登录

4. **运行程序**
```bash
python 云盘批量下载.py
```

### 交互式菜单

程序启动后会显示菜单：
```
请选择要下载的文件类型:
1. VSD文件 (.vsd)
2. VSDX文件 (.vsdx)
3. CAD文件 (.dwg)
4. DXF文件 (.dxf)
5. PDF文件 (.pdf)
6. 文件夹
8. Word文件 (.doc/.docx) - 勘察报告
```

**举例**：
- 选择 `1` → 只下载VSD文件
- 选择 `1,3` → 先下载VSD，没有则下载CAD
- 选择 `8` → 只下载Word文件（勘察报告）
- 选择 `6` → 只下载文件夹

### 鼠标位置定位

**首次运行时**会提示：
```
★★★ 请将鼠标移动到搜索输入框内，然后按回车继续 ★★★
准备好后按回车...
```

此时请：
1. 在云盘客户端窗口找到搜索框
2. 把鼠标光标移动到搜索框内
3. 按回车键
4. 程序会记住位置，后续无需重复此操作

**重新定位**：若要更改搜索框位置，首次提示时输入 `n`

## 输出文件

程序完成后会生成：
- `已下载的文件.xlsx` - 成功下载的文件列表
- `未下载的文件.xlsx` - 未找到或失败的文件列表
- `cloud_downloader/debug/` - 详细的调试日志和截图

## 最新修复（2026-03-09）

本次已确认稳定的版本包含以下改动：
- 支持在首个选项提示直接输入 `1,2,5` 这样的优先级组合。
- 连接客户端失败时，自动尝试启动移动云盘客户端并重连。
- 增加弹窗清理逻辑，降低 PDF 打开方式提示对自动化流程的干扰。
- 下载动作优化为优先右键下载，减少误触发预览/打开。
- 批次内去重，跳过 Excel 重复项。
- 下载目录已存在同名文件时自动跳过，避免重复下载。
- 新增 `跳过的文件.xlsx`，记录被跳过项目和原因。

推荐执行命令：
```bash
C:/Users/lucky/AppData/Local/Programs/Python/Python311/python.exe "c:/Users/lucky/projects/my_project/云盘批量下载.py"
```

## 常见问题

### Q: 程序找不到搜索框
**A**: 
1. 确保移动云盘窗口在前台且可见
2. 重新运行程序，选择 `n` 重新定位
3. 手动把鼠标移到搜索框内

### Q: 总是下载错误的文件
**A**: 
1. 检查Excel文件中的文件名是否准确
2. 确保文件名包含足够的识别特征（避免过于通用的名称）
3. 查看 `cloud_downloader/debug/` 中的截图，检查识别结果

### Q: 程序找不到图标文件
**A**:
1. 确保所有`.png`文件在 `cloud_downloader/resources/images/` 目录中
2. 文件名必须完全匹配（区分大小写）
3. 程序会自动回退到颜色识别，可继续使用

### Q: 下载目录权限不足
**A**:
1. 确保下载目录存在且可写
2. 运行程序时使用管理员权限
3. 检查配置中的路径是否正确

### Q: 程序运行缓慢
**A**:
1. 这是正常的（需要UI交互和等待搜索结果）
2. 每个文件平均耗时 30-60 秒
3. 检查网络连接和云盘客户端状态

## 故障排查

### 检查运行环境
```bash
# 检查Python版本
python --version

# 检查依赖安装
pip list | findstr pywinauto

# 检查配置文件
python -c "import json; json.load(open('config.json'))"
```

### 查看详细日志
最新的日志文件位于：
```
c:\Users\lucky\projects\my_project\cloud_downloader\debug\download_log_*.txt
```

## 高级配置

### 修改下载目录
编辑 `config.json`：
```json
{
  "download_dir": "D:\\CloudDownloads"
}
```

### 指定云盘内的子目录
编辑 `config.json`：
```json
{
  "cloud_folder_path": ["工作文件", "2024项目", "图纸"]
}
```

---

## 通信PDF参数提取分析工具

这是一个专门用于从通信领域PDF文档中提取和分析参数的工具，支持批量处理多个PDF文件，自动识别常见的通信参数，并生成结构化Excel报告。

## 功能特点

- 支持多种PDF文档类型，包括文本PDF和扫描PDF（OCR支持）
- 自动提取通信领域常见参数（频率、增益、功率、天线参数等）
- 使用轻量级机器学习模型对文档内容进行分类和实体识别
- 支持批量处理多个PDF文件，提供多进程加速
- 生成结构化Excel报告，便于后续分析
- 支持参数统计和汇总，自动分类整理

## 安装指南

### 环境要求

- Python 3.7+
- 依赖库：详见requirements.txt

### 安装步骤

1. 克隆或下载本项目

2. 安装依赖库

```bash
pip install -r requirements.txt
```


3. OCR支持需要安装Tesseract

- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- Linux: `sudo apt install tesseract-ocr tesseract-ocr-chi-sim`
- macOS: `brew install tesseract tesseract-lang`

## 使用方法

### 命令行参数

```
usage: telecom_analyzer.py [-h] [-d PDF_DIR] [-o OUTPUT_DIR] [-s SINGLE] 
                          [--ocr] [--extract_images] [-w WORKERS] [-v]

通信PDF参数提取分析工具

optional arguments:
  -h, --help            显示帮助信息
  -d PDF_DIR, --pdf_dir PDF_DIR
                        PDF文件目录路径 (默认: ./pdf)
  -o OUTPUT_DIR, --output_dir OUTPUT_DIR
                        输出目录路径 (默认: ./output)
  -s SINGLE, --single SINGLE
                        单个PDF文件路径
  --ocr                 对扫描PDF使用OCR
  --extract_images      提取图像
  -w WORKERS, --workers WORKERS
                        并行处理的最大进程数
  -v, --verbose         显示详细日志
```

### 示例用法

1. 处理单个PDF文件

```bash
python telecom_analyzer.py -s path/to/document.pdf -o output_dir
```

2. 批量处理目录中的所有PDF文件

```bash
python telecom_analyzer.py -d path/to/pdf_folder -o output_dir
```

3. 使用OCR处理扫描PDF

```bash
python telecom_analyzer.py -d path/to/pdf_folder -o output_dir --ocr
```

4. 提取图像并使用4个并行进程

```bash
python telecom_analyzer.py -d path/to/pdf_folder -o output_dir --extract_images -w 4
```

## 输出结果

程序会在指定的输出目录中生成以下内容：

1. `/excel` 目录：包含每个PDF的参数Excel报告
2. `/logs` 目录：包含处理日志和结果统计
3. `/models` 目录：保存训练好的模型（如适用）
4. `/images` 目录：如果启用了图像提取，则保存提取的图像
5. 汇总报告：包含所有处理结果的汇总Excel文件

## 项目结构

- `telecom_analyzer.py` - 主程序
- `pdf_extractor.py` - PDF内容提取模块
- `models.py` - 文本分类和实体识别模型
- `excel_reporter.py` - Excel报告生成模块
- `utils.py` - 通用工具函数

## 注意事项

- 对于扫描PDF，需要启用OCR功能并安装Tesseract
- 处理大量PDF文件时，建议指定合理的并行进程数
- 参数识别准确性依赖于PDF文档的质量和格式

## 常见问题

1. OCR识别质量不佳？
   - 确保安装了正确的Tesseract及语言包
   - 提高PDF扫描质量或尝试使用预处理增强图像

2. 参数提取不完整？
   - 检查PDF文档格式是否规范
   - 可以通过修改`models.py`中的模式来适配特定文档类型

3. 处理速度慢？
   - 尝试增加并行进程数
   - 禁用不必要的功能，如图像提取

## 许可证

本项目采用MIT许可证
