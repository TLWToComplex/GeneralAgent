/* ============================================================================
   资产页卡片渲染 —— 等价迁移自原型 console.js 的四段卡片拼装

     · 1559–1620  renderRegCards()   镜像卡（regrow：身份 / 六项元信息 / 同步与操作）
     · 1887–1962  renderModCards()   模型卡（modrow：身份 / 12 小时曲线 / 规格与操作）
     · 2254–2301  renderTools()      工具卡（toolrow：名称描述 / 接入配置 / 调用与操作）
     · 2767–2820  renderKbCards()    知识库卡（kbrow：语料 / 切片向量 / 命中与操作）

    这些卡片都是「一行铺满 + 三档信息带」的固定结构，用字符串拼装最直观，
    也与原型一一对应（改一处即对一处）。所有插入内容都过 esc()。
    视图层用 v-html 输出，事件用 data-* 属性 + 事件委托。
   ========================================================================== */

import { bigNum, card, chipOf, esc, fam, kv, kvGrid, tag } from '@/lib/util'
import type { ImageStatus, RegistryImage } from '@/data/registry'
import { REG } from '@/data/registry'
import type { ModelItem } from '@/data/models'
import { MFAM, MOD, MST, modCurve, modLine } from '@/data/models'
import type { ToolItem } from '@/data/tools'
import { TCAT, TST, TSTCN } from '@/data/tools'
import type { AiTool } from '@/data/aitools'
import { AICHANNEL, AIKIND, AIST } from '@/data/aitools'
import type { KbItem } from '@/data/kb'
import { KBCLS, KBKIND, KBST, KBSTCN } from '@/data/kb'
import { REG_ST } from '@/stores/registry'
import type { GwRow } from '@/data/gateway'
import type { PermRecord } from '@/data/authz'

/* ---------------------------------------------------------------- 小工具 */

const svg = (name: string): string =>
  `<svg class="ic" aria-hidden="true"><use href="#${name}"/></svg>`

/** 状态胶囊：--st 变量由各卡自行给出（对齐原型的 style="--st:..."） */
const chip = (text: string, stVar: string, blink = false): string =>
  `<span class="stchip${blink ? ' is-blink' : ''}" data-role="st" style="--st:${stVar}">${text}</span>`

/** 索引进度条 */
const progBar = (pct: number): string =>
  `<div class="regcard__prog"><i style="width:${pct}%"></i></div>`

const emptyOf = (text: string): string => `<p class="view__empty">${text}</p>`

/* ---------------------------------------------------------------- 镜像卡 */

/** 状态 → 进度条/徽标的颜色变量（原型 1573–1574） */
export function regCardsHtml(list: readonly RegistryImage[]): string {
  if (!list.length) return emptyOf('没有匹配的镜像，换个关键词或切回「全部」。')

  return list
    .map((m) => {
      const cn = REG[m.status].cn
      const cls = REG[m.status].cls
      const stvar = REG_ST[m.status]
      const tags = m.tags
        .slice(0, 3)
        .map(
          (t) =>
            `<span class="tagchip${t.latest ? ' is-latest' : ''}">${esc(t.v)}<em>${esc(t.size)}</em></span>`,
        )
        .join('')
      const more = m.tags.length > 3 ? `<i class="regcard__more">+${m.tags.length - 3}</i>` : ''
      const canSync = m.status === 'outdated' || m.status === 'failed'
      const prog = m.status === 'syncing' ? progBar(m.prog) : ''

      return (
        `<article class="regcard regrow ${cls}${m.status === 'syncing' ? ' is-syncing' : ''}" data-id="${m.id}" role="listitem">` +
        /* ① 身份与版本标签 */
        '<div class="regrow__id">' +
        '<div class="regcard__top">' +
        `<span class="regcard__ico">${svg('i-cube')}</span>` +
        `<span class="regcard__name"><b>${esc(m.name)}</b><i>${esc(m.repo)}/${esc(m.ns)}</i></span>` +
        chip(cn, stvar, m.status === 'syncing') +
        '</div>' +
        `<div class="regcard__tags">${tags}${more}</div>` +
        '</div>' +
        /* ② 六项元信息（三列两行） */
        '<div class="regcard__meta regrow__meta">' +
        `<span><i>最近标签</i><b>${esc(m.tags[0]?.v ?? '—')}</b></span>` +
        `<span><i>体积</i><b>${esc(m.tags[0]?.size ?? '—')}</b></span>` +
        `<span><i>基础镜像</i><b>${esc(m.base)}</b></span>` +
        `<span><i>架构 / 层数</i><b>${esc(m.arch)} · ${m.layers} 层</b></span>` +
        `<span><i>digest</i><b>${esc(m.digest)}</b></span>` +
        `<span><i>复制到</i><b>${esc(m.copies.join(' / '))}</b></span>` +
        '</div>' +
        /* ③ 进度 / 拉取情况 + 操作 */
        '<div class="regrow__side">' +
        `<p class="kpi__delta" data-role="delta">${
          m.status === 'syncing'
            ? `同步进度 ${m.prog}%`
            : `${m.pulls} 次拉取 · 最近 ${esc(m.ago)}`
        }</p>` +
        prog +
        '<div class="regcard__acts">' +
        `<button type="button" data-ract="sync"${canSync ? '' : ' disabled'}>${svg('i-restart')}${
          m.status === 'syncing' ? '同步中' : '同步'
        }</button>` +
        `<button type="button" data-ract="detail">${svg('i-eye')}详情</button>` +
        `<button type="button" data-ract="pull">${svg('i-download')}拉取</button>` +
        '</div>' +
        '</div>' +
        '</article>'
      )
    })
    .join('')
}

