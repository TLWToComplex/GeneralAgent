import type { Ref } from 'vue';
import type { MCPClient } from '@/services/mcp/client';

/**
 * 专门处理MCP客户端配置的composable
 * 职责：API凭据管理、客户端配置更新
 */
export function useClientConfiguration(mcpClient: Ref<MCPClient>) {
  
  /**
   * 设置API凭据和配置
   */
  function setCredentials(newApiKey: string, newBaseUrl?: string, newModel?: string) {
    // 构建API URL
    let apiUrl = newBaseUrl?.trim() || '';
    // 去除末尾所有斜杠
    while (apiUrl.endsWith('/')) apiUrl = apiUrl.slice(0, -1);
    
    // 处理URL
    // 如果URL中包含/chat/completions，需要移除这部分
    // 统一 baseUrl 格式供后端代理使用
    if (apiUrl.includes('/chat/completions')) {
      // 找到/chat/completions的位置
      const index = apiUrl.indexOf('/chat/completions');
      // 截取到这个位置，移除/chat/completions及之后的所有内容
      apiUrl = apiUrl.substring(0, index);
    } 
    // 如果URL以/v1/chat结尾，也需要移除/chat部分
    else if (apiUrl.endsWith('/v1/chat')) {
      apiUrl = apiUrl.substring(0, apiUrl.length - 5); // 移除/chat
    }
    // 不包含/v1，则添加
    else if (!apiUrl.endsWith('/v1') && apiUrl) {
      apiUrl = apiUrl + '/v1';
    }
    
    // 创建新的MCP客户端实例，应用新的配置
    mcpClient.value.setCredentials(newApiKey, apiUrl, newModel);
    
    return {
      apiKey: newApiKey,
      apiUrl,
      model: newModel
    };
  }

  return {
    setCredentials,
  };
}