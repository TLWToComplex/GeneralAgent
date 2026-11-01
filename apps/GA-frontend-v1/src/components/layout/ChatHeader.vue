<template>
  <div class="chat-header">
    <div class="header-left">
      <slot name="navigation">
      <!-- 返回按钮，仅在设置页面或账户页面显示 -->
      <div class="back-btn-container" v-if="showBackButton">
        <a-button
            type="text"
            class="back-btn"
            @click="handleBackClick"
        >
          <LeftOutlined/>
        </a-button>
        <span v-if="isSettingsPage">应用设置</span>
        <span v-else-if="isAccountPage">账户管理</span>
      </div>

      <!-- 共用同一网格位置交叉淡入淡出，切换工作区时保持按钮高度稳定。 -->
      <div v-if="!isSettingsPage && !isAccountPage" class="header-primary-action">
        <transition name="model-select-fade">
          <a-button
              v-if="activeWorkspace !== 'chat'"
              type="text"
              class="knowledge-new-chat-btn"
              @click="emit('new-chat')"
              key="knowledge-new-chat-button"
          >
            <div class="knowledge-new-chat-content">
              <div class="knowledge-new-chat-icon" aria-hidden="true">
                <img :src="knowledgeNewChatIcon" alt="" />
              </div>
              <span class="knowledge-new-chat-label">新对话</span>
            </div>
          </a-button>
          <a-button
              v-else-if="!isAgentMode"
              type="text"
              class="model-select-btn"
              @click="showModelSelector = true"
              key="model-select-button"
          >
            <div class="model-selection">
              <div class="model-icon" v-if="currentModel" :style="{ backgroundColor: (shouldShowIcon(currentModelName, 'qwen') || shouldShowIcon(currentModelName, 'deepseek') || shouldShowIcon(currentModelName, 'glm')) ? 'transparent' : (currentModelObj ? getModelColor(currentModelObj) : '#1890ff') }">
                <QwenIcon v-if="shouldShowIcon(currentModelName, 'qwen')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                <DeepSeekIcon v-else-if="shouldShowIcon(currentModelName, 'deepseek')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                <ZaiIcon v-else-if="shouldShowIcon(currentModelName, 'glm') && currentModelName.toLowerCase().includes('z')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                <ZhipuIcon v-else-if="shouldShowIcon(currentModelName, 'glm')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                <span v-else>{{ currentModelName ? currentModelName.charAt(0).toUpperCase() : 'M' }}</span>
              </div>
              <span class="model-select-name" :title="currentModelName">{{ currentModelName || '选择模型' }}</span>
              <DownOutlined/>
            </div>
          </a-button>
          <a-button
              v-else
              type="text"
              class="model-select-btn agent-select-btn"
              @click="handleAgentSelectClick"
              key="agent-select-button"
          >
            <div class="model-selection">
              <div class="model-icon" :class="{ 'with-image': currentAgentAvatar }" v-if="currentAgentName" :style="{ backgroundColor: currentAgentAvatar ? 'transparent' : (activeAgentConfig?.basic?.themeColor || '#1890ff') }">
                <img v-if="currentAgentAvatar" :src="currentAgentAvatar" class="model-icon-image" alt=""/>
                <span v-else>{{ currentAgentName ? currentAgentName.charAt(0).toUpperCase() : 'A' }}</span>
              </div>
              <span class="model-select-name" :title="currentAgentName">{{ currentAgentName || '选择智能体' }}</span>
              <transition name="agent-arrow-toggle" mode="out-in">
                <MenuIcon class="agent-arrow" key="icon-menu" />
              </transition>
            </div>
          </a-button>
        </transition>
      </div>
      </slot>
    </div>

    <div class="header-center">
      <span class="security-notice">- 内部系统禁止上传处理涉密信息 -</span>
    </div>

    <div class="header-right">
      <!-- 用户头像和下拉菜单 -->
      <a-dropdown :trigger="['click']">
        <a-avatar 
          class="user-avatar" 
          :size="35"
          :src="userAvatar"
          :style="userAvatarStyle"
        >
          <template v-if="!userAvatar">{{ userInitial }}</template>
        </a-avatar>
        <template #overlay>
          <a-menu class="user-menu">
            <a-menu-item key="userInfo" class="user-info-noninteractive" @click.stop>
              <div class="user-info-menu-item">
                <a-avatar :size="40" :src="userAvatar" :style="userAvatarStyle">
                  <template v-if="!userAvatar">{{ userInitial }}</template>
                </a-avatar>
                <div class="user-details">
                  <div class="user-name">{{ userName }}</div>
                  <div v-if="userGroupLoading" class="user-groups-hint">正在加载用户组...</div>
                  <div v-else-if="userGroups.length" class="user-groups" :title="userGroupNames">
                    {{ userGroupNames }}
                  </div>
                  <div v-else class="user-groups-hint">未分配用户组</div>
                </div>
              </div>
            </a-menu-item>
            <a-menu-divider />
            <a-menu-item key="account" @click="goToAccount">
              <div class="menu-item-content">
                <UserOutlined />
                <span>账户管理</span>
              </div>
            </a-menu-item>
            <a-menu-item key="settings" @click="goToSettings">
              <div class="menu-item-content">
                <SettingOutlined />
                <span>应用设置</span>
              </div>
            </a-menu-item>
            <a-menu-item key="logout" @click="handleLogout">
              <div class="menu-item-content">
                <LogoutOutlined />
                <span>退出登录</span>
              </div>
            </a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>

    <!-- 画布 / 交付中心 Tab：对齐右侧 Canvas 面板“预览/编辑”正上方 -->
    <div v-if="showPanelTabs" class="panel-tabs-anchor">
      <PanelTabs
        :active="activePanel"
        @switch="handlePanelSwitch"
      />
    </div>
  </div>

  <!-- 模型选择模态窗口 -->
  <a-modal
      v-model:open="showModelSelector"
      title="选择模型"
      :footer="null"
      width="638px"
      :maskClosable="false"
      :closable="true"
      :destroyOnClose="false"
      centered
      class="model-selector-modal"
      @cancel="handleModelSelectorCancel"
  >
    <template v-if="Object.keys(modelGroups).length > 0">
      <div class="model-search">
        <div class="custom-search-wrapper">
          <SearchOutlined class="search-icon" />
          <input
            v-model="modelSearchText"
            placeholder="搜索模型..."
            class="custom-input"
          />
        </div>
      </div>

      <div class="model-categories" ref="modelCategoriesRef" @scroll="handleScroll" :class="scrollMaskClass">
        <template v-if="modelSearchText">
          <!-- 搜索结果 -->
          <div class="category">
            <div class="category-title">搜索结果</div>
            <div class="model-list">
              <div
                  v-for="model in filteredModels"
                  :key="buildModelSelectionKey(model)"
                  class="model-item"
                  :class="{ 'selected': isCurrentModel(model) }"
                  @click="selectModel(model)"
              >
                <div class="model-icon" :style="{ backgroundColor: (shouldShowIcon(model.name, 'qwen') || shouldShowIcon(model.name, 'deepseek') || shouldShowIcon(model.name, 'glm')) ? 'transparent' : getModelColor(model) }">
                   <QwenIcon v-if="shouldShowIcon(model.name, 'qwen')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <DeepSeekIcon v-else-if="shouldShowIcon(model.name, 'deepseek')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <ZaiIcon v-else-if="shouldShowIcon(model.name, 'glm') && model.name.toLowerCase().includes('z')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <ZhipuIcon v-else-if="shouldShowIcon(model.name, 'glm')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <span v-else>{{ model.iconText.charAt(0).toUpperCase() }}</span>
                 </div>
                <div class="model-info">
                  <div class="model-name" :title="model.name">{{ model.name }}</div>
                  <div class="model-meta">
                    <span class="model-provider-text" v-if="model.serviceProvider">{{ model.serviceProvider }}</span>
                    <span
                      v-for="type in (model.types || [])"
                      :key="type"
                      class="model-type-tag"
                      :class="type"
                    >
                      {{ getModelTypeLabel(type) }}
                    </span>
                    <span v-if="model.contextSize" class="model-type-tag context-size-tag">
                      {{ formatContextSize(model.contextSize) }}
                    </span>
                  </div>
                </div>
                <div class="model-select-indicator" v-if="isCurrentModel(model)">
                  <CheckOutlined/>
                </div>
              </div>
            </div>
          </div>
        </template>
        <template v-else>
          <!-- 按提供商分组 -->
          <div v-for="provider in orderedProviders" :key="provider" class="category">
            <div class="category-title">{{ provider }}</div>
            <div class="model-list">
              <div
                  v-for="model in modelGroups[provider]"
                  :key="buildModelSelectionKey(model)"
                  class="model-item"
                  :class="{ 'selected': isCurrentModel(model) }"
                  @click="selectModel(model)"
              >
                <div class="model-icon" :style="{ backgroundColor: (shouldShowIcon(model.name, 'qwen') || shouldShowIcon(model.name, 'deepseek') || shouldShowIcon(model.name, 'glm')) ? 'transparent' : getModelColor(model) }">
                   <QwenIcon v-if="shouldShowIcon(model.name, 'qwen')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <DeepSeekIcon v-else-if="shouldShowIcon(model.name, 'deepseek')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <ZaiIcon v-else-if="shouldShowIcon(model.name, 'glm') && model.name.toLowerCase().includes('z')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <ZhipuIcon v-else-if="shouldShowIcon(model.name, 'glm')" class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                   <span v-else>{{ model.iconText.charAt(0).toUpperCase() }}</span>
                 </div>
                <div class="model-info">
                  <div class="model-name" :title="model.name">{{ model.name }}</div>
                  <div class="model-meta">
                    <span
                      v-for="type in (model.types || [])"
                      :key="type"
                      class="model-type-tag"
                      :class="type"
                    >
                      {{ getModelTypeLabel(type) }}
                    </span>
                    <span v-if="model.contextSize" class="model-type-tag context-size-tag">
                      {{ formatContextSize(model.contextSize) }}
                    </span>
                  </div>
                </div>
                <div class="model-select-indicator" v-if="isCurrentModel(model)">
                  <CheckOutlined/>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </template>
    <div v-else class="empty-models">
      <p>未配置任何模型，请前往「设置」页面添加模型服务</p>
      <a-button type="primary" @click="goToSettings">前往设置</a-button>
    </div>

    <div class="model-selector-footer">
      <a class="model-service-link" @click="goToModelService">模型服务管理</a>
      <div class="model-selector-buttons">
        <button @click="cancelModelSelection" class="model-cancel-button">取消</button>
        <button @click="confirmModelSelection" :disabled="!currentModel" class="model-confirm-button">确定</button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import {ref, onMounted, computed, watch, onUnmounted, nextTick} from 'vue';
