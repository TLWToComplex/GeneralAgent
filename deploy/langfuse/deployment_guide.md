# Langfuse — Docker 一键部署指南

> **适用环境：** Ubuntu 22.04 LTS（x86_64 / ARM64）｜ Docker 24.0+ / Compose v2  
> **最后更新：** 2026-09-16  
> [Langfuse](https://langfuse.com) 是开源 LLM 工程平台，提供追踪（Tracing）、评测（Evals）、提示词管理（Prompt Management）与指标观测（Metrics）。  
> **本部署完全独立于 GA 主系统**：独立的 compose 栈、独立的网络与数据卷，可单独部署在任意服务器上，互不影响。

---

> [!IMPORTANT]
> **本部署包同时支持 x86_64 与 ARM64（aarch64）两种架构**：部署/卸载脚本通过 `uname -m` 自动识别架构，自动选择 compose 文件（x86 → `docker-compose.yml`，ARM64 → `docker-compose.arm64.yml`，后者每个服务已固定 `platform: linux/arm64`）与镜像 tar（x86 → `*.tar`，ARM64 → `*-arm64.tar`，导入后镜像标签一致），非 x86_64/aarch64 架构直接报错退出。`images/` 中只需放入与目标服务器架构对应的 tar。文档中手动执行的 `docker compose -f docker-compose.yml ...` 命令，在 ARM64 服务器上请将文件名替换为 `docker-compose.arm64.yml`。

## 一、部署包清单

```
langfuse/
├── docker-compose.yml              # Langfuse 服务编排（6 个服务，x86_64）
├── docker-compose.arm64.yml        # 同上，ARM64（platform: linux/arm64）
├── import-and-start.sh             # 一键部署脚本（自动识别架构）
├── uninstall-and-clean.sh          # 一键卸载脚本（自动识别架构）
├── deployment_guide.md             # 本文档
├── .env                            # 首次运行脚本自动生成（随机密钥，请备份）
└── images/                         # 离线镜像 tar（可选，联网环境可不放）
```

## 二、服务与端口一览

| 服务 | 作用 | 镜像 | 宿主机端口 |
|------|------|------|-----------|
| langfuse-web | Web UI 与 API | `docker.io/langfuse/langfuse:3` | **13000**（对外） |
| langfuse-worker | 异步任务（事件摄取、批处理） | `docker.io/langfuse/langfuse-worker:3` | 127.0.0.1:13030 |
| postgres | 元数据存储 | `docker.io/postgres:17` | 127.0.0.1:15432 |
| clickhouse | 追踪数据 / 指标存储 | `docker.io/clickhouse/clickhouse-server:25.12` | 127.0.0.1:18123 / 19000 |
| redis | 队列 / 缓存 | `docker.io/redis:7` | 127.0.0.1:16379 |
| minio | S3 兼容对象存储（事件与媒体文件） | `cgr.dev/chainguard/minio:latest` | **19090**(API) / 127.0.0.1:19091(Console) |

> 除 `langfuse-web`(13000) 与 `minio API`(19090) 外，其余组件均只绑定 `127.0.0.1`，外部无法直连，符合安全最佳实践。防火墙只需放行 13000、19090。

### 离线镜像 tar 清单（放入 `images/`，按服务器架构二选一）

| tar 文件（x86_64 / ARM64） | 导入后镜像名:标签（两架构一致） |
|----------|------------------|
| `postgres.tar` / `postgres-arm64.tar` | `docker.io/postgres:17` |
| `clickhouse.tar` / `clickhouse-arm64.tar` | `docker.io/clickhouse/clickhouse-server:25.12` |
| `redis.tar` / `redis-arm64.tar` | `docker.io/redis:7` |
| `minio.tar` / `minio-arm64.tar` | `cgr.dev/chainguard/minio:latest` |
| `langfuse-web.tar` / `langfuse-web-arm64.tar` | `docker.io/langfuse/langfuse:3` |
| `langfuse-worker.tar` / `langfuse-worker-arm64.tar` | `docker.io/langfuse/langfuse-worker:3` |

在联网机器上导出镜像：

```bash
# x86_64 版
docker pull <镜像名:标签> && docker save -o <tar文件> <镜像名:标签>
# ARM64 版（在任意联网机器上均可执行，注意 --platform 参数）
docker pull --platform linux/arm64 <镜像名:标签> && docker save -o <tar文件-arm64.tar> <镜像名:标签>
```

## 三、部署步骤

### 步骤 1：传输部署包

```bash
ssh user@your-server "mkdir -p /data/deploy/langfuse/images"
scp -r langfuse/* user@your-server:/data/deploy/langfuse/          # 脚本 + compose
scp langfuse/images/*.tar user@your-server:/data/deploy/langfuse/images/   # 离线镜像（如有）
```

### 步骤 2：执行一键部署

```bash
cd /data/deploy/langfuse
sudo bash import-and-start.sh <服务器IP>     # IP 参数可省略，脚本会自动探测
```

脚本自动完成（4 步）：

| 步骤 | 操作 |
|------|------|
| 1/4 | 环境检查：**架构识别（选择 compose 文件与 tar 后缀）**/ docker / compose / 13000 端口占用 / 确定服务器 IP |
| 2/4 | 导入 `images/` 下对应架构的离线镜像并统一打标签（本地已有的镜像自动跳过；缺失的启动时联网拉取） |
| 3/4 | 生成 `.env`：**全部密钥随机化**（NEXTAUTH_SECRET / SALT / ENCRYPTION_KEY / 各数据库与 MinIO 密码），已存在则保留不覆盖 |
| 4/4 | `docker compose up -d` 并轮询 `/api/public/health` 等待就绪（最长 5 分钟） |

### 步骤 3：访问与初始化

1. 浏览器打开 `http://<服务器IP>:13000`
2. 首次使用注册账号，创建 Organization 和 Project
3. 在 Project 设置中创建 API Keys（`Public Key` + `Secret Key`）

> [!TIP]
> 也可以编辑 `.env` 末尾的 `LANGFUSE_INIT_*` 注释段（组织/项目/管理员账号/预置 API Keys），取消注释后 `docker compose -f docker-compose.yml up -d` 重建，即可跳过手动注册。

### 步骤 4：在 ai-service-backend 中接入

编辑 `/data/GA-service-backend/config.yaml`：

```yaml
langfuse:
  enabled: true
  host: "http://<服务器IP>:13000"
  public_key: "<Public Key>"
  secret_key: "<Secret Key>"
```

重启后端：`docker compose restart app-GA-service-backend`，之后即可在 Langfuse Web 中看到 LLM 调用追踪数据。

## 四、.env 配置说明

脚本生成的 `.env` 包含以下关键项（均为随机值，**请妥善备份**）：

| 变量 | 说明 |
|------|------|
| `NEXTAUTH_URL` | 浏览器访问地址，必须是客户端可达的 IP/域名（改 IP 后需同步修改） |
| `NEXTAUTH_SECRET` | Web 会话密钥 |
| `SALT` / `ENCRYPTION_KEY` | 密码加盐 / 数据加密密钥，**丢失后已有加密数据无法恢复** |
| `POSTGRES_PASSWORD` + `DATABASE_URL` | 两者必须保持一致（脚本已同步生成） |
| `CLICKHOUSE_PASSWORD` / `REDIS_AUTH` | ClickHouse / Redis 密码 |
| `MINIO_ROOT_PASSWORD` + `LANGFUSE_S3_*_SECRET_ACCESS_KEY` | MinIO 凭据，多处必须一致（脚本已同步生成） |

修改 `.env` 后执行 `docker compose -f docker-compose.yml up -d` 生效。

> [!WARNING]
> 手动修改 `POSTGRES_PASSWORD` 或 `MINIO_ROOT_PASSWORD` 时，必须同步修改对应的 `DATABASE_URL` / 各 `LANGFUSE_S3_*_SECRET_ACCESS_KEY`，否则服务无法连接存储。

## 五、常用运维命令

```bash
cd /data/deploy/langfuse
CF="docker compose -f docker-compose.yml"

$CF ps                            # 查看状态
$CF logs -f langfuse-web          # 查看日志
$CF stop                          # 停止服务（保留数据）
$CF down                          # 删除容器（数据卷保留）
$CF down -v                       # ⚠ 彻底清理（删除全部数据卷，数据丢失）
$CF pull && $CF up -d             # 升级到最新镜像（联网环境）
```

### 一键卸载

```bash
cd /data/deploy/langfuse
sudo bash uninstall-and-clean.sh
```

| 步骤 | 操作 | 确认方式 |
|------|------|---------|
| 1/5 | 停止并删除所有 Langfuse 容器 | 首次统一确认 |
| 2/5 | 删除 6 个 Langfuse 相关镜像 | 自动执行 |
| 3/5 | 清理 Docker 网络 | 自动执行 |
| 4/5 | 删除数据卷（全部追踪数据）及 `.env`（密钥） | **二次确认** ⚠ |
| 5/5 | Docker 系统级深度清理（作用于整个 Docker，与主系统共用服务器时谨慎选择） | **二次确认** ⚠ |

> 卸载脚本按 compose 项目标签识别资源，**只清理 Langfuse 栈**，不影响 GA 主系统。

## 六、数据持久化

数据保存在 5 个 Docker 命名卷中（默认位于 `/var/lib/docker/volumes/`），升级/重建容器不丢数据：

- `langfuse_postgres_data`
- `langfuse_clickhouse_data` / `langfuse_clickhouse_logs`
- `langfuse_redis_data`
- `langfuse_minio_data`

迁移或备份示例：

```bash
docker run --rm -v langfuse_postgres_data:/data -v $(pwd):/backup alpine \
  tar czf /backup/langfuse_postgres_data.tar.gz -C /data .
```

## 七、常见问题

**Q1: 页面能打开但登录跳转异常 / 一直回到登录页**  
`NEXTAUTH_URL` 与浏览器实际访问地址不一致（如写了 127.0.0.1 却用 IP 访问）。修改 `.env` 中 `NEXTAUTH_URL` 后 `$CF up -d`。

**Q2: 启动后 langfuse-web 反复重启**  
多为 `.env` 中密码与连接串不一致（手动改过 `POSTGRES_PASSWORD` 或 MinIO 密码但未同步 `DATABASE_URL` / `LANGFUSE_S3_*`）。查看日志定位：`$CF logs langfuse-web langfuse-worker`。

**Q3: 离线环境启动时报镜像拉取失败**  
`images/` 中缺少对应 tar。按「离线镜像 tar 清单」补齐后重新执行脚本；脚本对已导入的镜像会自动跳过。

**Q4: 13000 端口被占用**  
脚本会在启动前检测并报错。释放端口，或修改对应架构的 compose 文件（`docker-compose.yml` / `docker-compose.arm64.yml`，建议两份同步改）中 `langfuse-web` 的宿主机端口并同步修改 `.env` 的 `NEXTAUTH_URL`。

**Q5: 忘记管理员密码**  
在 Web 登录页无法重置（未配置 SMTP）时，可删除账号记录重新注册：  
`docker exec -it $(docker ps -qf name=postgres) psql -U postgres -c "DELETE FROM users WHERE email='<邮箱>';"`  
（仅删除该登录账号，追踪数据不受影响；如配置了 `SMTP_CONNECTION_URL` 则走邮件重置。）

**Q6: 与 GA 主系统有依赖吗？**  
没有。Langfuse 栈独立运行、独立网络与数据卷；主系统的部署/卸载脚本不会触碰 Langfuse，反之亦然。仅 ai-service-backend 通过 HTTP(13000) 单向上报追踪数据，Langfuse 不可用不影响主系统功能。

**Q7: ARM64 服务器上如何确认用的是 arm64 镜像？**  
部署脚本第 1 步会输出「系统架构：aarch64 → compose: docker-compose.arm64.yml / 镜像 tar: *-arm64.tar」；也可用 `docker image inspect <镜像名:标签> --format '{{.Os}}/{{.Architecture}}'` 逐个校验（应为 linux/arm64）。注意在 x86 联网机器上制作 arm64 tar 时，`docker pull` 必须带 `--platform linux/arm64`。

**Q8: postgres 报 `could not execute command ".../postgres" -V": Operation not permitted`，或 clickhouse 报 `Illegal instruction (core dumped)`**  
两个不同的问题：

1. **postgres `Operation not permitted`**：宿主机 Docker 版本过旧（<20.10.10），默认 seccomp 策略对 `clone3` 系统调用返回 EPERM，postgres:17 等新版 glibc 镜像 fork 子进程即失败（与 GA-app kb-chat 的 OpenBLAS pthread_create 报错同根因）。两份 compose 已为**全部 6 个服务**添加 `security_opt: seccomp:unconfined`；根治方案是升级宿主机 Docker 到 20.10.10+（建议 24+），升级后可移除该配置。  
   修复后需清掉初始化失败的残留数据卷再启动：
   ```bash
   docker compose down
   docker volume rm langfuse_langfuse_postgres_data   # initdb 半途失败会残留，不清理会报数据目录非空
   docker compose up -d
   ```

2. **clickhouse `Illegal instruction (core dumped)`**：SIGILL 是 **CPU 指令集不匹配**，与 seccomp 无关。按序排查：
   ```bash
   uname -m                                                                  # 宿主机架构
   docker image inspect docker.io/clickhouse/clickhouse-server:25.12 --format '{{.Os}}/{{.Architecture}}'
   grep -m1 'model name' /proc/cpuinfo                                       # x86 看 CPU 型号；显示 QEMU/Virtual CPU 说明是虚拟机
   grep -m1 -o 'sse4_2\|avx2' /proc/cpuinfo                                  # ClickHouse 至少需要 sse4_2
   ```
   - **镜像架构与宿主机不一致**（如 ARM 服务器装了 x86 tar，经 qemu 模拟运行必现 SIGILL）→ 重新制作/导入正确架构的 `clickhouse[-arm64].tar`（见 Q7）；
   - **虚拟机 CPU 型号为模拟型**（KVM/Proxmox 默认 qemu64、VMware 默认 EVC 等不透传指令集）→ 将虚拟机 CPU 类型改为 **host（透传）** 后重启虚拟机（Proxmox：VM → Hardware → Processor → Type=host）；
   - **物理 CPU 过旧**（不支持 SSE4.2，2008 年前的 x86）→ 无法运行官方 ClickHouse 镜像，需更换部署机器；
   - **ARM 服务器指令集不足**：官方 arm64 镜像按 Graviton 3/4（Neoverse V1/V2）级基线编译，要求 SVE/SVE2 等扩展。用 `grep -m1 -o 'atomics\|sve2\|sve\|i8mm\|bf16\|lrcpc' /proc/cpuinfo` 核对：若缺 `atomics`（LSE，ARMv8.1+，如飞腾 FT-2000+ 等 ARMv8.0 CPU），或**有 `atomics` 但缺 `sve`/`sve2`（如华为 Kunpeng-920，ARMv8.2 但未实现 SVE）**，均会 SIGILL。处理：换到支持 SVE 的 ARM 服务器（AWS Graviton 3/4 等）；或降级到 arm64 基线更低的 ClickHouse 版本（逐个用 `docker run --rm --entrypoint /usr/bin/clickhouse <镜像>:<版本> --version` 试跑确认，并对照 langfuse 版本下限）；或源码以 `-march=armv8.2-a`（去掉 SVE）自编译。

## 八、参考资料

- Langfuse 官方文档：<https://langfuse.com/docs>
- Langfuse 自托管指南：<https://langfuse.com/self-hosting>
- Langfuse 仓库：<https://github.com/langfuse/langfuse>
