# GA GeneralAgent软件系统（应用部分）— Docker 一键部署指南

> **适用环境：** Ubuntu 22.04 LTS（x86_64 / ARM64）｜ Docker 29.1.0+ / Compose v2.40.0+  
> **最后更新：** 2026-09-16  
> 整体部署拆分为四个相互独立的部分：**GA-app（本文档，应用系统）**、**model-service（GPU 模型服务：LLM / Embedding / Reranker / MinerU 文档解析 + FunASR 语音识别，见 `../model-service/deployment_guide.md`）**、**llm-ops（大模型集 / 统一网关，见 `../llm-ops/deployment_guide.md`）**、**langfuse（LLM 可观测性，见 `../langfuse/deployment_guide.md`）**。四者可分别部署/卸载，互不影响。

---

> [!IMPORTANT]
> **本部署包同时支持 x86_64 与 ARM64（aarch64）两种架构**：部署/卸载脚本通过 `uname -m` 自动识别架构，自动选择 compose 文件（x86 → `docker-compose.yml`，ARM64 → `docker-compose.arm64.yml`，后者每个服务已固定 `platform: linux/arm64`）与镜像 tar（x86 → `*.tar`，ARM64 → `*-arm64.tar`，导入后镜像标签一致），非 x86_64/aarch64 架构直接报错退出。`images/` 中只需放入与目标服务器架构对应的 tar；第三方中间件多有官方 arm64 镜像，**自研镜像需用 `docker buildx --platform linux/arm64` 重新构建**。

## 一、部署包清单

```
GA-app/
├── docker-compose.yml              # 应用服务编排（8 个服务，x86_64）
├── docker-compose.arm64.yml        # 同上，ARM64（platform: linux/arm64）
├── import-and-start.sh             # 一键部署脚本（自动识别架构）
├── uninstall-and-clean.sh          # 一键卸载脚本（自动识别架构）
├── sql/ai_service.sql              # MySQL 初始化脚本
├── neo4j/                          # Neo4j 插件 jar（apoc.jar + graph-data-science.jar）
├── GA-mcp/.docker.env            # 图表 MCP 环境变量
├── GA-kb-chat/kb_config.yaml     # 知识库配置
├── GA-service-backend/           # 后端配置 config.yaml + skills_repo/ + deepagent.db + deepagent.db-shm + deepagent.db-wal
├── GA-document-processor/config.yaml   # 文档解析引擎配置
├── GA-frontend-v2/runtime-config.json  # 前端运行时配置
└── images/                         # 9 个镜像 tar 包（自行放入，按架构选择）
```

## 二、服务与镜像一览

| tar 文件 | 镜像名:标签 | 服务（容器名）                           | 宿主机端口 |
|----------|------------|-----------------------------------|-|
| `mysql.tar` | `mid/mysql:8.0.45` | MySQL（mid-mysql）                  | 13306 |
| `neo4j.tar` | `mid/neo4j:2026-05-15` | Neo4j（mid-neo4j）                  | 17474 / 17687(Bolt) |
| `elasticsearch.tar` | `mid/elasticsearch:9.1.6` | ES（mid-elasticsearch）             | 19200 |
| `GA-kb-chat.tar` | `app/ga-kb-chat:2026-05-15` | 知识库对话（app-GA-kb-chat）           | 17861 |
| `GA-service-backend.tar` | `app/ga-service-backend:2026-05-15` | 业务后端（app-GA-service-backend）    | 18038 |
| `GA-document-processor.tar` | `app/ga-document-processor:2026-05-15` | AI 文档处理（app-ai-doc-processor）     | 18200 |
| `GA-frontend-v2.tar` | `app/ga-frontend-v2:2026-05-15` | 前端（app-GA-frontend-v2）          | 15174 |
| `mcp-chart-streamable-http.tar` | `mcp-server-chart-streamable-http:1.0.0` | 图表 MCP（app-mcp-server-chart）      | **1122**(MCP) / **8999**(渲染) |
| `skill-agent.tar` | `skill-agent:latest` | 沙盒镜像包（skill-agent-sandbox-会话线程id） ||

> **ARM64 环境**：tar 文件名为上表名称加 `-arm64` 后缀（如 `mysql-arm64.tar`、`skill-agent-arm64.tar`），脚本自动按架构匹配；导入后的镜像名:标签两架构完全一致。

