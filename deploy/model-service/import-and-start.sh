#!/bin/bash
##############################################################################
# 模型服务（GPU 版）一键部署脚本 —— 独立于 GA 应用系统
#   一个 compose 编排 5 个服务（4 个 GPU 推理 + 1 个 CPU 语音识别）：
#     llm(Qwen3.8-27B,8666) / embedding(Qwen3-Embedding-4B,6667)
#     reranker(Qwen3-Reranker-4B,6657) / mineru-router(文档解析,18002)
#     funasr(语音识别 ASR,10095/10096,CPU)
# 适用环境：Ubuntu 22.04 LTS（x86_64 / ARM64）+ Docker 29.1.0+ / Compose v2.40.0+
#           + NVIDIA 驱动 + nvidia-container-toolkit
#   脚本通过 uname -m 自动识别架构：
#     x86_64  → docker-compose.yml       + images/*.tar
#     aarch64 → docker-compose.arm64.yml + images/*-arm64.tar
#
# 使用方式：
#   1. 将本目录传输到服务器（如 /data/deploy/model-service/）
#   2. 将对应架构的镜像 tar 放到 images/ 子目录下（ARM64 为 *-arm64.tar）：
#        mineru.tar / vllm-openai-v0.20.0.tar（llm+embedding+reranker 共用）/ funasr.tar
#   3. 将各模型放到对应宿主机目录（脚本会检查完整性，详见 deployment_guide.md）：
#        /data/llm/model/Qwen3.8-27B/
#        /data/embedding/model/Qwen3-Embedding-4B/
#        /data/reranker/model/Qwen3-Reranker-4B/
#        /data/mineru/models/{PDF-Extract-Kit-1___0, MinerU2___5-Pro-2604-1___2B}
#        /data/funasr/models/
#   4. 执行：sudo bash import-and-start.sh
#
# 目录结构：
#   /data/deploy/model-service/
#   ├── docker-compose.yml               # x86_64
#   ├── docker-compose.arm64.yml         # ARM64（aarch64）
#   ├── import-and-start.sh
#   ├── uninstall-and-clean.sh
#   ├── deployment_guide.md
#   ├── mineru/mineru.json          # MinerU 配置（自动分发到 /data/mineru/）
#   └── images/                     # x86 用 *.tar，ARM64 用 *-arm64.tar
#       ├── mineru
#       ├── vllm-openai-v0.20.0          # llm + embedding + reranker（共用）
#       └── funasr                       # funasr（语音识别 ASR）
#
# 脚本流程（5 步）：
#   1/5 环境检查（架构识别 / root / docker / compose / GPU 与 nvidia 运行时 / 端口占用）
#   2/5 创建数据目录 + 分发 mineru.json + 检查各模型完整性
#   3/5 导入 3 个镜像 tar 并统一打标签
#   4/5 docker compose up -d（启动 5 个服务）
#   5/5 轮询各 GPU 服务 /health 等待就绪（funasr 为 websocket 服务，无 HTTP 健康端点）
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

# 镜像文件 → 目标镜像名:标签
# 键为 x86 tar 基础名；ARM64 环境自动改用同名加 -arm64 后缀的 tar（导入后标签一致）
declare -A IMAGE_MAP=(
  ["mineru.tar"]="mineru:latest"
  ["vllm-openai-v0.20.0.tar"]="vllm/vllm-openai:v0.20.0"
  ["funasr.tar"]="funasr:20260520"
)

# 对外服务端口（占用检查）
SERVICE_PORTS=(8666 6667 6657 18002 10095 10096)

# 模型目录检查表：路径|说明（不随部署包分发，需提前放好）
MODEL_DIRS=(
  "/data/llm/model/Qwen3.8-27B|LLM (Qwen3.8-27B)"
  "/data/embedding/model/Qwen3-Embedding-4B|Embedding (Qwen3-Embedding-4B)"
  "/data/reranker/model/Qwen3-Reranker-4B|Reranker (Qwen3-Reranker-4B)"
  "/data/mineru/models/PDF-Extract-Kit-1___0|MinerU Pipeline 模型"
  "/data/mineru/models/MinerU2___5-Pro-2604-1___2B|MinerU VLM 模型"
  "/data/funasr/models|FunASR 语音识别模型"
)

# 需创建的数据目录
DATA_DIRS=(
  "/data/llm/model"
  "/data/embedding/model"
  "/data/reranker/model"
  "/data/mineru/models"
  "/data/funasr/models"
)

# 各服务健康检查地址（容器名 → URL）
# 注：funasr 为 websocket 服务（10095/10096），无 HTTP 健康端点，故不纳入轮询
declare -A HEALTH=(
  ["llm"]="http://localhost:8666/health"
  ["embedding"]="http://localhost:6667/health"
  ["reranker"]="http://localhost:6657/health"
  ["mineru-router"]="http://localhost:18002/health"
)

