import { computed, onUnmounted, ref, watch } from 'vue';
import type { Message } from '@/types/mcp';
import { getToolPresentation } from '@/utils/toolPresentation';

export const AGENT_PROGRESS_IDLE_MS = 3000;

export function getAgentWaitingLabel(message: Message): string {
  const running = [...(message.tool_calls || [])].reverse().find(tool => tool.status === 'executing');
  if (!running) return '正在规划下一步';
  const info = getToolPresentation(running);
  const labels = {
    read: '正在读取文件', write: '正在更新文件', command: '正在执行命令',
    search: '正在搜索', browser: '正在操作浏览器', mcp: '正在调用工具', tool: '正在调用工具'
  };
  return `${labels[info.kind]}，等待结果`;
}

// 只计入可见内容/状态的进展；心跳、重新包装消息对象不应清除等待提示。
export function getAgentProgressSignature(message: Message): string {
  return JSON.stringify([
    message.content, message.reasoning_content, message.orchestratorBlocks,
    message.tool_calls, message.todos, message.stage
  ]);
}

// 尚未收到有效首帧时保留原有「正在思考」占位，不启动步骤间等待计时。
export function hasAgentProgress(message: Message): boolean {
  return !!(message.content?.trim() || message.reasoning_content?.trim()
    || message.tool_calls?.length || message.todos?.length || message.stage?.trim()
    || message.orchestratorBlocks?.some(block => block.type === 'tools'
      ? block.toolCallIds.length > 0 : !!block.content?.trim()));
}

export function useAgentProgress(getMessage: () => Message, isAgent: () => boolean) {
  const isIdle = ref(false);
  let timer: ReturnType<typeof setTimeout> | undefined;
  const active = computed(() => {
    const message = getMessage();
    return isAgent() && message.role === 'assistant' && !!message.isStreaming
      && !message.interrupt && !(message as Message & { isStopped?: boolean }).isStopped;
  });
  const clearTimer = () => {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
  };
  watch([() => active.value, () => active.value ? getAgentProgressSignature(getMessage()) : ''], () => {
    clearTimer();
    isIdle.value = false;
    if (active.value && hasAgentProgress(getMessage())) timer = setTimeout(() => { isIdle.value = true; }, AGENT_PROGRESS_IDLE_MS);
  }, { immediate: true });
  onUnmounted(clearTimer);
  const isWaiting = computed(() => active.value && isIdle.value);
  const waitingLabel = computed(() => getAgentWaitingLabel(getMessage()));
  return { isWaiting, waitingLabel };
}
