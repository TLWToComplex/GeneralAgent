/* ============================================================================
   网关 store —— 反代（proxy）+ dsh 容器实例（dsh-new.sh）

   等价迁移自原型 console.js 的这几处：
     · 3446–3487  Gw 状态、gwData / gwById / gwKindOf / gwHay / gwFiltered / gwCounts
     · 3490–3546  renderGwKpis / updateGwKpis   指标条
     · 3549–3640  gwActions / gwHead / gwBands  卡片的三档信息带
     · 3689–3927  gwCols                        明细表的列定义
     · 3929–4104  renderGwViz                   三块可视化（流量 / 就绪环形 / 水位）
     · 4106–4157  renderOpsGrid（网关分支）      tab 徽标、页头计数、空态
     · 4446–4610  opsFormOpen / gwFormSubmit    新增 / 编辑
     · 4784–4850  gwPing 巡检 / handleOpsAction 启用停用
     · 4853–4883  askOpsDelete / doOpsDelete    删除
     · 5362–5386  心跳里的网关分支

   数据模型对齐真实部署（见 dsh-plugin/proxy/server.js 与
   docker/dsh-docker/dsh-new.sh），字段含义见各 interface 的注释。
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ACCESSLOGS, GWALERTS, GWROUTES, GWUPS, GWTABS } from '@/data/gateway'
import type { GwAlert, GwLog, GwRoute, GwRow, GwStatus, GwTab, GwUp } from '@/data/gateway'
import { clamp, esc, rand } from '@/lib/util'
import { series } from '@/lib/viz'
import { useUiStore } from '@/stores/ui'
import { useOverlayStore } from '@/stores/overlay'

/** 告警严重度的分类色（家族色 .mfamily is-*） */
export const GW_SEV: Record<string, string> = {
  'P1 严重': 'is-asr',
  'P2 警告': 'is-rerank',
  'P3 提示': 'is-llm',
}


/** 表单回填模型（由 store 的 formModel() 派生） */
export type GwFormModel = {
  isAlert: boolean
  gwAlertName: string
  gwTarget: string
  gwCond: string
  gwSev: string
  gwName: string
  gwContainer: string
  gwPort: string
  gwToken: string
  gwCache: string
  gwLimit: string
  gwFuse: string
  gwNotice: string
  gwStatus: GwStatus
}

