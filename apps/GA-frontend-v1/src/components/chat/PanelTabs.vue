<template>
  <div class="panel-tabs" :class="{ 'is-deliverables': active === 'deliverables' }">
    <div class="panel-tabs-glider"></div>
    <button
      type="button"
      class="panel-tab"
      :class="{ active: active === 'canvas' }"
      @click="emit('switch', 'canvas')"
    >
      <svg class="tab-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="m9.06 11.9 8.07-8.06a2.85 2.85 0 1 1 4.03 4.03l-8.06 8.08"></path>
        <path d="M7.07 14.94c-1.66 0-3 1.35-3 3.02 0 1.33-2.5 1.52-2 2.02 1.08 1.1 2.49 2.02 4 2.02 2.2 0 4-1.8 4-4.04a3.01 3.01 0 0 0-3-3.02z"></path>
      </svg>
      <span class="tab-label">画布</span>
    </button>
    <button
      type="button"
      class="panel-tab"
      :class="{ active: active === 'deliverables' }"
      @click="emit('switch', 'deliverables')"
    >
      <svg class="tab-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path>
        <path d="M3.3 7 12 12l8.7-5"></path>
        <path d="M12 22V12"></path>
      </svg>
      <span class="tab-label">交付面板</span>
    </button>
  </div>
</template>

<script setup lang="ts">
defineOptions({
  name: 'PanelTabs'
});

defineProps<{
  active: 'canvas' | 'deliverables'
}>();

const emit = defineEmits<{
  (e: 'switch', mode: 'canvas' | 'deliverables'): void
}>();
</script>

<style scoped>
/* ===== 轨道：玻璃质感 ===== */
.panel-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  position: relative;
  isolation: isolate;
  flex-shrink: 0;
  padding: 4px;
  border-radius: 12px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(241, 245, 249, 0.82));
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.85),
    0 2px 10px rgba(15, 23, 42, 0.06);
  backdrop-filter: blur(6px);
}

/* ===== 滑块：白底 + 氛围光晕 + 流动极光高光 ===== */
.panel-tabs-glider {
  position: absolute;
  top: 4px;
  left: 4px;
  bottom: 4px;
  width: calc(50% - 4px);
  border-radius: 9px;
  background: #ffffff;
  box-shadow:
    0 0 0 1px rgba(59, 130, 246, 0.14),
    0 1px 2px rgba(15, 23, 42, 0.06),
    0 4px 12px rgba(59, 130, 246, 0.16);
  transition: transform 0.45s cubic-bezier(0.34, 1.3, 0.64, 1);
  will-change: transform;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
}

/* 缓慢流动的高光带，让滑块“呼吸”起来 */
.panel-tabs-glider::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(
    115deg,
    transparent 25%,
    rgba(96, 165, 250, 0.14) 50%,
    transparent 75%
  );
  background-size: 220% 100%;
  animation: glider-aurora 3.2s ease-in-out infinite alternate;
}

/* 顶部发丝高光，增强立体感 */
.panel-tabs-glider::after {
  content: '';
  position: absolute;
  top: 0;
  left: 10%;
  right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(147, 197, 253, 0.9), transparent);
}

@keyframes glider-aurora {
  from {
    background-position: 120% 0;
  }
  to {
    background-position: -20% 0;
  }
}

/* ===== Tab 按钮 ===== */
.panel-tab {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding: 7px 14px;
  border: none;
  background: transparent;
  border-radius: 9px;
  font-size: 13px;
  line-height: 1;
  letter-spacing: 0.2px;
  font-weight: 500;
  color: #64748b;
  cursor: pointer;
  white-space: nowrap;
  transition: color 0.25s ease, transform 0.15s ease;
}

.panel-tab:active {
  transform: scale(0.96);
}

.tab-icon {
  flex-shrink: 0;
  transition: transform 0.25s ease;
}

/* 未激活项 hover：文字提亮，图标轻轻上浮 */
.panel-tab:hover:not(.active) {
  color: #334155;
}

.panel-tab:hover:not(.active) .tab-icon {
  transform: translateY(-1px);
}

/* ===== 激活态 ===== */
.panel-tab.active {
  color: #2563eb;
  font-weight: 600;
}

/* 图标弹跳入场 */
.panel-tab.active .tab-icon {
  animation: icon-pop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@keyframes icon-pop {
  0% {
    transform: scale(0.6) rotate(-8deg);
  }
  60% {
    transform: scale(1.18) rotate(3deg);
  }
  100% {
    transform: scale(1) rotate(0deg);
  }
}

/* ===== 滑块位置：交付中心 ===== */
.panel-tabs.is-deliverables .panel-tabs-glider {
  transform: translateX(100%);
}

/* 无障碍：减少动态效果 */
@media (prefers-reduced-motion: reduce) {
  .panel-tabs-glider {
    transition: none;
  }

  .panel-tabs-glider::before,
  .panel-tab.active .tab-icon {
    animation: none;
  }

  .panel-tab,
  .tab-icon {
    transition: none;
  }
}
</style>