/* ---------------------------------------------------------------- 模型卡 */

/** 近 12 小时调用趋势的面积路径（原型 modArea） */
function modArea(vals: number[]): string {
  return `${modLine(vals)} L100 32 L0 32 Z`
}

export function modCardsHtml(list: readonly ModelItem[]): string {
  if (!list.length) return emptyOf('没有匹配的模型，换个关键词或切回「全部」。')

  return list
    .map((m, i) => {
      const cfg = MOD[m.status]
      const stv = MST[m.status]
      const live = m.status === 'deployed' || m.status === 'deploying'
      const vals = modCurve(m, i)
      const bar = m.status === 'deploying' ? progBar(m.load) : ''
      const canDeploy = m.status === 'offline' || m.status === 'degraded'
      const deployTxt =
        m.status === 'deploying' ? '部署中…' : m.status === 'offline' ? '上线' : '重新部署'

      return (
        `<article class="regcard modrow ${cfg.cls}${m.status === 'deploying' ? ' is-deploying' : ''}" data-id="${m.id}" role="listitem" style="--st:${stv}">` +
        /* ① 身份与实时状态 */
        '<div class="modrow__id">' +
        '<div class="regcard__top">' +
        `<span class="regcard__ico">${svg('i-model')}</span>` +
        `<span class="regcard__name"><b>${esc(m.name)}</b><i>${esc(m.family)} · ${esc(m.ver)}</i></span>` +
        chip(cfg.cn, stv, m.status === 'deploying') +
        '</div>' +
        '<div class="regcard__tags">' +
        `<span class="mfamily ${MFAM[m.type] ?? ''}">${esc(m.type)}</span>` +
        `<span class="tagchip">上下文 <em>${esc(m.ctx)}</em></span>` +
        `<span class="tagchip">精度 <em>${esc(m.quant)}</em></span>` +
        '</div>' +
        bar +
        '<div class="modrow__kv">' +
        `<span>调用配额占用<b data-role="quota">${live ? `${m.load}%` : '—'}</b></span>` +
        `<span>当前 QPS<b data-role="qps">${esc(m.qps)}</b></span>` +
        `<span>已上线<b>${
          m.status === 'deploying' ? '部署中' : m.status === 'offline' ? '—' : esc(m.from)
        }</b></span>` +
        '</div>' +
        '</div>' +
        /* ② 近 12 小时调用曲线 */
        '<div class="modrow__trend">' +
        '<div class="mchart__head"><span>近 12 小时调用</span>' +
        `<b data-role="calls">${fmtNumShort(m.calls)} 次</b></div>` +
        '<svg class="mchart" viewBox="0 0 100 32" preserveAspectRatio="none" aria-hidden="true">' +
        `<path class="mchart__area" d="${modArea(vals)}"></path>` +
        `<path class="mchart__line" d="${modLine(vals)}"></path>` +
        '</svg>' +
        `<div class="mchart__meta"><span>今日 Token <b>${esc(m.tokens)}</b></span>` +
        `<span>部署资源 <b>${esc(m.res)}</b></span></div>` +
        '</div>' +
        /* ③ 规格 / 资源 / 操作 */
        '<div class="modrow__side">' +
        '<div class="mspecs">' +
        `<span class="mspec">规格 <b>${esc(m.params)}</b></span>` +
        `<span class="mspec">资源 <b>${esc(m.res)}</b></span>` +
        `<span class="mspec">P95 <b>${esc(m.p95)}</b></span>` +
        `<span class="mspec">错误率 <b>${esc(m.err)}</b></span>` +
        '</div>' +
        '<div class="regcard__acts">' +
        `<button type="button" data-mact="deploy"${
          canDeploy || m.status === 'deploying' ? '' : ' disabled'
        }>${svg('i-play')}${deployTxt}</button>` +
        `<button type="button" data-mact="detail">${svg('i-eye')}详情</button>` +
        `<button type="button" data-mact="probe">${svg('i-pulse')}压测</button>` +
        (m.status === 'offline'
          ? ''
          : `<button type="button" data-mact="offline">${svg('i-minus')}下线</button>`) +
        '</div>' +
        '</div>' +
        '</article>'
      )
    })
    .join('')
}

