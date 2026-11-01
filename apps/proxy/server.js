// 前置代理：按 ?username= 识别用户 → 向后端校验映射 → 反代到该用户的 dsh 实例
//
// 本代理**不再有登录页**：所有登录都在前端（GA-frontend-v2）完成，代理只做三件事 ——
//   ① 识别用户（URL 上的 ?username=<用户名>）
//   ② 向后端校验（GET /internal/dsh/route，共享密钥；用户存在 + 已登记 + 未停用）
//   ③ 转发（含 WebSocket），并接管 dsh 0.1.2 的会话 cookie
//
// 关于「URL 带用户名」的两点事实，部署前务必知道：
//
// 1. URL 上的用户名只在**进入的那一次**有效。浏览器对子资源（JS/CSS/API）与 WebSocket
//    不会带父页面的查询串，所以代理把它落成一个自己签名的 httpOnly cookie（dsh_user），
//    并 302 到去掉 username 的同一个地址；后续请求全部靠 cookie 识别。
//    302 还有第二个好处：dsh 自己看不到这个参数，不会污染它的路由与 Refere。
// 2. 这条路径**可伪造**：谁都能把 URL 里的 username 换成别人。这一版按需求先接受。
//    将来换成「一次性票据」时，只需要替换 resolveUser()，其余代码不动。
//
// 路线 1（回环改写）+ 0.1.2 会话接管：
// - 转发时 changeOrigin 把 Host 改写为后端回环 authority（127.0.0.1:<端口>），
//   Origin / Sec-Fetch-* 经同源补偿校验后删除 → dsh 视角等同本机直连。
// - dsh 0.1.2 起强制浏览器会话认证：index 页、全部 /api、WebSocket 都必须带
//   该容器启动令牌（启动日志里的 ?token=...）换来的签名 cookie（dsh-auth-*），
//   否则 401。本代理在服务端完成令牌交换并持有 cookie，转发时注入；用户浏览器
//   完全不接触 dsh 会话。
// - 令牌文件：tokensDir/<proxyUser>，由 dsh-new.sh 写入（后端映射表里的 proxyUser 为准，
//   若后端下发了 tokenFile 则用它）。容器重建/重启后令牌会变化，用
//   ./dsh-new.sh refresh <容器名> [用户] 重新获取。
// - 浏览器端 isLoopback 由 TRANSPORT_HOOK 注入 ownsHost:true 强制为 true，设置持久化保持 host 模式。
//
// 配置：
//   全部配置来自 proxy/config.js（CommonJS 模块，可写注释；正式部署把它挂进容器：
//   -v /opt/dsh/proxy-config.js:/app/config.js）。也可以用 --config <路径> 指定别处，
//   或 node -e "require('./server.js')" 之外直接调用 createProxy(overrides)。
//   **不读任何环境变量**：这样配置只有一个来源，挂载/回滚都是一份文件的事。
//   各项含义见 config.example.js（每一项都可省略，省略即用那里的默认值）。
//
// run: npm start            （先在 proxy/config.js 里配好 internalSecret）
// 自检: npm run smoke       （起假后端 + 假 dsh，不需要真容器、不需要配置文件）
const http = require('http')
const crypto = require('crypto')
const fs = require('fs')
const path = require('path')
const httpProxy = require('http-proxy')

/** 入口参数名：前端「新建会话」拼的就是这个（两边必须一致） */
const USERNAME_PARAM = 'username'
/** 识别用户用的 cookie 名 */
const COOKIE_NAME = 'dsh_user'
/** cookie 有效期：8 小时（够一个工作日，且不依赖后端 JWT 的 1 小时） */
const COOKIE_TTL_MS = 8 * 3600 * 1000

// ---------------------------------------------------------------------------
// 小工具
// ---------------------------------------------------------------------------
const b64url = (buf) => Buffer.from(buf).toString('base64url')

/** 把用户名签成 cookie 值：`<base64url(用户名)>.<HMAC>` */
const signUser = (username, secret) => {
  const payload = b64url(username)
  const sig = crypto.createHmac('sha256', secret).update(payload).digest('base64url')
  return `${payload}.${sig}`
}

/** 校验并解出 cookie 里的用户名；签名不对/被篡改一律当作"没有身份" */
const verifyUserCookie = (value, secret) => {
  if (typeof value !== 'string' || !value.includes('.')) return null
  const [payload, sig] = value.split('.')
  if (!payload || !sig) return null
  const expect = crypto.createHmac('sha256', secret).update(payload).digest('base64url')
  const a = Buffer.from(sig)
  const b = Buffer.from(expect)
  if (a.length !== b.length || !crypto.timingSafeEqual(a, b)) return null
  try {
    const username = Buffer.from(payload, 'base64url').toString('utf8').trim()
    return username || null
  } catch {
    return null
  }
}

