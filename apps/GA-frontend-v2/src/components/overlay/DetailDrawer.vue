<!--
  详情抽屉 —— 等价迁移自原型 console.html 第 732–743 行 + console.js openDrawer()（673–1204）。

  九种形态（原型的 kind 参数）：
     session   会话详情：运行态 / 载体与编排 / 挂载的生产资料 / 实时日志 / 操作
     logs      日志汇总
     monitor   统一网关监控
     registry  镜像详情：基本信息 / 标签 / 多地域复制 / 操作
     model     模型详情：基本信息 / 部署与资源 / 调用趋势 / 操作
     tool      MCP 或 Skill 详情：基本信息 / 端点与能力 / 调用情况 / 操作
     kb        知识库详情：基本信息 / 切片与向量 / 调用情况 / 操作
     gw        网关详情：按 用户路由|容器实例|告警规则|访问日志 四态分支
     perm      权限详情：按 角色|账号|资源策略|提权工单 四态分支

  内容由各 store 的数据拼装（保留原型那把 kvHtml 的行结构），
  所以这里用 v-html —— 所有插入值都经过 esc() 转义。
-->
<script setup lang="ts">
import { computed } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import { useOverlayStore } from '@/stores/overlay'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useRegistryStore } from '@/stores/registry'
import { useModelsStore } from '@/stores/models'
import { useToolsStore } from '@/stores/tools'
import { useKbStore } from '@/stores/kb'
import { useGatewayStore } from '@/stores/gateway'
import { useAuthzStore } from '@/stores/authz'
import { esc, fmtDur, kv, kvGrid, stamp } from '@/lib/util'
import { ST } from '@/data/sessions'
import { REG } from '@/data/registry'
import { MOD, modCurve } from '@/data/models'
import { TSTCN } from '@/data/tools'
import { KBKIND, KBSTCN } from '@/data/kb'
import { GW_SEV } from '@/stores/gateway'
import { PZTABS } from '@/stores/authz'

const overlay = useOverlayStore()
const ui = useUiStore()
const session = useSessionStore()
const registry = useRegistryStore()
const models = useModelsStore()
const tools = useToolsStore()
const kb = useKbStore()
const gateway = useGatewayStore()
const authz = useAuthzStore()

const id = computed(() => overlay.drawerId)
const kind = computed(() => overlay.drawerKind)

/* 抽屉标题与「形态」小字 */
const title = computed(() => overlay.drawerTitle)
const kindText = computed(() => {
  switch (kind.value) {
    case 'session':
      return '会话详情 · SESSION'
    case 'logs':
      return '日志汇总 · LOGS'
    case 'monitor':
      return '统一网关监控 · GATEWAY'
    case 'registry':
      return '镜像详情 · IMAGE'
    case 'model':
      return '模型详情 · MODEL'
    case 'tool': {
      const t = tools.byId(id.value)
      return t?.kind === 'skill' ? 'Skill 详情 · SKILL' : 'MCP 详情 · MCP'
    }
    case 'kb': {
      const k = kb.byId(id.value)
      return `知识库详情 · ${k ? KBKIND[k.kind] : 'KB'}`
    }
    case 'gw': {
      const g = gateway.byId(id.value)
      return g?.tab === 'gwup'
        ? '容器实例 · CONTAINER'
        : g?.tab === 'gwalert'
          ? '告警规则 · ALERT'
          : g?.tab === 'gwlog'
            ? '访问日志 · ACCESS'
            : '用户路由 · ROUTE'
    }
    case 'perm': {
      const z = authz.byId(id.value)
      return z?.tab === 'role'
        ? '角色详情 · ROLE'
        : z?.tab === 'acct'
          ? '账号详情 · ACCOUNT'
          : z?.tab === 'pol'
            ? '资源策略详情 · POLICY'
            : '提权工单详情 · REQUEST'
    }
    default:
      return '详情'
  }
})

