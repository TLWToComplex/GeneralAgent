# MCP Client

基于 Vue 3 + TypeScript 的 MCP (Model Context Protocol) 客户端应用，提供完整的 MCP 服务器管理和 AI 对话功能。

## 项目概述

MCP Client 是一个现代化的 Web 应用程序，实现了 Model Context Protocol 协议，允许用户连接多个 MCP 服务器，与 AI 模型进行对话，并调用服务器提供的工具。项目采用模块化架构，具有完整的状态管理、事件系统和本地存储功能。

## 🛠️ 技术栈

### 核心框架
- **Vue 3** (^3.5.13) - 渐进式 JavaScript 框架
- **TypeScript** (^5.6.3) - 类型安全的 JavaScript 超集
- **Vite** (^6.0.5) - 现代化构建工具

### UI 组件库
- **Ant Design Vue** (^4.2.6) - 企业级 UI 设计语言
- **@ant-design/icons-vue** (^7.0.1) - 图标组件库

### 状态管理
- **Pinia** (^2.3.0) - Vue 3 官方状态管理库
- **pinia-plugin-persistedstate** (^4.1.3) - 状态持久化插件

### MCP 协议支持
- MCP 协议通过后端接口代理，无需前端直接连接服务器

### 文档渲染
- **markdown-it** (^14.1.0) - Markdown 解析器
- **katex** (^0.16.11) - 数学公式渲染
- **highlight.js** (^11.10.0) - 代码高亮

### 工具库
- **mitt** (^3.0.1) - 事件发射器
- **uuid** (^11.0.3) - UUID 生成器
- **jspdf** (^2.5.2) - PDF 生成库
- **html2canvas** (^1.4.1) - HTML 转 Canvas

## 项目结构

