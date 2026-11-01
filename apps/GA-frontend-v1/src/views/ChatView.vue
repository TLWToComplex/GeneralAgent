<template>
  <div class="chat-page-shell">
    <transition name="history-sider">
      <div v-if="isHistoryRailVisible" class="history-sider-host">
        <HistorySider
          :items="historyItems"
          :running-session-ids="runningSessionIds"
          :loading="historyLoading"
          :active-session-thread-id="pendingHistorySessionId || activeSessionThreadId"
          :active-workspace="activeWorkspace"
          @collapse="handleCollapseHistorySidebar"
          @open-agent="handleOpenAgentWorkspace"
          @agent-new-chat="handleAgentNewChat"
          @manage-agent="handleManageHistoryAgent"
          @open-knowledge="handleOpenKnowledgeWorkspace"
          @open-delivery="handleOpenDeliveryWorkspace"
          @new-chat="handleNewChatFromHistory"
          @select="handleSelectHistoryRecord"
          @rename="handleRenameHistoryRecord"
          @delete="handleDeleteHistoryRecord"
        />
      </div>
    </transition>

    <div
      :class="{ 'with-history-rail': isHistoryRailVisible }"
      class="main-container"
    >
      <!-- 左侧浮动按钮工具栏：历史侧栏展开时隐藏 -->
      <transition name="fade">
        <div v-if="!isHistoryRailVisible" class="left-float-toolbar-stack">
          <div class="left-float-toolbar">
            <a-tooltip placement="right">
              <template #title>展开侧栏</template>
              <button
                type="button"
                class="left-float-toolbar-btn is-primary"
                aria-label="展开侧栏"
                @click="handleToggleHistorySidebar"
              >
                <span class="left-float-toolbar-swap-icon" aria-hidden="true">
                  <img :src="logoImage" alt="" class="left-float-toolbar-logo" />
                  <img :src="sidebarCollapseIcon" alt="" class="left-float-toolbar-expand-icon" />
                </span>
              </button>
            </a-tooltip>
            <a-tooltip placement="right">
              <template #title>新对话</template>
              <button
                type="button"
                class="left-float-toolbar-btn"
                aria-label="新对话"
                @click="handleNewChatFromHistory"
              >
                <img :src="newChatNavIcon" alt="" class="left-float-toolbar-icon is-lg" />
              </button>
            </a-tooltip>
            <a-tooltip placement="right">
              <template #title>智能体</template>
              <button
                type="button"
                class="left-float-toolbar-btn"
                aria-label="智能体"
                :class="{ 'is-active': activeWorkspace === 'agents' }"
                :aria-pressed="activeWorkspace === 'agents'"
                @click="handleOpenAgentWorkspace"
              >
                <img :src="agentNavIcon" alt="" class="left-float-toolbar-icon" />
              </button>
            </a-tooltip>
            <a-tooltip placement="right">
              <template #title>交付中心</template>
              <button
                type="button"
                class="left-float-toolbar-btn"
                :class="{ 'is-active': activeWorkspace === 'delivery' }"
                aria-label="交付中心"
                :aria-pressed="activeWorkspace === 'delivery'"
                @click="handleOpenDeliveryWorkspace"
              >
                <img :src="vectorNavIcon" alt="" class="left-float-toolbar-icon" />
              </button>
            </a-tooltip>
            <a-tooltip placement="right">
              <template #title>知识库</template>
              <button
                type="button"
                class="left-float-toolbar-btn"
                :class="{ 'is-active': activeWorkspace === 'knowledge' }"
                aria-label="知识库"
                :aria-pressed="activeWorkspace === 'knowledge'"
                @click="handleOpenKnowledgeWorkspace"
              >
                <img :src="knowledgeNavIcon" alt="" class="left-float-toolbar-icon is-lg" />
              </button>
            </a-tooltip>
          </div>

          <div class="left-float-toolbar left-float-toolbar-secondary">
            <a-tooltip placement="right">
              <template #title>设置</template>
              <button
                type="button"
                class="left-float-toolbar-btn"
                aria-label="设置"
                @click="handleOpenSettings"
              >
                <SettingOutlined class="left-float-toolbar-ant-icon" />
              </button>
            </a-tooltip>
          </div>
        </div>
      </transition>

      <!-- ChatHeader组件移到内容区顶层 -->
      <div class="chat-header-host">
        <ChatHeader
          v-model:isAgentMode="isAgentMode"
          v-model:showModelSelector="showModelSelector"
          :active-panel="showCanvas ? 'canvas' : 'deliverables'"
          :show-panel-tabs="shouldShowPanelTabs"
          :active-workspace="activeWorkspace"
          @switch-panel="switchRightPanel"
          @new-chat="handleNewChatFromHistory"
        />
      </div>

      <Transition name="workspace-fade">
        <KeepAlive>
          <KnowledgeBaseView
            v-if="activeWorkspace === 'knowledge'"
            layout="workspace"
            @back="handleBackToChat"
          />
        </KeepAlive>
      </Transition>

      <Transition name="workspace-fade">
        <DeliveryCenterView v-if="activeWorkspace === 'delivery'" :conversations="historyItems" @open-conversation="handleSelectHistoryRecord" />
      </Transition>

      <Transition name="workspace-fade">
        <AgentWorkspace
          v-show="activeWorkspace === 'agents'"
          ref="agentWorkspaceRef"
          :chat-workspace-active="activeWorkspace === 'chat'"
          @start-chat="handleBackToChat"
        />
      </Transition>

      <!-- 切换智能体模态框（输入框智能体按钮触发） -->
      <AgentPickerModal
        v-model:open="agentPickerOpen"
        @select-agent="handleAgentPickerSelect"
        @browse-agents="handleOpenAgentWorkspace"
      />

      <!-- 右侧聊天区域 -->
      <Transition name="workspace-fade">
      <div v-show="activeWorkspace === 'chat'" class="chat-layout">
        <div :class="{ 'full-width': true, 'has-right-panel': shouldShowRightPanel, 'has-bottom-input': showBottomInput, 'is-history-switching': !!pendingHistorySessionId }" class="chat-col">
          <div class="chat-container">
          <Transition name="history-loading">
            <HistoryConversationLoading v-if="pendingHistorySessionId" :key="pendingHistorySessionId" :content-style="historyLoadingContentStyle" />
          </Transition>
          <div class="history-content-host" :class="{ 'is-loading': pendingHistorySessionId, 'is-entering': historyContentEntering }" :inert="!!pendingHistorySessionId" :aria-hidden="pendingHistorySessionId ? true : undefined">
          <!-- 当没有消息时，欢迎语与输入框作为一组垂直居中显示 -->
          <div v-if="showWelcomeGroup" class="welcome-group">
            <WelcomeMessage :active-agent="activeAgent" @select-agent="handleWelcomeAgentSelect" @browse-agents="handleOpenAgentWorkspace"/>

            <transition mode="out-in" name="input-center">
              <ChatInput
                  ref="chatInputWelcomeRef"
                  :has-selection="hasSelection"
                  :is-all-selected="isAllSelected"
                  :is-selection-mode="isSelectionMode"
                  :is-welcome-active="true" :selected-messages="selectedMessages"
                  :active-artifact-id="activeArtifactId"
                  @toggle-all="handleToggleAll"
                  @cancel-selection="handleCancelSelection"
                  @copy-selected="handleCopySelected"
                  @export-text="handleExportText"
                  @export-markdown="handleExportMarkdown"
                  @toggle-canvas="handleToggleCanvas"
                  @new-chat="handleNewChat"
                  @toolbar-visibility-change="handleToolbarVisibilityChange"
                  @toolbar-expand-change="handleToolbarExpandChange"
                  @toolbar-panel-height-change="handleToolbarPanelHeightChange"
                  @input-height-change="handleInputHeightChange"
                  @message-submit="handleMessageSubmit"
                  @open-artifact="handleOpenArtifact"
              />
            </transition>
          </div>

          <!-- 有消息时显示聊天历史与输入框 -->
          <template v-else>
            <ChatHistory
              ref="chatHistoryRef"
              :history-session-id="pendingHistorySessionId"
              :is-agent-mode="isAgentMode"
              :input-toolbar-visible="isInputToolbarVisible"
              :input-toolbar-expanded="isInputToolbarExpanded"
              :input-toolbar-panel-height="inputToolbarPanelHeight"
              :input-height="inputHeight"
              :active-artifact-id="activeArtifactId"
              @selection-mode-changed="handleSelectionModeChanged"
              @all-selected-changed="handleAllSelectedChanged"
              @selection-changed="handleSelectionChanged"
              @open-artifact="handleOpenArtifact"
          />

            <transition mode="out-in" name="input-bottom">
              <ChatInput
                  v-if="showBottomInput"
                  ref="chatInputBottomRef"
                  :has-selection="hasSelection"
                  :is-all-selected="isAllSelected"
                  :is-selection-mode="isSelectionMode"
                  :is-welcome-active="false"
                  :selected-messages="selectedMessages"
                  :active-artifact-id="activeArtifactId"
                  @toggle-all="handleToggleAll"
                  @cancel-selection="handleCancelSelection"
                  @copy-selected="handleCopySelected"
                  @export-text="handleExportText"
                  @export-markdown="handleExportMarkdown"
                  @toggle-canvas="handleToggleCanvas"
                  @new-chat="handleNewChat"
                  @toolbar-visibility-change="handleToolbarVisibilityChange"
                  @toolbar-expand-change="handleToolbarExpandChange"
                  @toolbar-panel-height-change="handleToolbarPanelHeightChange"
                  @input-height-change="handleInputHeightChange"
                  @message-submit="handleMessageSubmit"
                  @open-artifact="handleOpenArtifact"
              />
            </transition>
          </template>
          </div>
          </div>

          <!-- 右侧面板：画布 / 交付中心 双 Tab -->
          <transition name="canvas-expand" :css="!pendingHistorySessionId" @before-enter="onCanvasTransitionStart" @after-enter="onCanvasTransitionEnd" @before-leave="onCanvasTransitionStart" @after-leave="onCanvasTransitionEnd">
            <div
              v-if="shouldRenderRightPanel"
              v-show="shouldShowRightPanel"
              class="right-panel"
            >
              <div class="right-panel-body">
                <transition name="panel-fade" :css="!pendingHistorySessionId">
                  <div v-show="showCanvas" class="panel-slot">
                    <CanvasPanel
                      ref="canvasPanelRef"
                      :suspend-docx="isCanvasAnimating || activeWorkspace !== 'chat'"
                      @close="handleCloseCanvas"
                      @screenshot="handleScreenshot"
                      @screenshot-start="handleScreenshotStart"
                    />
                  </div>
                </transition>
                <transition name="panel-fade" :css="!pendingHistorySessionId">
                  <div v-show="showDeliverables" class="panel-slot">
                    <DeliverablesPanel
                      @preview="handleDeliverablePreview"
                      @close="handleCloseCanvas"
                    />
                  </div>
                </transition>
              </div>
            </div>
          </transition>

          <!-- 版权信息 -->
          <transition name="copyright-fade" @after-leave="onCopyrightAfterLeave">
            <div v-if="messages.length === 0 && copyrightText" class="chat-copyright">
              Copyright
              <CopyrightCircleOutlined/>
              {{ copyrightText }}
            </div>
          </transition>
        </div>
      </div>
      </Transition>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { getStreamStatus, pendingConversations, forgetPendingConversation } from '@/services/conversationStream';
