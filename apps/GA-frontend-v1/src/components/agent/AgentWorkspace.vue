<template>
  <section class="agent-workspace" aria-labelledby="agent-workspace-title">
    <div class="aw-scroll" ref="agentListContainer">
      <div class="aw-content">
        <header class="aw-masthead">
          <div class="aw-heading">
            <h1 id="agent-workspace-title">智能体工作台</h1>
            <p class="aw-lead">把经验交出去，让专业替你干活。</p>
          </div>

          <div class="aw-stage">
            <template v-if="activeAgent">
              <div class="aw-stage-head">
                <div class="aw-stage-avatar" :class="{ 'has-image': activeAgent.config?.basic?.avatar }"
                  :style="{ '--aw-avatar-bg': getAgentThemeColor(activeAgent) }" aria-hidden="true">
                  <img v-if="activeAgent.config?.basic?.avatar" :src="getAgentAvatar(activeAgent)" alt="" />
                  <span v-else>{{ activeAgent.config?.basic?.icon || activeAgent.name?.trim().charAt(0).toUpperCase() || 'A' }}</span>
                </div>
                <div class="aw-stage-identity">
                  <strong class="aw-stage-name" :title="activeAgent.name">{{ activeAgent.name }}</strong>
                  <span class="aw-stage-desc" :title="getAgentDescription(activeAgent)">{{ getAgentDescription(activeAgent) }}</span>
                </div>
                <div class="aw-stage-action">
                <button class="aw-stage-exit" type="button"
                  :disabled="isExitingAgent || !!launchingAgentId"
                  :aria-busy="isExitingAgent"
                  title="退出当前智能体"
                  @click="handleStageExit">
                  <span>{{ isExitingAgent ? '正在退出' : '退出智能体' }}</span>
                </button>
                </div>
              </div>

              <div class="aw-stage-stats">
                <div :title="getAgentTypeLabel(activeAgent)">
                  <span>类型</span>
                  <strong>{{ getAgentTypeLabel(activeAgent) }}</strong>
                </div>
                <div :title="getCardBarLabel(activeAgent)">
                  <span>模型</span>
                  <strong>{{ getCardBarLabel(activeAgent) }}</strong>
                </div>
                <div :title="getMcpTooltip(activeAgent)">
                  <span>MCP 工具</span>
                  <strong>{{ getMcpServerCount(activeAgent) }} 个服务</strong>
                </div>
                <div :title="getKnowledgeTooltip(activeAgent)">
                  <span>知识库</span>
                  <strong>{{ getKnowledgeStatus(activeAgent) }}</strong>
                </div>
              </div>
            </template>

            <template v-else>
              <div class="aw-stage-head is-idle">
                <div class="aw-stage-avatar is-idle" aria-hidden="true"></div>
                <div class="aw-stage-identity">
                  <strong class="aw-stage-name">当前未启用智能体</strong>
                  <span class="aw-stage-idle-tip" title="在下方选择一位智能体开始对话">在下方选择一位智能体开始对话</span>
                </div>
                <span class="aw-stage-action" aria-hidden="true"></span>
              </div>
              <div class="aw-stage-stats">
                <div><span>类型</span><strong>未指定</strong></div>
                <div><span>模型</span><strong>未选择</strong></div>
                <div><span>MCP 工具</span><strong>未配置</strong></div>
                <div><span>知识库</span><strong>未启用</strong></div>
              </div>
            </template>
          </div>
        </header>

        <section class="aw-library" aria-label="智能体目录">
          <div class="aw-console">
            <div class="aw-console-filters">
              <div class="aw-segment aw-segment-scope" role="group" aria-label="智能体归属筛选"
                :style="{ '--aw-seg-count': scopeTabs.length, '--aw-seg-index': scopeThumbIndex }">
                <span class="aw-segment-thumb" aria-hidden="true"></span>
                <button v-for="scope in scopeTabs" :key="scope.key" type="button"
                  :class="{ active: activeAgentScope === scope.key }" :aria-pressed="activeAgentScope === scope.key"
                  @click="activeAgentScope = scope.key">{{ scope.label }}<sup>{{ scope.count }}</sup></button>
              </div>

              <span class="aw-console-rule" aria-hidden="true"></span>

              <div class="aw-segment aw-segment-types" role="group" aria-label="智能体类型筛选"
                :style="{ '--aw-seg-count': typeOptions.length, '--aw-seg-index': typeThumbIndex }">
                <span class="aw-segment-thumb" aria-hidden="true"></span>
                <button v-for="option in typeOptions" :key="option.key" type="button"
                  :class="{ active: typeFilter === option.key }" :aria-pressed="typeFilter === option.key"
                  @click="typeFilter = option.key">{{ option.label }}</button>
              </div>

              <span class="aw-console-rule" aria-hidden="true"></span>

              <span class="aw-tally" aria-live="polite"><b>{{ currentScopeAgents.length }}</b> 位智能体</span>
            </div>

            <div class="aw-console-tools">
              <label class="aw-search">
                <SearchOutlined /><input v-model="searchQuery" type="search" placeholder="搜索名称或能力…"
                  aria-label="搜索智能体" />
              </label>
              <button class="aw-icon-button" type="button" :disabled="loading" aria-label="刷新智能体" title="刷新智能体"
                @click="refresh">
                <ReloadOutlined :spin="loading" />
              </button>
              <button class="aw-primary" type="button" @click="handleAddAgent">
                <PlusOutlined /> 创建智能体
              </button>
            </div>
          </div>

          <div v-if="loadError" class="aw-notice" role="alert">{{ loadError }}<button :disabled="loading"
              @click="refresh">重新同步</button></div>
          <div v-if="loading && !localAgentList.length" class="aw-empty" role="status">
            <LoadingOutlined spin />
            <h3>正在连接你的智能体团队</h3>
            <p>加载配置与能力信息…</p>
          </div>
          <div v-else-if="!currentScopeAgents.length" class="aw-empty">
            <h3>{{ activeScopeAgentCount ? '还没有找到合适的伙伴' : (localAgentList.length ? '这个分类下还没有智能体' : '你的第一位伙伴，从这里开始') }}</h3>
            <p>{{ activeScopeAgentCount ? '换个关键词，或调整类型筛选。' : '选择模型，连接工具，把你的专业经验交给智能体。' }}</p>
            <button class="aw-primary" @click="activeScopeAgentCount ? resetFilters() : handleAddAgent()">{{
              activeScopeAgentCount ? '清除筛选' : (localAgentList.length ? '创建智能体' : '创建第一个智能体') }}</button>
          </div>
          <div v-else class="aw-grid">
            <article v-for="agent in currentScopeAgents" :key="agent.id" class="aw-card"
              :class="{ 'is-current': isAgentActivated(agent) }"
              :data-agent-id="agent.id">
              <div class="aw-card-head">
                <div class="aw-avatar" :class="{ 'has-image': agent.config?.basic?.avatar }"
                  :style="{ '--aw-avatar-bg': getAgentThemeColor(agent) }" aria-hidden="true">
                  <img v-if="agent.config?.basic?.avatar" :src="getAgentAvatar(agent)" alt="" />
                  <span v-else>{{ agent.config?.basic?.icon || agent.name?.trim().charAt(0).toUpperCase() || 'A' }}</span>
                </div>
                <div class="aw-card-identity">
                  <h3 class="aw-card-name">
                    <button type="button" :title="agent.name">{{ agent.name }}</button>
                  </h3>
                  <div class="aw-card-kicker">
                    <span class="aw-card-type" :title="`类型：${getAgentTypeLabel(agent)}`">类型：{{ getAgentTypeLabel(agent) }}</span>
                    <span v-if="isAgentActivated(agent)" class="aw-card-status" title="当前对话">当前对话</span>
                  </div>
                </div>
                <a-dropdown :trigger="['click']" overlay-class-name="aw-more-menu" :open="dropdownVisible[agent.id]"
                  @openChange="open => handleDropdownVisibleChange(agent.id, open)">
                  <button type="button" class="aw-icon-button aw-more" :aria-label="`${agent.name}的更多操作`">
                    <MoreOutlined />
                  </button>
                  <template #overlay><a-menu>
                      <a-menu-item v-if="isAgentActivated(agent)" key="new"
                        :disabled="!!launchingAgentId" @click="launchAgent(agent, true)">
                        <img :src="newChatNav2Icon" alt="" class="aw-menu-icon" /> 开启新对话
                      </a-menu-item>
                      <a-menu-item key="edit" :disabled="isAgentActivated(agent) || isSharedAgentReadonly(agent)"
                        @click="handleEditAgentWithClose(agent, agent.id)">
                        <!-- 使用中禁止编辑时，用 tooltip 告知需先退出智能体；标题为空则不展示浮层 -->
                        <a-tooltip placement="right"
                          :title="isAgentActivated(agent) ? '该智能体正在使用中，请先退出智能体后再进行编辑' : ''">
                          <span><EditOutlined /> 编辑智能体</span>
                        </a-tooltip>
                      </a-menu-item>
                      <a-menu-item key="delete" danger
                        :disabled="isSharedAgentReadonly(agent) || chatStore.isProcessing"
                        @click="handleDeleteAgentConfirmWithClose(agent, agent.id)">
                        <DeleteOutlined /> 删除智能体
                      </a-menu-item>
                    </a-menu></template>
                </a-dropdown>
              </div>

              <div class="aw-meta-full"><em :title="agent.description || '为你的任务提供专业支持，开启对话探索更多可能。'">{{ agent.description ||
                '为你的任务提供专业支持，开启对话探索更多可能。' }}</em></div>

              <div class="aw-fields">
                <template v-if="getAgentType(agent) !== 'orchestrator'">
                  <a-tooltip placement="top" :title="getMcpTooltip(agent)">
                    <div><span>MCP 工具</span><strong>{{ getMcpServerCount(agent) }} 个服务</strong></div>
                  </a-tooltip>
                  <a-tooltip placement="top" :title="getKnowledgeTooltip(agent)">
                    <div class="aw-field-kb"><span>知识库</span><strong>{{ getKnowledgeStatus(agent) }}</strong></div>
                  </a-tooltip>
                  <a-tooltip placement="top" :title="getMemoryTooltip(agent)">
                    <div><span>记忆</span><strong>{{ agent.config?.memory?.enabled ? '已开启' : '未开启' }}</strong></div>
                  </a-tooltip>
                </template>
                <template v-else>
                  <a-tooltip placement="top" title="通过编排工作流自动执行任务">
                    <div><span>执行方式</span><strong>编排工作流</strong></div>
                  </a-tooltip>
                  <a-tooltip placement="top" :title="agent.config?.orchestrator?.serviceUrl || '待配置服务地址'">
                    <div><span>服务地址</span><strong>{{ agent.config?.orchestrator?.serviceUrl ? '已配置' : '待配置' }}</strong></div>
                  </a-tooltip>
                  <a-tooltip placement="top" title="按流程执行任务并交付结果">
                    <div><span>交付</span><strong>按流程执行任务</strong></div>
                  </a-tooltip>
                </template>
              </div>

              <div class="aw-card-bar">
                <div class="aw-card-bar-model" :title="getCardBarLabel(agent)">
                  <span v-if="showCardBarIcon(agent)" class="aw-model-icon">
                    <component v-if="getModelIcon(agent)" :is="getModelIcon(agent)" />
                    <em v-else>{{ getCardBarLabel(agent).charAt(0).toUpperCase() }}</em>
                  </span>
                  <span class="aw-model-name">{{ getCardBarLabel(agent) }}</span>
                </div>
                <button type="button" class="aw-bar-launch" @click.stop="launchAgent(agent)"><svg class="aw-bar-launch-icon" viewBox="0 0 1075 1024" fill="currentColor" aria-hidden="true"><path d="M193.7408 145.8688c4.4544-21.8624 35.7376-21.8624 40.2432 0 9.8304 48.3328 47.616 86.1184 95.9488 96 21.9136 4.4544 21.9136 35.7376 0 40.192A123.136 123.136 0 0 0 233.984 378.0608c-4.5056 21.8624-35.7888 21.8624-40.2432 0A123.136 123.136 0 0 0 97.792 282.0608c-21.8624-4.4544-21.8624-35.7376 0-40.192a123.136 123.136 0 0 0 96-96z" /><path d="M122.4192 381.184a32.2048 32.2048 0 0 1 22.016 39.7824l-3.2256 12.3904c-30.208 129.3824 36.4544 291.9424 185.1392 396.032A482.816 482.816 0 0 0 499.5072 906.24a32.1536 32.1536 0 0 1-13.6704 62.8224 547.1232 547.1232 0 0 1-196.4032-87.04c-169.984-119.04-253.952-314.88-206.848-478.8736l2.4576-6.0416a32.2048 32.2048 0 0 1 37.376-15.9744z m630.016-231.424a117.9136 117.9136 0 1 1 166.8096 166.8096l-72.8064 72.7552c48.9472 65.536 75.776 133.12 85.4016 194.0992 10.3936 65.9456 1.024 127.1808-26.368 168.192-51.968 77.9776-130.6624 89.9072-190.7712 83.9168a337.7152 337.7152 0 0 1-105.0112-28.7744l-1.8432-0.8704-0.5632-0.256-0.2048-0.1024-0.0512-0.0512-5.5296-3.4816a32.1536 32.1536 0 0 1 34.2016-54.0672h0.1536a74.8544 74.8544 0 0 0 5.7856 2.6624c4.1984 1.792 10.5472 4.352 18.432 7.0656 15.8208 5.4784 37.376 11.4688 61.0304 13.824 47.0528 4.7104 97.024-4.864 130.816-55.5008 15.5136-23.296 25.1904-66.56 16.384-122.5216-7.5776-47.9232-28.4672-103.0656-67.8912-158.1568l-210.4832 210.5856a250.4704 250.4704 0 0 1-169.472 73.216 68.608 68.608 0 0 1-70.6048-70.6048 250.368 250.368 0 0 1 73.216-169.472l196.9152-196.864c-77.2096-38.7072-158.4128-54.016-231.7312-47.5136a32.1536 32.1536 0 1 1-5.632-64l18.4832-1.28c87.04-3.9936 180.224 17.664 266.5472 65.1776l84.7872-84.7872z m121.2928 45.4656a53.6576 53.6576 0 0 0-75.776 0l-329.3696 329.3696a186.0608 186.0608 0 0 0-54.4256 125.8496 4.1984 4.1984 0 0 0 4.352 4.352 186.0608 186.0608 0 0 0 125.952-54.4256l329.216-329.3184a53.6576 53.6576 0 0 0 0-75.8272z" /></svg>{{ isAgentActivated(agent) ? '继续对话' : '开始对话' }}</button>
              </div>
            </article>
            <button class="aw-create-card" @click="handleAddAgent"><span aria-hidden="true">
                <PlusOutlined />
              </span><strong>创建智能体</strong>
              <p>组合模型、工具与知识，构建适合你的工作方式</p>
            </button>
          </div>
        </section>
      </div>
    </div>
    <AddAgentModal v-model:open="addAgentModalVisible" :edit-mode="isEditMode" :agent-data="currentEditingAgent"
      :create-defaults="createDefaults"
      @confirm="handleAddAgentConfirm" @cancel="handleAddAgentCancel" @delete="handleDeleteAgent" />
  </section>
