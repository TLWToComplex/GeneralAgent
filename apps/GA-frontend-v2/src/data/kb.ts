/* ============================================================================
   知识库中心数据 —— 等价迁移自原型 console.js 第 2557–2644 行。

   四种类型（文档库 / 问答库 / 表格库 / 图谱库）共用一套卡片与增删改查，
   外加一个离线假的「检索试跑」面板（向量召回 → 关键词加权 → 重排 → 答句），
   面板的假数据来自每个库的 sample 字段。
   ========================================================================== */

export type KbState = 'ready' | 'indexing' | 'paused' | 'failed'

/** 状态基色（写进卡片的 --st） */
export const KBST: Record<KbState, string> = {
  ready: 'var(--teal)',
  indexing: 'var(--azure)',
  paused: 'var(--gold)',
  failed: 'var(--coral)',
}

export const KBSTCN: Record<KbState, string> = {
  ready: '就绪',
  indexing: '索引中',
  paused: '已暂停',
  failed: '异常',
}

export type KbKind = 'doc' | 'qa' | 'sheet' | 'graph'

export const KBKIND: Record<KbKind, string> = {
  doc: '文档库',
  qa: '问答库',
  sheet: '表格库',
  graph: '图谱库',
}

/** 类型 → 家族色（doc 无底色，故为 null） */
export const KBCLS: Record<KbKind, string | null> = {
  doc: null,
  qa: 'is-llm',
  sheet: 'is-data',
  graph: 'is-rerank',
}

/** 检索试跑的样例：[出处, 定位] */
export type KbCite = readonly [string, string]

export interface KbSample {
  q: string
  a: string
  cites: readonly KbCite[]
}

export interface KbItem {
  id: string
  kind: KbKind
  name: string
  owner: string
  desc: string
  /** 文档 / 条目数 */
  docs: number
  chunks: number
  /** 切片长度 */
  size: string
  overlap: string
  /** 切片策略 */
  win: string
  /** 向量模型 */
  embed: string
  store: string
  index: string
  metric: string
  hit: string
  recall: string
  calls: number
  updated: string
  lang: string
  status: KbState
  /** 索引进度 0–100 */
  prog: number
  scope: string
  /** 表格库 / 图谱库的条目数，文档库为 0 */
  rows: number
  sample: KbSample
}

