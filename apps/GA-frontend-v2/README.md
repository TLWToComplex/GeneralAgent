# GA-frontend-v2 · GeneralAgent V2 内容分发平台前端

内容分发平台控制台的界面与前端逻辑：登录（验证码 + 令牌 + 记住账号）、工作台、资产（镜像 / 模型 /
工具平台 / 知识库）、运维（网关 / 权限中心）。Vue 3 + TypeScript + Vite + Pinia + vue-router，
发布物是纯静态文件。

> 改密 / 解锁账号的后端接口已就绪（`/aiUser/changePassword`、`/aiUser/unlockAccount`），前端页面尚未开工。

| 配套服务 | 位置 | 默认地址 |
| --- | --- | --- |
| 后端（`/captcha`、`/aiUser`） | `../GA-backend-v2` | `http://127.0.0.1:8038` |
| 前置代理（进 dsh 控制台） | `../proxy` | 当前页面 host，80 端口（本地无权限用 8080） |
| 用户各自的 dsh 实例 | 由代理按后端映射反代 | 端口由映射表下发（示例 `127.0.0.1:8083`），一用户一容器 |

## 拉起（本地开发）

要求：Node 18+（建议 20 LTS）。

```bash
npm install
npm run dev          # http://127.0.0.1:5173
```

- `npm run dev` 把 `/captcha`、`/aiUser` 转发到 `http://127.0.0.1:8038`；换后端地址用 `VITE_DEV_BACKEND`。
  `/internal`（代理用的内部接口，需共享密钥）**故意不转发**，要调就 curl 直连后端。
- 受限环境（没有子进程权限）：`npm install --ignore-scripts --no-fund --no-audit`（esbuild / vue-demi 的
  postinstall 会 `spawn EPERM`）。工程内 `.npmrc` 已把 npm 缓存放进 `.npm-cache`，不写系统临时目录。
- 地址类配置**不配也能跑**（默认同源相对路径）。要直连别的源就复制 `.env.example` 为 `.env.local` 改
  `VITE_API_BASE` / `VITE_DSH_PROXY_BASE`；优先级：运行期 `config/config.json` > 这两个变量 > 内置默认。
  配成其它源时后端要放行该源（后端 `config/config.yaml` 的 `cors.allow_origins`）。

| 命令 | 作用 |
| --- | --- |
| `npm run dev` | 开发服务器（HMR，5173；后端转发见上） |
| `npm run build` | 类型检查（`vue-tsc --noEmit`）+ 打包到 `dist/` |
| `npm run build:only` | 只打包，跳过类型检查 |
| `npm run preview` | Vite 预览 `dist/` |
| `npm run serve:dist` | 自带静态服务器（`node tools/serve-dist.mjs 4175`），验收脚本用 |
| `npm run typecheck` | `vue-tsc --noEmit`；`typecheck:fast` 是不走 vue-tsc 的近似检查 |
| `npm run check:*` | 各页面几何与行为验收，见「运维」 |

## 配置（运行期 `config/config.json`）

后端地址、代理地址不写进构建产物，由运行期读 `public/config/config.json`（构建后是
`dist/config/config.json`）——**同一个镜像挂不同配置走不同环境，不用重新构建**：

```bash
docker run -v /opt/GA/config.json:/usr/share/nginx/html/config/config.json ...
```

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| `apiBase` | string | `""` | 后端接口前缀。空 = 同源相对路径（生产由 nginx / 统一入口转发） |
| `dshProxyBase` | string | `""` | 前置代理基地址。空 = 取当前页面 host、不带端口（代理默认 80） |
| `dshUsernameParam` | string | `"username"` | 「新建会话」携带用户名的查询参数名，须与 `../proxy/server.js` 一致 |
| `loginRememberKey` | string | `"aiPlatform.lastUser"` | 「记住账号」的 localStorage 键名 |
| `skipLogin` | boolean | `false` | 免登录开关，**只跳过前端登录页**，后端该 401 还是 401 |
| `skipLoginUser` | string | `""` | 免登录模式下的用户名；空则为 `guest` |

- 六个键要齐（`tools/check-runtime-config.mjs` 会断言），值可省略、省略即用默认；必须是合法 JSON，
  键名写错会被忽略。
- 改完**刷新页面**生效（拉取带时间戳且 `no-store`，不经中间层缓存）；拉不到 / 404 / JSON 坏 / 网络错
  **不阻塞启动**，退回内置默认并在控制台说明原因。
- `public/config/config.example.json` 是给运维抄的模板（`skipLogin: false`），随站点一起下发；
  **仓库里那份 `config.json` 当前是 `skipLogin: true`（免登录开启）**，属于内网演示形态，上线按环境决定用哪份，
  改挂载进去的那份即可，不用改仓库这份。
  注：`tools/check-runtime-config.mjs` 的 A 段按「默认关闭」断言，对着仓库这份跑会红。

## 部署

- 发布物 = `dist/`（纯静态）+ 运行期配置。构建：`npm run build`。
- 用 **hash 路由**（`#/console/workbench`），刷深链**不需要服务端 rewrite**；默认按**根路径**部署
  （产物引用 `/assets/...`），要放子路径得在 `vite.config.ts` 设 `base` 重新构建。
