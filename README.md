# GeneralAgent

**通用智能体构建与服务平台 · GA**

GeneralAgent 提供通用智能体的配置、构建与服务能力，将模型、角色提示词、知识库、MCP 工具、Skill 和执行环境组合为可复用的智能体。资料问答、信息检索、办公处理和文档生成等场景通过统一的能力接入与任务执行流程完成。

平台以 Agent Harness 的思路组织模型调用、工具执行、上下文和任务过程管理，支持从用户提出问题，到检索资料、调用工具，再到生成与交付文档的完整流程。

## 核心能力

### 可配置的智能体

- 创建通用 Agent 与 DeepAgent，按任务组合模型、提示词、知识库、MCP 工具、Skill 和环境变量。
- 设置个人使用或公开共享，按角色与权限管理可访问的能力。
- 维护可复用的智能体配置，将同类任务流程应用到不同场景。

### 模型与工具接入

- 接入兼容接口的大模型服务，配置对话、推理和工具调用能力。
- 注册并管理 MCP 服务，选择可用工具并绑定到智能体。
- 上传和解析 Skill 文件，组织触发条件、执行步骤及依赖资源。
- 通过沙盒运行需要文件、脚本或独立环境的任务，管理执行产物。

### 知识库与知识图谱

- 创建知识库，选择 Embedding 模型及向量库，管理文档和分块参数。
- 对接知识检索服务，为模型回答提供相关资料。
- 配置实体、关系及 Neo4j 图谱能力，支持组织关系等关联知识查询。
- 按场景组合知识库与工具，完成资料查询和业务处理。

### 对话、历史记录与文档交付

- 提供模型对话与智能体对话，展示任务过程和执行结果。
- 支持角色提示词动态变量预览，以及对话视图和文档视图切换。
- 管理会话列表、历史消息和会话详情，方便回看已完成的任务。
- 通过对话生成 Word 等文档，在交付中心查看和管理产物。

## 使用流程

```mermaid
flowchart LR
    A[选择或创建智能体] --> B[配置模型与角色提示词]
    B --> C[关联知识库、MCP 与 Skill]
    C --> D[发起对话任务]
    D --> E[检索资料与调用工具]
    E --> F[生成回答或文档]
    F --> G[交付中心与历史会话]
```

例如，可配置资料整理智能体：根据问题检索知识库，调用工具处理资料，再通过文档 Skill 生成报告，并将文档与会话过程关联保存。

## 技术组成

| 层次 | 技术与职责 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite：配置、对话、知识库与文档界面 |
| 服务接口 | Python、Flask、FastAPI：业务 API、认证和任务入口 |
| 智能体执行 | LangChain、LangGraph、DeepAgents：模型与工具编排、状态与执行过程管理 |
| 数据访问 | SQLAlchemy、MySQL：账号、配置、权限及会话数据 |
| 执行状态 | SQLite 检查点、文件存储：执行状态、会话附件及产物 |
| 知识服务 | Embedding、向量检索、Neo4j：文档检索与关系知识 |
| 能力扩展 | MCP、Skill、Docker 沙盒：工具接入和隔离执行 |
| 部署与观测 | Docker Compose、代理服务、Langfuse |

## 仓库结构

```text
GeneralAgent/
├── apps/
│   ├── GA-backend-v1/       智能体、模型、知识库、Skill、会话与交付服务
│   ├── GA-frontend-v1/      对应的业务工作台
│   ├── GA-backend-v2/       FastAPI 认证与执行实例路由服务
│   ├── GA-frontend-v2/      新版控制台与工作台界面
│   ├── proxy/              统一入口与执行实例代理
│   ├── mirror-hub/         依赖及制品镜像服务
│   ├── gateway/            网关扩展目录
│   └── permission/         权限能力扩展目录
├── assets/
│   ├── skills/             文档、表格、图表等技能与资源
│   ├── mcp/                知识库、数据库、图表等 MCP 服务
│   ├── tools/              工具资源
│   └── others/             其他运行资源
├── dsh/                    执行底座镜像、插件和预设的集成目录
├── deploy/
│   ├── GA-app-v1/          应用服务编排与配置模板
│   ├── model-service/      模型服务部署配置
│   ├── llm-ops/            模型网关部署配置
│   └── langfuse/           可观测性部署配置
└── document/               长期维护文档
```