/** 8 个知识库：4 个文档库 + 2 个问答库 + 1 个表格库 + 1 个图谱库 */
export const KBS: readonly KbItem[] = [
  { id: 'kb-01', kind: 'doc', name: '财报语料库', owner: '财务管理部',
    desc: '近三年年报 / 审计报告 / 附注，按章节切片，供报表口径核对与结论溯源',
    docs: 1284, chunks: 48620, size: '512 字', overlap: '64 字', win: '语义段落',
    embed: 'bge-m3-1024', store: 'milvus-corp', index: 'HNSW · M32 / ef256', metric: '余弦相似度',
    hit: '92.4%', recall: 'P95 118 ms', calls: 18420, updated: '18 分钟前', lang: '中文',
    status: 'ready', prog: 100, scope: '12 类制度文件 + 3 套操作手册', rows: 0,
    sample: { q: '报告期内存货跌价准备的计提口径是什么？',
              a: '按成本与可变现净值孰低计量：可变现净值 = 估计售价 − 至完工估计成本 − 销售费用与税费；期末逐项比较后计提跌价准备，并计入资产减值损失。',
              cites: [['2024 年年度报告', '附注三·存货 · p.86'], ['审计报告 2024', '关键审计事项 · p.12']] } },

  { id: 'kb-02', kind: 'doc', name: '制度与政策库', owner: '综合管理部',
    desc: '公司规章制度、办法、通知与外部监管文件，条款级切片便于精确引用',
    docs: 862, chunks: 31480, size: '256 字', overlap: '32 字', win: '条款切分',
    embed: 'text-embedding-3-large', store: 'pgvector-ha', index: 'IVF-Flat · nlist 4096', metric: '余弦相似度',
    hit: '88.1%', recall: 'P95 96 ms', calls: 9640, updated: '2 小时前', lang: '中文',
    status: 'ready', prog: 100, scope: '制度 / 办法 / 通知 三级效力分层', rows: 0,
    sample: { q: '出差住宿费的报销标准是多少？',
              a: '一线城市主管及以下 600 元/晚、经理级 800 元/晚；其他城市分别下调 20%。超标部分需部门负责人事前审批，凭证齐全后 5 个工作日内到账。',
              cites: [['差旅费管理办法（2024 修订）', '第九条 · p.4'], ['费用报销操作指引', '第二部分 · p.2']] } },

  { id: 'kb-03', kind: 'doc', name: '运维手册库', owner: '云原生组',
    desc: '集群部署与故障处置手册，含回滚步骤与演练记录，供值班机器人按需召回',
    docs: 419, chunks: 12960, size: '512 字', overlap: '96 字', win: '命令块保护',
    embed: 'bge-m3-1024', store: 'milvus-corp', index: 'HNSW · M24 / ef128', metric: '内积',
    hit: '94.7%', recall: 'P95 72 ms', calls: 14260, updated: '35 分钟前', lang: '中英混合',
    status: 'indexing', prog: 68, scope: '7 套手册 + 240 条演练记录', rows: 0,
    sample: { q: '网关 P95 抖动时怎么快速回滚副本？',
              a: '先核对 `cluster-a` 副本版本与镜像摘要，确认新版本无 schema 变更后执行滚动回滚；回滚期间把流量切到 `cluster-b`，观察 5 分钟错误率曲线再决定是否扩大范围。',
              cites: [['网关运维手册', '第 6 章 · 回滚 · p.31'], ['演练记录 2024-11', '副本回滚 · 第 3 条']] } },

  { id: 'kb-04', kind: 'doc', name: '产品说明书库', owner: '产品部',
    desc: '产品功能说明、参数表与常见问题，图文混排内容按版面还原后切片',
    docs: 326, chunks: 9840, size: '384 字', overlap: '48 字', win: '版面还原',
    embed: 'qwen-embed-1024', store: 'elasticsearch-knn', index: 'HNSW + BM25 融合', metric: '混合检索',
    hit: '90.2%', recall: 'P95 140 ms', calls: 7310, updated: '1 天前', lang: '中文',
    status: 'paused', prog: 0, scope: '48 个产品线说明书', rows: 0,
    sample: { q: '这个型号支持的最大并发是多少？',
              a: '标准版单实例 200 QPS，扩容到 3 副本后线性到 560 QPS；超过阈值建议开启请求合并，否则 P95 会明显上翘。',
              cites: [['参数规格表', '性能章节 · p.18'], ['常见问题', '第 7 条']] } },

  { id: 'kb-05', kind: 'qa', name: '客服问答库', owner: '客户服务中心',
    desc: '标准问答对 + 话术库，按问题向量召回后返回标准答句与话术变体',
    docs: 3120, chunks: 3120, size: '一问一答', overlap: '—', win: '问答对齐',
    embed: 'bge-m3-1024', store: 'pgvector-ha', index: 'IVF-Flat · nlist 2048', metric: '余弦相似度',
    hit: '95.8%', recall: 'P95 44 ms', calls: 26840, updated: '26 分钟前', lang: '中文',
    status: 'ready', prog: 100, scope: '18 个业务线标准问答对', rows: 3120,
    sample: { q: '退货多久能到账？',
              a: '审核通过后 1–3 个工作日原路退回：银行卡 3 个工作日、微信/支付宝实时到账；超时可在「我的订单」发起催办。',
              cites: [['售后标准话术', '退款时效 · 第 4 条'], ['订单问题 FAQ', 'Q12']] } },

  { id: 'kb-06', kind: 'qa', name: '工单处置经验库', owner: '客户服务中心',
    desc: '历史工单的处置过程与结论，脱敏后作为相似问题处置建议',
    docs: 8640, chunks: 15420, size: '一段一单', overlap: '32 字', win: '按工单聚合',
    embed: 'm3e-base-768', store: 'elasticsearch-knn', index: 'HNSW + BM25 融合', metric: '混合检索',
    hit: '83.6%', recall: 'P95 210 ms', calls: 4180, updated: '8 小时前', lang: '中文',
    status: 'failed', prog: 0, scope: '近两年已关闭工单（已脱敏）', rows: 8640,
    sample: { q: '批量导入失败提示主键冲突怎么处理？',
              a: '先按主键做一次去重快照，用「存在即更新」模式重跑；若仍冲突，检查是否有大小写或前后空格差异，必要时启用严格模式并导出冲突行清单。',
              cites: [['工单 #48210', '处置结论 · 第 2 段'], ['工单 #51077', '处置结论 · 第 1 段']] } },

  { id: 'kb-07', kind: 'sheet', name: '指标口径库', owner: '数据平台组',
    desc: '指标定义、计算口径与责任人，按指标名 + 同义表述建立可召回条目',
    docs: 640, chunks: 1280, size: '一条一口径', overlap: '—', win: '表格行切片',
    embed: 'bge-m3-1024', store: 'milvus-corp', index: 'HNSW · M16 / ef64', metric: '余弦相似度',
    hit: '96.1%', recall: 'P95 38 ms', calls: 12460, updated: '41 分钟前', lang: '中文',
    status: 'ready', prog: 100, scope: '320 个核心指标 + 同义词表', rows: 320,
    sample: { q: '月度活跃用户的统计口径是什么？',
              a: '自然月内至少有一次有效会话（时长 ≥ 30s 且非探测流量）的去重用户数；跨月不累计，口径变更需在指标平台登记版本。',
              cites: [['指标字典', '用户域 · MAU'], ['埋点规范 v4', '有效会话定义']] } },

  { id: 'kb-08', kind: 'graph', name: '组织与权限图谱', owner: '信息安全部',
    desc: '组织、岗位、系统与权限点之间的实体关系，用于跨系统的权限推理',
    docs: 18400, chunks: 28600, size: '实体 + 关系', overlap: '—', win: '实体关系抽取',
    embed: 'bge-m3-1024', store: 'milvus-corp', index: 'HNSW · M32 / ef256', metric: '内积',
    hit: '87.3%', recall: 'P95 165 ms', calls: 3620, updated: '2 天前', lang: '中文',
    status: 'ready', prog: 100, scope: '组织 42 个部门 / 系统 68 个 / 权限点 1240', rows: 1240,
    sample: { q: '谁能审批跨部门的敏感数据导出？',
              a: '需同时满足：数据归属部门的负责人 + 信息安全部值班审批人；涉及个人信息时追加法务会签，审批链最长两级，超时自动升级到分管领导。',
              cites: [['权限管理办法', '第十二条 · p.9'], ['图谱关系 R-3182', '敏感数据导出 · 审批链']] } },
]

/** 页面级 UI 状态 */
export interface KbUi {
  tab: KbKind
  filter: 'all' | KbState
  owner: 'all' | string
  q: string
  /** 新建时的自增序号 */
  seq: number
  /** 正在编辑的条目 id，null 表示新建 */
  editing: string | null
  /** 检索试跑面板当前选中的库 id */
  cur: string | null
}

/** 知识库「检索试跑」的召回阶段（离线假数据，按固定权重拼出来的） */
export interface RecallStep {
  label: string
  /** 该阶段的耗时文案 */
  cost: string
  /** 该阶段留下的条目数 */
  kept: number
}

export const RECALL_STEPS: readonly RecallStep[] = [
  { label: '向量召回', cost: '38 ms', kept: 40 },
  { label: '关键词加权', cost: '12 ms', kept: 24 },
  { label: '交叉重排', cost: '64 ms', kept: 8 },
  { label: '答句生成', cost: '420 ms', kept: 1 },
]

/** 知识库归属人下拉（从 KBS 去重派生，与原型的 fillKbOwners 一致） */
export function kbOwners(): string[] {
  const out: string[] = []
  KBS.forEach((k) => {
    if (out.indexOf(k.owner) < 0) out.push(k.owner)
  })
  return out
}