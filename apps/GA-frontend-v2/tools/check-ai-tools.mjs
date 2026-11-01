/* ============================================================================
   工具平台 · AI 工具标签页与安装流程验收

   验十件事（⑨ 是本轮「内网自包含」的专项：无外链、无官方入口、安装包直接下载）：
      ① 标签页：AI 工具是第一个且默认落地，MCP / Skill 两个「开发中」置灰不可点
      ② AI 卡片：3 张（DSH 桌面版 / DSH 终端版 / Zed），形态标签齐全
      ③ 形态筛选与搜索：点「桌面端」→ 1 张；搜「zed」→ 1 张；切回全部 → 3 张
      ④ 点「安装流程」进入流程页：步骤数（桌面版 7 步，第 4 步是「换内网镜像源」+ 两个脚本文件）、
         命令块、复制按钮、步骤导航都对得上
      ⑤ 顶部三个工具的切换、左侧导航跳转、每步「标记完成」都真的生效（进度会变）
      ⑥ 复制按钮能把代码写进剪贴板（给了 toast 反馈）
      ⑦ 页头「内网模型参数」进入参数速查页，再返回能回到列表
      ⑧ 几何体检：文字不被截断、窄屏下左栏折叠成横向条、没有横向溢出
      ⑨ 内网自包含：左下角没有「官方入口」；正文里的 http(s) 只有内网地址；
         dsh 桌面版 / Zed 流程里没有 winget / GitHub / zed.dev；
         「领取安装包」与第 4 步的两个镜像脚本，触发的都是本平台 public/ai-tools/ 下文件的下载
      ⑩ 回归对照：MCP / Skill 两个「开发中」标签页不可进入，AI 区不受影响

   用法: node tools/check-ai-tools.mjs [base] [CDP_PORT]
        默认 base = http://127.0.0.1:4175、CDP_PORT = 9222

   注意（两个都踩过）：
     · /console/* 有登录守卫，脚本会先往 localStorage 写一个假令牌（守卫只验
       「有令牌且 exp 未过期」，验签是后端的事）—— 它验的是页面，不是鉴权；
     · CSS / JS 会被浏览器缓存，所以要 Network.setCacheDisabled + 经 about:blank
       过渡再导航，否则量到的是上一版。
   ========================================================================== */
import { statSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE = (process.argv[2] || 'http://127.0.0.1:4175').replace(/\/$/, '')
const CDP_PORT = Number(process.argv[3] || process.env.CDP_PORT || 9222)
/** 仓库根（本文件在 tools/ 下）——用来核对构建产物里安装包的字节数 */
const ROOT = fileURLToPath(new URL('..', import.meta.url))

class Cdp {
  constructor(ws) {
    this.ws = ws
    this.id = 0
    this.p = new Map()
    ws.addEventListener('message', (ev) => {
      const m = JSON.parse(ev.data)
      if (m.id && this.p.has(m.id)) {
        const { resolve, reject } = this.p.get(m.id)
        this.p.delete(m.id)
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
await cdp.send('Page.enable')
await cdp.send('Runtime.enable')
await cdp.send('Network.enable')
await cdp.send('Network.clearBrowserCache')
await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 1440,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
})

const ev = async (expr) =>
  (await cdp.send('Runtime.evaluate', { expression: expr, returnByValue: true })).result.value
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

/** 真实鼠标点击（不能用 el.click()：那绕过命中测试，永远"点得动"） */
async function click(selector, nth = 0) {
  const selectorJs = JSON.stringify(selector)
  const measure = async () =>
    JSON.parse(
      await ev(`(() => {
        const el = document.querySelectorAll(${selectorJs})[${nth}];
        if (!el) return JSON.stringify(null);
        const r = el.getBoundingClientRect();
        return JSON.stringify({
          x: Math.round(r.left + r.width / 2),
          y: Math.round(r.top + r.height / 2),
          inView: r.top >= 0 && r.bottom <= window.innerHeight && r.width > 0,
        });
      })()`),
    )
  let box = await measure()
  if (!box) throw new Error(`找不到可点元素：${selector}[${nth}]`)
  if (!box.inView) {
    // 先滚进视口再量一次：滚动是异步的，直接点会点到滚动前的位置上（踩过）
    await ev(
      `document.querySelectorAll(${selectorJs})[${nth}].scrollIntoView({ block: 'center', behavior: 'instant' })`,
    )
    await sleep(300)
    box = await measure()
  }
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mousePressed',
    x: box.x,
    y: box.y,
    button: 'left',
    clickCount: 1,
  })
  await cdp.send('Input.dispatchMouseEvent', {
    type: 'mouseReleased',
    x: box.x,
    y: box.y,
    button: 'left',
    clickCount: 1,
  })
  await sleep(320)
}

let bad = 0
function check(ok, label, extra = '') {
  if (!ok) bad++
  console.log(`  ${ok ? '✓' : '✗'} ${label}${extra ? `  ${extra}` : ''}`)
}

/* ------------------------------------------------------------------ 登录态 */
const b64url = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const nowSec = Math.floor(Date.now() / 1000)
const stubToken =
  `${b64url({ alg: 'HS256', typ: 'JWT' })}.` +
  `${b64url({ username: 'ai-tools-check', exp: nowSec + 3600, iat: nowSec })}.stub-signature`

await cdp.send('Page.navigate', { url: 'about:blank' })
await sleep(400)
await cdp.send('Page.navigate', { url: BASE + '/#/login' })
await sleep(1500)
await ev(
  `window.localStorage.setItem('GA.token', ${JSON.stringify(stubToken)});` +
    `window.localStorage.setItem('GA.user', ${JSON.stringify(
      JSON.stringify({ username: 'ai-tools-check', realname: 'AI 工具检查' }),
    )});'ok'`,
)
// 必须先回 about:blank：只有 hash 不同的地址是同文档跳转，不会重跑 main.ts 的 restore
await cdp.send('Page.navigate', { url: 'about:blank' })
await sleep(400)
await cdp.send('Page.navigate', { url: BASE + '/#/console/toolplatform' })
await sleep(2600)

// 给 <a download> 的点击装一个探针：领取安装包是「造一个临时 a 再 click 再删掉」，
// 同步过程，DOM 里抓不到痕迹；拦一下原型方法就能记下解析后的绝对地址与 download 文件名，
// 而且不会真的下载 148 MB（headless 里也没配下载目录）。
await ev(`(() => {
  window.__dl = [];
  const orig = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (this.hasAttribute('download')) window.__dl.push({ href: this.href, download: this.download });
    else return orig.apply(this, arguments);
  };
  return 'ok';
})()`)

/* ------------------------------------------------------------------ ① 标签页 */
console.log('\n=== ① 工具平台标签页（AI 工具 + 两个「开发中」）===')
const tabInfo = JSON.parse(
  await ev(`(() => {
    // 置灰的 tab 也带 .tabs__btn（额外挂 .is-locked），只是从 <button> 变成 <span>
    const items = [...document.querySelectorAll('.reg__filters .tabs__btn')];
    return JSON.stringify(items.map((b) => ({
      tag: b.tagName.toLowerCase(),
      text: (b.querySelector('em:not(.tabs__dev)') ? b.textContent.replace(b.querySelector('em:not(.tabs__dev)').textContent, '') : b.textContent).replace(/\\s+/g, ''),
      badge: b.querySelector('em:not(.tabs__dev)') ? b.querySelector('em:not(.tabs__dev)').textContent.trim() : '',
      dev: b.querySelector('.tabs__dev') ? b.querySelector('.tabs__dev').textContent.trim() : '',
      on: b.classList.contains('is-on'),
      locked: b.classList.contains('is-locked') || b.getAttribute('aria-disabled') === 'true',
    })));
  })()`),
)
console.log(
  '  标签页：' +
    tabInfo.map((t) => `${t.text}(${t.badge || t.dev})${t.on ? ' ←当前' : ''}${t.locked ? '/不可点' : ''}`).join(' · '),
)
check(tabInfo.length === 3, '共有 3 个标签页（AI 工具 / MCP 服务 / Skill 工具）')
check(tabInfo[0] && tabInfo[0].text === 'AI工具' && tabInfo[0].badge === '3', '第一项是「AI 工具」，徽标 3')
check(tabInfo[0].on === true, 'AI 工具是默认落地的标签页')
// MCP / Skill 由另一处改动改成「开发中」置灰（不是本功能的范围，但要知道它在那儿）
check(
  tabInfo[1].tag === 'span' && tabInfo[2].tag === 'span' && tabInfo[1].dev === '开发中',
  'MCP / Skill 两个标签页是「开发中」置灰态（渲染成 span，点不动）',
  `${tabInfo[1].tag}/${tabInfo[2].tag}`,
)

/* ------------------------------------------------------------------ ② 卡片 */
console.log('\n=== ② AI 工具卡片 ===')
const cardInfo = JSON.parse(
  await ev(`(() => {
    const cards = [...document.querySelectorAll('.reg__grid .airow')];
    return JSON.stringify(cards.map((c) => ({
      id: c.getAttribute('data-ai'),
      name: (c.querySelector('.regcard__name b') || {}).textContent || '',
      kind: (c.querySelector('.mfamily') || {}).textContent || '',
      cfg: [...c.querySelectorAll('.toolrow__cfg span')].length,
      acts: [...c.querySelectorAll('.regcard__acts button')].map((b) => b.getAttribute('data-aiact')),
    })));
  })()`),
)
cardInfo.forEach((c) =>
  console.log(`  ${c.id.padEnd(12)} ${c.name}  [${c.kind}] 配置项 ${c.cfg}  操作 ${c.acts.join('/')}`),
)
check(cardInfo.length === 3, 'AI 工具卡片 3 张')
check(
  cardInfo.map((c) => c.id).join(',') === 'dsh-desktop,dsh-cli,zed',
  '卡片顺序：dsh 桌面版 → dsh 终端版 → Zed',
)
check(cardInfo.every((c) => c.cfg === 6), '每张卡的「安装与配置」都是 6 项')
check(
  cardInfo.every((c) => c.acts.includes('guide') && c.acts.includes('cfg')),
  '每张卡都有「安装流程」与「复制配置」',
)
const dlActs = cardInfo.map((c) => c.acts.filter((a) => a === 'dl' || a === 'cmd').join('')).join(',')
check(dlActs === 'dl,cmd,dl', '按形态给对了第三个按钮（exe→领取安装包，命令行→复制安装命令）', dlActs)

const kpis = JSON.parse(
  await ev(`JSON.stringify([...document.querySelectorAll('.reg-kpis .kpi')].map((k) => ({
    num: (k.querySelector('.kpi__num b')?.textContent || '').trim(),
    unit: (k.querySelector('.kpi__sub')?.textContent || '').trim(),
    delta: (k.querySelector('.kpi__delta')?.textContent || '').trim(),
  })))`),
)
console.log('  指标：' + kpis.map((k) => `${k.num}${k.unit}`).join(' · '))
check(kpis.length === 4, 'AI 标签页有 4 张指标卡')
check(
  kpis.map((k) => k.unit).join(',') === 'AI 工具,装机步骤,累计下发,内网模型',
  '指标口径是 AI 工具自己的（不是 MCP 的调用量）',
  kpis.map((k) => k.unit).join(','),
)
check(
  kpis[0].num === '3' && kpis[1].num === '19',
  '指标数：3 个工具 / 19 个装机步骤（7+6+6，桌面版把 yaml 降级为可选块后又加了「换内网镜像源」一步）',
  `${kpis[0].num} / ${kpis[1].num}`,
)
check(kpis[0].delta.includes('2 个可领取文件'), '可领取文件数：2 个（dsh 桌面版 + Zed 各一个安装包）', kpis[0].delta)

// 卡片上的「复制配置」走的是 quickConfigText（按工具拼 settings.yaml / settings.json + 环境变量）
await click('.reg__grid .airow [data-aiact="cfg"]', 0)
await sleep(400)
const cfgToast = await ev(
  `(() => { const t = document.getElementById('toast'); return t ? t.className.includes('is-on') + '|' + t.textContent.trim().slice(0, 60) : 'no-toast'; })()`,
)
check(cfgToast.startsWith('true'), '卡片「复制配置」给了轻提示反馈', cfgToast)

/* ------------------------------------------------------------------ ③ 筛选 */
console.log('\n=== ③ 形态筛选与关键词搜索 ===')
await click('.reg__filters .fchip', 1) // 桌面端
await sleep(320)
let n = await ev(`document.querySelectorAll('.reg__grid .airow').length`)
check(n === 1, '点「桌面端」→ 只剩 1 张卡', `实际 ${n}`)
await click('.reg__filters .fchip', 0) // 全部
await sleep(320)
n = await ev(`document.querySelectorAll('.reg__grid .airow').length`)
check(n === 3, '点「全部」→ 回到 3 张卡', `实际 ${n}`)

await ev(`(() => { const i = document.querySelector('.reg__seek input'); i.focus(); i.select(); return 'ok'; })()`)
await cdp.send('Input.insertText', { text: 'zed' })
await sleep(500)
const searched = JSON.parse(
  await ev(`JSON.stringify([...document.querySelectorAll('.reg__grid .airow')].map((c) => c.getAttribute('data-ai')))`),
)
check(searched.length === 1 && searched[0] === 'zed', '搜「zed」→ 命中 Zed', searched.join(','))
// 清空搜索：内容里的「内网模型」也在关键词范围内，这里顺手验一下中文命中
await ev(`(() => { const i = document.querySelector('.reg__seek input'); i.focus(); i.select(); return 'ok'; })()`)
await cdp.send('Input.insertText', { text: '内网模型' })
await sleep(500)
const searched2 = JSON.parse(
  await ev(`JSON.stringify([...document.querySelectorAll('.reg__grid .airow')].map((c) => c.getAttribute('data-ai')))`),
)
check(searched2.length === 3, '搜「内网模型」→ 三个工具都命中（配置项也在搜索范围内）', searched2.join(','))
await ev(`(() => { const i = document.querySelector('.reg__seek input'); i.value = ''; i.dispatchEvent(new Event('input', { bubbles: true })); return 'ok'; })()`)
await sleep(400)

/* ------------------------------------------------------------------ ④ 流程页 */
console.log('\n=== ④ 进入安装流程页（DSH 桌面版）===')
await click('.reg__grid .airow [data-aiact="guide"]', 0)
await sleep(600)
const guide = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    if (!g) return JSON.stringify(null);
    const main = g.querySelector('.aiguide__main');
    const rail = g.querySelector('.aiguide__rail');
    return JSON.stringify({
      title: (g.querySelector('.aiguide__name b') || {}).textContent || '',
      steps: g.querySelectorAll('.aistep').length,
      railItems: g.querySelectorAll('.aiguide__railitem').length,
      codes: g.querySelectorAll('.aicode').length,
      copies: g.querySelectorAll('.aicode__copy').length,
      notes: g.querySelectorAll('.ainote').length,
      tables: g.querySelectorAll('.aitable table').length,
      files: g.querySelectorAll('.aifile').length,
      firstStep: (g.querySelector('.aistep__title b') || {}).textContent || '',
      railW: Math.round(rail.getBoundingClientRect().width),
      mainOverflowX: main.scrollWidth - main.clientWidth,
      mainH: Math.round(main.getBoundingClientRect().height),
      cardGridGone: document.querySelectorAll('.reg__grid .airow').length === 0,
    });
  })()`),
)
console.log('  ' + JSON.stringify(guide))
check(!!guide, '流程页已渲染（.aiguide 出现）')
check(guide.title === 'DSH 桌面版', '流程页顶部是「DSH 桌面版」')
check(guide.steps === 7 && guide.railItems === 7, '7 个步骤 + 左侧 7 个导航项（桌面版）')
// 第 4 步「换内网镜像源」：脚本随站点下发（.cmd + .ps1 必须同目录），且这一步不占用「可选块」
const mirrorStep = JSON.parse(
  await ev(`(() => {
    const steps = [...document.querySelectorAll('.aistep')];
    const s = steps.find((x) => ((x.querySelector('.aistep__title b') || {}).textContent || '').includes('换内网镜像源'));
    if (!s) return JSON.stringify(null);
    return JSON.stringify({
      idx: steps.indexOf(s),
      files: [...s.querySelectorAll('.aifile b')].map((b) => b.textContent.trim()),
      codes: s.querySelectorAll('.aicode').length,
      tables: s.querySelectorAll('.aitable table').length,
      opts: s.querySelectorAll('.aiopt').length,
    });
  })()`),
)
console.log('  ' + JSON.stringify(mirrorStep))
check(
  !!mirrorStep && mirrorStep.idx === 3,
  '第 4 步是「换内网镜像源」（紧跟「安装与首次启动」）',
  mirrorStep ? `实际第 ${mirrorStep.idx + 1} 步` : '没找到这一步',
)
check(
  !!mirrorStep && mirrorStep.files.join(',') === 'setup-internal-mirror.cmd,setup-internal-mirror.ps1',
  '这一步给出两个脚本文件（.cmd 双击入口 + .ps1 主脚本）',
  mirrorStep ? mirrorStep.files.join(',') : '',
)
check(
  !!mirrorStep && mirrorStep.codes === 2 && mirrorStep.tables === 1 && mirrorStep.opts === 0,
  '这一步有执行/验证命令与常见问题表，且没有新增「可选块」',
  mirrorStep ? `code=${mirrorStep.codes} table=${mirrorStep.tables} opt=${mirrorStep.opts}` : '',
)
const opt = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    const o = g.querySelectorAll('.aiopt');
    return JSON.stringify({
      n: o.length,
      badge: o.length ? (o[0].querySelector('.aiopt__badge') || {}).textContent.trim() : '',
      title: o.length ? (o[0].querySelector('.aiopt__title') || {}).textContent.trim() : '',
      step: o.length ? o[0].closest('.aistep').querySelector('.aistep__title b').textContent.trim() : '',
      border: o.length ? getComputedStyle(o[0]).borderTopStyle : '',
      rail: [...g.querySelectorAll('.aiguide__railitem span')].map((s) => s.textContent.trim()).join('|'),
    });
  })()`),
)
check(
  opt.n === 1 && opt.badge === '可选' && opt.title.includes('settings.yaml'),
  'settings.yaml 与两个兼容开关已降级成「可选」块',
  opt.n + ' 个 · ' + opt.badge + ' · ' + opt.title,
)
check(
  opt.step === '配置内网模型' && !opt.rail.includes('settings.yaml') && !opt.rail.includes('进阶'),
  '可选块挂在「配置内网模型」这一步里，左侧导航里没有它的一格',
  opt.step + ' / 导航 ' + opt.rail,
)
check(opt.border === 'dashed', '可选块是虚线降级样式（视觉上不与必经步骤同权）', opt.border)
check(guide.firstStep.includes('准备工作'), '第 1 步是「准备工作」（桌面版不讲网络前提）')
check(guide.codes >= 4 && guide.copies === guide.codes, '每个命令块都带一个复制按钮', `${guide.copies}/${guide.codes}`)
check(guide.notes >= 4, '提示条（注意 / 说明 / 要点）都在')
check(guide.tables >= 1, '常见问题表格已渲染')
check(guide.files >= 1, '下载条目已渲染（平台内置的安装包）', `${guide.files} 个`)
check(guide.cardGridGone, '流程页整块替换掉了卡片区（不是叠在上面）')
check(guide.railW >= 200 && guide.railW <= 260, '左侧导航宽度符合设计（236px 档）', `${guide.railW}px`)
check(guide.mainOverflowX <= 1, '内容区没有横向溢出', `scrollWidth-clientWidth=${guide.mainOverflowX}`)
check(guide.mainH > 300, '内容区高度正常（有独立滚动条，不是被压扁）', `${guide.mainH}px`)

