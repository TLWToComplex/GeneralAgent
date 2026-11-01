<template>
  <div class="notification-handler"></div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';
import EventBus from '@/utils/EventBus';
import { NOTIFICATION_EVENTS, type NotificationData, NotificationType } from '@/utils/NotificationService';

// 消息持续时间（毫秒）
const DEFAULT_DURATION = 3;

// 处理通知事件
const handleNotification = (data: NotificationData) => {
  if (!data) return;
  
  // 关闭通知
  if (data.type === NotificationType.CLOSE && data.key) {
    message.destroy(data.key);
    return;
  }

  const duration = data.duration !== undefined ? data.duration : DEFAULT_DURATION;
  
  switch (data.type) {
    case NotificationType.SUCCESS:
      message.success(data.message);
      break;
    case NotificationType.ERROR:
      message.error(data.message);
      break;
    case NotificationType.WARNING:
      message.warning(data.message);
      break;
    case NotificationType.INFO:
      message.info(data.message);
      break;
    case NotificationType.LOADING:
      return message.loading({
        content: data.message,
        duration,
        key: data.key
      });
  }
};

// 注册和清理事件监听
let unsubscribe: (() => void) | null = null;

onMounted(() => {
  unsubscribe = EventBus.on(NOTIFICATION_EVENTS.SHOW, handleNotification);
});

onUnmounted(() => {
  if (unsubscribe) {
    unsubscribe();
  }
});
</script>

<style scoped>
.notification-handler {
  display: none;
}
</style> 