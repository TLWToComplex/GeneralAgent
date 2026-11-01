import { http } from '@/utils/http'

interface AiSystemConfigItem {
  id: number
  config_key: string
  config_value: string
  update_by: string
  update_time: string
}

interface ListAiSystemConfigResponse {
  code: number
  data: AiSystemConfigItem[]
  message: string
}

export interface AiSystemConfigValues {
  top_k: number
  score_threshold: number
}

// 缓存的检索配置
let cachedRetrievalConfig: AiSystemConfigValues | null = null

/**
 * 获取 AI 系统配置列表
 */
export async function listAiSystemConfig(): Promise<AiSystemConfigValues> {
  const res = await http.get<ListAiSystemConfigResponse>('/aiSystemConfig/list')
  const data = res.data

  const result: AiSystemConfigValues = {
    top_k: 3,
    score_threshold: 0.1
  }

  if (data?.data && Array.isArray(data.data)) {
    for (const item of data.data) {
      if (item.config_key === 'top_k') {
        result.top_k = Number(item.config_value) || 3
      } else if (item.config_key === 'score_threshold') {
        result.score_threshold = Number(item.config_value) || 0.1
      }
    }
  }

  return result
}

/**
 * 获取缓存的检索配置，若未缓存则返回默认值
 */
export function getCachedRetrievalConfig(): AiSystemConfigValues {
  return cachedRetrievalConfig ?? { top_k: 3, score_threshold: 0.1 }
}

/**
 * 从服务端获取检索配置并缓存，供 RAG 检索时使用
 */
export async function fetchAndCacheRetrievalConfig(): Promise<AiSystemConfigValues> {
  try {
    const config = await listAiSystemConfig()
    cachedRetrievalConfig = config
    return config
  } catch {
    // 获取失败时保留旧缓存或返回默认值
    return getCachedRetrievalConfig()
  }
}

/**
 * 更新 AI 系统配置
 */
export async function updateAiSystemConfig(payload: Record<string, string>): Promise<void> {
  await http.put('/aiSystemConfig/update', payload)
  // 更新成功后将缓存清除，下次启用增强检索时会重新拉取
  cachedRetrievalConfig = null
}