```
mcp-client/
├── public/                          # 静态资源目录
├── src/                            # 源代码目录
│   ├── App.vue                     # 根组件
│   ├── main.ts                     # 应用入口文件
│   ├── assets/                     # 静态资源
│   │   ├── base.css               # 基础样式
│   │   ├── main.css               # 主样式文件
│   │   └── styles/                # 样式模块
│   │       ├── app.css            # 应用主样式
│   │       ├── chat-view.css      # 聊天界面样式
│   │       ├── markdown.css       # Markdown 渲染样式
│   │       ├── mcp-server-view.css # MCP 服务器页面样式
│   │       ├── message.css        # 消息组件样式
│   │       ├── model-service-view.css # 模型服务页面样式
│   │       └── welcome.css        # 欢迎页面和引导流程样式
│   ├── components/                 # Vue 组件
│   │   ├── SwitchComponent.vue    # 开关组件
│   │   ├── chat/                  # 聊天相关组件
│   │   │   ├── ChatHistroy.vue    # 聊天历史
│   │   │   ├── ChatInput.vue      # 聊天输入框
│   │   │   ├── ChatMessage.vue    # 聊天消息显示
│   │   │   ├── ExportButton.vue   # 导出按钮
│   │   │   ├── MessageActions.vue # 消息操作组件
│   │   │   ├── MessageSelection.vue # 消息选择组件
│   │   │   ├── SimpleImageViewer.vue # 图片查看器
│   │   │   ├── SystemMessageModal.vue # 系统消息模态框
│   │   │   ├── SystemPromptVariablePreview.vue # 系统提示词变量预览
│   │   │   └── ToolCallDisplay.vue # 工具调用显示组件
│   │   ├── common/                # 通用组件
│   │   │   ├── MarkdownRenderer.vue # Markdown 渲染器
│   │   │   └── NotificationHandler.vue # 通知处理器
│   │   ├── icons/                 # 图标组件
│   │   │   ├── CopyIcon.vue       # 复制图标
│   │   │   ├── EditIcon.vue       # 编辑图标

│   │   │   ├── MarkdownIcon.vue   # Markdown 图标
│   │   │   ├── NewChatIcon.vue    # 新建聊天图标
│   │   │   ├── PdfIcon.vue        # PDF 图标
│   │   │   ├── PromptIcon.vue     # 提示图标
│   │   │   ├── RetryIcon.vue      # 重试图标
│   │   │   ├── SendIcon.vue       # 发送图标
│   │   │   ├── ShareIcon.vue      # 分享图标
│   │   │   ├── StopIcon.vue       # 停止图标
│   │   │   └── TextIcon.vue       # 文本图标
│   │   ├── layout/                # 布局组件
│   │   │   └── Header.vue         # 页面头部
│   │   ├── mcp-server/            # MCP 服务器管理组件
│   │   │   ├── AddServerModal.vue # 添加服务器模态框
│   │   │   ├── ServerConfigForm.vue # 服务器配置表单
│   │   │   ├── ServerList.vue     # 服务器列表
│   │   │   ├── ToolDetailModal.vue # 工具详情模态框
│   │   │   ├── ToolList.vue       # 工具列表
│   │   │   └── types.ts           # 类型定义
│   │   ├── model-service/         # 模型服务组件
│   │   │   ├── AddModelModal.vue  # 添加模型模态框
│   │   │   ├── AddProviderModal.vue # 添加提供商模态框
│   │   │   ├── EditModelModal.vue # 编辑模型模态框
│   │   │   ├── EditProviderModal.vue # 编辑提供商模态框
│   │   │   └── types.ts           # 类型定义
│   │   └── server/                # 服务器组件目录
│   ├── composables/               # Vue 组合式函数
│   │   ├── index.ts               # 导出文件
│   │   ├── useClientConfiguration.ts # 客户端配置
│   │   ├── useConfig.ts           # 配置管理
│   │   ├── useEventListener.ts    # 事件监听
│   │   ├── useLocalStorage.ts     # 本地存储
│   │   ├── useMcpClient.ts        # MCP 客户端逻辑
│   │   ├── useMessageManager.ts   # 消息管理
│   │   ├── useSystemPromptVariables.ts # 系统提示词变量处理
│   │   └── useTheme.ts            # 主题管理
│   ├── config/                    # 配置文件
│   │   ├── constants.ts           # 应用常量
│   │   ├── index.ts               # 配置导出
│   │   └── theme.ts               # 主题配置
│   ├── router/                    # 路由配置
│   │   └── index.ts               # 路由定义
│   ├── services/                  # 服务层
│   │   ├── index.ts               # 服务导出
│   │   ├── mcp/                   # MCP 客户端服务
│   │   │   ├── client.ts          # MCP 客户端核心
│   │   │   ├── messageHandler.ts  # 消息处理
│   │   │   ├── modelHandler.ts    # 模型 API 处理
│   │   │   └── types.ts           # MCP 类型定义
│   │   └── pdf/                   # PDF 相关服务
│   │       ├── constants.ts       # PDF 常量
│   │       ├── index.ts           # PDF 服务导出
│   │       ├── PdfExporter.ts     # PDF 导出器
│   │       ├── PdfPreviewGenerator.ts # PDF 预览生成
│   │       ├── PdfRenderer.ts     # PDF 渲染器
│   │       └── types.ts           # PDF 类型定义
│   ├── stores/                    # Pinia 状态管理
│   │   ├── chat-store.ts          # 聊天状态
│   │   ├── chatConfigStore.ts     # 聊天配置状态
│   │   ├── chatMessagesStore.ts   # 聊天消息状态
│   │   ├── artifactStore.ts       # 产物状态
│   │   ├── knowledgeBaseStore.ts  # 知识库状态
│   │   └── uiStore.ts             # UI 状态
│   ├── types/                     # TypeScript 类型定义
│   │   ├── index.ts               # 类型导出
│   │   ├── markdown-it-katex.d.ts # markdown-it-katex 类型声明
│   │   └── mcp.ts                 # MCP 类型定义
│   ├── utils/                     # 工具函数
│   │   ├── ConfigManager.ts       # 配置管理器
│   │   ├── EventBus.ts            # 事件总线
│   │   ├── NotificationService.ts # 通知服务
│   │   ├── StorageService.ts      # 存储服务
│   │   ├── SystemPromptVariables.ts # 系统提示词变量处理
│   │   ├── http.ts                # HTTP 工具
│   │   ├── index.ts               # 工具导出
│   │   └── storage.ts             # 存储工具
│   └── views/                     # 页面视图
│       ├── ChatView.vue           # 聊天页面
│       ├── McpServerView.vue      # MCP 服务器管理页面
│       ├── ModelServiceView.vue   # 模型服务页面
│       ├── SettingsView.vue       # 设置页面
│       └── WelcomeView.vue        # 欢迎页面和初始化引导
├── Dockerfile                     # Docker 配置文件
├── env.d.ts                       # 环境类型声明
├── index.html                     # HTML 入口文件
├── mcp_client.conf                # Nginx 配置文件
├── package.json                   # 项目依赖配置
├── tsconfig.json                  # TypeScript 配置
├── tsconfig.app.json              # 应用 TypeScript 配置
├── tsconfig.node.json             # Node.js TypeScript 配置
└── vite.config.ts                 # Vite 构建配置
```

