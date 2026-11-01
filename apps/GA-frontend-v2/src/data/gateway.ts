/* ============================================================================
   网关数据 —— 等价迁移自原型 console.js 第 3238–3446 行。

   本页对齐真实部署（见 dsh-plugin/proxy/server.js 与 docker/dsh-docker/dsh-new.sh）：
     · 前置 proxy 是唯一入口：静态登录页 + 按登录用户把请求（含 WebSocket）
       反代到该用户自己的 dsh 容器
     · 容器由 dsh-new.sh 拉起，--network host，端口只绑 127.0.0.1，不走 docker 映射
     · 启动令牌（docker logs 里打印的 ?token=）由代理在服务端换成签名会话 cookie
   所以这里的四张表分别是：ROUTES 用户路由 / 容器实例 / 告警规则 / 访问日志。
   ========================================================================== */

export type GwStatus = 'ok' | 'warn' | 'off'

/** 用户路由：代理侧 ROUTES[登录用户] → http://127.0.0.1:<端口>/ */
export interface GwRoute {
  id: string
  tab: 'gwroute'
  /** 登录用户（ROUTES 的键） */
  name: string
  status: GwStatus
  /** 映射类型：固定映射 / 新建待注册 / 只读回放 / 已摘除 */
  cat: string
  /** 表格分组标识（用户路由上就是入口源） */
  cluster: string
  desc: string
  /** 容器启动日志里打印的启动令牌 */
  loginToken: string
  /** 目标容器名（dsh-new.sh 的 <Name>） */
  container: string
  /** 回源地址 */
  target: string
  /** 入口源（proxy 的 ENTRY_ORIGIN） */
  entry: string
  /** dsh 会话状态 */
  session: string
  auth: string
  /** 会话缓存是否已落盘 */
  cache: string
  ip: string
  home: string
  ws: string
  /** 日请求量，可能是 '6.2k' 这类字符串 */
  requests: string
  p95: string
  err: string
  limit: string
  fuse: string
  /** 通知渠道（表单可改；原型里是 f.elements.gwNotice 的回填目标） */
  notice?: string
  /**
   * 回源地址去掉 scheme 与尾斜杠后的形式（'127.0.0.1:8083'）。
   * 由表单提交时从 target 派生，供表格的「回源地址」列与入口源筛选使用。
   */
  addr?: string
  token: string
  lastReq: string
}

/** 容器实例：dsh-new.sh 拉起的实例，端口只绑 127.0.0.1 */
export interface GwUp {
  id: string
  tab: 'gwup'
  name: string
  status: GwStatus
  cat: string
  /** 监听地址 */
  cluster: string
  desc: string
  addr: string
  ver: string
  /** 映射的用户 */
  weight: string
  /** 连接占用 '18 / 200' */
  conn: string
  cpu: string
  mem: string
  qps: string
  p95: string
  err: string
  /** 心跳时间 */
  beat: string
  drain: string
  health: string
  /** 数据根 */
  dataRoot: string
  image: string
  ports: string
  restart: string
  token: string
  tokenFile: string
  logPlugin: string
  logs: string
}

/** 告警规则：全部围绕实例可用性与令牌/会话有效性的真实故障模式 */
export interface GwAlert {
  id: string
  tab: 'gwalert'
  name: string
  status: GwStatus
  /** 严重度：P1 严重 / P2 警告 / P3 提示 */
  cat: string
  cluster: string
  desc: string
  /** 监控对象 */
  target: string
  /** 触发条件 */
  cond: string
  cl1: string
  v1: string
  cl2: string
  v2: string
  notice: string
  owner: string
  at: string
  runs: string
  ack: string
  mute: string
}

/** 访问日志：浏览器 → 入口 → 鉴权门 → 容器 */
export interface GwLog {
  id: string
  tab: 'gwlog'
  status: GwStatus
  /** 'GET /api/login' 形式 */
  name: string
  method: string
  path: string
  entry: string
  /** 登录用户 */
  user: string
  caller: string
  code: string
  cost: string
  rid: string
  /** 处置：同源校验拒绝 / 会话缺失 · 401 / 跳转登录 / 放行 */
  gate: string
  hop: string
  at: string
  size: string
  note: string
}

export type GwRow = GwRoute | GwUp | GwAlert | GwLog
export type GwTab = 'gwroute' | 'gwup' | 'gwalert' | 'gwlog'

