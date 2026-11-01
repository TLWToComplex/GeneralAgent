import { AgentStandbyPool } from '@/utils/agentStandbyPool';
import { AgentInitializationRegistry } from '@/utils/agentInitialization';
import { pendingConversations } from '@/services/conversationStream';
import {defineStore} from 'pinia';
import {computed, ref} from 'vue';
import {v4 as uuidv4} from 'uuid';
import {useMcpClient} from '@/composables/useMcpClient';
import {useChatConfigStore} from './chatConfigStore';
import {useChatMessagesStore} from './chatMessagesStore';
import StorageService from '@/utils/StorageService';
import type { ConversationImageItem } from '@/utils/conversationImages';
import type { PendingInputImage } from '@/types/mcp';

/**
 * 主聊天 store，整合其他功能模块
 */
export const useChatStore = defineStore('chat', () => {
    // 使用拆分后的 store
    const configStore = useChatConfigStore();
    const messagesStore = useChatMessagesStore();

    // 使用 MCP client composable，传入初始空值
    const {
        messages,
        systemMessage,
        isProcessing,
        error,
        setSystemMessage: mcpSetSystemMessage,
        clearChat,
        detachCurrentConversation,
        resumeConversation,
        replaceMessages,
        sendMessage: mcpSendMessage,
        setCredentials,
        stopCurrentRequest,
        truncateMessagesTo,
        removeAssistantMessageAt,
        retryAssistant,
        compressConversationContext: mcpCompressConversationContext,
        isCompressingContext,
        contextCompressionInfo,
        sessionThreadId,
        initializeAgentSession,
        startSandboxContainer,
        releaseSandboxContainer: releaseSandboxContainerRemote,
        regenerateSessionThreadId,
        setSessionThreadId
    } = useMcpClient(
        configStore.model,
        configStore.apiKey,
        configStore.apiBaseUrl
    );

    const pendingInputImages = ref<Array<ConversationImageItem | PendingInputImage>>([]);

    // ===== 智能体初始化状态机 =====
    /** 智能体初始化状态：idle 未初始化 / initializing 初始化中 / ready 就绪 / error 失败 */
    const agentInitStatus = ref<'idle' | 'initializing' | 'ready' | 'error'>('idle');
    const agentInitError = ref('');
    let agentInitGeneration = 0;
    const agentInitializations = new AgentInitializationRegistry();
    /** 当前需要维持备用上下文的智能体。 */
    let lastInitAgentUuid = '';
    /** 容器已就绪（初始化成功）的会话 ID；用于判断某个会话 ID 是否可以直接复用而无需再等建容器 */
    const agentReadySessionId = ref('');
    const sessionAgents = new Map<string, string>();
    /** 只有被明确标记的空白新对话 session 才允许再次复用，避免误接管真实历史/后台任务会话 */
    const reusableSessionIds = new Set<string>();
    /** 暂存的空白新对话 session：切到历史后，返回新对话时优先恢复它 */
    let preservedReusableSessionId = '';
    /** 与暂存空白新对话 session 绑定的智能体 ID，用于返回新对话时恢复智能体身份 */
    let preservedReusableAgentId = '';

    const isAgentInitializing = computed(() => agentInitStatus.value === 'initializing');

    function markSessionReusable(targetSessionId?: string) {
        const sessionId = String(targetSessionId || '').trim();
        if (!sessionId) return;
        reusableSessionIds.add(sessionId);
    }

    function clearReusableSession(targetSessionId?: string) {
        const sessionId = String(targetSessionId || '').trim();
        if (!sessionId) return;
        reusableSessionIds.delete(sessionId);
    }

    function isReusableSession(targetSessionId?: string) {
        const sessionId = String(targetSessionId || '').trim();
        if (!sessionId) return false;
        return reusableSessionIds.has(sessionId);
    }

    function preserveReusableSession(targetSessionId?: string, agentId?: string) {
        const sessionId = String(targetSessionId || sessionThreadId.value || '').trim();
        if (!sessionId || !isReusableSession(sessionId)) return false;
        if (messages.value.length || pendingConversations()[sessionId]) return false;

        const previousPreservedSessionId = String(preservedReusableSessionId || '').trim();
        if (previousPreservedSessionId && previousPreservedSessionId !== sessionId && !pendingConversations()[previousPreservedSessionId]) {
            clearReusableSession(previousPreservedSessionId);
            if (agentReadySessionId.value === previousPreservedSessionId) agentReadySessionId.value = '';
            releaseInitializedSession(previousPreservedSessionId);
        }

        preservedReusableSessionId = sessionId;
        preservedReusableAgentId = String(agentId || preservedReusableAgentId || '').trim();
        return true;
    }

    function takePreservedReusableSessionId(): string {
        const sessionId = String(preservedReusableSessionId || '').trim();
        if (!sessionId || pendingConversations()[sessionId]) return '';
        preservedReusableSessionId = '';
        return sessionId;
    }

    function takePreservedReusableAgentId(): string {
        const agentId = String(preservedReusableAgentId || '').trim();
        preservedReusableAgentId = '';
        return agentId;
    }

    /** 切换只更新当前视图，初始化结果和进行中的请求按会话保留。 */
    function startAgentInit(
        agentUuid: string,
        existingSessionThreadId?: string,
        isCurrent: () => boolean = () => true,
        options?: { reusable?: boolean }
    ): Promise<string> {
        const targetId = String(existingSessionThreadId || '').trim() || uuidv4();
        if (sessionThreadId.value !== targetId) setSessionThreadId(targetId);
        const generation = ++agentInitGeneration;
        const canCommit = () => generation === agentInitGeneration &&
            sessionThreadId.value === targetId && isCurrent();
        lastInitAgentUuid = agentUuid;
        standbyPool.activate(agentUuid);
        sessionAgents.set(targetId, agentUuid);
        const result = agentInitializations.ensure(targetId, agentIdentity(agentUuid),
            () => startSandboxContainer(targetId, agentUuid));
        if (options?.reusable) markSessionReusable(targetId);
        else clearReusableSession(targetId);
        agentInitStatus.value = result.ready ? 'ready' : 'initializing';
        agentInitError.value = '';
        agentReadySessionId.value = result.ready ? targetId : '';
        const promise = result.promise.then((threadId) => {
            if (canCommit()) {
                agentInitStatus.value = 'ready';
                agentReadySessionId.value = threadId;
                void refillSpareSandbox();
            }
            return threadId;
        }).catch((e: unknown) => {
            if (canCommit()) {
                agentInitStatus.value = 'error';
                agentInitError.value = (e as Error)?.message || '智能体初始化失败';
                agentReadySessionId.value = '';
            }
            throw e;
        });
        promise.catch(() => {});
        return promise;
    }

    /** 只重置当前视图，不取消已暂存会话的初始化。 */
    function resetAgentInit() {
        agentInitGeneration++;
        standbyPool.activate('');
        agentInitStatus.value = 'idle';
        agentInitError.value = '';
        agentReadySessionId.value = '';
    }

    function releaseInitializedSession(sessionId: string) {
        sessionAgents.delete(sessionId);
        clearReusableSession(sessionId);
        void agentInitializations.invalidate(sessionId, () => releaseSandboxContainerRemote(sessionId));
    }

    /** 切换智能体时将当前空白会话交回池中，后台继续初始化。 */
    function retainCurrentAgentSession(): boolean {
        const id = sessionThreadId.value;
        const agent = sessionAgents.get(id);
        const initialization = agentInitializations.get(id);
        if (!agent || !initialization || !isReusableSession(id) ||
            messages.value.length || pendingConversations()[id]) return false;
        // 历史导航暂存的会话已有独立所有权，不能同时交给池淘汰。
        if (preservedReusableSessionId !== id) standbyPool.retain(agent, id, initialization);
        resetAgentInit();
        return true;
    }

    // ===== 按智能体隔离的备用上下文池 =====
    function resolveAgentUuid(agent: any): string {
        return String(agent?.uuid || agent?.config?.basic?.uuid || agent?.id || '').trim();
    }

    function agentIdentity(agentUuid: string): string {
        const selected = StorageService.getSelectedAgent();
        const agents = StorageService.getAgents() || [];
        const agent = agents.find((item: any) => resolveAgentUuid(item) === agentUuid);
        const active = StorageService.getActiveAgent();
        const config = agent && String(agent.id) !== String(selected) ? agent.config : (active || agent?.config);
        // 仅存内存，不写日志；配置和登录身份变化后不能复用旧上下文。
        return JSON.stringify([StorageService.getAccessToken(), configStore.apiBaseUrl, agentUuid, config]);
    }

    const standbyPool = new AgentStandbyPool({
        createId: uuidv4,
        identity: agentIdentity,
        initialize: (sessionId, agentUuid, identity) => {
            sessionAgents.set(sessionId, agentUuid);
            return agentInitializations.ensure(sessionId, identity,
                () => startSandboxContainer(sessionId, agentUuid, { silent: true })).promise;
        },
        release: releaseInitializedSession,
        capacity: 3,
        // 小于初始化记录的 5 分钟有效期，避免取出过期记录再初始化。
        ttl: 4 * 60 * 1000
    });

    function prewarmSandbox(agentUuid?: string): Promise<void> {
        const uuid = String(agentUuid || lastInitAgentUuid || '').trim();
        if (!uuid) return Promise.resolve();
        lastInitAgentUuid = uuid;
        standbyPool.activate(uuid);
        return standbyPool.warm(uuid);
    }

    function takeSpareSandboxSessionId(agentUuid = lastInitAgentUuid): string {
        const id = standbyPool.take(agentUuid);
        if (id) markSessionReusable(id);
        return id;
    }

    /** 通用新对话恢复暂存草稿；明确选择智能体时只能使用该智能体的上下文。 */
    function resolveWarmSandboxSessionId(agentUuid?: string): string {
        if (!agentUuid || sessionAgents.get(preservedReusableSessionId) === agentUuid) {
            const preservedSessionId = takePreservedReusableSessionId();
            if (preservedSessionId) {
                // 明确选择智能体时由调用方设置身份，不留给后续新对话误用。
                if (agentUuid) preservedReusableAgentId = '';
                return preservedSessionId;
            }
        }
        const targetAgent = agentUuid || lastInitAgentUuid;
        const currentId = sessionThreadId.value;
        if (!messages.value.length && !pendingConversations()[currentId] &&
            isReusableSession(currentId) && sessionAgents.get(currentId) === targetAgent) {
            return currentId;
        }
        return takeSpareSandboxSessionId(targetAgent);
    }

    /** 实际释放时同步失效初始化记录，创建和释放按同一会话顺序执行。 */
    function releaseSandboxContainer(targetSessionId: string) {
        const sessionId = String(targetSessionId || '').trim();
        if (!sessionId || pendingConversations()[sessionId]) return;
        if (preservedReusableSessionId === sessionId) return;
        if (agentReadySessionId.value === sessionId) agentReadySessionId.value = '';
        clearReusableSession(sessionId);
        releaseInitializedSession(sessionId);
    }

    /** 仅补充当前智能体，旧智能体条目保留到过期或容量淘汰。 */
    function refillSpareSandbox(): Promise<void> {
        return standbyPool.warm(lastInitAgentUuid);
    }

    function discardSpareSandbox() {
        agentInitGeneration++;
        lastInitAgentUuid = '';
        standbyPool.discard();
    }

    /**
     * 应用配置
     */
    function applyConfig() {
        // 检查当前模型是否在可用模型列表中
        const allModels = configStore.availableModels;

        // 只有当模型列表不为空时才检查模型有效性
        if (allModels.length > 0) {
            // 如果当前没有选择模型，直接选择第一个可用模型
            if (!configStore.model) {
                configStore.model = allModels[0].id;
                configStore.selectedModelService = allModels[0].serviceProvider || '';
            } else {
                // 检查当前选择的模型是否在可用列表中
                const modelExists = allModels.some(m =>
                    m.id === configStore.model &&
                    (!configStore.selectedModelService || m.serviceProvider === configStore.selectedModelService)
                );
                if (!modelExists) {
                    configStore.model = allModels[0].id;
                    configStore.selectedModelService = allModels[0].serviceProvider || '';
                }
            }
        }

        try {
            // 应用配置到 MCP 客户端
            setCredentials(configStore.apiKey, configStore.apiBaseUrl, configStore.model);

            // 保存配置到本地存储
            configStore.saveConfig();

            return true;
        } catch (e) {
            console.error('应用配置失败:', e);
            configStore.setError('配置应用失败: ' + (e as Error).message);
            return false;
        }
    }

    /**
     * 设置系统提示词
     */
    function setSystemMessage(message: string, persist: boolean = true) {
        messagesStore.setSystemMessage(message, mcpSetSystemMessage, persist);
    }

    /**
     * 发送消息
     * 发送消息
     */
    async function sendMessage(
        content: string,
        files?: any[],
        kbConfig?: { enabled: boolean, kbNames: string[] },
        options?: { reuseUserMessageUiKey?: string, turnId?: string }
    ) {
        clearReusableSession(sessionThreadId.value);
        return await messagesStore.sendMessage(content, mcpSendMessage, configStore.isConfigured, files, kbConfig, options);
    }

    function setPendingInputImages(images: Array<ConversationImageItem | PendingInputImage>) {
        pendingInputImages.value = Array.isArray(images) ? images : [];
    }

    /**
     * 初始化 store，从本地存储加载配置
     */
    function initialize() {
        // 初始化配置
        configStore.loadSavedConfig();

        // 如果有API密钥，尝试应用配置
        if (configStore.apiKey) {
            applyConfig();
        }

        // 加载系统提示词
        const savedSystemMessage = messagesStore.getSystemMessage();
        if (savedSystemMessage) {
            setSystemMessage(savedSystemMessage);
        } else {
            // 设置默认系统提示词
            setSystemMessage('你是一个有用的AI助手，现在是${datetime}。');
        }

        // 模型信息已通过 configStore.loadSavedConfig() 从 apiConfig 加载，不需要单独获取
        // 如果需要，我们可以从 apiConfig 中获取最新的模型信息
        const apiConfig = StorageService.getApiConfig();
        if (apiConfig && apiConfig.model && apiConfig.model !== configStore.model) {
            configStore.model = apiConfig.model;
            configStore.selectedModelService = apiConfig.service || configStore.selectedModelService;
            applyConfig();
        }
    }

    /**
     * 设置API密钥
     */
    function setApiKey(apiKey: string) {
        configStore.apiKey = apiKey;
        applyConfig();
    }

    /**
     * 设置API基础URL
     */
    function setApiBaseUrl(apiBaseUrl: string) {
        configStore.apiBaseUrl = apiBaseUrl;
        applyConfig();
    }

    /**
     * 设置模型ID
     */
    function setModel(modelId: string) {
        configStore.model = modelId;
        applyConfig();
    }

    // 初始化 store
    initialize();

    return {
        // 从配置 store 暴露
        apiKey: computed(() => configStore.apiKey),
        apiBaseUrl: computed(() => configStore.apiBaseUrl),
        model: computed(() => configStore.model),
        isConfigured: computed(() => {
            // 直接计算配置状态，确保实时响应
            return !!configStore.apiKey && !!configStore.apiBaseUrl && !!configStore.model;
        }),
        selectedModelService: computed(() => configStore.selectedModelService),
        availableModelServices: computed(() => configStore.availableModelServices),
        availableModels: computed(() => configStore.availableModels),
        refreshModelList: configStore.refreshModelList,
        loadModelServiceConfig: configStore.loadModelServiceConfig,
        loadSavedConfig: configStore.loadSavedConfig,

        // 配置更新方法
        setApiKey,
        setApiBaseUrl,
        setModel,

        // 从消息 store 暴露
        messages,
        systemMessage,
        isProcessing,
        setSystemMessage,
        clearChat,
        detachCurrentConversation,
        resumeConversation,
        replaceMessages,
        sendMessage,
        stopCurrentRequest,
        truncateMessagesTo,
        removeAssistantMessageAt,
        retryAssistant,
        pendingInputImages,
        setPendingInputImages,
        isCompressingContext,
        contextCompressionInfo,
        compressConversationContext: mcpCompressConversationContext,

        // 其他
        error,
        applyConfig,
        sessionThreadId,
        initializeAgentSession,
        regenerateSessionThreadId,
        setSessionThreadId,

        // 智能体初始化状态机
        agentInitStatus,
        agentInitError,
        isAgentInitializing,
        startAgentInit,
        resetAgentInit,

        // 沙盒容器预热池
        prewarmSandbox,
        takeSpareSandboxSessionId,
        retainCurrentAgentSession,
        isReusableSession,
        preserveReusableSession,
        takePreservedReusableAgentId,
        resolveWarmSandboxSessionId,
        releaseSandboxContainer,
        refillSpareSandbox,
        discardSpareSandbox
    };
});
