/* ============================================================================
   工具平台 tab 体检（不依赖 CDP）

   本机 Chrome 153 上，CDP 的 Page / Runtime 域（含 session 级）命令一律静默
   不回复，只有 Browser 域能通，所以浏览器内的断言改走 `--dump-dom`：
     1) 用 dist 里真实的 index.html 资源名生成一份探针页 dist/__tabprobe.html，
        它加载真正的应用、等 tab 渲染出来，把 getComputedStyle 的结果
        序列化成 base64 写进 <pre id="__probe">；
     2) Chrome --dump-dom 把渲染后的 DOM 打到 stdout，这里解出那段 base64。
   这样拿到的是**真实浏览器里的计算样式**，不是靠读 CSS 猜。

   用法: node tools/check-tool-tabs.mjs <BASE_URL>
   ========================================================================== */
import { readFileSync, writeFileSync, readdirSync, existsSync, unlinkSync } from 'node:fs'
import { execFileSync } from 'node:child_process'

const BASE = (process.argv[2] || 'http://localhost:4173').replace(/\/$/, '')
const DIST = 'dist'

/* ---------- 找到 Chrome ---------- */
const CHROME = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  `${process.env.LOCALAPPDATA}\\Google\\Chrome\\Application\\chrome.exe`,
].find((p) => existsSync(p))
if (!CHROME) { console.error('找不到 Chrome'); process.exit(1) }

/* ---------- 1) 生成探针页 ---------- */
const idx = readFileSync(`${DIST}/index.html`, 'utf8')
const entry = idx.match(/src="([^"]+\.js)"/)[1]
const cssLinks = [...idx.matchAll(/href="([^"]+\.css)"/g)].map((m) => `<link rel="stylesheet" href="${m[1]}">`).join('\n')

const PROBE_HTML = `<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>tabprobe</title>
${cssLinks}
<script>
/* 先塞一份本地开发用的登录态（与服务端无关，只为本机验证页面可达）。
   localStorage 必须在应用模块之前同步写，否则路由守卫会把我们送去 /login。 */
try {
  localStorage.setItem('GA.token', 'tabprobe-local-token');
  localStorage.setItem('GA.user', JSON.stringify({ name: '本地验证', role: 'admin', account: 'local' }));
  localStorage.setItem('aiPlatform.lastUser', 'local');
} catch (e) { window.__lsErr = String(e) }
</script>
<script type="module" crossorigin src="${entry}"></script>
</head><body>
<div id="app"></div>
<pre id="__probe">PENDING</pre>
<script>
/* 等应用把 tab 渲染出来（最多 12s），然后量计算样式 */
const t0 = Date.now();
const tick = () => {
  const tabs = [...document.querySelectorAll('.tabs__btn')];
  const done = tabs.length >= 3 || Date.now() - t0 > 12000;
  if (done) {
    const app = document.getElementById('app');
    const out = {
      ready: tabs.length >= 3,
      waited: Date.now() - t0,
      hash: location.hash,
      title: document.title,
      lsErr: window.__lsErr || null,
      bodyPage: document.body.getAttribute('data-page'),
      appChildren: app ? app.children.length : -1,
      appHtmlHead: app ? app.innerHTML.slice(0, 700) : null,
      hasLogin: !!document.querySelector('#login, .login, [data-page="login"]'),
      counts: {
        tabs__btn: document.querySelectorAll('.tabs__btn').length,
        locked: document.querySelectorAll('.tabs__btn.is-locked').length,
        kpi: document.querySelectorAll('.reg-kpis .kpi').length,
        fchip: document.querySelectorAll('.fchip').length,
        sideLink: document.querySelectorAll('.side__link').length,
        routerLink: document.querySelectorAll('a[href]').length,
      },
      activeLabel: (() => { const e = document.querySelector('.tabs__btn.is-on'); return e ? e.textContent.trim() : null })(),
      kpis: [...document.querySelectorAll('.reg-kpis .kpi')].map((c) => c.textContent.replace(/\\s+/g, ' ').trim()),
      filters: [...document.querySelectorAll('.fchip')].map((b) => b.textContent.replace(/\\s+/g, ' ').trim()),
      tabs: tabs.map((e) => {
        const cs = getComputedStyle(e);
        const dev = e.querySelector('.tabs__dev');
        const cnt = e.querySelector('em:not(.tabs__dev)');
        return {
          tag: e.tagName, label: e.textContent.replace(/\\s+/g, ' ').trim(),
          locked: e.classList.contains('is-locked'), active: e.classList.contains('is-on'),
          ariaDisabled: e.getAttribute('aria-disabled'), title: e.getAttribute('title'),
          role: e.getAttribute('role'), type: e.getAttribute('type'),
          opacity: cs.opacity, filter: cs.filter, cursor: cs.cursor, color: cs.color,
          tabIndex: e.tabIndex,
          dev: dev ? { text: dev.textContent.trim(), font: getComputedStyle(dev).fontFamily,
                       color: getComputedStyle(dev).color, bg: getComputedStyle(dev).backgroundColor,
                       radius: getComputedStyle(dev).borderRadius, h: Math.round(dev.getBoundingClientRect().height) } : null,
          count: cnt ? cnt.textContent.trim() : null,
          rect: (() => { const r = e.getBoundingClientRect()
            return { x: Math.round(r.left), w: Math.round(r.width), h: Math.round(r.height) } })(),
        };
      }),
    };
    document.getElementById('__probe').textContent = btoa(unescape(encodeURIComponent(JSON.stringify(out))));
    return;
  }
  setTimeout(tick, 150);
};
tick();
</script>
</body></html>`

