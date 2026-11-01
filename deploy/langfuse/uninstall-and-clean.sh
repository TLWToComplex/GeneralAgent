#!/bin/bash
##############################################################################
# Langfuse 一键卸载 & 深度清理脚本（独立于 GA 主系统）
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64，自动识别架构选择 compose 文件）
#
# 使用方式：sudo bash uninstall-and-clean.sh
#
# 功能（5 步分级清理）：
#   1/5 停止并删除所有 Langfuse 容器
#   2/5 删除 Langfuse 相关镜像（6 个）
#   3/5 清理 Docker 网络
#   4/5 (可选，需二次确认) 删除数据卷（PostgreSQL/ClickHouse/Redis/MinIO）及 .env
#   5/5 (可选，需二次确认) Docker 系统级深度清理
#
# 说明：仅清理 Langfuse 栈（按 compose 项目标签识别），不影响 GA 主系统
#       及其他任何容器/镜像/卷。
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
PROJECT_NAME="$(basename "$SCRIPT_DIR" | tr '[:upper:]' '[:lower:]')"
ENV_FILE="${SCRIPT_DIR}/.env"

# 按架构选择部署时使用的 compose 文件（两者服务定义一致，缺失时自动回退到另一份）
ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64) COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.arm64.yml" ;;
  *)             COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml" ;;
esac
[ -f "$COMPOSE_FILE" ] || COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
[ -f "$COMPOSE_FILE" ] || COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.arm64.yml"

# ============ 需要清理的镜像列表（与 compose 引用一致） ============
IMAGES_TO_REMOVE=(
  "docker.io/langfuse/langfuse:3"
  "docker.io/langfuse/langfuse-worker:3"
  "docker.io/postgres:17"
  "docker.io/clickhouse/clickhouse-server:25.12"
  "docker.io/redis:7"
  "cgr.dev/chainguard/minio:latest"
)

# ============ 需要清理的数据卷（不带项目前缀的卷名） ============
VOLUMES_TO_REMOVE=(
  "langfuse_postgres_data"
  "langfuse_clickhouse_data"
  "langfuse_clickhouse_logs"
  "langfuse_redis_data"
  "langfuse_minio_data"
)

# ============ 前置检查 ============
echo -e "${RED}============================================${NC}"
echo -e "${RED}  Langfuse 一键卸载 & 深度清理${NC}"
echo -e "${RED}============================================${NC}"
echo ""

command -v docker &> /dev/null || { echo -e "${RED}[错误] Docker 未安装${NC}"; exit 1; }
docker info &> /dev/null || { echo -e "${RED}[错误] 无法连接 Docker daemon，请使用 sudo 运行${NC}"; exit 1; }

echo -e "${YELLOW}⚠  警告：此操作将停止并删除所有 Langfuse 容器和镜像！${NC}"
echo -e "${YELLOW}   如果选择删除数据卷，全部追踪数据/账号/密钥将永久丢失！${NC}"
echo -e "${CYAN}   （不影响 GA 主系统及其他任何服务）${NC}"
echo ""
read -p "是否继续？(y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo -e "${CYAN}已取消操作${NC}"
  exit 0
fi
echo ""

# ============ 步骤 1/5：停止并删除容器 ============
echo -e "${CYAN}[步骤 1/5] 停止并删除所有 Langfuse 容器...${NC}"

if [ -f "$COMPOSE_FILE" ]; then
  cd "$SCRIPT_DIR"
  docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Docker Compose 容器已停止并删除"
else
  echo -e "  ${YELLOW}⚠${NC} compose 文件不存在，按项目标签手动清理容器..."
  CONTAINER_IDS=$(docker ps -aq --filter "label=com.docker.compose.project=${PROJECT_NAME}" 2>/dev/null || true)
  if [ -n "$CONTAINER_IDS" ]; then
    docker rm -f $CONTAINER_IDS 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 已删除 $(echo "$CONTAINER_IDS" | wc -l) 个容器"
  else
    echo -e "  ${YELLOW}⚠${NC} 未找到属于项目 ${PROJECT_NAME} 的容器"
  fi
fi
echo ""

# ============ 步骤 2/5：删除镜像 ============
echo -e "${CYAN}[步骤 2/5] 删除 Langfuse 相关镜像...${NC}"

for image in "${IMAGES_TO_REMOVE[@]}"; do
  # 同时匹配带 docker.io/ 前缀与不带前缀的标签形式
  SHORT_IMAGE="${image#docker.io/}"
  FOUND=$(docker images --format '{{.Repository}}:{{.Tag}}' | grep -E "^(${image}|${SHORT_IMAGE})$" | head -1 || true)
  if [ -n "$FOUND" ]; then
    docker rmi "$FOUND" 2>/dev/null || true
    # 短名删除后如仍有带前缀标签残留，一并删除
    [ "$FOUND" != "$image" ] && docker rmi "$image" 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 已删除镜像: ${FOUND}"
  else
    echo -e "  ${YELLOW}⚠${NC} 镜像不存在，跳过: $image"
  fi