/** 调用量缩写（≥1 万折成 "w"），与 stores/models.ts 的 fmtNum 同口径 */
function fmtNumShort(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}w` : String(n)
}

/* ---------------------------------------------------------------- 工具卡 */

export function toolCardsHtml(list: readonly ToolItem[], isMcp: boolean): string {
  if (!list.length) {
    const kind = isMcp ? ' MCP 服务' : ' Skill 工具'
    const btn = isMcp ? '新增 MCP' : '新增 Skill'
    return emptyOf(`没有匹配的${kind}，换个关键词、切个分类，或点「${btn}」新建一个。`)
  }

  return list
    .map((t) => {
      const stv = TST[t.status]
      const catCls = TCAT[t.cat] ?? ''
      const canToggle = t.status !== 'offline'
      /* 原型按 tab 决定列名，这里按条目的判别式取，两者始终一致 */
      const asMcp = t.kind === 'mcp'
      const owner = asMcp ? t.vendor : t.owner
      const sub = asMcp
        ? `${esc(t.transport)} · ${esc(t.vendor)}`
        : `${esc(t.version)} · ${esc(t.owner)}`

      return (
        `<article class="regcard toolrow ${
          t.status === 'degraded' ? 's-warn' : t.status === 'offline' ? 's-fail' : 's-idle'
        }" data-id="${t.id}" role="listitem" style="--st:${stv}">` +
        /* ① 名称与描述 */
        '<div class="regrow__id">' +
        '<div class="regcard__top">' +
        `<span class="regcard__ico">${svg(asMcp ? 'i-plug' : 'i-spark')}</span>` +
        `<span class="regcard__name"><b>${esc(t.name)}</b><i>${sub}</i></span>` +
        chip(TSTCN[t.status], stv, t.status === 'degraded') +
        '</div>' +
        '<div class="regcard__tags">' +
        `<span class="mfamily ${catCls}">${esc(t.cat)}</span>` +
        `<span class="tagchip">暴露 <em>${t.exposes}</em></span>` +
        (asMcp ? '' : `<span class="tagchip">超时 <em>${esc(t.timeout)}</em></span>`) +
        '</div>' +
        `<p class="regcard__desc">${esc(t.desc)}</p>` +
        '</div>' +
        /* ② 接入与配置 */
        '<div class="toolrow__cfg regrow__meta">' +
        `<span><i>${asMcp ? '接入方式' : '运行时'}</i><b>${esc(t.transport)}</b></span>` +
        `<span><i>${asMcp ? '提供方' : '适用智能体'}</i><b>${esc(owner)}</b></span>` +
        `<span class="is-wide"><i>${asMcp ? '端点' : '入口脚本'}</i><b class="toolrow__endpoint">${esc(
          t.endpoint,
        )}</b></span>` +
        `<span><i>P95 耗时</i><b data-role="p95">${esc(t.p95)}</b></span>` +
        `<span><i>调用配额</i><b>${t.status === 'offline' ? '已回收' : '标准 · 200 次/分'}</b></span>` +
        '</div>' +
        /* ③ 调用情况与操作 */
        '<div class="regrow__side">' +
        '<div class="toolrow__calls">' +
        `<b data-role="calls">${fmtNumShort(t.calls)}</b><span>次调用 · 近 7 天</span>` +
        '</div>' +
        '<div class="regcard__acts">' +
        `<button type="button" data-tact="edit">${svg('i-tool')}编辑</button>` +
        `<button type="button" data-tact="detail">${svg('i-eye')}详情</button>` +
        `<button type="button" data-tact="toggle">${svg(canToggle ? 'i-minus' : 'i-play')}${
          canToggle ? '下线' : '上线'
        }</button>` +
        `<button type="button" data-tact="del">${svg('i-x')}删除</button>` +
        '</div>' +
        '</div>' +
        '</article>'
      )
    })
    .join('')
}

