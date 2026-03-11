# Docker 部署指南

## 构建镜像

```bash
docker build -f Dockerfile.process -t process-user-file:latest .
```

## 运行容器

### 基础命令

```bash
docker run --rm -v /path/to/data:/data process-user-file:latest -i /data/input.csv -o /data/output.csv
```

### 参数说明

- `-v /path/to/data:/data` - 挂载本地目录到容器的 `/data` 目录
- `-i /data/input.csv` - 输入 CSV 文件路径
- `-o /data/output.csv` - 输出 CSV 文件路径
- `--open-google` - 批量完成后打开 Google 地图
- `--open-amap` - 批量完成后打开高德地图
- `--delay 1.0` - API 调用间隔（秒）

## 使用示例

### 1. 单点分析

```bash
docker run --rm process-user-file:latest --single 113.41547,23.23962
```

输出：
```
区域属性: 市区
地理特征: 路边 | 人员密集处
POI: 商业中心
...
```

### 2. 批量处理 CSV

```bash
# 在本机创建数据目录
mkdir -p ~/map_data

# 将 CSV 文件放入
cp my_locations.csv ~/map_data/

# 运行容器
docker run --rm \
  -v ~/map_data:/data \
  process-user-file:latest \
  -i /data/my_locations.csv \
  -o /data/results.csv

# 查看输出
ls ~/map_data/
cat ~/map_data/results.csv
```

### 3. 生成 KML 文件

```bash
docker run --rm \
  -v ~/map_data:/data \
  process-user-file:latest \
  -i /data/my_locations.csv \
  -o /data/results.xlsx
# 输出: ~/map_data/batch_results_*.kml
```

## Docker Compose 快速部署

创建 `docker-compose.yml`：

```yaml
version: '3.8'
services:
  location-analyzer:
    build:
      context: .
      dockerfile: Dockerfile.process
    image: process-user-file:latest
    volumes:
      - ./data:/data
    environment:
      AMAP_KEY: ${AMAP_KEY}
    command: ["-i", "/data/input.csv", "-o", "/data/output.csv"]
```

运行：

```bash
export AMAP_KEY=your_amap_key_here
docker-compose up --build
```

## 云部署（Docker Hub / ACR）

### 推送到 Docker Hub

```bash
docker tag process-user-file:latest yourname/process-user-file:latest
docker push yourname/process-user-file:latest
```

### 推送到 Azure Container Registry

```bash
az acr build --registry myregistry --image process-user-file:latest .
```

### 在云服务运行

**Azure Container Instances：**

```bash
az container create \
  --resource-group myResourceGroup \
  --name process-user-file \
  --image myregistry.azurecr.io/process-user-file:latest \
  --registry-login-server myregistry.azurecr.io \
  --registry-username <username> \
  --registry-password <password> \
  --environment-variables AMAP_KEY=xxxxx \
  --volume-mount-path /data \
  /data
```

**AWS ECS / 阿里云 ACR 类似部署方式。**

## 环境变量

| 变量 | 说明 | 示例 |
|------|------|------|
| `AMAP_KEY` | 高德地图 API Key | `abc123xyz` |
| `AMAP_FORCE_DIRECT` | 强制直连高德 | `1` 或 `0` |
| `AMAP_FORCE_NO_PROXY` | 禁用代理 | `1` 或 `0` |
| `AMAP_IP_OVERRIDE` | 指定高德 API IP | `106.11.28.122` |

## 常见问题

**Q: 容器内如何访问本机文件？**
A: 使用 `-v` 参数挂载本地目录，容器内访问 `/data` 路径

**Q: 如何在容器内运行 GUI？**
A: 当前镜像仅支持 CLI 模式。如需 GUI，可在本机运行可执行文件或 Python 脚本

**Q: 高德 API 请求失败？**
A: 检查 `AMAP_KEY` 环境变量、网络连接，或使用 `AMAP_IP_OVERRIDE` 绕过 DNS

**Q: 输出文件没有生成？**
A: 确保挂载目录有写入权限，容器内工作目录为 `/data`
