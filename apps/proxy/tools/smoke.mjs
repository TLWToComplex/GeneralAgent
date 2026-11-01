/* ============================================================================
   proxy 自检：假后端 + 假 dsh 容器，不需要任何真环境

   验的是「代理自己那层」：
     · 识别用户（URL 的 ?username= → 签名 cookie → 302 到干净地址）
     · 向 后端 校验映射（走不通时的四种错误页：未登记 / 已停用 / 密钥不一致 / 后端不可达）
     · 转发（dsh 0.1.2 会话令牌交换、cookie 注入、HTML 注入、JSON 透传）
     · WebSocket 透传（带 cookie 才 101）
     · 同源补偿校验（顶层导航放行、子资源/接口跨站拒绝）
     · 映射缓存（TTL 内不重复打后端）

   用法: node tools/smoke.mjs
   退出码：0 全通过 / 1 有失败项。
   ========================================================================== */
import http from 'node:http'
import net from 'node:net'
import fs from 'node:fs'
import path from 'node:path'
import crypto from 'node:crypto'
import { createRequire } from 'node:module'

// server.js 是 CommonJS（proxy/package.json 里 type=commonjs），ESM 里要经 createRequire 载入
const { createProxy } = createRequire(import.meta.url)('../server.js')

const INTERNAL_SECRET = 'smoke-internal-secret'
const DSH_TOKEN = 'smoke-dsh-token'
const DSH_COOKIE = 'dsh-auth-smoke=ok'
const TMP_DIR = path.join(import.meta.dirname, '.tmp-smoke')

let passed = 0
const failed = []
const check = (name, ok, detail = '') => {
  if (ok) { passed++; console.log(`  ✓ ${name}`) } else { failed.push(name); console.log(`  ✗ ${name}${detail ? `   → ${detail}` : ''}`) }
}

const listen = (server) => new Promise((resolve) => server.listen(0, '127.0.0.1', () => resolve(server.address().port)))

// ---------------------------------------------------------------- 假后端
let backendHits = 0
const ROUTES = {
  // proxyUser 与 登录用户名 故意不同，用来验证"令牌文件按 proxyUser 取"
  demo: { containerName: 'dsh-demo', proxyUser: 'demo' },
  custom: { containerName: 'dsh-custom', proxyUser: 'custom-user', tokenFile: null },
}
const makeBackend = () => http.createServer((req, res) => {
  backendHits++
  const url = new URL(req.url, 'http://backend.local')
  const send = (status, body) => {
    res.writeHead(status, { 'content-type': 'application/json; charset=utf-8' })
    res.end(JSON.stringify(body))
  }
  if (url.pathname !== '/internal/dsh/route') return send(404, { code: 404, message: 'not found' })
  if (req.headers['x-internal-token'] !== INTERNAL_SECRET) {
    return send(401, { code: 401, message: '内部接口令牌无效' })
  }
  const username = url.searchParams.get('username')
  if (username === 'disabled') return send(403, { code: 403, message: '该用户的 dsh 实例已停用' })
  if (username === 'nomap') return send(404, { code: 404, message: '该用户未登记 dsh 实例' })
  if (username === 'ghost') return send(404, { code: 404, message: '用户不存在或已删除' })
  const r = ROUTES[username]
  if (!r) return send(404, { code: 404, message: '该用户未登记 dsh 实例' })
  const port = DSH_PORTS[username]
  send(200, {
    code: 200,
    message: 'success',
    data: {
      username,
      uuid: `uuid-${username}`,
      containerName: r.containerName,
      proxyUser: r.proxyUser,
      host: '127.0.0.1',
      port,
      target: `http://127.0.0.1:${port}/`,
      tokenFile: r.tokenFile || null,
      status: 1,
    },
  })
})

