# ChatChat MCP Server

[![Python](https://img.shields.io/badge/Python-3.12.3+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/Docker-Ready-green.svg)](https://www.docker.com/)
[![MCP](https://img.shields.io/badge/MCP-1.4.1-orange.svg)](https://github.com/modelcontextprotocol/python-sdk)

ChatChat MCP Server 是一个基于 Model Context Protocol (MCP) 的知识库搜索服务，为 AI 助手提供强大的知识库检索能力。

## 🚀 功能特性

### 核心功能
- **知识库搜索**: 支持在指定知识库中进行语义搜索
- **多知识库管理**: 可以列出和管理多个知识库
- **相似度控制**: 支持自定义相似度阈值和返回结果数量
- **文件过滤**: 支持按文件名和元数据进行过滤搜索
- **安全验证**: 内置参数验证和安全限制

### 技术特性
- **MCP 协议**: 基于标准 MCP 协议，兼容各种 AI 客户端
- **异步处理**: 全异步架构，支持高并发请求
- **SSE 支持**: 支持 Server-Sent Events 实时通信
- **健康检查**: 内置健康检查端点
- **日志管理**: 完善的日志记录和错误处理

## 📋 系统要求

- **Python**: 3.12.3 或更高版本
- **内存**: 建议 512MB 以上
- **网络**: 需要访问 ChatChat API 服务
- **Docker**: 可选，用于容器化部署

## 🛠️ 安装部署

### 方式一：Docker 部署（推荐）

#### 1. 构建镜像

```bash
# 克隆项目
git clone <repository-url>
cd chatchat-mcp-server

# 构建 Docker 镜像
docker build -t chatchat-mcp-server:latest .

# 或使用构建脚本（Windows）
build.bat

# 或使用构建脚本（Linux/Mac）
chmod +x build.sh
./build.sh
```

#### 2. 运行容器

```bash
# 方式1：使用配置文件挂载（推荐）
# 首先创建配置文件
cp config.example.yaml my-config.yaml
# 编辑配置文件后运行
docker run -d \
  --name chatchat-mcp \
  -p 8848:8848 \
  -v $(pwd)/my-config.yaml:/config/config.yaml \
  chatchat-mcp-server:latest

# 方式2：使用配置目录挂载
mkdir config
cp config.example.yaml config/config.yaml
docker run -d \
  --name chatchat-mcp \
  -p 8848:8848 \
  -v $(pwd)/config:/config \
  chatchat-mcp-server:latest

# 方式3：使用环境变量（向后兼容）
docker run -d \
  --name chatchat-mcp \
  -p 8848:8848 \
  -e CHATCHAT_API_BASE_URL=http://your-chatchat-server:7861 \
  -e DEFAULT_SCORE_THRESHOLD=0.2 \
  chatchat-mcp-server:latest

# 方式4：使用环境文件
docker run -d \
  --name chatchat-mcp \
  -p 8848:8848 \
  --env-file .env \
  chatchat-mcp-server:latest

# 使用 Docker Compose
docker-compose up -d
```

#### 3. 验证部署

```bash
# 检查容器状态
docker ps

# 查看日志
docker logs -f chatchat-mcp

# 健康检查
curl http://localhost:8848/health
```

### 方式二：本地部署

#### 1. 安装依赖

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt
```

#### 2. 配置环境

```bash
# 方式1：使用YAML配置文件（推荐）
cp config.example.yaml config.yaml
nano config.yaml

# 方式2：使用环境变量文件（向后兼容）
cp example.env .env
nano .env
```

#### 3. 启动服务

```bash
python start.py
```

## ⚙️ 配置说明

### 配置方式

### YAML配置文件（推荐）

使用YAML格式的配置文件更易读和维护：

```yaml
# 服务器配置
server:
  host: "0.0.0.0"
  port: 8848

# ChatChat API配置
chatchat:
  api_base_url: "http://localhost:7861"
  api_timeout: 30

# 环境配置
environment:
  type: "development"  # development 或 production

# 安全配置
security:
  max_query_length: 1000
  max_top_k: 50
  default_score_threshold: 0.5
  max_output_tokens: 30000

# 日志配置
logging:
  level: "INFO"
  simplified: true
```

### 环境变量（向后兼容）

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `HOST` | `0.0.0.0` | 服务器监听地址 |
| `PORT` | `8848` | 服务器监听端口 |
| `CHATCHAT_API_BASE_URL` | `http://localhost:7861` | ChatChat API 基础 URL |
| `CHATCHAT_API_TIMEOUT` | `30` | API 请求超时时间（秒） |
| `ENV_TYPE` | `development` | 环境类型（development/production） |
| `MAX_QUERY_LENGTH` | `1000` | 最大查询长度限制 |
| `MAX_TOP_K` | `50` | 最大返回结果数量 |
| `DEFAULT_SCORE_THRESHOLD` | `0.5` | 默认相似度阈值 |
| `MAX_OUTPUT_TOKENS` | `30000` | 最大输出 token 数量 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `SIMPLIFIED_LOGGING` | `true` | 是否启用简化日志 |

### 配置文件示例

```env
# 服务器配置
HOST=0.0.0.0
PORT=8848

# ChatChat API 配置
CHATCHAT_API_BASE_URL=http://localhost:7861
CHATCHAT_API_TIMEOUT=30

# 环境配置
ENV_TYPE=production

# 安全配置
MAX_QUERY_LENGTH=1000
MAX_TOP_K=50
DEFAULT_SCORE_THRESHOLD=0.5
MAX_OUTPUT_TOKENS=30000

# 日志配置
LOG_LEVEL=INFO
SIMPLIFIED_LOGGING=true
```

## 🔧 API 使用

### MCP 工具

#### 1. search_knowledge_base

在指定知识库中搜索相关文档。

**参数：**
- `query` (string): 搜索查询文本
- `knowledge_base_name` (string): 知识库名称
- `top_k` (int, 可选): 返回结果数量，默认 3，最大 50
- `score_threshold` (float, 可选): 相似度阈值，范围 0.0-1.0，默认 0.5
- `file_name` (string, 可选): 文件名过滤
- `metadata` (object, 可选): 元数据过滤

**示例：**
```json
{
  "query": "人工智能的发展历史",
  "knowledge_base_name": "ai_knowledge",
  "top_k": 5,
  "score_threshold": 0.7
}
```

#### 2. list_knowledge_bases

列出所有可用的知识库。

**示例响应：**
```json
{
  "success": true,
  "data": [
    {
      "kb_name": "ai_knowledge",
      "kb_info": "人工智能相关知识库",
      "vs_type": "faiss",
      "embed_model": "bge-large-zh"
    }
  ]
}
```

### HTTP 端点

#### 健康检查
```bash
GET /health
```

#### SSE 连接
```bash
GET /sse
```

## 🐳 Docker 详细说明

### Dockerfile 特性

- **基础镜像**: Python 3.12.3-slim
- **多阶段构建**: 优化镜像大小
- **安全性**: 非 root 用户运行
- **健康检查**: 内置健康检查机制
- **优化**: 最小化层数和缓存优化

### Docker Compose

#### 使用配置文件挂载（推荐）

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'

services:
  chatchat-mcp:
    build: .
    container_name: chatchat-mcp-server
    ports:
      - "8848:8848"
    volumes:
      - ./config.yaml:/config/config.yaml  # 挂载配置文件
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8848/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - chatchat-network

networks:
  chatchat-network:
    driver: bridge
```

#### 使用环境变量（向后兼容）

```yaml
version: '3.8'

services:
  chatchat-mcp:
    build: .
    container_name: chatchat-mcp-server
    ports:
      - "8848:8848"
    environment:
      - CHATCHAT_API_BASE_URL=http://chatchat-server:7861
      - ENV_TYPE=production
      - LOG_LEVEL=INFO
    env_file:
      - .env
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8848/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - chatchat-network

networks:
  chatchat-network:
    driver: bridge
```

### 镜像管理

```bash
# 查看镜像
docker images chatchat-mcp-server

# 删除镜像
docker rmi chatchat-mcp-server:latest

# 导出镜像
docker save -o chatchat-mcp-server.tar chatchat-mcp-server:latest

# 导入镜像
docker load -i chatchat-mcp-server.tar

# 推送到仓库
docker tag chatchat-mcp-server:latest your-registry/chatchat-mcp-server:latest
docker push your-registry/chatchat-mcp-server:latest
```

## 📊 监控和日志

### 日志查看

```bash
# Docker 容器日志
docker logs -f chatchat-mcp

# 本地部署日志
tail -f logs/chatchat-server.log
```

### 性能监控

```bash
# 容器资源使用
docker stats chatchat-mcp

# 健康状态检查
curl http://localhost:8848/health
```

## 🔍 故障排除

### 常见问题

#### 1. 连接 ChatChat API 失败
```bash
# 检查网络连接
curl http://your-chatchat-server:7861/docs

# 检查环境变量
docker exec chatchat-mcp env | grep CHATCHAT
```

#### 2. 端口冲突
```bash
# 查看端口占用
netstat -tulpn | grep 8848

# 使用不同端口
docker run -p 8849:8848 chatchat-mcp-server:latest
```

#### 3. 内存不足
```bash
# 增加内存限制
docker run --memory=1g chatchat-mcp-server:latest
```

#### 4. 权限问题
```bash
# 检查文件权限
ls -la /app

# 重新构建镜像
docker build --no-cache -t chatchat-mcp-server:latest .
```

### 调试模式

```bash
# 启用调试日志
docker run -e LOG_LEVEL=DEBUG chatchat-mcp-server:latest

# 进入容器调试
docker exec -it chatchat-mcp bash
```

## 🤝 开发指南

### 项目结构

```
chatchat-mcp-server/
├── src/
│   ├── client/          # ChatChat API 客户端
│   ├── tools/           # MCP 工具实现
│   ├── config.py        # 配置管理
│   └── server.py        # 服务器主程序
├── config.yaml          # 默认YAML配置文件
├── config.example.yaml  # 配置文件示例
├── Dockerfile           # Docker 构建文件
├── DOCKER_CONFIG.md     # Docker配置详细说明
├── requirements.txt     # Python 依赖
├── start.py            # 启动脚本
├── example.env         # 环境变量示例（向后兼容）
└── README.md           # 项目文档
```

### 本地开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/

# 代码格式化
black src/
isort src/

# 类型检查
mypy src/
```

## 📝 配置文件管理

### 灵活配置系统

本项目现在支持灵活的配置文件系统，无需每次修改配置都重新构建Docker镜像：

#### 快速开始

```bash
# 1. 复制配置示例
cp config.example.yaml config.yaml

# 2. 编辑配置
nano config.yaml

# 3. 使用配置文件运行
docker run -d \
  --name chatchat-mcp \
  -p 8848:8848 \
  -v $(pwd)/config.yaml:/config/config.yaml \
  chatchat-mcp-server:latest

# 4. 修改配置后重启容器即可
docker restart chatchat-mcp
```

#### 配置文件优势

- ✅ **无需重建镜像**：修改配置只需重启容器
- ✅ **向后兼容**：仍支持环境变量配置
- ✅ **易于管理**：YAML格式更清晰易读
- ✅ **版本控制友好**：配置文件可以版本化管理
- ✅ **多环境支持**：轻松管理开发、测试、生产环境

#### 详细配置说明

更多配置选项和使用方法，请参考：[Docker配置详细说明](DOCKER_CONFIG.md)

## 📄 许可证

本项目采用 MIT 许可证，详见 [LICENSE](LICENSE) 文件。

## 🆘 支持

如果您遇到问题或有建议，请：

1. 查看 [常见问题](#故障排除) 部分
2. 提交 [Issue](https://github.com/your-repo/issues)
3. 联系维护团队

---

**版本**: 1.1.0  
**更新时间**: 2024年12月  
**主要更新**: 新增灵活配置文件系统，支持YAML配置文件挂载  
**维护者**: ChatChat Team