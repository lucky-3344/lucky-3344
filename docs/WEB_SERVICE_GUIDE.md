# FastAPI Web 服务部署指南

## 快速开始

### 1. 本地运行

#### 安装依赖
```bash
pip install fastapi uvicorn
```

#### 启动服务
```bash
python web_service.py
```

访问：http://localhost:8000

### 2. Docker 运行

#### 构建镜像
```bash
docker build -f Dockerfile.web -t process-user-file-web:latest .
```

#### 运行容器
```bash
docker run -d \
  -p 8000:8000 \
  -v ./data:/app/data \
  -e AMAP_KEY=your_key \
  --name process-web \
  process-user-file-web:latest
```

访问：http://localhost:8000

#### Docker Compose（推荐）
```bash
# 启动
docker-compose -f docker-compose.web.yml up -d

# 停止
docker-compose -f docker-compose.web.yml down

# 查看日志
docker-compose -f docker-compose.web.yml logs -f
```

## 功能特性

### 前端界面
- ✅ 响应式设计（支持移动设备）
- ✅ 实时地址搜索
- ✅ 单点查询结果展示
- ✅ 批量 CSV 上传处理
- ✅ 搜索结果表格显示

### API 接口

#### 1. 单点查询
```bash
curl "http://localhost:8000/api/single-point?lng=113.41547&lat=23.23962"
```

**响应：**
```json
{
  "success": true,
  "data": {
    "wgs84": {"lng": 113.41547, "lat": 23.23962},
    "gcj02": {"lng": 113.42, "lat": 23.24},
    "area_info": "市区",
    "features": "路边 | 人员密集处",
    "poi": "商业中心",
    "distance_to_road": "50m",
    "business_area": "五一广场商圈",
    "standard_address": "广东省广州市黄埔区",
    "amap_url": "https://uri.amap.com/marker?position=...",
    "google_url": "https://www.google.com/maps?q=..."
  }
}
```

#### 2. 地址搜索
```bash
curl "http://localhost:8000/api/address-search?address=黄埔区中山大道"
```

**响应：**
```json
{
  "success": true,
  "data": [
    {
      "formatted_address": "广东省广州市黄埔区中山大道西",
      "wgs84": {"lng": 113.41547, "lat": 23.23962},
      "gcj02": {"lng": 113.42, "lat": 23.24}
    }
  ]
}
```

#### 3. 批量上传
```bash
curl -X POST \
  -F "file=@input.csv" \
  http://localhost:8000/api/batch-upload
```

**CSV 格式示例：**
```csv
名称,描述,经度,纬度
点位1,描述1,113.41547,23.23962
点位2,描述2,113.42,23.24
```

**响应：**
```json
{
  "success": true,
  "count": 2,
  "data": [
    {
      "行号": 2,
      "名称": "点位1",
      "WGS84经度": 113.41547,
      "WGS84纬度": 23.23962,
      "GCJ02经度": 113.42,
      "GCJ02纬度": 23.24,
      "区域属性": "市区",
      "地理特征": "路边",
      "状态": "成功"
    }
  ]
}
```

## 部署到云平台

### 阿里云 ECS

```bash
# 1. 登录 ACR
docker login -u username -p token registry.cn-hangzhou.aliyuncs.io

# 2. 构建并标记镜像
docker build -f Dockerfile.web -t registry.cn-hangzhou.aliyuncs.io/my-project/process-web:latest .

# 3. 推送到 ACR
docker push registry.cn-hangzhou.aliyuncs.io/my-project/process-web:latest

# 4. 在 ECS 上拉取并运行
docker run -d \
  -p 8000:8000 \
  -e AMAP_KEY=your_key \
  --restart always \
  registry.cn-hangzhou.aliyuncs.io/my-project/process-web:latest
```

### 阿里云容器实例（ECI）

```bash
docker run -d \
  -p 8000:8000 \
  -e AMAP_KEY=your_key \
  registry.cn-hangzhou.aliyuncs.io/my-project/process-web:latest
```

### Kubernetes（ACK）

创建 `deployment.yaml`：

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: process-user-file-web
spec:
  replicas: 3
  selector:
    matchLabels:
      app: process-web
  template:
    metadata:
      labels:
        app: process-web
    spec:
      containers:
      - name: process-web
        image: registry.cn-hangzhou.aliyuncs.io/my-project/process-web:latest
        ports:
        - containerPort: 8000
        env:
        - name: AMAP_KEY
          valueFrom:
            secretKeyRef:
              name: amap-secret
              key: key
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: process-web-service
spec:
  selector:
    app: process-web
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

部署：
```bash
kubectl apply -f deployment.yaml
```

## 配置说明

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| AMAP_KEY | 高德 API Key | 内置默认 Key |
| AMAP_FORCE_DIRECT | 强制直连高德 | 0 |
| AMAP_FORCE_NO_PROXY | 禁用代理 | 0 |
| AMAP_IP_OVERRIDE | 指定高德 API IP | - |

## 性能优化

### 1. API 调用速率限制
当前每条记录 API 调用间隔为 0.5 秒，可在 `web_service.py` 中调整：
```python
time.sleep(0.5)  # 改为你需要的间隔
```

### 2. 缓存结果
建议在生产环境添加 Redis 缓存同一坐标的查询结果

### 3. 异步处理
对于大批量文件（>1000 条），建议改为异步任务处理，返回任务 ID，前端轮询查询结果

### 4. 数据库存储
建议添加 PostgreSQL/MySQL 存储历史查询记录

## 常见问题

**Q: 上传大文件超时？**
A: 修改超时配置，或分批上传。在 `web_service.py` 中调整：
```python
# 修改 FastAPI 配置
app = FastAPI(
    ...
    timeout=300  # 秒
)
```

**Q: 前端界面样式错乱？**
A: 检查浏览器控制台错误，确保网络连接。刷新页面或清除缓存。

**Q: 如何添加认证？**
A: 可使用 FastAPI 的 Security 模块：
```python
from fastapi.security import HTTPBearer
security = HTTPBearer()

@app.get("/api/single-point")
async def analyze_single_point(lng: float, lat: float, credentials = Depends(security)):
    ...
```

**Q: 如何集成现有系统？**
A: 通过 REST API 调用，或使用 SDK（可根据需要开发）。