import {ref, onMounted, onUnmounted, watch, computed, nextTick, defineAsyncComponent} from 'vue';
import {useRouter} from 'vue-router';
import {useChatStore} from '@/stores/chat-store';
import ChatHistory from '@/components/chat/ChatHistroy.vue';
import ChatInput from '@/components/chat/ChatInput.vue';
import HistorySider from '@/components/chat/HistorySider.vue';
import HistoryConversationLoading from '@/components/chat/HistoryConversationLoading.vue';
import { yieldToBrowser } from '@/utils/yieldToBrowser';
import AgentWorkspace from '@/components/agent/AgentWorkspace.vue';
import WelcomeMessage from '@/components/chat/WelcomeMessage.vue';
import AgentPickerModal from '@/components/chat/AgentPickerModal.vue';
import StorageService from '@/utils/StorageService';
import { eventBus, MCP_EVENTS } from '@/utils/EventBus';
import ChatHeader from '@/components/layout/ChatHeader.vue';
import CanvasPanel from '@/components/chat/CanvasPanel.vue';
import DeliverablesPanel from '@/components/chat/DeliverablesPanel.vue';
import { useSandboxFilesStore, type SandboxFile } from '@/stores/sandboxFilesStore';
import {CopyrightCircleOutlined, SettingOutlined} from '@ant-design/icons-vue';
import { message } from 'ant-design-vue';
import { getCopyright } from '@/utils/RuntimeConfig';
import { parseAutoOpenArtifacts, getCanvasAnswerContent } from '@/utils/artifactParser';
import { useWorkspaceStorage } from '@/composables/useWorkspaceStorage';
import { parseKbCitationsFromKnowledgePrompt } from '@/composables/useMessageManager.helpers';
import { checkChatRecordSummary, editChatRecordSummary, listChatRecordSummary, listChatRecord, deleteChatRecord } from '@/services/aiChatRecord';
import agentNavIcon from '@/assets/image/svg/agent-icon-nav.svg';
import vectorNavIcon from '@/assets/image/svg/icon-vector-nav.svg';
import knowledgeNavIcon from '@/assets/image/svg/knowledge-nav.svg';
import logoImage from '@/assets/ga-logo.svg';
import newChatNavIcon from '@/assets/image/svg/new-chat-nav.svg';
import sidebarCollapseIcon from '@/assets/image/svg/sidebar-collapse.svg';

// 定义组件名以便keep-alive能够识别
defineOptions({
  name: 'ChatView'
});

const router = useRouter();
const KnowledgeBaseView = defineAsyncComponent(() => import('@/views/KnowledgeBaseView.vue'));
const DeliveryCenterView = defineAsyncComponent(() => import('@/views/DeliveryCenterView.vue'));

// 当前工作区（对话 / 知识库）持久化到 localStorage，刷新后仍停留在离开前的工作区
const ACTIVE_WORKSPACE_KEY = 'mcp-active-workspace';
type WorkspaceKind = 'chat' | 'knowledge' | 'delivery' | 'agents';
const readStoredWorkspace = (): WorkspaceKind => {
  const stored = StorageService.get<string>(ACTIVE_WORKSPACE_KEY, 'chat');
  return stored === 'knowledge' || stored === 'delivery' || stored === 'agents' ? stored : 'chat';
};
const activeWorkspace = ref<WorkspaceKind>(readStoredWorkspace());
watch(activeWorkspace, (value) => {
  StorageService.set(ACTIVE_WORKSPACE_KEY, value);
});

const isKnowledgeBaseEnabled = useWorkspaceStorage<boolean>('kb-enabled', false);
// 当前工作区选中的知识库名，用于历史会话恢复时为知识引用补全 knowledge_base_name 以走下载接口
const selectedKnowledgeBaseNames = useWorkspaceStorage<string[]>('kb-selected-names', []);

const HISTORY_SIDEBAR_VISIBLE_KEY = 'mcp-history-sidebar-visible';
const showHistorySidebar = ref<boolean>(StorageService.get<boolean>(HISTORY_SIDEBAR_VISIBLE_KEY, false) ?? false);
watch(showHistorySidebar, (value) => {
  StorageService.set(HISTORY_SIDEBAR_VISIBLE_KEY, value);
});
const showCanvas = ref(false);
const showDeliverables = ref(false);
const canvasHasBeenOpened = ref(false);
const isCanvasAnimating = ref(false);
const activeArtifactId = ref<string>('');
const lastProcessedArtifactId = ref<string>('');
const chatStore = useChatStore();
const chatHistoryRef = ref<InstanceType<typeof ChatHistory> | null>(null);
const canvasPanelRef = ref<InstanceType<typeof CanvasPanel> | null>(null);
const chatInputWelcomeRef = ref<InstanceType<typeof ChatInput> | null>(null);
const chatInputBottomRef = ref<InstanceType<typeof ChatInput> | null>(null);
const activeAgent = ref<any | null>(null);

// 历史记录列表相关状态
const historyItems = ref<any[]>([]);
// 后台任务也要保留运行标记，不能仅依赖当前会话的 isProcessing。
const backgroundRunningSessionIds = ref<string[]>(Object.keys(pendingConversations()));
const runningSessionIds = computed(() => [...new Set([
  ...backgroundRunningSessionIds.value,
  ...(chatStore.isProcessing ? [chatStore.sessionThreadId] : [])
])]);
let runningStatusTimer: ReturnType<typeof setTimeout> | undefined;
let runningStatusDisposed = false;
async function refreshRunningSessions() {
  const pending = Object.values(pendingConversations());
  backgroundRunningSessionIds.value = pending.map(item => item.sessionThreadId);
  await Promise.all(pending.map(async item => {
    if (chatStore.isProcessing && chatStore.sessionThreadId === item.sessionThreadId) return;
    try {
      const status = await getStreamStatus(item.chatType, item.sessionThreadId);
      if (runningStatusDisposed || pendingConversations()[item.sessionThreadId]?.turnId !== item.turnId) return;
      if (chatStore.isProcessing && chatStore.sessionThreadId === item.sessionThreadId) return;
      if (!status.exists) {
        forgetPendingConversation(item.sessionThreadId);
        backgroundRunningSessionIds.value = backgroundRunningSessionIds.value.filter(id => id !== item.sessionThreadId);
      }
    } catch { /* 暂时查询失败时保留运行状态，下一轮重试。 */ }
  }));
  if (!runningStatusDisposed) runningStatusTimer = setTimeout(refreshRunningSessions, 3000);
}
watch(() => [chatStore.isProcessing, chatStore.sessionThreadId], () => {
  backgroundRunningSessionIds.value = Object.keys(pendingConversations());
});
onMounted(() => { void refreshRunningSessions(); });
onUnmounted(() => { runningStatusDisposed = true; clearTimeout(runningStatusTimer); });

const agentWorkspaceRef = ref<InstanceType<typeof AgentWorkspace> | null>(null);
const agentPickerOpen = ref(false);
const historySessionMeta = useWorkspaceStorage<Record<string, { agentId: string; chatType: string }>>('history-session-meta', {});
const historyLoading = ref(false);
// 由左侧历史列表切换到的会话，在用户发起新一轮消息前禁止任何异步自动展开右侧面板。
const historyAutoOpenBlockedSessionId = ref('');
let historySelectionRequestId = 0;
// 刷新后首帧即进入历史恢复态：仅当当前会话已被确认是“历史会话”时，
// 才把加载态作为初始值。空白新对话即使在后台做智能体初始化，也不能显示“正在加载对话”。
const resolveBootstrapHistorySessionId = () => {
  const sid = (StorageService.getWorkspaceSessionThreadId() || '').trim();
  if (!sid) return '';
  if (chatStore.messages.length > 0 || chatStore.isProcessing) return '';
  if ((chatStore.sessionThreadId || '').trim() !== sid) return '';
  // history-session-meta 只在会话真正产生过内容（发送过消息或打开过历史）时写入，
  // 用它区分“待恢复的历史会话”与“全新的空对话”，后者必须立即显示欢迎页。
  return historySessionMeta.value[sid] ? sid : '';
};
const pendingHistorySessionId = ref(resolveBootstrapHistorySessionId());
// 首帧恢复进行中标记：恢复结束（载入历史成功或确认无历史）后清除，欢迎页才重新参与渲染
const isBootstrappingHistory = ref(pendingHistorySessionId.value !== '');
const historyContentEntering = ref(false);
const cancelHistorySelection = () => {
  ++historySelectionRequestId;
  pendingHistorySessionId.value = '';
  historyContentEntering.value = false;
};
watch(activeWorkspace, (workspace) => {
  if (workspace !== 'chat') cancelHistorySelection();
}, { flush: 'sync' });
watch(() => chatStore.sessionThreadId, (id) => {
  if (id !== pendingHistorySessionId.value) cancelHistorySelection();
}, { flush: 'sync' });
onUnmounted(() => {
  cancelHistorySelection();
  chatStore.detachCurrentConversation();
  // 保留会话 ID，让重新进入聊天页时走状态查询与回放。
  chatStore.replaceMessages([]);
});
const pendingSummarySessionIds = new Set<string>();
const pendingHistoryRefreshSessionIds = new Set<string>();
const summaryPollTimers = new Map<string, number>();
const SUMMARY_POLL_INTERVAL_MS = 1500;
let historyListRefreshInFlight = false;

type HistoryRecordItem = {
  id: string;
  sessionThreadId: string;
  title: string;
  preview: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  chatType: string;
  agentId: string;
  summaryPending?: boolean;
};

const mapHistorySummary = (item: any): HistoryRecordItem => ({
  id: item.session_thread_id,
  sessionThreadId: item.session_thread_id,
  title: item.summary || '未命名对话',
  preview: item.summary || '',
  createdAt: item.create_time || '',
  updatedAt: item.update_time || '',
  messageCount: 0,
  chatType: item.chat_type || item.chatType || historySessionMeta.value[item.session_thread_id]?.chatType || '',
  agentId: String(item.agent_id || item.agentId || historySessionMeta.value[item.session_thread_id]?.agentId || ''),
  summaryPending: !String(item.summary || '').trim()
});

const fetchHistoryList = async (options: { showLoading?: boolean } = {}) => {
  const showLoading = options.showLoading !== false;
  if (showLoading) historyLoading.value = true;
  try {
    const res = await listChatRecordSummary();
    if ((res?.code !== undefined && Number(res.code) !== 200) || !Array.isArray(res?.data)) {
      throw new Error('历史摘要列表返回异常');
    }
    const list = res.data;
    const summaries = list.map(mapHistorySummary);
    const metadata = { ...historySessionMeta.value };
    for (const item of summaries) {
      if (item.agentId || item.chatType) metadata[item.sessionThreadId] = { agentId: item.agentId, chatType: item.chatType };
    }
    historySessionMeta.value = metadata;
    const summaryIds = new Set(summaries.map((item: any) => item.sessionThreadId));
    const pendingItems = historyItems.value.filter(
      (item) => item.summaryPending && pendingSummarySessionIds.has(item.sessionThreadId) && !summaryIds.has(item.sessionThreadId)
    );
    const visibleIds = new Set([...pendingItems, ...summaries].map(item => item.sessionThreadId));
    const cachedItems = Object.values(pendingConversations()).filter(item => !visibleIds.has(item.sessionThreadId)).map(item => ({ ...item, id: item.sessionThreadId, title: item.user?.content?.slice(0, 50) || '进行中的对话', preview: '', summaryPending: true, messageCount: 0 }));
    historyItems.value = [...cachedItems, ...pendingItems, ...summaries];
    queueHistoryMetadata(summaries);
    return summaries;
  } catch {
    // 请求失败静默处理
    return [];
  } finally {
    if (showLoading) historyLoading.value = false;
  }
};

