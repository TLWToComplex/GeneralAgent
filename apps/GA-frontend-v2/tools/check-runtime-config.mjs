/* ============================================================================
   运期配置（public/config/config.json）的端到端验收

   要证明的三件事，缺一不可：
     A. 构建产物里确实带上了 dist/config/config.json，且是合法 JSON；
     B. 应用启动时真的**读到并用上**了它 —— 不是"文件在但没人读"；
     C. 换掉那个文件（模拟 docker -v 挂载）后行为跟着变 —— 这才是本次改动的意义。
        C 是最关键的一条：B 只能说明默认路径通了，C 才说明"挂载覆盖"成立。
     D. 配置坏掉时不阻塞启动，退回默认值。

   免登录开关（`skipLogin` / `skipLoginUser`）的验收**不在本脚本**：A 段只验"字段存在且默认关闭"，
   开关打开后的行为与容错解析（"true"/1/"off"/乱写、空名字落 guest）走
   tools/smoke-login-ui.mjs 第 ⑧ 段 —— 那条是**行为级**的（看页面是否真的跳过登录页），不依赖下面前提。

   ⚠️ 既有问题（本次改动**没有**引入，也没修）：B/C/D 段依赖"运期配置模块是可独立加载的 chunk
   且保留公开导出名"。当前构建把配置模块并进了入口 chunk，且 chunk 导出统一被压缩成内部名
   （`export{hf as A,…}`），所以探针页里的 `cfg.runtimeConfig()` 必然取不到 —— 表现为
   "探针页没跑完"、B/C/D 全红。要恢复这三段，需要给配置模块单独切 chunk
   （vite.config.ts 的 build.rollupOptions.output.manualChunks），或把探针改成行为级观测。
   A 段的断言不受影响，仍然有效。

   怎么在不改生产代码的前提下观测配置值：
     构建产物里的配置模块是独立 chunk，从 dist/index.html 的模块图能反查出它的文件名。
     构造一个只做 `import * as cfg from './<那个 chunk>'` 的探针页，把
     runtimeConfig() / runtimeConfigLoaded / runtimeConfigError 序列化出来。
     这样读到的是**应用真正使用的那个模块实例**，不是复制的实现。

   用法：
     npm run build
     node tools/check-runtime-config.mjs            # 内部自带静态服务器，不需要先起 serve:dist
   ========================================================================== */
import { readFileSync, writeFileSync, existsSync, mkdirSync, rmSync, readdirSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createServer } from 'node:http'
import { join, extname, normalize } from 'node:path'
import { readFile, stat } from 'node:fs/promises'

const CHROME = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
].find((p) => existsSync(p))
if (!CHROME) {
  console.error('找不到 chrome.exe，无法验收')
  process.exit(1)
}

let pass = 0
let fail = 0
const check = (name, ok, extra = '') => {
  console.log(`  ${ok ? '✓' : '✗'} ${name}${extra ? '  — ' + extra : ''}`)
  if (ok) pass++
  else fail++
}

const PORT = 4399
const BASE = `http://127.0.0.1:${PORT}`

/* ---------------------------------------------------------------- 找配置 chunk */
/*
 * 从入口 chunk 里反查运期配置模块所在文件。
 * 依据：构建后代码保留了可辨识的字符串，例如 'config/config.json'（CONFIG_URL）。
 * 这个字符串只出现在配置模块里，所以命中它的那个 chunk 就是配置模块。
 */
function findConfigChunk() {
  const files = readdirSync('dist/assets').filter((f) => f.endsWith('.js'))
  const hits = files.filter((f) => readFileSync(join('dist/assets', f), 'utf8').includes('config/config.json'))
  return hits
}

const chunks = findConfigChunk()
console.log('############ A) 构建产物自带配置 ############')
check('dist/config/config.json 存在', existsSync('dist/config/config.json'))
check('dist/config/config.example.json 存在（给运维抄的模板）', existsSync('dist/config/config.example.json'))