</template>

<script setup lang="ts">

import { useChatStore } from '@/stores/chat-store';
import StorageService from '@/utils/StorageService';
import { addAiAgent, deleteAiAgent, updateAiAgent, listAiAgents } from '@/services/aiAgent';
import { onMounted, onUnmounted, ref, watch, computed, nextTick, defineAsyncComponent } from 'vue';

// 弹窗（内含 js-tiktoken 等重型依赖）按需加载，避免占用首屏
const AddAgentModal = defineAsyncComponent(() => import('./AddAgentModal.vue'));

import { useChatConfigStore } from '@/stores/chatConfigStore';
import { Dropdown as ADropdown, Menu as AMenu, MenuItem as AMenuItem, Modal } from 'ant-design-vue';
import { PlusOutlined, SearchOutlined, MoreOutlined, EditOutlined, DeleteOutlined, ReloadOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import newChatNav2Icon from '@/assets/image/svg/new-chat-nav-2.svg';
import QwenIcon from '@/components/icons/llm/qwen.vue';
import DeepSeekIcon from '@/components/icons/llm/deepseek.vue';
import ZhipuIcon from '@/components/icons/llm/zhipu.vue';
import ZaiIcon from '@/components/icons/llm/zai.vue';
import { shouldShowModelIcon } from '@/utils/modelIcon';
import { resolveAgentAvatar } from '@/utils/agentAvatar';
import { getPrompt } from '@/services/aiPrompt';
import { updateAiPermission } from '@/services/aiPermission';
import NotificationService from '@/utils/NotificationService';

interface AgentInfo {
  id: string;
  name: string;
  description: string;
  themeColor?: string;
  visibility?: string;
  config?: any;
}

// 仅当处于对话工作区时才恢复并初始化智能体会话
const props = withDefaults(defineProps<{
  chatWorkspaceActive?: boolean;
}>(), {
  chatWorkspaceActive: true
});

const localAgentList = ref<AgentInfo[]>([]);

const searchQuery = ref('');
const selectedAgentId = ref<string | null>(null);
const chatStore = useChatStore();
const configStore = useChatConfigStore();

const agentListContainer = ref<HTMLElement | null>(null);
const emit = defineEmits<{ (e: 'start-chat'): void }>();
const loading = ref(true);
const loadError = ref('');
const launchingAgentId = ref<string | null>(null);
const isExitingAgent = ref(false);
const handleStageExit = async () => {
  if (isExitingAgent.value || launchingAgentId.value) return;
  isExitingAgent.value = true;
  try {
    await exitAgentMode();
  } finally {
    isExitingAgent.value = false;
  }
};
const typeFilter = ref('all');
const typeOptions = [
  { key: 'all', label: '全部类型' },
  { key: 'assistant', label: '通用智能体' },
  { key: 'deepagent', label: 'DeepAgent' },
  { key: 'orchestrator', label: '编排式' }
];
const resetFilters = () => { searchQuery.value = ''; activeAgentScope.value = 'shared'; typeFilter.value = 'all'; };
const refresh = async () => {
  loading.value = true;
  loadError.value = '';
  try { await refreshAgentsFromBackend(); }
  catch {
    await loadLocalAgents();
    loadError.value = localAgentList.value.length
      ? '暂时无法同步智能体，当前显示本地缓存。'
      : '暂时无法加载智能体，请检查连接后重试。';
  }
  finally { loading.value = false; }
};
const launchAgent = async (agent: AgentInfo, newChat = false) => {
  if (launchingAgentId.value) {
    NotificationService.info('正在切换智能体，请稍候');
    return;
  }
  launchingAgentId.value = agent.id;
  try {
    if (restoreSessionPromise) await restoreSessionPromise;
    if (selectedAgentId.value === agent.id && !newChat) { emit('start-chat'); return; }
    // 选中逻辑（写入 activeAgent、派发事件）在首个 await 前同步完成，
    // 因此先跳转对话界面，初始化改为后台执行，其状态在输入框内呈现，避免停留在名册页干等
    const selecting = handleSelectAgent(agent.id, true);
    emit('start-chat');
    await selecting;
  } finally { launchingAgentId.value = null; }
};

// 计算过滤后的智能体列表
const filteredAgentList = computed(() => {
  if (!searchQuery.value) {
    return localAgentList.value;
  }

  const query = searchQuery.value.toLowerCase().trim();
  return localAgentList.value.filter(agent =>
    (agent.name || '').toLowerCase().includes(query) ||
    (agent.description || '').toLowerCase().includes(query)
  );
});

type AgentScope = 'shared' | 'personal';

const activeAgentScope = ref<AgentScope>('shared');

const getAgentOwnership = (agent: AgentInfo): AgentScope => {
  const visibility = String(agent.visibility ?? agent.config?.basic?.visibility ?? '').toLowerCase();
  if (visibility === 'private') {
    return 'personal';
  }
  return 'shared';
};

const scopeTabs = computed(() => [
  { key: 'shared' as AgentScope, label: '共享智能体', count: localAgentList.value.filter(a => getAgentOwnership(a) === 'shared').length },
  { key: 'personal' as AgentScope, label: '我的智能体', count: localAgentList.value.filter(a => getAgentOwnership(a) === 'personal').length }
]);
const scopeThumbIndex = computed(() => Math.max(0, scopeTabs.value.findIndex(tab => tab.key === activeAgentScope.value)));
const typeThumbIndex = computed(() => Math.max(0, typeOptions.findIndex(option => option.key === typeFilter.value)));
// 当前归属下（不考虑搜索与类型筛选）的智能体数量，用于区分「筛选无结果」与「该分类为空」两种空状态
const activeScopeAgentCount = computed(() =>
  localAgentList.value.filter(agent => getAgentOwnership(agent) === activeAgentScope.value).length
);
const currentScopeAgents = computed(() => filteredAgentList.value.filter(agent =>
  getAgentOwnership(agent) === activeAgentScope.value &&
  (typeFilter.value === 'all' || getAgentType(agent) === typeFilter.value)
));

// 页首状态面板：展示当前正在使用（已激活会话）的智能体信息
const activeAgent = computed(() =>
  localAgentList.value.find(agent => agent.id === selectedAgentId.value) || null
);

const loadLocalAgents = async () => {
  try {
    localAgentList.value = StorageService.getAgents();
    selectedAgentId.value = StorageService.getSelectedAgent();
  } catch (error) {
    localAgentList.value = [];
  }
};

const syncSelectedAgentState = (evt?: Event) => {
  const detail = (evt as CustomEvent | undefined)?.detail as { selected?: boolean; agentId?: string | null } | undefined;
  const normalizedAgentId = detail && 'agentId' in detail
    ? String(detail.agentId || '').trim()
    : String(StorageService.getSelectedAgent() || '').trim();

  selectedAgentId.value = normalizedAgentId || null;
  if (!normalizedAgentId) {
    chatStore.resetAgentInit();
    lastInitializedSessionThreadId = '';
  }
};

const refreshAgentsFromBackend = async () => {
  const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
  const res = await listAiAgents();
  if (!Array.isArray(res?.data)) throw new Error('智能体列表响应格式无效');
  const arr: any[] = res.data;
  const mapped = arr.map((item: any) => {
    const m = item.config?.model || {};
    const resolvedVisibility = item.visibility ?? item.config?.basic?.visibility ?? null;
    const basicConfig = {
      ...(item.config?.basic || {}),
      type: item.config?.basic?.type || item.agent_type || 'assistant',
      visibility: resolvedVisibility
    };
    const skills = Array.isArray(item.skills)
      ? item.skills
      : (Array.isArray(item.config?.skills) ? item.config.skills : []);
    const normalizedModel = {
      service: m.service,
      name: m.name,
      temperature: typeof m.temperature === 'number' ? m.temperature : 0.7,
      top_p: typeof m.topP === 'number' ? m.topP : (typeof m.top_p === 'number' ? m.top_p : 1.0),
      presence_penalty: typeof m.presencePenalty === 'number' ? m.presencePenalty : (typeof m.presence_penalty === 'number' ? m.presence_penalty : 0),
      frequency_penalty: typeof m.frequencyPenalty === 'number' ? m.frequencyPenalty : (typeof m.frequency_penalty === 'number' ? m.frequency_penalty : 0),
      apiKey: m.apiKey,
      apiUrl: sanitizeUrl(m.apiUrl)
    };
    const resolvedOrchestratorUrl = sanitizeUrl((item.config?.orchestrator?.serviceUrl) || (item.config?.orchestrator?.url) || (item.config?.orchestrator?.endpoint) || (item.config?.orchestrator?.apiUrl));
    return {
      id: item.id,
      name: item.name,
      description: item.description,
      themeColor: item.themeColor,
      uuid: item.uuid,
      agent_type: item.agent_type || basicConfig.type,
      visibility: resolvedVisibility,
      skills,
      config: {
        basic: basicConfig,
        prompt: { ...(item.config?.prompt || {}) },
        model: normalizedModel,
        knowledge: { ...(item.config?.knowledge || {}) },
        mcp: { ...(item.config?.mcp || { enabledServerIdentifiers: [] }) },
        orchestrator: { serviceUrl: resolvedOrchestratorUrl },
        skills,
        phrases: Array.isArray(item.config?.phrases) ? item.config.phrases : [],
        memory: { enabled: item.config?.memory?.enabled ?? false },
        env_vars: item.config?.envVars || item.config?.env_vars || {}
      }
    } as any;
  });
  StorageService.setAgents(mapped);
  window.dispatchEvent(new Event('agents-updated'));
  await loadLocalAgents();
};

// 监听全局 agents-updated 事件以刷新列表UI
const handleAgentsUpdated = async (_evt?: Event) => {
  try {
    await loadLocalAgents();
  } catch (e) {
    console.warn('刷新智能体列表失败（非致命）:', e);
  }
};

const resolveAgentType = (agent: any) => {
  return agent?.config?.basic?.type || 'assistant';
};

const shouldInitializeAgentSession = (agent: any) => {
  const agentType = resolveAgentType(agent);
  return agentType === 'assistant' || agentType === 'deepagent';
};

const resolveAgentUuid = (agent: any) => {
  return String(agent?.uuid || agent?.config?.basic?.uuid || agent?.id || '').trim();
};

// 最近激活的会话，用于释放旧沙盒；初始化复用由 store 统一判断
let lastInitializedSessionThreadId = '';
async function exitAgentMode(options?: { clearChat?: boolean; isCurrent?: () => boolean }) {
  const isCurrent = options?.isCurrent || (() => true);
  if (!isCurrent()) return false;
  if (!selectedAgentId.value) return false;

  chatStore.detachCurrentConversation();
  const clearChat = options?.clearChat !== false;
  const currentAgent = localAgentList.value.find(agent => agent.id === selectedAgentId.value);
  const agentType = currentAgent?.config?.basic?.type;

  if (agentType === 'deepagent' && chatStore.sessionThreadId && !chatStore.isProcessing) {
    // 容器释放交给后台静默执行：不阻塞退出流程、不占用全局 loading
    chatStore.releaseSandboxContainer(chatStore.sessionThreadId);
  }

  if (!isCurrent()) {
    return false;
  }
  selectedAgentId.value = null;
  StorageService.setSelectedAgent(null);
  chatStore.resetAgentInit();
  lastInitializedSessionThreadId = '';
  if (clearChat) {
    chatStore.clearChat();
  }

  StorageService.removeActiveAgent();
  window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: null } }));
  window.dispatchEvent(new CustomEvent('agent-selection-changed', { detail: { selected: false, agentId: null } }));

  StorageService.remove('mcp-original-config');
  try {
    const list = await getPrompt();
    const first = list[0] || '';
    if (isCurrent() && first.trim()) {
      const text = first.trim();
      chatStore.setSystemMessage(text, false);
    }
  } catch (_) { }

  setTimeout(() => {
    window.dispatchEvent(new Event('mcp-models-changed'));
  }, 100);

  return true;
}