/** 各页共用的「操作」按钮组（原型的 actsHtml） */
interface DrawerAct {
  key: string
  label: string
  main?: boolean
}
function actsHtml(acts: readonly DrawerAct[]): string {
  return (
    '<div class="drawer__acts">' +
    acts
      .map(
        (a) =>
          `<button class="btn ${a.main ? 'btn--main' : 'btn--ghost'}" type="button" data-dact="${a.key}">` +
          (a.main ? `<span>${esc(a.label)}</span>` : esc(a.label)) +
          '</button>',
      )
      .join('') +
    '</div>'
  )
}

/** 会话的「按需挂载的 AI 生产资料」：按会话序号确定性派生（原型 mounts()） */
function mounts(idx: number): [string, string, string, string] {
  const MODELS = ['qwen2.5-72b-instruct', 'deepseek-v3', 'bge-m3', 'glm-4-plus']
  const SKILLS = ['table-diff', 'doc-parse', 'sql-runner', 'chart-render', 'cve-scan']
  const KBS = ['经营指标库', '制度规程库', '合同范本库', '运维手册库']
  const MCPS = ['fs-mcp', 'git-mcp', 'browser-mcp', 'sheet-mcp']
  return [
    MODELS[idx % MODELS.length]!,
    `${SKILLS[idx % SKILLS.length]} / ${SKILLS[(idx + 2) % SKILLS.length]}`,
    KBS[idx % KBS.length]!,
    `${MCPS[idx % MCPS.length]} / ${MCPS[(idx + 1) % MCPS.length]}`,
  ]
}

