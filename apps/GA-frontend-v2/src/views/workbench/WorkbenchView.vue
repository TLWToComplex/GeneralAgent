<!--
  工作台（会话调度 · 工作区工位）—— 等价迁移自原型 console.html 143–222。

  结构：
    .stage__bar  标题 + 浮动指标条（四张带 spark 的 KPI）+ 三视图切换
    #filters     六个状态胶囊 + 自动巡航开关
    ① 工位视图   FloorView（等距平面，默认 180%，pan=(0,0) 居中）
    ② 卡片视图   CardsView
    ③ 表格视图   ListView
    .dock        底部浮动工具栏（任务概览 / 资产分发 / 新建会话 / 运行监控 / 审计日志）

  巡航：工位视图下每 3400ms 轮播一次选中态（原型 5150–5173），
  选中池优先排除空闲会话；手动点选工位会中断巡航。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import IconSprite from '@/components/IconSprite.vue'
import FloorView from './FloorView.vue'
import CardsView from './CardsView.vue'
import ListView from './ListView.vue'
import { kpiStrip } from '@/lib/util'
import { openDshConsole } from '@/lib/dsh'
import { useSessionStore } from '@/stores/session'
import type { WorkbenchView } from '@/stores/session'
import { useOverlayStore } from '@/stores/overlay'
import { useUiStore } from '@/stores/ui'
import { useAuthStore } from '@/stores/auth'
import { SNAMES, ST, type SName } from '@/data/sessions'
import { useHeartbeat } from '@/composables/useHeartbeat'

const session = useSessionStore()
const overlay = useOverlayStore()
const ui = useUiStore()
const auth = useAuthStore()
useHeartbeat(() => 'workbench')

/* 四个视图按钮（原型 console.html 156–164） */
const VIEWS: readonly { view: WorkbenchView; label: string; icon: string }[] = [
  { view: 'floor', label: '工位视图', icon: 'i-cube' },
  { view: 'cards', label: '卡片视图', icon: 'i-cards' },
  { view: 'list', label: '表格视图', icon: 'i-list' },
]

/* 状态胶囊：全部 + 五个状态（原型 console.html 169–174） */
const FILTERS: readonly { value: SName; label: string }[] = SNAMES.map((v) => ({
  value: v,
  label: v === 'all' ? '全部' : ST[v].cn,
}))

/* ---------------------------------------------------------------- 指标条 */
const kpisHtml = computed(() =>
  kpiStrip([
    {
      icon: 'i-term',
      kind: 'running',
      num: session.countsAll.running,
      unit: `/ ${session.sessions.length} 工位`,
      delta: '<span class="is-up"><i>▲ 3</i> 较上一小时</span>',
      spark: 'M2 26 L20 22 L38 24 L56 15 L74 18 L92 11 L110 13 L130 6',
    },
    {
      icon: 'i-pause',
      kind: 'queue',
      num: session.countsAll.queue,
      unit: `平均 ${Math.round(session.avgGpu / 6 + 22)}s`,
      delta: '<span><i>▼ 2</i> 较上一小时</span>',
      spark: 'M2 20 L20 24 L38 17 L56 21 L74 12 L92 19 L110 9 L130 14',
    },
    {
      icon: 'i-gauge',
      kind: 'gpu',
      num: `${Math.round(session.avgGpu)}%`,
      unit: 'A100 × 32',
      delta: '<span class="is-up"><i>▲ 6pt</i> 较上一小时</span>',
      spark: 'M2 27 L20 25 L38 20 L56 22 L74 14 L92 16 L110 10 L130 12',
    },
    {
      icon: 'i-cube',
      kind: 'dist',
      num: ui.distToday,
      unit: '模型 / 技能 / 工具',
      delta: '<span class="is-up"><i>▲ 18%</i> 较昨日</span>',
      spark: 'M2 28 L20 23 L38 25 L56 19 L74 21 L92 13 L110 15 L130 8',
    },
  ]),
)

/* ---------------------------------------------------------------- 巡航 */
let cruiseTimer: number | null = null

function stopCruise(): void {
  if (cruiseTimer !== null) {
    window.clearInterval(cruiseTimer)
    cruiseTimer = null
  }
}

function cruiseStep(): void {
  if (session.view !== 'floor' || !session.cruise) return
  let pool = session.hits.filter((s) => s.state !== 'idle')
  if (!pool.length) pool = session.hits.slice()
  if (!pool.length) return
  const at = pool.findIndex((s) => s.id === session.cruiseId)
  const next = pool[(at + 1) % pool.length]!
  session.selectSession(next.id)
  session.cruiseId = next.id
}

function startCruise(): void {
  stopCruise()
  cruiseTimer = window.setInterval(cruiseStep, 3400)
}