/** 读 cookie 里的某个键 */
const readCookie = (req, name) => {
  const m = new RegExp(`(?:^|;\\s*)${name}=([^;]*)`).exec(req.headers.cookie || '')
  return m ? decodeURIComponent(m[1]) : null
}

/** 顶层文档导航：等价于"用户在地址栏敲了这个地址"，允许跨站进来 */
const isNavigation = (req) =>
  String(req.headers['sec-fetch-mode'] || '') === 'navigate'
  || String(req.headers['sec-fetch-dest'] || '') === 'document'

/**
 * 同源补偿校验（路线 1 的安全底线）：转发时会删除 Origin，故必须先在此校验。
 *
 * 与上一版的差别：**顶层导航放行**。前端与 proxy 同机不同端口（甚至不同站）时，
 * 从控制台点「新建会话」打开新标签页，浏览器会带 Sec-Fetch-Site: cross-site，
 * 若照旧拒绝，用户一进就 403。导航本身是只读的 GET，且拿不到响应内容，
 * 放行的风险等于"别人把地址贴给你"，与 URL 带用户名这一版的取舍一致。
 * 子资源 / fetch / XHR / WebSocket 仍然严格：跨站或 Origin 不匹配一律拒绝。
 */
const makeOriginGuard = (entryOrigin) => (req) => {
  if (isNavigation(req)) return true
  if (String(req.headers['sec-fetch-site'] || '') === 'cross-site') return false
  const origin = req.headers.origin
  if (origin === undefined) return true
  try { return new URL(origin).origin === entryOrigin } catch { return false }
}

/** 出错时的回应页：说清原因 + 给一个回登录页的入口（本代理没有登录页） */
const errorPage = (status, title, detail, hint, loginUrl) => `<!doctype html><html lang="zh-CN"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${title}</title>
<style>
  body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;display:grid;place-items:center;min-height:100vh;margin:0;background:#f5f6f8;color:#1b2436}
  .card{background:#fff;padding:30px 32px;border-radius:14px;box-shadow:0 6px 28px rgba(20,30,50,.10);width:min(460px,92vw)}
  h1{font-size:17px;margin:0 0 6px}
  .code{font-family:ui-monospace,Consolas,monospace;font-size:12px;color:#8b93a3;margin:0 0 16px}
  p{margin:0 0 10px;font-size:13.5px;line-height:1.7;color:#3c4761}
  .hint{font-size:12.5px;color:#6b7488;border-top:1px solid #eceff4;padding-top:12px;margin-top:16px;white-space:pre-wrap}
  a{display:inline-block;margin-top:18px;padding:9px 16px;border-radius:8px;background:#2d6cdf;color:#fff;text-decoration:none;font-size:13.5px}
</style>
<div class="card">
  <h1>${title}</h1>
  <p class="code">HTTP ${status}</p>
  <p>${detail}</p>
  ${hint ? `<p class="hint">${hint}</p>` : ''}
  <a href="${loginUrl}">回到登录页</a>
</div></html>`

const escapeHtml = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))

/**
 * 读取配置文件（proxy/config.js，CommonJS 模块）。
 *
 * 为什么用配置文件而不是环境变量：正式部署时要把它挂进容器
 * （`-v /opt/dsh/proxy-config.js:/app/config.js`），配置文件能写注释、能一眼看全、
 * 也能被运维直接改；散在环境变量里既看不见历史也容易漏项。
 *
 * 这里**不读任何环境变量**：配置只有一个来源，就是这份文件
 * （自检脚本通过 createProxy(overrides) 直接传值）。
 *
 * 校验失败抛错（start() 会打印后退出）——配置错在启动时说，而不是等第一个请求报 500。
 */
const CONFIG_DEFAULTS = {
  port: 80,
  backendBaseUrl: 'http://127.0.0.1:8038',
  entryOrigin: 'http://172.16.235.50',
  frontendLoginUrl: '',            // 空 = 由 entryOrigin 推导出 :5173/#/login
  tokensDir: './tokens.d',
  sessionsFile: './sessions.json',
  routeCacheTtlMs: 30000,
  internalSecret: '',
  cookieSecret: '',                // 空 = 每次启动随机
  cookieSecure: false,
}

const CONFIG_KEYS = Object.keys(CONFIG_DEFAULTS)

