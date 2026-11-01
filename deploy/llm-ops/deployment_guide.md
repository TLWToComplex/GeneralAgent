# LLM-OPS（大模型集 / 统一网关）— Docker 一键部署指南

> **适用环境：** Ubuntu 22.04 LTS（x86_64 / ARM64）｜ Docker 29.1.0+ / Compose v2.40.0+  
> **最后更新：** 2026-09-21  
> 本包为整体部署的独立部分之一（**GA-app / model-service / langfuse / llm-ops**），提供 **统一网关（LiteLLM）+ 监控（Prometheus）+ 后台管理 + 前端** 的大模型纳管与运维能力。一个 compose 编排 **6 个服务**（自带 MySQL + PostgreSQL），**完全独立自包含，不依赖 GA-app**，可单独部署/卸载，互不影响。

---

> [!IMPORTANT]
> **本部署包同时支持 x86_64 与 ARM64（aarch64）两种架构**：部署/卸载脚本通过 `uname -m` 自动识别架构，自动选择 compose 文件（x86 → `docker-compose.yml`，ARM64 → `docker-compose.arm64.yml`，后者每个服务已固定 `platform: linux/arm64`）与镜像 tar（x86 → `images/*.tar`，ARM64 → `images/*-arm64.tar`），非 x86_64/aarch64 架构直接报错退出。`images/` 中只需放入与目标服务器架构对应的 tar。**`llm-app*.tar` 一个包内含 llm-backend + llm-frontend 两个镜像**，包内标签为 `:amd64` / `:arm64`，脚本导入后自动重打为 `:latest`（与 compose 引用一致）。

> [!IMPORTANT]
> **部署方式（2026-09-21 新版）**：6 个服务运行在自定义 **bridge 网络 `llm-net`** 上，服务间通过 **容器名 DNS** 互联（`config/` 中直接引用 `llm-mysql` / `postgres` / `llm-litellm` / `llm-prometheus` / `llm-backend`），容器内使用各自的标准端口（MySQL 3306、PostgreSQL 15432、LiteLLM 4000、Prometheus 9090、Backend 8038、Frontend 5173），对外映射到宿主机端口统一以 **2** 开头（23306 / 25432 / 24000 / 29090 / 28038 / 25173）。配置文件全部位于包内 `config/`，由 compose **就地挂载**，所有服务间地址均使用容器名，**部署后无需按服务器 IP 修改任何配置**。数据与日志位于包内 `./data`、`./logs`，整目录拷贝即完成迁移。卸载脚本会自动兜底清理历史旧版（曾用 `llm-ops-` 前缀 / host 网络时期）的容器、镜像、网络与 `/data/llm-ops-*` 目录。

## 一、部署包清单

```
llm-ops/
├── docker-compose.yml              # 6 个服务编排（x86_64，bridge 网络 llm-net）
├── docker-compose.arm64.yml        # 同上，ARM64（platform: linux/arm64）
├── import-and-start.sh             # 一键部署脚本（自动识别架构）
├── uninstall-and-clean.sh          # 一键卸载脚本（自动识别架构）
├── deployment_guide.md             # 本文档
├── config/                         # 全部配置（compose 就地挂载，修改后重启对应服务生效）
│   ├── config.yaml                 #   后台管理配置（端口/数据库/网关/监控地址，用容器名）
│   ├── config.js                   #   前端运行时配置（标题 / API 前缀 / SSO 开关）
│   ├── litellm.yaml                #   LiteLLM 网关配置（master_key / database_url / 路由策略）
│   ├── nginx/default.conf          #   前端 Nginx（listen 5173，/admin-api 反代 llm-backend:8038）
│   └── prometheus/                 #   prometheus.yml（抓取 llm-litellm:4000）+ litellm_alerts.yml（告警规则）
├── sql/init.sql                    # MySQL 首次初始化（建 ai_service + chat_history 库表）
├── images/                         # 镜像 tar（自行放入，按架构选择）
├── data/                           # 运行数据（脚本自动创建：mysql / pgdata）
└── logs/                           # 运行日志（脚本自动创建：mysql / postgres / backend / nginx）
```

## 二、服务、镜像与端口

