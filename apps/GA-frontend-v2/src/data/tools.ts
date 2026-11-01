/* ============================================================================
   工具平台数据（MCP 服务 / Skill 工具）—— 等价迁移自原型 console.js 第 2079–2142 行。

   两种工具共用一张卡骨架与一套增删改查流程，由 .tabs 切换当前列表：
   MCP 侧的关键字段是 transport / endpoint / exposes，
   Skill 侧多出 owner / timeout / version（所以用判别联合区分）。
   ========================================================================== */

export type ToolState = 'online' | 'degraded' | 'offline'

/** 状态基色（写进卡片的 --st） */
export const TST: Record<ToolState, string> = {
  online: 'var(--teal)',
  degraded: 'var(--gold)',
  offline: 'var(--slate)',
}

export const TSTCN: Record<ToolState, string> = {
  online: '在线',
  degraded: '异常',
  offline: '已下线',
}

/** 分类 → 家族色（.mfamily is-*） */
export const TCAT: Record<string, string> = {
  数据处理: 'is-data',
  文档处理: 'is-doc',
  系统运维: 'is-sys',
  代码工程: 'is-llm',
  检索增强: 'is-embed',
  数据分析: 'is-rerank',
  系统: 'is-sys',
  数据: 'is-data',
  协作: 'is-llm',
  搜索: 'is-embed',
}

/** MCP 服务的传输方式 */
export type McpTransport = 'stdio' | 'SSE' | 'streamable-http'
/** Skill 工具的运行时 */
export type SkillRuntime = 'Python 3.12' | 'Node 22'

export interface ToolCommon {
  id: string
  name: string
  cat: string
  desc: string
  vendor: string
  /** 对外暴露的能力数 */
  exposes: number
  status: ToolState
  calls: number
  p95: string
}

export interface McpTool extends ToolCommon {
  kind: 'mcp'
  transport: McpTransport
  endpoint: string
  owner: '—'
  timeout: '—'
}

export interface SkillTool extends ToolCommon {
  kind: 'skill'
  transport: SkillRuntime
  endpoint: string
  /** 归属智能体 */
  owner: string
  timeout: string
  version: string
}

export type ToolItem = McpTool | SkillTool

/** MCP 服务：8 个（其中 browser-mcp 异常、mail-mcp 已下线） */
export const MCPS: readonly McpTool[] = [
  { kind: 'mcp', id: 'mcp-01', name: 'fs-mcp', cat: '系统运维', desc: '读写 workspace 内的文件与目录树',
    transport: 'stdio', endpoint: 'stdio://fs-mcp', vendor: '平台基础组', exposes: 6,
    status: 'online', calls: 12840, p95: '12 ms', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-02', name: 'git-mcp', cat: '代码工程', desc: '仓库读写、分支与提交记录查询',
    transport: 'SSE', endpoint: 'wss://mcp.internal/git', vendor: 'DevOps 组', exposes: 9,
    status: 'online', calls: 8210, p95: '38 ms', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-03', name: 'browser-mcp', cat: '检索增强', desc: '无头浏览器抓取与页面结构抽取',
    transport: 'SSE', endpoint: 'wss://mcp.internal/browser', vendor: '搜索组', exposes: 5,
    status: 'degraded', calls: 4310, p95: '860 ms', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-04', name: 'sheet-mcp', cat: '数据处理', desc: '电子表格读写、透视与公式求值',
    transport: 'streamable-http', endpoint: 'https://mcp.internal/sheet', vendor: '数据平台组', exposes: 7,
    status: 'online', calls: 9642, p95: '66 ms', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-05', name: 'db-mcp', cat: '数据处理', desc: '只读 SQL 查询与表结构内省',
    transport: 'SSE', endpoint: 'wss://mcp.internal/db', vendor: '数据平台组', exposes: 4,
    status: 'online', calls: 6120, p95: '54 ms', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-06', name: 'k8s-mcp', cat: '系统运维', desc: '集群资源查询与滚动发布编排',
    transport: 'SSE', endpoint: 'wss://mcp.internal/k8s', vendor: '云原生组', exposes: 12,
    status: 'online', calls: 3180, p95: '92 ms', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-07', name: 'mail-mcp', cat: '协作', desc: '邮件草拟、发送与回执跟踪',
    transport: 'streamable-http', endpoint: 'https://mcp.internal/mail', vendor: '办公协同组', exposes: 3,
    status: 'offline', calls: 0, p95: '—', owner: '—', timeout: '—' },
  { kind: 'mcp', id: 'mcp-08', name: 'docs-mcp', cat: '文档处理', desc: '文档解析、格式转换与批量脱敏',
    transport: 'SSE', endpoint: 'wss://mcp.internal/docs', vendor: '内容组', exposes: 5,
    status: 'online', calls: 5270, p95: '140 ms', owner: '—', timeout: '—' },
]

