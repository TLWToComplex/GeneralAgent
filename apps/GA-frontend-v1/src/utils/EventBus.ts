// src/utils/EventBus.ts

/**
 * 事件处理器类型
 */
export type EventHandler = (...args: any[]) => void;

/**
 * 统一事件总线类
 * 提供应用内事件发布-订阅功能，替代DOM事件
 * 整合了原有的两套事件系统，提供完整的事件管理功能
 */
export class EventBus {
  /**
   * 事件处理器映射
   */
  private events: Map<string, EventHandler[]> = new Map();
  
  /**
   * 单例实例
   */
  private static instance: EventBus;

  /**
   * 获取单例实例
   */
  public static getInstance(): EventBus {
    if (!EventBus.instance) {
      EventBus.instance = new EventBus();
    }
    return EventBus.instance;
  }
  
  /**
   * 订阅事件
   * 
   * @param event 事件名称
   * @param handler 事件处理器
   * @returns 取消订阅的函数
   */
  public on(event: string, handler: EventHandler): () => void {
    if (!this.events.has(event)) {
      this.events.set(event, []);
    }
    
    const handlers = this.events.get(event);
    if (handlers) {
      handlers.push(handler);
    }
    
    // 返回取消订阅函数
    return () => {
      this.off(event, handler);
    };
  }
  
  /**
   * 订阅事件，只触发一次
   * 
   * @param event 事件名称
   * @param handler 事件处理器
   * @returns 取消订阅的函数
   */
  public once(event: string, handler: EventHandler): () => void {
    const onceHandler = (...args: any[]) => {
      handler(...args);
      this.off(event, onceHandler);
    };
    
    return this.on(event, onceHandler);
  }
  
  /**
   * 取消订阅事件
   * 
   * @param event 事件名称
   * @param handler 要取消的事件处理器，不提供则移除所有该事件的监听器
   */
  public off(event: string, handler?: EventHandler): void {
    if (!handler) {
      this.events.delete(event);
      return;
    }

    const handlers = this.events.get(event);
    if (handlers) {
      const index = handlers.indexOf(handler);
      if (index !== -1) {
        handlers.splice(index, 1);
      }
      
      if (handlers.length === 0) {
        this.events.delete(event);
      }
    }
  }
  
  /**
   * 触发事件
   * 
   * @param event 事件名称
   * @param args 传递给事件处理函数的参数
   */
  public emit(event: string, ...args: any[]): void {
    const handlers = this.events.get(event);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(...args);
        } catch (error) {
          console.error(`事件处理器执行错误 [${event}]:`, error);
        }
      });
    }
  }
  
  /**
   * 清除所有事件监听
   */
  public clear(): void {
    this.events.clear();
  }
  
  /**
   * 清除指定事件的所有监听
   * 
   * @param event 事件名称
   */
  public clearEvent(event: string): void {
    if (this.events.has(event)) {
      this.events.delete(event);
    }
  }
}

/**
 * 预定义事件常量
 */
export const MCP_EVENTS = {
  MESSAGE_CREATED: 'mcp-message-created',
  MESSAGE_UPDATED: 'mcp-message-updated',
  CONVERSATION_COMPLETE: 'mcp-conversation-complete',
  CONVERSATION_STOPPED: 'mcp-conversation-stopped',
  SANDBOX_FILES_UPDATED: 'sandbox-files-updated'
};

/**
 * 音频相关事件
 */
export const AUDIO_EVENTS = {
  STOP_ASR: 'audio-stop-asr',
  STOP_TTS: 'audio-stop-tts'
};

/**
 * 默认事件总线实例
 * 兼容原有的 eventBus 导出
 */
export const eventBus = EventBus.getInstance();

/**
 * 默认导出，保持向后兼容
 */
export default EventBus.getInstance();