- 转发规则：`/captcha`、`/aiUser` → 后端 `8038`；进 dsh 控制台走 `../proxy`（不经过本服务）。
- 镜像与容器编排由部署包负责（`deploy/GA-app` 下的前端包），本仓不出 Dockerfile。当前部署文档里
  前端容器名为 `app-GA-frontend-v2`、宿主机端口 `15174`（见 `../部署脚本.md`）。
  ⚠️ 那份部署包里的前端配置叫 `runtime-config.json`，与本仓的 `config/config.json` 不是同一份，
  上线时按实际挂载路径确认。
- `public/ai-tools/` 下两个安装包**不进仓库**，clone 后要补（见下）。

### 补包：clone 之后把两个安装包放回来

`public/ai-tools/*.exe` 在 `.gitignore` 里，clone 出来只有两个镜像源脚本（那两个脚本随代码入库，
真身在仓库根目录）。按环境补：

| 环境 | 怎么补 |
| --- | --- |
| 外网 | 到各自的官网下载对应版本，按下表重命名后放进 `public/ai-tools/`：DSH 桌面版 = DeepSeek Harness **0.2.0-rc.2**，Zed = **1.20.2** |
| 内网 | 从已部署站点下回来（`http://<前端地址>/ai-tools/<文件名>`，页面上「领取安装包」走的就是这个地址），或找平台组要同一份 |

| 文件名 | 字节数 | SHA256（前 16 位） |
| --- | --- | --- |
| `dsh-latest-windows-x64.exe` | 289313640 | `D61CD8882F8B8A12` |
| `Zed-x86_64.exe` | 85627488 | `82C2F6E682A73E3F` |

```powershell
Get-FileHash .\public\ai-tools\Zed-x86_64.exe -Algorithm SHA256   # 应为 82C2F6E682A73E3F…
```

没补包时：页面上两个「领取安装包」会 404，`check-ai-tools.mjs` 的 ⑨c / ⑨d 段会直接抛错
（它们按字节数与 PE 头断言 `dist/ai-tools/` 里的真身），其余验收段落不受影响。

## 运维

### 验收 / 冒烟

```bash
npm run build
node tools/serve-dist.mjs 4175                       # 另开一个窗口
node tools/check-ai-tools.mjs http://127.0.0.1:4175  # AI 工具标签页与安装流程
node tools/check-runtime-config.mjs                  # 运行期配置端到端（自带静态服务器）
node tools/smoke-login-ui.mjs --shot                 # 登录链路冒烟 + 截图
```

`npm run check:sidebar-lock` / `check:tool-tabs` / `check:login-layout` / `check:kpi-breakpoints`
分别验侧栏置灰、工具平台标签页、登录页布局、工作台断点。截图落在 `tools/__shots__/`（不入库），
抓法见 `tools/shots-ai-tools.mjs`。

### 排查

| 现象 | 先看什么 |
| --- | --- |
| 白屏 / 静态资源 404 | 是否按根路径铺了 `dist/`；子路径部署需要设 `base` 重新构建 |
| 接口 401 / 被踢回登录页 | `config.json` 的 `apiBase` 是否可达；后端令牌有效期 1 小时 |
| 刷新后偶发连不上后端 | `config/config.json` 是否真能被站点取到（挂载路径、文件名）；取不到会退回默认值 |
| 「新建会话」打不开 / 403 / 404 | 后端 `/internal/dsh/route` 与代理的 `internalSecret` 是否一致；该用户是否登记了 dsh 实例 |
| 免登录没生效 | 挂载进去的那份 `config.json` 是否真被取到（路径 / 文件名），`skipLogin` 是否为 `true`（仓库那份已是 `true`） |
| AI 工具安装包下载 404 | `public/ai-tools/` 里两个 exe 是否已按「补包」放回 |

### 已知取舍（部署前知道就行）

- 「新建会话」把用户名放在 URL 上（`?username=`）**可伪造**，本版接受；补偿是代理会校验「该用户存在
  且已登记 dsh 实例」。根治要换成一次性票据（前端向后端申请、代理校验后作废），代理侧只替换
  `resolveUser()`。
- 用户名会留在浏览器历史里（首次进入那一跳）。
- 免登录开关只跳过前端登录页，不放开后端鉴权。

## 目录

```
src/
  api/        接口封装（按运行期配置拼地址）
  components/ 公共组件（侧栏 / 顶栏 / 资产页外壳 / 明细表 / 安装流程内容块 / 浮层）
  composables/ useHeartbeat
  config/     运行期配置解析（runtime.ts）与页面表（pages.ts）
  data/       各页面静态数据（原型迁移过来的演示数据）
  lib/        工具（卡片、剪贴板、dsh 跳转、图表、列定义）
  router/     路由（hash 模式）+ 登录 / 页面锁定守卫
  stores/     Pinia：auth / session / tools / gateway / kb / models / registry / authz / overlay / ui
  styles/     login.css（登录页）/ console.css（控制台）
  views/      登录页 + 控制台外壳 + 7 个子页面
public/
  ai-tools/   安装包与镜像源脚本（两个 exe 不入库，见「补包」）
  config/     运行期配置（config.json + config.example.json）
tools/        开发与验收脚本（不参与构建产物）
```

不入库：`dist/`、`node_modules/`、`.npm-cache/`、`.env*`、`public/ai-tools/*.exe`、`tools/__shots__/`。