// src/types/mcp.ts

export interface ToolCall {
  id: string;
  type?: string;
  function: {
    name: string;
    arguments: string;
  };
  server_id?: string;
  server_url?: string;
  // 工具调用状态相关字段
  status?: 'pending' | 'executing' | 'completed' | 'failed';
  startTime?: number;
  endTime?: number;
  duration?: number;
  error?: string;
}

export type OrchestratorBlock =
  | { type: 'content'; content: string }
  | { type: 'reasoning'; content: string }
  | { type: 'tools'; toolCallIds: string[] };

export interface TodoItem {
  content: string;
  status: 'pending' | 'in_progress' | 'completed';
  id?: string;
  priority?: string;
}

export interface InterruptMessage {
  content: string;
  isInterrupt?: string;
  okText?: string;
  cancelText?: string;
}

export interface Interrupt {
  type: 'interrupt';
  message: string | InterruptMessage;
  run_id?: string;
  thread_id?: string;
}

export interface ContextMetrics {
  mode: 'pending' | 'estimated' | 'exact';
  model: string;
  contextWindow?: number;
  promptTokens: number;
  messagesTokens: number;
  textTokens: number;
  imageTokens: number;
  toolsTokens: number;
  reservedOutputTokens: number;
  safetyMarginTokens: number;
  usableInputTokens: number;
  utilization: number;
  messageCount: number;
  toolsCount: number;
}

export interface ContextCompressionInfo {
  beforePromptTokens: number;
  afterPromptTokens: number;
  reducedTokens: number;
  compressedMessageCount: number;
  keptMessageCount: number;
  hasCompressedFiles: boolean;
  updatedAt: number;
}

export interface PendingInputImage {
  key: string;
  url: string;
  alt?: string;
  name?: string;
  source: 'input';
  messageIndex: number;
  messageId: string;
  role: 'user';
  isCapturePending?: boolean;
  pendingMessageKey?: string;
}
  
export interface Message {
    id?: string;
    role: 'system' | 'user' | 'assistant' | 'tool';
    content: string;
    turn_id?: string;
    display_content?: string;
    uiKey?: string;
    reasoning_content?: string;
    tool_calls?: ToolCall[];
    orchestratorBlocks?: OrchestratorBlock[];
    /** 历史消息所属智能体配置，未激活智能体时用于还原头像与名称 */
    agentConfig?: any;
    tool_call_id?: string;
    isStreaming?: boolean;
    taskStartedAt?: number;
    taskFinishedAt?: number;
    model?: string;
    todos?: TodoItem[];
    interrupt?: Interrupt;
    stage?: string;
    contextMetrics?: ContextMetrics;
    /** 仅用于UI展示的知识库引用数据，不参与模型请求 */
    kb_citations?: Array<{
      page_content: string;
      metadata?: Record<string, any>;
      type?: string;
      id?: string | null;
      score?: number;
      /** 原始文件路径，可用于 Canvas 预览 */
      file_path?: string;
    }>;
    /** 消息关联的文件信息 */
    files?: Array<{
      name: string;
      size: number;
      type?: string;
      content?: any; // 解析后的内容或原始内容
      uploadStatus?: 'uploading' | 'parsing' | 'success' | 'error';
      chunkCount?: number;
      tokenCount?: number;
      parseResult?: any;
      isFileImage?: boolean;
      imagePreviewUrl?: string;
      imageWidth?: number;
      imageHeight?: number;
      imageTokenEstimate?: number;
      isCapturePending?: boolean;
      /** 历史消息中文件的下载链接 */
      path?: string;
      url?: string;
    }>;
    liked?: boolean;
    disliked?: boolean;
    compressedIntoSummary?: boolean;
  }
