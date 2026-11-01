/* ============================================================================
   工具平台 store —— MCP 服务 / Skill 工具 / AI 工具

   等价迁移自原型 console.js 的这几处：
     · 2079–2142  TST / TSTCN / TCAT / TOOLS / Tp（UI 状态）
     · 2144–2162  tList / tHay / tFiltered / tCounts
     · 2164–2214  renderToolKpis / updateToolKpis
     · 2216–2227  fillToolCats        分类下拉随 tab 变化
     · 2230–2304  renderTools         tab 徽标、页头计数、空态
     · 2305       tById
     · 2330–2545  新增 / 编辑 / 删除流程（表单回填与提交、确认弹窗）
     · 5311–5333  心跳里的工具页分支

   AI 工具（原型里没有，现排第一位并默认落地）是**下发给人装的客户端软件**，
   与 MCP / Skill（平台内部的可调用能力）不是一类对象，所以：
     · 数据与类型单独放 data/aitools.ts，不进 ToolItem 判别联合；
     · 卡片骨架仍复用 .regcard.toolrow（同一张卡、同一套列名）；
     · 点卡片不是开抽屉，而是**进入该工具的安装流程**（aiView = 'guide'）。

   注：卡片本身由视图层用 lib/cards.ts 渲染，
   store 只负责数据与状态 —— 原型里那套「只 patch [data-role] 节点」的
   局部刷新在 Vue 下由响应式接管。
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { MCPS, SKILLS, TST, TSTCN, TCAT } from '@/data/tools'
import type { McpTool, SkillTool, ToolItem, ToolState, ToolTab } from '@/data/tools'
import { AI_TOOLS, AICHANNEL, AIKIND } from '@/data/aitools'
import type { AiTool, AiToolChannel, AiToolId, AiToolKind } from '@/data/aitools'
import { esc, rand } from '@/lib/util'
import { useUiStore } from '@/stores/ui'
import { useOverlayStore } from '@/stores/overlay'

export { TST, TSTCN, TCAT }
export type { McpTool, SkillTool, ToolItem, ToolState, ToolTab }

/** AI 工具的形态筛选（与卡片上的 .fchip 一一对应） */
export type AiKindFilter = 'all' | AiToolKind
/** AI 工具的分发渠道筛选（右上角下拉） */
export type AiChannelFilter = 'all' | AiToolChannel

/**
 * 工具平台页面的三个标签页。
 * 注意与 data/tools.ts 的 ToolTab（数据判别式，只有 mcp / skill）区分：
 * 这里是**页面级 UI 状态**，所以多出 'ai'。
 */
export type ToolsTab = 'mcp' | 'skill' | 'ai'

/** AI 工具区的三种视图：列表 / 某个工具的安装流程 / 内网模型参数参考 */
export type AiView = 'list' | 'guide' | 'ref'

/**
 * 「开发中」的 tab：MCP / Skill 目前不可进入。
 *
 * 只放在 store 这一处，是因为切 tab 有两个入口 —— 模板上的按钮，以及任何
 * 直接调用 setTab 的代码（含未来可能加的深链/快捷键）。按钮那边已经渲染成
 * 不可点的 <span>，这里的守卫是第二道闸：把 locked 改回空集合即可全部恢复。
 */
const LOCKED_TABS: ReadonlySet<ToolsTab> = new Set<ToolsTab>(['mcp', 'skill'])

export type ToolFilter = 'all' | ToolState

/** tab 元信息（原型 renderTools 里的 tab 徽标与页头文案） */
export const TOOL_TABS: Record<ToolsTab, { item: string; ph: string; icon: string }> = {
  mcp: { item: 'MCP 服务', ph: '搜索服务名 / 分类 / 端点', icon: 'i-plug' },
  skill: { item: 'Skill 工具', ph: '搜索技能名 / 分类 / 归属智能体', icon: 'i-spark' },
  ai: { item: 'AI 工具', ph: '搜索工具名 / 形态 / 安装方式', icon: 'i-download' },
}

/** 新增 / 编辑表单模型 */
export interface ToolFormModel {
  toolName: string
  toolCat: string
  toolDesc: string
  toolTransport: string
  toolEndpoint: string
  toolVendor: string
  toolExposes: string
  toolOwner: string
  toolTimeout: string
  toolVersion: string
  toolStatus: ToolState
}

