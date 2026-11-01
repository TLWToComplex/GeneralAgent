# Sequential Thinking MCP Server (Streamable HTTP)

这是一个基于 Python 实现的 Sequential Thinking MCP (Model Context Protocol) 服务器，使用 **Streamable HTTP** 通信。

## 功能特性

- **动态思考过程**：支持灵活的思考过程，可适应并演进
- **思考修订**：可以质疑或修订之前的思考
- **分支思考**：支持思考分支和回溯
- **实时交互**：通过 MCP Streamable HTTP 进行工具调用
- **安全验证**：内置参数验证和输出限制
- **彩色输出**：支持终端彩色输出以提高可读性

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

默认服务地址：`http://localhost:8849`

MCP Streamable HTTP 端点：`http://localhost:8849/`

## Docker 部署

### 构建 Docker 镜像

#### Windows Docker Desktop

```bash
# 构建镜像
docker build -t sequential-thinking-mcp-streamable-http .

# 运行容器（带自动重启）
docker run -d --name sequential-thinking-streamable-http --restart unless-stopped -p 8849:8849 sequential-thinking-mcp-streamable-http
```

#### Linux x86_64

```bash
# 构建镜像
docker build -t sequential-thinking-mcp-streamable-http .

# 运行容器（带自动重启）
docker run -d --name sequential-thinking-streamable-http --restart unless-stopped -p 8849:8849 sequential-thinking-mcp-streamable-http
```

#### Linux ARM64

```bash
# 构建ARM64镜像
docker build --platform linux/arm64 -t sequential-thinking-mcp-streamable-http:arm64 .

# 运行容器（带自动重启）
docker run -d --name sequential-thinking-streamable-http --restart unless-stopped -p 8849:8849 sequential-thinking-mcp-streamable-http:arm64
```

### 多架构构建（推荐）

```bash
# 创建并使用新的构建器
docker buildx create --name multiarch --use

# 构建并推送多架构镜像
docker buildx build --platform linux/amd64,linux/arm64 -t sequential-thinking-mcp-streamable-http:latest --push .

# 或者只构建到本地
docker buildx build --platform linux/amd64,linux/arm64 -t sequential-thinking-mcp-streamable-http:latest --load .
```

## 配置选项

### 环境变量

- `HOST`: 服务器主机地址（默认：`0.0.0.0`）
- `PORT`: 服务器端口（默认：`8849`）
- `ENV_TYPE`: 环境类型（`development`/`production`）
- `MAX_THOUGHT_LENGTH`: 最大思考内容长度（默认：`5000`）
- `MAX_TOTAL_THOUGHTS`: 最大思考步数（默认：`100`）
- `MAX_OUTPUT_TOKENS`: 最大输出 token 数（默认：`30000`）
- `LOG_LEVEL`: 日志级别（默认：`INFO`）
- `SIMPLIFIED_LOGGING`: 简化日志输出（默认：`true`）
- `DISABLE_THOUGHT_LOGGING`: 禁用思考过程日志（默认：`false`）

## 工具使用

### `sequentialthinking` 工具

用于动态反思问题解决，通过分步思考帮助分析问题。

#### 参数说明

- `thought`（必需）：当前思考步骤内容
- `nextThoughtNeeded`（必需）：是否需要下一步思考
- `thoughtNumber`（必需）：当前思考步骤编号
- `totalThoughts`（必需）：预估总思考步骤数
- `isRevision`（可选）：是否修订之前思考
- `revisesThought`（可选）：修订的思考步骤编号
- `branchFromThought`（可选）：分支起点步骤编号
- `branchId`（可选）：分支标识符
- `needsMoreThoughts`（可选）：是否需要更多思考步骤

### `get_thinking_results` 工具

返回当前思考历史与分支信息，输出为 JSON 字符串，便于追踪完整推理过程。

## 项目结构

```text
mcp-sequential-thinking-streamable-http/
├── src/
│   ├── __init__.py
│   ├── config.py                      # 配置管理
│   ├── server.py                      # Streamable HTTP 服务器入口
│   └── tools/
│       ├── __init__.py
│       └── sequential_thinking_tool.py
├── requirements.txt                   # Python 依赖
├── .env.example                       # 环境变量示例
├── start.py                           # 启动脚本
└── README.md
```

## 开发

### 运行测试

```bash
pytest
```

### 日志调试

设置 `SIMPLIFIED_LOGGING=false` 和 `LOG_LEVEL=DEBUG` 以获取详细调试日志。

## 许可证

本项目基于现有的 Sequential Thinking 实现，遵循相同许可证条款。
