# mcp-server-chart-streamable-http

基于 `mcp-server-chart` 的私有化部署思路实现：

1. 本地渲染服务：`src/index.ts`，提供 `POST /render-chart`（默认 `8999`）
2. 官方 MCP 服务：`@antv/mcp-server-chart`，使用 `streamable` 传输（默认 `1122`，endpoint `/mcp`）

该方案与 `mcp-server-chart`（SSE 版）功能保持一致，区别仅在 MCP 传输方式从 `sse` 改为 `streamable-http`。

## 环境变量

参考 `example.env`：

```env
VIS_REQUEST_SERVER=http://127.0.0.1:8999/render-chart
COMPATIBILITY_MODE=true
RENDER_PORT=8999
MCP_HOST=0.0.0.0
MCP_PORT=1122
MCP_ENDPOINT=/mcp
SERVICE_ID=
DISABLED_TOOLS=
```

其中 `VIS_REQUEST_SERVER` 是私有化部署关键配置，MCP 服务会将图表渲染请求转发到该地址。

## 本地运行

```bash
npm install
npm run start:all
```

## Docker 运行

```bash
docker build -t mcp-server-chart-streamable-http:1.0.0 .
docker run -d --name mcp-server-chart-streamable-http --env-file .docker.env  -p 8999:8999 -p 1122:1122 mcp-server-chart-streamable-http:1.0.0
```

## 端点

- 渲染 API: `http://localhost:8999/render-chart`
- MCP Streamable HTTP: `http://localhost:1122/mcp`

## 说明

- 进程管理使用 `pm2-runtime`，配置文件为 `ecosystem.config.js`
- 目前私有化部署方式不支持地理可视化 3 个工具：`geographic-district-map`、`geographic-path-map`、`geographic-pin-map`
