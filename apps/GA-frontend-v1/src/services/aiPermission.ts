import { http } from '@/utils/http'

export interface UserGroupItem {
  id: string
  uuid: string
  name: string
}

export interface UserGroupRecord {
  id: number
  uuid: string
  name: string
  additional_info: Record<string, any>
  create_by: string | null
  create_time: string | null
  update_by: string | null
  update_time: string | null
}

export async function listAiUserGroups(): Promise<UserGroupItem[]> {
  const res = await http.get('/aiUserGroup/list')
  const groups = Array.isArray((res.data as any)?.data) ? (res.data as any).data : []
  return groups
    .map((group: any) => ({
      id: String(group?.id || '').trim(),
      uuid: String(group?.uuid || '').trim(),
      name: String(group?.name || '').trim()
    }))
    .filter((group: UserGroupItem) => group.uuid && group.name)
}

export async function getAiUserGroupRecord(uuid: string): Promise<UserGroupRecord | null> {
  const res = await http.get('/aiUserGroup/record', {
    params: { uuid }
  })
  const group = (res.data as any)?.data
  if (!group) return null

  return {
    id: Number(group?.id || 0),
    uuid: String(group?.uuid || '').trim(),
    name: String(group?.name || '').trim(),
    additional_info:
      group?.additional_info && typeof group.additional_info === 'object'
        ? group.additional_info
        : {},
    create_by: group?.create_by ? String(group.create_by).trim() : null,
    create_time: group?.create_time ? String(group.create_time).trim() : null,
    update_by: group?.update_by ? String(group.update_by).trim() : null,
    update_time: group?.update_time ? String(group.update_time).trim() : null
  }
}

export interface AddAiUserGroupPayload {
  name: string
  additional_info?: Record<string, any>
}

export async function addAiUserGroup(payload: AddAiUserGroupPayload): Promise<any> {
  const res = await http.post('/aiUserGroup/add', payload)
  return res.data
}

export interface UpdateAiUserGroupPayload {
  uuid: string
  name?: string
  additional_info?: Record<string, any>
}

export async function updateAiUserGroup(payload: UpdateAiUserGroupPayload): Promise<any> {
  const res = await http.post('/aiUserGroup/update', payload)
  return res.data
}

export async function setDefaultAiUserGroup(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiUserGroup/setDefault', payload)
  return res.data
}

export async function getDefaultAiUserGroup(): Promise<UserGroupRecord | null> {
  const res = await http.get('/aiUserGroup/getDefault')
  const group = (res.data as any)?.data
  if (!group) return null

  return {
    id: Number(group?.id || 0),
    uuid: String(group?.uuid || '').trim(),
    name: String(group?.name || '').trim(),
    additional_info:
      group?.additional_info && typeof group.additional_info === 'object'
        ? group.additional_info
        : {},
    create_by: group?.create_by ? String(group.create_by).trim() : null,
    create_time: group?.create_time ? String(group.create_time).trim() : null,
    update_by: group?.update_by ? String(group.update_by).trim() : null,
    update_time: group?.update_time ? String(group.update_time).trim() : null
  }
}

export async function deleteAiUserGroup(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiUserGroup/delete', payload)
  return res.data
}

export interface UpdateAiPermissionPayload {
  group_id: string
  list: Array<{
    entity_id: string
    entity_type: number
    permission: 1 | 2
  }>
}

export async function updateAiPermission(payload: UpdateAiPermissionPayload): Promise<any> {
  const res = await http.post('/aiPermission/update', payload)
  return res.data
}

export interface AiEntityAssignedGroupsResponse {
  code: number
  message?: string
  msg?: string
  data?: {
    assigned_groups?: unknown[]
    entity_id?: string
    entity_type?: number
  }
}

const normalizeAssignedGroupIds = (groups: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(groups) ? groups : []).flatMap((group) => {
        if (typeof group === 'string' && group.trim()) {
          return [group.trim()]
        }
        if (group && typeof group === 'object') {
          const candidate = (group as Record<string, unknown>).group_id
            || (group as Record<string, unknown>).uuid
            || (group as Record<string, unknown>).id
          if (typeof candidate === 'string' && candidate.trim()) {
            return [candidate.trim()]
          }
          if (typeof candidate === 'number' && Number.isFinite(candidate)) {
            return [String(candidate)]
          }
        }
        return []
      })
    )
  )

export async function listAiEntityAssignedGroups(entityId: string, entityType: number): Promise<string[]> {
  const res = await http.get<AiEntityAssignedGroupsResponse>('/aiEntityPermission/assignedGroups', {
    params: {
      entity_id: entityId,
      entity_type: String(entityType)
    }
  })
  const payload = res.data
  if (payload?.code !== 0) {
    throw new Error(payload?.message || payload?.msg || '获取实体已分配用户组失败')
  }
  return normalizeAssignedGroupIds(payload?.data?.assigned_groups)
}
