<!--
  工具平台（MCP / Skill / AI 工具）—— MCP / Skill 部分等价迁移自原型
  console.html 325–378 + console.js 2165–2301；AI 工具是本项目新增的标签页，现排在第一位并默认落地。

  ① MCP / Skill：比其他资产页多一条「工具类型」切换（.tabs.tabs__btn），
     通过 AssetPage 的 #filters 插槽插在状态筛选条最前面，
     与原型 console.html 342–351 的位置完全一致；
  ② AI 工具（第一个 tab）：同一套页面外壳，但口径换成了**下发给人的客户端软件**
     （dsh 桌面版 exe / dsh 终端版 / Zed）。卡片点「安装流程」不是开抽屉，
     而是整块换成该工具的安装使用流程页（AiToolGuide），
     页头主按钮「内网模型参数」换成参数速查页（AiModelRef）。
     两者都是 store 里的 aiView 状态，不是嵌套路由 —— 与项目其它子 tab 的处理一致。

  卡片仍然用 v-html 输出（RichHtml 落点），所以 AI 卡片的按钮同样是
  data-* 委托：data-aiact 与 data-tact / data-ract 共用 onCards 这一个入口。
-->
<script setup lang="ts">
import { computed } from 'vue'
import AssetPage from '@/components/AssetPage.vue'
import IconSprite from '@/components/IconSprite.vue'
import RichHtml from '@/components/RichHtml.vue'
import AiToolGuide from '@/views/tools/AiToolGuide.vue'
import AiModelRef from '@/views/tools/AiModelRef.vue'
import { aiToolCardsHtml, toolCardsHtml } from '@/lib/cards'
import { kpiStrip } from '@/lib/util'
import { copyText } from '@/lib/clipboard'
import { quickConfigText } from '@/data/aitools'
import type { AiTool } from '@/data/aitools'
import { useToolsStore } from '@/stores/tools'
import type { AiKindFilter, ToolFilter, ToolsTab } from '@/stores/tools'
import { useOverlayStore } from '@/stores/overlay'
import { useHeartbeat } from '@/composables/useHeartbeat'

const tools = useToolsStore()
const overlay = useOverlayStore()
useHeartbeat(() => 'toolplatform')

/* ------------------------------------------------------------------ 标签页 */

/**
 * 三个页面级 tab（不是数据判别式：AI 工具不是 ToolItem，见 stores/tools.ts）。
 *
 * 顺序：AI 工具排第一，是默认落地的 tab（store 里 `tab` 的初值也是 'ai'）。
 *
 * locked：MCP / Skill 两个 tab 目前**功能开发中**，置灰且不可点击进入。
 * 与侧栏那四处「开发中」采用同一套做法（AppSidebar + 本文件模板）：
 *   · 置灰项渲染成 <span> 而不是 <button> —— 不是靠 disabled / pointer-events
 *     拦截，而是压根没有可点的控件；键盘也 Tab 不上去，语义上也不冒充 tab。
 *   · 之所以用 span 而不是给 button 加 disabled：disabled 的 <button> 仍会被
 *     读屏念成按钮，且视觉上要额外处理；span 更直接。
 *   · 有用的东西留着：title 说明原因，免得用户以为页面坏了。
 * 数据、store、卡片渲染全部保持不变 —— 把 locked 改回 false 即可随时恢复。
 */
const TABS: { id: ToolsTab; label: string; icon: string; locked?: boolean }[] = [
  { id: 'ai', label: 'AI 工具', icon: 'i-download' },
  { id: 'mcp', label: 'MCP 服务', icon: 'i-plug', locked: true },
  { id: 'skill', label: 'Skill 工具', icon: 'i-spark', locked: true },
]

const isAi = computed(() => tools.tab === 'ai')
/**
 * AI 工具区的三个视图：列表 / 某个工具的安装流程 / 内网模型参数速查。
 * 这里把「当前在流程页 + 有选中的工具」收成一个非空 computed，
 * 模板里就不需要靠 v-if 的收窄把 AiTool | null 变成 AiTool。
 */
const guideTool = computed<AiTool | null>(() =>
  isAi.value && tools.aiView === 'guide' ? tools.aiTool : null,
)
const showRef = computed(() => isAi.value && tools.aiView === 'ref')

/* ------------------------------------------------------------------ 筛选条 */

