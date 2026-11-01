#!/bin/bash
##############################################################################
# GA 系统 Docker 一键部署脚本（镜像导入 + 配置分发 + 启动）
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64）+ Docker 29.1.0+ / Compose v2.40.0+
#   脚本通过 uname -m 自动识别架构：
#     x86_64  → docker-compose.yml       + images/*.tar
#     aarch64 → docker-compose.arm64.yml + images/*-arm64.tar
#
# 使用方式：
#   1. 将整个部署目录传输到服务器（如 /data/deploy/GA-app/）
#   2. 将对应架构的 .tar 镜像文件放到 images/ 子目录下
#   3. 执行：sudo bash import-and-start.sh
#
# 目录结构：
#   /data/deploy/GA-app/
#   ├── docker-compose.yml              # x86_64
#   ├── docker-compose.arm64.yml        # ARM64（aarch64）
#   ├── import-and-start.sh
#   ├── uninstall-and-clean.sh
#   ├── sql/ai_service.sql
#   ├── neo4j/                        # Neo4j 插件 jar（apoc.jar + graph-data-science.jar，
#   │                                 #   脚本自动分发到 /data/neo4j/plugins/，缺失会导致报错）
#   ├── GA-mcp/.docker.env
#   ├── GA-kb-chat/kb_config.yaml
#   ├── GA-service-backend/{config.yaml, skills_repo/}
#   ├── GA-document-processor/config.yaml
#   ├── GA-frontend-v2/runtime-config.json
#   └── images/                         # x86 用 *.tar，ARM64 用 *-arm64.tar
#       ├── mysql / neo4j / elasticsearch
#       ├── GA-kb-chat / GA-service-backend
#       ├── GA-document-processor / GA-frontend-v2
#       ├── mcp-chart-streamable-http          # 图表 MCP
#       └── skill-agent                        # 沙盒镜像包
#
# 脚本流程（5 步）：
#   1/5 环境检查（架构识别 / root / docker / compose）
#   2/5 创建数据目录 + 分发配置文件（已存在的配置不覆盖）
#   3/5 导入镜像并统一打标签
#   4/5 docker compose up -d（首次创建时 mid-neo4j 可能崩溃重启一次，
#       脚本自动等待其 healthy 后补启依赖服务，无需二次执行）
#   5/5 部署结果验证
#
# 说明：GPU 模型服务（LLM/Embedding/Reranker/MinerU）已拆分至独立的 model-service 部署包（../model-service/），
#       Langfuse 监控为独立部署包（../langfuse/），均与本脚本互不影响。
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

# ============ 镜像文件 → 目标镜像名:标签 映射表 ============
# 键为 x86 tar 基础名；ARM64 环境自动改用同名加 -arm64 后缀的 tar（导入后标签一致）
declare -A IMAGE_MAP=(
  ["mysql.tar"]="mid/mysql:8.0.45"
  ["neo4j.tar"]="mid/neo4j:2026-05-15"
  ["elasticsearch.tar"]="mid/elasticsearch:9.1.6"
  ["GA-frontend-v2.tar"]="app/ga-frontend-v2:2026-05-15"
  ["GA-kb-chat.tar"]="app/ga-kb-chat:2026-05-15"
  ["GA-service-backend.tar"]="app/ga-service-backend:2026-05-15"
  ["GA-document-processor.tar"]="app/ga-document-processor:2026-05-15"
  ["mcp-chart-streamable-http.tar"]="mcp-server-chart-streamable-http:1.0.0"
  ["skill-agent.tar"]="skill-agent:latest"
)

# ============ 配置文件分发表：包内路径|目标路径 ============
CONFIG_MAP=(
  "GA-kb-chat/kb_config.yaml|/data/GA-kb-chat/kb_config.yaml"
  "GA-service-backend/config.yaml|/data/GA-service-backend/config.yaml"
  "GA-document-processor/config.yaml|/data/GA-document-processor/config.yaml"
  "GA-frontend-v2/runtime-config.json|/data/GA-frontend-v2/runtime-config.json"
  "GA-mcp/.docker.env|/data/GA-mcp/.docker.env"
)

