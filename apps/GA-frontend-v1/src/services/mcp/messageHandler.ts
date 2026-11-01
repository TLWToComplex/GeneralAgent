import type { Message } from '@/types/mcp';
import EventBus, { MCP_EVENTS } from '@/utils/EventBus';
import { SystemPromptVariables } from '@/utils/SystemPromptVariables';
import type { ContextMetrics } from '@/types/mcp';

interface CleanupOptions {
  compressedSummary?: string;
}

/**
 * 消息处理类
 * 处理对话中的各类消息
 */
export class MessageHandler {
  private conversation: Message[] = [];
  private uiKeySeed = 0;

  private createUiKey(): string {
    this.uiKeySeed += 1;
    const uuid = (globalThis as any)?.crypto?.randomUUID?.();
    if (typeof uuid === 'string' && uuid) return uuid;
    return `${Date.now()}-${this.uiKeySeed}-${Math.random().toString(16).slice(2)}`;
  }

  /**
   * 设置系统消息
   */
  setSystemMessage(content: string): void {
    // 删除任何现有的系统消息
    this.conversation = this.conversation.filter(msg => msg.role !== 'system');
    
    // 如果内容不为空，处理变量并添加新的系统消息
    if (content) {
      // 处理系统提示词中的变量
      const processedContent = SystemPromptVariables.processVariables(content);
      
      this.conversation.unshift({
        role: 'system',
        content: processedContent,
        uiKey: this.createUiKey()
      });
    }
  }

  /**
   * 清除对话历史记录
   */
  clearHistory(): void {
    // 保留系统消息（如果存在）
    const systemMessage = this.conversation.find(msg => msg.role === 'system');
    this.conversation = systemMessage ? [systemMessage] : [];
  }

  /**
   * 触发消息创建事件
   * @param message 新创建的消息
   */
  private triggerMessageCreatedEvent(message: Message): void {
    EventBus.emit(MCP_EVENTS.MESSAGE_CREATED, { message });
  }

  /**
   * 触发消息更新事件
   * @param message 更新的消息
   */
  private triggerMessageUpdatedEvent(message: Message): void {
    EventBus.emit(MCP_EVENTS.MESSAGE_UPDATED, { message });
  }

  private ensureBlocks(message: Message) {
    if (!message.orchestratorBlocks) {
      message.orchestratorBlocks = [];
    }
    return message.orchestratorBlocks;
  }

  private appendContentBlock(message: Message, content: string): void {
    if (!content) return;
    const blocks = this.ensureBlocks(message);
    const lastBlock = blocks[blocks.length - 1];
    if (lastBlock && lastBlock.type === 'content') {
      lastBlock.content += content;
      return;
    }
    blocks.push({ type: 'content', content });
  }

  private appendReasoningBlock(message: Message, content: string): void {
    if (!content) return;
    const blocks = this.ensureBlocks(message);
    const lastBlock = blocks[blocks.length - 1];
    if (lastBlock && lastBlock.type === 'reasoning') {
      lastBlock.content += content;
      return;
    }
    blocks.push({ type: 'reasoning', content });
  }

  /**
   * 添加用户消息到对话历史（不触发事件）
   * @param content 消息内容
   * @param files 可选的文件列表
   * @param displayContent 可选的UI显示内容
   */
  addUserMessageSilent(content: string, files?: any[], displayContent?: string, turnId?: string): void {
    const userMessage: Message = {
      role: 'user',
      content,
      turn_id: turnId,
      display_content: displayContent,
      uiKey: this.createUiKey(),
      files
    };
    this.conversation.push(userMessage);
  }

  /**
   * 添加流式智能体消息
   * @returns 新创建的流式消息对象
   */
  createStreamingAssistantMessage(model?: string, kbCitations?: any[], turnId?: string): Message {
    const streamingMessage: Message = {
      role: 'assistant',
      content: '',
      turn_id: turnId,
      reasoning_content: '',
      orchestratorBlocks: [],
      isStreaming: true,
      model,
      kb_citations: kbCitations,
      uiKey: this.createUiKey()
    };
    
    this.conversation.push(streamingMessage);
    this.triggerMessageCreatedEvent(streamingMessage);
    return streamingMessage;
  }

