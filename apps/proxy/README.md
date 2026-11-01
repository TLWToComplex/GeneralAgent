# proxy · dsh 前置代理

把「登录后的用户」带到「他自己的 dsh 容器」面前。**它自己不再有登录页** —— 登录全部在
[`../GA-frontend-v2`](../GA-frontend-v2) 完成，代理只做三件事：

```
① 识别用户            URL 上的 ?username=<用户名>
② 向后端校验          GET /internal/dsh/route（共享密钥）→ 用户存在 + 已登记 + 未停用
③ 转发                反代到该用户的 dsh 实例（含 WebSocket），并接管 dsh 0.1.2 的会话 cookie
```

## 完整链路

```
控制台点「新建会话」
  → 新标签页打开  http://<proxy>/?username=demo
  → proxy 查后端映射（命中则缓存 30s）
  → 302 到 /           并 Set-Cookie: dsh_user=<签名后的用户名>; HttpOnly; SameSite=Lax
  → 浏览器带 cookie 重新请求 /
  → proxy 用 tokens.d/demo 里的启动令牌换取 dsh 会话 cookie（dsh-auth-*）
  → 转发到 http://127.0.0.1:8083/，注入会话 cookie、改写 Host 为回环、注入 polyfill
```

**为什么要 302 + cookie**：浏览器对子资源（JS/CSS/API）和 WebSocket 不会带父页面的查询串，
所以用户名必须在第一次进入时落到 cookie 上，后续请求才认得出是谁。302 顺带让 dsh 自己
永远看不到 `?username=`（不污染它的路由与 Referer）。

## 配置

配置的**唯一来源是 `config.js`**（CommonJS 模块，模板见 `config.example.js`）。
服务器**不读任何环境变量** —— 这样配置只有一份、能写注释、能 diff、能随容器挂载回滚。
各项都可省略，省略即用下表默认值；改完**重启进程**生效。

| 配置项 | 必填 | 默认 | 说明 |
| --- | --- | --- | --- |
| `internalSecret` | **是** | — | 与后端 `dsh.internal_secret`（或后端的 `DSH_INTERNAL_SECRET`）一致。**留空则拒绝启动**（与后端"不配就 503"同一立场） |
| `port` | 否 | `80` | 监听端口（80 需要 root/管理员；本地可用 8080） |
| `backendBaseUrl` | 否 | `http://127.0.0.1:8038` | 后端地址 |
| `entryOrigin` | 否 | `http://172.16.235.50` | 浏览器地址栏看到的源，用于同源补偿校验 |
| `frontendLoginUrl` | 否 | `<entryOrigin>:5173/#/login` | 错误页「回到登录页」的链接 |
| `tokensDir` | 否 | `./tokens.d` | dsh 启动令牌目录（相对路径以配置文件所在目录为基准） |
| `sessionsFile` | 否 | `./sessions.json` | dsh 会话缓存，重启后不必重新交换 |
| `routeCacheTtlMs` | 否 | `30000` | 映射缓存；设 `0` 关闭（改了映射表端口能立即生效） |
| `cookieSecret` | 否 | 每次启动随机 | 签发 `dsh_user` cookie 的密钥；留空则代理重启后用户需从控制台重新进入一次 |
| `cookieSecure` | 否 | `false` | 入口在 HTTPS 后面时置 `true`（给 cookie 加 `Secure`） |

配置源优先级：`createProxy(overrides)`（自检脚本/以库方式调用）> `config.js` > 上表默认值。
写错的键名会被启动日志点名忽略，非法值（端口不是数字、URL 不合法…）会**启动即报错**。

## 跑起来

```bash
cp config.example.js config.js   # 至少填 internalSecret（要与后端一致）
npm start

# 自检：假后端 + 假 dsh，不需要真容器、不需要网络、不需要配置文件
npm run smoke                    # 52 项断言
```

`config.js` 不在 / 没填 `internalSecret` 都会**拒绝启动**，并打印该怎么办 —— 这是故意的：
宁可起不来，也不要留下一个"谁都能进"的代理。端口被占用时也会直接说明是哪一项要改。

