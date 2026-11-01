/* ============================================================================
   模型清单 —— 等价迁移自原型 console.js 第 1725–1778 行。

   每个模型带「家族 / 规格 / 上下文 / 量化 / 资源」与「部署态 / 负载 / 吞吐 /
   P95 / 错误率 / 调用量」两组信息，对应卡片上的三档信息带。
   ========================================================================== */

/** 部署态 */
export type ModelState = 'deployed' | 'deploying' | 'degraded' | 'offline'

export interface ModelStateMeta {
  cn: string
  cls: string
}

export const MOD: Record<ModelState, ModelStateMeta> = {
  deployed: { cn: '在线', cls: 's-idle' },
  deploying: { cn: '部署中', cls: 's-running' },
  degraded: { cn: '异常', cls: 's-warn' },
  offline: { cn: '已下线', cls: 's-fail' },
}

/** 部署态基色（写进卡片的 --st） */
export const MST: Record<ModelState, string> = {
  deployed: 'var(--teal)',
  deploying: 'var(--azure)',
  degraded: 'var(--gold)',
  offline: 'var(--slate)',
}

/** 顶栏状态筛选项 */
export type ModelFilter = 'all' | ModelState
export const MSTATES: readonly ModelFilter[] = ['all', 'deployed', 'deploying', 'degraded', 'offline']

/** 模型类型 → 家族色（.mfamily is-*） */
export type ModelType = '推理模型' | '向量模型' | '重排序' | '多模态' | '语音模型'

export const MFAM: Record<ModelType, string> = {
  推理模型: 'is-llm',
  向量模型: 'is-embed',
  重排序: 'is-rerank',
  多模态: 'is-mm',
  语音模型: 'is-asr',
}

export interface ModelItem {
  id: string
  name: string
  /** 家族（Qwen / DeepSeek / GLM / BGE …） */
  family: string
  type: ModelType
  ver: string
  params: string
  ctx: string
  quant: string
  res: string
  status: ModelState
  /** 负载水位 0–100 */
  load: number
  qps: string
  p95: string
  err: string
  tokens: string
  calls: number
  from: string
}

/** 页面级 UI 状态（筛选 / 类型 / 搜索词），由 store 持有 */
export interface ModelsUi {
  filter: ModelFilter
  type: 'all' | ModelType
  q: string
}

export const MODELS: readonly ModelItem[] = [
  { id: 'md-01', name: 'Qwen3-72B-Instruct', family: 'Qwen', type: '推理模型', ver: '3.0.2',
    params: '72B', ctx: '128K', quant: 'INT8', res: '4 × A100 80G',
    status: 'deployed', load: 62, qps: '38 req/s', p95: '420 ms', err: '0.12%',
    tokens: '18.6M', calls: 48211, from: '2024-11-02 10:20' },
  { id: 'md-02', name: 'DeepSeek-V3-Chat', family: 'DeepSeek', type: '推理模型', ver: '3.1.0',
    params: '671B', ctx: '128K', quant: 'FP8', res: '8 × A100 80G',
    status: 'deployed', load: 74, qps: '26 req/s', p95: '510 ms', err: '0.18%',
    tokens: '24.1M', calls: 31408, from: '2024-10-28 16:05' },
  { id: 'md-03', name: 'GLM-4-9B', family: 'GLM', type: '推理模型', ver: '4.0.1',
    params: '9B', ctx: '64K', quant: 'BF16', res: '1 × A100 40G',
    status: 'deployed', load: 41, qps: '64 req/s', p95: '260 ms', err: '0.07%',
    tokens: '9.4M', calls: 52890, from: '2024-11-11 09:12' },
  { id: 'md-04', name: 'BGE-M3', family: 'BGE', type: '向量模型', ver: '1.4.2',
    params: '568M', ctx: '8K', quant: 'FP16', res: '1 × L40S 48G',
    status: 'deployed', load: 28, qps: '420 req/s', p95: '88 ms', err: '0.02%',
    tokens: '—', calls: 213044, from: '2024-09-19 14:30' },
  { id: 'md-05', name: 'bge-reranker-v2', family: 'BGE', type: '重排序', ver: '2.0.3',
    params: '568M', ctx: '8K', quant: 'FP16', res: '1 × L40S 48G',
    status: 'deployed', load: 33, qps: '180 req/s', p95: '74 ms', err: '0.03%',
    tokens: '—', calls: 96420, from: '2024-09-19 14:36' },
  { id: 'md-06', name: 'Qwen2.5-VL-7B', family: 'Qwen', type: '多模态', ver: '2.5.1',
    params: '7B', ctx: '32K', quant: 'INT4', res: '1 × A100 80G',
    status: 'deploying', load: 18, qps: '—', p95: '—', err: '—',
    tokens: '3.2M', calls: 7421, from: '2024-11-19 08:40' },
  { id: 'md-07', name: 'Whisper-large-v3', family: 'Whisper', type: '语音模型', ver: '3.0.0',
    params: '1.55B', ctx: '—', quant: 'FP16', res: '1 × L40S 48G',
    status: 'degraded', load: 6, qps: '8 req/s', p95: '1.24 s', err: '4.80%',
    tokens: '—', calls: 1877, from: '2024-11-05 11:58' },
  { id: 'md-08', name: 'Qwen2.5-32B', family: 'Qwen', type: '推理模型', ver: '2.5.4',
    params: '32B', ctx: '128K', quant: 'AWQ', res: '2 × A100 80G',
    status: 'offline', load: 0, qps: '—', p95: '—', err: '—',
    tokens: '5.7M', calls: 12903, from: '2024-08-14 09:00' },
  { id: 'md-09', name: 'gte-large-zh', family: 'GTE', type: '向量模型', ver: '1.5.0',
    params: '326M', ctx: '8K', quant: 'FP16', res: '1 × L40S 48G',
    status: 'offline', load: 0, qps: '—', p95: '—', err: '—',
    tokens: '—', calls: 41260, from: '2024-07-22 15:44' },
]

/** 近 12 小时调用量曲线（确定性的伪随机——首次渲染与后续刷新一致） */
export function modCurve(m: ModelItem, i: number): number[] {
  const out: number[] = []
  const n = 12
  const base = m.calls / 24
  for (let k = 0; k < n; k++) {
    const v =
      base *
      (0.72 + 0.42 * Math.abs(Math.sin((k + 1) * 1.7 + i * 0.9))) *
      (m.status === 'offline' ? 0.06 : m.status === 'degraded' ? 0.42 : 1)
    out.push(Math.max(2, Math.round(v)))
  }
  return out
}

/** 把调用量序列折成卡片里那条 100×30 的迷你走势线 */
export function modLine(vals: number[]): string {
  const max = Math.max(...vals) || 1
  return vals
    .map((v, k) => {
      const x = (k / (vals.length - 1)) * 100
      const y = 30 - (v / max) * 26
      return `${k ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`
    })
    .join(' ')
}