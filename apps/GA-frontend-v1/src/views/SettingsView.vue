<template>
  <div class="settings-container">
    <!-- 添加ChatHeader组件 -->
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
            <a-menu-item key="chat-preferences" @click="goToChatPreferences">
              <template #icon><MessageOutlined /></template>
              <span>聊天偏好</span>
            </a-menu-item>
            <a-menu-item key="knowledge-base" @click="goToKnowledgeBase">
              <template #icon><DatabaseOutlined /></template>
              <span>知识库</span>
            </a-menu-item>
            <a-menu-item key="role-settings" @click="goToRoleSettings">
              <template #icon><TeamOutlined /></template>
              <span>角色设置</span>
            </a-menu-item>
            <a-menu-item key="rule-skill-settings" @click="goToRuleSkillSettings">
              <template #icon><AuditOutlined /></template>
              <span>技能</span>
            </a-menu-item>
            <a-menu-item v-if="isCurrentUserAdmin" key="user-management" @click="goToUserManagement">
              <template #icon><UserOutlined /></template>
              <span>用户管理</span>
            </a-menu-item>
            <a-menu-item key="model-service" @click="goToModelService">
              <template #icon><CloudOutlined /></template>
              <span>模型服务</span>
            </a-menu-item>
            <a-menu-item key="mcp-server" @click="goToMcpServer">
              <template #icon><CodeOutlined /></template>
              <span>MCP服务器</span>
            </a-menu-item>
          </a-menu>
        </div>
        <div class="sidebar-version">
          <div class="ver-app">{{ APP_NAME }}</div>
          <div class="ver-num">应用版本: v{{ appVersion }}</div>
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
import { CloudOutlined, CodeOutlined, MessageOutlined, TeamOutlined, DatabaseOutlined, AuditOutlined, UserOutlined } from '@ant-design/icons-vue';
import ChatHeader from '@/components/layout/ChatHeader.vue';
import { ROUTES, APP_NAME } from '@/config';
import { getAppVersion } from '@/utils/RuntimeConfig';

// 定义组件名以便keep-alive能够识别
defineOptions({
  name: 'SettingsView'
});

// 添加Header相关的状态和方法
const showModelSelector = ref(false);
const isAgentMode = ref(true); // 设置为true以隐藏模型选择按钮

const router = useRouter();
const route = useRoute();

const appVersion = getAppVersion();

// 计算当前路由的key
const currentRoute = computed(() => {
  const path = route.path;
  if (path.includes('knowledge-base')) return 'knowledge-base';
  if (path.includes('role-settings')) return 'role-settings';
  if (path.includes('rule-skill-settings')) return 'rule-skill-settings';
  if (path.includes('user-management')) return 'user-management';
  if (path.includes('model-service')) return 'model-service';
  if (path.includes('mcp-server')) return 'mcp-server';
  if (path.includes('chat-preferences')) return 'chat-preferences';
  return '';
});

const isCurrentUserAdmin = computed(() => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) return false;
    const profile = JSON.parse(raw);
    return String(profile?.username || '').trim().toLowerCase() === 'admin';
  } catch {
    return false;
  }
});

// 导航到知识库页面
const goToKnowledgeBase = () => {
  router.push(ROUTES.KNOWLEDGE_BASE);
};

// 导航到模型服务页面
const goToModelService = () => {
  router.push(ROUTES.MODEL_SERVICE);
};

// 导航到MCP服务器页面
const goToMcpServer = () => {
  router.push(ROUTES.MCP_SERVER);
};

// 导航到聊天偏好页面
const goToChatPreferences = () => {
  router.push(ROUTES.CHAT_PREFERENCES);
};

// 导航到角色设置页面
const goToRoleSettings = () => {
  router.push(ROUTES.ROLE_SETTINGS);
};

const goToRuleSkillSettings = () => {
  router.push(ROUTES.RULE_SKILL_SETTINGS);
};

const goToUserManagement = () => {
  router.push(ROUTES.USER_MANAGEMENT);
};

// ChatHeader 的事件由其内部处理，这里不再监听或实现空方法
</script>

<style scoped>
.settings-container {
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

.sidebar-version {
  flex-shrink: 0;
  padding: 12px 16px;
  text-align: center;
  user-select: none;
}

.ver-app {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  line-height: 1.4;
}

.ver-num {
  margin-top: 4px;
  font-size: 12px;
  color: #9aa4b2;
  line-height: 1.4;
  letter-spacing: .5px;
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

/* 覆盖Header样式以适应设置界面 */
:deep(.chat-header) {
  margin-top: 0 !important;
  padding: 0 24px !important;
  border-bottom: 1px solid #f0f0f0;
  display: flex !important;
  flex-direction: row !important;
  justify-content: space-between !important;
}
</style>
