// MCP服务器相关类型定义

export interface ServerTool {
  id: string;
  name: string;
  description?: string;
  argsSchema?: Record<string, any>;
}

export interface ServerFormData {
  name: string;
  description: string;
  type: string;
  url: string;
  timeout: number;
  visibility: 'private' | 'public';
  permissionGroupIds: string[];
}

export interface ServerData extends ServerFormData {
  id?: string;
  uuid?: string;
  headers: Array<{ key: string; value: string }>;
  tools: ServerTool[];
}

export interface ServerStatus {
  status: 'connected' | 'disconnected' | 'connecting' | 'error';
  error?: string;
}

export interface ServerListItem {
  id?: string;
  name: string;
  type?: string;
}

export interface Tool {
  server_id?: string;
  function: {
    name: string;
    description?: string;
    parameters?: Record<string, any>;
  };
}
