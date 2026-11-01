<template>
  <component
    :is="collapsible ? 'button' : 'div'"
    class="thinking-state"
    :class="{ 'is-active': active, 'is-clickable': collapsible }"
    :type="collapsible ? 'button' : undefined"
    :aria-expanded="collapsible ? expanded : undefined"
    :aria-label="collapsible ? `${displayText}，${expanded ? '收起' : '展开'}思考过程` : undefined"
    :role="collapsible ? undefined : 'status'"
    @click="collapsible && emit('toggle')"
  >
    <span v-if="active" class="thinking-orb" aria-hidden="true">
      <span class="thinking-orb-globe">
        <span v-for="dot in orbDots" :key="dot.key" class="thinking-orb-dot" :style="dot.style" />
      </span>
    </span>
    <BulbOutlined v-else class="thinking-state-icon" aria-hidden="true" />
    <span class="thinking-state-label" :class="{ 'pb-shimmer': active }">{{ displayText }}</span>
    <span v-if="!active && duration" class="thinking-state-duration">{{ duration }}</span>
    <RightOutlined v-if="collapsible" class="thinking-state-chevron" :class="{ 'is-expanded': expanded }" aria-hidden="true" />
  </component>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { BulbOutlined, RightOutlined } from '@ant-design/icons-vue';
import { orbDots } from './orbGeometry';

const props = withDefaults(defineProps<{
  active: boolean;
  expanded?: boolean;
  duration?: string;
  collapsible?: boolean;
  /** 自定义文案：传入后覆盖默认的「正在思考 / 已思考 / 思考过程」 */
  label?: string;
}>(), { expanded: false, duration: '', collapsible: true, label: '' });
const emit = defineEmits<{ (event: 'toggle'): void }>();
const displayText = computed(() => props.label || (props.active ? '正在思考' : props.duration ? '已思考' : '思考过程'));
</script>

<style scoped>
.thinking-state {
  display: inline-flex;
  align-items: center;
  align-self: flex-start;
  gap: 6px;
  max-width: 100%;
  min-height: 26px;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: var(--pb-verb, #6d6d6d);
  font-family: inherit;
  font-size: 13px;
  font-weight: 400;
  line-height: 18px;
  text-align: left;
}
.thinking-state.is-clickable { cursor: pointer; }
.thinking-state:focus-visible { outline: 2px solid var(--pb-meta); outline-offset: 4px; }
.thinking-state-icon { flex: none; width: 18px; font-size: 14px; }
.thinking-state-label { white-space: nowrap; }
.thinking-state-duration { color: var(--pb-meta); font-size: 12px; font-variant-numeric: tabular-nums; }
.thinking-state-chevron { flex: none; font-size: 10px; color: var(--pb-meta); transition: transform 220ms ease; }
.thinking-state-chevron.is-expanded { transform: rotate(90deg); }
.thinking-state.is-clickable:hover .thinking-state-chevron { color: var(--pb-verb); }
/* ---- Orbs（aicss.dev）G1 地球自转：思考中的活动指示器 ----
   几何按 28px 舞台绘制，但地球本体只占舞台中央 19px（四周留白多），
   所以 --orb-k 不再按「显示框 / 舞台」折算，而是直接按地球直径折算到
   18px 显示框（与 13px 文案、12px 箭头同一视觉量级），点径和纬度环
   密度的相对比例仍保持原版。 */
.thinking-orb {
  position: relative;
  display: block;
  flex: none;
  width: 18px;
  height: 18px;
  overflow: hidden;
  contain: strict;
  color: var(--tre-verb, #6d6d6d);
}

.thinking-orb-globe {
  /* 地球半径 8.5 + 点半径 1 = 9.5，×0.9 = 8.55 < 半框 9，不会裁到点 */
  --orb-k: 0.9;
  position: absolute;
  inset: 0;
  transform: scale(var(--orb-k));
}

.thinking-orb-dot {
  position: absolute;
  left: 50%;
  top: 50%;
  width: 2px;
  height: 2px;
  margin: -1px 0 0 -1px;
  border-radius: 50%;
  background: currentColor;
  /* 姿势 0 作为静态兜底：reduced-motion 关掉动画后依然是一颗完整的地球 */
  transform: translate(var(--g0x), var(--g0y));
  opacity: var(--g0o);
  will-change: transform, opacity;
  animation: thinking-globe-spin 4.5s linear infinite both;
}

/* 8 个预计算姿势（脚本里算好写进 --g0…--g7 变量）：
   每 12.5% 均匀步进一格，末帧与姿势 0 重合，循环点无缝。 */
@keyframes thinking-globe-spin {
  0%,
  100% {
    transform: translate(var(--g0x), var(--g0y));
    opacity: var(--g0o);
  }

  12.5% {
    transform: translate(var(--g1x), var(--g1y));
    opacity: var(--g1o);
  }

  25% {
    transform: translate(var(--g2x), var(--g2y));
    opacity: var(--g2o);
  }

  37.5% {
    transform: translate(var(--g3x), var(--g3y));
    opacity: var(--g3o);
  }

  50% {
    transform: translate(var(--g4x), var(--g4y));
    opacity: var(--g4o);
  }

  62.5% {
    transform: translate(var(--g5x), var(--g5y));
    opacity: var(--g5o);
  }

  75% {
    transform: translate(var(--g6x), var(--g6y));
    opacity: var(--g6o);
  }

  87.5% {
    transform: translate(var(--g7x), var(--g7y));
    opacity: var(--g7o);
  }
}

@media (prefers-reduced-motion: reduce) {
  .thinking-orb-dot {
    animation: none !important;
  }
}


@media (prefers-reduced-motion: reduce) {
  .thinking-state-chevron { transition: none; }
}
</style>
