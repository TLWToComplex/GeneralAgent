<!--
  顶栏 —— 等价迁移自原型 console.html 第 108–140 行。

  三处行为来自原型 console.js：
    · 1280–1297 / 5734–5776  顶栏搜索按当前页面的 search 语义分发到各页筛选，
                             并与页内搜索框双向同步（各自 160ms 防抖）
    · 5677–5690              左侧汉堡按钮（移动端展开侧栏）
    · 4896–4960  signOut()   退出登录：清「记住账号」→ 停掉全部定时器 → 回登录页

  与原型不同：右上角身份卡改为展示真实登录用户（姓名/账号首字做头像），
  退出登录同时清掉登录态（令牌 + 用户信息），否则刷新页面又会被守卫放进来。
-->
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import IconSprite from '@/components/IconSprite.vue'
import { PAGES } from '@/config/pages'
import type { PageId } from '@/config/pages'
import { useAuthStore } from '@/stores/auth'
import { useUiStore } from '@/stores/ui'
import { useOverlayStore } from '@/stores/overlay'
import { useSessionStore } from '@/stores/session'
import { useRegistryStore } from '@/stores/registry'
import { useModelsStore } from '@/stores/models'
import { useToolsStore } from '@/stores/tools'
import { useKbStore } from '@/stores/kb'
import { useGatewayStore } from '@/stores/gateway'
import { useAuthzStore } from '@/stores/authz'
import { rememberKey } from '@/config/runtime'

const ui = useUiStore()
const overlay = useOverlayStore()
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const session = useSessionStore()
const registry = useRegistryStore()
const models = useModelsStore()
const tools = useToolsStore()
const kb = useKbStore()
const gateway = useGatewayStore()
const authz = useAuthzStore()

const pageId = computed<PageId>(() => (route.meta.page as PageId | undefined) ?? 'workbench')
const meta = computed(() => PAGES[pageId.value])

/**
 * 顶栏搜索与页内搜索的同步表。原型用 PAGES[page].search 分发，
 * 这里把「取当前词 / 设当前词」两头都集中成一张表，避免散落的 if。
 */
const SEARCH = {
  sessions: { get: () => session.query, set: (v: string) => session.setQuery(v) },
  registry: { get: () => registry.q, set: (v: string) => registry.setQuery(v) },
  models: { get: () => models.q, set: (v: string) => models.setQuery(v) },
  tools: { get: () => tools.q, set: (v: string) => tools.setQuery(v) },
  kb: { get: () => kb.q, set: (v: string) => kb.setQuery(v) },
  gw: { get: () => gateway.q, set: (v: string) => gateway.setQuery(v) },
  perm: { get: () => authz.q, set: (v: string) => authz.setQuery(v) },
} as const

const seekEl = ref<HTMLInputElement | null>(null)
/** 输入框自己的值（受控），切换页面时要把新页面的词读进来 */
const draft = ref('')

/* 切换页面：把该页搜索词与占位文案灌进顶栏输入框 */
watch(
  () => meta.value.search,
  (scope) => {
    draft.value = SEARCH[scope].get()
    ui.placeholder = meta.value.ph
  },
  { immediate: true },
)

/* 反向同步：页内搜索框改动后，顶栏也要跟着变 */
watch(
  () => SEARCH[meta.value.search].get(),
  (v) => {
    if (v !== draft.value) draft.value = v
  },
)

let seekTimer: number | null = null
function onSeekInput(): void {
  if (seekTimer !== null) window.clearTimeout(seekTimer)
  // 原型是 160ms 防抖（避免每敲一个字就重排整页卡片）
  seekTimer = window.setTimeout(() => {
    SEARCH[meta.value.search].set(draft.value.trim())
  }, 160)
}

/* Ctrl/⌘ + K 聚焦搜索框（原型 <kbd>Ctrl K</kbd> 的提示语义） */
function onKeydown(e: KeyboardEvent): void {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    seekEl.value?.focus()
    seekEl.value?.select()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  window.removeEventListener('keydown', onKeydown)
  if (seekTimer !== null) window.clearTimeout(seekTimer)
})

