# 工作区整理说明

## 本次已完成

1. 将过程版本与运行产物移出根目录，统一归档到：
`_archive/process_tool/`

2. 归档目录结构：
- `legacy/`：过程版本脚本（如 `process_user_file_fixed.py`）
- `logs/`：运行日志与临时结果（`batch_processing_log_*.txt`、`batch_results_*.kml`）
- `samples/`：临时样例文件（如 `_tmp_only_name.csv`）

3. 已在 `.gitignore` 增加以下规则，避免后续再次堆积：
- `batch_processing_log_*.txt`
- `batch_results_*.kml`
- `batch_results_*.xlsx`
- `batch_results_*.csv`

4. 第二轮已完成：
- 将测试脚本统一移动到 `tests/`（`test_*.py` 与 `*_test.py`）
- 将核心说明以外的文档移动到 `docs/`
- 保留根目录入口文档：`README.md`、`README_process_user_file.md`
- 取消 `docs/`、`tests/` 的忽略，确保可纳入版本控制

5. 第三轮已完成：
- 将明显实验/过程脚本移动到 `tools/` 下分组目录：
	- `tools/maps_legacy/`
	- `tools/news_search/`
	- `tools/experimental/`
	- `tools/misc_cn/`
- 新增根目录保留清单：`ROOT_KEEP_LIST.md`

## 建议的文件分类（后续可继续）

1. 主入口脚本（保留在根目录）
- `process_user_file.py`
- `run_process_quickstart.bat`
- `run_process_cli.bat`
- `README_process_user_file.md`

2. 文档（建议集中到 `docs/`）
- 各类 `README_*.md`
- `*_GUIDE.md`
- `*_SUMMARY.md`

3. 工具脚本（建议集中到 `tools/`）
- 非主入口、一次性或辅助脚本

4. 测试脚本（建议集中到 `tests/`）
- `test_*.py`
- `*_test.py`

5. 历史实验版本（建议集中到 `_archive/`）
- `*_fixed.py`
- `*_final.py`
- `*_complete.py`
- 以及名字带“副本/临时/old/backup”的文件

## 清理原则

1. 根目录只保留“常用入口 + 关键文档”。
2. 过程版本不直接删除，先移动到 `_archive/`，稳定后再清理。
3. 所有运行期产物统一忽略，避免误提交。
