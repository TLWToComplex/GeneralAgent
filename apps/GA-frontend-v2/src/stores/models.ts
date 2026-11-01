/* ============================================================================
   模型中心 store —— 模型清单（家族 / 规格 / 上下文 / 部署态 / 调用水位）+ 部署演示

   等价迁移自原型 console.js 的这几处：
     · 1726–1739  MOD / MST / MSTATES / MFAM / Mo（页面 UI 状态：filter / type / q）
     · 1801–1803  fmtNum()                        调用量缩写（≥1 万折成 "w"）
     · 1840–1859  updateModKpis()                 顶栏四张统计卡
     · 1862–1885  modHay / modFiltered / modCounts / updateModCounts  筛选与计数
     · 1887–1963  renderModCards()                卡片渲染（结构交给组件，这里定口径）
     · 1965–1998  modTimers / startModDeploy()    部署演示（600ms 推进到 100%）
     · 2000–2073  bindModels()                    部署按钮 / 下线 / 筛选 / 类型 / 搜索 / 批量部署
     · 5280–5309  beat() 里模型页那一拍           抖动 load、累加 calls、刷新 P95 与错误率

   ⚠️ 原型的 MODELS 是「模块级数组 + 直接 mutate」：部署定时器会不停改 load / status，
   心跳每 1.8 秒改 load / calls / p95 / err。Vue 里必须让这些字段是响应式的，所以
   store 持有一份 structuredClone 出来的副本，用 shallowRef + touch() 触发更新
   （与 stores/session.ts 同样的做法）。
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { MOD, MODELS as SEED_MODELS, MSTATES, MST } from '@/data/models'
import type {
  ModelFilter,
  ModelItem,
  ModelState,
  ModelStateMeta,
  ModelType,
} from '@/data/models'
import { clamp, esc, rand } from '@/lib/util'
import { useUiStore } from '@/stores/ui'

/* 原型的 MOD / MST / MSTATES 是页面级常量，组件（状态徽标、家族色）也要用，直接透出 */
export { MOD, MST, MSTATES }

/** 部署演示的推进间隔（原型 1997 行的 600ms） */
export const MOD_DEPLOY_EVERY = 600
/** 列表页心跳间隔（原型 5463 行的 1800ms） */
export const MOD_BEAT_EVERY = 1800
/** 页内搜索与顶栏搜索的防抖时长（原型 2052–2059 的 160ms） */
export const MOD_SEEK_DEBOUNCE = 160

/** 调用量缩写（原型 1801–1803）：≥1 万换成 "4.8w"，否则原样返回 */
export function fmtNum(n: number): string {
  return n >= 10000 ? (n / 10000).toFixed(1) + 'w' : String(n)
}