## 核心功能模块

### 1. MCP 服务器管理
- **服务器连接管理**: 支持添加、连接、断开多个 MCP 服务器
- **智能连接测试**: 独立的连接测试器，支持单个和批量服务器连接测试
- **工具发现与获取**: 自动发现和管理服务器提供的工具，支持多重获取机制确保工具列表完整性
- **连接状态监控**: 实时监控服务器连接状态，支持连接中、已连接、错误、断开等状态
- **服务器配置**: 支持自定义服务器启动命令、环境变量、请求头和超时设置
- **双重工具获取机制**: 当主要连接测试未获取到工具时，自动使用备用机制确保工具列表完整
- **连接重试机制**: 内置重试逻辑，提高连接成功率和稳定性
- **批量操作**: 支持批量测试多个服务器连接，提供进度反馈和结果统计

### 2. AI 模型服务
- **多提供商支持**: 支持 OpenAI、通义千问等多种 AI 服务
- **模型管理**: 动态添加和管理不同的 AI 模型
- **API 配置**: 灵活的 API 密钥和端点配置
- **模型切换**: 无缝切换不同的 AI 模型

### 3. 聊天系统
- **实时对话**: 支持流式响应的实时聊天
- **工具调用**: AI 可以调用 MCP 服务器提供的工具
- **消息历史**: 完整的聊天记录管理
- **系统提示**: 自定义系统提示词
- **消息操作**: 支持消息复制、编辑、分享、重试等操作
- **消息选择**: 支持批量选择和操作消息
- **数学公式渲染**: 支持 LaTeX 数学公式的实时渲染
- **系统提示词变量**: 支持动态变量替换（如当前时间、日期等）

### 4. Markdown 和数学公式渲染
- **Markdown 解析**: 完整的 Markdown 语法支持
- **数学公式渲染**: 基于 KaTeX 的 LaTeX 数学公式渲染
- **代码高亮**: 支持多种编程语言的语法高亮
- **实时渲染**: 流式输出时的实时 Markdown 渲染
- **自定义宏**: 支持自定义数学公式宏定义

### 5. PDF 导出
- **聊天记录导出**: 将聊天记录导出为 PDF 文件
- **格式化输出**: 支持 Markdown 渲染和代码高亮
- **自定义样式**: 可配置的 PDF 输出样式

### 6. 事件系统
- **统一事件总线**: 基于 EventBus 的组件间通信
- **MCP 事件**: 专门的 MCP 协议事件处理
- **生命周期管理**: 完整的事件订阅和取消订阅机制
- **连接测试事件**: 监听连接测试进度和结果
- **实时状态同步**: 确保UI状态与实际连接状态保持同步

