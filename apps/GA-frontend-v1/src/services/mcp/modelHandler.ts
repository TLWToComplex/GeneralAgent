import type { MCPClientConfig, ModelChatType } from './types';
import type { Message } from '@/types/mcp';
import type { MessageHandler } from './messageHandler';
import EventBus, { MCP_EVENTS } from '@/utils/EventBus';
import StorageService from '@/utils/StorageService';
import { getApiBaseUrl } from '@/utils/RuntimeConfig';
import { createPendingContextMetrics, estimateContextMetrics, withExactPromptUsage } from '@/utils/contextMetrics';

// 扩展的Delta类型，包含reasoning_content和reasoning字段
interface ExtendedDelta {
  content?: string | null;
  reasoning_content?: string | null;
  reasoning?: string | null;
  role?: string | null;
  // 其他可能的字段
  [key: string]: any;
}

interface ChunkUsageLike {
  prompt_tokens?: number;
  prompt_tokens_details?: {
    text_tokens?: number;
    image_tokens?: number;
  };
}

/**
 * 模型API处理类
 * 处理与模型API的交互（通过后端代理转发，纯文本流式响应，不含工具调用）
 */
export class ModelHandler {
  private abortController: AbortController | null = null;
  
  constructor(private config: MCPClientConfig) {}
  
  /**
   * 获取当前使用的模型ID
   */
  private getCurrentModel(): string {
    return this.config.model;
  }
  
  /**
   * 检查API客户端是否已配置
   */
  isInitialized(): boolean {
    return !!this.config.apiKey;
  }

  /**
   * 获取当前用户的UUID
   */
  private getUserId(): string {
    try {
      const raw = localStorage.getItem('user-profile');
      if (raw) {
        const profile = JSON.parse(raw);
        return profile?.uuid || '';
      }
    } catch {
      // ignore
    }
    return '';
  }

  async summarizeContextForCompression(source: string): Promise<string> {
    if (!this.config.apiKey) {
      throw new Error('API密钥未配置。');
    }

    const apiBaseUrl = getApiBaseUrl();
    const accessToken = StorageService.getAccessToken();
    const headers: Record<string, string> = { 'Content-Type': 'application/json' };
    if (accessToken) {
      headers['Authorization'] = `Bearer ${accessToken}`;
    }

    const payload = {
      model: this.getCurrentModel(),
      user_id: this.getUserId(),
      baseUrl: this.config.baseUrl || '',
      apiKey: this.config.apiKey,
      messages: [
        {
          role: 'system',
          content: '你是一个负责压缩对话上下文的助手。请将提供的历史内容压缩为中文摘要，保留用户目标、关键事实、已经完成的操作、未完成事项、重要工具结果与文档结论。输出纯文本，不要使用Markdown标题，控制在450字以内。'
        },
        {
          role: 'user',
          content: source
        }
      ],
      stream: false,
      temperature: 0.2
    };

    const response = await fetch(`${apiBaseUrl}/aiChat/model`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`压缩请求失败: ${response.status}`);
    }