/** Skill 工具：8 个（其中 cve-scan 异常、lint-fix 已下线） */
export const SKILLS: readonly SkillTool[] = [
  { kind: 'skill', id: 'sk-01', name: 'table-diff', cat: '数据处理', desc: '两张表格做结构 + 数值差异比对并输出变更清单',
    transport: 'Python 3.12', endpoint: 'skills/table_diff.py', vendor: '数据平台组', exposes: 3,
    status: 'online', calls: 4820, p95: '2.1 s', owner: 'Report-Agent', timeout: '120s', version: '2.3.1' },
  { kind: 'skill', id: 'sk-02', name: 'doc-parse', cat: '文档处理', desc: 'PDF / Word 版式还原为结构化 Markdown',
    transport: 'Python 3.12', endpoint: 'skills/doc_parse.py', vendor: '内容组', exposes: 2,
    status: 'online', calls: 3640, p95: '4.6 s', owner: 'Ingest-Agent', timeout: '300s', version: '1.9.0' },
  { kind: 'skill', id: 'sk-03', name: 'sql-runner', cat: '数据处理', desc: '按白名单执行只读 SQL 并返回结果集',
    transport: 'Python 3.12', endpoint: 'skills/sql_runner.py', vendor: '数据平台组', exposes: 2,
    status: 'online', calls: 2915, p95: '1.4 s', owner: 'Report-Agent', timeout: '60s', version: '1.4.2' },
  { kind: 'skill', id: 'sk-04', name: 'chart-render', cat: '数据分析', desc: '按数据与图表类型渲染静态图表产物',
    transport: 'Node 22', endpoint: 'skills/chart_render.js', vendor: '可视化组', exposes: 1,
    status: 'online', calls: 2184, p95: '0.9 s', owner: 'Report-Agent', timeout: '45s', version: '3.1.0' },
  { kind: 'skill', id: 'sk-05', name: 'cve-scan', cat: '系统运维', desc: '依赖清单 CVE 扫描与修复优先级建议',
    transport: 'Python 3.12', endpoint: 'skills/cve_scan.py', vendor: '安全组', exposes: 2,
    status: 'degraded', calls: 962, p95: '18.2 s', owner: 'Code-Agent', timeout: '600s', version: '0.9.7' },
  { kind: 'skill', id: 'sk-06', name: 'sheet-merge', cat: '数据处理', desc: '多份表格按主键合并、去重与列对齐',
    transport: 'Python 3.12', endpoint: 'skills/sheet_merge.py', vendor: '数据平台组', exposes: 2,
    status: 'online', calls: 1573, p95: '3.2 s', owner: 'Report-Agent', timeout: '180s', version: '1.2.0' },
  { kind: 'skill', id: 'sk-07', name: 'kb-index', cat: '检索增强', desc: '文档切片、向量化并写入知识库索引',
    transport: 'Python 3.12', endpoint: 'skills/kb_index.py', vendor: '搜索组', exposes: 3,
    status: 'online', calls: 1128, p95: '9.4 s', owner: 'Search-Agent', timeout: '600s', version: '2.0.4' },
  { kind: 'skill', id: 'sk-08', name: 'lint-fix', cat: '代码工程', desc: '静态扫描并自动修复常见代码规范问题',
    transport: 'Node 22', endpoint: 'skills/lint_fix.js', vendor: 'DevOps 组', exposes: 1,
    status: 'offline', calls: 0, p95: '—', owner: 'Code-Agent', timeout: '90s', version: '0.6.1' },
]

/** 按 tab 取当前列表 */
export const TOOLS: { mcp: readonly McpTool[]; skill: readonly SkillTool[] } = {
  mcp: MCPS,
  skill: SKILLS,
}

export type ToolTab = 'mcp' | 'skill'

/** 页面级 UI 状态 */
export interface ToolsUi {
  tab: ToolTab
  filter: 'all' | ToolState
  cat: 'all' | string
  q: string
  /** 新建时的自增序号，用于生成 id 与默认名 */
  seq: number
}