// src/stores/knowledgeBaseStore.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';

/**
 * 知识库状态管理：用于在不同组件间传递知识库相关状态
 */
export const useKnowledgeBaseStore = defineStore('knowledgeBase', () => {
  // 需要打开添加文档模态框的知识库名称
  const kbNameToOpenUploadModal = ref<string | null>(null);

  // 设置需要打开上传模态框的知识库名称
  function setKbNameToOpenUploadModal(kbName: string | null) {
    kbNameToOpenUploadModal.value = kbName;
  }

  // 获取需要打开上传模态框的知识库名称
  function getKbNameToOpenUploadModal() {
    return kbNameToOpenUploadModal.value;
  }

  // 清除需要打开上传模态框的知识库名称
  function clearKbNameToOpenUploadModal() {
    kbNameToOpenUploadModal.value = null;
  }

  return {
    // 状态
    kbNameToOpenUploadModal,

    // 方法
    setKbNameToOpenUploadModal,
    getKbNameToOpenUploadModal,
    clearKbNameToOpenUploadModal,
  };
});