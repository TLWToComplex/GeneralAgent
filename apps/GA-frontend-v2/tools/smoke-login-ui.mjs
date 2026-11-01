/* ============================================================================
   登录链路 UI 冒烟（真实浏览器 + CDP）

   前置条件（与 tools/check-sidebar-lock.mjs 相同）：
     1. 前端已起来：npm run dev（默认 http://localhost:5173）
     2. 有一个带调试端口的 Chrome：
        chrome.exe --remote-debugging-port=9222 --user-data-dir=<临时目录> about:blank

   用法:
     node tools/smoke-login-ui.mjs                                  # 默认 BASE
     node tools/smoke-login-ui.mjs http://localhost:5173
     node tools/smoke-login-ui.mjs http://localhost:5173 --real      # 打真后端
     node tools/smoke-login-ui.mjs http://localhost:5173 --shot tools/__shots__/login.png

   两种模式：
     · 默认（拦截模式）：CDP 拦下 GET /captcha 与 POST /aiUser/login，用固定响应驱动页面。
       好处是**不依赖后端**：验证的是前端自身的接线（取验证码 → 提交 → 错误落位 →
       换验证码 → 成功落地登录态 → 跳控制台 → 退出 → 守卫弹回 → 新建会话开新标签页），
       可在 CI / 无后端时跑。
       —— 校验用的验证码答案由拦截响应直接给定，因此不需要后端配合。
     · --real：不拦截，真实调用后端。此时只能验"页面渲染 + 错误分支"：真后端的验证码
       是随机的，脚本读不到答案，无法完成成功登录（成功路径由拦截模式覆盖）。
       需要后端在 BASE 的同源代理后面（dev 见 vite.config.ts 的 server.proxy）。

   关于「新建会话」（⑦ 段）：它只验前端拼出来的 URL（`http://<host>/?username=<用户>`）
   与"确实开了新标签页"，**不验 proxy 侧**。代理自己的行为由 proxy/tools/smoke.mjs 覆盖。
   断言不写死端口：只要求"同一台主机 + 没误用前端自己的端口 + 参数正确"；若本地在
   .env.local 里把 VITE_DSH_PROXY_BASE 指到了别的端口（如 http://localhost:8080），
   可以用 EXPECT_PROXY_BASE=http://localhost:8080 额外做一次精确断言。

   关于「免登录开关」（⑧ 段）：验 config.json 的 `skipLogin=true` 时"不弹登录页、直接以
   配置里的用户名进控制台、不发令牌、顶栏不渲染退出按钮"，开关关闭时"未登录仍被守卫弹回登录页"
   （默认值回归），以及**手写容错**（"true" / 1 / "off" / 乱写一律按行为判定，写错绝不能意外打开）
   与用户名去空白 / 缺省落 guest。配置文件由 CDP **顶替响应**（不改仓库里那份），所以这些状态
   都能在没有后端时验完；同时会读一次站点上真实的 config.json，断言开关字段存在且默认 false。
   对静态构建产物（`node tools/serve-dist.mjs 4175`）同样适用。

   退出码：0 全部通过；1 有失败项（便于接进流水线）。
   ========================================================================== */
import { Buffer } from 'node:buffer'

const args = process.argv.slice(2)
const REAL = args.includes('--real')
const BASE = args.find((a) => a.startsWith('http')) || 'http://localhost:5173'
const CDP_PORT = Number(process.env.CDP_PORT || 9222)
/** --shot <路径>：把登录页截图存下来（人工看视觉回归用） */
const SHOT = args.includes('--shot') ? args[args.indexOf('--shot') + 1] : ''

/** 与后端 tools/dev_sqlite_server.py 的演示账号一致 */
const DEMO_USER = 'demo'
const DEMO_PASSWORD = 'Kp!3RzT7Vm'
const DEMO_REALNAME = '演示用户'

/* ---------------------------------------------------------------- CDP 封装 */
class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.pending = new Map()
    this.handlers = new Map()
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.pending.has(m.id)) {
        const { resolve, reject } = this.pending.get(m.id)
        this.pending.delete(m.id)
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result)
        return
      }
      if (m.method && this.handlers.has(m.method)) {
        for (const fn of this.handlers.get(m.method)) fn(m.params)
      }
    })
  }
  send(method, params = {}) {
    const id = ++this.id
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => this.pending.set(id, { resolve, reject }))
  }
  on(method, fn) {
    if (!this.handlers.has(method)) this.handlers.set(method, [])
    this.handlers.get(method).push(fn)
  }
}

