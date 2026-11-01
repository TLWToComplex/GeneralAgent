<template>
  <div class="account-container">
    <!-- 使用ChatHeader组件 -->
    <ChatHeader 
      v-model:showModelSelector="showModelSelector"
      v-model:isAgentMode="isAgentMode"
    />

    <!-- 左侧菜单栏和内容区域 -->
    <div class="main-content">
      <div class="left-sidebar">
        <div class="sidebar-menu">
          <a-menu
            mode="inline"
            :selected-keys="[currentRoute]"
            style="margin-top: 4px; border-inline-end: 1px solid rgb(5 5 5 / 0%);"
          >
            <a-menu-item key="profile" @click="goToProfile">
              <template #icon>
                <UserOutlined />
              </template>
              <span>个人资料</span>
            </a-menu-item>
            <a-menu-item key="security" @click="goToSecurity">
              <template #icon>
                <LockOutlined />
              </template>
              <span>账户安全</span>
            </a-menu-item>
          </a-menu>
        </div>
      </div>
      
      <!-- 内容区域 -->
      <div class="content-area">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue';
import ChatHeader from '@/components/layout/ChatHeader.vue';

defineOptions({
  name: 'AccountView'
});

const router = useRouter();
const route = useRoute();

// 添加Header相关的状态
const showModelSelector = ref(false);
const isAgentMode = ref(true); // 设置为true以隐藏模型选择按钮

// 计算当前路由的key
const currentRoute = computed(() => {
  const path = route.path;
  if (path.includes('profile')) return 'profile';
  if (path.includes('security')) return 'security';
  return 'profile'; // 默认选中个人资料
});

// 导航到个人资料页面
const goToProfile = () => {
  router.push('/account/profile');
};

// 导航到安全页面
const goToSecurity = () => {
  router.push('/account/security');
};
</script>

<style scoped>
.account-container {
  display: flex;
  height: 100%;
  background-color: #ffffff;
  overflow: hidden;
  flex-direction: column;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.left-sidebar {
  width: 180px;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  height: 100%;
  overflow-y: auto;
}

.sidebar-menu {
  flex: 1;
  overflow-y: auto;
}

:deep(.ant-menu-item) {
  height: 40px;
  line-height: 40px;
}

.content-area {
  flex: 1;
  height: 100%;
  overflow: hidden;
}

/* 覆盖Header样式以适应账户界面 */
:deep(.chat-header) {
  margin-top: 0 !important;
  padding: 0 24px !important;
  border-bottom: 1px solid #f0f0f0;
  display: flex !important;
  flex-direction: row !important;
  justify-content: space-between !important;
}
</style>