<template>
  <div class="pb" :class="[`pb--${variant}`, `pb--${status}`]">
    <!-- 头部：与 .tr-header 同一套排版（13px/18px、gap 6、min-height 20） -->
    <component
      :is="collapsible ? 'button' : 'div'"
      class="pb-header"
      :class="{ 'is-clickable': collapsible }"
      :type="collapsible ? 'button' : undefined"
      :aria-expanded="collapsible ? isExpanded : undefined"
      @click="collapsible && toggle()"
    >
      <slot name="indicator"><StatusIndicator v-if="showIndicator" :status="status" class="pb-indicator" /></slot>

      <span class="pb-label">
        <span v-if="verb" class="pb-verb" :class="{ 'pb-shimmer': shimmer && meta.shimmer }">{{ verb }}</span>
        <span v-if="subject" class="pb-subject" :title="subject">{{ subject }}</span>
        <span v-if="metaText" class="pb-meta">{{ metaText }}</span>
      </span>

      <slot name="header-extra" />

      <!-- 耗时右对齐 + 等宽数字：多行之间形成一条可扫读的时间轴 -->
      <span v-if="durationText" class="pb-duration">{{ durationText }}</span>

      <span v-if="count !== undefined && count !== null && count !== ''" class="pb-count">
        {{ count }}
      </span>

      <svg
        v-if="collapsible"
        class="pb-chevron" viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"
      >
        <path
          d="m4.5 15.75 7.5-7.5 7.5 7.5" fill="none" stroke="currentColor"
          stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"
        />
      </svg>
    </component>

    <!-- 折叠区：统一 grid-template-rows 0fr/1fr，替代各处 max-height hack -->
    <div v-if="collapsible" class="pb-collapsible" :class="{ 'is-collapsed': !isExpanded }" :inert="!isExpanded">
      <div class="pb-inner">
        <div
          ref="viewportEl"
          class="pb-viewport"
          :class="{ 'is-scroll': isExpanded && overflow, 'hide-scrollbar': !scrollbarVisible }"
          :style="viewportStyle"
          @scroll="onScroll"
          @wheel.passive="markUserScroll"
          @touchstart.passive="markUserScroll"
        >
          <!-- 折叠即卸载：只有展开时才渲染内容，收起动画跑完后整棵子树移出组件树 -->
          <div v-if="renderContent" ref="contentEl" class="pb-content">
            <slot name="content" />
          </div>
        </div>
      </div>
    </div>

    <!-- 非折叠（审批等常驻展开）直接渲染 -->
    <div v-else class="pb-static">
      <slot name="content" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import StatusIndicator from './StatusIndicator.vue';
import { isNestedScrollTarget } from '@/utils/scrollTarget';
import { formatDuration, getStatusMeta, type ProcessStatus } from '@/utils/processStatus';

const props = withDefaults(defineProps<{
  /** 统一状态，决定指示器图形、扫光与默认展开策略 */
  status: ProcessStatus;
  /** 动词，如「已思考」「正在调用」「任务清单」 */
  verb?: string;
  /** 主体，如工具名、当前执行的任务 */
  subject?: string;
  /** 弱化元信息，如「mcp-github」 */
  meta?: string;
  /** 耗时：数字走 formatDuration，字符串原样显示，右对齐 */
  duration?: number | string | null;
  /** 右侧计数，如「5」「2/5」 */
  count?: string | number | null;
  /** ghost=思考(无容器) / row=时间线步骤行 / subtle=清单(细边) / alert=审批(琥珀块) */
  variant?: 'ghost' | 'row' | 'subtle' | 'alert';
  /** 是否可折叠；审批卡为 false */
  collapsible?: boolean;
  /** 受控展开态；传 null/undefined 走内部策略 */
  expanded?: boolean | null;
  /** 非受控初值；传 null 则由状态机 autoExpand 决定 */
  defaultExpanded?: boolean | null;
  /** 详情区最大高度，超出后内部滚动 + 渐隐 */
  maxHeight?: number;
  /** 流式内容是否自动跟随到底部 */
  autoFollow?: boolean;
  showIndicator?: boolean;
  autoExpand?: boolean;
  shimmer?: boolean;
}>(), {
  verb: '',
  subject: '',
  meta: '',
  duration: null,
  count: null,
  variant: 'ghost',
  collapsible: true,
  expanded: null,
  defaultExpanded: null,
  maxHeight: 180,
  autoFollow: true,
  showIndicator: true,
  autoExpand: true,
  shimmer: true,
});

const emit = defineEmits<{
  (e: 'update:expanded', value: boolean): void;
  (e: 'toggle', value: boolean): void;
}>();