// ---------------------------------------------------------------- 假 dsh 容器
const DSH_PORTS = {}
const makeDsh = (label) => http.createServer((req, res) => {
  const url = new URL(req.url, 'http://dsh.local')
  if (url.searchParams.get('token') === DSH_TOKEN) {
    res.writeHead(303, { location: '/', 'set-cookie': `${DSH_COOKIE}; Path=/` })
    return res.end()
  }
  const authed = String(req.headers.cookie || '').includes(DSH_COOKIE)
  if (!authed) {
    res.writeHead(401, { 'content-type': 'application/json' })
    return res.end(JSON.stringify({ error: 'unauthorized' }))
  }
  if (url.pathname === '/api/ping') {
    res.writeHead(200, { 'content-type': 'application/json' })
    return res.end(JSON.stringify({ ok: true, container: label }))
  }
  res.writeHead(200, { 'content-type': 'text/html; charset=utf-8' })
  res.end(`<!doctype html><html><head><title>${label}</title></head><body>${label} OK</body></html>`)
})
// WebSocket 握手：只有带上 dsh 会话 cookie 才 101
const attachDshUpgrade = (server) => server.on('upgrade', (req, socket) => {
  const authed = String(req.headers.cookie || '').includes(DSH_COOKIE)
  if (!authed) {
    socket.end('HTTP/1.1 401 Unauthorized\r\nconnection: close\r\ncontent-length: 0\r\n\r\n')
    return
  }
  const key = req.headers['sec-websocket-key'] || ''
  const accept = crypto.createHash('sha1')
    .update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64')
  socket.write('HTTP/1.1 101 Switching Protocols\r\nupgrade: websocket\r\n'
    + `connection: Upgrade\r\nsec-websocket-accept: ${accept}\r\n\r\n`)
})

// ---------------------------------------------------------------- HTTP 小工具
const request = ({ port, path: p = '/', method = 'GET', headers = {} }) => new Promise((resolve, reject) => {
  const req = http.request({ hostname: '127.0.0.1', port, path: p, method, headers }, (res) => {
    let body = ''
    res.setEncoding('utf8')
    res.on('data', (c) => (body += c))
    res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body }))
  })
  req.on('error', reject)
  req.end()
})

/** 原始握手：拿到响应头就返回（WS 成功时连接会一直开着，不能等 end） */
const rawRequest = (port, text, timeoutMs = 4000) => new Promise((resolve, reject) => {
  const sock = net.connect(port, '127.0.0.1', () => sock.write(text))
  let buf = ''
  let done = false
  const finish = () => { if (!done) { done = true; clearTimeout(timer); sock.destroy(); resolve(buf) } }
  const timer = setTimeout(finish, timeoutMs)
  sock.on('data', (d) => { buf += d.toString('latin1'); if (buf.includes('\r\n\r\n')) finish() })
  sock.on('end', finish)
  sock.on('error', (err) => { if (!done) { done = true; clearTimeout(timer); reject(err) } })
})

const cookieOf = (res, name) => {
  const raw = res.headers['set-cookie'] || []
  const hit = raw.find((c) => c.startsWith(`${name}=`))
  return hit ? hit.split(';')[0] : null
}

// ---------------------------------------------------------------- 环境准备
fs.rmSync(TMP_DIR, { recursive: true, force: true })
fs.mkdirSync(TMP_DIR, { recursive: true })
const tokensDir = path.join(TMP_DIR, 'tokens.d')
fs.mkdirSync(tokensDir, { recursive: true })
fs.writeFileSync(path.join(tokensDir, 'demo'), `${DSH_TOKEN}\n`)
// 注意：tokens.d 里**故意**不放 custom-user —— 它的令牌只能从后端下发的 tokenFile 拿到
fs.writeFileSync(path.join(TMP_DIR, 'custom-token'), `${DSH_TOKEN}\n`) // tokenFile 指定路径的分支

const backend = makeBackend()
const backendPort = await listen(backend)
const dsh = makeDsh('dsh-demo')
const dshPort = await listen(dsh)
attachDshUpgrade(dsh)
const dsh2 = makeDsh('dsh-custom')
const dsh2Port = await listen(dsh2)
attachDshUpgrade(dsh2)
DSH_PORTS.demo = dshPort
DSH_PORTS.custom = dsh2Port

// 中性配置文件：每个实例都显式指向它，这样自检结果与机器上真实的 config.js 无关
const NEUTRAL_CFG = path.join(TMP_DIR, 'neutral-config.js')
fs.writeFileSync(NEUTRAL_CFG, "module.exports = {}\n")

