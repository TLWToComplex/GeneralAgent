<!--
  轻提示 —— 等价迁移自原型 console.html 第 801 行 + console.js 的 toast()（4885–4895）。

  行为对齐原型：
    · 一次只显示一条，标题可带 <b> 等标签（所以用 v-html；内容由调用方转义/受控）
    · 下面最多三行补充说明
    · 2600ms 后自动淡出；新消息会顶掉旧的并重置计时
-->
<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <div class="toast" id="toast" role="status" aria-live="polite" :class="{ 'is-on': ui.toast.on }">
    <b class="toast__title" v-html="ui.toast.title" />
    <ul v-if="ui.toast.lines.length" class="toast__lines">
      <li v-for="(l, i) in ui.toast.lines" :key="i">{{ l }}</li>
    </ul>
  </div>
</template>