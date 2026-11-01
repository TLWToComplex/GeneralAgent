<template>
  <a-modal v-model:open="modalOpen" centered :width="560" :footer="null" :closable="false"
    wrap-class-name="agent-picker-modal" transition-name="agent-picker-zoom" mask-transition-name="agent-picker-fade"
    :mask-style="{ backgroundColor: 'rgba(255, 255, 255, 0.45)', backdropFilter: 'blur(6px)' }">
    <header class="agent-picker-header">
      <h2>新任务</h2>
      <button class="agent-picker-close" aria-label="关闭" @click="closeModal">
        <CloseOutlined />
      </button>
      <p>选择一个智能体开始对话。已有的会话将直接打开。</p>
    </header>
    <label class="agent-picker-search">
      <SearchOutlined /><input v-model="query" placeholder="搜索智能体..." aria-label="搜索智能体" />
    </label>
    <div class="agent-picker-tabs" role="tablist">
      <span class="agent-picker-thumb" :class="{ 'is-shared': pickerTab === 'shared' }"
        aria-hidden="true"></span>
      <button v-for="tab in pickerTabs" :key="tab.key" type="button" role="tab" class="agent-picker-tab"
        :class="{ active: pickerTab === tab.key }" :aria-selected="pickerTab === tab.key"
        @click="selectPickerTab(tab.key)">
        {{ tab.title }}<span class="agent-picker-tab-count">{{ tab.count }}</span>
      </button>
    </div>
    <div class="agent-picker-list">
      <button v-for="agent in pickerAgents" :key="agent.id" class="agent-picker-item" @click="selectAgent(agent)">
        <a-avatar :size="40" :src="agentAvatar(agent)"
          :style="{ backgroundColor: agentAvatar(agent) ? 'transparent' : (agent.config?.basic?.themeColor || '#b9dba0') }">{{ agent.name?.charAt(0)
          }}</a-avatar>
        <span class="agent-picker-details">
          <span class="agent-picker-name">{{ agent.name }}</span>
          <span class="agent-picker-description">{{ agent.description || agent.config?.basic?.description || '暂无描述'
          }}</span>
        </span>
      </button>
      <p v-if="!pickerAgents.length" class="agent-picker-empty">{{ pickerEmptyText }}</p>
    </div>
    <button class="agent-picker-footer" @click="browseAll">查看全部智能体
      <RightOutlined />
    </button>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { Avatar as AAvatar, Modal as AModal } from 'ant-design-vue';
import { CloseOutlined, SearchOutlined, RightOutlined } from '@ant-design/icons-vue';
import StorageService from '@/utils/StorageService';
import { resolveAgentAvatar } from '@/utils/agentAvatar';

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void;
  (event: 'select-agent', agent: any): void;
  (event: 'browse-agents'): void;
}>();

const modalOpen = computed({
  get: () => props.open,
  set: (value: boolean) => emit('update:open', value)
});

const query = ref('');
const agents = ref<ReturnType<typeof StorageService.getAgents>>([]);
const loadAgents = () => { agents.value = StorageService.getAgents(); };
// 渲染层统一解析头像：兼容 localStorage 中的稳定 key / dev 路径 / 旧打包路径
const agentAvatar = (agent: any) => resolveAgentAvatar(agent?.config?.basic?.avatar);
const filteredAgents = computed(() => {
  const term = query.value.trim().toLowerCase();
  return agents.value.filter(agent => `${agent.name || ''} ${agent.description || agent.config?.basic?.description || ''}`.toLowerCase().includes(term));
});
// visibility 取值 'private' | 'public'，private 为个人智能体，其余归入共享
const isSharedAgent = (agent: any) => (agent?.visibility || agent?.config?.basic?.visibility) !== 'private';
const pickerTab = ref<'mine' | 'shared'>('mine');
const selectPickerTab = (tab: 'mine' | 'shared') => {
  if (tab === pickerTab.value) return;
  pickerTab.value = tab;
};
const mineAgents = computed(() => filteredAgents.value.filter(agent => !isSharedAgent(agent)));
const sharedAgents = computed(() => filteredAgents.value.filter(isSharedAgent));
const pickerTabs = computed(() => [
  { key: 'mine' as const, title: '个人智能体', count: mineAgents.value.length },
  { key: 'shared' as const, title: '共享智能体', count: sharedAgents.value.length }
]);
const pickerAgents = computed(() => pickerTab.value === 'shared' ? sharedAgents.value : mineAgents.value);
const pickerEmptyText = computed(() => {
  if (!agents.value.length) return '暂无可用智能体';
  if (!filteredAgents.value.length) return '未找到匹配的智能体';
  return '该分类下暂无智能体';
});

const resetOnOpen = () => { loadAgents(); query.value = ''; pickerTab.value = 'mine'; };
watch(() => props.open, (val) => { if (val) resetOnOpen(); });