// .btn 的宽度 / 字距 / 上边距必须是控制台口径：login.css 里另有一条 .btn（登录页整宽主按钮），
// 两张表同时在场时，console.css 没声明的属性会被它漏进来 —— 按钮被拉成整宽、字距 .22em、
// 整体下移 8px（既有页面上的抽屉按钮就是这个现象）
const btnGeom = JSON.parse(
  await ev(`JSON.stringify([...document.querySelectorAll('.aiguide .btn')].map((b) => {
    const s = getComputedStyle(b);
    return {
      text: b.textContent.trim().slice(0, 8),
      display: s.display,
      w: Math.round(b.getBoundingClientRect().width),
      h: s.height,
      mt: s.marginTop,
      ls: s.letterSpacing,
      ti: s.textIndent,
    };
  }))`),
)
console.log(
  '  按钮：' +
    btnGeom.map((b) => `${b.text}(${b.w}px,${b.h},mt=${b.mt},ls=${b.ls})`).join(' · '),
)
// 说明：flex 项目里的 .btn 会被「块化」（inline-flex → flex），所以 display 只要求是 flex 系
check(
  btnGeom.length > 0 && btnGeom.every((b) => b.w < 240 && /flex/.test(b.display)),
  '流程页里的按钮贴合内容宽度（没有被 login.css 的 .btn 拉成整宽）',
)
check(
  btnGeom.every((b) => b.h === '32px' && b.mt === '0px' && /^(normal|0px)$/.test(b.ls) && b.ti === '0px'),
  '按钮的尺寸 / 上边距 / 字距是控制台口径（没有被 login.css 的 .btn 漏进来）',
)