const meta = computed(() => getStatusMeta(props.status));
const metaText = computed(() => props.meta || '');
const durationText = computed(() => {
  const d = props.duration;
  if (d === null || d === undefined || d === '') return '';
  return typeof d === 'number' ? formatDuration(d) : d;
});

/* ---------------- 展开状态 ---------------- */

const userToggled = ref(false);

function resolveInitial(): boolean {
  if (props.defaultExpanded !== null && props.defaultExpanded !== undefined) {
    return props.defaultExpanded;
  }
  return props.autoExpand ? getStatusMeta(props.status).autoExpand : props.status === 'error';
}

const innerExpanded = ref(resolveInitial());

const isExpanded = computed(() =>
  props.expanded === null || props.expanded === undefined
    ? innerExpanded.value
    : props.expanded
);

function toggle() {
  const next = !isExpanded.value;
  userToggled.value = true;
  // 受控模式下由父组件回写，非受控模式自己更新
  if (props.expanded === null || props.expanded === undefined) {
    innerExpanded.value = next;
  }
  emit('update:expanded', next);
  emit('toggle', next);
}

// 状态推进时按策略自动展开/折叠（用户手动操作过则不再干预）
watch(() => props.status, (next) => {
  if (userToggled.value) return;
  if (props.expanded !== null && props.expanded !== undefined) return;
  innerExpanded.value = props.autoExpand ? getStatusMeta(next).autoExpand : next === 'error';
});

/* ---------------- 折叠即卸载 ---------------- */

/**
 * 收起动画时长为 --pb-dur(320ms)，等它跑完再卸载，避免内容在动画中途消失。
 * 期间容器已被 grid-template-rows: 0fr 压到 0 高度，视觉上没有变化。
 */
const PB_UNMOUNT_DELAY = 360;

/** 详情区内容是否挂载在组件树上；不可折叠的块（审批卡）恒定渲染 */
const renderContent = ref(!props.collapsible || isExpanded.value);
let unmountTimer: number | null = null;

watch(isExpanded, (expanded) => {
  if (unmountTimer) {
    window.clearTimeout(unmountTimer);
    unmountTimer = null;
  }
  if (expanded) {
    renderContent.value = true;
    return;
  }
  unmountTimer = window.setTimeout(() => {
    unmountTimer = null;
    renderContent.value = false;
  }, PB_UNMOUNT_DELAY);
});

/* ---------------- 详情区视口：限高 + 渐隐 + 自动跟随 ---------------- */

const viewportEl = ref<HTMLElement | null>(null);
const contentEl = ref<HTMLElement | null>(null);
const overflow = ref(false);
const fadeTop = ref(false);
const fadeBottom = ref(false);
const scrollbarVisible = ref(false);
const pinnedToBottom = ref(true);

let observer: ResizeObserver | null = null;
let scrollbarTimer: number | null = null;

const FADE = 16;

const viewportStyle = computed(() => {
  if (!isExpanded.value) return {};
  const style: Record<string, string> = {
    maxHeight: props.maxHeight > 0 ? `${props.maxHeight}px` : 'none',
  };
  if (overflow.value) {
    const top = fadeTop.value ? `linear-gradient(to bottom, transparent 0, #000 ${FADE}px, #000 calc(100% - ${FADE}px), transparent 100%)` : undefined;
    const mask = fadeTop.value && fadeBottom.value
      ? top
      : fadeTop.value
        ? `linear-gradient(to bottom, transparent 0, #000 ${FADE}px)`
        : fadeBottom.value
          ? `linear-gradient(to bottom, #000 calc(100% - ${FADE}px), transparent 100%)`
          : undefined;
    if (mask) {
      style.maskImage = mask;
      style.WebkitMaskImage = mask;
    }
  }
  return style;
});

function measure() {
  const vp = viewportEl.value;
  if (!vp) return;
  overflow.value = vp.scrollHeight > vp.clientHeight + 1;
  updateFade();
  if (props.autoFollow && pinnedToBottom.value && overflow.value) {
    vp.scrollTop = vp.scrollHeight;
  }
}

function updateFade() {
  const vp = viewportEl.value;
  if (!vp || !overflow.value) {
    fadeTop.value = false;
    fadeBottom.value = false;
    return;
  }
  fadeTop.value = vp.scrollTop > 4;
  fadeBottom.value = vp.scrollTop + vp.clientHeight < vp.scrollHeight - 4;
}