const newApp = (overrides = {}) => createProxy({
  configFile: NEUTRAL_CFG,
  entryOrigin: 'http://proxy.local',
  backendBaseUrl: `http://127.0.0.1:${backendPort}`,
  internalSecret: INTERNAL_SECRET,
  frontendLoginUrl: 'http://proxy.local:5173/#/login',
  cookieSecret: 'smoke-cookie-secret',
  tokensDir,
  sessionsFile: path.join(TMP_DIR, 'sessions.json'),
  ...overrides,
})

console.log('proxy 自检（假后端 + 假 dsh）')

// ------------------------------------------------------------------ ⓪ 配置文件
console.log('\n=== ⓪ 配置文件（config.js）===')
const cfgDir = path.join(TMP_DIR, 'cfg')
fs.mkdirSync(cfgDir, { recursive: true })
const CFG_FILE = path.join(cfgDir, 'proxy-config.js')
fs.writeFileSync(CFG_FILE, `module.exports = {
  internalSecret: 'secret-from-file',
  port: 8123,
  backendBaseUrl: 'http://127.0.0.1:1',
  tokensDir: './tk',
  sessionsFile: './sess.json',
  typoKey: 'x',
}\n`)
let warns = []
const realWarn = console.warn
console.warn = (...a) => warns.push(a.join(' '))
const fromFile = createProxy({ configFile: CFG_FILE })
console.warn = realWarn
check('从文件读到值', fromFile.config.port === 8123 && fromFile.config.internalSecret === 'secret-from-file')
check('未写的项用默认值', fromFile.config.routeCacheTtlMs === 30000
  && fromFile.config.entryOrigin === 'http://172.16.235.50', JSON.stringify({
  ttl: fromFile.config.routeCacheTtlMs, origin: fromFile.config.entryOrigin,
}))
check('相对路径以配置文件所在目录为基准', fromFile.config.tokensDir === path.join(cfgDir, 'tk')
  && fromFile.config.sessionsFile === path.join(cfgDir, 'sess.json'), fromFile.config.tokensDir)
check('frontendLoginUrl 留空时由 entryOrigin 推导',
  fromFile.config.frontendLoginUrl === 'http://172.16.235.50:5173/#/login', fromFile.config.frontendLoginUrl)
check('拼错的键名会被明确报出来', warns.some((w) => w.includes('typoKey')), warns.join(' | '))
check('日志里记下了用的哪个配置文件', fromFile.config.configFile === CFG_FILE, fromFile.config.configFile)

try {
  createProxy({ configFile: path.join(cfgDir, 'bad-port.js') })
  fs.writeFileSync(path.join(cfgDir, 'bad-port.js'), "module.exports = { internalSecret: 'x', port: 'abc' }\n")
  createProxy({ configFile: path.join(cfgDir, 'bad-port.js') })
  check('port 不是数字 → 启动即报错', false, '居然起来了')
} catch (err) {
  check('port 不是数字 → 启动即报错', String(err.message).includes('port'), String(err.message))
}
try {
  createProxy({ configFile: path.join(cfgDir, 'no-such-file.js') })
  check('显式指定的配置文件不存在 → 报错', false, '居然起来了')
} catch (err) {
  check('显式指定的配置文件不存在 → 报错（并给出 cp 提示）',
    String(err.message).includes('找不到配置文件') && String(err.message).includes('config.example.js'),
    String(err.message).split('\n')[0])
}

// ------------------------------------------------------------------ ① 启动门槛
console.log('\n=== ① 未配置内部密钥：拒绝启动 ===')
try {
  createProxy({ configFile: NEUTRAL_CFG, internalSecret: '' })
  check('未配置密钥直接抛错', false, '居然起来了')
} catch (err) {
  check('未配置密钥直接抛错', String(err.message).includes('internalSecret'), String(err.message).split('\n')[0])
}

const app = newApp()
await new Promise((r) => app.server.listen(0, '127.0.0.1', r))
const proxyPort = app.server.address().port

