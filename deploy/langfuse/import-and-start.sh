#!/bin/bash
##############################################################################
# Langfuse 一键部署脚本（独立于 GA 主系统，可单独部署到任意服务器）
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64）+ Docker 24.0+ / Compose v2
#   脚本通过 uname -m 自动识别架构：
#     x86_64  → docker-compose.yml       + images/*.tar
#     aarch64 → docker-compose.arm64.yml + images/*-arm64.tar
#
# 使用方式：
#   sudo bash import-and-start.sh [服务器IP]
#   - 服务器IP 可选，用于生成 NEXTAUTH_URL；不传则自动探测本机 IP
#   - 离线部署：将 6 个对应架构的镜像 tar 放到同目录 images/ 下（清单见 deployment_guide.md）
#   - 在线部署：无 images/ 目录时由 docker compose 自动拉取镜像
#
# 目录结构：
#   langfuse/
#   ├── docker-compose.yml           # x86_64
#   ├── docker-compose.arm64.yml     # ARM64（aarch64）
#   ├── import-and-start.sh
#   ├── uninstall-and-clean.sh
#   ├── deployment_guide.md
#   ├── .env                     # 首次运行自动生成（随机密钥），已存在则保留
#   └── images/                  # 可选，离线镜像 tar
#
# 脚本流程（4 步）：
#   1/4 环境检查（架构识别 / docker / compose / compose 文件）
#   2/4 导入离线镜像（images/ 存在时）
#   3/4 生成 .env（随机密钥 + NEXTAUTH_URL，已存在则保留不覆盖）
#   4/4 docker compose up -d + 等待健康检查
##############################################################################

set -e

# ============ 颜色定义 ============
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ============ 变量定义 ============
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_DIR="${SCRIPT_DIR}/images"
ENV_FILE="${SCRIPT_DIR}/.env"
SERVER_IP="${1:-}"
WEB_PORT=13000

# ============ 架构自动识别：选择 compose 文件与镜像 tar 后缀 ============
# x86_64/amd64   → docker-compose.yml       + images/*.tar
# aarch64/arm64  → docker-compose.arm64.yml + images/*-arm64.tar
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)
    TAR_SUFFIX=""
    COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
    ;;
  aarch64|arm64)
    TAR_SUFFIX="-arm64"
    COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.arm64.yml"
    ;;
  *)
    echo -e "${RED}[错误] 不支持的系统架构: ${ARCH}（本部署包仅支持 x86_64 / aarch64）${NC}"
    exit 1
    ;;
esac

# ============ 镜像文件 → 目标镜像名:标签 映射表（须与 compose 中引用一致） ============
# 键为 x86 tar 基础名；ARM64 环境自动改用同名加 -arm64 后缀的 tar（导入后标签一致）
declare -A IMAGE_MAP=(
  ["postgres.tar"]="docker.io/postgres:17"
  ["clickhouse.tar"]="docker.io/clickhouse/clickhouse-server:25.12"
  ["redis.tar"]="docker.io/redis:7"
  ["minio.tar"]="cgr.dev/chainguard/minio:latest"


  ["langfuse-web.tar"]="docker.io/langfuse/langfuse:3"
  ["langfuse-worker.tar"]="docker.io/langfuse/langfuse-worker:3"
)

# ============ 工具函数 ============
# 生成随机十六进制密钥（$1 = 字节数），优先 openssl，无则用 /dev/urandom
gen_secret() {
  if command -v openssl &> /dev/null; then
    openssl rand -hex "$1"
  else
    head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'
  fi
}

# 探测本机默认出口 IP
detect_ip() {
  local ip
  ip=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' | head -1)
  [ -z "$ip" ] && ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  echo "$ip"
}