import {useChatStore} from '@/stores/chat-store';
import {SettingOutlined, DownOutlined, CheckOutlined, LeftOutlined, UserOutlined, LogoutOutlined, SearchOutlined} from '@ant-design/icons-vue';
import {useRouter, useRoute} from 'vue-router';
import NotificationService from '@/utils/NotificationService';
import StorageService from '@/utils/StorageService';
import { resolveAgentAvatar } from '@/utils/agentAvatar';
import MenuIcon from '@/components/icons/MenuIcon.vue';
import knowledgeNewChatIcon from '@/assets/image/svg/new_chat_nav.svg';
import PanelTabs from '@/components/chat/PanelTabs.vue';
import QwenIcon from '@/components/icons/llm/qwen.vue';
import DeepSeekIcon from '@/components/icons/llm/deepseek.vue';
import ZhipuIcon from '@/components/icons/llm/zhipu.vue';
import ZaiIcon from '@/components/icons/llm/zai.vue';
import bgPoster from '@/assets/image/jpg/background.jpg';
import { listPlatformModels } from '@/services/aiPlatformModel';
import { MODEL_TYPE_OPTIONS, formatContextSize } from '@/components/model-service/types';
import { shouldShowModelIcon } from '@/utils/modelIcon';
import { getAiUserRecord, type UserGroupInfo } from '@/services/aiUser';
import { broadcastGlobalLogout } from '@/utils/TabScopeService';
import { ROUTES } from '@/config/constants';

// 模型类型标签映射
const getModelTypeLabel = (typeValue: string) => {
  const option = MODEL_TYPE_OPTIONS.find(opt => opt.value === typeValue);
  return option ? option.label : typeValue;
};

// 定义组件名称
defineOptions({
  name: 'ChatHeader'
});

// 定义组件的 emits
const emit = defineEmits<{
  (e: 'update:model', modelId: string): void;
  (e: 'navigate-to-settings'): void;
  (e: 'navigate-to-chat'): void;
  (e: 'model-selector-open', isOpen: boolean): void;
  (e: 'switch-panel', mode: 'canvas' | 'deliverables'): void;
  (e: 'new-chat'): void;
}>();

// 右侧面板（画布 / 交付中心）Tab 切换
withDefaults(defineProps<{
  activePanel?: 'canvas' | 'deliverables';
  showPanelTabs?: boolean;
  activeWorkspace?: 'chat' | 'knowledge' | 'delivery' | 'agents';
}>(), {
  activePanel: 'canvas',
  showPanelTabs: false,
  activeWorkspace: 'chat',
});