/* ------------------------------------------------------------------ ⑤ 交互 */
console.log('\n=== ⑤ 步骤导航 / 标记完成 / 工具切换 ===')
await click('.aiguide__railitem', 2)
await sleep(700)
const activeIdx = await ev(
  `[...document.querySelectorAll('.aiguide__railitem')].findIndex((b) => b.classList.contains('is-on'))`,
)
check(activeIdx === 2, '点左侧第 3 项 → 高亮跟到第 3 项', `实际第 ${activeIdx + 1} 项`)

await click('.aistep__done', 1)
await sleep(320)
const done = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    return JSON.stringify({
      stepDone: g.querySelectorAll('.aistep')[1].classList.contains('is-done'),
      railDone: g.querySelectorAll('.aiguide__railitem')[1].classList.contains('is-done'),
      prog: (g.querySelector('.aiguide__prog span') || {}).textContent.trim(),
      barW: g.querySelector('.aiguide__meter i').style.width,
    });
  })()`),
)
check(done.stepDone && done.railDone, '「标记完成」把第 2 步与左侧导航一起置为已完成')
check(done.prog.includes('1/7'), '顶部进度变成 1/7', done.prog)
check(done.barW !== '0%', '进度条宽度跟着变', done.barW)

await click('.aiguide__sw', 2) // Zed
await sleep(500)
const zed = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    return JSON.stringify({
      title: (g.querySelector('.aiguide__name b') || {}).textContent || '',
      steps: g.querySelectorAll('.aistep').length,
      settingsJson: [...g.querySelectorAll('.aicode__title')].some((t) => t.textContent.includes('settings.json')),
      prog: (g.querySelector('.aiguide__prog span') || {}).textContent.trim(),
    });
  })()`),
)
check(zed.title === 'Zed' && zed.steps === 6, '顶部切到 Zed → 6 步流程', `${zed.title}/${zed.steps} 步`)
check(zed.settingsJson, 'Zed 流程里给出了 settings.json 片段')
check(zed.prog.includes('0/6'), '换工具后进度独立（Zed 是 0/6）', zed.prog)