/* ---------------------------------------------------------------- 断言与工具 */
let passed = 0
let failed = 0
function check(name, ok, extra = '') {
  if (ok) {
    passed++
    console.log(`  ✓ ${name}`)
  } else {
    failed++
    console.log(`  ✗ ${name}${extra ? `   → ${extra}` : ''}`)
  }
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/* 拦截模式用的固定响应 ------------------------------------------------------ */
let captchaSeq = 0
let loginError = null // 非空时让下一次登录返回该错误（验证码错误分支）
/** 非空时用它顶替 config/config.json 的响应（⑧ 免登录开关用；仓库里那份不动） */
let stubConfig = null

/** 1×1 透明 PNG，够 <img> 加载即可 */
const PIXEL_PNG =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg=='

/** 造一个"形如 JWT、exp 在未来"的令牌：守卫只看 exp，不验签（验签是后端的事） */
function cannedToken() {
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
  const header = b64({ alg: 'HS256', typ: 'JWT' })
  const payload = b64({
    username: DEMO_USER,
    identity: { username: DEMO_USER, user_id: 1 },
    exp: Math.floor(Date.now() / 1000) + 3600,
    iat: Math.floor(Date.now() / 1000),
    jti: 'ui-smoke',
  })
  return `${header}.${payload}.ui-smoke-signature`
}

function fulfill(cdp, requestId, status, body) {
  return cdp.send('Fetch.fulfillRequest', {
    requestId,
    responseCode: status,
    responseHeaders: [{ name: 'Content-Type', value: 'application/json; charset=utf-8' }],
    body: Buffer.from(JSON.stringify(body), 'utf8').toString('base64'),
  })
}

/* ---------------------------------------------------------------- 主流程 */
const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json()
const target = list.find((p) => p.type === 'page')
if (!target) {
  console.error(`未找到可用的页面目标。请先用 --remote-debugging-port=${CDP_PORT} 启动 Chrome。`)
  process.exit(1)
}
const ws = new WebSocket(target.webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const cdp = new Cdp(ws)
await cdp.send('Page.enable')
await cdp.send('Runtime.enable')
await cdp.send('Network.enable')
await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 1440,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
})

const ev = async (expr) =>
  (await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value

/** 给 v-model 绑定的输入框赋值（直接改 value 不会触发 Vue 的更新，必须派发 input 事件） */
const setValue = (selector, value) =>
  ev(`(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return 'NO_ELEMENT';
    el.value = ${JSON.stringify(value)};
    el.dispatchEvent(new Event('input', { bubbles: true }));
    return el.value;
  })()`)

/** 真实鼠标点击（走 Input 域，比 el.click() 更接近用户操作）
 *
 *  返回 '' 表示点成功；否则返回一句可读的原因。
 *  必须先确认「按钮在视口内、中心点上确实是它」——否则坐标会落到别的元素上，
 *  表现为"点了没反应"，最难查（本脚本第一次跑就踩到过：顶栏退出按钮被挤出视口）。
 */
async function clickSelector(selector) {
  const info = await ev(`(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return JSON.stringify({ error: '元素不存在' });
    el.scrollIntoView({ block: 'nearest', inline: 'nearest' });
    const r = el.getBoundingClientRect();
    const x = Math.round(r.left + r.width / 2);
    const y = Math.round(r.top + r.height / 2);
    const hit = document.elementFromPoint(x, y);
    return JSON.stringify({
      x, y, w: Math.round(r.width), h: Math.round(r.height),
      vw: window.innerWidth, vh: window.innerHeight, hash: location.hash,
      hitTag: hit ? hit.tagName : null,
      hitId: hit ? hit.id : null,
      hitCls: hit ? String(hit.className || '') : null,
      ours: !!(hit && (hit === el || el.contains(hit))),
    });
  })()`)
  if (!info) return `${selector}: 取不到元素信息`
  const d = JSON.parse(info)
  if (d.error) return `${selector}: ${d.error}`
  if (d.w === 0 || d.h === 0) return `${selector}: 尺寸为 0（不可见？）`
  if (!d.ours) {
    return (
      `${selector}: 中心点(${d.x},${d.y})命中的是 <${d.hitTag} id=${d.hitId} class="${d.hitCls}">` +
      `，不是目标；视口 ${d.vw}×${d.vh}，目标 ${d.w}×${d.h}`
    )
  }
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: d.x, y: d.y, button: 'left', clickCount: 1 })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: d.x, y: d.y, button: 'left', clickCount: 1 })
  return ''
}

