// src/stores/uiStore.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';

/**
 * 全局UI状态管理：用于控制整页Loading覆盖层
 */
export const useUiStore = defineStore('ui', () => {
  const isGlobalLoading = ref<boolean>(false);
  const loadingMessage = ref<string>('正在启动服务…');

  function showGlobalLoading(message?: string) {
    if (message) {
      loadingMessage.value = message;
    }
    isGlobalLoading.value = true;
  }

  function hideGlobalLoading() {
    isGlobalLoading.value = false;
  }

  return {
    // 状态
    isGlobalLoading,
    loadingMessage,

    // 方法
    showGlobalLoading,
    hideGlobalLoading,
  };
});