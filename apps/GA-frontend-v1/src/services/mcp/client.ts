import type { MCPClientConfig, ModelChatType } from './types';
import type { Message } from '@/types/mcp';
import {MessageHandler} from './messageHandler';
import {ModelHandler} from './modelHandler';
import EventBus, {MCP_EVENTS} from '@/utils/EventBus';

/**
 * MCP客户端类
 * 整合所有功能模块，提供完整的MCP客户端功能
 */
export class MCPClient {
    private readonly messageHandler: MessageHandler;
    private modelHandler: ModelHandler;
    private transientCompressedSummary = '';

    // 添加公共属性以便外部访问
    public readonly model: string;
    public readonly apiKey: string;
    public readonly baseUrl: string;

    constructor(
        model: string,
        apiKey: string,
        baseUrl: string
    ) {
        const config: MCPClientConfig = {model, apiKey, baseUrl};

        // 保存配置到公共属性
        this.model = model;
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;

        // 初始化各个组件
        this.messageHandler = new MessageHandler();
        this.modelHandler = new ModelHandler(config);
    }

    /**
     * 设置系统消息
     */
    setSystemMessage(content: string): void {
        this.messageHandler.setSystemMessage(content);
    }

    /**
     * 清除对话历史记录
     */
    clearHistory(): void {
        this.messageHandler.clearHistory();
    }

    /**
     * 处理用户查询（纯文本流式，不含工具调用）
     * @param query 用户查询
     * @param files 可选的文件列表
     * @param displayContent 可选的UI显示内容（如果不提供，则使用query）
     * @param kbCitations 知识库引用
     * @param options.chatType 对话类型：model-普通对话 / kb_chat-知识库检索增强问答
     * @returns 更新后的消息列表和可能的错误信息
     */
    async processQuery(
        query: string,
        files?: any[],
        displayContent?: string,
        kbCitations?: any[],
        options?: { compressedSummary?: string; sessionThreadId?: string; turnId?: string; chatType?: ModelChatType }
    ): Promise<{ messages: Message[], error?: string }> {
        if (!this.modelHandler.isInitialized()) {
            return {
                messages: this.messageHandler.getMessages(),
                error: 'API密钥未配置。'
            };
        }

        try {
            this.transientCompressedSummary = options?.compressedSummary?.trim() || '';
            // 不要重复添加用户消息，因为UI已经添加了
            // 使用静默方法添加用户消息到对话历史，不触发事件
            this.messageHandler.addUserMessageSilent(query, files, displayContent, options?.turnId);

            // 获取现有消息
            const currentMessages = [...this.messageHandler.getMessages()];

            // 执行查询 - 纯文本流式响应，不再处理工具调用
            await this.modelHandler.executeQuery(
                currentMessages,
                this.messageHandler,
                kbCitations,
                this.transientCompressedSummary,
                options?.sessionThreadId,
                options?.turnId,
                options?.chatType
            );

            // 对话完成
            this.triggerConversationComplete();

            return {
                messages: this.messageHandler.getMessages()
            };
        } catch (e) {
            // 用户主动取消请求，静默返回，不显示错误
            if (e instanceof Error && (e.message === 'REQUEST_CANCELLED' || e.name === 'AbortError' || e.message.includes('aborted'))) {
                this.triggerConversationComplete();
                return {
                    messages: this.messageHandler.getMessages()
                };
            }

            let errorMsg = `请求过程中出现错误: ${e}`;

            // 检查是否是网络错误
            if (e instanceof TypeError && typeof e.message === 'string' && e.message.includes('network error')) {
                errorMsg = `网络连接错误: ${e.message}`;
            } else if (e instanceof TypeError && typeof e.message === 'string' && (e.message.includes('fetch') || e.message.includes('Failed to fetch'))) {
                errorMsg = `网络连接错误: 无法连接到服务器`;
            }

            this.messageHandler.addAssistantMessage(errorMsg, this.model);
            // 出错时触发对话完成事件
            this.triggerConversationComplete();
            return {
                messages: this.messageHandler.getMessages(),
                error: errorMsg
            };
        } finally {
            this.transientCompressedSummary = '';
        }
    }

    /**
     * 截断消息列表到指定索引
     * @param endIndex 结束索引（包含）
     */
    truncateMessagesTo(endIndex: number): void {
        this.messageHandler.truncateMessagesTo(endIndex);
    }

    /**
     * 获取消息列表
     * @returns 消息列表
     */
    getMessages(): Message[] {
        return this.messageHandler.getMessages();
    }

    replaceMessages(messages: Message[]): void {
        this.messageHandler.replaceConversation(messages);
    }

    async summarizeContextForCompression(source: string): Promise<string> {
        return this.modelHandler.summarizeContextForCompression(source);
    }

    /**
     * 停止当前的API请求
     */
    detachCurrentRequest(): void {
        this.modelHandler.detachCurrentRequest();
    }

    stopCurrentRequest(): void {
        this.modelHandler.stopCurrentRequest();
    }

    /**
     * 触发对话完成事件
     * 通知UI层对话已完全完成，包括所有工具响应和后续对话
     */
    private triggerConversationComplete(): void {
        // 使用 EventBus 触发事件，而不是 DOM 事件
        EventBus.emit(MCP_EVENTS.CONVERSATION_COMPLETE);
    }

    /**
     * 设置 API 凭据
     *
     * @param apiKey - API 密钥
     * @param baseUrl - API 基础 URL
     * @param model - 模型名称
     */
    setCredentials(apiKey: string, baseUrl: string, model?: string): { apiKey: string, apiUrl: string, model: string } {
        // 创建更新后的配置
        const newModel = model || this.model;
        const config: MCPClientConfig = {
            model: newModel,
            apiKey: apiKey,
            baseUrl: baseUrl
        };

        // 创建新的模型处理器实例
        this.modelHandler = new ModelHandler(config);

        // 不再单独保存模型到localStorage，模型会通过统一的配置管理保存
        // 模型信息应该在调用setCredentials的地方，通过StorageService.setApiConfig统一保存

        return {
            apiKey: apiKey,
            apiUrl: baseUrl,
            model: newModel
        };
    }
}