/** 硬跳转：先 about:blank 再进目标，确保是整页加载（否则改 hash 不会重新跑 main.ts 的 restore） */
async function hardNavigate(url) {
  await cdp.send('Page.navigate', { url: 'about:blank' })
  await sleep(300)
  await cdp.send('Page.navigate', { url })
  await sleep(2000)
}

/** 轮询等待条件成立 */
async function waitFor(expr, timeoutMs = 8000, step = 200) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await ev(expr)) return true
    await sleep(step)
  }
  return false
}

console.log(`登录链路 UI 冒烟  BASE=${BASE}  模式=${REAL ? '--real（打真后端）' : '拦截（不依赖后端）'}`)

/* ---------------------------------------------------------- 0. 拦截装配 */
let captchaRequests = 0
let lastClickError = ''
async function click(selector) {
  lastClickError = await clickSelector(selector)
  return lastClickError === ''
}
if (!REAL) {
  cdp.on('Fetch.requestPaused', async (params) => {
    const url = params.request.url
    try {
      if (url.includes('/captcha')) {
        captchaRequests++
        await fulfill(cdp, params.requestId, 200, {
          code: 200,
          message: 'success',
          data: { captchaId: `ui-smoke-captcha-${captchaRequests}`, captchaImage: PIXEL_PNG },
        })
      } else if (url.includes('/aiUser/login')) {
        if (loginError) {
          const { status, message } = loginError
          loginError = null
          await fulfill(cdp, params.requestId, status, { error: message })
        } else {
          await fulfill(cdp, params.requestId, 200, {
            status: 'success',
            message: '登录成功',
            user: {
              id: 1,
              uuid: 'ui-smoke-uuid',
              username: DEMO_USER,
              realname: DEMO_REALNAME,
              email: 'demo@example.com',
              needUpdateMsg: false,
            },
            token: cannedToken(),
            passwordExpiredWarning: false,
          })
        }
      } else if (url.includes('config/config.json')) {
        /* ⑧ 免登录开关：stubConfig 非空才顶替；否则原样放行（①②…⑦ 走真实配置） */
        if (stubConfig) await fulfill(cdp, params.requestId, 200, stubConfig)
        else await cdp.send('Fetch.continueRequest', { requestId: params.requestId })
      }
    } catch (err) {
      console.log(`  ! 拦截处理失败: ${err.message}`)
    }
  })
  await cdp.send('Fetch.enable', {
    patterns: [
      { urlPattern: '*/captcha*', requestStage: 'Request' },
      { urlPattern: '*/aiUser/login*', requestStage: 'Request' },
      { urlPattern: '*/config/config.json*', requestStage: 'Request' },
    ],
  })
}