/* 通知：列出最近的告警日志，点过之后小圆点消失 */
function onBell(): void {
  const warns = session.warnLogs(3)
  ui.pushText(
    '告警通知',
    warns.length ? warns.map((l) => `${l.t}  ${l.m}`) : ['当前没有新的告警'],
  )
  ui.bellDot = false
}

/* 身份卡：真实登录用户（未登录时兜底展示，正常走不到 —— 路由守卫已挡住） */
const chipName = computed(() => auth.displayName || '未登录')
const chipAvatar = computed(() => auth.avatarText)
const chipTitle = computed(() => {
  const u = auth.user
  if (!u) return '当前未登录'
  /* 免登录模式：没有可退的会话，标题直接说明身份从哪来（排查"为什么没登录页"用） */
  if (auth.isSkipLogin) return `${u.username} · 免登录模式（config.json 的 skipLogin=true）`
  const role = auth.isAdmin ? '管理员' : '普通用户'
  return `${u.realname || u.username}（${u.username}）· ${role}`
})

/* 退出登录 */
const signingOut = ref(false)
function signOut(): void {
  if (signingOut.value) return
  signingOut.value = true
  try {
    window.localStorage.removeItem(rememberKey())
  } catch {
    /* 隐私模式忽略 */
  }
  ui.stopAllTimers()
  overlay.closeDrawer()
  overlay.closeModal()
  overlay.closeConfirm()
  ui.closeToast()
  // 清登录态必须在跳转前完成：守卫读的是 store 状态，漏了就会被"已登录"再放回控制台
  auth.clearSession()
  void router.replace('/login')
}
</script>

<template>
  <header class="topbar">
    <button
      class="topbar__burger"
      id="burger"
      type="button"
      aria-label="展开菜单栏"
      @click="ui.toggleOpen()"
    >
      <IconSprite name="i-list" />
    </button>

    <p class="crumbs">
      <span id="crumbHead">{{ meta.head }}</span><IconSprite name="i-chev" /><b id="crumbTail">{{ meta.tail }}</b>
    </p>

    <label class="seek">
      <IconSprite name="i-search" />
      <input
        id="seek"
        ref="seekEl"
        v-model="draft"
        type="search"
        :placeholder="ui.placeholder"
        autocomplete="off"
        @input="onSeekInput"
      />
      <kbd>Ctrl K</kbd>
    </label>

    <span class="pill pill--live" id="gatewayPill" @click="overlay.openDrawer('monitor', null, '统一网关')">
      <i class="dot"></i>统一网关 <b id="gatewayMs">{{ ui.gatewayMs }}ms</b>
    </span>

    <button class="iconbtn" id="bellBtn" type="button" aria-label="通知" @click="onBell">
      <IconSprite name="i-bell" />
      <em v-if="ui.bellDot" class="iconbtn__dot">3</em>
    </button>

    <button class="chipbtn" type="button" id="userChip" :title="chipTitle">
      <span class="avatar">{{ chipAvatar }}</span><span>{{ chipName }}</span>
    </button>

    <!-- 退出登录：回到统一登录页（登录页成功后进的正是控制台）
         免登录模式（config.json 的 skipLogin=true）下没有会话可退，整个按钮不渲染 ——
         否则点一下就会被守卫弹回控制台，看起来"按钮坏了" -->
    <button
      v-if="!auth.isSkipLogin"
      class="logoutbtn"
      type="button"
      id="logoutBtn"
      title="退出登录，返回统一登录页"
      :disabled="signingOut"
      :aria-busy="signingOut"
      @click="signOut"
    >
      <svg class="ic" aria-hidden="true" viewBox="0 0 24 24">
        <path d="M14.2 3.6H6.4A2.2 2.2 0 0 0 4.2 5.8v12.4a2.2 2.2 0 0 0 2.2 2.2h7.8" />
        <path d="M15.8 8.3L19.5 12l-3.7 3.7" />
        <path d="M9.4 12h10" />
      </svg>
      <span>退出</span>
    </button>
  </header>
</template>