const handlePanelSwitch = (mode: 'canvas' | 'deliverables') => {
  emit('switch-panel', mode);
};

// 使用 chatStore
const chatStore = useChatStore();

// 获取路由实例
const router = useRouter();
const route = useRoute();

// 模型选择相关状态
const showModelSelector = defineModel<boolean>('showModelSelector', {default: false});
const modelSearchText = ref('');
const currentModel = ref('');
const currentModelService = ref('');
const selectedModel = ref<any>(null);
const previousModel = ref(''); // 保存打开模态窗口前的模型选择
const previousModelService = ref('');

// 滚动渐变效果相关
const modelCategoriesRef = ref<HTMLElement | null>(null);
const scrollMaskClass = ref('');

const checkScrollMask = () => {
  const el = modelCategoriesRef.value;
  if (!el) return;
  
  const { scrollTop, scrollHeight, clientHeight } = el;
  // 容差值，避免计算误差
  const tolerance = 1;
  const isTop = scrollTop <= tolerance;
  const isBottom = Math.abs(scrollHeight - clientHeight - scrollTop) <= tolerance;
  
  if (scrollHeight <= clientHeight) {
    scrollMaskClass.value = '';
    return;
  }
  
  if (isTop && isBottom) scrollMaskClass.value = '';
  else if (isTop) scrollMaskClass.value = 'mask-bottom';
  else if (isBottom) scrollMaskClass.value = 'mask-top';
  else scrollMaskClass.value = 'mask-both';
};

const handleScroll = () => {
  checkScrollMask();
};

// 监听模态窗口打开，重置滚动状态
watch(showModelSelector, (val) => {
  if (val) {
    nextTick(() => {
      checkScrollMask();
    });
  }
});

// 监听模型数据变化（如搜索），也需要检查
watch(modelSearchText, () => {
  nextTick(() => {
    checkScrollMask();
  });
});

// 添加检测智能体模式的计算属性
const isAgentMode = defineModel<boolean>('isAgentMode', {default: false});

// 活跃智能体配置
const activeAgentConfig = ref<any | null>(null);


// 提供商数据
const providers = ref<any[]>([]);
// 模型数据
const modelsData = ref<Record<string, any>>({});
// 提供商背景颜色映射
const providerColors = ref<Record<string, string>>({});
// 提供商头像映射
const providerAvatars = ref<Record<string, string>>({});

// 用户信息相关
const userAvatar = ref<string>('');
const userInitial = ref<string>('U');
const userName = ref<string>('用户');
const userEmail = ref<string>('user@example.com');
const userAvatarBg = ref<string>('#1890ff');
const userAvatarTextColor = ref<string>('#ffffff');
const userUuid = ref<string>('');
const userGroupLoading = ref(false);
const userGroups = ref<UserGroupInfo[]>([]);

const userGroupNames = computed(() => userGroups.value.map(group => group.group_name).join(' / '));

// 从localStorage加载用户信息
const loadUserInfo = () => {
  try {
    const profileData = localStorage.getItem('user-profile');
    if (profileData) {
      const profile = JSON.parse(profileData);
      userUuid.value = (profile.uuid || '').trim();
      userName.value = profile.username || '用户';
      userEmail.value = profile.email || 'user@example.com';
      const isAllEmpty = !profile.avatar && !profile.avatarBackground && !profile.avatarTextColor;
      userAvatar.value = profile.avatar || (isAllEmpty ? (bgPoster as unknown as string) : '');
      userAvatarBg.value = profile.avatarBackground || (userAvatar.value ? '#ffffff' : '#1890ff');
      userAvatarTextColor.value = profile.avatarTextColor || '#ffffff';
      
      // 计算用户首字母（仅在没有头像时显示）
      if (!userAvatar.value) {
        userInitial.value = userName.value.charAt(0).toUpperCase();
      }
    }
  } catch (e) {
    console.error('加载用户信息失败:', e);
  }
};

const loadUserGroups = async () => {
  const uuid = userUuid.value.trim();
  if (!uuid) {
    userGroups.value = [];
    return;
  }

  userGroupLoading.value = true;
  try {
    const record = await getAiUserRecord({ uuid });
    userGroups.value = record?.groups || [];
  } catch (e) {
    console.error('加载用户组失败:', e);
    userGroups.value = [];
  } finally {
    userGroupLoading.value = false;
  }
};

// 监听用户头像变化，动态设置背景图片
// 判断当前是否为设置页面
const isSettingsPage = computed(() => {
  return route.path.startsWith('/settings');
});

// 判断当前是否为账户页面
const isAccountPage = computed(() => {
  return route.path.startsWith('/account');
});

// 判断是否需要显示返回按钮（设置页面或账户页面）
const showBackButton = computed(() => {
  return isSettingsPage.value || isAccountPage.value;
});

// 头像样式：图片白底，文字使用配置背景与文字颜色
const userAvatarStyle = computed(() => {
  const style: Record<string, string> = {
    backgroundColor: userAvatar.value ? '#ffffff' : (userAvatarBg.value || '#1890ff')
  };
  if (!userAvatar.value) {
    style.color = userAvatarTextColor.value || '#ffffff';
  }
  return style;
});

// 处理返回按钮点击事件
const handleBackClick = () => {
  router.push('/chat');
  emit('navigate-to-chat');
};

// 从本地存储直接加载原始数据
const loadRawData = () => {
  try {
    const providersData = localStorage.getItem('mcp-providers');
    const modelsStorageData = localStorage.getItem('mcp-models');

    if (providersData) {
      providers.value = JSON.parse(providersData);

      // 构建提供商颜色映射和头像映射
      providers.value.forEach(provider => {
        if (provider.name && provider.backgroundColor) {
          providerColors.value[provider.name] = provider.backgroundColor;
        }
        if (provider.name && provider.avatar) {
          providerAvatars.value[provider.name] = provider.avatar;
        }
      });
    }

    if (modelsStorageData) {
      modelsData.value = JSON.parse(modelsStorageData);
    }
  } catch (e) {
    console.error('直接加载本地存储数据失败:', e);
  }
};

// 获取模型颜色
const getModelColor = (model: any) => {
  if (model.serviceProvider && providerColors.value[model.serviceProvider]) {
    return providerColors.value[model.serviceProvider];
  }
  return '#1890ff'; // 默认颜色
};

const normalizeUrl = (url?: string) => (url || '').trim().replace(/^[`\s]+|[`\s]+$/g, '');

const buildModelSelectionKey = (model: any) => `${model.serviceProvider || ''}::${model.id || model.name || ''}`;

