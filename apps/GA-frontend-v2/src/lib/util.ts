/* ============================================================================
   确定性工具函数 —— 从原型 console.js 第 16–51 / 3165–3211 行等价迁移。

   原型的这些函数多为「拼 HTML 字符串」的助手（kv / tag / fam / card …）。
   迁移到 Vue 后模板负责结构，但卡片内部的「三档信息带」结构高度重复，
   保留字符串助手能避免把 24 个卡片模板重复写一遍，同时保证与原型逐字节一致。
   因此这里保留它们，并在 Vue 组件里通过 v-html 使用（内容全部经 esc 转义）。
   ========================================================================== */

export const SVGNS = 'http://www.w3.org/2000/svg'

export function svgEl<K extends keyof SVGElementTagNameMap>(
  tag: K,
  attrs?: Record<string, string | number | null | undefined>,
  parent?: Node | null,
): SVGElementTagNameMap[K] {
  const n = document.createElementNS(SVGNS, tag)
  if (attrs) {
    for (const k in attrs) {
      const v = attrs[k]
      if (v !== null && v !== undefined) n.setAttribute(k, String(v))
    }
  }
  if (parent) parent.appendChild(n)
  return n
}

export function txt(node: Element | null | undefined, s: string | number): void {
  if (node) node.textContent = String(s)
}

const ESC_MAP: Record<string, string> = {
  '&': '&amp;',
  '<': '&lt;',
  '>': '&gt;',
  '"': '&quot;',
  "'": '&#39;',
}

