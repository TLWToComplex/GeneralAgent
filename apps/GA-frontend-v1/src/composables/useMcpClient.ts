import { http } from '@/utils/http';
import { ref, computed } from 'vue';
import { MCPClient } from '@/services/mcp/client';
import { useMessageManager } from './useMessageManager';
import { useClientConfiguration } from './useClientConfiguration';
import { useChatConfigStore } from '@/stores/chatConfigStore';

/**
 * MCP客户端composable
 * 职责：整合各个专门化的composable，提供统一的接口
 */
export function useMcpClient(
    model: string,
    apiKey: string,
    baseUrl: string
) {
    // 创建 MCP 客户端实例
    const mcpClient = ref<MCPClient>(new MCPClient(model, apiKey, baseUrl));

    // 使用专门化的 composables
    const messageManager = useMessageManager(mcpClient as any);
    const clientConfig = useClientConfiguration(mcpClient as any);

    /**
     * 设置API凭据并更新客户端
     */
    function setCredentials(newApiKey: string, newBaseUrl?: string, newModel?: string) {
        // 规范化 URL：去尾斜杠、处理 /chat/completions 路径、补充 /v1 后缀
        const result = clientConfig.setCredentials(newApiKey, newBaseUrl, newModel);
        
        try {
            let uiKeySeed = 0;
            const ensureUiKey = (msg: any): string => {
                const existing = msg?.uiKey;
                if (typeof existing === 'string' && existing) return existing;
                uiKeySeed += 1;
                const uuid = (globalThis as any)?.crypto?.randomUUID?.();
                if (typeof uuid === 'string' && uuid) return uuid;
                return `${Date.now()}-${uiKeySeed}-${Math.random().toString(16).slice(2)}`;
            };

            // 保存当前消息和系统消息
            const currentMessages = [...messageManager.messages.value];
            const currentSystemMessage = messageManager.systemMessage.value;
            
            // 创建配置store实例，获取兜底值
            const configStore = useChatConfigStore();
            
            // 使用规范化后的 URL 和 model 创建新客户端
            const newModelId = result.model || configStore.model;
            const newBaseUrlValue = result.apiUrl || configStore.apiBaseUrl;
            
            // 直接替换MCPClient实例
            mcpClient.value = new MCPClient(newModelId, newApiKey, newBaseUrlValue);
            
            // 重新设置系统消息
            if (currentSystemMessage) {
                mcpClient.value.setSystemMessage(currentSystemMessage);
            }
            
            // 重建消息历史
            mcpClient.value.clearHistory();
            if (currentSystemMessage) {
                mcpClient.value.setSystemMessage(currentSystemMessage);
            }
            
            currentMessages.forEach(msg => {
                if (msg.role === 'user' || msg.role === 'assistant' || msg.role === 'tool') {
                    mcpClient.value.getMessages().push({ ...msg, uiKey: ensureUiKey(msg) });
                }
            });
            
            // 重新设置事件监听
            messageManager.setupStreamingEventListeners();
            
        } catch (e) {
            console.error('重新初始化MCP客户端失败:', e);
        }

        return result;
    }

    /**
     * 停止当前请求
     */
    async function stopCurrentRequest() {
        const handledByOrchestratorChat = await messageManager.orchestratorChat.stopCurrentRequest();
        if (handledByOrchestratorChat) {
            return;
        }
        if (mcpClient.value && messageManager.isProcessing.value) {
            const client = mcpClient.value;
            const sessionId = messageManager.orchestratorChat.sessionThreadId.value;
            await http.post('/skill/api/chat/interrupt', { session_thread_id: sessionId });
            if (client === mcpClient.value && sessionId === messageManager.orchestratorChat.sessionThreadId.value) client.stopCurrentRequest();
        }
    }

    // 计算属性：统一错误状态
    const error = computed(() => messageManager.error.value);

    return {
        // 消息管理相关
        messages: messageManager.messages,
        systemMessage: messageManager.systemMessage,
        isProcessing: messageManager.isProcessing,
        sessionThreadId: messageManager.orchestratorChat.sessionThreadId,
        initializeAgentSession: messageManager.orchestratorChat.initializeAgentSession,
        startSandboxContainer: messageManager.orchestratorChat.startSandboxContainer,
        releaseSandboxContainer: messageManager.orchestratorChat.releaseSandboxContainer,
        regenerateSessionThreadId: messageManager.orchestratorChat.regenerateSessionThreadId,
        setSessionThreadId: messageManager.orchestratorChat.setSessionThreadId,
        setSystemMessage: messageManager.setSystemMessage,
        clearChat: messageManager.clearChat,
        detachCurrentConversation: messageManager.detachCurrentConversation,
        resumeConversation: messageManager.resumeConversation,
        replaceMessages: messageManager.replaceMessages,
        truncateMessagesTo: messageManager.truncateMessagesTo,
        removeAssistantMessageAt: messageManager.removeAssistantMessageAt,
        retryAssistant: messageManager.retryAssistant,
        sendMessage: messageManager.sendMessage,
        compressConversationContext: messageManager.compressConversationContext,
        isCompressingContext: messageManager.isCompressingContext,
        contextCompressionInfo: messageManager.contextCompressionInfo,

        // 统一状态
        error,

        // 统一方法
        setCredentials,
        stopCurrentRequest,
    };
}
