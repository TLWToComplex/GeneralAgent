<!--
  控制台外壳 —— 等价迁移自原型 console.html 第 45–745 行。

  结构对齐原型：
    .shell
      ├─ AppSidebar（<aside class="side">）
      └─ .main
           ├─ AppTopbar（<header class="topbar">）
           ├─ 工作台交互区 <section class="stage"> —— 只在工作台页渲染
           │    （原型 index.html 的 stage 是静态的，其余六页的 .subpage 也在里面）
           └─ 各页 <section class="subpage"> —— 由路由懒挂载

  ⚠️ 关键：原型的七个页面互斥靠 console.css 的
       .subpage { display:none !important }
       body[data-page="X"] #X { display:flex !important }
     这一组规则。迁到 Vue 后这里改成「路由只挂载当前页」，
     但 body[data-page] 仍然照写 —— 一来让那组规则继续成立（视觉零回归），
     二来其它依赖 data-page 的样式（如 .stage 的显隐）不用改一行 CSS。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import ToastHost from '@/components/overlay/ToastHost.vue'
import ConfirmDialog from '@/components/overlay/ConfirmDialog.vue'
import DetailDrawer from '@/components/overlay/DetailDrawer.vue'
import ToolModal from '@/components/overlay/ToolModal.vue'
import KbModal from '@/components/overlay/KbModal.vue'
import GwModal from '@/components/overlay/GwModal.vue'
import PzModal from '@/components/overlay/PzModal.vue'
import WorkbenchView from '@/views/workbench/WorkbenchView.vue'
import { PAGES } from '@/config/pages'
import type { PageId } from '@/config/pages'
import { useUiStore } from '@/stores/ui'
import { useOverlayStore } from '@/stores/overlay'

const ui = useUiStore()
const overlay = useOverlayStore()
const route = useRoute()

const pageId = computed<PageId>(() => (route.meta.page as PageId | undefined) ?? 'workbench')

/**
 * body[data-page] 同步。原型是 switchPage 里 document.body.setAttribute('data-page', page)。
 * 同时按 body 的类名同步 is-folded / is-open（原型的侧栏状态就落在这两个类上）。
 */
watch(
  pageId,
  (id) => {
    document.body.setAttribute('data-page', id)
    document.body.setAttribute('data-shell', 'console')
  },
  { immediate: true },
)

watch(
  () => [ui.folded, ui.open],
  ([folded, open]) => {
    document.body.classList.toggle('is-folded', folded)
    document.body.classList.toggle('is-open', open)
  },
  { immediate: true },
)

/* 遮罩点击与 Esc：关掉最上层的浮层（原型 scrim + 键盘处理） */
function onScrim(): void {
  overlay.dismissTop()
}

function onKeydown(e: KeyboardEvent): void {
  if (e.key !== 'Escape') return
  if (!overlay.anyOpen) return
  e.preventDefault()
  overlay.dismissTop()
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.removeAttribute('data-page')
  document.body.removeAttribute('data-shell')
  document.body.classList.remove('is-folded', 'is-open', 'is-settled')
})

/* ============================================================================
   入场动画「只放一次」

   卡片是用 v-html 输出的一整段 HTML：心跳每 1800ms 改动一个数字，Vue 就会把
   整块 innerHTML 换掉，新插入的卡片重新触发自己的入场动画。
   实测（headless Chrome + MutationObserver，8 秒窗口）：
       镜像中心 网格子树变动 80 次 / 入场动画重放 56 次
       模型中心 72 / 80，工具平台 64 / 36，工作台 338 / 4，权限中心 0 / 0
   而 cardPop 是 translateY(8px) → 0，所以肉眼看到的就是
   「页面一直在刷新，而且内容往上跳一下」。

   这里在首屏稳定之后给 body 挂 is-settled，
   console.css 末尾那组 body.is-settled 规则会把「重建区域里」的入场动画关掉。
   数字照旧每秒更新（顶层 .kpi 的数字与 .stchip.is-blink 的呼吸点不受影响），
   只是不再重放动画。
   ========================================================================== */
let settleTimer: number | null = null
onMounted(() => {
  settleTimer = window.setTimeout(() => {
    document.body.classList.add('is-settled')
    settleTimer = null
  }, 1400)
  ui.registerTimer(settleTimer)
})

export type { PageId }
</script>

<template>
  <div class="shell">
    <AppSidebar />
    <main class="main">
      <AppTopbar />

      <!-- 工作台交互区：原型它是常驻 DOM，用 body[data-page] 控制显隐。
           这里只在工作台页挂载，但 class 与 id 保持不变。 -->
      <WorkbenchView v-if="pageId === 'workbench'" />

      <!-- 其余六页：各自渲染 <section class="subpage" id="..."> -->
      <RouterView v-else />

      <!-- 面包屑尾部兜底：某些页面标题依赖 PAGES 的 tail -->
      <span hidden>{{ PAGES[pageId].tail }}</span>
    </main>
  </div>

  <!-- 浮层：抽屉 / 表单弹窗 / 删除确认 / 轻提示，原型里都是 shell 之外的同级节点 -->
  <DetailDrawer />
  <!-- 「新建会话」不再是弹窗：它改成新标签页打开 dsh 控制台（见 views/workbench/WorkbenchView.vue） -->
  <ToolModal v-if="overlay.modalOpen && overlay.modalKind === 'tool'" />
  <KbModal v-if="overlay.modalOpen && overlay.modalKind === 'kb'" />
  <GwModal v-if="overlay.modalOpen && overlay.modalKind === 'gw'" />
  <PzModal v-if="overlay.modalOpen && overlay.modalKind === 'perm'" />
  <ConfirmDialog />
  <div class="scrim" :class="{ 'is-on': overlay.anyOpen }" id="scrim" @click="onScrim" />
  <ToastHost />
</template>