function onScroll(event: Event) {
  const vp = viewportEl.value;
  if (!vp || event.target !== vp) return;
  updateFade();
  pinnedToBottom.value = vp.scrollTop + vp.clientHeight >= vp.scrollHeight - 8;
  scrollbarVisible.value = true;
  if (scrollbarTimer) window.clearTimeout(scrollbarTimer);
  scrollbarTimer = window.setTimeout(() => { scrollbarVisible.value = false; }, 600);
}

/** 用户主动滚动即放弃自动跟随，避免和用户抢滚动条 */
function markUserScroll(event: Event) {
  if (!viewportEl.value || isNestedScrollTarget(event, viewportEl.value)) return;
  pinnedToBottom.value = false;
}

onMounted(() => {
  nextTick(measure);
  if (typeof ResizeObserver === 'undefined') return;
  // 观察器必须先建好：初始即折叠时 contentEl 还不存在，展开后才能挂上目标
  observer = new ResizeObserver(() => measure());
  if (contentEl.value) observer.observe(contentEl.value);
});

// 内容随折叠被卸载、展开时重建，观察目标必须跟着换，否则展开后高度不再更新
watch(contentEl, (el, prevEl) => {
  if (!observer) return;
  if (prevEl && prevEl !== el) observer.unobserve(prevEl);
  if (!el) return;
  observer.observe(el);
  nextTick(measure);
}, { flush: 'post' });

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
  if (scrollbarTimer) window.clearTimeout(scrollbarTimer);
  if (unmountTimer) window.clearTimeout(unmountTimer);
  unmountTimer = null;
});

watch(isExpanded, (v) => {
  if (v) nextTick(measure);
});
</script>

<style scoped>
.pb {
  display: flex;
  flex-direction: column;
  width: 100%;
  font-family: "Inter", system-ui, -apple-system, sans-serif;
  animation: pb-in var(--pb-dur, 320ms) var(--pb-ease, cubic-bezier(0.22, 1, 0.36, 1)) both;
}

@keyframes pb-in {
  from { opacity: 0; }
  to   { opacity: 1; }
}

/* ---------------- header ---------------- */

.pb-header {
  display: inline-flex;
  align-items: center;
  gap: var(--pb-gap, 6px);
  align-self: flex-start;
  max-width: 100%;
  min-height: 20px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: default;
  font-family: inherit;
  text-align: left;
}

.pb-header.is-clickable {
  cursor: pointer;
}

.pb-indicator {
  flex: none;
}

.pb-label {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  min-width: 0;
  font-size: var(--pb-font, 13px);
  line-height: var(--pb-line, 18px);
  font-weight: var(--pb-weight, 500);
  letter-spacing: var(--pb-tracking, -0.005em);
  color: var(--pb-label);
}

.pb-verb {
  color: var(--pb-verb);
  flex: none;
}