// 初始化失败：不保留错误态与重试入口，直接自动退回普通模式
watch(() => chatStore.agentInitStatus, (status) => {
  if (status !== 'error' || !selectedAgentId.value) return;
  console.error('智能体初始化失败，自动退出智能体模式:', chatStore.agentInitError);
  NotificationService.error('智能体初始化失败，已自动退出智能体模式');
  exitAgentMode();
});

// 释放当前激活的 DeepAgent 沙箱（若存在）。用于切换智能体 / 打开其他历史会话前，
// 避免旧沙箱残留导致后端资源泄漏。
// 打开历史记录时 chatStore.sessionThreadId 已先被切到目标会话，
// 因此以最近激活的会话 ID 为准，包括仍在初始化的会话。
// 释放请求由 store 后台静默发出，这里同步返回，不阻塞切换。
function releaseCurrentDeepAgent() {
  const currentAgent = localAgentList.value.find(agent => agent.id === selectedAgentId.value);
  if (currentAgent?.config?.basic?.type !== 'deepagent') return;
  // 正在执行任务时不释放沙箱，让任务继续后台执行
  if (chatStore.isProcessing) return;
  const sandboxSessionId = lastInitializedSessionThreadId || chatStore.sessionThreadId;
  if (!sandboxSessionId) return;
  // 先清空，避免同一条会话被重复释放
  lastInitializedSessionThreadId = '';
  chatStore.releaseSandboxContainer(sandboxSessionId);
}

