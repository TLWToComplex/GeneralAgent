# GA GeneralAgent软件系统 — 部署包总览（x86_64 / ARM64 双架构）

> **适用环境：** Ubuntu 22.04 LTS（x86_64 / ARM64 aarch64）｜ Docker 29.1.0+ / Compose v2.40.0+  
> **最后更新：** 2026-09-16

> [!IMPORTANT]
> **本部署包为双架构统一版**：同一套脚本与文档同时支持 x86_64 与 ARM64（aarch64）服务器。每个模块包含两份 compose 编排（`docker-compose.yml` → x86_64；`docker-compose.arm64.yml` → ARM64，每个服务已固定 `platform: linux/arm64`），`import-and-start.sh` / `uninstall-and-clean.sh` 通过 `uname -m` 自动识别架构并选择对应 compose 文件与镜像 tar（x86 → `*.tar`，ARM64 → `*-arm64.tar`，导入后镜像标签一致），非 x86_64/aarch64 架构直接报错退出。

本部署包拆分为 **四个相互独立的部分**，各自拥有独立的 compose 编排、一键部署/卸载脚本与文档，可分别部署到同一台或不同服务器上，互不影响：

```
├── GA-app/        应用系统 —— 中间件 + 业务服务 + 前端 + 图表 MCP 
├── model-service/   模型服务 —— LLM + Embedding + Reranker + MinerU 文档解析（GPU）+ FunASR 语音识别（CPU），GPU 部分需 NVIDIA GPU 服务器
├── llm-ops/         大模型集 / 统一网关 —— LiteLLM 网关 + Prometheus 监控 + 后台管理 + 前端（自带 MySQL + PostgreSQL，完全独立自包含）
└── langfuse/        LLM 可观测性平台 —— 追踪 / 评测 / 提示词管理
```

> 部署包上传目录约定为 `/data/deploy/{GA-app, model-service, llm-ops, langfuse}`（各服务的数据/模型挂载路径仍为 `/data/*`，详见各自文档）。

## 双架构说明

部署逻辑、端口、卷挂载、服务编排两架构**完全一致**；差异仅集中在「镜像架构」与文件命名约定：

| 维度 | 说明 |
|------|------|
| **镜像** | ARM64 服务器所有镜像须为 **linux/arm64**。第三方中间件（MySQL / Neo4j / ES / PostgreSQL / Redis / MinIO / ClickHouse / Prometheus / LiteLLM / Langfuse 等）多有官方 arm64 镜像（拉取时加 `--platform linux/arm64`）；**自研镜像**（GA-* / llm-backend / llm-frontend / mineru / funasr / vLLM 等）需用 `docker buildx --platform linux/arm64` 重新构建 |
| **compose** | 每模块两份：`docker-compose.yml`（x86_64）与 `docker-compose.arm64.yml`（ARM64，已固定 `platform: linux/arm64`，避免误拉 amd64 镜像）；**修改端口/参数等请两份同步** |
| **镜像 tar 命名** | x86 为 `*.tar`，ARM64 为 `*-arm64.tar`；脚本按 `uname -m` 自动匹配，导入后镜像标签两架构一致 |
| **部署/卸载脚本** | 每模块各一份，自动识别架构选择 compose 文件与 tar 后缀；不支持的架构直接报错退出 |
| **GPU（model-service）** | ARM64 + NVIDIA GPU（Grace-Hopper / Jetson 等）：nvidia-container-toolkit 与 compose 的 GPU 预留语法和 x86 一致；但 **vLLM / MinerU / FunASR 的 arm64+CUDA 镜像官方发布较少，通常需自行构建** |

## 各部分说明

| 部分 | 内容 | 端口 | 文档 |
|------|------|------|------|
| **GA-app** | MySQL / Neo4j / ES / 知识库对话 / 业务后端 / AI 文档处理 / 前端 / 图表 MCP（8 服务，9 个镜像 tar） | 13306, 17474, 17687, 19200, 17861, 18038, 18200, 15174, 1122, 8999 | [GA-app/deployment_guide.md](GA-app-v1/deployment_guide.md) |
| **model-service** | LLM(Qwen3.8-27B) / Embedding(Qwen3-Embedding-4B) / Reranker(Qwen3-Reranker-4B) / MinerU 文档解析 / FunASR 语音识别（4 个 GPU 服务 + 1 个 CPU 服务，3 个镜像 tar） | 8666, 6667, 6657, 18002, 10095, 10096 | [model-service/deployment_guide.md](model-service/deployment_guide.md) |
| **llm-ops** | MySQL / PostgreSQL / LiteLLM 统一网关 / Prometheus 监控 / 后台管理 / 前端（6 服务 bridge 网络 llm-net，5 个镜像 tar，llm-app.tar 含前后端双镜像） | 23306, 25432, 24000, 29090, 28038, 25173 | [llm-ops/deployment_guide.md](llm-ops/deployment_guide.md) |
| **langfuse** | langfuse-web / worker / postgres / clickhouse / redis / minio（6 服务） | 13000, 19090 | [langfuse/deployment_guide.md](langfuse/deployment_guide.md) |

