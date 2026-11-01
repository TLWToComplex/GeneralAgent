<!--
  左侧菜单栏 —— 等价迁移自原型 console.html 第 48–103 行。

  导航结构由 config/pages.ts 的 NAV 驱动（原型的侧栏是写死的 7 个 <a>）。
  「工作台」沿用原型的 is-on 默认高亮，实际高亮由当前路由决定。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import IconSprite from '@/components/IconSprite.vue'
import { NAV, PAGE_PATHS, isPageLocked } from '@/config/pages'
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
const route = useRoute()

/** 当前页面对应的侧栏 data-nav 标识 */
const activeNav = computed(() => {
  const page = route.meta.page as keyof typeof PAGE_PATHS | undefined
  if (!page) return ''
  return Object.values(NAV)
    .flatMap((g) => g.items)
    .find((it) => it.page === page)?.nav ?? ''
})
</script>

<template>
  <aside class="side" id="side">
    <div class="side__brand">
      <span class="side__logo" aria-hidden="true">
        <svg viewBox="0 0 40 40" class="side__logo-mark">
          <path
            d="M20 3.5l5.4 11.1 12.1 1.7-8.8 8.5 2.1 12-10.8-5.7-10.8 5.7 2.1-12-8.8-8.5 12.1-1.7z"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linejoin="round"
          />
          <circle cx="20" cy="19" r="3.1" fill="currentColor" />
        </svg>
      </span>
      <span class="side__wordmark">
        <b>GeneralAgent</b>
        <i>ORG-LEVEL AI PLATFORM</i>
      </span>
      <button
        class="side__fold"
        id="sideFold"
        type="button"
        aria-label="收起菜单栏"
        title="收起菜单栏"
        @click="ui.toggleFold()"
      >
        <IconSprite name="i-chev" />
      </button>
    </div>

    <nav class="side__nav" aria-label="主菜单">
      <template v-for="(group, gi) in NAV" :key="gi">
        <!--
          「运行」组省略组标题、只留工作台：会话 Workspace 与智能体已并入工作台的工位视图
        -->
        <p v-if="group.label" class="side__group">{{ group.label }}</p>

        <!--
          菜单项两种形态：
            · 正常项 —— 可点的 <RouterLink>
            · 「开发中」项 —— 渲染成 <span>（**根本不是链接**，所以连"点了没反应"
              这种状态都不存在），置灰并挂个「开发中」小标。
          真源是 config/pages.ts 的 locked 字段；用 span 而不是给链接加
          pointer-events:none，是因为后者键盘仍能 Tab 上去回车进入，语义也不对。
          span 没有 href，不会被 Tab 聚焦，屏幕阅读器也不会把它报成链接。
        -->
        <template v-for="item in group.items" :key="item.nav">
          <span
            v-if="isPageLocked(item.page)"
            class="side__link is-locked"
            :data-nav="item.nav"
            aria-disabled="true"
            title="功能开发中，暂不可进入"
          >
            <IconSprite :name="item.icon" />
            <span>{{ item.label }}</span>
            <em class="side__badge side__badge--dev">开发中</em>
          </span>

          <RouterLink
            v-else
            class="side__link"
            :class="{ 'is-on': activeNav === item.nav }"
            :to="PAGE_PATHS[item.page]"
            :data-nav="item.nav"
          >
            <IconSprite :name="item.icon" />
            <span>{{ item.label }}</span>
            <em v-if="item.badge" class="side__badge">{{ item.badge }}</em>
          </RouterLink>
        </template>
      </template>
    </nav>

    <div class="side__foot">
      <span class="side__quota">
        <i>GPU 池配额</i>
        <b><span id="quotaBar" :style="{ width: ui.quotaPct + '%' }"></span></b>
        <em id="quotaText">{{ ui.quotaPct }}%</em>
      </span>
      <span class="side__user">
        <span class="avatar">运</span>
        <span class="side__user-txt"><b>平台运维</b><i>超级管理员</i></span>
      </span>
    </div>
  </aside>
</template>