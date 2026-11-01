/* ============================================================================
   AI 工具相关页面的截图脚本（人工目检用）

   用法（先起静态服务器）:
     node tools/serve-dist.mjs 4175
     node tools/shots-ai-tools.mjs http://127.0.0.1:4175 9222

   PNG 落在 tools/__shots__/（该目录在 .gitignore 里，不进仓库）。
   为什么要有它：本工程没有可用的看图能力（描述图片的工具没配好、模型不支持读图），
   所以只能"抓出来给人看" —— 几何断言在 tools/check-ai-tools.mjs 里，这里只负责出图。
   ========================================================================== */
import { mkdir, writeFile } from 'node:fs/promises'

const BASE = process.argv[2] || 'http://127.0.0.1:4175'
const CDP_PORT = Number(process.argv[3] || 9222)
const OUT = 'tools/__shots__'

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
await cdp.send('Network.setCacheDisabled', { cacheDisabled: true })
const view = (width, height) =>
  cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false })
await view(1440, 900)

const ev = async (e) => (await cdp.send('Runtime.evaluate', { expression: e, returnByValue: true })).result.value
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
await mkdir(OUT, { recursive: true })
const shot = async (name) => {
  const { data } = await cdp.send('Page.captureScreenshot', { format: 'png' })
  await writeFile(`${OUT}/${name}.png`, Buffer.from(data, 'base64'))
  console.log(`  saved ${OUT}/${name}.png`)
}

/* 登录态：/console/* 有守卫，先塞一个假令牌（守卫只验"有令牌且未过期"） */
const b64url = (o) => Buffer.from(JSON.stringify(o)).toString('base64url')
const now = Math.floor(Date.now() / 1000)
const tok =
  `${b64url({ alg: 'HS256', typ: 'JWT' })}.` +
  `${b64url({ username: 'shots', exp: now + 3600, iat: now })}.sig`
await cdp.send('Page.navigate', { url: 'about:blank' })
await sleep(400)
await cdp.send('Page.navigate', { url: BASE + '/#/login' })
await sleep(1400)
await ev(`localStorage.setItem('GA.token', ${JSON.stringify(tok)});'ok'`)
await cdp.send('Page.navigate', { url: 'about:blank' })
await sleep(300)
await cdp.send('Page.navigate', { url: BASE + '/#/console/toolplatform' })
await sleep(2800)

const tab = (i) => ev(`document.querySelectorAll('.reg__filters .tabs__btn')[${i}].click()`)
const scrollTop = (px) => ev(`document.querySelector('.aiguide__main').scrollTop = ${px}`)
/** 精确滚到第 i 步的顶部（比写死像素稳，步骤内容改过也不会拍偏） */
const stepTop = (i) =>
  ev(`document.querySelector('.aiguide__main').scrollTop = document.querySelectorAll('.aistep')[${i}].offsetTop`)
const sw = (i) => ev(`document.querySelectorAll('.aiguide__sw')[${i}].click()`)

// AI 工具是第一个 tab，而且现在是默认落地页；MCP / Skill 已置灰成 <span>（点不动）
await tab(0)
await sleep(600)
await shot('ai-01-list')

await ev(`document.querySelectorAll('.reg__grid .airow [data-aiact="guide"]')[0].click()`)
await sleep(800)
await shot('ai-02-dsh-desktop-top')
await stepTop(1) // 第 2 步「下载安装包」：平台内置的 exe 与校验值
await sleep(400)
await shot('ai-03-dsh-desktop-mid')
await stepTop(1)
await sleep(200)
await shot('ai-04-dsh-desktop-files')
await stepTop(6) // 最后一步：常见问题表
await sleep(400)
await shot('ai-05-dsh-desktop-faq')

await sw(1)
await sleep(700)
await shot('ai-06-dsh-cli-top')
await sw(2)
await sleep(700)
await shot('ai-07-zed-top') // 顶部就是「安装 Zed」：平台内置的 Zed-x86_64.exe 下载条目
await stepTop(4)
await sleep(400)
await shot('ai-08-zed-settings')

await ev(`document.querySelector('.aiguide__back').click()`)
await sleep(600)
await ev(`document.querySelector('.reg__bar .reg__sync').click()`)
await sleep(700)
await shot('ai-09-ref-top')
await scrollTop(900)
await sleep(400)
await shot('ai-10-ref-zed')

/* 窄屏：左侧步骤导航折叠成横向条（先回到某个工具的流程页） */
await ev(`document.querySelector('.aiguide__back').click()`)
await sleep(500)
await ev(`document.querySelectorAll('.reg__grid .airow [data-aiact="guide"]')[0].click()`)
await sleep(700)
await view(1180, 820)
await sleep(700)
await shot('ai-11-guide-narrow')
await view(1440, 900)

console.log('done')
ws.close()