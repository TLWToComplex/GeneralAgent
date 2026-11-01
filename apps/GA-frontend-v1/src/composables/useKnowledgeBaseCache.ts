// src/composables/useKnowledgeBaseCache.ts
// 知识库列表 / 文档列表的模块级缓存（单例，跨组件实例、跨页面切换共享）。
// 目的：个人 ↔ 共享切换、聊天 ↔ 知识库工作区来回切换时，先用缓存内容上屏（SWR），
// 不再每次都退回骨架屏，再由后台请求静默校验数据新鲜度。
import type {
  KnowledgeBaseFileVM,
  KnowledgeBasePermissionCode,
  KnowledgeBaseVM,
} from '@/services/knowledgeBase'
import { listKnowledgeBaseFiles } from '@/services/knowledgeBase'

// 列表缓存有效期：命中且未过期时直接复用，不再发请求；过期则「先用缓存、后台刷新」
export const KB_LIST_CACHE_TTL = 60_000
// 文档缓存有效期相对更短：文档增删比知识库本身频繁
export const KB_DOCS_CACHE_TTL = 30_000

type CacheEntry<T> = { value: T; fetchedAt: number }

const listCache = new Map<KnowledgeBasePermissionCode, CacheEntry<KnowledgeBaseVM[]>>()
const docsCache = new Map<string, CacheEntry<KnowledgeBaseFileVM[]>>()
const pendingDocs = new Map<string, Promise<KnowledgeBaseFileVM[]>>()

const isFresh = (entry: CacheEntry<unknown> | undefined, ttl: number): boolean =>
  !!entry && Date.now() - entry.fetchedAt < ttl

// ---------- 知识库列表 ----------

// 返回缓存内容（不判断新鲜度），供 stale-while-revalidate 先渲染
export const peekKbListCache = (filter: KnowledgeBasePermissionCode): KnowledgeBaseVM[] | null => {
  const entry = listCache.get(filter)
  return entry ? [...entry.value] : null
}

export const isKbListCacheFresh = (filter: KnowledgeBasePermissionCode): boolean =>
  isFresh(listCache.get(filter), KB_LIST_CACHE_TTL)

export const writeKbListCache = (filter: KnowledgeBasePermissionCode, items: KnowledgeBaseVM[]): void => {
  listCache.set(filter, { value: items, fetchedAt: Date.now() })
}

// 不传 filter 时清空全部分类：新建 / 编辑 / 删除会同时影响个人与共享两个列表
export const invalidateKbListCache = (filter?: KnowledgeBasePermissionCode): void => {
  if (filter) {
    listCache.delete(filter)
    return
  }
  listCache.clear()
}

// ---------- 知识库文档 ----------

export const peekKbDocsCache = (kbName: string): KnowledgeBaseFileVM[] | null => {
  const entry = docsCache.get(kbName)
  return entry ? [...entry.value] : null
}

export const isKbDocsCacheFresh = (kbName: string): boolean =>
  isFresh(docsCache.get(kbName), KB_DOCS_CACHE_TTL)

export const writeKbDocsCache = (kbName: string, files: KnowledgeBaseFileVM[]): void => {
  docsCache.set(kbName, { value: files, fetchedAt: Date.now() })
}

// Format previews and the reader share the same request and freshness policy.
// Invalidated/replaced requests may finish, but cannot overwrite newer cache data.
export const loadKbDocs = (kbName: string, options: { force?: boolean } = {}): Promise<KnowledgeBaseFileVM[]> => {
  if (!options.force) {
    if (isKbDocsCacheFresh(kbName)) return Promise.resolve(peekKbDocsCache(kbName)!)
    const pending = pendingDocs.get(kbName)
    if (pending) return pending
  }
  const request = listKnowledgeBaseFiles(kbName).then(files => {
    if (pendingDocs.get(kbName) === request) writeKbDocsCache(kbName, files)
    return files
  }).finally(() => {
    if (pendingDocs.get(kbName) === request) pendingDocs.delete(kbName)
  })
  pendingDocs.set(kbName, request)
  return request
}

export const invalidateKbDocsCache = (kbName?: string): void => {
  if (kbName) {
    docsCache.delete(kbName)
    pendingDocs.delete(kbName)
    return
  }
  docsCache.clear()
  pendingDocs.clear()
}

export const clearKnowledgeBaseRuntimeCache = (): void => {
  listCache.clear()
  docsCache.clear()
  pendingDocs.clear()
}