const shippedRaw = readFileSync('dist/config/config.json', 'utf8')
let shipped = null
try {
  shipped = JSON.parse(shippedRaw)
  check('dist/config/config.json 是合法 JSON', true, JSON.stringify(shipped))
} catch (e) {
  check('dist/config/config.json 是合法 JSON', false, String(e))
}
check(
  '配置字段齐全（apiBase / dshProxyBase / dshUsernameParam / loginRememberKey / skipLogin / skipLoginUser）',
  shipped &&
    ['apiBase', 'dshProxyBase', 'dshUsernameParam', 'loginRememberKey', 'skipLogin', 'skipLoginUser'].every(
      (k) => k in shipped,
    ),
  shipped ? Object.keys(shipped).join(', ') : '',
)
check(
  '免登录开关默认关闭（skipLogin === false，与改动前行为一致）',
  shipped && shipped.skipLogin === false,
  shipped ? JSON.stringify(shipped.skipLogin) : '',
)
check('找到了运期配置模块所在的 chunk', chunks.length > 0, chunks.join(', '))

/* ---------------------------------------------------------------- 静态服务器 */
const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
}
let root = 'dist'
const server = createServer(async (req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0])
  if (p.includes('..')) return void res.writeHead(403).end('no')
  let file = join(root, normalize(p))
  try {
    const st = await stat(file)
    if (st.isDirectory()) file = join(file, 'index.html')
  } catch {
    file = join(root, 'index.html')
  }
  try {
    const body = await readFile(file)
    res.writeHead(200, {
      'content-type': MIME[extname(file)] || 'application/octet-stream',
      'cache-control': 'no-store',
    })
    res.end(body)
  } catch {
    res.writeHead(404).end('404')
  }
})
await new Promise((r) => server.listen(PORT, '127.0.0.1', r))
console.log(`\n（临时静态服务器 http://127.0.0.1:${PORT} ）`)