const resolveSelectedModel = (modelId = currentModel.value, serviceProvider = currentModelService.value) => {
  if (!modelId) {
    return null;
  }

  if (serviceProvider) {
    const exactMatch = processedModels.value.find(
      m => m.id === modelId && m.serviceProvider === serviceProvider
    );
    if (exactMatch) {
      return exactMatch;
    }
  }

  const candidates = processedModels.value.filter(m => m.id === modelId);
  if (candidates.length <= 1) {
    return candidates[0] || null;
  }

  const persistedConfig = StorageService.getApiConfig();
  const persistedService = (persistedConfig?.service || '').trim();
  if (persistedService) {
    const persistedMatch = candidates.find(m => m.serviceProvider === persistedService);
    if (persistedMatch) {
      return persistedMatch;
    }
  }

  const currentApiBaseUrl = normalizeUrl((chatStore.apiBaseUrl as string) || persistedConfig?.apiBaseUrl);
  if (currentApiBaseUrl) {
    const apiUrlMatch = candidates.find(
      m => normalizeUrl(modelsData.value[m.serviceProvider]?.apiUrl) === currentApiBaseUrl
    );
    if (apiUrlMatch) {
      return apiUrlMatch;
    }
  }

  return candidates[0] || null;
};

const isCurrentModel = (model: any) => {
  const selected = resolveSelectedModel();
  return !!selected &&
    selected.id === model.id &&
    selected.serviceProvider === model.serviceProvider;
};

const normalizeProviderModelGroups = (providerData: any) => {
  if (!providerData?.models) return [] as any[];
  if (Array.isArray(providerData.models)) {
    if (providerData.models.length === 0) return [];
    if (Array.isArray(providerData.models[0]?.models)) {
      return providerData.models;
    }
    return [{
      id: providerData.id || providerData.name || 'default',
      name: providerData.name || providerData.id || 'default',
      models: providerData.models
    }];
  }
  return Array.isArray(providerData.modelsArray) && providerData.modelsArray.length
    ? providerData.modelsArray
    : Object.values(providerData.models);
};

const normalizeApiModelGroups = (item: any) => {
  const rawModels = Array.isArray(item?.models) ? item.models : [];
  if (rawModels.length === 0) return [] as any[];
  if (Array.isArray(rawModels[0]?.models)) {
    return rawModels;
  }
  return [{
    id: item.id || item.name || 'default',
    name: item.name || item.id || 'default',
    models: rawModels
  }];
};

const syncModelDataFromServer = async () => {
  const arr = await listPlatformModels();
  const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
  const newProviders = arr.map((item: any) => ({
    name: item.name,
    iconClass: 'custom',
    iconText: (item.name || 'P').charAt(0).toUpperCase(),
    avatar: item.avatar?.url || '',
    backgroundColor: item.backgroundColor || undefined,
    providerIcon: item.providerIcon
  }));
  const modelsMap: Record<string, any> = {};
  arr.forEach((item: any) => {
    const groupsRecord: Record<string, any> = {};
    const normalizedGroups = normalizeApiModelGroups(item);
    normalizedGroups.forEach((g: any) => {
      groupsRecord[g.id] = {
        id: g.id,
        name: g.name || g.id,
        models: (g.models || []).map((m: any) => ({
          id: m.id,
          name: m.name || m.id,
          iconText: m.iconText || (m.name || 'M').charAt(0).toUpperCase(),
          types: m.types || [],
          contextSize: typeof m.contextSize === 'number'
            ? m.contextSize
            : (typeof m.context_size === 'number' ? m.context_size : undefined)
        }))
      };
    });
    modelsMap[item.name] = {
      apiKey: item.credentials?.apiKey || (item.noApiKeyRequired ? 'sk-no-key' : ''),
      apiUrl: sanitizeUrl(item.connection?.apiBaseUrl),
      models: groupsRecord,
      modelsArray: normalizedGroups,
      avatar: item.avatar?.url || '',
      backgroundColor: item.backgroundColor || undefined,
      noApiKeyRequired: !!item.noApiKeyRequired,
      providerIcon: item.providerIcon,
      type: item.type || 'OpenAI'
    };
  });
  localStorage.setItem('mcp-providers', JSON.stringify(newProviders));
  localStorage.setItem('mcp-models', JSON.stringify(modelsMap));
  loadRawData();
};

// 处理过的模型列表
const processedModels = computed(() => {
  const result: any[] = [];

  // 确保providers和modelsData都已加载
  if (providers.value.length === 0 || Object.keys(modelsData.value).length === 0) {
    return [];
  }

  // 获取有效的提供商名称
  const validProviders = new Set(providers.value.map(p => p.name));

  // 遍历模型数据，只处理有效提供商的模型
  Object.keys(modelsData.value).forEach(providerName => {
    if (validProviders.has(providerName)) {
      const providerData = modelsData.value[providerName];

      // 检查模型服务配置是否完整：apiKey、apiUrl、models都不能为空
      const hasApiKey = providerData.apiKey && providerData.apiKey.trim() !== '';
      const hasApiUrl = providerData.apiUrl && providerData.apiUrl.trim() !== '';
      const groups = normalizeProviderModelGroups(providerData);
      const hasModels = groups.length > 0;

      // 只有配置完整的模型服务才显示在模态窗口中
      if (hasApiKey && hasApiUrl && hasModels) {
        groups.forEach((group: any) => {
          if (group.models && Array.isArray(group.models)) {
            // 遍历组中的每个模型
            group.models.forEach((model: any) => {
              result.push({
                id: model.id,
                name: model.name,
                iconText: model.iconText || model.name.charAt(0).toUpperCase(),
                serviceProvider: providerName,
                avatar: providerAvatars.value[providerName], // 添加提供商头像
                types: model.types || [],
                contextSize: typeof model.contextSize === 'number'
                  ? model.contextSize
                  : (typeof model.context_size === 'number' ? model.context_size : undefined)
              });
            });
          }
        });
      } else {
      }
    }
  });

  return result;
});

// 提供商顺序 - 只显示有有效模型的提供商
const orderedProviders = computed(() => {
  // 获取所有有效模型的提供商名称
  const validProviders = new Set(processedModels.value.map(model => model.serviceProvider));

  // 按原始顺序返回有效的提供商
  return providers.value
      .map(p => p.name)
      .filter(name => validProviders.has(name));
});

// 模型分组，按服务提供商分组
const modelGroups = computed(() => {
  const groups: Record<string, any[]> = {};

  // 按提供商分组模型
  processedModels.value.forEach(model => {
    const provider = model.serviceProvider;
    if (!groups[provider]) {
      groups[provider] = [];
    }
    groups[provider].push(model);
  });

  return groups;
});

