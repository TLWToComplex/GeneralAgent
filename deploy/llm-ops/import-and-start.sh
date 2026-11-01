#!/bin/bash
##############################################################################
# LLM-OPS（大模型集 / 统一网关）Docker 一键部署脚本（镜像导入 + 数据目录初始化 + 启动）
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64）+ Docker 29.1.0+ / Compose v2.40.0+
#   脚本通过 uname -m 自动识别架构：
#     x86_64  → docker-compose.yml       + images/*.tar
#     aarch64 → docker-compose.arm64.yml + images/*-arm64.tar
#
# 新版部署方式（2026-09-21 原始包：6 个服务，bridge 网络 llm-net，自带 MySQL，
# 完全独立于 GA-app）：
#   容器名统一以 llm- 为前缀，服务间通过容器名 DNS 互联（llm-mysql / postgres /
#   llm-litellm / llm-prometheus / llm-backend），对外端口（宿主机:容器内）：
#   mysql(23306:3306) / postgres(25432:15432) / litellm(24000:4000)
#   / prometheus(29090:9090) / backend(28038:8038) / frontend(25173:5173)
#   配置文件位于包内 config/，由 compose 就地挂载，无需分发、无需修改 IP；
#   数据与日志位于包内 ./data 与 ./logs（脚本自动创建）。
#
# 使用方式：
#   1. 将整个部署目录传输到服务器（如 /data/deploy/llm-ops/）
#   2. 将对应架构的镜像 tar 放到 images/ 子目录下：
#        x86_64：llm-app.tar / mysql.tar / postgres.tar / litellm.tar / prometheus.tar
#        ARM64 ：llm-app-arm64.tar / mysql-arm64.tar / postgres-arm64.tar
#                / litellm-arm64.tar / prometheus-arm64.tar
#      （llm-app*.tar 内含 llm-backend 与 llm-frontend 两个镜像）
#   3. 执行：sudo bash import-and-start.sh
#
# 目录结构：
#   /data/deploy/llm-ops/
#   ├── docker-compose.yml              # x86_64
#   ├── docker-compose.arm64.yml        # ARM64（aarch64）
#   ├── import-and-start.sh
#   ├── uninstall-and-clean.sh
#   ├── deployment_guide.md
#   ├── config/                         # 全部配置（compose 就地挂载，修改后重启对应服务生效）
#   │   ├── config.yaml                 #   后台管理配置（端口/数据库/网关/监控地址）
#   │   ├── config.js                   #   前端运行时配置
#   │   ├── litellm.yaml                #   LiteLLM 网关配置
#   │   ├── nginx/default.conf          #   前端 Nginx（监听 5173，反代 llm-backend:8038）
#   │   └── prometheus/                 #   抓取配置 + 告警规则
#   ├── sql/init.sql                    # MySQL 初始化（ai_service + chat_history 库表）
#   ├── images/                         # 镜像 tar（自行放入，按架构选择）
#   ├── data/                           # 运行数据（脚本创建：mysql / pgdata）
#   └── logs/                           # 运行日志（脚本创建：mysql / postgres / backend / nginx）
#
# 脚本流程（5 步）：
#   1/5 环境检查（架构识别 / root / docker / compose / 端口占用）
#   2/5 创建 data/ 与 logs/ 目录并放开日志目录权限（postgres/mysql 容器内为非 root 用户）
#   3/5 导入镜像 tar 并统一打标签（llm-app 包含双镜像，单独处理）
#   4/5 docker compose up -d（启动 6 个服务）
#   5/5 输出服务状态 + 健康探测（litellm/prometheus/backend/frontend）
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

# ============ 架构自动识别：选择 compose 文件与镜像 tar 后缀 ============
# x86_64/amd64   → docker-compose.yml       + images/*.tar
# aarch64/arm64  → docker-compose.arm64.yml + images/*-arm64.tar
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64)
    TAR_SUFFIX=""
    IMAGE_VARIANT="amd64"
    COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
    ;;
  aarch64|arm64)
    TAR_SUFFIX="-arm64"
    IMAGE_VARIANT="arm64"
    COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.arm64.yml"
    ;;
  *)
    echo -e "${RED}[错误] 不支持的系统架构: ${ARCH}（本部署包仅支持 x86_64 / aarch64）${NC}"
    exit 1
    ;;
esac