const refreshHistoryListAfterTurn = async () => {
  if (!pendingHistoryRefreshSessionIds.size || historyListRefreshInFlight) return;

  historyListRefreshInFlight = true;
  const refreshingSessionIds = [...pendingHistoryRefreshSessionIds];
  refreshingSessionIds.forEach((sessionThreadId) => pendingHistoryRefreshSessionIds.delete(sessionThreadId));

  try {
    await fetchHistoryList({ showLoading: false });
  } finally {
    historyListRefreshInFlight = false;
    if (pendingHistoryRefreshSessionIds.size > 0) {
      void refreshHistoryListAfterTurn();
    }
  }
};

const stopSummaryPolling = (sessionThreadId: string) => {
  pendingSummarySessionIds.delete(sessionThreadId);
  const timer = summaryPollTimers.get(sessionThreadId);
  if (timer !== undefined) window.clearTimeout(timer);
  summaryPollTimers.delete(sessionThreadId);
};

const scheduleSummaryPoll = (sessionThreadId: string) => {
  if (!pendingSummarySessionIds.has(sessionThreadId)) return;
  const timer = window.setTimeout(() => {
    summaryPollTimers.delete(sessionThreadId);
    void pollSummaryUntilReady(sessionThreadId);
  }, SUMMARY_POLL_INTERVAL_MS);
  summaryPollTimers.set(sessionThreadId, timer);
};

const isSummaryReady = (response: any) => {
  const value = response?.exists ?? response?.data?.exists;
  return value === true || value === 1 || value === '1' || value === 'true';
};

async function pollSummaryUntilReady(sessionThreadId: string) {
  if (!pendingSummarySessionIds.has(sessionThreadId)) return;

  try {
    const response = await checkChatRecordSummary(sessionThreadId);
    if (!pendingSummarySessionIds.has(sessionThreadId)) return;
    if (response?.code !== undefined && Number(response.code) !== 200) {
      throw new Error(response.message || '查询会话摘要失败');
    }

    if (isSummaryReady(response)) {
      const summaries = await fetchHistoryList({ showLoading: false });
      const loaded = summaries.some((item: any) => item.sessionThreadId === sessionThreadId && !item.summaryPending);
      if (loaded) {
        stopSummaryPolling(sessionThreadId);
        return;
      }
    }
  } catch {
    // 摘要可能仍在生成或暂时查询失败，保持骨架行并继续轮询。
  }

  scheduleSummaryPoll(sessionThreadId);
}

const handleMessageSubmit = (rawSessionThreadId: string, knowledgeBaseEnabled = false) => {
  // 新一轮发送优先于上一轮恢复完成后的历史回查。
  cancelHistorySelection();
  const sessionThreadId = (rawSessionThreadId || '').trim();
  if (sessionThreadId && historyAutoOpenBlockedSessionId.value === sessionThreadId) {
    historyAutoOpenBlockedSessionId.value = '';
  }
  if (!sessionThreadId) return;

  // 无论是新会话还是继续追问，等本轮结束后都静默刷新一次 list_summary，
  // 让服务端返回的 update_time 驱动左侧历史排序。
  pendingHistoryRefreshSessionIds.add(sessionThreadId);

  if (pendingSummarySessionIds.has(sessionThreadId)) return;

  const existingItem = historyItems.value.find((item) => item.sessionThreadId === sessionThreadId);
  if (existingItem && !existingItem.summaryPending) return;

  pendingSummarySessionIds.add(sessionThreadId);
  if (!existingItem) {
    const now = new Date().toISOString();
    const selectedId = StorageService.getSelectedAgent();
    const agent = StorageService.getAgents().find(item => String(item.id) === String(selectedId));
    const agentId = String(agent?.uuid || agent?.id || '').trim();
    const type = agent?.config?.basic?.type;
    const chatType = agentId ? (type === 'deepagent' ? 'deepagent' : type === 'orchestrator' ? 'travel_planner' : 'agent') : knowledgeBaseEnabled ? 'kb_chat' : 'model';
    historySessionMeta.value = { ...historySessionMeta.value, [sessionThreadId]: { agentId, chatType } };
    historyItems.value.unshift({
      id: sessionThreadId,
      sessionThreadId,
      title: '',
      preview: '',
      createdAt: now,
      updatedAt: now,
      messageCount: 0,
      chatType,
      agentId,
      summaryPending: true
    });
  }

  void pollSummaryUntilReady(sessionThreadId);
};

const isOrchestratorActive = computed(() => {
  const agent = activeAgent.value;
  const type = (agent?.basic?.type) || (agent?.config?.basic?.type) || 'assistant';
  return type === 'orchestrator';
});

// 模型选择相关状态（传递给ChatHeader组件）
const showModelSelector = ref(false);
const isAgentMode = ref(false);

// 选择模式状态
const isSelectionMode = ref(false);
const isAllSelected = ref(false);
const hasSelection = ref(false);
const selectedMessages = ref<any[]>([]);

// 计算属性
const messages = computed(() => chatStore.messages);
const isHistoryRailVisible = computed(() => showHistorySidebar.value);
const hasConversationMessages = computed(() => messages.value.length > 0);
// 仅当当前确实处于某个已加载的对话中时才高亮历史记录；
// 新对话（欢迎页）时消息为空，不应选中任何历史项，
// 避免刷新后恢复的持久化会话 ID 与最近一条历史记录误匹配
const activeSessionThreadId = computed(() =>
  hasConversationMessages.value ? (chatStore.sessionThreadId || '').trim() : ''
);
const shouldRenderRightPanel = computed(() => hasConversationMessages.value && (canvasHasBeenOpened.value || showDeliverables.value));
const shouldShowRightPanel = computed(() => hasConversationMessages.value && (showCanvas.value || showDeliverables.value));

// 沙箱交付文件 store：用于判断交付中心是否有内容，为空时隐藏“画布/交付中心”双 Tab（DeepAgent 会话除外）
const sandboxFilesStore = useSandboxFilesStore();
const hasDeliverables = computed(() => {
  if (sandboxFilesStore.files.length === 0) return false;
  const sid = (StorageService.getWorkspaceSessionThreadId() || '').trim();
  // 文件清单属于其他会话（切换会话后尚未刷新）时按空处理，避免误显示
  return !sid || sandboxFilesStore.loadedSessionId === sid;
});

const isDeepAgentActive = computed(() => {
  const agent = activeAgent.value;
  const type = (agent?.basic?.type) || (agent?.config?.basic?.type) || '';
  return type === 'deepagent';
});

// DeepAgent 会话只要右侧面板打开就展示双 Tab：
// 沙箱文件清单可能为空或尚未拉取（历史会话沙箱已回收、请求进行中、
// 文档仅以 artifact 形式出现在消息里），此时交付面板走空态 + 刷新，
// 不应因此让用户失去“画布/交付面板”的切换入口
const shouldShowPanelTabs = computed(() =>
  activeWorkspace.value === 'chat' &&
  shouldShowRightPanel.value &&
  (hasDeliverables.value || isDeepAgentActive.value)
);

// 会话可用后（含历史会话恢复）主动查询一次沙箱文件清单，
// 保证交付中心已有文件时双 Tab 能正确显示
watch(
  () => chatStore.messages.length,
  (len) => {
    if (len === 0) return;
    const sid = (StorageService.getWorkspaceSessionThreadId() || '').trim();
    if (!sid || sandboxFilesStore.loading || sandboxFilesStore.loadedSessionId === sid) return;
    void sandboxFilesStore.fetchFiles(sid);
  },
  { immediate: true }
);

// 计算属性获取copyright文本
const copyrightText = computed(() => {
  return getCopyright();
});

const showWelcomeGroup = computed(() => {
  // 刷新恢复期间不渲染欢迎页，否则会出现“先新对话、再切回历史对话”的闪跳。
  // 仅限首帧恢复；用户主动点击历史记录时，欢迎页仍作为加载背景保留。
  if (isBootstrappingHistory.value) return false;
  if (isOrchestratorActive.value || isKnowledgeBaseEnabled.value || isAgentMode.value) {
    if (messages.value.length === 0 && !chatStore.isProcessing) {
      return true;
    }
    return false;
  }
  return messages.value.length === 0 && !chatStore.isProcessing;
});

// 控制底部输入框的显示：仅在版权完成淡出后显示
const showBottomInput = ref(messages.value.length > 0 || chatStore.isProcessing);
// 历史切换期间挂起底部输入框的显示，等分批渲染落定后再 enter，
// 避免输入框挂载/过渡与消息列表逐批渲染争抢同一帧。
let bottomInputRevealDeferred = false;
const revealBottomInput = () => {
  if (pendingHistorySessionId.value) {
    bottomInputRevealDeferred = true;
    return;
  }
  showBottomInput.value = true;
};
watch(pendingHistorySessionId, (pending) => {
  if (pending || !bottomInputRevealDeferred) return;
  bottomInputRevealDeferred = false;
  void nextTick(() => {
    showBottomInput.value = true;
  });
});
// 工具栏是否显示
const isInputToolbarVisible = ref(false);
const handleToolbarVisibilityChange = (visible: boolean) => {
  isInputToolbarVisible.value = visible;
};

// 工具栏是否展开
const isInputToolbarExpanded = ref(false);
const handleToolbarExpandChange = (expanded: boolean) => {
  isInputToolbarExpanded.value = expanded;
};

// 工具栏面板高度
const inputToolbarPanelHeight = ref(0);
const handleToolbarPanelHeightChange = (height: number) => {
  inputToolbarPanelHeight.value = height;
};

// 底部输入框高度
const inputHeight = ref(0);
const historyLoadingContentStyle = computed(() => ({
  '--history-loading-shift': showBottomInput.value
    ? `${-Math.round((inputHeight.value + 12) / 2)}px`
    : '0px'
}));
const handleInputHeightChange = (height: number) => {
  inputHeight.value = height;
};

watch(() => messages.value.length, (newLen, oldLen) => {
  if (isOrchestratorActive.value || isAgentMode.value || isKnowledgeBaseEnabled.value) {
    // 编排式助手或智能体模式或知识库：首条消息发出后立即切换到底部输入框
    if (newLen !== 0) {
      revealBottomInput();
    }
  } else {
    // 普通模式：首条消息先让版权淡出，再显示底部输入框
    if (newLen !== 0 && oldLen !== 0) {
      revealBottomInput();
    }
  }
});

watch(() => chatStore.isProcessing, (isProcessing, wasProcessing) => {
  if (isProcessing) {
    revealBottomInput();
    return;
  }

  if (wasProcessing) {
    void refreshHistoryListAfterTurn();
  }
});

const onCopyrightAfterLeave = () => {
  // 版权淡出完成后，显示底部输入框
  revealBottomInput();
};

const onCanvasTransitionStart = () => {
  isCanvasAnimating.value = true;
};

const onCanvasTransitionEnd = () => {
  isCanvasAnimating.value = false;
};

// 右侧面板（画布 / 交付中心）任一 Tab 打开即视为面板打开
const rightPanelOpen = computed(() => showCanvas.value || showDeliverables.value);

// 画布仅在有对话内容时打开；工作区切换无需改写面板状态。
watch(rightPanelOpen, (open) => {
  if (open && !hasConversationMessages.value) closeCanvasCompletely();
});

watch(
  () => messages.value.length,
  (newLen) => {
    if (newLen === 0) {
      closeCanvasCompletely();
    }
  }
);

// 处理选择模式变化
const handleSelectionModeChanged = (selectionMode: boolean) => {
  isSelectionMode.value = selectionMode;
  // 当选择模式变化时，更新选中消息
  updateSelectedMessages();
};

// 处理消息选择变化
const handleSelectionChanged = (_messageId: string, _selected: boolean) => {
  // 当消息选择状态变化时，更新选中消息
  updateSelectedMessages();
};