##############################################################################
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  Langfuse 一键部署脚本${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============ 步骤 1/4：环境检查 ============
echo -e "${CYAN}[步骤 1/4] 环境检查...${NC}"

command -v docker &> /dev/null || { echo -e "${RED}[错误] Docker 未安装${NC}"; exit 1; }
docker compose version &> /dev/null || { echo -e "${RED}[错误] Docker Compose 未安装${NC}"; exit 1; }
docker info &> /dev/null || { echo -e "${RED}[错误] 无法连接 Docker daemon，请使用 sudo 运行或确认当前用户在 docker 组${NC}"; exit 1; }
[ -f "$COMPOSE_FILE" ] || { echo -e "${RED}[错误] 缺少 ${COMPOSE_FILE}${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} 系统架构：${ARCH} → compose: ${COMPOSE_FILE##*/} / 镜像 tar: *${TAR_SUFFIX}.tar"
echo -e "  ${GREEN}✓${NC} docker / compose / 编排文件 检查通过"

# Web 端口占用检查
if ss -tlnp 2>/dev/null | grep -q ":${WEB_PORT} " && ! docker ps --format '{{.Ports}}' | grep -q ":${WEB_PORT}->"; then
  echo -e "${RED}[错误] 宿主机端口 ${WEB_PORT} 已被其他进程占用，请释放后重试${NC}"
  exit 1
fi

# 确定服务器 IP（用于 NEXTAUTH_URL）
if [ -z "$SERVER_IP" ]; then
  SERVER_IP=$(detect_ip)
fi
if [ -z "$SERVER_IP" ]; then
  SERVER_IP="127.0.0.1"
  echo -e "  ${YELLOW}⚠ 无法自动探测 IP，NEXTAUTH_URL 将使用 127.0.0.1，请在 .env 中手动修改${NC}"
else
  echo -e "  ${GREEN}✓${NC} 服务器 IP: ${SERVER_IP}"
fi
echo -e "${GREEN}[✓] 环境检查通过${NC}"
echo ""

# ============ 步骤 2/4：导入离线镜像 ============
echo -e "${CYAN}[步骤 2/4] 导入 Docker 镜像...${NC}"

IMPORT_COUNT=0
LOCAL_COUNT=0
MISSING_COUNT=0

for TAR_FILE in "${!IMAGE_MAP[@]}"; do
  ACTUAL_TAR="${TAR_FILE%.tar}${TAR_SUFFIX}.tar"      # arm64 环境自动使用 *-arm64.tar
  TAR_PATH="${IMAGE_DIR}/${ACTUAL_TAR}"
  TARGET_IMAGE="${IMAGE_MAP[$TAR_FILE]}"

  if [ -f "$TAR_PATH" ]; then
    echo -e "  ${CYAN}→${NC} 导入 ${ACTUAL_TAR} ..."
    LOADED_OUTPUT=$(docker load -i "$TAR_PATH" 2>&1) || {
      echo -e "  ${RED}✗ 导入失败${NC}: ${LOADED_OUTPUT}"
      exit 1
    }
    LOADED_IMAGE=$(echo "$LOADED_OUTPUT" | grep -oP 'Loaded image: \K.*' | head -1)
    if [ -n "$LOADED_IMAGE" ] && [ "$LOADED_IMAGE" != "$TARGET_IMAGE" ]; then
      docker tag "$LOADED_IMAGE" "$TARGET_IMAGE"
      echo -e "  ${YELLOW}  原始标签: ${LOADED_IMAGE} → 重新标记为: ${TARGET_IMAGE}${NC}"
    elif [ -z "$LOADED_IMAGE" ]; then
      LOADED_ID=$(echo "$LOADED_OUTPUT" | grep -oP 'Loaded image ID: \K.*' | head -1)
      [ -n "$LOADED_ID" ] && docker tag "$LOADED_ID" "$TARGET_IMAGE"
    fi
    echo -e "  ${GREEN}✓${NC} ${TARGET_IMAGE}"
    IMPORT_COUNT=$((IMPORT_COUNT + 1))
  elif docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${TARGET_IMAGE}$"; then
    echo -e "  ${GREEN}✓${NC} 本地已存在: ${TARGET_IMAGE}"
    LOCAL_COUNT=$((LOCAL_COUNT + 1))
  else
    echo -e "  ${YELLOW}⚠ 缺少${NC} ${ACTUAL_TAR}（本地也无 ${TARGET_IMAGE}）"
    MISSING_COUNT=$((MISSING_COUNT + 1))
  fi
done

echo -e "${GREEN}[✓] 镜像准备完成${NC} — 导入: ${IMPORT_COUNT}, 本地已有: ${LOCAL_COUNT}, 缺失: ${MISSING_COUNT}"
if [ "$MISSING_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}    缺失镜像将在启动时尝试从仓库拉取（需联网）；离线环境请将 tar 放入 ${IMAGE_DIR}/ 后重新执行${NC}"
fi
echo ""

# ============ 步骤 3/4：生成 .env ============
echo -e "${CYAN}[步骤 3/4] 生成环境配置 .env ...${NC}"

if [ -f "$ENV_FILE" ]; then
  echo -e "  ${YELLOW}→ .env 已存在，保留不覆盖${NC}（如需重新生成请先备份后删除 ${ENV_FILE}）"
  # 校验关键项，避免旧 .env 缺少 NEXTAUTH_URL
  if ! grep -q '^NEXTAUTH_URL=' "$ENV_FILE"; then
    echo "NEXTAUTH_URL=http://${SERVER_IP}:${WEB_PORT}" >> "$ENV_FILE"
    echo -e "  ${GREEN}✓${NC} 已追加 NEXTAUTH_URL=http://${SERVER_IP}:${WEB_PORT}"
  fi
else
  POSTGRES_PASSWORD="$(gen_secret 16)"
  CLICKHOUSE_PASSWORD="$(gen_secret 16)"
  REDIS_AUTH="$(gen_secret 16)"
  MINIO_ROOT_PASSWORD="$(gen_secret 16)"

  cat > "$ENV_FILE" <<EOF
##############################################################################
# Langfuse 环境配置（由 import-and-start.sh 自动生成，密钥已随机化）
# 修改后执行: docker compose -f ${COMPOSE_FILE##*/} up -d
##############################################################################

# ---- 访问地址（浏览器访问 Langfuse Web 的地址，必须是客户端可达的 IP/域名）----
NEXTAUTH_URL=http://${SERVER_IP}:${WEB_PORT}

# ---- Langfuse 应用密钥 ----
NEXTAUTH_SECRET=$(gen_secret 32)
SALT=$(gen_secret 32)
ENCRYPTION_KEY=$(gen_secret 32)

# ---- PostgreSQL（DATABASE_URL 须与 POSTGRES_PASSWORD 保持一致）----
POSTGRES_USER=postgres
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=postgres
DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/postgres

# ---- ClickHouse ----
CLICKHOUSE_USER=clickhouse
CLICKHOUSE_PASSWORD=${CLICKHOUSE_PASSWORD}

# ---- Redis ----
REDIS_AUTH=${REDIS_AUTH}

# ---- MinIO / S3（各 SECRET_ACCESS_KEY 须与 MINIO_ROOT_PASSWORD 保持一致）----
MINIO_ROOT_USER=minio
MINIO_ROOT_PASSWORD=${MINIO_ROOT_PASSWORD}
LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID=minio
LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
LANGFUSE_S3_MEDIA_UPLOAD_ACCESS_KEY_ID=minio
LANGFUSE_S3_MEDIA_UPLOAD_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}
LANGFUSE_S3_BATCH_EXPORT_ACCESS_KEY_ID=minio
LANGFUSE_S3_BATCH_EXPORT_SECRET_ACCESS_KEY=${MINIO_ROOT_PASSWORD}

# ---- 可选：初始化管理员账号（取消注释并修改后，首次启动自动创建）----
# LANGFUSE_INIT_ORG_ID=GA
# LANGFUSE_INIT_ORG_NAME=GA
# LANGFUSE_INIT_PROJECT_ID=GA-default
# LANGFUSE_INIT_PROJECT_NAME=GA-Default
# LANGFUSE_INIT_PROJECT_PUBLIC_KEY=pk-GA
# LANGFUSE_INIT_PROJECT_SECRET_KEY=sk-GA
# LANGFUSE_INIT_USER_EMAIL=admin@GA.local
# LANGFUSE_INIT_USER_NAME=admin
# LANGFUSE_INIT_USER_PASSWORD=请修改此密码
EOF
  chmod 600 "$ENV_FILE"
  echo -e "  ${GREEN}✓${NC} 已生成 ${ENV_FILE}（全部密钥随机化，权限 600）"
  echo -e "  ${YELLOW}  请妥善备份 .env：ENCRYPTION_KEY/SALT 丢失将导致已有数据无法解密${NC}"
fi
echo -e "${GREEN}[✓] 环境配置完成${NC}"
echo ""

# ============ 步骤 4/4：启动服务 ============
echo -e "${CYAN}[步骤 4/4] 启动 Langfuse 服务栈...${NC}"
cd "$SCRIPT_DIR"
docker compose -f "$COMPOSE_FILE" up -d
echo ""

# 等待 langfuse-web 健康（最长 5 分钟，首次启动需初始化数据库）
echo -e "${CYAN}→${NC} 等待 Langfuse Web 就绪（首次启动约 1-3 分钟）..."
READY=false
for _ in $(seq 1 60); do
  if curl -sf "http://localhost:${WEB_PORT}/api/public/health" &> /dev/null; then
    READY=true
    break
  fi
  sleep 5
done

echo ""
docker compose -f "$COMPOSE_FILE" ps
echo ""

echo -e "${CYAN}============================================${NC}"
if [ "$READY" = true ]; then
  echo -e "${GREEN}[✓] Langfuse 部署完成，服务已就绪！${NC}"
else
  echo -e "${YELLOW}[!] 部署完成，但 Web 健康检查未通过，请查看日志：${NC}"
  echo -e "    docker compose -f ${COMPOSE_FILE} logs -f langfuse-web"
fi
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${CYAN}访问信息：${NC}"
echo -e "  ├── Web 控制台:   http://${SERVER_IP}:${WEB_PORT}  （首次访问需注册账号）"
echo -e "  ├── MinIO API:    http://${SERVER_IP}:19090  （账号/密码见 .env）"
echo -e "  └── 其余组件（postgres/clickhouse/redis 等）仅绑定 127.0.0.1，外部不可直连"
echo ""
echo -e "${CYAN}接入 ai-service-backend：${NC}"
echo -e "  1. Web 控制台注册账号 → 创建 Organization / Project → 创建 API Keys"
echo -e "  2. 在 /data/GA-service-backend/config.yaml 中配置 langfuse："
echo -e "     host: http://${SERVER_IP}:${WEB_PORT}"
echo -e "     public_key: <Public Key>"
echo -e "     secret_key: <Secret Key>"
echo -e "  3. docker compose restart app-GA-service-backend"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo -e "  查看日志:   docker compose -f ${COMPOSE_FILE} logs -f langfuse-web"
echo -e "  停止服务:   docker compose -f ${COMPOSE_FILE} stop"
echo -e "  删除容器:   docker compose -f ${COMPOSE_FILE} down       （数据卷保留）"
echo -e "  彻底清理:   docker compose -f ${COMPOSE_FILE} down -v    （⚠ 删除全部数据）"
