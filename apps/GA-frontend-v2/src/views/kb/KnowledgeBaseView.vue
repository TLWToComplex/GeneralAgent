<!--
  知识库中心 —— 等价迁移自原型 console.html 381–472 + console.js 2672–2820。

  比其他资产页多两处：
    · 四个「知识库类型」tab（文档库 / 问答库 / 表格库 / 图谱库）
    · 「检索试跑」面板（.kbask，默认收起；展开后跑离线假检索链路）
  前者走 AssetPage 的 #filters 插槽，后者走 #panel 插槽，
  位置与原型 401–437 / 439–464 完全一致。
-->
<script setup lang="ts">
import { computed } from 'vue'
import AssetPage from '@/components/AssetPage.vue'
import IconSprite from '@/components/IconSprite.vue'
import RichHtml from '@/components/RichHtml.vue'
import { kbCardsHtml } from '@/lib/cards'
import { kpiStrip } from '@/lib/util'
import { useKbStore } from '@/stores/kb'
import type { KbFilter } from '@/stores/kb'
import { useOverlayStore } from '@/stores/overlay'
import { useHeartbeat } from '@/composables/useHeartbeat'
import type { KbKind } from '@/data/kb'

const kb = useKbStore()
const overlay = useOverlayStore()
useHeartbeat(() => 'kb')

/* 四个类型 tab（原型 console.html 403–414） */
const KIND_TABS: readonly { kind: KbKind; label: string; icon: string }[] = [
  { kind: 'doc', label: '文档库', icon: 'i-book' },
  { kind: 'qa', label: '问答库', icon: 'i-spark' },
  { kind: 'sheet', label: '表格库', icon: 'i-tool' },
  { kind: 'graph', label: '图谱库', icon: 'i-pulse' },
]

const filters = computed(() => [
  { value: 'all', label: '全部', count: kb.counts.all },
  { value: 'ready', label: '就绪', count: kb.counts.ready },
  { value: 'indexing', label: '索引中', count: kb.counts.indexing },
  { value: 'paused', label: '已暂停', count: kb.counts.paused },
  { value: 'failed', label: '异常', count: kb.counts.failed },
])

const kpisHtml = computed(() =>
  kpiStrip([
    {
      icon: 'i-book',
      kind: 'running',
      num: kb.kpis.total,
      unit: '知识库',
      delta: `<i>${kb.kpis.ready}</i> 个就绪`,
    },
    {
      icon: 'i-file',
      kind: 'dist',
      num: kb.kpis.docs,
      unit: '份语料',
      delta: `<i>${kb.kpis.chunks}</i> 个分片`,
    },
    {
      icon: 'i-search',
      kind: 'gpu',
      num: kb.kpis.hit,
      unit: '命中率',
      delta: `<i>${kb.kpis.recall}</i> 召回 P95`,
    },
    {
      icon: 'i-pulse',
      kind: 'queue',
      num: kb.kpis.calls,
      unit: '今日检索',
      delta: `<i>${kb.kpis.busy}</i> 个索引中`,
    },
  ]),
)

const cardsHtml = computed(() => kbCardsHtml(kb.filtered))

function setFilter(v: string): void {
  kb.setFilter(v as KbFilter)
}

/* 卡片上的五个操作（原型 data-kact 委托） */
function onCards(e: MouseEvent): void {
  const btn = (e.target as HTMLElement | null)?.closest('[data-kact]')
  if (!btn) return
  const id = btn.closest('[data-id]')?.getAttribute('data-id')
  if (!id) return
  switch (btn.getAttribute('data-kact')) {
    case 'test':
      /* 点「试跑」时带上这个库，并立刻跑一次（原型 kbAskOpen + kbAskRun） */
      kb.openAsk(id)
      kb.runAsk()
      break
    case 'edit':
      overlay.openModal('kb', id, null)
      break
    case 'detail':
      overlay.openDrawer('kb', id, kb.byId(id)?.name ?? id)
      break
    case 'toggle':
      kb.toggle(id)
      break
    case 'del':
      kb.askDelete(id)
      break
  }
}

/* ---------------------------------------------------------------- 检索试跑 */
function onAskSubmit(): void {
  kb.runAsk()
}
</script>