WAIT_SECONDS=1200   # 最长等待 20 分钟（27B 张量并行加载较慢）

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
echo -e "${CYAN}  模型服务（GPU 版）一键部署脚本${NC}"
echo -e "${CYAN}  llm / embedding / reranker / mineru-router / funasr${NC}"
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
echo -e "  ${GREEN}✓${NC} 系统架构：${ARCH} → compose: ${COMPOSE_FILE##*/} / 镜像 tar: *${TAR_SUFFIX}.tar"
echo -e "  ${GREEN}✓${NC} root / docker / compose / 编排文件 检查通过"

# GPU 硬性检查（本包全部服务均需 GPU）
if ! command -v nvidia-smi &> /dev/null || ! nvidia-smi &> /dev/null; then
  echo -e "${RED}[错误] 未检测到 NVIDIA GPU（nvidia-smi 不可用），本部署包仅支持 GPU 环境${NC}"
  exit 1
fi
echo -e "  ${GREEN}✓${NC} 检测到 NVIDIA GPU："
nvidia-smi --query-gpu=index,name,memory.total --format=csv,noheader | sed 's/^/      /'

GPU_COUNT=$(nvidia-smi -L 2>/dev/null | wc -l)
if [ "$GPU_COUNT" -lt 6 ]; then
  echo -e "${YELLOW}  ⚠ 当前仅 ${GPU_COUNT} 张 GPU，默认编排需要至少 6 张（llm 用 0-3、emb/rer 用 4、mineru 用 5）。${NC}"
  echo -e "${YELLOW}    请调整 ${COMPOSE_FILE##*/} 中各服务的 device_ids 后重试。${NC}"
  exit 1
fi

# nvidia-container-toolkit 检查（容器内使用 GPU 的必要组件）
if ! docker info 2>/dev/null | grep -qi 'nvidia'; then
  echo -e "${RED}[错误] Docker 未注册 nvidia 运行时，请先安装 nvidia-container-toolkit：${NC}"
  echo -e "  ${YELLOW}sudo apt-get install -y nvidia-container-toolkit${NC}"
  echo -e "  ${YELLOW}sudo nvidia-ctk runtime configure --runtime=docker${NC}"
  echo -e "  ${YELLOW}sudo systemctl restart docker${NC}"
  exit 1
fi
echo -e "  ${GREEN}✓${NC} nvidia-container-toolkit 已就绪（共 ${GPU_COUNT} 张 GPU）"

# 端口占用检查
for port in "${SERVICE_PORTS[@]}"; do
  if ss -tlnp 2>/dev/null | grep -q ":${port} " && ! docker ps --format '{{.Ports}}' | grep -q ":${port}->"; then
    echo -e "${RED}[错误] 宿主机端口 ${port} 已被其他进程占用，请释放后重试${NC}"
    exit 1
  fi
done
echo -e "  ${GREEN}✓${NC} 端口检查通过（${SERVICE_PORTS[*]}）"

echo -e "${GREEN}[✓] 环境检查通过${NC}"
echo ""

# ============ 步骤 2/5：数据目录 + 配置分发 + 模型检查 ============
echo -e "${CYAN}[步骤 2/5] 创建数据目录 & 检查模型...${NC}"

for dir in "${DATA_DIRS[@]}"; do
  mkdir -p "$dir"
done
echo -e "  ${GREEN}✓${NC} 数据目录创建完成"

# 分发 mineru.json（已存在则保留不覆盖）
if [ -f "${SCRIPT_DIR}/mineru/mineru.json" ]; then
  if [ -f "/data/mineru/mineru.json" ]; then
    echo -e "  ${YELLOW}→ 已存在，保留不覆盖: /data/mineru/mineru.json${NC}（如需更新请参考包内 mineru/mineru.json）"
  else
    cp "${SCRIPT_DIR}/mineru/mineru.json" /data/mineru/mineru.json
    echo -e "  ${GREEN}✓${NC} mineru/mineru.json → /data/mineru/mineru.json"
  fi
else
  echo -e "  ${YELLOW}⚠ 包内缺少 mineru/mineru.json${NC}"
fi

# 模型完整性检查（模型体积大，不随部署包分发，需提前放好且非空）
MODEL_MISSING=false
for entry in "${MODEL_DIRS[@]}"; do
  path="${entry%%|*}"
  desc="${entry##*|}"
  if [ -d "$path" ] && [ -n "$(ls -A "$path" 2>/dev/null)" ]; then
    echo -e "  ${GREEN}✓${NC} ${desc}: ${path}"
  else
    echo -e "  ${RED}✗ 缺少模型 [${desc}]: ${path}${NC}"
    MODEL_MISSING=true
  fi
