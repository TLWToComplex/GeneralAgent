/* ============================================================================
   工作台 store —— 会话调度（工位平面 / 卡片视图 / 表格视图）

   等价迁移自原型 console.js 的这几处：
     · 243–255   R 运行时状态（视图 / 筛选 / 搜索 / 选中 / 巡航 / 缩放平移）
     · 493–509   isVis() / hits()         筛选与排序
     · 510–522   updateCounts()           状态计数
     · 1178–1204 countStates / avgGpu / allLogs / warnLogs
     · 5205–5397 beat()                   模拟心跳：任务 / 进度 / 资源 / 日志

   ⚠️ 原型的 SESSIONS 是「模块级数组 + 直接 mutate」，心跳每 1.8 秒改一次字段。
   Vue 里必须让这些字段是响应式的，所以 store 持有一份 structuredClone 出来的副本。
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import {
  SESSIONS as SEED_SESSIONS,
  ST,
  SORDER,
  LOGS,
  PHASES,
  logLine,
  fillMsg,
} from '@/data/sessions'
import type { Session, SessionState, LogLine, SName } from '@/data/sessions'
import { clamp, esc, fmtDur, pick, rand, trunc } from '@/lib/util'
import { useUiStore } from '@/stores/ui'

/** 工作台的三种视图（原型 switchView 的参数） */
export type WorkbenchView = 'floor' | 'cards' | 'list'

/** 平面默认视口：默认放大到 180%（原型 FLOOR_ZOOM），下限 60%、上限 200% */
export const FLOOR_ZOOM = 1.8
export const FLOOR_ZOOM_MIN = 0.6
export const FLOOR_ZOOM_MAX = 2
/** 气泡宽 / 高 / 上沿距工位中心 */
export const BUB = { w: 148, h: 47, off: 100 }
/** viewBox：紧贴内容包围盒 */
export const VB = { w: 1344, h: 752, cx: 672, cy: 376 }

