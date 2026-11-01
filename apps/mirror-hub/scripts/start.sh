#!/usr/bin/env bash
# MirrorHub 一键启动（内网离线部署）
#
#   ./scripts/start.sh
#
# 首次运行会自动从 .env.example 生成 .env，并把 change-me-* 占位符替换为
# 随机强密钥（MIRRORHUB_ENV=production 下后端会拒绝弱凭据启动）。
#
# 流程：准备 .env → 选择 compose 命令 → 加载镜像 → 启动服务 →
#       对齐 devpi root 密码并创建可写索引 → 轮询 /api/health 直到就绪
set -euo pipefail
cd "$(dirname "$0")/.."

# ---------------------------------------------------------------- 0. 准备 .env
if [ ! -f .env ]; then
  if [ ! -f .env.example ]; then
    echo "缺少 .env 与 .env.example，无法继续" >&2
    exit 1
  fi
  echo "[0/5] 未找到 .env，从 .env.example 生成并填入随机密钥..."

  cp .env.example .env

  # 用 openssl 生成随机密钥；没有 openssl 时退回 /dev/urandom
  gen_secret() {
    if command -v openssl >/dev/null 2>&1; then
      openssl rand -hex 24
    else
      head -c 24 /dev/urandom | od -An -tx1 | tr -d ' \n'
    fi
  }

  set_kv() {  # set_kv KEY VALUE —— 替换 .env 中该键的值（没有则追加）
    local key="$1" val="$2"
    if grep -qE "^${key}=" .env; then
      # 用 | 作分隔符，避免值里出现 / 时出错
      sed -i.bak "s|^${key}=.*|${key}=${val}|" .env && rm -f .env.bak
    else
      printf '%s=%s\n' "$key" "$val" >> .env
    fi
  }

  set_kv SECRET_KEY          "$(gen_secret)"
  set_kv ADMIN_TOKENS        "mirror-admin-$(gen_secret)"
  set_kv POSTGRES_PASSWORD   "$(gen_secret)"
  set_kv DEVPI_PASSWORD      "$(gen_secret)"
  set_kv VERDACCIO_PASSWORD  "$(gen_secret)"

  # SERVER_IP 供客户端访问与 verdaccio tarball 地址改写使用。
  # 无法可靠自动探测内网 IP，先填本机可达地址，并提示用户按需修改。
  if grep -qE '^SERVER_IP=change-me' .env; then
    set_kv SERVER_IP "$(hostname -I 2>/dev/null | awk '{print $1}')"
    [ -n "$(grep -E '^SERVER_IP=' .env | cut -d= -f2)" ] || set_kv SERVER_IP "localhost"
    echo "      SERVER_IP 已设为 $(grep -E '^SERVER_IP=' .env | cut -d= -f2)"
    echo "      ⚠ 若内网客户端用其他地址访问，请修改 .env 的 SERVER_IP 后重启"
  fi
  echo "      已写入 .env"
else
  echo "[0/5] 使用已有 .env"
fi

# 检查是否还有未替换的占位符
# 只匹配「以 KEY=change-me- 开头」的赋值行，避免注释中出现的同名字样造成误判
if grep -qE '^[A-Za-z_][A-Za-z0-9_]*=change-me-' .env; then
  echo "" >&2
  echo "⚠  .env 中仍存在未替换的占位符：" >&2
  grep -nE '^[A-Za-z_][A-Za-z0-9_]*=change-me-' .env >&2
  echo "" >&2
  echo "   请先修改这些项，否则后端会拒绝启动。" >&2
  echo "   若只想快速试用，可执行：" >&2
  echo "     sed -i 's|^SERVER_IP=.*|SERVER_IP=localhost|' .env" >&2
  exit 1
fi

# ------------------------------------------------------------ 1. 选择 compose
if docker compose version >/dev/null 2>&1; then
  DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  DC="docker-compose"
else
  echo "未找到 docker compose（需要 docker compose v2 或 docker-compose v1）" >&2
  exit 1
fi
echo "使用 compose 命令: $DC"

mkdir -p data

