<template>
  <div class="history-conversation-loading" role="status" aria-live="polite">
    <div v-if="showIndicator" class="history-loading-content" :style="contentStyle">
      <img :src="loadingAnimation" alt="" class="loading-animation" />
      <span>正在加载对话</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';
import loadingAnimation from '@/assets/image/svg/history-loading-agent.svg';
defineProps<{ contentStyle?: Record<string, string> }>();

const showIndicator = ref(false);
let indicatorTimer: ReturnType<typeof setTimeout> | undefined;
onMounted(() => {
  indicatorTimer = setTimeout(() => {
    showIndicator.value = true;
  }, 2000);
});
onBeforeUnmount(() => {
  clearTimeout(indicatorTimer);
});
</script>

<style scoped>
.history-conversation-loading {
  position: absolute;
  inset: 0;
  z-index: 12;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  background: transparent;
  color: #737db8;
  font-size: 13px;
  font-weight: 500;
  pointer-events: none;
}
.loading-animation {
  width: 48px;
  height: 48px;
  /* HTML 元素的 transform 可独立合成，避免仅依赖 SVG 内部动画重绘。 */
  will-change: transform;
  animation: loading-float 1.4s ease-in-out infinite;
}
@keyframes loading-float {
  0%, 100% { transform: translateY(2px) rotate(-4deg); }
  50% { transform: translateY(-2px) rotate(4deg); }
}
.history-loading-content {
  display: flex;
  align-items: center;
  gap: 8px;
  transform: translateY(var(--history-loading-shift, 0px));
  transition: transform 200ms ease;
  animation: loading-fade-in 160ms ease-out;
}
@keyframes loading-fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
@media (prefers-reduced-motion: reduce) {
  .history-loading-content { transition: none; animation: none; }
  .loading-animation { animation: none; will-change: auto; }
}
</style>