启动顺序由 `depends_on` + `healthcheck` 自动控制：中间件层（MySQL/Neo4j/ES）→ 应用层 → 前端。  
`app-mcp-server-chart` 无中间件依赖，独立启动。MinerU 解析路由（mineru-router，端口 **18002**）由独立的 **model-service 部署包** 提供，见 `../model-service/deployment_guide.md`。

## 三、部署前提

1. **Docker / Docker Compose** 已安装并满足版本要求。
2. **GPU 模型服务（model-service 部署包）**：知识库对话依赖的 **LLM(8666) / Embedding(6667) / Reranker(6657)** 与可选的 **MinerU 文档解析(18002)** 均由独立的 model-service 部署包提供（需 GPU 服务器，见 `../model-service/deployment_guide.md`）。部署后在 `/data/GA-kb-chat/kb_config.yaml` 的 `MODEL_PLATFORMS` 中将各 `api_base_url` 指向对应地址。未部署时应用系统仍可启动，但知识库问答/解析功能不可用。

## 四、部署步骤

### 步骤 1：传输部署包

```bash
ssh user@your-server "mkdir -p /data/deploy/GA-app/images"
scp -r GA-app/* user@your-server:/data/deploy/GA-app/          # 脚本 + 配置（含两份 compose）
scp images/*.tar user@your-server:/data/deploy/GA-app/images/    # 9 个对应架构的镜像 tar（ARM64 为 *-arm64.tar）
```

### 步骤 2：执行一键部署

```bash
cd /data/deploy/GA-app
sudo bash import-and-start.sh
```

脚本自动完成（无需再手动复制配置）：

| 步骤 | 操作                                                                  |
|------|---------------------------------------------------------------------|
| 1/5 | 环境检查：**架构识别（选择 compose 文件与 tar 后缀）**/ root / Docker / Compose        |
| 2/5 | 创建 `/data/*` 数据目录 + **自动分发配置文件**（已存在的配置保留不覆盖）+ **分发 Neo4j 插件 jar**（apoc / graph-data-science → `/data/neo4j/plugins/`，每次覆盖更新） |
| 3/5 | 导入 9 个对应架构的 tar 镜像并统一打标签                                            |
| 4/5 | `docker compose up -d`（自动使用对应架构的 compose 文件；若 mid-neo4j 首次创建时崩溃自动重启导致首轮启动失败，脚本会等待其转为 healthy 后自动补启其余服务，**无需二次执行脚本**） |
| 5/5 | 输出服务状态与端口清单                                                         |

### 步骤 3：修改 IP 等相关配置（重要）

部署完成后，如果需要修改服务配置，则修改以下文件，然后重启对应服务：

| 文件                                           | 修改项                                                                           | 重启服务                     |
|----------------------------------------------|-------------------------------------------------------------------------------|--------------------------|
| `/data/GA-frontend-v2/runtime-config.json` | `API_BASE_URL`、`KB_BASE_URL` 中的 IP等                                           | app-GA-frontend-v2     |
| `/data/GA-service-backend/config.yaml`     | `kb_chat.base_url`、`file_processing.service_url`、`langfuse`相关配置等              | app-GA-service-backend |
| `/data/GA-document-processor/config.yaml`  | 如启用 MinerU：`mineru.base_url: http://<服务器IP>:18002`、`llm` 等相关配置                | app-ai-doc-processor     |
| `/data/GA-kb-chat/kb_config.yaml`          | 如启用 MinerU：`ENABLE_MINERU: true`、`MINERU_URL: http://<服务器IP>:18200/api/parse_to_markdown` | app-GA-kb-chat         |

重启对应服务：
```bash
docker compose up -d --force-recreate --no-deps <容器名>
```

### 步骤 4：验证部署

```bash
docker compose ps                                   # 全部应为 running / healthy
curl -u elastic:GA@123456 http://localhost:19200  # Elasticsearch
curl http://localhost:18038                         # 业务后端
curl http://localhost:15174                         # 前端
docker exec -it mid-mysql mysql -u root -p'GA@123456' -e "SHOW DATABASES;"
```

图表 MCP 端点：`http://<服务器IP>:1122/mcp`（Streamable HTTP）。

## 五、统一密码

所有中间件密码统一为 `GA@123456`（MySQL: root ｜ Neo4j: neo4j ｜ ES: elastic）。

> [!WARNING]
> 连接字符串中密码的 `@` 必须编码为 `%40`：  
> `mysql+pymysql://root:GA%40123456@localhost:13306/ai_service?charset=utf8mb4`

## 六、数据目录