# ============ 工具函数 ============
# 复制配置文件：目标不存在才复制，避免覆盖线上已修改的配置
copy_if_absent() {
  local src="$1" dst="$2"
  if [ ! -f "$src" ]; then
    echo -e "  ${YELLOW}⚠ 包内缺少配置: ${src}${NC}"
    return 0
  fi
  if [ -f "$dst" ]; then
    echo -e "  ${YELLOW}→ 已存在，保留不覆盖: ${dst}${NC}（如需更新请参考包内 ${src}）"
  else
    mkdir -p "$(dirname "$dst")"
    cp "$src" "$dst"
    echo -e "  ${GREEN}✓${NC} ${src} → ${dst}"
  fi
}

##############################################################################
echo -e "${CYAN}============================================${NC}"
echo -e "${CYAN}  GA 系统 Docker 一键部署脚本${NC}"
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
[ -d "$IMAGE_DIR" ] || { echo -e "${RED}[错误] 镜像目录不存在: ${IMAGE_DIR}${NC}"; exit 1; }
[ -f "$COMPOSE_FILE" ] || { echo -e "${RED}[错误] 缺少 ${COMPOSE_FILE}${NC}"; exit 1; }
echo -e "  ${GREEN}✓${NC} 系统架构：${ARCH} → compose: ${COMPOSE_FILE##*/} / 镜像 tar: *${TAR_SUFFIX}.tar"
echo -e "  ${GREEN}✓${NC} root / docker / compose / 部署文件 检查通过"
echo -e "${GREEN}[✓] 环境检查通过${NC}"
echo ""

# ============ 步骤 2/5：创建数据目录 + 分发配置 ============
echo -e "${CYAN}[步骤 2/5] 创建数据目录 & 分发配置文件...${NC}"

DATA_DIRS=(
  "/data/mysql"
  "/data/mysql-init"
  "/data/neo4j/data"
  "/data/neo4j/logs"
  "/data/neo4j/import"
  "/data/neo4j/plugins"
  "/data/elasticsearch/data"
  "/data/elasticsearch/plugins"
  "/data/GA-kb-chat/data/knowledge_base"
  "/data/GA-service-backend/skills_repo"
  "/data/GA-service-backend/agent_memory"
  "/data/GA-document-processor"
  "/data/GA-frontend-v2"
  "/data/GA-mcp"
)
for dir in "${DATA_DIRS[@]}"; do
  mkdir -p "$dir"
done
echo -e "  ${GREEN}✓${NC} 数据目录创建完成（/data/*）"

# Neo4j / Elasticsearch 数据与插件目录需要写权限
chmod 777 /data/neo4j/data /data/neo4j/plugins
chmod 777 /data/elasticsearch/data /data/elasticsearch/plugins

# Neo4j 插件 jar（apoc / graph-data-science）：必须放入 /data/neo4j/plugins 否则报错；
# 插件与镜像版本强绑定，每次执行都用包内版本覆盖更新
if [ -d "${SCRIPT_DIR}/neo4j" ]; then
  for jar in "${SCRIPT_DIR}/neo4j/"*.jar; do
    [ -f "$jar" ] || continue
    cp -f "$jar" /data/neo4j/plugins/
    echo -e "  ${GREEN}✓${NC} Neo4j 插件: $(basename "$jar") → /data/neo4j/plugins/"
  done
else
  echo -e "  ${YELLOW}⚠ 包内缺少 neo4j/ 插件目录（apoc.jar / graph-data-science.jar），Neo4j 相关功能会报错${NC}"
fi

# MySQL 初始化 SQL（仅在首次初始化空数据目录时执行）
if [ -f "${SCRIPT_DIR}/sql/ai_service.sql" ]; then
  cp "${SCRIPT_DIR}/sql/ai_service.sql" /data/mysql-init/ai_service.sql
  echo -e "  ${GREEN}✓${NC} ai_service.sql → /data/mysql-init/"
else
  echo -e "  ${YELLOW}⚠ 缺少 sql/ai_service.sql，跳过数据库初始化文件${NC}"
fi