/* ---- 访问日志：浏览器 → 入口 → 鉴权门 → 容器，确定性生成 14 条 ---- */
interface AccessSeed {
  path: string
  m: string
  code: number
  ms: number
  note: string
}

export const ACCESS_POOL: readonly AccessSeed[] = [
  { path: '/', m: 'GET', code: 200, ms: 18, note: '登录页（静态资源，代理直接回）' },
  { path: '/api/login', m: 'POST', code: 303, ms: 42, note: '校验通过，下发 token cookie' },
  { path: '/console.html', m: 'GET', code: 200, ms: 26, note: '已注入 dsh-auth-* 会话，回源成功' },
  { path: '/api/stream', m: 'GET', code: 200, ms: 312, note: 'SSE 流式对话，会话复用命中' },
  { path: '/', m: 'GET', code: 401, ms: 6, note: '容器返回 401：启动令牌已换，会话需刷新' },
  { path: '/api/fs/list', m: 'POST', code: 200, ms: 74, note: '文件树读取，回环 Host 改写生效' },
  { path: '/api/terminal/ws', m: 'GET', code: 101, ms: 58, note: 'WebSocket 升级成功，双向透传' },
  { path: '/api/login', m: 'POST', code: 403, ms: 3, note: 'Origin 与入口源不一致，同源校验拦截' },
  { path: '/api/agent/run', m: 'POST', code: 200, ms: 2210, note: '长任务受理，回写 12 KB' },
  { path: '/', m: 'GET', code: 303, ms: 9, note: '未登录访问首页，跳转登录' },
  { path: '/api/mcp/call', m: 'POST', code: 200, ms: 96, note: 'MCP 工具调用，changeOrigin 改写 Host' },
  { path: '/api/login', m: 'POST', code: 200, ms: 38, note: '错误口令，返回登录页错误态' },
  { path: '/api/terminal/ws', m: 'GET', code: 502, ms: 4, note: '目标容器已停止，上游不可达' },
  { path: '/metrics', m: 'GET', code: 404, ms: 2, note: '代理不暴露指标端点（端口仅本机可达）' },
]

const CALLERS = ['浏览器 · Chrome', '浏览器 · Edge', 'cli · curl'] as const

export const ACCESSLOGS: GwLog[] = ACCESS_POOL.map((t, i) => {
  const st: GwStatus = t.code >= 500 ? 'warn' : t.code === 401 || t.code === 403 ? 'warn' : 'ok'
  const hh = String(9 + Math.floor(i / 4)).padStart(2, '0')
  const mm = String((i * 7 + 3) % 60).padStart(2, '0')
  const ss = String((i * 13 + 5) % 60).padStart(2, '0')
  /* 事件编号顺序与 server.js 的处置顺序一致：同源校验 → 登录校验 → 会话确保 → 反代 */
  return {
    id: `gw-lg${i + 1}`,
    tab: 'gwlog',
    status: st,
    name: `${t.m} ${t.path}`,
    method: t.m,
    path: t.path,
    entry: i % 4 === 0 ? '172.16.235.50' : '172.16.235.50:80',
    user: ['a', 'b', 'c'][i % 3]!,
    caller: CALLERS[i % 3]!,
    code: String(t.code),
    cost: t.ms ? `${t.ms} ms` : '—',
    rid: `req-${(0x51c3 + i * 811).toString(16)}`,
    gate:
      t.code === 403
        ? '同源校验拒绝'
        : t.code === 401
          ? '会话缺失 · 401'
          : t.code === 303
            ? '跳转登录'
            : '放行',
    hop: `127.0.0.1:${8083 + (i % 3)}`,
    at: `${hh}:${mm}:${ss}`,
    size: `${1 + i * 2} KB / ${2 + i * 3} KB`,
    note: t.note,
  }
})

export interface GwTabMeta {
  kind: string
  item: string
  icon: string
  ph: string
}

export const GWTABS: Record<GwTab, GwTabMeta> = {
  gwroute: {
    kind: 'gwroute', item: '用户路由', icon: 'i-cube',
    ph: '搜索登录用户 / 目标实例 / 入口源',
  },
  gwup: { kind: 'gwup', item: '容器实例', icon: 'i-pulse', ph: '搜索容器名 / 端口 / 数据根 / 镜像' },
  gwalert: { kind: 'gwalert', item: '告警规则', icon: 'i-gauge', ph: '搜索规则 / 监控对象 / 责任人' },
  gwlog: { kind: 'gwlog', item: '访问日志', icon: 'i-term', ph: '搜索路径 / 用户 / 请求号 / 处置' },
}

