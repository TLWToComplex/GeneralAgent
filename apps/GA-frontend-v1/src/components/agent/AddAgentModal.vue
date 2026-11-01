<template>
  <a-modal
      v-model:open="visible"
      :title="props.editMode ? '编辑智能体' : '添加智能体'"
      :footer="null"
      width="900px"
      :maskClosable="false"
      class="agent-modal"
      centered
      @cancel="handleCancel"
  >
    <div class="agent-form-container">
      <!-- 左侧菜单 -->
      <div class="left-menu" :class="{ 'no-anim': !menuTransitionEnabled }">
        <transition name="menu-fade" mode="out-in" :appear="false">
          <a-menu :key="menuMode" mode="inline" v-model:selectedKeys="selectedMenuKey" class="agent-left-menu" @select="handleMenuSelect">
            <a-menu-item v-for="item in menuItems" :key="item.key">
              <span>{{ item.label }}</span>
            </a-menu-item>
          </a-menu>
        </transition>
      </div>

      <!-- 右侧配置区域 -->
      <div class="right-config">
        <div v-if="isSharedAgentReadonly" class="agent-readonly-banner">
          公开共享的智能体仅管理用户可编辑或删除，当前为只读模式
        </div>
        <!-- 智能体信息 -->
        <div v-if="selectedMenuKey[0] === 'basic'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <BasicInfoPanel
            :basicConfig="formData.basic"
            :errors="formErrors"
            :editMode="props.editMode"
            :canEditVisibility="canEditVisibility"
            :readonly="isSharedAgentReadonly"
            :agentData="props.agentData"
            :permission-group-options="permissionGroupOptions"
            :permission-groups="formData.permissionGroupIds"
            :permission-group-loading="permissionGroupsLoading"
            @update:basicConfig="handleBasicConfigUpdate"
            @update:errors="handleErrorsUpdate"
            @update:permission-groups="handlePermissionGroupsUpdate"
            @delete="handleDelete"
            ref="basicInfoPanelRef"
          />
        </div>

        <!-- 提示词设置 -->
        <div v-if="selectedMenuKey[0] === 'prompt'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <PromptConfigPanel 
            :prompt-config="formData.prompt" 
            :errors="formErrors" 
            :model-name="formData.model.name"
            @update:prompt-config="handlePromptConfigUpdate"
            @update:errors="handleErrorsUpdate"
          />
        </div>

        <!-- 模型设置 -->
        <div v-if="selectedMenuKey[0] === 'model'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <ModelConfigPanel 
            :model-config="formData.model" 
            :errors="formErrors" 
            :model-groups="modelGroups"
            @update:modelConfig="handleModelConfigUpdate"
            @update:errors="handleErrorsUpdate"
          />
        </div>

        <!-- 知识库设置 -->
        <div v-if="selectedMenuKey[0] === 'knowledge'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <KnowledgeConfigPanel 
            :knowledge-config="formData.knowledge as any" 
            :errors="formErrors"
            @update:knowledgeConfig="handleKnowledgeConfigUpdate"
            @update:errors="handleErrorsUpdate"
            @close-modal="handleCloseModal"
          />
        </div>

        <!-- MCP服务器设置 -->
        <div v-if="selectedMenuKey[0] === 'mcp'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <McpServerPanel 
               :mcpConfig="formData.mcp" 
               :formErrors="formErrors"
               :editMode="props.editMode"
               @update:mcpConfig="handleMcpConfigUpdate"
            />
        </div>

        <div v-if="selectedMenuKey[0] === 'skills'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <SkillsConfigPanel
            :skills="formData.skills"
            @update:skills="handleSkillsUpdate"
            @close-agent-modal="handleCloseModal"
          />
        </div>

        <div v-if="selectedMenuKey[0] === 'environment'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <EnvVarConfigPanel
            :envVars="formData.environment"
            @update:envVars="handleEnvVarsUpdate"
          />
        </div>

        <div v-if="selectedMenuKey[0] === 'memory'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <DeepAgentMemoryPanel
            v-model:enabled="memoryConfig.enabled"
            :agent-uuid="currentAgentUuid"
          />
        </div>

        <!-- 常用提问 -->
        <div v-if="selectedMenuKey[0] === 'phrases'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <PhrasesConfigPanel
            :phrases="formData.phrases"
            :formErrors="formErrors"
            @update:phrases="handlePhrasesUpdate"
            @update:errors="handleErrorsUpdate"
          />
        </div>

        <div v-if="selectedMenuKey[0] === 'orchestrator'" class="config-section" :class="{ 'is-readonly': isSharedAgentReadonly }">
          <OrchestratorConfigPanel
            :orchestratorConfig="formData.orchestrator"
            :formErrors="formErrors"
            @update:orchestratorConfig="handleOrchestratorConfigUpdate"
            @update:errors="handleErrorsUpdate"
          />
        </div>

        <!-- 操作按钮 -->
        <div class="form-actions-agent">
          <!-- 仅在编辑模式下显示删除按钮 -->
          <a-button v-if="props.editMode" type="primary" danger @click="handleDeleteClick" class="delete-button" :disabled="isSharedAgentReadonly">
            删除智能体
          </a-button>
          <a-button class="cancel-btn" @click="handleCancel">取消</a-button>
          <a-button type="primary" class="confirm-btn" @click="handleConfirm" :disabled="isSharedAgentReadonly">确定</a-button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import {Modal} from 'ant-design-vue';