writeFileSync(`${DIST}/__tabprobe.html`, PROBE_HTML)

/* ---------- 2) --dump-dom ---------- */
const sleep = (ms) => { const e = Date.now() + ms; while (Date.now() < e) { /* spin */ } }
const profile = `${process.env.TEMP}\\dsh-tabprobe-${Date.now()}`
let dom = ''
try {
  dom = execFileSync(CHROME, [
    '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
    '--disable-extensions', '--disable-crashpad', '--no-sandbox',
    `--user-data-dir=${profile}`,
    '--virtual-time-budget=6000',
    '--dump-dom',
    `${BASE}/__tabprobe.html#/console/toolplatform`,
  ], { encoding: 'utf8', maxBuffer: 64 * 1024 * 1024, timeout: 90000, stdio: ['ignore', 'pipe', 'ignore'] })
} finally {
  try { unlinkSync(`${DIST}/__tabprobe.html`) } catch {}
}

/* ---------- 3) 解析 ---------- */
const m = dom.match(/<pre id="__probe">([\s\S]*?)<\/pre>/)
if (!m) {
  console.log('✗ 没拿到探针输出。DOM 长度: ' + dom.length)
  console.log(dom.slice(0, 600))
  process.exit(1)
}
const raw = m[1].trim()
if (raw === 'PENDING') { console.log('✗ 探针没跑完（应用没渲染出 tab，可能是登录态把页面拦走了）'); process.exit(1) }
const R = JSON.parse(Buffer.from(raw, 'base64').toString('utf8'))
if (!R.ready) {
  console.log('✗ 应用没渲染出 3 个 tab。诊断：')
  console.log(`  hash=${R.hash}  data-page=${R.bodyPage}  appChildren=${R.appChildren}  命中登录页=${R.hasLogin}`)
  console.log(`  localStorage 写入错误=${R.lsErr}`)
  console.log(`  计数: ${JSON.stringify(R.counts)}`)
  console.log(`  #app 片段: ${(R.appHtmlHead || '').slice(0, 500)}`)
  process.exit(1)
}

/* ---------- 4) 断言 ---------- */
let pass = 0, fail = 0
const check = (name, ok, detail = '') => {
  console.log(`  ${ok ? '✓' : '✗'} ${name}${detail ? `  — ${detail}` : ''}`)
  ok ? pass++ : fail++
}

console.log(`\n================ 探针就绪 ================`)
console.log(`  等了 ${R.waited}ms  ·  hash=${R.hash}  ·  data-page=${R.bodyPage}  ·  激活=${R.activeLabel}`)
const [ai, mcp, sk] = R.tabs

console.log('\n================ 1) 顺序与默认落地 ================')
check('第一个 tab 是「AI 工具」', (R.tabs[0]?.label || '').startsWith('AI 工具'), R.tabs[0]?.label)
check('顺序 = AI 工具 / MCP 服务 / Skill 工具',
  R.tabs.length === 3 && R.tabs[0].label.startsWith('AI 工具') && R.tabs[1].label.startsWith('MCP 服务') && R.tabs[2].label.startsWith('Skill 工具'),
  R.tabs.map((t) => t.label).join(' | '))
check('默认激活的是 AI 工具', (R.activeLabel || '').startsWith('AI 工具'), R.activeLabel)
check('AI 工具是 <BUTTON> 且 role=tab', ai.tag === 'BUTTON' && ai.role === 'tab', `tag=${ai.tag} role=${ai.role}`)

