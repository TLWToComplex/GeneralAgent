<template>
  <!-- 单个工具调用：不再套一层聚合块，否则同一件事要说两遍（两层 header + 两个 chevron） -->
  <div v-if="toolCalls.length === 1" class="trace" @click.stop>
    <OrchestrateToolCallItem
      :tool="toolCalls[0]"
      :is-streaming="!!message.isStreaming"
      :server-name="getServerDisplayName(toolCalls[0])"
      :result="toolResultsMap[toolCalls[0].id]"
    />
  </div>

  <ProcessBlock
    v-else-if="hasToolCalls"
    class="otcd"
    variant="ghost"
    :status="overallStatus"
    :verb="verb"
    :show-indicator="false"
    :shimmer="false"
    :max-height="0"
    :auto-follow="isCalling"
    @click.stop
    @toggle="onToggle"
  >
    <template #content>
      <div class="trace">
        <OrchestrateToolCallItem
          v-for="tool in visibleToolCalls"
          :key="tool.id"
          :tool="tool"
          :is-streaming="!!message.isStreaming"
          :server-name="getServerDisplayName(tool)"
          :result="toolResultsMap[tool.id]"
        />
      </div>
    </template>
  </ProcessBlock>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import type { Message, ToolCall } from '@/types/mcp.ts';
import ProcessBlock from './ProcessBlock.vue';
import OrchestrateToolCallItem from './OrchestrateToolCallItem.vue';
import { useChatStore } from '@/stores/chat-store.ts';
import { getToolPresentation, resolveToolServer } from '@/utils/toolPresentation';
import { getStatusMeta, type ProcessStatus } from '@/utils/processStatus';

const props = defineProps<{
  message: Message;
  toolCalls?: ToolCall[];
}>();

const chatStore = useChatStore();

const toolCalls = computed(() => props.toolCalls ?? props.message.tool_calls ?? []);

const hasToolCalls = computed(() => toolCalls.value.length > 0);

/* ---------------- 聚合状态 ---------------- */

const runningTool = computed(() => {
  return [...toolCalls.value].reverse().find(tool => {
    const status = tool.status || 'pending';
    return status === 'pending' || status === 'executing';
  });
});

const overallStatus = computed<ProcessStatus>(() => {
  const list = toolCalls.value;
  if (list.length === 0) return 'pending';
  if (list.some(t => t.status === 'failed')) return 'error';
  if (runningTool.value) {
    // 只有消息仍在流式输出时才呈现"进行中"；
    // 历史记录挂载时 isStreaming 即为 false，直接落到排队/完成态，避免卡在"正在调用"
    return props.message.isStreaming ? 'running' : 'pending';
  }
  return 'completed';
});

const isCalling = computed(() =>
  !!props.message.isStreaming && (overallStatus.value === 'running' || overallStatus.value === 'streaming')
);

// 聚合层只说"整体进度"，具体是哪个工具由下面的步骤行自己讲，避免父子重复
const verb = computed(() => {
  const counts = new Map<string, number>();
  for (const tool of toolCalls.value) {
    const info = getToolPresentation(tool, getServerDisplayName(tool));
    const label = info.kind === 'mcp' ? '调用' : info.action;
    const prefix = tool.status === 'completed' ? '已' : tool.status === 'failed' ? '未能' : props.message.isStreaming ? '正在' : '等待';
    const key = `${prefix}${label}|${info.unit}`;
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  const summary = [...counts].map(([key, count]) => {
    const [action, unit] = key.split('|');
    return `${action} ${count} ${unit}`;
  }).join('，');
  return overallStatus.value === 'error' ? `${summary} · 部分失败` : summary;
});

/* ---------------- 服务器名称 ---------------- */

const serverMap = ref<Record<string, any>>({});

onMounted(() => {
  try {
    const serverDataStr = localStorage.getItem('mcp-servers-data');
    if (serverDataStr) {
      const parsed = JSON.parse(serverDataStr);
      if (parsed && typeof parsed === 'object') serverMap.value = parsed;
    }
  } catch (e) {
    console.error('Failed to load server data', e);
  }
});

function getServerDisplayName(tool: ToolCall): string {
  return resolveToolServer(tool, serverMap.value);
}

/* ---------------- 工具结果 ---------------- */

// 计算所有相关工具的执行结果Map，避免在子组件中重复查询 Store
const toolResultsMap = computed(() => {
  const map: Record<string, string> = {};
  if (toolCalls.value.length === 0) return map;

  const toolIds = new Set(toolCalls.value.map(t => t.id));
  // 倒序查找，通常结果在后面
  for (let i = chatStore.messages.length - 1; i >= 0; i--) {
    const msg = chatStore.messages[i];
    if (msg.role === 'tool' && msg.tool_call_id && toolIds.has(msg.tool_call_id) && !(msg.tool_call_id in map)) {
      map[msg.tool_call_id] = msg.content;
      if (Object.keys(map).length === toolIds.size) break;
    }
  }
  return map;
});

/* ---------------- 渐进渲染（性能优化，保留原策略） ---------------- */

const renderLimit = ref(10);
const visibleToolCalls = computed(() => toolCalls.value.slice(0, renderLimit.value));

let rafId: number | null = null;

function grow() {
  const total = toolCalls.value.length;
  if (renderLimit.value >= total) {
    rafId = null;
    return;
  }
  const remaining = total - renderLimit.value;
  renderLimit.value += Math.max(5, Math.ceil(remaining / 5));
  rafId = requestAnimationFrame(grow);
}

function stopGrow() {
  if (rafId) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
}

function onToggle(expanded: boolean) {
  stopGrow();
  if (expanded) {
    grow();
  } else {
    // 折叠后等动画结束再收缩渲染数量，减轻下次展开的 DOM 压力
    setTimeout(() => {
      renderLimit.value = 10;
    }, 400);
  }
}

// 流式期间块默认自动展开（autoExpand），新工具到达时需要跟进渲染
watch(() => toolCalls.value.length, () => {
  if (getStatusMeta(overallStatus.value).autoExpand && !rafId) grow();
}, { immediate: true });

onMounted(() => {
  if (getStatusMeta(overallStatus.value).autoExpand) grow();
});

onUnmounted(stopGrow);
</script>

<style scoped>
/* 连接线从上一项底部接到下一项图标上沿，与详情竖线对齐且不重叠。 */
.trace {
  display: flex;
  flex-direction: column;
}

.otcd .trace > :deep(.tci + .tci) {
  margin-top: 10px;
}

.otcd .trace > :deep(.tci + .tci::before) {
  display: block;
  left: 8px;
  top: -10px;
  height: calc(10px + (var(--pb-header-h, 20px) - var(--pb-indicator-size, 18px)) / 2);
}


.otcd, .trace { margin: 12px 0; }
.otcd > :deep(.pb-collapsible > .pb-inner > .pb-viewport) { padding-left: 20px; }
.otcd .trace { margin: 6px 0; }
</style>
