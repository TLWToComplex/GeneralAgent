/**
 * 类型定义索引文件
 * 统一导出所有类型
 */

// 重新导出MCP相关类型
export * from './mcp';

// 聊天消息类型
export interface ChatMessage {
  id: string;
  role: 'system' | 'user' | 'assistant' | 'tool';
  content: string;
  timestamp: number;
  reasoning_content?: string;
  tool_calls?: any[];
  tool_call_id?: string;
  isStreaming?: boolean;
}

// 主题类型
export type ThemeMode = 'light' | 'dark' | 'system'; 