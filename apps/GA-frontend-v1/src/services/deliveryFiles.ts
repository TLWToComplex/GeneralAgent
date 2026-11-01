import StorageService from '@/utils/StorageService'
import { getApiBaseUrl } from '@/utils/RuntimeConfig'

/** 文件接口必须读取原始 Blob，不能按 JSON / 文本自动解析。 */
export async function fetchDeliveryFile(path: string, signal?: AbortSignal): Promise<Blob> {
  const base = new URL(getApiBaseUrl() || '/', window.location.origin)
  const url = new URL(path, `${base.href.replace(/\/$/, '')}/`)
  if (!['http:', 'https:'].includes(url.protocol)) throw new Error('文件地址无效')
  // 后端可能返回内网 localhost 下载地址；使用部署时配置的同一文件服务。
  if (['localhost', '127.0.0.1', '::1', '[::1]'].includes(url.hostname) && url.pathname === '/aiFileProcessor/download') {
    url.protocol = base.protocol
    url.host = base.host
    url.pathname = `${base.pathname.replace(/\/$/, '')}/aiFileProcessor/download`
  }
  const headers = new Headers()
  const token = StorageService.getAccessToken()
  if (token && url.origin === base.origin) headers.set('Authorization', `Bearer ${token}`)
  const response = await fetch(url, { headers, signal })
  if (!response.ok) throw new Error(`文件获取失败（${response.status}），请稍后重试`)
  return response.blob()
}
