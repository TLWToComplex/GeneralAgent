import { ref, computed } from 'vue';
import { ConfigManager, type ApiConfig, type ModelData } from '@/utils/ConfigManager';

/**
 * 配置管理的 composable
 * 基于 ConfigManager 提供响应式的配置管理能力
 */
export function useConfig() {
  // 获取配置管理器实例
  const configManager = ConfigManager.getInstance();
  
  // 响应式状态
  const apiKey = ref<string>('');
  const apiBaseUrl = ref<string>('');
  const model = ref<string>('');
  const selectedModelService = ref<string>('');
  const isConfigured = ref<boolean>(false);
  const error = ref<string | null>(null);
  const modelListVersion = ref<number>(0);
  
  /**
   * 保存API配置到本地存储
   */
  function saveApiConfig() {
    const config: ApiConfig = {
      apiKey: apiKey.value,
      apiBaseUrl: apiBaseUrl.value,
      model: model.value,
      service: selectedModelService.value || undefined
    };
    
    try {
      configManager.saveApiConfig(config);
    } catch (e) {
      console.error('Failed to save API configuration:', e);
    }
  }
  
  /**
   * 从本地存储加载API配置
   */
  function loadApiConfig(): boolean {
    const config = configManager.getApiConfig();
    if (config) {
      apiKey.value = config.apiKey || '';
      apiBaseUrl.value = config.apiBaseUrl || '';
      model.value = config.model || '';
      selectedModelService.value = config.service || '';
      return true;
    }
    return false;
  }
  
  /**
   * 保存系统消息
   */
  function saveSystemMessage(message: string) {
    configManager.saveSystemMessage(message);
  }
  
  /**
   * 获取系统消息
   */
  function getSystemMessage(): string | null {
    return configManager.getSystemMessage();
  }
  
  /**
   * 保存选定的模型
   * 不再单独保存模型，而是通过保存完整API配置来保存模型
   */
  function saveSelectedModel() {
    if (model.value) {
      saveApiConfig();
    }
  }
  
  /**
   * 加载选定的模型
   * 不再单独加载模型，而是通过加载完整API配置来获取模型
   */
  function loadSelectedModel(): boolean {
    // 现在模型信息存储在apiConfig中，通过loadApiConfig加载
    return false;
  }
  
  /**
   * 从模型服务中加载配置
   */
  function loadModelServiceConfig(serviceName: string, silent = false): boolean {
    const serviceData = configManager.getModelServiceData(serviceName);
    
    if (serviceData) {
      apiKey.value = serviceData.apiKey || '';
      apiBaseUrl.value = serviceData.apiUrl || '';
      
      // 保存选定的模型服务
      selectedModelService.value = serviceName;
      
      // 如果当前没有选择模型，自动选择该服务的第一个可用模型
      if (!model.value) {
        const availableModelsForService = availableModels.value.filter(m => m.serviceProvider === serviceName);
        if (availableModelsForService.length > 0) {
          model.value = availableModelsForService[0].id;
          saveApiConfig();
        }
      }
      
      return true;
    } else if (!silent) {
      error.value = '服务数据不存在';
      console.error('服务数据不存在，请先配置服务');
    }
    
    return false;
  }
  
  /**
   * 查找模型对应的服务并加载配置
   */
  function loadConfigForModel(modelId: string, preferredService = selectedModelService.value): boolean {
    const result = configManager.findServiceForModel(modelId, preferredService);
    
    if (result) {
      const { serviceName, serviceData } = result;
      selectedModelService.value = serviceName;
      apiKey.value = serviceData.apiKey || '';
      apiBaseUrl.value = serviceData.apiUrl || '';
      return true;
    }
    
    return false;
  }
  
  /**
   * 刷新模型列表版本
   * 用于触发 availableModels 计算属性重新计算
   */
  function refreshModelList() {
    modelListVersion.value += 1;
  }
  
  /**
   * 获取所有可用模型
   */
  const availableModels = computed((): ModelData[] => {
    // 使用 modelListVersion 触发重新计算
    modelListVersion.value;
    return configManager.getAvailableModels();
  });
  
  /**
   * 获取所有可用模型服务
   */
  const availableModelServices = computed(() => {
    return configManager.getAvailableModelServices();
  });
  
  /**
   * 验证当前配置是否完整
   */
  function validateConfig(): boolean {
    const hasApiKey = !!apiKey.value;
    const hasApiUrl = !!apiBaseUrl.value;
    const hasModel = !!model.value;
    
    const isValid = hasApiKey && hasApiUrl && hasModel;
    
    // 自动更新配置状态
    isConfigured.value = isValid;
    
    return isValid;
  }

  /**
   * 初始化配置
   * 从本地存储加载配置
   */
  function initialize() {
    // 加载API配置
    loadApiConfig();
    if (typeof apiKey.value === 'string') { apiKey.value = apiKey.value.trim(); }
    if (typeof apiBaseUrl.value === 'string') { apiBaseUrl.value = apiBaseUrl.value.trim().replace(/^[`\s]+|[`\s]+$/g, ''); }
    if (typeof model.value === 'string') { model.value = model.value.trim(); }
    saveApiConfig();
    
    // 验证并更新配置状态
    validateConfig();

    // 若仅存在模型但缺少密钥或基础URL，则根据模型自动加载对应服务配置
    if (model.value && (!apiKey.value || !apiBaseUrl.value || !selectedModelService.value)) {
      loadConfigForModel(model.value, selectedModelService.value);
      validateConfig();
      saveApiConfig();
    }

    // 若没有选择模型但存在可用模型，自动选择第一个并加载其服务配置
    if (!model.value) {
      const models = availableModels.value;
      if (models.length > 0) {
        model.value = models[0].id;
        selectedModelService.value = models[0].serviceProvider || '';
        saveApiConfig();
        loadConfigForModel(model.value, selectedModelService.value);
        validateConfig();
        saveApiConfig();
      }
    }
  }
  
  // 在创建时初始化
  initialize();
  
  return {
    // 响应式状态
    apiKey,
    apiBaseUrl,
    model,
    selectedModelService,
    isConfigured,
    error,
    
    // 计算属性
    availableModels,
    availableModelServices,
    
    // 方法
    saveApiConfig,
    loadApiConfig,
    saveSystemMessage,
    getSystemMessage,
    saveSelectedModel,
    loadSelectedModel,
    loadModelServiceConfig,
    loadConfigForModel,
    refreshModelList,
    initialize,
    validateConfig,
    
    // 设置方法
    setIsConfigured(value: boolean) {
      isConfigured.value = value;
    },
    setError(value: string | null) {
      error.value = value;
    }
  };
}