import '@/assets/styles/add-agent-modal.css';
import defaultAgentAvatar from '@/assets/image/png/angent-bg.png';
import {useChatStore} from '@/stores/chat-store';
import BasicInfoPanel from './BasicInfoPanel.vue';
import McpServerPanel from './McpServerPanel.vue';
import {StorageService} from '@/utils/StorageService';
import NotificationService from '@/utils/NotificationService';
import ModelConfigPanel from './ModelConfigPanel.vue';
import PromptConfigPanel from './PromptConfigPanel.vue';
import PhrasesConfigPanel from './PhrasesConfigPanel.vue';
import KnowledgeConfigPanel from './KnowledgeConfigPanel.vue';
import OrchestratorConfigPanel from './OrchestratorConfigPanel.vue';
import SkillsConfigPanel from './SkillsConfigPanel.vue';
import DeepAgentMemoryPanel from './DeepAgentMemoryPanel.vue';
import EnvVarConfigPanel from './EnvVarConfigPanel.vue';
import {ref, watch, onMounted, onUnmounted, computed, nextTick} from 'vue';
import { listAiEntityAssignedGroups, listAiUserGroups, type UserGroupItem } from '@/services/aiPermission';

// 定义本地服务器信息接口
interface LocalServerInfo {
  id: string;
  name: string;
  url: string;
  tools: string[];
  connected: boolean;
  reconnecting?: boolean;
  fullToolInfo?: any[];
  type?: string;
}

// 定义工具接口
interface ToolInfo {
  id: string;
  name: string;
  description: string;
  parameters?: Record<string, any>;
}

// 获取StorageService实例
const storageService = StorageService.getInstance();

// 使用chatStore获取服务器列表
const chatStore = useChatStore();

// 本地存储键
const SERVERS_STORAGE_KEY = 'mcp-servers-list';
const SERVER_DATA_STORAGE_KEY = 'mcp-servers-data';

// BasicInfoPanel组件引用
const basicInfoPanelRef = ref<InstanceType<typeof BasicInfoPanel> | null>(null);

// 本地服务器列表
const localServerList = ref<LocalServerInfo[]>([]);

// 辅助函数：通过名称查找服务器数据，处理键名可能不一致的情况
function findServerDataByName(parsedData: Record<string, any>, name: string): any {
  // 尝试直接匹配
  if (parsedData[name]) {
    return parsedData[name];
  }

  // 遍历所有键，进行模糊匹配
  for (const key in parsedData) {
    if (key.includes(name) || name.includes(key)) {
      return parsedData[key];
    }
  }

  return null;
}

// 加载本地存储的服务器配置
const loadLocalServers = async () => {
  try {
    // 从本地存储加载服务器列表
    const serversList = localStorage.getItem(SERVERS_STORAGE_KEY);
    const serversData = localStorage.getItem(SERVER_DATA_STORAGE_KEY);

    if (serversList && serversData) {
      try {
        const parsedList = JSON.parse(serversList);
        const parsedData = JSON.parse(serversData);

        // 将服务器列表与chatStore中的服务器状态合并
        localServerList.value = parsedList.map((item: { id?: string; name: string }) => {
          // 检查item是否有id，如果有则使用id作为键，否则回退到使用name
          const serverKey = item.id || item.name;
          
          // 特殊处理，因为JSON.parse后键可能会有空格或特殊字符
          const serverData = parsedData[serverKey] || findServerDataByName(parsedData, item.name);
          if (!serverData) {
            return null;
          }

          // 从本地存储获取工具信息
          const localTools = serverData.tools || [];

          // 格式化工具列表，提取工具名称
          const toolNames = localTools.map((tool: ToolInfo) => tool.name || tool.id || '未知工具');

          // 使用服务器数据中的id（如果有），否则使用名称和URL组合作为唯一ID
          const uniqueId = serverData.id || (item.id ? item.id : `${item.name}|${serverData.url}`);

          return {
            id: uniqueId,
            name: item.name,
            url: serverData.url,
            tools: toolNames,
            connected: false,
            reconnecting: false,
            fullToolInfo: localTools,
            type: serverData.type || 'default'
          };
        }).filter(Boolean);

        // 不再默认启用所有服务器，保持为空数组表示默认关闭所有服务
        // 仅在编辑模式下加载已有配置，添加模式下默认全部关闭
        if (props.editMode && props.agentData && formData.value.mcp.enabledServerIdentifiers.length === 0) {
          // 编辑模式下，如果没有设置过enabledServerIdentifiers，则不做任何操作
          // 保持为空数组，让原有逻辑处理
        }
      } catch (parseError) {
        console.error('解析本地存储数据失败:', parseError);
      }
    } else {
      // 本地存储中没有服务器配置
    }
  } catch (error) {
    console.error('加载本地服务器配置失败:', error);
  }
};

// 组件挂载时加载本地服务器
onMounted(async () => {
  await loadLocalServers();
});


