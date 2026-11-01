import { savePendingConversation, pendingConversations, getStreamStatus, forgetPendingConversation } from '@/services/conversationStream';
import { ref, onUnmounted, watch, type Ref } from 'vue';
import type { Message } from '@/types/mcp';
import { eventBus, MCP_EVENTS } from '@/utils/EventBus';
import NotificationService from '@/utils/NotificationService';
import { MCPClient } from '@/services/mcp/client';
import { useSystemPromptVariables } from './useSystemPromptVariables';
import StorageService from '@/utils/StorageService';
import { useOrchestratorChat } from './useOrchestratorChat';
import { getAgentType, resolveAgentType, shouldUseAgentConversationFlow, isAgentRenderingType } from '@/utils/agentMode';
import { estimateContextMetrics } from '@/utils/contextMetrics';
import { buildCompressionInput, buildLocalCompressionSummary } from '@/utils/contextCompression';
import type { ContextCompressionInfo } from '@/types/mcp';
import { runPromptEnhancers, type KnowledgeBaseConfig } from './promptEnhancers';
import {
  buildAgentMessageContent,
  buildFinalSystemPrompt as buildMessageManagerSystemPrompt,
  type SessionFileContext
} from './useMessageManager.helpers';

// 解构导入系统提示词变量处理函数
const { hasVariables, extractVariables, processSystemPrompt } = useSystemPromptVariables();

let uiKeySeed = 0;
function createUiKey(): string {
  uiKeySeed += 1;
  const uuid = (globalThis as any)?.crypto?.randomUUID?.();
  if (typeof uuid === 'string' && uuid) return uuid;
  return `${Date.now()}-${uiKeySeed}-${Math.random().toString(16).slice(2)}`;
}

