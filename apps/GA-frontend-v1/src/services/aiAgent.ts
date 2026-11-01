import { ensureAuthenticatedRequestAllowed, http } from '@/utils/http'
import { getApiBaseUrl } from '@/utils/RuntimeConfig'
import StorageService from '@/utils/StorageService'
import { resolveAgentAvatar, agentAvatarToKey } from '@/utils/agentAvatar'

export interface SkillListResponse {
  code: number
  message?: string
  data?: Array<{
    skills?: SkillInfo[]
  }>
}

export interface SkillInfo {
  additionalInfo?: any
  additional_info?: Record<string, any>
  createBy?: string
  createTime?: string
  description?: string
  folderName?: string
  id?: number
  name: string
  uuid?: string
  visibility?: 'public' | 'private' | 'global' | 'project' | string
}

export interface SkillUploadResponse {
  code: number
  message?: string
  data?: any
}

export interface SkillActionResponse {
  code: number
  message?: string
  data?: any
}

const requestSkillApi = async <T>(path: string, init: RequestInit): Promise<T> => {
  const base = getApiBaseUrl().replace(/\/$/, '')
  const url = `${base}${path.startsWith('/') ? path : `/${path}`}`
  ensureAuthenticatedRequestAllowed(url)
  const headers = new Headers(init.headers || {})
  const token = StorageService.getAccessToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(url, { ...init, headers })
  const contentType = res.headers.get('content-type') || ''
  const payload = contentType.includes('application/json') ? await res.json() : await res.text()
  if (!res.ok) {
    const message = typeof payload === 'string' ? payload : payload?.message || `请求失败: ${res.status}`
    throw new Error(message)
  }
  return payload as T
}

// 写库前把头像 URL 归一化为稳定 key，避免本地 dev 的 /src/... 路径被持久化
function withKeyedAvatar(payload: any): any {
  const avatar = payload?.config?.basic?.avatar;
  if (avatar == null || !payload?.config?.basic) return payload;
  return {
    ...payload,
    config: {
      ...payload.config,
      basic: { ...payload.config.basic, avatar: agentAvatarToKey(avatar) }
    }
  };
}

// 读取后把持久化的头像 key 解析回当前构建环境的 URL
function withResolvedAvatar(item: any): any {
  if (!item?.config?.basic || item.config.basic.avatar == null) return item;
  return {
    ...item,
    config: {
      ...item.config,
      basic: { ...item.config.basic, avatar: resolveAgentAvatar(item.config.basic.avatar) }
    }
  };
}

export async function addAiAgent(payload: any): Promise<any> {
  const res = await http.post('/aiAgent/add', withKeyedAvatar(payload))
  return res.data
}

export async function listAiAgents(): Promise<{ code: number; data: any[]; message?: string; total?: number; skip?: number; take?: number }> {
  const res = await http.get('/aiAgent/list')
  const data = res.data as any
  if (data && Array.isArray(data.data)) {
    data.data = data.data.map(withResolvedAvatar)
  }
  return data
}

export async function deleteAiAgent(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiAgent/delete', payload)
  return res.data
}

export async function updateAiAgent(payload: any): Promise<any> {
  const res = await http.post('/aiAgent/update', withKeyedAvatar(payload))
  return res.data
}

export async function listAgentSkills(): Promise<SkillListResponse> {
  return requestSkillApi<SkillListResponse>('/aiSkill/list', { method: 'GET' })
}

type SkillUploadPayload = {
  name: string
  description: string
  visibility: string
  file: File | Blob
  additional_info?: Record<string, string>
}

export async function uploadAgentSkill(payload: SkillUploadPayload): Promise<SkillUploadResponse> {
  const formData = new FormData()
  formData.append('name', payload.name)
  formData.append('description', payload.description)
  formData.append('visibility', payload.visibility)
  if (payload.additional_info && Object.keys(payload.additional_info).length > 0) {
    formData.append('additional_info', JSON.stringify(payload.additional_info))
  }
  formData.append('file', payload.file, 'name' in payload.file && payload.file.name ? payload.file.name : 'skill-file')
  return requestSkillApi<SkillUploadResponse>('/aiSkill/upload', { method: 'POST', body: formData })
}

export interface SkillMdReadResponse {
  code: number
  message?: string
  data?: {
    content?: string
  }
}

export async function readAgentSkillMd(skillId: string): Promise<SkillMdReadResponse> {
  return requestSkillApi<SkillMdReadResponse>(`/aiSkill/read?skill_id=${encodeURIComponent(skillId)}`, {
    method: 'GET'
  })
}

export async function deleteAgentSkill(payload: { uuid: string }): Promise<SkillActionResponse> {
  return requestSkillApi<SkillActionResponse>('/aiSkill/delete', {
    method: 'DELETE',
    body: JSON.stringify(payload)
  })
}

type SkillUpdatePayload = {
  uuid: string
  description: string
  visibility: string
  additional_info?: Record<string, string>
}

export async function updateAgentSkill(payload: SkillUpdatePayload): Promise<SkillActionResponse> {
  const body: Record<string, any> = {
    uuid: payload.uuid,
    description: payload.description,
    visibility: payload.visibility
  }
  if (payload.additional_info && Object.keys(payload.additional_info).length > 0) {
    body.additional_info = JSON.stringify(payload.additional_info)
  }
  return requestSkillApi<SkillActionResponse>('/aiSkill/update', {
    method: 'POST',
    body: JSON.stringify(body)
  })
}