done
if [ "$MODEL_MISSING" = true ]; then
  echo -e "${RED}[错误] 模型不完整，对应服务启动后将无法加载。${NC}"
  echo -e "  ${YELLOW}请将模型拷贝到上述目录后重新执行本脚本。${NC}"
  echo -e "  ${YELLOW}（MinerU 模型可在有网环境执行：mineru-models-download -s modelscope -m all）${NC}"
  exit 1
fi

echo -e "${GREEN}[✓] 数据目录与模型检查完成${NC}"
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

echo -e "${GREEN}[✓] 镜像导入完成${NC} — 成功: ${IMPORT_COUNT}, 跳过: ${SKIP_COUNT}, 失败: ${FAIL_COUNT}"
if [ "$FAIL_COUNT" -gt 0 ]; then
  echo -e "${RED}[错误] 存在缺失/导入失败的镜像，请检查 images/ 目录后重新执行脚本${NC}"
  exit 1
fi
echo ""

# ============ 步骤 4/5：启动服务 ============
echo -e "${CYAN}[步骤 4/5] 启动 5 个服务...${NC}"
cd "$SCRIPT_DIR"
docker compose -f "$COMPOSE_FILE" up -d
echo ""

# ============ 步骤 5/5：等待各服务就绪 ============
echo -e "${CYAN}[步骤 5/5] 等待服务就绪（大模型加载较慢，最长等待 $((WAIT_SECONDS/60)) 分钟）...${NC}"
SERVER_IP=$(detect_ip)

declare -A READY
pending=("${!HEALTH[@]}")
elapsed=0
while [ ${#pending[@]} -gt 0 ] && [ $elapsed -lt $WAIT_SECONDS ]; do
  still=()
  for svc in "${pending[@]}"; do
    if curl -sf "${HEALTH[$svc]}" &> /dev/null; then
      READY[$svc]=1
      echo -e "  ${GREEN}✓${NC} ${svc} 就绪"
    else
      still+=("$svc")
    fi
  done
  pending=("${still[@]}")
  if [ ${#pending[@]} -gt 0 ]; then
    sleep 5
    elapsed=$((elapsed + 5))
  fi
done

echo ""
docker compose -f "$COMPOSE_FILE" ps
echo ""

echo -e "${CYAN}============================================${NC}"
if [ ${#pending[@]} -eq 0 ]; then
  echo -e "${GREEN}[✓] 模型服务部署完成，全部服务已就绪！${NC}"
else
  echo -e "${YELLOW}[!] 部署完成，但以下服务健康检查未通过：${pending[*]}${NC}"
  echo -e "    查看日志：docker compose -f ${COMPOSE_FILE} logs -f <服务名>"
fi
echo -e "${CYAN}============================================${NC}"
echo ""
echo -e "${CYAN}服务信息：${NC}"
echo -e "  ├── llm:        http://${SERVER_IP}:8666/v1     模型名: qwen3.8-27b"
echo -e "  ├── embedding:  http://${SERVER_IP}:6667/v1     模型名: Qwen3-Embedding-4B"
echo -e "  ├── reranker:   http://${SERVER_IP}:6657/v1     模型名: Qwen3-Reranker-4B"
echo -e "  ├── mineru:     http://${SERVER_IP}:18002       解析: /file_parse  健康: /health"
echo -e "  └── funasr:     ws://${SERVER_IP}:10095         语音识别(ASR)，websocket（备用端口 10096）"
echo ""
echo -e "${CYAN}接入 GA 应用系统（可选）：${NC}"
echo -e "  ① 知识库模型平台 /data/GA-kb-chat/kb_config.yaml 的 MODEL_PLATFORMS api_base_url："
echo -e "       LLM       → http://${SERVER_IP}:8666/v1"
echo -e "       Embedding → http://${SERVER_IP}:6667/v1"
echo -e "       Rerank    → http://${SERVER_IP}:6657/v1"
echo -e "  ② MinerU 解析链路：kb-chat → ai-doc-processor(:18200/api/parse_to_markdown) → mineru-router(:18002)"
echo -e "       /data/GA-document-processor/config.yaml: mineru.base_url = http://${SERVER_IP}:18002"
echo -e "       /data/GA-kb-chat/kb_config.yaml:         ENABLE_MINERU=true, MINERU_URL=http://${SERVER_IP}:18200/api/parse_to_markdown"
echo -e "  ③ 重启相关服务：cd <GA-app部署目录> && docker compose restart app-ai-doc-processor app-GA-kb-chat"
echo ""
echo -e "${YELLOW}常用命令：${NC}"
echo -e "  查看日志:   docker compose -f ${COMPOSE_FILE} logs -f [服务名]"
echo -e "  重启服务:   docker compose -f ${COMPOSE_FILE} restart [服务名]"
echo -e "  停止全部:   docker compose -f ${COMPOSE_FILE} down"
