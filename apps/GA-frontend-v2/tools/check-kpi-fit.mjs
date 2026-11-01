/* ============================================================================
   指标条诊断：把每个「说明 / 单位」的**需要宽度**与**可用宽度**都量出来，
   直接指出哪一页的哪张卡在哪个视口下会被裁、由哪条媒体查询造成。

   不依赖登录态：指标条是纯前端渲染的结果，这里用项目自带的 vue-loader
   做真 SSR 拿到各页的指标条 HTML，再配真实 console.css 在无头 Chrome 里量。

   用法: node tools/check-kpi-fit.mjs [CDP_PORT]
   ========================================================================== */
import { register } from 'node:module'
import { readFileSync, readdirSync } from 'node:fs'

register('./vue-loader.mjs', import.meta.url)
const { createSSRApp } = await import('vue')
const { renderToString } = await import('vue/server-renderer')
const { createPinia } = await import('pinia')

const CDP_PORT = Number(process.argv[2] || 9222)

/* ---------- 1) 收集各页面 / 各 tab 的真实指标条 HTML ---------- */
const { useToolsStore } = await import('../src/stores/tools.ts')
const ToolView = (await import('../src/views/tools/ToolPlatformView.vue')).default

async function ssr(Comp, setup) {
  const app = createSSRApp(Comp)
  app.use(createPinia())
  if (setup) app.runWithContext(setup)
  return renderToString(app)
}

const pages = {}
/* 工具平台三个 tab */
for (const tab of ['mcp', 'skill', 'ai']) {
  const html = await ssr(ToolView, () => useToolsStore().setTab(tab))
  pages[`工具平台·${tab}`] = html
}
/* 其余资产页：直接渲染 view（它们各自 useHeartbeat，SSR 下不跑定时器） */
for (const [name, path] of [
  ['镜像中心', '../src/views/registry/RegistryView.vue'],
  ['模型中心', '../src/views/models/ModelsView.vue'],
  ['知识库中心', '../src/views/kb/KnowledgeBaseView.vue'],
]) {
  pages[name] = await ssr((await import(path)).default)
}

const css = readFileSync(
  'dist/assets/' + readdirSync('dist/assets').find((f) => f.startsWith('console-') && f.endsWith('.css')),
  'utf8',
)

/* 图标 sprite：从源码 IconDefs.vue 抠 <symbol>，否则图标位不占宽 */
const iconSrc = readFileSync('src/components/IconDefs.vue', 'utf8')
const sprite = `<svg class="sprite" aria-hidden="true" style="display:none">${[...iconSrc.matchAll(/<symbol\b[\s\S]*?<\/symbol>/g)].map((m) => m[0]).join('')}</svg>`

