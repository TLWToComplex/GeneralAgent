import NotificationService from './NotificationService';
import { getTabScopeId, getTabWorkspaceKey, shouldHydrateLegacyWorkspace } from './TabScopeService';
import { clearKnowledgeBaseRuntimeCache } from '@/composables/useKnowledgeBaseCache';
import { resetChatInputKnowledgeBaseState } from '@/composables/useChatInputKnowledgeBaseState';

export const WORKSPACE_STORAGE_CLEARED_EVENT = 'mcp-workspace-storage-cleared';

/**
 * 存储键定义
 */
export const STORAGE_KEYS = {
  API_CONFIG: 'mcp-client-api-config',
  SYSTEM_MESSAGE: 'mcp-client-system-message',
  PROVIDERS: 'mcp-providers',
  MODELS: 'mcp-models',
  USER_PREFERENCES: 'mcp-user-preferences',
  AGENTS: 'mcp-agents',
  SELECTED_AGENT: 'mcp-selected-agent',
  ACTIVE_AGENT: 'mcp-active-agent',
  WORKSPACE_SELECTED_AGENT: 'selected-agent',
  WORKSPACE_ACTIVE_AGENT: 'active-agent',
  WORKSPACE_SESSION_THREAD_ID: 'session-thread-id'
};

/**
 * 存储服务类
 * 统一管理本地存储操作
 */
export class StorageService {
  private defaultValues: Record<string, any> = {
    [STORAGE_KEYS.USER_PREFERENCES]: {
      autoCollapseReasoning: false,
      autoCollapseToolPanels: false,
      autoCollapseToolDetailsOnComplete: false,
      renderUserMessageMarkdown: true,
      chatWindowStyle: 'conversation'
    }
  };
  /**
   * 单例实例
   */
  private static instance: StorageService;

  /**
   * 获取单例实例
   */
  public static getInstance(): StorageService {
    if (!StorageService.instance) {
      StorageService.instance = new StorageService();
    }
    return StorageService.instance;
  }

  /**
   * 存储项
   * 
   * @param key 存储键名
   * @param value 要存储的值
   * @returns 是否存储成功
   */
  public set<T>(key: string, value: T): boolean {
    try {
      const serializedValue = JSON.stringify(value);
      localStorage.setItem(key, serializedValue);
      return true;
    } catch (e) {
      console.error(`Failed to store key ${key}:`, e);
      if (e instanceof DOMException && e.name === 'QuotaExceededError') {
        this.showStorageQuotaExceededError(key);
      }
      return false;
    }
  }

  /**
   * 显示存储配额超出错误提示
   * @param key 导致错误的存储键名
   */
  private showStorageQuotaExceededError(key: string): void {
    // 使用项目封装的通知服务
    NotificationService.warning(`无法保存"${key}"的数据，请减小文件大小后再次尝试`);
  }

  /**
   * 获取存储项
   * 
   * @param key 存储键名
   * @param defaultValue 默认值，如果存储项不存在则返回此值
   * @returns 存储的值或默认值
   */
  public get<T>(key: string, defaultValue?: T): T | null {
    try {
      const serializedValue = localStorage.getItem(key);
      if (serializedValue === null) {
        const preset = this.defaultValues[key] as T | undefined;
        if (preset !== undefined) {
          this.set(key, preset);
          return preset;
        }
        return defaultValue !== undefined ? defaultValue : null;
      }
      const value = JSON.parse(serializedValue);
      return value;
    } catch (e) {
      console.error(`Failed to get key ${key}:`, e);
      const preset = this.defaultValues[key] as T | undefined;
      if (preset !== undefined) {
        return preset;
      }
      return defaultValue !== undefined ? defaultValue : null;
    }
  }

  /**
   * 移除存储项
   * 
   * @param key 存储键名
   */
  public remove(key: string): void {
    try {
      localStorage.removeItem(key);
    } catch (e) {
      console.error(`Failed to remove key ${key}:`, e);
    }
  }