### 7. 存储系统
- **本地存储**: 配置和数据的持久化存储
- **配置管理**: 统一的配置管理系统
- **数据同步**: 跨组件的数据同步机制

### 8. 用户引导和初始化
- **欢迎页面**: 全新的用户引导界面，提供友好的初始化体验
- **分步配置**: 引导用户逐步完成模型服务和MCP服务器配置
- **配置向导**: 智能化的配置流程，降低新用户使用门槛
- **进度指示**: 清晰的进度提示和状态反馈

## 快速开始

### 环境要求
- Node.js >= 16.0.0
- npm >= 7.0.0

### 安装和运行

1. 克隆项目
```bash
git clone <repository-url>
cd mcp-client
```

2. 安装依赖
```bash
npm install
```

3. 启动开发服务器
```bash
npm run dev
# 或
npm run serve
```

4. 构建生产版本
```bash
npm run build
```

5. 预览构建结果
```bash
npm run preview
```

6. 类型检查
```bash
npm run type-check
```

## 使用指南

### 首次使用
1. 启动应用后，系统会自动引导您进入欢迎页面
2. 按照引导步骤完成初始配置：
   - 配置模型服务（OpenAI、Anthropic 等）
   - 添加 MCP 服务器
   - 完成基础设置
3. 配置完成后即可开始使用聊天功能

### 配置模型服务

1. 进入"设置" → "模型服务"页面
2. 点击"添加提供商"按钮
3. 填写提供商信息（名称、API 密钥、基础 URL）
4. 添加该提供商支持的模型
5. 在聊天页面选择要使用的模型

### 添加 MCP 服务器

1. 进入"设置" → "MCP 服务器"页面
2. 点击"添加服务器"按钮
3. 填写服务器配置：
   - 服务器名称
   - 启动命令
   - 命令参数
   - 环境变量
   - 请求头设置
   - 超时配置
4. 点击"测试连接"验证服务器配置：
   - 系统会尝试连接服务器并获取可用工具列表
   - 如果主要连接测试失败，会自动尝试备用连接机制
   - 测试成功后会显示服务器提供的工具信息
5. 保存并启动服务器
6. 查看服务器提供的工具列表

**批量测试功能**：
- 在服务器列表页面，可以点击"测试所有连接"批量测试多个服务器
- 系统会显示测试进度和每个服务器的连接结果
- 支持并发测试，提高效率

### 开始对话

1. 进入"对话"页面
2. 输入消息开始对话
3. AI 会自动调用可用的工具来完成任务

**工具使用提示**：
- 系统会自动检测并使用合适的 MCP 工具
- 可以在服务器管理页面查看所有可用工具
- 工具调用失败时会自动重试或使用备用机制

### 4. 使用数学公式

1. 在聊天中输入 LaTeX 数学公式
2. 使用 `$...$` 包围行内公式，如：`$E = mc^2$`
3. 使用 `$$...$$` 包围块级公式，如：`$$\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}$$`
4. 支持常用数学符号和函数

### 5. 使用系统提示词变量

1. 在系统提示词中使用 `${变量名}` 格式
2. 支持的变量包括：
   - `${current_date}`: 当前日期 (YYYY-MM-DD)
   - `${current_time}`: 当前时间 (HH:MM:SS)
   - `${current_datetime}`: 当前日期时间
3. 变量会在发送消息时自动替换为实际值

### 6. 导出聊天记录

1. 在聊天页面点击导出按钮
2. 选择导出格式（PDF）
3. 下载生成的文件

## 开发指南

### 添加新的组合式函数

```typescript
// src/composables/useNewFeature.ts
import { ref, computed } from 'vue'

export function useNewFeature() {
  const state = ref(false)
  
  const toggle = () => {
    state.value = !state.value
  }
  
  const isActive = computed(() => state.value)
  
  return {
    state: readonly(state),
    isActive,
    toggle
  }
}
```

