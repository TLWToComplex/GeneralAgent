<template>
  <a-config-provider :locale="zhCN">
    <!-- 添加通知处理器组件 -->
    <notification-handler />
    
    <!-- 全局 Loading 覆盖层（带过渡动画） -->
    <transition name="global-loading" appear>
      <div v-if="ui.isGlobalLoading" class="global-loading-overlay">
        <div class="global-loading-content">
          <LoadingMagic />
          <div class="global-loading-text">{{ ui.loadingMessage }}</div>
        </div>
      </div>
    </transition>
    
    <!-- 欢迎页面不显示主布局 -->
    <div v-if="shouldHideLayout">
      <router-view v-slot="{ Component, route }">
        <transition 
          :name="getTransitionName(route)"
          mode="out-in"
          appear
        >
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </div>
    
    <!-- 主应用布局 -->
    <a-layout v-else class="layout">
      <a-layout>
        <a-layout-content class="content">
          <router-view v-slot="{ Component, route }">
            <transition 
              :name="getTransitionName(route)"
              mode="out-in"
              appear
            >
              <keep-alive>
                <component :is="Component" :key="route.path" />
              </keep-alive>
            </transition>
          </router-view>
        </a-layout-content>
      </a-layout>
    </a-layout>
  </a-config-provider>
</template>

<script setup lang="ts">
import { onUnmounted, computed, onMounted } from 'vue';
import { useRouter, useRoute, type RouteLocationNormalized } from 'vue-router';
import { useChatStore } from '@/stores/chat-store';
import { useUiStore } from '@/stores/uiStore';
import NotificationHandler from '@/components/common/NotificationHandler.vue';
import LoadingMagic from '@/components/common/LoadingMagic.vue';

import zhCN from "ant-design-vue/es/locale/zh_CN";
import { STORAGE_KEYS, EVENTS, ROUTES } from '@/config/constants';
import { eventBus } from '@/utils/EventBus';
import StorageService, { STORAGE_KEYS as SVC_STORAGE_KEYS } from '@/utils/StorageService';
import { GLOBAL_LOGOUT_EVENT } from '@/utils/TabScopeService';

const router = useRouter();
const route = useRoute();
const chatStore = useChatStore();
const ui = useUiStore();

// 计算是否应该隐藏主布局（修改这里的逻辑）
const shouldHideLayout = computed(() => {
  return route.meta?.hideLayout === true;
});

const getNeedUpdateMsg = () => localStorage.getItem(STORAGE_KEYS.NEED_UPDATE_MSG) === 'true';

// 处理模型选择器打开事件
const handleOpenModelSelector = () => {
  // 使用事件总线触发事件，由Header组件监听
  eventBus.emit('open-model-selector');
};

// 偏好缓存守护
const handlePreferencesStorageChange = (event: StorageEvent) => {
  if (event.key === SVC_STORAGE_KEYS.USER_PREFERENCES && event.newValue === null) {
    StorageService.get(SVC_STORAGE_KEYS.USER_PREFERENCES);
  }
};
const ensurePreferencesPresence = () => {
  StorageService.get(SVC_STORAGE_KEYS.USER_PREFERENCES);
};

let isHandlingGlobalLogout = false;
const handleGlobalLogout = async () => {
  if (isHandlingGlobalLogout) {
    return;
  }
  isHandlingGlobalLogout = true;
  try {
    try {
      void chatStore.stopCurrentRequest();
    } catch {}
    try {
      chatStore.clearChat();
    } catch {}
    StorageService.clearForLogout();
    if (route.path !== ROUTES.LOGIN) {
      await router.replace(ROUTES.LOGIN);
    }
  } finally {
    isHandlingGlobalLogout = false;
  }
};

// 检查首次访问并重定向
onMounted(() => {
  // 检查是否存在持久化的访问令牌
  const persistToken = localStorage.getItem('access_token');
  
  // 如果存在持久化的token，恢复到StorageService
  if (persistToken) {
    StorageService.setAccessToken(persistToken, true);
  }
  
  // 首次挂载时初始导航尚未完成，route.path 还是 '/'，
  // 必须等路由就绪后按真实路径判断，否则深链接会被误重定向到登录页
  router.isReady().then(() => {
    // 检查用户是否已登录（检查是否存在访问令牌）
    const accessToken = StorageService.getAccessToken();

    // 如果用户未登录，优先跳转到登录页面
    if (!accessToken) {
      // 允许直接访问认证页面，不重定向到登录页
      if (
        route.path !== ROUTES.AUTH &&
        route.path !== ROUTES.LOGIN &&
        route.path !== ROUTES.REGISTER
      ) {
        router.replace(ROUTES.LOGIN);
        return;
      }
    }

    // 如果用户已登录且后端标记需要补充初始化信息，则跳转到欢迎页
    if (
      accessToken &&
      getNeedUpdateMsg() &&
      route.path !== ROUTES.WELCOME &&
      route.path !== ROUTES.AUTH &&
      route.path !== ROUTES.LOGIN &&
      route.path !== ROUTES.REGISTER
    ) {
      router.replace(ROUTES.WELCOME);
    }
  });

  window.addEventListener('storage', handlePreferencesStorageChange);
  window.addEventListener('focus', ensurePreferencesPresence);
  window.addEventListener(GLOBAL_LOGOUT_EVENT, handleGlobalLogout as EventListener);
  ensurePreferencesPresence();
});

// 加载保存的API配置和系统提示词
chatStore.loadSavedConfig();

// 使用事件总线替代document事件
eventBus.on(EVENTS.OPEN_MODEL_SELECTOR, handleOpenModelSelector);

// 获取过渡动画名称
const getTransitionName = (route: RouteLocationNormalized) => {
  const currentRouteName = route.name;
  
  // 只有切换到 chat 页面时才有进入动画，切换到其他页面时没有动画
  if (currentRouteName === 'chat') {
    return 'page-fade';
  }
  
  // 其他所有页面间切换都没有动画
  return '';
};

// 组件卸载时清理事件监听
onUnmounted(() => {
  eventBus.off(EVENTS.OPEN_MODEL_SELECTOR, handleOpenModelSelector);
  window.removeEventListener('storage', handlePreferencesStorageChange);
  window.removeEventListener('focus', ensurePreferencesPresence);
  window.removeEventListener(GLOBAL_LOGOUT_EVENT, handleGlobalLogout as EventListener);
});
</script>

<style>
@import './assets/styles/app.css';

.global-loading-overlay {
  position: fixed;
  inset: 0;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.global-loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.global-loading-text {
  color: #333;
  font-size: 14px;
}

/* 过渡动画：整体淡入淡出 */
.global-loading-enter-active,
.global-loading-leave-active {
  transition: opacity 200ms ease;
}

.global-loading-enter-from,
.global-loading-leave-to {
  opacity: 0;
}

/* 过渡动画：内容轻微缩放与淡入 */
.global-loading-enter-active .global-loading-content,
.global-loading-leave-active .global-loading-content {
  transition: transform 220ms ease, opacity 200ms ease;
}

.global-loading-enter-from .global-loading-content,
.global-loading-leave-to .global-loading-content {
  transform: scale(0.98);
  opacity: 0;
}
</style>