function loadConfigFile(file) {
  const abs = path.resolve(file)
  if (!fs.existsSync(abs)) {
    throw new Error(
      `找不到配置文件 ${abs}\n`
      + '  请复制模板并按环境修改：cp config.example.js config.js\n'
      + '  Docker：把宿主机那份挂进来 —— docker run --network host \\\n'
      + '            -v /opt/dsh/proxy-config.js:/app/config.js dsh-proxy',
    )
  }
  let raw
  try {
    // 配置文件是 CommonJS 模块：require 即可（改完文件需重启进程生效）
    raw = require(abs)
  } catch (err) {
    throw new Error(`配置文件 ${abs} 载入失败：${err.message}`)
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error(`配置文件 ${abs} 必须 module.exports 一个对象，例如 module.exports = { port: 80 }`)
  }

  // 拼错的键名会被静默忽略，这里明确报出来（打错一个字母却"没生效"最难查）
  const unknown = Object.keys(raw).filter((k) => !CONFIG_KEYS.includes(k))
  if (unknown.length > 0) {
    console.warn(`[config] ${abs} 里有无法识别的配置项，已忽略：${unknown.join(', ')}`)
    console.warn(`[config] 可用配置项：${CONFIG_KEYS.join(', ')}`)
  }

  const baseDir = path.dirname(abs)
  const num = (v) => (typeof v === 'string' && v.trim() !== '' ? Number(v) : v)
  const cfg = { ...CONFIG_DEFAULTS, ...raw }

  // 类型/范围校验：配置错了要在启动时说出来，而不是等第一个请求报 500
  if (!Number.isInteger(num(cfg.port)) || num(cfg.port) < 1 || num(cfg.port) > 65535) {
    throw new Error(`[config] port 必须是 1–65535 的整数，当前是 ${JSON.stringify(raw.port)}`)
  }
  cfg.port = num(cfg.port)
  for (const key of ['backendBaseUrl', 'entryOrigin', 'frontendLoginUrl', 'tokensDir', 'sessionsFile', 'internalSecret', 'cookieSecret']) {
    if (typeof cfg[key] !== 'string') throw new Error(`[config] ${key} 必须是字符串，当前是 ${JSON.stringify(raw[key])}`)
  }
  if (typeof num(cfg.routeCacheTtlMs) !== 'number' || Number.isNaN(num(cfg.routeCacheTtlMs)) || num(cfg.routeCacheTtlMs) < 0) {
    throw new Error(`[config] routeCacheTtlMs 必须是 ≥0 的数字（0 = 不缓存），当前是 ${JSON.stringify(raw.routeCacheTtlMs)}`)
  }
  cfg.routeCacheTtlMs = num(cfg.routeCacheTtlMs)
  if (typeof cfg.cookieSecure !== 'boolean') {
    throw new Error(`[config] cookieSecure 必须是 true / false，当前是 ${JSON.stringify(raw.cookieSecure)}`)
  }
  for (const key of ['backendBaseUrl', 'entryOrigin']) {
    try { new URL(cfg[key]) } catch { throw new Error(`[config] ${key} 不是合法 URL：${JSON.stringify(cfg[key])}`) }
  }

  // 相对路径以**配置文件所在目录**为基准：容器里 /app/config.js + './tokens.d' → /app/tokens.d
  for (const key of ['tokensDir', 'sessionsFile']) {
    if (cfg[key] && !path.isAbsolute(cfg[key])) cfg[key] = path.join(baseDir, cfg[key])
  }
  cfg.entryOrigin = new URL(cfg.entryOrigin).origin
  if (!cfg.frontendLoginUrl) cfg.frontendLoginUrl = `${cfg.entryOrigin}:5173/#/login`
  cfg.backendBaseUrl = cfg.backendBaseUrl.replace(/\/+$/, '')
  cfg.configFile = abs
  return cfg
}

// ---------------------------------------------------------------------------
// 主构造函数：配置文件 + 显式覆盖（自检脚本直接用 overrides，不碰文件）
// ---------------------------------------------------------------------------
/** --config <路径> 指定配置文件；默认 <proxy>/config.js */
function resolveConfigPath(argv = process.argv.slice(2)) {
  const i = argv.indexOf('--config')
  return (i !== -1 && argv[i + 1]) || path.join(__dirname, 'config.js')
}