# 分发各服务配置文件（已存在则保留）
for entry in "${CONFIG_MAP[@]}"; do
  copy_if_absent "${SCRIPT_DIR}/${entry%%|*}" "${entry##*|}"
done

# skills_repo：目标为空才复制，保护线上已有技能数据
if [ -d "${SCRIPT_DIR}/GA-service-backend/skills_repo" ]; then
  if [ -z "$(ls -A /data/GA-service-backend/skills_repo 2>/dev/null)" ]; then
    cp -r "${SCRIPT_DIR}/GA-service-backend/skills_repo/." /data/GA-service-backend/skills_repo/
    echo -e "  ${GREEN}✓${NC} skills_repo → /data/GA-service-backend/skills_repo/"
  else
    echo -e "  ${YELLOW}→ skills_repo 已存在，保留不覆盖${NC}"
  fi
fi

# deepagent.db（DeepAgent SQLite 数据库 + WAL 附属文件）：线上已存在则一律不覆盖；
# bind 挂载目标必须是文件，缺失时创建空文件占位（否则 Docker 会自动建成同名目录导致 SQLite 无法使用）
for dbf in deepagent.db deepagent.db-shm deepagent.db-wal; do
  src="${SCRIPT_DIR}/GA-service-backend/${dbf}"
  dst="/data/GA-service-backend/${dbf}"
  if [ -f "$dst" ]; then
    echo -e "  ${YELLOW}→ 已存在，保留不覆盖: ${dst}${NC}"
  elif [ -f "$src" ]; then
    cp "$src" "$dst"
    echo -e "  ${GREEN}✓${NC} ${dbf} → ${dst}"
  else
    touch "$dst"
    echo -e "  ${YELLOW}⚠ 包内缺少 ${dbf}，已创建空文件占位: ${dst}${NC}"
  fi
done

echo -e "${GREEN}[✓] 数据目录与配置分发完成${NC}"
echo ""

# ============ 步骤 3/5：导入镜像 ============
echo -e "${CYAN}[步骤 3/5] 导入 Docker 镜像...${NC}"

IMPORT_COUNT=0
SKIP_COUNT=0
FAIL_COUNT=0

for TAR_FILE in "${!IMAGE_MAP[@]}"; do
  ACTUAL_TAR="${TAR_FILE%.tar}${TAR_SUFFIX}.tar"      # arm64 环境自动使用 *-arm64.tar
  TAR_PATH="${IMAGE_DIR}/${ACTUAL_TAR}"
  TARGET_IMAGE="${IMAGE_MAP[$TAR_FILE]}"

  if [ ! -f "$TAR_PATH" ]; then
    echo -e "  ${YELLOW}⚠ 跳过${NC} ${ACTUAL_TAR} (文件不存在)"
    SKIP_COUNT=$((SKIP_COUNT + 1))
    continue
  fi

  echo -e "  ${CYAN}→${NC} 导入 ${ACTUAL_TAR} ..."
  LOADED_OUTPUT=$(docker load -i "$TAR_PATH" 2>&1) || {
    echo -e "  ${RED}✗ 导入失败${NC}: ${LOADED_OUTPUT}"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    continue
  }

  # 解析 docker load 输出并统一打标签
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

echo -e "${GREEN}[✓] 镜像导入完成${NC} — 成功: ${IMPORT_COUNT}, 跳过: ${SKIP_COUNT}, 失败: ${FAIL_COUNT}"
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo -e "${RED}[错误] 存在导入失败的镜像，请检查 images/ 目录后重新执行脚本${NC}"
  exit 1
fi
echo ""

# ============ 步骤 4/5：启动服务 ============
echo -e "${CYAN}[步骤 4/5] 启动服务...${NC}"
cd "$SCRIPT_DIR"
# 说明：mid-neo4j 容器首次创建时，entrypoint 可能出现一次 apoc.conf (Permission denied)
# 崩溃并由 restart: unless-stopped 自动重启恢复（详见 deployment_guide.md Q7）。
# 该一次性崩溃会让首轮 up -d 在等待 service_healthy 时报错退出，导致依赖它的
# 前后端/kb-chat 等应用服务未启动。此处容忍首轮失败 → 轮询等待 neo4j 转为
# healthy → 再执行一次 up -d（幂等，已运行的服务不受影响），保证一次脚本即可完成部署。
set +e
docker compose -f "$COMPOSE_FILE" up -d
UP_RC=$?
set -e