const sessionBody = computed(() => {
  const s = session.byId(id.value)
  if (!s) return ''
  const m = mounts(s.idx)
  const st = ST[s.state]
  return (
    '<section class="drawer__sec"><h4>运行态</h4>' +
    kvGrid([
      ['状态', `<span class="stchip ${st.cls}${st.blink ? ' is-blink' : ''}">${st.cn}</span>`],
      ['会话 ID', `<b>${esc(s.id)}</b>`],
      ['此刻任务', `<span data-live="task">${esc(s.task)}</span>`],
      ['进度', `<span data-live="prog">${s.prog}%</span>`],
      ['已运行', `<span data-live="dur">${esc(fmtDur(s.elapsed))}</span>`],
      ['优先级', `${esc(s.prio)} · 归属 ${esc(s.owner)}`],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>载体 / 编排</h4>' +
    kvGrid([
      ['智能体', esc(s.agent)],
      ['workspace', `<span data-live="ws">${esc(s.ws)}</span>`],
      ['基础镜像', 'registry.internal/agent-runtime:24.09'],
      ['CPU', esc(s.cpu)],
      ['GPU', `${esc(s.gpu)}（水位 ${s.gpuPct}%）`],
      ['内存', esc(s.mem)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>按需挂载的 AI 生产资料</h4>' +
    kvGrid([
      ['模型', esc(m[0])],
      ['技能', esc(m[1])],
      ['知识库', esc(m[2])],
      ['MCP', esc(m[3])],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>实时日志</h4>' +
    '<div class="drawer__logs" id="drawerLogs">' +
    s.logs
      .slice(-24)
      .map((l) => `<p><time>${l.t}</time><span class="lg-${l.lvl}">${esc(l.m)}</span></p>`)
      .join('') +
    '</div></section>' +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      { key: 'enter', label: '进入会话', main: true },
      { key: 'pause', label: '暂停' },
      { key: 'restart', label: '重启工位' },
      { key: 'audit', label: '查看审计' },
    ]) +
    '</section>'
  )
})

const registryBody = computed(() => {
  const im = registry.byId(id.value)
  if (!im) return ''
  const cfg = REG[im.status]
  return (
    '<section class="drawer__sec"><h4>基本信息</h4>' +
    kvGrid([
      ['镜像地址', `<b>${esc(`${im.repo}/${im.ns}/${im.name}`)}</b>`],
      ['状态', cfg.cn],
      ['最近标签', `${esc(im.tags[0]?.v ?? '—')} · ${esc(im.tags[0]?.size ?? '—')}`],
      ['digest', esc(im.digest)],
      ['架构', esc(im.arch)],
      ['层数 / 基础镜像', `${im.layers} 层 · ${esc(im.base)}`],
      ['累计拉取', `${im.pulls} 次 · 最近 ${esc(im.ago)}`],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>标签</h4>' +
    kvGrid(im.tags.map((t) => [`${t.v}${t.latest ? ' · latest' : ''}`, esc(t.size)] as [string, string])) +
    '</section>' +
    '<section class="drawer__sec"><h4>多地域复制</h4>' +
    kvGrid(
      im.copies.map(
        (c) =>
          [
            c,
            im.status === 'synced'
              ? '已就绪 · 校验通过'
              : im.status === 'syncing'
                ? `同步中 · ${im.prog}%`
                : im.status === 'failed'
                  ? '失败 · 等待重试'
                  : '未同步',
          ] as [string, string],
      ),
    ) +
    '</section>' +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      { key: 'regsync', label: im.status === 'syncing' ? '同步中…' : '立即同步', main: true },
      { key: 'regpull', label: '拉取到本地' },
      { key: 'regscan', label: '安全扫描' },
    ]) +
    '</section>'
  )
})

const modelBody = computed(() => {
  const mo = models.byId(id.value)
  if (!mo) return ''
  return (
    '<section class="drawer__sec"><h4>基本信息</h4>' +
    kvGrid([
      ['状态', MOD[mo.status].cn],
      ['家族 / 类型', `${esc(mo.family)} · ${esc(mo.type)}`],
      ['当前版本', esc(mo.ver)],
      ['参数规模', `${esc(mo.params)} · ${esc(mo.quant)}`],
      ['上下文窗口', esc(mo.ctx)],
      ['上线时间', esc(mo.from)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>部署与资源</h4>' +
    kvGrid([
      ['部署资源', esc(mo.res)],
      [
        '调用配额占用',
        mo.status === 'deployed' || mo.status === 'deploying' ? `${mo.load}%` : '—',
      ],
      ['当前 QPS', esc(mo.qps)],
      ['P95 时延', esc(mo.p95)],
      ['错误率', esc(mo.err)],
      ['今日 Token', esc(mo.tokens)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>调用趋势（近 12 小时）</h4>' +
    kvGrid(
      modCurve(mo, 3).map((v, k) => [`T-${11 - k}h`, `${v} 次/小时`] as [string, string]),
    ) +
    '</section>' +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      {
        key: 'moddeploy',
        label:
          mo.status === 'deploying' ? '部署中…' : mo.status === 'offline' ? '上线' : '重新部署',
        main: true,
      },
      { key: 'modprobe', label: '发起压测' },
      { key: 'modquota', label: '调整配额' },
    ]) +
    '</section>'
  )
})

const toolBody = computed(() => {
  const tl = tools.byId(id.value)
  if (!tl) return ''
  const isMcpTool = tl.kind === 'mcp'
  const rows: [string, string][] = [
    ['类型', isMcpTool ? 'MCP 服务' : 'Skill 工具'],
    ['状态', TSTCN[tl.status]],
    ['分类', esc(tl.cat)],
    ['描述', esc(tl.desc)],
    [isMcpTool ? '提供方' : '适用智能体', esc(isMcpTool ? tl.vendor : tl.owner)],
    [isMcpTool ? '接入方式' : '运行时', esc(tl.transport)],
  ]
  const rows2: [string, string][] = [
    [isMcpTool ? '端点' : '入口脚本', `<b>${esc(tl.endpoint)}</b>`],
    ['暴露能力', `${tl.exposes} 个`],
    [
      isMcpTool ? '调用配额' : '时长上限',
      isMcpTool ? (tl.status === 'offline' ? '已回收' : '标准 · 200 次/分') : esc(tl.timeout),
    ],
  ]
  if (tl.kind === 'skill') rows2.push(['版本', esc(tl.version)])

  return (
    '<section class="drawer__sec"><h4>基本信息</h4>' +
    kvGrid(rows) +
    '</section>' +
    `<section class="drawer__sec"><h4>${isMcpTool ? '端点与能力' : '脚本与配置'}</h4>` +
    kvGrid(rows2) +
    '</section>' +
    '<section class="drawer__sec"><h4>调用情况</h4>' +
    kvGrid([
      ['近 7 天调用', `${models.fmtNum(tl.calls)} 次`],
      ['P95 耗时', esc(tl.p95)],
      ['最近调用', tl.calls ? '4 分钟前 · Report-Agent' : '暂无调用记录'],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      { key: 'tooledit', label: '编辑配置', main: true },
      { key: 'tooltoggle', label: tl.status === 'offline' ? '上线' : '下线' },
      { key: 'toolprobe', label: '连通性探测' },
      { key: 'tooldel', label: '删除' },
    ]) +
    '</section>'
  )
})

const kbBody = computed(() => {
  const k = kb.byId(id.value)
  if (!k) return ''
  const stTag =
    k.status === 'ready'
      ? '就绪 · 索引最新'
      : k.status === 'indexing'
        ? `索引重建中 · ${k.prog}%`
        : k.status === 'paused'
          ? '已暂停 · 不再下发检索'
          : '异常 · 上次重建失败'
  return (
    '<section class="drawer__sec"><h4>基本信息</h4>' +
    kvGrid([
      ['类型', KBKIND[k.kind]],
      ['归属业务', esc(k.owner)],
      ['状态', stTag],
      ['语料范围', esc(k.scope)],
      ['语料 / 分片', `${models.fmtNum(k.docs)} 份 · ${models.fmtNum(k.chunks)} 个`],
      ['最近更新', esc(k.updated)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>切片与向量</h4>' +
    kvGrid([
      ['切片长度', esc(k.size)],
      ['重叠', esc(k.overlap)],
      ['切分方式', esc(k.win)],
      ['向量模型', esc(k.embed)],
      ['向量库', esc(k.store)],
      ['索引', esc(k.index)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>检索质量</h4>' +
    kvGrid([
      ['命中率', esc(k.hit)],
      ['召回 P95', esc(k.recall)],
      ['相似度口径', esc(k.metric)],
      ['今日检索', `${models.fmtNum(k.calls)} 次`],
      ['语言', esc(k.lang)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>说明</h4>' +
    `<p class="drawer__note">${esc(k.desc)}</p></section>` +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      { key: 'kbtest', label: '检索试跑', main: true },
      { key: 'kbedit', label: '编辑配置' },
      { key: 'kbrebuild', label: k.status === 'indexing' ? '重建中…' : '重建索引' },
      { key: 'kbtoggle', label: k.status === 'paused' ? '启用' : '暂停' },
      { key: 'kbdel', label: '删除' },
    ]) +
    '</section>'
  )
})

const gwBody = computed(() => {
  const g = gateway.byId(id.value)
  if (!g) return ''
  const chip = (cls: string, text: string): string => `<span class="stchip ${cls}">${text}</span>`
  const para = ui.pushHtml

  if (g.tab === 'gwup') {
    return (
      '<section class="drawer__sec"><h4>容器实例</h4>' +
      kvGrid([
        ['容器名', `<b>${esc(g.name)}</b>`],
        ['监听地址', `<code>${esc(g.addr)}</code>`],
        ['映射用户', esc(g.weight)],
        ['状态', g.status === 'ok' ? chip('is-ok', '正常') : g.status === 'warn' ? chip('is-warn is-blink', '告警') : chip('is-off', '停用')],
        ['镜像 / 版本', esc(g.ver)],
        ['数据根', `<code>${esc(g.dataRoot)}</code>`],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>运行指标</h4>' +
      kvGrid([
        ['连接占用', esc(g.conn)],
        ['CPU / 内存', `${esc(g.cpu)} · ${esc(g.mem)}`],
        ['QPS', esc(g.qps)],
        ['P95 时延', esc(g.p95)],
        ['错误率', esc(g.err)],
        ['最近心跳', esc(g.beat)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>生命周期</h4>' +
      kvGrid([
        ['端口映射', esc(g.ports)],
        ['重启策略', esc(g.restart)],
        ['承接状态', esc(g.drain)],
        ['健康判定', esc(g.health)],
        ['日志插件', esc(g.logPlugin)],
        ['日志量', esc(g.logs)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>说明</h4>' +
      `<p class="drawer__note">${esc(g.desc)}</p></section>` +
      '<section class="drawer__sec"><h4>操作</h4>' +
      actsHtml([
        { key: 'gwdetail', label: '查看容器日志', main: true },
        { key: 'gwping', label: '端口连通性探测' },
        { key: 'gwtoggle', label: g.status === 'off' ? '恢复承接流量' : '摘除流量' },
        { key: 'gwdel', label: '下线记录（不删容器）' },
      ]) +
      '</section>'
    )
  }

  if (g.tab === 'gwalert') {
    void para
    return (
      '<section class="drawer__sec"><h4>规则条件</h4>' +
      kvGrid([
        ['规则名称', `<b>${esc(g.name)}</b>`],
        ['监控对象', esc(g.target)],
        ['触发条件', esc(g.cond)],
        ['严重程度', `<span class="mfamily ${GW_SEV[g.cat] ?? 'is-llm'}">${esc(g.cat)}</span>`],
        ['聚合窗口 / 连续', `${esc(g.v1)} · ${esc(g.v2)}`],
        ['状态', g.status === 'ok' ? chip('is-ok', '正常') : g.status === 'warn' ? chip('is-warn is-blink', '告警') : chip('is-off', '停用')],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>通知与责任</h4>' +
      kvGrid([
        ['通知渠道', esc(g.notice)],
        ['负责人', esc(g.owner)],
        ['最近触发', esc(g.at)],
        ['触发频次', esc(g.runs)],
        ['确认状态', esc(g.ack)],
        ['静默', esc(g.mute)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>说明</h4>' +
      `<p class="drawer__note">${esc(g.desc)}</p></section>` +
      '<section class="drawer__sec"><h4>操作</h4>' +
      actsHtml([
        { key: 'gwdetail', label: '查看触发记录', main: true },
        { key: 'gwedit', label: '编辑规则' },
        { key: 'gwtoggle', label: g.status === 'off' ? '启用规则' : '停用规则' },
        { key: 'gwdel', label: '删除规则' },
      ]) +
      '</section>'
    )
  }

  if (g.tab === 'gwlog') {
    return (
      '<section class="drawer__sec"><h4>请求</h4>' +
      kvGrid([
        ['请求', `<b>${esc(g.method)} ${esc(g.path)}</b>`],
        ['请求号', `<code>${esc(g.rid)}</code>`],
        ['登录用户', esc(g.user)],
        ['客户端', esc(g.caller)],
        ['入口源', esc(g.entry)],
        ['时间', esc(g.at)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>链路与处置</h4>' +
      kvGrid([
        ['响应码', esc(g.code)],
        ['耗时', esc(g.cost)],
        ['处置', esc(g.gate)],
        ['回源', esc(g.hop)],
        ['状态', g.status === 'ok' ? chip('is-ok', '正常') : chip('is-warn is-blink', '异常')],
        ['流量', esc(g.size)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>说明</h4>' +
      `<p class="drawer__note">${esc(g.note)}</p></section>` +
      '<section class="drawer__sec"><h4>操作</h4>' +
      actsHtml([
        { key: 'gwdetail', label: '查看同请求号链路', main: true },
        { key: 'gwreplay', label: '重放该请求' },
      ]) +
      '</section>'
    )
  }

  /* 用户路由 */
  const route = g
  return (
    '<section class="drawer__sec"><h4>代理映射</h4>' +
    kvGrid([
      ['登录用户', `<b>${esc(route.name)}</b>`],
      ['映射容器', `<code>${esc(route.container)}</code>`],
      ['目标地址', `<code>${esc(route.target)}</code>`],
      ['入口源', esc(route.entry)],
      ['映射类型', esc(route.cat)],
      ['状态', route.status === 'ok' ? chip('is-ok', '正常') : route.status === 'warn' ? chip('is-warn is-blink', '告警') : chip('is-off', '停用')],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>令牌与会话</h4>' +
    kvGrid([
      ['登录 token', `<code>${esc(route.loginToken)}</code>`],
      ['令牌有效期', esc(route.token)],
      ['dsh 会话', esc(route.session)],
      ['鉴权方式', esc(route.auth)],
      ['会话缓存', esc(route.cache)],
      ['回源 Host', esc(route.ip)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>流量与保护</h4>' +
    kvGrid([
      ['请求数', esc(route.requests)],
      ['P95 时延', esc(route.p95)],
      ['错误率', esc(route.err)],
      ['入口限速', esc(route.limit)],
      ['取消防护', esc(route.fuse)],
      ['WebSocket', esc(route.ws)],
      ['最近访问', esc(route.lastReq)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>说明</h4>' +
    `<p class="drawer__note">${esc(route.desc)}</p></section>` +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      { key: 'gwdetail', label: '查看近期访问', main: true },
      { key: 'gwedit', label: '编辑映射' },
      { key: 'gwtoggle', label: route.status === 'off' ? '启用路由' : '停用路由' },
      { key: 'gwdel', label: '删除路由' },
    ]) +
    '</section>'
  )
})

const permBody = computed(() => {
  const z = authz.byId(id.value)
  if (!z) return ''
  const chip = (cls: string, text: string): string => `<span class="stchip ${cls}">${text}</span>`
  const zChip =
    z.status === 'ok' ? chip('is-ok', '正常') : z.status === 'warn' ? chip('is-warn is-blink', '告警') : chip('is-off', '停用')

  if (z.tab === 'role') {
    return (
      '<section class="drawer__sec"><h4>角色定义</h4>' +
      kvGrid([
        ['角色名称', `<b>${esc(z.name)}</b>`],
        ['角色类型', esc(z.cat)],
        ['数据范围', esc(z.scope)],
        ['成员数', esc(z.members)],
        ['状态', zChip],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>权限范围</h4>' +
      kvGrid([
        ['允许动作', esc(z.acts)],
        ['权限域', esc(z.domains)],
        ['生效期', esc(z.life)],
        ['强约束', esc(z.mfa)],
        ['审批人', esc(z.approver)],
        ['最近复核', esc(z.lastReview)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>风险与说明</h4>' +
      `<p class="drawer__note">${esc(z.risk)}。${esc(z.desc)}</p></section>` +
      '<section class="drawer__sec"><h4>操作</h4>' +
      actsHtml([
        { key: 'pzedit', label: '编辑角色', main: true },
        { key: 'pzreview', label: '发起复核' },
        { key: 'pztoggle', label: z.status === 'off' ? '启用角色' : '停用角色' },
        { key: 'pzdel', label: '删除角色' },
      ]) +
      '</section>'
    )
  }

  if (z.tab === 'acct') {
    return (
      '<section class="drawer__sec"><h4>账号信息</h4>' +
      kvGrid([
        ['账号', `<b>${esc(z.name)}</b>`],
        ['所属部门', esc(z.dept)],
        ['绑定角色', esc(z.role)],
        ['数据范围', esc(z.scope)],
        ['状态', zChip],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>安全与活动</h4>' +
      kvGrid([
        ['双因子', esc(z.mfa)],
        ['最近登录', esc(z.login)],
        ['允许动作', esc(z.acts)],
        ['可访问资源', esc(z.res)],
        ['有效期', esc(z.expire)],
        ['近期审计', esc(z.lastReview)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>风险与说明</h4>' +
      `<p class="drawer__note">${esc(z.risk)}。${esc(z.desc)}</p></section>` +
      '<section class="drawer__sec"><h4>操作</h4>' +
      actsHtml([
        { key: 'pzedit', label: '编辑账号', main: true },
        { key: 'pzreview', label: '查看审计流水' },
        { key: 'pztoggle', label: z.status === 'off' ? '恢复账号' : '停用账号' },
        { key: 'pzdel', label: '移除账号' },
      ]) +
      '</section>'
    )
  }

  if (z.tab === 'pol') {
    return (
      '<section class="drawer__sec"><h4>策略定义</h4>' +
      kvGrid([
        ['策略名称', `<b>${esc(z.name)}</b>`],
        ['资源匹配', `<code>${esc(z.res)}</code>`],
        ['效果', esc(z.effect)],
        ['优先级', esc(z.prio)],
        ['允许动作', esc(z.acts)],
        ['状态', zChip],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>命中条件</h4>' +
      kvGrid([
        ['生效条件', esc(z.cond)],
        ['生效范围', esc(z.applied)],
        ['最近命中', esc(z.hit)],
        ['有效期', esc(z.expire)],
      ]) +
      '</section>' +
      '<section class="drawer__sec"><h4>说明</h4>' +
      `<p class="drawer__note">${esc(z.desc)}</p></section>` +
      '<section class="drawer__sec"><h4>操作</h4>' +
      actsHtml([
        { key: 'pzedit', label: '编辑策略', main: true },
        { key: 'pzreview', label: '查看命中记录' },
        { key: 'pztoggle', label: z.status === 'off' ? '启用策略' : '停用策略' },
        { key: 'pzdel', label: '删除策略' },
      ]) +
      '</section>'
    )
  }

  /* 提权工单 */
  return (
    '<section class="drawer__sec"><h4>工单内容</h4>' +
    kvGrid([
      ['工单名称', `<b>${esc(z.name)}</b>`],
      ['申请人', esc(z.who)],
      ['申请资源', `<code>${esc(z.res)}</code>`],
      ['申请动作', esc(z.acts)],
      ['时限', esc(z.life)],
      ['状态', zChip],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>审批链</h4>' +
    kvGrid([
      ['审批人', esc(z.approver)],
      ['当前环节', esc(z.stage)],
      ['提交时间', esc(z.at)],
      ['剩余时限', esc(z.due)],
    ]) +
    '</section>' +
    '<section class="drawer__sec"><h4>风险与说明</h4>' +
    `<p class="drawer__note">${esc(z.risk)}。${esc(z.desc)}</p></section>` +
    '<section class="drawer__sec"><h4>操作</h4>' +
    actsHtml([
      { key: 'pzedit', label: '编辑工单', main: true },
      { key: 'pzreview', label: '催办审批' },
      { key: 'pztoggle', label: z.status === 'off' ? '恢复受理' : '驳回工单' },
      { key: 'pzdel', label: '删除工单' },
    ]) +
    '</section>'
  )
})

/** 日志汇总 / 网关监控两种「只读」形态 */
const logsBody = computed(() => {
  const list = session.allLogs(40)
  return (
    '<section class="drawer__sec"><h4>全部会话日志（最近 40 条）</h4>' +
    '<div class="drawer__logs">' +
    list
      .map((l) => `<p><time>${l.t}</time><span class="lg-${l.lvl}">${esc(l.m)}</span></p>`)
      .join('') +
    '</div></section>'
  )
})

const monitorBody = computed(() => {
  const rows = [
    ['入口状态', `<span class="stchip is-ok">正常</span>`],
    ['今日已鉴权请求', esc(gateway.kpis.req)],
    ['命中会话缓存', esc(gateway.kpis.cacheHit)],
    ['反代成功率', esc(gateway.kpis.ok)],
    ['反代平均 P95', esc(gateway.kpis.p95)],
    ['活跃告警', String(gateway.kpis.alert)],
    ['已就绪容器', `${gateway.kpis.up} / ${gateway.kpis.upAll}`],
    ['用户路由', `${gateway.kpis.routeOk} 个已映射容器`],
  ]
  return (
    '<section class="drawer__sec"><h4>统一网关</h4>' +
    kvGrid(rows as [string, string][]) +
    '</section>' +
    '<section class="drawer__sec"><h4>最近告警</h4>' +
    '<div class="drawer__logs">' +
    gateway.alerts
      .filter((a) => a.status === 'warn')
      .map(
        (a) =>
          `<p><time>${esc(a.at)}</time><span class="lg-warn">${esc(a.name)} · ${esc(a.cond)}</span></p>`,
      )
      .join('') +
    '</div></section>'
  )
})

const body = computed(() => {
  switch (kind.value) {
    case 'session':
      return sessionBody.value
    case 'logs':
      return logsBody.value
    case 'monitor':
      return monitorBody.value
    case 'registry':
      return registryBody.value
    case 'model':
      return modelBody.value
    case 'tool':
      return toolBody.value
    case 'kb':
      return kbBody.value
    case 'gw':
      return gwBody.value
    case 'perm':
      return permBody.value
    default:
      return ''
  }
})

/* 抽屉里的操作按钮：原型用 data-dact 事件委托分发（5590–5640） */
function onActs(e: MouseEvent): void {
  const btn = (e.target as HTMLElement | null)?.closest('[data-dact]')
  if (!btn) return
  const act = btn.getAttribute('data-dact')
  const sid = id.value
  switch (act) {
    case 'enter':
      if (sid) session.enterSession(sid)
      break
    case 'pause':
      if (sid) session.pauseSession(sid)
      break
    case 'restart':
      if (sid) session.restartSession(sid)
      break
    case 'audit':
      ui.pushText('审计流水', ['该会话近 30 天的全部操作已导出', `会话：${title.value}`])
      break
    case 'regsync':
      if (sid) registry.startSync(sid)
      break
    case 'regpull':
      ui.pushText('开始拉取镜像', [`目标：${title.value}`, '拉取任务已入队，完成后会回到就绪态'])
      break
    case 'regscan':
      ui.pushText('安全扫描已提交', [`目标：${title.value}`, `${stamp()} 起开始扫描，结果写入审计流水`])
      break
    case 'moddeploy':
      if (sid) models.startDeploy(sid)
      break
    case 'modprobe':
      ui.pushText('压测任务已提交', [`目标：${title.value}`, '按 200 并发跑 5 分钟，完成后出报告'])
      break
    case 'modquota':
      ui.pushText('打开配额调整', [`目标：${title.value}`, '调整后对新请求生效，已在跑的会话不受影响'])
      break
    case 'tooledit':
      overlay.openModal('tool', sid, null)
      break
    case 'tooltoggle':
      if (sid) tools.toggle(sid)
      break
    case 'toolprobe':
      ui.pushText('连通性探测完成', [`目标：${title.value}`, '握手成功，能力清单与注册表一致'])
      break
    case 'tooldel':
      if (sid) tools.askDelete(sid)
      break
    case 'kbtest':
      kb.openAsk(sid ?? undefined)
      kb.runAsk()
      break
    case 'kbedit':
      overlay.openModal('kb', sid, null)
      break
    case 'kbrebuild':
      if (sid) kb.startIndex(sid)
      break
    case 'kbtoggle':
      if (sid) kb.toggle(sid)
      break
    case 'kbdel':
      if (sid) kb.askDelete(sid)
      break
    case 'gwdetail':
      ui.pushText('链路明细', [`目标：${title.value}`, '已按请求号聚合出最近 20 条链路'])
      break
    case 'gwedit':
      overlay.openModal('gw', sid, null)
      break
    case 'gwping':
      gateway.ping()
      break
    case 'gwreplay':
      ui.pushText('已重放该请求', ['使用同一条会话 cookie 从入口重放', '结果已写入访问日志'])
      break
    case 'gwtoggle':
      if (sid) gateway.toggle(sid)
      break
    case 'gwdel':
      if (sid) gateway.askDelete(sid)
      break
    case 'pzedit':
      overlay.openModal('perm', sid, null)
      break
    case 'pzreview':
      authz.review()
      break
    case 'pztoggle':
      if (sid) authz.toggle(sid)
      break
    case 'pzdel':
      if (sid) authz.askDelete(sid)
      break
    default:
      ui.pushText('演示操作', [`动作：${act ?? '未知'}`, `对象：${title.value}`])
  }
}

/** 抽屉打开时同步会话选中态（原型 openDrawer 里 R.selId = s.id） */
function onClose(): void {
  overlay.closeDrawer()
}

/* 这两张表只用于抽屉标题的兜底文案（KBSTCN / PZTABS 已在 kindText 里用到） */
void KBSTCN
void PZTABS
</script>

<template>
  <aside
    class="drawer"
    id="drawer"
    aria-label="详情面板"
    :class="{ 'is-on': overlay.drawerOpen }"
    :aria-hidden="!overlay.drawerOpen"
  >
    <header class="drawer__head">
      <div>
        <p class="drawer__kind" id="drawerKind">{{ kindText }}</p>
        <h3 id="drawerTitle">{{ title }}</h3>
      </div>
      <button class="iconbtn" id="drawerClose" type="button" aria-label="关闭" @click="onClose">
        <IconSprite name="i-x" />
      </button>
    </header>
    <div class="drawer__body" id="drawerBody" v-html="body" @click="onActs" />
  </aside>
</template>