# MirrorHub 安装与启动说明

> 内网 Python / npm 镜像管理平台 · x86_64 离线安装包

本包在**有外网的机器上构建**，整体拷贝进内网后**无需外网**即可完成安装与运行。

## 1. 包内容

```text
mirrorhub-install-x86_64/
├── docker-compose.yml        # 运行时编排（只引用镜像，不构建）
├── .env.example              # 环境变量模板
├── INSTALL.md                # 本文档
├── images/                   # 镜像导出包（5 个 tar，约 3.2 GB）
├── config/
│   ├── nginx/nginx.conf      # 反向代理 + 包名提取 + JSON 访问日志
│   └── verdaccio/config.yaml # npm 镜像配置（纯离线，无 uplink）
├── frontend/                 # 前端静态资源（由 nginx 挂载）
├── scripts/
│   └── start.sh              # 一键启动
└── data/                     # 运行时数据（首次启动自动创建）
```

## 2. 前置条件

| 项 | 要求 |
|---|---|
| 架构 | **x86_64 / amd64**（镜像已固定为该架构） |
| 操作系统 | Linux（建议内核 3.10+） |
| Docker | Docker 20.10+ |
| Docker Compose | **v2**（`docker compose`）或 v1（`docker-compose`） |
| 内存 | 建议 ≥ 4 GB |
| 磁盘 | 建议 ≥ 20 GB（含镜像与后续包缓存） |
| 网络 | **无需外网**；仅需内网客户端能访问本机 |

检查环境：

```bash
uname -m                 # 应输出 x86_64
docker --version
docker compose version   # 或 docker-compose --version
```

> 若 `uname -m` 输出 `aarch64` 或 `arm64`，本包**不适用**，需在 x86_64 机器上重新构建镜像。

## 3. 快速开始

```bash
# 1. 拷贝整个目录进内网
#    （建议用 tar 打包传输，避免权限丢失）

# 2. 进入目录
cd mirrorhub-install-x86_64

# 3. 设置本机内网 IP（客户端将用这个地址访问）
sed -i 's|^SERVER_IP=.*|SERVER_IP=192.168.1.10|' .env.example

# 4. 一键启动（首次会自动生成 .env 与随机强密钥）
chmod +x scripts/start.sh
./scripts/start.sh
```

脚本会依次完成：

1. 生成 `.env` 并把 `change-me-*` 替换为**随机强密钥**
2. 选择可用的 compose 命令（v2 优先，回退 v1）
3. `docker load` 加载 `images/*.tar`
4. `docker compose up -d` 启动五个服务
5. 对齐 devpi root 密码并创建可写索引 `root/local`
6. 轮询 `/api/health` 直到就绪，最后打印访问地址与登录 token

成功时输出：

```
  管理界面 : http://192.168.1.10/
  登录 token: mirror-admin-<随机串>

  客户端接入:
    pip config set global.index-url http://192.168.1.10/pypi/root/local/+simple/
    npm config set registry http://192.168.1.10/npm/
```

**请记录输出的 token**，也可事后在 `.env` 的 `ADMIN_TOKENS` 中查看。

## 4. 手动安装（不使用脚本）

```bash
# 1. 生成配置
cp .env.example .env
vi .env      # 必须把 change-me-* 全部替换为真实强密钥，否则后端拒绝启动

# 2. 加载镜像
for f in images/*.tar; do docker load -i "$f"; done

# 3. 启动
docker compose up -d

# 4. 验证
curl http://localhost/api/health
```

## 5. 服务与端口

| 服务 | 容器名 | 默认端口 | 说明 |
|---|---|---|---|
| nginx | mirrorhub-nginx | 80 | Web 界面 + 统一入口 |
| backend | mirrorhub-backend | — | FastAPI（仅内网，经 nginx 反代） |
| devpi | mirrorhub-devpi | 3141 | Python / PyPI 镜像 |
| verdaccio | mirrorhub-verdaccio | 4873 | npm 镜像 |
| postgres | mirrorhub-postgres | — | 数据库（仅内网） |

端口可通过 `.env` 的 `NGINX_PORT` / `DEVPI_PORT` / `VERDACCIO_PORT` 调整。

## 6. 客户端接入

```bash
# pip
pip config set global.index-url http://<SERVER_IP>/pypi/root/local/+simple/
pip config set global.trusted-host <SERVER_IP>

# npm
npm config set registry http://<SERVER_IP>/npm/

# pnpm
pnpm config set registry http://<SERVER_IP>/npm/
```