if [ "$UP_RC" -ne 0 ]; then
  echo -e "  ${YELLOW}⚠ 首轮启动未完全成功（常见于 mid-neo4j 首次创建时崩溃自动重启），等待其转为 healthy...${NC}"

  NEO4J_TIMEOUT=300
  NEO4J_WAITED=0
  while true; do
    NEO4J_STATUS="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' mid-neo4j 2>/dev/null || echo missing)"
    if [ "$NEO4J_STATUS" = "healthy" ]; then
      break
    fi
    if [ "$NEO4J_WAITED" -ge "$NEO4J_TIMEOUT" ]; then
      echo -e "  ${RED}[错误] mid-neo4j 在 ${NEO4J_TIMEOUT}s 内未转为 healthy（当前状态: ${NEO4J_STATUS}）${NC}"
      echo -e "  ${RED}请查看日志定位: docker logs --tail 100 mid-neo4j${NC}"
      exit 1
    fi
    echo -e "  ${CYAN}→${NC} mid-neo4j: ${NEO4J_STATUS}（已等待 ${NEO4J_WAITED}s / ${NEO4J_TIMEOUT}s）"
    sleep 10
    NEO4J_WAITED=$((NEO4J_WAITED + 10))
  done
  echo -e "  ${GREEN}✓${NC} mid-neo4j 已就绪（healthy），补启其余服务..."

  # 重新执行 up -d：幂等操作，仅启动尚未运行的依赖服务
  docker compose -f "$COMPOSE_FILE" up -d
fi
echo ""

# ============ 步骤 5/5：部署验证 ============
echo -e "${CYAN}[步骤 5/5] 部署结果验证...${NC}"
echo ""
docker compose -f "$COMPOSE_FILE" ps
echo ""

echo -e "${CYAN}============================================${NC}"
echo -e "${GREEN}[✓] 部署完成！${NC}"
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${YELLOW}部署后必查：${NC}"
echo -e "  • /data/GA-frontend-v2/runtime-config.json 中的 API_BASE_URL / KB_BASE_URL 改为实际服务器 IP"
echo -e "  • /data/GA-mcp/.docker.env 中的 VIS_REQUEST_SERVER 改为 http://<服务器IP>:8999/render-chart"
echo -e "  • 如启用 MinerU 解析（需先通过 model 包部署 mineru-router:18002）："
echo -e "      - /data/GA-document-processor/config.yaml 中 mineru.base_url 指向 http://<服务器IP>:18002"
echo -e "      - /data/GA-kb-chat/kb_config.yaml 中 ENABLE_MINERU: true、MINERU_URL 指向 http://<服务器IP>:18200/api/parse_to_markdown"
echo -e "  修改配置后执行: docker compose -f ${COMPOSE_FILE} restart <服务名>"
echo ""
echo -e "${CYAN}服务端口一览：${NC}"
echo -e "  ├── MySQL:              13306"
echo -e "  ├── Neo4j (HTTP/Bolt):  17474 / 17687"
echo -e "  ├── Elasticsearch:      19200"
echo -e "  ├── GA-kb-chat:       17861"
echo -e "  ├── GA-backend:       18038"
echo -e "  ├── ai-doc-processor:   18200"
echo -e "  ├── GA-frontend:      15174"
echo -e "  └── mcp-server-chart:   1122 (MCP) / 8999 (图表渲染)"
echo -e "  （LLM:8666 / Embedding:6667 / Reranker:6657 / mineru-router:18002 由独立的 model-service 部署包提供，见 ../model-service/deployment_guide.md）"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo -e "  查看日志:   docker compose -f ${COMPOSE_FILE} logs -f [服务名]"
echo -e "  重启服务:   docker compose -f ${COMPOSE_FILE} restart [服务名]"
echo -e "  停止全部:   docker compose -f ${COMPOSE_FILE} down"