const filters = computed(() =>
  isAi.value
    ? [
        { value: 'all', label: '全部', count: tools.aiCounts.all },
        { value: 'desktop', label: '桌面端', count: tools.aiCounts.desktop },
        { value: 'cli', label: '终端', count: tools.aiCounts.cli },
        { value: 'ide', label: 'IDE', count: tools.aiCounts.ide },
      ]
    : [
        { value: 'all', label: '全部', count: tools.counts.all },
        { value: 'online', label: '在线', count: tools.counts.online },
        { value: 'degraded', label: '异常', count: tools.counts.degraded },
        { value: 'offline', label: '已下线', count: tools.counts.offline },
      ],
)

const filterValue = computed(() => (isAi.value ? tools.aiKind : tools.filter))

function setFilter(v: string): void {
  if (isAi.value) tools.setAiKind(v as AiKindFilter)
  else tools.setFilter(v as ToolFilter)
}

/* ------------------------------------------------------------------ 页面文案 */

const subText = computed(() =>
  isAi.value
    ? '内网 AI 编码工具的下发与装机：安装包、内网大模型配置、安装使用全流程（dsh 桌面版 / dsh 终端版 / Zed）'
    : 'MCP 服务与 Skill 工具的注册、变更、下线与调用配额，支持增删改查',
)

const head = computed<[string, string, string]>(() =>
  isAi.value
    ? ['工具 / 定位', '安装与配置', '下发与操作']
    : ['名称 / 描述', '接入与配置', '调用与操作'],
)

/* ------------------------------------------------------------------ KPI */

const kpisHtml = computed(() => {
  if (isAi.value) {
    const k = tools.aiKpis
    return kpiStrip([
      {
        icon: 'i-download',
        kind: 'dist',
        num: k.total,
        unit: 'AI 工具',
        delta: `<i>${k.files}</i> 个可领取文件`,
      },
      {
        icon: 'i-term',
        kind: 'gpu',
        num: k.steps,
        unit: '装机步骤',
        delta: '含配置与验证',
      },
      {
        icon: 'i-pulse',
        kind: 'queue',
        num: k.downloads,
        unit: '累计下发',
        delta: `今日 <i>${k.today}</i> 次`,
      },
      {
        icon: 'i-model',
        kind: 'running',
        num: 1,
        unit: '内网模型',
        delta: '<i>qwen3.8-27b</i> vLLM 部署',
      },
    ])
  }
  return kpiStrip([
    {
      icon: 'i-plug',
      kind: 'running',
      num: tools.kpis.mcp,
      unit: 'MCP 服务',
      delta: `<i>${tools.kpis.mcpOn}</i> 在线`,
    },
    {
      icon: 'i-spark',
      kind: 'dist',
      num: tools.kpis.sk,
      unit: 'Skill 工具',
      delta: `<i>${tools.kpis.skOn}</i> 在线`,
    },
    {
      icon: 'i-tool',
      kind: 'gpu',
      num: tools.kpis.expose,
      unit: '暴露能力',
      delta: `<i>${tools.kpis.warn}</i> 个异常`,
    },
    {
      icon: 'i-pulse',
      kind: 'queue',
      num: tools.kpis.calls,
      unit: '今日调用',
      delta: `<i>${tools.kpis.p95}</i> MCP 平均 P95`,
    },
  ])
})

/* ------------------------------------------------------------------ 卡片 */

const cardsHtml = computed(() =>
  isAi.value ? aiToolCardsHtml(tools.aiFiltered) : toolCardsHtml(tools.filtered, tools.tab === 'mcp'),
)

/** 卡片右下角的三个操作（MCP / Skill 的原型委托 + AI 工具的四个动作） */
function onCards(e: MouseEvent): void {
  const btn = (e.target as HTMLElement | null)?.closest('[data-tact],[data-aiact]')
  if (!btn) return

  const aiId = btn.closest('[data-ai]')?.getAttribute('data-ai')
  if (aiId) {
    onAiAction(btn.getAttribute('data-aiact'), aiId)
    return
  }

  const id = btn.closest('[data-id]')?.getAttribute('data-id')
  if (!id) return
  switch (btn.getAttribute('data-tact')) {
    case 'edit':
      overlay.openModal('tool', id, tools.tab)
      break
    case 'detail':
      overlay.openDrawer('tool', id, tools.byId(id)?.name ?? id)
      break
    case 'toggle':
      tools.toggle(id)
      break
    case 'del':
      tools.askDelete(id)
      break
  }
}