/* ---------------------------------------------------------------- 探针页 */
const entry = readFileSync('dist/index.html', 'utf8').match(/src="([^"]+\.js)"/)[1]
const chunkUrl = './' + (chunks[0] ? 'assets/' + chunks[0] : entry.replace(/^\//, ''))

function writeProbe(name) {
  /* 探针要点：
     1) 先同步 import 配置 chunk 再写结果 —— 不能用 --virtual-time-budget 等异步，
        那个 flag 和模块加载一起用时 Chrome 会一直不退出（实测 ETIMEDOUT）。
     2) 用 **静态** URL（写死文件名，不带查询串）。带查询串的 URL 在这里会 404
        （静态服务器按路径找文件），是之前踩过的坑。 */
  const body = [
    '<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>cfg</title>',
    '</head><body><div id="app"></div><pre id="__probe">PENDING</pre>',
    '<script type="module">',
    `import * as cfg from '${chunkUrl}';`,
    'const out = {',
    '  loaded: cfg.runtimeConfigLoaded,',
    '  error: cfg.runtimeConfigError,',
    '  values: cfg.runtimeConfig(),',
    '  apiBase: cfg.apiBase(),',
    '  proxyBaseConfig: cfg.proxyBaseConfig(),',
    '  dshUsernameParam: cfg.dshUsernameParam(),',
    '  rememberKey: cfg.rememberKey(),',
    '};',
    'document.getElementById("__probe").textContent =',
    '  btoa(unescape(encodeURIComponent(JSON.stringify(out))));',
    '</script></body></html>',
  ].join('\n')
  writeFileSync(join('dist', name), body)
}

function runChrome(url) {
  const profile = join(process.env.TEMP || '.', `dsh-cfg-${Date.now()}-${Math.round(Math.random() * 1e6)}`)
  try {
    const dom = execFileSync(
      CHROME,
      [
        '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
        '--disable-extensions', '--disable-crashpad', '--no-sandbox',
        `--user-data-dir=${profile}`, '--window-size=1280,800',
        /* 不用 --virtual-time-budget：它会让模块加载中的 Chrome 不退出。
           --timeout 是"最多跑多久"，到点就 dump 当前 DOM。 */
        '--timeout=6000', '--dump-dom', url,
      ],
      { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, timeout: 120000, stdio: ['ignore', 'pipe', 'ignore'] },
    )
    const m = dom.match(/<pre id="__probe">([\s\S]*?)<\/pre>/)
    if (!m || m[1].trim() === 'PENDING') return null
    return JSON.parse(Buffer.from(m[1].trim(), 'base64').toString('utf8'))
  } finally {
    rmSync(profile, { recursive: true, force: true })
  }
}

/* ------------------------------------------------- B) 默认配置文件被真正读取 */
console.log('\n############ B) 应用启动时真的读到并用上了它 ############')
writeProbe('__cfgprobe.html')
const def = runChrome(`${BASE}/__cfgprobe.html`)
if (!def) {
  check('探针能读到运期配置模块', false, '探针页没跑完')
} else {
  check('探针能读到运期配置模块', true)
  check('runtimeConfigLoaded = true（config.json 被成功加载）', def.loaded === true, `loaded=${def.loaded}`)
  check('runtimeConfigError 为空', def.error === null, `error=${JSON.stringify(def.error)}`)
  check(
    '默认内容与 public/config/config.json 一致',
    JSON.stringify(def.values) === JSON.stringify(shipped),
    JSON.stringify(def.values),
  )
  check('apiBase() 与文件里的 apiBase 一致', def.apiBase === shipped.apiBase, `apiBase=${JSON.stringify(def.apiBase)}`)
  check(
    'proxyBaseConfig() 与文件里的 dshProxyBase 一致',
    def.proxyBaseConfig === shipped.dshProxyBase,
    `proxyBaseConfig=${JSON.stringify(def.proxyBaseConfig)}`,
  )
  check('dshUsernameParam() 生效', def.dshUsernameParam === shipped.dshUsernameParam, def.dshUsernameParam)
  check('rememberKey() 生效', def.rememberKey === shipped.loginRememberKey, def.rememberKey)
}

/* --------------------------------------- C) 替换文件（模拟 docker -v 挂载）后行为改变 */
console.log('\n############ C) 换掉 config.json（模拟 docker -v 挂载）后取值跟着变 ############')
const MOUNTED = {
  apiBase: 'http://172.16.235.50:8038',
  dshProxyBase: 'https://dsh.example.com',
  dshUsernameParam: 'u',
  loginRememberKey: 'aiPlatform.lastUser',
}
const backup = readFileSync('dist/config/config.json', 'utf8')
writeFileSync('dist/config/config.json', JSON.stringify(MOUNTED, null, 2))
try {
  const mounted = runChrome(`${BASE}/__cfgprobe.html`)
  if (!mounted) {
    check('挂载后探针能跑完', false)
  } else {
    check('挂载后探针能跑完', true)
    check('runtimeConfigLoaded 仍为 true', mounted.loaded === true)
    check(
      'apiBase() 已切换为挂载值',
      mounted.apiBase === MOUNTED.apiBase,
      `${JSON.stringify(mounted.apiBase)}（期望 ${MOUNTED.apiBase}）`,
    )
    check(
      'proxyBaseConfig() 已切换为挂载值',
      mounted.proxyBaseConfig === MOUNTED.dshProxyBase,
      `${JSON.stringify(mounted.proxyBaseConfig)}（期望 ${MOUNTED.dshProxyBase}）`,
    )
    check(
      'dshUsernameParam() 已切换为挂载值',
      mounted.dshUsernameParam === MOUNTED.dshUsernameParam,
      `${mounted.dshUsernameParam}（期望 ${MOUNTED.dshUsernameParam}）`,
    )
    check(
      '未覆盖的字段保持原值（部分覆盖也成立）',
      mounted.rememberKey === shipped.loginRememberKey,
      mounted.rememberKey,
    )
  }
} finally {
  /* 必须还原：dist 是构建产物，不能留着测试值 */
  writeFileSync('dist/config/config.json', backup)
}

/* --------------------------------- D) 坏配置不能把应用卡住（失败要能退回默认） */
console.log('\n############ D) 配置坏掉时不阻塞启动，退回默认值 ############')
writeFileSync('dist/config/config.json', '{ 这不是合法 JSON ')
try {
  const broken = runChrome(`${BASE}/__cfgprobe.html`)
  if (!broken) {
    check('坏 JSON 时探针仍能跑完（说明没白屏/没抛错卡死）', false)
  } else {
    check('坏 JSON 时探针仍能跑完（说明没白屏/没抛错卡死）', true)
    check('runtimeConfigLoaded = false', broken.loaded === false)
    check('runtimeConfigError 有说明原因', typeof broken.error === 'string' && broken.error.length > 0, broken.error)
    check(
      '退回内置默认值（apiBase 为空 = 同源相对路径）',
      broken.apiBase === '',
      `apiBase=${JSON.stringify(broken.apiBase)}`,
    )
  }
} finally {
  writeFileSync('dist/config/config.json', backup)
}
rmSync('dist/__cfgprobe.html', { force: true })

console.log(`\n================ 结果: ${pass} 通过 / ${fail} 失败 ================`)
server.close()
process.exit(fail ? 1 : 0)