console.log('\n================ 2) MCP / Skill 置灰不可点 ================')
check('MCP 服务渲染成 <SPAN>（不是 button/a）', mcp.tag === 'SPAN', `tag=${mcp.tag}`)
check('Skill 工具渲染成 <SPAN>', sk.tag === 'SPAN', `tag=${sk.tag}`)
check('MCP 无 role=tab（不冒充 tab）', mcp.role === null, `role=${mcp.role}`)
check('MCP 带 aria-disabled="true"', mcp.ariaDisabled === 'true', `aria-disabled=${mcp.ariaDisabled}`)
check('Skill 带 aria-disabled="true"', sk.ariaDisabled === 'true', `aria-disabled=${sk.ariaDisabled}`)
check('MCP 有 title 说明原因', !!mcp.title, mcp.title)
check('Skill 有 title 说明原因', !!sk.title, sk.title)
check('MCP 不可 Tab 聚焦（tabIndex<0）', mcp.tabIndex < 0, `tabIndex=${mcp.tabIndex}`)
check('Skill 不可 Tab 聚焦', sk.tabIndex < 0, `tabIndex=${sk.tabIndex}`)
check('AI 工具可 Tab 聚焦', ai.tabIndex >= 0, `tabIndex=${ai.tabIndex}`)

console.log('\n================ 3) 置灰视觉（浏览器计算样式）================')
const grayOk = (d) => parseFloat(d.opacity) < 0.9 && /grayscale/.test(d.filter) && d.cursor === 'not-allowed'
check('MCP 生效: opacity<0.9 + grayscale + cursor:not-allowed', grayOk(mcp),
  `opacity=${mcp.opacity} filter=${mcp.filter} cursor=${mcp.cursor}`)
check('Skill 生效: opacity<0.9 + grayscale + cursor:not-allowed', grayOk(sk),
  `opacity=${sk.opacity} filter=${sk.filter} cursor=${sk.cursor}`)
check('AI 工具未被置灰', parseFloat(ai.opacity) === 1 && !/grayscale/.test(ai.filter),
  `opacity=${ai.opacity} filter=${ai.filter}`)
check('置灰后文字色更浅（--ink-4 系）', mcp.color !== ai.color, `mcp=${mcp.color} ai=${ai.color}`)
check('「开发中」小标存在', mcp.dev?.text === '开发中' && sk.dev?.text === '开发中',
  `${mcp.dev?.text} / ${sk.dev?.text}`)
check('小标用回无衬线字体（压过 .tabs__btn em 的等宽）',
  !!mcp.dev && !/mono|Menlo|Consolas/i.test(mcp.dev.font), mcp.dev?.font)
check('小标是灰底胶囊（不是金色徽标）',
  !!mcp.dev && /rgba?\(23,\s*33,\s*54/.test(mcp.dev.bg), `bg=${mcp.dev?.bg} radius=${mcp.dev?.radius}`)
check('置灰项不显示 tab 计数', mcp.count === null && sk.count === null, `mcp=${mcp.count} skill=${sk.count}`)
check('AI 工具仍显示计数', ai.count !== null && ai.count !== '', `count=${ai.count}`)

console.log('\n================ 4) 默认内容确实是 AI 工具 ================')
check('KPI 是 AI 口径（可领取文件 / 装机步骤 / 累计下发 / 内网模型）',
  R.kpis.some((k) => k.includes('可领取文件')) && R.kpis.some((k) => k.includes('装机步骤')) &&
  R.kpis.some((k) => k.includes('累计下发')) && R.kpis.some((k) => k.includes('内网模型')),
  R.kpis.join(' | '))
check('筛选条是 AI 口径（桌面端 / 终端 / IDE）',
  R.filters.some((f) => f.includes('桌面端')) && R.filters.some((f) => f.includes('IDE')),
  R.filters.join(' / '))
check('没有被登录页拦走（data-page 是 toolplatform）', R.bodyPage === 'toolplatform', `data-page=${R.bodyPage}`)

console.log('\n================ 5) 布局未被破坏 ================')
check('三个 tab 都有实体尺寸（没塌掉）', R.tabs.every((t) => t.rect.w > 40 && t.rect.h > 18),
  R.tabs.map((t) => `${t.label}:${t.rect.w}x${t.rect.h}`).join(' '))
check('AI 工具在最左（x 最小）',
  R.tabs[0].rect.x <= R.tabs[1].rect.x && R.tabs[0].rect.x <= R.tabs[2].rect.x,
  R.tabs.map((t) => `${t.label.slice(0, 4)}@${t.rect.x}`).join(' '))

console.log(`\n================ 结果: ${pass} 通过 / ${fail} 失败 ================`)
process.exit(fail ? 1 : 0)