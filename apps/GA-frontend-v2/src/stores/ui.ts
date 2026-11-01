/* ============================================================================
   外壳 UI store —— 侧栏 / 顶栏 / 指标条 / 轻提示

   对应原型里散落在 console.js 的这几处：
     · 5677–5690  bindEvents() 里的侧栏折叠与移动端展开（body 上的 is-folded / is-open）
     · 5178–5195  tickKpi()     顶栏「统一网关 xx ms」与侧栏「GPU 池配额 xx%」
     · 4886–4901  toast()       右下角轻提示
     · 5498–5505  pushToast()   带标题 + 多行正文的轻提示

   原型用 document.body.classList 承载 is-folded / is-open，Vue 里仍写回 body，
   但状态源放在 store，这样任何组件都能读到并切换。
   ========================================================================== */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface ToastLine {
  /** 可选的标题行（pushToast 的第一行，加粗） */
  title?: string
  /** 正文行（多行依次渲染） */
  lines: string[]
}

export const useUiStore = defineStore('ui', () => {
  /* ---------------------------------------------------------------- 侧栏 */
  /** 折叠成窄栏（原型 body.is-folded） */
  const folded = ref(false)
  /** 移动端抽屉式展开（原型 body.is-open） */
  const open = ref(false)

  function toggleFold(): void {
    folded.value = !folded.value
    document.body.classList.toggle('is-folded', folded.value)
  }

  function toggleOpen(): void {
    open.value = !open.value
    document.body.classList.toggle('is-open', open.value)
  }

  function closeOpen(): void {
    open.value = false
    document.body.classList.remove('is-open')
  }

  /* ---------------------------------------------------------------- 顶栏 */
  /** 顶栏搜索词。各页共享同一个输入框，切换页面时由页面写回自己的搜索词 */
  const query = ref('')
  /** 顶栏搜索框占位文案（来自 PAGES[page].ph） */
  const placeholder = ref('搜索会话 / 智能体 / workspace 路径')
  /** 顶栏「统一网关 xx ms」 */
  const gatewayMs = ref(12)
  /** 通知小圆点（点过通知后隐藏） */
  const bellDot = ref(true)
  /** 侧栏 GPU 池配额百分比 */
  const quotaPct = ref(68)
  /** 今日派发会话数（原型的 distToday） */
  const distToday = ref(148)

  function setQuery(v: string): void {
    query.value = v
  }

  /* ---------------------------------------------------------------- 轻提示 */
  const toast = ref<{ on: boolean; title: string; lines: string[] }>({
    on: false,
    title: '',
    lines: [],
  })
  let toastTimer: number | null = null

  /** 原型 toast(html)：直接给一段 HTML（内部已转义），显示 2.6 秒 */
  function pushHtml(html: string): void {
    toast.value = { on: true, title: html, lines: [] }
    if (toastTimer !== null) window.clearTimeout(toastTimer)
    toastTimer = window.setTimeout(() => {
      toast.value.on = false
    }, 2600)
  }

  /** 原型 pushToast(title, lines)：标题加粗 + 若干灰色正文行 */
  function pushText(title: string, lines: string[] = []): void {
    pushHtml('')
    toast.value = { on: true, title, lines }
    if (toastTimer !== null) window.clearTimeout(toastTimer)
    toastTimer = window.setTimeout(() => {
      toast.value.on = false
    }, 2600)
  }

  function closeToast(): void {
    toast.value.on = false
    if (toastTimer !== null) {
      window.clearTimeout(toastTimer)
      toastTimer = null
    }
  }

  /* ---------------------------------------------------------------- 心跳定时器登记 */
  /**
   * 原型 signOut() 要停掉「本次会话注册过的所有定时器」。
   * 这里把各页心跳 timer 统一登记，登出时一次性清理。
   */
  const timers = ref<number[]>([])

  function registerTimer(id: number): void {
    timers.value.push(id)
  }

  function stopAllTimers(): void {
    /* 这里同时用 clearInterval 和 clearTimeout：两者在浏览器里共用同一个 id 空间，
       所以登记进来的既有 setInterval 也有一次性的 setTimeout（如外壳的 is-settled）。 */
    timers.value.forEach((id) => {
      window.clearInterval(id)
      window.clearTimeout(id)
    })
    timers.value = []
    if (toastTimer !== null) {
      window.clearTimeout(toastTimer)
      toastTimer = null
    }
  }

  const hasTimers = computed(() => timers.value.length > 0)

  return {
    folded,
    open,
    toggleFold,
    toggleOpen,
    closeOpen,

    query,
    placeholder,
    gatewayMs,
    bellDot,
    quotaPct,
    distToday,
    setQuery,

    toast,
    pushHtml,
    pushText,
    closeToast,

    timers,
    hasTimers,
    registerTimer,
    stopAllTimers,
  }
})