// 生成一轮对话的唯一标识（turn_id）：
// 正常发送由 ChatInput 在上传/发送阶段生成并透传，此处仅为未携带 turnId 的入口
// （重新生成、编辑重发、中断确认等）兜底，生成后写入 sendContext 全链路透传
function createTurnId(): string {
  const uuid = (globalThis as any)?.crypto?.randomUUID?.();
  if (typeof uuid === 'string' && uuid) return uuid;
  return `turn-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

type SendMessageOptions = {
  reuseUserMessageUiKey?: string;
  turnId?: string;
};

type AgentSendContext = {
  selectedAgentId: string | null;
  allAgents: any[];
  currentAgent: any;
  activeAgentConfig: any;
  agentType: string | null;
  shouldUseAgentFlow: boolean;
  reuseUserMessageUiKey?: string;
  turnId?: string;
};

/**
 * 专门处理消息管理的composable
 * 职责：消息发送、接收、历史管理、系统消息设置
 */
export function useMessageManager(mcpClient: Ref<MCPClient>) {
  const messages = ref<Message[]>([]);
  const systemMessage = ref<string>('');
  // 用于存储当前会话累积的文件上下文
  const sessionFileContexts = ref<SessionFileContext[]>([]);
  // 用于存储“干净”的系统提示词（未包含文件内容的版本），以便在清空对话时恢复
  const lastCleanSystemMessage = ref<string>('');
  const compressedContextSummary = ref<string>('');
  const isProcessing = ref<boolean>(false);
  const error = ref<string | null>(null);
  const isCompressingContext = ref<boolean>(false);
  const contextCompressionInfo = ref<ContextCompressionInfo | null>(null);
  const orchestratorChat = useOrchestratorChat();
  let requestGeneration = 0;
  const isResuming = ref(false);
  
  // 创建取消订阅函数引用
  let messageCreatedUnsubscribe: (() => void) | null = null;
  let messageUpdatedUnsubscribe: (() => void) | null = null;
  let conversationStoppedUnsubscribe: (() => void) | null = null;

  watch(orchestratorChat.messages, (newMessages) => {
    const activeAgent = StorageService.getActiveAgent();
    const type = getAgentType(activeAgent);
    if (isResuming.value || isAgentRenderingType(type)) {
      messages.value = [...newMessages];
    }
  }, { deep: true });

  watch(orchestratorChat.isProcessing, (isProc) => {
    const activeAgent = StorageService.getActiveAgent();
    const type = getAgentType(activeAgent);
    if (isResuming.value || isAgentRenderingType(type)) {
      isProcessing.value = !!isProc;
    }
  });

  function isRegularConversationMode(): boolean {
    const selectedAgentId = StorageService.getSelectedAgent();
    const allAgents = StorageService.getAgents();
    const activeAgentConfig = StorageService.getActiveAgent();
    return !shouldUseAgentConversationFlow({
      selectedAgentId,
      allAgents,
      activeAgentConfig
    });
  }

  function buildEstimatedRequestMessages(messages: Message[], compressedSummary?: string): Message[] {
    const contextMessages = messages.filter((message) => !message.compressedIntoSummary && message.role !== 'tool');
    const requestMessages = [...contextMessages];
    const normalizedSummary = compressedSummary?.trim();

    if (!normalizedSummary) {
      return requestMessages;
    }

    const summaryMessage: Message = {
      role: 'assistant',
      content: `[历史上下文摘要]\n${normalizedSummary}`
    };
    const systemIndex = requestMessages.findIndex((message) => message.role === 'system');

    if (systemIndex >= 0) {
      requestMessages.splice(systemIndex + 1, 0, summaryMessage);
    } else {
      requestMessages.unshift(summaryMessage);
    }

    return requestMessages;
  }

  function resolveAgentSendContext(options?: SendMessageOptions): AgentSendContext {
    const selectedAgentId = StorageService.getSelectedAgent();
    const allAgents = StorageService.getAgents();
    const currentAgent = selectedAgentId
      ? allAgents.find((agent: any) => agent.id === selectedAgentId)
      : null;
    const activeAgentConfig = StorageService.getActiveAgent();

    return {
      selectedAgentId,
      allAgents,
      currentAgent,
      activeAgentConfig,
      agentType: resolveAgentType(selectedAgentId, allAgents, activeAgentConfig),
      shouldUseAgentFlow: shouldUseAgentConversationFlow({
        selectedAgentId,
        allAgents,
        activeAgentConfig
      }),
      reuseUserMessageUiKey: options?.reuseUserMessageUiKey,
      turnId: options?.turnId
    };
  }

  function getReusableUserMessage(targetMessages: Message[], reuseUserMessageUiKey?: string): Message | undefined {
    if (!reuseUserMessageUiKey) return undefined;
    return targetMessages.find((message) => message.role === 'user' && message.uiKey === reuseUserMessageUiKey);
  }

  function preparePendingMessages(content: string, files: any[] | undefined, sendContext: AgentSendContext): void {
    const turnId = sendContext.turnId || createTurnId();
    sendContext.turnId = turnId;

    if (sendContext.shouldUseAgentFlow) {
      // 智能体模式下以 orchestratorChat 为唯一历史来源。
      const reusedUserMessage = getReusableUserMessage(
        orchestratorChat.messages.value as Message[],
        sendContext.reuseUserMessageUiKey
      );

      if (reusedUserMessage) {
        reusedUserMessage.content = content;
        reusedUserMessage.turn_id = turnId;
        reusedUserMessage.display_content = content;
        reusedUserMessage.files = files;
      } else {
        orchestratorChat.messages.value.push({
          role: 'user',
          content,
          turn_id: turnId,
          display_content: content,
          uiKey: createUiKey(),
          files
        });
      }

      orchestratorChat.messages.value.push({
        role: 'assistant',
        content: '',
        turn_id: turnId,
        isStreaming: true,
        uiKey: createUiKey(),
        orchestratorBlocks: []
      });
      messages.value = [...orchestratorChat.messages.value];
      return;
    }

    const reusedUserMessage = getReusableUserMessage(messages.value, sendContext.reuseUserMessageUiKey);

    if (reusedUserMessage) {
      reusedUserMessage.content = content;
      reusedUserMessage.turn_id = turnId;
      reusedUserMessage.display_content = content;
      reusedUserMessage.files = files;
    } else {
      messages.value.push({
        role: 'user',
        content,
        turn_id: turnId,
        uiKey: createUiKey(),
        files
      });
    }

    messages.value.push({
      role: 'assistant',
      content: '',
      turn_id: turnId,
      reasoning_content: '',
      isStreaming: true,
      uiKey: createUiKey()
    });
  }

  async function loadPromptEnhancements(
    content: string,
    sendContext: AgentSendContext,
    files?: any[],
    kbConfig?: KnowledgeBaseConfig
  ) {
    return await runPromptEnhancers({
      content,
      sessionThreadId: orchestratorChat.sessionThreadId.value,
      turnId: sendContext.turnId,
      files,
      kbConfig,
      currentSessionFileContexts: sessionFileContexts.value,
      // 智能体对话的身份说明已由后端 system_role_prompt 注入，前端不再重复拼接
      enableIdentityEnhancer: !sendContext.shouldUseAgentFlow
    });
  }

  function resolveActiveAgentId(sendContext: AgentSendContext): string | undefined {
    return sendContext.currentAgent?.uuid
      || sendContext.currentAgent?.id
      || (sendContext.activeAgentConfig as any)?.uuid
      || (sendContext.activeAgentConfig as any)?.id;
  }

  async function tryHandleAgentConversation(
    content: string,
    files: any[] | undefined,
    sendContext: AgentSendContext,
    ragSystemPromptAddon: string,
    retrievedDocs?: any[]
  ): Promise<{ handled: boolean; success: boolean }> {
    if (sendContext.agentType === 'orchestrator') {
      const orchestratorContent = buildAgentMessageContent(content, ragSystemPromptAddon);
      const ok = await orchestratorChat.send(orchestratorContent, content, retrievedDocs, true, sendContext.turnId);
      return { handled: true, success: ok };
    }

    if (sendContext.agentType === 'assistant') {
      const agentId = resolveActiveAgentId(sendContext);

      if (agentId) {
        const assistantContent = buildAgentMessageContent(content, ragSystemPromptAddon);
        const ok = await orchestratorChat.sendToAgent(assistantContent, agentId, content, retrievedDocs, true, sendContext.turnId);
        return { handled: true, success: ok };
      }

      if (sendContext.selectedAgentId) {
        NotificationService.error('未找到有效的智能体ID');
        return { handled: true, success: false };
      }
    }

    if (sendContext.agentType === 'deepagent') {
      const agentId = resolveActiveAgentId(sendContext);

      if (agentId) {
        const assistantContent = buildAgentMessageContent(content, ragSystemPromptAddon);
        const filePaths = (files || []).map((file) => {
          if (file.parseResult?.data?.filename) {
            return file.parseResult.data.filename;
          }
          return file.name || '';
        }).filter(Boolean);
        const ok = await orchestratorChat.sendToDeepAgent(assistantContent, agentId, filePaths, content, retrievedDocs, true, sendContext.turnId);
        return { handled: true, success: ok };
      }

      if (sendContext.selectedAgentId) {
        NotificationService.error('未找到有效的智能体ID');
        return { handled: true, success: false };
      }
    }

    return { handled: false, success: false };
  }

  function applyEnhancedSessionFileContexts(nextSessionFileContexts?: SessionFileContext[]): void {
    if (!nextSessionFileContexts) return;
    sessionFileContexts.value = nextSessionFileContexts;
  }

  function buildFinalSystemPrompt(systemPromptAddons: string[]): string {
    return buildMessageManagerSystemPrompt({
      baseSystemPrompt: lastCleanSystemMessage.value || systemMessage.value || '',
      sessionFileContexts: sessionFileContexts.value,
      systemPromptAddons,
      hasActiveAgent: !!StorageService.getActiveAgent()
    });
  }

  function applyRequestSystemPrompt(systemPromptAddons: string[]): void {
    const hasTemporaryPrompt = sessionFileContexts.value.length > 0 || systemPromptAddons.length > 0;

    if (hasTemporaryPrompt) {
      setSystemMessage(buildFinalSystemPrompt(systemPromptAddons), true);
      return;
    }

    if (systemMessage.value !== lastCleanSystemMessage.value) {
      setSystemMessage(lastCleanSystemMessage.value, false);
    }
  }

  function createConversationCompletePromise(): Promise<void> {
    return new Promise<void>((resolve) => {
      const completeHandler = () => {
        resolve();
      };

      const unsubscribe = eventBus.once(MCP_EVENTS.CONVERSATION_COMPLETE, completeHandler);

      setTimeout(() => {
        unsubscribe();
        resolve();
      }, 30000);
    });
  }

  function removePendingStreamingMessage(): void {
    const lastMessage = messages.value[messages.value.length - 1];
    if (lastMessage && lastMessage.isStreaming && !lastMessage.content && !lastMessage.reasoning_content) {
      messages.value.pop();
    }
  }

  /**
   * 设置系统消息
   */
  function setSystemMessage(message: string, isTemporary: boolean = false): void {
    // 只有在非文件问答模式且非临时消息时，才视为“干净”的 Prompt 更新并进行备份
    if (sessionFileContexts.value.length === 0 && !isTemporary) {
      lastCleanSystemMessage.value = message;
    }
    systemMessage.value = message;
    // 系统消息的变量处理在 MessageHandler 中进行
    mcpClient.value.setSystemMessage(message);
  }

  /**
   * 清除聊天历史
   */
  function detachCurrentConversation(): void {
    requestGeneration++;
    orchestratorChat.detachCurrentRequest();
    mcpClient.value.detachCurrentRequest();
    // A detached client's final callbacks must not modify the next conversation.
    const previous = mcpClient.value;
    mcpClient.value = new MCPClient(previous.model, previous.apiKey, previous.baseUrl);
    isResuming.value = false;
    isProcessing.value = false;
  }

  async function resumeConversation(type: string, turnId: string, createdAt?: number): Promise<boolean> {
    const generation = ++requestGeneration;
    isResuming.value = true;
    isProcessing.value = true;
    try {
      const ok = await orchestratorChat.resumeStream(type, turnId, createdAt);
      if (generation !== requestGeneration) return false;
      messages.value = [...orchestratorChat.messages.value];
      mcpClient.value.replaceMessages(messages.value);
      return ok;
    } finally {
      if (generation === requestGeneration) { isProcessing.value = false; isResuming.value = false; }
    }
  }

  function clearChat(options?: { regenerateSessionThreadId?: boolean }): void {

    detachCurrentConversation();
    mcpClient.value.clearHistory();
    messages.value = [];
    sessionFileContexts.value = []; // 清空累积的文件上下文
    compressedContextSummary.value = '';
    contextCompressionInfo.value = null;
    orchestratorChat.clear(options);
    
    // 优先恢复到最近一次“干净”的系统提示词（备份值）
    let targetPrompt = lastCleanSystemMessage.value;

    // 如果备份为空（可能初始化后从未设置过），则尝试从缓存或配置恢复
    if (!targetPrompt) {
        // 尝试从本地缓存恢复
        targetPrompt = getSystemMessage();
    }
    
    // 强制重置系统消息为原始值
    setSystemMessage(targetPrompt);
  }

  /**
   * 截断消息列表到指定索引
   */
  function truncateMessagesTo(endIndex: number): void {
    const agentType = getAgentType(StorageService.getActiveAgent());

    // 智能体模式直接截断 orchestratorChat 历史。
    if (agentType === 'orchestrator' || agentType === 'assistant' || agentType === 'deepagent') {
      const list = orchestratorChat.messages.value;
      orchestratorChat.messages.value = endIndex >= 0 && Array.isArray(list)
        ? list.slice(0, endIndex + 1)
        : [];
      messages.value = [...orchestratorChat.messages.value];
      return;
    }

    mcpClient.value.truncateMessagesTo(endIndex);
    messages.value = [...mcpClient.value.getMessages()];
  }

  /**
   * 在编排式智能体模式下移除指定索引的智能体消息
   */
  function removeAssistantMessageAt(index: number): void {
    const agentType = getAgentType(StorageService.getActiveAgent());
    if (agentType !== 'orchestrator') return;
    const list = orchestratorChat.messages.value;
    if (!Array.isArray(list)) return;
    if (index < 0 || index >= list.length) return;
    if (list[index]?.role !== 'assistant') return;
    list.splice(index, 1);
    // 同步到本地 UI 列表
    messages.value = [...list];
  }

  /**
   * 在编排式智能体模式下重试（仅添加智能体消息，不追加用户消息）
   */
  async function retryAssistant(): Promise<boolean> {
    const agentType = getAgentType(StorageService.getActiveAgent());
    if (agentType !== 'orchestrator' && agentType !== 'assistant' && agentType !== 'deepagent') return false;
    return await orchestratorChat.retry();
  }

  /**
   * 获取系统提示词变量信息
   */
  function getSystemPromptVariableInfo() {
    const currentSystemMessage = systemMessage.value;
    return {
      hasVariables: hasVariables(currentSystemMessage),
      variables: extractVariables(currentSystemMessage),
      processedContent: processSystemPrompt(currentSystemMessage)
    };
  }

  /**
   * 注册消息更新事件监听器
   */
  function setupStreamingEventListeners(): void {
    // 先清理之前的监听器
    if (messageCreatedUnsubscribe) {
      messageCreatedUnsubscribe();
    }
    if (messageUpdatedUnsubscribe) {
      messageUpdatedUnsubscribe();
    }
    if (conversationStoppedUnsubscribe) {
      conversationStoppedUnsubscribe();
    }
    
    // 监听消息创建事件
    messageCreatedUnsubscribe = eventBus.on(MCP_EVENTS.MESSAGE_CREATED, (event) => {
      if (!isResuming.value && event?.message && mcpClient.value.getMessages().some(m => m.uiKey === event.message.uiKey)) {
        // 添加新消息到UI
        messages.value = [...mcpClient.value.getMessages()];
      }
    });
    
    // 监听消息更新事件
    messageUpdatedUnsubscribe = eventBus.on(MCP_EVENTS.MESSAGE_UPDATED, (event) => {
      if (!isResuming.value && event?.message && mcpClient.value.getMessages().some(m => m.uiKey === event.message.uiKey)) {
        // 更新消息列表，触发UI重新渲染
        messages.value = [...mcpClient.value.getMessages()];
      }
    });
    
    // 监听对话停止事件
    conversationStoppedUnsubscribe = eventBus.on(MCP_EVENTS.CONVERSATION_STOPPED, () => {
      // 找到最后一个流式智能体消息并标记为已停止
      const lastMessage = messages.value[messages.value.length - 1];
      if (lastMessage && lastMessage.role === 'assistant' && lastMessage.isStreaming) {
        (lastMessage as any).isStopped = true;
        lastMessage.isStreaming = false;
        // 触发UI更新
        messages.value = [...messages.value];
      }
    });
  }

  /**
   * 发送消息
   */
  async function sendMessage(
    content: string,
    files?: any[],
    kbConfig?: { enabled: boolean, kbNames: string[] },
    options?: SendMessageOptions
  ): Promise<boolean> {
    // 如果没有内容且没有文件，且不是重试（重试逻辑在其他地方），则不发送
    // 但如果用户上传了文件，允许内容为空（后续会设置默认内容）
    if (!content.trim() && (!files || files.length === 0)) return false;

    const generation = ++requestGeneration;
    const isCurrent = () => generation === requestGeneration;
    isResuming.value = false;
    isProcessing.value = true;
    error.value = null;
    const sendContext = resolveAgentSendContext(options);
    preparePendingMessages(content, files, sendContext);
    const sendingSessionId = orchestratorChat.sessionThreadId.value;
    savePendingConversation({ sessionThreadId: sendingSessionId, chatType: sendContext.agentType === 'deepagent' ? 'deepagent' : sendContext.agentType === 'assistant' ? 'agent' : sendContext.agentType === 'orchestrator' ? 'travel_planner' : kbConfig?.enabled ? 'kb_chat' : 'model', agentId: resolveActiveAgentId(sendContext) || '', turnId: sendContext.turnId || '', user: [...messages.value].reverse().find(m => m.role === 'user') });

    try {
      const {
        systemPromptAddons,
        retrievedDocs,
        sessionFileContexts: enhancedSessionFileContexts
      } = await loadPromptEnhancements(content, sendContext, files, kbConfig);
      if (!isCurrent()) return false;
      const ragSystemPromptAddon = systemPromptAddons[0] || '';
      const agentResult = await tryHandleAgentConversation(
        content,
        files,
        sendContext,
        ragSystemPromptAddon,
        retrievedDocs
      );

      if (!isCurrent()) return false;
      if (agentResult.handled) {
        return agentResult.success;
      }

      applyEnhancedSessionFileContexts(enhancedSessionFileContexts);
      applyRequestSystemPrompt(systemPromptAddons);
      const conversationComplete = createConversationCompletePromise();

      // 启用知识库检索增强时上报 kb_chat，否则为普通对话 model
      const isKbChat = !!kbConfig?.enabled && !!kbConfig.kbNames?.length;

      const result = await mcpClient.value.processQuery(
        content,
        files,
        content,
        retrievedDocs,
        {
          compressedSummary: compressedContextSummary.value,
          sessionThreadId: orchestratorChat.sessionThreadId.value,
          turnId: sendContext.turnId,
          chatType: isKbChat ? 'kb_chat' : 'model'
        }
      );
      
      if (!isCurrent()) return false;
      // 检查是否有错误
      if (result.error) {
        NotificationService.error(result.error);
        removePendingStreamingMessage();
      }
      
      // 不要覆盖消息列表，依赖事件系统来更新消息
      // messages.value = [...result.messages];
      
      // 等待对话完全完成的事件
      await conversationComplete;
      
      return !result.error;
    } catch (e) {
      if (!isCurrent()) return false;
      const errorMsg = `处理消息时出错: ${e}`;
      NotificationService.error(errorMsg);
      removePendingStreamingMessage();
      
      return false;
    } finally {
      if (isCurrent()) {
        isProcessing.value = false;
        const pending = pendingConversations()[sendingSessionId];
        if (pending?.turnId === sendContext.turnId) {
          void getStreamStatus(pending.chatType, sendingSessionId).then(status => {
            if (!status.exists && pendingConversations()[sendingSessionId]?.turnId === pending.turnId) forgetPendingConversation(sendingSessionId);
          }).catch(() => {});
        }
      }
    }
  }
  
  /**
   * 获取系统消息（从本地存储）
   */
  function getSystemMessage(): string {
    const current = StorageService.getSystemMessage();
    if (typeof current === 'string') {
      return current;
    }
    // 向后兼容：迁移旧 key 的值到统一存储
    const legacy = localStorage.getItem('mcp-system-message') || '';
    if (legacy) {
      StorageService.setSystemMessage(legacy);
      localStorage.removeItem('mcp-system-message');
      return legacy;
    }
    return '';
  }

  /**
   * 保存系统消息到本地存储
   */
  function saveSystemMessage(message: string): void {
    StorageService.setSystemMessage(message);
    // 清理旧 key，避免后续逻辑再次读到历史残留
    localStorage.removeItem('mcp-system-message');
  }

  function replaceMessages(nextMessages: Message[]): void {
    const normalizedMessages = Array.isArray(nextMessages) ? nextMessages : [];
    orchestratorChat.replaceMessages(normalizedMessages);
    mcpClient.value.replaceMessages(normalizedMessages);
    messages.value = normalizedMessages.map((message) => ({
      ...message,
      tool_calls: Array.isArray(message?.tool_calls)
        ? message.tool_calls.map((toolCall) => ({
            ...toolCall,
            function: toolCall?.function ? { ...toolCall.function } : toolCall?.function
          }))
        : message?.tool_calls,
      orchestratorBlocks: Array.isArray(message?.orchestratorBlocks)
        ? message.orchestratorBlocks.map((block) => (
            block?.type === 'tools'
              ? { ...block, toolCallIds: Array.isArray(block.toolCallIds) ? [...block.toolCallIds] : [] }
              : { ...block }
          ))
        : message?.orchestratorBlocks,
      files: Array.isArray(message?.files) ? message.files.map((file) => ({ ...file })) : message?.files,
      kb_citations: Array.isArray(message?.kb_citations)
        ? message.kb_citations.map((citation) => ({ ...citation }))
        : message?.kb_citations,
      todos: Array.isArray(message?.todos) ? message.todos.map((todo) => ({ ...todo })) : message?.todos
    }));
  }

  async function compressConversationContext(): Promise<boolean> {
    if (isProcessing.value || isCompressingContext.value) {
      return false;
    }

    if (!isRegularConversationMode()) {
      NotificationService.warning('上下文压缩仅支持普通对话模式');
      return false;
    }

    const currentMessages = [...mcpClient.value.getMessages()];
    const conversationalMessages = currentMessages.filter((message) => (
      message.role === 'user' || message.role === 'assistant'
    ));
    const messagesToCompress = conversationalMessages
      .filter((message) => !message.compressedIntoSummary);
    const hasFileContexts = sessionFileContexts.value.length > 0;

    if (messagesToCompress.length === 0 && !hasFileContexts) {
      NotificationService.info('当前没有可压缩的历史上下文');
      return false;
    }

    isCompressingContext.value = true;

    try {
      const tools: any[] = [];
      const beforeRequestMessages = buildEstimatedRequestMessages(
        currentMessages,
        compressedContextSummary.value
      );
      const estimatedBeforeMetrics = estimateContextMetrics({
        model: mcpClient.value.model,
        messages: beforeRequestMessages,
        tools
      });
      const lastAssistantMessage = [...messages.value].reverse().find((message) => message.role === 'assistant');
      const beforeMetrics = lastAssistantMessage?.contextMetrics?.mode === 'exact'
        ? {
            ...estimatedBeforeMetrics,
            mode: 'exact' as const,
            promptTokens: lastAssistantMessage.contextMetrics.promptTokens,
            messagesTokens: lastAssistantMessage.contextMetrics.messagesTokens,
            textTokens: lastAssistantMessage.contextMetrics.textTokens,
            imageTokens: lastAssistantMessage.contextMetrics.imageTokens,
            utilization: (estimatedBeforeMetrics.contextWindow ?? 0) > 0
              ? lastAssistantMessage.contextMetrics.promptTokens / (estimatedBeforeMetrics.contextWindow ?? 0)
              : 0
          }
        : estimatedBeforeMetrics;

      const compressionInput = buildCompressionInput(messagesToCompress, sessionFileContexts.value);
      let summary = '';

      if (compressionInput) {
        try {
          summary = await mcpClient.value.summarizeContextForCompression(compressionInput);
        } catch (error) {
          console.warn('模型摘要压缩失败，回退为本地摘要:', error);
        }
      }

      if (!summary) {
        summary = buildLocalCompressionSummary(messagesToCompress, sessionFileContexts.value);
      }

      const compressedMessageSet = new Set(messagesToCompress);
      const candidateMessages = currentMessages.map((message) => (
        compressedMessageSet.has(message)
          ? { ...message, compressedIntoSummary: true }
          : message
      ));
      const afterRequestMessages = buildEstimatedRequestMessages(candidateMessages, summary);
      const afterMetrics = estimateContextMetrics({
        model: mcpClient.value.model,
        messages: afterRequestMessages,
        tools
      });

      compressedContextSummary.value = summary;
      sessionFileContexts.value = [];
      messagesToCompress.forEach((message) => {
        message.compressedIntoSummary = true;
      });

      contextCompressionInfo.value = {
        beforePromptTokens: beforeMetrics.promptTokens,
        afterPromptTokens: afterMetrics.promptTokens,
        reducedTokens: Math.max(0, beforeMetrics.promptTokens - afterMetrics.promptTokens),
        compressedMessageCount: messagesToCompress.length,
        keptMessageCount: 0,
        hasCompressedFiles: hasFileContexts,
        updatedAt: Date.now()
      };

      if (lastAssistantMessage) {
        lastAssistantMessage.contextMetrics = afterMetrics;
      }

      messages.value = [...messages.value];
      NotificationService.success('上下文已压缩');
      return true;
    } catch (error) {
      console.error('压缩上下文失败:', error);
      NotificationService.error('上下文压缩失败，请稍后重试');
      return false;
    } finally {
      isCompressingContext.value = false;
    }
  }
  
  // 初始设置事件监听器
  setupStreamingEventListeners();
  
  // 在组件卸载时清理事件监听
  onUnmounted(() => {
    if (messageCreatedUnsubscribe) {
      messageCreatedUnsubscribe();
    }
    if (messageUpdatedUnsubscribe) {
      messageUpdatedUnsubscribe();
    }
    if (conversationStoppedUnsubscribe) {
      conversationStoppedUnsubscribe();
    }
  });

  return {
    messages,
    systemMessage,
    isProcessing,
    error,
    orchestratorChat,
    setSystemMessage,
    clearChat,
    detachCurrentConversation,
    resumeConversation,
    truncateMessagesTo,
    removeAssistantMessageAt,
    retryAssistant,
    sendMessage,
    setupStreamingEventListeners,
    getSystemMessage,
    saveSystemMessage,
    replaceMessages,
    getSystemPromptVariableInfo,
    sessionFileContexts,
    compressConversationContext,
    isCompressingContext,
    contextCompressionInfo
  };
}