  /**
   * 清除所有存储项
   */
  public clear(): void {
    try {
      localStorage.clear();
    } catch (e) {
      console.error('Failed to clear storage:', e);
    }
  }

  private getWorkspaceStorageKey(key: string): string {
    return getTabWorkspaceKey(key);
  }

  private getWorkspaceItem<T>(key: string): T | null {
    try {
      const rawValue = sessionStorage.getItem(this.getWorkspaceStorageKey(key));
      if (!rawValue) {
        return null;
      }
      return JSON.parse(rawValue) as T;
    } catch (e) {
      console.error(`Failed to get workspace key ${key}:`, e);
      return null;
    }
  }

  private getWorkspaceRawItem(key: string): string | null {
    try {
      return sessionStorage.getItem(this.getWorkspaceStorageKey(key));
    } catch (e) {
      console.error(`Failed to get workspace raw key ${key}:`, e);
      return null;
    }
  }

  private setWorkspaceItem<T>(key: string, value: T): boolean {
    try {
      sessionStorage.setItem(this.getWorkspaceStorageKey(key), JSON.stringify(value));
      return true;
    } catch (e) {
      console.error(`Failed to store workspace key ${key}:`, e);
      return false;
    }
  }

  private setWorkspaceRawItem(key: string, value: string): boolean {
    try {
      sessionStorage.setItem(this.getWorkspaceStorageKey(key), value);
      return true;
    } catch (e) {
      console.error(`Failed to store workspace raw key ${key}:`, e);
      return false;
    }
  }

  private removeWorkspaceItem(key: string): void {
    try {
      sessionStorage.removeItem(this.getWorkspaceStorageKey(key));
    } catch (e) {
      console.error(`Failed to remove workspace key ${key}:`, e);
    }
  }