/* ---------------------------------------------------------- 1. 登录页渲染 */
try {
  /* 先清干净：本脚本可能接在上一次运行的会话后面跑，带令牌进 /#/login 会被
     guestOnly 守卫弹到控制台，于是整轮断言全部对不上。 */
  await hardNavigate(`${BASE}/`)
  await ev('window.localStorage.clear()')
  await hardNavigate(`${BASE}/#/login`)

  console.log('\n=== ① 登录页渲染与验证码 ===')
  check('停在登录页', (await ev('location.hash')) === '#/login', await ev('location.hash'))
  check('验证码字段存在（.field--captcha）', !!(await ev('!!document.querySelector(".field--captcha")')))
  check('验证码输入框存在（#captcha）', !!(await ev('!!document.querySelector("#captcha")')))
  const imgSrc = await ev('(document.querySelector("img.captcha")||{}).src || ""')
  check('验证码图片已加载', imgSrc.startsWith('data:image/') || imgSrc.includes('/captcha'), imgSrc.slice(0, 60))
  check('提交按钮存在', !!(await ev('!!document.querySelector("#submit")')))

  if (SHOT) {
    const shot = await cdp.send('Page.captureScreenshot', { format: 'png' })
    const { writeFileSync, mkdirSync } = await import('node:fs')
    const { dirname } = await import('node:path')
    mkdirSync(dirname(SHOT), { recursive: true })
    writeFileSync(SHOT, Buffer.from(shot.data, 'base64'))
    console.log(`  · 已截图: ${SHOT}`)
  }

  /* ---------------------------------------------------------- 1b. 布局断言
     截图只能靠人眼，这里把「验证码图片与输入框对齐、不重叠、不溢出」变成可断言
     的几何条件 —— 布局回归在流水线里也能拦住。 */
  console.log('\n=== ①b 验证码布局 ===')
  const geo = JSON.parse(
    await ev(`(() => {
      const rect = (el) => {
        const b = el.getBoundingClientRect();
        return { l: b.left, t: b.top, r: b.right, b: b.bottom, w: b.width, h: b.height };
      };
      const box = document.querySelector('.field--captcha .field__box');
      const img = document.querySelector('img.captcha') || document.querySelector('.captcha');
      return JSON.stringify({
        box: rect(box),
        img: rect(img),
        card: rect(document.querySelector('.card')),
        label: (document.querySelector('.field--captcha .field__k') || {}).textContent || '',
        placeholder: (document.querySelector('#captcha') || {}).placeholder || '',
        natural: [img.naturalWidth || 0, img.naturalHeight || 0],
        scrollW: document.documentElement.scrollWidth,
        innerW: window.innerWidth,
      });
    })()`),
  )
  const midY = (r) => (r.t + r.b) / 2
  check('标签为「图形验证码」', geo.label.trim() === '图形验证码', geo.label.trim())
  check('输入框与图片同一行（垂直中心对齐）', Math.abs(midY(geo.box) - midY(geo.img)) < 4, `${midY(geo.box)} vs ${midY(geo.img)}`)
  check('图片在输入框右侧且不重叠', geo.img.l >= geo.box.r - 1, `img.left=${geo.img.l} box.right=${geo.box.r}`)
  check('图片尺寸正常（>60×30）', geo.img.w > 60 && geo.img.h > 30, `${geo.img.w}×${geo.img.h}`)
  check('图片已真正解码', geo.natural[0] > 0 && geo.natural[1] > 0, geo.natural.join('×'))
  check('未溢出卡片右边界', geo.img.r <= geo.card.r + 1, `img.right=${geo.img.r} card.right=${geo.card.r}`)
  check('页面无横向滚动', geo.scrollW <= geo.innerW + 1, `scrollWidth=${geo.scrollW} innerWidth=${geo.innerW}`)

  /* ---------------------------------------------------------- 2. 失败分支 */
  console.log('\n=== ② 验证码错误：文案落在字段上 + 自动换验证码 ===')
  const srcBefore = imgSrc
  if (!REAL) loginError = { status: 401, message: '验证码错误' }

  await setValue('#username', DEMO_USER)
  await setValue('#password', DEMO_PASSWORD)
  await setValue('#captcha', 'ZZZZ')
  check('提交按钮可点（未被遮挡）', await click('#submit'), lastClickError)

  const gotFieldError = await waitFor('!!document.querySelector(".field--captcha.is-error")', 8000)
  check('验证码字段进入错误态', gotFieldError)
  const errText = await ev(
    '(document.querySelector(".field--captcha .field__err")||{}).textContent || ""',
  )
  check(
    `错误文案来自后端（"${errText.trim()}"）`,
    REAL ? errText.includes('验证码') : errText.trim() === '验证码错误',
    errText.trim(),
  )
  const srcAfter = await ev('(document.querySelector("img.captcha")||{}).src || ""')
  check('失败后自动换了验证码', srcAfter !== srcBefore || captchaRequests >= 2)
  check('失败时留在登录页（没误跳控制台）', (await ev('location.hash')) === '#/login', await ev('location.hash'))

  /* ---------------------------------------------------------- 3. 成功路径 */
  console.log('\n=== ③ 登录成功：落地登录态 → 跳控制台 ===')
  if (REAL) {
    console.log('  – 跳过：--real 模式下后端验证码随机，脚本读不到答案（成功路径见拦截模式）')
  } else {
    await setValue('#username', DEMO_USER)
    await setValue('#password', DEMO_PASSWORD)
    await setValue('#captcha', 'ABCD') // 答案无所谓：请求已被拦下，由固定响应作答
    check('提交按钮可点（未被遮挡）', await click('#submit'), lastClickError)

    const landed = await waitFor('location.hash.includes("/console")', 10000)
    check('跳转到控制台', landed, await ev('location.hash'))
    const token = await ev('window.localStorage.getItem("GA.token") || ""')
    check('localStorage 写入了令牌', token.length > 20)
    const storedUser = await ev('window.localStorage.getItem("GA.user") || ""')
    check('localStorage 写入了用户信息', storedUser.includes(DEMO_USER))
    check('控制台外壳已渲染（侧栏存在）', !!(await ev('!!document.querySelector(".side__nav")')))
    const chip = await ev('((document.querySelector("#userChip")||{}).textContent||"").trim()')
    check(`顶栏显示真实用户（"${chip}"）`, chip.includes(DEMO_REALNAME), chip)

    /* 刷新页面：登录态必须能从 localStorage 恢复（否则刷深链就被踢回登录页） */
    await hardNavigate(`${BASE}/#/console/workbench`)
    check('刷新后仍在控制台（登录态已恢复）', (await ev('location.hash')).includes('/console'), await ev('location.hash'))
    check('刷新后侧栏仍在', !!(await ev('!!document.querySelector(".side__nav")')))

    /* -------------------------------------------------------- 4. 退出登录 */
    console.log('\n=== ④ 退出登录：清登录态 → 回登录页 ===')
    check('退出按钮可点（未被遮挡）', await click('#logoutBtn'), lastClickError)
    const backToLogin = await waitFor('location.hash === "#/login"', 6000)
    check('回到登录页', backToLogin, await ev('location.hash'))
    check('令牌已清除', !(await ev('window.localStorage.getItem("GA.token")')))
  }

  /* ---------------------------------------------------------- 5. 路由守卫 */
  console.log('\n=== ⑤ 未登录深链控制台：被守卫弹回登录页 ===')
  await ev('window.localStorage.clear()')
  await hardNavigate(`${BASE}/#/console/workbench`)
  const bounced = await ev('location.hash')
  check('停在登录页', bounced === '#/login', bounced)
  check('控制台未渲染', !(await ev('!!document.querySelector(".side__nav")')))

  /* ---------------------------------------------------------- 6. 反例 */
  console.log('\n=== ⑥ 对照组：已登录深链控制台子页应当放行 ===')
  if (REAL) {
    console.log('  – 跳过：--real 模式无法建立会话')
  } else {
    await hardNavigate(`${BASE}/#/login`)
    await setValue('#username', DEMO_USER)
    await setValue('#password', DEMO_PASSWORD)
    await setValue('#captcha', 'ABCD')
    check('提交按钮可点（未被遮挡）', await click('#submit'), lastClickError)
    const ok = await waitFor('location.hash.includes("/console")', 10000)
    if (ok) {
      await hardNavigate(`${BASE}/#/console/gateway`)
      const hash = await ev('location.hash')
      check('已登录可进控制台子页', hash.includes('/console/gateway'), hash)
    } else {
      check('已登录可进控制台子页', false, '第二次登录未成功')
    }

    /* ------------------------------------------------ 7. 新建会话 → 进 dsh */
    console.log('\n=== ⑦ 新建会话：新标签页打开 dsh 控制台 ===')
    if (!(await ev('location.hash')).includes('/console/workbench')) {
      await hardNavigate(`${BASE}/#/console/workbench`)
    }
    check('原「新建会话」弹窗已移除', !(await ev('!!document.querySelector("#newModal")')))
    check('浮栏按钮带 data-act', !!(await ev('!!document.querySelector(".dock__btn[data-act=\\"new\\"]")')))

    // 先换掉 window.open 记录调用（不依赖真的弹窗，断言的是前端拼出来的地址）
    await ev(`(() => {
      window.__opened = []; window.__realOpen = window.open;
      window.open = (u, t, f) => { window.__opened.push({ u, t, f: f || '' }); return { opener: null }; };
      return 'ok';
    })()`)
    check('「新建会话」按钮可点', await click('.dock__btn[data-act="new"]'), lastClickError)
    await sleep(400)
    const opened = JSON.parse(await ev('JSON.stringify(window.__opened || [])'))
    const u = opened[0]?.u || ''
    let pu = null
    try { pu = new URL(u) } catch { /* 地址不合法，下面的断言会报出来 */ }
    const pageHost = new URL(BASE).hostname
    check(
      `打开的是同一台机器上的代理地址（${u || '没调用 window.open'}）`,
      !!pu && pu.pathname === '/' && pu.hostname === pageHost && pu.search === `?username=${DEMO_USER}`,
      u,
    )
    check('没误用前端自己的端口', !!pu && pu.port !== new URL(BASE).port, u)
    if (process.env.EXPECT_PROXY_BASE) {
      // 配了 VITE_DSH_PROXY_BASE 时给出精确断言
      check(`与 EXPECT_PROXY_BASE 一致（${process.env.EXPECT_PROXY_BASE}）`,
        u.startsWith(`${process.env.EXPECT_PROXY_BASE.replace(/\/+$/, '')}/?username=${DEMO_USER}`), u)
    }
    check('新标签页方式打开（_blank）', opened[0]?.t === '_blank', opened[0]?.t)
    const toast = await ev('(document.querySelector("#toast")||document.body).textContent || ""')
    check('给出了轻提示', toast.includes('dsh 控制台'), toast.slice(0, 60))
    check('轻提示里带了地址（万一被拦时可手动打开）', toast.includes(`username=${DEMO_USER}`), toast.slice(0, 120))

    // 再恢复真实 window.open，确认真能开出新标签页（headless 下也会建 target）。
    // 注意不能按"URL 里含 username="去认：proxy 会 302 到去掉该参数的干净地址，
    // 所以这里按「新出现的 page 目标 + 与入口同源」判定 —— 后者恰好也验证了 302 没跳去别处。
    await ev('window.open = window.__realOpen')
    const beforeIds = new Set((await cdp.send('Target.getTargets')).targetInfos
      .filter((t) => t.type === 'page').map((t) => t.targetId))
    await click('.dock__btn[data-act="new"]')
    let popup = null
    let seen = []
    for (let i = 0; i < 15 && !popup; i++) {
      await sleep(200)
      seen = (await cdp.send('Target.getTargets')).targetInfos
        .filter((t) => t.type === 'page' && !beforeIds.has(t.targetId))
      popup = seen[0] || null
    }
    check('真的开出了新标签页', !!popup, seen.length ? JSON.stringify(seen.map((t) => t.url)) : '没等到新目标页')
    if (popup && pu) {
      let sameOrigin = false
      try { sameOrigin = new URL(popup.url).origin === pu.origin } catch { sameOrigin = false }
      check('新标签页最终停在代理同源（302 没跳去别处）', sameOrigin, popup.url)
    }
    if (popup) await cdp.send('Target.closeTarget', { targetId: popup.targetId }).catch(() => {})
  }

  /* ---------------------------------------------------------- 8. 免登录开关
     验 config.json 的 skipLogin（字段默认 false）。配置由上面的 Fetch 拦截顶替，
     仓库里那份 config.json 一个字节都不改 —— 两种状态都能在无后端时验完。 */
  console.log('\n=== ⑧ 免登录开关：config.json 的 skipLogin ===')
  const baseConfig = {
    apiBase: '',
    dshProxyBase: '',
    dshUsernameParam: 'username',
    loginRememberKey: 'aiPlatform.lastUser',
    skipLogin: false,
    skipLoginUser: '',
  }
  /* 站点上那份真实配置：开关字段必须存在且默认关闭（默认关 = 与改动前行为一致） */
  const shipped = await (await fetch(`${BASE}/config/config.json?t=${Date.now()}`)).json()
  check('随站点下发的 config.json 带 skipLogin 且默认 false', shipped.skipLogin === false, JSON.stringify(shipped))

  stubConfig = { ...baseConfig, skipLogin: true, skipLoginUser: '免登录演示' }
  await ev('window.localStorage.clear()')
  await hardNavigate(`${BASE}/#/console/toolplatform`)
  check('免登录：没登录也能直接进控制台（没被弹回登录页）', (await ev('location.hash')).includes('/console'), await ev('location.hash'))
  check('免登录：控制台外壳已渲染', !!(await ev('!!document.querySelector(".side__nav")')))
  const chip2 = await ev('((document.querySelector("#userChip")||{}).textContent||"").trim()')
  check(`免登录：顶栏显示配置里的用户名（"${chip2}"）`, chip2.includes('免登录演示'), chip2)
  const chipT2 = (await ev('((document.querySelector("#userChip")||{}).getAttribute("title"))||""')) || ''
  check('免登录：身份卡 title 说明身份来自 skipLogin 开关', chipT2.includes('skipLogin'), chipT2)
  check('免登录：不往 localStorage 写假令牌', !(await ev('window.localStorage.getItem("GA.token")')))
  check('免登录：顶栏不渲染「退出」按钮（没有会话可退）', !(await ev('!!document.querySelector("#logoutBtn")')))

  await hardNavigate(`${BASE}/#/login`)
  check('免登录：直接敲 /#/login 也被弹回控制台', (await ev('location.hash')).includes('/console'), await ev('location.hash'))

  /* 关掉开关 = 默认值：原有「未登录深链进不去」的行为必须一模一样 */
  stubConfig = { ...baseConfig }
  await ev('window.localStorage.clear()')
  await hardNavigate(`${BASE}/#/console/workbench`)
  check('开关关闭：未登录深链仍被弹回登录页（原行为不变）', (await ev('location.hash')) === '#/login', await ev('location.hash'))

  /* 容错解析：手写 config.json 的常见写法，一律用"页面到底进不进控制台"来判 */
  for (const [raw, wantConsole, label] of [
    ['true', true, '真布尔 true'],
    ['"true"', true, '字符串 "true" 也认（JSON 里手写忘了去引号）'],
    ['1', true, '数字 1 也认'],
    ['"off"', false, '字符串 "off" 认作关闭'],
    ['"随便写的"', false, '认不出来 → 默认 false（绝不能意外打开）'],
  ]) {
    stubConfig = { ...baseConfig, skipLogin: JSON.parse(raw) }
    await ev('window.localStorage.clear()')
    await hardNavigate(`${BASE}/#/console/workbench`)
    const h = await ev('location.hash')
    check(
      `skipLogin=${raw} → ${wantConsole ? '免登录直接进控制台' : '被守卫弹回登录页'}（${label}）`,
      h.includes('/console') === wantConsole,
      h,
    )
  }

  /* 用户名：两端空白要去掉；没配要落 guest（顶栏不能出现空名字） */
  stubConfig = { ...baseConfig, skipLogin: true, skipLoginUser: '  演示账号  ' }
  await hardNavigate(`${BASE}/#/console/workbench`)
  const chip3 = await ev('((document.querySelector("#userChip")||{}).textContent||"").trim()')
  check('skipLoginUser 两端空白被去掉', chip3.includes('演示账号') && !chip3.includes(' 演示'), chip3)

  stubConfig = { ...baseConfig, skipLogin: true }
  await hardNavigate(`${BASE}/#/console/workbench`)
  const chip4 = await ev('((document.querySelector("#userChip")||{}).textContent||"").trim()')
  check('skipLoginUser 缺省落 guest（不留空名字）', chip4.includes('guest'), chip4)

  /* 真令牌优先：开关开着 + 本地已有有效令牌时，仍用真身份（不降级成免登录名，退出照常） */
  stubConfig = { ...baseConfig, skipLogin: true, skipLoginUser: '免登录演示' }
  await ev(
    `window.localStorage.setItem('GA.token', ${JSON.stringify(cannedToken())});` +
      `window.localStorage.setItem('GA.user', ${JSON.stringify(
        JSON.stringify({ username: DEMO_USER, realname: DEMO_REALNAME }),
      )});'ok'`,
  )
  await hardNavigate(`${BASE}/#/console/workbench`)
  const chipReal = await ev('((document.querySelector("#userChip")||{}).textContent||"").trim()')
  check('免登录开着但已有真令牌：仍用真身份（不被降级成免登录名）', chipReal.includes(DEMO_REALNAME), chipReal)
  check('免登录开着但已有真令牌：顶栏「退出」照常在', !!(await ev('!!document.querySelector("#logoutBtn")')))

  await ev('window.localStorage.clear()')
  stubConfig = null
} finally {
  if (!REAL) await cdp.send('Fetch.disable').catch(() => {})
  ws.close()
}

console.log(`\n结果: PASS=${passed} FAIL=${failed}`)
console.log(failed === 0 ? '登录链路 UI 冒烟全部通过 ✓' : `有 ${failed} 项未通过 ✗`)
process.exit(failed === 0 ? 0 : 1)