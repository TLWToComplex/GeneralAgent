 
import StorageService, { STORAGE_KEYS } from '@/utils/StorageService'
import { updateUserPreferences, getUserPreferences } from '@/services/aiUserPreferences'

export interface UpdatePromptPayload {
  prompt: string
}

export async function getPrompt(): Promise<string[]> {
  const res = await getUserPreferences()
  const body: any = res
  const prefs = (body?.data?.preferences ?? body?.preferences ?? {}) as any
  StorageService.set(STORAGE_KEYS.USER_PREFERENCES, prefs)
  const prompt = typeof prefs.prompt === 'string' ? prefs.prompt : ''
  if (prompt && typeof prompt === 'string' && prompt.trim()) {
    return [prompt.trim()]
  }
  return []
}

export async function updatePrompt(payload: UpdatePromptPayload): Promise<any> {
  const raw = localStorage.getItem('user-profile')
  const userId = raw ? (JSON.parse(raw as string).uuid || '') : ''
  const localPrefs = (StorageService.get(STORAGE_KEYS.USER_PREFERENCES) || {}) as any
  const promptText = payload.prompt
  const preferences = { ...localPrefs, prompt: promptText } as any
  const res = await updateUserPreferences({ userId, preferences })
  return res
}