| tar 文件（x86 / ARM64） | 镜像名:标签 | 服务名（容器名） | 端口（宿主机:容器内） |
|------------------------|------------|------------------|---------|
| `llm-app.tar` / `llm-app-arm64.tar`（含双镜像） | `llm-backend:latest` | backend（llm-backend） | **28038**:8038 |
| （同上） | `llm-frontend:latest` | frontend（llm-frontend） | **25173**:5173 |
| `mysql.tar` / `mysql-arm64.tar` | `mysql:8.3` | mysql（llm-mysql） | **23306**:3306 |
| `postgres.tar` / `postgres-arm64.tar` | `postgres:16` | postgres（llm-postgres） | **25432**:15432 |
| `litellm.tar` / `litellm-arm64.tar` | `docker.litellm.ai/berriai/litellm:main-latest` | litellm（llm-litellm） | **24000**:4000 |
| `prometheus.tar` / `prometheus-arm64.tar` | `prom/prometheus:latest` | prometheus（llm-prometheus） | **29090**:9090 |

> **网络说明**：全部服务加入自定义 bridge 网络 `llm-net`，容器间用容器名互访（如 backend 连 `llm-mysql:3306`、litellm 连 `postgres:15432`）；`restart` 统一为 `unless-stopped`。  
> **命名约定**：compose 服务名为 `mysql/postgres/litellm/prometheus/backend/frontend`，容器名统一加 `llm-` 前缀（`llm-mysql` 等，`config/` 中的 DNS 地址即引用这些容器名/服务名）。  
> **端口映射**：compose 将各服务端口映射到宿主机（左侧为宿主机端口、右侧为容器内端口），对外端口统一以 **2** 开头；如需改宿主机端口只改 compose 映射左侧即可（见 Q4）。  
> `llm-app*.tar` 导入后的包内标签为 `llm-backend:amd64/arm64` 与 `llm-frontend:amd64/arm64`，脚本自动重打为 `:latest`。  
> 第三方中间件（mysql/postgres/litellm/prometheus）如服务器本地已存在同名镜像，脚本自动跳过导入。

启动顺序由 `depends_on` + `healthcheck` 控制：mysql(healthy) → backend → frontend；postgres(healthy) → litellm；prometheus 独立启动。

## 三、部署前提

1. **Docker / Docker Compose** 已安装并满足版本要求。
2. **无外部模块依赖**：本栈自带 MySQL（后台库）与 PostgreSQL（网关库），与 GA-app / model-service / langfuse 完全独立，可同机共存（端口不冲突即可）。
3. **6 个端口空闲**：23306 / 25432 / 24000 / 29090 / 28038 / 25173（脚本启动前自动检测；对外端口统一以 2 开头，已避开常见默认端口冲突）。
4. `images/` 中已放入与服务器架构对应的 5 个镜像 tar。

## 四、部署步骤

### 步骤 1：传输部署包

```bash
ssh user@your-server "mkdir -p /data/deploy/llm-ops/images"
scp -r llm-ops/* user@your-server:/data/deploy/llm-ops/                  # 脚本 + 配置 + sql
scp llm-ops/images/*.tar user@your-server:/data/deploy/llm-ops/images/   # 5 个镜像 tar（按架构）
```

### 步骤 2：执行一键部署

```bash
cd /data/deploy/llm-ops
sudo bash import-and-start.sh
```

脚本自动完成：

| 步骤 | 操作 |
|------|------|
| 1/5 | 环境检查：**架构识别（选择 compose 文件与 tar 后缀）**/ root / Docker / Compose / 端口（23306,25432,24000,29090,28038,25173）占用 |
| 2/5 | 创建包内 `data/{mysql,pgdata}` 与 `logs/{mysql,postgres,backend,nginx}` 运行目录，并对 `logs/postgres`、`logs/mysql` 执行 `chmod 777`（容器内以非 root 用户写日志，见 Q9；配置随包就地挂载，无需分发） |
| 3/5 | 导入 5 个对应架构的 tar；`llm-app*.tar` 双镜像单独处理并重打 `:latest` 标签 |
| 4/5 | `docker compose up -d`（自动使用对应架构的 compose 文件，启动 6 个服务） |
| 5/5 | 输出服务状态 + 健康探测（litellm 首次启动需初始化数据库，最长等待 3 分钟） |

### 步骤 3：验证部署

```bash
cd /data/deploy/llm-ops
docker compose -f docker-compose.yml ps          # ARM64 服务器改用 docker-compose.arm64.yml，全部应为 running/healthy
curl http://localhost:24000/health/liveliness    # LiteLLM 网关
curl http://localhost:29090/-/healthy            # Prometheus
curl http://localhost:28038                      # 后台管理 API
curl http://localhost:25173                      # 前端
```

访问入口：

- 前端控制台：`http://<服务器IP>:25173`（默认账号 **admin / 123456**）
- 后台 API：`http://<服务器IP>:28038`
- LiteLLM 网关：`http://<服务器IP>:24000`（Master Key：`sk-master-1234`）
- Prometheus：`http://<服务器IP>:29090`