export const useModelsStore = defineStore('models', () => {
  const ui = useUiStore()

  /** 可变的模型副本（部署定时器与心跳会改它，所以不能直接用 data 里的种子数组） */
  const models: ModelItem[] = structuredClone(SEED_MODELS) as ModelItem[]
  const list = shallowRef<ModelItem[]>(models)

  /* ---------------------------------------------------------------- 页面 UI 状态 */
  /** 状态胶囊（原型 Mo.filter） */
  const filter = ref<ModelFilter>('all')
  /** 模型类型下拉（原型 Mo.type，'all' 为全部类型） */
  const type = ref<'all' | ModelType>('all')
  /** 页内 / 顶栏搜索词（原型 Mo.q，两端都是 160ms 防抖后写进来） */
  const q = ref('')

  function setFilter(f: ModelFilter): void {
    filter.value = f
  }

  function setType(t: 'all' | ModelType): void {
    type.value = t
  }

  function setQuery(v: string): void {
    // 原型 `Mo.q = ms.value.trim()`（2055 行）：存进来的永远是去空格的值
    q.value = v.trim()
    if (ui.query !== q.value) ui.query = q.value
  }

  function byId(id: string | null): ModelItem | null {
    if (!id) return null
    return models.find((m) => m.id === id) ?? null
  }

  /** 通知响应式系统「内部字段变了」（原型是直接 mutate DOM） */
  function touch(): void {
    list.value = models.slice()
  }

  /* ---------------------------------------------------------------- 筛选 */
  /** 原型 modHay（1862–1863）：名称 / 家族 / 类型 / 版本 / 规格 */
  function hay(m: ModelItem): string {
    return `${m.name} ${m.family} ${m.type} ${m.ver} ${m.params}`.toLowerCase()
  }

  /** byState=false 时忽略状态胶囊（算计数用），类型与关键词始终生效 */
  function isVis(m: ModelItem, byState: boolean): boolean {
    if (byState && filter.value !== 'all' && m.status !== filter.value) return false
    if (type.value !== 'all' && m.type !== type.value) return false
    if (q.value && hay(m).indexOf(q.value.toLowerCase()) < 0) return false
    return true
  }

  /** 卡片列表（原型 modFiltered(true) 1865–1872）：状态 + 类型 + 关键词，保持原始顺序 */
  const filtered = computed<ModelItem[]>(() => list.value.filter((m) => isVis(m, true)))

  /**
   * 胶囊上的五个计数（原型 modCounts 1873–1877）。
   * 注意口径：**忽略状态胶囊本身**，只受类型下拉与关键词影响。
   */
  const counts = computed<Record<ModelFilter, number>>(() => {
    const c: Record<ModelFilter, number> = {
      all: 0,
      deployed: 0,
      deploying: 0,
      degraded: 0,
      offline: 0,
    }
    list.value.forEach((m) => {
      if (!isVis(m, false)) return
      c.all++
      c[m.status]++
    })
    return c
  })

  /** 页头「N 个模型」（原型 updateModCounts 1884） */
  const countText = computed(() => `${counts.value.all} 个模型`)

  /**
   * 类型去重列表（HTML 里 #modType 是五个写死的 option，console.html 305–312）。
   * 这里从数据按首次出现顺序去重派生，顺序与原型的 option 完全一致。
   */
  const types = computed<ModelType[]>(() => {
    const out: ModelType[] = []
    list.value.forEach((m) => {
      if (out.indexOf(m.type) < 0) out.push(m.type)
    })
    return out
  })

  /** 全量状态计数（不受任何筛选影响，KPI 口径） */
  const statusCounts = computed<Record<ModelState, number>>(() => {
    const c: Record<ModelState, number> = { deployed: 0, deploying: 0, degraded: 0, offline: 0 }
    list.value.forEach((m) => {
      c[m.status]++
    })
    return c
  })

  const deployedCount = computed(() => statusCounts.value.deployed)
  const deployingCount = computed(() => statusCounts.value.deploying)
  const degradedCount = computed(() => statusCounts.value.degraded)
  const offlineCount = computed(() => statusCounts.value.offline)

  /**
   * 顶栏四张统计卡（原型 updateModKpis 1840–1859）。
   * 口径是全量模型，与筛选无关；几处刻意的原型细节都保留：
   *   · 在线 = deployed + deploying（部署中也算「在线」）
   *   · 占用 GPU 取 res 的数字前缀（'4 × A100 80G' → 4），且只算在线那两个状态
   *   · 今日 Token 累加 tokens 里的数字（'—' 跳过），拼成一位小数 + 'M'
   *   · P95 首字原型写死 '420 ms'（1855 行），这里照旧
   *   · 错误率是各模型 err 的算术平均（'—' 不参与），两位小数 + '%'
   */
  const kpi = computed(() => {
    let online = 0
    let calls = 0
    let tk = 0
    let gpu = 0
    const errs: number[] = []
    list.value.forEach((m) => {
      const live = m.status === 'deployed' || m.status === 'deploying'
      if (live) online++
      calls += m.calls
      gpu += live ? parseInt(m.res, 10) : 0
      const t = parseFloat(String(m.tokens).replace('M', ''))
      if (!isNaN(t)) tk += t
      if (m.err && m.err !== '—') errs.push(parseFloat(m.err))
    })
    const avgErr = errs.length ? errs.reduce((a, b) => a + b, 0) / errs.length : 0
    return {
      /** 在线模型 */
      online,
      /** 个已注册 */
      total: list.value.length,
      /** 今日 Token */
      tokensText: tk.toFixed(1) + 'M',
      /** 次调用 */
      callsText: fmtNum(calls),
      /** P95 首字（原型写死） */
      p95Text: '420 ms',
      /** 错误率 */
      errText: avgErr.toFixed(2) + '%',
      /** 占用 GPU（数字） */
      gpu,
      /** 占用 GPU（'N ×'） */
      gpuText: gpu + ' ×',
      /** 张卡 · 集群 A/B/C */
      cardsText: String(gpu),
    }
  })

  /* ---------------------------------------------------------------- 卡片取值 */
  /** 状态徽标文案（原型 1919 的 MOD[m.status].cn，部署中额外带进度 1996） */
  function stChipText(m: ModelItem): string {
    return m.status === 'deploying' ? `部署中 ${m.load}%` : MOD[m.status].cn
  }

  /** 状态徽标元信息（原型 MOD[m.status]，取 cn / cls） */
  function modCfg(m: ModelItem): ModelStateMeta {
    return MOD[m.status]
  }

  /** 状态基色（原型 MST[m.status]，写进卡片的 --st） */
  function stVar(m: ModelItem): string {
    return MST[m.status]
  }

  /** 「调用配额占用」：只有在线 / 部署中才有水位（原型 1928） */
  function quotaText(m: ModelItem): string {
    const live = m.status === 'deployed' || m.status === 'deploying'
    return live ? `${m.load}%` : '—'
  }

  /** 「已上线」一栏（原型 1930）：部署中 / 已下线不显示时间 */
  function fromText(m: ModelItem): string {
    return m.status === 'deploying' ? '部署中' : m.status === 'offline' ? '—' : m.from
  }

  /** 调用量文案（原型 1936 / 5301）：'4.8w 次' */
  function callsText(m: ModelItem): string {
    return `${fmtNum(m.calls)} 次`
  }

  /** 部署按钮是否可点（原型 1907：只有已下线 / 异常需要上线） */
  function canDeploy(m: ModelItem): boolean {
    return m.status === 'offline' || m.status === 'degraded'
  }

  /** 部署按钮文案（原型 1908–1909） */
  function deployTxt(m: ModelItem): string {
    return m.status === 'deploying' ? '部署中…' : m.status === 'offline' ? '上线' : '重新部署'
  }

  /* ---------------------------------------------------------------- 部署演示 */
  /** 每个模型的部署定时器（原型 modTimers 1966，用 id 作键） */
  const deployTimers = new Map<string, number>()

  function stopDeploy(id: string): void {
    const t = deployTimers.get(id)
    if (t !== undefined) {
      window.clearInterval(t)
      deployTimers.delete(id)
    }
  }

  /**
   * 原型 startModDeploy(m)（1967–1998）：
   *   起手 status=deploying / load=6 / qps='预热中' / p95='—' / err='—'，
   *   600ms 推进一次（clamp(load + rand(8,19), 6, 100)），到 100 变 deployed、
   *   load=34，并把 qps / p95 / err 换成一组合理的实测值。
   *
   * 原型 bindModels 在按钮分支里先拦一次「已在部署」（2013 行）：此时只弹提示不再重复
   * 起定时器。这里把那一句折进 startDeploy，组件直接调它即可。
   */
  function startDeploy(id: string): void {
    const m = byId(id)
    if (!m) return
    if (m.status === 'deploying') {
      ui.pushHtml(`<b>${esc(m.name)}</b> 正在部署，进度 ${m.load}%`)
      return
    }
    m.status = 'deploying'
    m.load = 6
    m.qps = '预热中'
    m.p95 = '—'
    m.err = '—'
    stopDeploy(m.id)
    touch()
    ui.pushHtml(`开始部署 <b>${esc(m.name)}:${esc(m.ver)}</b> · 目标 ${esc(m.res)}`)

    const t = window.setInterval(() => {
      m.load = clamp(m.load + rand(8, 19), 6, 100)
      if (m.load >= 100) {
        stopDeploy(m.id)
        m.status = 'deployed'
        m.load = 34
        m.qps = rand(18, 58) + ' req/s'
        m.p95 = rand(240, 480) + ' ms'
        m.err = (rand(4, 18) / 100).toFixed(2) + '%'
        touch()
        ui.pushHtml(`<b>${esc(m.name)}</b> 已上线，灰度流量 5%`)
        return
      }
      /* 原型这里只改这一张卡的进度条与状态徽标（1991–1996）：
         Vue 里一次 touch() 就够，卡片按 id 复用 DOM。 */
      touch()
    }, MOD_DEPLOY_EVERY)
    deployTimers.set(m.id, t)
    /* 登记到 ui store：退出登录能一次性 clearInterval 掉 */
    ui.registerTimer(t)
  }

  /** 「批量部署」（原型 2063–2071）：已下线 / 异常的模型一次性上线 */
  function startDeployAll(): number {
    let n = 0
    models.forEach((m) => {
      if (m.status === 'offline' || m.status === 'degraded') {
        startDeploy(m.id)
        n++
      }
    })
    if (!n) ui.pushHtml('当前没有需要上线的模型')
    return n
  }

  /** 下线（原型 2022–2029）：状态改 offline、水位归零，QPS 置 '—' */
  function offlineModel(id: string): void {
    const m = byId(id)
    if (!m) return
    m.status = 'offline'
    m.load = 0
    m.qps = '—'
    touch()
    ui.pushHtml(`<b>${esc(m.name)}</b> 已下线，正在回收 ${esc(m.res)}`)
  }

  /** 压测（原型 2018–2021）：只下发任务并提示，不改数据 */
  function probe(id: string): void {
    const m = byId(id)
    if (!m) return
    ui.pushText(`已下发压测任务 ${m.name}`, ['并发 32 · 时长 60s · 采样 P50 / P95 / 错误率'])
  }

  /* ---------------------------------------------------------------- 心跳 */
  let beatTimer: number | null = null

  /**
   * 模型页那一拍（原型 5280–5309）：只抖动已在线模型的数值，不重建卡片。
   * load ±2（夹在 8–96）、calls 累加 4–30，18% 概率刷新 p95 与错误率。
   * 原型用 `R.page === 'models'` 把关；Vue 里由 composables/useHeartbeat.ts
   * 按当前页调这一拍，所以这里不再判断页面。
   */
  function beat(): void {
    let changed = false
    models.forEach((m) => {
      if (m.status !== 'deployed') return
      m.load = clamp(m.load + rand(-2, 2), 8, 96)
      m.calls += rand(4, 30)
      if (Math.random() < 0.18) {
        m.p95 = rand(240, 520) + ' ms'
        m.err = (rand(4, 20) / 100).toFixed(2) + '%'
      }
      changed = true
    })
    /* load / calls / p95 / err 变了：KPI 与卡片上的水位、调用量要跟着更新 */
    if (changed) touch()
  }

  /**
   * 起停心跳。实际调度由 composables/useHeartbeat.ts 统一负责
   * （它按当前页调 models.beat()，间隔 1800ms / 减少动效时 2600ms，
   * 并对齐了原型的 visibilitychange 行为）；这里保留一对自持定时器的入口，
   * 方便脱离外壳单独跑这一页。两者只择其一，别同时开。
   */
  function startBeat(): void {
    stopBeat()
    beatTimer = window.setInterval(beat, MOD_BEAT_EVERY)
    ui.registerTimer(beatTimer)
  }

  function stopBeat(): void {
    if (beatTimer !== null) {
      window.clearInterval(beatTimer)
      beatTimer = null
    }
  }

  return {
    list,
    models,

    q,
    filter,
    type,
    setQuery,
    setFilter,
    setType,

    filtered,
    counts,
    countText,
    types,
    statusCounts,
    deployedCount,
    deployingCount,
    degradedCount,
    offlineCount,
    kpi,

    byId,
    modCfg,
    stChipText,
    stVar,
    quotaText,
    fromText,
    callsText,
    canDeploy,
    deployTxt,

    startDeploy,
    startDeployAll,
    stopDeploy,
    offlineModel,
    probe,

    beat,
    startBeat,
    stopBeat,
    touch,

    fmtNum,
  }
})