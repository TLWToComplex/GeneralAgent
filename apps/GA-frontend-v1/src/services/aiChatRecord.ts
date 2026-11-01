import { http } from '@/utils/http'
import { replaceChatRecordServerUrls } from '@/utils/serverUrl'

export interface ChatRecordFileGroup {
  agent_id: string
  agent_name: string
  session_thread_id: string
  files: Array<{ name: string; path: string }>
}

/** 获取所有 Agent 对话产生的交付文件。 */
export async function listChatRecordFiles(): Promise<ChatRecordFileGroup[]> {
  const { data } = await http.get<{ code: number; data: ChatRecordFileGroup[]; message: string }>('/aiChatRecord/list_files')
  if (data.code !== 200 || !Array.isArray(data.data)) {
    throw new Error(data.message || '交付文件加载失败')
  }
  return data.data
}

/**
 * 获取聊天历史记录列表摘要
 * GET /aiChatRecord/list_summary
 */
export async function listChatRecordSummary(): Promise<any> {
  const res = await http.get('/aiChatRecord/list_summary')
  return res.data
}

/**
 * 检查指定会话的摘要是否已经生成
 * GET /aiChatRecord/check_summary
 */
export async function checkChatRecordSummary(sessionThreadId: string): Promise<any> {
  const res = await http.get('/aiChatRecord/check_summary', {
    params: { session_thread_id: sessionThreadId }
  })
  return res.data
}

/**
 * 获取指定会话的聊天记录
 * GET /aiChatRecord/list
 * @param params.session_thread_id 会话线程ID
 * @param params.chat_type 对话类型: model-普通对话 / deepagent / agent / travel_planner
 * @param params.agent_id 智能体ID
 */
export async function listChatRecord(params: {
  session_thread_id?: string
  chat_type?: string
  agent_id?: string
}): Promise<any> {
  const queryParams: Record<string, string> = {}
  if (params.session_thread_id) queryParams.session_thread_id = params.session_thread_id
  if (params.chat_type) queryParams.chat_type = params.chat_type
  if (params.agent_id) queryParams.agent_id = params.agent_id

  const res = await http.get('/aiChatRecord/list', { params: queryParams })
  return replaceChatRecordServerUrls(res.data)
}

/**
 * 删除指定会话的聊天记录
 * DELETE /aiChatRecord/delete
 * @param payload.session_thread_id 会话线程ID
 * @param payload.chat_type 对话类型: model-普通对话 / deepagent / agent / travel_planner
 * @param payload.agent_id 智能体ID
 */
export async function deleteChatRecord(payload: {
  session_thread_id: string
  chat_type?: string
  agent_id?: string
}): Promise<any> {
  const body: Record<string, string> = { session_thread_id: payload.session_thread_id }
  if (payload.chat_type) body.chat_type = payload.chat_type
  if (payload.agent_id) body.agent_id = payload.agent_id

  const res = await http.delete('/aiChatRecord/delete', body)
  return res.data
}

/**
 * 编辑指定会话的摘要
 * POST /aiChatRecord/edit_summary
 */
export async function editChatRecordSummary(payload: {
  session_thread_id: string
  summary: string
}): Promise<any> {
  const res = await http.post('/aiChatRecord/edit_summary', payload)
  return res.data
}
