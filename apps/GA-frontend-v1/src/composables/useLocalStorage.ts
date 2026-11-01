import { ref, watch } from 'vue';
import { getStorageItem, setStorageItem } from '@/utils/storage';

/**
 * 本地存储组合式函数
 * 提供响应式的本地存储数据
 * 
 * @param key 存储键名
 * @param defaultValue 默认值
 * @returns 响应式数据和更新函数
 */
export function useLocalStorage<T>(key: string, defaultValue: T) {
  // 创建响应式引用，初始值从localStorage获取
  const storedValue = ref<T>(getStorageItem<T>(key, defaultValue));
  
  /**
   * 更新存储的值
   * @param value 新值
   */
  const updateValue = (value: T) => {
    storedValue.value = value;
    setStorageItem(key, value);
  };
  
  // 监听值变化，自动更新到localStorage
  watch(storedValue, (newValue) => {
    setStorageItem(key, newValue);
  }, { deep: true });
  
  return {
    value: storedValue,
    updateValue
  };
} 