function createProxy(overrides = {}) {
  const explicitFile = overrides.configFile !== undefined
  const configFile = explicitFile ? overrides.configFile : resolveConfigPath()
  // 显式指定了配置文件 → 必须存在（start() 走这条，缺文件时报"请 cp config.example.js"）；
  // 没显式指定（自检脚本、以库方式调用）→ 存在才读，否则用内置默认值。
  let fileCfg = { ...CONFIG_DEFAULTS }
  if (configFile && (explicitFile || fs.existsSync(path.resolve(configFile)))) {
    fileCfg = loadConfigFile(configFile)
  }

  // 合并规则：overrides（显式传值）> 配置文件 > 内置默认值
  const merged = { ...CONFIG_DEFAULTS, ...fileCfg }
  for (const [k, v] of Object.entries(overrides)) if (v !== undefined) merged[k] = v

  let entryOrigin = merged.entryOrigin
  try { entryOrigin = new URL(entryOrigin).origin } catch { /* 交给下面的显式校验 */ }

  const config = {
    entryOrigin,
    backendBaseUrl: String(merged.backendBaseUrl).replace(/\/+$/, ''),
    internalSecret: merged.internalSecret,
    frontendLoginUrl: merged.frontendLoginUrl || `${entryOrigin}:5173/#/login`,
    routeCacheTtlMs: Number(merged.routeCacheTtlMs ?? 30000),
    cookieSecret: merged.cookieSecret || crypto.randomBytes(32).toString('hex'),
    cookieSecure: !!merged.cookieSecure,
    tokensDir: merged.tokensDir,
    sessionsFile: merged.sessionsFile,
    port: Number(merged.port ?? 80),
    configFile: fileCfg.configFile || (configFile ? path.resolve(configFile) : '(内置默认值)'),
  }

  if (!config.internalSecret) {
    // 与后端 dsh.internal_secret 的立场一致：宁可显式失败，也不留一个"谁都放进来"的代理
    throw new Error(
      `未配置内部密钥（配置文件：${config.configFile}）\n`
      + '  internalSecret 必须与后端 config/config.yaml 的 dsh.internal_secret\n'
      + '  （或后端的 DSH_INTERNAL_SECRET）完全相同，否则后端会 401。\n'
      + '  本地：cp config.example.js config.js 后填 internalSecret\n'
      + '  Docker：挂载配置文件 —— -v /opt/dsh/proxy-config.js:/app/config.js',
    )
  }

  const sameOriginGuard = makeOriginGuard(entryOrigin)
  const proxy = httpProxy.createProxyServer()

  // ------------------------------------------------------------------ 后端映射
  const routeCache = new Map() // username -> { route, at }
  let routeFetched = 0        // 自检用：真实打到后端的次数

  /** 查一次后端内部接口；返回 { route } 或 { error: { status, title, detail, hint } } */
  const fetchRoute = (username) => new Promise((resolve) => {
    routeFetched++
    const base = new URL(config.backendBaseUrl)
    const req = http.request({
      hostname: base.hostname,
      port: base.port || 80,
      path: `/internal/dsh/route?${USERNAME_PARAM}=${encodeURIComponent(username)}`,
      method: 'GET',
      headers: {
        accept: 'application/json',
        'x-internal-token': config.internalSecret,
      },
      timeout: 5000,
    }, (res) => {
      let body = ''
      res.setEncoding('utf8')
      res.on('data', (c) => (body += c))
      res.on('end', () => {
        let json = null
        try { json = JSON.parse(body) } catch { /* 非 JSON：按后端不可用处理 */ }
        if (res.statusCode === 200 && json && json.data) {
          const d = json.data
          return resolve({
            route: {
              username: d.username || username,
              proxyUser: d.proxyUser || username,
              containerName: d.containerName || '',
              host: d.host,
              port: d.port,
              target: d.target,
              tokenFile: d.tokenFile || null,
            },
          })
        }
        const message = (json && (json.message || json.detail)) || `HTTP ${res.statusCode}`
        if (res.statusCode === 404) {
          return resolve({ error: { status: 404, title: '无法进入 dsh 控制台', detail: escapeHtml(message), hint: '' } })
        }
        if (res.statusCode === 403) {
          return resolve({
            error: {
              status: 403, title: '该账号的 dsh 实例已停用', detail: escapeHtml(message),
              hint: '如需恢复，请联系管理员在映射表里把该用户的 status 改回 1。',
            },
          })
        }
        if (res.statusCode === 401 || res.statusCode === 503) {
          // 密钥不对 / 后端未启用内部接口：属部署配置问题，不要把细节抛给用户
          return resolve({
            error: {
              status: 500, title: '服务端配置有误', detail: '代理无法向后端校验用户映射。',
              hint: `后端返回：${escapeHtml(message)}\n请确认代理 config.js 的 internalSecret 与后端 dsh.internal_secret 一致。`,
            },
          })
        }
        resolve({
          error: {
            status: 502, title: '校验服务暂时不可用', detail: '查询用户映射失败，请稍后重试。',
            hint: `后端返回：${escapeHtml(message)}`,
          },
        })
      })
    })
    req.on('timeout', () => req.destroy(new Error('超时')))
    req.on('error', (err) => resolve({
      error: {
        status: 502, title: '后端服务不可达', detail: '代理联系不上后端，无法确认该账号的 dsh 实例。',
        hint: `目标 ${config.backendBaseUrl}：${escapeHtml(err.message)}`,
      },
    }))
    req.end()
  })

  /** 带缓存地解析映射；成功后缓存 TTL，失败不缓存（错误页本身就少见） */
  const resolveRoute = async (username) => {
    const hit = routeCache.get(username)
    if (hit && config.routeCacheTtlMs > 0 && Date.now() - hit.at < config.routeCacheTtlMs) {
      return { route: hit.route, cached: true }
    }
    const out = await fetchRoute(username)
    if (out.route) routeCache.set(username, { route: out.route, at: Date.now() })
    return out
  }

  // ------------------------------------------------------------------ dsh 会话
  const sessions = new Map() // proxyUser -> "dsh-auth-xxx=yyy"
  const inflight = new Map() // proxyUser -> 进行中的交换（并发去重）

  const loadSessions = () => {
    try {
      const obj = JSON.parse(fs.readFileSync(config.sessionsFile, 'utf8'))
      for (const [u, c] of Object.entries(obj)) if (typeof c === 'string' && c) sessions.set(u, c)
      if (sessions.size > 0) console.log(`[session] 已从 ${config.sessionsFile} 载入 ${sessions.size} 个缓存会话`)
    } catch { /* 首次运行或文件损坏：空启动，按需交换 */ }
  }
  const saveSessions = () => {
    try {
      fs.writeFileSync(config.sessionsFile, JSON.stringify(Object.fromEntries(sessions), null, 2), { mode: 0o600 })
    } catch (err) { console.error(`[session] 写 ${config.sessionsFile} 失败: ${err.message}`) }
  }

  /** 令牌文件路径：后端给了 tokenFile 就用它，否则按 tokensDir/<proxyUser> 推导 */
  const tokenPathFor = (route) => {
    const p = route.tokenFile || path.join(config.tokensDir, route.proxyUser)
    if (p.includes('..')) return null // 防路径穿越
    return p
  }
  const readToken = (route) => {
    const p = tokenPathFor(route)
    if (!p) return null
    try {
      const token = fs.readFileSync(p, 'utf8').trim()
      return token || null
    } catch { return null }
  }

  // 用令牌交换会话 cookie。不跟随 303（core http 本就不自动跟随），只取 Set-Cookie。
  const exchangeToken = (target, token) => new Promise((resolve, reject) => {
    const url = new URL(target)
    const req = http.request({
      hostname: url.hostname,
      port: url.port || 80,
      path: `/?token=${encodeURIComponent(token)}`,
      method: 'GET',
      headers: { accept: 'text/html' },
      timeout: 5000,
    }, (res) => {
      res.resume()
      const pairs = (res.headers['set-cookie'] || [])
        .map((c) => c.split(';')[0]).filter((p) => p.startsWith('dsh-auth-'))
      if (res.statusCode >= 300 && res.statusCode < 400 && pairs.length > 0) return resolve(pairs[0])
      reject(new Error(`HTTP ${res.statusCode}（未签发 dsh-auth cookie，令牌可能已失效）`))
    })
    req.on('timeout', () => req.destroy(new Error('超时')))
    req.on('error', reject)
    req.end()
  })

  const exchangeFor = async (route) => {
    const token = readToken(route)
    if (!token) {
      console.error(`[session] ${route.proxyUser}: 缺少启动令牌（期望文件 ${tokenPathFor(route) || '(路径非法)'}；`
        + `在服务器执行 ./dsh-new.sh refresh <容器名> ${route.proxyUser} 获取）`)
      return false
    }
    try {
      const cookie = await exchangeToken(route.target, token)
      sessions.set(route.proxyUser, cookie)
      saveSessions()
      console.log(`[session] ${route.proxyUser}: 令牌交换成功，dsh 会话已建立`)
      return true
    } catch (err) {
      console.error(`[session] ${route.proxyUser}: 令牌交换失败: ${err.message}`)
      return false
    }
  }
  // 有缓存直接过；没有则交换（同用户并发去重）
  const ensureSession = (route) => {
    if (sessions.has(route.proxyUser)) return Promise.resolve(true)
    let pending = inflight.get(route.proxyUser)
    if (!pending) {
      pending = exchangeFor(route).finally(() => inflight.delete(route.proxyUser))
      inflight.set(route.proxyUser, pending)
    }
    return pending
  }
  // 收到后端 401 后强制重新交换（旧缓存已作废）
  const forceExchange = (route) => {
    sessions.delete(route.proxyUser)
    let pending = inflight.get(route.proxyUser)
    if (!pending) {
      pending = exchangeFor(route).finally(() => inflight.delete(route.proxyUser))
      inflight.set(route.proxyUser, pending)
    }
    return pending
  }
  loadSessions()

  // ------------------------------------------------------------------ 身份识别
  /**
   * 从请求里解出用户名。
   * - URL 上的 ?username= 优先（进入的那一次，同时要求写 cookie）
   * - 否则用签名的 dsh_user cookie
   * 返回 { username, fromUrl }
   */
  const resolveUser = (req) => {
    let fromUrl = null
    try {
      fromUrl = (new URL(req.url, 'http://proxy.local').searchParams.get(USERNAME_PARAM) || '').trim()
    } catch { fromUrl = null }
    if (fromUrl) return { username: fromUrl, fromUrl: true }
    const cookieUser = verifyUserCookie(readCookie(req, COOKIE_NAME), config.cookieSecret)
    if (cookieUser) return { username: cookieUser, fromUrl: false }
    return { username: null, fromUrl: false }
  }

  const userCookie = (username) => {
    const parts = [
      `${COOKIE_NAME}=${signUser(username, config.cookieSecret)}`,
      'Path=/',
      'HttpOnly',
      'SameSite=Lax',
      `Max-Age=${Math.floor(COOKIE_TTL_MS / 1000)}`,
    ]
    if (config.cookieSecure) parts.push('Secure')
    return parts.join('; ')
  }

  // ------------------------------------------------------------------ 错误回应
  const respondError = (res, err) => {
    const html = errorPage(err.status, err.title, err.detail, err.hint, config.frontendLoginUrl)
    res.writeHead(err.status, { 'content-type': 'text/html; charset=utf-8', 'cache-control': 'no-store' })
    res.end(html)
  }

  /** 把 302 的目标算出来：同一个地址，去掉 username（其余参数保留） */
  const stripUsername = (reqUrl) => {
    try {
      const u = new URL(reqUrl, 'http://proxy.local')
      u.searchParams.delete(USERNAME_PARAM)
      const q = u.searchParams.toString()
      return u.pathname + (q ? `?${q}` : '')
    } catch { return '/' }
  }

  // ------------------------------------------------------------------ 代理装配
  // 代理错误处理：后端 dsh 容器不可达时返回友好提示，不卡死
  proxy.on('error', (err, req, res) => {
    if (res && !res.headersSent && typeof res.writeHead === 'function') {
      respondError(res, {
        status: 502, title: 'dsh 实例不可达',
        detail: `无法连接该账号的 dsh 实例（${escapeHtml(err.code || err.message)}）。`,
        hint: '请确认容器已启动，且映射表里的 host/port 与实际一致。',
      })
    } else if (res && typeof res.destroy === 'function') {
      res.destroy()
    }
  })

  // 出站删除浏览器源标记（HTTP 与 WebSocket 通用）：
  // Origin(公网入口) 与改写后的 Host(127.0.0.1) 不匹配会在 /api 围栏 403；必须
  // removeHeader，置空串仍会进入 Origin 分支并因解析失败 403。
  const stripBrowserMarkers = (proxyReq) => {
    proxyReq.removeHeader('origin')
    proxyReq.removeHeader('sec-fetch-site')
    proxyReq.removeHeader('sec-fetch-mode')
    proxyReq.removeHeader('sec-fetch-dest')
  }
  // 注入 dsh 会话 cookie（与浏览器自带的 dsh_user cookie 合并，互不影响）
  const attachSessionCookie = (proxyReq, req) => {
    const cookie = req.dshProxyUser ? sessions.get(req.dshProxyUser) : undefined
    if (!cookie) return
    const incoming = proxyReq.getHeader('cookie')
    proxyReq.setHeader('cookie', incoming ? `${incoming}; ${cookie}` : cookie)
  }
  proxy.on('proxyReq', (proxyReq, req) => { stripBrowserMarkers(proxyReq); attachSessionCookie(proxyReq, req) })   // HTTP 转发
  proxy.on('proxyReqWs', (proxyReq, req) => { stripBrowserMarkers(proxyReq); attachSessionCookie(proxyReq, req) }) // WebSocket upgrade

  // --- crypto.randomUUID polyfill 注入 ---
  // dsh 前端 SDK 依赖 crypto.randomUUID 生成 RPC ID；用户经 http://<服务器IP>:80
  // 访问属于非安全上下文，浏览器的 randomUUID 为 undefined，导致会话/模型目录
  // 加载失败。这里在反代的 HTML 响应 <head> 后注入基于 crypto.getRandomValues
  // 的 RFC 4122 v4 实现（本段逻辑等价于 dsh/remote-web-ui 自带的 uuid-polyfill）。
  const UUID_POLYFILL = `(function(){var g=typeof globalThis!=="undefined"?globalThis:typeof window!=="undefined"?window:self;if(typeof g.crypto==="undefined"){g.crypto={};}if(typeof g.crypto.randomUUID!=="function"){g.crypto.randomUUID=function(){var a=new Uint8Array(16);if(g.crypto.getRandomValues){g.crypto.getRandomValues(a);}else{for(var j=0;j<16;j++){a[j]=Math.random()*256|0;}}a[6]=(a[6]&0x0f)|0x40;a[8]=(a[8]&0x3f)|0x80;var h="",x="0123456789abcdef";for(var i=0;i<16;i++){h+=x[a[i]>>4]+x[a[i]&0xf];if(i===3||i===5||i===7||i===9)h+="-";}return h;};}})();`

  // --- 强制回环身份 ---
  // 客户端 ctx.connection.isLoopback 按 location.hostname 判定，经服务器 IP 访问
  // 恒为 false → 设置持久化降为 memory、设置页显示 unavailable。0.1.2 起官方客户端
  // 在 shell 启动前读取 globalThis.__DSH_TRANSPORT__.ownsHost：true 强制 isLoopback
  // 为 true，且不携带 createApiClient/fetch/loadBundle 时传输仍回落到默认
  // HTTP+WebSocket 载体（已核对 dsh-client-connection 源码）。
  // 注入点在 <head> 之后、启动清单与 shell 入口之前，先于一切 dsh 脚本执行。
  // 注意：该钩子原为自建传输的宿主（worker 运行时）设计，dsh 升级后需重新验证。
  const TRANSPORT_HOOK = `window.__DSH_TRANSPORT__=Object.assign(window.__DSH_TRANSPORT__||{},{ownsHost:true});`

  // 注入 <head> 的完整脚本：先置回环身份，再补 randomUUID polyfill
  const INJECT_JS = TRANSPORT_HOOK + UUID_POLYFILL

  const injectPolyfill = (html) => {
    const headIdx = html.search(/<head[^>]*>/i)
    if (headIdx !== -1) {
      const close = html.indexOf('>', headIdx) + 1
      return html.slice(0, close) + '<script>' + INJECT_JS + '</script>' + html.slice(close)
    }
    const htmlIdx = html.search(/<html[^>]*>/i)
    if (htmlIdx !== -1) {
      const close = html.indexOf('>', htmlIdx) + 1
      return html.slice(0, close) + '<script>' + INJECT_JS + '</script>' + html.slice(close)
    }
    return '<script>' + INJECT_JS + '</script>' + html
  }

  /** 写响应头：把「新签发的 dsh_user cookie」与后端自己的 Set-Cookie 合并上 */
  const writeUpstreamHeaders = (res, status, headers, extraCookies) => {
    const out = { ...headers }
    if (extraCookies && extraCookies.length) {
      out['set-cookie'] = [...(headers['set-cookie'] || []), ...extraCookies]
    }
    res.writeHead(status, out)
  }

  // 拦截后端响应：对未压缩的 HTML 注入 polyfill，其余（JSON/静态资源/SSE 等）原样透传
  proxy.on('proxyRes', (proxyRes, req, res) => {
    // 0.1.2 会话门禁：后端 401 说明会话 cookie 缺失/失效。
    // GET/HEAD 无请求体，可安全重放：强制重新交换令牌后重试一次。
    if (proxyRes.statusCode === 401 && req.dshProxyUser && !req.dshRetried
      && (req.method === 'GET' || req.method === 'HEAD')) {
      proxyRes.resume() // 丢弃该 401 响应体
      void forceExchange(req.dshRoute).then((ok) => {
        if (res.writableEnded) return
        if (!ok) {
          respondError(res, {
            status: 502, title: '无法建立 dsh 会话',
            detail: '该实例的启动令牌缺失或已失效，代理拿不到 dsh 会话。',
            hint: `请在服务器执行 ./dsh-new.sh refresh <容器名> ${req.dshProxyUser} 重新获取令牌。`,
          })
          return
        }
        req.dshRetried = true
        proxy.web(req, res, { target: req.dshRoute.target, changeOrigin: true, selfHandleResponse: true })
      })
      return
    }
    // 其余 401（POST 等带体请求，不重放）：清掉失效缓存，下个请求会重新交换；本次原样透传
    if (proxyRes.statusCode === 401 && req.dshProxyUser) sessions.delete(req.dshProxyUser)

    const ct = String(proxyRes.headers['content-type'] || '')
    const encoding = String(proxyRes.headers['content-encoding'] || '').toLowerCase()
    const isHtml = ct.includes('text/html') && !encoding

    if (!isHtml) {
      // 非 HTML 或已压缩：直接透传（保持 SSE/JSON/静态资源行为不变）
      writeUpstreamHeaders(res, proxyRes.statusCode, proxyRes.headers, req.dshSetCookies)
      proxyRes.pipe(res)
      return
    }

    const chunks = []
    proxyRes.on('data', (c) => chunks.push(c))
    proxyRes.on('end', () => {
      let html = Buffer.concat(chunks).toString('utf8')
      html = injectPolyfill(html)
      const body = Buffer.from(html, 'utf8')
      const headers = { ...proxyRes.headers }
      delete headers['transfer-encoding']
      headers['content-length'] = String(body.length)
      writeUpstreamHeaders(res, proxyRes.statusCode, headers, req.dshSetCookies)
      res.end(body)
    })
    proxyRes.on('error', () => res.destroy())
  })

  // ------------------------------------------------------------------ 请求主流程
  const server = http.createServer(async (req, res) => {
    // 0. 同源补偿校验（顶层导航放行，子资源/接口严格；详见 makeOriginGuard）
    if (!sameOriginGuard(req)) {
      res.writeHead(403, { 'content-type': 'text/plain; charset=utf-8' })
      return res.end('forbidden')
    }

    // 1. 识别用户
    const { username, fromUrl } = resolveUser(req)
    if (!username) {
      return respondError(res, {
        status: 401, title: '缺少用户身份',
        detail: '本代理不再提供登录页，请先从控制台登录，再点「新建会话」进入。',
        hint: '（如果你是从收藏夹或直接贴地址进来的，这个入口需要带上 ?username= 参数。）',
      })
    }

    // 2. 校验映射（有缓存就直接用）。URL 带来的用户名还要额外走一次「落 cookie + 302」，
    //    让浏览器后续的子资源与 WebSocket 请求能凭 cookie 被识别。
    const out = await resolveRoute(username)
    if (out.error) return respondError(res, out.error)
    const route = out.route
    if (!route || !route.target) {
      return respondError(res, {
        status: 502, title: '映射信息不完整',
        detail: '后端返回的映射里缺少反代目标地址。',
        hint: '请检查映射表的 host/port 字段是否填全。',
      })
    }
    if (fromUrl && (req.method === 'GET' || req.method === 'HEAD')) {
      // 302 到去掉 username 的同一个地址：dsh 本身永远看不到这个参数
      res.writeHead(302, {
        location: stripUsername(req.url),
        'set-cookie': userCookie(username),
        'cache-control': 'no-store',
      })
      return res.end()
    }

    // 3. 确保 dsh 会话 → 转发
    //    changeOrigin:true 把 Host 改写为后端回环 authority（127.0.0.1:<端口>）；
    //    会话 cookie 由 proxyReq 钩子注入；交换失败时仍转发，让后端 401 触发上方
    //    proxyRes 的恢复分支（给出可操作的错误提示）。
    req.dshUser = username
    req.dshProxyUser = route.proxyUser
    req.dshRoute = route
    if (fromUrl) req.dshSetCookies = [userCookie(username)]
    await ensureSession(route)
    proxy.web(req, res, { target: route.target, changeOrigin: true, selfHandleResponse: true })
  })

  // 4. WebSocket 透传（dsh 对话界面依赖）—— 与 HTTP 同一套：同源校验 → 识别用户
  //    → 校验映射 → 确保会话 → changeOrigin 改写 Host 为回环 → proxyReqWs 注入 cookie、
  //    删除 Origin/Sec-Fetch-*。WebSocket 握手不会带父页面查询串，所以这里主要靠 cookie。
  server.on('upgrade', async (req, socket, head) => {
    const refuse = (status, text) => {
      if (socket.writable) {
        socket.end(`HTTP/1.1 ${status} ${text}\r\nconnection: close\r\ncontent-length: 0\r\n\r\n`)
      } else {
        socket.destroy()
      }
    }
    if (!sameOriginGuard(req)) return refuse(403, 'Forbidden')
    const { username } = resolveUser(req)
    if (!username) return refuse(401, 'Unauthorized')
    const out = await resolveRoute(username)
    if (out.error) {
      const s = out.error.status
      return refuse(s === 404 || s === 403 ? s : 502, 'Refused')
    }
    const route = out.route
    if (!route || !route.target) return refuse(502, 'Bad Gateway')
    req.dshUser = username
    req.dshProxyUser = route.proxyUser
    req.dshRoute = route
    await ensureSession(route)
    if (!sessions.has(route.proxyUser)) return refuse(502, 'No dsh session') // 会话未建立：客户端会自行重连
    proxy.ws(req, socket, head, { target: route.target, changeOrigin: true })
  })

  return {
    server,
    config,
    state: { sessions, routeCache, inflight },
    stats: () => ({ routeFetched, sessions: sessions.size, cachedRoutes: routeCache.size }),
  }
}

