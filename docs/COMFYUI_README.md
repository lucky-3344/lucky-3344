# ComfyUI 安装和启动指南

## 方式一：一键安装（推荐）

```powershell
cd C:\Users\lucky\projects\my_project
.\comfyui_install.bat
```

## 方式二：手动安装

```powershell
# 1. 克隆仓库
cd %USERPROFILE%
git clone https://github.com/comfyanonymous/ComfyUI.git

# 2. 安装依赖
cd ComfyUI
"C:\Program Files\Lenovo\ModelMgr\Plugins\Image\python.exe" -m pip install -r requirements.txt

# 3. 下载模型
# 访问: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
# 放到: ComfyUI\models\checkpoints\

# 4. 启动
python main.py
```

## 启动后

- **Web界面**: http://127.0.0.1:8188
- **API地址**: http://127.0.0.1:8188

## 使用API生成图片

```python
cd C:\Users\lucky\projects\my_project
python generate_comfyui.py --check
```

## 注意事项

1. 首次启动会自动下载一些文件
2. 建议下载 SD XL 模型以获得高质量图片
3. 如果CPU模式较慢，可以后续配置GPU