/* ---------------------------------------------------------------- AI 工具卡 */

/**
 * AI 工具卡（工具平台 AI 工具标签页）。
 *
 * 骨架仍是 .regcard.toolrow 的三档信息带 —— 与 MCP / Skill 卡同一套列名，
 * 只是内容口径换成了「客户端软件」：
 *   ① 工具与定位（形态标签、渠道、版本 / 体积 / 流程步数）
 *   ② 安装与配置（六项键值，与 data/aitools.ts 的 cfg 一一对应）
 *   ③ 下发与操作（累计下发次数 + 安装流程 / 复制配置 / 领取安装包）
 *
 * 按钮用 data-aiact，与 data-tact / data-ract 一样走 v-html 的事件委托
 * （落点在 RichHtml 上，见 ToolPlatformView 的 onCards）。
 */
export function aiToolCardsHtml(list: readonly AiTool[]): string {
  if (!list.length) return emptyOf('没有匹配的 AI 工具，换个关键词或切回「全部」。')

  return list
    .map((t) => {
      const kind = AIKIND[t.kind]
      const st = AIST[t.state]
      const cfg = t.cfg
        .map(([k, v]) => `<span><i>${esc(k)}</i><b>${esc(v)}</b></span>`)
        .join('')
      const tags = t.tags.map(([k, v]) => tag(k, v)).join('')
      /* 有安装包 → 领取安装包；没有（命令行形态）→ 复制安装命令 */
      const dl = t.files.length
        ? `<button type="button" data-aiact="dl">${svg('i-download')}领取安装包</button>`
        : `<button type="button" data-aiact="cmd">${svg('i-term')}复制安装命令</button>`

      return (
        `<article class="regcard toolrow airow ${t.state === 'preview' ? 's-warn' : 's-idle'}" data-ai="${t.id}" role="listitem" style="--st:${st.v}">` +
        /* ① 工具与定位 */
        '<div class="regrow__id">' +
        '<div class="regcard__top">' +
        `<span class="regcard__ico">${svg(kind.icon)}</span>` +
        `<span class="regcard__name"><b>${esc(t.name)}</b><i>${esc(t.sub)}</i></span>` +
        chip(st.cn, st.v, t.state === 'preview') +
        '</div>' +
        '<div class="regcard__tags">' +
        `<span class="mfamily ${kind.cls}">${esc(kind.cn)}</span>` +
        `<span class="tagchip">渠道 <em>${esc(AICHANNEL[t.channel])}</em></span>` +
        tags +
        '</div>' +
        `<p class="regcard__desc">${esc(t.desc)}</p>` +
        '</div>' +
        /* ② 安装与配置 */
        `<div class="toolrow__cfg regrow__meta">${cfg}</div>` +
        /* ③ 下发与操作 */
        '<div class="regrow__side">' +
        '<div class="toolrow__calls">' +
        `<b data-role="dl">${t.downloads}</b><span>次下发 · 本页累计</span>` +
        '</div>' +
        `<p class="kpi__delta">装机流程 ${t.steps.length} 步 · ${esc(t.eta)}</p>` +
        '<div class="regcard__acts">' +
        `<button type="button" data-aiact="guide">${svg('i-play')}安装流程</button>` +
        `<button type="button" data-aiact="cfg">${svg('i-tool')}复制配置</button>` +
        dl +
        '</div>' +
        '</div>' +
        '</article>'
      )
    })
    .join('')
}

/* ---------------------------------------------------------------- 知识库卡 */

/** 原型 kbNum：万位折算 */
function kbNumShort(n: number): string {
  return n >= 10000 ? `${(n / 10000).toFixed(1)}w` : String(n)
}

