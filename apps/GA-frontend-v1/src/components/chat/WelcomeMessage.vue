<template>
  <div class="welcome-message">
    <Transition name="fade-slide" mode="out-in">
      <div v-if="!activeAgent" class="welcome-content" :key="showLogo ? 'logo' : 'title'">
        <Transition name="logo-title-swap" mode="out-in" appear>
          <div v-if="showLogo" class="welcome-logo">
            <img class="welcome-logo-img" :src="logoPng" alt="logo" :class="{ loaded: imageLoaded }" />
            <span class="logo-text">{{ systemName }}</span>
          </div>
          <p v-else class="welcome-title">向我提问，我来帮您解答～</p>
        </Transition>
      </div>
      <div v-else class="welcome-content agent-mode" key="agent">
        <div class="agent-welcome">
          <a-avatar :size="56" :src="resolveAvatar(activeAgent.basic?.avatar)"
            :style="{ backgroundColor: resolveAvatar(activeAgent.basic?.avatar) ? 'transparent' : (activeAgent.basic?.themeColor || '#b9dba0'), fontSize: '20px' }">
            {{ (activeAgent.basic?.name || 'A').charAt(0) }}
          </a-avatar>
          <div class="agent-info">
            <h3 class="agent-name">{{ activeAgent.basic?.name || '未命名智能体' }}</h3>
            <p class="agent-desc">{{ activeAgent.basic?.description || '暂无描述' }}</p>
          </div>
        </div>
        <button class="agent-switch-button" type="button" @click="openPicker">
          <SwapOutlined /><span>切换智能体</span>
          <span class="agent-switch-avatars" aria-hidden="true">
            <a-avatar v-for="agent in switchPreviewAgents" :key="agent.id" :size="22" :src="resolveAvatar(agent.config?.basic?.avatar)"
              :style="{ backgroundColor: resolveAvatar(agent.config?.basic?.avatar) ? 'transparent' : (agent.config?.basic?.themeColor || '#b9dba0'), fontSize: '11px' }">{{
                agentDisplayName(agent).charAt(0) }}</a-avatar>
          </span>
        </button>
      </div>
    </Transition>
    <AgentPickerModal v-model:open="pickerOpen" @select-agent="handleSelectAgent" @browse-agents="handleBrowseAgents" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { Avatar as AAvatar } from 'ant-design-vue';
import { SwapOutlined } from '@ant-design/icons-vue';
import StorageService from '@/utils/StorageService';
import { resolveAgentAvatar } from '@/utils/agentAvatar';
import AgentPickerModal from '@/components/chat/AgentPickerModal.vue';
import logoPng from '@/assets/ga-logo.svg';
import { getSystemName } from '@/utils/RuntimeConfig';

const props = defineProps<{
  activeAgent: any | null;
}>();

const emit = defineEmits<{ (event: 'select-agent', agent: any): void; (event: 'browse-agents'): void }>();
const pickerOpen = ref(false);
const agents = ref<ReturnType<typeof StorageService.getAgents>>([]);
const loadAgents = () => { agents.value = StorageService.getAgents(); };
// 渲染层统一解析头像：兼容 localStorage 中的稳定 key / dev 路径 / 旧打包路径
const resolveAvatar = (value?: string) => resolveAgentAvatar(value);
// activeAgent 存的是 config 对象（无 id），只能用 basic.name 比对；取值层级需与模板一致
const agentDisplayName = (agent: any) => agent?.config?.basic?.name || agent?.name || '';
const switchPreviewAgents = computed(() => agents.value.filter(agent => agentDisplayName(agent) !== (props.activeAgent?.basic?.name || '')).slice(0, 3));

const openPicker = () => { pickerOpen.value = true; };
const handleSelectAgent = (agent: any) => emit('select-agent', agent);
const handleBrowseAgents = () => emit('browse-agents');

const showLogo = ref(true);
const imageLoaded = ref(false);

// 预加载logo图片
const preloadImage = new Image();
preloadImage.src = logoPng;
preloadImage.onload = () => {
  imageLoaded.value = true;
};

function handleShowTitle() {
  showLogo.value = false;
}

function handleShowLogo() {
  showLogo.value = true;
}

onMounted(() => {
  loadAgents();
  window.addEventListener('agents-updated', loadAgents);
  window.addEventListener('welcome-message-show-title', handleShowTitle as EventListener);
  window.addEventListener('welcome-message-show-logo', handleShowLogo as EventListener);

  // 确保图片已加载
  if (preloadImage.complete) {
    imageLoaded.value = true;
  }
});

onUnmounted(() => {
  window.removeEventListener('agents-updated', loadAgents);
  window.removeEventListener('welcome-message-show-title', handleShowTitle as EventListener);
  window.removeEventListener('welcome-message-show-logo', handleShowLogo as EventListener);
});

// 计算属性获取系统名称
const systemName = computed(() => {
  return getSystemName();
});
</script>

<style scoped>
@import '../../assets/styles/chat-view.css';

/* 3D 透视仅服务于 logo/标题切换动画；智能体区域不使用，避免文字被栅格化后发虚 */
.welcome-content:not(.agent-mode) {
  perspective: 1000px;
  transform-style: preserve-3d;
}

.logo-title-swap-enter-active,
.logo-title-swap-leave-active {
  transition:
    opacity 420ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 480ms cubic-bezier(0.16, 1, 0.3, 1),
    filter 380ms ease;
  will-change: opacity, transform, filter;
}

.logo-title-swap-enter-from {
  opacity: 0;
  transform: translateY(10px) rotateX(-12deg) scale(0.98);
  filter: blur(8px);
}

