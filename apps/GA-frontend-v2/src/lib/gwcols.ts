/* ============================================================================
   运维明细表的列定义 —— 等价迁移自原型 console.js gwCols（3689–3794）

   每列给出 { k, t, cls, w, num, v(row) }，v 返回单元格 HTML 片段。
   内容全部过 esc()；行尾操作列复用 util 的 actsHtml，data 前缀为 gact。
   ========================================================================== */

import { actsHtml, chipOf, esc, fam } from '@/lib/util'
import type { OpsCol } from '@/lib/util'
import { meter, routeSpk, spk, upSpk } from '@/lib/viz'
import type { GwAlert, GwLog, GwRoute, GwStatus, GwUp } from '@/data/gateway'

/**
 * 表格行：四张表（用户路由 / 容器实例 / 告警规则 / 访问日志）字段差异很大，
 * 原型是一把通用对象，而 TS 里 GwRow 是判别联合。
 * 既然每个 tab 只走自己那组列定义，这里用「把所有字段收成一个可选字段的并集」来承接。
 *
 * 注意不能写 Partial<A & B & C & D>：Partial 是映射类型，
 * 会把交叉类型整个包进去求同态映射，不存在的键会一路收敛成 never，
 * 于是 g.code / g.gate 这些都会报 TS2339。逐接口 Partial 再交叉才对。
 */
export type GwTableRow = Partial<GwRoute> &
  Partial<GwUp> &
  Partial<GwAlert> &
  Partial<GwLog> & {
    id: string
    name: string
    status: GwStatus
  }

const code = (s: unknown): string => `<code>${esc(s)}</code>`

/** 行尾操作列（原型 3690–3693 的 tail） */
const tail: OpsCol<GwTableRow> = {
  k: 'acts',
  t: '',
  cls: 'gtable__act',
  w: '132px',
  v: (g) => actsHtml(g.status, 'gact'),
}

