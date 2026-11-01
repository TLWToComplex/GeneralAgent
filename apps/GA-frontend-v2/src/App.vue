<!--
  应用根组件

  职责有两个：
    1. 为全站挂一次图标精灵（原型是每个 html 各写一份 <svg class="sprite">）
    2. 按路由挂载对应的全局样式表 —— 原型的两个页面各引自己的 CSS，
       Vue 里把它做成「进入控制台才加载 console.css」的懒加载，登录页只带 login.css。

  注意：这两张表就是原型的 console.css / login.css，逐字节复制过来、类名未改，
  所以全部视觉与原型一致。
-->
<script setup lang="ts">
import { onBeforeUnmount, watch } from 'vue'
import { useRoute } from 'vue-router'
import IconDefs from '@/components/IconDefs.vue'

const route = useRoute()

/** 已挂载的样式表 <link>，按路径去重 */
const loaded = new Map<string, HTMLLinkElement>()

function ensureStyle(id: string, href: string): void {
  if (loaded.has(id)) return
  const link = document.createElement('link')
  link.rel = 'stylesheet'
  link.href = href
  link.dataset.sheet = id
  document.head.appendChild(link)
  loaded.set(id, link)
}

function syncStyles(shell: boolean): void {
  if (shell) {
    ensureStyle('console', new URL('./styles/console.css', import.meta.url).href)
  } else {
    ensureStyle('login', new URL('./styles/login.css', import.meta.url).href)
  }
}

watch(
  () => route.meta.shell === true,
  (shell) => syncStyles(shell),
  { immediate: true },
)

onBeforeUnmount(() => {
  loaded.forEach((link) => link.remove())
  loaded.clear()
})
</script>

<template>
  <IconDefs />
  <RouterView />
</template>