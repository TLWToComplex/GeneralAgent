FROM node:20-slim

# 设置工作目录
WORKDIR /workspace

# 配置npm使用淘宝镜像源
RUN npm config set registry https://registry.npmmirror.com

# 首先处理证书和镜像源问题
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

# 刷新字体缓存
RUN fc-cache -f -v

# 拷贝依赖配置和源码
COPY package.json tsconfig.json ./
COPY src ./src

# 安装依赖
RUN npm install

# 安装 pm2 和 mcp-server-chart 全局包(0.7.1版本)
RUN npm install -g pm2 @antv/mcp-server-chart@0.7.1

# 设置环境变量（也可以在 docker run 时传）
ENV VIS_REQUEST_SERVER=http://127.0.0.1:8999/render-chart
# 确保新版本mcp-server-chart能使用本地渲染服务
ENV COMPATIBILITY_MODE=true

# 设置服务端口
EXPOSE 8999
# mcp-server-chart 监听1122端口
EXPOSE 1122

# 复制 pm2 配置文件
COPY ecosystem.config.js ./

# 启动 pm2
CMD ["pm2-runtime", "ecosystem.config.js"]
