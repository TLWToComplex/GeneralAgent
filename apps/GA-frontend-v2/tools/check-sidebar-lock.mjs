/* ============================================================================
   侧栏「开发中」置灰验收

   验四件事：
     ① 该灰的菜单项灰了、且根本不是链接（没有 href，不可 Tab 聚焦）
     ② 不该灰的菜单项原样（仍是 <a>、仍可点）
     ③ 真实点击置灰项：URL 不变、页面不切换
     ④ 直接敲 URL / 深链进入「开发中」页面：被守卫重定向回工作台
       —— 这一条是 #3 的关键：「不可点击进入对应的子页面」不能只靠 CSS

   用法: node tools/sidebar-lock-check.mjs <base> [CDP_PORT]

   注意：/console/* 已有登录守卫（未登录会弹回登录页），本脚本会先往 localStorage
   写一个假令牌把门打开 —— 它验的是侧栏置灰，不是鉴权。
   ========================================================================== */
const BASE = process.argv[2] || 'http://127.0.0.1:4175'
const CDP_PORT = Number(process.argv[3] || process.env.CDP_PORT || 9222)

class Cdp {
  constructor(ws) {
    this.ws = ws; this.id = 0; this.p = new Map()
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.p.has(m.id)) {
        const { resolve, reject } = this.p.get(m.id); this.p.delete(m.id)
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result)
      }
    })
  }
  send(method, params = {}) {
    const id = ++this.id
    this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => this.p.set(id, { resolve, reject }))
  }
}

const SIDEBAR = `(() => {
  const items = [...document.querySelectorAll('.side__nav .side__link')].map((el) => {
    const s = getComputedStyle(el);
    const isLink = el.tagName === 'A' && !!el.getAttribute('href');
    return {
      nav: el.getAttribute('data-nav'),
      tag: el.tagName,
      label: (el.textContent || '').trim(),
      isLink,
      href: el.getAttribute('href') || '',
      tabbable: el.tabIndex >= 0 && isLink,
      opacity: s.opacity,
      filter: s.filter,
      cursor: s.cursor,
      grayed: s.cursor === 'not-allowed' || (s.filter !== 'none' && s.filter.includes('grayscale')),
      ariaDisabled: el.getAttribute('aria-disabled'),
      title: el.getAttribute('title') || '',
      hasDevBadge: !!el.querySelector('.side__badge--dev'),
      hasGoldBadge: !!el.querySelector('.side__badge:not(.side__badge--dev)'),
    };
  });
  return JSON.stringify({ items, url: location.hash });
})()`

const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json()
const ws = new WebSocket(list.find((p) => p.type === 'page').webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const cdp = new Cdp(ws)
await cdp.send('Page.enable'); await cdp.send('Runtime.enable'); await cdp.send('Network.enable')
await cdp.send('Network.clearBrowserCache')
await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
await cdp.send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false })