.logo-title-swap-enter-to {
  opacity: 1;
  transform: translateY(0) rotateX(0deg) scale(1);
  filter: blur(0);
}

.logo-title-swap-leave-from {
  opacity: 1;
  transform: translateY(0) rotateX(0deg) scale(1);
  filter: blur(0);
}

.logo-title-swap-leave-to {
  opacity: 0;
  transform: translateY(-10px) rotateX(12deg) scale(0.98);
  filter: blur(6px);
}

/* 关闭 3D 上下文并用整数尺寸，保证文字与边框在像素边界上清晰渲染 */
/* 宽度与输入框 .input-bar-outer 保持一致 */
.welcome-content.agent-mode { width: calc(100% - 40px); max-width: 780px; min-width: 280px; box-sizing: border-box; margin: 0 auto 22px; min-height: 48px; justify-content: space-between; gap: 18px; perspective: none; transform-style: flat; backface-visibility: visible; }

.agent-mode .agent-welcome {
  flex-direction: row;
  justify-content: flex-start;
  align-items: center;
  gap: 14px;
  padding: 0;
  flex: 1;
  border-radius: 0;
  /* Let the circular avatar shadow extend beyond this row's rectangular bounds. */
  overflow: visible;
  background: none;
  min-width: 0;
}

.agent-mode .ant-avatar {
  flex-shrink: 0;
}

/* 主头像加一层柔和投影，让它在浅色背景上有轻微悬浮感（切换按钮里的小头像不加）；
   头像图片本身可能是带白底的圆形贴纸，这里显式裁成圆形，保证投影轮廓也是圆的 */
.agent-mode .agent-welcome>.ant-avatar {
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 4px 14px rgb(31 45 61 / 14%);
}

/* antd 给头像首字母加了内联 scale(1) translateX(-50%)，会产生半像素偏移导致文字发虚，改用 flex 居中 */
.agent-mode :deep(.ant-avatar) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.agent-mode :deep(.ant-avatar > .ant-avatar-string) {
  position: static;
  left: auto;
  transform: none !important;
}

.agent-mode .agent-info {
  align-items: flex-start;
  text-align: left;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.agent-mode .agent-name {
  font-size: 21px;
  line-height: 24px;
  font-weight: 600;
  color: #262626;
}

.agent-mode .agent-desc {
  font-size: 13px;
  line-height: 20px;
  color: #8a8a8a;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-switch-button {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 9px;
  height: 36px;
  padding: 19px 14px;
  border: 1px solid transparent;
  border-radius: 18px;
  background: #fff;
  color: #262626;
  cursor: pointer;
  font-size: 13px;
  transition:
    background-color .3s cubic-bezier(.2, 0, 0, 1),
    border-color .3s cubic-bezier(.2, 0, 0, 1),
    box-shadow .3s cubic-bezier(.2, 0, 0, 1),
    transform .3s cubic-bezier(.2, 0, 0, 1);
}

/* 悬浮时轻微上浮 + 描边 + 投影，与输入框卡片的阴影语言保持一致 */
.agent-switch-button:hover {
  background: #fff;
  border-color: #e3e9f2;
  box-shadow: 0 6px 16px rgba(146, 159, 202, .22);
  transform: translateY(-1px);
}

.agent-switch-button:active {
  transform: translateY(0) scale(.98);
  box-shadow: 0 2px 6px rgba(146, 159, 202, .18);
  transition-duration: .12s;
}

.agent-switch-button:focus-visible {
  outline: none;
  border-color: #91caff;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, .18);
}

.agent-switch-avatars {
  display: flex;
  flex-direction: row;
  padding-left: 5px;
}

.agent-switch-avatars .ant-avatar {
  margin-left: -9px;
  /* 以底边为轴心，旋转时像小人在摆动而不是原地打转 */
  transform-origin: 50% 100%;
  transition:
    transform .34s cubic-bezier(.34, 1.32, .64, 1),
    box-shadow .3s cubic-bezier(.2, 0, 0, 1);
}

/* 归位时反向错峰：右侧先落回，形成来回的波浪感 */
.agent-switch-avatars .ant-avatar:first-child {
  z-index: 3;
  transition-delay: .07s;
}

.agent-switch-avatars .ant-avatar:nth-child(2) {
  z-index: 2;
  transition-delay: .035s;
}

/* 悬浮：头像依次轻微弹开——两侧小幅外扩摆动，中间略抬高 */
.agent-switch-button:hover .agent-switch-avatars .ant-avatar {
  box-shadow: 0 3px 8px rgba(31, 45, 61, .14);
}

.agent-switch-button:hover .agent-switch-avatars .ant-avatar:first-child {
  transform: translate(-3px, -1px) rotate(-5deg);
  transition-delay: 0s;
}

.agent-switch-button:hover .agent-switch-avatars .ant-avatar:nth-child(2) {
  transform: translateY(-3px) scale(1.04);
  transition-delay: .04s;
}

.agent-switch-button:hover .agent-switch-avatars .ant-avatar:nth-child(3) {
  transform: translate(3px, -1px) rotate(5deg);
  transition-delay: .08s;
}

@media (prefers-reduced-motion: reduce) {
  .agent-switch-button,
  .agent-switch-avatars .ant-avatar {
    transition: none;
  }

  .agent-switch-button:hover {
    transform: none;
  }

  .agent-switch-button:hover .agent-switch-avatars .ant-avatar {
    transform: none;
    box-shadow: none;
  }
}

@media (max-width: 600px) {
  .agent-switch-avatars {
    display: none;
  }

  .agent-mode .agent-desc {
    max-width: 100%;
  }

  .agent-mode .agent-name {
    font-size: 15px;
  }

  .agent-mode .agent-welcome {
    gap: 12px;
  }
}
</style>