`v1` 工作台与业务服务提供模型、智能体、知识库、工具和会话等业务。`v2` 控制台配合认证、实例路由与执行底座使用。两套前后端按对应关系启动。

## 本地运行

### 准备环境

- Python 3.11、Node.js 20.19+ 或 22.12+、npm。
- MySQL；使用知识能力时准备对应的知识检索、Embedding 与图谱服务。
- 可访问的模型 API。
- 使用 Skill 执行沙盒时，需要 Docker Engine 与对应执行镜像。

### 业务后端

```bash
cd apps/GA-backend-v1
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows PowerShell：.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp config.example.yaml config.yaml
cp .env.example .env
```

在 MySQL 中准备 `ai_service` 数据库，并执行 [`src/sql/`](apps/GA-backend-v1/src/sql/) 中的建表脚本。填写本地配置后启动：

```bash
python main.py
```

PowerShell 中复制文件使用 `Copy-Item`。后端默认监听 `http://localhost:8038`。

| 配置 | 用途 |
| --- | --- |
| `DATABASE_URL` | MySQL 连接 |
| `LLM_API_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL_NAME` | 模型接口、凭据与模型名 |
| `KB_CHAT_BASE_URL` | 知识检索服务地址 |
| `file_processing.service_url` | 文档解析服务地址，位于 YAML 配置 |
| `DEEPAGENT_SKILLS_PATH` / `HOST_SKILLS_PATH` | 技能目录与沙盒挂载源 |
| `deepagent.memory.*` | 执行实例内外的记忆目录映射 |
| `LANGFUSE_ENABLED` / `LANGFUSE_HOST` | 可选的调用观测服务 |

环境变量优先于 YAML 配置。使用 `GA_CONFIG_FILE` 可指定其他本地配置文件。

### 业务前端

```bash
cd apps/GA-frontend-v1
npm ci
npm run dev
```

默认访问 `http://localhost:5173`。通过 [`public/runtime-config.json`](apps/GA-frontend-v1/public/runtime-config.json) 配置后端地址、系统名称及外部服务地址。

### 新版控制台与认证服务

```bash
# 认证服务
cd apps/GA-backend-v2
pip install -r requirements.txt
cp .env.example .env
python run.py
```

```bash
# 新版控制台
cd apps/GA-frontend-v2
npm ci
npm run dev
```

认证服务使用 [`sql/001_init_auth.sql`](apps/GA-backend-v2/sql/001_init_auth.sql) 和 [`sql/003_init_dsh_instance.sql`](apps/GA-backend-v2/sql/003_init_dsh_instance.sql) 初始化表结构。详见 [认证服务文档](apps/GA-backend-v2/README.md) 和 [控制台配置示例](apps/GA-frontend-v2/public/config/config.example.json)。

## 部署

应用编排与配置位于 [`deploy/GA-app-v1/`](deploy/GA-app-v1/)。准备对应的模型、文档解析、知识库及应用镜像，调整镜像标签、服务地址和挂载目录后启动：

```bash
cd deploy/GA-app-v1
docker compose -f docker-compose.yml config
docker compose -f docker-compose.yml up -d
```

仓库内服务的镜像构建示例，在仓库根目录执行：

```bash
docker build -t app/ga-service-backend:local apps/GA-backend-v1
docker build -t app/ga-frontend-v1:local apps/GA-frontend-v1
docker build -t app/ga-backend-v2:local apps/GA-backend-v2
```

执行底座、知识库和文档处理服务分别管理，不要求运行在同一进程。部署细节见 [`deploy/`](deploy/README.md) 中的文档。

## 开发验证

```bash
# 认证、权限、实例路由与数据库结构测试，使用 SQLite 内存库
cd apps/GA-backend-v2
pip install -r requirements-dev.txt
python -m unittest discover -s tests -q
```

```bash
# 新版前端类型检查与构建
cd apps/GA-frontend-v2
npm run typecheck
npm run build
```

## 命名与第三方组件

- 产品显示名为 **GeneralAgent**，目录缩写为 **GA**。
- npm 包名与镜像仓库名使用合法的小写 `ga-…`，目录使用 `GA-…`。
- 外部模型、MCP、Skill 与执行底座的协议名称按各自接口保留。
- `src/vendors/`、第三方技能与 MCP 服务保留各自许可证和来源说明。