本地想连着控制台一起看：`config.js` 里 `port: 80`（前端默认就取当前 host + 80，什么都不用配）；
若本机没有权限绑 80 就改 `port: 8080`，同时在前端 `GA-frontend-v2/.env.local` 里写
`VITE_DSH_PROXY_BASE=http://localhost:8080`。之后在控制台点「新建会话」，
就会开新标签页打到这个代理（会话在 dsh 里创建）。

Linux 下绑定 80 端口需要 root 或 `setcap`；Docker 运行必须 `--network host`
（代理要访问宿主机 `127.0.0.1` 上绑定的 dsh 端口），配置以**挂载文件**的形式提供：

```bash
docker build -t dsh-proxy .
docker run -d --name dsh-proxy --network host \
  -v /opt/dsh/proxy-config.js:/app/config.js \
  -v /opt/dsh/tokens.d:/app/tokens.d \
  dsh-proxy
```

换配置 = 改宿主机那份 `proxy-config.js` 后 `docker restart dsh-proxy`（不必重建镜像）。
`node server.js --config <路径>` 也可以把配置文件放到别处。

## 出错时看到什么

代理的错误页会写明原因，并给一个回前端登录页的按钮（本代理没有登录页可回）：

| 页面 | HTTP | 触发 |
| --- | --- | --- |
| 缺少用户身份 | 401 | 既没有 `?username=` 也没有有效 cookie（例如直接贴地址、收藏夹进来） |
| 无法进入 dsh 控制台 | 404 | 后端说：用户不存在或已删除 / 该用户未登记 dsh 实例 |
| 该账号的 dsh 实例已停用 | 403 | 映射表里 `status = 0` |
| 服务端配置有误 | 500 | 代理与后端的共享密钥不一致，或后端没启用内部接口 |
| 后端服务不可达 | 502 | 联系不上 `backendBaseUrl` |
| 无法建立 dsh 会话 | 502 | 拿不到 dsh 启动令牌（令牌文件缺失/失效）→ 按提示执行 `./dsh-new.sh refresh <容器名> <用户>` |
| dsh 实例不可达 | 502 | 容器没起来，或映射表里的 host/port 与实际不一致 |

## 安全态势（部署前读一遍）

- **`?username=` 可伪造** —— 谁都能把用户名换成别人直接进对方 dsh。这一版按需求先这样，
  唯一的补偿是后端那一步会校验"该用户存在且有启用的实例"。要真正防住，需要换成
  **一次性票据**（前端向后端申请、代理校验后作废）：代理侧只需替换 `resolveUser()`，
  链路其余部分不动。
- **URL 上的用户名会留在浏览器历史里**（首次进入那一跳）。上述票据方案同时能解决这一点。
- `dsh_user` cookie 是签名的 httpOnly cookie，但它只是"记住是谁"，**不是身份凭据** ——
  伪造它有和伪造 URL 同等的效果，所以没把它当安全边界。
- 顶层导航（`Sec-Fetch-Mode: navigate`）允许跨站进入，这样控制台才能在新标签页打开它；
  子资源、`fetch`/XHR、WebSocket 仍然要求同源（`Origin` 不匹配或 `Sec-Fetch-Site: cross-site` 一律 403）。
- 代理返回的 HTML 会注入 dsh 客户端需要的 `__DSH_TRANSPORT__.ownsHost` 与 `crypto.randomUUID`
  polyfill（非安全上下文下浏览器没有 `randomUUID`）；非 HTML 响应原样透传，不改写。

## 目录

```
server.js           全部逻辑（单文件）：配置加载 / 识别 / 校验 / 转发 / dsh 会话接管
config.example.js   配置模板（逐项中文注释）；复制成 config.js 改
config.js           真实配置（含内部密钥，gitignore）
tools/smoke.mjs     自检脚本（假后端 + 假 dsh，52 项断言）
Dockerfile          镜像（配置靠挂载注入，不打进镜像）
tokens.d/           dsh 启动令牌（dsh-new.sh 写入，gitignore）
sessions.json       dsh 会话缓存（gitignore）
```