export const useToolsStore = defineStore('tools', () => {
  const ui = useUiStore()
  const overlay = useOverlayStore()

  /* ---------------------------------------------------------------- 可变副本 */
  const mcps = ref<McpTool[]>(structuredClone(MCPS) as McpTool[])
  const skills = ref<SkillTool[]>(structuredClone(SKILLS) as SkillTool[])
  /* AI 工具：平台下发的客户端软件（dsh 桌面版 / dsh 终端版 / Zed） */
  const aiTools = ref<AiTool[]>(structuredClone(AI_TOOLS) as AiTool[])

  /* ---------------------------------------------------------------- UI 状态 */
  /* 默认落在 AI 工具：MCP / Skill 两个 tab 目前置灰不可进入（见 ToolPlatformView 的 TABS） */
  const tab = ref<ToolsTab>('ai')
  const filter = ref<ToolFilter>('all')
  const cat = ref<'all' | string>('all')
  const q = ref('')
  let seq = 0

  /* AI 标签页自己的筛选与视图状态（与 MCP / Skill 的筛选互不干扰） */
  const aiKind = ref<AiKindFilter>('all')
  const aiChannel = ref<AiChannelFilter>('all')
  const aiView = ref<AiView>('list')
  const aiToolId = ref<AiToolId | null>(null)
  /**
   * 装机流程里「已勾掉的步骤」，键是 `${toolId}#${stepId}`。
   * 有意不做持久化：流程是「照着做一遍」的东西，重开页面重新走一遍更符合直觉，
   * 也避免 localStorage 里堆一份没人清的安装态。
   */
  const aiDone = ref<Record<string, boolean>>({})
  /** 今日新增下发次数（KPI 里显示，心跳里涨） */
  const aiToday = ref(46)

  function setTab(t: ToolsTab): void {
    /* 开发中的 tab 不可进入（见 LOCKED_TABS）。守卫放在最前，
       这样即便有人直接调 setTab('mcp') 也不会切过去。 */
    if (LOCKED_TABS.has(t)) return
    tab.value = t
    filter.value = 'all'
    q.value = ''
    /* 分类下拉随 tab 变化，切过去要复位（原型 fillToolCats 里的兜底） */
    cat.value = 'all'
    aiKind.value = 'all'
    aiChannel.value = 'all'
    /* 离开 AI 标签页时退出安装流程，回来看到的是列表 */
    aiView.value = 'list'
  }

  function setQuery(v: string): void {
    q.value = v
    if (ui.query !== v) ui.query = v
  }

  function setCat(c: string): void {
    cat.value = c
  }

  /** 状态筛选条的点击（原型 console.html 353–356 的 data-tst） */
  function setFilter(f: ToolFilter): void {
    filter.value = f
  }

  /* ---------------------------------------------------------------- 查询 */
  /**
   * 取当前 tab 的 MCP / Skill 列表。
   * 入参放宽到 ToolsTab：页面 tab 多了一个 'ai'，而 AI 工具有自己的 aiFiltered
   * （它不是 ToolItem），所以这里对非 mcp 一律返回 Skill 列表，
   * 调用方（filtered / counts / cats）在被 AI 标签页使用时不会被走到。
   */
  function dataOf(t: ToolsTab): readonly ToolItem[] {
    return t === 'mcp' ? mcps.value : skills.value
  }

  /** 原型 tList()：当前 tab 的列表 */
  const list = computed<ToolItem[]>(() => dataOf(tab.value).slice())

  const allTools = computed<ToolItem[]>(() => [...mcps.value, ...skills.value])

  function byId(id: string | null): ToolItem | null {
    if (!id) return null
    return allTools.value.find((t) => t.id === id) ?? null
  }

  function hay(t: ToolItem): string {
    return (
      `${t.name} ${t.cat} ${t.desc} ${t.endpoint} ${t.transport} ${t.vendor} ${t.owner ?? ''}`
    ).toLowerCase()
  }

  function filteredOf(byState: boolean): ToolItem[] {
    return dataOf(tab.value).filter((t) => {
      if (byState && filter.value !== 'all' && t.status !== filter.value) return false
      if (cat.value !== 'all' && t.cat !== cat.value) return false
      if (q.value && hay(t).indexOf(q.value.toLowerCase()) < 0) return false
      return true
    })
  }

  const filtered = computed<ToolItem[]>(() => filteredOf(true))

  const counts = computed(() => {
    const c = { all: 0, online: 0, degraded: 0, offline: 0 }
    filteredOf(false).forEach((t) => {
      c.all++
      c[t.status]++
    })
    return c
  })

  const tabCounts = computed(() => ({
    mcp: mcps.value.length,
    skill: skills.value.length,
    ai: aiTools.value.length,
  }))

  /** 分类下拉的选项：当前 tab 出现过的分类（去重） */
  const cats = computed<string[]>(() => {
    const out: string[] = []
    dataOf(tab.value).forEach((t) => {
      if (out.indexOf(t.cat) < 0) out.push(t.cat)
    })
    return out
  })

  /** 页头汇总文案（原型对应位置的表达；AI 标签页给的是「可领取的安装包」口径） */
  const headCount = computed(() => {
    if (tab.value === 'ai') {
      return `${aiTools.value.length} 个 AI 工具 · ${aiFiles.value} 个可领取文件`
    }
    return `${mcps.value.length} 个 MCP 服务 · ${skills.value.length} 个 Skill 工具`
  })
  const newLabel = computed(() => `新建${TOOL_TABS[tab.value].item}`)
  const seekPlaceholder = computed(() => TOOL_TABS[tab.value].ph)

  /** 页头主按钮文案：MCP / Skill 是「新建」，AI 工具是「查看内网模型参数」 */
  const actionLabel = computed(() => (tab.value === 'ai' ? '内网模型参数' : newLabel.value))
  const actionIcon = computed(() => (tab.value === 'ai' ? 'i-model' : 'i-plus'))

  /* ================================================================ AI 工具 */
  /*
     AI 工具（AI 标签页）与 MCP / Skill 共用「筛选条 + 卡片网格」的页面外壳，
     但筛选维度不同：这里按**形态**（桌面端 / 终端 / IDE）与**渠道**（官方 / 第三方）筛。
     关键词搜索同时命中名称、定位、卡片配置项与流程步骤标题 —— 想找「怎么接内网模型」
     的人直接搜「内网」也能落到对应的工具上。
  */
  function aiHay(t: AiTool): string {
    return (
      `${t.name} ${t.sub} ${t.desc} ${AIKIND[t.kind].cn} ${AICHANNEL[t.channel]} ` +
      t.cfg.map((r) => r.join(' ')).join(' ') +
      ' ' +
      t.steps.map((s) => `${s.title} ${s.goal}`).join(' ')
    ).toLowerCase()
  }

  const aiFiltered = computed<AiTool[]>(() =>
    aiTools.value.filter((t) => {
      if (aiKind.value !== 'all' && t.kind !== aiKind.value) return false
      if (aiChannel.value !== 'all' && t.channel !== aiChannel.value) return false
      if (q.value && aiHay(t).indexOf(q.value.toLowerCase()) < 0) return false
      return true
    }),
  )

  /** 形态筛选条上的计数：按「渠道 + 关键词」过滤后统计（与 MCP / Skill 同口径） */
  const aiCounts = computed(() => {
    const c = { all: 0, desktop: 0, cli: 0, ide: 0 }
    aiTools.value.forEach((t) => {
      if (aiChannel.value !== 'all' && t.channel !== aiChannel.value) return
      if (q.value && aiHay(t).indexOf(q.value.toLowerCase()) < 0) return
      c.all++
      c[t.kind]++
    })
    return c
  })

  function setAiKind(k: AiKindFilter): void {
    aiKind.value = k
  }

  function setAiChannel(c: string): void {
    aiChannel.value = c as AiChannelFilter
  }

  /** 当前打开的 AI 工具（安装流程视图用；null = 停在列表） */
  const aiTool = computed<AiTool | null>(
    () => aiTools.value.find((t) => t.id === aiToolId.value) ?? null,
  )

  function openAiGuide(id: AiToolId): void {
    aiToolId.value = id
    aiView.value = 'guide'
  }

  function openAiRef(): void {
    aiView.value = 'ref'
  }

  function closeAiView(): void {
    aiView.value = 'list'
  }

  /* 装机流程的勾选进度（键是 `${toolId}#${stepId}`） */
  function isStepDone(toolId: string, stepId: string): boolean {
    return aiDone.value[`${toolId}#${stepId}`] === true
  }

  function toggleStep(toolId: string, stepId: string): void {
    const k = `${toolId}#${stepId}`
    if (aiDone.value[k]) delete aiDone.value[k]
    else aiDone.value[k] = true
  }

  /** 某个工具的装机进度（已完成 / 总步数 / 百分比） */
  function progressOf(t: AiTool): { done: number; total: number; pct: number } {
    const total = t.steps.length
    const done = t.steps.filter((s) => isStepDone(t.id, s.id)).length
    return { done, total, pct: total ? Math.round((done / total) * 100) : 0 }
  }

  /** 全部标记完成 / 重走一遍（流程页底部两个按钮） */
  function markAllSteps(t: AiTool): void {
    t.steps.forEach((s) => {
      aiDone.value[`${t.id}#${s.id}`] = true
    })
  }

  function resetSteps(t: AiTool): void {
    t.steps.forEach((s) => {
      delete aiDone.value[`${t.id}#${s.id}`]
    })
  }

  /* 下发计数：卡片③栏、KPI 条与心跳共用 */
  const aiDownloads = computed(() => aiTools.value.reduce((a, t) => a + t.downloads, 0))
  const aiFiles = computed(() => aiTools.value.reduce((a, t) => a + t.files.length, 0))

  /**
   * 触发一次「平台内置文件」的下载：拼绝对地址 + 一个带 download 属性的临时 <a>。
   *
   * 用相对地址（`ai-tools/xxx.exe`，真身在 public/ai-tools/）而不是写死 `/ai-tools/...`，
   * 是因为 `new URL(url, document.baseURI)` 在部署到子路径时同样成立；
   * 用 <a download> 而不是 window.open，是因为 exe 开新标签只会闪一下，
   * 而 download 会让浏览器直接存盘。返回 false 表示当前没有 document（SSR 兜底）。
   */
  function downloadFrom(label: string, url: string, name?: string): boolean {
    if (typeof document === 'undefined') return false
    const abs = new URL(url, document.baseURI).href
    const a = document.createElement('a')
    a.href = abs
    a.download = name || url.split('/').pop() || label
    a.rel = 'noopener'
    a.style.display = 'none'
    document.body.appendChild(a)
    a.click()
    a.remove()
    return true
  }

  /**
   * 领取一个安装包：记一次下发，然后把安装包**直接下载**下来。
   *
   * 平台内置的安装包都是相对地址（见 downloadFrom）；绝对 http(s) 地址仍按老办法
   * window.open —— 与「新建会话 → dsh 控制台」（lib/dsh.ts）同一套写法，
   * 好处是能判断是否被浏览器拦截（返回 null），被拦时给出可手动打开的地址。
   */
  function claimFile(t: AiTool, url: string): void {
    t.downloads++
    aiToday.value++
    if (typeof window === 'undefined') return

    if (!/^https?:\/\//i.test(url)) {
      downloadFrom(t.name, url)
      ui.pushText(`已开始下载：${t.name}`, ['安装包来自平台内置，全程走内网'])
      return
    }

    const win = window.open(url, '_blank')
    if (win) {
      try {
        win.opener = null
      } catch {
        /* 跨源时个别浏览器不让写，忽略 */
      }
      ui.pushText(`已记一次下发：${t.name}`, [url])
      return
    }
    ui.pushText('下载被浏览器拦截', [`请手动打开：${url}`])
  }

  /** 复制某个工具的接入速查（settings.yaml / settings.json + 密钥环境变量） */
  function notifyCopy(label: string, ok: boolean): void {
    if (!ok) {
      ui.pushText('复制失败', ['浏览器拒绝了剪贴板写入，请手动选中复制'])
      return
    }
    ui.pushText(`已复制${label}`, ['粘贴到配置文件即可，两个 compat 开关已带上'])
  }

  /** AI 标签页的 KPI（四张卡与其它页面的 .kpi 同一套骨架） */
  const aiKpis = computed(() => ({
    total: aiTools.value.length,
    files: aiFiles.value,
    downloads:
      aiDownloads.value >= 1000
        ? `${(aiDownloads.value / 1000).toFixed(1)}k`
        : String(aiDownloads.value),
    today: aiToday.value,
    steps: aiTools.value.reduce((a, t) => a + t.steps.length, 0),
  }))

  /* ---------------------------------------------------------------- KPI */
  const kpis = computed(() => {
    const count = (arr: ToolItem[], st: ToolState) => arr.filter((t) => t.status === st).length
    let calls = 0
    let expose = 0
    allTools.value.forEach((t) => {
      calls += t.calls
      expose += t.exposes
    })
    const p95Sum = mcps.value.reduce((a, t) => {
      const n = parseInt(t.p95, 10)
      return a + (isNaN(n) ? 0 : n)
    }, 0)
    return {
      mcp: mcps.value.length,
      mcpOn: count(mcps.value, 'online'),
      sk: skills.value.length,
      skOn: count(skills.value, 'online'),
      expose,
      warn: count(mcps.value, 'degraded') + count(skills.value, 'degraded'),
      calls: calls >= 1000 ? `${(calls / 1000).toFixed(1)}k` : String(calls),
      p95: `${Math.round(p95Sum / (mcps.value.length || 1))} ms`,
    }
  })

  /* ---------------------------------------------------------------- 表单 */
  /** 快捷键与提示文案（原型 2330–2360 的表单头部） */
  const formSub = computed(() =>
    tab.value === 'mcp'
      ? 'MCP 服务按标准协议接入：stdio 走本地进程，SSE / streamable-http 走内网端点。'
      : 'Skill 工具是带进出参约束的脚本能力，需声明运行时、归属智能体与执行超时。',
  )
  const formHint = computed(() =>
    overlay.modalEditingId
      ? '保存后会立即更新注册表，已建立的调用链不受影响。'
      : '保存后需重新执行一次连通性探测，探测通过才会被智能体调度。',
  )

  function formModel(id: string | null): ToolFormModel {
    const item = id ? byId(id) : null
    const isMcp = (item?.kind ?? tab.value) === 'mcp'
    const sk = item && item.kind === 'skill' ? item : null
    return {
      toolName: item?.name ?? '',
      toolCat: item?.cat ?? '',
      toolDesc: item?.desc ?? '',
      toolTransport: item?.transport ?? (isMcp ? 'stdio' : 'Python 3.12'),
      toolEndpoint: item?.endpoint ?? '',
      toolVendor: item?.vendor ?? '',
      toolExposes: String(item?.exposes ?? 1),
      toolOwner: sk?.owner ?? '',
      toolTimeout: sk?.timeout ?? '',
      toolVersion: sk?.version ?? '',
      toolStatus: item?.status ?? 'online',
    }
  }

  const formIsMcp = computed(() => {
    const id = overlay.modalEditingId
    return id ? kindOf(id) === 'mcp' : tab.value === 'mcp'
  })

  /** 编辑时该走哪种表单（Skill 有运行时与版本字段，MCP 没有） */
  function kindOf(id: string | null): ToolTab {
    return byId(id)?.kind ?? 'mcp'
  }

  function submitForm(v: ToolFormModel): boolean {
    const name = v.toolName.trim()
    if (!name) {
      ui.pushHtml('请先填写工具名称')
      return false
    }
    const isMcp = formIsMcp.value
    const exposes = parseInt(v.toolExposes.replace(/[^\d]/g, ''), 10) || 1
    const editingId = overlay.modalEditingId
    const editing = editingId ? byId(editingId) : null

    if (editing) {
      editing.name = name
      editing.cat = v.toolCat.trim() || '数据处理'
      editing.desc = v.toolDesc.trim() || '未填写说明'
      editing.transport = v.toolTransport as never
      editing.endpoint = v.toolEndpoint.trim() || '未填写端点'
      editing.vendor = v.toolVendor.trim() || '未标注归属组'
      editing.exposes = exposes
      editing.status = v.toolStatus
      if (editing.kind === 'skill') {
        editing.owner = v.toolOwner.trim() || '未绑定智能体'
        editing.timeout = v.toolTimeout.trim() || '120s'
        editing.version = v.toolVersion.trim() || '0.1.0'
      }
      ui.pushText(`${name} 已更新`, ['注册表已刷新，下次调用生效'])
      return true
    }

    seq++
    /* 原型新建时计数从 0 起、P95 为 '—'（未探测） */
    if (isMcp) {
      const fresh: McpTool = {
        kind: 'mcp',
        id: `mcp-n${seq}`,
        name,
        cat: v.toolCat.trim() || '数据处理',
        desc: v.toolDesc.trim() || '未填写说明',
        transport: (v.toolTransport || 'stdio') as McpTool['transport'],
        endpoint: v.toolEndpoint.trim() || '未填写端点',
        vendor: v.toolVendor.trim() || '未标注归属组',
        exposes,
        status: v.toolStatus,
        calls: 0,
        p95: '—',
        owner: '—',
        timeout: '—',
      }
      mcps.value = [fresh, ...mcps.value]
    } else {
      const fresh: SkillTool = {
        kind: 'skill',
        id: `sk-n${seq}`,
        name,
        cat: v.toolCat.trim() || '数据处理',
        desc: v.toolDesc.trim() || '未填写说明',
        transport: (v.toolTransport || 'Python 3.12') as SkillTool['transport'],
        endpoint: v.toolEndpoint.trim() || '未填写路径',
        vendor: v.toolVendor.trim() || '未标注归属组',
        exposes,
        status: v.toolStatus,
        calls: 0,
        p95: '—',
        owner: v.toolOwner.trim() || '未绑定智能体',
        timeout: v.toolTimeout.trim() || '120s',
        version: v.toolVersion.trim() || '0.1.0',
      }
      skills.value = [fresh, ...skills.value]
    }
    ui.pushText(`${TOOL_TABS[isMcp ? 'mcp' : 'skill'].item} ${name} 已创建`, [
      '已写入注册表，等待连通性探测',
    ])
    return true
  }

  /* ---------------------------------------------------------------- 行内动作 */
  function toggle(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.status === 'offline') {
      item.status = 'online'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已上线`)
    } else {
      item.status = 'offline'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已下线`)
    }
  }

  function askDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    overlay.askConfirm({
      title: `删除${item.kind === 'mcp' ? 'MCP 服务' : 'Skill 工具'}`,
      text:
        `确认删除 <b>${esc(item.name)}</b>？` +
        '删除后已引用该能力的智能体会立即失去这项工具，' +
        '操作会记入审计流水，不可恢复。',
      mode: 'tool',
      id: item.id,
      name: item.name,
    })
  }

  function doDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.kind === 'mcp') mcps.value = mcps.value.filter((x) => x.id !== id)
    else skills.value = skills.value.filter((x) => x.id !== id)
    ui.pushText(`${item.name} 已删除`, ['审计流水已记录'])
  }

  /* ---------------------------------------------------------------- 心跳 */
  /**
   * 累加调用量、抖动 P95（原型 5311–5333）；
   * AI 工具没有调用量，用「下发次数」承担同一件事：让这一页的数据是活的。
   */
  function beat(): void {
    allTools.value.forEach((t) => {
      if (t.status === 'offline') return
      t.calls += rand(2, 18)
      if (Math.random() < 0.15 && t.p95 !== '—') {
        const base = parseFloat(t.p95)
        if (!isNaN(base)) {
          t.p95 = /s$/.test(t.p95)
            ? `${(base * (1 + rand(-12, 12) / 100)).toFixed(1)} s`
            : `${Math.round(base * (1 + rand(-12, 12) / 100))} ms`
        }
      }
    })
    aiTools.value.forEach((t) => {
      t.downloads += rand(0, 2)
    })
    aiToday.value += rand(0, 2)
  }

  return {
    mcps,
    skills,
    aiTools,
    list,
    allTools,

    tab,
    filter,
    cat,
    q,
    setTab,
    setQuery,
    setFilter,
    setCat,

    dataOf,
    byId,
    kindOf,
    filtered,
    counts,
    tabCounts,
    cats,
    headCount,
    newLabel,
    seekPlaceholder,
    actionLabel,
    actionIcon,
    kpis,

    /* AI 工具（第一个 tab） */
    aiKind,
    aiChannel,
    aiView,
    aiToolId,
    aiDone,
    aiFiltered,
    aiCounts,
    aiTool,
    aiDownloads,
    aiFiles,
    aiKpis,
    aiToday,
    setAiKind,
    setAiChannel,
    openAiGuide,
    openAiRef,
    closeAiView,
    isStepDone,
    toggleStep,
    progressOf,
    markAllSteps,
    resetSteps,
    claimFile,
    downloadFrom,
    notifyCopy,

    formSub,
    formHint,
    formIsMcp,
    formModel,
    submitForm,

    toggle,
    askDelete,
    doDelete,
    beat,
  }
})