> 所有服务间地址均使用容器名（bridge 网络内部 DNS），**无需修改任何配置即可直接使用**；仅当需要对接 SSO 或修改前端标题时编辑 `config/config.js`。

## 五、配置文件说明（config/ 就地挂载）

修改后重启对应服务生效：`docker compose -f <compose文件> restart <服务名>`（服务名如 `backend`、`litellm`）。

| 文件 | 作用 | 关键项 |
|------|------|--------|
| `config/config.yaml` | 后台管理 | `server.port`(8038)、`database`/`user_database`(`llm-mysql:3306`，库 ai_service/chat_history)、`gateway.base_url`(`llm-litellm:4000`)、`monitor.base_url`(`llm-prometheus:9090`)、`postgres`(`postgres:15432`)、`sso.url`(LOCAL_NO_AUTHZ) |
| `config/config.js` | 前端运行时配置 | 标题、`VITE_API_URL=/admin-api`、SSO 开关 |
| `config/litellm.yaml` | LiteLLM 网关 | `master_key`、`database_url`(`postgres:15432`)、路由/健康检查/日志回调策略 |
| `config/nginx/default.conf` | 前端 Nginx | `listen 5173`、SPA fallback、`/admin-api` 反代 `llm-backend:8038` |
| `config/prometheus/prometheus.yml` | 抓取配置 | 目标 `llm-litellm:4000` |
| `config/prometheus/litellm_alerts.yml` | 告警规则 | LiteLLM 告警阈值 |
| `sql/init.sql` | MySQL 首次初始化 | 建 `ai_service` + `chat_history` 库及表（仅 data/mysql 为空时执行一次） |

## 六、统一凭据

| 项 | 值 |
|----|----|
| 前端登录 | `admin / 123456` |
| LiteLLM Master Key | `sk-master-1234` |
| MySQL（后台库） | `root / 123456`（库 `ai_service` + `chat_history`，宿主机端口 23306） |
| PostgreSQL（网关库） | `admin / 1qaz2wsx3edc`（库 `litellm`，宿主机端口 25432） |

> 上述凭据同时出现在两份 compose 文件、`config/config.yaml`、`config/litellm.yaml` 中，如需修改请多处同步。

## 七、数据与日志目录

```
llm-ops/
├── data/
│   ├── mysql/          # MySQL 数据（首次启动由 init.sql 自动初始化）
│   └── pgdata/         # PostgreSQL 数据（首次启动自动初始化）
└── logs/
    ├── mysql/          # MySQL 日志
    ├── postgres/       # PostgreSQL 日志（logging_collector，需 chmod 777，见 Q9）
    ├── backend/        # 后台管理日志（backend.log）
    └── nginx/          # 前端 Nginx 访问/错误日志
```

数据全部位于**包内**，备份或迁移时整目录拷贝即可；卸载脚本第 4 步可选择性删除（默认保留）。

## 八、常用运维命令

```bash
cd /data/deploy/llm-ops
# ARM64 服务器请为下列 docker compose 命令追加 -f docker-compose.arm64.yml（下同）

docker compose ps                          # 查看状态
docker compose logs -f <服务名>            # 查看日志（服务名如 litellm / backend / mysql）
docker compose restart <服务名>            # 重启服务
docker compose down && docker compose up -d   # 重启全部

# 更新应用镜像（llm-app 双镜像示例，x86 为 :amd64，ARM64 为 :arm64）：
docker load -i images/llm-app.tar
docker tag llm-backend:amd64  llm-backend:latest
docker tag llm-frontend:amd64 llm-frontend:latest
docker compose up -d --force-recreate --no-deps backend frontend
```

## 九、一键卸载

```bash
cd /data/deploy/llm-ops
sudo bash uninstall-and-clean.sh
```

| 步骤 | 操作 | 确认方式 |
|------|------|---------|
| 1/5 | 停止并删除 6 个容器（含旧版 `llm-ops-*` 容器名兜底清理） | 首次统一确认 |
| 2/5 | 删除相关镜像（含 `:amd64`/`:arm64` 标签、旧版 aiwu3-frontend / ai-service-backend 与无标签镜像） | 自动执行 |
| 3/5 | 清理 Docker 网络（bridge 网络 `llm-net`，及旧版 `gateway-net` 等残留） | 自动执行 |
| 4/5 | 删除包内 `data/`（MySQL + PostgreSQL 数据）与 `logs/`，及旧版 `/data/llm-ops-*` 目录 | **二次确认** ⚠ |
| 5/5 | Docker 系统级深度清理 | **二次确认** ⚠ |

