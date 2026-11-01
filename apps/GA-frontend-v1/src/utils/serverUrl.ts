import { getApiBaseUrl } from './RuntimeConfig'

/** 替换接口 JSON 中的服务器地址占位符，保留下载路径及查询参数。 */
export function replaceServerUrlPlaceholders<T>(value: T, baseUrl = getApiBaseUrl()): T {
  const base = baseUrl.trim().replace(/\/+$/, '')
  const authority = base.replace(/^https?:\/\//i, '')

  function replace(item: unknown): unknown {
    if (typeof item === 'string') {
      return item
        .replace(/https?:\/\/<server_host>:<server_port>/gi, () => base)
        .replace(/<server_host>:<server_port>/g, () => authority)
    }
    if (Array.isArray(item)) return item.map(replace)
    if (item !== null && typeof item === 'object') {
      return Object.fromEntries(Object.entries(item).map(([key, entry]) => [key, replace(entry)]))
    }
    return item
  }

  // 空 API_BASE_URL 与 HTTP 客户端保持一致，生成同源相对地址。
  return replace(value) as T
}

/** 遍历会话包装结构，仅处理 user/response 记录的 messages。 */
export function replaceChatRecordServerUrls<T>(value: T, baseUrl = getApiBaseUrl()): T {
  function visit(item: unknown): unknown {
    if (Array.isArray(item)) return item.map(visit)
    if (item === null || typeof item !== 'object') return item
    const record = item as Record<string, unknown>
    if ('msg_type' in record) {
      if (record.msg_type !== 'user' && record.msg_type !== 'response') return item
      if (!('messages' in record)) return item
      return { ...record, messages: replaceServerUrlPlaceholders(record.messages, baseUrl) }
    }
    return Object.fromEntries(Object.entries(record).map(([key, entry]) => [key, visit(entry)]))
  }

  return visit(value) as T
}