export const useSessionStore = defineStore('session', () => {
  const ui = useUiStore()

  /** 可变的会话副本（心跳会改它，所以不能直接用 data 里的只读数组） */
  const sessions: Session[] = structuredClone(SEED_SESSIONS) as Session[]
  const list = shallowRef<Session[]>(sessions)

  /* ---------------------------------------------------------------- 视图状态 */
  const view = ref<WorkbenchView>('floor')
  const filter = ref<SName>('all')
  const query = ref('')
  const selId = ref<string | null>(null)
  /** 自动巡航开关（工位视图下按固定节奏轮播选中态） */
  const cruise = ref(true)
  /**
   * 巡航选中的会话 id。
   * 原型 5150–5166 把 `cruiseId` 与 `selId` 一起当「巡航轮播游标」用，
   * 存的是会话 id（字符串）—— 不是定时器句柄（那个叫 cruiseTimer）。
   */
  const cruiseId = ref<string | null>(null)
  /** 当前命中的会话（筛选 + 排序后的结果） */
  const hits = ref<Session[]>([])

  /* ---------------------------------------------------------------- 平面相机 */
  const zoom = ref(FLOOR_ZOOM)
  /**
   * 平移量，单位是**屏幕像素**。
   * 内容水平中心 = 672 = VB.cx，所以 pan=(0,0) 在任何缩放下都是居中的。
   */
  const pan = ref({ x: 0, y: 0 })

  function setZoom(z: number): void {
    zoom.value = Math.round(clamp(z, FLOOR_ZOOM_MIN, FLOOR_ZOOM_MAX) * 1000) / 1000
  }

  function setPan(x: number, y: number): void {
    pan.value = { x, y }
  }

  function resetView(): void {
    setZoom(FLOOR_ZOOM)
    setPan(0, 0)
  }

  /** 视图切换（原型 switchView 591–602）：工位 / 卡片 / 表格 */
  function setView(v: WorkbenchView): void {
    view.value = v
  }

  /* ---------------------------------------------------------------- 筛选 */
  function isVis(s: Session): boolean {
    if (filter.value !== 'all' && s.state !== filter.value) return false
    if (query.value) {
      const q = query.value.toLowerCase()
      const hay = `${s.name} ${s.agent} ${s.ws} ${s.id} ${s.task} ${s.owner}`.toLowerCase()
      if (hay.indexOf(q) < 0) return false
    }
    return true
  }

  /** 原型 hits()：按状态优先级排序，同状态按原始序号 */
  const filtered = computed<Session[]>(() =>
    list.value
      .filter(isVis)
      .slice()
      .sort((m, n) => SORDER[m.state] - SORDER[n.state] || m.idx - n.idx),
  )

  /** 状态计数（原型 updateCounts 的 c 对象 + countStates） */
  const counts = computed(() => {
    const c: Record<SName, number> = { all: 0, running: 0, queue: 0, idle: 0, warn: 0, fail: 0 }
    sessions.forEach((s) => {
      if (!isVis(s)) return
      c.all++
      c[s.state]++
    })
    return c
  })

  /** 全量状态计数（不受筛选影响，指标条用） */
  const countsAll = computed(() => {
    const c: Record<SessionState, number> = { running: 0, queue: 0, idle: 0, warn: 0, fail: 0 }
    sessions.forEach((s) => {
      c[s.state]++
    })
    return c
  })

  /** 平均显存水位（原型 avgGpu） */
  const avgGpu = computed(() => {
    let sum = 0
    sessions.forEach((s) => {
      sum += s.gpuPct
    })
    return sum / (sessions.length || 1)
  })

  function setFilter(f: SName): void {
    filter.value = f
  }

  function setQuery(q: string): void {
    query.value = q
    if (ui.query !== q) ui.query = q
  }

  function byId(id: string | null): Session | null {
    if (!id) return null
    return sessions.find((s) => s.id === id) ?? null
  }

  function selectSession(id: string | null): void {
    selId.value = id
    if (cruiseId.value !== null) cruiseId.value = null
  }

  /* ---------------------------------------------------------------- 日志汇总 */
  function allLogs(n: number): LogLine[] {
    const out: LogLine[] = []
    sessions.forEach((s) => {
      s.logs.slice(-6).forEach((l) => {
        out.push({ t: l.t, lvl: l.lvl, m: `[${s.code}] ${l.m}` })
      })
    })
    out.sort((a, b) => (a.t < b.t ? 1 : -1))
    return out.slice(0, n)
  }

  function warnLogs(n: number): LogLine[] {
    const out: LogLine[] = []
    sessions.forEach((s) => {
      if (s.state === 'warn' || s.state === 'fail') {
        s.logs.forEach((l) => {
          out.push({ t: l.t, lvl: l.lvl, m: `[${s.code} ${s.agent}] ${l.m}` })
        })
      }
    })
    return out.slice(-n)
  }

  /* ---------------------------------------------------------------- 抽屉里的三个操作 */
  function enterSession(id: string): void {
    const s = byId(id)
    if (!s) return
    ui.pushText(`正在进入 ${s.name}`, [`workspace：${s.ws}`, `智能体：${s.agent} · 会话 ${s.id}`])
  }

  function pauseSession(id: string): void {
    const s = byId(id)
    if (!s) return
    s.state = 'idle'
    s.task = '已由人工暂停，工位挂起'
    s.gpuPct = rand(2, 8)
    s.logs.push(logLine('warn', '人工暂停，正在回收 GPU 资源'))
    touch()
    ui.pushHtml(`会话 <b>${esc(s.name)}</b> 已暂停`)
  }

  function restartSession(id: string): void {
    const s = byId(id)
    if (!s) return
    s.state = 'queue'
    s.prog = 0
    s.gpuPct = 0
    s.task = '重启中，等待调度器重新分配工位'
    s.logs.push(logLine('info', '收到重启指令，镜像层重新校验'))
    touch()
    ui.pushHtml(`会话 <b>${esc(s.name)}</b> 已重启，进入排队`)
  }

  /** 通知响应式系统「内部字段变了」（原型是直接 mutate DOM） */
  function touch(): void {
    list.value = sessions.slice()
  }

  /* ---------------------------------------------------------------- 心跳 */
  let beatTimer: number | null = null
  let lastTick = Date.now()
  /** 原型用 stateDirty 决定这一拍要不要整体重排 */
  const stateDirty = ref(false)

  /**
   * 心跳：任务 / 进度 / 资源 / 日志。
   * 只改字段，DOM 由 Vue 的响应式负责 —— 原型里那套「只 patch [data-role] 节点」
   * 的优化在虚拟 DOM 下不再需要。
   */
  function beat(): void {
    const now = Date.now()
    const dt = Math.max(1, Math.min(6, Math.round((now - lastTick) / 1000)))
    lastTick = now
    let dirty = false

    sessions.forEach((s) => {
      if (s.state === 'running') {
        s.elapsed += dt
        s.prog = clamp(s.prog + rand(0, 2), 4, 99)
        s.gpuPct = clamp(s.gpuPct + rand(-3, 3), 22, 97)
        if (Math.random() < 0.55) {
          s.task = `${pick(PHASES)}，已完成 ${s.prog}%`
          s.logs.push(logLine('info', fillMsg(pick(LOGS.running)[1])))
          if (s.logs.length > 40) s.logs.splice(0, s.logs.length - 40)
        }
        if (s.prog >= 99 && Math.random() < 0.3) {
          s.state = 'idle'
          s.prog = 100
          s.task = '本轮任务已交付，工位待命'
          s.gpuPct = rand(2, 9)
          s.logs.push(logLine('ok', '任务完成，产物已分发，工位回到空闲池'))
          dirty = true
          /* 让一个排队会话顶上这个工位 */
          const q = sessions.find((x) => x.state === 'queue')
          if (q) {
            q.state = 'running'
            q.prog = rand(4, 12)
            q.gpuPct = rand(30, 56)
            q.task = `已分配到 #${s.code} 工位，初始化运行环境`
            q.logs.push(logLine('ok', '调度器分配 GPU，工位就绪，开始执行'))
            ui.pushHtml(`会话 <b>${esc(q.name)}</b> 已调度执行`)
          }
        }
      } else if (s.state === 'queue' && Math.random() < 0.14) {
        s.state = 'running'
        s.prog = rand(4, 12)
        s.gpuPct = rand(28, 54)
        s.task = '已分配到工位，正在初始化运行环境'
        s.logs.push(logLine('ok', '调度器分配 GPU，工位就绪，开始执行'))
        dirty = true
      } else if (s.state === 'warn' && Math.random() < 0.09) {
        s.state = 'running'
        s.gpuPct = clamp(s.gpuPct - rand(6, 16), 30, 80)
        s.task = '批量尺寸回退完成，恢复满速运行'
        s.logs.push(logLine('ok', fillMsg(LOGS.warn[2][1]).replace('重试第 ', '回退重试第 ')))
        dirty = true
      }
    })

    if (Math.random() < 0.12) ui.distToday++

    stateDirty.value = dirty
    /* 状态变了就整体重排（list 换新数组触发响应式），否则只靠字段变更原地更新 */
    if (dirty) touch()
    hits.value = filtered.value
  }

  function startBeat(): void {
    stopBeat()
    lastTick = Date.now()
    beatTimer = window.setInterval(beat, 1800)
    ui.registerTimer(beatTimer)
  }

  function stopBeat(): void {
    if (beatTimer !== null) {
      window.clearInterval(beatTimer)
      beatTimer = null
    }
  }

  /** 原型 startBeat 里 clearInterval 的那一步，登出时也要能整体停掉 */
  function restartBeat(): void {
    startBeat()
  }

  /** 派生给视图用：把气泡文案切两行（原型 setBubble） */
  function bubbleLines(s: Session): [string, string] {
    const [a, b] = [s.task.slice(0, 10), s.task.length > 10 ? trunc(s.task.slice(10), 10) : '']
    return [a, b]
  }

  return {
    list,
    sessions,

    view,
    filter,
    query,
    selId,
    cruise,
    cruiseId,
    zoom,
    pan,
    hits,

    filtered,
    counts,
    countsAll,
    avgGpu,

    setZoom,
    setPan,
    resetView,
    setView,
    setFilter,
    setQuery,
    byId,
    selectSession,
    isVis,

    allLogs,
    warnLogs,
    enterSession,
    pauseSession,
    restartSession,

    beat,
    startBeat,
    stopBeat,
    restartBeat,
    stateDirty,

    bubbleLines,
    fmtDur,
    ST,
  }
})