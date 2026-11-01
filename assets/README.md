# assets

`assets/` 按可分发对象的类型分目录。

| 目录 | 内容 |
| --- | --- |
| `skills/` | 技能 |
| `mcp/` | MCP 服务定义与配套资源 |
| `tools/` | AI 工具 |
| `others/` | 还没有独立成类的生产资料 |

`others/` 的作用是放一些暂时还未归类的其他资源。

## mcp

同一个 MCP 能力通常有两份：`*-sse` 走 SSE 传输，`*-streamable-http` 走流式 HTTP 传输。

| 目录 | 类型 | 内容 |
| --- | --- | --- |
| `kbchat-mcp-server/` | MCP 服务 | 知识库会话 MCP |
| `mcp-sequential-thinking/` | MCP 服务 | 顺序思考 MCP，用 3.12 以上的 Python |
| `mcp-sequential-thinking-streamable-http/` | MCP 服务 | 同一个 MCP 的流式 HTTP 传输版 |
| `mcp-server-chart/` | MCP 服务 | 图表 MCP，含 docker 镜像构建与 kb-chat server |
| `mcp-server-chart-streamable-http/` | MCP 服务 | 同一个 MCP 的流式 HTTP 传输版 |
| `mysql-mcp-server-sse/` | MCP 服务 | MySQL MCP，SSE 传输，含 docker 镜像构建与 kb-chat server |
| `mysql-mcp-server-streamable-http/` | MCP 服务 | 同一个 MCP 的流式 HTTP 传输版 |

MCP 服务本体可独立部署；`mcp/` 存放它们的服务定义、代理与配套资源，运行期按需拉取，不进镜像。