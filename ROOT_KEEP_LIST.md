# 根目录保留清单（当前建议）

以下文件建议保留在根目录，作为主入口或核心依赖：

## 主入口
- `process_user_file.py`
- `run_process_quickstart.bat`
- `run_process_cli.bat`
- `clean_c_drive.py`
- `telecom_analyzer.py`
- `telecom_pdf_analyzer.py`

## 核心依赖
- `coord_transform.py`
- `pdf_extractor.py`
- `excel_reporter.py`
- `models.py`
- `telecom_config.py`
- `utils.py`

## 项目说明
- `README.md`
- `README_process_user_file.md`
- `WORKSPACE_ORGANIZATION.md`

## 说明
- 过程版本、实验脚本、抓取/检索脚本已移动到 `tools/`。
- 测试脚本已移动到 `tests/`。
- 文档（除关键入口README）已移动到 `docs/`。