# ============ 第三方镜像文件 → 目标镜像名:标签 映射表（须与 compose 中引用一致） ============
# 键为 x86 tar 基础名；ARM64 环境自动改用同名加 -arm64 后缀的 tar（导入后标签一致）
declare -A IMAGE_MAP=(
  ["mysql.tar"]="mysql:8.3"
  ["postgres.tar"]="postgres:16"
  ["litellm.tar"]="docker.litellm.ai/berriai/litellm:main-latest"
  ["prometheus.tar"]="prom/prometheus:latest"
)

# llm-app tar（含 llm-backend + llm-frontend 双镜像，包内标签为 :amd64 / :arm64，需重打为 :latest）
LLM_APP_TAR="llm-app${TAR_SUFFIX}.tar"
LLM_APP_IMAGES=("llm-backend" "llm-frontend")

# 对外服务端口（占用检查，宿主机映射端口，统一以 2 开头）
SERVICE_PORTS=(23306 25432 24000 29090 28038 25173)

# 需要创建的运行目录（相对包目录）
RUNTIME_DIRS=(
  "data/mysql"
  "data/pgdata"
  "logs/mysql"
  "logs/postgres"
  "logs/backend"
  "logs/nginx"
)

# ============ 工具函数 ============
# 探测本机默认出口 IP（仅用于提示信息）
detect_ip() {
  local ip
  ip=$(ip route get 1.1.1.1 2>/dev/null | grep -oP 'src \K\S+' | head -1)
  [ -z "$ip" ] && ip=$(hostname -I 2>/dev/null | awk '{print $1}')
  [ -z "$ip" ] && ip="<服务器IP>"
  echo "$ip"
}

##############################################################################
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  LLM-OPS（大模型集 / 统一网关）一键部署脚本${NC}"
echo -e "${CYAN}  6 个服务：llm-{mysql,postgres,litellm,prometheus,backend,frontend}${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""

# ============ 步骤 1/5：环境检查 ============
echo -e "${CYAN}[步骤 1/5] 环境检查...${NC}"

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[错误] 请使用 sudo 或 root 用户运行此脚本${NC}"
  exit 1
fi