// 定义表单数据结构
export interface BasicConfig {
  name: string;
  description: string;
  type: string;
  visibility: 'private' | 'public';
  icon: string;
  avatar: string;
  themeColor: string;
}

interface PromptConfig {
  systemPrompt: string;
  historyDepth?: number;
}

interface ModelConfig {
  service: string | undefined;
  name: string | undefined;
  temperature: number;
  top_p: number;
  presence_penalty: number;
  frequency_penalty: number;
  // 添加apiKey和apiUrl字段，用于存储完整的模型配置信息
  apiKey?: string;
  apiUrl?: string;
}

interface KnowledgeConfig {
  enabled: boolean;
  selectedKnowledge: string[];
  retrievalMode: string;
}

interface OrchestratorConfig {
  serviceUrl: string;
}

interface MCPConfig {
  // 使用服务器名称和URL的组合作为唯一标识符，处理名称重复的情况
  enabledServerIdentifiers: string[];
}

interface FormData {
  basic: BasicConfig;
  prompt: PromptConfig;
  model: ModelConfig;
  knowledge: KnowledgeConfig;
  mcp: MCPConfig;
  orchestrator: OrchestratorConfig;
  skills: string[];
  environment: Array<{ key: string; value: string }>;
  phrases: string[];
  memory: { enabled: boolean };
  permissionGroupIds: string[];
  originalPermissionGroupIds?: string[];
}

export interface FormErrors {
  name: boolean;
  description: boolean;
  modelService: boolean;
  modelName: boolean;
  type: boolean;
  visibility?: boolean;
  orchestratorUrl?: boolean;
  permissionGroups?: boolean;
}

interface Props {
  open: boolean;
  editMode: boolean;
  agentData: any;
  // 新建模式下按列表筛选预选的默认值（类型 / 可见性）
  createDefaults?: { type?: string; visibility?: 'private' | 'public' };
}

interface Emits {
  (e: 'update:open', value: boolean): void;

  (e: 'confirm', data: FormData): void;

  (e: 'cancel'): void;

  (e: 'delete', agentId: string): void;
  
  (e: 'close-modal'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const getCurrentUsername = () => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) return '';
    const profile = JSON.parse(raw);
    return String(profile?.username || '').trim();
  } catch (_) {
    return '';
  }
};
const isCurrentUserAdmin = computed(() => getCurrentUsername().toLowerCase() === 'admin');
const canEditVisibility = computed(() => isCurrentUserAdmin.value);
const isSharedAgentReadonly = computed(() =>
  !!props.editMode
  && !isCurrentUserAdmin.value
  && String(
    formData.value.basic.visibility
    || props.agentData?.visibility
    || props.agentData?.config?.basic?.visibility
    || ''
  ).trim().toLowerCase() === 'public'
);
const AGENT_ENTITY_TYPE = 3;
const permissionGroupsLoading = ref(false);
const availablePermissionGroups = ref<UserGroupItem[]>([]);
const permissionGroupsLoaded = ref(false);
const originalPermissionGroupIds = ref<string[]>([]);
const permissionGroupDraftIds = ref<string[]>([]);
const permissionGroupOptions = computed(() =>
  availablePermissionGroups.value.map((group) => ({
    label: group.name,
    value: group.uuid
  }))
);

const visible = ref(false);
const selectedMenuKey = ref(['basic']);
const updateTimer = ref<NodeJS.Timeout | null>(null);
const forceUpdate = ref(0);
const menuTransitionEnabled = ref(false);
const initializing = ref(false);
const memoryConfig = ref({ enabled: false });
const currentAgentUuid = computed(() => String(props.agentData?.uuid || '').trim());

const isOrchestrator = computed(() => formData.value.basic.type === 'orchestrator');
const isDeepAgent = computed(() => formData.value.basic.type === 'deepagent');
const menuMode = computed(() => {
  if (isOrchestrator.value) {
    return 'orchestrator';
  }

  if (isDeepAgent.value) {
    return 'deepagent';
  }

  return 'assistant';
});
const menuItems = computed(() =>
  isOrchestrator.value
    ? [
        { key: 'basic', label: '智能体信息' },
        { key: 'orchestrator', label: '智能体配置' }
      ]
    : isDeepAgent.value
      ? [
          { key: 'basic', label: '智能体信息' },
          { key: 'prompt', label: '提示词设置' },
          { key: 'model', label: '模型设置' },
          { key: 'knowledge', label: '知识库设置' },
          { key: 'mcp', label: 'MCP设置' },
          { key: 'skills', label: '技能配置' },
          { key: 'environment', label: '环境变量' },
          { key: 'memory', label: '记忆' },
          { key: 'phrases', label: '常用提问' }
        ]
    : [
        { key: 'basic', label: '智能体信息' },
        { key: 'prompt', label: '提示词设置' },
        { key: 'model', label: '模型设置' },
        { key: 'knowledge', label: '知识库设置' },
        { key: 'mcp', label: 'MCP设置' },
        { key: 'phrases', label: '常用提问' }
      ]
);

// 处理基本配置更新
const handleBasicConfigUpdate = (newConfig: Partial<BasicConfig>) => {
  formData.value.basic = { ...formData.value.basic, ...newConfig };
};