// ------------------------------------------------------------------ ② 身份识别
console.log('\n=== ② 识别用户：?username= → 签名 cookie → 302 ===')
let res = await request({ port: proxyPort, path: '/' })
check('无身份 → 401', res.status === 401, `实际 ${res.status}`)
check('错误页说明"没有登录页"', res.body.includes('缺少用户身份'))
check('错误页带登录页链接', res.body.includes('http://proxy.local:5173/#/login'))

res = await request({ port: proxyPort, path: '/?username=demo' })
check('带 username → 302', res.status === 302, `实际 ${res.status}`)
check('Location 去掉 username', res.headers.location === '/', res.headers.location)
const cookie = cookieOf(res, 'dsh_user')
check('签发了 dsh_user cookie', !!cookie)
const setCookieRaw = (res.headers['set-cookie'] || [])[0] || ''
check('cookie 是 HttpOnly + SameSite=Lax', /HttpOnly/i.test(setCookieRaw) && /SameSite=Lax/i.test(setCookieRaw), setCookieRaw)

res = await request({ port: proxyPort, path: '/?username=demo&keep=1' })
check('其它查询参数保留', res.headers.location === '/?keep=1', res.headers.location)

res = await request({ port: proxyPort, path: '/', headers: { cookie: cookie } })
check('凭 cookie 可以直接进（子资源就靠这个）', res.status === 200, `实际 ${res.status}`)
check('转发的是 dsh 页面本身', res.body.includes('dsh-demo OK'))
check('注入了回环身份钩子', res.body.includes('__DSH_TRANSPORT__'))
check('注入了 randomUUID polyfill', res.body.includes('randomUUID'))
check('HTML 注入后 content-length 一致', Number(res.headers['content-length']) === Buffer.byteLength(res.body))

// 会话交换：假 dsh 只在带 dsh-auth cookie 时才给 200，所以上面的 200 已经证明 cookie 被注入
check('dsh 会话令牌已交换并注入', app.state.sessions.has('demo'))

// ------------------------------------------------------------------ ③ 透传
console.log('\n=== ③ 非 HTML 原样透传 ===')
res = await request({ port: proxyPort, path: '/api/ping', headers: { cookie } })
check('JSON 透传 200', res.status === 200, `实际 ${res.status}`)
check('JSON 内容未被改写', res.body === '{"ok":true,"container":"dsh-demo"}', res.body.slice(0, 80))

// ------------------------------------------------------------------ ④ 错误分支
console.log('\n=== ④ 校验不通过时的错误页 ===')
res = await request({ port: proxyPort, path: '/?username=nomap' })
check('未登记实例 → 404', res.status === 404, `实际 ${res.status}`)
check('文案来自后端', res.body.includes('该用户未登记 dsh 实例'))
res = await request({ port: proxyPort, path: '/?username=ghost' })
check('用户不存在 → 404', res.status === 404, `实际 ${res.status}`)
res = await request({ port: proxyPort, path: '/?username=disabled' })
check('实例已停用 → 403', res.status === 403, `实际 ${res.status}`)
check('停用错误页给了恢复提示', res.body.includes('status'))

console.log('\n=== ⑤ 密钥/后端异常 ===')
const badSecret = newApp({ internalSecret: 'wrong-secret' })
await new Promise((r) => badSecret.server.listen(0, '127.0.0.1', r))
const badPort = badSecret.server.address().port
res = await request({ port: badPort, path: '/?username=demo' })
check('密钥不一致 → 500', res.status === 500, `实际 ${res.status}`)
check('提示指向配置项', res.body.includes('internalSecret') && res.body.includes('dsh.internal_secret'))
check('不把密钥写进页面', !res.body.includes('wrong-secret') && !res.body.includes(INTERNAL_SECRET))
badSecret.server.close()

const noBackend = newApp({ backendBaseUrl: 'http://127.0.0.1:1' })
await new Promise((r) => noBackend.server.listen(0, '127.0.0.1', r))
const noPort = noBackend.server.address().port
res = await request({ port: noPort, path: '/?username=demo' })
check('后端不可达 → 502', res.status === 502, `实际 ${res.status}`)
check('提示后端不可达', res.body.includes('后端服务不可达'))
noBackend.server.close()