/* ------------------------------------------------------------------ ⑥ 复制 */
console.log('\n=== ⑥ 复制按钮 ===')
await cdp.send('Browser.grantPermissions', {
  origin: BASE,
  permissions: ['clipboardReadWrite', 'clipboardSanitizedWrite'],
})
await click('.aicode__copy', 0)
await sleep(400)
const toast = await ev(
  `(() => { const t = document.getElementById('toast'); return t ? t.className.includes('is-on') + '|' + t.textContent.trim().slice(0, 40) : 'no-toast'; })()`,
)
check(toast.startsWith('true'), '点复制后给了轻提示反馈', toast)

/* ------------------------------------------------------------------ ⑦ 参数速查 */
console.log('\n=== ⑦ 内网模型参数速查 ===')
await click('.aiguide__back', 0)
await sleep(500)
const backToCards = await ev(`document.querySelectorAll('.reg__grid .airow').length`)
check(backToCards === 3, '返回后回到 AI 工具列表（3 张卡）', `实际 ${backToCards}`)

const actionLabel = await ev(`document.querySelector('.reg__bar .reg__sync span').textContent.trim()`)
check(actionLabel === '内网模型参数', 'AI 标签页的页头主按钮是「内网模型参数」', actionLabel)
await click('.reg__bar .reg__sync', 0)
await sleep(500)
const ref = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    if (!g) return JSON.stringify(null);
    const main = g.querySelector('.aiguide__main');
    return JSON.stringify({
      title: (g.querySelector('.aiguide__name b') || {}).textContent || '',
      sections: g.querySelectorAll('.aistep').length,
      yaml: [...g.querySelectorAll('.aicode__title')].some((t) => t.textContent.includes('settings.yaml')),
      json: [...g.querySelectorAll('.aicode__title')].some((t) => t.textContent.includes('settings.json')),
      curl: g.textContent.includes('172.16.234.96:8666'),
      overflowX: main.scrollWidth - main.clientWidth,
    });
  })()`),
)
console.log('  ' + JSON.stringify(ref))
check(!!ref, '参数速查页已渲染')
check(ref.sections === 4, '4 节：端点 / dsh 配置 / Zed 配置 / 网络与代理')
check(ref.yaml && ref.json, 'dsh 与 Zed 的配置片段都在这一页')
check(ref.curl, '内网端点与连通性自检命令都在')
check(ref.overflowX <= 1, '参数速查页也没有横向溢出', `overflowX=${ref.overflowX}`)
await click('.aiguide__back', 0)
await sleep(500)
check(
  (await ev(`document.querySelectorAll('.reg__grid .airow').length`)) === 3,
  '再返回 → 回到列表',
)

/* ------------------------------------------------------------------ ⑧ 几何体检 */
console.log('\n=== ⑧ 几何体检（文字不被截断 / 窄屏折叠）===')
const shape = JSON.parse(
  await ev(`(() => {
    const grid = document.querySelector('.reg__grid');
    const clipped = [];
    const sel = ['.regcard__name b', '.regcard__sub', '.toolrow__cfg span', '.kpi__num b', '.kpi__sub'];
    sel.forEach((s) => {
      document.querySelectorAll(s).forEach((el) => {
        if (el.scrollWidth > el.clientWidth + 1) clipped.push(s + ' :: ' + el.textContent.trim().slice(0, 24));
      });
    });
    const cards = [...document.querySelectorAll('.reg__grid .airow')];
    return JSON.stringify({
      gridW: Math.round(grid.getBoundingClientRect().width),
      cardWs: cards.map((c) => Math.round(c.getBoundingClientRect().width)),
      clipped,
    });
  })()`),
)
check(shape.clipped.length === 0, '列表页文字没有被截断', shape.clipped.join(' | '))
check(
  shape.cardWs.every((w) => w < shape.gridW + 1 && w > 120),
  '卡片宽度正常（贴合栅格，没有溢出）',
  `grid=${shape.gridW} cards=${shape.cardWs.join(',')}`,
)

// 窄屏：左侧步骤导航折叠成横向条，正文仍然不能横向溢出
await click('.reg__grid .airow [data-aiact="guide"]', 0)
await sleep(600)
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 1180,
  height: 820,
  deviceScaleFactor: 1,
  mobile: false,
})
await sleep(700)
const narrow = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    const main = g.querySelector('.aiguide__main');
    const rail = g.querySelector('.aiguide__rail');
    return JSON.stringify({
      railDir: getComputedStyle(rail).flexDirection,
      railH: Math.round(rail.getBoundingClientRect().height),
      mainOverflowX: main.scrollWidth - main.clientWidth,
      overflowX: getComputedStyle(rail).overflowX,
    });
  })()`),
)
console.log('  ' + JSON.stringify(narrow))
check(narrow.railDir === 'row', '窄屏下步骤导航折叠成横向条', narrow.railDir)
check(narrow.mainOverflowX <= 1, '窄屏下正文仍然没有横向溢出', `overflowX=${narrow.mainOverflowX}`)
await cdp.send('Emulation.setDeviceMetricsOverride', {
  width: 1440,
  height: 900,
  deviceScaleFactor: 1,
  mobile: false,
})
await sleep(500)
await click('.aiguide__back', 0)
await sleep(500)