export function esc(s: unknown): string {
  return String(s).replace(/[&<>"']/g, (c) => ESC_MAP[c]!)
}

export function rand(a: number, b: number): number {
  return Math.floor(Math.random() * (b - a + 1)) + a
}

export function pick<T>(a: readonly T[]): T {
  return a[Math.floor(Math.random() * a.length)]!
}

export function pad2(n: number): string {
  return (n < 10 ? '0' : '') + n
}

export function clamp(v: number, a: number, b: number): number {
  return v < a ? a : v > b ? b : v
}

export function trunc(s: unknown, n: number): string {
  const v = String(s)
  return v.length > n ? v.slice(0, n - 1) + '…' : v
}

/** 把任务文案切成长度均衡的两行，避免文字溢出气泡 */
export function wrap2(s: unknown, n: number): [string, string] {
  const v = String(s == null ? '' : s)
  if (v.length <= n) return [v, '']
  return [v.slice(0, n), trunc(v.slice(n), n)]
}

export function fmtDur(sec: number): string {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (h) return `${h}h ${m}m`
  return `${m}m ${pad2(sec % 60)}s`
}

export function stamp(offsetMin = 0): string {
  const d = new Date(Date.now() + offsetMin * 60000)
  return `${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}`
}

/** 用状态变量派生半透明填充/描边，随 .s-* 的 --st 自动换色 */
export function st(alpha: number, kind?: 'stroke'): string {
  return `${kind === 'stroke' ? 'stroke' : 'fill'}:color-mix(in srgb,var(--st) ${alpha}%,transparent)`
}

/* ---------------------------------------------------------------- 状态表 */

export type OpsKey = 'ok' | 'warn' | 'wait' | 'off'

export interface OpsMeta {
  cn: string
  cls: string
  v: string
}

/** 状态基色：正常 / 告警 / 待处理 / 停用 */
export const OPS: Record<OpsKey, OpsMeta> = {
  ok: { cn: '正常', cls: 's-idle', v: 'var(--teal)' },
  warn: { cn: '告警', cls: 's-warn', v: 'var(--gold)' },
  wait: { cn: '待处理', cls: 's-queue', v: 'var(--violet)' },
  off: { cn: '停用', cls: 's-fail', v: 'var(--slate)' },
}

/** 复用工具/知识库的分类色 */
export const CATCLS: Record<string, string> = {
  推理服务: 'is-llm',
  向量检索: 'is-embed',
  数据服务: 'is-data',
  观测采集: 'is-rerank',
  接口网关: 'is-mm',
  管理后台: 'is-sys',
  核心平台: 'is-llm',
  生产环境: 'is-asr',
  数据资源: 'is-data',
  知识库: 'is-embed',
  内置角色: 'is-llm',
  自定义角色: 'is-rerank',
  服务账号角色: 'is-mm',
  研发中心: 'is-llm',
  云原生组: 'is-mm',
  数据平台组: 'is-data',
  信息安全部: 'is-rerank',
  财务管理部: 'is-sys',
  外部协作: 'is-asr',
  允许: 'is-data',
  拒绝: 'is-asr',
  需要审批: 'is-rerank',
  'P1 严重': 'is-asr',
  'P2 警告': 'is-rerank',
  'P3 提示': 'is-llm',
}

export function cls4(k: string): string {
  return CATCLS[k] || ''
}

export function opsOf(s: string | undefined | null): OpsMeta {
  return (s && OPS[s as OpsKey]) || OPS.ok
}

/* ---------------------------------------------------------------- HTML 助手 */

export function tag(t: string, v: unknown): string {
  return `<span class="tagchip">${esc(t)} <em>${esc(v)}</em></span>`
}

export function fam(text: string): string {
  return `<span class="mfamily ${cls4(text)}">${esc(text)}</span>`
}

export function bigNum(label: string, value: unknown, unit?: string): string {
  return (
    `<div class="opstat"><span>${esc(label)}</span><b>${esc(value)}</b>` +
    (unit ? `<em>${esc(unit)}</em>` : '') +
    '</div>'
  )
}

/** 详情抽屉里的一行「键 / 值」（原型 kvHtml 639）—— 入参为 [键, 值] 元组 */
export function kv(row: readonly [string, unknown], wide?: boolean, role?: string): string {
  const [i, v] = row
  return (
    `<span${wide ? ' class="is-wide"' : ''}><i>${esc(i)}</i><b` +
    (role ? ` data-role="${role}"` : '') +
    `>${esc(v)}</b></span>`
  )
}

/**
 * 详情抽屉里一整块「键 / 值」网格（原型 kvHtml 639 的用法）。
 * 注意：普通函数声明 `kv(a, b)` 不是重载，一次只能吃一个元组，
 * 所以成组渲染必须走这个函数，不能把数组直接塞给 kv()。
 */
export function kvGrid(rows: readonly (readonly [string, unknown])[]): string {
  return rows.map((r) => kv(r)).join('')
}

export function chipOf(s: string): string {
  const o = opsOf(s)
  return (
    `<span class="stchip${s === 'warn' || s === 'wait' ? ' is-blink' : ''}"` +
    ` data-role="st" style="--st:${o.v}">${o.cn}</span>`
  )
}

/** 卡片骨架：三档信息带（头部 / 配置 / 操作） */
export function card(status: string, id: string, bands: [string, string, string]): string {
  const o = opsOf(status)
  return (
    `<article class="regcard opcard ${o.cls}" data-id="${id}" role="listitem" style="--st:${o.v}">` +
    `<div class="regrow__id">${bands[0]}</div>` +
    `<div class="regrow__meta opcard__cfg">${bands[1]}</div>` +
    `<div class="regrow__side">${bands[2]}</div>` +
    '</article>'
  )
}

export interface KpiSpec {
  /** 指标条左侧图标（i-cube / i-model / …） */
  icon: string
  /** 主数字 */
  num: string | number
  /** 主数字后的单位小字 */
  unit: string
  /** 右下角的补充说明（可含 <i> 数字，故按 HTML 传入） */
  delta: string
  /** 顶部色带的语义类（原型的 data-kpi） */
  kind?: string
  /** 卡内右侧的迷你折线（原型 kpiSpark 的 path d，只有工作台用） */
  spark?: string
}

/** 指标卡里的迷你折线（原型 kpiSpark 1368–1371） */
export function kpiSpark(d: string): string {
  return (
    '<svg class="spark" viewBox="0 0 132 34" preserveAspectRatio="none" aria-hidden="true">' +
    `<path class="spark__line" d="${d}"/></svg>`
  )
}

/** 顶栏指标卡（原型 1411–1437 的四张 .kpi，被镜像 / 模型 / 工具 / 知识库页复用） */
export function kpiStrip(items: readonly KpiSpec[]): string {
  return items
    .map(
      (k) =>
        `<article class="kpi"${k.kind ? ` data-kpi="${k.kind}"` : ''}>` +
        `<span class="kpi__label"><svg class="ic" aria-hidden="true"><use href="#${k.icon}"/></svg></span>` +
        '<span class="kpi__main">' +
        `<span class="kpi__num"><b>${esc(k.num)}</b><i class="kpi__sub">${esc(k.unit)}</i></span>` +
        `<span class="kpi__delta">${k.delta}</span>` +
        '</span>' +
        (k.spark ? kpiSpark(k.spark) : '') +
        '</article>',
    )
    .join('')
}

/**
 * 运维明细表的一列定义 —— 对应原型 gwCols / pzCols 里的
 * { k, t, cls, w, num, v(row) }。
 *
 * 因为 .ts 文件 import 不了 .vue 里的类型（shim 只声明了默认导出），
 * 这个类型放在这里，OpsTable.vue 与各列定义文件共同引用。
 */
export interface OpsCol<T> {
  /** 列键，仅用于 :key */
  k: string
  /** 表头文案（空串表示操作列） */
  t: string
  /** 右对齐数字列 */
  num?: boolean
  /** 附加类（gtable__lead / gtable__act） */
  cls?: string
  /** 列宽，写进 --w（如 '92px' 或 '2.4fr'） */
  w?: string
  /** 单元格内容（返回 HTML 片段） */
  v: (row: T) => string
}

/** 明细表行尾的四个操作按钮（原型 gwActionsHtml 3879 / pzCols 里的 acts） */
export function actsHtml(status: string, act: string): string {
  const ic = (name: string): string =>
    `<svg class="ic" aria-hidden="true"><use href="#${name}"/></svg>`
  return (
    '<div class="trow__acts">' +
    `<button type="button" data-${act}="detail" title="详情">${ic('i-eye')}</button>` +
    `<button type="button" data-${act}="edit" title="编辑">${ic('i-tool')}</button>` +
    `<button type="button" data-${act}="toggle" title="启停">${
      ic(status === 'off' ? 'i-play' : 'i-pause')
    }</button>` +
    `<button type="button" data-${act}="del" title="删除">${ic('i-x')}</button>` +
    '</div>'
  )
}