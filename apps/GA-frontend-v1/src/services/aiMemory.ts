import { http } from '@/utils/http'

export interface AiMemoryFile {
  name: string
  content: string
  size?: number
  updatedAt?: string
  containerPath?: string
  sandboxPath?: string
}

export interface AiMemoryListData {
  agent_uuid: string
  enabled?: boolean
  files: AiMemoryFile[]
  user_uuid?: string
}

export interface AiMemoryGetData {
  agent_uuid: string
  file_name?: string
  content?: string
  memory?: string
  files?: AiMemoryFile[]
  user_uuid?: string
}

export interface AiMemoryResponse<T = any> {
  code: number
  data: T
  message?: string
}

export async function listAiMemory(agentUuid: string): Promise<AiMemoryResponse<AiMemoryListData>> {
  const res = await http.get<AiMemoryResponse<AiMemoryListData>>('/aiMemory/list', {
    params: { agent_uuid: agentUuid }
  })
  return res.data
}

export async function getAiMemory(agentUuid: string, fileName?: string): Promise<AiMemoryResponse<AiMemoryGetData>> {
  const params: Record<string, string> = { agent_uuid: agentUuid }
  if (fileName) params.file_name = fileName
  const res = await http.get<AiMemoryResponse<AiMemoryGetData>>('/aiMemory/get', { params })
  return res.data
}

export async function updateAiMemory(payload: {
  agent_uuid: string
  file_name: string
  content: string
}): Promise<AiMemoryResponse> {
  const res = await http.post<AiMemoryResponse>('/aiMemory/update', payload)
  return res.data
}

export async function resetAiMemory(agentUuid: string): Promise<AiMemoryResponse> {
  const res = await http.post<AiMemoryResponse>('/aiMemory/reset', { agent_uuid: agentUuid })
  return res.data
}

export async function downloadAiMemory(agentUuid: string): Promise<{ blob: Blob; filename: string }> {
  const res = await http.get<Blob>('/aiMemory/download', {
    params: { agent_uuid: agentUuid },
    timeout: 0
  })
  const disposition = res.headers.get('content-disposition') || ''
  const filenameMatch = disposition.match(/filename\*=UTF-8''([^;]+)|filename="?([^"]+)"?/i)
  const filename = decodeURIComponent(filenameMatch?.[1] || filenameMatch?.[2] || `deepagent-memory-${agentUuid}.zip`)
  return { blob: res.data, filename }
}