// 处理智能体选择
const handleSelectAgent = async (agentId: string, forceNewChat = false) => {
  chatStore.detachCurrentConversation();
  if (selectedAgentId.value === agentId && !forceNewChat) {
    return await exitAgentMode();
  } else {
    const selectedAgent = localAgentList.value.find(agent => agent.id === agentId);
    if (!selectedAgent) {
      return;
    }

    try {
      const needInitialization = shouldInitializeAgentSession(selectedAgent);
      const retainedPrevious = selectedAgentId.value !== agentId && chatStore.retainCurrentAgentSession();
      // 备用池按智能体隔离，不能把其他智能体的沙盒重新绑定给当前智能体。
      // 已发送过消息的会话仍由历史/后台任务管理，只有空白草稿允许复用。
      const warmSessionId = chatStore.resolveWarmSandboxSessionId(resolveAgentUuid(selectedAgent));
      const targetSessionId = needInitialization ? (warmSessionId || undefined) : undefined;

      const previousId = chatStore.sessionThreadId;
      if (!retainedPrevious && previousId !== targetSessionId && chatStore.isReusableSession(previousId)) {
        chatStore.releaseSandboxContainer(previousId);
      }
      applyAgentSelection(selectedAgent);
      // 新对话不重新生成会话 ID：复用上文决定的 targetSessionId
      chatStore.clearChat({ regenerateSessionThreadId: false });

      if (needInitialization) {
        // 后台准备上下文；同一会话复用就绪记录或进行中的请求。
        // 状态在输入框内呈现，失败时自动退回普通模式。
        const initPromise = chatStore.startAgentInit(resolveAgentUuid(selectedAgent), targetSessionId, () => true, { reusable: true });
        // startAgentInit 已同步落地会话 ID，此处即可读到最终 ID
        lastInitializedSessionThreadId = chatStore.sessionThreadId;
        void initPromise.catch((error: unknown) => { console.error('智能体初始化失败:', error); });
      } else {
        chatStore.regenerateSessionThreadId();
        lastInitializedSessionThreadId = '';
        chatStore.resetAgentInit();
      }

      setTimeout(() => {
        window.dispatchEvent(new Event('mcp-models-changed'));
      }, 100);
    } catch (error) {
      console.error('初始化智能体会话时出错:', error);
      return false;
    }
    restoreSessionPromise ??= Promise.resolve();
    return true;
  }
};