// 处理全选状态变化
const handleAllSelectedChanged = (allSelected: boolean, hasSelected: boolean) => {
  isAllSelected.value = allSelected;
  hasSelection.value = hasSelected;
  // 更新选中的消息
  updateSelectedMessages();
};

watch(isAgentMode, (newVal, oldVal) => {
  if (newVal !== oldVal && isSelectionMode.value) {
    handleCancelSelection();
  }
});

// 获取选中的消息
const updateSelectedMessages = () => {
  if (chatHistoryRef.value) {
    const chatHistoryInstance = chatHistoryRef.value as any;
    // 优先使用 ChatHistory 暴露的 selectedMessageObjects
    if (chatHistoryInstance.selectedMessageObjects) {
      selectedMessages.value = chatHistoryInstance.selectedMessageObjects;
    } else if (chatHistoryInstance.selectedMessages) {
      // 降级兼容：如果未暴露对象列表，则尝试手动重建（保留原有逻辑以防万一）
      const selectedIds = Array.from(chatHistoryInstance.selectedMessages);

      // 使用与ChatHistory相同的过滤逻辑获取显示的消息
      const filteredMessages = chatStore.messages.filter(message => message.role !== 'tool' && message.role !== 'system');
      const selected = [];

      // 遍历过滤后的消息，找到选中的消息
      for (let index = 0; index < filteredMessages.length; index++) {
        const message = filteredMessages[index];

        // 生成消息ID（与ChatHistory中的逻辑完全一致）
        const messageRef = message.content + message.role + index;
        const messageId = `msg-${message.role}-${index}-${messageRef.length}`;

        if (selectedIds.includes(messageId)) {
          selected.push(message);
        }
      }

      selectedMessages.value = selected;
    } else {
      selectedMessages.value = [];
    }
  } else {
    selectedMessages.value = [];
  }
};

// 处理切换全选事件（点击选择框或文本）
const handleToggleAll = () => {
  if (chatHistoryRef.value) {
    if (isAllSelected.value) {
      // 如果已全选，则取消全选
      if (typeof (chatHistoryRef.value as any).clearAllSelection === 'function') {
        (chatHistoryRef.value as any).clearAllSelection();
      }
    } else {
      // 如果未全选，则全选
      if (typeof (chatHistoryRef.value as any).selectAllMessages === 'function') {
        (chatHistoryRef.value as any).selectAllMessages();
      }
    }
  }
};

// 处理取消选择事件（退出选择模式）
const handleCancelSelection = () => {
  if (chatHistoryRef.value) {
    // 调用ChatHistory的handleSelectionModeChanged方法，传递false来退出选择模式
    if (typeof (chatHistoryRef.value as any).handleSelectionModeChanged === 'function') {
      (chatHistoryRef.value as any).handleSelectionModeChanged(false);
    }
  }
};

// 处理复制选中内容事件
const handleCopySelected = () => {
  if (chatHistoryRef.value) {
    // 调用ChatHistory的复制方法
    if (typeof (chatHistoryRef.value as any).copySelectedMessages === 'function') {
      (chatHistoryRef.value as any).copySelectedMessages();
    }
  }
};

// 处理导出文本事件
const handleExportText = () => {
  // 使用事件分发的方式触发导出模态窗口
  const exportEvent = new CustomEvent('show-export-dialog', {
    detail: {
      isSelectionMode: true,
      selectedMessages: selectedMessages.value,
      defaultFormat: 'text' // 默认选择纯文本格式
    }
  });

  document.dispatchEvent(exportEvent);
};

// 处理导出Markdown事件
const handleExportMarkdown = () => {
  // 使用事件分发的方式触发导出模态窗口
  const exportEvent = new CustomEvent('show-export-dialog', {
    detail: {
      isSelectionMode: true,
      selectedMessages: selectedMessages.value,
      defaultFormat: 'markdown'
    }
  });

  document.dispatchEvent(exportEvent);
};

const handleOpenAgentWorkspaceEvent = () => handleOpenAgentWorkspace();
const handleOpenKnowledgeWorkspaceEvent = () => handleOpenKnowledgeWorkspace();
const handleOpenAgentPickerEvent = () => {
  agentPickerOpen.value = true;
};

const handleCollapseHistorySidebar = () => {
  showHistorySidebar.value = false;
};

const handleToggleHistorySidebar = () => {
  showHistorySidebar.value = !showHistorySidebar.value;
};

const handleOpenKnowledgeWorkspace = () => {
  showModelSelector.value = false;
  activeWorkspace.value = 'knowledge';
};

const handleOpenDeliveryWorkspace = () => {
  showModelSelector.value = false;
  activeWorkspace.value = 'delivery';
};

const handleBackToChat = () => {
  activeWorkspace.value = 'chat';
};

const handleOpenAgentWorkspace = () => {
  showModelSelector.value = false;
  activeWorkspace.value = 'agents';
};

const triggerGenericNewChat = async () => {
  cancelHistorySelection();
  handleBackToChat();
  await nextTick();
  const targetInput = chatInputBottomRef.value || chatInputWelcomeRef.value;
  targetInput?.initNewChat?.();
};

const handleNewChatFromHistory = () => {
  void triggerGenericNewChat();
};

const handleAgentNewChat = async (agentId: string) => {
  cancelHistorySelection();
  handleBackToChat();
  await nextTick();
  await agentWorkspaceRef.value?.startNewAgentChat(agentId);
};

const handleManageHistoryAgent = async (agentId: string) => {
  handleOpenAgentWorkspace();
  await nextTick();
  agentWorkspaceRef.value?.focusAgent(agentId);
};

const handleOpenSettings = () => {
  void router.push('/settings');
};

const handleRenameHistoryRecord = async (record: any, summary: string) => {
  const index = historyItems.value.findIndex((item) => item.id === record.id);
  if (index < 0) return;

  const previousTitle = historyItems.value[index].title;
  const previousPreview = historyItems.value[index].preview;
  historyItems.value[index].title = summary;
  historyItems.value[index].preview = summary;

  try {
    const res = await editChatRecordSummary({
      session_thread_id: record.sessionThreadId,
      summary
    });
    if (res?.code !== undefined && Number(res.code) !== 200) {
      throw new Error(res.message || '重命名失败');
    }
  } catch (error) {
    historyItems.value[index].title = previousTitle;
    historyItems.value[index].preview = previousPreview;
    message.error(error instanceof Error ? error.message : '重命名失败，请稍后重试');
  }
};

const handleDeleteHistoryRecord = async (record: any) => {
  const index = historyItems.value.findIndex((item) => item.id === record.id);
  if (index < 0) return;

  try {
    const resolved = await resolveChatRecordParams(record);
    const params = resolved?.params || buildChatRecordParams(record);
    const res = await deleteChatRecord(params);
    if (res?.code !== undefined && Number(res.code) !== 200) {
      throw new Error(res.message || '删除失败');
    }
    historyItems.value.splice(index, 1);
    // 若删除的是当前打开的对话，切换到新对话
    if (record.sessionThreadId && record.sessionThreadId === activeSessionThreadId.value) {
      handleNewChatFromHistory();
    }
  } catch (error) {
    message.error(error instanceof Error ? error.message : '删除失败，请稍后重试');
  }
};

// 构建聊天记录相关参数（与 /aiChatRecord/list 传参逻辑一致）
const buildChatRecordParams = (record: { sessionThreadId?: string; chatType?: string; agentId?: string } | string): {
  session_thread_id: string;
  chat_type: string;
  agent_id?: string;
} => {
  const sessionThreadId = typeof record === 'string'
    ? record
    : String(record?.sessionThreadId || '').trim();
  let chatType = typeof record === 'string'
    ? ''
    : String(record?.chatType || '').trim();
  let agentId = typeof record === 'string'
    ? ''
    : String(record?.agentId || '').trim();

  if (!chatType) {
    // 删除历史记录的兜底参数只信历史项自身元数据；
    // 缺失时按普通对话处理，避免把“当前会话”的 agent 身份误带到其他历史记录上。
    chatType = 'model';
  }

  const params: { session_thread_id: string; chat_type: string; agent_id?: string } = {
    session_thread_id: sessionThreadId,
    chat_type: chatType
  };
  if (agentId) params.agent_id = agentId;
  return params;
};

const findMatchingSessionData = (data: any, sessionThreadId: string) => {
  if (!Array.isArray(data)) return null;
  return data.find((item: any) => String(item?.session_thread_id || '').trim() === sessionThreadId) || null;
};

const buildChatRecordParamCandidates = (record: { sessionThreadId?: string; chatType?: string; agentId?: string } | string) => {
  const sessionThreadId = typeof record === 'string'
    ? String(record || '').trim()
    : String(record?.sessionThreadId || '').trim();
  const explicitChatType = typeof record === 'string'
    ? ''
    : String(record?.chatType || '').trim();
  const explicitAgentId = typeof record === 'string'
    ? ''
    : String(record?.agentId || '').trim();

  const currentAgent = activeAgent.value;
  const currentAgentId = String((currentAgent as any)?.agentUuid || (currentAgent as any)?.agentId || '').trim();
  const candidateAgentId = explicitAgentId || currentAgentId;

  const candidates: Array<{ session_thread_id: string; chat_type: string; agent_id?: string }> = [];
  const seen = new Set<string>();
  const pushCandidate = (chatType: string, agentId: string = '') => {
    if (!sessionThreadId || !chatType) return;
    const key = `${chatType}::${agentId}`;
    if (seen.has(key)) return;
    seen.add(key);
    const params: { session_thread_id: string; chat_type: string; agent_id?: string } = {
      session_thread_id: sessionThreadId,
      chat_type: chatType
    };
    if (agentId) params.agent_id = agentId;
    candidates.push(params);
  };

  if (explicitChatType) pushCandidate(explicitChatType, explicitAgentId);
  pushCandidate('model');
  pushCandidate('kb_chat');
  pushCandidate('deepagent');
  pushCandidate('travel_planner');
  pushCandidate('agent', explicitAgentId);
  if (candidateAgentId && candidateAgentId !== explicitAgentId) {
    pushCandidate('agent', candidateAgentId);
  }

  return candidates;
};

const cacheResolvedHistoryRecordMeta = (
  sessionThreadId: string,
  resolved: { chat_type?: string; agent_id?: string },
  fallback?: { chat_type?: string; agent_id?: string }
) => {
  const index = historyItems.value.findIndex((item) => item.sessionThreadId === sessionThreadId);
  if (index < 0) return;
  historyItems.value[index] = {
    ...historyItems.value[index],
    chatType: String(resolved?.chat_type || fallback?.chat_type || historyItems.value[index]?.chatType || '').trim(),
    agentId: String(resolved?.agent_id || fallback?.agent_id || historyItems.value[index]?.agentId || '').trim()
  };
  const item = historyItems.value[index];
  historySessionMeta.value = { ...historySessionMeta.value, [sessionThreadId]: { agentId: item.agentId, chatType: item.chatType } };
};

// 旧摘要可能不含归属信息；限制详情补查并发，避免每次摘要轮询重复请求。
const checkedHistoryMetadata = new Set<string>();
const historyMetadataQueue: HistoryRecordItem[] = [];
let historyMetadataWorkers = 0;
let historyMetadataDisposed = false;
onUnmounted(() => { historyMetadataDisposed = true; historyMetadataQueue.length = 0; });

