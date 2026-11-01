/* ============================================================================
   心跳调度器 —— 替代原型 console.js 5207–5397 那个大 beat()

   原型用一串 `if (R.page === 'xxx') { … return; }` 在同一个函数里分发到各页，
   每页只做「局部字段刷新 + 只 patch [data-role] 节点」这件事。
   迁到 Vue 后响应式接管了 DOM 更新，所以这里只保留「按当前页面驱动各页 store 的
   数据变化」这一层，DOM 由 Vue 自己决定怎么最小化更新。

   同时把定时器登记进 ui store，退出登录时能一次性清掉
   （原型对应 stopAllTimers()）。
   ========================================================================== */

import { watch, onBeforeUnmount, onMounted } from 'vue'
import type { PageId } from '@/config/pages'
import { useUiStore } from '@/stores/ui'
import { useSessionStore } from '@/stores/session'
import { useRegistryStore } from '@/stores/registry'
import { useModelsStore } from '@/stores/models'
import { useToolsStore } from '@/stores/tools'
import { useKbStore } from '@/stores/kb'
import { useGatewayStore } from '@/stores/gateway'
import { useAuthzStore } from '@/stores/authz'

export function useHeartbeat(pageId: () => PageId | undefined): void {
  const ui = useUiStore()
  const session = useSessionStore()
  const registry = useRegistryStore()
  const models = useModelsStore()
  const tools = useToolsStore()
  const kb = useKbStore()
  const gateway = useGatewayStore()
  const authz = useAuthzStore()

  /** 原型每页心跳只刷新自己那一页的数据 */
  const byPage: Record<PageId, () => void> = {
    workbench: () => {
      session.beat()
      ui.gatewayMs = Math.round(session.avgGpu / 4 + 9)
      ui.quotaPct = Math.min(96, Math.max(24, Math.round(session.avgGpu * 0.9 + 18)))
    },
    registry: () => registry.beat(),
    models: () => models.beat(),
    toolplatform: () => tools.beat(),
    kb: () => kb.beat(),
    gateway: () => gateway.beat(),
    authz: () => authz.beat(),
  }

  let timer: number | null = null

  function tick(): void {
    const id = pageId()
    if (!id) return
    const fn = byPage[id]
    if (fn) fn()
  }

  function start(): void {
    stop()
    /* 原型间隔 1800ms（prefers-reduced-motion 时放慢到 2600ms） */
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false
    timer = window.setInterval(tick, reduce ? 2600 : 1800)
    ui.registerTimer(timer)
  }

  function stop(): void {
    if (timer !== null) {
      window.clearInterval(timer)
      timer = null
    }
  }

  /* 标签页隐藏时停心跳（原型 visibilitychange），回到前台再恢复 */
  function onVisibility(): void {
    if (document.hidden) stop()
    else if (timer === null) start()
  }

  onMounted(() => {
    start()
    document.addEventListener('visibilitychange', onVisibility)
  })

  /* 切页时立刻打一拍，让新页面马上有「活着」的数据 */
  watch(pageId, () => tick())

  onBeforeUnmount(() => {
    stop()
    document.removeEventListener('visibilitychange', onVisibility)
  })
}