console.log('\n=== ⑥ 令牌文件缺失：进得去校验但建不了会话 ===')
// 用独立的 sessions 文件：主实例已经缓存了 demo 的会话，共用就测不出"建不了会话"
const noToken = newApp({
  tokensDir: path.join(TMP_DIR, 'empty-tokens'),
  sessionsFile: path.join(TMP_DIR, 'sessions-notoken.json'),
})
await new Promise((r) => noToken.server.listen(0, '127.0.0.1', r))
const noTokenPort = noToken.server.address().port
res = await request({ port: noTokenPort, path: '/?username=demo' })
check('先给 cookie（302）', res.status === 302, `实际 ${res.status}`)
const noTokenCookie = cookieOf(res, 'dsh_user')
res = await request({ port: noTokenPort, path: '/', headers: { cookie: noTokenCookie } })
check('建不了会话 → 502 且给出 refresh 指引', res.status === 502 && res.body.includes('dsh-new.sh refresh'), `实际 ${res.status}`)
noToken.server.close()

// ------------------------------------------------------------------ ⑦ cookie 完整性
console.log('\n=== ⑦ cookie 被篡改 ===')
const tampered = cookie.replace(/.$/, (c) => (c === 'A' ? 'B' : 'A'))
res = await request({ port: proxyPort, path: '/', headers: { cookie: tampered } })
check('签名不对 → 当作没有身份', res.status === 401, `实际 ${res.status}`)
const forged = `dsh_user=${Buffer.from('admin').toString('base64url')}.${Buffer.from('x'.repeat(43)).toString('base64url')}`
res = await request({ port: proxyPort, path: '/', headers: { cookie: forged } })
check('伪造 cookie 不认（换用户名必须走 URL）', res.status === 401, `实际 ${res.status}`)

// ------------------------------------------------------------------ ⑧ tokenFile 分支
console.log('\n=== ⑧ tokenFile 由后端指定时按它取令牌 ===')
const customApp = newApp({
  sessionsFile: path.join(TMP_DIR, 'sessions-custom.json'),
  routeCacheTtlMs: 0,
})
// custom 的 tokenFile 指到 TMP_DIR/custom-token（不在 tokens.d 里）
ROUTES.custom.tokenFile = path.join(TMP_DIR, 'custom-token')
await new Promise((r) => customApp.server.listen(0, '127.0.0.1', r))
const customPort = customApp.server.address().port
res = await request({ port: customPort, path: '/?username=custom' })
const customCookie = cookieOf(res, 'dsh_user')
res = await request({ port: customPort, path: '/', headers: { cookie: customCookie } })
check('按 tokenFile 取到令牌 → 200', res.status === 200, `实际 ${res.status}`)
check('转发到 custom 容器', res.body.includes('dsh-custom OK'))
check('会话键用的是 proxyUser', customApp.state.sessions.has('custom-user'))
customApp.server.close()
ROUTES.custom.tokenFile = null

// ------------------------------------------------------------------ ⑨ 缓存
console.log('\n=== ⑨ 映射缓存 ===')
// 用干净实例计量：主实例的 demo 映射早就缓存过了，共用就测不出"只打一次"
const cacheApp = newApp({ sessionsFile: path.join(TMP_DIR, 'sessions-cache.json') })
await new Promise((r) => cacheApp.server.listen(0, '127.0.0.1', r))
const cachePort = cacheApp.server.address().port
res = await request({ port: cachePort, path: '/?username=demo' })
const cacheCookie = cookieOf(res, 'dsh_user')
const base = cacheApp.stats().routeFetched
await request({ port: cachePort, path: '/', headers: { cookie: cacheCookie } })
await request({ port: cachePort, path: '/', headers: { cookie: cacheCookie } })
await request({ port: cachePort, path: '/', headers: { cookie: cacheCookie } })
check('TTL 内 3 次请求只打后端 1 次', cacheApp.stats().routeFetched - base === 0,
  `实际 ${cacheApp.stats().routeFetched - base}（入口那次已打后端）`)
check('入口那次确实打过后端', base === 1, `实际 ${base}`)
cacheApp.server.close()