const ev = async (expr) => (await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value
let bad = 0

const EXPECT_LOCKED = ['model', 'mirror', 'kb', 'authz']
const EXPECT_OPEN = ['workbench', 'toolplatform', 'gateway']

/* ----------------------------------------------------------------------------
   先给浏览器塞一个登录态。

   路由守卫（src/router/index.ts）在未登录时会把 /console/* 全部弹回登录页，
   本脚本验的是「侧栏置灰」而不是鉴权，所以这里直接写一份 localStorage 让它进得去：
   守卫只检查「令牌存在且 exp 未过期」，不验签名（验签是后端的事），
   因此这个假令牌足够。真正的登录链路由 tools/smoke-login-ui.mjs 覆盖。
   ---------------------------------------------------------------------------- */
const b64url = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const nowSec = Math.floor(Date.now() / 1000)
const stubToken =
  `${b64url({ alg: 'HS256', typ: 'JWT' })}.` +
  `${b64url({ username: 'sidebar-check', exp: nowSec + 3600, iat: nowSec })}.stub-signature`

await cdp.send('Page.navigate', { url: 'about:blank' })
await new Promise((r) => setTimeout(r, 400))
// 先落到同源页面才能写该源的 localStorage
await cdp.send('Page.navigate', { url: BASE + '/#/login' })
await new Promise((r) => setTimeout(r, 1500))
await ev(
  `window.localStorage.setItem('GA.token', ${JSON.stringify(stubToken)});` +
    `window.localStorage.setItem('GA.user', ${JSON.stringify(JSON.stringify({ username: 'sidebar-check', realname: '侧栏检查' }))});` +
    `'ok'`,
)

// 必须先回 about:blank 再进控制台：两个只有 hash 不同的地址属于同文档跳转，
// 不会重新执行 main.ts 的 auth.restore()，改完 localStorage 直接跳过去仍会被守卫弹回登录页。
await cdp.send('Page.navigate', { url: 'about:blank' })
await new Promise((r) => setTimeout(r, 400))
await cdp.send('Page.navigate', { url: BASE + '/#/console/workbench' })
await new Promise((r) => setTimeout(r, 2800))

console.log('=== ① 侧栏每一项的状态 ===')
const d = JSON.parse(await ev(SIDEBAR))
for (const it of d.items) {
  const shouldLock = EXPECT_LOCKED.includes(it.nav)
  const ok = shouldLock ? it.grayed && !it.isLink : !it.grayed && it.isLink
  if (!ok) bad++
  console.log(
    `  ${ok ? '✓' : '✗'} ${it.nav.padEnd(12)} <${it.tag}> ${it.isLink ? '可点链接' : '非链接  '}  ` +
      `opacity=${it.opacity} filter=${it.filter === 'none' ? 'none' : 'grayscale'} cursor=${it.cursor}` +
      `  ${it.hasDevBadge ? '「开发中」标' : it.hasGoldBadge ? '金色徽标' : '无标'}` +
      `${it.title ? `  title="${it.title}"` : ''}`,
  )
  if (shouldLock) {
    if (!it.ariaDisabled) { console.log(`      ✗ 缺少 aria-disabled，屏幕阅读器会当成普通文本`); bad++ }
    if (!it.hasDevBadge) { console.log(`      ✗ 缺少「开发中」小标`); bad++ }
    if (it.tabbable) { console.log(`      ✗ 竟然还能被 Tab 聚焦`); bad++ }
  }
}

console.log('\n=== ② 真实点击置灰的菜单项（应毫无反应）===')
for (const nav of EXPECT_LOCKED) {
  const before = await ev('location.hash')
  const box = JSON.parse(
    await ev(`(() => { const el = document.querySelector('.side__link[data-nav="${nav}"]'); const r = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }); })()`),
  )
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1 })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1 })
  await new Promise((r) => setTimeout(r, 600))
  const after = await ev('location.hash')
  const unchanged = before === after
  if (!unchanged) bad++
  console.log(`  ${unchanged ? '✓' : '✗'} 点「${nav}」: URL ${unchanged ? '没变' : `变成了 ${after}`}（点之前 ${before}）`)
}

console.log('\n=== ③ 未锁的菜单项必须照旧能点（对照组）===')
for (const nav of EXPECT_OPEN.filter((n) => n !== 'workbench')) {
  const box = JSON.parse(
    await ev(`(() => { const el = document.querySelector('.side__link[data-nav="${nav}"]'); const r = el.getBoundingClientRect();
      return JSON.stringify({ x: Math.round(r.left + r.width / 2), y: Math.round(r.top + r.height / 2) }); })()`),
  )
  await cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: box.x, y: box.y, button: 'left', clickCount: 1 })
  await cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: box.x, y: box.y, button: 'left', clickCount: 1 })
  await new Promise((r) => setTimeout(r, 900))
  const after = await ev('location.hash')
  const navigated = after.includes(`/${nav}`)
  if (!navigated) bad++
  console.log(`  ${navigated ? '✓' : '✗'} 点「${nav}」: 跳到 ${after}  ${navigated ? '（正常）' : '（没跳过去，异常）'}`)
}

console.log('\n=== ④ 直接敲 URL 进「开发中」页面（应被守卫弹回工作台）===')
for (const page of ['models', 'registry', 'kb', 'authz']) {
  await cdp.send('Page.navigate', { url: BASE + `/#/console/${page}` })
  await new Promise((r) => setTimeout(r, 1800))
  const hash = await ev('location.hash')
  const bodyPage = await ev('document.body.getAttribute("data-page")')
  const bounced = hash.includes('/console/workbench') && bodyPage === 'workbench'
  if (!bounced) bad++
  console.log(`  ${bounced ? '✓' : '✗'} 敲 /#/console/${page} → 停在 ${hash}（body data-page=${bodyPage}）`)
}

console.log('\n=== ⑤ 对照组：未锁页面的深链必须照旧能进 ===')
for (const page of ['toolplatform', 'gateway']) {
  await cdp.send('Page.navigate', { url: BASE + `/#/console/${page}` })
  await new Promise((r) => setTimeout(r, 1800))
  const bodyPage = await ev('document.body.getAttribute("data-page")')
  const ok = bodyPage === page
  if (!ok) bad++
  console.log(`  ${ok ? '✓' : '✗'} 敲 /#/console/${page} → body data-page=${bodyPage}`)
}

console.log(`\n${bad === 0 ? '侧栏置灰验收全部通过 ✓' : `有 ${bad} 项未通过 ✗`}`)
ws.close()