// 过滤模型列表
const filteredModels = computed(() => {
  if (!modelSearchText.value) return processedModels.value;
  return processedModels.value.filter(model =>
      model.name.toLowerCase().includes(modelSearchText.value.toLowerCase())
  );
});

// 当前选中的模型名称
const currentModelName = computed(() => {
  const model = resolveSelectedModel();
  return model ? model.name : '';
});



// 当前选中的智能体名称
const currentAgentName = computed(() => {
  const ag = activeAgentConfig.value || StorageService.getActiveAgent();
  try {
    return ag?.basic?.name || '';
  } catch {
    return '';
  }
});

// 当前选中的智能体头像
const currentAgentAvatar = computed(() => {
  const ag = activeAgentConfig.value || StorageService.getActiveAgent();
  try {
    return resolveAgentAvatar(ag?.basic?.avatar || '');
  } catch {
    return '';
  }
});

// 当前选中的模型对象（包含提供商信息，用于颜色计算）
const currentModelObj = computed(() => {
  const model = resolveSelectedModel();
  return model || null;
});

// 判断是否应该显示特定图标
const shouldShowIcon = (modelName: string, iconType: string) => {
  return shouldShowModelIcon(modelName, iconType);
};

// 初始化从chatStore获取模型
const initFromChatStore = () => {
  // 确保从chatStore获取最新的模型
  if (chatStore.model) {
    currentModel.value = chatStore.model;
    currentModelService.value = (chatStore.selectedModelService as string) || StorageService.getApiConfig()?.service || '';
  } else {
    // 如果有可用模型，自动选择第一个
    if (processedModels.value.length > 0) {
      currentModel.value = processedModels.value[0].id;
      currentModelService.value = processedModels.value[0].serviceProvider || '';
    }
  }

  const resolved = resolveSelectedModel(currentModel.value, currentModelService.value);
  if (resolved) {
    currentModelService.value = resolved.serviceProvider || '';
  }
};

// 在模型加载时自动更新当前模型
watch(
    () => processedModels.value,
    (newModels) => {

      // 如果模型列表为空，说明可能还在加载中，不做任何操作
      if (newModels.length === 0) {
        return;
      }

      // 如果当前没有选择模型，则尝试初始化并自动选择第一个模型
      if (!currentModel.value) {
        currentModel.value = newModels[0].id;
        currentModelService.value = newModels[0].serviceProvider || '';
        return;
      }

      // 检查当前模型是否在新模型列表中
      const modelExists = newModels.some(m =>
        m.id === currentModel.value &&
        (!currentModelService.value || m.serviceProvider === currentModelService.value)
      );

      if (!modelExists && currentModel.value) {

        // 如果当前模型不存在于新模型列表中，选择第一个可用模型
        currentModel.value = newModels[0].id;
        currentModelService.value = newModels[0].serviceProvider || '';
      } else if (currentModel.value) {
        const resolved = resolveSelectedModel(currentModel.value, currentModelService.value);
        if (resolved) {
          currentModelService.value = resolved.serviceProvider || '';
        }
      }
    }
);

// 监听chatStore中模型的变化
watch(
    () => chatStore.model,
    (newModel) => {
      if (newModel && newModel !== currentModel.value) {
        currentModel.value = newModel;
        const resolved = resolveSelectedModel(newModel, (chatStore.selectedModelService as string) || currentModelService.value);
        currentModelService.value = resolved?.serviceProvider || (chatStore.selectedModelService as string) || '';
      }
    }
);

watch(
    () => chatStore.selectedModelService,
    (newService) => {
      currentModelService.value = (newService as string) || '';
    }
);

// 监听模态窗口的打开状态变化
watch(
    () => showModelSelector.value,
    async (isOpen) => {
      emit('model-selector-open', isOpen);
      if (isOpen) {
        // 模态窗口打开时，保存当前选择的模型
        previousModel.value = currentModel.value;
        previousModelService.value = currentModelService.value;

        // 模态窗口打开时，强制刷新模型列表

        // 重新加载模型数据
        await reloadModelData();
      }
    }
);

// 重新加载模型数据的函数
const reloadModelData = async () => {
  // 重置搜索文本
  modelSearchText.value = '';

  try {
    await syncModelDataFromServer();
  } catch (_) {
    // 请求失败时回退到本地缓存
    loadRawData();
  }

  // 确保当前选择的模型仍然有效
  const modelExists = processedModels.value.some(m =>
    m.id === currentModel.value &&
    (!currentModelService.value || m.serviceProvider === currentModelService.value)
  );
  if (!modelExists && processedModels.value.length > 0) {
    currentModel.value = processedModels.value[0].id;
    currentModelService.value = processedModels.value[0].serviceProvider || '';
  } else {
    const resolved = resolveSelectedModel(currentModel.value, currentModelService.value);
    if (resolved) {
      currentModelService.value = resolved.serviceProvider || '';
    }
  }
};

// 选择模型
const selectModel = (model: any) => {
  selectedModel.value = model;
  currentModel.value = model.id;
  currentModelService.value = model.serviceProvider || '';
};

// 取消模型选择，恢复原来的选择
const cancelModelSelection = () => {
  currentModel.value = previousModel.value;
  currentModelService.value = previousModelService.value;
  showModelSelector.value = false;
};

// 确认模型选择
const confirmModelSelection = () => {
  if (currentModel.value) {
    const selectedModel = resolveSelectedModel();
    if (!selectedModel) {
      NotificationService.warning('未找到所选模型对应的模型服务');
      return;
    }

    // 先切换服务配置，再设置模型，避免setModel内部applyConfig时仍使用旧服务信息
    if (selectedModel.serviceProvider) {
      // 加载该服务商的API配置
      chatStore.loadModelServiceConfig(selectedModel.serviceProvider, true);
      currentModelService.value = selectedModel.serviceProvider;

      // 确保尝试加载apiKey
      if (!chatStore.apiKey) {
        try {
          if (modelsData.value[selectedModel.serviceProvider]) {
            const serviceData = modelsData.value[selectedModel.serviceProvider];
            if (serviceData && serviceData.apiKey) {
              chatStore.setApiKey(serviceData.apiKey);
              chatStore.setApiBaseUrl(serviceData.apiUrl || '');
            }
          }
        } catch (e) {
          console.error('读取模型服务配置失败:', e);
        }
      }
    }

    // 最后再设置模型，确保applyConfig时使用的是最新的服务配置
    chatStore.setModel(currentModel.value);

    // 应用配置
    chatStore.applyConfig();

    // 检查配置状态
    if (chatStore.isConfigured) {
      NotificationService.success('模型已切换');
      showModelSelector.value = false;
      emit('update:model', currentModel.value);
    } else {
      if (!chatStore.apiKey) {
        NotificationService.warning('请先在设置中配置API密钥');
      } else {
        NotificationService.error('模型配置失败，请检查API设置');
      }
    }
  } else {
    showModelSelector.value = false;
  }
};

