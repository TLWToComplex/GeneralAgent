<!--
  资产页公共外壳 —— 镜像中心 / 模型中心 / 工具平台 / 知识库中心 共用。

  对应原型 console.html 226–240、275–288、325–340、381–399 的 .reg__bar，
  以及 242–264 / 290–314 / ... 的 .reg__filters、266–271 的 .reg__body。

  页面差异全部通过 props / slot 传入：
    · title / sub / count / countUnit   —— 标题、描述、数量徽标
    · kpis                              —— 页面级指标（.reg-kpis.kpis）
    · filters                           —— 状态筛选条（value / label / count）
    · seekPlaceholder / q               —— 搜索框
    · select                            —— 右上角那个下拉（仓库 / 类型 / 分类 / 归属）
    · head                              —— 表头三列文案
    · gridClass                         —— 卡片网格的附加类（reggrid / modgrid / …）
    · #actions                          —— 右上角主按钮
    · 默认 slot                          —— 卡片区（v-html 输出）
-->
<script setup lang="ts">
import IconSprite from '@/components/IconSprite.vue'

export interface AssetFilter {
  value: string
  label: string
  count: number
}

export interface AssetSelectOption {
  value: string
  label: string
}

defineProps<{
  title: string
  sub: string
  /** 标题旁的数量，如 "12 个镜像" */
  countText: string
  /** 页面级指标 HTML（空则不渲染） */
  kpisHtml: string
  filters: readonly AssetFilter[]
  filter: string
  seekValue: string
  seekPlaceholder: string
  selectValue: string
  selectLabel: string
  selectOptions: readonly AssetSelectOption[]
  /** 表头三列 */
  head: readonly [string, string, string]
  /** 卡片网格的类名，如 reggrid / modgrid */
  gridClass: string
  /** .reg__body 的附加类（知识库用 kb__body） */
  bodyClass?: string
}>()

const emit = defineEmits<{
  (e: 'update:filter', v: string): void
  (e: 'update:seekValue', v: string): void
  (e: 'update:selectValue', v: string): void
}>()

function onSeek(e: Event): void {
  emit('update:seekValue', (e.target as HTMLInputElement).value)
}
function onSelect(e: Event): void {
  emit('update:selectValue', (e.target as HTMLSelectElement).value)
}
</script>

<template>
  <div class="reg__bar">
    <div class="reg__title">
      <h2>{{ title }} <em>{{ countText }}</em></h2>
      <p>{{ sub }}</p>
    </div>

    <div v-if="kpisHtml" class="reg-kpis kpis" v-html="kpisHtml" />

    <slot name="actions" />
  </div>

  <div class="reg__filters">
    <slot name="filters" />

    <button
      v-for="f in filters"
      :key="f.value"
      class="fchip"
      :class="{ 'is-on': filter === f.value }"
      type="button"
      @click="emit('update:filter', f.value)"
    >
      {{ f.label }} <em>{{ f.count }}</em>
    </button>

    <span class="reg__gap" />

    <label class="reg__seek">
      <IconSprite name="i-search" cls="ic" />
      <input
        type="search"
        :value="seekValue"
        :placeholder="seekPlaceholder"
        autocomplete="off"
        @input="onSeek"
      />
    </label>

    <span class="reg__sel">
      <select :aria-label="selectLabel" :value="selectValue" @change="onSelect">
        <option value="all">{{ selectLabel }}</option>
        <option v-for="o in selectOptions" :key="o.value" :value="o.value">
          {{ o.label }}
        </option>
      </select>
    </span>
  </div>

  <!-- 筛选条下方的可插拔面板（知识库的「检索试跑」就挂在这里） -->
  <slot name="panel" />

  <div class="reg__body" :class="bodyClass">
    <div class="reggrid__head" aria-hidden="true">
      <span>{{ head[0] }}</span><span>{{ head[1] }}</span><span>{{ head[2] }}</span>
    </div>
    <div class="reg__grid" :class="gridClass" role="list">
      <slot />
    </div>
  </div>
</template>