// 处理错误状态更新
const handleErrorsUpdate = (newErrors: Partial<FormErrors>) => {
  formErrors.value = { ...formErrors.value, ...newErrors };
};

// 处理提示词配置更新
const handlePromptConfigUpdate = (newConfig: PromptConfig) => {
  formData.value.prompt = { ...formData.value.prompt, ...newConfig };
};

// 处理模型配置更新
const handleModelConfigUpdate = (newConfig: ModelConfig) => {
  formData.value.model = { ...formData.value.model, ...newConfig };
};

// 处理知识库配置更新
const handleKnowledgeConfigUpdate = (newConfig: KnowledgeConfig) => {
  formData.value.knowledge = { ...formData.value.knowledge, ...newConfig };
};

// 处理MCP配置更新
const handleMcpConfigUpdate = (newConfig: MCPConfig) => {
  formData.value.mcp = { ...formData.value.mcp, ...newConfig };
};

// 处理编排式智能体配置更新
const handleOrchestratorConfigUpdate = (newConfig: OrchestratorConfig) => {
  formData.value.orchestrator = { ...formData.value.orchestrator, ...newConfig };
};

const handleSkillsUpdate = (skills: string[]) => {
  formData.value.skills = [...skills];
};

// 处理环境变量更新
const handleEnvVarsUpdate = (envVars: Array<{ key: string; value: string }>) => {
  formData.value.environment = [...envVars];
};

// 处理常用提问更新
const handlePhrasesUpdate = (phrases: string[]) => {
  formData.value.phrases = [...phrases];
};

const normalizePermissionGroupIds = (groupIds: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(groupIds) ? groupIds : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

const handlePermissionGroupsUpdate = (groupIds: string[]) => {
  if (isSharedAgentReadonly.value) return;
  const normalizedGroupIds = normalizePermissionGroupIds(groupIds);
  formData.value.permissionGroupIds = normalizedGroupIds;
  permissionGroupDraftIds.value = normalizedGroupIds.slice();
  formErrors.value.permissionGroups = false;
};

const ensurePermissionGroupsLoaded = async () => {
  if (!canEditVisibility.value || permissionGroupsLoaded.value || permissionGroupsLoading.value) return;
  permissionGroupsLoading.value = true;
  try {
    availablePermissionGroups.value = await listAiUserGroups();
    permissionGroupsLoaded.value = true;
  } catch {
    availablePermissionGroups.value = [];
  } finally {
    permissionGroupsLoading.value = false;
  }
};

// 处理删除事件
const handleDelete = (agentId: string) => {
  if (isSharedAgentReadonly.value) {
    NotificationService.info('非 admin 用户不能删除共享智能体');
    return;
  }
  emit('delete', agentId);
};

// 处理删除按钮点击事件
const handleDeleteClick = () => {
  if (isSharedAgentReadonly.value) {
    NotificationService.info('非 admin 用户不能删除共享智能体');
    return;
  }
  const agentId = props.agentData?.id;
  if (basicInfoPanelRef.value && (basicInfoPanelRef.value as any).handleDelete) {
    (basicInfoPanelRef.value as any).handleDelete();
    return;
  }
  if (!agentId) return;
  Modal.confirm({
    title: '确认删除',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: '确定要删除这个智能体吗？此操作不可撤销。',
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: () => {
      emit('delete', agentId);
    }
  });
};

// 处理关闭模态框事件
const handleCloseModal = () => {
  // 关闭当前模态框
  visible.value = false;
  emit('update:open', false);
  emit('close-modal');
};

// 监听props.open变化
watch(() => props.open, (newVal) => {
  visible.value = newVal;
  if (newVal) {
    if (canEditVisibility.value) {
      ensurePermissionGroupsLoaded();
    }
    initializing.value = true;
    // 先加载模型数据
    loadModelData();
    // 确保模型数据已经加载完成
    nextTick(() => {
      if (props.editMode && props.agentData) {
        // 编辑模式，加载智能体数据
        void loadAgentData();
      } else {
        // 添加模式，重置表单
        resetForm();
      }
      startVariableUpdateTimer();
      menuTransitionEnabled.value = false;
      initializing.value = false;
    });
  } else {
    stopVariableUpdateTimer();
    menuTransitionEnabled.value = false;
    initializing.value = false;
  }
});

// 监听编辑模式和智能体数据变化
watch(
    () => [props.editMode, props.agentData],
    ([editMode, agentData]) => {
      if (visible.value && editMode && agentData) {
        void loadAgentData();
      }
    },
    {deep: true}
)

// 模型数据相关
const providers = ref<any[]>([]);
const modelsData = ref<Record<string, any>>({});

// 从本地存储加载模型数据
const loadModelData = () => {
  try {
    const providersData = localStorage.getItem('mcp-providers');
    const modelsStorageData = localStorage.getItem('mcp-models');

    if (providersData) {
      providers.value = JSON.parse(providersData);
    }

    if (modelsStorageData) {
      modelsData.value = JSON.parse(modelsStorageData);
    }
  } catch (e) {
    console.error('Failed to load model data:', e);
  }
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
      const hasModels = providerData.models && Object.keys(providerData.models).length > 0;

      // 只有配置完整的模型服务才显示
      if (hasApiKey && hasApiUrl && hasModels) {
        // 遍历每个模型组
        Object.values(providerData.models).forEach((group: any) => {
          if (group.models && Array.isArray(group.models)) {
            // 遍历组中的每个模型
            group.models.forEach((model: any) => {
              result.push({
                id: model.id,
                name: model.name,
                serviceProvider: providerName
              });
            });
          }
        });
      }
    }
  });

  return result;
});

