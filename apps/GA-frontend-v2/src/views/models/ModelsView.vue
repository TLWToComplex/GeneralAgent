<!--
  模型中心 —— 等价迁移自原型 console.html 275–322 + console.js 1806–1962。

  结构：页头（标题 + 四张指标卡 + 批量部署）→ 状态筛选 + 搜索 + 类型下拉 → 模型卡片。
  卡片由 @/lib/cards 的 modCardsHtml 生成（含近 12 小时调用曲线）。
-->
<script setup lang="ts">
import { computed } from 'vue'
import AssetPage from '@/components/AssetPage.vue'
import IconSprite from '@/components/IconSprite.vue'
import RichHtml from '@/components/RichHtml.vue'
import { modCardsHtml } from '@/lib/cards'
import { kpiStrip } from '@/lib/util'
import { useModelsStore } from '@/stores/models'
import { useOverlayStore } from '@/stores/overlay'
import { useUiStore } from '@/stores/ui'
import { useHeartbeat } from '@/composables/useHeartbeat'
import type { ModelFilter, ModelType } from '@/data/models'

const models = useModelsStore()
const overlay = useOverlayStore()
const ui = useUiStore()
useHeartbeat(() => 'models')

const filters = computed(() => [
  { value: 'all', label: '全部', count: models.counts.all },
  { value: 'deployed', label: '在线', count: models.counts.deployed },
  { value: 'deploying', label: '部署中', count: models.counts.deploying },
  { value: 'degraded', label: '异常', count: models.counts.degraded },
  { value: 'offline', label: '已下线', count: models.counts.offline },
])

/* 类型下拉：原型写死五个 option（console.html 305–312） */
const TYPE_OPTIONS = [
  '推理模型',
  '向量模型',
  '重排序',
  '多模态',
  '语音模型',
] as const

const kpisHtml = computed(() =>
  kpiStrip([
    {
      icon: 'i-model',
      kind: 'running',
      num: models.kpi.online,
      unit: '在线模型',
      delta: `<i>${models.kpi.total}</i> 个已注册`,
    },
    {
      icon: 'i-pulse',
      kind: 'dist',
      num: models.kpi.tokensText,
      unit: '今日 Token',
      delta: `<i>${models.kpi.callsText}</i> 次调用`,
    },
    {
      icon: 'i-clock',
      kind: 'gpu',
      num: models.kpi.p95Text,
      unit: 'P95 首字',
      delta: `<i>${models.kpi.errText}</i> 平均错误率`,
    },
    {
      icon: 'i-gpu',
      kind: 'queue',
      num: models.kpi.gpuText,
      unit: '占用 GPU',
      delta: `<i>${models.kpi.cardsText}</i> 张卡 · 集群 A/B/C`,
    },
  ]),
)

const cardsHtml = computed(() => modCardsHtml(models.filtered))

function setFilter(v: string): void {
  models.setFilter(v as ModelFilter)
}
function setType(v: string): void {
  models.setType(v as ModelType | 'all')
}

/* 卡片上的四个操作（原型 5590–5640 的 data-mact 分支） */
function onCards(e: MouseEvent): void {
  const btn = (e.target as HTMLElement | null)?.closest('[data-mact]')
  if (!btn) return
  const id = btn.closest('[data-id]')?.getAttribute('data-id')
  if (!id) return
  switch (btn.getAttribute('data-mact')) {
    case 'deploy':
      models.startDeploy(id)
      break
    case 'detail':
      overlay.openDrawer('model', id, models.byId(id)?.name ?? id)
      break
    case 'probe':
      models.probe(id)
      break
    case 'offline':
      models.offlineModel(id)
      break
  }
}
</script>

<template>
  <section class="subpage" id="models" role="region" aria-label="模型中心">
    <AssetPage
      title="模型中心"
      sub="推理模型 / 向量模型 / 重排序 / 多模态的版本、部署与调用配额"
      :count-text="models.countText"
      :kpis-html="kpisHtml"
      :filters="filters"
      :filter="models.filter"
      :seek-value="models.q"
      seek-placeholder="搜索模型 / 家族 / 版本"
      :select-value="models.type"
      select-label="全部类型"
      :select-options="TYPE_OPTIONS.map((t) => ({ value: t, label: t }))"
      :head="['模型 / 实时状态', '近 12 小时调用趋势', '规格 · 资源 · 操作']"
      grid-class="modgrid"
      @update:filter="setFilter"
      @update:seekValue="models.setQuery"
      @update:selectValue="setType"
    >
      <template #actions>
        <button class="reg__sync" type="button" @click="models.startDeployAll()">
          <IconSprite name="i-play" cls="ic" /><span>批量部署</span>
        </button>
      </template>

      <!-- RichHtml 见组件注释：裸 <div v-html> 会成为 .modgrid 的唯一格子，
           单列卡片会被压在半屏里，右侧留白 -->
      <RichHtml :html="cardsHtml" @click="onCards" />
    </AssetPage>
  </section>
</template>