// 前往聊天偏好设置页面
const goToSettings = () => {
  showModelSelector.value = false;
  router.push('/settings/chat-preferences');
  emit('navigate-to-settings');
};

// 前往模型服务管理页面
const goToModelService = () => {
  showModelSelector.value = false;
  router.push('/settings/model-service');
  emit('navigate-to-settings');
};

// 前往账户管理页面
const goToAccount = () => {
  showModelSelector.value = false;
  router.push('/account');
};

let isLoggingOut = false;

// 处理登出
const handleLogout = async () => {
  if (isLoggingOut) {
    return;
  }
  isLoggingOut = true;
  showModelSelector.value = false;
  try {
    try {
      void chatStore.stopCurrentRequest();
    } catch {}
    try {
      chatStore.clearChat();
    } catch {}
    StorageService.clearForLogout();
    if (route.path !== ROUTES.LOGIN) {
      await router.replace(ROUTES.LOGIN);
    }
    broadcastGlobalLogout('manual');
  } finally {
    isLoggingOut = false;
  }
};

// 处理模态窗口关闭事件
const handleModelSelectorCancel = () => {
  showModelSelector.value = false;
};

// 初始化数据
onMounted(() => {
  // 直接从本地存储加载原始数据
  loadRawData();

  (async () => {
    try {
      await syncModelDataFromServer();
    } catch (e) {
      
    }
  })();

  // 确保chatStore已加载配置
  if (!chatStore.isConfigured) {
    chatStore.loadSavedConfig();
  }

  // 初始化组件数据
  initFromChatStore();

  // 初始化时检查智能体状态
  const initialAgent = StorageService.getActiveAgent();
  isAgentMode.value = !!initialAgent;
  activeAgentConfig.value = initialAgent;


  // 加载用户信息
  loadUserInfo();
  loadUserGroups();

  // 监听模型列表变更事件
  const handleModelsChanged = () => {

    // 如果模态窗口当前是打开状态，则重新加载数据
    if (showModelSelector.value) {
      reloadModelData();
    } else {
      // 即使模态窗口未打开，也刷新模型数据以保持最新
      loadRawData();
    }

    // 检查是否有活动的智能体
    const activeAgent = StorageService.getActiveAgent();

    // 如果没有活动的智能体，才加载模型服务配置
    if (!activeAgent && currentModel.value) {
      // 查找当前选中模型所属的服务商
      const selectedModelData = resolveSelectedModel();
      if (selectedModelData && selectedModelData.serviceProvider) {
        // 加载该服务商的API配置
        chatStore.loadModelServiceConfig(selectedModelData.serviceProvider, true);

        // 确保尝试加载apiKey
        if (!chatStore.apiKey) {
          try {
            if (modelsData.value[selectedModelData.serviceProvider]) {
              const serviceData = modelsData.value[selectedModelData.serviceProvider];
              if (serviceData && serviceData.apiKey) {
                chatStore.setApiKey(serviceData.apiKey);
                chatStore.setApiBaseUrl(serviceData.apiUrl || '');
              }
            }
          } catch (e) {
            console.error('读取模型服务配置失败:', e);
          }
        }
      }

      // 应用配置，确保同步到mcp-client-api-config
      chatStore.applyConfig();
    }
  };

  // 添加对活跃智能体更新事件的监听
  const handleActiveAgentUpdated = () => {
    // 更新isAgentMode状态以触发重新渲染
    const ag = StorageService.getActiveAgent();
    isAgentMode.value = !!ag;
    activeAgentConfig.value = ag;
  };

  // 添加对智能体选择变更事件的监听
  const handleAgentSelectionChanged = () => {
    // 更新isAgentMode状态以触发重新渲染
    const ag = StorageService.getActiveAgent();
    isAgentMode.value = !!ag;
    activeAgentConfig.value = ag;
  };

  // 添加对用户信息更新事件的监听
  const handleUserInfoUpdated = () => {
    // 重新加载用户信息
    loadUserInfo();
    loadUserGroups();
  };

  window.addEventListener('mcp-models-changed', handleModelsChanged);
  window.addEventListener('active-agent-updated', handleActiveAgentUpdated);
  window.addEventListener('agent-selection-changed', handleAgentSelectionChanged);
  window.addEventListener('user-info-updated', handleUserInfoUpdated);
  // 在组件卸载时移除事件监听器
  onUnmounted(() => {
    window.removeEventListener('mcp-models-changed', handleModelsChanged);
    window.removeEventListener('active-agent-updated', handleActiveAgentUpdated);
    window.removeEventListener('agent-selection-changed', handleAgentSelectionChanged);
    window.removeEventListener('user-info-updated', handleUserInfoUpdated);
  });
});

// 暴露方法给父组件
defineExpose({
  showModelSelector,
  reloadModelData
});

// 所有智能体入口打开独立工作台。
const handleAgentSelectClick = () => {
  window.dispatchEvent(new Event('open-agent-workspace'));
};
</script>

<style scoped>
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0;
  height: 55px;
  position: relative;
  z-index: 99;
  width: 100%;
  margin-top: -24px;
}

.header-left {
  display: flex;
  align-items: center;
}

.header-center {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  white-space: nowrap;
}

.security-notice {
  color: #999;
  font-size: 13px;
  user-select: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 画布 / 交付中心 Tab：绝对定位对齐右侧 Canvas 面板“预览/编辑”中心 */
.panel-tabs-anchor {
  position: absolute;
  top: 50%;
  left: calc((100% - 5px) * 17 / 22 + 5px);
  transform: translate(-50%, -50%);
  z-index: 100;
  display: flex;
}

.user-avatar {
  cursor: pointer;
  background-color: #ffffff;
  color: #1890ff;
  font-weight: bold;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-avatar :deep(.ant-avatar-string) {
  color: inherit;
  z-index: 1;
}

/* 添加针对头像图片的样式 */
.user-avatar :deep(.ant-avatar-image) {
  object-fit: cover; /* 改为cover确保图片填充容器 */
  transition: transform 0.3s ease;
  width: 100%; /* 改为100%以完全填充 */
  height: 100%; /* 改为100%以完全填充 */
  object-position: center;
}

.user-avatar :deep(.ant-avatar-image:hover) {
  transform: scale(1.05);
}

.user-avatar :deep(img) {
  object-fit: cover; /* 改为cover确保图片填充容器 */
  transition: transform 0.3s ease;
  width: 100%; /* 改为100%以完全填充 */
  height: 100%; /* 改为100%以完全填充 */
  object-position: center;
}

.user-avatar :deep(img:hover) {
  transform: scale(1.05);
}

/* 实现图片平铺效果的样式 - 仅对需要平铺的图片使用 */
.user-avatar.tiled {
  position: relative;
}

.user-avatar.tiled::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: auto;
  background-repeat: repeat;
  background-position: center;
  z-index: 0;
}

.user-avatar.tiled :deep(.ant-avatar-image),
.user-avatar.tiled :deep(img) {
  /* 隐藏原始图片，使用背景图片替代 */
  opacity: 0;
}

/* 确保在没有头像时显示文字 */
.user-avatar.tiled :deep(.ant-avatar-string) {
  position: relative;
  z-index: 1;
}

.user-menu {
  min-width: 200px;
  border-radius: 12px !important;
  padding: 0 0 !important;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12) !important;
  border: 1px solid #f0f0f0 !important;
}

