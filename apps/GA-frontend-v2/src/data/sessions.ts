/* ============================================================================
   会话数据 —— 等价迁移自原型 console.js 第 54–94 / 97–159 / 5200–5204 行。

   `SESSIONS` 是 `SEED.map()` 的派生结果，其中 rand / pick 的调用顺序与参数
   直接决定每次刷新页面的初始值，因此这里逐字照搬原型的派生逻辑。
   ========================================================================== */

import { pad2, pick, rand, stamp } from '../lib/util'

/* ---------------------------------------------------------------- 状态表 */

/** 工位（会话）状态：执行中 / 排队 / 空闲 / 降级 / 中断 */
export type SessionState = 'running' | 'queue' | 'idle' | 'warn' | 'fail'

export interface SessionStateMeta {
  cn: string
  cls: string
  blink: boolean
}

export const ST: Record<SessionState, SessionStateMeta> = {
  running: { cn: '执行中', cls: 's-running', blink: true },
  queue: { cn: '排队', cls: 's-queue', blink: false },
  idle: { cn: '空闲', cls: 's-idle', blink: false },
  warn: { cn: '降级', cls: 's-warn', blink: true },
  fail: { cn: '中断', cls: 's-fail', blink: false },
}

export const SORDER: Record<SessionState, number> = { running: 0, queue: 1, warn: 2, fail: 3, idle: 4 }

/** 顶栏状态筛选项：all + 五个状态键 */
export type SName = 'all' | SessionState

export const SNAMES: readonly SName[] = ['all', 'running', 'queue', 'idle', 'warn', 'fail']

/* ---------------------------------------------------------------- 语料池 */

export type LogLevel = 'info' | 'ok' | 'warn' | 'err'

export interface LogLine {
  t: string
  lvl: LogLevel
  m: string
}

/** 语料模板：[级别, 文案] */
export type LogTemplate = readonly [LogLevel, string]

export type LogPhase = 'running' | 'warn' | 'fail' | 'boot'

export const LOGS: Record<LogPhase, readonly LogTemplate[]> = {
  running: [
    ['info', '拉取上游数据集分片 %s，命中缓存 62%'],
    ['info', '调用 %m 完成一次推理，耗时 %s ms'],
    ['ok', '写入中间结果 %s 行，校验通过'],
    ['info', '网关路由命中副本 cluster-a/2，P95 %s ms'],
    ['ok', '技能 %s 执行完成，产物已归档'],
    ['info', '向量库检索 top-%s，召回 0.91'],
  ],
  warn: [
    ['warn', '显存水位 %s%%，已降级 batch 尺寸'],
    ['warn', '知识库 %s 分片响应超时，切换备用副本'],
    ['info', '重试第 %s 次，退避 2^n 秒'],
  ],
  fail: [
    ['err', '任务中断：镜像层校验失败（digest 不匹配）'],
    ['err', '沙箱退出码 137，疑似 OOM，已回收工位'],
  ],
  boot: [
    ['info', 'workspace 已挂载 %s'],
    ['info', '加载智能体 %a，镜像 registry.internal/agent-runtime:24.09'],
    ['ok', '按配额挂载模型 / 技能 / 知识库 / MCP 完成'],
  ],
}

/** 造一条日志：时间戳取过去 0–9 分钟内的随机偏移 */
export function logLine(lvl: LogLevel, m: string): LogLine {
  return { t: stamp(rand(-9, 0)), lvl: lvl, m: m }
}

/** 填充语料里的占位符：%m 模型 / %s 数值 / %a 智能体 */
export function fillMsg(m: string): string {
  return m
    .replace(/%m/g, pick(['qwen2.5-72b', 'deepseek-v3', 'bge-m3', 'glm-4-plus']))
    .replace(/%s/g, String(rand(3, 96)))
    .replace(/%a/g, 'agent')
}

/* ---------------------------------------------------------------- 会话数据 */

/** 工位种子：`[名称, 智能体, 工作区, 状态, 任务]` */
export type SeedRow = readonly [string, string, string, SessionState, string]