const findAgent = (id: string) => localAgentList.value.find(agent => String(agent.id) === id || resolveAgentUuid(agent) === id);

function applyAgentSelection(agent: AgentInfo) {
  selectedAgentId.value = agent.id;
  StorageService.setSelectedAgent(agent.id);
  StorageService.setActiveAgent(agent.config);
  window.dispatchEvent(new CustomEvent('agent-selection-changed', { detail: { selected: true, agentId: agent.id } }));
  window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: agent.config } }));
}

function syncAgentSelectionForSession(agentKey: string) {
  const key = String(agentKey || '').trim();
  if (!key) return false;

  let agent = findAgent(key);
  if (!agent?.config) {
    const cachedAgents = StorageService.getAgents() || [];
    agent = cachedAgents.find((item: any) => String(item?.id) === key || resolveAgentUuid(item) === key);
    if (agent?.config && !localAgentList.value.some((item) => item.id === agent?.id)) {
      localAgentList.value = [...localAgentList.value, agent as AgentInfo];
    }
  }
  if (!agent?.config) return false;

  applyAgentSelection(agent);
  return true;
}

async function startNewAgentChat(id: string) {
  await loadLocalAgents();
  const agent = findAgent(id);
  if (!agent) {
    NotificationService.info('该智能体已不可用，请在智能体管理中检查');
    return;
  }
  await handleSelectAgent(agent.id, true);
}

async function focusAgent(id: string) {
  await loadLocalAgents();
  const agent = findAgent(id);
  if (!agent) {
    NotificationService.info('该智能体已不可用');
    return;
  }
  activeAgentScope.value = getAgentOwnership(agent);
  searchQuery.value = '';
  typeFilter.value = 'all';
  await nextTick();
  agentListContainer.value?.querySelector(`[data-agent-id="${CSS.escape(String(agent.id))}"]`)?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

defineExpose({ startNewAgentChat, focusAgent, activateAgentForSession, exitAgentMode, reinitAgentForNewChat, syncAgentSelectionForSession });

const focusCreatedAgent = async (agent: AgentInfo) => { await focusAgent(String(agent.id)); };

const addAgentModalVisible = ref(false);
const currentEditingAgent = ref<any>(null);
const isEditMode = ref(false);
const AGENT_ENTITY_TYPE = 3;
const isCurrentUserAdmin = computed(() => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) return false;
    const profile = JSON.parse(raw);
    return String(profile?.username || '').trim().toLowerCase() === 'admin';
  } catch (_) {
    return false;
  }
});

const resolveAgentVisibility = (agent: any): 'private' | 'public' => {
  const visibility = String(agent?.visibility || agent?.config?.basic?.visibility || '').trim().toLowerCase();
  return visibility === 'public' ? 'public' : 'private';
};
const isSharedAgentReadonly = (agent: any): boolean =>
  !isCurrentUserAdmin.value && resolveAgentVisibility(agent) === 'public';

// 创建智能体时按当前筛选预选默认值：类型沿用类型筛选，归属"共享"对应公开可见性
const createDefaults = computed<{ type?: string; visibility?: 'private' | 'public' }>(() => ({
  type: typeFilter.value !== 'all' ? typeFilter.value : undefined,
  visibility: activeAgentScope.value === 'shared' ? 'public' : 'private'
}));

const handleAddAgent = () => {
  addAgentModalVisible.value = true;
};

const handleEditAgent = async (agent: any) => {
  // 智能体正在使用中时禁止编辑，需先退出智能体
  if (selectedAgentId.value === agent?.id) {
    NotificationService.info('该智能体正在使用中，请先退出智能体后再进行编辑');
    return;
  }
  let enriched = agent;
  try {
    const hasOrchestrator = !!(agent?.config?.orchestrator && (agent.config.orchestrator.serviceUrl || agent.config.orchestrator.url || agent.config.orchestrator.endpoint || agent.config.orchestrator.apiUrl));
    if (!hasOrchestrator) {
      await refreshAgentsFromBackend();
      const updated = localAgentList.value.find(a => a.id === agent.id);
      if (updated) {
        enriched = updated;
      }
    }
  } catch (e) {
  }
  currentEditingAgent.value = enriched;
  isEditMode.value = true;
  addAgentModalVisible.value = true;
};

// 处理编辑智能体（先关闭下拉菜单）
const handleEditAgentWithClose = (agent: any, agentId: string) => {
  closeDropdown(agentId);
  setTimeout(() => {
    handleEditAgent(agent);
  }, 0);
};

const extractAgentUuid = (response: any, fallbackUuid?: string) => {
  const candidates = [
    response?.data?.uuid,
    response?.uuid,
    fallbackUuid
  ];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim()) {
      return candidate.trim();
    }
  }

  return '';
};