export function kbCardsHtml(list: readonly KbItem[]): string {
  if (!list.length) {
    return emptyOf('没有匹配的知识库，换个关键词、切个归属，或点「新建知识库」创建一个。')
  }

  return list
    .map((k) => {
      const stv = KBST[k.status]
      const progress =
        k.status === 'indexing' || (k.status === 'failed' && k.prog > 0) ? progBar(k.prog) : ''

      return (
        `<article class="regcard kbrow ${
          k.status === 'failed'
            ? 's-fail'
            : k.status === 'paused'
              ? 's-queue'
              : k.status === 'indexing'
                ? 's-running'
                : 's-idle'
        }" data-id="${k.id}" role="listitem" style="--st:${stv}">` +
        /* ① 知识库与语料 */
        '<div class="regrow__id">' +
        '<div class="regcard__top">' +
        `<span class="regcard__ico">${svg('i-book')}</span>` +
        `<span class="regcard__name"><b>${esc(k.name)}</b><i>${esc(k.owner)} · ${esc(k.lang)}</i></span>` +
        chip(
          KBSTCN[k.status] + (k.status === 'indexing' ? ` ${k.prog}%` : ''),
          stv,
          k.status === 'indexing',
        ) +
        '</div>' +
        '<div class="regcard__tags">' +
        `<span class="mfamily ${KBCLS[k.kind] ?? ''}">${KBKIND[k.kind]}</span>` +
        (k.rows ? `<span class="tagchip">条目 <em>${kbNumShort(k.rows)}</em></span>` : '') +
        `<span class="tagchip">分片 <em>${kbNumShort(k.chunks)}</em></span>` +
        '</div>' +
        `<p class="regcard__desc">${esc(k.desc)}</p>` +
        `<span class="kbrow__stat"><b data-role="docs">${kbNumShort(k.docs)}</b>` +
        `<span>份语料 · 更新于 ${esc(k.updated)}</span></span>` +
        '</div>' +
        /* ② 切片与向量化 */
        '<div class="toolrow__cfg regrow__meta kbrow__cfg">' +
        `<span><i>切片长度 / 重叠</i><b>${esc(k.size)} / ${esc(k.overlap)}</b></span>` +
        `<span><i>切分方式</i><b>${esc(k.win)}</b></span>` +
        `<span class="is-wide"><i>向量模型</i><b>${esc(k.embed)}</b></span>` +
        `<span class="is-wide"><i>向量库 / 索引</i><b class="kbrow__store">${esc(k.store)}</b></span>` +
        `<span><i>相似度度量</i><b>${esc(k.metric)}</b></span>` +
        `<span><i>召回 P95</i><b data-role="recall">${esc(k.recall)}</b></span>` +
        `<span class="is-wide"><i>语料范围</i><b>${esc(k.scope)}</b></span>` +
        '</div>' +
        /* ③ 命中与操作 */
        '<div class="regrow__side">' +
        '<div class="kbrow__hit">' +
        `<span>命中率</span><b data-role="hit">${esc(k.hit)}</b>` +
        '</div>' +
        '<div class="toolrow__calls">' +
        `<b data-role="calls">${kbNumShort(k.calls)}</b><span>次检索 · 近 7 天</span>` +
        '</div>' +
        progress +
        '<div class="regcard__acts">' +
        `<button type="button" data-kact="test">${svg('i-search')}试跑</button>` +
        `<button type="button" data-kact="edit">${svg('i-tool')}编辑</button>` +
        `<button type="button" data-kact="detail">${svg('i-eye')}详情</button>` +
        `<button type="button" data-kact="toggle">${svg(
          k.status === 'paused' ? 'i-play' : 'i-pause',
        )}${k.status === 'paused' ? '恢复' : '暂停'}</button>` +
        `<button type="button" data-kact="del">${svg('i-x')}删除</button>` +
        '</div>' +
        '</div>' +
        '</article>'
      )
    })
    .join('')
}

/* ---------------------------------------------------------------- 运维页离屏卡片

   网关与权限中心的主视图是「面板 + 明细表」，卡片只作为兼容层留在 #gwGrid / #pzGrid
   （hidden + .gwcardbin{display:none}），供导出 / 打印与回归测试复用。
   等价迁移自原型 gwBands 3565–3639 与 pzBands 4395–4449。

   三档信息带：① 身份（regcard__top + 标签 + 描述 + 大数）
              ② 元信息（.regrow__meta 里成对的 kv）
              ③ 操作与备注（opcard__acts + opcard__note）
   ---------------------------------------------------------------------- */

