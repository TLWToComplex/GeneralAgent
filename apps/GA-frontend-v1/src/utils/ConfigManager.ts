import StorageService from './StorageService';

/**
 * API配置类型
 */
export interface ApiConfig {
  apiKey: string;
  apiBaseUrl: string;
  model: string;
  service?: string;
}

/**
 * 模型数据类型
 */
export interface ModelData {
  id: string;
  name: string;
  iconText?: string;
  serviceProvider?: string;
  types?: string[];
  contextSize?: number;
}

/**
 * 服务数据类型
 */
export interface ServiceData {
  apiKey?: string;
  apiUrl?: string;
  models?: Record<string, any>;
}

/**
 * 配置管理类
 * 统一处理配置的存储和获取
 */
export class ConfigManager {
  private normalizeModelEntries(modelsSource: any): any[] {
    if (!modelsSource) return [];
    if (Array.isArray(modelsSource)) {
      if (modelsSource.length === 0) return [];
      if (Array.isArray(modelsSource[0]?.models)) {
        return modelsSource.flatMap((group: any) => Array.isArray(group.models) ? group.models : []);
      }
      return modelsSource;
    }
    return Object.values(modelsSource).flatMap((group: any) =>
      Array.isArray(group?.models) ? group.models : []
    );
  }

  /**
   * 单例实例
   */
  private static instance: ConfigManager;

  /**
   * 获取单例实例
   */
  public static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }

  /**
   * 保存API配置
   */
  saveApiConfig(config: ApiConfig): void {
    StorageService.setApiConfig(config);
  }

  /**
   * 获取API配置
   */
  getApiConfig(): ApiConfig | null {
    return StorageService.getApiConfig();
  }

  /**
   * 保存系统消息
   */
  saveSystemMessage(message: string): void {
    StorageService.setSystemMessage(message);
  }

  /**
   * 获取系统消息
   */
  getSystemMessage(): string | null {
    return StorageService.getSystemMessage();
  }

  /**
   * 获取所有模型数据
   */
  getAllModelsData(): Record<string, ServiceData> | null {
    return StorageService.getModels();
  }

  /**
   * 获取模型服务数据
   */
  getModelServiceData(serviceName: string): ServiceData | null {
    const modelsData = this.getAllModelsData();
    if (modelsData && modelsData[serviceName]) {
      return modelsData[serviceName];
    }
    return null;
  }

  /**
   * 获取可用的模型服务
   */
  getAvailableModelServices(): any[] {
    return StorageService.getProviders();
  }

  /**
   * 从所有模型数据中提取可用模型列表
   */
  getAvailableModels(): ModelData[] {
    const allModels: ModelData[] = [];
    
    try {
      const modelsData = this.getAllModelsData();
      const providers = this.getAvailableModelServices();
      
      // 创建有效提供商集合
      const validProviders = new Set(providers.map((p: any) => p.name));
      
      if (!modelsData) {
        return allModels;
      }
      
      // 遍历每个服务提供商
      Object.keys(modelsData).forEach(provider => {
        // 只处理有效提供商的模型
        if (validProviders.has(provider)) {
          const serviceData = modelsData[provider];
          
          const modelEntries = this.normalizeModelEntries(serviceData.models);
          if (modelEntries.length) {
            modelEntries.forEach((modelData: any) => {
              allModels.push({
                id: modelData.id,
                name: modelData.name,
                iconText: modelData.iconText || modelData.name.charAt(0).toUpperCase(),
                serviceProvider: provider,
                types: Array.isArray(modelData.types) ? modelData.types : [],
                contextSize: typeof modelData.contextSize === 'number'
                  ? modelData.contextSize
                  : (typeof modelData.context_size === 'number' ? modelData.context_size : undefined)
              });
            });
          }
        }
      });
    } catch (e) {
      console.error('获取可用模型列表失败:', e);
    }
    
    return allModels;
  }

  /**
   * 根据模型ID查找对应的服务
   */
  findServiceForModel(modelId: string, preferredService?: string): { serviceName: string, serviceData: ServiceData } | null {
    const modelsData = this.getAllModelsData();
    
    if (!modelsData) {
      return null;
    }

    const serviceContainsModel = (serviceData: ServiceData) => {
      return this.normalizeModelEntries(serviceData.models).some((modelData: any) => modelData.id === modelId);
    };

    if (preferredService && modelsData[preferredService] && serviceContainsModel(modelsData[preferredService])) {
      return {
        serviceName: preferredService,
        serviceData: modelsData[preferredService]
      };
    }

    for (const serviceName in modelsData) {
      const serviceData = modelsData[serviceName];

      if (serviceContainsModel(serviceData)) {
        return {
          serviceName,
          serviceData
        };
      }
    }
    
    return null;
  }
}
