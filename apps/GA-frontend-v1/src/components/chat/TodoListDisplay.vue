<template>
  <ProcessBlock
    v-if="todos && todos.length > 0"
    class="todo-block"
    variant="subtle"
    :status="blockStatus"
    :verb="blockVerb"
    :subject="currentTaskText"
    :count="`${completedCount}/${total}`"
    :max-height="260"
    :auto-follow="false"
  >
    <template #content>
      <!-- 进度条：与左色条同用状态色，完成即满格转绿 -->
      <div class="todo-progress">
        <div class="todo-progress-bar" :style="{ width: progressPercent + '%' }" />
      </div>

      <ul class="todo-items">
        <li
          v-for="(todo, index) in todos"
          :key="todo.id || index"
          class="todo-item"
          :class="`is-${normalizeTodoStatus(todo.status)}`"
          @click="handleTodoClick(todo)"
        >
          <StatusIndicator :status="normalizeTodoStatus(todo.status)" :size="14" class="todo-item-indicator" />
          <span class="todo-item-content">{{ todo.content }}</span>
        </li>
      </ul>
    </template>
  </ProcessBlock>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { TodoItem } from '@/types/mcp';
import ProcessBlock from './ProcessBlock.vue';
import StatusIndicator from './StatusIndicator.vue';
import { normalizeTodoStatus, type ProcessStatus } from '@/utils/processStatus';

const props = defineProps<{
  todos?: TodoItem[];
}>();

function handleTodoClick(todo: TodoItem) {
  window.dispatchEvent(new CustomEvent('open-todo-toolbar', {
    detail: { todo },
  }));
}

const list = computed(() => props.todos ?? []);
const total = computed(() => list.value.length);
const completedCount = computed(() => list.value.filter(t => t.status === 'completed').length);
const progressPercent = computed(() =>
  total.value === 0 ? 0 : Math.round((completedCount.value / total.value) * 100)
);

/** 整块状态：有任务在跑 → running；全部完成 → completed；否则 pending */
const blockStatus = computed<ProcessStatus>(() => {
  if (total.value === 0) return 'pending';
  if (list.value.some(t => t.status === 'in_progress')) return 'running';
  if (completedCount.value === total.value) return 'completed';
  return 'pending';
});

const blockVerb = computed(() => {
  if (blockStatus.value === 'running') return '正在执行';
  if (blockStatus.value === 'completed') return '已完成任务清单';
  return '任务清单';
});

/** 运行中把当前任务名放到 subject，与思考块「正在思考…」同一句式 */
const currentTaskText = computed(() => {
  if (blockStatus.value !== 'running') return '';
  return list.value.find(t => t.status === 'in_progress')?.content ?? '';
});
</script>

<style scoped>
.todo-block {
  margin: 10px 0;
}

/* ---- 进度条 ---- */

.todo-progress {
  height: 2px;
  border-radius: 1px;
  background: color-mix(in srgb, var(--pb-label) 18%, transparent);
  overflow: hidden;
}

.todo-progress-bar {
  height: 100%;
  border-radius: 1px;
  background: var(--pb-c-running);
  transition: width var(--pb-dur, 320ms) var(--pb-ease, cubic-bezier(0.22, 1, 0.36, 1)),
    background-color 260ms ease;
}

.todo-block.pb--completed .todo-progress-bar {
  background: var(--pb-c-done);
}

/* ---- 条目 ---- */

.todo-items {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 3px 6px;
  margin: 0 -6px;
  border-radius: 6px;
  font-size: var(--pb-detail-font, 12px);
  line-height: 20px;
  cursor: pointer;
  transition: background-color 180ms ease;
}

.todo-item:hover {
  background: color-mix(in srgb, var(--pb-label) 9%, transparent);
}

.todo-item-indicator {
  margin-top: 3px;
}

.todo-item-content {
  color: var(--pb-subject);
  word-break: break-word;
  transition: color 200ms ease, opacity 200ms ease;
}

.todo-item.is-running .todo-item-content {
  color: var(--pb-subject);
  font-weight: 500;
}

.todo-item.is-pending .todo-item-content {
  opacity: 0.72;
}

.todo-item.is-completed .todo-item-content {
  color: var(--pb-meta);
  text-decoration: line-through;
  text-decoration-thickness: 1px;
}
</style>