.user-menu :deep(.ant-dropdown-menu-item) {
  padding: 8px 12px !important;
  border-radius: 8px !important;
  margin: 4px !important;
  transition: all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94) !important;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
  cursor: pointer !important;
}

.user-menu :deep(.ant-dropdown-menu-item:hover) {
  background-color: rgba(24, 144, 255, 0.1) !important;
  color: #1890ff !important;
}

.user-menu :deep(.ant-dropdown-menu-item.user-info-noninteractive) {
  opacity: 1 !important;
  cursor: default !important;
  pointer-events: auto !important;
  background-color: transparent !important;
  padding: 8px 12px !important;
  border-radius: 8px !important;
  margin: 4px !important;
  color: inherit !important;
}

.user-menu :deep(.ant-dropdown-menu-item.user-info-noninteractive:hover) {
  background-color: transparent !important;
  color: inherit !important;
}

.user-menu :deep(.ant-dropdown-menu-item.user-info-noninteractive .user-info-menu-item) {
  cursor: default !important;
  pointer-events: auto !important;
}

.user-info-menu-item {
  display: flex;
  align-items: center;
}

.user-details {
  margin-left: 12px;
  min-width: 0;
}

.user-name {
  color: #1f1f1f;
  font-weight: 600;
  font-size: 14px;
}

.user-email {
  font-size: 12px;
  color: #8c8c8c;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-groups,
.user-groups-hint {
  margin-top: 2px;
  font-size: 12px;
  line-height: 1.4;
}

.user-groups {
  color: #595959;
}

.user-groups,
.user-groups-hint {
  max-width: 110px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-groups-hint {
  color: #bfbfbf;
}

/* 添加下拉菜单中用户头像的样式 */
.user-info-menu-item :deep(.ant-avatar) {
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-info-menu-item :deep(.ant-avatar-image) {
  object-fit: cover; /* 改为cover确保图片填充容器 */
  transition: transform 0.3s ease;
  width: 100%; /* 改为100%以完全填充 */
  height: 100%; /* 改为100%以完全填充 */
  object-position: center;
}

.user-info-menu-item :deep(img) {
  object-fit: cover; /* 改为cover确保图片填充容器 */
  transition: transform 0.3s ease;
  width: 100%; /* 改为100%以完全填充 */
  height: 100%; /* 改为100%以完全填充 */
  object-position: center;
}

/* 实现下拉菜单中图片平铺效果的样式 */
.user-info-menu-item :deep(.ant-avatar.tiled) {
  position: relative;
}

.user-info-menu-item :deep(.ant-avatar.tiled)::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-size: auto;
  background-repeat: repeat;
  background-position: center;
  z-index: 0;
}

.user-info-menu-item :deep(.ant-avatar.tiled .ant-avatar-image),
.user-info-menu-item :deep(.ant-avatar.tiled img) {
  /* 隐藏原始图片，使用背景图片替代 */
  opacity: 0;
}

/* 确保在没有头像时显示文字 */
.user-info-menu-item :deep(.ant-avatar.tiled .ant-avatar-string) {
  position: relative;
  z-index: 1;
}

.trigger {
  font-size: 15px;
  cursor: pointer;
  transition: color 0.3s;
  border-radius: 12px;
}

.back-btn-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 5px;
  font-size: 16px;
  font-weight: 600;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 12px;
  margin-right: 8px;
  transition: all 0.3s;
}

.back-btn:hover {
  background-color: #f5f5f5;
}

.model-select-btn {
  display: flex;
  align-items: center;
  border-radius: 10px;
  transition: all 0.3s;
  height: 41px;
  padding: 6px 14px 6px 16px;
  position: relative;
}

.model-select-btn:hover {
  background-color: #ffffff;
}

.header-primary-action {
  display: grid;
  min-height: 41px;
  align-items: center;
  justify-items: start;
}

/* 知识库/交付中心「新对话」与「模型选择」共用同一网格位做交叉淡入，
   但两者样式已完全解耦，互不影响 */
.header-primary-action > .model-select-btn,
.header-primary-action > .knowledge-new-chat-btn {
  grid-area: 1 / 1;
}

/* 知识库「新对话」按钮：独立样式，不复用 .model-select-btn */
.knowledge-new-chat-btn {
  display: flex;
  align-items: center;
  border-radius: 10px;
  transition: all 0.3s;
  height: 34px;
  /* 左内边距与 .model-select-btn 一致，使两个按钮的图标左边缘、文字起点对齐 */
  padding: 2px 11px 2px 16px;
  position: relative;
}

.knowledge-new-chat-btn:hover {
  background-color: #ffffff;
}

.knowledge-new-chat-content {
  display: flex;
  align-items: center;
  /* 图标容器两侧各留 2px，视觉间距 = 2 + 5 = 7px */
  gap: 5px;
  height: 100%;
}

/* 与 .model-icon 同宽（26px），保证图标与文字的横向位置对齐 */
.knowledge-new-chat-icon {
  width: 26px;
  height: 26px;
  min-width: 26px;
  margin-left: -2px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.knowledge-new-chat-icon img {
  /* new_chat_nav.svg 的 viewBox 为 1075x1024，按原始比例换算避免被压扁 */
  width: 22px;
  height: 21px;
  display: block;
}

.knowledge-new-chat-label {
  margin-right: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 500;
}

.model-select-fade-enter-active,
.model-select-fade-leave-active {
  transition: opacity 180ms ease;
}

.model-select-fade-leave-active {
  pointer-events: none;
}

.model-select-fade-enter-from,
.model-select-fade-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .model-select-fade-enter-active,
  .model-select-fade-leave-active {
    transition-duration: 0.01ms;
  }
}

.model-selection {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 100%;
}

.agent-arrow {
  width: 16px;
  height: 16px;
  display: inline-block;
}

/* 智能体图标切换过渡动画 */
.agent-arrow-toggle-enter-active,
.agent-arrow-toggle-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.agent-arrow-toggle-enter-from,
.agent-arrow-toggle-leave-to {
  opacity: 0;
  transform: scale(0.9);
}

.model-select-name {
  margin-right: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
  font-weight: 500;
}

.model-icon {
  width: 26px;
  height: 26px;
  min-width: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  font-size: 14px;
  margin-left: -2px;
  overflow: hidden;
}

/* 确保字符头像有合适的背景色和文字居中 */
.model-icon:not(.with-image) {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 确保字符头像有背景色 */
.model-icon:not(.with-image) span {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.model-icon-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 999px;
}

:deep(.ant-space) {
  display: flex;
  align-items: center;
}

:deep(.ant-btn.active) {
  color: #1890ff;
  background: rgba(24, 144, 255, 0.1);
}

/* 搜索框样式 */
.model-search {
  margin-top: 12px;
  margin-bottom: 12px;
}

.custom-search-wrapper {
  display: flex;
  align-items: center;
  background-color: #f3f3f3b9;
  border-radius: 12px;
  padding: 6px 14px;
  border: 1px solid transparent;
  color: #333;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.custom-search-wrapper:hover {
  background-color: #e5e7eb;
}

.custom-search-wrapper:focus-within {
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.search-icon {
  color: #999;
  font-size: 16px;
  margin-right: 8px;
}

.custom-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-size: 14px;
  color: #333;
}

.custom-input::placeholder {
  color: #bfbfbf;
}

/* 模型选择器样式 */
.model-categories {
  min-height: 400px;
  max-height: 400px;
  overflow-y: auto;
  margin-right: -10px;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
}

.model-categories.mask-top {
  mask-image: linear-gradient(to bottom, transparent, black 15px, black 100%);
  -webkit-mask-image: linear-gradient(to bottom, transparent, black 15px, black 100%);
}

.model-categories.mask-bottom {
  mask-image: linear-gradient(to bottom, black 0%, black calc(100% - 15px), transparent);
  -webkit-mask-image: linear-gradient(to bottom, black 0%, black calc(100% - 15px), transparent);
}

.model-categories.mask-both {
  mask-image: linear-gradient(to bottom, transparent, black 15px, black calc(100% - 15px), transparent);
  -webkit-mask-image: linear-gradient(to bottom, transparent, black 15px, black calc(100% - 15px), transparent);
}

.model-categories:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.model-categories::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.model-categories::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.model-categories:hover::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
}

.model-categories::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, 0.25);
}

