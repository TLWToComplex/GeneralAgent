FROM node:20-slim

WORKDIR /workspace

RUN npm config set registry https://registry.npmmirror.com

RUN apt-get update || true && \
    apt-get install -y --no-install-recommends ca-certificates && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb http://mirrors.aliyun.com/debian-security bookworm-security main contrib non-free" >> /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    make \
    g++ \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    fontconfig \
    fonts-noto-cjk \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

RUN fc-cache -f -v

COPY package.json tsconfig.json ./
COPY ecosystem.config.js ./
COPY src ./src

RUN npm install
RUN npm install -g pm2 @antv/mcp-server-chart@0.9.0

ENV VIS_REQUEST_SERVER=http://127.0.0.1:8999/render-chart
ENV COMPATIBILITY_MODE=true

EXPOSE 8999
EXPOSE 1122

CMD ["pm2-runtime", "ecosystem.config.js"]