> 卸载脚本只清理 LLM-OPS 栈，不影响 GA-app / model-service / langfuse；其他模块请分别执行各自目录下的 `uninstall-and-clean.sh`。

## 十、常见问题

**Q1: litellm 启动后连不上数据库 / 反复重启**  
确认 postgres 容器（llm-postgres）健康（`docker compose ps`），且 compose 中 `DATABASE_URL`、`config/litellm.yaml` 的 `database_url` 与 postgres 环境变量一致（默认 `postgresql://admin:1qaz2wsx3edc@postgres:15432/litellm`，`postgres` 为 bridge 网络内服务名）。首次启动 litellm 需初始化数据库表，最长约 3 分钟，部署脚本已自动等待。

**Q2: Prometheus 无网关指标**  
`config/prometheus/prometheus.yml` 抓取目标为 `llm-litellm:4000`（bridge 网络内容器名直连）；litellm 需开启 `LITELLM_PROMETHEUS=True`（compose 已设置）且 `config/litellm.yaml` 中 callbacks 含 `prometheus`（已配置）。

**Q3: 后台登录失败 / backend 连不上 MySQL**  
确认 mysql 容器（llm-mysql）健康；`config/config.yaml` 中 `database.url` / `user_database.url` 指向 `llm-mysql:3306`（root/123456）。`data/mysql` 为空时首次启动会执行 `sql/init.sql` 自动建库建表；如曾以其他密码初始化过 MySQL 数据目录，需保持一致或清空 `data/mysql` 重新初始化。

**Q4: 如何修改服务端口？**  
本栈为 bridge 网络，端口分两层，按需求选择：

- **只改宿主机对外端口**（推荐，不影响任何配置）：只需改两份 compose 中对应服务 `ports` 映射的**左侧**（宿主机侧），例如把前端由 25173 改到 25174 → `"25174:5173"`。容器内端口与 `config/` 中的容器名地址都不变。改完 `docker compose -f <文件> up -d` 重建对应服务。
- **改容器内端口**（会牵动配置）：需同步修改该服务的容器内监听端口 + `config/` 中引用它的地址 + 两份 compose 的映射右侧与 healthcheck：

| 服务（容器内端口） | 改内部端口需同步的位置 |
|------|-------------|
| mysql (3306) | compose：映射右侧 + healthcheck；`config/config.yaml`：`database.url` / `user_database.url` 中的 `:3306` |
| postgres (15432) | compose：`PGPORT` + 映射右侧 + healthcheck + litellm `DATABASE_URL`；`config/litellm.yaml`：`database_url`；`config/config.yaml`：`postgres.port` |
| litellm (4000) | compose：映射右侧 + litellm `command --port`（如需）；`config/config.yaml`：`gateway.base_url`；`config/prometheus/prometheus.yml`：抓取目标 |
| prometheus (9090) | compose：映射右侧 + `command --web.listen-address`（如需）；`config/config.yaml`：`monitor.base_url` |
| backend (8038) | compose：映射右侧；`config/config.yaml`：`server.port`；`config/nginx/default.conf`：`proxy_pass` |
| frontend (5173) | compose：映射右侧；`config/nginx/default.conf`：`listen` |

若修改了对外端口，同时更新 `import-and-start.sh` 中的 `SERVICE_PORTS` 端口检测列表。

**Q5: 端口被占用**  
脚本启动前会检测 23306/25432/24000/29090/28038/25173，被其他进程占用即报错退出。对外端口统一以 2 开头，已避开 MySQL(3306)/Prometheus(9090) 等常见默认端口；若仍被占用（如同机其他服务恰好用了 2 开头端口），释放端口，或按 Q4「只改宿主机对外端口」把 compose 映射左侧改成空闲端口（如 `"13306:3306"`）后重试。

**Q6: 前端页面能打开，但登录/接口报错**  
前端通过 Nginx `/admin-api` 反代 `llm-backend:8038`，确认 backend 容器运行中（`docker compose ps`）、`logs/backend/backend.log` 无报错；backend 依赖 MySQL 健康后才启动。

**Q7: 重新执行部署脚本会覆盖我已修改的配置/数据吗？**  
不会。配置随包就地挂载，脚本不改动 `config/` 与 `sql/` 内容；`data/` 已有数据时 MySQL/PostgreSQL 不会重新初始化；镜像本地已存在时自动跳过导入。

