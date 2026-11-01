<!--
  删除确认 —— 等价迁移自原型 console.html 第 1136–1149 行 + console.js 的
  askOpsDelete / doOpsDelete / closeConfirm（4853–4883 / 2447–2448）。

  工具 / 知识库 / 网关 / 权限四页共用同一个弹窗（原型的 pendingDelete + pendingMode），
  点「确认删除」时按 mode 分发到对应 store 的 doDelete / doDelete。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useOverlayStore } from '@/stores/overlay'
import { useToolsStore } from '@/stores/tools'
import { useKbStore } from '@/stores/kb'
import { useGatewayStore } from '@/stores/gateway'
import { useAuthzStore } from '@/stores/authz'
import { useSessionStore } from '@/stores/session'

const overlay = useOverlayStore()
const tools = useToolsStore()
const kb = useKbStore()
const gateway = useGatewayStore()
const authz = useAuthzStore()
const session = useSessionStore()

const req = computed(() => overlay.confirm)

/** 确认按钮文案：默认「确认删除」，网关页是摘除映射 */
const okText = computed(() => req.value?.okText ?? '确认删除')

function onCancel(): void {
  overlay.closeConfirm()
}

function onConfirm(): void {
  const r = req.value
  if (!r) return
  const id = r.id
  switch (r.mode) {
    case 'tool':
      tools.doDelete(id)
      break
    case 'kb':
      kb.doDelete(id)
      break
    case 'gw':
      gateway.doDelete(id)
      break
    case 'perm':
      authz.doDelete(id)
      break
    case 'session':
      /* 工作台会话删除由工作台视图自己处理（它会重排工位） */
      session.selectSession(null)
      break
  }
  overlay.closeConfirm()
}
</script>

<template>
  <!-- 原型用 .is-on 控制显隐；没有请求时整块不渲染，避免遮挡点击 -->
  <div
    v-if="req"
    class="modal modal--mini is-on"
    id="confirmModal"
    role="dialog"
    aria-modal="true"
    aria-labelledby="confirmTitle"
    aria-hidden="false"
  >
    <div class="modal__card">
      <header class="modal__head">
        <h3 id="confirmTitle">{{ req.title }}</h3>
      </header>
      <p class="confirm__text" id="confirmText" v-html="req.text" />
      <footer class="modal__foot">
        <div class="modal__acts">
          <button class="btn btn--ghost" type="button" id="confirmNo" @click="onCancel">
            取消
          </button>
          <button class="btn btn--danger" type="button" id="confirmYes" @click="onConfirm">
            {{ okText }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>