### 添加新的 Pinia Store

```typescript
// src/stores/newStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useNewStore = defineStore('new', () => {
  const items = ref([])
  
  const addItem = (item: any) => {
    items.value.push(item)
  }
  
  const itemCount = computed(() => items.value.length)
  
  return {
    items: readonly(items),
    itemCount,
    addItem
  }
})
```

### 添加新的服务

```typescript
// src/services/newService.ts
export class NewService {
  private baseUrl: string
  
  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }
  
  async fetchData(): Promise<any[]> {
    const response = await fetch(`${this.baseUrl}/api/data`)
    return response.json()
  }
}
```

### 使用事件总线

```typescript
import EventBus, { MCP_EVENTS } from '@/utils/EventBus'

// 订阅事件
const unsubscribe = EventBus.on(MCP_EVENTS.MESSAGE_CREATED, (payload) => {
  console.log('新消息:', payload.message)
})

// 发布事件
EventBus.emit(MCP_EVENTS.MESSAGE_CREATED, { message: { content: 'Hello' } })

// 清理订阅
unsubscribe()
```

### 使用系统提示词变量

```typescript
// src/composables/useSystemPromptVariables.ts
import { useSystemPromptVariables } from '@/composables/useSystemPromptVariables'

const { processSystemPrompt, hasVariables, extractVariables } = useSystemPromptVariables()

// 处理包含变量的系统提示词
const prompt = '当前时间是 ${current_time}，请根据当前日期 ${current_date} 回答问题。'
const processedPrompt = processSystemPrompt(prompt)

// 检查是否包含变量
if (hasVariables(prompt)) {
  const variables = extractVariables(prompt)
  console.log('检测到变量:', variables)
}
```

## 部署

### 构建生产版本

```bash
npm run build
```

构建产物将生成在 `dist/` 目录下。

### 使用 Docker 部署

项目包含完整的 Docker 配置：

```bash
# 构建镜像
docker build -t aisix-frontend-v2-2026-02-06 .

# 保存镜像为 tar 文件
docker save -o aisix-frontend-v2-2026-02-06.tar aisix-frontend-v2-2026-02-06

# 加载镜像到 Docker 中
docker load -i aisix-frontend-v2-2026-02-06.tar

# 运行容器
docker run -d --name aisix-frontend-v2-2026-02-06 --restart unless-stopped -p 5174:5174 -d aisix-frontend-v2-2026-02-06
```

### ARM 架构 Docker 部署

对于 ARM 架构的服务器，使用以下命令进行构建和打包：

```
# 构建 ARM64 镜像
docker buildx build --platform linux/arm64 -t aisix-frontend-v2-2026-02-06 .

# 保存镜像为 tar 文件
docker save -o aisix-frontend-v2-2026-02-06.tar aisix-frontend-v2-2026-02-06

# 加载 ARM64 镜像到 Docker 中
docker load -i aisix-frontend-v2-2026-02-06.tar

# 运行容器
docker run -d --name aisix-frontend-v2-2026-02-06 --restart unless-stopped -p 5174:5174 -d aisix-frontend-v2-2026-02-06
```

### 部署到静态服务器

将 `dist/` 目录的内容部署到任何静态文件服务器：
- Nginx
- Apache
- Vercel
- Netlify
- GitHub Pages

## 配置说明

### 应用常量配置

```typescript
// src/config/constants.ts
export const STORAGE_KEYS = {
  NEED_UPDATE_MSG: 'mcp-need-update-msg',
  OPEN_ADD_SERVER_MODAL: 'mcp-open-add-modal'
}
```

### MCP 服务器配置格式

```json
{
  "name": "示例服务器",
  "command": "node",
  "args": ["server.js"],
  "env": {
    "NODE_ENV": "production",
    "API_KEY": "your-api-key"
  }
}
```

### 模型服务配置格式