# ------------------------------------------------------------- 2. 加载镜像
echo "[1/5] 加载镜像..."
loaded=0
for f in images/*.tar; do
  [ -e "$f" ] || continue
  echo "      loading $(basename "$f")"
  docker load -i "$f" >/dev/null
  loaded=$((loaded+1))
done
if [ "$loaded" -eq 0 ]; then
  echo "images/ 下没有 .tar 文件，跳过加载（假定镜像已存在）"
else
  echo "      已加载 $loaded 个镜像"
fi

# --------------------------------------------------------------- 3. 启动
echo "[2/5] 启动服务..."
$DC up -d

# ------------------------------------------- 4. devpi 密码对齐与可写索引
# 镜像内置数据由构建期初始化，root 密码与 .env 中的 DEVPI_PASSWORD 可能不一致；
# 这里统一对齐，并创建导入用的可写索引 root/local。
echo "[3/5] 初始化 devpi..."
set -a; . ./.env; set +a
DEVPI_PASSWORD="${DEVPI_PASSWORD:-}"
DEVPI_USER="${DEVPI_USER:-root}"

for i in $(seq 1 30); do
  if docker exec mirrorhub-devpi python -c \
      "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:3141/+status',timeout=5).status==200 else 1)" \
      >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

docker exec -e DEVPI_USER="$DEVPI_USER" -e DEVPI_PASSWORD="$DEVPI_PASSWORD" mirrorhub-devpi \
  python - <<'PY' || echo "      (devpi 初始化跳过，可稍后重试)"
import base64, json, os, urllib.error, urllib.request

USER = os.environ.get("DEVPI_USER", "root")
PWD  = os.environ.get("DEVPI_PASSWORD", "")
BASE = "http://127.0.0.1:3141"

def call(path, payload=None, auth=None, method="GET", timeout=15):
    h = {"Accept": "application/json"}
    if auth:
        h["X-Devpi-Auth"] = auth
    data = json.dumps(payload).encode() if payload is not None else None
    if data is not None:
        h["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    return urllib.request.urlopen(req, timeout=timeout)

# 登录：先试配置的密码，失败则试空密码（全新 devpi 的 root 无密码）
token = None
for pw in (PWD, ""):
    try:
        r = json.loads(call("/+login", {"user": USER, "password": pw}, method="POST").read())
        token = r["result"]["password"]
        break
    except urllib.error.HTTPError:
        continue

if not token:
    print("      devpi 登录失败，跳过后处理")
    raise SystemExit(0)

auth = base64.b64encode(f"{USER}:{token}".encode()).decode()

# 若用了空密码登录，则把密码设为 .env 中配置的值
if PWD:
    try:
        call(f"/{USER}", {"password": PWD}, auth=auth, method="PATCH")
    except urllib.error.HTTPError:
        pass
    try:
        r = json.loads(call("/+login", {"user": USER, "password": PWD}, method="POST").read())
        auth = base64.b64encode(f"{USER}:{r['result']['password']}".encode()).decode()
    except urllib.error.HTTPError:
        pass

# 创建可写 stage 索引 root/local（devpi 不允许往 mirror 索引上传）
try:
    call("/root/local")
    print("      root/local 已存在")
except urllib.error.HTTPError as e:
    if e.code == 404:
        call("/root/local", {"type": "stage", "bases": ["root/pypi"]}, auth=auth, method="PUT")
        print("      已创建可写索引 root/local")
    else:
        print(f"      检查 root/local 返回 {e.code}")

print("      devpi 就绪")
PY

# --------------------------------------------------------------- 5. 健康检查
echo "[4/5] 等待服务就绪..."
PORT="${NGINX_PORT:-80}"
ok=0
for i in $(seq 1 60); do
  if curl -fsS "http://127.0.0.1:${PORT}/api/health" >/dev/null 2>&1; then
    ok=1
    break
  fi
  sleep 3
done

echo "[5/5] 完成"
echo ""
if [ "$ok" -eq 1 ]; then
  echo "  健康检查:"
  curl -fsS "http://127.0.0.1:${PORT}/api/health" || true
  echo ""
else
  echo "  ⚠ 健康检查未通过，请查看日志：$DC logs -f backend" >&2
fi
echo ""
echo "  管理界面 : http://${SERVER_IP}:${PORT}/"
echo "  登录 token: ${ADMIN_TOKENS}"
echo ""
echo "  客户端接入:"
echo "    pip config set global.index-url http://${SERVER_IP}:${PORT}/pypi/root/local/+simple/"
echo "    pip config set global.trusted-host ${SERVER_IP}"
echo "    npm config set registry http://${SERVER_IP}:${PORT}/npm/"
echo ""
echo "  说明：镜像初始为空，需先导入依赖（见 INSTALL.md「填充依赖树」）。"