const normalizePermissionGroupIds = (groupIds: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(groupIds) ? groupIds : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

const syncAgentPermissionGroups = async (
  agentUuid: string,
  targetGroupIds: string[],
  existingGroupIdsSource: string[] = []
) => {
  const targetGroupIdsNormalized = normalizePermissionGroupIds(targetGroupIds);
  const existingGroupIds = normalizePermissionGroupIds(existingGroupIdsSource);
  const nextPermissionByGroupId = new Map<string, 1 | 2>();

  existingGroupIds.forEach((groupId) => {
    nextPermissionByGroupId.set(groupId, targetGroupIdsNormalized.includes(groupId) ? 1 : 2);
  });
  targetGroupIdsNormalized.forEach((groupId) => {
    nextPermissionByGroupId.set(groupId, 1);
  });

  for (const [groupId, permission] of nextPermissionByGroupId.entries()) {
    await updateAiPermission({
      group_id: groupId,
      list: [
        {
          entity_id: agentUuid,
          entity_type: AGENT_ENTITY_TYPE,
          permission
        }
      ]
    });
  }
};

// 处理添加/编辑智能体 确认：后端驱动 + 列表刷新缓存
const handleAddAgentConfirm = async (agentData: any) => {
  let createdAgentToFocus: AgentInfo | null = null;
  try {
    if (isEditMode.value && currentEditingAgent.value && isSharedAgentReadonly(currentEditingAgent.value)) {
      NotificationService.info('非 admin 用户不能修改共享智能体');
      return;
    }
    const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
    const agentType = agentData.basic?.type || 'assistant';
    const isDeepAgent = agentType === 'deepagent';
    const oldVisibility = isEditMode.value && currentEditingAgent.value
      ? resolveAgentVisibility(currentEditingAgent.value)
      : 'private';
    const requestedVisibility = String(agentData?.basic?.visibility || '').toLowerCase() === 'public' ? 'public' : 'private';
    const visibility = isEditMode.value
      ? (isCurrentUserAdmin.value ? requestedVisibility : oldVisibility)
      : (isCurrentUserAdmin.value ? requestedVisibility : 'private');
    const skills = isDeepAgent && Array.isArray(agentData.skills) ? agentData.skills : [];
    const basicConfig = {
      ...(agentData.basic || {})
    } as Record<string, any>;
    basicConfig.visibility = visibility;

    const payload = {
      uuid: isEditMode.value && currentEditingAgent.value ? (currentEditingAgent.value as any).uuid : undefined,
      id: isEditMode.value && currentEditingAgent.value ? currentEditingAgent.value.id : `agent-${Date.now()}`,
      name: agentData.basic?.name,
      description: agentData.basic?.description,
      themeColor: agentData.basic?.themeColor,
      agent_type: agentType,
      visibility,
      config: {
        basic: basicConfig,
        prompt: { ...(agentData.prompt || {}) },
        model: {
          service: agentData.model?.service,
          name: agentData.model?.name,
          temperature: agentData.model?.temperature,
          top_p: agentData.model?.top_p,
          presence_penalty: agentData.model?.presence_penalty,
          frequency_penalty: agentData.model?.frequency_penalty,
          apiKey: agentData.model?.apiKey,
          apiUrl: sanitizeUrl(agentData.model?.apiUrl)
        },
        knowledge: { ...(agentData.knowledge || {}) },
        mcp: { ...(agentData.mcp || {}) },
        orchestrator: { serviceUrl: sanitizeUrl(agentData.orchestrator?.serviceUrl) },
        ...(isDeepAgent ? { skills } : { skills: [] }),
        phrases: Array.isArray(agentData.phrases) ? agentData.phrases : [],
        memory: { enabled: agentData.memory?.enabled ?? false },
        env_vars: agentData.env_vars || {}
      }
    } as any;
    let savedAgentUuid = String(payload.uuid || '').trim();

    if (isEditMode.value && currentEditingAgent.value) {
      const updateResult = await updateAiAgent(payload);
      savedAgentUuid = extractAgentUuid(updateResult, savedAgentUuid);

      // 编辑场景优先做本地增量更新，避免每次都全量拉取智能体列表
      const targetId = currentEditingAgent.value.id;
      const index = localAgentList.value.findIndex(agent => agent.id === targetId);
      if (index > -1) {
        const prevAgent = localAgentList.value[index] as any;
        const nextAgent = {
          ...prevAgent,
          name: payload.name,
          description: payload.description,
          themeColor: payload.themeColor,
          agent_type: payload.agent_type,
          visibility: payload.visibility,
          config: {
            ...(prevAgent?.config || {}),
            ...(payload.config || {}),
            basic: {
              ...(prevAgent?.config?.basic || {}),
              ...(payload.config?.basic || {}),
              visibility: payload.visibility
            }
          }
        } as any;
        localAgentList.value.splice(index, 1, nextAgent);
        StorageService.setAgents(localAgentList.value as any);
        window.dispatchEvent(new Event('agents-updated'));
      } else {
        // 兜底：本地未命中时仍走全量刷新
        await refreshAgentsFromBackend();
      }
    } else {
      const previousAgentIds = new Set(localAgentList.value.map(agent => agent.id));
      const addResult = await addAiAgent(payload);
      savedAgentUuid = extractAgentUuid(addResult, savedAgentUuid);

      // 新增场景需要拿到后端分配的完整数据，保持全量刷新
      await refreshAgentsFromBackend();

      // 定位本次新增的智能体，用于后续聚焦
      createdAgentToFocus = localAgentList.value.find(agent => savedAgentUuid && (agent as any).uuid === savedAgentUuid)
        || localAgentList.value.find(agent => !previousAgentIds.has(agent.id))
        || null;
    }

    if (isCurrentUserAdmin.value && savedAgentUuid) {
      const permissionGroupIds = visibility === 'public'
        ? normalizePermissionGroupIds(agentData?.permissionGroupIds)
        : [];
      const originalPermissionGroupIds = isEditMode.value
        ? normalizePermissionGroupIds(agentData?.originalPermissionGroupIds)
        : [];
      await syncAgentPermissionGroups(savedAgentUuid, permissionGroupIds, originalPermissionGroupIds);
    }

    // 如果编辑的是当前选中的智能体，更新活跃配置与连接
    if (isEditMode.value && currentEditingAgent.value && selectedAgentId.value === currentEditingAgent.value.id) {
      const updatedAgent = localAgentList.value.find(agent => agent.id === currentEditingAgent.value.id);
      if (updatedAgent && updatedAgent.config) {
        StorageService.setActiveAgent(updatedAgent.config);
        window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: updatedAgent.config } }));

        const agentModelConfig = updatedAgent.config.model || {};
        const apiKey = agentModelConfig.apiKey;
        const apiBaseUrl = agentModelConfig.apiUrl;
        const model = agentModelConfig.name;

        if (model && apiKey && apiBaseUrl) {
          configStore.apiKey = apiKey;
          configStore.apiBaseUrl = apiBaseUrl;
          configStore.model = model;
          configStore.saveConfig();
          chatStore.setApiKey(apiKey);
          chatStore.setApiBaseUrl(apiBaseUrl);
          chatStore.setModel(model);
        }

        window.dispatchEvent(new Event('mcp-models-changed'));
      }
    }

    // 新增成功：在工作台聚焦新卡片，不切换当前会话
    if (createdAgentToFocus) {
      await focusCreatedAgent(createdAgentToFocus);
    }
  } finally {
    currentEditingAgent.value = null;
    isEditMode.value = false;
    addAgentModalVisible.value = false;
  }
};

// 处理添加智能体取消
const handleAddAgentCancel = () => {
  // 重置编辑状态
  currentEditingAgent.value = null;
  isEditMode.value = false;
  addAgentModalVisible.value = false;
};

