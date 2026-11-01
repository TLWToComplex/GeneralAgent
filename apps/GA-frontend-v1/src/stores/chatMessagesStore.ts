import {defineStore} from 'pinia';
import {ref} from 'vue';
import NotificationService from '@/utils/NotificationService';
import {ConfigManager} from '@/utils/ConfigManager';
import StorageService from '@/utils/StorageService';

/**
 * 聊天消息状态管理
 * 优化：简化职责，专注于消息状态管理和本地存储
 */
export const useChatMessagesStore = defineStore('chatMessages', () => {
    // 获取配置管理器实例
    const configManager = ConfigManager.getInstance();

    // 消息处理状态
    const isProcessing = ref<boolean>(false);
    const error = ref<string | null>(null);

    /**
     * 保存系统提示词到本地存储
     */
    function saveSystemMessage(message: string): void {
        configManager.saveSystemMessage(message);
    }

    /**
     * 发送消息
     * 优化：简化参数，减少耦合
     * @param content 消息内容
     * @param mcpSendMessage MCP客户端发送消息方法
     * @param isConfigured 是否已配置API
     */
    async function sendMessage(
        content: string,
        mcpSendMessage: (
            content: string,
            files?: any[],
            kbConfig?: { enabled: boolean, kbNames: string[] },
            options?: { reuseUserMessageUiKey?: string, turnId?: string }
        ) => Promise<boolean>,
        isConfigured: boolean,
        files?: any[],
        kbConfig?: { enabled: boolean, kbNames: string[] },
        options?: { reuseUserMessageUiKey?: string, turnId?: string }
    ): Promise<boolean> {
        if (!content.trim() && (!files || files.length === 0)) return false;

        // 检查是否配置了API或处于编排式助手模式
        try {
            const activeAgent = StorageService.getActiveAgent();
            const agentType = (activeAgent?.basic?.type) || (activeAgent?.config?.basic?.type) || 'assistant';
            const orchestratorUrl = (activeAgent?.orchestrator?.serviceUrl) || (activeAgent?.config?.orchestrator?.serviceUrl);
            const orchestratorReady = agentType === 'orchestrator' && typeof orchestratorUrl === 'string' && !!orchestratorUrl.trim();
            if (!isConfigured && !orchestratorReady) {
                NotificationService.error('请先配置API设置');
                return false;
            }
        } catch (_) {
            if (!isConfigured) {
                NotificationService.error('请先配置API设置');
                return false;
            }
        }

        try {
            // 知识库检索与上下文拼装已在消息管理流程中处理，这里直接发送原始内容
            return await mcpSendMessage(content, files, kbConfig, options);
        } catch (error) {
            console.error('Failed to send message:', error);
            NotificationService.error(`发送消息失败: ${error}`);
            return false;
        }
    }

    /**
     * 设置系统提示词并缓存
     * 优化：明确参数类型
     */
    function setSystemMessage(message: string, mcpSetSystemMessage: (message: string) => void, persist: boolean = true): void {
        mcpSetSystemMessage(message);
        if (persist) {
            saveSystemMessage(message);
        }
    }

    /**
     * 获取保存的系统消息
     */
    function getSystemMessage(): string | null {
        return configManager.getSystemMessage();
    }

    /**
     * 设置处理状态
     */
    function setIsProcessing(value: boolean): void {
        isProcessing.value = value;
    }

    /**
     * 设置错误状态
     */
    function setError(value: string | null): void {
        error.value = value;
    }

    return {
        // 状态
        isProcessing,
        error,

        // 方法
        sendMessage,
        setSystemMessage,
        saveSystemMessage,
        getSystemMessage,
        setIsProcessing,
        setError
    };
});