## 部署顺序（推荐）

四部分无强启动依赖，可任意顺序；推荐：

1. **model-service**（NVIDIA GPU 服务器）—— 先按 deployment_guide 准备各模型到 `/data/{llm,embedding,reranker,mineru,funasr}/`，再部署，为知识库提供 LLM/Embedding/Reranker 与文档解析能力，并提供 FunASR 语音识别（CPU）
   ```bash
   cd model-service && sudo bash import-and-start.sh
   ```
2. **GA-app** —— 核心应用系统
   ```bash
   cd GA-app && sudo bash import-and-start.sh
   ```
3. **llm-ops**（统一网关 / 大模型纳管，需要时）—— 完全独立自包含（自带 MySQL + PostgreSQL，bridge 网络 llm-net），与其他模块无依赖，任意时机可部署
   ```bash
   cd llm-ops && sudo bash import-and-start.sh
   ```
4. **langfuse**（需要 LLM 追踪观测时）
   ```bash
   cd langfuse && sudo bash import-and-start.sh <服务器IP>
   ```

## 各部分之间的对接关系

```
GA-app ──HTTP:8666/6667/6657──▶ model-service (LLM / Embedding / Reranker)   # kb_config.yaml: MODEL_PLATFORMS.api_base_url
GA-app ──HTTP:18002───────────▶ model-service (MinerU /file_parse)           # GA-document-processor/config.yaml: mineru.base_url
                                                                            # （kb-chat 经 ai-doc-processor:18200 间接调用，kb_config.yaml: ENABLE_MINERU / MINERU_URL）
GA-app ──HTTP:13000───────────▶ langfuse (追踪数据上报)                       # GA-service-backend/config.yaml: langfuse.*
```

均为单向 HTTP 调用、弱依赖：model-service / langfuse 未部署或不可用时，GA-app 仍可启动（对应功能自动降级；知识库问答依赖 model-service 的模型服务）。**llm-ops 完全独立自包含**（自带 MySQL + PostgreSQL），与其他三个模块无任何对接依赖。对接配置详见各自文档。

## 卸载

各部分独立卸载，互不影响（脚本自动识别架构选择对应 compose 文件）：

```bash
cd GA-app        && sudo bash uninstall-and-clean.sh
cd model-service   && sudo bash uninstall-and-clean.sh
cd llm-ops         && sudo bash uninstall-and-clean.sh
cd langfuse        && sudo bash uninstall-and-clean.sh
```

> 卸载脚本中的「Docker 系统级深度清理」（prune）作用于整个 Docker，共用服务器时请谨慎选择。

## 镜像 tar 分发表（按服务器架构二选一放入对应 images/ 目录）

| 归属 | x86_64（linux/amd64） | ARM64（linux/arm64） |
|------|---------|---------|
| GA-app/images/ | mysql.tar, neo4j.tar, elasticsearch.tar, GA-kb-chat.tar, GA-service-backend.tar, GA-document-processor.tar, GA-frontend-v2.tar, mcp-chart-streamable-http.tar, skill-agent.tar | 同左名称加 `-arm64` 后缀（如 mysql-arm64.tar） |
| model-service/images/ | mineru.tar, vllm-openai-v0.20.0.tar（llm + embedding + reranker 共用）, funasr.tar（语音识别 ASR） | 同左名称加 `-arm64` 后缀 |
| llm-ops/images/ | llm-app.tar（含 llm-backend + llm-frontend 双镜像，包内标签 :amd64）, mysql.tar, postgres.tar, litellm.tar, prometheus.tar | 同左名称加 `-arm64` 后缀（llm-app-arm64.tar 内标签为 :arm64） |
| langfuse/images/ | postgres.tar, clickhouse.tar, redis.tar, minio.tar, langfuse-web.tar, langfuse-worker.tar | 同左名称加 `-arm64` 后缀 |

> ARM64 tar 制作方法（任意联网机器）：`docker pull --platform linux/arm64 <镜像名:标签> && docker save -o <名称-arm64.tar> <镜像名:标签>`；自研镜像用 `docker buildx build --platform linux/arm64 ...` 构建后导出。
