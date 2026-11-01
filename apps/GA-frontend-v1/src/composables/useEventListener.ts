import { onMounted, onUnmounted } from 'vue';

/**
 * 事件监听组合式函数
 * 自动在组件挂载时添加事件监听，卸载时移除
 * 
 * @param target 事件目标（DOM元素、window、document等）
 * @param event 事件名称
 * @param handler 事件处理函数
 * @param options 事件选项
 */
export function useEventListener(
  target: EventTarget,
  event: string,
  handler: EventListenerOrEventListenerObject,
  options?: boolean | AddEventListenerOptions
) {
  // 组件挂载时添加事件监听
  onMounted(() => {
    target.addEventListener(event, handler, options);
  });
  
  // 组件卸载时移除事件监听
  onUnmounted(() => {
    target.removeEventListener(event, handler, options);
  });
} 