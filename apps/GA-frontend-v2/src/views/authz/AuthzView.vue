<!--
  权限中心 —— 等价迁移自原型 console.html 601–727 + console.js 4350（KPI）/ 4013–4103（四块面板）。

  面板结构（与网关同款「控制台仪表盘」）：
    ① 权限态势：最小权限评分环 + 双因子覆盖 / 拒绝策略 / 待整改 / 休眠账号
    ② 角色 × 资源矩阵：6 个角色 × 6 个资源域，格子档位 0–3
    ③ 最短审批链（ol.chain） + 授权趋势（12 周净增 gbars）
    ④ 明细表（列定义见 @/lib/pzcols），并保留离屏卡片仓 #pzGrid
-->
<script setup lang="ts">
import { computed } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import OpsTable from '@/components/OpsTable.vue'
import RichHtml from '@/components/RichHtml.vue'
import { pzCardsHtml } from '@/lib/cards'
import { pzCols } from '@/lib/pzcols'
import { kpiStrip } from '@/lib/util'
import { ringDash } from '@/lib/viz'
import { useAuthzStore } from '@/stores/authz'
import { MX_DOMAINS } from '@/stores/authz'
import { useOverlayStore } from '@/stores/overlay'
import { useHeartbeat } from '@/composables/useHeartbeat'
import type { PzStatus, PzTab } from '@/data/authz'

const pz = useAuthzStore()
const overlay = useOverlayStore()
useHeartbeat(() => 'authz')

/* 四个视图 tab（原型 console.html 623–634） */
const TABS: readonly { tab: PzTab; label: string; icon: string }[] = [
  { tab: 'role', label: '角色', icon: 'i-shield' },
  { tab: 'acct', label: '账号', icon: 'i-agent' },
  { tab: 'pol', label: '资源策略', icon: 'i-cube' },
  { tab: 'appr', label: '提权工单', icon: 'i-term' },
]

const filters = computed(() => [
  { value: 'all', label: '全部', count: pz.counts.all },
  { value: 'ok', label: '已生效', count: pz.counts.ok },
  { value: 'warn', label: '待处理', count: pz.counts.warn },
  { value: 'off', label: '已停用', count: pz.counts.off },
])

const kpisHtml = computed(() =>
  kpiStrip([
    {
      icon: 'i-shield',
      kind: 'running',
      num: pz.kpis.role,
      unit: '个角色',
      delta: `账号 <i>${pz.kpis.acct}</i> 个`,
    },
    {
      icon: 'i-cube',
      kind: 'dist',
      num: pz.kpis.pol,
      unit: '条资源策略',
      delta: `<i>${pz.kpis.deny}</i> 条含拒绝/审批`,
    },
    {
      icon: 'i-gauge',
      kind: 'gpu',
      num: pz.kpis.risk,
      unit: '个高风险角色',
      delta: `双因子覆盖 <i>${pz.kpis.mfa}</i>`,
    },
    {
      icon: 'i-term',
      kind: 'queue',
      num: pz.kpis.appr,
      unit: '个待处理工单',
      delta: `<i>${pz.kpis.calls}</i> 次鉴权 / 分钟`,
    },
  ]),
)

/* ---------------------------------------------------------------- ① 权限态势 */
const score = computed(() => pz.score)
const ringDashOf = computed(() => ringDash(pz.score))

/* ---------------------------------------------------------------- ② 权限矩阵 */
const matrix = computed(() => pz.matrix)
const domains = MX_DOMAINS

/* 点格子：原型用 data-mxrow / data-mxdom 让抽屉说明命中来源 */
function onCell(ev: MouseEvent): void {
  const btn = (ev.target as HTMLElement | null)?.closest('[data-mxdom]')
  if (!btn) return
  const row = btn.getAttribute('data-mxrow') ?? '—'
  const dom = btn.getAttribute('data-mxdom') ?? '—'
  const lv = Number(btn.getAttribute('data-mxlv') ?? 0)
  pz.openMatrixCell(row, dom, lv)
}