```
/data/
├── mysql/  mysql-init/ai_service.sql     # MySQL 数据 + 初始化 SQL（首次启动执行）
├── neo4j/{data,logs,import,plugins}      # Neo4j（data/plugins 已 chmod 777；plugins 内含
│                                         #   apoc.jar + graph-data-science.jar，脚本自动分发）
├── elasticsearch/{data,plugins}          # ES（已 chmod 777）
├── GA-kb-chat/                         # kb_config.yaml + 知识库数据
├── GA-service-backend/                 # 后端配置 config.yaml + skills_repo/ + agent_memory/
├── GA-document-processor/config.yaml   # 文件解析引擎配置
├── GA-frontend-v2/runtime-config.json  # 前端运行时配置
└── GA-mcp/.docker.env                  # 图表 MCP 环境变量
```

> MinerU 的数据目录（`/data/mineru/`）由 model-service 部署包管理，见 `../model-service/deployment_guide.md`。

> **deepagent.db 说明**：后端 DeepAgent 的 SQLite 数据库（WAL 模式），首次部署时脚本自动从包内带入，线上已存在则不覆盖；`-shm`/`-wal` 为运行附属文件，缺失时脚本自动创建空文件占位（bind 挂载目标必须是文件，否则 Docker 会建成同名目录导致不可用）。**备份时需先停止 app-GA-service-backend 容器，三个文件一起拷贝**（仅拷贝 `.db` 可能丢失 WAL 中未合并的最新写入）。`chat_record_files/` 为聊天记录文件目录，由脚本自动创建。

## 七、常用运维命令

```bash
cd /data/deploy/GA-app
# ARM64 服务器请为下列 docker compose 命令追加 -f docker-compose.arm64.yml（下同）

docker compose ps                          # 查看状态
docker compose logs -f <容器名>            # 查看日志
docker compose restart <容器名>            # 重启服务
docker compose down && docker compose up -d   # 重启全部

# 更新某个服务镜像：
docker load -i images/<服务>.tar
docker tag <原始镜像名:标签> <目标镜像名:标签>   # 当需要修改镜像名时
docker compose up -d --force-recreate --no-deps <容器名>
```

## 八、一键卸载

```bash
cd /data/deploy/GA-app
sudo bash uninstall-and-clean.sh
```

| 步骤 | 操作                             | 确认方式 |
|------|--------------------------------|---------|
| 1/5 | 停止并删除所有应用容器                    | 首次统一确认 |
| 2/5 | 删除 9 个导入的镜像                    | 自动执行 |
| 3/5 | 清理 Docker 网络                   | 自动执行 |
| 4/5 | 删除 `/data/*` 数据目录              | **二次确认** ⚠ |
| 5/5 | Docker 系统级深度清理                 | **二次确认** ⚠ |

> 卸载脚本只清理 GA 应用栈；MinerU / Langfuse 请分别执行 `../model-service/` 与 `../langfuse/` 下的 `uninstall-and-clean.sh`。

## 九、常见问题

**Q1: MySQL 密码 / 初始化 SQL 不生效**  
`MYSQL_ROOT_PASSWORD` 和 `ai_service.sql` 仅在 `/data/mysql` 为空的首次初始化时生效。重置：
```bash
docker compose stop mid-mysql && rm -rf /data/mysql/* && docker compose up -d mid-mysql
```

**Q2: ES 连接被拒绝**  
已开启 xpack 安全认证，请求需携带认证：`curl -u elastic:GA@123456 http://localhost:19200`

**Q3: 图表 MCP 渲染的图片打不开**  
`/data/GA-mcp/.docker.env` 中 `VIS_REQUEST_SERVER` 的 IP 必须是客户端可访问的服务器 IP，修改后 `docker compose restart app-mcp-server-chart`。

**Q4: 重新执行部署脚本会覆盖我已修改的配置吗？**  
不会。脚本对已存在的配置文件一律保留，仅在目标缺失时复制；如需更新请参考部署包内的新版配置手动合并。

**Q5: 启用 MinerU 文件解析后不生效**  
解析链路为 **kb-chat → ai-doc-processor(`:18200/api/parse_to_markdown`) → mineru-router(`:18002`)**，MinerU 由独立的 model-service 部署包提供：① 确认 `../model-service/` 已部署且 `curl http://localhost:18002/health` 正常；② 确认 `/data/GA-document-processor/config.yaml` 中 `mineru.base_url` 指向 `http://<服务器IP>:18002`；③ 确认 `/data/GA-kb-chat/kb_config.yaml` 中 `ENABLE_MINERU: true`、`MINERU_URL` 指向 `http://<服务器IP>:18200/api/parse_to_markdown`；④ 依次重启 `app-ai-doc-processor` 与 `app-GA-kb-chat`。

