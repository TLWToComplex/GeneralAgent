# 后台管理

Ai-service 后台管理服务
## 环境

- Python: 3.10.0
- MySql: 8.3.0 （版本 >= 5.7 就行）



## 运行

1. 安装mysql （推荐docker安装）
2. 运行仓库中的sql文件夹下的create table的脚本
3. 安装包`pip install -r requirements.txt`
4. 安装 Playwright Chromium 浏览器：`playwright install --with-deps chromium`
5. 启动`admin_server.py` 注册用户
6. 测试功能


### 文件解析服务说明

**重要提示：**普通模型对话和智能体对话中的文件解析功能已经抽离，需要使用文档解析功能需要单独启动文件解析服务。

- 文件解析服务配置地址在 `config.yaml` 的 `file_processing.service_url` 中
- 请确保文件解析服务已独立部署并正常运行
- 在 `config.yaml` 中正确配置文件解析服务的访问地址


##  打包并部署ai-service-backend



### 1.创建Dockerfile文件

#### Dockerfile：

```shell
# 基于 Python 3.11.8 镜像构建
FROM python:3.11.8

# 设置工作目录
WORKDIR /code

# 复制项目文件到容器中
COPY . /code

# 安装 Python 依赖项
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 暴露容器端口
EXPOSE 8038

# 启动应用
CMD ["python", "/code/main.py"]
```



### 2.打包ai-service-backend镜像

```shell
#确保Dockerfile文件在ai-service-backend/Dockerfile的位置，切换到ai-service-backend下打包
docker build -t ai-service-backend:<yyyy-mm-dd> .
```

（打包中如果遇到报错Read timed out,就多尝试命令几次）

```shell
# 用于在其他服务器上部署
docker save -o ai-service-backend.tar ai-service-backend:<yyyy-mm-dd>
```

### 3.部署

将准备好的ai-service-backend.tar

1.加载ai-service-backend镜像

```shell
docker load -i ai-service-backend.tar
```

2.输入启动命令：
**前置条件：**
- 确保 Docker socket 挂载可用（用于创建技能执行沙盒）
- 确保当前目录下存在 `config.yaml` 配置文件，**Docker 启动时必须配置 `deepagent.skills.host_path` 为宿主机上 `skills_repo` 的绝对路径**（沙盒容器启动时需要此路径进行挂载）
- 确保当前目录下存在 `skills_repo` 文件夹，并包含所需的技能模块（可从项目代码的 `skills_repo/` 目录复制）
- **若启用 deepagent 记忆功能**（`deepagent.memory.enabled: true`，默认开启），需要在宿主机准备记忆根目录（如 Linux `/home/ai-service-backend/agent_memory`、Windows `D:/agent_memory`）。**记忆没有 fallback 复制机制**，不挂载会导致跨对话记忆丢失。挂载需同时满足两个角色（宿主机视角 `host_path` + 主容器视角 `container_path`），详见下文「Deepagent 记忆挂载」一节

**Linux/Mac 系统：**
```bash
docker run -d \
  --name ai-service-backend \
  -p 8038:8038 \
  -v /home/ai-service-backend/config.yaml:/code/config.yaml \
  -v /home/ai-service-backend/skills_repo:/code/skills_repo \
  -v /home/ai-service-backend/agent_memory:/code/agent_memory:rw \
  -v /home/ai-service-backend/chat_record_files:/code/chat_record_files \
  -v /home/ai-service-backend/deepagent.db:/code/deepagent.db \
  -v /home/ai-service-backend/deepagent.db-shm:/code/deepagent.db-shm \
  -v /home/ai-service-backend/deepagent.db-wal:/code/deepagent.db-wal \
  -v /var/run/docker.sock:/var/run/docker.sock \
  --add-host host.docker.internal:host-gateway \
  --restart unless-stopped \
  ai-service-backend:<yyyy-mm-dd>
```

**Windows 完整配置（支持技能沙盒）：**
**PowerShell：**
```powershell
docker run -d `
  --name ai-service-backend `
  -p 8038:8038 `
  -v D:/config.yaml:/code/config.yaml `
  -v D:/skills_repo:/code/skills_repo `
  -v D:/agent_memory:/code/agent_memory:rw `
  -v D:/chat_record_files:/code/chat_record_files `
  -v D:/deepagent.db:/code/deepagent.db `
  -v D:/deepagent.db-shm:/code/deepagent.db-shm `
  -v D:/deepagent.db-wal:/code/deepagent.db-wal `
  -v //var/run/docker.sock:/var/run/docker.sock `
  --add-host host.docker.internal:host-gateway `
  --restart unless-stopped `
  ai-service-backend:<yyyy-mm-dd>