done

# 清理 docker load 导入时可能残留的无标签镜像
DANGLING_COUNT=$(docker images -f "dangling=true" -q | wc -l)
if [ "$DANGLING_COUNT" -gt 0 ]; then
  docker rmi $(docker images -f "dangling=true" -q) 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} 已清理 ${DANGLING_COUNT} 个无标签镜像"
fi
echo ""

# ============ 步骤 3/5：清理 Docker 网络 ============
echo -e "${CYAN}[步骤 3/5] 清理 Docker 网络...${NC}"

# compose down 正常会删除默认网络，此处兜底（网络名 = 项目名_default）
NETWORK_NAME="${PROJECT_NAME}_default"
if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
  docker network rm "$NETWORK_NAME" 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} 已删除网络: $NETWORK_NAME"
else
  echo -e "  ${GREEN}✓${NC} 网络已由 compose down 清理"
fi
echo ""

# ============ 步骤 4/5：(可选) 删除数据卷与 .env ============
echo -e "${CYAN}[步骤 4/5] 数据卷与密钥文件清理...${NC}"
echo ""
echo -e "${RED}⚠  警告：数据卷包含全部追踪数据、账号与配置；.env 包含加密密钥。${NC}"
echo -e "${RED}   删除后无法恢复（ENCRYPTION_KEY 丢失后即使保留卷中数据也无法解密）！${NC}"
echo ""

# 按 compose 项目标签列出实际存在的数据卷（自动带项目前缀，如 langfuse_langfuse_postgres_data）
FOUND_VOLUMES=$(docker volume ls -q --filter "label=com.docker.compose.project=${PROJECT_NAME}" 2>/dev/null || true)
if [ -n "$FOUND_VOLUMES" ]; then
  echo "$FOUND_VOLUMES" | sed 's/^/  📦 /'
else
  echo -e "  （未发现属于项目 ${PROJECT_NAME} 的数据卷）"
fi
[ -f "$ENV_FILE" ] && echo -e "  🔑 ${ENV_FILE}"
echo ""

read -p "是否删除以上数据卷及 .env？(y/N): " DELETE_DATA
if [[ "$DELETE_DATA" == "y" || "$DELETE_DATA" == "Y" ]]; then
  if [ -n "$FOUND_VOLUMES" ]; then
    docker volume rm $FOUND_VOLUMES 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 已删除 $(echo "$FOUND_VOLUMES" | wc -l) 个数据卷"
  fi
  # 兜底：清理无标签但名称匹配的残留卷（如项目目录改名部署过）
  for vol in "${VOLUMES_TO_REMOVE[@]}"; do
    for candidate in "${PROJECT_NAME}_${vol}" "${vol}"; do
      if docker volume ls --format '{{.Name}}' | grep -q "^${candidate}$"; then
        docker volume rm "$candidate" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} 已删除残留卷: $candidate"
      fi
    done
  done
  if [ -f "$ENV_FILE" ]; then
    rm -f "$ENV_FILE"
    echo -e "  ${GREEN}✓${NC} 已删除: $ENV_FILE"
  fi
else
  echo -e "  ${CYAN}→${NC} 已跳过数据卷与 .env 删除"
fi
echo ""

# ============ 步骤 5/5：Docker 系统级深度清理 ============
echo -e "${CYAN}[步骤 5/5] Docker 系统级深度清理...${NC}"
echo ""
echo -e "此步骤将清理：已停止的容器 / 未使用网络 / 无标签镜像 / 未使用卷 / 构建缓存"
echo -e "${YELLOW}注意：系统级清理作用于整个 Docker，可能影响 GA 主系统之外的其他无关资源，${NC}"
echo -e "${YELLOW}      与主系统共用服务器时请谨慎选择。${NC}"
echo ""
read -p "是否执行 Docker 系统级深度清理？(y/N): " DEEP_CLEAN
if [[ "$DEEP_CLEAN" == "y" || "$DEEP_CLEAN" == "Y" ]]; then
  docker container prune -f 2>/dev/null || true
  docker network prune -f 2>/dev/null || true
  docker image prune -f 2>/dev/null || true
  docker volume prune -f 2>/dev/null || true
  docker builder prune -f 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Docker 系统级深度清理完成"
else
  echo -e "  ${CYAN}→${NC} 已跳过 Docker 系统级清理"
fi

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}[✓] Langfuse 卸载清理完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${CYAN}当前 Docker 资源状态：${NC}"
echo -e "  容器数量: $(docker ps -a -q | wc -l)"
echo -e "  镜像数量: $(docker images -q | wc -l)"
echo -e "  网络数量: $(docker network ls -q | wc -l)"
echo -e "  卷数量:   $(docker volume ls -q | wc -l)"
echo ""
docker system df 2>/dev/null || true
