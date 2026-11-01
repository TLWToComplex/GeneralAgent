import { ref, watch, onUnmounted } from 'vue';
import type { ThemeMode } from '@/types';
import { getThemeMode, setThemeMode } from '@/config/theme';

/**
 * 主题组合式函数
 * 提供主题切换功能
 * 
 * @returns 主题相关的响应式数据和方法
 */
export function useTheme() {
  // 当前主题模式
  const themeMode = ref<ThemeMode>(getThemeMode());
  
  // 是否为暗色模式
  const isDarkMode = ref(themeMode.value === 'dark' || 
    (themeMode.value === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches));
  
  // 监听系统主题变化
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
  
  // 更新主题模式
  const updateThemeMode = (mode: ThemeMode) => {
    themeMode.value = mode;
    setThemeMode(mode);
    
    // 更新暗色模式状态
    isDarkMode.value = mode === 'dark' || 
      (mode === 'system' && mediaQuery.matches);
  };
  
  // 切换主题模式
  const toggleTheme = () => {
    const newMode: ThemeMode = isDarkMode.value ? 'light' : 'dark';
    updateThemeMode(newMode);
  };
  
  // 监听系统主题变化
  const handleSystemThemeChange = (e: MediaQueryListEvent) => {
    if (themeMode.value === 'system') {
      isDarkMode.value = e.matches;
    }
  };
  
  // 添加系统主题变化监听器
  mediaQuery.addEventListener('change', handleSystemThemeChange);
  
  // 组件卸载时移除监听器
  onUnmounted(() => {
    mediaQuery.removeEventListener('change', handleSystemThemeChange);
  });
  
  // 监听主题模式变化
  watch(themeMode, (newMode) => {
    setThemeMode(newMode);
  });
  
  return {
    themeMode,
    isDarkMode,
    updateThemeMode,
    toggleTheme
  };
} 