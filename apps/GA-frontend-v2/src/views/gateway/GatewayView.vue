<!--
  网关 —— 等价迁移自原型 console.html 475–598 + console.js 3490（KPI）/ 3929–4000（三块面板）。

  页面结构（原型即「控制台仪表盘」风格，不用卡片）：
    .reg__bar     页头：标题 + 概览指标 + 容器巡检 / 新建
    .reg__filters 四个 tab（用户路由 / 容器实例 / 告警规则 / 访问日志）+ 状态胶囊 + 搜索 + 入口源
    .gwgrid       ① 反代流量折线 ② 容器就绪环形 ③ 会话与连接水位
    .gtable       明细表（列定义见 @/lib/gwcols）
                 另含离屏卡片仓 #gwGrid，供导出 / 打印与回归测试复用
-->
<script setup lang="ts">
import { computed } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import OpsTable from '@/components/OpsTable.vue'
import RichHtml from '@/components/RichHtml.vue'
import { gwCardsHtml } from '@/lib/cards'
import { gwCols } from '@/lib/gwcols'
import { esc, kpiStrip } from '@/lib/util'
import { areaOf, pathOf, ringDash } from '@/lib/viz'
import { useGatewayStore } from '@/stores/gateway'
import { useOverlayStore } from '@/stores/overlay'
import { useHeartbeat } from '@/composables/useHeartbeat'
import type { GwStatus, GwTab } from '@/data/gateway'

const gw = useGatewayStore()
const overlay = useOverlayStore()
useHeartbeat(() => 'gateway')

/* 四个视图 tab（原型 console.html 497–508） */
const TABS: readonly { tab: GwTab; label: string; icon: string }[] = [
  { tab: 'gwroute', label: '用户路由', icon: 'i-cube' },
  { tab: 'gwup', label: '容器实例', icon: 'i-pulse' },
  { tab: 'gwalert', label: '告警规则', icon: 'i-gauge' },
  { tab: 'gwlog', label: '访问日志', icon: 'i-term' },
]

const filters = computed(() => [
  { value: 'all', label: '全部', count: gw.counts.all },
  { value: 'ok', label: '正常', count: gw.counts.ok },
  { value: 'warn', label: '异常', count: gw.counts.warn },
  { value: 'off', label: '停用', count: gw.counts.off },
])

/*
  四张概览卡。文案与卡片分工严格对齐原型 renderGwKpis（3490–3522）+ updateGwKpis（3523–3546）：
    [queue]   i-cube   数字 = 今日已鉴权请求(19x.xw)   副行 = 命中会话缓存 N / M 条
    [dist]    i-shield 数字 = 反代成功率(99.xx%)       副行 = 5xx 具体占比
    [gpu]     i-gauge  数字 = 反代平均 P95(1xx ms)     副行 = N 个用户已映射容器
    [running] i-pulse  数字 = 活跃告警                 副行 = N / M 个容器已就绪

  ⚠️ 文案长度被卡宽硬约束，改文案前先算一遍：
      .reg-kpis .kpi 是 flex-basis:176px，卡内一行可用宽度 ≈
      min-width(0) 下 176 - 22(图标) - 14(gap) - 26(padding) ≈ 114px，
      按 .kpi__delta 的 10px 字号换算就是「11 个汉字」或「7 汉字 + 6 个 ASCII」的量级
      （汉字 10px/字，ASCII 约 6.6px/字符，等宽数字 11.4px/字符）。
      这里曾经写过「命中会话缓存 5 / 6 条」「4 条用户路由在线」这类长句，
      四张卡一起把整条指标条撑到约 240px/卡：卡被压到 176px 之后
      文字冲出了卡片圆角边框（.kpi 虽然有 overflow:hidden，但子元素里
      多个 inline <i> 会把文本切成碎片，Chrome 不出省略号，看起来就是"字超出去"），
      同时整条指标条被挤向右侧、把标题压到左边。 */
const kpisHtml = computed(() =>
  kpiStrip([
    {
      icon: 'i-cube',
      kind: 'queue',
      num: gw.kpis.req,
      unit: '今日请求',
      delta: `<i>${gw.kpis.cacheHit}</i> 命中缓存`,
    },
    {
      icon: 'i-shield',
      kind: 'dist',
      num: gw.kpis.ok,
      unit: '成功率',
      delta: `5xx <i>${gw.kpis.err}</i>`,
    },
    {
      icon: 'i-gauge',
      kind: 'gpu',
      num: gw.kpis.p95,
      unit: '反代 P95',
      delta: `<i>${gw.kpis.routeOk}</i> 条路由在线`,
    },
    {
      icon: 'i-pulse',
      kind: 'running',
      num: gw.kpis.alert,
      unit: '活跃告警',
      delta: `容器 <i>${gw.kpis.up}</i>/<i>${gw.kpis.upAll}</i> 就绪`,
    },
  ]),
)