export const useGatewayStore = defineStore('gateway', () => {
  const ui = useUiStore()
  const overlay = useOverlayStore()

  /* ---------------------------------------------------------------- 可变副本 */
  const routes = ref<GwRoute[]>(structuredClone(GWROUTES) as GwRoute[])
  const ups = ref<GwUp[]>(structuredClone(GWUPS) as GwUp[])
  const alerts = ref<GwAlert[]>(structuredClone(GWALERTS) as GwAlert[])
  const logs = ref<GwLog[]>(structuredClone(ACCESSLOGS) as GwLog[])

  /* ---------------------------------------------------------------- UI 状态 */
  const tab = ref<GwTab>('gwroute')
  const filter = ref<'all' | GwStatus>('all')
  /** 入口源筛选（原型叫 cluster，值域是 entry + 各容器的监听地址） */
  const cluster = ref<'all' | string>('all')
  const q = ref('')
  /** 新建时的自增序号 */
  let seq = 0

  function setTab(t: GwTab): void {
    tab.value = t
    filter.value = 'all'
    q.value = ''
    cluster.value = 'all'
  }

  function setQuery(v: string): void {
    q.value = v
    if (ui.query !== v) ui.query = v
  }

  /** 状态筛选条（原型 data-gwst） */
  function setFilter(f: 'all' | GwStatus): void {
    filter.value = f
  }

  /** 入口源下拉（原型 #gwCluster） */
  function setCluster(c: string): void {
    cluster.value = c
  }

  /* ---------------------------------------------------------------- 查询 */
  function dataOf(t: GwTab): readonly GwRow[] {
    if (t === 'gwroute') return routes.value
    if (t === 'gwup') return ups.value
    if (t === 'gwalert') return alerts.value
    return logs.value
  }

  const allRows = computed<GwRow[]>(() => [
    ...routes.value,
    ...ups.value,
    ...alerts.value,
    ...logs.value,
  ])

  function byId(id: string | null): GwRow | null {
    if (!id) return null
    return allRows.value.find((g) => g.id === id) ?? null
  }

  /** 编辑时判断该走「用户路由」还是「告警规则」表单（容器与日志没有独立表单） */
  function kindOf(id: string | null): 'gwroute' | 'gwalert' {
    return byId(id)?.tab === 'gwalert' ? 'gwalert' : 'gwroute'
  }

  /** 全字段拼串，供搜索匹配 */
  function hay(g: GwRow): string {
    return Object.keys(g)
      .map((k) => String((g as unknown as Record<string, unknown>)[k]))
      .join(' ')
      .toLowerCase()
  }

  /** 原型 gwFiltered(byState)：byState=false 时忽略状态胶囊（用于算计数） */
  function filteredOf(byState: boolean): GwRow[] {
    return dataOf(tab.value).filter((g) => {
      if (byState && filter.value !== 'all') {
        if (g.status !== filter.value) return false
      }
      /* 入口源筛选：两类值同处一个下拉 —— 用户路由看「入口源」(entry)，
         容器实例看「监听地址」(addr / cluster)，两个字段都试一次。 */
      const gAny = g as unknown as Record<string, unknown>
      const pick = [gAny.entry, gAny.cluster, gAny.addr, gAny.hop]
      if (cluster.value !== 'all' && pick.indexOf(cluster.value) < 0) return false
      if (q.value && hay(g).indexOf(q.value.toLowerCase()) < 0) return false
      return true
    })
  }

  const filtered = computed<GwRow[]>(() => filteredOf(true))

  /** 状态计数（胶囊上的数字） */
  const counts = computed(() => {
    const c = { all: 0, ok: 0, warn: 0, off: 0 }
    filteredOf(false).forEach((g) => {
      c.all++
      if (g.status === 'ok') c.ok++
      else if (g.status === 'warn') c.warn++
      else c.off++
    })
    return c
  })

  /** tab 徽标 */
  const tabCounts = computed(() => ({
    gwroute: routes.value.length,
    gwup: ups.value.length,
    gwalert: alerts.value.length,
    gwlog: logs.value.length,
  }))

  /** 页头汇总文案 */
  const headCount = computed(
    () =>
      `${routes.value.length} 条用户路由 · ${ups.value.length} 个容器实例 · ` +
      `${alerts.value.length} 条告警规则`,
  )

  /** 新建按钮文案（容器页与日志页退回新建用户路由） */
  const newLabel = computed(() =>
    tab.value === 'gwalert' ? '新建告警规则' : `新建${GWTABS[tab.value].item}`,
  )

  /** 页内搜索框占位 */
  const seekPlaceholder = computed(() => GWTABS[tab.value].ph)

  /** 入口源下拉的选项：用户路由的 entry + 容器的监听地址（去重） */
  const clusters = computed<string[]>(() => {
    const out: string[] = []
    routes.value.forEach((g) => {
      if (g.entry && out.indexOf(g.entry) < 0) out.push(g.entry)
    })
    ups.value.forEach((g) => {
      if (g.cluster && out.indexOf(g.cluster) < 0) out.push(g.cluster)
    })
    return out
  })

  /* ---------------------------------------------------------------- KPI */
  const kpis = computed(() => {
    let qps = 0
    let ms = 0
    let n = 0
    let err = 0
    let cn = 0
    let cacheN = 0
    routes.value.forEach((r) => {
      if (r.status === 'off') return
      const qv = parseFloat(r.requests) || 0
      qps += (qv * (r.requests && /k$/.test(r.requests) ? 1000 : 1)) / 1000 /* 千次/日 折算 */
      if (/缓存命中|已落盘/.test(r.session + r.cache)) cacheN++
      const m = parseInt(r.p95, 10)
      if (!isNaN(m)) {
        ms += m
        n++
      }
      const e = parseFloat(r.err)
      if (!isNaN(e)) {
        err += e
        cn++
      }
    })
    const alertsOn = alerts.value.filter((a) => a.status === 'warn').length
    const ready = ups.value.filter((u) => u.status === 'ok').length
    return {
      /** 今日已鉴权请求 */
      req: `${(189 + qps / 10).toFixed(1)}w`,
      /** 命中会话缓存 'N / M 条' */
      cacheHit: `${cacheN} / ${routes.value.filter((r) => r.status !== 'off').length} 条`,
      /** 反代成功率 */
      ok: `${(100 - err / (cn || 1)).toFixed(2)}%`,
      /** 5xx 占比 */
      err: `${(err / (cn || 1)).toFixed(2)}%`,
      /** 反代平均 P95 */
      p95: `${Math.round(ms / (n || 1))} ms`,
      /** 已有映射的用户数 */
      routeOk: routes.value.filter((r) => r.status === 'ok').length,
      /** 活跃告警 */
      alert: alertsOn,
      /** 已就绪容器 */
      up: ready,
      upAll: ups.value.length,
    }
  })

  /* ---------------------------------------------------------------- 可视化 */
  /** 反代流量曲线（原型 3933–3935 的三条 series） */
  const flow = computed(() => {
    const qps = series(9173, 60, 26, 92, 0.3)
    const p95 = series(4421, 60, 18, 74, 0.26)
    const err = series(8811, 60, 4, 26, 0.4)
    const peak = Math.max(...qps)
    const avg = qps.reduce((a, b) => a + b, 0) / qps.length
    return {
      w: 600,
      h: 150,
      qps,
      p95,
      err,
      /** 峰值文案（原型 3957：peak / 100 * 4.4 k 请求/min） */
      peakText: `${((peak / 100) * 4.4).toFixed(1)}k 请求/min`,
      avgText: `${((avg / 100) * 4.4).toFixed(1)}k 请求/min`,
      /** 曲线末点的 y 坐标（原型 3953–3954） */
      dotY: 8 + (150 - 16) - ((qps[qps.length - 1]! - 20) / 80) * (150 - 16),
    }
  })

  /** 会话与连接水位（原型 3972–3990 的四条 gmeter） */
  const meters = computed(() => {
    const liveN = routes.value.filter(
      (r) => r.status !== 'off' && /缓存命中/.test(r.session),
    ).length
    const liveAll = routes.value.filter((r) => r.status !== 'off').length || 1
    const sessionPct = Math.round((liveN / liveAll) * 100)

    /* 连接占用：所有未停容器里最紧的那个（原型 3979–3983） */
    let connPct = 0
    const alive = ups.value.filter((u) => u.status !== 'off')
    alive.forEach((u) => {
      const parts = String(u.conn).split('/')
      const cur = parseInt(parts[0] ?? '0', 10) || 0
      const max = parseInt(parts[1] ?? '1', 10) || 1
      connPct = Math.max(connPct, Math.round((cur / max) * 100))
    })

    const okN = ups.value.filter((u) => u.status === 'ok').length
    const goodPct = Math.round((okN / (ups.value.length || 1)) * 100)

    return [
      {
        t: '会话缓存命中',
        v: sessionPct,
        s: `${liveN} / ${liveAll} 条用户路由已落盘`,
      },
      {
        t: '容器连接占用',
        v: connPct,
        s: `峰值取自 ${alive.length} 个运行中的容器`,
      },
      {
        t: '容器就绪率',
        v: goodPct,
        s: '就绪判定：端口可连且首页返回 401',
      },
      {
        t: '令牌有效期',
        v: 100,
        s: '30 天签名 cookie · 容器重启需 refresh',
      },
    ].map((x) => ({
      ...x,
      /* 原型 3992：水位越高越危险，所以 ≥80 是 bad、≥60 是 warn */
      tone: x.v >= 80 ? 'bad' : x.v >= 60 ? 'warn' : 'ok',
    }))
  })

  /**
   * 反代流量曲线：入口请求 / 反代时延 / 5xx 占比。
   * 原型用确定性序列（同一份数据每次得到同一条曲线），这里沿用 series()。
   */
  const viz = computed(() => {
    const base = routes.value.reduce((s, r) => s + (parseFloat(r.requests) || 0), 0)
    const peak = Math.max(1, Math.round(base * 1.1))
    const avg = Math.max(1, Math.round(base * 0.72))
    const ready = ups.value.filter((u) => u.status === 'ok').length
    const warn = ups.value.filter((u) => u.status === 'warn').length
    const off = ups.value.filter((u) => u.status === 'off').length
    const readyPct = Math.round((ready / (ups.value.length || 1)) * 100)
    const cacheHitN = Number(kpis.value.cacheHit.split(' / ')[0]) || 0
    const cachePct = Math.round((cacheHitN / (routes.value.length || 1)) * 100)
    const connMax = ups.value.reduce((s, u) => {
      const cur = parseInt(String(u.conn).split('/')[0] ?? '0', 10) || 0
      return s + cur
    }, 0)
    const connCap = ups.value.reduce((s, u) => {
      const cap = parseInt(String(u.conn).split('/')[1] ?? '0', 10) || 0
      return s + cap
    }, 0)
    return {
      peak,
      avg,
      ready,
      warn,
      off,
      readyPct,
      cachePct,
      connPct: connCap ? Math.round((connMax / connCap) * 100) : 0,
      tokenLeft: 100 - Math.round((routes.value.filter((r) => /已过期|失效/.test(r.token)).length / (routes.value.length || 1)) * 100),
    }
  })

  /* ---------------------------------------------------------------- 表单 */
  /** 打开新增容器/日志时的兜底说明（这两类不能手工新建） */
  function formSub(mode: 'add' | 'edit'): string {
    const fallback = (tab.value === 'gwup' || tab.value === 'gwlog') && mode === 'add'
    if (fallback) {
      return tab.value === 'gwup'
        ? '容器实例由 dsh-new.sh 拉起后自动注册（端口只绑 127.0.0.1），这里改为新建一条用户路由指向它。'
        : '访问日志由代理运行时产生，不可手工新建。这里改为新建一条用户路由。'
    }
    return tab.value === 'gwalert'
      ? '规则由值班巡检统一评估，命中后按渠道通知，覆盖容器不可达、令牌失效、5xx 抬升等真实故障。'
      : '用户路由 = 代理侧 ROUTES[用户] → http://127.0.0.1:<端口>/，改动需与 dsh-new.sh 的端口一致。'
  }

  const formHint = computed(() =>
    overlay.modalEditingId
      ? '保存后会重写该用户在 ROUTES 里的目标；已建立的 dsh 会话不受影响。'
      : '保存后该用户即可从入口登录进入自己的容器；会话由代理在服务端换取并缓存。',
  )

  /** 表单回填用的初始值 */
  function formModel(id: string | null) {
    const item = id ? byId(id) : null
    const isAlert = (item ? kindOf(id) : (tab.value === 'gwalert' ? 'gwalert' : 'gwroute')) === 'gwalert'
    const route = item && item.tab === 'gwroute' ? item : null
    const alert = item && item.tab === 'gwalert' ? item : null
    return {
      isAlert,
      gwAlertName: alert?.name ?? '',
      gwTarget: alert?.target ?? '',
      gwCond: alert?.cond ?? '',
      gwSev: alert?.cat ?? 'P2 警告',
      gwName: route?.name ?? '',
      gwContainer: route?.container ?? '',
      /* 从 http://127.0.0.1:8084/ 里取端口：不能直接剥非数字字符，
         否则 '127.0.0.1' 的点和前面那段会被拼成 1270018084 */
      gwPort: route ? (String(route.target).match(/:(\d+)\/?$/) || [0, ''])[1] : '',
      gwToken: route?.loginToken ?? '',
      gwCache: route && /已落盘/.test(route.cache) ? 'sessions.json 已落盘' : '未落盘',
      gwLimit: item && 'entry' in item ? item.entry : '172.16.235.50:80',
      gwFuse:
        item && 'fuse' in item
          ? item.fuse
          : isAlert
            ? '—'
            : 'cross-site 拒绝 · 删除 Origin 与 Sec-Fetch-*',
      gwNotice: (item && 'notice' in item ? item.notice : '') || '值班群',
      gwStatus: item?.status ?? 'ok',
    }
  }


  /** 提交：新增或编辑 */
  function submitForm(v: {
    isAlert: boolean
    gwAlertName: string
    gwTarget: string
    gwCond: string
    gwSev: string
    gwName: string
    gwContainer: string
    gwPort: string
    gwToken: string
    gwCache: string
    gwLimit: string
    gwFuse: string
    gwNotice: string
    gwStatus: GwStatus
  }): boolean {
    const name = (v.isAlert ? v.gwAlertName : v.gwName).trim()
    if (!name) {
      ui.pushHtml(`请先填写${v.isAlert ? '规则名称' : '登录用户'}`)
      return false
    }
    const editingId = overlay.modalEditingId
    const editing = editingId ? byId(editingId) : null

    if (editing) {
      if (editing.tab === 'gwalert') {
        editing.name = name
        editing.cat = v.gwSev
        editing.target = v.gwTarget.trim() || '未指定对象'
        editing.cond = v.gwCond.trim() || '未填写触发条件'
        editing.notice = v.gwNotice.trim() || '值班群'
        editing.status = v.gwStatus
      } else if (editing.tab === 'gwroute') {
        const target = `http://127.0.0.1:${v.gwPort.replace(/[^\d]/g, '') || '8080'}/`
        editing.name = name
        editing.container = v.gwContainer.trim() || name
        editing.target = target
        editing.loginToken = v.gwToken.trim() || '待生成'
        editing.cache = v.gwCache
        editing.entry = v.gwLimit.trim() || '172.16.235.50:80'
        editing.fuse = v.gwFuse.trim() || '未设置'
        editing.notice = v.gwNotice.trim() || '值班群'
        editing.status = v.gwStatus
        /* 目标端口改了要同步 addr / 集群标识，表格与详情才有意义 */
        editing.addr = String(target).replace(/^https?:\/\//, '').replace(/\/$/, '')
        editing.cluster = editing.addr
      } else {
        // 容器实例与访问日志没有独立表单（走的是用户路由表单）
        editing.status = v.gwStatus
      }
      ui.pushText(`已更新 ${name}`, ['ROUTES 映射已重写，下次请求生效'])
      return true
    }

    seq++
    if (v.isAlert) {
      const fresh: GwAlert = {
        id: `gw-aln${seq}`, tab: 'gwalert', name, status: v.gwStatus, cat: v.gwSev,
        cluster: '全部容器',
        desc: '新建的告警规则，尚未产生触发记录',
        target: v.gwTarget.trim() || '未指定对象',
        cond: v.gwCond.trim() || '未填写触发条件',
        cl1: '聚合窗口', v1: '5 分钟', cl2: '连续次数', v2: '1 次',
        notice: v.gwNotice.trim() || '值班群', owner: '待指派', at: '尚未触发',
        runs: '近 30 天触发 0 次', ack: '待确认', mute: '未静默',
      }
      alerts.value = [fresh, ...alerts.value]
      ui.pushText(`告警规则 ${name} 已创建`, ['规则已进入巡检评估'])
    } else {
      const entry = v.gwLimit.trim() || '172.16.235.50:80'
      const target = `http://127.0.0.1:${v.gwPort.replace(/[^\d]/g, '') || '8080'}/`
      const fresh: GwRoute = {
        id: `gw-n${seq}`, tab: 'gwroute', name, status: v.gwStatus,
        cat: '固定映射', cluster: entry,
        desc: '新建的用户路由，尚未产生流量',
        container: v.gwContainer.trim() || name,
        target,
        loginToken: v.gwToken.trim() || '待生成',
        entry,
        session: '尚未建立', auth: '等待首次登录换取会话',
        cache: v.gwCache,
        ip: '127.0.0.1（host 网络 · 真实回环）',
        home: '/console.html · 401 即视为就绪', ws: '未连接',
        requests: '0', p95: '—', err: '—', limit: '入口限速 6000 QPS / 单 IP 300',
        fuse: v.gwFuse.trim() || '未设置', token: '有效（30 天）', lastReq: '尚未访问',
      }
      routes.value = [fresh, ...routes.value]
      ui.pushText(`用户路由 ${name} 已创建`, ['保存后请在 dsh-new.sh 用同端口拉起容器'])
    }
    return true
  }

  /* ---------------------------------------------------------------- 行内动作 */
  function toggle(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.status === 'off') {
      item.status = 'ok'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已启用`)
    } else {
      item.status = 'off'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已停用`)
    }
  }

  /** 删除确认文案里对该类行的称呼 */
  function deleteLabel(item: GwRow): string {
    return item.tab === 'gwroute'
      ? '用户路由'
      : item.tab === 'gwup'
        ? '容器实例记录'
        : item.tab === 'gwalert'
          ? '告警规则'
          : '访问日志'
  }

  function askDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    overlay.askConfirm({
      title: `删除${deleteLabel(item)}`,
      text:
        `确认删除 <b>${esc(item.name)}</b>？` +
        '删除后该用户会立刻从代理 ROUTES 里摘掉，入口登录将不再映射到任何容器；' +
        '容器本身与数据根不受影响，可用 dsh-new.sh 重新挂上。' +
        '操作会记入审计流水，不可恢复。',
      mode: 'gw',
      id: item.id,
      name: item.name,
    })
  }

  function doDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.tab === 'gwroute') routes.value = routes.value.filter((x) => x.id !== id)
    else if (item.tab === 'gwup') ups.value = ups.value.filter((x) => x.id !== id)
    else if (item.tab === 'gwalert') alerts.value = alerts.value.filter((x) => x.id !== id)
    else logs.value = logs.value.filter((x) => x.id !== id)
    ui.pushText(`${item.name} 已删除`, ['审计流水已记录'])
  }

  /** 页头「容器巡检」 */
  function ping(): void {
    const down = ups.value.filter((u) => u.status !== 'ok')
    ui.pushText('容器健康巡检完成', [
      `${ups.value.length} 个容器实例中 ${down.length} 个异常：${down.map((u) => u.name).join('、') || '无'}`,
      '就绪判定：端口可连且首页返回 401（认证墙生效即视为就绪）',
    ])
  }

  /* ---------------------------------------------------------------- 心跳 */
  function beat(): void {
    routes.value.forEach((r) => {
      if (r.status === 'off' || !/^\d/.test(String(r.requests))) return
      const cur = parseInt(String(r.requests).replace(/[^\d]/g, ''), 10) || 0
      const v = Math.max(0, Math.round(cur * (1 + rand(-4, 4) / 100)))
      r.requests = v >= 1000 ? `${(v / 1000).toFixed(1)}k` : String(v)
    })
    ups.value.forEach((u) => {
      if (u.status === 'off') return
      const max = parseInt(String(u.conn).split('/')[1] ?? '0', 10) || 200
      const cur = parseInt(String(u.conn).split('/')[0] ?? '0', 10) || 0
      u.conn = `${clamp(cur + rand(-6, 6), 0, max)} / ${max}`
      u.beat = `${rand(4, 14)} 秒前`
    })
  }

  return {
    routes,
    ups,
    alerts,
    logs,

    tab,
    filter,
    cluster,
    q,
    setTab,
    setFilter,
    setCluster,
    setQuery,

    dataOf,
    allRows,
    byId,
    kindOf,
    filtered,
    counts,
    tabCounts,
    headCount,
    newLabel,
    seekPlaceholder,
    clusters,
    kpis,
    viz,
    flow,
    meters,

    formSub,
    formHint,
    formModel,
    submitForm,

    toggle,
    askDelete,
    doDelete,
    ping,
    beat,
  }
})