command -v docker &> /dev/null || { echo -e "${RED}[错误] Docker 未安装${NC}"; exit 1; }
docker compose version &> /dev/null || { echo -e "${RED}[错误] Docker Compose 未安装${NC}"; exit 1; }
[ -f "$COMPOSE_FILE" ] || { echo -e "${RED}[错误] 缺少 ${COMPOSE_FILE}${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} root / docker / compose / 编排文件 检查通过"
echo -e "  ${GREEN}✓${NC} 系统架构：${ARCH} → compose: ${COMPOSE_FILE##*/} / 镜像 tar: *${TAR_SUFFIX}.tar"

# 端口占用检查
for port in "${SERVICE_PORTS[@]}"; do
  if ss -tlnp 2>/dev/null | grep -q ":${port} " && ! docker ps --format '{{.Ports}}' | grep -q ":${port}->"; then
    echo -e "${RED}[错误] 宿主机端口 ${port} 已被其他进程占用，请释放后重试${NC}"
    echo -e "${YELLOW}        注意：本栈为 bridge 网络，上述端口为宿主机映射端口（容器内端口见 compose）。${NC}"
    exit 1
  fi
done
echo -e "  ${GREEN}✓${NC} 端口检查通过（${SERVICE_PORTS[*]}）"

echo -e "${GREEN}[✓] 环境检查通过${NC}"
echo ""

# ============ 步骤 2/5：创建运行目录 ============
echo -e "${CYAN}[步骤 2/5] 创建 data/ 与 logs/ 目录...${NC}"

cd "$SCRIPT_DIR"
for dir in "${RUNTIME_DIRS[@]}"; do
  mkdir -p "${SCRIPT_DIR}/${dir}"
done
# 日志目录权限：容器内 postgres / mysql 以非 root 用户（uid 999）运行，
# 而目录由本脚本以 root 创建（755）。不放开权限会导致 postgres 的
# logging_collector 无法在 /var/log/postgresql 写日志而崩溃重启
# （FATAL: could not open log file ... Permission denied），
# 且首次初始化中断后密码/数据库未创建，需清空 data/pgdata 重来
chmod 777 "${SCRIPT_DIR}/logs/postgres" "${SCRIPT_DIR}/logs/mysql"
echo -e "  ${GREEN}✓${NC} 运行目录就绪（${RUNTIME_DIRS[*]}，logs/postgres 与 logs/mysql 已 chmod 777）"
echo -e "  ${GREEN}✓${NC} 配置文件随包就地挂载（config/ + sql/），无需分发"

echo -e "${GREEN}[✓] 目录初始化完成${NC}"
echo ""

# ============ 步骤 3/5：导入镜像 ============
echo -e "${CYAN}[步骤 3/5] 导入 Docker 镜像...${NC}"

IMPORT_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

# ---- 3.1 第三方镜像（一 tar 一镜像）----
for TAR_FILE in "${!IMAGE_MAP[@]}"; do
  ACTUAL_TAR="${TAR_FILE%.tar}${TAR_SUFFIX}.tar"      # arm64 环境自动使用 *-arm64.tar
  TAR_PATH="${IMAGE_DIR}/${ACTUAL_TAR}"
  TARGET_IMAGE="${IMAGE_MAP[$TAR_FILE]}"

  if [ ! -f "$TAR_PATH" ]; then
    if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${TARGET_IMAGE}$"; then
      echo -e "  ${GREEN}✓${NC} 本地已存在: ${TARGET_IMAGE}（跳过导入）"
      SKIP_COUNT=$((SKIP_COUNT + 1))
    else
      echo -e "  ${RED}✗ 缺少镜像 tar 且本地无镜像: ${ACTUAL_TAR} → ${TARGET_IMAGE}${NC}"
      FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
    continue
  fi

  echo -e "  ${CYAN}→${NC} 导入 ${ACTUAL_TAR} ..."
  LOADED_OUTPUT=$(docker load -i "$TAR_PATH" 2>&1) || {
    echo -e "  ${RED}✗ 导入失败${NC}: ${LOADED_OUTPUT}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    continue
  }

  LOADED_IMAGE=$(echo "$LOADED_OUTPUT" | grep -oP 'Loaded image: \K.*' | head -1)
  if [ -z "$LOADED_IMAGE" ]; then
    LOADED_ID=$(echo "$LOADED_OUTPUT" | grep -oP 'Loaded image ID: \K.*' | head -1)
    if [ -n "$LOADED_ID" ]; then
      docker tag "$LOADED_ID" "$TARGET_IMAGE"
      echo -e "  ${GREEN}✓ 无标签镜像已标记为 ${TARGET_IMAGE}${NC}"
    else
      echo -e "  ${RED}✗ 无法解析导入的镜像信息${NC}"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      continue
    fi
  else
    if [ "$LOADED_IMAGE" != "$TARGET_IMAGE" ]; then
      echo -e "  ${YELLOW}  原始标签: ${LOADED_IMAGE} → 重新标记为: ${TARGET_IMAGE}${NC}"
      docker tag "$LOADED_IMAGE" "$TARGET_IMAGE"
    fi
    echo -e "  ${GREEN}✓ ${TARGET_IMAGE}${NC}"
  fi
  IMPORT_COUNT=$((IMPORT_COUNT + 1))
done

# ---- 3.2 llm-app tar（一个 tar 内含 llm-backend + llm-frontend 双镜像）----
LLM_APP_TAR_PATH="${IMAGE_DIR}/${LLM_APP_TAR}"
if [ -f "$LLM_APP_TAR_PATH" ]; then
  echo -e "  ${CYAN}→${NC} 导入 ${LLM_APP_TAR}（含 llm-backend + llm-frontend）..."
  LOADED_OUTPUT=$(docker load -i "$LLM_APP_TAR_PATH" 2>&1) || {
    echo -e "  ${RED}✗ 导入失败${NC}: ${LOADED_OUTPUT}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  }
  if [ -n "$LOADED_OUTPUT" ] && echo "$LOADED_OUTPUT" | grep -q "Loaded image"; then
    echo "$LOADED_OUTPUT" | grep -oP 'Loaded image: \K.*' | sed 's/^/      /'
    # 包内镜像标签为 :amd64 / :arm64，统一重打为 :latest（与 compose 引用一致）
    for name in "${LLM_APP_IMAGES[@]}"; do
      if docker image inspect "${name}:${IMAGE_VARIANT}" &> /dev/null; then
        docker tag "${name}:${IMAGE_VARIANT}" "${name}:latest"
        echo -e "  ${GREEN}✓${NC} ${name}:${IMAGE_VARIANT} → ${name}:latest"
      elif docker image inspect "${name}:latest" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} ${name}:latest 已就绪"
      else
        echo -e "  ${RED}✗ 导入后未找到镜像 ${name}（期望标签 :${IMAGE_VARIANT} 或 :latest）${NC}"
        FAIL_COUNT=$((FAIL_COUNT + 1))
      fi
    done
    IMPORT_COUNT=$((IMPORT_COUNT + 1))
  fi
else
  LOCAL_OK=true
  for name in "${LLM_APP_IMAGES[@]}"; do
    docker image inspect "${name}:latest" &> /dev/null || LOCAL_OK=false
  done
  if [ "$LOCAL_OK" = true ]; then
    echo -e "  ${GREEN}✓${NC} 本地已存在: llm-backend:latest / llm-frontend:latest（跳过导入）"
    SKIP_COUNT=$((SKIP_COUNT + 1))
  else
    echo -e "  ${RED}✗ 缺少镜像 tar 且本地无镜像: ${LLM_APP_TAR} → llm-backend:latest + llm-frontend:latest${NC}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
fi

echo -e "${GREEN}[✓] 镜像导入完成${NC} — 成功: ${IMPORT_COUNT}, 跳过: ${SKIP_COUNT}, 失败: ${FAIL_COUNT}"
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo -e "${RED}[错误] 存在缺失/导入失败的镜像，请检查 images/ 目录后重新执行脚本${NC}"
  exit 1
fi
echo ""

# ============ 步骤 4/5：启动服务 ============
echo -e "${CYAN}[步骤 4/5] 启动 6 个服务...${NC}"
cd "$SCRIPT_DIR"
docker compose -f "$COMPOSE_FILE" up -d
echo ""

# ============ 步骤 5/5：健康探测 ============
echo -e "${CYAN}[步骤 5/5] 健康探测...${NC}"

# 等待 litellm 就绪（首次启动需初始化数据库，最长 3 分钟）
LITELLM_READY=false
for _ in $(seq 1 36); do
  if curl -sf http://localhost:24000/health/liveliness &> /dev/null; then
    LITELLM_READY=true
    break
  fi
  sleep 5
done
[ "$LITELLM_READY" = true ] \
  && echo -e "  ${GREEN}✓${NC} litellm (24000) 就绪" \
  || echo -e "  ${YELLOW}⚠${NC} litellm (24000) 暂未就绪，请稍后查看日志"

for probe in "prometheus|http://localhost:29090/-/healthy" \
             "backend|http://localhost:28038" \
             "frontend|http://localhost:25173"; do
  svc="${probe%%|*}"
  url="${probe##*|}"
  if curl -s -o /dev/null --max-time 5 "$url"; then
    echo -e "  ${GREEN}✓${NC} ${svc} 可访问（${url}）"
  else
    echo -e "  ${YELLOW}⚠${NC} ${svc} 暂未就绪（${url}），首次启动请稍等后重试"
  fi
done
echo ""

SERVER_IP=$(detect_ip)
docker compose -f "$COMPOSE_FILE" ps
echo ""

echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}[✓] LLM-OPS 部署完成！${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${CYAN}访问信息（bridge 网络 llm-net，宿主机映射端口）：${NC}"
echo -e "  ├── 前端:        http://${SERVER_IP}:25173  （默认账号 admin / 123456）"
echo -e "  ├── 后台 API:    http://${SERVER_IP}:28038"
echo -e "  ├── LiteLLM:     http://${SERVER_IP}:24000  （Master Key: sk-master-1234）"
echo -e "  ├── Prometheus:  http://${SERVER_IP}:29090"
echo -e "  ├── MySQL:       ${SERVER_IP}:23306  （root / 123456，库 ai_service + chat_history）"
echo -e "  └── PostgreSQL:  ${SERVER_IP}:25432  （admin / 1qaz2wsx3edc，库 litellm）"
echo ""
echo -e "${CYAN}配置说明（config/ 就地挂载，服务间用容器名互联，修改后重启对应服务生效）：${NC}"
echo -e "  ├── config/config.yaml        后台：server.port(8038) / database(llm-mysql:3306) / gateway(llm-litellm:4000) / monitor(llm-prometheus:9090) / postgres(postgres:15432)"
echo -e "  ├── config/config.js          前端运行时配置（标题 / SSO 等）"
echo -e "  ├── config/litellm.yaml       网关：master_key / database_url(postgres:15432) / 路由与日志策略"
echo -e "  ├── config/nginx/default.conf 前端 Nginx：listen 5173，/admin-api 反代 llm-backend:8038"
echo -e "  └── config/prometheus/        抓取目标（llm-litellm:4000）与告警规则"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo -e "  查看日志:   docker compose -f ${COMPOSE_FILE} logs -f [服务名]"
echo -e "  重启服务:   docker compose -f ${COMPOSE_FILE} restart [服务名]"
echo -e "  停止全部:   docker compose -f ${COMPOSE_FILE} down"