/* ---- 代理用户路由：ROUTES（用户 → 容器）+ 登录 token + 会话缓存 ---- */
export const GWROUTES: GwRoute[] = [
  { id: 'gw-01', tab: 'gwroute', name: 'a', status: 'ok',
    cat: '固定映射', cluster: '172.16.235.50:80', desc: '最早接入的测试用户，映射到 dsh-web-a，会话缓存与容器令牌一致',
    loginToken: 'tok-a-8f3c1d', container: 'dsh-web-a', target: 'http://127.0.0.1:8083/', entry: '172.16.235.50:80',
    session: 'dsh-auth-a=9c1f…（缓存命中）', auth: 'Bearer 启动令牌 · 已交换会话 cookie',
    cache: 'sessions.json 已落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '/console.html · 401 即视为就绪', ws: '101 升级成功 · 双向透传',
    requests: '6.2k', p95: '96 ms', err: '0.3%', limit: '入口限速 6000 QPS / 单 IP 300',
    fuse: '同源校验拒绝 · 错误率 30% 暂停', token: '有效（30 天）', lastReq: '12 秒前' },
  { id: 'gw-02', tab: 'gwroute', name: 'b', status: 'ok',
    cat: '固定映射', cluster: '172.16.235.50:80', desc: '与 a 同规格的隔离实例，数据根独立，互不可见',
    loginToken: 'tok-b-2e7a45', container: 'dsh-web-b', target: 'http://127.0.0.1:8084/', entry: '172.16.235.50:80',
    session: 'dsh-auth-b=41de…（缓存命中）', auth: 'Bearer 启动令牌 · 已交换会话 cookie',
    cache: 'sessions.json 已落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '/console.html · 401 即视为就绪', ws: '101 升级成功 · 双向透传',
    requests: '4.8k', p95: '88 ms', err: '0.2%', limit: '入口限速 6000 QPS / 单 IP 300',
    fuse: '同源校验拒绝 · 错误率 30% 暂停', token: '有效（30 天）', lastReq: '34 秒前' },
  { id: 'gw-03', tab: 'gwroute', name: 'c', status: 'ok',
    cat: '固定映射', cluster: '172.16.235.50:80', desc: '与 a 同规格的隔离实例，数据根独立，互不可见',
    loginToken: 'tok-c-77b902', container: 'dsh-web-c', target: 'http://127.0.0.1:8085/', entry: '172.16.235.50:80',
    session: 'dsh-auth-c=7a2c…（缓存命中）', auth: 'Bearer 启动令牌 · 已交换会话 cookie',
    cache: 'sessions.json 已落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '/console.html · 401 即视为就绪', ws: '101 升级成功 · 双向透传',
    requests: '5.1k', p95: '102 ms', err: '0.4%', limit: '入口限速 6000 QPS / 单 IP 300',
    fuse: '同源校验拒绝 · 错误率 30% 暂停', token: '有效（30 天）', lastReq: '51 秒前' },
  { id: 'gw-04', tab: 'gwroute', name: 'dsh-web2', status: 'warn',
    cat: '新建待注册', cluster: '172.16.235.50:80', desc: '刚用 dsh-new.sh 拉起，代理侧 ROUTES 还没加上去，暂时进不来',
    loginToken: 'tok-d-1c05fe', container: 'dsh-web2', target: 'http://127.0.0.1:8083/', entry: '172.16.235.50:80',
    session: '尚未建立（需先在 ROUTES 里注册）', auth: '启动令牌已写入 tokens.d，等待代理加载',
    cache: '未落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '/console.html · 401 即视为就绪', ws: '未连接',
    requests: '0', p95: '—', err: '—', limit: '未纳入入口限速',
    fuse: '未生效', token: '有效（30 天）', lastReq: '尚未访问' },
  { id: 'gw-05', tab: 'gwroute', name: 'e', status: 'ok',
    cat: '固定映射', cluster: '172.16.235.50:80', desc: '运维专用账号，容器数据根单独一份，仅值班人员使用',
    loginToken: 'tok-e-93ad10', container: 'dsh-ops', target: 'http://127.0.0.1:8086/', entry: '172.16.235.50:80',
    session: 'dsh-auth-e=b8f0…（缓存命中）', auth: 'Bearer 启动令牌 · 已交换会话 cookie',
    cache: 'sessions.json 已落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '/console.html · 401 即视为就绪', ws: '101 升级成功 · 双向透传',
    requests: '1.4k', p95: '134 ms', err: '0.1%', limit: '入口限速 2000 QPS / 单 IP 120',
    fuse: '同源校验拒绝 · 错误率 30% 暂停', token: '有效（30 天）', lastReq: '6 分钟前' },
  { id: 'gw-06', tab: 'gwroute', name: 'report', status: 'warn',
    cat: '只读回放', cluster: '172.16.235.50:80', desc: '报表回放账号，只放行 GET，POST 一律 403',
    loginToken: 'tok-r-40e7aa', container: 'dsh-report', target: 'http://127.0.0.1:8087/', entry: '172.16.235.50:80',
    session: 'dsh-auth-r=30d1…（缓存命中）', auth: '只读白名单 · 会话 cookie 只允许 GET',
    cache: 'sessions.json 已落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '/console.html · 401 即视为就绪', ws: '已禁用（只读账号不开终端）',
    requests: '860', p95: '78 ms', err: '0.0%', limit: '入口限速 1200 QPS / 单 IP 60',
    fuse: '写操作直接 403', token: '有效（30 天）', lastReq: '18 分钟前' },
  { id: 'gw-07', tab: 'gwroute', name: 'qa', status: 'off',
    cat: '已摘除', cluster: '172.16.235.50:80', desc: '压测专用账号，本轮压测结束后已从 ROUTES 摘除',
    loginToken: 'tok-q-6b2f81', container: 'dsh-qa', target: 'http://127.0.0.1:8088/', entry: '172.16.235.50:80',
    session: '已从 sessions.json 清除', auth: '令牌文件已删除',
    cache: '未落盘', ip: '127.0.0.1（host 网络 · 真实回环）',
    home: '—', ws: '—',
    requests: '0', p95: '—', err: '—', limit: '已回收',
    fuse: '已停用', token: '已撤销', lastReq: '3 天前' },
]

