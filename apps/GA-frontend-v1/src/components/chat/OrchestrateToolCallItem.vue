<template>
  <ProcessBlock
    class="tci"
    variant="row"
    :status="status"
    :verb="verb"
    :subject="presentation.subject"
    :auto-expand="false"
    :duration="tool.duration"
    :max-height="320"
    :auto-follow="argsStreaming"
  >
    <template #indicator>
      <StatusIndicator v-if="status === 'running' || status === 'streaming' || status === 'error' || status === 'denied'" :status="status" />
      <component v-else :is="toolIcon" class="tci-icon" aria-hidden="true" />
    </template>

    <template #content>
      <!-- 参数 -->
      <div v-if="parsedArguments" class="tci-sec">
        <div class="tci-sec-head">
          <span class="tci-sec-label">参数</span>
          <button class="tci-copy" title="复制参数" @click="copyToolArgs">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25v-7.5z"/>
              <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25v-7.5zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25h-7.5z"/>
            </svg>
          </button>
        </div>
        <pre class="pb-code" @scroll.self="onCodeScroll">{{ parsedArguments }}<span v-if="argsStreaming" class="pb-caret">▌</span></pre>
      </div>

      <!-- 执行结果 -->
      <div v-if="result" class="tci-sec">
        <div class="tci-sec-head">
          <span class="tci-sec-label" :class="{ 'tci-sec-label--error': status === 'error' }">执行结果</span>
          <button class="tci-copy" title="复制结果" @click="copyToolResult">
            <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
              <path d="M0 6.75C0 5.784.784 5 1.75 5h1.5a.75.75 0 010 1.5h-1.5a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-1.5a.75.75 0 011.5 0v1.5A1.75 1.75 0 019.25 16h-7.5A1.75 1.75 0 010 14.25v-7.5z"/>
              <path d="M5 1.75C5 .784 5.784 0 6.75 0h7.5C15.216 0 16 .784 16 1.75v7.5A1.75 1.75 0 0114.25 11h-7.5A1.75 1.75 0 015 9.25v-7.5zm1.75-.25a.25.25 0 00-.25.25v7.5c0 .138.112.25.25.25h7.5a.25.25 0 00.25-.25v-7.5a.25.25 0 00-.25-.25h-7.5z"/>
            </svg>
          </button>
        </div>
        <pre class="pb-code" @scroll.self="onCodeScroll">{{ formattedResult }}</pre>
      </div>

      <!-- 错误信息 -->
      <div v-if="tool.error" class="tci-error">{{ tool.error }}</div>
    </template>
  </ProcessBlock>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount } from 'vue';
import { FileTextOutlined, EditOutlined, GlobalOutlined, CodeOutlined, ToolOutlined, DesktopOutlined } from '@ant-design/icons-vue';
import StatusIndicator from './StatusIndicator.vue';
import { getToolPresentation } from '@/utils/toolPresentation';
import ProcessBlock from './ProcessBlock.vue';
import NotificationService from '@/utils/NotificationService.ts';
import { copyText } from '@/utils/clipboard.ts';
import {
  normalizeProcessStatus,
  formatToolArguments,
  isArgumentsStreaming,
  type ProcessStatus,
} from '@/utils/processStatus';

const props = defineProps<{
  tool: any;
  isStreaming: boolean;
  serverName: string;
  result?: string;
}>();

/**
 * 统一状态：
 * - 后端 'pending' 在流式期间表示"参数还在生成"，映射为 streaming；
 *   历史消息中的 pending 保持排队态。
 * - executing→running、failed→error、completed→completed 由归一化函数处理。
 */
const status = computed<ProcessStatus>(() => {
  const raw = props.tool.status || 'pending';
  if (raw === 'pending') return props.isStreaming ? 'streaming' : 'pending';
  return normalizeProcessStatus(raw);
});