// 按服务提供商分组的模型
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

// 表单错误状态
const formErrors = ref<FormErrors>({
  name: false,
  description: false,
  modelService: false,
  modelName: false,
  type: false,
  permissionGroups: false
});

// 生成随机颜色
const getRandomColor = () => {
  const defaultColors = [
    '#1890ff',
    '#52c41a',
    '#faad14',
    '#f5222d',
    '#722ed1',
    '#13c2c2',
    '#eb2f96',
    '#fa8c16',
  ];
  const randomIndex = Math.floor(Math.random() * defaultColors.length);
  return defaultColors[randomIndex];
};

// 表单数据
const formData = ref<FormData>({
  basic: {
    name: '',
    description: '',
    type: 'assistant',
    visibility: 'private',
    icon: 'A',
    avatar: defaultAgentAvatar,
    themeColor: getRandomColor()
  },
  prompt: {
    systemPrompt: '',
    historyDepth: 3
  },
  model: {
    service: '',
    name: '',
    temperature: 0.7,
    top_p: 1.0,
    presence_penalty: 0,
    frequency_penalty: 0
  },
  knowledge: {
    enabled: false,
    selectedKnowledge: [],
    retrievalMode: 'semantic'
  },
  mcp: {
    enabledServerIdentifiers: []
  },
  orchestrator: {
    serviceUrl: ''
  },
  skills: [],
  environment: [],
  phrases: [],
  memory: { enabled: false },
  permissionGroupIds: []
});

// 在加载智能体数据（编辑模式）时，确保正确初始化MCP配置
const loadAgentData = async () => {
  if (!props.agentData || !props.agentData.config) {
    originalPermissionGroupIds.value = [];
    permissionGroupDraftIds.value = [];
    resetForm();
    return;
  }

  const agentConfig = props.agentData.config;

  // 先设置表单数据，但模型名称暂时设为空
  formData.value = {
    basic: {
      name: agentConfig.basic?.name || '',
      description: agentConfig.basic?.description || '',
      type: agentConfig.basic?.type || props.agentData?.agent_type || 'assistant',
      visibility: agentConfig.basic?.visibility || props.agentData?.visibility || 'private',
      icon: agentConfig.basic?.icon || (agentConfig.basic?.name ? agentConfig.basic.name.charAt(0).toUpperCase() : 'A'),
      avatar: agentConfig.basic?.avatar || defaultAgentAvatar,
      themeColor: agentConfig.basic?.themeColor || getRandomColor()
    },
    prompt: {
      systemPrompt: agentConfig.prompt?.systemPrompt || '你是一个智能智能体，我会为你提供任务和对话，你需要根据上下文提供准确、有用的回答。请保持友好、专业的语气，并确保你的回复简洁明了。',
      historyDepth: agentConfig.prompt?.historyDepth || 3
    },
    model: {
      service: agentConfig.model?.service || undefined,
      name: '', // 先不设置模型名称
      temperature: agentConfig.model?.temperature || 0.7,
      top_p: agentConfig.model?.top_p || 1.0,
      presence_penalty: agentConfig.model?.presence_penalty || 0,
      frequency_penalty: agentConfig.model?.frequency_penalty || 0
    },
    knowledge: {
      enabled: agentConfig.knowledge?.enabled || false,
      selectedKnowledge: Array.isArray(agentConfig.knowledge?.selectedKnowledge)
        ? agentConfig.knowledge.selectedKnowledge
        : agentConfig.knowledge?.selectedKnowledge
          ? [agentConfig.knowledge.selectedKnowledge]
          : [],
      retrievalMode: agentConfig.knowledge?.retrievalMode || 'semantic'
    },
    mcp: {
      enabledServerIdentifiers: agentConfig.mcp?.enabledServerIdentifiers || []
    },
    orchestrator: {
      serviceUrl: agentConfig.orchestrator?.serviceUrl || agentConfig.orchestrator?.url || agentConfig.orchestrator?.endpoint || agentConfig.orchestrator?.apiUrl || ''
    },
    skills: Array.isArray(agentConfig.skills) ? agentConfig.skills : (Array.isArray(props.agentData?.skills) ? props.agentData.skills : []),
    environment: (() => {
      const envVarsCamel = agentConfig.envVars || {};
      const envVarsSnake = (agentConfig as any).env_vars || {};
      const envArray = Array.isArray(agentConfig.environment) ? agentConfig.environment : [];

      // 优先使用有值的字段
      const sourceEnv = Object.keys(envVarsCamel).length > 0
        ? envVarsCamel
        : (Object.keys(envVarsSnake).length > 0 ? envVarsSnake : null);

      if (sourceEnv) {
        return Object.entries(sourceEnv).map(([key, value]) => ({ key, value: String(value) }));
      }
      return envArray;
    })(),
    phrases: agentConfig.phrases || [],
    memory: { enabled: agentConfig.memory?.enabled ?? false },
    permissionGroupIds: [],
    originalPermissionGroupIds: []
  };

  // 同步 memory 配置到独立变量
  memoryConfig.value = { enabled: agentConfig.memory?.enabled ?? false };
  originalPermissionGroupIds.value = [];
  permissionGroupDraftIds.value = [];

  // 确保模型服务数据已经完全加载后，再设置模型名称
  nextTick(() => {
    if (agentConfig.model?.name) {
      formData.value.model.name = agentConfig.model.name;
    }
  });

  formErrors.value = {
    name: false,
    description: false,
    modelService: false,
    modelName: false,
    type: false,
    visibility: false,
    orchestratorUrl: false,
    permissionGroups: false
  };

  const visibility = String(formData.value.basic.visibility || '').toLowerCase();
  const agentUuid = String(props.agentData?.uuid || '').trim();
  if (visibility === 'public' && agentUuid) {
    try {
      await Promise.all([
        ensurePermissionGroupsLoaded(),
        listAiEntityAssignedGroups(agentUuid, AGENT_ENTITY_TYPE).then((assignedGroups) => {
          const normalizedAssignedGroups = normalizePermissionGroupIds(assignedGroups);
          formData.value.permissionGroupIds = normalizedAssignedGroups.slice();
          formData.value.originalPermissionGroupIds = normalizedAssignedGroups.slice();
          originalPermissionGroupIds.value = normalizedAssignedGroups.slice();
          permissionGroupDraftIds.value = normalizedAssignedGroups.slice();
        })
      ]);
    } catch (error) {
      console.error('加载智能体可访问用户组失败:', error);
    }
  }
};

