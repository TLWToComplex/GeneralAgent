// 客户端配置接口
export interface MCPClientConfig {
  model: string;
  apiKey: string;
  baseUrl: string;
}

// /aiChat/model 的对话类型：model-普通对话 / kb_chat-知识库检索增强问答
export type ModelChatType = 'model' | 'kb_chat';