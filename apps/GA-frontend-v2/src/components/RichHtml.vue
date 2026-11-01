<!--
  满格填充容器 —— 给「用 v-html 吐一串卡片」的地方当外层用。

  为什么需要它（这是一个真实踩过的坑）：
    卡片区的布局父级是 CSS Grid / Flex，比如
      .reg__grid.reggrid   → display:grid; grid-template-columns:repeat(2,minmax(0,1fr))
      .reg-kpis.kpis       → display:flex
    而 v-html 必须落在一个真实元素上，于是很自然会写成
      <div v-html="cardsHtml" />
    结果：这个 <div> 自己成了网格里**唯一的一个格子**，占掉第 1 列，
    所有卡片全挤在它肚子里纵向排——镜像中心看起来就是「一行只有一张、右边一大片空白」。

  修法：给这层包一层 `display:contents`。
    · 元素本身不生成盒子，不再是 grid/flex item；
    · 它的子元素（也就是 v-html 吐出来的那些卡片）直接成为父级网格/弹性容器的子项，
      与原型 `grid.innerHTML = list.map(...)` 的结构完全一致；
    · 事件委托依旧挂在这个元素上，data-* 委托照常冒泡。

  代价：display:contents 会把这个 div 从无障碍树里摘掉。这里无所谓 —— 它是
  `<div>`，本来就没有语义角色，语义在卡片自身的 role="listitem" 上。

  用法：
      <RichHtml :html="cardsHtml" @click="onCards" />
      <RichHtml :html="pzCardsHtml(pz.filtered)" />
-->
<script setup lang="ts">
defineProps<{ html: string }>()
</script>

<template>
  <div class="fill" v-html="html" />
</template>

<!--
  .fill{display:contents} 定义在 src/styles/console.css 末尾，
  不写在这里：组件自己的 <style> 会进按需加载的 CSS chunk，
  而本项目的 CSS 全部由 JS 注入，chunk 里的规则加载时机不可靠。
  console.css 由 App.vue 进入控制台时注入，必然存在。
-->