// 处理删除智能体
const handleDeleteAgent = async (agentId: string) => {
  const target = localAgentList.value.find(a => a.id === agentId) as any;
  if (target && isSharedAgentReadonly(target)) {
    NotificationService.info('非 admin 用户不能删除共享智能体');
    return;
  }
  const uuid = target?.uuid;
  if (!uuid) return;
  try {
    await deleteAiAgent({ uuid });
    await refreshAgentsFromBackend();
    if (selectedAgentId.value === agentId) {
      selectedAgentId.value = null;
      StorageService.setSelectedAgent(null);
      chatStore.clearChat();
      StorageService.removeActiveAgent();
      StorageService.remove('mcp-original-config');
      window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: null } }));
      window.dispatchEvent(new CustomEvent('agent-selection-changed', { detail: { selected: false, agentId: null } }));
      try {
        const list = await getPrompt();
        const first = list[0] || '';
        if (first.trim()) {
          const text = first.trim();
          chatStore.setSystemMessage(text, false);
        }
      } catch (_) { }
      try { await getPrompt(); } catch (_) { }
    }
  } finally {
    currentEditingAgent.value = null;
    isEditMode.value = false;
    addAgentModalVisible.value = false;
  }
};

// 切换搜索框显示状态
// 获取模型显示名称
const getModelDisplayName = (agent: AgentInfo) => {
  if (!agent.config?.model?.name) {
    return '未配置';
  }
  return agent.config.model.name;
};

// 底部信息栏文案：编排式展示执行方式，未选模型时提示未配置模型
const getCardBarLabel = (agent: AgentInfo) => {
  if (getAgentType(agent) === 'orchestrator') {
    return '编排工作流';
  }
  return agent.config?.model?.name ? agent.config.model.name : '未配置模型';
};

// 未配置模型时底部栏不展示徽标，只留文案
const showCardBarIcon = (agent: AgentInfo) => {
  return getAgentType(agent) === 'orchestrator' || !!agent.config?.model?.name;
};

// 底部信息栏的模型徽标：与消息区沿用同一套品牌匹配规则
const getModelIcon = (agent: AgentInfo) => {
  if (getAgentType(agent) === 'orchestrator') {
    return null;
  }
  const target = getModelDisplayName(agent).toLowerCase();
  if (shouldShowModelIcon(target, 'qwen')) return QwenIcon;
  if (shouldShowModelIcon(target, 'deepseek')) return DeepSeekIcon;
  if (target.includes('glm')) return target.includes('z') ? ZaiIcon : ZhipuIcon;
  return null;
};

const getAgentType = (agent: AgentInfo) => resolveAgentType(agent);

// 头像底色直接取接口返回的 themeColor，不再按智能体类型派生
const getAgentThemeColor = (agent: AgentInfo) => agent.themeColor || agent.config?.basic?.themeColor || '';

// 渲染层统一解析头像：兼容 localStorage 中的稳定 key / dev 路径 / 旧打包路径
const getAgentAvatar = (agent: AgentInfo) => resolveAgentAvatar(agent.config?.basic?.avatar);

const isAgentActivated = (agent: AgentInfo) => selectedAgentId.value === agent.id;

const getAgentTypeLabel = (agent: AgentInfo) => {
  const agentType = getAgentType(agent);
  if (agentType === 'orchestrator') {
    return '内置编排式智能体';
  }
  if (agentType === 'deepagent') {
    return 'DeepAgent';
  }
  return '通用智能体';
};

const getAgentDescription = (agent: AgentInfo) =>
  agent.description || '为你的任务提供专业支持，开启对话探索更多可能。';

// 获取MCP服务器数量
const getMcpServerCount = (agent: AgentInfo) => {
  if (!agent.config?.mcp?.enabledServerIdentifiers) {
    return 0;
  }
  return agent.config.mcp.enabledServerIdentifiers.length;
};

// 获取知识库状态
const getKnowledgeStatus = (agent: AgentInfo) => {
  if (!agent.config?.knowledge?.enabled) {
    return '未启用';
  }
  const raw = agent.config?.knowledge?.selectedKnowledge;
  const list = Array.isArray(raw)
    ? raw.filter((name: any) => typeof name === 'string' && name)
    : (typeof raw === 'string' && raw ? [raw] : []);
  if (!list.length) return '已启用';
  if (list.length === 1) return list[0];
  return `${list[0]} 等 ${list.length} 个`;
};

// 将启用的 MCP 服务器标识符解析为可读名称（读取本地缓存中的服务器名称）
const resolveMcpServerNames = (agent: AgentInfo): string[] => {
  const identifiers = Array.isArray(agent.config?.mcp?.enabledServerIdentifiers)
    ? agent.config.mcp.enabledServerIdentifiers
    : [];
  if (!identifiers.length) return [];

  try {
    const raw = localStorage.getItem('mcp-servers-data');
    const dataMap = raw ? JSON.parse(raw) : {};
    const map: Record<string, any> = dataMap && typeof dataMap === 'object' ? dataMap : {};

    return identifiers.map((identifier: string) => {
      const direct = map[identifier];
      if (direct?.name) return String(direct.name);

      // 兼容“名称|URL”形式的旧标识符
      const pipeIndex = identifier.lastIndexOf('|');
      if (pipeIndex > 0) {
        const maybeName = identifier.slice(0, pipeIndex);
        const byName = Object.values(map).find((server: any) => server?.name === maybeName);
        if (byName?.name) return String(byName.name);
      }

      // 兼容直接以名称作为标识符的情况
      const byName = Object.values(map).find((server: any) => server?.name === identifier);
      if (byName?.name) return String(byName.name);

      return String(identifier);
    });
  } catch (_) {
    return identifiers.map(String);
  }
};

// MCP 工具提示：列出已启用的具体服务名称
const getMcpTooltip = (agent: AgentInfo): string => {
  const names = resolveMcpServerNames(agent);
  if (!names.length) return '未启用 MCP 服务';
  return `已启用 ${names.length} 个 MCP 服务：${names.join('、')}`;
};

// 归一化知识库名称列表
const getKnowledgeNames = (agent: AgentInfo): string[] => {
  const raw = agent.config?.knowledge?.selectedKnowledge;
  if (Array.isArray(raw)) return raw.filter((name: any) => typeof name === 'string' && name);
  if (typeof raw === 'string' && raw) return [raw];
  return [];
};

// 知识库提示：列出已启用的具体知识库名称
const getKnowledgeTooltip = (agent: AgentInfo): string => {
  if (!agent.config?.knowledge?.enabled) return '未启用知识库';
  const names = getKnowledgeNames(agent);
  if (!names.length) return '已启用知识库，但未选择具体知识库';
  return `已启用知识库：${names.join('、')}`;
};

// 记忆提示
const getMemoryTooltip = (agent: AgentInfo): string =>
  agent.config?.memory?.enabled ? '记忆功能已开启' : '记忆功能未开启';

// 添加dropdownVisible响应式变量
const dropdownVisible = ref<Record<string, boolean>>({});

// 处理下拉菜单显示状态变化
const handleDropdownVisibleChange = (agentId: string, visible: boolean) => {
  dropdownVisible.value[agentId] = visible;
};

// 添加关闭下拉菜单的方法
const closeDropdown = (agentId: string) => {
  dropdownVisible.value[agentId] = false;
};

