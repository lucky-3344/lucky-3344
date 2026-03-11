# 项目组织指南

## 当前文件统计
根据分析，您的项目包含以下类型的文件：

| 文件类型 | 数量 | 建议存放目录 |
|----------|------|--------------|
| .py      | 50   | scripts/     |
| .spec    | 13   | specs/       |
| .log     | 7    | logs/        |
| .txt     | 7    | docs/ 或 configs/ |
| .xlsx    | 5    | data/        |
| 无扩展名 | 4    | 根据内容分类 |
| .ofd     | 3    | outputs/     |
| .md      | 3    | docs/        |
| .ico     | 2    | images/      |
| .bat     | 2    | scripts/     |

## 建议的项目结构

```
my_project/
├── .vscode/                    # VS Code 配置
│   ├── settings.json          # 编辑器设置
│   ├── launch.json            # 调试配置
│   └── tasks.json             # 任务配置
├── scripts/                   # Python脚本和批处理文件
│   ├── data_processing/      # 数据处理脚本
│   ├── web_scraping/         # 网络爬虫脚本
│   ├── automation/           # 自动化脚本
│   └── utils/                # 工具函数
├── configs/                  # 配置文件
│   ├── json/                # JSON配置文件
│   ├── yaml/                # YAML配置文件
│   └── txt/                 # 文本配置文件
├── docs/                    # 文档文件
│   ├── guides/             # 使用指南
│   ├── api/                # API文档
│   └── reports/            # 报告文档
├── data/                    # 数据文件
│   ├── raw/                # 原始数据
│   ├── processed/          # 处理后的数据
│   └── outputs/            # 输出文件
├── images/                  # 图片资源
│   ├── icons/              # 图标文件
│   └── screenshots/        # 截图
├── specs/                  # 构建规范
│   ├── pyinstaller/        # PyInstaller规范
│   └── docker/             # Docker构建规范
├── tests/                  # 测试文件
│   ├── unit/              # 单元测试
│   ├── integration/       # 集成测试
│   └── fixtures/          # 测试数据
├── docker/                 # Docker相关文件
│   ├── Dockerfile
│   └── docker-compose.yml
├── logs/                   # 日志文件
│   ├── app/               # 应用日志
│   └── debug/             # 调试日志
└── README.md              # 项目说明
```

## 整理步骤

### 第一步：创建目录结构
```bash
# 创建主要目录
mkdir scripts configs docs data images specs tests docker logs

# 创建子目录
mkdir scripts/data_processing scripts/web_scraping scripts/automation scripts/utils
mkdir configs/json configs/yaml configs/txt
mkdir docs/guides docs/api docs/reports
mkdir data/raw data/processed data/outputs
mkdir images/icons images/screenshots
mkdir specs/pyinstaller specs/docker
mkdir tests/unit tests/integration tests/fixtures
mkdir logs/app logs/debug
```

### 第二步：移动文件到相应目录

#### Python脚本 (.py文件)
```bash
# 移动所有Python脚本到scripts目录
move *.py scripts/

# 特殊处理：保留根目录的关键脚本
move scripts/run_server.py .
move scripts/setup.py .
```

#### 构建规范 (.spec文件)
```bash
# 移动所有.spec文件到specs目录
move *.spec specs/
```

#### 数据文件 (.xlsx, .csv等)
```bash
# 移动Excel文件到data目录
move *.xlsx data/
move *.csv data/
```

#### 文档文件 (.md, .txt)
```bash
# 移动文档文件到docs目录
move *.md docs/
move AGENT_ROADMAP.md docs/
move claude_code_guide.md docs/
```

#### 配置文件 (.json, .yaml, .conf)
```bash
# 移动配置文件到configs目录
move *.json configs/
move *.yaml configs/
move *.conf configs/
move config.json configs/
move clean_config.yaml configs/
```

#### 输出文件 (.ofd, .pptx)
```bash
# 移动输出文件到data/outputs目录
move *.ofd data/outputs/
move *.pptx data/outputs/
```

