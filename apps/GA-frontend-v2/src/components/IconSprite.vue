<!--
  图标精灵 —— 24×24 描边风格，靠 CSS 的 stroke:currentColor 上色。
  等价迁移自原型 console.html 第 12–43 行，symbol 内容一字未改。

  用法：<Icon name="i-grid" />  →  <svg class="ic"><use href="#i-grid"/></svg>
  精灵本体已在 App.vue 里挂载一次。
-->
<script setup lang="ts">
withDefaults(
  defineProps<{
    /** symbol id（i-grid / i-model / …） */
    name: string
    /** 自定义 class，默认 .ic */
    cls?: string
  }>(),
  { cls: 'ic' },
)
</script>

<template>
  <svg :class="cls" aria-hidden="true" focusable="false">
    <use :href="`#${name}`" />
  </svg>
</template>