// 处理删除智能体确认
const handleDeleteAgentConfirm = (agent: AgentInfo) => {
  if (isSharedAgentReadonly(agent)) {
    NotificationService.info('非 admin 用户不能删除共享智能体');
    return;
  }
  // 关闭下拉菜单
  dropdownVisible.value[agent.id] = false;

  // 使用Ant Design的Modal组件显示确认对话框
  Modal.confirm({
    title: '确认删除',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: '确定要删除这个智能体吗？此操作不可撤销。',
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: async () => {
      const target = localAgentList.value.find(a => a.id === agent.id) as any;
      const uuid = target?.uuid;
      if (!uuid) return;
      await deleteAiAgent({ uuid });
      await refreshAgentsFromBackend();

      if (selectedAgentId.value === agent.id) {
        selectedAgentId.value = null;
        StorageService.setSelectedAgent(null);

        // 重置对话历史
        chatStore.clearChat();

        // 清除活动智能体标识
        StorageService.removeActiveAgent();

        // 删除当前选中智能体后清理原始配置键值
        StorageService.remove('mcp-original-config');
        window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: null } }));
        window.dispatchEvent(new CustomEvent('agent-selection-changed', { detail: { selected: false, agentId: null } }));
      }
    },
    onCancel: () => {
      // 用户取消删除，不执行任何操作
    }
  });
};

// 处理删除智能体确认（先关闭下拉菜单）
const handleDeleteAgentConfirmWithClose = (agent: AgentInfo, agentId: string) => {
  closeDropdown(agentId);
  setTimeout(() => {
    handleDeleteAgentConfirm(agent);
  }, 0);
};

// 智能体会话恢复：需要「列表已就绪」且「处于对话工作区」两个条件，且每次挂载只执行一次
let agentListReady = false;
let chatWorkspaceRestoreRequested = false;
let restoreSessionPromise: Promise<void> | null = null;

const doRestoreActiveAgentSession = async () => {
  // 恢复身份即可；初始化由 ChatView 查询流状态后统一处理。
  const agent = localAgentList.value.find(item => item.id === selectedAgentId.value);
  if (agent?.config) applyAgentSelection(agent);
};

const restoreActiveAgentSession = () => {
  if (restoreSessionPromise || !chatWorkspaceRestoreRequested || !agentListReady) {
    return restoreSessionPromise ?? Promise.resolve();
  }
  // 无论本次是否存在待恢复的智能体，都只尝试一次，避免后续手动选择的智能体被重复初始化
  restoreSessionPromise = doRestoreActiveAgentSession();
  return restoreSessionPromise;
};

// 进入对话工作区（含刷新后回到对话界面）时才触发恢复
watch(() => props.chatWorkspaceActive, (active) => {
  if (!active) return;
  chatWorkspaceRestoreRequested = true;
  void restoreActiveAgentSession();
}, { immediate: true });

/**
 * 从历史记录进入某个智能体的会话时激活该智能体：
 * 复用历史记录的会话 ID 初始化，且不清空已恢复的消息
 */
async function activateAgentForSession(agentKey: string, sessionThreadId: string, isCurrent: () => boolean = () => true) {
  const canCommit = () => isCurrent() && chatStore.sessionThreadId === sessionThreadId;
  if (!canCommit()) return false;
  const key = String(agentKey || '').trim();
  if (!key) return false;

  let agent = findAgent(key);
  if (!agent?.config) {
    // 刷新后立即点击历史记录时列表可能还没加载完，回退读取本地缓存
    await loadLocalAgents();
    if (!canCommit()) return false;
    agent = findAgent(key);
  }
  if (!agent?.config) return false;

  // 等待刷新后的自动恢复结束，避免两条初始化链路互相覆盖会话 ID
  if (restoreSessionPromise) await restoreSessionPromise;
  if (!canCommit()) return false;

  const isSameAgent = selectedAgentId.value === agent.id;
  const targetSessionId = String(sessionThreadId || '').trim();
  // 同一智能体且会话未变化：沿用已初始化上下文，不释放也不重复初始化
  const isSameLiveSession = isSameAgent && targetSessionId && targetSessionId === lastInitializedSessionThreadId;

  // 切换到其他智能体 / 其他会话前，后台释放旧 DeepAgent 沙箱（不阻塞切换）
  if (!isSameLiveSession) {
    releaseCurrentDeepAgent();
    if (!canCommit()) return false;
  }

  applyAgentSelection(agent);

  // 是否就绪由 store 按会话统一判断，不能仅凭最近一次 ID 跳过。

  const needInitialization = shouldInitializeAgentSession(agent);

  try {
    if (needInitialization) {
      // 后台初始化，状态在输入框内呈现，不阻塞整屏；
      // 由 store 判断目标会话可否复用，避免重复初始化
      const initPromise = chatStore.startAgentInit(resolveAgentUuid(agent), sessionThreadId, canCommit, { reusable: false });
      lastInitializedSessionThreadId = sessionThreadId;
      await initPromise;
      if (!canCommit()) return false;
    } else {
      lastInitializedSessionThreadId = '';
      chatStore.resetAgentInit();
    }

    window.dispatchEvent(new Event('mcp-models-changed'));
    return true;
  } catch (error) {
    console.error('历史记录激活智能体会话时出错:', error);
    return false;
  }
}

/**
 * 全局「新对话」：保持当前智能体激活，用清空后的新会话 ID 重新初始化。
 * 否则新会话在后端没有智能体上下文，继续追问会失败。
 * 若存在已预热就绪的备用沙盒容器，则直接取用其会话 ID，跳过等待容器启动。
 */
async function reinitAgentForNewChat() {
  if (!selectedAgentId.value) return false;

  const agent = localAgentList.value.find(item => item.id === selectedAgentId.value);
  if (!agent?.config || !shouldInitializeAgentSession(agent)) return false;

  try {
    // 新对话入口已分配独立会话 ID（或取用预热容器），在此初始化该 ID。
    const targetSessionId = chatStore.sessionThreadId;
    const initPromise = chatStore.startAgentInit(resolveAgentUuid(agent), targetSessionId, () => true, { reusable: true });
    // startAgentInit 已同步落地会话 ID
    lastInitializedSessionThreadId = chatStore.sessionThreadId;
    await initPromise;
    return true;
  } catch (error) {
    console.error('新对话重新初始化智能体时出错:', error);
    return false;
  }
}

// 保持工作台挂载，让历史会话恢复与页面切换共用同一份智能体状态。
onMounted(async () => {
  window.addEventListener('agents-updated', handleAgentsUpdated);
  window.addEventListener('agent-selection-changed', syncSelectedAgentState as EventListener);
  await refresh();
  agentListReady = true;
  // 智能体列表就绪后立即后台预热备用沙盒容器，与会话恢复初始化并行，
  // 不必等恢复用的容器启动完成（最长 60s）才开始预热
  const prewarmAgent = localAgentList.value.find(agent => agent.id === selectedAgentId.value)
    || localAgentList.value.find(agent => shouldInitializeAgentSession(agent));
  if (prewarmAgent) {
    void chatStore.prewarmSandbox(resolveAgentUuid(prewarmAgent));
  }
  await restoreActiveAgentSession();
});
onUnmounted(() => {
  chatStore.discardSpareSandbox();
  window.removeEventListener('agents-updated', handleAgentsUpdated);
  window.removeEventListener('agent-selection-changed', syncSelectedAgentState as EventListener);
});
</script>

<style scoped src="@/assets/styles/agent-workspace.css"></style>