<template>
  <section class="subpage" id="kb" role="region" aria-label="知识库中心">
    <AssetPage
      title="知识库中心"
      sub="语料接入、切片与向量化策略、索引重建与检索配额，支持增删改查与在线试跑"
      :count-text="kb.headCount"
      :kpis-html="kpisHtml"
      :filters="filters"
      :filter="kb.filter"
      :seek-value="kb.q"
      seek-placeholder="搜索知识库 / 语料 / 向量库"
      :select-value="kb.owner"
      select-label="全部归属"
      :select-options="kb.owners.map((o) => ({ value: o, label: o }))"
      :head="['知识库 / 语料', '切片与向量化', '命中与操作']"
      grid-class="kblist"
      body-class="kb__body"
      @update:filter="setFilter"
      @update:seekValue="kb.setQuery"
      @update:selectValue="kb.setOwner"
    >
      <template #actions>
        <span class="kb__baracts">
          <button class="reg__sync reg__sync--ghost" type="button" @click="kb.openAsk()">
            <IconSprite name="i-search" cls="ic" />检索试跑
          </button>
          <button class="reg__sync" type="button" @click="overlay.openModal('kb', null, null)">
            <IconSprite name="i-plus" cls="ic" /><span>{{ kb.newLabel }}</span>
          </button>
        </span>
      </template>

      <!-- 知识库类型 tab：原型放在状态筛选条最前面 -->
      <template #filters>
        <span class="tabs" role="tablist" aria-label="知识库类型">
          <button
            v-for="t in KIND_TABS"
            :key="t.kind"
            class="tabs__btn"
            :class="{ 'is-on': kb.tab === t.kind }"
            type="button"
            role="tab"
            :aria-selected="kb.tab === t.kind"
            @click="kb.setTab(t.kind)"
          >
            <IconSprite :name="t.icon" cls="ic" />{{ t.label }}<em>{{ kb.tabCounts[t.kind] }}</em>
          </button>
        </span>

        <span class="tool__divider" />
      </template>

      <!-- 检索试跑面板（默认收起） -->
      <template #panel>
        <section
          class="kbask"
          :class="{ 'is-off': !kb.askOpen }"
          aria-label="检索试跑"
          :aria-hidden="!kb.askOpen"
        >
          <form class="kbask__form" autocomplete="off" @submit.prevent="onAskSubmit">
            <label class="kbask__field">
              <IconSprite name="i-search" cls="ic" />
              <input
                v-model="kb.askQ"
                type="text"
                name="kbq"
                placeholder="输入一个问题，看这个库会召回哪些分片（示例：退货多久能到账？）"
                maxlength="60"
              />
            </label>
            <button class="btn btn--main" type="submit">
              <span>检索</span><IconSprite name="i-chev" cls="ic" />
            </button>
            <button class="iconbtn" type="button" aria-label="收起试跑面板" @click="kb.closeAsk()">
              <IconSprite name="i-x" cls="ic" />
            </button>
          </form>

          <div class="kbask__opts">
            <span class="kbask__cur">{{ kb.askCurText }}</span>
            <label class="kbask__topk">
              Top-K
              <input v-model.number="kb.askTopk" type="range" min="1" max="8" step="1" />
              <b>{{ kb.askTopk }}</b>
            </label>
            <span class="kbask__tip">支持 Enter 快速检索 · 命中的分片会显示相似度与来源页码</span>
          </div>

          <div class="kbask__out">
            <!-- 未检索：提示文案（原型 console.html 462） -->
            <p v-if="!kb.askDone" class="kbask__hint">
              试跑用离线假数据模拟检索链路：向量召回 → 关键词加权 → 重排 → 拼接答案。
            </p>

            <!-- 空命中 -->
            <p v-else-if="kb.askEmpty" class="kbask__hint">
              这一问没召回任何分片：换个说法，或调大 Top-K 再试。
            </p>

            <!-- 命中列表：相似度 + 来源 + 正文 + 引用 -->
            <template v-else>
              <div class="kbask__hits">
                <article v-for="(h, i) in kb.askHits" :key="i" class="kbhit">
                  <header>
                    <b>{{ h.title }}</b>
                    <em>{{ h.score.toFixed(2) }}</em>
                  </header>
                  <p>{{ h.text }}</p>
                  <footer><span>{{ h.at }}</span></footer>
                </article>
              </div>
              <p class="kbask__cite">
                引用来源：<span v-for="(c, i) in kb.askCites" :key="i">{{ c[0] }} {{ c[1] }}</span>
              </p>
            </template>
          </div>
        </section>
      </template>

      <!-- RichHtml 见组件注释：裸 <div v-html> 会成为 .kblist 的唯一格子 -->
      <RichHtml :html="cardsHtml" @click="onCards" />
    </AssetPage>
  </section>
</template>