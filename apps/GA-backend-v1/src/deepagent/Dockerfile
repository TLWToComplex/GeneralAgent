FROM python:3.11-slim-bookworm

ARG APT_MIRROR=https://deb.debian.org
ARG NPM_REGISTRY=https://registry.npmjs.org
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN echo "deb ${APT_MIRROR}/debian/ bookworm main non-free non-free-firmware contrib" > /etc/apt/sources.list && \
    echo "deb ${APT_MIRROR}/debian-security/ bookworm-security main" >> /etc/apt/sources.list && \
    echo "deb ${APT_MIRROR}/debian/ bookworm-updates main non-free non-free-firmware contrib" >> /etc/apt/sources.list && \
    rm -rf /etc/apt/sources.list.d/*

# Install bootstrap tools + Node.js 20.x（基础设施，不列入提示词清单）
#   gcc：供 soffice.py 的 _ensure_shim() 在沙箱禁用 AF_UNIX socket 时现场编译 LD_PRELOAD shim；
#        Docker 默认不禁用故通常不触发、python-slim 也不带 gcc，预装作廉价保险（内部构建依赖，不进提示词）。
RUN apt-get update --allow-releaseinfo-change && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    sudo \
    gcc \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install document/system tools（文档/图像/OCR 工具）
# 清单抽离到 sandbox-apt-packages.txt，与系统提示词第 6 条共用同一份（单一事实来源）。
# 加/删系统工具只改 sandbox-apt-packages.txt 后重建镜像即可，无需改 Dockerfile 或提示词代码。
# 构建上下文 = src/deepagent/（本目录），即 `cd src/deepagent && docker build -t skill-agent:latest .`，
# 故 COPY 用裸文件名（与本 Dockerfile、三个 sandbox-*.txt 同目录）。
COPY sandbox-apt-packages.txt /tmp/sandbox-apt-packages.txt
# tr -d '\r'：清单可能在 Windows 上被编辑成 CRLF；不去掉 \r 会让包名带尾随回车（如 "pandoc\r"），
# 导致 apt-get 找不到包而装不上（即"空的"）。加这道后无论 LF/CRLF 都能正确解析。
RUN apt-get update && \
    pkgs=$(sed 's/#.*//' /tmp/sandbox-apt-packages.txt | tr -d '\r' | grep -vE '^[[:space:]]*$' | tr '\n' ' ') && \
    if [ -n "$pkgs" ]; then apt-get install -y --no-install-recommends $pkgs; fi && \
    rm -rf /var/lib/apt/lists/*

RUN npm config set registry ${NPM_REGISTRY}

# Install global node tools
# 清单抽离到 sandbox-npm-packages.txt，与系统提示词第 6 条共用同一份（单一事实来源）。
# 加/删 npm 包只改 sandbox-npm-packages.txt 后重建镜像即可，无需改 Dockerfile 或提示词代码。
# 构建上下文 = src/deepagent/（本目录），COPY 用裸文件名（与本 Dockerfile 同目录）。
COPY sandbox-npm-packages.txt /tmp/sandbox-npm-packages.txt
RUN pkgs=$(sed 's/#.*//' /tmp/sandbox-npm-packages.txt | grep -vE '^[[:space:]]*$' | tr '\n' ' ') && \
    if [ -n "$pkgs" ]; then npm install -g $pkgs; fi

ENV NODE_PATH=/usr/lib/node_modules

RUN pip config set global.index-url ${PIP_INDEX_URL}

# Upgrade pip to ensure latest dependency resolution
RUN pip install --upgrade pip

# Install Python dependencies
# 清单抽离到 sandbox-requirements.txt，与系统提示词第 6 条共用同一份（单一事实来源）。
# 加/删包只改 sandbox-requirements.txt 后重建镜像即可，无需改 Dockerfile 或提示词代码。
# 构建上下文 = src/deepagent/（本目录），COPY 用裸文件名（与本 Dockerfile 同目录）。
COPY sandbox-requirements.txt /tmp/sandbox-requirements.txt
RUN pip install --no-cache-dir -r /tmp/sandbox-requirements.txt

# Install Playwright browsers and dependencies
RUN playwright install --with-deps chromium && \
    npx agent-browser install && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

CMD ["tail", "-f", "/dev/null"]