function queueHistoryMetadata(items: HistoryRecordItem[]) {
  for (const item of items) {
    if (item.agentId || item.chatType === 'model' || item.chatType === 'kb_chat' || checkedHistoryMetadata.has(item.sessionThreadId)) continue;
    checkedHistoryMetadata.add(item.sessionThreadId);
    historyMetadataQueue.push(item);
  }
  while (historyMetadataWorkers < 3 && historyMetadataQueue.length) {
    historyMetadataWorkers++;
    void (async () => {
      try {
        while (!historyMetadataDisposed && historyMetadataQueue.length) {
          const item = historyMetadataQueue.shift()!;
          // 只用记录自身的信息查询，不能把当前正在使用的 Agent 当作旧会话归属。
          const types = [...new Set(['', item.chatType, 'agent', 'deepagent', 'travel_planner', 'model', 'kb_chat'])];
          for (const chatType of types) {
            try {
              const params = { session_thread_id: item.sessionThreadId, ...(chatType ? { chat_type: chatType } : {}) };
              const response = await listChatRecord(params);
              if (historyMetadataDisposed) return;
              const session = findMatchingSessionData(response?.data, item.sessionThreadId);
              if (!session) continue;
              if (session.agent_id || session.chat_type || chatType) {
                cacheResolvedHistoryRecordMeta(item.sessionThreadId, session, params);
                break;
              }
            } catch {
              if (historyMetadataDisposed) return;
              // 兼容要求显式 chat_type 的旧接口；失败时保留原记录。
            }
          }
        }
      } finally {
        historyMetadataWorkers--;
      }
    })();
  }
}

const resolveChatRecordParams = async (record: { sessionThreadId?: string; chatType?: string; agentId?: string } | string) => {
  const candidates = buildChatRecordParamCandidates(record);
  for (const params of candidates) {
    try {
      const res = await listChatRecord(params);
      const sessionData = findMatchingSessionData(res?.data, params.session_thread_id);
      if (!sessionData) continue;
      cacheResolvedHistoryRecordMeta(params.session_thread_id, sessionData, params);
      return {
        params: {
          session_thread_id: params.session_thread_id,
          chat_type: String(sessionData?.chat_type || params.chat_type || '').trim(),
          ...(String(sessionData?.agent_id || params.agent_id || '').trim()
            ? { agent_id: String(sessionData?.agent_id || params.agent_id || '').trim() }
            : {})
        },
        sessionData
      };
    } catch {
      // 尝试下一组候选参数
    }
  }
  return null;
};

/**
 * 历史记录可能在未激活智能体时打开，按 agent_id 反查智能体配置，
 * 附加到 assistant 消息上供 ChatMessage 还原头像与名称
 */
const resolveHistoryAgentConfig = (sessionData: any, record: any) => {
  const targetId = String(sessionData?.agent_id || record?.agentId || '').trim();
  if (!targetId) return null;
  const agents = StorageService.getAgents() || [];
  const matched = agents.find((agent: any) => String(agent?.uuid || '') === targetId || String(agent?.id || '') === targetId);
  return matched?.config || null;
};

const handleWelcomeAgentSelect = async (agent: any) => {
  if (chatStore.isProcessing) return;
  const ids = [agent.id, agent.uuid].filter(Boolean).map(String);
  const existing = historyItems.value.find(record => ids.includes(String(record.agentId || '')));
  if (existing) {
    await handleSelectHistoryRecord(existing);
  } else if (String(StorageService.getSelectedAgent()) !== String(agent.id)) {
    await agentWorkspaceRef.value?.startNewAgentChat(String(agent.id));
  }
};

// 输入框“智能体”弹出“新任务”模态后选择智能体：始终开启一个新对话，而非复用历史会话
const handleAgentPickerSelect = (agent: any) => {
  const agentId = String(agent?.id ?? agent?.uuid ?? '');
  void handleAgentNewChat(agentId);
};

const handleSelectHistoryRecord = async (
  record: any,
  options: { silentWhenMissing?: boolean; isBootstrap?: boolean } = {}
) => {
  handleBackToChat();
  const targetSessionThreadId = String(record?.sessionThreadId || '').trim();
  if (!targetSessionThreadId) return;
  // 刷新恢复时加载态已在 setup 阶段预置为同一会话 ID，需要放行，否则恢复流程直接被去重拦掉。
  if (!options.isBootstrap) {
    if (targetSessionThreadId === pendingHistorySessionId.value) return;
    if (targetSessionThreadId === activeSessionThreadId.value && chatStore.isProcessing) return;
  }

  const pending = pendingConversations()[targetSessionThreadId];
  record = { ...pending, ...record, chatType: record.chatType || pending?.chatType, agentId: record.agentId || pending?.agentId };
  chatStore.preserveReusableSession?.(undefined, StorageService.getSelectedAgent() || '');
  chatStore.detachCurrentConversation();
  chatStore.resetAgentInit();
  // 在历史列表点击入口立即建立会话级拦截，覆盖消息 watcher、文件清单更新等异步链路。
  historyAutoOpenBlockedSessionId.value = targetSessionThreadId;
  const requestId = ++historySelectionRequestId;
  historyContentEntering.value = false;
  pendingHistorySessionId.value = targetSessionThreadId;
  closeCanvasCompletely();

  try {
    const resolved = await resolveChatRecordParams(record);
    if (requestId !== historySelectionRequestId) return;
    await yieldToBrowser();
    if (requestId !== historySelectionRequestId) return;
    let sessionData = resolved?.sessionData || { records: [], chat_type: record.chatType || 'model', agent_id: record.agentId || '' };
    const streamType = sessionData.chat_type || record.chatType || 'model';
    const streamStatus = await getStreamStatus(streamType, targetSessionThreadId);
    if (requestId !== historySelectionRequestId) return;
    const hasLiveStream = streamStatus.exists && ['starting', 'running'].includes(streamStatus.status || '');
    if (!hasLiveStream) {
      // The turn may have committed between the initial history request and status.
      const refreshed = await resolveChatRecordParams(record);
      if (requestId !== historySelectionRequestId) return;
      sessionData = refreshed?.sessionData || sessionData;
    }
    const records = sessionData?.records || [];
    if (!records.length && !hasLiveStream) {
      chatStore.setSessionThreadId(targetSessionThreadId);
      chatStore.replaceMessages([]);
      forgetPendingConversation(targetSessionThreadId);
      // 已确认没有历史消息，后续智能体初始化不属于历史加载。
      pendingHistorySessionId.value = '';
      if (options.isBootstrap) isBootstrappingHistory.value = false;
      const agentKey = record.agentId || (options.isBootstrap ? StorageService.getSelectedAgent() : '');
      if (agentKey) await agentWorkspaceRef.value?.activateAgentForSession(agentKey, targetSessionThreadId, () => requestId === historySelectionRequestId);
      return;
    }

    // 将接口返回的记录映射为内部 Message 格式（deepagent 会话按轮次合并展示）
    let mappedMessages = mapRecordsToMessages(records, sessionData?.chat_type);
    if (hasLiveStream) {
      const turnId = streamStatus.turn_id || pending?.turnId || '';
      mappedMessages = mappedMessages.filter((msg: any) => !turnId || msg.turn_id !== turnId);
      if (pending?.user && (!streamStatus.turn_id || pending.turnId === streamStatus.turn_id)) {
        mappedMessages.push({ ...pending.user, turn_id: turnId });
      }
    }
    const historyAgentConfig = resolveHistoryAgentConfig(sessionData, record);
    const resolvedChatType = String(sessionData?.chat_type || record?.chatType || '').trim();
    const isRegularHistory = !resolvedChatType || resolvedChatType === 'model' || resolvedChatType === 'kb_chat';
    if (historyAgentConfig) {
      mappedMessages.forEach((msg: any) => {
        if (msg.role === 'assistant') msg.agentConfig = historyAgentConfig;
      });
    } else if (isRegularHistory && StorageService.getActiveAgent()) {
      // 当前处于智能体模式，但打开的是普通对话历史时，需要先退出智能体模式，
      // 避免继续追问仍沿用智能体链路。
      await agentWorkspaceRef.value?.exitAgentMode?.({ clearChat: false, isCurrent: () => requestId === historySelectionRequestId });
    }
    if (requestId !== historySelectionRequestId) return;

    // 切换 sessionThreadId
    chatStore.setSessionThreadId(targetSessionThreadId);

    // 历史会话恢复后，需要把消息同步回普通对话与智能体对话两套内存，
    // 否则“继续问答”时会被底层空状态覆盖，表现为历史内容瞬间消失。
    chatStore.replaceMessages(mappedMessages);
    const historyAgentId = String(sessionData?.agent_id || record?.agentId || '').trim();
    if (historyAgentId) {
      // 先同步当前会话归属的 agent 身份，避免用户在历史会话刚展示出来时继续追问，
      // 发送链路仍读取到上一个会话遗留的 selectedAgent / activeAgent。
      agentWorkspaceRef.value?.syncAgentSelectionForSession?.(historyAgentId);
    }
    // 消息已可展示后立即收起加载提示；智能体上下文初始化可以继续在后台完成。
    await nextTick();
    await chatHistoryRef.value?.waitForHistoryRender();
    if (requestId !== historySelectionRequestId) return;
    if (requestId === historySelectionRequestId) {
      historyContentEntering.value = true;
      pendingHistorySessionId.value = '';
    }

    // 历史记录属于某个智能体时，激活并初始化该智能体，
    // 保证普通对话中点开智能体历史后继续追问仍走智能体链路
    if (hasLiveStream) {
      // Starting/running sessions already own their backend context; do not reinitialize.
      const restored = await chatStore.resumeConversation(streamType, streamStatus.turn_id || pending?.turnId || '', streamStatus.created_at);
      if (requestId !== historySelectionRequestId || !restored) return;
      const completed = await resolveChatRecordParams(record);
      if (requestId !== historySelectionRequestId) return;
      if (completed?.sessionData?.records?.length) {
        const finalMessages = mapRecordsToMessages(completed.sessionData.records, completed.sessionData.chat_type);
        if (historyAgentConfig) finalMessages.forEach((msg: any) => { if (msg.role === 'assistant') msg.agentConfig = historyAgentConfig; });
        chatStore.replaceMessages(finalMessages);
      }
      const latest = await getStreamStatus(streamType, targetSessionThreadId);
      if (requestId !== historySelectionRequestId) return;
      if (latest.exists) return;
      forgetPendingConversation(targetSessionThreadId);
    } else {
      forgetPendingConversation(targetSessionThreadId);
    }
    if (historyAgentId) {
      void agentWorkspaceRef.value?.activateAgentForSession(historyAgentId, targetSessionThreadId, () => requestId === historySelectionRequestId);
    }
  } catch {
    if (requestId === historySelectionRequestId) message.warning('打开历史记录失败，请稍后重试');
  } finally {
    if (requestId === historySelectionRequestId) {
      pendingHistorySessionId.value = '';
    }
  }
};

/**
 * 页面刷新（重新加载）后，当前仍停留在原会话但消息尚未加载时，
 * 自动恢复该会话的历史消息，避免刷新后落入空白的“新对话”界面。
 * 加载态已由 resolveBootstrapHistorySessionId 在 setup 阶段预置，
 * 因此首帧即显示历史会话加载，不会先闪现欢迎页再切换。
 */
const restoreActiveSessionOnRefresh = async () => {
  try {
    const targetSid = (StorageService.getWorkspaceSessionThreadId() || '').trim();
    if (!targetSid) return;
    // 已有消息说明并非全新加载，无需恢复
    if (hasConversationMessages.value) return;
    // 会话已切换，跳过
    if ((chatStore.sessionThreadId || '').trim() !== targetSid) return;
    if (chatStore.isProcessing) return;
    // 与首帧保持一致：新对话也有会话 ID，但只有已知历史会话才需要恢复。
    if (!historySessionMeta.value[targetSid]) return;
    // chatType/agentId 由 resolveChatRecordParams 自动探测。
    await handleSelectHistoryRecord(
      { sessionThreadId: targetSid, chatType: '', agentId: '' },
      { silentWhenMissing: true, isBootstrap: true }
    );
  } finally {
    // 恢复流程结束（含无历史记录的失败分支，其加载态已在 handleSelectHistoryRecord 内清除），
    // 此后欢迎页才允许重新参与渲染。
    isBootstrappingHistory.value = false;
  }
};

