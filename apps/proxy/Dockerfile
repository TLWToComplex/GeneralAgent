# dsh 前置代理镜像
# 注意：必须用 host 网络模式运行（--network host），
# 因为 proxy 需要访问宿主机 127.0.0.1 上绑定的 dsh 容器端口。
FROM node:20-slim

WORKDIR /app

# 先拷贝依赖清单，利用 Docker 层缓存加速构建
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# 拷贝应用代码（配置不进镜像：运行时把 config.js 挂进来）
COPY server.js config.example.js ./

EXPOSE 80

# ---- 配置 ----
# 配置的唯一来源是 config.js（CommonJS 模块，模板见 config.example.js），
# 运行时挂载即可，不需要重建镜像：
#   docker run -d --name dsh-proxy --network host \
#     -v /opt/dsh/proxy-config.js:/app/config.js \
#     -v /opt/dsh/tokens.d:/app/tokens.d \
#     dsh-proxy
# 首次启动若没挂 config.js，会打印「找不到配置文件」并退出（不会带着默认值裸跑）。
# 注意：容器内没有登录页 —— 登录全部在前端完成，本代理只做「识别 → 校验 → 转发」。

# node:20-slim 默认以 root 运行，可直接绑定 80 端口
CMD ["node", "server.js"]