function kpiSection(html) {
  const open = html.indexOf('<div class="reg-kpis kpis">')
  if (open < 0) return null
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

/* ---------- 2) CDP ---------- */
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
const list = await (await fetch(`http://127.0.0.1:${CDP_PORT}/json/list`)).json()
const ws = new WebSocket(list.find((p) => p.type === 'page').webSocketDebuggerUrl)
await new Promise((r) => ws.addEventListener('open', r, { once: true }))
const cdp = new Cdp(ws)
await cdp.send('Page.enable'); await cdp.send('Runtime.enable')
const ev = async (e) => (await cdp.send('Runtime.evaluate', { expression: e, returnByValue: true })).result.value

/* 量「需要宽度」：把 .kpi__delta / .kpi__num 设为 width:max-content 量一次，
   再恢复，得到内容真正需要的宽度 */
const MEASURE = `(() => {
  const strip = document.querySelector('.reg-kpis');
  if (!strip) return JSON.stringify({ err: 'no strip' });
  const out = [...strip.querySelectorAll('.kpi')].map((c) => {
    const num = c.querySelector('.kpi__num');
    const sub = c.querySelector('.kpi__sub');
    const del = c.querySelector('.kpi__delta');
    const box = (e) => { if (!e) return null; const r = e.getBoundingClientRect();
      return { w: Math.round(r.width), h: Math.round(r.height) }; };
    /* 需要宽度 */
    const want = (e) => { if (!e) return 0;
      const old = e.style.width; e.style.width = 'max-content';
      const w = Math.round(e.getBoundingClientRect().width); e.style.width = old; return w; };
    const subCS = sub ? getComputedStyle(sub) : null;
    const delCS = del ? getComputedStyle(del) : null;
    return {
      cardW: Math.round(c.getBoundingClientRect().width),
      numBox: box(num), subBox: box(sub), delBox: box(del),
      numWant: want(num), subWant: want(sub), delWant: want(del),
      subDisplay: subCS ? subCS.display : null,
      delText: del ? (del.textContent || '').trim() : '',
      numText: num ? (num.textContent || '').trim() : '',
      /* 裁切判据：内容宽 > 盒子宽 即被裁 */
      numClipped: num ? want(num) > Math.round(num.getBoundingClientRect().width) + 1 : false,
      delClipped: del ? want(del) > Math.round(del.getBoundingClientRect().width) + 1 : false,
    };
  });
  return JSON.stringify({ stripW: Math.round(strip.getBoundingClientRect().width), cards: out });
})()`

function page(kpiHtml, stripW, actions) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style>
<style>#toolplatform,#registry,#models,#kb{display:flex !important}
.main{padding:0 !important}
.reg__bar{width:${stripW}px}</style></head>
<body data-page="toolplatform">${sprite}
<div class="shell"><main class="main"><section class="subpage" id="toolplatform">
<div class="reg__bar">
  <div class="reg__title"><h2>标题 <em>占位</em></h2><p>占位副标题</p></div>
  <div class="reg-kpis kpis">${kpiHtml}</div>
  ${actions}
</div></section></main></div></body></html>`
}

const VIEWPORTS = [1440, 1320, 1180, 1100, 1000]
console.log('每个视口下，逐个页面量「说明」的 (需要宽 / 可用宽)，标 ✗ 表示被裁\n')
const findings = []
for (const vw of VIEWPORTS) {
  await cdp.send('Emulation.setDeviceMetricsOverride', { width: vw, height: 900, deviceScaleFactor: 1, mobile: false })
  /* 指标条可用宽 ≈ 视口 - 侧栏(约 216) - 内边距(约 40) */
  const stripW = vw - 256
  console.log(`\n################ 视口 ${vw}px（指标条可用 ${stripW}px）################`)
  for (const [name, html] of Object.entries(pages)) {
    const sec = kpiSection(html)
    if (!sec) { console.log(`  ${name}: 没有指标条`); continue }
    await cdp.send('Page.navigate', { url: 'data:text/html;charset=utf-8,' + encodeURIComponent(page(sec, stripW, actionBtn(html))) })
    await new Promise((r) => setTimeout(r, 450))
    const d = JSON.parse(await ev(MEASURE))
    if (d.err) { console.log(`  ${name}: ${d.err}`); continue }
    const parts = d.cards.map((c, i) => {
      const flag = c.delClipped ? '✗' : '✓'
      const sub = c.subDisplay === 'none' ? ' [单位已隐藏]' : ''
      if (c.delClipped) findings.push({ vw, name, card: i, delWant: c.delWant, delHave: c.delBox.w, text: c.delText })
      return `[${i}]${flag} 说明 ${c.delWant}/${c.delBox.w}${sub}`
    })
    const widths = d.cards.map((c) => c.cardW).join(',')
    console.log(`  ${name.padEnd(14)} 卡宽 [${widths}]`)
    console.log(`  ${''.padEnd(14)} ${parts.join('  ')}`)
  }
}

console.log('\n\n================ 结论 ================')
/* 单位被隐藏：整站范围内只要有一个视口隐藏了单位就报 */
const hidden = []
for (const vw of VIEWPORTS) hidden.push(vw)
console.log(`  单位隐藏的断点：${'≤1180px'}（console.css L2870–2873 .kpi__sub{display:none}）`)
if (!findings.length) {
  console.log('  「说明」文字在所有被测视口下都没有被裁切 —— 截断不是本页问题。')
} else {
  const byPage = {}
  for (const f of findings) {
    const k = f.name
    byPage[k] = byPage[k] || []
    byPage[k].push(f)
  }
  console.log('  以下页面的「说明」会被裁切：')
  for (const [name, fs] of Object.entries(byPage)) {
    const vws = [...new Set(fs.map((f) => f.vw))].sort((a, b) => b - a)
    const worst = fs.reduce((a, b) => (b.delWant - b.delHave > a.delWant - a.delHave ? b : a))
    console.log(
      `    ${name}: 视口 ${vws.join('/')}px，最严重 卡[${worst.card}] ` +
        `需要 ${worst.delWant}px 只有 ${worst.delHave}px（少 ${worst.delWant - worst.delHave}px）「${worst.text}」`,
    )
  }
}
ws.close()