watch(() => formData.value.model.service, (newService, oldService) => {
  if (newService !== oldService) {
    formData.value.model.name = undefined;
  }
});

watch(
  () => formData.value.basic.visibility,
  (newVal) => {
    if (newVal === 'public' && canEditVisibility.value) {
      formData.value.permissionGroupIds = normalizePermissionGroupIds(permissionGroupDraftIds.value);
      ensurePermissionGroupsLoaded();
    }
    if (newVal !== 'public') {
      permissionGroupDraftIds.value = normalizePermissionGroupIds(formData.value.permissionGroupIds);
      formData.value.permissionGroupIds = [];
      formErrors.value.permissionGroups = false;
    }
  }
);

watch(() => formData.value.basic.type, (newType) => {
  const allowed = newType === 'orchestrator'
    ? ['basic', 'orchestrator']
    : newType === 'deepagent'
      ? ['basic', 'prompt', 'model', 'knowledge', 'mcp', 'skills', 'memory', 'phrases']
      : ['basic', 'prompt', 'model', 'knowledge', 'mcp', 'phrases'];
  if (!allowed.includes(selectedMenuKey.value[0])) {
    selectedMenuKey.value = ['basic'];
  }
});

watch(menuMode, (newVal, oldVal) => {
  if (visible.value && !initializing.value && oldVal !== undefined && newVal !== oldVal) {
    menuTransitionEnabled.value = true;
  }
}, { flush: 'sync' });

// 监听visible变化
watch(visible, (newVal) => {
  emit('update:open', newVal);
  if (!newVal) {
    stopVariableUpdateTimer();
    menuTransitionEnabled.value = false;
    initializing.value = false;
  }
});

// 组件挂载时
onMounted(() => {
  if (visible.value) {
    startVariableUpdateTimer();
  }
});

// 组件卸载时
onUnmounted(() => {
  stopVariableUpdateTimer();
});

// 启动变量更新定时器
const startVariableUpdateTimer = () => {
  if (updateTimer.value) {
    clearInterval(updateTimer.value);
  }
  // 每秒更新一次变量值
  updateTimer.value = setInterval(() => {
    // 强制重新渲染变量显示区域
    forceUpdate.value += 1;
  }, 1000);
};

// 停止变量更新定时器
const stopVariableUpdateTimer = () => {
  if (updateTimer.value) {
    clearInterval(updateTimer.value);
  }
  updateTimer.value = null;
};

// 监听名称变化更新头像文字
watch(() => formData.value.basic.name, (newName) => {
  if (!formData.value.basic.avatar && newName) {
    formData.value.basic.icon = newName.charAt(0).toUpperCase();
  } else if (!formData.value.basic.avatar && !newName) {
    // 当名称为空时，设置默认图标
    formData.value.basic.icon = 'A';
  }
});