const presentation = computed(() => getToolPresentation(props.tool, props.serverName));
const toolIcon = computed(() => ({ read: FileTextOutlined, write: EditOutlined, search: GlobalOutlined, command: CodeOutlined, browser: DesktopOutlined, mcp: ToolOutlined, tool: ToolOutlined })[presentation.value.kind]);
const verb = computed(() => {
  if (status.value === 'error') return '调用失败';
  if (status.value === 'denied') return '已取消';
  if (status.value === 'completed') return presentation.value.completed;
  if (status.value === 'pending') return '等待' + presentation.value.action;
  return '正在' + presentation.value.action;
});
const formattedResult = computed(() => formatToolArguments(props.result));

const parsedArguments = computed(() => formatToolArguments(props.tool.function?.arguments));
const argsStreaming = computed(() => isArgumentsStreaming(props.tool.function?.arguments, props.isStreaming));

const codeScrollTimers = new Map<HTMLElement, number>();
function onCodeScroll(event: Event) {
  const element = event.currentTarget as HTMLElement;
  window.clearTimeout(codeScrollTimers.get(element));
  element.classList.add('is-scrolling');
  codeScrollTimers.set(element, window.setTimeout(() => {
    element.classList.remove('is-scrolling');
    codeScrollTimers.delete(element);
  }, 600));
}

onBeforeUnmount(() => {
  codeScrollTimers.forEach(timer => window.clearTimeout(timer));
  codeScrollTimers.clear();
});

async function copyToolArgs() {
  const ok = await copyText(parsedArguments.value);
  if (ok) {
    NotificationService.success('参数已复制到剪贴板');
  } else {
    NotificationService.error('复制失败，请手动复制');
  }
}

async function copyToolResult() {
  if (!props.result) return;
  const ok = await copyText(props.result);
  if (ok) {
    NotificationService.success('结果已复制到剪贴板');
  } else {
    NotificationService.error('复制失败，请手动复制');
  }
}
</script>

<style scoped>
/* 行间距必须与 --pb-row-gap 一致：时间线上下线段按这个值首尾相接 */
.tci + .tci {
  margin-top: var(--pb-row-gap, 6px);
}

.tci-sec + .tci-sec {
  margin-top: 10px;
}

.tci-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 4px;
}

.tci-sec-label {
  font-size: var(--pb-detail-font, 12px);
  line-height: 18px;
  color: var(--pb-meta);
  font-weight: 500;
}

.tci-sec-label--error {
  color: var(--pb-c-error);
}

.tci-copy {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--pb-meta);
  cursor: pointer;
  opacity: 0;
  transition: opacity 160ms ease, color 160ms ease, background-color 160ms ease;
}

.tci-sec:hover .tci-copy {
  opacity: 1;
}

.tci-copy:hover {
  color: var(--pb-verb);
  background: rgba(127, 127, 127, 0.12);
}

.tci-error {
  margin-top: 8px;
  font-size: var(--pb-detail-font, 12px);
  line-height: 1.5;
  color: var(--pb-c-error);
  word-break: break-word;
}


.tci-icon { width: 18px; flex: none; font-size: 14px; color: var(--pb-verb); }
.tci + .tci { margin-top: 10px; }
.tci-sec { padding: 4px 0 8px; }
.tci-copy { opacity: .6; }
.tci-copy:focus-visible { opacity: 1; outline: 2px solid var(--pb-meta); }
.tci :deep(.pb-subject) { color: var(--pb-meta); }
.tci :deep(.pb-code) { max-height: 280px; overflow: auto; border-radius: 10px; padding: 12px 14px; }
.tci .pb-code {
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}
.tci .pb-code.is-scrolling { scrollbar-color: var(--pb-sb) transparent; }
.tci .pb-code::-webkit-scrollbar { width: 5px; height: 5px; }
.tci .pb-code::-webkit-scrollbar-track { background: transparent; }
.tci .pb-code::-webkit-scrollbar-thumb { background: transparent; border-radius: 3px; }
.tci .pb-code.is-scrolling::-webkit-scrollbar-thumb { background: var(--pb-sb); }
</style>