/**
 * 映射图片问答记录：images 中是图片的 base64 dataURL（或图片链接），
 * 转成 files 里的图片项，复用现有的图片画廊渲染与大图预览
 */
const mapHistoryImageFiles = (images: any[]): any[] => {
  if (!Array.isArray(images)) return [];
  return images
    .map((image: any) => {
      const url = String(image?.url || '').trim();
      if (!url) return null;
      return {
        name: '',
        type: /^data:(image\/[\w.+-]+);/i.exec(url)?.[1] || '',
        isFileImage: true,
        imagePreviewUrl: url,
        url
      };
    })
    .filter(Boolean) as any[];
};

/** 映射 user 记录：历史消息中的文件只有下载链接（path），映射为 { name, url, path } 供展示与预览 */
const mapUserRecordMessage = (msg: any, uiKey: string) => {
  const historyFiles = Array.isArray(msg?.files)
    ? msg.files
        .filter((f: any) => f && (f.name || f.path))
        .map((f: any) => ({ name: f.name || '', url: f.path || '', path: f.path || '' }))
    : [];
  // 图片放在文档之后，保持文档在 files 中的原有下标（画布 artifactId 依赖下标）
  const mergedFiles = [...historyFiles, ...mapHistoryImageFiles(msg?.images)];
  return {
    role: 'user',
    content: msg?.display_content || msg?.user || '',
    ...(mergedFiles.length ? { files: mergedFiles } : {}),
    uiKey
  };
};

/**
 * 历史接口返回的引用通常缺少 knowledge_base_name 与 file_path，
 * 这里用当前工作区选中的知识库名兜底补全，使预览/下载能走 download_doc 接口。
 */
const enrichParsedCitations = (parsed: any[]): any[] | undefined => {
  if (!parsed || parsed.length === 0) return undefined;
  const kbName = (selectedKnowledgeBaseNames.value?.[0] || '').trim();
  if (!kbName) return parsed;
  return parsed.map((c) => ({ ...c, knowledge_base_name: kbName }));
};

/**
 * 映射 deepagent 历史记录：与实时对话保持一致，
 * 同一轮的 reasoning / tool_calls / response 合并为一条 assistant 消息，
 * 按生成顺序写入 orchestratorBlocks，工具执行结果放入 role:'tool' 消息（渲染时按 tool_call_id 反查）
 */
const mapDeepAgentRecordsToMessages = (records: any[]): any[] => {
  const messages: any[] = [];
  let uiKeySeed = 0;
  const genUiKey = () => `history-${Date.now()}-${++uiKeySeed}`;

  let assistant: any = null;
  const pendingToolMessages: any[] = [];
  // 知识库增强检索会话：system 记录携带检索片段，接口 kb_citations 为空时用于兜底还原“知识引用”
  let lastKbSystemPrompt = '';
  const resolveKbCitations = (msg: any): any[] | undefined => {
    const systemPrompt = lastKbSystemPrompt;
    lastKbSystemPrompt = '';
    if (Array.isArray(msg?.kb_citations) && msg.kb_citations.length > 0) return msg.kb_citations;
    const parsed = parseKbCitationsFromKnowledgePrompt(systemPrompt);
    return enrichParsedCitations(parsed);
  };

  const ensureAssistant = () => {
    if (!assistant) {
      assistant = {
        role: 'assistant',
        content: '',
        tool_calls: [] as any[],
        orchestratorBlocks: [] as any[],
        isStreaming: false,
        uiKey: genUiKey()
      };
    }
    return assistant;
  };

  const flushTurn = () => {
    if (!assistant) return;
    messages.push(assistant);
    messages.push(...pendingToolMessages);
    pendingToolMessages.length = 0;
    assistant = null;
  };

  const appendTextBlock = (type: 'content' | 'reasoning', text: string) => {
    if (!text) return;
    const msg = ensureAssistant();
    const blocks = msg.orchestratorBlocks;
    const last = blocks[blocks.length - 1];
    if (last && last.type === type) {
      last.content += text;
    } else {
      blocks.push({ type, content: text });
    }
  };

  for (const record of records) {
    const { msg_type, messages: msg } = record;

    if (msg_type === 'system') {
      lastKbSystemPrompt = msg?.system || '';
    } else if (msg_type === 'user') {
      flushTurn();
      messages.push(mapUserRecordMessage(msg, genUiKey()));
    } else if (msg_type === 'reasoning') {
      const text = msg?.reasoning || '';
      if (!text) continue;
      const current = ensureAssistant();
      current.reasoning_content = (current.reasoning_content || '') + text;
      appendTextBlock('reasoning', text);
    } else if (msg_type === 'tool_calls') {
      const current = ensureAssistant();
      for (const tc of (msg?.tool_calls || [])) {
        const id = tc?.tool_call_id || genUiKey();
        current.tool_calls.push({
          id,
          type: 'function',
          function: {
            name: tc?.tool || '',
            arguments: typeof tc?.input === 'string' ? tc.input : JSON.stringify(tc?.input || {})
          },
          status: tc?.status === 'success' ? 'completed' : 'failed'
        });
        const blocks = current.orchestratorBlocks;
        const last = blocks[blocks.length - 1];
        if (last && last.type === 'tools') {
          if (!last.toolCallIds.includes(id)) last.toolCallIds.push(id);
        } else {
          blocks.push({ type: 'tools', toolCallIds: [id] });
        }
        pendingToolMessages.push({ role: 'tool', content: tc?.output || '', tool_call_id: id });
      }
    } else if (msg_type === 'response') {
      const text = msg?.response || '';
      if (!text) continue;
      const current = ensureAssistant();
      current.content += text;
      appendTextBlock('content', text);
      const citations = resolveKbCitations(msg);
      if (citations) current.kb_citations = citations;
    }
  }
  flushTurn();

  return messages;
};

/** 将接口返回的 records 映射为内部 Message[] 格式 */
const mapRecordsToMessages = (records: any[], chatType?: string): any[] => {
  if (chatType === 'deepagent') {
    return mapDeepAgentRecordsToMessages(records);
  }

  const messages: any[] = [];
  let pendingReasoning = '';
  let uiKeySeed = 0;
  // 知识库增强检索会话：system 记录携带检索片段，接口 kb_citations 为空时用于兜底还原“知识引用”
  let pendingKbSystemPrompt = '';

  const genUiKey = () => `history-${Date.now()}-${++uiKeySeed}`;

  const resolveKbCitations = (msg: any): any[] | undefined => {
    const systemPrompt = pendingKbSystemPrompt;
    pendingKbSystemPrompt = '';
    if (Array.isArray(msg?.kb_citations) && msg.kb_citations.length > 0) return msg.kb_citations;
    const parsed = parseKbCitationsFromKnowledgePrompt(systemPrompt);
    return enrichParsedCitations(parsed);
  };

  for (const record of records) {
    const { msg_type, messages: msg } = record;

    if (msg_type === 'system') {
      pendingKbSystemPrompt = msg?.system || '';
    } else if (msg_type === 'user') {
      messages.push(mapUserRecordMessage(msg, genUiKey()));
      pendingReasoning = '';
    } else if (msg_type === 'reasoning') {
      pendingReasoning = msg?.reasoning || '';
    } else if (msg_type === 'tool_calls') {
      const toolCalls = (msg?.tool_calls || []).map((tc: any) => ({
        id: tc.tool_call_id || genUiKey(),
        type: 'function',
        function: {
          name: tc.tool || '',
          arguments: tc.input || ''
        },
        status: tc.status === 'success' ? 'completed' : 'failed',
        result: tc.output || ''
      }));
      messages.push({
        role: 'assistant',
        content: '',
        tool_calls: toolCalls,
        uiKey: genUiKey()
      });
    } else if (msg_type === 'response') {
      messages.push({
        role: 'assistant',
        content: msg?.response || '',
        reasoning_content: pendingReasoning || undefined,
        kb_citations: resolveKbCitations(msg),
        uiKey: genUiKey()
      });
      pendingReasoning = '';
    }
  }

  return messages;
};

const isRestoredHistoryMessage = (message: any) =>
  typeof message?.uiKey === 'string' && message.uiKey.startsWith('history-');

const isHistoryAutoOpenBlocked = () => {
  const currentSessionThreadId = (chatStore.sessionThreadId || '').trim();
  return !!currentSessionThreadId && historyAutoOpenBlockedSessionId.value === currentSessionThreadId;
};

// 右侧面板 Tab 切换：画布 / 交付中心 互斥
const switchRightPanel = (mode: 'canvas' | 'deliverables') => {
  if (!hasConversationMessages.value) {
    closeCanvasCompletely();
    return;
  }
  if (mode === 'canvas') {
    showDeliverables.value = false;
    showCanvas.value = true;
  } else {
    showCanvas.value = false;
    showDeliverables.value = true;
  }
  canvasHasBeenOpened.value = true;
};

const handleToggleCanvas = () => {
  if (!hasConversationMessages.value) {
    closeCanvasCompletely();
    return;
  }

  // 画布已打开时，再次点击关闭整个右侧面板
  if (showCanvas.value) {
    handleCloseCanvas();
    return;
  }

  if (lastOpenedArtifact.value) {
    const firstOpen = !canvasHasBeenOpened.value;
    switchRightPanel('canvas');
    if (firstOpen) {
      // 首次打开：需要加载 artifact
      pendingOpenArtifact.value = lastOpenedArtifact.value;
      nextTick(() => {
        tryApplyPendingOpenArtifact();
      });
    } else {
      // 重新打开：Canvas 里同文件已渲染完毕，仅恢复 visible 和 id，不重绘
      activeArtifactId.value = lastOpenedArtifact.value.id || '';
    }
  } else {
    // 没有待展示的 artifact 时，切到“交付中心”Tab
    switchRightPanel('deliverables');
  }
};

// 交付中心点击预览：切回画布，复用现有 artifact 预览管线
const handleDeliverablePreview = (file: SandboxFile) => {
  const ext = (file.filename.split('.').pop() || 'text').toLowerCase();
  switchRightPanel('canvas');
  handleOpenArtifact({
    code: file.download_url || file.path,
    lang: ext,
    id: `deliverable-${file.path}`,
    isComplete: true,
    title: file.filename,
    downloadUrl: file.download_url
  });
};

// DeepAgent 对话结束后若有新增交付文件，自动打开“交付中心”
const handleSandboxFilesUpdated = (payload?: { added?: unknown[] }) => {
  if (!hasConversationMessages.value) return;
  if (isHistoryAutoOpenBlocked()) return;
  const added = payload?.added;
  if (!Array.isArray(added) || added.length === 0) return;
  switchRightPanel('deliverables');
};

const handleCloseCanvas = () => {
  showCanvas.value = false;
  showDeliverables.value = false;
  activeArtifactId.value = '';
};

// 处理 Canvas 截图事件，转发到 ChatInput
const handleScreenshotStart = () => {
  const targetInput = chatInputBottomRef.value || chatInputWelcomeRef.value;
  const pendingMessageKey = `capture-message-${Date.now()}-${Math.random().toString(16).slice(2)}`;

  chatStore.messages.push({
    role: 'user',
    content: '',
    display_content: '',
    uiKey: pendingMessageKey,
    files: []
  });

  if (targetInput?.beginScreenshotCapture) {
    targetInput.beginScreenshotCapture(pendingMessageKey);
  }

  chatStore.setPendingInputImages([{
    key: `capture-pending-${Date.now()}`,
    url: '',
    alt: '正在截取网页页面',
    name: '网页截图',
    source: 'input',
    messageIndex: chatStore.messages.length - 1,
    messageId: pendingMessageKey,
    role: 'user',
    isCapturePending: true as any,
    pendingMessageKey
  }] as any);
};