function toggleCruise(): void {
  session.cruise = !session.cruise
  if (session.cruise) {
    session.cruiseId = null
    startCruise()
  } else {
    stopCruise()
    session.cruiseId = null
  }
}

onMounted(startCruise)
onBeforeUnmount(stopCruise)

/* 切视图时巡航节奏跟着走（原型 startCruise 里对 R.view 的判断） */
watch(
  () => session.view,
  () => {
    if (session.cruise) startCruise()
  },
)

/* ---------------------------------------------------------------- 底部浮栏 */
const dock: readonly { act: string; label: string; icon: string; cta?: boolean }[] = [
  { act: 'overview', label: '任务概览', icon: 'i-pulse' },
  { act: 'assets', label: '资产分发', icon: 'i-cube' },
  { act: 'new', label: '新建会话', icon: 'i-plus', cta: true },
  { act: 'monitor', label: '运行监控', icon: 'i-gauge' },
  { act: 'logs', label: '审计日志', icon: 'i-term' },
]

/**
 * 「新建会话」：新标签页打开 dsh 控制台。
 *
 * 会话本身在 dsh 里创建（控制台不再自己造会话），这里只负责把当前登录用户带过去；
 * proxy 会拿用户名去后端校验映射，通过才反代到该用户的实例。
 */
function openNewSession(): void {
  const username = String(auth.user?.username ?? '').trim()
  if (!username) {
    ui.pushHtml('登录信息里没有用户名，无法打开 dsh 控制台')
    return
  }
  const { ok, url } = openDshConsole(username)
  if (!ok) {
    ui.pushText('浏览器拦截了新标签页', ['请手动打开下面的地址', url])
    return
  }
  ui.pushText('已在新标签页打开 <b>dsh 控制台</b>', ['会话在 dsh 里创建', url])
}

function onDock(act: string): void {
  switch (act) {
    case 'overview':
      overlay.openDrawer('monitor', null, '任务概览')
      break
    case 'assets':
      overlay.openDrawer('registry', null, '资产分发')
      break
    case 'new':
      /* 「新建会话」= 进 dsh 控制台：会话在 dsh 里创建，这里只负责把用户带过去。
         用户名放 URL 上（proxy 会校验映射并换成自己的 cookie），见 src/lib/dsh.ts。 */
      openNewSession()
      break
    case 'monitor':
      overlay.openDrawer('monitor', session.selId, '运行监控')
      break
    case 'logs':
      overlay.openDrawer('logs', session.selId, '审计日志')
      break
  }
}
</script>

<template>
  <section class="stage" id="stage" aria-label="会话调度工作区">
    <!-- 工具栏（浮动在工作区上方）：标题 + 浮动指标条 + 视图切换 -->
    <div class="stage__bar">
      <div class="stage__title">
        <h2>会话调度 · 工作区工位</h2>
        <p>
          每个工位是一个 dsh 会话（agent + workspace），气泡里是它此刻正在做的事 ·
          点击工位查看会话详情
        </p>
      </div>

      <section class="kpis" aria-label="运行概览" v-html="kpisHtml" />

      <div class="viewsw" role="tablist" aria-label="视图切换">
        <button
          v-for="v in VIEWS"
          :key="v.view"
          class="viewsw__btn"
          :class="{ 'is-on': session.view === v.view }"
          type="button"
          role="tab"
          :aria-selected="session.view === v.view"
          @click="session.setView(v.view)"
        >
          <IconSprite :name="v.icon" cls="ic" />{{ v.label }}
        </button>
      </div>
    </div>

    <div class="filters">
      <button
        v-for="f in FILTERS"
        :key="f.value"
        class="fchip"
        :class="{ 'is-on': session.filter === f.value }"
        type="button"
        @click="session.setFilter(f.value)"
      >
        {{ f.label }} <em>{{ session.counts[f.value] }}</em>
      </button>

      <span class="filters__gap" />

      <button
        class="fchip fchip--ghost"
        type="button"
        :aria-pressed="session.cruise"
        @click="toggleCruise"
      >
        <IconSprite name="i-eye" cls="ic" />自动巡航
      </button>
    </div>

    <!-- ① 工位视图 -->
    <FloorView />
    <!-- ② 卡片视图 -->
    <CardsView />
    <!-- ③ 表格视图 -->
    <ListView />

    <!-- 底部浮动工具栏：浮在工作区上方 -->
    <div class="dock" role="toolbar" aria-label="快捷工具栏">
      <button
        v-for="b in dock"
        :key="b.act"
        class="dock__btn"
        :class="{ 'dock__btn--cta': b.cta }"
        :data-act="b.act"
        type="button"
        @click="onDock(b.act)"
      >
        <IconSprite :name="b.icon" cls="ic" /><span>{{ b.label }}</span>
      </button>
    </div>
  </section>
</template>