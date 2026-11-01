<template>
  <!-- 第一步：欢迎页面 -->
  <div class="step-content welcome-step" style="margin-top: -15vh;">
    <!-- Logo 区域 -->
    <div class="logo-section" :class="{ 'animate': showContent }">
      <div class="logo-image-container">
        <img :src="logoImage" alt="Logo" class="logo-image" :class="{ loaded: imageLoaded }" />
      </div>
      <span class="app-name">{{ systemName }}</span>
    </div>
    <p class="subtitle" :class="{ 'animate': showContent, 'leaving': isTransitioning && !showContent }">
      企业级智能体平台
    </p>

    <!-- 按钮区域 -->
    <div class="action-section" :class="{ 'animate': showContent }">
      <a-button type="primary" size="middle" class="start-button" @click="handleStart" shape="round">
        <RightOutlined />
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { getSystemName } from '@/utils/RuntimeConfig';
import { RightOutlined } from '@ant-design/icons-vue';

const { showContent, isTransitioning, imageLoaded, logoImage } = defineProps<{ 
  showContent: boolean;
  isTransitioning: boolean;
  imageLoaded: boolean;
  logoImage: string;
}>();

const emit = defineEmits<{ (e: 'start'): void }>();

function handleStart() {
  emit('start');
}

// 计算属性获取系统名称
const systemName = computed(() => {
  return getSystemName();
});
</script>

<style scoped>
@import '@/assets/styles/welcome.css';

/* 欢迎页 Logo 预加载淡入效果 */
.logo-image {
  opacity: 0;
  transition: opacity 0.3s ease;
}

.logo-image.loaded {
  opacity: 1;
}
</style>