/* ---- dsh 容器实例：dsh-new.sh 拉起的实例，端口只绑 127.0.0.1 ---- */
export const GWUPS: GwUp[] = [
  { id: 'gw-up1', tab: 'gwup', name: 'dsh-web-a', status: 'ok', cat: 'dsh web',
    cluster: '127.0.0.1:8083', desc: 'dsh web --port 8083，--network host，仅本机代理可达',
    addr: '127.0.0.1:8083', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 a',
    conn: '18 / 200', cpu: '12%', mem: '410 MB', qps: '1.4k', p95: '96 ms', err: '0.3%',
    beat: '6 秒前', drain: '正常承接', health: '就绪（首页 401 = 认证墙已生效）',
    dataRoot: '/srv/dsh/dsh-data-dsh-web-a', image: 'dsh:latest',
    ports: '127.0.0.1:8083（无 docker 映射，host 网络）', restart: 'unless-stopped',
    token: 'tok-a-8f3c1d', tokenFile: 'tokens.d/a', logPlugin: 'logger-console（level 2）', logs: '18 行' },
  { id: 'gw-up2', tab: 'gwup', name: 'dsh-web-b', status: 'ok', cat: 'dsh web',
    cluster: '127.0.0.1:8084', desc: 'dsh web --port 8084，数据根与 a 完全隔离',
    addr: '127.0.0.1:8084', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 b',
    conn: '14 / 200', cpu: '9%', mem: '388 MB', qps: '1.1k', p95: '88 ms', err: '0.2%',
    beat: '8 秒前', drain: '正常承接', health: '就绪（首页 401 = 认证墙已生效）',
    dataRoot: '/srv/dsh/dsh-data-dsh-web-b', image: 'dsh:latest',
    ports: '127.0.0.1:8084（无 docker 映射，host 网络）', restart: 'unless-stopped',
    token: 'tok-b-2e7a45', tokenFile: 'tokens.d/b', logPlugin: 'logger-console（level 2）', logs: '16 行' },
  { id: 'gw-up3', tab: 'gwup', name: 'dsh-web-c', status: 'ok', cat: 'dsh web',
    cluster: '127.0.0.1:8085', desc: 'dsh web --port 8085，数据根与 a / b 隔离',
    addr: '127.0.0.1:8085', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 c',
    conn: '21 / 200', cpu: '15%', mem: '452 MB', qps: '1.6k', p95: '102 ms', err: '0.4%',
    beat: '4 秒前', drain: '正常承接', health: '就绪（首页 401 = 认证墙已生效）',
    dataRoot: '/srv/dsh/dsh-data-dsh-web-c', image: 'dsh:latest',
    ports: '127.0.0.1:8085（无 docker 映射，host 网络）', restart: 'unless-stopped',
    token: 'tok-c-77b902', tokenFile: 'tokens.d/c', logPlugin: 'logger-console（level 2）', logs: '23 行' },
  { id: 'gw-up4', tab: 'gwup', name: 'dsh-ops', status: 'ok', cat: 'dsh web',
    cluster: '127.0.0.1:8086', desc: '运维专用实例，日志级别调到 debug 便于排障',
    addr: '127.0.0.1:8086', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 e',
    conn: '7 / 100', cpu: '6%', mem: '296 MB', qps: '240', p95: '134 ms', err: '0.1%',
    beat: '5 秒前', drain: '正常承接', health: '就绪（首页 401 = 认证墙已生效）',
    dataRoot: '/srv/dsh/dsh-data-dsh-ops', image: 'dsh:latest',
    ports: '127.0.0.1:8086（无 docker 映射，host 网络）', restart: 'unless-stopped',
    token: 'tok-e-93ad10', tokenFile: 'tokens.d/e', logPlugin: 'logger-console（level 3 · debug）', logs: '64 行' },
  { id: 'gw-up5', tab: 'gwup', name: 'dsh-report', status: 'ok', cat: 'dsh web',
    cluster: '127.0.0.1:8087', desc: '只读回放实例，入口侧按方法白名单二次收紧',
    addr: '127.0.0.1:8087', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 report',
    conn: '3 / 100', cpu: '4%', mem: '264 MB', qps: '120', p95: '78 ms', err: '0.0%',
    beat: '11 秒前', drain: '正常承接（仅 GET）', health: '就绪（首页 401 = 认证墙已生效）',
    dataRoot: '/srv/dsh/dsh-data-dsh-report', image: 'dsh:latest',
    ports: '127.0.0.1:8087（无 docker 映射，host 网络）', restart: 'unless-stopped',
    token: 'tok-r-40e7aa', tokenFile: 'tokens.d/report', logPlugin: 'logger-console（level 0 · 只留 error）', logs: '4 行' },
  { id: 'gw-up6', tab: 'gwup', name: 'dsh-web2', status: 'warn', cat: 'dsh web',
    cluster: '127.0.0.1:8083', desc: '与 dsh-web-a 端口冲突，后起的这个实际没绑定成功',
    addr: '127.0.0.1:8083', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 dsh-web2',
    conn: '0 / 200', cpu: '2%', mem: '96 MB', qps: '0', p95: '—', err: '—',
    beat: '2 分钟前', drain: '已摘除流量', health: '端口占用 · 容器在但未监听（EADDRINUSE）',
    dataRoot: '/srv/dsh/dsh-data-dsh-web2', image: 'dsh:latest',
    ports: '127.0.0.1:8083（与 dsh-web-a 冲突）', restart: 'unless-stopped',
    token: 'tok-d-1c05fe', tokenFile: 'tokens.d/dsh-web2', logPlugin: 'logger-console（level 2）', logs: '9 行' },
  { id: 'gw-up7', tab: 'gwup', name: 'dsh-qa', status: 'off', cat: 'dsh web',
    cluster: '127.0.0.1:8088', desc: '压测实例，压测结束后已 docker stop，数据根保留',
    addr: '127.0.0.1:8088', ver: 'dsh 0.1.2 · dsh:latest', weight: '用户 qa（已摘）',
    conn: '0 / 500', cpu: '0%', mem: '0 MB', qps: '0', p95: '—', err: '—',
    beat: '3 天前', drain: '已停止', health: '容器已停止（docker stop），可用 docker start 恢复',
    dataRoot: '/srv/dsh/dsh-data-dsh-qa', image: 'dsh:latest',
    ports: '127.0.0.1:8088（容器已停，端口释放）', restart: 'unless-stopped',
    token: '已移除', tokenFile: 'tokens.d/qa（已删除）', logPlugin: '未启用', logs: '—' },
]