// 重置表单
const resetForm = () => {
  // 从缓存获取当前对话页面使用的模型配置
  const apiConfig = storageService.getApiConfig();

  let defaultService: string | undefined = undefined;
  let defaultModel: string | undefined = undefined;

  // 检查API配置是否存在且包含有效的模型信息
  if (apiConfig && apiConfig.model) {
    // 尝试根据API配置中的信息查找对应的服务
    if (apiConfig.service) {
      // 如果有service字段，直接使用
      defaultService = apiConfig.service;
      defaultModel = apiConfig.model;
    } else {
      // 遍历所有服务提供者
      for (const provider of providers.value) {
        const providerName = provider.name;
        const providerData = modelsData.value[providerName];

        // 检查提供者数据是否存在，并且apiKey和apiUrl是否匹配
        if (providerData && providerData.apiKey === apiConfig.apiKey &&
            (providerData.apiUrl === apiConfig.apiBaseUrl || providerData.apiUrl === apiConfig.apiUrl)) {
          defaultService = providerName;
          defaultModel = apiConfig.model;
          break;
        }
      }
    }
  }

  // 如果没有从API配置中找到合适的服务或模型，使用服务列表的第一个服务
  if (!defaultService && providers.value.length > 0) {
    // 使用服务列表的第一个服务
    defaultService = providers.value[0].name;

    // 尝试获取该服务的第一个模型
    if (defaultService) {
      const serviceModels = modelsData.value[defaultService];
      if (serviceModels && typeof serviceModels.models === 'object') {
        const modelGroups = Object.values(serviceModels.models);
        if (Array.isArray(modelGroups) && modelGroups.length > 0) {
          const firstGroup = modelGroups[0];
          if (typeof firstGroup === 'object' && firstGroup !== null &&
              'models' in firstGroup && Array.isArray(firstGroup.models) && firstGroup.models.length > 0) {
            defaultModel = firstGroup.models[0].name;
          }
        }
      }
    }
  }

  // 监听类型变化，动态更新默认智能体名称
  watch(() => formData.value.basic.type, (newType) => {
    // 只有在名称是默认名称之一，或者是空的情况下，才更新名称
    const currentName = formData.value.basic.name;
    const isDefaultName = currentName === '默认智能体' || currentName === '默认DeepAgent智能体' || currentName === '默认编排式智能体' || currentName === '';
    
    if (isDefaultName) {
      if (newType === 'deepagent') {
        formData.value.basic.name = '默认DeepAgent智能体';
      } else if (newType === 'orchestrator') {
        formData.value.basic.name = '默认编排式智能体';
      } else {
        formData.value.basic.name = '默认智能体';
      }
      
      // 更新图标为名称首字母
      if (formData.value.basic.name) {
        formData.value.basic.icon = formData.value.basic.name.charAt(0).toUpperCase();
      }
    }
  });

  // 按列表筛选预选创建默认值：类型直接沿用，"共享"对应 public（仅管理员可创建公开智能体）
  const presetType = props.createDefaults?.type;
  const defaultType = presetType && presetType !== 'all' ? presetType : 'assistant';
  const defaultVisibility = props.createDefaults?.visibility === 'public' && canEditVisibility.value ? 'public' : 'private';

  // 设置默认智能体名称和描述（名称随预选类型变化）
  const defaultAgentName = defaultType === 'deepagent'
    ? '默认DeepAgent智能体'
    : defaultType === 'orchestrator'
      ? '默认编排式智能体'
      : '默认智能体';
  const defaultAgentDescription = '这是一个默认的智能体描述';

  // 先设置表单数据，但模型名称暂时设为空
  formData.value = {
    basic: {
      name: defaultAgentName,
      description: defaultAgentDescription,
      type: defaultType,
      visibility: defaultVisibility,
      icon: defaultAgentName.charAt(0).toUpperCase(),
      avatar: defaultAgentAvatar,
      themeColor: getRandomColor()
    },
    prompt: {
      systemPrompt: '你是一个智能助手，我会为你提供任务和对话，你需要根据上下文提供准确、有用的回答。请保持友好、专业的语气，并确保你的回复简洁明了。',
      historyDepth: 3
    },
    model: {
      service: defaultService,
      name: '',
      temperature: 0.7,
      top_p: 1.0,
      presence_penalty: 0,
      frequency_penalty: 0
    },
    knowledge: {
      enabled: false,
      selectedKnowledge: [],
      retrievalMode: 'semantic'
    },
    mcp: {
      enabledServerIdentifiers: []
    },
    orchestrator: {
      serviceUrl: ''
    },
    skills: [],
    environment: [],
    phrases: [],
    memory: { enabled: false },
    permissionGroupIds: [],
    originalPermissionGroupIds: []
  };
  originalPermissionGroupIds.value = [];
  permissionGroupDraftIds.value = [];

  // 确保模型服务数据已经完全加载后，再设置模型名称
  nextTick(() => {
    if (defaultModel) {
      formData.value.model.name = defaultModel;
    }
  });

  formErrors.value = {
    name: false,
    description: false,
    modelService: false,
    modelName: false,
    type: false,
    visibility: false,
    orchestratorUrl: false,
    permissionGroups: false
  };

  // 重置菜单选择
  selectedMenuKey.value = ['basic'];
};

// 处理菜单选择
const handleMenuSelect = ({key}: { key: string }) => {
  selectedMenuKey.value = [key];
};

