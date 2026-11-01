#!/bin/bash
##############################################################################
# GA 系统 Docker 一键卸载 & 深度清理脚本
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64，自动识别架构选择 compose 文件）
#
# 使用方式：sudo bash uninstall-and-clean.sh
#
# 功能（5 步分级清理）：
#   1/5 停止并删除所有 GA 应用容器
#   2/5 删除导入的 Docker 镜像（9 个）
#   3/5 清理 Docker 网络
#   4/5 (可选，需二次确认) 删除数据持久化目录
#   5/5 (可选，需二次确认) Docker 系统级深度清理
#
# 说明：仅清理 GA 应用栈；MinerU（model 包）与 Langfuse（langfuse 包）
#       请使用各自目录下的 uninstall-and-clean.sh 卸载。
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

# 按架构选择部署时使用的 compose 文件（两者服务定义一致，缺失时自动回退到另一份）
ARCH="$(uname -m)"
case "$ARCH" in
  aarch64|arm64) COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.arm64.yml" ;;
  *)             COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml" ;;
esac
[ -f "$COMPOSE_FILE" ] || COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
[ -f "$COMPOSE_FILE" ] || COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.arm64.yml"

# ============ 需要清理的镜像列表 ============
IMAGES_TO_REMOVE=(
  "mid/mysql:8.0.45"
  "mid/neo4j:2026-05-15"
  "mid/elasticsearch:9.1.6"
  "app/ga-kb-chat:2026-05-15"
  "app/ga-service-backend:2026-05-15"
  "app/ga-document-processor:2026-05-15"
  "app/ga-frontend-v2:2026-05-15"
  "mcp-server-chart-streamable-http:1.0.0"
  "skill-agent:latest"
)

# ============ 数据持久化目录 ============
DATA_DIRS=(
  "/data/mysql"
  "/data/mysql-init"
  "/data/neo4j"
  "/data/elasticsearch"
  "/data/GA-kb-chat"
  "/data/GA-service-backend"
  "/data/GA-document-processor"
  "/data/GA-frontend-v2"
  "/data/GA-mcp"
)

# ============ 前置检查 ============
echo -e "${RED}============================================${NC}"
echo -e "${RED}  GA 系统 Docker 一键卸载 & 深度清理${NC}"
echo -e "${RED}============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[错误] 请使用 sudo 或 root 用户运行此脚本${NC}"
  exit 1
fi

command -v docker &> /dev/null || { echo -e "${RED}[错误] Docker 未安装${NC}"; exit 1; }

echo -e "${YELLOW}⚠  警告：此操作将停止并删除所有 GA 服务容器和镜像！${NC}"
echo -e "${YELLOW}   如果选择删除数据目录，所有持久化数据将永久丢失！${NC}"
echo ""
read -p "是否继续？(y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo -e "${CYAN}已取消操作${NC}"
  exit 0
fi
echo ""

# ============ 步骤 1/5：停止并删除容器 ============
echo -e "${CYAN}[步骤 1/5] 停止并删除所有 GA 容器...${NC}"

if [ -f "$COMPOSE_FILE" ]; then
  cd "$SCRIPT_DIR"
  docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Docker Compose 容器已停止并删除"
else
  echo -e "  ${YELLOW}⚠${NC} compose 文件不存在，尝试手动清理容器..."
  CONTAINERS=(
    "mid-mysql"
    "mid-neo4j"
    "mid-elasticsearch"
    "app-GA-kb-chat"
    "app-GA-service-backend"
    "app-ai-doc-processor"
    "app-GA-frontend-v2"
    "app-mcp-server-chart"
  )
  for container in "${CONTAINERS[@]}"; do
    if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
      docker rm -f "$container" 2>/dev/null || true
      echo -e "  ${GREEN}✓${NC} 已删除容器: $container"
    fi
  done
fi
echo ""

# ============ 步骤 2/5：删除导入的镜像 ============
echo -e "${CYAN}[步骤 2/5] 删除导入的 Docker 镜像...${NC}"

for image in "${IMAGES_TO_REMOVE[@]}"; do
  if docker images --format '{{.Repository}}:{{.Tag}}' | grep -q "^${image}$"; then
    docker rmi "$image" 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 已删除镜像: $image"
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

# compose down 正常会删除网络，此处兜底清理（网络名 = 部署目录名_GA-net）
NETWORK_NAME="${PROJECT_NAME}_GA-net"
if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
  docker network rm "$NETWORK_NAME" 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} 已删除网络: $NETWORK_NAME"
else
  echo -e "  ${GREEN}✓${NC} 网络已由 compose down 清理"
fi
echo ""

# ============ 步骤 4/5：(可选) 删除数据持久化目录 ============
echo -e "${CYAN}[步骤 4/5] 数据持久化目录清理...${NC}"
echo ""
echo -e "${RED}⚠  警告：以下目录包含数据库数据、模型、配置文件等重要数据！删除后无法恢复！${NC}"
echo ""
for dir in "${DATA_DIRS[@]}"; do
  [ -d "$dir" ] && echo -e "  📁 $dir"
done
echo ""
read -p "是否删除以上数据目录？(y/N): " DELETE_DATA
if [[ "$DELETE_DATA" == "y" || "$DELETE_DATA" == "Y" ]]; then
  for dir in "${DATA_DIRS[@]}"; do
    if [ -d "$dir" ]; then
      rm -rf "$dir"
      echo -e "  ${GREEN}✓${NC} 已删除: $dir"
    fi
  done
else
  echo -e "  ${CYAN}→${NC} 已跳过数据目录删除"
fi
echo ""

# ============ 步骤 5/5：Docker 系统级深度清理 ============
echo -e "${CYAN}[步骤 5/5] Docker 系统级深度清理...${NC}"
echo ""
echo -e "此步骤将清理：已停止的容器 / 未使用网络 / 无标签镜像 / 未使用卷 / 构建缓存"
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
echo -e "${GREEN}[✓] GA 系统卸载清理完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${CYAN}当前 Docker 资源状态：${NC}"
echo -e "  容器数量: $(docker ps -a -q | wc -l)"
echo -e "  镜像数量: $(docker images -q | wc -l)"
echo -e "  网络数量: $(docker network ls -q | wc -l)"
echo -e "  卷数量:   $(docker volume ls -q | wc -l)"
echo ""
docker system df 2>/dev/null || true
