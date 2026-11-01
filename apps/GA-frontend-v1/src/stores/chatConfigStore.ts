// src/stores/chatConfigStore.ts
import { defineStore } from 'pinia';
import NotificationService from '@/utils/NotificationService';
import { useConfig } from '@/composables/useConfig';
import { ConfigManager } from '@/utils/ConfigManager';

/**
 * 聊天配置状态管理
 */
export const useChatConfigStore = defineStore('chatConfig', () => {
  // 使用配置 composable
  const config = useConfig();
  
  /**
   * 从模型服务中加载配置
   * 保持与原有函数相同的接口
   */
  function loadModelServiceConfig(serviceName: string, silent = false) {
    const result = config.loadModelServiceConfig(serviceName, silent);
    
    if (result) {
      // 配置加载成功，验证并更新配置状态
      config.validateConfig();
      return true;
    } else if (!silent) {
      config.setError('所选服务未配置API密钥');
      NotificationService.warning('所选服务未配置API密钥，请在设置中配置');
    }
    
    return false;
  }
  
  /**
   * 刷新模型列表
   */
  function refreshModelList() {
    config.refreshModelList();
    
    // 检查当前选择的模型是否仍然有效
    const currentModelValid = config.availableModels.value.some(m =>
      m.id === config.model.value &&
      (!config.selectedModelService.value || m.serviceProvider === config.selectedModelService.value)
    );
    
    if (!currentModelValid) {
      // 如果有可用模型，自动选择第一个
      if (config.availableModels.value.length > 0) {
        config.model.value = config.availableModels.value[0].id;
        config.selectedModelService.value = config.availableModels.value[0].serviceProvider || '';
        config.saveSelectedModel();
        
        // 为新选择的模型加载对应的服务配置
        const selectedModel = config.availableModels.value[0];
        if (selectedModel.serviceProvider) {
          loadModelServiceConfig(selectedModel.serviceProvider, true);
        }
      } else {
        // 如果没有可用模型，重置模型选择
        config.model.value = '';
      }
    } else if (!config.model.value && config.availableModels.value.length > 0) {
      // 如果当前没有选择模型但有可用模型，自动选择第一个
      config.model.value = config.availableModels.value[0].id;
      config.selectedModelService.value = config.availableModels.value[0].serviceProvider || '';
      config.saveSelectedModel();
      
      // 为新选择的模型加载对应的服务配置
      const selectedModel = config.availableModels.value[0];
      if (selectedModel.serviceProvider) {
        loadModelServiceConfig(selectedModel.serviceProvider, true);
      }
    }
  }
  
  return {
    // 暴露配置状态
    apiKey: config.apiKey,
    apiBaseUrl: config.apiBaseUrl,
    model: config.model,
    selectedModelService: config.selectedModelService,
    isConfigured: config.isConfigured,
    error: config.error,
    availableModels: config.availableModels,
    availableModelServices: config.availableModelServices,
    
    // 暴露方法
    saveConfig: config.saveApiConfig,
    loadSavedConfig: config.initialize,
    loadModelServiceConfig,
    refreshModelList,
    loadAllModelsData: () => ConfigManager.getInstance().getAllModelsData(),
    
    // 设置方法
    setIsConfigured: config.setIsConfigured,
    setError: config.setError
  };
}); 