  public clearWorkspaceScope(): void {
    const scopeId = getTabScopeId();
    const prefix = `mcp-tab::${scopeId}::`;
    const toRemove: string[] = [];
    try {
      for (let i = 0; i < sessionStorage.length; i += 1) {
        const key = sessionStorage.key(i);
        if (key && key.startsWith(prefix)) {
          toRemove.push(key);
        }
      }
      toRemove.forEach((key) => sessionStorage.removeItem(key));
    } catch (e) {
      console.error('Failed to clear workspace scope:', e);
    } finally {
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent(WORKSPACE_STORAGE_CLEARED_EVENT));
      }
    }
  }

  public getWorkspaceValue<T>(key: string, defaultValue?: T): T | null {
    const value = this.getWorkspaceItem<T>(key);
    if (value === null || value === undefined) {
      return defaultValue === undefined ? null : defaultValue;
    }
    return value;
  }

  public setWorkspaceValue<T>(key: string, value: T): boolean {
    return this.setWorkspaceItem(key, value);
  }

  public removeWorkspaceValue(key: string): void {
    this.removeWorkspaceItem(key);
  }

  public clearForLogout(): void {
    this.clearWorkspaceScope();
    this.removeAccessToken();
    clearKnowledgeBaseRuntimeCache();
    resetChatInputKnowledgeBaseState();
    try {
      sessionStorage.removeItem('shouldOpenInputToolbar');
    } catch (e) {
      console.error('Failed to clear toolbar session state:', e);
    }
    [
      STORAGE_KEYS.API_CONFIG,
      STORAGE_KEYS.SYSTEM_MESSAGE,
      STORAGE_KEYS.PROVIDERS,
      STORAGE_KEYS.MODELS,
      STORAGE_KEYS.USER_PREFERENCES,
      STORAGE_KEYS.AGENTS,
      STORAGE_KEYS.SELECTED_AGENT,
      STORAGE_KEYS.ACTIVE_AGENT,
      'user-profile',
      'mcp-need-update-msg',
      'mcp-original-config',
      // 界面所处的视图状态：换账号登录后不应继承上一位用户停留的位置
      'mcp-active-workspace',
      'mcp-history-sidebar-visible',
      'mcp-history-expanded-agent-ids',
      'mcp-history-agent-section-expanded',
      'mcp-history-recent-section-expanded',
      'mcp-kb-availability-snapshot',
      'kb-workspace-detail-open',
      'selected_knowledge_base_name',
      'selected_knowledge_base_permission_filter',
      'mcp-open-add-modal'
    ].forEach((key) => this.remove(key));
  }



  // 专用方法 - 配置相关

  /**
   * 获取API配置
   */
  public getApiConfig(): any {
    const cfg = this.get(STORAGE_KEYS.API_CONFIG);
    if (cfg && typeof cfg === 'object') {
      if (!(cfg as any).apiBaseUrl && (cfg as any).apiUrl) {
        (cfg as any).apiBaseUrl = (cfg as any).apiUrl;
      }
      if (typeof (cfg as any).apiBaseUrl === 'string') {
        (cfg as any).apiBaseUrl = (cfg as any).apiBaseUrl.trim().replace(/^[`\s]+|[`\s]+$/g, '');
      }
      if (typeof (cfg as any).apiKey === 'string') {
        (cfg as any).apiKey = (cfg as any).apiKey.trim();
      }
      if (typeof (cfg as any).model === 'string') {
        (cfg as any).model = (cfg as any).model.trim();
      }
    }
    return cfg;
  }

  /**
   * 保存API配置
   */
  public setApiConfig(config: any): void {
    this.set(STORAGE_KEYS.API_CONFIG, config);
  }

  /**
   * 获取系统消息
   */
  public getSystemMessage(): string | null {
    return this.get<string>(STORAGE_KEYS.SYSTEM_MESSAGE);
  }

  /**
   * 保存系统消息
   */
  public setSystemMessage(message: string): void {
    this.set(STORAGE_KEYS.SYSTEM_MESSAGE, message);
  }

  /**
   * 获取模型提供者列表
   */
  public getProviders(): any[] {
    return this.get<any[]>(STORAGE_KEYS.PROVIDERS, []) || [];
  }

  /**
   * 获取所有模型数据
   */
  public getModels(): any {
    return this.get(STORAGE_KEYS.MODELS, {});
  }

  /**
   * 获取所有智能体配置
   */
  public getAgents(): any[] {
    return this.get<any[]>(STORAGE_KEYS.AGENTS, []) || [];
  }

  /**
   * 保存所有智能体配置
   */
  public setAgents(agents: any[]): void {
    this.set(STORAGE_KEYS.AGENTS, agents);
  }

  /**
   * 添加单个智能体配置
   */
  public addAgent(agent: any): void {
    const agents = this.getAgents();
    agents.push(agent);
    this.setAgents(agents);
  }

  /**
   * 根据ID删除智能体配置
   */
  public removeAgent(agentId: string): void {
    const agents = this.getAgents();
    const filteredAgents = agents.filter((agent: any) => agent.id !== agentId);
    this.setAgents(filteredAgents);
  }

  /**
   * 获取选中的智能体 ID
   */
  public getSelectedAgent(): string | null {
    try {
      const workspaceValue = this.getWorkspaceRawItem(STORAGE_KEYS.WORKSPACE_SELECTED_AGENT);
      if (workspaceValue) {
        return workspaceValue;
      }
      if (!shouldHydrateLegacyWorkspace()) {
        return null;
      }
      const legacyValue = localStorage.getItem(STORAGE_KEYS.SELECTED_AGENT);
      if (legacyValue) {
        this.setWorkspaceRawItem(STORAGE_KEYS.WORKSPACE_SELECTED_AGENT, legacyValue);
        return legacyValue;
      }
      return null;
    } catch (e) {
      console.error(`Failed to get selected agent:`, e);
      return null;
    }
  }

  /**
   * 保存选中的智能体ID或清除选中状态
   */
  public setSelectedAgent(agentId: string | null): void {
    try {
      if (agentId === null) {
        this.removeWorkspaceItem(STORAGE_KEYS.WORKSPACE_SELECTED_AGENT);
        localStorage.removeItem(STORAGE_KEYS.SELECTED_AGENT);
      } else {
        this.setWorkspaceRawItem(STORAGE_KEYS.WORKSPACE_SELECTED_AGENT, agentId);
        localStorage.removeItem(STORAGE_KEYS.SELECTED_AGENT);
      }
    } catch (e) {
      console.error(`Failed to save selected agent:`, e);
    }
  }
  
  /**
   * 获取当前活跃的智能体配置
   */
  public getActiveAgent(): any | null {
    try {
      const workspaceValue = this.getWorkspaceItem<any>(STORAGE_KEYS.WORKSPACE_ACTIVE_AGENT);
      if (workspaceValue) {
        return workspaceValue;
      }
      if (!shouldHydrateLegacyWorkspace()) {
        return null;
      }
      const rawValue = localStorage.getItem(STORAGE_KEYS.ACTIVE_AGENT);
      if (!rawValue) {
        return null;
      }
      const parsedValue = JSON.parse(rawValue);
      this.setWorkspaceItem(STORAGE_KEYS.WORKSPACE_ACTIVE_AGENT, parsedValue);
      return parsedValue;
    } catch (e) {
      console.error(`Failed to get active agent:`, e);
      return null;
    }
  }
  
  /**
   * 设置当前活跃的智能体配置
   */
  public setActiveAgent(agentConfig: any): void {
    try {
      this.setWorkspaceItem(STORAGE_KEYS.WORKSPACE_ACTIVE_AGENT, agentConfig);
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_AGENT);
    } catch (e) {
      console.error(`Failed to save active agent:`, e);
    }
  }
  
  /**
   * 移除当前活跃的智能体配置
   */
  public removeActiveAgent(): void {
    try {
      this.removeWorkspaceItem(STORAGE_KEYS.WORKSPACE_ACTIVE_AGENT);
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_AGENT);
    } catch (e) {
      console.error(`Failed to remove active agent:`, e);
    }
  }

  public getWorkspaceSessionThreadId(): string | null {
    return this.getWorkspaceRawItem(STORAGE_KEYS.WORKSPACE_SESSION_THREAD_ID);
  }

  public setWorkspaceSessionThreadId(sessionThreadId: string | null): void {
    if (!sessionThreadId) {
      this.removeWorkspaceItem(STORAGE_KEYS.WORKSPACE_SESSION_THREAD_ID);
      return;
    }
    this.setWorkspaceRawItem(STORAGE_KEYS.WORKSPACE_SESSION_THREAD_ID, sessionThreadId);
  }
  
  /**
   * 获取访问令牌
   */
  public getAccessToken(): string | null {
    try {
      // 优先从 sessionStorage 获取（当前会话）
      // 如果没有则从 localStorage 获取（持久化）
      const token = sessionStorage.getItem('access_token') || localStorage.getItem('access_token');
      return token || null;
    } catch (e) {
      console.error('Failed to get access token:', e);
      return null;
    }
  }
  
  /**
   * 设置访问令牌
   * @param token 令牌
   * @param persist 是否持久化存储（保持登录）
   */
  public setAccessToken(token: string, persist: boolean = false): void {
    try {
      // 始终保存到会话存储（当前标签页/窗口生命周期）
      sessionStorage.setItem('access_token', token);

      // 如果需要持久化，则也保存到 localStorage；否则确保清除本地持久化
      if (persist) {
        localStorage.setItem('access_token', token);
      } else {
        localStorage.removeItem('access_token');
      }
    } catch (e) {
      console.error('Failed to save access token:', e);
    }
  }
  
  /**
   * 移除访问令牌
   */
  public removeAccessToken(): void {
    try {
      // 同时移除会话与持久化令牌
      sessionStorage.removeItem('access_token');
      localStorage.removeItem('access_token');
    } catch (e) {
      console.error('Failed to remove access token:', e);
    }
  }
}

/**
 * 默认存储服务实例
 */
export default StorageService.getInstance();
