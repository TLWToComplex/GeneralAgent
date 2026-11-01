/**
 * 主题配置文件
 * 集中管理主题相关配置
 */
import type { ThemeMode } from '@/types';
import { getStorageItem, setStorageItem } from '@/utils/storage';

// 本地存储键名
const THEME_MODE_KEY = 'mcp-theme-mode';

// 默认主题模式
const DEFAULT_THEME_MODE: ThemeMode = 'light';

/**
 * 获取当前主题模式
 * @returns 当前主题模式
 */
export const getThemeMode = (): ThemeMode => {
  return getStorageItem<ThemeMode>(THEME_MODE_KEY, DEFAULT_THEME_MODE);
};

/**
 * 设置主题模式
 * @param mode 主题模式
 */
export const setThemeMode = (mode: ThemeMode): void => {
  setStorageItem(THEME_MODE_KEY, mode);
  applyThemeMode(mode);
};

/**
 * 应用主题模式到文档
 * @param mode 主题模式
 */
export const applyThemeMode = (mode: ThemeMode): void => {
  // 如果是系统主题，则根据系统偏好设置
  const effectiveMode = mode === 'system' 
    ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
    : mode;
  
  // 设置文档根元素的data-theme属性
  document.documentElement.setAttribute('data-theme', effectiveMode);
  
  // 设置body类名
  if (effectiveMode === 'dark') {
    document.body.classList.add('dark-theme');
    document.body.classList.remove('light-theme');
  } else {
    document.body.classList.add('light-theme');
    document.body.classList.remove('dark-theme');
  }
};

/**
 * 初始化主题
 */
export const initTheme = (): void => {
  const mode = getThemeMode();
  applyThemeMode(mode);
  
  // 监听系统主题变化
  if (mode === 'system') {
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
      applyThemeMode('system');
    });
  }
}; 