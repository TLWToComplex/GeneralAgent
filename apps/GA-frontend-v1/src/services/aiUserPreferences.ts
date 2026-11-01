import { http } from '@/utils/http'

export async function addUserPreferences(payload: { userId: string, preferences: any }): Promise<any> {
  const res = await http.post('/aiUserPreferences/add', payload)
  return res.data
}

export async function getUserPreferences(): Promise<any> {
  const res = await http.get('/aiUserPreferences/get')
  return res.data
}

export async function updateUserPreferences(payload: { userId: string, preferences: any }): Promise<any> {
  const res = await http.post('/aiUserPreferences/update', payload)
  return res.data
}