/** 卡片头部（原型 gwHead 3558–3564） */
function opsHead(name: string, ico: string, sub: string, status: string): string {
  return (
    '<div class="regcard__top">' +
    `<span class="regcard__ico">${svg(ico)}</span>` +
    `<span class="regcard__name"><b>${esc(name)}</b><i>${esc(sub)}</i></span>` +
    chipOf(status) +
    '</div>'
  )
}

/** 卡片上的四操作按钮（原型 gwActions 3549–3557，data 前缀 gact / pact） */
function opsActs(status: string, act: string): string {
  return (
    '<div class="opcard__acts">' +
    `<button type="button" data-${act}="detail">${svg('i-eye')}详情</button>` +
    `<button type="button" data-${act}="edit">${svg('i-tool')}编辑</button>` +
    `<button type="button" data-${act}="toggle">${svg(
      status === 'off' ? 'i-play' : 'i-pause',
    )}${status === 'off' ? '启用' : '停用'}</button>` +
    `<button type="button" data-${act}="del">${svg('i-x')}删除</button>` +
    '</div>'
  )
}

const note = (html: string): string => `<p class="kpi__delta opcard__note">${html}</p>`

/* ---------------------------------------------------------------- 网关卡片 */

export function gwCardsHtml(list: readonly GwRow[]): string {
  if (!list.length) {
    return emptyOf('没有匹配的记录，换个关键词、切个筛选，或点右上角新建一条。')
  }

  return list
    .map((g) => {
      let bands: [string, string, string]

      if (g.tab === 'gwroute') {
        bands = [
          opsHead(g.name, 'i-cube', `${g.target} · ${g.container}`, g.status) +
            '<div class="regcard__tags">' +
            fam(g.cat) +
            tag('容器', g.container) +
            `<span class="tagchip">请求 <em data-role="qps">${esc(g.requests)}</em></span>` +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            bigNum('反代 P95', g.p95),

          kvGrid([
            ['登录用户', g.name],
            ['目标实例', `${g.container} → ${g.target}`],
            ['登录 token', g.loginToken],
            ['入口源', g.entry],
            ['会话状态', g.session],
            ['令牌有效期', g.token],
          ]),

          opsActs(g.status, 'gact') +
            note(`错误率 <b>${esc(g.err)}</b> · ${esc(g.ws)} · 最近访问 ${esc(g.lastReq)}`),
        ]
      } else if (g.tab === 'gwup') {
        bands = [
          opsHead(g.name, 'i-pulse', `${g.addr} · ${g.image}`, g.status) +
            '<div class="regcard__tags">' +
            fam(g.cat) +
            tag('版本', g.ver) +
            tag('映射用户', g.weight) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            `<div class="opstat"><span>承载 QPS</span><b data-role="qps">${esc(g.qps)}</b></div>`,

          kvGrid([
            ['监听地址', g.ports],
            ['数据根', g.dataRoot],
            ['启动令牌', `${g.token}（${g.tokenFile}）`],
            ['重启策略', g.restart],
            ['连接数', g.conn],
            ['CPU / 内存', `${g.cpu} / ${g.mem}`],
            ['P95 时延', g.p95],
            ['心跳', g.beat],
          ]),

          opsActs(g.status, 'gact') + note(`${esc(g.health)} · ${esc(g.drain)}`),
        ]
      } else if (g.tab === 'gwalert') {
        bands = [
          opsHead(g.name, 'i-gauge', g.target, g.status) +
            '<div class="regcard__tags">' +
            fam(g.cat) +
            tag('窗口', g.v1) +
            tag('连续', g.v2) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            `<p class="opcard__cond"><i>触发条件</i>${esc(g.cond)}</p>`,

          kvGrid([
            ['监控对象', g.target],
            ['聚合窗口 / 连续', `${g.v1} · ${g.v2}`],
            ['通知渠道', g.notice],
            ['负责人', g.owner],
            ['最近触发', g.at],
            ['触发频次', g.runs],
          ]),

          opsActs(g.status, 'gact') + note(`${esc(g.ack)} · ${esc(g.mute)}`),
        ]
      } else {
        /* 访问日志（原型 3614–3638） */
        const codeCls = /^5/.test(g.code) ? 'is-bad' : /^4/.test(g.code) ? 'is-warn' : 'is-ok'
        bands = [
          '<div class="regcard__top">' +
            `<span class="regcard__ico">${svg('i-term')}</span>` +
            `<span class="regcard__name"><b>${esc(g.name)}</b><i>${esc(
              `${g.method} ${g.path}`,
            )}</i></span>` +
            `<span class="trace__code ${codeCls}">${esc(g.code)}</span>` +
            '</div>' +
            '<div class="regcard__tags">' +
            fam(g.method) +
            tag('耗时', g.cost) +
            tag('用户', g.user) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.note)}</p>` +
            `<span class="trace__at">${esc(g.at)} · ${esc(g.hop)}</span>`,

          kvGrid([
            ['处置', g.gate],
            ['请求号', g.rid],
            ['来源', g.entry],
            ['客户端', g.caller],
            ['入 / 出大小', g.size],
          ]),

          opsActs(g.status, 'gact') + note(`响应 ${esc(g.code)} · 端到端 ${esc(g.cost)}`),
        ]
      }

      return card(g.status, g.id, bands)
    })
    .join('')
}

/* ---------------------------------------------------------------- 权限中心卡片 */

export function pzCardsHtml(list: readonly PermRecord[]): string {
  if (!list.length) {
    return emptyOf('没有匹配的记录，换个关键词、切个筛选，或点右上角新建一条。')
  }

  return list
    .map((g) => {
      let bands: [string, string, string]

      if (g.tab === 'role') {
        bands = [
          opsHead(g.name, 'i-shield', `${g.scope} · ${g.members}`, g.status) +
            '<div class="regcard__tags">' +
            fam(g.cat) +
            tag('数据范围', g.scope) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            bigNum('账号数', g.members.replace(' 个账号', '')),

          kvGrid([
            ['允许动作', g.acts],
            ['权限域', g.domains],
            ['生效期', g.life],
            ['强约束', g.mfa],
            ['审批人', g.approver],
            ['最近复核', g.lastReview],
          ]),

          opsActs(g.status, 'pact') + note(esc(g.risk)),
        ]
      } else if (g.tab === 'acct') {
        bands = [
          opsHead(g.name, 'i-agent', `${g.dept} · ${g.role}`, g.status) +
            '<div class="regcard__tags">' +
            fam(g.dept) +
            tag('角色', g.role) +
            tag('数据范围', g.scope) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            `<span class="trace__at">最近登录 ${esc(g.login)}</span>`,

          kvGrid([
            ['所属部门', g.dept],
            ['数据范围', g.scope],
            ['双因子', g.mfa],
            ['允许动作', g.acts],
            ['可访问资源', g.res],
            ['有效期', g.expire],
          ]),

          opsActs(g.status, 'pact') + note(`${esc(g.risk)} · ${esc(g.lastReview)}`),
        ]
      } else if (g.tab === 'pol') {
        bands = [
          opsHead(g.name, 'i-cube', `${g.scope} · ${g.prio}`, g.status) +
            '<div class="regcard__tags">' +
            fam(g.effect) +
            tag('动作', g.acts) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            `<p class="opcard__cond"><i>资源匹配</i>${esc(g.res)}</p>`,

          kvGrid([
            ['效果', g.effect],
            ['优先级', g.prio],
            ['命中生效', g.cond],
            ['生效范围', g.applied],
            ['最近命中', g.hit],
            ['负责人 / 复核', `${g.owner} · ${g.lastReview}`],
          ]),

          opsActs(g.status, 'pact') + note(esc(g.expire)),
        ]
      } else {
        /* 提权工单（原型 4437–4448） */
        bands = [
          opsHead(g.name, 'i-term', `${g.who} · ${g.cat}`, g.status) +
            '<div class="regcard__tags">' +
            fam(g.cat) +
            tag('时限', g.life) +
            '</div>' +
            `<p class="regcard__desc">${esc(g.desc)}</p>` +
            `<span class="trace__at">${esc(g.at)} · ${esc(g.due)}</span>`,

          kvGrid([
            ['申请人', g.who],
            ['申请资源', g.res],
            ['申请动作', g.acts],
            ['时限', g.life],
            ['审批链', g.approver],
            ['当前环节', g.stage],
          ]),

          opsActs(g.status, 'pact') + note(esc(g.risk)),
        ]
      }

      return card(g.status, g.id, bands)
    })
    .join('')
}