const closeModal = () => { modalOpen.value = false; };
const selectAgent = (agent: any) => { modalOpen.value = false; emit('select-agent', agent); };
const browseAll = () => { modalOpen.value = false; emit('browse-agents'); };

onMounted(() => {
  loadAgents();
  window.addEventListener('agents-updated', loadAgents);
});

onUnmounted(() => {
  window.removeEventListener('agents-updated', loadAgents);
});
</script>

<style>
.agent-picker-modal .ant-modal-content {
  position: relative;
  font-family: Arial, "Microsoft YaHei", sans-serif;
  padding: 0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 24px 48px rgba(0, 0, 0, .18);
  background: #f6f7fa;
}

/* 背景图层：整图铺满（不能用 cover，弹窗偏竖会裁掉两侧浅色边缘导致颜色偏深）；
   加模糊制造磨砂玻璃感；向外扩展一圈避免模糊后边缘透底 */
.agent-picker-modal .ant-modal-content::before {
  content: '';
  position: absolute;
  inset: -32px;
  z-index: 0;
  background: url('@/assets/image/webp/nux-modal-background.webp') center / 100% 100% no-repeat;
  filter: blur(20px);
}

/* 背景图上方的白色半透明磨砂遮罩，白色越重背景越浅 */
.agent-picker-modal .ant-modal-content::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  background: rgba(255, 255, 255, .4);
}

/* 内容浮在背景与遮罩层之上 */
.agent-picker-modal .ant-modal-content>* {
  position: relative;
  z-index: 1;
}

/* 开合动画：默认 ant-zoom 以点击位置为缩放原点，弹窗从按钮处"飞"进来显得突兀，
   这里固定为中心原点，只做位移 + 轻微缩放 + 淡入，且动画结束后 transform 归零避免文字发虚 */
.agent-picker-modal .ant-modal {
  transform-origin: 50% 50% !important;
}

@keyframes agent-picker-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(.985);
  }

  to {
    opacity: 1;
    transform: none;
  }
}

@keyframes agent-picker-out {
  from {
    opacity: 1;
    transform: none;
  }

  to {
    opacity: 0;
    transform: translateY(4px) scale(.99);
  }
}

@keyframes agent-picker-mask-in {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

@keyframes agent-picker-mask-out {
  from {
    opacity: 1;
  }

  to {
    opacity: 0;
  }
}

.agent-picker-zoom-enter {
  /* Vue 在第一帧只加 enter 类、下一帧才加 active 类，这里必须先隐藏，否则弹窗会先完整显示一帧再淡入（闪烁） */
  opacity: 0;
  animation-duration: .28s;
  animation-fill-mode: both;
  animation-timing-function: cubic-bezier(.16, 1, .3, 1);
  animation-play-state: paused;
}

.agent-picker-zoom-enter.agent-picker-zoom-enter-active {
  animation-name: agent-picker-in;
  animation-play-state: running;
}

.agent-picker-zoom-leave {
  animation-duration: .18s;
  animation-fill-mode: both;
  animation-timing-function: cubic-bezier(.4, 0, .2, 1);
  animation-play-state: paused;
}

.agent-picker-zoom-leave.agent-picker-zoom-leave-active {
  animation-name: agent-picker-out;
  animation-play-state: running;
}

.agent-picker-fade-enter {
  opacity: 0;
  animation-duration: .24s;
  animation-fill-mode: both;
  animation-timing-function: cubic-bezier(.33, 0, .2, 1);
  animation-play-state: paused;
}

.agent-picker-fade-enter.agent-picker-fade-enter-active {
  animation-name: agent-picker-mask-in;
  animation-play-state: running;
}

.agent-picker-fade-leave {
  animation-duration: .18s;
  animation-fill-mode: both;
  animation-timing-function: cubic-bezier(.4, 0, .2, 1);
  animation-play-state: paused;
}

.agent-picker-fade-leave.agent-picker-fade-leave-active {
  animation-name: agent-picker-mask-out;
  animation-play-state: running;
}

.agent-picker-header {
  position: relative;
  padding: 24px 24px 16px;
}

.agent-picker-header h2 {
  margin: 0 0 8px;
  color: #202020;
  font-size: 20px;
  font-weight: 600;
  line-height: 28px;
}

.agent-picker-header p {
  margin: 0;
  font-size: 13px;
  line-height: 21px;
  color: #777780;
}

.agent-picker-close {
  position: absolute;
  right: 18px;
  top: 18px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 25px;
  background: transparent;
  color: #8a8a94;
  font-size: 14px;
  cursor: pointer;
  transition: color .2s ease, background-color .2s ease;
}

.agent-picker-close:hover {
  color: #666;
  background: rgba(255, 255, 255, .55);
}

.agent-picker-search {
  display: flex;
  align-items: center;
  gap: 10px;
  height: 40px;
  margin: 0 16px 8px;
  padding: 0 14px;
  background: rgba(255, 255, 255, .5);
  border-radius: 16px;
  color: #a0a0aa;
}

.agent-picker-search input {
  width: 100%;
  border: 0;
  outline: none;
  background: transparent;
  color: #262626;
  font: inherit;
  font-size: 14px;
}

.agent-picker-search input::placeholder {
  color: #9b9ba5;
}

.agent-picker-list {
  /* 260px ≈ 弹窗除列表外的头部/搜索/tab/底部总高，避免小屏被裁切 */
  height: min(400px, calc(100vh - 260px));
  overflow-y: auto;
  border-top: 1px solid rgba(0, 0, 0, .06);
  /* 留出内边距，配合列表项圆角，hover 时呈现内嵌卡片而不是贴边横条 */
  padding: 6px 8px;
  scrollbar-width: thin;
  scrollbar-color: #aaa transparent;
}

.agent-picker-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 16px;
  min-height: 80px;
  padding: 16px;
  background: transparent;
  border: 0;
  border-radius: 16px;
  text-align: left;
  cursor: pointer;
}