/* ------------------------------------------------------------------ ⑧ 回归 */
console.log('\n=== ⑨ 内网自包含：无外链、无官方入口、安装包可直接下载 ===')

// ⑨a 左下角「官方入口」必须整块没了
await click('.reg__grid .airow [data-aiact="guide"]', 0)
await sleep(600)
const selfContained = JSON.parse(
  await ev(`(() => {
    const g = document.querySelector('.aiguide');
    const text = g.textContent;
    const urls = [...new Set((text.match(/https?:\\/\\/[^\\s"'）)、，,；;]+/g) || []))];
    return JSON.stringify({
      docsBlock: g.querySelectorAll('.aiguide__docs').length,
      hasOfficialEntry: text.includes('官方入口'),
      links: [...g.querySelectorAll('a[href]')].map((a) => a.getAttribute('href')),
      urls,
      external: urls.filter((u) => !/^https?:\\/\\/(172\\.16\\.234\\.96|127\\.0\\.0\\.1)([:\\/]|$)/.test(u)),
    });
  })()`),
)
console.log('  外链扫描（DSH 桌面版流程）：' + (selfContained.urls.join(' ') || '（没有 http(s) 地址）'))
check(selfContained.docsBlock === 0, '左下角「官方入口」整块已删除')
check(!selfContained.hasOfficialEntry, '页面里不再出现「官方入口」字样')
check(selfContained.links.length === 0, '流程页里没有任何 <a href> 外链', selfContained.links.join(','))
check(
  selfContained.external.length === 0,
  '正文里出现的 http(s) 地址全是内网（172.16.234.96 / 127.0.0.1），没有 github / zed.dev 之类',
  selfContained.external.join(','),
)
check(
  !/winget|GitHub|github|zed\.dev/.test(await ev(`document.querySelector('.aiguide').textContent`)),
  'DSH 桌面版流程里没有 winget / GitHub / zed.dev 这类需要外网的步骤',
)
check(
  !/robot WiFi|网络要求|NO_PROXY|代理/.test(await ev(`document.querySelector('.aiguide').textContent`)),
  'DSH 桌面版流程里没有任何网络前提（默认访问者的网络环境是通的）',
)