#### 图片文件 (.png, .ico)
```bash
# 移动图片文件到images目录
move *.png images/
move *.ico images/
```

#### 日志文件 (.log)
```bash
# 移动日志文件到logs目录
move *.log logs/
```

### 第三步：更新文件引用

移动文件后，需要更新Python脚本中的文件路径引用：

1. **相对路径更新**：检查所有Python脚本中的文件路径，确保它们指向新的目录结构
2. **导入语句更新**：更新模块导入语句
3. **配置文件路径更新**：更新配置文件中的路径引用

### 第四步：创建.gitignore文件

创建或更新.gitignore文件，忽略不必要的文件：

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# VS Code
.vscode/
!.vscode/settings.json
!.vscode/tasks.json
!.vscode/launch.json
!.vscode/extensions.json

# 日志文件
*.log
logs/

# 数据文件
*.xlsx
*.csv
*.ofd

# 环境变量
.env
.env.local
.env.*.local

# 系统文件
.DS_Store
Thumbs.db
```

## VS Code侧边栏优化

我已经创建了`.vscode/settings.json`文件，包含以下优化：

### 1. 文件嵌套（File Nesting）
- 相关文件自动分组显示（如.py文件与其对应的.spec、_test.py文件）
- 减少资源管理器中的视觉杂乱

### 2. 文件排除（Files Exclude）
- 隐藏系统文件（.DS_Store, Thumbs.db）
- 隐藏缓存目录（__pycache__, .pytest_cache）
- 隐藏构建输出（dist/, build/）
- 隐藏虚拟环境（.venv/, venv/）

### 3. 搜索优化
- 排除node_modules、dist、build等目录
- 提高搜索速度和准确性

### 4. 侧边栏布局
- 保持活动栏和状态栏可见
- 优化编辑器标签页大小
- 启用面包屑导航

### 5. 编辑器增强
- 启用小地图（Minimap）
- 启用括号配对颜色
- 启用缩进参考线
- 自动保存和格式化

## 立即行动建议

1. **先备份重要文件**：在执行任何移动操作前，备份关键文件
2. **分批移动**：不要一次性移动所有文件，分批进行以便检查
3. **测试移动后的功能**：每次移动后，运行相关脚本确保功能正常
4. **使用版本控制**：使用Git跟踪文件移动，便于回滚

## 自动化整理脚本

您可以创建一个Python脚本来自动化整理过程：

```python
# organize_project.py
import os
import shutil
from pathlib import Path

def organize_files():
    # 定义文件类型到目录的映射
    file_mapping = {
        '.py': 'scripts',
        '.spec': 'specs',
        '.log': 'logs',
        '.txt': 'docs',
        '.xlsx': 'data',
        '.ofd': 'data/outputs',
        '.md': 'docs',
        '.ico': 'images',
        '.bat': 'scripts',
        '.json': 'configs',
        '.yaml': 'configs',
        '.conf': 'configs',
        '.png': 'images',
        '.pptx': 'data/outputs'
    }
    
    # 创建目录
    for directory in set(file_mapping.values()):
        os.makedirs(directory, exist_ok=True)
    
    # 移动文件
    for file in Path('.').iterdir():
        if file.is_file():
            ext = file.suffix.lower()
            if ext in file_mapping:
                target_dir = file_mapping[ext]
                shutil.move(str(file), f"{target_dir}/{file.name}")
                print(f"Moved {file.name} to {target_dir}/")

if __name__ == "__main__":
    organize_files()
```

## 注意事项

1. **路径引用**：移动文件后，需要更新所有代码中的文件路径引用
2. **相对路径**：尽量使用相对路径而不是绝对路径
3. **环境变量**：考虑使用环境变量或配置文件管理路径
4. **符号链接**：对于需要保持原位置的文件，可以考虑使用符号链接

通过以上组织，您的项目将更加清晰、易于维护，VS Code侧边栏和资源管理器也会更加流畅。
