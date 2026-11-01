// src/utils/NotificationService.ts

import EventBus from './EventBus';

/**
 * 通知类型枚举
 */
export enum NotificationType {
  SUCCESS = 'success',
  ERROR = 'error',
  WARNING = 'warning',
  INFO = 'info',
  LOADING = 'loading',
  CLOSE = 'close'
}

/**
 * 通知事件名称
 */
export const NOTIFICATION_EVENTS = {
  SHOW: 'notification-show',
};

/**
 * 通知数据接口
 */
export interface NotificationData {
  type: NotificationType;
  message: string;
  duration?: number;
  key?: string; // 用于标识需要关闭的通知
}

/**
 * 通知服务类
 * 提供统一的通知接口，解耦UI通知和业务逻辑
 */
export class NotificationService {
  private static instance: NotificationService;

  private constructor() {}

  /**
   * 获取单例实例
   */
  public static getInstance(): NotificationService {
    if (!NotificationService.instance) {
      NotificationService.instance = new NotificationService();
    }
    return NotificationService.instance;
  }

  /**
   * 显示成功通知
   * @param message 通知内容
   */
  public success(message: string): void {
    EventBus.emit(NOTIFICATION_EVENTS.SHOW, {
      type: NotificationType.SUCCESS,
      message
    });
  }

  /**
   * 显示错误通知
   * @param message 通知内容
   */
  public error(message: string): void {
    EventBus.emit(NOTIFICATION_EVENTS.SHOW, {
      type: NotificationType.ERROR,
      message
    });
  }

  /**
   * 显示警告通知
   * @param message 通知内容
   */
  public warning(message: string): void {
    EventBus.emit(NOTIFICATION_EVENTS.SHOW, {
      type: NotificationType.WARNING,
      message
    });
  }

  /**
   * 显示信息通知
   * @param message 通知内容
   */
  public info(message: string): void {
    EventBus.emit(NOTIFICATION_EVENTS.SHOW, {
      type: NotificationType.INFO,
      message
    });
  }

  /**
   * 显示加载通知
   * @param message 通知内容
   * @param duration 持续时间，0表示不自动关闭
   * @returns 加载通知的key，可用于手动关闭
   */
  public loading(message: string, duration: number = 0): string {
    const key = `loading-${Date.now()}`;
    EventBus.emit(NOTIFICATION_EVENTS.SHOW, {
      type: NotificationType.LOADING,
      message,
      duration,
      key
    });
    return key;
  }

  /**
   * 关闭指定的通知
   * @param key 通知的key
   */
  public close(key: string): void {
    EventBus.emit(NOTIFICATION_EVENTS.SHOW, {
      type: NotificationType.CLOSE,
      message: '',
      key
    });
  }
}

// 导出默认实例
export default NotificationService.getInstance(); 