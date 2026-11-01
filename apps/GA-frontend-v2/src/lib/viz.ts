/* ============================================================================
   自绘 SVG 可视化助手 —— 等价迁移自原型 console.js 3196–3211 / 3645–3686 行。

   运维类页面（网关 / 权限中心）刻意不用资产页的卡片流，改用「面板 + 明细表」。
   这里的函数负责那套面板里的折线、面积、环形进度、sparkline 与容量条。
   ========================================================================== */

import { clamp } from './util'

/**
 * 确定性伪随机：同一行数据每次刷新都一致，便于对比与测试。
 * 原型用 32 位 LCG（乘 1103515245 加 12345 对 2^31 取模）。
 */
export function seeded(seed: number): () => number {
  let s = seed
  return () => {
    s = (s * 1103515245 + 12345) % 2147483648
    return s / 2147483648
  }
}

/** 轻量确定性序列：同一个种子每次得到同一条曲线 */
export function series(
  seed: number,
  n: number,
  lo: number,
  hi: number,
  jitter?: number,
): number[] {
  const r = seeded(seed)
  const out: number[] = []
  let v = (lo + hi) / 2
  for (let i = 0; i < n; i++) {
    v = clamp(v + (r() - 0.5) * (hi - lo) * (jitter || 0.32), lo, hi)
    out.push(v)
  }
  return out
}

export function pathOf(
  vals: number[],
  w: number,
  h: number,
  pad: number,
  lo: number,
  hi: number,
): string {
  const n = vals.length
  const span = hi - lo || 1
  return vals
    .map((v, i) => {
      const x = (i / (n - 1)) * w
      const y = pad + (h - pad * 2) - ((v - lo) / span) * (h - pad * 2)
      return `${i ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join('')
}

export function areaOf(
  vals: number[],
  w: number,
  h: number,
  pad: number,
  lo: number,
  hi: number,
): string {
  return `${pathOf(vals, w, h, pad, lo, hi)}L${w} ${h}L0 ${h}Z`
}

/** 极小内联 sparkline（表格单元格里用） */
export function spk(vals: number[], tone?: string): string {
  const lo = Math.min(...vals)
  const hi = Math.max(...vals)
  return (
    '<svg class="spk" viewBox="0 0 74 20" preserveAspectRatio="none" aria-hidden="true">' +
    `<path class="spk__l is-${tone || 'ok'}" d="${pathOf(vals, 74, 20, 3, lo, hi)}"/></svg>`
  )
}

/** 单元格里的迷你容量条 */
export function meter(cur: number, max: number, tone?: string): string {
  const pct = max ? clamp((cur / max) * 100, 0, 100) : 0
  return `<span class="cmeter is-${tone || 'ok'}"><i style="width:${pct.toFixed(0)}%"></i></span>`
}

/* ---------------------------------------------------------------- sparkline 缓存 */

const spkCache: Record<string, number[]> = {}

export function routeSpk(id: string): number[] {
  if (!spkCache[id]) spkCache[id] = series(id.length * 977 + 13, 12, 20, 100, 0.42)
  return spkCache[id]!
}

export function upSpk(id: string): number[] {
  const key = `u${id}`
  if (!spkCache[key]) spkCache[key] = series(id.length * 613 + 7, 12, 30, 90, 0.38)
  return spkCache[key]!
}

/* ---------------------------------------------------------------- 环形进度 */

/** 环形进度：把百分比写成 stroke-dasharray（半径固定 50） */
export function ringDash(pct: number, r = 50): string {
  const len = 2 * Math.PI * r
  return `${((len * pct) / 100).toFixed(1)} ${len.toFixed(1)}`
}

/** 水位条的色档：越高越紧张（与原型 gmeter 的 tone 规则一致） */
export function meterTone(pct: number): 'ok' | 'warn' | 'bad' {
  return pct >= 80 ? 'bad' : pct >= 60 ? 'warn' : 'ok'
}