.model-categories::-webkit-scrollbar-track {
  background-color: transparent;
}

.category {
  margin-bottom: 16px;
}

.category-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #1f1f1f;
}

.model-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.model-item {
  display: flex;
  align-items: center;
  padding: 11px 39px 11px 13px;
  border-radius: 12px;
  background-color: #ffffff;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  border: 1px solid #f0f0f0;
  position: relative;
  overflow: hidden;
}

.model-item:hover {
  background-color: #f8fafc;
  border-color: #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transform: translateY(-1px);
}

.model-item.selected {
  background-color: #f0f7ff;
  border-color: #bae0ff;
}

.model-item.selected::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 16px;
  background-color: #1890ff;
  border-radius: 0 3px 3px 0;
}

.model-info {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.model-list .model-icon {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: bold;
  margin-right: 10px;
  flex-shrink: 0;
  overflow: hidden;
  font-size: 13px;
}

.model-list .model-icon-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  border-radius: 10px;
}

.model-list .model-name {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: #1f2937;
  line-height: 1.4;
}

.model-meta {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-top: 3px;
  flex-wrap: nowrap;
  min-height: 16px;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
}

.model-provider-text {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 400;
  white-space: nowrap;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}

.model-type-tag {
  display: inline-flex;
  align-items: center;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  border: 1px solid transparent;
  font-weight: 500;
  line-height: 1.3;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s ease;
}

.model-type-tag.dialogue {
  background-color: #e0f2fe;
  color: #0284c7;
}

.model-type-tag.vision {
  background-color: #f3e8ff;
  color: #9333ea;
}

.model-type-tag.reasoning {
  background-color: #fff7ed;
  color: #ea580c;
}

.model-type-tag.tool {
  background-color: #ecfdf5;
  color: #059669;
}

.model-type-tag.context-size-tag {
  background-color: #eef2ff;
  color: #364fc7;
}

.model-item.selected .model-type-tag.dialogue {
  border-color: #7dd3fc;
}

.model-item.selected .model-type-tag.vision {
  border-color: #d8b4fe;
}

.model-item.selected .model-type-tag.reasoning {
  border-color: #fdba74;
}

.model-item.selected .model-type-tag.tool {
  border-color: #86efac;
}

.model-item.selected .model-type-tag.context-size-tag {
  border-color: #c7d2fe;
}

.model-select-indicator {
  color: #1890ff;
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background-color: rgba(24, 144, 255, 0.1);
  border-radius: 50%;
  font-size: 10px;
}

.model-selector-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  margin-bottom: -5px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.model-selector-buttons {
  display: flex;
}

.model-service-link {
  color: #1890ff;
  cursor: pointer;
  font-size: 13px;
}

.model-service-link:hover {
  color: #40a9ff;
}

.empty-models {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  min-height: 400px;
  max-height: 400px;
}

.empty-models p {
  color: #8c8c8c;
  margin-bottom: 16px;
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 模型图标 SVG 容器样式，确保与模型卡片一致 */
.model-icon-svg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: white;
}

.model-icon-svg :deep(svg) {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.model-icon-svg :deep(svg path) {
  fill: currentColor;
}

.model-cancel-button {
  margin-right: 10px;
  background: #f3f4f6;
  color: #374151;
  font-weight: 500;
  font-size: 13px;
  border-radius: 10px;
  padding: 5px 24px;
  border: none;
  cursor: pointer;
}

.model-cancel-button:hover {
  background: #e5e7eb;
}

.model-confirm-button {
  background: #3b82f6;
  color: #fff;
  font-weight: 500;
  font-size: 13px;
  border-radius: 10px;
  padding: 5px 24px;
  border: none;
  cursor: pointer;
}

.model-confirm-button:hover {
  background: #2563eb;
}

/* 自定义模态窗口样式 */
:global(.model-selector-modal .ant-modal-content) {
  border-radius: 22px !important;
}
</style>