    const data = await response.json();
    return data.choices?.[0]?.message?.content?.trim() || '';
  }

  /**
   * 停止当前的API请求
   */
  detachCurrentRequest(): void {
    this.abortController?.abort();
    this.abortController = null;
  }

  stopCurrentRequest(): void {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
      // 发出停止事件
      EventBus.emit(MCP_EVENTS.CONVERSATION_STOPPED);
    }
  }

  /**
   * 解析SSE流式响应，返回异步迭代器
   * @private
   */
  private async *parseSSEStream(response: Response): AsyncGenerator<any> {
    const reader = response.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data: ')) continue;
          const data = trimmed.slice(6);
          if (data === '[DONE]') return;
          try {
            yield JSON.parse(data);
          } catch {
            // 跳过无法解析的行
          }
        }
      }
    } finally {
      reader.releaseLock();
    }
  }
  
  /**
   * 执行初始查询（纯文本流式，不含工具调用）
   * @param messages 消息历史
   * @param messageHandler 消息处理器
   * @param kbCitations 知识库引用
   * @param chatType 对话类型：model-普通对话 / kb_chat-知识库检索增强问答
   */
  async executeQuery(
    messages: Message[], 
    messageHandler: MessageHandler,
    kbCitations?: any[],
    compressedSummary?: string,
    sessionThreadId?: string,
    turnId?: string,
    chatType?: ModelChatType
  ): Promise<void> {
    if (!this.config.apiKey) {
      throw new Error('API密钥未配置。');
    }
    
    try {
      // 准备消息 - 确保消息格式正确
      const formattedMessages = messageHandler.cleanupMessages(messages, {
        compressedSummary
      });
      
      // 创建流式消息
      messageHandler.createStreamingAssistantMessage(this.getCurrentModel(), kbCitations, turnId);

      // 进行API调用并处理响应
      await this.processApiCall(
        formattedMessages,
        messageHandler,
        sessionThreadId,
        turnId,
        chatType
      );
      
      // 完成流式消息
      messageHandler.finishStreamingMessage();
    } catch (e) {
      // 取消请求时，完成流式消息并清除pending状态的metrics
      if (e instanceof Error && (e.message === 'REQUEST_CANCELLED' || e.name === 'AbortError')) {
        messageHandler.clearStreamingContextMetrics();
        messageHandler.finishStreamingMessage();
      }
      throw e;
    }
  }
  
  /**
   * 处理API调用并解析响应（纯文本流式，不含工具调用）
   * @private
   * @param messages 处理后的消息
   * @param messageHandler 消息处理器
   */
  private async processApiCall(
    messages: any[],
    messageHandler: MessageHandler,
    sessionThreadId?: string,
    turnId?: string,
    chatType?: ModelChatType
  ): Promise<void> {
    try {
      // 获取当前使用的模型ID
      const currentModel = this.getCurrentModel();
    
    // 创建请求配置对象
    const requestConfig: Record<string, any> = {
      model: currentModel,
      messages: messages,
      stream: true
    };

    const estimatedContextMetrics = createPendingContextMetrics({
      model: currentModel,
      messageCount: Array.isArray(messages) ? messages.length : 0,
      toolsCount: 0
    });
    let exactUsage: ChunkUsageLike | null = null;
    messageHandler.updateCurrentStreamingContextMetrics(estimatedContextMetrics);
    
    // 检查是否有活跃的智能体配置，如果有则应用其模型参数
    const activeAgent = StorageService.getActiveAgent();
    if (activeAgent) {
      try {
        const agentConfig = activeAgent;
        if (agentConfig.model) {
          if (agentConfig.model.temperature !== undefined && agentConfig.model.temperature !== null) {
            requestConfig.temperature = agentConfig.model.temperature;
          }
          if (agentConfig.model.top_p !== undefined && agentConfig.model.top_p !== null) {
            requestConfig.top_p = agentConfig.model.top_p;
          }
          if (agentConfig.model.presence_penalty !== undefined && agentConfig.model.presence_penalty !== null) {
            requestConfig.presence_penalty = agentConfig.model.presence_penalty;
          }
          if (agentConfig.model.frequency_penalty !== undefined && agentConfig.model.frequency_penalty !== null) {
            requestConfig.frequency_penalty = agentConfig.model.frequency_penalty;
          }
        }
      } catch (e) {
        console.warn('解析活跃智能体配置失败:', e);
      }
    }
    
    // 创建AbortController用于取消请求
    this.abortController = new AbortController();

    // 构建后端接口 payload
    const apiBaseUrl = getApiBaseUrl();
    const accessToken = StorageService.getAccessToken();
    const fetchHeaders: Record<string, string> = { 'Content-Type': 'application/json' };
    if (accessToken) {
      fetchHeaders['Authorization'] = `Bearer ${accessToken}`;
    }

    const payload: Record<string, any> = {
      model: requestConfig.model,
      user_id: this.getUserId(),
      baseUrl: this.config.baseUrl || '',
      apiKey: this.config.apiKey,
      messages: requestConfig.messages,
      stream: true,
      turn_id: turnId,
      chat_type: chatType === 'kb_chat' ? 'kb_chat' : 'model'
    };
    const normalizedSessionThreadId = (sessionThreadId || '').trim();
    if (normalizedSessionThreadId) {
      payload.session_thread_id = normalizedSessionThreadId;
    }
    if (requestConfig.temperature !== undefined) payload.temperature = requestConfig.temperature;
    if (requestConfig.top_p !== undefined) payload.top_p = requestConfig.top_p;
    if (requestConfig.presence_penalty !== undefined) payload.presence_penalty = requestConfig.presence_penalty;
    if (requestConfig.frequency_penalty !== undefined) payload.frequency_penalty = requestConfig.frequency_penalty;

    // 调用后端代理接口
    const response = await fetch(`${apiBaseUrl}/aiChat/model`, {
      method: 'POST',
      headers: fetchHeaders,
      body: JSON.stringify(payload),
      signal: this.abortController.signal
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => '');
      throw new Error(`API请求失败: ${response.status} ${response.statusText} ${errorText}`);
    }
    
    // 处理流式SSE响应
    for await (const chunk of this.parseSSEStream(response)) {
      if (typeof chunk.usage?.prompt_tokens === 'number' && chunk.usage.prompt_tokens > 0) {
        const promptTokenDetails = (chunk.usage.prompt_tokens_details || {}) as {
          text_tokens?: number;
          image_tokens?: number;
        };
        exactUsage = {
          prompt_tokens: chunk.usage.prompt_tokens,
          prompt_tokens_details: {
            text_tokens: promptTokenDetails.text_tokens,
            image_tokens: promptTokenDetails.image_tokens
          }
        };
        messageHandler.updateCurrentStreamingContextMetrics(
          withExactPromptUsage(estimatedContextMetrics, exactUsage)
        );
      }

      // 使用扩展Delta类型处理响应
      const delta = chunk.choices[0]?.delta as ExtendedDelta || {};
      
      // 处理普通内容
      if (delta.content) {
        messageHandler.appendToStreamingMessage(delta.content, false);
      }
      
      // 处理reasoning_content或reasoning（思考过程内容）
      const reasoningContent = delta.reasoning_content || delta.reasoning;
      if (reasoningContent) {
        messageHandler.appendToStreamingMessage(reasoningContent, true);
      }
    }

    if (!exactUsage) {
      messageHandler.updateCurrentStreamingContextMetrics(
        estimateContextMetrics({
          model: currentModel,
          messages,
          tools: []
        })
      );
    }
    
  } catch (error: any) {
    // 处理取消请求的情况
    if (error.name === 'AbortError' || error.message?.includes('aborted')) {
      // 清理AbortController
      this.abortController = null;
      // 抛出特定的取消错误
      throw new Error('REQUEST_CANCELLED');
    }
    // 其他错误继续抛出
    throw error;
  } finally {
    // 清理AbortController
    this.abortController = null;
  }
}
}
