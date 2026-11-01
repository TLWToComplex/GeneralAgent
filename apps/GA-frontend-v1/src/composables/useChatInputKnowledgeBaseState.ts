import type { KnowledgeBaseVM } from '@/services/knowledgeBase'

export type KnowledgeBaseListCache = {
  public: KnowledgeBaseVM[]
  private: KnowledgeBaseVM[]
}

let kbListCacheShared: KnowledgeBaseListCache | null = null
let kbListCacheAt = 0
let kbToggleEntrancePlayed = false

export const getKbListCacheShared = (): KnowledgeBaseListCache | null => kbListCacheShared

export const getKbListCacheAt = (): number => kbListCacheAt

export const setKbListCacheShared = (cache: KnowledgeBaseListCache): void => {
  kbListCacheShared = cache
  kbListCacheAt = Date.now()
}

export const invalidateKbListCacheShared = (): void => {
  kbListCacheShared = null
  kbListCacheAt = 0
}

export const consumeKbToggleEntranceActive = (): boolean => {
  const isActive = !kbToggleEntrancePlayed
  if (isActive) {
    kbToggleEntrancePlayed = true
  }
  return isActive
}

export const resetChatInputKnowledgeBaseState = (): void => {
  kbToggleEntrancePlayed = false
  invalidateKbListCacheShared()
}
