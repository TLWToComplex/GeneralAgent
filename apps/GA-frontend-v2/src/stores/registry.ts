/* ============================================================================
   镜像中心 store —— 镜像清单（状态 / 版本 / digest / 多地域复制）+ 同步演示

   等价迁移自原型 console.js 的这几处：
     · 1313–1322  REG / RSTATES / Reg（页面 UI 状态：filter / repo / q）
     · 1484–1492  sizeToMB / fmtGB               体积字符串与「总占用」的换算
     · 1494–1515  updateRegKpis()                顶栏四张统计卡
     · 1518–1557  regHits / regCfg / regCounts / updateRegCounts   筛选与计数
     · 1559–1620  renderRegCards()               卡片渲染（结构交给组件，这里定口径）
     · 1622–1652  regSyncTimers / startRegSync() 同步演示（620ms 推进到 100%）
     · 1676–1719  bindRegistry()                 状态胶囊 / 仓库下拉 / 页内搜索 / 同步全部
     · 5264–5279  beat() 里镜像页那一拍          只累加 pulls，不重建卡片

   ⚠️ 原型的 IMAGES 是「模块级数组 + 直接 mutate」：同步定时器会不停改 prog / status，
   心跳每 1.8 秒改 pulls。Vue 里必须让这些字段是响应式的，所以 store 持有一份
   structuredClone 出来的副本，用 shallowRef + touch() 触发更新（与 stores/session.ts
   同样的做法）。卡片按 id 复用 DOM，重排不会打断 hover / 滚动。
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import { IMAGES as SEED_IMAGES, REG, RSTATES } from '@/data/registry'
import type { ImageStatus, RegMeta, RegState, RegistryImage } from '@/data/registry'
import { clamp, esc, rand } from '@/lib/util'
import { useUiStore } from '@/stores/ui'

/* 原型的 REG / RSTATES 是页面级常量，组件（状态胶囊、卡片徽标）也要用，直接透出 */
export { REG, RSTATES }

/** 同步演示的推进间隔（原型 1651 行的 620ms） */
export const REG_SYNC_EVERY = 620
/** 列表页心跳间隔（原型 5463 行的 1800ms） */
export const REG_BEAT_EVERY = 1800
/** 页内搜索与顶栏搜索的防抖时长（原型 1698–1705 / 5755–5761 的 160ms） */
export const REG_SEEK_DEBOUNCE = 160

/** 状态基色（原型 1573–1574 的三目链，写进卡片的 --st） */
export const REG_ST: Record<ImageStatus, string> = {
  syncing: 'var(--azure)',
  failed: 'var(--coral)',
  outdated: 'var(--gold)',
  synced: 'var(--slate)',
}

/** 体积字符串 → MB（原型 1484–1489，"1.42 GB" / "512 MB"） */
export function sizeToMB(s: string): number {
  const mm = String(s).match(/([\d.]+)\s*(GB|MB)/i)
  if (!mm) return 0
  const n = parseFloat(mm[1])
  return /gb/i.test(mm[2]) ? Math.round(n * 1024) : Math.round(n)
}

/** MB → "1.4 GB" / "512 MB"（原型 1490–1492，保留一位小数） */
export function fmtGB(mb: number): string {
  return mb >= 1024 ? (mb / 1024).toFixed(1) + ' GB' : mb + ' MB'
}