**Q8: ARM64 镜像 tar 如何获取？**  
第三方镜像可在有网机器上执行 `docker pull --platform linux/arm64 <镜像>` 后 `docker save` 导出为 `*-arm64.tar`；自研 `llm-app-arm64.tar`（内含 `llm-backend:arm64` + `llm-frontend:arm64`）需用 `docker buildx build --platform linux/arm64` 构建导出。若 `docker save` 报 `content digest ... not found`，为 containerd 镜像存储的多架构问题，可加 `--platform linux/arm64` 参数或用 buildx `--output type=docker,dest=xxx.tar` 方式导出。

**Q9: postgres 反复重启，日志报 `could not open log file "/var/log/postgresql/postgresql-....log": Permission denied`**  
postgres 开启了 `logging_collector=on` 并把宿主机 `./logs/postgres` 挂到容器 `/var/log/postgresql`。postgres 镜像内以 **uid 999（postgres 用户）** 运行，而宿主机目录由部署脚本以 root 创建（755），postgres 用户对该目录无写权限，导致日志文件打不开、进程无法启动并被 `restart: unless-stopped` 反复拉起。**新版部署脚本已在步骤 2/5 自动 `chmod 777 logs/postgres logs/mysql`**，全新部署不会遇到；旧部署或手动部署补救：
```bash
cd /data/deploy/llm-ops
chmod 777 logs/postgres logs/mysql
rm -rf data/pgdata/*        # 首次初始化因日志失败被中断，密码/库未建成，需清空重来
docker compose -f docker-compose.arm64.yml up -d --force-recreate --no-deps postgres
docker logs -f llm-postgres   # 等到 "database system is ready to accept connections" 且无 Permission denied
# postgres 起来后重建依赖它的 litellm：
docker compose -f docker-compose.arm64.yml up -d --force-recreate --no-deps litellm
```
> 注意：若只 `chmod` 不清空 `data/pgdata`，因首次 `initdb` 中途失败，`admin` 密码与 `litellm` 库并未真正创建（日志中 `Skipping initialization` 即表示跳过了建库建密码步骤），litellm 仍会连不上，务必清空 pgdata 让其重新初始化。

**Q10: 从旧版（`llm-ops-` 前缀 / host 网络）升级到本版要注意什么？**  
本版改为 bridge 网络 + 容器名 DNS，宿主机对外端口与旧版一致（仍以 2 开头：23306 / 25432 / 24000 / 29090 / 28038 / 25173，仅前端由旧的 25174 调整为 25173）。升级步骤：① 先 `sudo bash uninstall-and-clean.sh` 卸载旧栈（**第 4 步删除数据目录时选 N**，以保留 `data/mysql`、`data/pgdata`）；② 用新版部署包覆盖，重新执行 `import-and-start.sh`。因数据目录仍在包内且格式不变，MySQL/PostgreSQL 数据可平滑沿用；外部系统/防火墙按旧端口对接时仅需注意前端端口 25174→25173。

**Q11: postgres 反复重启，日志报 `popen failure: Operation not permitted` / `initdb: error: program "postgres" is needed by initdb but was not found...`**  
与 GA-app kb-chat（Q6 同类）、langfuse postgres 同根因：**宿主机 Docker 版本过旧（<20.10.10）**，默认 seccomp 策略对 `clone3` 系统调用返回 EPERM，postgres:16（Debian bookworm，新版 glibc）在 initdb 阶段派生 `postgres --single` 子进程被拦截 → `popen` 失败 → initdb 误报"找不到 postgres 程序"（并非镜像缺文件）。两份 compose 已为**全部 6 个服务**添加 `security_opt: seccomp:unconfined`；根治方案是升级宿主机 Docker 到 20.10.10+（建议 24+），新版默认 seccomp 对 `clone3` 返回 ENOSYS 使 glibc 自动回退，升级后可移除该配置。  
修复后需清掉初始化失败的残留数据再启动（半途失败的 pgdata 会导致后续 `Skipping initialization` 或校验错误）：
```bash
cd /data/deploy/llm-ops
docker compose -f docker-compose.arm64.yml down          # x86 用 docker-compose.yml
rm -rf data/pgdata/* data/mysql/*                        # mysql 若同样失败过也一并清理
docker compose -f docker-compose.arm64.yml up -d
docker logs -f llm-postgres                              # 应完成 initdb 并 "ready to accept connections"
```
> 排查确认：`docker version` 查看宿主机版本；`grep -m1 Seccomp /proc/self/status` 一般为 2（启用过滤）。若升级 Docker 不方便，保留 `seccomp:unconfined` 即可（仅放宽本栈容器的系统调用过滤，内网部署风险可控）。