// ⑨b 另外两个工具 + 参数速查页也扫一遍
for (const [i, name] of [
  [1, 'DSH 终端版'],
  [2, 'Zed'],
]) {
  await click('.aiguide__sw', i)
  await sleep(500)
  const scan = JSON.parse(
    await ev(`(() => {
      const text = document.querySelector('.aiguide').textContent;
      const urls = [...new Set((text.match(/https?:\\/\\/[^\\s"'）)、，,；;]+/g) || []))];
      return JSON.stringify({
        urls,
        external: urls.filter((u) => !/^https?:\\/\\/(172\\.16\\.234\\.96|127\\.0\\.0\\.1)([:\\/]|$)/.test(u)),
        docs: document.querySelectorAll('.aiguide__docs').length,
      });
    })()`),
  )
  console.log(`  ${name}：` + (scan.urls.join(' ') || '（没有 http(s) 地址）'))
  check(scan.docs === 0, `${name} 也没有「官方入口」块`)
  // dsh 终端版按约定「先不做改动」，它的 winget / npx 外网步骤留着，不在这里断言
  if (name === 'Zed') {
    check(scan.external.length === 0, 'Zed 流程里没有外链', scan.external.join(','))
    check(
      !/winget|\bzed\.dev\b/.test(await ev(`document.querySelector('.aiguide').textContent`)),
      'Zed 流程里没有 winget / 官网下载步骤',
    )
    check(
      /robot WiFi/.test(await ev(`document.querySelector('.aiguide').textContent`)),
      'Zed 流程仍按手册口径保留 robot WiFi（只有桌面版去掉该限制）',
    )
  }
}

await click('.aiguide__back', 0)
await sleep(500)
await click('.reg__bar .reg__sync', 0)
await sleep(600)
const refExternal = JSON.parse(
  await ev(`(() => {
    const text = document.querySelector('.aiguide').textContent;
    const urls = [...new Set((text.match(/https?:\\/\\/[^\\s"'）)、，,；;]+/g) || []))];
    return JSON.stringify({ urls, external: urls.filter((u) => !/^https?:\\/\\/(172\\.16\\.234\\.96|127\\.0\\.0\\.1)([:\\/]|$)/.test(u)), docs: document.querySelectorAll('.aiguide__docs').length });
  })()`),
)
check(refExternal.external.length === 0 && refExternal.docs === 0, '参数速查页同样自包含（无外链、无官方入口）')
await click('.aiguide__back', 0)
await sleep(500)

// ⑨c 平台内置安装包：构建产物里真的有这个文件（字节数对得上），HTTP 也能取到
//     （静态服务器对二进制走 chunked，不给 content-length，所以大小用 fs 查 dist 里的真身）
const installers = [
  { id: 'dsh-desktop', path: 'ai-tools/dsh-latest-windows-x64.exe', bytes: 289313640, tool: 'DSH 桌面版' },
  { id: 'zed', path: 'ai-tools/Zed-x86_64.exe', bytes: 85627488, tool: 'Zed' },
]
for (const f of installers) {
  const onDisk = statSync(join(ROOT, 'dist', f.path)).size
  const res = await fetch(BASE + '/' + f.path)
  const reader = res.body.getReader()
  const first = await reader.read()
  await reader.cancel()
  const head = first.value && first.value.length >= 2 ? String.fromCharCode(first.value[0], first.value[1]) : ''
  check(
    res.status === 200 && onDisk === f.bytes && head === 'MZ',
    `${f.tool} 的安装包在构建产物里且能直接下载（${(onDisk / 1024 / 1024).toFixed(1)} MB，PE 头 ${head || '?'}）`,
    f.path,
  )
  check(
    head === 'MZ' && first.value.length > 0,
    `${f.tool}：下载响应确实在传文件内容（不是空响应）`,
    `${first.value.length} 字节`,
  )
}

