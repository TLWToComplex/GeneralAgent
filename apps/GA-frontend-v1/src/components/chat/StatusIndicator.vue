<template>
  <span class="si" :class="`si--${status}`" :style="siStyle" aria-hidden="true">
    <svg class="si-glyph" viewBox="0 0 16 16" fill="none">
      <!-- 进行中：细环 spinner。光球只保留给思考块，执行区不再出现多球同屏 -->
      <template v-if="meta.indicator === 'spinner'">
        <circle
          cx="8" cy="8" r="5.6"
          stroke="currentColor" stroke-opacity="0.2" stroke-width="1.6"
        />
        <circle
          class="si-arc"
          cx="8" cy="8" r="5.6"
          stroke="currentColor" stroke-width="1.6" stroke-linecap="round"
          stroke-dasharray="8.8 26.4"
        />
      </template>
      <path
        v-else-if="meta.indicator === 'check'"
        d="M13.2 4.4 6.4 11.2 2.8 7.6"
        stroke="currentColor" stroke-width="1.8"
        stroke-linecap="round" stroke-linejoin="round"
      />
      <path
        v-else-if="meta.indicator === 'cross'"
        d="M4.2 4.2l7.6 7.6M11.8 4.2l-7.6 7.6"
        stroke="currentColor" stroke-width="1.8" stroke-linecap="round"
      />
      <template v-else-if="meta.indicator === 'shield'">
        <path
          d="M8 1.8 12.8 3.6v3.9c0 2.9-1.9 5.3-4.8 6.7-2.9-1.4-4.8-3.8-4.8-6.7V3.6z"
          stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"
        />
        <path d="M8 5.4v3" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
        <circle cx="8" cy="10.6" r="0.85" fill="currentColor" />
      </template>
      <template v-else-if="meta.indicator === 'ban'">
        <circle cx="8" cy="8" r="5.9" stroke="currentColor" stroke-width="1.5" />
        <path d="M3.9 12.1 12.1 3.9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" />
      </template>
      <circle
        v-else
        cx="8" cy="8" r="3" stroke="currentColor" stroke-width="1.5"
      />
    </svg>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { getStatusMeta, type ProcessStatus } from '@/utils/processStatus';

const props = withDefaults(defineProps<{
  status: ProcessStatus;
  /** 显示尺寸（px），图标按 0.78 比例随尺寸缩放 */
  size?: number;
}>(), {
  status: 'pending',
  size: 18,
});

const meta = computed(() => getStatusMeta(props.status));
const siStyle = computed(() => ({
  '--si-size': `${props.size}px`,
}));
</script>

<style scoped>
.si {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: none;
  width: var(--si-size, 18px);
  height: var(--si-size, 18px);
}

.si-glyph {
  display: block;
  width: calc(var(--si-size, 18px) * 0.78);
  height: calc(var(--si-size, 18px) * 0.78);
  transition: color 220ms ease;
}

/* ---- 状态着色：与 process-block.css 的 --pb-c-* 对齐 ---- */
.si--pending           { color: var(--pb-c-idle); }
.si--streaming,
.si--running           { color: var(--pb-verb); }
.si--awaiting-approval { color: var(--pb-c-warn); }
.si--completed         { color: var(--pb-c-done); }
.si--error             { color: var(--pb-c-error); }
.si--denied            { color: var(--pb-meta); }

/* ---- 细环旋转：只有圆弧在动，视觉重量远小于光球 ---- */
.si-arc {
  transform-origin: center;
  transform-box: view-box;
  animation: si-spin 0.9s linear infinite;
}

@keyframes si-spin {
  to { transform: rotate(360deg); }
}

@media (prefers-reduced-motion: reduce) {
  .si-arc {
    animation: none !important;
  }
}
</style>
