/* ============================================================================
   权限中心 store —— 角色 / 账号 / 资源策略 / 提权工单

   等价迁移自原型 console.js 的这几处：
     · 4111–4157  renderOpsGrid（权限分支）：tab 徽标、页头计数、空态
     · 4162–4311  PZTABS / PERMROLES / PERMACCTS / PERMPOLS / PERMAPPRS
     · 4312–4349  pzData / pzById / pzKindOf / pzScopeOf / pzHay / pzFiltered / pzCounts
     · 4350–4394  renderPzKpis / updatePzKpis
     · 4395–4449  pzBands            卡片的三档信息带
     · 4013–4104  renderPzViz        评分环 / 态势 / 角色×资源矩阵 / 审批链 / 授权趋势
     · 4511–4533  opsFormOpen（权限分支）表单回填
     · 4611–4667  pzFormSubmit       新增 / 编辑
     · 4793–4799  pzReview 发起复核
     · 4837–4883  handleOpsAction / askOpsDelete / doOpsDelete
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { esc } from '@/lib/util'
import { seeded, series } from '@/lib/viz'
import { useUiStore } from '@/stores/ui'
import { useOverlayStore } from '@/stores/overlay'
import {
  PERMACCTS,
  PERMAPPRS,
  PERMPOLS,
  PERMROLES,
} from '@/data/authz'
import type {
  PermAcct,
  PermAppr,
  PermPol,
  PermRecord,
  PermRole,
  PzRow,
  PzStatus,
  PzTab,
} from '@/data/authz'

export type { PermAcct, PermAppr, PermPol, PermRecord, PermRole, PzRow, PzStatus, PzTab }

/** 权益状态：正常 / 告警 / 停用（沿用原型三态） */
export type PzFilter = 'all' | PzStatus

/* ---------------------------------------------------------------- tab 元信息 */

/** 与原型 PZTABS 一一对应 */
export const PZTABS: Record<PzTab, { kind: PzTab; item: string; ph: string }> = {
  role: { kind: 'role', item: '角色', ph: '搜索角色 / 数据范围 / 权限域' },
  acct: { kind: 'acct', item: '账号', ph: '搜索账号 / 部门 / 角色' },
  pol: { kind: 'pol', item: '资源策略', ph: '搜索策略 / 资源匹配' },
  appr: { kind: 'appr', item: '提权工单', ph: '搜索工单 / 申请人' },
}

/** 权限矩阵的资源域列（原型 renderPzViz 里的 domains） */
export const MX_DOMAINS = ['模型', '镜像', '知识库', '工具', '网关', '权限'] as const
export const MX_LEVELS = ['无权', '只读', '部分', '完全'] as const

/** 表单回填模型 */
export interface PzFormModel {
  pzName: string
  pzKind: string
  pzScope: string
  pzAcct: string
  pzDept: string
  pzRoleBind: string
  pzPolName: string
  pzRes: string
  pzEffect: string
  pzApprName: string
  pzWho: string
  pzLife: string
  pzActs: string
  pzDesc: string
  pzStatus: PzStatus
}