```json
{
  "name": "OpenAI",
  "apiKey": "sk-...",
  "baseUrl": "https://api.openai.com/v1",
  "models": {
    "gpt-4": {
      "name": "GPT-4",
      "id": "gpt-4"
    }
  }
}
```

### 运行时后端基础地址配置（支持 Docker 镜像动态修改）

为便于在打包成 Docker 镜像后动态调整后端 IP/端口，项目增加了运行时配置文件：

- 文件路径：`public/runtime-config.json`
- 配置键：`API_BASE_URL`、`FILE_UPLOAD_MAX_SIZE`、`KB_UPLOAD_DEFAULT_CHUNK_SIZE`

使用方式：
- 开发环境：直接修改 `public/runtime-config.json`
  ```json
  {
    "API_BASE_URL": "http://127.0.0.1:8080",
    "FILE_UPLOAD_MAX_SIZE": 25,
    "KB_UPLOAD_DEFAULT_CHUNK_SIZE": 500
  }
  ```
  留空字符串 `""` 表示使用同源相对路径（例如 `fetch('/api/login')` 将请求到当前站点的 `/api/login`）。

- 生产环境构建后：确保 `dist/runtime-config.json` 存在并可由前端访问（路径为站点根 `/runtime-config.json`）。
  - 如果使用 Docker/Nginx 运行镜像，可通过挂载卷覆盖该文件，实现运行时修改后端地址，例如：
    ```bash
    docker run -d --name mcp-client \
      -p 5174:5174 \
      -v /path/to/runtime-config.json:/usr/share/nginx/html/runtime-config.json:ro \
      mcp-client
    ```
    上述示例假设 Nginx 的站点根为 `/usr/share/nginx/html`，请按你的镜像实际路径调整。

前端行为说明：
- `src/utils/http.ts` 的封装将自动在相对路径请求（如 `/api/login`）前拼接 `API_BASE_URL`（当其非空时）。
- 当 `API_BASE_URL` 为空时，保留相对路径以便使用同源部署/反向代理方案。
- 应用在 `main.ts` 启动时会优先加载 `/runtime-config.json`，因此无需重新构建镜像即可修改后端地址。

注意事项：
- 确保后端允许跨域（如前后端不同源时）或推荐通过反向代理统一同源。
- 如果后端有鉴权/令牌机制，`http.ts` 会自动把本地存储中的 `access_token` 注入到请求头 `Authorization: Bearer <token>`。

### 单一配置方式：仅使用 runtime-config.json

为简化管理，前端仅从运行时文件 `runtime-config.json` 加载后端地址：

- 位置：`public/runtime-config.json`（开发）与 `dist/runtime-config.json`（生产）
- 字段：`API_BASE_URL`（例如：`http://192.168.1.137:8030`）
- 为空字符串 `""` 时表示同源相对路径（适合反向代理或同源部署）

好处：
- 构建后可动态修改，无需重建或重新发布镜像
- 运维统一，只需确保该文件可被前端访问

示例文件：
```json
{
  "API_BASE_URL": "http://192.168.1.137:8030"
}
```

### 子路径部署与 BASE_URL（影响 runtime-config.json 加载路径）

当前项目会使用 `import.meta.env.BASE_URL` 来确定运行时配置文件的加载路径（`${BASE_URL}runtime-config.json`）。

- 如果你的应用部署在子路径（例如 `https://example.com/mcp/`），请在 Vite 配置中设置 `base`：
  ```ts
  // vite.config.ts
  import { defineConfig } from 'vite';
  import vue from '@vitejs/plugin-vue';

  export default defineConfig({
    plugins: [vue()],
    base: '/mcp/',
  });
  ```
- 构建时也可以通过 CLI 指定：`vite build --base=/mcp/`
- 设置完成后，前端会从 `/mcp/runtime-config.json` 加载运行时配置。请确保该文件在部署目录的子路径下可访问（例如 `dist/mcp/runtime-config.json` 或 Nginx 对应的站点根子目录）。