  /**
   * 更新流式消息内容
   * @param content 新增内容
   * @param isReasoning 是否为思考内容
   */
  appendToStreamingMessage(content: string, isReasoning: boolean = false): void {
    // 查找最后一条智能体消息
    const lastAssistantMessage = [...this.conversation].reverse().find(
      msg => msg.role === 'assistant' && msg.isStreaming
    );
    
    if (lastAssistantMessage) {
      if (isReasoning) {
        // 追加到思考内容
        if (!lastAssistantMessage.reasoning_content) {
          lastAssistantMessage.reasoning_content = '';
        }
        lastAssistantMessage.reasoning_content += content;
        this.appendReasoningBlock(lastAssistantMessage, content);
      } else {
        // 追加到普通内容
        lastAssistantMessage.content += content;
        this.appendContentBlock(lastAssistantMessage, content);
      }
      
      // 触发消息更新事件
      this.triggerMessageUpdatedEvent(lastAssistantMessage);
    }
  }

  /**
   * 更新当前流式消息的上下文度量
   */
  updateCurrentStreamingContextMetrics(contextMetrics: ContextMetrics): void {
    const lastStreamingMessage = [...this.conversation].reverse().find(
      msg => msg.role === 'assistant' && msg.isStreaming
    );

    if (lastStreamingMessage) {
      lastStreamingMessage.contextMetrics = contextMetrics;
      this.triggerMessageUpdatedEvent(lastStreamingMessage);
    }
  }

  /**
   * 清除流式消息的contextMetrics（取消请求时使用，避免显示"等待usage"）
   */
  clearStreamingContextMetrics(): void {
    const lastStreamingMessage = [...this.conversation].reverse().find(
      msg => msg.role === 'assistant' && msg.isStreaming
    );

    if (lastStreamingMessage) {
      lastStreamingMessage.contextMetrics = undefined;
      this.triggerMessageUpdatedEvent(lastStreamingMessage);
    }
  }

  /**
   * 完成流式消息
   */
  finishStreamingMessage(): Message | null {
    // 查找最后一条流式智能体消息
    const lastStreamingMessage = [...this.conversation].reverse().find(
      msg => msg.role === 'assistant' && msg.isStreaming
    );
    
    if (lastStreamingMessage) {
      // 标记为非流式状态
      lastStreamingMessage.isStreaming = false;
      
      // 触发消息更新事件
      this.triggerMessageUpdatedEvent(lastStreamingMessage);
      
      return lastStreamingMessage;
    }
    
    return null;
  }

  /**
   * 添加智能体消息到对话历史
   * @param content 消息内容
   * @returns 智能体消息
   */
  addAssistantMessage(content: string, model?: string): Message {
    // 如果是错误消息，先完成任何现有的流式消息
    if (content.includes('请求过程中出现错误') || content.includes('Connection error')) {
      const lastStreamingMessage = [...this.conversation].reverse().find(
        msg => msg.role === 'assistant' && msg.isStreaming
      );
      
      if (lastStreamingMessage) {
        // 标记为非流式状态，不添加内容
        lastStreamingMessage.isStreaming = false;
        // 触发消息更新事件
        this.triggerMessageUpdatedEvent(lastStreamingMessage);
      }
    }
    
    const assistantMessage: Message = {
      role: 'assistant',
      content,
      model,
      uiKey: this.createUiKey()
    };
    
    this.conversation.push(assistantMessage);
    this.triggerMessageCreatedEvent(assistantMessage);
    return assistantMessage;
  }

  /**
   * 截断消息列表到指定索引（保留从0到指定索引的消息）
   * @param endIndex 结束索引（包含）
   */
  truncateMessagesTo(endIndex: number): void {
    if (endIndex >= 0 && endIndex < this.conversation.length) {
      this.conversation = this.conversation.slice(0, endIndex + 1);
    }
  }