const handleScreenshot = async (screenshotFile: File) => {
  const targetInput = chatInputBottomRef.value || chatInputWelcomeRef.value;
  if (targetInput?.handleScreenshot) {
    await targetInput.handleScreenshot(screenshotFile);
  } else {
    console.warn('ChatInput handleScreenshot 方法不可用');
  }
};

const handleNewChat = () => {
  cancelHistorySelection();
  handleBackToChat();
  closeCanvasCompletely();
  const preservedAgentId = chatStore.takePreservedReusableAgentId?.();
  if (preservedAgentId) {
    agentWorkspaceRef.value?.syncAgentSelectionForSession?.(preservedAgentId);
  }
  // 仍处于智能体模式时，清空后的新会话需要重新初始化，否则后端没有该会话的智能体上下文
  void agentWorkspaceRef.value?.reinitAgentForNewChat?.();
};

const handleClearCanvas = () => {
  closeCanvasCompletely();
};

function closeCanvasCompletely() {
  showCanvas.value = false;
  showDeliverables.value = false;
  canvasHasBeenOpened.value = false;
  activeArtifactId.value = '';
  pendingOpenArtifact.value = null;
  lastOpenedArtifact.value = null;
  canvasPanelRef.value?.clearCanvas?.();
}

// 普通对话重试时，关闭 Canvas 并清理相关状态
function handleRetryCleanup() {
  closeCanvasCompletely();
}

// 更新当前选中的智能体配置
function updateActiveAgent(evt?: Event) {
  try {
    // 优先使用事件中携带的最新配置，避免读取时序造成的旧值
    const ce = evt as CustomEvent | undefined;
    if (ce && (ce as any).detail && (ce as any).detail.activeAgent !== undefined) {
      activeAgent.value = (ce as any).detail.activeAgent || null;
      return;
    }

    activeAgent.value = StorageService.getActiveAgent();
  } catch (e) {
    activeAgent.value = null;
  }
}

type OpenArtifactPayload = { code: string | ArrayBuffer | ArrayBufferView; lang: string; id?: string; isComplete?: boolean; title?: string; downloadUrl?: string; autoOpen?: boolean };

const pendingOpenArtifact = ref<OpenArtifactPayload | null>(null);
const lastOpenedArtifact = ref<OpenArtifactPayload | null>(null);
const lastAppliedFingerprint = ref('');
const lastAppliedAt = ref(0);
const isUserFileArtifactId = (id?: string) => !!id && /-file-\d+$/.test(id);
const normalizeArtifactLang = (lang?: string) => (lang || '').toLowerCase().trim();
const getArtifactCodeMeta = (code: string | ArrayBuffer | ArrayBufferView) => {
  if (typeof code === 'string') return { kind: 'string', size: code.length, preview: code.slice(0, 120) };
  if (code instanceof ArrayBuffer) return { kind: 'ArrayBuffer', size: code.byteLength };
  if (ArrayBuffer.isView(code)) return { kind: 'ArrayBufferView', size: code.byteLength };
  return { kind: typeof code, size: 0 };
};
const buildArtifactFingerprint = (payload: OpenArtifactPayload) => {
  const meta = getArtifactCodeMeta(payload.code);
  return `${normalizeArtifactLang(payload.lang)}|${(payload.title || '').trim()}|${meta.kind}:${meta.size}`;
};

const tryApplyPendingOpenArtifact = () => {
  const payload = pendingOpenArtifact.value;
  if (!payload) {
    return;
  }
  if (!payload) return;
  if (!canvasPanelRef.value) return;

  const fingerprint = buildArtifactFingerprint(payload);
  const now = Date.now();
  // 避免短时间内同一 docx 因不同 id 被重复 apply，导致组件卸载重挂
  if (
    normalizeArtifactLang(payload.lang) === 'docx' &&
    lastAppliedFingerprint.value === fingerprint &&
    now - lastAppliedAt.value < 6000
  ) {
    pendingOpenArtifact.value = null;
    return;
  }

  activeArtifactId.value = payload.id || '';
  canvasPanelRef.value.setArtifact(payload.code, payload.lang, payload.id, payload.isComplete ?? true, payload.title, payload.downloadUrl);
  lastAppliedFingerprint.value = fingerprint;
  lastAppliedAt.value = now;
  pendingOpenArtifact.value = null;
};

watch(
  [() => canvasPanelRef.value, () => showCanvas.value],
  () => {
    nextTick(() => {
      tryApplyPendingOpenArtifact();
    });
  }
);

const handleOpenArtifact = (payload: OpenArtifactPayload) => {
  if (payload.autoOpen && (isHistoryAutoOpenBlocked() || chatStore.isProcessing)) return;

  const incomingFingerprint = buildArtifactFingerprint(payload);
  const sameAsLastOpened = !!lastOpenedArtifact.value && buildArtifactFingerprint(lastOpenedArtifact.value) === incomingFingerprint;

  // 同一文件已经在 Canvas 中渲染过（仅隐藏未销毁），直接显示，不重新 setArtifact 避免重绘
  if (sameAsLastOpened) {
    showDeliverables.value = false;
    showCanvas.value = true;
    canvasHasBeenOpened.value = true;
    activeArtifactId.value = payload.id || '';
    const lang = normalizeArtifactLang(payload.lang);
    if (lang === 'docx' || lang === 'xlsx' || lang === 'xls') {
      sessionStorage.setItem('shouldOpenInputToolbar', 'true');
      setTimeout(() => {
        window.dispatchEvent(new CustomEvent('open-input-toolbar'));
      }, 100);
    }
    return;
  }

  // 打开 Canvas（与交付面板互斥）
  showDeliverables.value = false;
  showCanvas.value = true;
  canvasHasBeenOpened.value = true;
  lastOpenedArtifact.value = payload;
  
  // 强制打开 input toolbar
  // 使用 sessionStorage 标记
  sessionStorage.setItem('shouldOpenInputToolbar', 'true');
  setTimeout(() => {
      window.dispatchEvent(new CustomEvent('open-input-toolbar'));
  }, 100);

  // 将待处理的 artifact 存入队列，等待 CanvasPanel 挂载
  pendingOpenArtifact.value = payload;
  
  // 尝试应用
  nextTick(() => {
    tryApplyPendingOpenArtifact();
  });
};