const zeroApp = newApp({ routeCacheTtlMs: 0, sessionsFile: path.join(TMP_DIR, 'sessions-zero.json') })
await new Promise((r) => zeroApp.server.listen(0, '127.0.0.1', r))
const zeroPort = zeroApp.server.address().port
res = await request({ port: zeroPort, path: '/?username=demo' })
const zeroCookie = cookieOf(res, 'dsh_user')
await request({ port: zeroPort, path: '/', headers: { cookie: zeroCookie } })
await request({ port: zeroPort, path: '/', headers: { cookie: zeroCookie } })
check('TTL=0 时每次都打后端（便于改端口后立即生效）', zeroApp.stats().routeFetched === 3, `实际 ${zeroApp.stats().routeFetched}`)
zeroApp.server.close()

// ------------------------------------------------------------------ ⑩ 同源校验
console.log('\n=== ⑩ 同源补偿校验 ===')
res = await request({
  port: proxyPort,
  path: '/?username=demo',
  headers: {
    origin: 'http://console.example', // 前端与 proxy 不同站
    'sec-fetch-site': 'cross-site',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-dest': 'document',
  },
})
check('顶层导航（点新建会话开新标签页）放行', res.status === 302, `实际 ${res.status}`)
res = await request({
  port: proxyPort,
  path: '/api/ping',
  headers: { cookie, 'sec-fetch-site': 'cross-site', 'sec-fetch-mode': 'cors' },
})
check('子资源/fetch 跨站仍拒绝', res.status === 403, `实际 ${res.status}`)
res = await request({
  port: proxyPort,
  path: '/api/ping',
  headers: { cookie, origin: 'http://evil.example' },
})
check('Origin 不匹配仍拒绝', res.status === 403, `实际 ${res.status}`)
res = await request({
  port: proxyPort,
  path: '/api/ping',
  headers: { cookie, origin: 'http://proxy.local' },
})
check('Origin 匹配放行', res.status === 200, `实际 ${res.status}`)

// ------------------------------------------------------------------ ⑪ WebSocket
console.log('\n=== ⑪ WebSocket 透传 ===')
const wsHandshake = (cookies, hostPort) => `GET /ws HTTP/1.1\r\nHost: 127.0.0.1:${hostPort}\r\n`
  + 'Upgrade: websocket\r\nConnection: Upgrade\r\n'
  + 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\nSec-WebSocket-Version: 13\r\n'
  + (cookies ? `Cookie: ${cookies}\r\n` : '')
  + '\r\n'
let wsRes = await rawRequest(proxyPort, wsHandshake(cookie, proxyPort))
check('带 cookie → 101', /HTTP\/1\.1 101/.test(wsRes), wsRes.split('\r\n')[0])
wsRes = await rawRequest(proxyPort, wsHandshake('', proxyPort))
check('无身份 → 401', /HTTP\/1\.1 401/.test(wsRes), wsRes.split('\r\n')[0])
wsRes = await rawRequest(proxyPort, wsHandshake('dsh_user=garbage.sig', proxyPort))
check('伪造 cookie → 401', /HTTP\/1\.1 401/.test(wsRes), wsRes.split('\r\n')[0])
const nomapCookie = cookieOf(await request({ port: proxyPort, path: '/?username=nomap' }), 'dsh_user')
if (nomapCookie) {
  wsRes = await rawRequest(proxyPort, wsHandshake(nomapCookie, proxyPort))
  check('未登记用户 → 404', /HTTP\/1\.1 404/.test(wsRes), wsRes.split('\r\n')[0])
}

// ------------------------------------------------------------------ 收尾
app.server.close()
backend.close()
dsh.close()
dsh2.close()
fs.rmSync(TMP_DIR, { recursive: true, force: true })

console.log(`\n结果: PASS=${passed} FAIL=${failed.length}`)
if (failed.length) {
  for (const f of failed) console.log(`  - ${f}`)
  console.log('proxy 自检未全部通过 ✗')
  process.exit(1)
}
console.log('proxy 自检全部通过 ✓')
// 显式退出：WebSocket 与 keep-alive 连接会让事件循环一直挂着
process.exit(0)