.pb-subject {
  color: var(--pb-subject);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pb-meta {
  color: var(--pb-meta);
  font-weight: 400;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.pb-meta::before {
  content: '·';
  margin-right: 4px;
  opacity: 0.6;
}

.pb-duration {
  flex: none;
  margin-left: auto;
  padding-left: 12px;
  font-size: var(--pb-detail-font, 12px);
  line-height: var(--pb-line, 18px);
  color: var(--pb-meta);
  font-variant-numeric: tabular-nums;
  font-feature-settings: "tnum" 1;
}

.pb-count {
  flex: none;
  margin-left: 2px;
  font-size: var(--pb-detail-font, 12px);
  line-height: var(--pb-line, 18px);
  color: var(--pb-count);
  font-variant-numeric: tabular-nums;
}

.pb-chevron {
  flex: none;
  color: var(--pb-label);
  transform: rotate(90deg);
  transition: transform var(--pb-chevron-dur, 280ms) var(--pb-ease, cubic-bezier(0.22, 1, 0.36, 1));
}

.pb-header[aria-expanded="true"] .pb-chevron {
  transform: rotate(180deg);
}

.pb-header.is-clickable:hover .pb-chevron {
  color: var(--pb-meta);
}

/* ---------------- 折叠动画 ---------------- */

.pb-collapsible {
  display: grid;
  grid-template-rows: 1fr;
  opacity: 1;
  transition:
    grid-template-rows var(--pb-dur, 320ms) var(--pb-ease, cubic-bezier(0.22, 1, 0.36, 1)),
    opacity 220ms ease;
}

.pb-collapsible.is-collapsed {
  grid-template-rows: 0fr;
  opacity: 0;
  pointer-events: none;
}

.pb-inner {
  min-height: 0;
  overflow: hidden;
}

/* ---------------- 详情区 ---------------- */

.pb-viewport {
  margin-top: 6px;
  padding-left: var(--pb-indent, 24px);
  overflow: hidden;
}

.pb-viewport.is-scroll {
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: transparent transparent;
}

.pb-viewport.is-scroll::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.pb-viewport.is-scroll::-webkit-scrollbar-track {
  background-color: transparent;
}

.pb-viewport.is-scroll::-webkit-scrollbar-thumb {
  background-color: var(--pb-sb);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.pb-viewport.is-scroll::-webkit-scrollbar-thumb:active {
  background-color: var(--pb-sb-active);
}

.pb-viewport.is-scroll:not(.hide-scrollbar) {
  scrollbar-color: var(--pb-sb) transparent;
}

.pb-viewport.is-scroll.hide-scrollbar::-webkit-scrollbar-thumb {
  background-color: transparent;
}

.pb-static {
  margin-top: 8px;
  padding-left: var(--pb-indent, 24px);
}

.pb-content {
  font-size: var(--pb-detail-font, 12px);
  color: var(--pb-label);
}

/* ---------------- variant: row（时间线步骤行）---------------- */

/* 一行一步骤：状态图标落在轨道上，上下各画一段 1px 细线把整列串起来。
   线段避开图标盒子（上下各留 (header-h - indicator) / 2 的空档），
   所以不需要用背景色去遮罩轨道，换主题/换底色都不会穿帮。 */
.pb--row {
  position: relative;
}

.pb--row::before,
.pb--row::after {
  content: '';
  position: absolute;
  left: calc(var(--pb-indicator-size, 18px) / 2 - 0.5px);
  width: 1px;
  background: var(--pb-rail);
  pointer-events: none;
}

/* 上段：接住上一行，停在图标上沿 */
.pb--row::before {
  top: calc(-1 * var(--pb-row-gap, 6px));
  height: calc(
    var(--pb-row-gap, 6px) +
    (var(--pb-header-h, 20px) - var(--pb-indicator-size, 18px)) / 2
  );
}

/* 下段：从图标下沿画到行底（含展开的详情区），再接到下一行 */
.pb--row::after {
  top: calc((var(--pb-header-h, 20px) + var(--pb-indicator-size, 18px)) / 2);
  bottom: calc(-1 * var(--pb-row-gap, 6px));
}

.pb--row .pb-header {
  align-self: stretch;
  width: 100%;
  min-height: var(--pb-header-h, 20px);
}

.pb--row .pb-header.is-clickable:hover .pb-subject {
  color: var(--pb-row-hover);
}

/* ---------------- variant: subtle（任务清单）---------------- */

/* 中性细边，只用来把"清单"与正文分开，不再承担状态着色
   （状态由图标与文字表达，一处信息只说一次） */
.pb--subtle {
  border-left: 1px solid var(--pb-rail);
  padding-left: 9px;
  margin-left: -10px;
}

/* ---------------- variant: alert（审批）---------------- */

.pb--alert {
  border-left: 4px solid var(--pb-c-warn);
  border-radius: 0 var(--pb-radius, 8px) var(--pb-radius, 8px) 0;
  background: color-mix(in srgb, var(--pb-c-warn) 5%, transparent);
  padding: 10px 12px;
}

.pb--alert .pb-verb {
  color: var(--pb-c-warn);
  font-weight: 600;
}

.pb--alert .pb-static {
  padding-left: 0;
}

/* ---------------- 状态强调 ---------------- */

/* 完成 / 拒绝不再整体降透明度：状态由图标与文案表达，
   文字虚化只会让已完成的内容看起来像渲染坏了 */
.pb--error .pb-subject {
  color: var(--pb-c-error);
}


.pb-header { min-height: 26px; border-radius: 4px; }
.pb-header:focus-visible { outline: 2px solid var(--pb-meta); outline-offset: 3px; }
.pb--row .pb-header { align-self: flex-start; width: auto; max-width: 100%; }
.pb-duration { margin-left: 2px; padding-left: 4px; }
/* 轨道放在滚动视口外：内容的 mask 渐隐不能把竖线一起擦掉。 */
.pb--row > .pb-collapsible > .pb-inner { position: relative; }
.pb--row > .pb-collapsible > .pb-inner::before {
  content: '';
  position: absolute;
  left: 8px;
  top: 6px;
  bottom: 0;
  width: 1px;
  background: var(--pb-rail);
  pointer-events: none;
}
.pb--row .pb-viewport { margin-left: 8px; padding-left: 17px; }
.pb--row::before, .pb--row::after { display: none; }
@media (prefers-reduced-motion: reduce) {
  .pb, .pb-collapsible, .pb-chevron { animation: none; transition: none; }
}
</style>