/* ---- 告警规则：覆盖容器不可达 / 令牌失效 / 5xx / 证书到期 / WS 重连 / 跨源拦截 ---- */
export const GWALERTS: GwAlert[] = [
  { id: 'gw-al1', tab: 'gwalert', name: '容器实例不可达', status: 'ok', cat: 'P1 严重',
    cluster: '全部容器', desc: '代理到目标端口的连接被拒或超时，用户会直接打不开控制台',
    target: '全部 dsh-web-*', cond: '连接失败 / 连续 3 次超时',
    cl1: '聚合窗口', v1: '2 分钟', cl2: '连续次数', v2: '3 次',
    notice: '值班群 + 短信', owner: '平台运维', at: '6 小时前触发', runs: '近 30 天触发 2 次',
    ack: '已确认', mute: '未静默' },
  { id: 'gw-al2', tab: 'gwalert', name: '启动令牌失效 / 会话未刷新', status: 'warn', cat: 'P2 警告',
    cluster: '全部容器', desc: '容器重启后启动令牌会变，tokens.d 未及时 refresh，表现为首页 401',
    target: 'tokens.d/* 与 sessions.json', cond: '首页连续返回 401 且令牌校验失败',
    cl1: '聚合窗口', v1: '5 分钟', cl2: '连续次数', v2: '5 次',
    notice: '值班群', owner: '平台运维', at: '41 分钟前触发', runs: '近 30 天触发 7 次',
    ack: '待确认', mute: '未静默' },
  { id: 'gw-al3', tab: 'gwalert', name: '反代 5xx 比例超阈值', status: 'ok', cat: 'P2 警告',
    cluster: '172.16.235.50:80', desc: '容器内部报错经代理回传为 5xx，通常是插件异常或容器 OOM',
    target: '前置 proxy', cond: '5xx 比例 > 1% 持续 5 分钟',
    cl1: '聚合窗口', v1: '5 分钟', cl2: '连续次数', v2: '2 次',
    notice: '邮件 + 值班群', owner: '平台运维', at: '2 天前触发', runs: '近 30 天触发 3 次',
    ack: '已关闭', mute: '未静默' },
  { id: 'gw-al4', tab: 'gwalert', name: '入口证书到期', status: 'ok', cat: 'P2 警告',
    cluster: '172.16.235.50:80', desc: '入口域名证书到期会直接中断所有用户访问，提前 30 / 7 / 1 天提醒',
    target: '172.16.235.50 入口证书', cond: '剩余有效期 < 30 天',
    cl1: '聚合窗口', v1: '1 天', cl2: '连续次数', v2: '1 次',
    notice: '邮件 + 值班群', owner: '信息安全部', at: '12 天前触发', runs: '近 30 天触发 1 次',
    ack: '已关闭', mute: '未静默' },
  { id: 'gw-al5', tab: 'gwalert', name: 'WebSocket 频繁重连', status: 'warn', cat: 'P3 提示',
    cluster: '全部容器', desc: '对话页依赖 WS，容器重启或会话丢失会造成客户端反复重连',
    target: '/api/terminal/ws · /api/stream', cond: '重连 > 5 次 / 10 分钟',
    cl1: '聚合窗口', v1: '10 分钟', cl2: '连续次数', v2: '2 次',
    notice: '值班群', owner: '平台运维', at: '17 分钟前触发', runs: '近 30 天触发 11 次',
    ack: '待确认', mute: '未静默' },
  { id: 'gw-al6', tab: 'gwalert', name: '跨源请求被大量拦截', status: 'off', cat: 'P2 警告',
    cluster: '172.16.235.50:80', desc: '入口源变更（ENTRY_ORIGIN）后旧域名会被同源校验全量拒绝，规则暂由人工巡检替代',
    target: 'sameOriginGuard', cond: '403（同源校验）> 100 次 / 分钟',
    cl1: '聚合窗口', v1: '1 分钟', cl2: '连续次数', v2: '1 次',
    notice: '值班群', owner: '平台运维', at: '1 个月前触发', runs: '近 30 天触发 0 次',
    ack: '已关闭', mute: '已静默' },
]