/* ============================================================================
   指标条断点体检：在真实外壳（侧栏 + 页面容器）里渲染三个 tab 的指标条，
   扫描一批视口宽度，报告：
     · 指标条是否被挤到标题下一行（order:3 → stripTop > titleTop）
     · 卡片宽度序列是否参差（窄屏 flex:0 1 auto 按内容定宽）
     · 单位 .kpi__sub 是否被隐藏
     · 说明 .kpi__delta 是否被裁（需要宽度 > 可用宽度）
   用法: node tools/check-kpi-breakpoints.mjs <CDP_PORT>
   ========================================================================== */
import { register } from 'node:module'
import { readFileSync, readdirSync } from 'node:fs'

register('./vue-loader.mjs', import.meta.url)
const { createSSRApp } = await import('vue')
const { renderToString } = await import('vue/server-renderer')
const { createPinia } = await import('pinia')

const CDP_PORT = Number(process.argv[2] || 9222)
const { useToolsStore } = await import('../src/stores/tools.ts')
const ToolView = (await import('../src/views/tools/ToolPlatformView.vue')).default

const css = readFileSync(
  'dist/assets/' + readdirSync('dist/assets').find((f) => f.startsWith('console-') && f.endsWith('.css')),
  'utf8',
)

async function ssrWith(tab) {
  const app = createSSRApp(ToolView)
  app.use(createPinia())
  app.runWithContext(() => useToolsStore().setTab(tab))
  return renderToString(app)
}
function kpiSection(html) {
  const open = html.indexOf('<div class="reg-kpis kpis">')
  const start = html.indexOf('>', open) + 1
  let depth = 1
  const re = /<div\b|<\/div>/g
  re.lastIndex = start
  let m
  while ((m = re.exec(html))) {
    depth += m[0] === '</div>' ? -1 : 1
    if (depth === 0) return html.slice(start, m.index)
  }
  return null
}
function actionBtn(html) {
  const m = html.match(/<button class="reg__sync"[\s\S]*?<\/button>/)
  return m ? m[0] : ''
}
const sec = {}, act = {}
for (const tab of ['mcp', 'ai']) {
  const h = await ssrWith(tab)
  sec[tab] = kpiSection(h); act[tab] = actionBtn(h)
}

const iconSrc = readFileSync('src/components/IconDefs.vue', 'utf8')
const sprite = `<svg style="display:none">${[...iconSrc.matchAll(/<symbol\b[\s\S]*?<\/symbol>/g)].map((m) => m[0]).join('')}</svg>`

class Cdp {
  constructor(ws) { this.ws = ws; this.id = 0; this.p = new Map()
    ws.addEventListener('message', (e) => { const m = JSON.parse(e.data)
      if (m.id && this.p.has(m.id)) { const { resolve, reject } = this.p.get(m.id); this.p.delete(m.id)
        m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result) } }) }
  send(method, params = {}) { const id = ++this.id; this.ws.send(JSON.stringify({ id, method, params }))
    return new Promise((resolve, reject) => this.p.set(id, { resolve, reject })) }
}
const list = await (await fetch(`http://localhost:${CDP_PORT}/json/list`)).json()
const ws = new WebSocket(list.find((p) => p.type === 'page').webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const cdp = new Cdp(ws)
await cdp.send('Page.enable'); await cdp.send('Runtime.enable')
const ev = async (e) => (await cdp.send('Runtime.evaluate', { expression: e, returnByValue: true })).result.value

const PROBE = `(() => {
  const st = document.querySelector('.reg-kpis');
  const bar = document.querySelector('.reg__bar');
  const title = document.querySelector('.reg__title');
  const r = (e) => { if (!e) return null; const q = e.getBoundingClientRect()
    return { t: Math.round(q.top), l: Math.round(q.left), w: Math.round(q.width), h: Math.round(q.height) } }
  const want = (e) => { if (!e) return 0; const o = e.style.width; e.style.width = 'max-content'
    const v = Math.round(e.getBoundingClientRect().width); e.style.width = o; return v }
  return JSON.stringify({
    bar: r(bar), title: r(title), strip: r(st),
    cards: [...st.querySelectorAll('.kpi')].map((c) => {
      const num = c.querySelector('.kpi__num'), del = c.querySelector('.kpi__delta'), sub = c.querySelector('.kpi__sub')
      const cr = c.getBoundingClientRect()
      return { w: Math.round(cr.width), h: Math.round(cr.height), left: Math.round(cr.left),
        subDisplay: sub ? getComputedStyle(sub).display : null,
        delNeed: want(del), delHave: Math.round(del.getBoundingClientRect().width),
        numNeed: want(num), numHave: Math.round(num.getBoundingClientRect().width) }
    }),
  })
})()`

function page(tab, width) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style>
<style>
html,body{margin:0;padding:0}
.shell{display:flex;min-height:100vh}
.side{flex:none;width:216px;background:#101a2e}
.main{flex:1 1 auto;min-width:0;padding:18px 20px}
.reg__bar{padding:0}
</style></head>
<body data-page="toolplatform">${sprite}
<div class="shell"><aside class="side"></aside><main class="main">
<section><div class="reg__bar">
<div class="reg__title"><h2>工具平台 <em>Tools</em></h2><p>统一管理 MCP 服务与 Skill 工具</p></div>
<div class="reg-kpis kpis">${sec[tab]}</div>
${act[tab]}
</div></section></main></div></body></html>`
}

const WIDTHS = [1600, 1500, 1440, 1380, 1320, 1260, 1200, 1180, 1100, 1024, 980]
console.log('外壳：侧栏 216px + 主区 padding 20px；指标条随视口变化\n')
for (const vw of WIDTHS) {
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: vw, height: 900, deviceScaleFactor: 1, mobile: false })
  const rows = []
  for (const tab of ['mcp', 'ai']) {
    await cdp.send('Page.navigate', { url: 'data:text/html;charset=utf-8,' + encodeURIComponent(page(tab, vw)) })
    await new Promise((r) => setTimeout(r, 380))
    const g = JSON.parse(await ev(PROBE))
    const ws2 = g.cards.map((c) => c.w)
    const ratio = Math.max(...ws2) / Math.max(1, Math.min(...ws2))
    const clipped = g.cards.map((c, i) => (c.delNeed > c.delHave + 1 ? `${i}(${c.delNeed}>${c.delHave})` : null)).filter(Boolean)
    const wrapped = g.strip.t > g.title.t + 8
    rows.push({ tab, ws2, ratio, clipped, wrapped, subHidden: g.cards[0].subDisplay === 'none', strip: g.strip })
  }
  console.log(`\n################ 视口 ${vw}px ################`)
  for (const r of rows) {
    console.log(`  ${r.tab.padEnd(4)} 条宽=${r.strip.w} 条top=${r.strip.t} ` +
      `${r.wrapped ? '⚠指标条已换到标题下方' : '✓与标题同行'} ` +
      `${r.subHidden ? '⚠单位已隐藏' : '单位可见'}`)
    console.log(`        卡宽 ${r.ws2.join(',')}  最大/最小=${r.ratio.toFixed(2)}${r.ratio > 1.35 ? ' ⚠参差' : ''}` +
      `${r.clipped.length ? `  ⚠说明被裁: ${r.clipped.join(' ')}` : ''}`)
  }
}
ws.close()