/* ---------------------------------------------------------------- 三块面板 */
const flow = computed(() => gw.flow)

/** 反代流量折线的三条 path（原型 3949–3952 的取值区间） */
const flowLines = computed(() => {
  const f = flow.value
  return {
    grid: [0.25, 0.5, 0.75].map((g) => (f.h * g).toFixed(1)),
    area: areaOf(f.qps, f.w, f.h, 8, 20, 100),
    qps: pathOf(f.qps, f.w, f.h, 8, 20, 100),
    p95: pathOf(f.p95, f.w, f.h, 8, 10, 90),
    err: pathOf(f.err, f.w, f.h, 8, 0, 30),
  }
})

/** 容器就绪环形（原型 3962–3969 的 score = 就绪 + 异常×0.5） */
const ring = computed(() => {
  const v = gw.viz
  return {
    score: Math.round(((v.ready + v.warn * 0.5) / (gw.ups.length || 1)) * 100),
    dash: ringDash(Math.round(((v.ready + v.warn * 0.5) / (gw.ups.length || 1)) * 100)),
  }
})

const meters = computed(() => gw.meters)

/* ---------------------------------------------------------------- 表格与操作 */
const cols = computed(() => gwCols(gw.tab))
/* rows 直接给 gw.filtered：GwRow 与 GwTableRow 是同一批数据，
   类型差异只在「四表字段并集」的收窄方式上，无需强转 */
const rows = computed(() => gw.filtered)

function setFilter(v: string): void {
  gw.setFilter(v as 'all' | GwStatus)
}

/** 行操作（原型 handleOpsAction 4837–4851） */
function onAct(id: string, act: string): void {
  switch (act) {
    case 'detail':
      overlay.openDrawer('gw', id, gw.byId(id)?.name ?? id)
      break
    case 'edit':
      overlay.openModal('gw', id, null)
      break
    case 'toggle':
      gw.toggle(id)
      break
    case 'del':
      gw.askDelete(id)
      break
  }
}

/** 新增：容器实例与访问日志不能手工建，退回到用户路由表单（原型 gwFormSubmit 里的兜底） */
function onNew(): void {
  overlay.openModal('gw', null, null)
}

const tabTitle = computed(() => {
  const item = TABS.find((t) => t.tab === gw.tab)
  return `${item ? item.label : '路由'}明细`
})
const tabItem = computed(() => TABS.find((t) => t.tab === gw.tab)?.label ?? '记录')
void esc
</script>

