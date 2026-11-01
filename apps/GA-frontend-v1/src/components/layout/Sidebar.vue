<template>
  <div class="sidebar-col" :class="{ 'sidebar-hidden': !visible }">
    <button
      v-if="visible || showToggleWhenHidden"
      type="button"
      class="sidebar-toggle-btn"
      :aria-label="visible ? 'Collapse sidebar' : 'Expand sidebar'"
      @click="emit('toggle')"
    >
      <svg class="sidebar-toggle-icon" viewBox="0 0 16 16" fill="none" aria-hidden="true">
        <path
          :d="visible ? 'M9.75 3.5L5.25 8L9.75 12.5' : 'M6.25 3.5L10.75 8L6.25 12.5'"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        />
      </svg>
    </button>
    <a-card class="left-sidebar" :bordered="false">
      <div class="sidebar-section server-container full-height">
        <div class="section-content" :class="{ 'content-visible': visible }">
          <slot></slot>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import {ref, watch} from 'vue';

interface Props {
  visible?: boolean;
  showToggleWhenHidden?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  visible: false,
  showToggleWhenHidden: false
});

const emit = defineEmits<{
  (e: 'toggle'): void
}>();

// 内部状态用于处理动画
const visible = ref(props.visible);

// 监听props变化
watch(() => props.visible, (newVal) => {
  visible.value = newVal;
});
</script>

<style scoped>
@import '../../assets//styles/chat-view.css';

.sidebar-toggle-btn {
  position: absolute;
  top: 50%;
  right: -12px;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 60px;
  border-radius: 10px;
  background:
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.24) 0%, rgba(59, 130, 246, 0) 42%),
    radial-gradient(circle at left bottom, rgba(124, 58, 237, 0.2) 0%, rgba(124, 58, 237, 0) 38%),
    linear-gradient(145deg, rgba(239, 243, 249, 0.98) 0%, rgba(227, 234, 244, 0.96) 48%, rgba(219, 227, 239, 0.98) 100%);
  border: none;
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.12),
    0 2px 8px rgba(255, 255, 255, 0.08);
  color: #475569;
  cursor: pointer;
  z-index: 12;
  transition: transform 0.28s ease, box-shadow 0.28s ease, filter 0.28s ease;
  backdrop-filter: blur(10px) saturate(1.1);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
}

.sidebar-toggle-btn:hover {
  transform: translateY(calc(-50% - 1px));
  box-shadow:
    0 11px 22px rgba(15, 23, 42, 0.16),
    0 4px 10px rgba(255, 255, 255, 0.1);
  filter: brightness(1.03);
}

.sidebar-toggle-icon {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
}
</style>