// 处理确认
const handleConfirm = () => {
  if (isSharedAgentReadonly.value) {
    NotificationService.info('非 admin 用户不能修改共享智能体');
    return;
  }
  // 表单验证
  let isValid = true;

  // 验证智能体信息
  if (!formData.value.basic.name.trim()) {
    formErrors.value.name = true;
    isValid = false;
  } else {
    formErrors.value.name = false;
  }

  if (!formData.value.basic.description.trim()) {
    formErrors.value.description = true;
    isValid = false;
  } else {
    formErrors.value.description = false;
  }

  if (!formData.value.basic.type) {
    formErrors.value.type = true;
    isValid = false;
  } else {
    formErrors.value.type = false;
  }

  if (!formData.value.basic.visibility) {
    formErrors.value.visibility = true;
    isValid = false;
  } else {
    formErrors.value.visibility = false;
  }

  if (formData.value.basic.type === 'orchestrator') {
    const url = formData.value.orchestrator.serviceUrl?.trim();
    if (!url) {
      formErrors.value.orchestratorUrl = true;
      isValid = false;
    } else {
      formErrors.value.orchestratorUrl = false;
    }
  }

  if (canEditVisibility.value && formData.value.basic.visibility === 'public' && formData.value.permissionGroupIds.length === 0) {
    formErrors.value.permissionGroups = true;
    isValid = false;
  } else {
    formErrors.value.permissionGroups = false;
  }

  if (isValid) {
    // 复制表单数据，准备添加apiKey和apiUrl
    const agentDataToSave = {...formData.value};
    const agentType = agentDataToSave.basic.type || 'assistant';
    
    // 如果选择了模型服务，从modelsData中获取对应的apiKey和apiUrl
    if (agentDataToSave.model.service && modelsData.value[agentDataToSave.model.service]) {
      const providerData = modelsData.value[agentDataToSave.model.service];
      // 添加apiKey和apiUrl信息到model配置中
      agentDataToSave.model.apiKey = providerData.apiKey;
      agentDataToSave.model.apiUrl = providerData.apiUrl;
    }
    
    // 当类型为通用智能体时，清空编排式智能体配置
    if (agentType !== 'orchestrator') {
      agentDataToSave.orchestrator = { serviceUrl: '' };
    } else {
      agentDataToSave.skills = [];
    }

    if (!canEditVisibility.value) {
      agentDataToSave.basic.visibility = props.editMode
        ? (props.agentData?.visibility || props.agentData?.config?.basic?.visibility || 'private')
        : 'private';
      agentDataToSave.permissionGroupIds = [];
    }

    agentDataToSave.permissionGroupIds = normalizePermissionGroupIds(agentDataToSave.permissionGroupIds);
    agentDataToSave.originalPermissionGroupIds = props.editMode
      ? normalizePermissionGroupIds(originalPermissionGroupIds.value)
      : [];

    if (agentType !== 'deepagent') {
      agentDataToSave.skills = [];
    }

    // 更新 memory 配置
    agentDataToSave.memory = { ...memoryConfig.value };

    // 将环境变量数组转换为 key-value 对象格式
    const saveData = agentDataToSave as any;
    if (saveData.environment && saveData.environment.length > 0) {
      saveData.env_vars = saveData.environment.reduce((acc: Record<string, string>, item: { key: string; value: string }) => {
        if (item.key.trim()) {
          acc[item.key.trim()] = item.value;
        }
        return acc;
      }, {});
    } else {
      saveData.env_vars = {};
    }
    delete saveData.environment;

    emit('confirm', agentDataToSave);
    visible.value = false;
    
    // 重置对话历史
    chatStore.clearChat();
  }
};

// 处理取消
const handleCancel = () => {
  emit('cancel');
  visible.value = false;
};
</script>

<style>
.agent-modal .ant-modal-content {
  border-radius: 22px !important;
}

.confirm-delete-modal .ant-modal-content {
  border-radius: 18px !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn {
  height: 30px !important;
  border-radius: 8px !important;
  font-size: 14px !important;
  padding: 0 20px !important;
  border: none !important;
  box-shadow: none !important;
  transition: all 0.3s !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-default {
  background-color: #f5f5f5 !important;
  color: #1a1a1a !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-default:hover {
  background-color: #e6e6e6 !important;
  color: #1a1a1a !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-primary {
  background: #ff5959 !important;
  color: #ffffff !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-primary:hover {
  background-color: #ff4040 !important;
  color: #ffffff !important;
}

.agent-form-container .right-config > div:first-child :deep(.ant-form-item) {
  margin-bottom: 18px !important;
}

.agent-readonly-banner {
  margin-bottom: 14px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #fff7e6;
  border: 1px solid #ffd591;
  color: #ad6800;
  font-size: 13px;
  line-height: 1.5;
}

.agent-form-container .config-section.is-readonly {
  position: relative;
}

.agent-form-container .config-section.is-readonly::after {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 8;
  background: rgba(255, 255, 255, 0.12);
  cursor: not-allowed;
}

.agent-form-container .config-section.is-readonly :deep(.ant-input),
.agent-form-container .config-section.is-readonly :deep(.ant-input-textarea),
.agent-form-container .config-section.is-readonly :deep(.ant-select-selector),
.agent-form-container .config-section.is-readonly :deep(.ant-input-number),
.agent-form-container .config-section.is-readonly :deep(.ant-btn),
.agent-form-container .config-section.is-readonly :deep(button) {
  opacity: 0.9;
}
</style>
