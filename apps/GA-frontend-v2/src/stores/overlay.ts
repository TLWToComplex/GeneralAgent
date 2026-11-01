/* ============================================================================
   浮层 store —— 详情抽屉 / 删除确认 / 各页表单弹窗

   原型里这些是一堆散装全局变量 + hand-rolled DOM 渲染：
     · 636–635   openDrawer(kind, item) / closeDrawer()  —— 抽屉内容按 kind 拼 HTML
     · 2447–2448 pendingDelete / pendingMode             —— 删除确认
     · 各页 xxxModal 的 show/hide + 表单回填
   这里统一成一份状态，弹窗与抽屉的「打开 / 关闭 / 回填」全部走 store，
   内容渲染交给各自的 Vue 组件。
   ========================================================================== */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

/** 抽屉的七种形态（原型 openDrawer 的 kind 参数） */
export type DrawerKind =
  | 'session'
  | 'logs'
  | 'monitor'
  | 'registry'
  | 'model'
  | 'tool'
  | 'kb'
  | 'gw'
  | 'perm'

/** 删除确认要删的对象类型（原型的 pendingMode） */
export type DeleteMode = 'tool' | 'kb' | 'gw' | 'perm' | 'session'

/**
 * 表单弹窗的类型。
 * 注意：曾经还有 `'session'`（新建会话弹窗）—— 已删除，「新建会话」改成
 * 新标签页打开 dsh 控制台，会话在 dsh 里创建。
 */
export type ModalKind = 'tool' | 'kb' | 'gw' | 'perm'

export interface ConfirmRequest {
  title: string
  text: string
  /** 确认按钮文案（原型固定「删除」，网关页改成「摘除映射」等） */
  okText?: string
  mode: DeleteMode
  id: string
  name: string
}

export const useOverlayStore = defineStore('overlay', () => {
  /* ---------------------------------------------------------------- 详情抽屉 */
  const drawerOpen = ref(false)
  const drawerKind = ref<DrawerKind>('session')
  /** 抽屉对应的数据 id（由各页 store 按 id 取全量数据） */
  const drawerId = ref<string | null>(null)
  /** 抽屉标题（列表页用的是对象名，会话详情页用的是会话名） */
  const drawerTitle = ref('—')

  function openDrawer(kind: DrawerKind, id: string | null, title = '—'): void {
    drawerKind.value = kind
    drawerId.value = id
    drawerTitle.value = title
    drawerOpen.value = true
  }

  function closeDrawer(): void {
    drawerOpen.value = false
    drawerId.value = null
  }

  /* ---------------------------------------------------------------- 删除确认 */
  const confirm = ref<ConfirmRequest | null>(null)

  function askConfirm(req: ConfirmRequest): void {
    confirm.value = req
  }

  function closeConfirm(): void {
    confirm.value = null
  }

  /* ---------------------------------------------------------------- 表单弹窗 */
  const modalOpen = ref(false)
  const modalKind = ref<ModalKind | null>(null)
  /** 正在编辑的对象 id，null 表示新建 */
  const modalEditingId = ref<string | null>(null)
  /**
   * 网关 / 权限这两个运维页是「一行两张 + 三档信息带」的共用骨架，
   * 弹窗字段也跟着当前 tab 走，所以要额外记一个 tab。
   */
  const modalTab = ref<string | null>(null)

  function openModal(kind: ModalKind, editingId: string | null = null, tab: string | null = null): void {
    modalKind.value = kind
    modalEditingId.value = editingId
    modalTab.value = tab
    modalOpen.value = true
  }

  function closeModal(): void {
    modalOpen.value = false
    modalKind.value = null
    modalEditingId.value = null
    modalTab.value = null
  }

  /** 遮罩点击：抽屉与弹窗都要能关（弹窗优先） */
  function dismissTop(): void {
    if (modalOpen.value) {
      closeModal()
      return
    }
    if (confirm.value) {
      closeConfirm()
      return
    }
    if (drawerOpen.value) closeDrawer()
  }

  /** 是否有浮层打开（scrim 的显隐 + Esc 键） */
  const anyOpen = computed(
    () => drawerOpen.value || confirm.value !== null || modalOpen.value,
  )

  return {
    drawerOpen,
    drawerKind,
    drawerId,
    drawerTitle,
    openDrawer,
    closeDrawer,

    confirm,
    askConfirm,
    closeConfirm,

    modalOpen,
    modalKind,
    modalEditingId,
    modalTab,
    openModal,
    closeModal,

    anyOpen,
    dismissTop,
  }
})