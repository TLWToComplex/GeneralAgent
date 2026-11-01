/**
 * 工具函数索引文件
 * 统一导出所有工具函数
 */

// 导出HTTP工具
export * from './http';

// 导出存储工具
export * from './storage';

// 导出事件总线
export * from './EventBus';

/**
 * 生成唯一ID
 * @returns 唯一ID字符串
 */
export const generateId = (): string => {
  return Date.now().toString(36) + Math.random().toString(36).substring(2);
};

/**
 * 格式化日期时间
 * @param timestamp 时间戳
 * @param format 格式化模板，默认为 'YYYY-MM-DD HH:mm:ss'
 * @returns 格式化后的日期时间字符串
 */
export const formatDateTime = (timestamp: number, format = 'YYYY-MM-DD HH:mm:ss'): string => {
  const date = new Date(timestamp);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  const seconds = String(date.getSeconds()).padStart(2, '0');
  
  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
};

/**
 * 防抖函数
 * @param fn 要执行的函数
 * @param delay 延迟时间(毫秒)
 * @returns 防抖处理后的函数
 */
export const debounce = <T extends (...args: any[]) => any>(fn: T, delay: number): ((...args: Parameters<T>) => void) => {
  let timer: number | null = null;
  
  return function(this: any, ...args: Parameters<T>) {
    if (timer) {
      clearTimeout(timer);
    }
    
    timer = window.setTimeout(() => {
      fn.apply(this, args);
      timer = null;
    }, delay);
  };
};

/**
 * 节流函数
 * @param fn 要执行的函数
 * @param limit 时间限制(毫秒)
 * @returns 节流处理后的函数
 */
export const throttle = <T extends (...args: any[]) => any>(fn: T, limit: number): ((...args: Parameters<T>) => void) => {
  let inThrottle = false;
  
  return function(this: any, ...args: Parameters<T>) {
    if (!inThrottle) {
      fn.apply(this, args);
      inThrottle = true;
      
      setTimeout(() => {
        inThrottle = false;
      }, limit);
    }
  };
}; 