export function gwCols(tab: string): OpsCol<GwTableRow>[] {
  if (tab === 'gwroute') {
    return [
      {
        k: 'name',
        t: '登录用户 / 目标实例',
        cls: 'gtable__lead',
        w: '2.4fr',
        v: (g) =>
          `<span class="cell__main">${esc(g.name)}</span>` +
          `<span class="cell__sub">${code(g.container)} → ${esc(g.target)}</span>`,
      },
      { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
      { k: 'cat', t: '映射类型', w: '112px', v: (g) => fam(g.cat ?? '') },
      {
        k: 'token',
        t: '令牌 / 会话',
        w: '190px',
        v: (g) => {
          const stale = /已撤销|待刷新/.test(g.token ?? '')
          return (
            `<span class="cell__main2${stale ? ' is-warn' : ''}">${esc(g.token)}</span>` +
            `<span class="cell__sub">${esc(g.session)}</span>`
          )
        },
      },
      {
        k: 'requests',
        t: '请求数',
        w: '110px',
        num: true,
        v: (g) => `<b data-role="qps">${esc(g.requests)}</b>${spk(routeSpk(g.id))}`,
      },
      { k: 'p95', t: 'P95', w: '80px', num: true, v: (g) => esc(g.p95) },
      {
        k: 'err',
        t: '错误率',
        w: '84px',
        num: true,
        v: (g) => {
          const bad = parseFloat(g.err ?? '0') >= 1
          return `<span class="cell__num${bad ? ' is-bad' : ''}">${esc(g.err)}</span>`
        },
      },
      {
        k: 'ws',
        t: 'WebSocket / 最近',
        w: '190px',
        v: (g) =>
          `<span class="cell__sub">${esc(g.ws)}</span>` +
          `<span class="cell__sub">最近访问 ${esc(g.lastReq)}</span>`,
      },
      tail,
    ]
  }

  if (tab === 'gwup') {
    return [
      {
        k: 'name',
        t: '容器实例 / 监听地址',
        cls: 'gtable__lead',
        w: '2.3fr',
        v: (g) =>
          `<span class="cell__main">${esc(g.name)}</span>` +
          `<span class="cell__sub">${esc(g.addr)} · ${esc(g.ver)}</span>`,
      },
      { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
      { k: 'weight', t: '映射用户', w: '104px', v: (g) => esc(g.weight) },
      {
        k: 'conn',
        t: '连接',
        w: '124px',
        num: true,
        v: (g) => {
          const parts = String(g.conn ?? '0').split('/')
          const cur = parseInt(parts[0] ?? '0', 10) || 0
          const max = parseInt(parts[1] ?? '1', 10) || 1
          const tone = cur / max > 0.8 ? 'warn' : 'ok'
          return (
            `<span class="cell__num">${esc(g.conn)}</span>` +
            meter(cur, max, tone) +
            spk(upSpk(g.id), tone)
          )
        },
      },
      {
        k: 'cpu',
        t: 'CPU / 内存',
        w: '116px',
        num: true,
        v: (g) => {
          const cpu = parseInt(g.cpu ?? '0', 10)
          return `<span class="cell__num${cpu >= 90 ? ' is-bad' : ''}">${esc(g.cpu)} / ${esc(g.mem)}</span>`
        },
      },
      {
        k: 'qps',
        t: '承载 QPS',
        w: '92px',
        num: true,
        v: (g) => `<b data-role="qps">${esc(g.qps)}</b>`,
      },
      {
        k: 'beat',
        t: '心跳',
        w: '84px',
        num: true,
        v: (g) => `<span data-role="beat">${esc(g.beat)}</span>`,
      },
      {
        k: 'drain',
        t: '令牌 / 健康',
        w: '190px',
        v: (g) =>
          `<span class="cell__main2">${esc(g.token)}</span>` +
          `<span class="cell__sub">${esc(g.health)}</span>`,
      },
      tail,
    ]
  }

  if (tab === 'gwalert') {
    return [
      {
        k: 'name',
        t: '规则 / 触发条件',
        cls: 'gtable__lead',
        w: '2.6fr',
        v: (g) =>
          `<span class="cell__main">${esc(g.name)}</span>` +
          `<span class="cell__sub">${esc(g.cond)}</span>`,
      },
      { k: 'st', t: '状态', w: '92px', v: (g) => chipOf(g.status) },
      { k: 'sev', t: '严重程度', w: '104px', v: (g) => fam(g.cat ?? '') },
      { k: 'target', t: '监控对象', w: '180px', v: (g) => code(g.target) },
      {
        k: 'win',
        t: '窗口 / 连续',
        w: '124px',
        num: true,
        v: (g) => `<span class="cell__sub">${esc(g.v1)} · ${esc(g.v2)}</span>`,
      },
      { k: 'notice', t: '通知渠道', w: '150px', v: (g) => esc(g.notice) },
      {
        k: 'at',
        t: '最近触发',
        w: '150px',
        v: (g) =>
          `<span class="cell__sub">${esc(g.at)}</span>` +
          `<span class="cell__sub">${esc(g.runs)}</span>`,
      },
      tail,
    ]
  }

  /* 访问日志（最后一个分支，原型 3777–3793）
     注意：最后这个 return 没有返回类型注解，TS 不会把上下文类型推给数组字面量里的
     箭头参数，所以这里必须显式写上 (g: GwTableRow)。 */
  return [
    { k: 'at', t: '时间', w: '92px', num: true, v: (g: GwTableRow) => code(g.at) },
    {
      k: 'ev',
      t: '请求 / 路径',
      cls: 'gtable__lead',
      w: '2.2fr',
      v: (g: GwTableRow) =>
        `<span class="cell__main">${esc(`${g.method ?? ''} ${g.path ?? ''}`)}</span>` +
        `<span class="cell__sub">${esc(g.note)}</span>`,
    },
    {
      k: 'code',
      t: '响应',
      w: '80px',
      num: true,
      v: (g: GwTableRow) => {
        const c = String(g.code ?? '')
        const cls = /^5/.test(c) ? 'is-bad' : /^4/.test(c) ? 'is-warn' : 'is-ok'
        return `<span class="trace__code ${cls}">${esc(g.code)}</span>`
      },
    },
    { k: 'gate', t: '处置', w: '120px', v: (g: GwTableRow) => fam(g.gate ?? '') },
    { k: 'user', t: '登录用户', w: '92px', v: (g: GwTableRow) => code(g.user) },
    { k: 'hop', t: '回源', w: '124px', num: true, v: (g: GwTableRow) => code(g.hop) },
    { k: 'cost', t: '耗时', w: '84px', num: true, v: (g: GwTableRow) => esc(g.cost) },
    { k: 'rid', t: '请求号', w: '124px', num: true, v: (g: GwTableRow) => code(g.rid) },
    tail,
  ]
}