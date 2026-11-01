import { http } from '@/utils/http'

export interface ScreenshotPayload {
  url: string
  width: number
  height: number
  isfullpage?: boolean
}

/**
 * 调用后端截图服务，返回 PNG 图片 Blob
 */
export async function captureScreenshot(payload: ScreenshotPayload): Promise<Blob> {
  const res = await http.post<Blob>('/api/screenshot', payload)
  return res.data
}