/** AI 卡片的四个动作：安装流程 / 复制配置 / 领取安装包 / 复制安装命令 */
function onAiAction(act: string | null, id: string): void {
  const t = tools.aiTools.find((x) => x.id === id)
  if (!t) return
  switch (act) {
    case 'guide':
      tools.openAiGuide(t.id)
      break
    case 'cfg':
      void copyAndNotify(quickConfigText(t.id), `${t.name}的接入配置`)
      break
    case 'cmd':
      void copyAndNotify(t.quickCmd ?? 'npx @deepseek-ai/dsh web', `${t.name}的安装命令`)
      break
    case 'dl': {
      const f = t.files[0]
      if (f) tools.claimFile(t, f.url)
      break
    }
  }
}

async function copyAndNotify(text: string, label: string): Promise<void> {
  tools.notifyCopy(label, await copyText(text))
}

/* ------------------------------------------------------------------ 页头按钮 */

/** 新增按钮：新建时带「当前 tab」，编辑时由卡片进入；AI 标签页换成参数速查 */
function onAction(): void {
  if (isAi.value) {
    tools.openAiRef()
    return
  }
  overlay.openModal('tool', null, tools.tab)
}
</script>

<template>
  <section class="subpage" id="toolplatform" role="region" aria-label="工具平台">
    <!-- 安装流程 / 参数速查：整块替换卡片区（返回按钮回到列表） -->
    <AiToolGuide v-if="guideTool" :tool="guideTool" @back="tools.closeAiView()" />
    <AiModelRef v-else-if="showRef" @back="tools.closeAiView()" />

    <AssetPage
      v-else
      title="工具平台"
      :sub="subText"
      :count-text="tools.headCount"
      :kpis-html="kpisHtml"
      :filters="filters"
      :filter="filterValue"
      :seek-value="tools.q"
      :seek-placeholder="tools.seekPlaceholder"
      :select-value="isAi ? tools.aiChannel : tools.cat"
      :select-label="isAi ? '全部渠道' : '全部分类'"
      :select-options="
        isAi
          ? [
              { value: 'official', label: '官方开源' },
              { value: 'thirdparty', label: '第三方' },
            ]
          : tools.cats.map((c) => ({ value: c, label: c }))
      "
      :head="head"
      grid-class="reggrid"
      @update:filter="setFilter"
      @update:seekValue="tools.setQuery"
      @update:selectValue="isAi ? tools.setAiChannel($event) : tools.setCat($event)"
    >
      <template #actions>
        <button class="reg__sync" type="button" @click="onAction">
          <IconSprite :name="tools.actionIcon" cls="ic" /><span>{{ tools.actionLabel }}</span>
        </button>
      </template>

      <!-- 工具类型切换：原型放在状态筛选条最前面；AI 工具是后加的一项，现在排在第一位 -->
      <template #filters>
        <span class="tabs" role="tablist" aria-label="工具类型">
          <template v-for="t in TABS" :key="t.id">
            <!-- 开发中：不是按钮，点不动，键盘也 Tab 不上去 -->
            <span
              v-if="t.locked"
              class="tabs__btn is-locked"
              data-tab
              aria-disabled="true"
              title="功能开发中，暂不可进入"
            >
              <IconSprite :name="t.icon" cls="ic" />{{ t.label }}
              <em class="tabs__dev">开发中</em>
            </span>

            <button
              v-else
              class="tabs__btn"
              data-tab
              :class="{ 'is-on': tools.tab === t.id }"
              type="button"
              role="tab"
              :aria-selected="tools.tab === t.id"
              @click="tools.setTab(t.id)"
            >
              <IconSprite :name="t.icon" cls="ic" />{{ t.label }}
              <em>{{ tools.tabCounts[t.id] }}</em>
            </button>
          </template>
        </span>

        <span class="tool__divider" />
      </template>

      <!-- RichHtml 见组件注释：裸 <div v-html> 会成为 .toolgrid 的唯一格子 -->
      <RichHtml :html="cardsHtml" @click="onCards" />
    </AssetPage>
  </section>
</template>