## 7. ⚠️ 镜像初始为空

**首次部署时镜像里没有任何包**，这是设计行为：

| 场景 | 结果 |
|---|---|
| 已导入的包 | 200，正常提供 |
| 未导入的包 | **404** |
| 回源公网 | **否** |

镜像不会静默回源公共源。这样既保证「内网确实不依赖外网」可被验证，也让缺失的包能被自动发现链路捕获。

### 填充依赖树

**方式一：自动发现（推荐）**

内网客户端请求缺失的包会失败（404），但请求已被记录，系统每 30 秒把缺失的包写入同步队列：

1. 打开 Web 界面 →「统计」页查看同步队列
2. 导出同步清单（`requirements.txt` + `package.json`）
3. 在外网机器用 `sync-tool` 按清单下载打包成 `bundle.tar.gz`
4. 回到内网 Web 界面 →「导入中心」上传，队列对应条目自动完成

**方式二：下载中心**

若服务器本身能访问外网，直接在「下载中心」上传清单，由服务端抓取打包。

### 必须同步完整依赖树

离线镜像**只提供已导入的包**，缺任何一层传递依赖都会导致安装失败：

```
ERROR: Could not find a version that satisfies the requirement colorama;
       platform_system == "Windows" (from click) (from versions: none)
```

实测中，`pip install click` 还需 `colorama`；`npm install chalk` 还需 `ansi-styles`、`supports-color`、`color-convert`、`color-name`、`has-flag`。

**建议从 lock 文件一次性提取完整清单**，而不是只写顶层包：

```bash
# Python
pip freeze > requirements.txt

# npm：从 package-lock.json 提取全部 name@version
python sync-tool/extract_npm_lock.py package-lock.json -o npm-packages.json
```

## 8. 日常运维

```bash
# 查看状态
docker compose ps

# 查看日志
docker compose logs -f backend
docker compose logs -f devpi

# 重启
docker compose restart

# 停止（保留数据）
docker compose down

# 停止并清除数据（谨慎：会删除包缓存与数据库）
docker compose down && rm -rf data/
```

### 备份与恢复

所有运行时数据都在 `data/` 目录：

```bash
# 备份（建议先停止服务以保证一致性）
docker compose down
tar -czf mirrorhub-data-$(date +%Y%m%d).tar.gz data/

# 恢复
docker compose down
rm -rf data/ && tar -xzf mirrorhub-data-YYYYMMDD.tar.gz
docker compose up -d
```

包缓存索引也可从磁盘重建：Web 界面「包管理」→ 刷新，或 `POST /api/packages/refresh`。

### 变更配置

编辑 `.env` 后重启生效：

```bash
vi .env
docker compose up -d
```

## 9. 升级

```bash
# 1. 备份数据
docker compose down
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# 2. 用新版镜像替换 images/*.tar（在构建机导出后传入）
# 3. 重新加载并启动
for f in images/*.tar; do docker load -i "$f"; done
docker compose up -d
```

## 10. 故障排查

| 现象 | 排查方向 |
|---|---|
| 后端反复重启 | `.env` 中是否有 `change-me-*` 未替换；`docker compose logs backend` |
| 健康检查不过 | `docker compose ps` 看 postgres 是否 healthy；`docker compose logs postgres` |
| 端口被占用 | 改 `.env` 的 `NGINX_PORT` 等；`ss -lntp \| grep :80` |
| 客户端 404 | 该包未导入，属预期。走第 7 节流程补包 |
| npm 元数据里 tarball 地址不对 | 检查 `.env` 的 `SERVER_IP` / `NGINX_PORT`，改后 `docker compose up -d` |
| 镜像加载慢 | 3.2 GB，视磁盘而定；可先 `docker load` 再启动 |

查看详细状态：

```bash
curl http://localhost/api/health
docker compose ps
docker compose logs --tail=100 backend
```

## 11. 安全建议

- `.env` 包含全部凭据，**权限设为 600**：`chmod 600 .env`
- `ADMIN_TOKENS` 生成的是强随机值，如手工改请保持足够长度
- 生产环境可设置 `AUTH_MODE=oidc` 对接企业 SSO（需填 `OIDC_*` 变量）
- 定期备份 `data/` 目录