// ⑨d 点「领取安装包」触发的是本平台地址的下载（不是跳外网、不是开新标签）
for (const f of installers) {
  await ev(`window.__dl = []`)
  await click(`.reg__grid .airow[data-ai="${f.id}"] [data-aiact="dl"]`)
  await sleep(400)
  const dl = JSON.parse(await ev(`JSON.stringify(window.__dl)`))
  const toast = await ev(`(() => { const t = document.getElementById('toast'); return t ? t.textContent.trim().slice(0, 30) : ''; })()`)
  const hit = dl.length === 1 && dl[0].href === BASE + '/' + f.path && dl[0].download === f.path.split('/').pop()
  check(hit, `${f.tool}：点「领取安装包」直接下载本平台的文件`, dl.length ? `${dl[0].href}` : `没触发下载（toast=${toast}）`)
}

// ⑨d' 第 4 步下发的两个镜像源脚本：构建产物里有、HTTP 能取到、点「领取」直接下载
const aiScripts = ['setup-internal-mirror.cmd', 'setup-internal-mirror.ps1']
for (const name of aiScripts) {
  const rel = 'ai-tools/' + name
  const inPublic = statSync(join(ROOT, 'public', rel)).size
  const inDist = statSync(join(ROOT, 'dist', rel)).size
  const res = await fetch(BASE + '/' + rel)
  const body = await res.text()
  check(
    res.status === 200 && inPublic > 0 && inPublic === inDist && body.length > 0,
    `镜像源脚本 ${name} 随站点下发且能直接下载（${inPublic} 字节）`,
    rel,
  )
}

// 流程页里那条下载条目（.aifile 里的「领取」）走的是同一个 claimFile，也验一下
await click('.reg__grid .airow [data-aiact="guide"]', 0)
await sleep(600)
await ev(`window.__dl = []`)
await click('.aifile .btn', 0)
await sleep(400)
const dlInGuide = JSON.parse(await ev(`JSON.stringify(window.__dl)`))
check(
  dlInGuide.length === 1 && dlInGuide[0].href === BASE + '/ai-tools/dsh-latest-windows-x64.exe',
  '流程页下载条目里的「领取」按钮同样直接下载本平台文件',
  dlInGuide.length ? dlInGuide[0].href : '没触发下载',
)

// 第 4 步两个脚本的「领取」：.aifile 里的按钮顺序 0 = 安装包（第 2 步），1 = .cmd（第 4 步），2 = .ps1
await ev(`window.__dl = []`)
await click('.aifile .btn', 1)
await sleep(400)
const dlMirror = JSON.parse(await ev(`JSON.stringify(window.__dl)`))
check(
  dlMirror.length === 1 && dlMirror[0].href === BASE + '/ai-tools/setup-internal-mirror.cmd',
  '流程第 4 步的脚本「领取」同样直接下载本平台文件',
  dlMirror.length ? dlMirror[0].href : '没触发下载',
)

await click('.aiguide__back', 0)
await sleep(500)

console.log('\n=== ⑩ 回归对照：MCP / Skill 两个标签页仍不可进入；AI 区不受影响 ===')
// 这两个 tab 现在是「开发中」置灰态（另一处改动），所以不能再去点它们数卡片；
// 能验的是：它们确实渲染成不可点的 <span>、挂了「开发中」小标，且真实点击不改变当前 tab。
const locked = JSON.parse(
  await ev(`(() => {
    const els = [...document.querySelectorAll('.reg__filters .tabs__btn.is-locked')];
    return JSON.stringify(els.map((e) => ({
      tag: e.tagName.toLowerCase(),
      dev: (e.querySelector('.tabs__dev') || {}).textContent || '',
      title: e.getAttribute('title') || '',
      aria: e.getAttribute('aria-disabled') || '',
      tabbable: e.tabIndex >= 0,
    })));
  })()`),
)
console.log('  ' + JSON.stringify(locked))
check(locked.length === 2, 'MCP / Skill 两个「开发中」标签页都在')
check(
  locked.every((l) => l.tag === 'span' && l.dev.trim() === '开发中' && /开发中/.test(l.title)),
  '两个置灰 tab 是 <span> + 「开发中」小标 + title 说明原因',
)
check(locked.every((l) => l.tabbable === false), '置灰 tab 不可被键盘 Tab 聚焦')

// 真实点击（走鼠标事件）其中一个：当前 tab 不能变
const before = await ev(`document.querySelector('.reg__filters .is-on').textContent.replace(/\\s+/g, '')`)
await click('.reg__filters .tabs__btn.is-locked', 0)
const after = await ev(`document.querySelector('.reg__filters .is-on').textContent.replace(/\\s+/g, '')`)
check(before === after && /AI工具/.test(after), '真实点击「开发中」的 tab：仍停在 AI 工具', `${before} → ${after}`)
check(
  (await ev(`document.querySelectorAll('.reg__grid .airow').length`)) === 3,
  'AI 工具列表照旧（3 张卡，没有被 tab 置灰改动影响）',
)
check(
  (await ev(`document.querySelectorAll('.reg__filters .tabs__btn.is-on').length`)) === 1,
  '同时只有一个「当前 tab」（筛选条上的 is-on 不算）',
)

console.log(`\n${bad === 0 ? 'AI 工具标签页验收全部通过 ✓' : `有 ${bad} 项未通过 ✗`}`)
ws.close()
process.exit(bad === 0 ? 0 : 1)