### 调试与验证

- 打开浏览器控制台（Console）：
  - 成功加载运行时配置会打印：`[RuntimeConfig] 加载成功`，包含加载 URL 与当前 `API_BASE_URL`。
  - 登录或发起请求时会打印：`[HTTP] 最终请求地址解析`，确认 `targetUrl` 是否为期望的后端地址。

## 故障排除

### 常见问题

1. **服务器连接失败**
   - 检查服务器配置是否正确
   - 确认 MCP 服务器进程是否正常运行
   - 查看浏览器控制台错误信息
   - 检查网络连接和防火墙设置
   - 尝试使用"测试连接"功能验证服务器状态
   - 如果连接测试失败，系统会自动尝试备用连接机制

2. **工具列表获取失败**
   - 确认服务器已成功连接
   - 检查服务器是否实现了 `tools/list` 方法
   - 使用批量测试功能检查多个服务器状态
   - 查看连接测试结果中的工具信息
   - 如果工具列表为空，系统会自动重试获取

3. **连接测试超时**
   - 检查服务器响应时间是否过长
   - 调整连接超时设置（默认5秒）
   - 确认服务器网络连接稳定
   - 尝试重新启动MCP服务器进程

4. **模型调用失败**
   - 验证 API 密钥是否有效且未过期
   - 检查 API 基础 URL 是否正确
   - 确认模型名称是否正确
   - 检查 API 配额是否充足

5. **工具调用失败**
   - 确认 MCP 服务器已正确连接
   - 检查工具参数是否符合要求
   - 查看服务器日志获取详细错误信息
   - 验证工具是否在工具列表中正确显示

6. **PDF 导出失败**
   - 检查浏览器是否支持 PDF 生成
   - 确认聊天记录不为空
   - 检查是否有足够的内存进行转换

7. **构建失败**
   - 确认 Node.js 版本 >= 16.0.0
   - 删除 `node_modules` 和 `package-lock.json` 重新安装
   - 运行 `npm run type-check` 检查类型错误

### 调试技巧

1. **开启详细日志**
   ```typescript
   // 在浏览器控制台中设置
   localStorage.setItem('debug', 'mcp:*')
   ```

2. **检查事件流**
   ```typescript
   // 监听所有 MCP 事件
   EventBus.on('*', (eventName, ...args) => {
     console.log('Event:', eventName, args)
   })
   ```

3. **查看存储状态**
   ```typescript
   // 检查本地存储
   console.log('API Config:', StorageService.getApiConfig())
   console.log('Selected Model:', StorageService.getSelectedModel())
   ```



## 项目特点

- **🎨 现代化界面**: 基于 Ant Design Vue 的美观界面设计
- **🚀 用户友好**: 全新的欢迎页面和配置引导流程
- **🔧 模块化架构**: 清晰的代码组织和职责分离
- **🛡️ 类型安全**: 完整的 TypeScript 类型定义和检查
- **📱 响应式设计**: 基于 Vue 3 Composition API 的现代开发模式
- **📊 状态管理**: 使用 Pinia 进行统一的状态管理
- **🔄 事件驱动**: 基于 EventBus 的松耦合组件通信
- **💾 本地存储**: 完整的配置和数据持久化方案
- **📐 数学公式支持**: 基于 KaTeX 的完整 LaTeX 数学公式渲染
- **🤖 智能变量系统**: 支持系统提示词中的动态变量替换
- **🛠️ 丰富的消息操作**: 支持消息编辑、复制、分享、重试等多种操作
- **⚡ 实时渲染**: 流式输出时的实时 Markdown 和数学公式渲染
- **🌐 国际化支持**: 内置中文界面和多语言支持基础
- **🎨 主题系统**: 可扩展的主题和样式系统
- **🚨 错误处理**: 完善的错误处理和用户反馈机制
- **🚀 性能优化**: 组件懒加载和 keep-alive 缓存
