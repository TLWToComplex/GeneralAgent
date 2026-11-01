import { http } from '@/utils/http'

export async function listPlatformModels(): Promise<any[]> {
  const res = await http.get('/aiPlatformModel/list')
  return (res.data?.data || []) as any[]
}

export async function addPlatformModel(payload: any): Promise<any> {
  const res = await http.post('/aiPlatformModel/add', payload)
  return res.data
}

export async function updatePlatformModel(payload: any): Promise<any> {
  const res = await http.post('/aiPlatformModel/update', payload)
  return res.data
}

export async function deletePlatformModel(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiPlatformModel/delete', payload)
  return res.data
}

export async function reorderPlatformModels(uuids: string[]): Promise<any> {
  const res = await http.post('/aiPlatformModel/reorder', { uuids })
  return res.data
}