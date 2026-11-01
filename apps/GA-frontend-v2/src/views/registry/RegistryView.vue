<!--
  镜像中心 —— 等价迁移自原型 console.html 226–272 + console.js 1461–1620。

  结构：页头（标题 + 四张指标卡 + 同步按钮）→ 状态筛选 + 搜索 + 仓库下拉 → 卡片列表。
  卡片由 @/lib/cards 的 regCardsHtml 生成，事件用 data-ract 委托回 store。
-->
<script setup lang="ts">
import { computed } from 'vue'
import AssetPage from '@/components/AssetPage.vue'
import IconSprite from '@/components/IconSprite.vue'
import RichHtml from '@/components/RichHtml.vue'
import { regCardsHtml } from '@/lib/cards'
import { kpiStrip } from '@/lib/util'
import { useRegistryStore } from '@/stores/registry'
import { useOverlayStore } from '@/stores/overlay'
import { useUiStore } from '@/stores/ui'
import { useHeartbeat } from '@/composables/useHeartbeat'
import type { RegState } from '@/data/registry'

const registry = useRegistryStore()
const overlay = useOverlayStore()
const ui = useUiStore()
useHeartbeat(() => 'registry')

/* AssetPage 抛上来的筛选/下拉是 string，这里收窄回 store 的联合类型 */
function setFilter(v: string): void {
  registry.setFilter(v as RegState)
}
function setRepo(v: string): void {
  registry.setRepo(v)
}

/* 状态筛选条（原型 console.html 243–247；计数来自整表，且会被搜索影响 —— 与原型 regCounts 同口径） */
const filters = computed(() => [
  { value: 'all', label: '全部', count: registry.counts.all },
  { value: 'synced', label: '已同步', count: registry.counts.synced },
  { value: 'outdated', label: '待更新', count: registry.counts.outdated },
  { value: 'syncing', label: '同步中', count: registry.counts.syncing },
  { value: 'failed', label: '同步失败', count: registry.counts.failed },
])

const kpisHtml = computed(() =>
  kpiStrip([
    {
      icon: 'i-cube',
      kind: 'running',
      num: registry.kpi.total,
      unit: '个镜像',
      delta: `<i>${registry.kpi.tags}</i> 个标签`,
    },
    {
      icon: 'i-restart',
      kind: 'dist',
      num: registry.kpi.syncing,
      unit: '同步中',
      delta: `<i>${registry.kpi.todo}</i> 待更新 / 失败`,
    },
    {
      icon: 'i-download',
      kind: 'gpu',
      num: registry.kpi.sizeText,
      unit: '总占用',
      delta: `<i>${registry.kpi.layers}</i> 层可复用`,
    },
    {
      icon: 'i-model',
      kind: 'queue',
      num: registry.kpi.repoCount,
      unit: '来源仓库',
      delta: `<i>${registry.kpi.pullText}</i> 次拉取`,
    },
  ]),
)

const cardsHtml = computed(() => regCardsHtml(registry.filtered))

/* 卡片上的三个操作（原型 5590–5640 的委托分支） */
function onCards(e: MouseEvent): void {
  const btn = (e.target as HTMLElement | null)?.closest('[data-ract]')
  if (!btn) return
  const article = btn.closest('[data-id]')
  const id = article?.getAttribute('data-id')
  if (!id) return
  const act = btn.getAttribute('data-ract')
  switch (act) {
    case 'sync':
      registry.startSync(id)
      break
    case 'detail':
      overlay.openDrawer('registry', id, registry.byId(id)?.name ?? id)
      break
    case 'pull':
      ui.pushText('开始拉取镜像', [`目标：${id}`, '拉取任务已入队，完成后会回到就绪态'])
      break
  }
}
</script>

<template>
  <section class="subpage" id="registry" role="region" aria-label="镜像中心">
    <AssetPage
      title="镜像中心"
      sub="Agent 运行时 / 推理服务 / 向量库 / 技能沙箱镜像的同步、版本与多地域复制"
      :count-text="registry.countText"
      :kpis-html="kpisHtml"
      :filters="filters"
      :filter="registry.filter"
      :seek-value="registry.q"
      seek-placeholder="搜索镜像 / 标签 / digest"
      :select-value="registry.repo"
      select-label="全部仓库"
      :select-options="registry.repos.map((r) => ({ value: r, label: r }))"
      :head="['镜像 / 版本标签', '元信息', '同步与操作']"
      grid-class="reggrid"
      @update:filter="setFilter"
      @update:seekValue="registry.setQuery"
      @update:selectValue="setRepo"
    >
      <template #actions>
        <button class="reg__sync" type="button" @click="registry.startSyncAll()">
          <IconSprite name="i-restart" cls="ic" /><span>同步镜像</span>
        </button>
      </template>

      <!-- 用 RichHtml 而不是裸 <div v-html>：后者会成为 .reggrid 的一个格子，
           卡片会全部挤在第 1 列里（一行两张变成一行一张）。见组件注释。 -->
      <RichHtml :html="cardsHtml" @click="onCards" />
    </AssetPage>
  </section>
</template>