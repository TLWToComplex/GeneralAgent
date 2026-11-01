# Sequential Thinking MCP Server

这是一个基于Python实现的Sequential Thinking MCP (Model Context Protocol) 服务器，支持SSE (Server-Sent Events) 通信。原服务由Anthropic公司用typescripts实现。地址 https://github.com/modelcontextprotocol/servers。

## 功能特性

- **动态思考过程**: 支持灵活的思考过程，可以适应和演进
- **思考修订**: 可以质疑或修订之前的思考
- **分支思考**: 支持思考分支和回溯
- **实时反馈**: 通过SSE提供实时的思考过程反馈
- **安全验证**: 内置参数验证和输出限制
- **彩色输出**: 支持终端彩色输出以提高可读性

## 安装和运行

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并根据需要修改配置：

```bash
cp .env.example .env
```

### 3. 启动服务器

```bash
python start.py
```

服务器将在 `http://localhost:8849/sse` 启动。

## Docker 部署

### 构建 Docker 镜像

#### Windows Docker Desktop

```bash
# 构建镜像
docker build -t sequential-thinking-mcp .

# 运行容器（带自动重启）
docker run -d --name sequential-thinking --restart unless-stopped -p 8849:8849 sequential-thinking-mcp
```

#### Linux x86_64

```bash
# 构建镜像
docker build -t sequential-thinking-mcp .

# 运行容器（带自动重启）
docker run -d --name sequential-thinking --restart unless-stopped -p 8849:8849 sequential-thinking-mcp
```

#### Linux ARM64

```bash
# 构建ARM64镜像
docker build --platform linux/arm64 -t sequential-thinking-mcp:arm64 .

# 运行容器（带自动重启）
docker run -d --name sequential-thinking --restart unless-stopped -p 8849:8849 sequential-thinking-mcp:arm64
```

### 多架构构建（推荐）

使用 Docker Buildx 构建支持多架构的镜像：

```bash
# 创建并使用新的构建器
docker buildx create --name multiarch --use

# 构建并推送多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 -t sequential-thinking-mcp:latest --push .

# 或者只构建到本地
docker buildx build --platform linux/amd64,linux/arm64 -t sequential-thinking-mcp:latest --load .
```

### Docker Compose 部署

创建 `docker-compose.yml` 文件：

```yaml
version: '3.8'
services:
  sequential-thinking:
    build: .
    container_name: sequential-thinking-mcp
    restart: unless-stopped
    ports:
      - "8849:8849"
    environment:
      - LOG_LEVEL=INFO
      - SIMPLIFIED_LOGGING=true
    volumes:
      - ./logs:/app/logs  # 可选：持久化日志
```

运行：

```bash
docker-compose up -d
```

## 配置选项

### 环境变量

- `HOST`: 服务器主机地址 (默认: 0.0.0.0)
- `PORT`: 服务器端口 (默认: 8849)
- `ENV_TYPE`: 环境类型 (development/production)
- `MAX_THOUGHT_LENGTH`: 最大思考内容长度 (默认: 5000)
- `MAX_TOTAL_THOUGHTS`: 最大思考步数 (默认: 100)
- `MAX_OUTPUT_TOKENS`: 最大输出token数 (默认: 30000)
- `LOG_LEVEL`: 日志级别 (默认: INFO)
- `SIMPLIFIED_LOGGING`: 简化日志输出 (默认: true)
- `DISABLE_THOUGHT_LOGGING`: 禁用思考过程日志 (默认: false)

## 工具使用

### sequentialthinking 工具

这是一个详细的动态反思问题解决工具，通过思考过程帮助分析问题。

#### 参数说明

- `thought` (必需): 当前思考步骤的内容
- `nextThoughtNeeded` (必需): 是否需要下一个思考步骤
- `thoughtNumber` (必需): 当前思考步骤编号
- `totalThoughts` (必需): 预估的总思考步骤数
- `isRevision` (可选): 是否为修订之前的思考
- `revisesThought` (可选): 如果是修订，指定修订的思考步骤编号
- `branchFromThought` (可选): 如果是分支，指定分支起点的思考步骤编号
- `branchId` (可选): 分支标识符
- `needsMoreThoughts` (可选): 是否需要更多思考步骤

#### 使用场景

- 分解复杂问题为步骤
- 需要修订的规划和设计
- 可能需要纠正方向的分析
- 初始范围不明确的问题
- 需要多步骤解决方案的任务
- 需要在多个步骤间保持上下文的任务
- 需要过滤无关信息的情况

## 项目结构

```
seq-thinking/
├── src/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── server.py              # 主服务器文件
│   └── tools/
│       ├── __init__.py
│       └── sequential_thinking_tool.py  # Sequential Thinking工具实现
├── requirements.txt           # Python依赖
├── .env.example              # 环境变量示例
├── start.py                  # 启动脚本
└── README.md                 # 项目文档
```

## 开发

### 运行测试

```bash
pytest
```

### 日志调试

设置环境变量 `SIMPLIFIED_LOGGING=false` 和 `LOG_LEVEL=DEBUG` 以获取详细的调试信息。

## 许可证

本项目基于现有的Sequential Thinking实现，遵循相同的许可证条款。