/* ---------------------------------------------------------------- ④ 表格 */
const cols = computed(() => pzCols(pz.tab))
/* rows 直接给 pz.filtered（同网关页，不做类型强转） */
const rows = computed(() => pz.filtered)

function setFilter(v: string): void {
  pz.setFilter(v as 'all' | PzStatus)
}

function onAct(id: string, act: string): void {
  switch (act) {
    case 'detail':
      overlay.openDrawer('perm', id, pz.byId(id)?.name ?? id)
      break
    case 'edit':
      overlay.openModal('perm', id, null)
      break
    case 'toggle':
      pz.toggle(id)
      break
    case 'del':
      pz.askDelete(id)
      break
  }
}

const tabTitle = computed(() => `${TABS.find((t) => t.tab === pz.tab)?.label ?? '角色'}明细`)
const tabItem = computed(() => TABS.find((t) => t.tab === pz.tab)?.label ?? '记录')
</script>

<template>
  <section class="subpage" id="authz" role="region" aria-label="权限中心">
    <div class="reg__bar">
      <div class="reg__title">
        <h2>权限中心 <em>{{ pz.headCount }}</em></h2>
        <p>角色、账号、资源策略与提权工单：按最小权限原则下发与定期复核</p>
      </div>

      <div class="reg-kpis kpis" aria-label="权限概览" v-html="kpisHtml" />

      <span class="kb__baracts">
        <button class="reg__sync reg__sync--ghost" type="button" @click="pz.review()">
          <IconSprite name="i-shield" cls="ic" />发起复核
        </button>
        <button class="reg__sync" type="button" @click="overlay.openModal('perm', null, null)">
          <IconSprite name="i-plus" cls="ic" /><span>{{ pz.newLabel }}</span>
        </button>
      </span>
    </div>

    <div class="reg__filters">
      <span class="tabs" role="tablist" aria-label="权限视图">
        <button
          v-for="t in TABS"
          :key="t.tab"
          class="tabs__btn"
          :class="{ 'is-on': pz.tab === t.tab }"
          type="button"
          role="tab"
          :aria-selected="pz.tab === t.tab"
          @click="pz.setTab(t.tab)"
        >
          <IconSprite :name="t.icon" cls="ic" />{{ t.label }}<em>{{ pz.tabCounts[t.tab] }}</em>
        </button>
      </span>

      <span class="tool__divider" />

      <button
        v-for="f in filters"
        :key="f.value"
        class="fchip"
        :class="{ 'is-on': pz.filter === f.value }"
        type="button"
        @click="setFilter(f.value)"
      >
        {{ f.label }} <em>{{ f.count }}</em>
      </button>

      <span class="reg__gap" />

      <label class="reg__seek">
        <IconSprite name="i-search" cls="ic" />
        <input
          :value="pz.q"
          type="search"
          :placeholder="pz.seekPlaceholder"
          autocomplete="off"
          @input="pz.setQuery(($event.target as HTMLInputElement).value)"
        />
      </label>

      <span class="reg__sel">
        <select
          :value="pz.scope"
          aria-label="适用范围"
          @change="pz.setScope(($event.target as HTMLSelectElement).value)"
        >
          <option value="all">全部范围</option>
          <option v-for="s in pz.scopes" :key="s" :value="s">{{ s }}</option>
        </select>
      </span>
    </div>

    <div class="reg__body pz__body">
      <div class="gwgrid">
        <!-- ① 权限态势 -->
        <section class="gpanel gpanel--posture" aria-label="权限态势">
          <header class="gpanel__head">
            <h3>权限态势</h3>
            <span class="gpanel__meta">最小权限评分 · 实时</span>
          </header>
          <div class="gposture">
            <div class="gring gring--sm">
              <svg class="gring__svg" viewBox="0 0 120 120" aria-hidden="true">
                <circle class="gring__bg" cx="60" cy="60" r="50" />
                <circle
                  class="gring__fg"
                  cx="60"
                  cy="60"
                  r="50"
                  :stroke-dasharray="ringDashOf"
                  :data-pct="String(score)"
                />
              </svg>
              <span class="gring__center">
                <b>{{ score }}</b>
                <i>评分</i>
              </span>
            </div>

            <ul class="gposture__list">
              <li
                v-for="x in pz.posture"
                :key="x.t"
                class="gpst"
                :class="`is-${x.tone}`"
              >
                <span class="gpst__t">{{ x.t }}</span>
                <b class="gpst__v">{{ x.v }}{{ x.suffix }}</b>
                <span class="gpst__bar">
                  <i :style="{ width: `${x.suffix === '%' ? x.v : Math.min(100, x.v * 20)}%` }" />
                </span>
              </li>
            </ul>
          </div>
        </section>

        <!-- ② 角色 × 资源矩阵 -->
        <section class="gpanel gpanel--matrix" aria-label="角色与资源权限矩阵">
          <header class="gpanel__head">
            <h3>角色 × 资源矩阵</h3>
            <span class="gpanel__meta">
              <span class="mx__legend"><i class="mx-3" />完全</span>
              <span class="mx__legend"><i class="mx-2" />部分</span>
              <span class="mx__legend"><i class="mx-1" />只读</span>
              <span class="mx__legend"><i class="mx-0" />无权</span>
            </span>
          </header>

          <div class="mx" @click="onCell">
            <div class="mx__row mx__row--head">
              <span class="mx__cell mx__cell--lead">角色 \ 资源</span>
              <button
                v-for="(d, i) in domains"
                :key="d"
                class="mx__cell mx__cell--hd"
                type="button"
                :data-mxcol="i"
              >{{ d }}</button>
            </div>

            <div v-for="r in matrix" :key="r.name" class="mx__row">
              <span class="mx__cell mx__cell--lead" :title="r.name">{{ r.name }}</span>
              <button
                v-for="c in r.cells"
                :key="c.dom"
                class="mx__cell"
                :class="`mx__cell--${c.lv}`"
                type="button"
                :data-mxlv="c.lv"
                :data-mxrow="r.name"
                :data-mxdom="c.dom"
                :title="`${r.name} × ${c.dom}：${c.text}`"
              ><i /></button>
            </div>

            <p class="mx__foot">
              格子深浅 = 该角色在这个资源域里的权限档位；点格子可让详情抽屉说明命中来源。
            </p>
          </div>
        </section>

        <!-- ③ 最短审批链 + 授权趋势 -->
        <div class="gwstack">
          <section class="gpanel gpanel--chain" aria-label="最短审批链">
            <header class="gpanel__head">
              <h3>最短审批链</h3><span class="gpanel__meta">当前工单</span>
            </header>
            <ol class="chain">
              <li v-for="(s, i) in pz.chain" :key="i" class="chain__step" :class="s.state">
                <span class="chain__dot" />
                <span class="chain__txt">
                  <b>{{ s.text }}</b>
                  <i>{{ s.meta }}</i>
                </span>
              </li>
            </ol>
          </section>

          <section class="gpanel gpanel--trend" aria-label="授权趋势">
            <header class="gpanel__head">
              <h3>授权趋势</h3>
              <span class="gpanel__meta">
                近 12 周 · 净增 <b>{{ pz.trendNetText }}</b>
              </span>
            </header>
            <div class="gbars" aria-hidden="true">
              <span
                v-for="b in pz.trend"
                :key="b.week"
                class="gbar"
                :class="b.up ? 'is-up' : 'is-down'"
                :title="b.title"
                :style="{ '--h': b.h }"
              />
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
        act-key="pact"
        @act="onAct"
      >
        <template #bin>
          <RichHtml :html="pzCardsHtml(pz.filtered)" />
        </template>
      </OpsTable>
    </div>
  </section>
</template>