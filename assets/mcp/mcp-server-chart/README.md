# mcp-server-chart

## 项目概述
mcp-server-chart 是一个基于 Node.js 和 Express 的图表渲染服务，结合 @antv/gpt-vis-ssr 实现服务端自动化图表生成。该项目通过 HTTP API 接收前端或其他服务的图表渲染请求，自动生成图片并返回图片访问链接，适用于自动化报表、智能可视化等场景。

- 支持 Docker 镜像一键部署，便于在各类环境下快速上线。
- 提供 RESTful API，支持通过 POST 请求传递图表参数，自动生成图片。
- 渲染结果以图片形式存储并通过静态服务对外访问。

## 原理说明
1. 服务启动后监听 8999 端口，暴露 `/render-chart` API。
2. 客户端通过 POST `/render-chart` 提交图表渲染参数（如数据、配置等）。
3. 服务端调用 `@antv/gpt-vis-ssr` 的 `render` 方法生成图表，并将结果转为图片 Buffer。
4. 图片以唯一文件名存储在本地 `images` 目录，并通过 `/images/[filename]` 路径对外提供访问。
5. 返回图片的 URL 给客户端，实现自动化、批量化的图表图片生成。

### Docker 部署原理
- 基于官方 node:20-slim 镜像，保证运行环境轻量且兼容性好。
- 安装必要的系统依赖（如字体、图像处理库），确保图表渲染的完整性和多语言支持。
- 拷贝项目源码和依赖配置，执行 npm install 安装依赖。
- 全局安装 pm2 及 mcp-server-chart，便于进程管理和服务启动。
- 设置环境变量和端口暴露，支持灵活配置和容器化部署。
- 通过 pm2-runtime 启动服务，保证服务高可用和自动重启。

技术栈：Node.js、Express、@antv/gpt-vis-ssr、Docker。

### 依赖说明

#### 系统依赖
- **python3**：部分 npm 包（如 node-canvas）在编译时需要 Python 环境。
- **make、g++**：用于编译 C++ 插件和底层依赖，node-canvas 等库安装时必需。
- **libcairo2-dev**：Cairo 图形库开发包，node-canvas 渲染图表时依赖。
- **libpango1.0-dev**：Pango 文本布局和渲染库，支持多语言文本渲染。
- **libjpeg-dev、libgif-dev、librsvg2-dev**：分别用于 JPEG、GIF、SVG 等图片格式的渲染和处理。
- **fontconfig**：字体配置和管理工具，保证字体查找和加载。
- **fonts-noto-cjk、fonts-dejavu-core、fonts-liberation**：常用字体包，支持中日韩等多语言文本的正常显示。
- **ca-certificates**：根证书，保证网络请求的安全性。

#### 主要 npm 依赖
- **express**：Node.js Web 框架，负责 HTTP 服务、路由和中间件管理。
- **@antv/gpt-vis-ssr**：AntV 图表服务端渲染核心库，负责将前端参数转为图表图片。
- **uuid**：生成唯一的图片文件名，避免文件冲突。
- **pm2**：Node.js 进程管理工具，支持服务守护、自动重启和日志管理。

> 依赖说明：
> - 系统依赖需在 Dockerfile 或宿主机环境中提前安装，保证 node-canvas 及相关图形渲染库能正常工作。
> - npm 依赖通过 `npm install` 自动安装，建议使用 lock 文件锁定版本。
> - 字体依赖建议包含常用中英文字体，避免渲染乱码。

## 镜像构建
```shell
docker build -t mcp-server-chart:0.7.1 .
```

## 运行（sse方式）
```shell
# docker 本地运行-e VIS_REQUEST_SERVER 可忽略
docker run -d -e VIS_REQUEST_SERVER=http://127.0.0.1:8999/render-chart --name mcp-server-chart -p 8999:8999 -p 1122:1122 mcp-server-chart:0.7.1
```

## 注意事项

> **NOTE:** 私有化部署方案目前不支持地理可视化图表生成，包括以下3种工具：geographic-district-map, geographic-path-map, geographic-pin-map。