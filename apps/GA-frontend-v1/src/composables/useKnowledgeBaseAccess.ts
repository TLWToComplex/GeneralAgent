// src/composables/useKnowledgeBaseAccess.ts
// 知识库权限判定的唯一来源：设置页（/settings/knowledge-base）与聊天页知识库工作区共用，
// 保证两个入口对 admin / 普通用户的限制完全一致。
import type { KnowledgeBasePermissionCode } from '@/services/knowledgeBase'

export type KnowledgeBaseLike = { permissionCode?: KnowledgeBasePermissionCode } | null | undefined

// 共享（public）知识库；permissionCode 缺失时按个人库处理，与列表过滤逻辑保持一致
export const isSharedKnowledgeBase = (kb: KnowledgeBaseLike): boolean => kb?.permissionCode === 'public'

/**
 * 共享（public）知识库仅 admin 可管理：编辑信息、删除知识库、上传 / 删除文档。
 * 个人（private）知识库不受限制。
 */
export const canManageKnowledgeBase = (kb: KnowledgeBaseLike, isAdmin: boolean): boolean =>
  !isSharedKnowledgeBase(kb) || isAdmin

export const KB_ADMIN_ONLY_TIP = '共享知识库仅 admin 可操作'
export const KB_DELETE_KB_ADMIN_ONLY_TIP = '共享知识库仅 admin 可删除'
export const KB_UPLOAD_ADMIN_ONLY_TIP = '共享知识库仅 admin 可上传文档'
export const KB_DELETE_DOC_ADMIN_ONLY_TIP = '共享知识库仅 admin 可删除文档'
export const KB_VISIBILITY_ADMIN_ONLY_TIP = '仅 admin 可创建共享知识库，将创建为个人知识库'
export const KB_VISIBILITY_EDIT_ADMIN_ONLY_TIP = '仅 admin 可修改可见范围'
export const KB_SHARED_READONLY_TIP = '共享知识库仅 admin 可修改'
