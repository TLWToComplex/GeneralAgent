/**
 * 本地存储工具函数
 */

/**
 * 从localStorage获取数据
 * @param key 存储键名
 * @param defaultValue 默认值
 * @returns 解析后的数据或默认值
 */
export function getStorageItem<T>(key: string, defaultValue: T): T {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error(`读取本地存储失败 [${key}]:`, error);
    return defaultValue;
  }
}

/**
 * 保存数据到localStorage
 * @param key 存储键名
 * @param value 要存储的数据
 */
export function setStorageItem<T>(key: string, value: T): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error(`保存到本地存储失败 [${key}]:`, error);
  }
}

/**
 * 从localStorage删除数据
 * @param key 存储键名
 */
export function removeStorageItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch (error) {
    console.error(`从本地存储删除失败 [${key}]:`, error);
  }
}

/**
 * 清空所有localStorage数据
 */
export function clearStorage(): void {
  try {
    localStorage.clear();
  } catch (error) {
    console.error('清空本地存储失败:', error);
  }
} 