onMounted(() => {
  // 立即尝试恢复刷新前的原会话：恢复函数在同步阶段即置入加载态，
  // 因此首帧渲染的是历史会话加载而非空白欢迎页，避免“先新对话再切换”。
  void restoreActiveSessionOnRefresh();
  // 加载历史记录列表
  void fetchHistoryList();

  // 添加事件监听器
  window.addEventListener('open-agent-workspace', handleOpenAgentWorkspaceEvent as EventListener);
  window.addEventListener('open-knowledge-workspace', handleOpenKnowledgeWorkspaceEvent as EventListener);
  window.addEventListener('open-agent-picker', handleOpenAgentPickerEvent as EventListener);
  window.addEventListener('clear-canvas', handleClearCanvas as EventListener);
  // 监听普通对话重试事件，关闭 Canvas 并清理 toolbar
  eventBus.on('chat-retry-cleanup', handleRetryCleanup);
  // 监听沙箱交付文件更新，自动打开画布“交付中心”
  eventBus.on(MCP_EVENTS.SANDBOX_FILES_UPDATED, handleSandboxFilesUpdated);

  // 监听智能体选择或配置变更事件，实现欢迎区实时切换
  window.addEventListener('mcp-models-changed', updateActiveAgent);
  // 显式监听智能体选择事件（由 AgentWorkspace 派发）
  window.addEventListener('agent-selection-changed', updateActiveAgent as EventListener);
  // 监听活跃智能体更新事件，确保即时刷新到最新智能体信息
  window.addEventListener('active-agent-updated', updateActiveAgent as EventListener);

  // 当模型或系统提示词发生变化时，同步刷新活跃智能体状态
  watch(() => chatStore.model, () => updateActiveAgent());
  watch(() => chatStore.systemMessage, () => updateActiveAgent());

  // 当从Welcome页面跳转过来时，确保重新加载最新的配置
  // 这解决了客户端未初始化的问题
  setTimeout(() => {
    try {
      // 重新从localStorage加载配置
      chatStore.loadSavedConfig();
      // 应用配置到客户端
      if (chatStore.apiKey && chatStore.model && chatStore.apiBaseUrl) {
        chatStore.applyConfig();
      }
    } catch (error) {
      // ignore error
    }
  }, 300);

  // 监听消息列表变化，自动处理 artifact
  watch([() => chatStore.messages, () => chatStore.isProcessing], async ([newMsgs]) => {
    if (!newMsgs || newMsgs.length === 0) return;
    
    // 检查最后一条消息(可能是 assistant 或 tool)
    const lastMsg = newMsgs[newMsgs.length - 1];

    // 从左侧历史面板恢复整段会话时，仅渲染消息列表；文件仍可由用户点击预览，
    // 但不能复用实时消息的自动展开逻辑。
    if (isRestoredHistoryMessage(lastMsg) || isHistoryAutoOpenBlocked()) return;

    if (lastMsg.role === 'user' && (lastMsg as any).files?.length > 0) {
       // Ensure uiKey for stable ID
       if (!lastMsg.uiKey) {
           const uuid = (lastMsg as any).uuid;
           lastMsg.uiKey = (typeof uuid === 'string' && uuid) ? uuid : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
       }
      const msgId =
        (typeof lastMsg.uiKey === 'string' && lastMsg.uiKey) ||
        (typeof lastMsg.id === 'string' && lastMsg.id) ||
        `${Date.now()}-${Math.random().toString(16).slice(2)}`;
       const file = (lastMsg as any).files[0];
       
       // 跳过图片文件，图片不走Canvas流程
       if (file.isFileImage) {
           return;
       }
       
       // 构造 artifact ID - 必须与 ChatMessage 和 ChatInput 中保持一致 (msgId-file-index)
       // 目前只自动打开第一个文件，index 为 0
       const fileId = `${msgId}-file-0`;
       
       // 如果 Canvas 未打开，或者当前显示的不是这个文件，则打开
       // 注意：我们希望“添加的瞬间”打开，所以只要是最新消息带文件，就应该展示
       if (!showCanvas.value || activeArtifactId.value !== fileId) {
           showCanvas.value = true;
           canvasHasBeenOpened.value = true;

           // 确保底部输入框已显示（如果是第一条消息，可能还在等待版权淡出）
           if (!showBottomInput.value) {
               showBottomInput.value = true;
           }

           // 延迟触发工具栏打开事件，确保 ChatInput 和 InputToolbar 组件已挂载并监听事件
           // 使用 double nextTick 或 setTimeout 确保 DOM 更新完成
           // 使用 sessionStorage 标记作为可靠的回退机制
           sessionStorage.setItem('shouldOpenInputToolbar', 'true');
           nextTick(() => {
               setTimeout(() => {
                   window.dispatchEvent(new CustomEvent('open-input-toolbar'));
               }, 100);
           });
           
           nextTick(() => {
              if (canvasPanelRef.value) {
                  activeArtifactId.value = fileId;
                  // 获取文件扩展名作为类型
                  const ext = file.name.split('.').pop()?.toLowerCase() || 'text';
                  // 如果有原始内容 (ArrayBuffer) 则使用它，否则使用 content (可能是解析后的文本)
                  let content = file.content || '';
                  const isBuffer = file.content instanceof ArrayBuffer || ArrayBuffer.isView(file.content) || Object.prototype.toString.call(file.content) === '[object ArrayBuffer]';
                  if (file.content && isBuffer) {
                      content = file.content;
                  }
                  
                  // 对于 docx 类型，我们需要确保 CanvasPanel 知道它是文档
                  // 但 setArtifact 的 type 参数主要用于选择渲染器
                  // DocxPreview 需要 ArrayBuffer
                  
                  canvasPanelRef.value.setArtifact(
                      content,
                      ext,
                      fileId,
                      true, // 用户上传的文件被视为完整
                      file.name
                  );
                  lastOpenedArtifact.value = { code: content, lang: ext, id: fileId, isComplete: true, title: file.name };
                  
                  // 强制更新 CanvasPanel 的 activeArtifactId，确保视图切换
                  // 有时候 setArtifact 内部逻辑可能没触发 watcher
                  // 但我们在 setArtifact 中已经处理了。
              }
          });
      } else if (activeArtifactId.value !== fileId && showCanvas.value) {
          // 如果 Canvas 已经打开，但显示的不是当前文件，也需要切换
          // 这种情况可能发生在用户连续上传多个文件，或者在文件和对话之间切换
           nextTick(() => {
              if (canvasPanelRef.value) {
                  activeArtifactId.value = fileId;
                  const ext = file.name.split('.').pop()?.toLowerCase() || 'text';
                  let content = file.content || '';
                  if (file.content && (file.content instanceof ArrayBuffer || ArrayBuffer.isView(file.content))) {
                      content = file.content;
                  }
                  canvasPanelRef.value.setArtifact(content, ext, fileId, true, file.name);
                  lastOpenedArtifact.value = { code: content, lang: ext, id: fileId, isComplete: true, title: file.name };
              }
           });
      }
      return; // 处理完文件后，通常不需要继续处理 artifacts 解析（除非混合了内容，但用户消息通常主要关注文件）
   }

    // 消息正文混有任务过程；只取最终回答，流式期间同步解析以便代码边生成边预览。
    const msgForArtifact = [...newMsgs].reverse().find(message => message.role !== 'tool');
    if (!msgForArtifact || isRestoredHistoryMessage(msgForArtifact)) return;
    const contentToParse = getCanvasAnswerContent(msgForArtifact);
    if (!contentToParse) return;

    if (!msgForArtifact.uiKey) {
       const uuid = (msgForArtifact as any).uuid; // 兼容旧版字段
       msgForArtifact.uiKey = (typeof uuid === 'string' && uuid) ? uuid : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
    }
    const msgId =
      (typeof msgForArtifact.uiKey === 'string' && msgForArtifact.uiKey) ||
      (typeof msgForArtifact.id === 'string' && msgForArtifact.id) ||
      `${Date.now()}-${Math.random().toString(16).slice(2)}`;

    // 只预览助手正文中的产物，排除 <think> 中的示例和内部文件。
    const artifacts = parseAutoOpenArtifacts(contentToParse, msgId, msgForArtifact.role);

    // 过滤无效的 map artifact（来自 read_file 源代码输出中的模板字面量）
    // 不完整的 map artifact 如果内容不是有效的地图配置 JSON，说明是源代码片段，应丢弃
    const validArtifacts = artifacts.filter(a => {
      if (a.type !== 'map' || a.isComplete) return true;
      // 不完整的 map artifact 需要验证内容是否为有效的地图配置
      const content = typeof a.content === 'string' ? a.content.trim() : '';
      if (!content) return false;
      try {
        const parsed = JSON.parse(content);
        return parsed && (parsed.type === 'map' || parsed.queryParams || parsed.center);
      } catch {
        // 尝试 unescape 双重转义后重新解析（execute 工具输出可能含 \"、\\）
        if (content.includes('\\"')) {
          try {
            const unescaped = content.replace(/\\"/g, '"').replace(/\\\\/g, '\\');
            const parsed2 = JSON.parse(unescaped);
            if (parsed2 && (parsed2.type === 'map' || parsed2.queryParams || parsed2.center)) return true;
          } catch (_) { /* fall through */ }
        }
        // 内容不是有效 JSON（可能是源代码片段），丢弃
        return false;
      }
    });

    if (validArtifacts.length > 0) {
      // 对于 map 类型，优先选择包含 queryResult.features 的 artifact（skill 的完整数据）
      // 而非 LLM 生成的简化版本（可能没有 features）
      // 同时去重：如果多个完整 map artifact 内容相同，只保留第一个（避免 LLM 流式响应重复创建）
      let latest = validArtifacts[validArtifacts.length - 1];
      if (validArtifacts.length > 1) {
        const mapArtifacts = validArtifacts.filter(a => a.type === 'map');
        if (mapArtifacts.length > 1) {
          // 优先选择包含 features 的完整 artifact
          const withFeatures = mapArtifacts.find(a => {
            const text = typeof a.content === 'string' ? a.content : '';
            return a.isComplete && (text.includes('queryResult') || text.includes('features'));
          });
          if (withFeatures) {
            latest = withFeatures;
          } else {
            // 多个完整 map artifact → 保留第一个（tool_end 注入的），忽略 LLM 流式生成的重复
            const firstComplete = mapArtifacts.find(a => a.isComplete);
            if (firstComplete) latest = firstComplete;
          }
        }
      }
      const latestText = typeof latest.content === 'string' ? latest.content : '';

      const latestType = (latest.type || '').toLowerCase().trim();
      const hasTextPayload = latestText.trim().length > 0;
      // map 类型总是应该打开,不需要检查 hasTextPayload
      const shouldOpen =
        latestType === 'map' ||
        ['mermaid', 'html', 'svg', 'markdown', 'docx', 'pdf', 'json'].includes(latestType) ||
        ((latestType === 'text' || latestType === 'txt') && hasTextPayload);

      const isNewArtifact = latest.id !== lastProcessedArtifactId.value;
      if (isNewArtifact) {
          lastProcessedArtifactId.value = latest.id;
      }

      // 如果是特定类型，且Canvas未打开，则自动打开
      if (shouldOpen) {
        if (!showCanvas.value) {
          showCanvas.value = true;
          canvasHasBeenOpened.value = true;
          window.dispatchEvent(new CustomEvent('open-input-toolbar'));
        }
        
        // 实时更新Canvas内容
        nextTick(() => {
          if (canvasPanelRef.value) {
            const currentArtifactId = activeArtifactId.value;
            const shouldSkipDocxAutoSwitch =
              latestType === 'docx' &&
              showCanvas.value &&
              isUserFileArtifactId(currentArtifactId) &&
              currentArtifactId !== latest.id;

            // 避免“同一轮上传文件 + 助手回复 docx artifact”导致 Word 画布二次挂载
            if (shouldSkipDocxAutoSwitch) {
              return;
            }

            let shouldSwitch = false;
            // 1. 如果当前没有选中的 artifact，或者
            // 2. 当前显示的正是这个 artifact，或者
            // 3. 这是一个新出现的 artifact (自动弹出)
            if (!activeArtifactId.value || activeArtifactId.value === latest.id || isNewArtifact) {
                shouldSwitch = true;
            }

            if (shouldSwitch) {
                activeArtifactId.value = latest.id;
                canvasPanelRef.value.setArtifact(
                  latestText, 
                  latest.type, 
                  latest.id, 
                  latest.isComplete,
                  latest.title
                );
                lastOpenedArtifact.value = { code: latestText, lang: latest.type, id: latest.id, isComplete: latest.isComplete, title: latest.title };
            }
          }
        });
      }
    }
  }, { deep: true });

  // 初始化时检查智能体状态
  isAgentMode.value = !!StorageService.getActiveAgent();

  // 在组件卸载时移除事件监听器
  onUnmounted(() => {
    summaryPollTimers.forEach((timer) => window.clearTimeout(timer));
    summaryPollTimers.clear();
    pendingSummarySessionIds.clear();
    pendingHistoryRefreshSessionIds.clear();
    window.removeEventListener('open-agent-workspace', handleOpenAgentWorkspaceEvent as EventListener);
    window.removeEventListener('open-knowledge-workspace', handleOpenKnowledgeWorkspaceEvent as EventListener);
    window.removeEventListener('open-agent-picker', handleOpenAgentPickerEvent as EventListener);
    window.removeEventListener('clear-canvas', handleClearCanvas as EventListener);
    eventBus.off('chat-retry-cleanup', handleRetryCleanup);
    eventBus.off(MCP_EVENTS.SANDBOX_FILES_UPDATED, handleSandboxFilesUpdated);
    window.removeEventListener('mcp-models-changed', updateActiveAgent);
    window.removeEventListener('agent-selection-changed', updateActiveAgent as EventListener);
    window.removeEventListener('active-agent-updated', updateActiveAgent as EventListener);
  });
});
</script>

<style scoped>
@import '../assets/styles/chat-view.css';

.chat-header-host {
  display: contents;
}

/* 知识库视图只在工作区为 knowledge 时才存在于 DOM，因此不再依赖 .is-knowledge-workspace，
   否则离场动画期间该类已移除，padding-left 会从 64px 突变回 0，内容横向抽动。 */
.main-container:not(.with-history-rail) > .knowledge-base-workspace,
.main-container:not(.with-history-rail) > .delivery-center-workspace {
  padding-left: 64px;
}

/* 开合侧栏时 .main-container 的 width/margin-left 以 0.35s 过渡，
   而上面的 64px 左内边距随类切换瞬时增删，内容左缘会先跳 64px 再被容器动画拖回，
   形成横向抽动。这里用同一缓动参数过渡内边距，使其与侧栏动画同步。 */
.main-container > .knowledge-base-workspace,
.main-container > .delivery-center-workspace {
  transition: padding-left 0.35s cubic-bezier(0.25, 0.1, 0.25, 1);
}

/* 工作区切换：两个视图共用同一个网格行（chat-view.css 中的 grid-area: 2 / 1），
   离场时保持在流内、仅压低层级并停止响应，由新视图在上层浮现，
   既不会出现旧视图盖在新视图之上，也不会因脱离文档流而位移到头部区域。
   两者都是“向上”的短促位移 + 交叉淡出，退出时长与左侧工具栏取消选中保持一致。
   选择器带上 .main-container > 是为了压过上面那条 padding-left 过渡：
   transition 是简写属性，特异度更低时会被整体覆盖，opacity/transform 就失去动画。 */
.main-container > .workspace-fade-enter-active {
  position: relative;
  z-index: 2;
  transition:
    opacity 0.2s ease,
    transform var(--workspace-exit-duration) cubic-bezier(0.22, 1, 0.36, 1);
  will-change: opacity, transform;
}

.main-container > .workspace-fade-leave-active {
  position: relative;
  z-index: 1;
  pointer-events: none;
  transition:
    opacity 0.2s ease,
    transform var(--workspace-exit-duration) cubic-bezier(0.4, 0, 0.2, 1);
  will-change: opacity, transform;
}

.workspace-fade-enter-from {
  opacity: 0;
  transform: translateY(12px);
}

.workspace-fade-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

@media (prefers-reduced-motion: reduce) {
  .main-container > .workspace-fade-enter-active,
  .main-container > .workspace-fade-leave-active {
    transition-duration: 0.01ms;
  }
}

@font-face {
  font-family: 'SmileySansOblique';
  src: url('../assets/fonts/SmileySans-Oblique.woff2') format('woff2');
  font-display: swap;
}

.welcome-logo {
  font-family: 'SmileySansOblique', sans-serif;
}
</style>