<template>
  <section class="subpage" id="gateway" role="region" aria-label="网关">
    <div class="reg__bar">
      <div class="reg__title">
        <h2>网关 <em>{{ gw.routes.length }}</em></h2>
        <p>
          反代与容器实例网关：登录用户到 dsh 容器的一对一反代、启动令牌换取会话、同源校验与入口访问日志
        </p>
      </div>

      <div class="reg-kpis kpis" aria-label="网关概览" v-html="kpisHtml" />

      <span class="kb__baracts">
        <button class="reg__sync reg__sync--ghost" type="button" @click="gw.ping()">
          <IconSprite name="i-pulse" cls="ic" />容器巡检
        </button>
        <button class="reg__sync" type="button" @click="onNew">
          <IconSprite name="i-plus" cls="ic" /><span>{{ gw.newLabel }}</span>
        </button>
      </span>
    </div>

    <div class="reg__filters">
      <span class="tabs" role="tablist" aria-label="网关视图">
        <button
          v-for="t in TABS"
          :key="t.tab"
          class="tabs__btn"
          :class="{ 'is-on': gw.tab === t.tab }"
          type="button"
          role="tab"
          :aria-selected="gw.tab === t.tab"
          @click="gw.setTab(t.tab)"
        >
          <IconSprite :name="t.icon" cls="ic" />{{ t.label }}<em>{{ gw.tabCounts[t.tab] }}</em>
        </button>
      </span>

      <span class="tool__divider" />

      <button
        v-for="f in filters"
        :key="f.value"
        class="fchip"
        :class="{ 'is-on': gw.filter === f.value }"
        type="button"
        @click="setFilter(f.value)"
      >
        {{ f.label }} <em>{{ f.count }}</em>
      </button>

      <span class="reg__gap" />

      <label class="reg__seek">
        <IconSprite name="i-search" cls="ic" />
        <input
          :value="gw.q"
          type="search"
          :placeholder="gw.seekPlaceholder"
          autocomplete="off"
          @input="gw.setQuery(($event.target as HTMLInputElement).value)"
        />
      </label>

      <span class="reg__sel">
        <select
          :value="gw.cluster"
          aria-label="入口源"
          @change="gw.setCluster(($event.target as HTMLSelectElement).value)"
        >
          <option value="all">全部入口源</option>
          <option v-for="c in gw.clusters" :key="c" :value="c">{{ c }}</option>
        </select>
      </span>
    </div>

    <div class="reg__body gw__body">
      <div class="gwgrid">
        <!-- ① 反代流量总览 -->
        <section class="gpanel gpanel--flow" aria-label="反代流量">
          <header class="gpanel__head">
            <h3>反代流量</h3>
            <span class="gpanel__meta">
              近 60 分钟 · 峰值 <b>{{ flow.peakText }}</b> · 均值 <b>{{ flow.avgText }}</b>
            </span>
          </header>

          <div class="flow">
            <svg
              class="flow__svg"
              :viewBox="`0 0 ${flow.w} ${flow.h}`"
              preserveAspectRatio="none"
              aria-hidden="true"
            >
              <defs>
                <linearGradient id="gwFlowFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stop-color="var(--azure)" stop-opacity=".28" />
                  <stop offset="100%" stop-color="var(--azure)" stop-opacity="0" />
                </linearGradient>
              </defs>
              <line
                v-for="(y, i) in flowLines.grid"
                :key="i"
                class="flow__grid"
                x1="0"
                :y1="y"
                :x2="flow.w"
                :y2="y"
              />
              <path class="flow__area" :d="flowLines.area" />
              <path class="flow__line is-qps" :d="flowLines.qps" />
              <path class="flow__line is-p95" :d="flowLines.p95" />
              <path class="flow__line is-err" :d="flowLines.err" />
              <circle class="flow__dot" :cx="flow.w" :cy="flow.dotY" r="3.4" />
            </svg>
          </div>

          <div class="flow__axis" aria-hidden="true">
            <span>-60m</span><span>-45m</span><span>-30m</span><span>-15m</span><span>现在</span>
          </div>

          <div class="flow__legend">
            <span><i class="is-qps" />入口请求</span>
            <span><i class="is-p95" />反代时延</span>
            <span><i class="is-err" />5xx 占比</span>
          </div>
        </section>

        <div class="gwstack">
          <!-- ② 容器就绪 -->
          <section class="gpanel gpanel--health" aria-label="容器就绪">
            <header class="gpanel__head">
              <h3>容器就绪</h3><span class="gpanel__meta">dsh-new.sh 拉起</span>
            </header>
            <div class="gring">
              <svg class="gring__svg" viewBox="0 0 120 120" aria-hidden="true">
                <circle class="gring__bg" cx="60" cy="60" r="50" />
                <circle
                  class="gring__fg"
                  cx="60"
                  cy="60"
                  r="50"
                  :stroke-dasharray="ring.dash"
                  :data-pct="String(ring.score)"
                />
              </svg>
              <span class="gring__center">
                <b>{{ ring.score }}</b>
                <i>就绪率</i>
              </span>
            </div>
            <div class="gring__legend">
              <span><i class="is-ok" />就绪 <b>{{ gw.viz.ready }}</b></span>
              <span><i class="is-warn" />异常 <b>{{ gw.viz.warn }}</b></span>
              <span><i class="is-off" />已停 <b>{{ gw.viz.off }}</b></span>
            </div>
          </section>

          <!-- ③ 会话与连接水位 -->
          <section class="gpanel gpanel--meter" aria-label="会话与连接水位">
            <header class="gpanel__head">
              <h3>会话与连接水位</h3><span class="gpanel__meta">代理侧采样</span>
            </header>
            <div class="gmeters">
              <div
                v-for="m in meters"
                :key="m.t"
                class="gmeter"
                :class="`is-${m.tone}`"
              >
                <div class="gmeter__top"><span>{{ m.t }}</span><b>{{ m.v }}%</b></div>
                <span class="gmeter__bar"><i :style="{ width: `${m.v}%` }" /></span>
                <span class="gmeter__sub">{{ m.s }}</span>
              </div>
            </div>
          </section>
        </div>
      </div>

      <!-- ④ 明细表 -->
      <OpsTable
        :title="tabTitle"
        :item-name="tabItem"
        :cols="cols"
        :rows="rows"
        act-key="gact"
        @act="onAct"
      >
        <template #bin>
          <RichHtml :html="gwCardsHtml(gw.filtered)" />
        </template>
      </OpsTable>
    </div>
  </section>
</template>