**Q6: kb-chat 启动报 `OpenBLAS ... pthread_create failed: Operation not permitted` / `FileNotFoundError`（multiprocessing manager）**  
根因是宿主机 Docker 的默认 seccomp 配置拦截了线程创建相关系统调用（`clone3`），OpenBLAS 按 CPU 核数批量建线程失败，导致 chatchat 的 Manager 子进程无法启动（随后的 `FileNotFoundError: [Errno 2]` 是 Manager socket 未创建的连锁反应，不是独立故障）。compose 已为 `app-GA-kb-chat` 配置 `security_opt: seccomp:unconfined` 并限制 `OPENBLAS_NUM_THREADS/OMP_NUM_THREADS=4`（向量化由远程 model-service 完成，本地无需大量 BLAS 线程）。若仍复现：① 确认使用的是最新 compose 文件并 `docker compose up -d --force-recreate --no-deps app-GA-kb-chat`；② `docker version` 检查宿主机 Docker 版本，过旧（<20.10.10）建议升级，新版默认 seccomp 配置对 `clone3` 返回 ENOSYS 使 glibc 自动回退，可不再依赖 seccomp:unconfined；③ 检查 `/etc/docker/daemon.json` 是否有自定义 seccomp profile。

**Q7: Neo4j 相关功能报错 / 提示找不到 apoc、gds 存储过程**  
`mid/neo4j` 镜像不自带 APOC 与 Graph Data Science 插件，启动时从 `/plugins`（宿主机 `/data/neo4j/plugins/`）加载。部署脚本会自动把包内 `neo4j/apoc.jar` 与 `neo4j/graph-data-science.jar` 分发过去；如遗漏（手动部署或旧版脚本），补救：
```bash
cp /data/deploy/GA-app/neo4j/*.jar /data/neo4j/plugins/
docker compose up -d --force-recreate --no-deps mid-neo4j
```
注意插件 jar 与镜像版本（`mid/neo4j:2026-05-15`）强绑定，升级镜像时需同步更换配套 jar，勿混用其他来源版本。两份 compose 已为 `mid-neo4j` 配置 `NEO4J_PLUGINS: '["apoc", "graph-data-science"]'`（2025.12+ 镜像内置 apoc/GDS 离线安装包，entrypoint 每次启动会用内置版本覆盖 `/plugins` 下的同名 jar，分发的 jar 仅作兜底），以及过程白名单（`NEO4J_dbms_security_procedures_unrestricted/allowlist: apoc.*,gds.*`）、APOC 文件读写开关（`apoc_import/export_file_enabled`、`apoc_import_file_use__neo4j__config`）与内存配置（`server_memory_heap_max__size: 4G` + `server_memory_pagecache_size: 2G`，**宿主机需为 neo4j 预留 ≥7G 内存，不足请调小这两项**）。另外**首次创建容器时可能出现一次 `apoc.conf (Permission denied)` 崩溃**（entrypoint 以 root 生成配置、neo4j 用户读取失败的时序问题），`restart: unless-stopped` 会自动重启并在第二次成功（日志末尾出现 `Started.` 即正常），不影响数据与密码初始化，无需处理。该崩溃曾导致首轮 `docker compose up -d` 等待 `service_healthy` 失败、前后端未随之启动（需二次执行脚本）；现部署脚本已自动化处理：首轮 `up -d` 失败后，脚本会轮询等待 `mid-neo4j` 转为 healthy（最长 5 分钟），再自动补执行一次 `up -d`（幂等）拉起 kb-chat / service-backend / frontend 等依赖服务，**一次执行脚本即可完成全部部署**。compose 中 mid-neo4j 的 healthcheck `start_period` 也已放宽至 120s 以容纳崩溃重启窗口。如需从镜像层面根治，可在构建 `mid/neo4j` 时加入 `RUN touch /var/lib/neo4j/conf/apoc.conf && chmod a+rw /var/lib/neo4j/conf/apoc.conf`（两种架构各需重新构建并打 tar）。

---

> 大模型服务（Qwen/BGE/LiteLLM 等）、Nginx、其他监控组件（Portainer/Prometheus）不在本部署包范围内，需单独部署；MinerU 见 `../model-service/`，Langfuse 见 `../langfuse/`。