/* 悬停为圆角卡片式浅提亮；底部渐变已褪成白色时白色提亮不可见，
   补一层柔和投影勾勒卡片轮廓，保证整列 hover 都有反馈 */
.agent-picker-item:hover,
.agent-picker-item:focus-visible {
  background: rgba(255, 255, 255, .5);
  box-shadow: 0 2px 8px rgba(31, 45, 61, .06);
}

.agent-picker-item .ant-avatar {
  flex-shrink: 0;
}

/* 图片头像不加描边，只给一层柔和投影保留悬浮层次；首字母头像仍用描边与白底分隔 */
.agent-picker-item .ant-avatar-image {
  box-shadow: 0 3px 10px rgba(31, 45, 61, .14);
}

.agent-picker-item .ant-avatar:not(.ant-avatar-image) {
  box-shadow: 0 0 0 2px #f4f4f4;
}

.agent-picker-details {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.agent-picker-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  line-height: 20px;
  color: #262626;
}

.agent-picker-tabs {
  position: relative;
  display: flex;
  gap: 4px;
  margin: 0 16px 10px;
  padding: 3px;
  background: rgba(255, 255, 255, .5);
  border-radius: 12px;
}

/* 滑块保持单段惯性过渡，只做位移与阴影变化，手感会更稳也更跟手 */
.agent-picker-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: calc(50% - 5px);
  height: calc(100% - 6px);
  border-radius: 9px;
  background: #fff;
  box-shadow:
    0 1px 1px rgba(17, 24, 39, .05),
    0 4px 10px rgba(17, 24, 39, .08);
  pointer-events: none;
  will-change: transform, box-shadow;
  transform: translate3d(0, 0, 0);
  transition:
    transform .34s cubic-bezier(.22, 1, .36, 1),
    box-shadow .34s cubic-bezier(.22, 1, .36, 1);
}

.agent-picker-thumb.is-shared {
  transform: translate3d(calc(100% + 4px), 0, 0);
  box-shadow:
    0 2px 3px rgba(17, 24, 39, .06),
    0 8px 18px rgba(17, 24, 39, .12);
}

.agent-picker-tab {
  position: relative;
  z-index: 1;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  padding: 0 10px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #9c9ca6;
  cursor: pointer;
  font-size: 13px;
  line-height: 20px;
  transition:
    color .2s ease,
    transform .18s cubic-bezier(.2, 0, 0, 1);
}

.agent-picker-tab:hover {
  color: #6b6b76;
}

/* 按下有轻微回馈，点击手感更实 */
.agent-picker-tab:active {
  transform: scale(.97);
}

.agent-picker-tab.active {
  color: #2f2f38;
  font-weight: 600;
}

.agent-picker-tab-count {
  padding: 0 6px;
  border-radius: 8px;
  background: rgba(0, 0, 0, .04);
  color: #a6a6b0;
  font-size: 11px;
  line-height: 16px;
  font-weight: 400;
  transform: translateZ(0);
  transition:
    background-color .24s ease,
    color .24s ease,
    transform .24s cubic-bezier(.22, 1, .36, 1);
}

/* 选中态只保留轻微跟随感，避免每次切换都跳一下 */
.agent-picker-tab.active .agent-picker-tab-count {
  background: #edf4ff;
  color: #1677ff;
  transform: scale(1.02);
}

@media (prefers-reduced-motion: reduce) {
  .agent-picker-tab,
  .agent-picker-tab-count,
  .agent-picker-thumb {
    transition: none;
  }
}

.agent-picker-description {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  color: #777780;
  font-size: 12px;
  line-height: 18px;
}

.agent-picker-footer {
  width: 100%;
  height: 54px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  border: 0;
  border-top: 1px solid rgba(0, 0, 0, .06);
  background: transparent;
  color: #777;
  cursor: pointer;
  font-size: 13px;
}

.agent-picker-footer .anticon {
  font-size: 10px;
}

.agent-picker-footer:hover {
  background: rgba(255, 255, 255, .6);
}

.agent-picker-empty {
  padding: 32px 16px;
  text-align: center;
  color: #999;
}
</style>