```
**CMD：**
```CMD
docker run -d ^
  --name ai-service-backend ^
  -p 8038:8038 ^
  -v D:/config.yaml:/code/config.yaml ^
  -v D:/skills_repo:/code/skills_repo ^
  -v D:/agent_memory:/code/agent_memory:rw ^
  -v D:/chat_record_files:/code/chat_record_files ^
  -v D:/deepagent.db:/code/deepagent.db ^
  -v D:/deepagent.db-shm:/code/deepagent.db-shm ^
  -v D:/deepagent.db-wal:/code/deepagent.db-wal ^
  -v //var/run/docker.sock:/var/run/docker.sock ^
  --add-host host.docker.internal:host-gateway ^
  --restart unless-stopped ^
  ai-service-backend:<yyyy-mm-dd>
```
**查看日志：**
```shell
docker logs -f ai-service-backend
```

**停止服务：**
```shell
docker stop ai-service-backend
docker rm ai-service-backend
```

**重启服务：**
```shell
docker restart ai-service-backend
```

**注意：**

- Windows Docker Desktop 版本过低可能导致沙盒无法创建（如 24.x 版本），报错示例：
  ```shell
  创建沙盒失败: 500 Server Error ... (“invalid volume specification: 'C:\repo\kb_data\skills_repo:/workspace/skills_repo:rw'”)
  ```

  **升级Windows Docker Desktop 后问题解决的原因：**

  1. **Docker API 与引擎升级**
     - `/v1.43` 对应 Docker 24.0（2023 年发布）
     - `/v1.54` 对应 Docker 27.x 及以上
     - 新版本优化了 Windows 环境下的路径解析和容错能力

  2. **自动路径转换优化**
     - 旧版报错：`C:\repo\kb_data\skills_repo`（反斜杠）
     - 新版成功：`C:/repo/kb_data/skills_repo`（正斜杠）
     - 新版 Docker Desktop 能自动将 Windows 路径转换为 POSIX 格式

  3. **WSL 2 集成改进**
     - 较新的 WSL 与 Docker Desktop 配合时，改进了跨操作系统文件共享挂载机制

  **推荐版本（截至 2026-04-19）：**
  ```shell
  # WSL 版本
  WSL 版本: 2.6.3.0
  内核版本: 6.6.87.2-1
  WSLg 版本: 1.0.71

  # Docker 版本
  Docker version 29.4.0, build 9d7ad9f
  ```

  升级后沙盒可正常创建。

- `-v $(pwd)/skills_repo:/code/skills_repo`：挂载技能仓库目录到主服务容器内路径
- `config.yaml` 中**必须配置** `deepagent.skills.host_path` 为宿主机上 `skills_repo` 的绝对路径（如 `/home/user/skills_repo`），沙盒容器启动时直接挂载此路径；也可通过环境变量 `-e HOST_SKILLS_PATH=/host/skills_repo` 指定（优先级高于配置文件）
- `-v /var/run/docker.sock:/var/run/docker.sock`：挂载 Docker socket，允许容器内创建子容器（技能执行沙盒）
- `--add-host host.docker.internal:host-gateway`：配置容器内访问宿主机服务
- `config.yaml` 中 `deepagent.sandbox_download.host` 用于配置浏览器下载沙盒文件时访问的主机地址，Docker 部署时配 `localhost` 或宿主机IP，本地启动时配 `localhost`
- `-v <宿主机记忆目录>:<容器内目录>:rw` 与对应的 `-e DEEPAGENT_MEMORY_HOST_PATH` / `-e DEEPAGENT_MEMORY_CONTAINER_PATH`：启用 deepagent 记忆功能时必加（详见下文「Deepagent 记忆挂载」一节）



### Deepagent 记忆挂载

启用 deepagent 记忆功能（仅类型为 `deepagent` 的智能体生效，其它类型无影响）时，沙盒容器需要挂载宿主机的记忆目录，否则记忆只存在于沙盒子容器内，**容器销毁即丢失**，跨对话记忆与 per-user 隔离都无法持久化。注意：与 skills_repo 不同，记忆**没有 fallback 复制机制**。

#### 核心设计：host_path 与 container_path 拆分为两个角色

记忆路径承担两个不同角色，由两个独立配置项分别表达：

| 配置项           | 角色                                                           | 由谁解释                  |
| ---------------- | -------------------------------------------------------------- | ------------------------- |
| `host_path`      | 沙盒子容器 `-v` 挂载的**源路径**                               | **宿主机** Docker daemon  |
| `container_path` | 主服务容器内种子写入与 `/aiMemory/*` 管理接口读写的根目录      | **主服务容器内** Python   |
| `sandbox_path`   | 沙盒容器内的挂载点（agent 在沙盒里看到的记忆路径）             | 沙盒容器                  |

为什么要拆？沙盒是宿主机 Docker daemon 创建的兄弟容器，挂载源只能用宿主机视角的绝对路径（Windows 上像 `D:/agent_memory`）；而主容器内是 Linux 文件系统，需要用容器内绝对路径（如 `/code/agent_memory`）写文件。Linux 部署时两者可以是同一字符串，Windows 部署时必须不同。

#### 配置项汇总（`config.yaml` 的 `deepagent.memory`）

| 配置项           | 说明                                                         | 对应环境变量                       | 默认值                                          |
| ---------------- | ------------------------------------------------------------ | ---------------------------------- | ----------------------------------------------- |
| `enabled`        | 记忆总开关                                                   | `DEEPAGENT_MEMORY_ENABLED`         | `true`                                          |
| `host_path`      | 宿主机记忆根目录（沙盒子容器 `-v` 挂载源）                   | `DEEPAGENT_MEMORY_HOST_PATH`       | `D:/agent_memory`                               |
| `container_path` | 主服务容器内的记忆目录（种子写入 / 管理接口读写）      | `DEEPAGENT_MEMORY_CONTAINER_PATH`  | `/code/agent_memory`                            |
| `sandbox_path`   | 沙盒容器内的记忆挂载点                                       | `DEEPAGENT_MEMORY_SANDBOX_PATH`    | `/workspace/agent_memory`                       |
| `files`          | 记忆文件清单                                                 | `DEEPAGENT_MEMORY_FILES`           | `AGENTS.md` / `preferences.md` / `knowledge.md` |

环境变量优先级高于 `config.yaml`。

#### Linux/Mac

宿主机目录是 `/home/ai-service-backend/agent_memory`，希望主容器内规整地挂到 `/code/agent_memory`。需在`config.yaml`文件中配置对应的 memory.host_path 和 memory.container_path, 也可通过环境变量实现：

```bash
-v /home/ai-service-backend/agent_memory:/code/agent_memory:rw \
-e DEEPAGENT_MEMORY_HOST_PATH=/home/ai-service-backend/agent_memory \
-e DEEPAGENT_MEMORY_CONTAINER_PATH=/code/agent_memory \
```

> ⚠️ 必须**同时**设置 `DEEPAGENT_MEMORY_HOST_PATH` 与 `DEEPAGENT_MEMORY_CONTAINER_PATH`：前者要等于 `-v` 左侧（宿主机绝对路径），后者要等于 `-v` 右侧（主容器内挂载点）。

#### Windows

```powershell
-v D:/agent_memory:/code/agent_memory:rw `
-e DEEPAGENT_MEMORY_HOST_PATH=D:/agent_memory `
-e DEEPAGENT_MEMORY_CONTAINER_PATH=/code/agent_memory `
```

> ⚠️ `DEEPAGENT_MEMORY_HOST_PATH` 必须填**宿主机**视角的绝对路径（`D:/agent_memory`），`DEEPAGENT_MEMORY_CONTAINER_PATH` 必须填**主容器内**的 Linux 路径（`/code/agent_memory`），两者通过 `-v` 关联到同一份宿主机文件。

#### 目录结构与持久化

- 自动按 `{agent_uuid}/{user_uuid}/` 隔离不同用户的记忆，例如 `<host_path>/<agent-uuid>/<user-uuid>/AGENTS.md`
- 记忆持久化在宿主机上，容器重启 / 重建均不会丢失
- 管理接口 `/aiMemory/list|get|update|reset|download` 通过 `container_path` 读写主容器内挂载到的同一份文件



## Langfuse 部署

[Langfuse](https://langfuse.com) 是一个开源的 LLM 工程平台，用于对 LLM 应用进行追踪（Tracing）、评测（Evals）、提示词管理（Prompt Management）和指标观测（Metrics），便于调试和迭代 AI 应用。本项目通过 `docker-compose.langfuse.yml` 提供 Langfuse 的本地/自托管部署方案。

### 1. 前置条件

- 已安装 Docker（建议 24.0+）和 Docker Compose v2
- 服务器开放以下端口（如需对外访问）：
  - `3000`：Langfuse Web 控制台
  - `9090`：MinIO（对象存储，S3 兼容）
- 其余服务（PostgreSQL、ClickHouse、Redis、MinIO Console）默认绑定在 `127.0.0.1`，仅本机可访问

### 2. 服务组成

`docker-compose.langfuse.yml` 中包含以下组件：

| 服务            | 作用                                  | 端口（宿主机）           |
| --------------- | ------------------------------------- | ------------------------ |
| langfuse-web    | Langfuse Web UI 与 API                | `3000`                   |
| langfuse-worker | 异步任务处理（事件摄取、批处理等）    | `127.0.0.1:3030`         |
| postgres        | 元数据存储                            | `127.0.0.1:5432`         |
| clickhouse      | 追踪数据 / 指标存储                   | `127.0.0.1:8123`、`9000` |
| redis           | 队列 / 缓存                           | `127.0.0.1:6379`         |
| minio           | S3 兼容对象存储，保存事件与媒体文件   | `9090`（API）、`127.0.0.1:9091`（Console） |

### 3. 配置说明

正式部署前，可修改 `docker-compose.langfuse.yml` 中所有标注了 `# CHANGEME` 的密钥/口令，包括：

- `NEXTAUTH_URL`：浏览器访问 Langfuse Web 的地址（外网/局域网部署时替换为服务器 IP 或域名，例如 `http://172.16.235.50:3000`）
- `NEXTAUTH_SECRET`：Web 会话密钥
- `SALT`：密码加盐
- `ENCRYPTION_KEY`：数据加密密钥，使用 `openssl rand -hex 32` 生成 64 位十六进制字符串
- `POSTGRES_PASSWORD`：PostgreSQL 密码
- `CLICKHOUSE_PASSWORD`：ClickHouse 密码
- `REDIS_AUTH`：Redis 密码
- `MINIO_ROOT_PASSWORD` 及 `LANGFUSE_S3_*_SECRET_ACCESS_KEY`：MinIO/S3 凭据

不修改则使用默认值。建议修改，尤其是对外部署时，确保安全性。

### 4. 启动 Langfuse

在项目根目录下执行：

```shell
docker compose -f docker-compose.langfuse.yml up -d
```

首次启动会拉取镜像并初始化数据库，耗时约 1-3 分钟。可使用以下命令查看启动状态：

```shell
docker compose -f docker-compose.langfuse.yml ps
docker compose -f docker-compose.langfuse.yml logs -f langfuse-web
```

### 5. 访问与初始化

- 浏览器打开 `http://<服务器IP>:3000`
- 首次使用需注册账号、创建 Organization 和 Project
- 在 Project 设置中创建 API Keys（包含 `Public Key` 和 `Secret Key`），用于 ai-service-backend 接入

### 6. 在 ai-service-backend 中接入

在 `config.yaml` 中配置 Langfuse 相关参数，通常包括：

- `deepagent.langfuse.host`：例如 `http://172.16.235.50:3000`
- `deepagent.langfuse.public_key`：Langfuse 项目 Public Key
- `deepagent.langfuse.secret_key`：Langfuse 项目 Secret Key

配置完成后重启 ai-service-backend，即可在 Langfuse Web 中看到 LLM 调用的追踪数据。

### 7. 常用运维命令

```shell
# 停止服务（保留数据）
docker compose -f docker-compose.langfuse.yml stop

# 停止并删除容器（数据卷保留）
docker compose -f docker-compose.langfuse.yml down

# 完全清理（包含数据卷，慎用，会丢失全部 Langfuse 数据）
docker compose -f docker-compose.langfuse.yml down -v

# 升级到最新镜像
docker compose -f docker-compose.langfuse.yml pull
docker compose -f docker-compose.langfuse.yml up -d
```

### 8. 数据持久化

PostgreSQL、ClickHouse、Redis、MinIO 的数据分别保存在以下 Docker 命名卷中，可按需在 `docker-compose.langfuse.yml` 中配置持久化卷路径，默认在 /var/lib/docker/volumes/ 下：

- `langfuse_postgres_data`
- `langfuse_clickhouse_data` / `langfuse_clickhouse_logs`
- `langfuse_redis_data`
- `langfuse_minio_data`

升级 / 重建容器不会丢失数据；如需迁移，请对上述卷执行备份。

### 9. 参考资料

- Langfuse 官方文档：<https://langfuse.com/docs>
- Langfuse 自托管指南：<https://langfuse.com/self-hosting>
- Langfuse 仓库（含中文 README）：<https://github.com/langfuse/langfuse>

