<template>
  <ProcessBlock
    v-if="shouldShow"
    class="ic"
    variant="alert"
    :collapsible="false"
    :status="blockStatus"
    :verb="verbText"
  >
    <template #content>
      <p class="ic-body">{{ interruptData.content }}</p>

      <!-- 决策前：两个动作按钮；决策后：一行弱化的结果回执 -->
      <div v-if="status === 'pending'" class="ic-actions">
        <button type="button" class="ic-btn ic-btn--ghost" @click="handleCancel">
          {{ interruptData.cancelText }}
        </button>
        <button type="button" class="ic-btn ic-btn--primary" @click="handleConfirm">
          {{ interruptData.okText }}
        </button>
      </div>
      <div v-else class="ic-receipt" :class="`is-${status}`">
        {{ status === 'confirmed' ? `已${interruptData.okText}` : `已${interruptData.cancelText}` }}
      </div>
    </template>
  </ProcessBlock>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { Message } from '@/types/mcp';
import { useChatStore } from '@/stores/chat-store';
import ProcessBlock from './ProcessBlock.vue';
import type { ProcessStatus } from '@/utils/processStatus';

const props = defineProps<{
  message: Message;
}>();

const chatStore = useChatStore();
const status = ref<'pending' | 'confirmed' | 'cancelled'>('pending');

const interruptData = computed(() => {
  const msg = props.message.interrupt?.message;
  if (typeof msg === 'string') {
    return {
      content: msg,
      okText: '确认',
      cancelText: '取消',
      isInterrupt: 'true'
    };
  }
  return {
    content: msg?.content || '',
    okText: msg?.okText || '确认',
    cancelText: msg?.cancelText || '取消',
    isInterrupt: typeof msg === 'object' && msg?.isInterrupt !== undefined ? String(msg.isInterrupt) : 'true'
  };
});

const shouldShow = computed(() => {
  // 如果是行程总结阶段，不显示打断卡片
  if (props.message.stage === '行程总结') {
    return false;
  }
  return interruptData.value.isInterrupt !== 'false';
});

/** 审批是唯一允许「重」的过程块：待确认走 awaiting-approval，决策后落到终态 */
const blockStatus = computed<ProcessStatus>(() => {
  if (status.value === 'confirmed') return 'completed';
  if (status.value === 'cancelled') return 'denied';
  return 'awaiting-approval';
});

const verbText = computed(() => {
  if (status.value === 'confirmed') return '已确认';
  if (status.value === 'cancelled') return '已取消';
  return '需要你确认';
});

const handleConfirm = () => {
  status.value = 'confirmed';
  chatStore.sendMessage(interruptData.value.okText);
};

const handleCancel = () => {
  status.value = 'cancelled';
  chatStore.sendMessage(interruptData.value.cancelText);
};
</script>

<style scoped>
.ic {
  margin: 10px 0;
}

.ic-body {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--pb-subject);
  white-space: pre-wrap;
  word-break: break-word;
}

/* ---- 动作按钮：主按钮用琥珀（风险色），次按钮彻底中性 ---- */

.ic-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
}

.ic-btn {
  height: 30px;
  min-width: 76px;
  padding: 0 14px;
  border-radius: 6px;
  border: 1px solid transparent;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
  transition: background-color 180ms ease, border-color 180ms ease, color 180ms ease;
}

.ic-btn--ghost {
  background: transparent;
  border-color: color-mix(in srgb, var(--pb-label) 28%, transparent);
  color: var(--pb-verb);
}

.ic-btn--ghost:hover {
  background: color-mix(in srgb, var(--pb-label) 9%, transparent);
  color: var(--pb-subject);
}

.ic-btn--primary {
  background: var(--pb-c-warn);
  border-color: var(--pb-c-warn);
  color: #fff;
}

.ic-btn--primary:hover {
  background: color-mix(in srgb, var(--pb-c-warn) 88%, #000);
  border-color: color-mix(in srgb, var(--pb-c-warn) 88%, #000);
}

.ic-btn:focus-visible {
  outline: 2px solid var(--pb-c-warn);
  outline-offset: 2px;
}

/* ---- 决策回执：一行灰字，不再抢视觉 ---- */

.ic-receipt {
  margin-top: 10px;
  font-size: 12px;
  color: var(--pb-meta);
}

.ic-receipt.is-confirmed {
  color: var(--pb-c-done);
}

/* ---- 终态：琥珀降权为中性，只保留左边框作为「这里曾需要审批」的痕迹 ---- */

.ic.pb--completed,
.ic.pb--denied {
  background: transparent;
}

.ic.pb--completed {
  border-left-color: var(--pb-c-done);
}

.ic.pb--denied {
  border-left-color: var(--pb-c-idle);
}

.ic.pb--completed :deep(.pb-verb) {
  color: var(--pb-c-done);
  font-weight: 500;
}

.ic.pb--denied :deep(.pb-verb) {
  color: var(--pb-meta);
  font-weight: 500;
}
</style>