function start() {
  let app
  try {
    app = createProxy({ configFile: resolveConfigPath() })
  } catch (err) {
    console.error(String(err.message || err))
    process.exit(1)
  }
  const c = app.config
  const PORT = c.port
  app.server.listen(PORT, () => {
    console.log(`proxy on http://127.0.0.1:${PORT}`)
    console.log(`  配置: ${c.configFile}`)
    console.log(`  入口: ?${USERNAME_PARAM}=<用户名>  → 校验后 302 到干净地址（并落 ${COOKIE_NAME} cookie）`)
    console.log(`  后端: ${c.backendBaseUrl}  (GET /internal/dsh/route)`)
    console.log(`  登录页: ${c.frontendLoginUrl}`)
    console.log(`  令牌: ${c.tokensDir}   会话: ${c.sessionsFile}`)
    console.log(`  映射缓存: ${c.routeCacheTtlMs}ms`)
  })
  app.server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
      console.error(`端口 ${PORT} 已被占用。改配置文件的 port，或先停掉占用该端口的进程。`)
      console.error('（Linux 绑 80 需要 root 或 setcap；Windows 需要管理员权限）')
    } else {
      console.error(`监听 ${PORT} 失败：${err.message}`)
    }
    process.exit(1)
  })
}

if (require.main === module) start()

module.exports = { createProxy, USERNAME_PARAM, COOKIE_NAME }