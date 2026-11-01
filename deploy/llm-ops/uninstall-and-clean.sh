#!/bin/bash
##############################################################################
# LLM-OPS（大模型集 / 统一网关）一键卸载 & 清理脚本 —— 独立部署包
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64，自动识别架构选择 compose 文件）
#
# 使用方式：sudo bash uninstall-and-clean.sh
#
# 功能（5 步分级清理）：
#   1/5 停止并删除全部容器（llm-mysql / llm-postgres / llm-litellm
#       / llm-prometheus / llm-backend / llm-frontend）
#   2/5 删除相关镜像
#   3/5 清理 Docker 网络（新版为 bridge 网络 llm-net；兜底清理旧版残留）
#   4/5 (可选，需二次确认) 删除包内 data/ 与 logs/（含 MySQL/PostgreSQL 数据）
#       以及旧版部署的 /data/llm-ops-* 目录
#   5/5 (可选，需二次确认) Docker 系统级深度清理
#
# 说明：仅清理 LLM-OPS 栈，不影响 GA-app / model-service / langfuse 及其他服务。
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

# 当前版容器（llm-* 前缀）+ 历史旧版容器名，一并纳入手动清理兜底
CONTAINERS=(
  "llm-mysql"
  "llm-postgres"
  "llm-litellm"
  "llm-prometheus"
  "llm-backend"
  "llm-frontend"
  # 历史旧版：曾用 llm-ops-* 前缀
  "llm-ops-mysql"
  "llm-ops-postgres"
  "llm-ops-litellm"
  "llm-ops-prometheus"
  "llm-ops-backend"
  "llm-ops-frontend"
  # 历史旧版：更早的 bridge 网络时期
  "litellm-app"
  "litellm-prometheus"
  "litellm-db"
)

# 当前版镜像 + llm-app 包内原始标签（:amd64/:arm64）+ 旧版镜像
IMAGES_TO_REMOVE=(
  "llm-backend:latest"
  "llm-frontend:latest"
  "llm-backend:amd64"
  "llm-frontend:amd64"
  "llm-backend:arm64"
  "llm-frontend:arm64"
  "mysql:8.3"
  "postgres:16"
  "docker.litellm.ai/berriai/litellm:main-latest"
  "prom/prometheus:latest"
  "aiwu3-frontend:latest"
  "ai-service-backend:latest"
)

# 新版：包内 data/ 与 logs/；旧版：/data/llm-ops-*
DATA_DIRS=(
  "${SCRIPT_DIR}/data"
  "${SCRIPT_DIR}/logs"
  "/data/llm-ops-backend"
  "/data/llm-ops-front"
  "/data/llm-ops-mid"
)

# ============ 前置检查 ============
echo -e "${RED}============================================${NC}"
echo -e "${RED}  LLM-OPS（统一网关）一键卸载 & 清理${NC}"
echo -e "${RED}============================================${NC}"
echo ""

if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[错误] 请使用 sudo 或 root 用户运行此脚本${NC}"
  exit 1
fi

command -v docker &> /dev/null || { echo -e "${RED}[错误] Docker 未安装${NC}"; exit 1; }

echo -e "${YELLOW}⚠  警告：此操作将停止并删除 LLM-OPS 全部容器和镜像！${NC}"
echo -e "${YELLOW}   如果选择删除数据目录，包内 data/（MySQL + PostgreSQL 数据）与 logs/ 将一并删除，无法恢复！${NC}"
echo -e "${CYAN}   （不影响 GA-app / model-service / langfuse 及其他任何服务）${NC}"
echo ""
read -p "是否继续？(y/N): " CONFIRM
if [[ "$CONFIRM" != "y" && "$CONFIRM" != "Y" ]]; then
  echo -e "${CYAN}已取消操作${NC}"
  exit 0
fi
echo ""

# ============ 步骤 1/5：停止并删除容器 ============
echo -e "${CYAN}[步骤 1/5] 停止并删除容器...${NC}"

if [ -f "$COMPOSE_FILE" ]; then
  cd "$SCRIPT_DIR"
  docker compose -f "$COMPOSE_FILE" down --remove-orphans 2>/dev/null || true
  echo -e "  ${GREEN}✓${NC} Docker Compose 容器已停止并删除"
else
  echo -e "  ${YELLOW}⚠${NC} compose 文件不存在，尝试手动清理容器..."
fi

# 兜底：手动清理列表中仍存在的容器（含旧版容器名）
for c in "${CONTAINERS[@]}"; do
  if docker ps -a --format '{{.Names}}' | grep -q "^${c}$"; then
    docker rm -f "$c" 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 已删除容器: $c"
  fi
done
echo ""

# ============ 步骤 2/5：删除镜像 ============
echo -e "${CYAN}[步骤 2/5] 删除镜像...${NC}"

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

# 新版为 bridge 网络 llm-net（compose down 通常已删除，此处兜底）；
# 同时清理旧版 host 网络时期的残留网络
for NETWORK_NAME in "${PROJECT_NAME}_llm-net" "llm-net" "${PROJECT_NAME}_gateway-net" "${PROJECT_NAME}_default" "gateway-net"; do
  if docker network ls --format '{{.Name}}' | grep -q "^${NETWORK_NAME}$"; then
    docker network rm "$NETWORK_NAME" 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} 已删除网络: $NETWORK_NAME"
  fi
done
echo -e "  ${GREEN}✓${NC} 网络清理完成"
echo ""

# ============ 步骤 4/5：(可选) 删除数据目录 ============
echo -e "${CYAN}[步骤 4/5] 数据目录清理...${NC}"
echo ""
echo -e "${RED}⚠  警告：以下目录包含 MySQL / PostgreSQL 数据与运行日志，删除后无法恢复！${NC}"
echo -e "${YELLOW}   如计划重新部署并复用数据，建议选择 N 跳过本步骤。${NC}"
echo ""
for dir in "${DATA_DIRS[@]}"; do
  [ -d "$dir" ] && echo -e "  📁 $dir ($(du -sh "$dir" 2>/dev/null | awk '{print $1}'))"
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
  echo -e "  ${CYAN}→${NC} 已跳过数据目录删除（数据已保留）"
fi
echo ""

# ============ 步骤 5/5：Docker 系统级深度清理 ============
echo -e "${CYAN}[步骤 5/5] Docker 系统级深度清理...${NC}"
echo ""
echo -e "此步骤将清理：已停止的容器 / 未使用网络 / 无标签镜像 / 未使用卷 / 构建缓存"
echo -e "${YELLOW}注意：系统级清理作用于整个 Docker，与其他模块共用服务器时请谨慎选择。${NC}"
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
echo -e "${GREEN}[✓] LLM-OPS 卸载清理完成！${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "${CYAN}当前 Docker 资源状态：${NC}"
echo -e "  容器数量: $(docker ps -a -q | wc -l)"
echo -e "  镜像数量: $(docker images -q | wc -l)"
echo -e "  网络数量: $(docker network ls -q | wc -l)"
echo -e "  卷数量:   $(docker volume ls -q | wc -l)"
echo ""
docker system df 2>/dev/null || true
