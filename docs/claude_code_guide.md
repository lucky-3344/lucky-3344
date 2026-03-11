# Claude Code (Cline) 使用指南

## 已安装的扩展
- **扩展名称**: Cline (原名 Claude Dev)
- **扩展ID**: `saoudrizwan.claude-dev`
- **版本**: 3.51.0
- **状态**: 已安装并启用

## 如何启动和使用

### 1. 打开Cline侧边栏
1. 在VS Code中，点击左侧活动栏的Cline图标（看起来像一个人形图标）
2. 或者使用快捷键 `Ctrl+'`（Windows）打开Cline聊天界面

### 2. 基本功能
Cline是一个自主编码代理，可以提供以下功能：
- **代码生成和编辑**: 根据您的需求生成或修改代码
- **文件操作**: 创建、编辑、删除文件
- **命令执行**: 在您的许可下运行终端命令
- **浏览器使用**: 可以访问网页获取信息
- **MCP工具**: 连接到数据库、API等外部工具

### 3. 首次使用配置
首次使用时，您可能需要：
1. 登录或配置API密钥（如果需要）
2. 授予必要的权限
3. 配置工作目录

### 4. 常用命令
- `Ctrl+'`: 聚焦到Cline聊天输入框
- 在Cline侧边栏中可以直接与AI对话
- 可以要求Cline执行特定任务，如：
  - "创建一个Python脚本"
  - "分析这个PDF文件"
  - "帮我调试这段代码"

### 5. 与您现有项目的集成
您的项目已经包含许多有用的工具：
- PDF处理工具 (`telecom_pdf_analyzer.py`)
- 云盘下载器 (`mobile_cloud_downloader.py`)
- 数据分析工具

您可以让Cline帮助您：
1. 改进现有代码
2. 添加新功能
3. 调试问题
4. 自动化任务

### 6. 权限控制
Cline会在执行以下操作前请求您的许可：
- 运行终端命令
- 修改文件
- 访问外部资源
- 安装软件包

### 7. 故障排除
如果遇到问题：
1. 检查扩展是否已启用
2. 查看VS Code的输出面板（查看 → 输出 → 选择"Cline"）
3. 重新加载VS Code窗口（Ctrl+Shift+P → "Developer: Reload Window"）
4. 检查网络连接（如果需要访问外部API）

## 其他已安装的AI编码助手
您还安装了以下AI编码扩展：
1. **GitHub Copilot** (`GitHub.copilot`) - GitHub的AI代码补全
2. **GitHub Copilot Chat** (`GitHub.copilot-chat`) - 与Copilot对话
3. **DeepSeek** (`Kingleo.deepseek-web`) - 深度求索的AI助手
4. **豆包** (`Doubao.doubao-app-share-vscode-plugin`) - 字节跳动的AI

## 下一步建议
1. 尝试打开Cline侧边栏并与它对话
2. 让Cline帮助您改进现有的PDF分析工具
3. 探索MCP工具集成，连接您的本地工具
4. 配置个性化设置以满足您的开发需求

现在您可以开始使用Claude Code（Cline）来提高您的开发效率了！