export const SEED: readonly SeedRow[] = [
  ['季度经营报表口径核对', 'Report-Agent', '/dsh/ws/report-q3',     'running', '比对 7 月口径差异，核到第 3 张底表'],
  ['合同条款风险扫描',     'Review-Agent', '/dsh/ws/contract-review','running', '逐条比对 212 份合同的违约条款'],
  ['离线知识库向量重建',   'Ingest-Agent', '/dsh/ws/kb-reindex',     'running', '重建 bge-m3 索引，已处理 68 万切片'],
  ['统一网关流量压测',     'Ops-Agent',    '/dsh/ws/gw-benchmark',   'running', '压到 3200 QPS，观察 P99 抖动'],
  ['指标口径血缘梳理',     'Search-Agent', '/dsh/ws/lineage-map',    'queue',   '排队中，等待调度器分配推理资源'],
  ['镜像依赖漏洞比对',     'Ops-Agent',    '/dsh/ws/image-cve',      'running', '比对 46 个镜像层与漏洞库快照'],
  ['工单工效分析',         'Report-Agent', '/dsh/ws/ticket-ops',     'idle',    '上一轮已交付，工位待命'],
  ['多轮对话语料清洗',     'Ingest-Agent', '/dsh/ws/corpus-clean',   'running', '去重与敏感词过滤，已过 41%'],
  ['Agent 提示词回归',     'Review-Agent', '/dsh/ws/prompt-regress', 'warn',    '第 7 组用例偏差 12%，降级重跑中'],
  ['模型效果抽检',         'Report-Agent', '/dsh/ws/model-eval',     'running', '抽取 1200 条样本做人工对齐'],
  ['权限矩阵重建',         'Ops-Agent',    '/dsh/ws/authz-matrix',   'idle',    '等待权限中心下发最新组织树'],
  ['数据脱敏批处理',       'Ingest-Agent', '/dsh/ws/mask-batch',     'running', '脱敏 8 类敏感字段，产物待复核'],
  ['技能包依赖求解',       'Code-Agent',   '/dsh/ws/skill-deps',     'queue',   '排队中，等待 Python 环境镜像拉取'],
  ['MCP 服务健康探针',     'Ops-Agent',    '/dsh/ws/mcp-probe',      'running', '探测 32 个 MCP 端点，2 个超时重试'],
  ['检索召回率调优',       'Search-Agent', '/dsh/ws/recall-tune',    'running', 'BM25 与向量权重网格搜索第 14 轮'],
  ['长文档摘要流水线',     'Report-Agent', '/dsh/ws/longdoc-sum',    'fail',    '中断：沙箱 OOM，产物未落盘'],
  ['代码仓静态扫描',       'Code-Agent',   '/dsh/ws/repo-scan',      'running', '扫描 3 个仓库，已出 214 条告警'],
  ['工具链兼容性验证',     'Code-Agent',   '/dsh/ws/tool-compat',    'idle',    '上一轮通过，工位待命'],
  ['工位资源画像',         'Report-Agent', '/dsh/ws/seat-profile',   'idle',    '按 15 分钟粒度聚合资源画像'],
  ['会话审计归档',         'Ops-Agent',    '/dsh/ws/audit-archive',  'queue',   '排队中，等待归档存储挂载'],
  ['知识图谱增量合并',     'Ingest-Agent', '/dsh/ws/kg-merge',       'running', '合并 1.2 万实体，冲突待人工裁决'],
  ['语音转写后处理',       'Ingest-Agent', '/dsh/ws/asr-post',       'warn',    '转写质量下降，已切小模型兜底'],
  ['报表可视化渲染',       'Code-Agent',   '/dsh/ws/chart-render',   'idle',    '模板已缓存，等待渲染队列'],
  ['灾备切换演练',         'Ops-Agent',    '/dsh/ws/dr-drill',       'queue',   '排队中，演练窗口 22:00 开启'],
]

export interface Session {
  idx: number
  id: string
  code: string
  name: string
  agent: string
  ws: string
  state: SessionState
  task: string
  prog: number
  cpu: string
  gpu: string
  mem: string
  gpuPct: number
  elapsed: number
  owner: string
  prio: string
  logs: LogLine[]
}

export const SESSIONS: Session[] = SEED.map(function (d, i) {
  const state = d[3]
  const isGpu = /Agent-(Report|Ingest|Search|Review)/.test(d[1]) || i % 3 !== 2
  const s: Session = {
    idx: i,
    id: 'dsh-' + (9200 + i),
    code: pad2(i + 1),
    name: d[0], agent: d[1], ws: d[2],
    state: state,
    task: d[4],
    prog: state === 'queue' ? 0 : (state === 'idle' ? 100 : rand(16, 88)),
    cpu: pick(['4 核', '8 核', '2 核']),
    gpu: isGpu ? pick(['1 × A100', '1 × A100', '2 × A100']) : '—',
    mem: pick(['16 GB', '32 GB', '8 GB']),
    gpuPct: state === 'running' ? rand(46, 92) : (state === 'idle' ? rand(2, 9) : rand(12, 40)),
    elapsed: state === 'idle' ? rand(300, 5400) : rand(420, 11000),
    owner: pick(['平台运维', '算法组', '数据组', '安全组']),
    prio: pick(['标准', '高', '低']),
    logs: [],
  }
  s.logs = [
    logLine('info', fillMsg(LOGS.boot[0][1]).replace('agent', s.agent).replace('%s', s.ws)),
    logLine('info', LOGS.boot[1][1].replace('%a', s.agent)),
    logLine('ok',   LOGS.boot[2][1]),
  ].concat(
    state === 'fail' ? LOGS.fail.map(function (l) { return logLine(l[0], l[1]) })
                     : state === 'warn' ? LOGS.warn.map(function (l) { return logLine(l[0], fillMsg(l[1])) })
                     : [logLine('info', fillMsg(pick(LOGS.running)[1]))],
  )
  return s
})

export function byId(id: string): Session | null {
  for (let i = 0; i < SESSIONS.length; i++) {
    if (SESSIONS[i].id === id) { return SESSIONS[i] }
  }
  return null
}

/* ---------------------------------------------------------------- 模拟心跳 */

/** 心跳阶段文案（beat() 里用于改写运行中工位的任务描述） */
export const PHASES: readonly string[] = [
  '拉取上游数据集分片', '调用推理服务完成一轮计算', '写入中间结果并校验',
  '向量库检索并重排 top-k', '执行技能脚本产出产物', '归档中间产物到对象存储',
  '比对血缘关系并回写元数据', '等待上游依赖返回后继续',
]