export const useAuthzStore = defineStore('authz', () => {
  const ui = useUiStore()
  const overlay = useOverlayStore()

  /* ---------------------------------------------------------------- 可变副本
     四张表分开持有各自的具体类型（而不是统一的联合类型数组），
     这样 store 内部访问 fields 时 TS 能直接收窄，不需要到处断言。 */
  const roles = ref<PermRole[]>(structuredClone(PERMROLES) as PermRole[])
  const accts = ref<PermAcct[]>(structuredClone(PERMACCTS) as PermAcct[])
  const pols = ref<PermPol[]>(structuredClone(PERMPOLS) as PermPol[])
  const apprs = ref<PermAppr[]>(structuredClone(PERMAPPRS) as PermAppr[])

  /* ---------------------------------------------------------------- UI 状态 */
  const tab = ref<PzTab>('role')
  const filter = ref<PzFilter>('all')
  /** 数据范围筛选（下拉值域来自四个 tab 出现过的全部范围） */
  const scope = ref<'all' | string>('all')
  const q = ref('')
  let seq = 0

  function setTab(t: PzTab): void {
    tab.value = t
    filter.value = 'all'
    q.value = ''
    scope.value = 'all'
  }

  function setQuery(v: string): void {
    q.value = v
    if (ui.query !== v) ui.query = v
  }

  /** 状态筛选条（原型 data-pzst：全部 / 已生效 / 待处理 / 已停用） */
  function setFilter(f: PzFilter): void {
    filter.value = f
  }

  /** 适用范围下拉（原型 #pzScope） */
  function setScope(s: string): void {
    scope.value = s
  }

  /* ---------------------------------------------------------------- 查询 */
  function dataOf(t: PzTab): readonly PzRow[] {
    if (t === 'role') return roles.value
    if (t === 'acct') return accts.value
    if (t === 'pol') return pols.value
    return apprs.value
  }

  const allRows = computed<PzRow[]>(() => [
    ...roles.value,
    ...accts.value,
    ...pols.value,
    ...apprs.value,
  ])

  function byId(id: string | null): PzRow | null {
    if (!id) return null
    return allRows.value.find((g) => g.id === id) ?? null
  }

  function kindOf(id: string | null): PzTab {
    return byId(id)?.tab ?? 'role'
  }

  /** 四类对象都有「数据范围」，统一用它做范围维度；工单没有范围，用审批链兜底 */
  function scopeOf(g: PzRow): string {
    if (g.tab === 'appr') return g.approver
    return g.scope
  }

  function hay(g: PzRow): string {
    return Object.keys(g)
      .map((k) => String((g as unknown as Record<string, unknown>)[k]))
      .join(' ')
      .toLowerCase()
  }

  function filteredOf(byState: boolean): PzRow[] {
    return dataOf(tab.value).filter((g) => {
      if (byState && filter.value !== 'all' && g.status !== filter.value) return false
      if (scope.value !== 'all' && scopeOf(g) !== scope.value) return false
      if (q.value && hay(g).indexOf(q.value.toLowerCase()) < 0) return false
      return true
    })
  }

  const filtered = computed<PzRow[]>(() => filteredOf(true))

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

  const tabCounts = computed(() => ({
    role: roles.value.length,
    acct: accts.value.length,
    pol: pols.value.length,
    appr: apprs.value.length,
  }))

  /** 页头汇总文案 */
  const headCount = computed(
    () =>
      `${roles.value.length} 个角色 · ${accts.value.length} 个账号 · ` +
      `${pols.value.length} 条资源策略`,
  )

  const newLabel = computed(() => `新建${PZTABS[tab.value].item}`)
  const seekPlaceholder = computed(() => PZTABS[tab.value].ph)

  /** 范围下拉的选项：四个 tab 里出现过的全部范围（切换 tab 后不会缺项） */
  const scopes = computed<string[]>(() => {
    const out: string[] = []
    ;[roles.value, accts.value, pols.value, apprs.value].forEach((arr) => {
      arr.forEach((g) => {
        const s = scopeOf(g)
        if (s && out.indexOf(s) < 0) out.push(s)
      })
    })
    return out
  })

  /* ---------------------------------------------------------------- KPI */
  const kpis = computed(() => {
    const risky = roles.value.filter((r) => /高风险/.test(r.risk) || /中风险/.test(r.risk)).length
    const mfa = roles.value.filter((r) => /强制双因子/.test(r.mfa)).length
    return {
      role: roles.value.length,
      acct: accts.value.length,
      pol: pols.value.length,
      deny: pols.value.filter((p) => p.effect !== '允许').length,
      risk: risky,
      mfa: `${Math.round((mfa / (roles.value.length || 1)) * 100)}%`,
      appr: apprs.value.filter((a) => a.status === 'warn').length,
      /** 鉴权调用量：原型写死 4820 */
      calls: 4820,
    }
  })

  /* ---------------------------------------------------------------- 可视化 */

  /** 评分环：双因子覆盖 60% + 含拒绝/审批策略占比 40% */
  const score = computed(() => {
    const mfaRatio = roles.value.filter((r) => /强制双因子/.test(r.mfa)).length / (roles.value.length || 1)
    const denyRatio = pols.value.filter((p) => p.effect !== '允许').length / (pols.value.length || 1)
    return Math.round((mfaRatio * 0.6 + denyRatio * 0.4) * 100)
  })

  /** 安全态势四项 */
  const posture = computed(() => {
    const mfaRatio = roles.value.filter((r) => /强制双因子/.test(r.mfa)).length / (roles.value.length || 1)
    const denyRatio = pols.value.filter((p) => p.effect !== '允许').length / (pols.value.length || 1)
    const stale = roles.value.filter((r) => /待整改|未强制/.test(r.mfa) || /中风险/.test(r.risk)).length
    const dormant = accts.value.filter((a) => a.status === 'off').length
    return [
      { t: '双因子覆盖', v: Math.round(mfaRatio * 100), tone: mfaRatio >= 0.9 ? 'ok' : 'warn', suffix: '%' },
      { t: '含拒绝 / 审批的策略', v: Math.round(denyRatio * 100), tone: 'ok', suffix: '%' },
      { t: '待整改角色', v: stale, tone: stale ? 'warn' : 'ok', suffix: ' 个' },
      { t: '休眠账号', v: dormant, tone: dormant ? 'warn' : 'ok', suffix: ' 个' },
    ]
  })

  /** 角色 × 资源矩阵：命中权限域给满档，否则按固定种子给「只读 / 部分 / 完全」 */
  const matrix = computed(() => {
    const r0 = seeded(20241102)
    const rows = roles.value.slice(0, 6)
    return rows.map((r) => ({
      name: r.name,
      cells: MX_DOMAINS.map((d) => {
        /* 权限域文案里命中资源名则给满权限，否则按种子给部分/只读 */
        const hit = r.domains.indexOf(d) >= 0
        const lv = hit ? 3 : Math.floor(r0() * 3)
        return { dom: d, lv, text: MX_LEVELS[lv]! }
      }),
    }))
  })

  /** 最短审批链：取当前待处理工单最多的那条 */
  const chain = computed(() => {
    const cur = apprs.value.filter((a) => a.status === 'warn')[0] ?? apprs.value[0]
    if (!cur) return []
    const steps = (cur.approver || '').split('+').map((s) => s.trim())
    steps.unshift(`申请人 ${cur.who}`)
    steps.push('权限下发')
    return steps.map((s, i) => {
      const state =
        i === 0
          ? 'is-done'
          : i <= steps.length - 3
            ? 'is-done'
            : i === steps.length - 1
              ? 'is-wait'
              : 'is-now'
      return {
        text: s,
        state,
        meta: state === 'is-done' ? '已通过' : state === 'is-now' ? '审批中' : '待触发',
      }
    })
  })

  /** 授权趋势：12 周内每周净增授权数（正负都可能有） */
  const trend = computed(() => {
    const bars = series(31337, 12, -6, 14, 0.55).map((v) => Math.round(v))
    const max = Math.max(...bars.map((v) => Math.abs(v))) || 1
    return bars.map((v, i) => ({
      week: i + 1,
      v,
      up: v >= 0,
      h: `${Math.max(6, (Math.abs(v) / max) * 100).toFixed(0)}%`,
      title: `第 ${i + 1} 周：${v >= 0 ? '+' : ''}${v} 项`,
    }))
  })

  /* ---------------------------------------------------------------- 表单 */
  const formSub = computed(
    () => '授权按最小权限原则：先选数据范围，再勾选动作，最后指定生效期与审批人。',
  )
  const formHint = computed(() =>
    overlay.modalEditingId
      ? '保存后会写入审计流水，权限立即生效。'
      : '保存后会写入审计流水；涉及生产资源的授权会同时通知审批人。',
  )

  function formModel(id: string | null): PzFormModel {
    const item = id ? byId(id) : null
    const role = item?.tab === 'role' ? item : null
    const acct = item?.tab === 'acct' ? item : null
    const pol = item?.tab === 'pol' ? item : null
    const appr = item?.tab === 'appr' ? item : null
    return {
      pzName: role?.name ?? '',
      pzKind: role?.cat ?? '自定义角色',
      pzScope: role?.scope ?? '本部门',
      pzAcct: acct?.name ?? '',
      pzDept: acct?.dept ?? '',
      pzRoleBind: acct?.role ?? '模型运营',
      pzPolName: pol?.name ?? '',
      pzRes: pol?.res ?? '',
      pzEffect: pol?.effect ?? '允许',
      pzApprName: appr?.name ?? '',
      pzWho: appr?.who ?? '',
      pzLife: appr?.life ?? '2 小时',
      pzActs: item?.acts ?? '查看',
      pzDesc: item?.desc ?? '',
      pzStatus: item?.status ?? 'ok',
    }
  }

  /** 当前表单应对应的 tab（编辑时看对象，新建时看当前 tab） */
  const formTab = computed<PzTab>(() => {
    const id = overlay.modalEditingId
    return id ? kindOf(id) : tab.value
  })

  /** 提交：新增或编辑 */
  function submitForm(v: PzFormModel): boolean {
    const t = formTab.value
    const name = (
      t === 'role' ? v.pzName : t === 'acct' ? v.pzAcct : t === 'pol' ? v.pzPolName : v.pzApprName
    ).trim()
    if (!name) {
      ui.pushHtml('请先填写名称')
      return false
    }
    const acts = v.pzActs.trim() || '查看'
    const desc = v.pzDesc.trim() || '未填写说明'
    const status = v.pzStatus

    /*
     * 原型按 tab 各自组织 data，然后 Object.keys(data) 逐字段盖到编辑对象上。
     * 这里保持同样的字段集合，多出来的 tab 专有字段用下方 Object.assign 补齐。
     */
    const editingId = overlay.modalEditingId
    const editing = editingId ? byId(editingId) : null

    if (editing) {
      const extra: Record<string, string> = {}
      if (editing.tab === 'role') {
        Object.assign(editing, {
          name,
          cat: v.pzKind,
          scope: v.pzScope,
          acts,
          desc,
          status,
        })
      } else if (editing.tab === 'acct') {
        extra.dept = v.pzDept.trim() || '未标注部门'
        extra.role = v.pzRoleBind
        Object.assign(editing, { name, dept: extra.dept, role: extra.role, acts, desc, status })
      } else if (editing.tab === 'pol') {
        extra.res = v.pzRes.trim() || '未指定资源'
        extra.effect = v.pzEffect
        Object.assign(editing, {
          name,
          res: extra.res,
          effect: extra.effect,
          cat: extra.effect,
          acts,
          desc,
          status,
        })
      } else {
        extra.who = v.pzWho.trim() || '未填写申请人'
        extra.life = v.pzLife.trim() || '2 小时'
        Object.assign(editing, {
          name,
          who: extra.who,
          life: extra.life,
          cat: '需要审批',
          acts,
          desc,
          status,
        })
      }
      ui.pushText(`${name} 已更新`, ['变更已写入审计流水'])
      return true
    }

    seq++
    /* 按 tab 分别构造完整对象（原型的 f2 + Object.assign 两段合并成一段） */
    if (t === 'role') {
      const fresh: PermRole = {
        id: `pz-n${seq}`, tab: 'role', name, status,
        cat: v.pzKind || '自定义角色', scope: v.pzScope || '本部门', desc, acts,
        owner: '待指派', lastReview: '尚未复核',
        domains: '待配置', members: '0 个账号', life: '长期有效',
        mfa: '待配置', approver: '信息安全部', risk: '新角色 · 待首次复核',
      }
      roles.value = [fresh, ...roles.value]
    } else if (t === 'acct') {
      const fresh: PermAcct = {
        id: `pz-n${seq}`, tab: 'acct', name, status,
        cat: v.pzDept.trim() || '未标注部门', scope: v.pzScope || '本部门', desc, acts,
        owner: '待指派', lastReview: '新账号',
        role: v.pzRoleBind, dept: v.pzDept.trim() || '未标注部门',
        mfa: '待开启', login: '尚未登录', res: '按角色继承',
        expire: '长期有效', risk: '新账号 · 待首次复核',
      }
      accts.value = [fresh, ...accts.value]
    } else if (t === 'pol') {
      const fresh: PermPol = {
        id: `pz-n${seq}`, tab: 'pol', name, status,
        cat: v.pzEffect || '自定义角色', scope: v.pzScope || '本部门', desc, acts,
        owner: '待指派', lastReview: '尚未复核',
        res: v.pzRes.trim() || '未指定资源', effect: v.pzEffect,
        cond: '无附加条件', prio: '优先级 500', applied: '尚未命中',
        hit: '近 7 天命中 0 次', expire: '长期有效',
      }
      pols.value = [fresh, ...pols.value]
    } else {
      const fresh: PermAppr = {
        id: `pz-n${seq}`, tab: 'appr', name, status,
        cat: '需要审批', scope: v.pzScope || '本部门', desc, acts,
        owner: '待指派', lastReview: '尚未复核',
        who: v.pzWho.trim() || '未填写申请人', res: '待填写资源',
        life: v.pzLife.trim() || '2 小时', approver: '待指派审批人',
        at: '刚刚提交', due: '待受理', stage: '待受理', risk: '新工单 · 待评估',
      }
      apprs.value = [fresh, ...apprs.value]
    }
    ui.pushText(`${PZTABS[t].item} ${name} 已创建`, ['已写入审计流水'])
    return true
  }

  /* ---------------------------------------------------------------- 行内动作 */
  function toggle(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.status === 'off') {
      /* 工单启用后回到「需要审批」，其余类别直接回到正常 */
      item.status = item.tab === 'appr' ? 'warn' : 'ok'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已启用`)
    } else {
      item.status = 'off'
      ui.pushHtml(`<b>${esc(item.name)}</b> 已停用`)
    }
  }

  function askDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    overlay.askConfirm({
      title: `删除${PZTABS[item.tab].item}`,
      text:
        `确认删除 <b>${esc(item.name)}</b>？` +
        '删除后配置会立即从权限判定面移除，' +
        '操作会记入审计流水，不可恢复。',
      mode: 'perm',
      id: item.id,
      name: item.name,
    })
  }

  function doDelete(id: string): void {
    const item = byId(id)
    if (!item) return
    if (item.tab === 'role') roles.value = roles.value.filter((x) => x.id !== id)
    else if (item.tab === 'acct') accts.value = accts.value.filter((x) => x.id !== id)
    else if (item.tab === 'pol') pols.value = pols.value.filter((x) => x.id !== id)
    else apprs.value = apprs.value.filter((x) => x.id !== id)
    ui.pushText(`${item.name} 已删除`, ['审计流水已记录'])
  }

  /** 页头「发起权限复核」 */
  function review(): void {
    ui.pushText('已发起权限复核', [
      `待复核角色 ${roles.value.length} 个 · 高风险 ` +
        `${roles.value.filter((r) => /高风险/.test(r.risk)).length} 个`,
    ])
  }

  /** 授权趋势的净增合计文案（原型 4101：(net >= 0 ? '+' : '') + net + ' 项'） */
  const trendNetText = computed(() => {
    const net = trend.value.reduce((a, b) => a + b.v, 0)
    return `${net >= 0 ? '+' : ''}${net} 项`
  })

  /**
   * 点权限矩阵的格子：说明该角色在这个资源域里的权限来源（原型 4721–4733）。
   * 选中态由视图自己用 .mx__cell--on 维护，这里只负责弹提示。
   */
  function openMatrixCell(row: string, dom: string, lv: number): void {
    ui.pushText(`${row} × ${dom}：${MX_LEVELS[lv] ?? '无权'}`, [
      lv === 0 ? '由更严格的拒绝策略兜底' : '来源：角色权限域 + 资源策略叠加',
    ])
  }

  /* ---------------------------------------------------------------- 心跳 */
  /** 提权工单的剩余时限会随时间收紧；鉴权调用量小幅波动 */
  function beat(): void {
    apprs.value.forEach((a) => {
      if (a.status !== 'warn') return
      const m = /剩 (\d+) 小时 (\d+) 分/.exec(a.due ?? '')
      if (m) {
        let h = Number(m[1])
        let mi = Number(m[2]) - 1
        if (mi < 0) {
          mi = 59
          h -= 1
        }
        a.due = h > 0 ? `剩 ${h} 小时 ${mi} 分` : `剩 ${mi} 分`
      } else {
        const d = /剩 (\d+) 天/.exec(a.due ?? '')
        if (d) a.due = a.due // 天级不动
      }
    })
  }

  return {
    roles,
    accts,
    pols,
    apprs,

    tab,
    filter,
    scope,
    q,
    setTab,
    setQuery,
    setFilter,
    setScope,

    dataOf,
    allRows,
    byId,
    kindOf,
    scopeOf,
    filtered,
    counts,
    tabCounts,
    headCount,
    newLabel,
    seekPlaceholder,
    scopes,
    kpis,

    score,
    posture,
    matrix,
    chain,
    trend,
    trendNetText,
    openMatrixCell,

    formSub,
    formHint,
    formTab,
    formModel,
    submitForm,

    toggle,
    askDelete,
    doDelete,
    review,
    beat,
  }
})