  /**
   * 获取对话历史
   * @returns 消息列表
   */
  getMessages(): Message[] {
    return this.conversation;
  }

  /**
   * 直接替换当前会话消息，用于历史会话恢复后继续追问。
   */
  replaceConversation(messages: Message[]): void {
    const nextMessages = Array.isArray(messages) ? messages : [];
    this.conversation = nextMessages.map((message) => ({
      ...message,
      uiKey: message?.uiKey || this.createUiKey(),
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

  /**
   * 清理消息格式，确保符合模型API的格式要求
   * @param messages 原始消息
   * @returns 清理后的消息
   */
  cleanupMessages(messages: any[], options?: CleanupOptions): any[] {
    const contextMessages = messages.filter(msg => !msg?.compressedIntoSummary && msg?.role !== 'tool');

    const cleanedMessages = contextMessages.map(msg => {
      // 处理智能体消息
      if (msg.role === 'assistant') {
        return {
          role: msg.role,
          content: msg.content || ""
        };
      }
      
      // 处理用户消息，支持图片多模态输入
      else if (msg.role === 'user') {
        const userMsg: any = {
          role: msg.role,
          content: msg.content || ""
        };

        if (Array.isArray(msg.files) && msg.files.length > 0) {
          const imageParts: any[] = [];
          if (msg.content) {
            imageParts.push({ type: 'text', text: msg.content });
          }

          for (const file of msg.files) {
            const isImage = file?.isFileImage || (typeof file?.name === 'string' && /\.(png|jpe?g|gif|webp|bmp|svg)$/i.test(file.name));
            const dataUrl = file?.dataUrl || file?.imageDataUrl || file?.imagePreviewUrl;
            if (isImage && typeof dataUrl === 'string' && dataUrl.startsWith('data:image/')) {
              imageParts.push({
                type: 'image_url',
                image_url: { url: dataUrl }
              });
            }
          }

          if (imageParts.length > 0) {
            userMsg.content = imageParts;
          }
        }

        return userMsg;
      }
      // 其他消息类型原样返回
      return {
        role: msg.role,
        content: msg.content
      };
    });

    const compressedSummary = options?.compressedSummary?.trim();
    if (compressedSummary) {
      const summaryMessage = {
        role: 'assistant',
        content: `[历史上下文摘要]\n${compressedSummary}`
      };
      const systemIndex = cleanedMessages.findIndex(message => message.role === 'system');
      if (systemIndex >= 0) {
        cleanedMessages.splice(systemIndex + 1, 0, summaryMessage);
      } else {
        cleanedMessages.unshift(summaryMessage);
      }
    }

    // 验证和修复消息序列，确保符合模型API规范
    return this.validateAndFixMessageSequence(cleanedMessages);
  }

  /**
   * 验证和修复消息序列，确保符合模型API规范
   * @param messages 清理后的消息
   * @returns 修复后的消息序列
   */
  private validateAndFixMessageSequence(messages: any[]): any[] {
    const validMessages: any[] = [];
    
    for (let i = 0; i < messages.length; i++) {
      const currentMsg = messages[i];
      
      // 处理assistant消息
      if (currentMsg.role === 'assistant') {
        // 检查原始消息是否有reasoning_content（用于处理中断请求的情况）
        const originalMessage = this.conversation
          .slice()
          .reverse()
          .find(msg => 
            msg.role === 'assistant' && 
            msg.reasoning_content && 
            (!msg.content || msg.content === currentMsg.content)
          );
        
        // 如果assistant消息没有内容，但原始消息有reasoning_content，说明被中断了
        if (!currentMsg.content) {
          if (originalMessage && originalMessage.reasoning_content) {
             currentMsg.content = '抱歉，我的回复被中断了。你的问题我已记录，如果需要我会重新为您处理。';
          } else {
            continue;
          }
        }
        
        validMessages.push(currentMsg);
      }
      // 其他消息类型直接添加
      else {
        validMessages.push(currentMsg);
      }
    }
    
    return validMessages;
  }
}