export const useRegistryStore = defineStore('registry', () => {
  const ui = useUiStore()

  /** 可变的镜像副本（同步定时器与心跳会改它，所以不能直接用 data 里的种子数组） */
  const images: RegistryImage[] = structuredClone(SEED_IMAGES) as RegistryImage[]
  const list = shallowRef<RegistryImage[]>(images)

  /* ---------------------------------------------------------------- 页面 UI 状态 */
  /** 状态胶囊（原型 Reg.filter） */
  const filter = ref<RegState>('all')
  /** 来源仓库下拉（原型 Reg.repo，'all' 为全部） */
  const repo = ref('all')
  /** 页内 / 顶栏搜索词（原型 Reg.q，两端都是 160ms 防抖后写进来） */
  const q = ref('')

  function setFilter(f: RegState): void {
    filter.value = f
  }

  function setRepo(r: string): void {
    repo.value = r
  }

  function setQuery(v: string): void {
    // 原型 `Reg.q = rs.value.trim()`（1701 行）：存进来的永远是去空格的值
    q.value = v.trim()
    if (ui.query !== q.value) ui.query = q.value
  }

  function byId(id: string | null): RegistryImage | null {
    if (!id) return null
    return images.find((m) => m.id === id) ?? null
  }

  /** 通知响应式系统「内部字段变了」（原型是直接 mutate DOM） */
  function touch(): void {
    list.value = images.slice()
  }

  /* ---------------------------------------------------------------- 筛选 */
  /** 原型 regHits / regCounts 里共用的搜索串（1523–1524 / 1541–1542） */
  function hay(m: RegistryImage): string {
    return (
      `${m.name} ${m.ns} ${m.repo} ${m.digest} ${m.base} ` +
      m.tags.map((t) => t.v).join(' ')
    ).toLowerCase()
  }

  /** byState=false 时忽略状态胶囊（算计数用），仓库与关键词始终生效 */
  function isVis(m: RegistryImage, byState: boolean): boolean {
    if (byState && filter.value !== 'all' && m.status !== filter.value) return false
    if (repo.value !== 'all' && m.repo !== repo.value) return false
    if (q.value && hay(m).indexOf(q.value.toLowerCase()) < 0) return false
    return true
  }

  /** 卡片列表（原型 regHits 1518–1529）：状态 + 仓库 + 关键词，**保持原始顺序** */
  const filtered = computed<RegistryImage[]>(() => list.value.filter((m) => isVis(m, true)))

  /**
   * 胶囊上的五个计数（原型 regCounts 1536–1548）。
   * 注意口径：**忽略状态胶囊本身**，只受仓库下拉与关键词影响 —— 这样切状态时
   * 各胶囊上的数字不会跟着塌成 0。
   */
  const counts = computed<Record<RegState, number>>(() => {
    const c: Record<RegState, number> = { all: 0, synced: 0, outdated: 0, syncing: 0, failed: 0 }
    list.value.forEach((m) => {
      if (!isVis(m, false)) return
      c.all++
      c[m.status]++
    })
    return c
  })

  /** 页头「N 个镜像」（原型 updateRegCounts 1556） */
  const countText = computed(() => `${counts.value.all} 个镜像`)

  /**
   * 来源仓库去重列表（原型 1496 / 1503 的 repos 对象）。
   * HTML 里 #regRepo 是三个写死的 option（console.html 256–263），
   * 这里改为从数据按首次出现顺序去重派生，顺序与原型的 option 完全一致。
   */
  const repos = computed<string[]>(() => {
    const out: string[] = []
    list.value.forEach((m) => {
      if (out.indexOf(m.repo) < 0) out.push(m.repo)
    })
    return out
  })

  /** 全量状态计数（不受任何筛选影响，KPI 口径） */
  const statusCounts = computed<Record<ImageStatus, number>>(() => {
    const c: Record<ImageStatus, number> = { synced: 0, outdated: 0, syncing: 0, failed: 0 }
    list.value.forEach((m) => {
      c[m.status]++
    })
    return c
  })

  const syncedCount = computed(() => statusCounts.value.synced)
  const outdatedCount = computed(() => statusCounts.value.outdated)
  const syncingCount = computed(() => statusCounts.value.syncing)
  const failedCount = computed(() => statusCounts.value.failed)

  /**
   * 顶栏四张统计卡（原型 updateRegKpis 1494–1515）。
   * 口径是全量镜像，与筛选无关；文案与单位必须与原型一致：
   *   「总占用」是 GB/MB 字符串，「次拉取」≥1000 折成一位小数的 k。
   */
  const kpi = computed(() => {
    let total = 0
    let tags = 0
    let syncing = 0
    let todo = 0
    let mb = 0
    let layers = 0
    let pulls = 0
    list.value.forEach((m) => {
      total++
      tags += m.tags.length
      mb += sizeToMB(m.tags[0].size)
      layers += m.layers
      pulls += m.pulls
      if (m.status === 'syncing') syncing++
      if (m.status === 'outdated' || m.status === 'failed') todo++
    })
    return {
      /** 个镜像 */
      total,
      /** 个标签 */
      tags,
      /** 同步中 */
      syncing,
      /** 待更新 / 失败 */
      todo,
      /** 总占用（fmtGB） */
      sizeText: fmtGB(mb),
      /** 层可复用 */
      layers,
      /** 来源仓库 */
      repoCount: repos.value.length,
      /** 次拉取 */
      pullText: pulls >= 1000 ? (pulls / 1000).toFixed(1) + 'k' : String(pulls),
    }
  })

  /* ---------------------------------------------------------------- 卡片取值 */
  /** 状态徽标文案与类名（原型 regCfg 1530–1535） */
  function regCfg(m: RegistryImage): RegMeta {
    if (m.status === 'syncing') return REG.syncing
    if (m.status === 'failed') return REG.failed
    if (m.status === 'outdated') return REG.outdated
    return REG.synced
  }

  /** 卡片右侧那行 delta 文案（原型 1606–1608，同步中显示进度） */
  function deltaText(m: RegistryImage): string {
    return m.status === 'syncing'
      ? `同步进度 ${m.prog}%`
      : `${m.pulls} 次拉取 · 最近 ${m.ago}`
  }

  /** 「同步」按钮是否可点（原型 1580：只有待更新 / 失败可同步） */
  function canSync(m: RegistryImage): boolean {
    return m.status === 'outdated' || m.status === 'failed'
  }

  /* ---------------------------------------------------------------- 同步演示 */
  /** 每张镜像的同步定时器（原型 regSyncTimers 1623，用 id 作键） */
  const syncTimers = new Map<string, number>()

  function stopSync(id: string): void {
    const t = syncTimers.get(id)
    if (t !== undefined) {
      window.clearInterval(t)
      syncTimers.delete(id)
    }
  }

  /**
   * 原型 startRegSync(m)（1624–1652）：
   *   起手 status=syncing / prog=8 / ago='同步中'，620ms 推进一次
   *   （clamp(prog + rand(9,22), 8, 100)），到 100% 变 synced、prog=100、ago='刚刚'。
   * 原型在推进过程中只改这一张卡的进度条与 delta 文案（1644–1650）；
   * Vue 里一次 touch() 就够 —— 卡片按 id 复用 DOM，不会打断 hover / 滚动。
   */
  function startSync(id: string): void {
    const m = byId(id)
    if (!m) return
    if (m.status === 'syncing') return
    m.status = 'syncing'
    m.prog = 8
    m.ago = '同步中'
    touch()
    ui.pushHtml(
      `开始同步 <b>${esc(m.name)}:${esc(m.tags[0].v)}</b> · 目标 ${esc(m.copies.join(' / '))}`,
    )

    stopSync(m.id)
    const t = window.setInterval(() => {
      m.prog = clamp(m.prog + rand(9, 22), 8, 100)
      if (m.prog >= 100) {
        stopSync(m.id)
        m.status = 'synced'
        m.prog = 100
        m.ago = '刚刚'
        touch()
        ui.pushHtml(`<b>${esc(m.name)}</b> 同步完成，已在 ${esc(m.copies.join(' / '))} 就绪`)
        return
      }
      touch()
    }, REG_SYNC_EVERY)
    syncTimers.set(m.id, t)
    /* 登记到 ui store：退出登录能一次性 clearInterval 掉 */
    ui.registerTimer(t)
  }

  /** 「同步全部」（原型 1710–1719）：待更新 / 失败的镜像一次性排队 */
  function startSyncAll(): number {
    let n = 0
    images.forEach((m) => {
      if (m.status === 'outdated' || m.status === 'failed') {
        startSync(m.id)
        n++
      }
    })
    if (!n) ui.pushHtml('当前没有待同步的镜像')
    return n
  }

  /* ---------------------------------------------------------------- 心跳 */
  let beatTimer: number | null = null

  /**
   * 镜像页那一拍（原型 5264–5279）：只累加 pulls，不重建卡片。
   * 原型用 `R.page === 'registry'` 把关；Vue 里由 composables/useHeartbeat.ts
   * 按当前页调这一拍，所以这里不再判断页面。
   * 原型先刷 KPI 再改 pulls（统计永远慢一拍），Vue 的 computed 天然是同步的，
   * 这里不刻意保留那一拍延迟。
   */
  function beat(): void {
    let changed = false
    images.forEach((m) => {
      if (m.status !== 'syncing' && Math.random() < 0.2) {
        m.pulls += rand(1, 3)
        changed = true
      }
    })
    /* pulls 变了：KPI 的「次拉取」与卡片 delta 文案都要跟着更新 */
    if (changed) touch()
  }

  /**
   * 起停心跳。实际调度由 composables/useHeartbeat.ts 统一负责
   * （它按当前页调 registry.beat()，间隔 1800ms / 减少动效时 2600ms，
   * 并对齐了原型的 visibilitychange 行为）；这里保留一对自持定时器的入口，
   * 方便脱离外壳单独跑这一页。两者只择其一，别同时开。
   */
  function startBeat(): void {
    stopBeat()
    beatTimer = window.setInterval(beat, REG_BEAT_EVERY)
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
    images,

    q,
    filter,
    repo,
    setQuery,
    setFilter,
    setRepo,

    filtered,
    counts,
    countText,
    repos,
    statusCounts,
    syncedCount,
    outdatedCount,
    syncingCount,
    failedCount,
    kpi,

    byId,
    regCfg,
    deltaText,
    canSync,

    startSync,
    startSyncAll,
    stopSync,

    beat,
    startBeat,
    stopBeat,
    touch,
  }
})