import { http } from '@/utils/http'

export interface LoginPayload {
  username: string
  password: string
  captchaId: string
  captchaCode: string
}

export interface LoginResponseData {
  token?: string
  accessToken?: string
  needUpdateMsg?: boolean
  passwordExpiredWarning?: boolean
  user?: Record<string, any>
  [key: string]: any
}

export interface LoginResponse {
  code?: number
  message?: string
  data?: LoginResponseData
  token?: string
  accessToken?: string
  needUpdateMsg?: boolean
  passwordExpiredWarning?: boolean
  user?: Record<string, any>
  [key: string]: any
}

export interface CaptchaData {
  captchaId: string
  captchaImage: string
}

export async function getCaptcha(): Promise<CaptchaData> {
  const res = await http.get('/captcha')
  return ((res.data as any)?.data || {}) as CaptchaData
}

export interface RegisterPayload {
  username: string
  email: string
  password: string
  additional_info?: Record<string, any>
}

export async function login(payload: LoginPayload): Promise<LoginResponse> {
  const res = await http.post('/aiUser/login', payload)
  return res.data as LoginResponse
}

export async function register(payload: RegisterPayload): Promise<any> {
  const res = await http.post('/aiUser/add', payload)
  return res.data
}

export interface UpdateUserPayload {
  uuid: string
  username?: string
  password?: string
  email?: string
  realname?: string
  additional_info?: Record<string, any>
  update_by?: string
}

export async function updateUser(payload: UpdateUserPayload): Promise<any> {
  const res = await http.post('/aiUser/update', payload)
  return res.data
}

export async function deleteUser(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiUser/delete', payload)
  return res.data
}

export interface AiUserRecord {
  id: number
  uuid: string
  username: string
  email: string | null
  realname: string | null
  contact: string | null
  address: string | null
  additional_info: Record<string, any>
  avatar: string
  avatarBackground: string
  avatarTextColor: string
  groups: UserGroupInfo[]
  create_time: string | null
  update_time: string | null
}

export interface GetAiUserRecordQuery {
  id?: number
  uuid?: string
  username?: string
}

export async function getAiUserRecord(query: GetAiUserRecordQuery): Promise<AiUserRecord | null> {
  const params: Record<string, string> = {}
  if (typeof query.id === 'number') params.id = String(query.id)
  if (query.uuid) params.uuid = String(query.uuid).trim()
  if (query.username) params.username = String(query.username).trim()
  const res = await http.get('/aiUser/record', {
    params
  })
  const user = (res.data as any)?.data
  if (!user) return null

  const additionalInfo =
    user?.additional_info && typeof user.additional_info === 'object'
      ? user.additional_info
      : {}

  return {
    id: Number(user?.id || 0),
    uuid: String(user?.uuid || '').trim(),
    username: String(user?.username || '').trim(),
    email: user?.email ? String(user.email).trim() : null,
    realname: user?.realname ? String(user.realname).trim() : null,
    contact: user?.contact ? String(user.contact).trim() : (additionalInfo?.contact ? String(additionalInfo.contact).trim() : null),
    address: user?.address ? String(user.address).trim() : (additionalInfo?.address ? String(additionalInfo.address).trim() : null),
    additional_info: additionalInfo,
    avatar: String(user?.avatar || additionalInfo?.avatar || '').trim(),
    avatarBackground: String(user?.avatarBackground || additionalInfo?.avatarBackground || '').trim(),
    avatarTextColor: String(user?.avatarTextColor || additionalInfo?.avatarTextColor || '').trim(),
    groups: normalizeUserGroups(user?.groups || additionalInfo?.groups),
    create_time: user?.create_time ? String(user.create_time).trim() : null,
    update_time: user?.update_time ? String(user.update_time).trim() : null
  }
}

export interface ChangePasswordPayload {
  uuid: string
  old_password: string
  new_password: string
}

export async function changePassword(payload: ChangePasswordPayload): Promise<any> {
  const res = await http.post('/aiUser/changePassword', payload)
  return res.data
}

export interface UserGroupInfo {
  group_id: string
  group_name: string
}

const normalizeUserGroups = (source: unknown): UserGroupInfo[] => {
  const candidates = Array.isArray(source)
    ? source
    : source && typeof source === 'object'
      ? [
          (source as Record<string, unknown>).groups,
          (source as Record<string, unknown>).items,
          (source as Record<string, unknown>).list,
          (source as Record<string, unknown>).records,
          source
        ]
      : []

  return Array.from(
    new Map(
      candidates
        .flatMap((item) => (Array.isArray(item) ? item : [item]))
        .map((group: any) => {
          const groupId = String(
            group?.group_id
              || group?.uuid
              || group?.id
              || ''
          ).trim()
          const groupName = String(
            group?.group_name
              || group?.name
              || group?.groupName
              || ''
          ).trim()

          if (!groupId || !groupName) {
            return null
          }

          return [groupId, { group_id: groupId, group_name: groupName }] as const
        })
        .filter((item): item is readonly [string, UserGroupInfo] => Boolean(item))
    ).values()
  )
}

export interface UserWithGroups {
  user_id: string
  username: string
  email: string | null
  realname: string | null
  is_locked: boolean
  groups: UserGroupInfo[]
}

export async function listAiUsersWithGroups(): Promise<UserWithGroups[]> {
  const res = await http.get('/aiUser/listWithGroups')
  const items = Array.isArray((res.data as any)?.data?.items) ? (res.data as any).data.items : []

  return items.map((item: any) => ({
    user_id: String(item?.user_id || '').trim(),
    username: String(item?.username || '').trim(),
    email: item?.email ? String(item.email).trim() : null,
    realname: item?.realname ? String(item.realname).trim() : null,
    is_locked: Boolean(item?.is_locked),
    groups: normalizeUserGroups(item?.groups)
  })).filter((item: UserWithGroups) => item.user_id && item.username)
}

export interface SyncUserGroupsPayload {
  user_group_map: Record<string, string[]>
}

export async function syncAiUserGroups(payload: SyncUserGroupsPayload): Promise<any> {
  const res = await http.post('/aiUser/syncGroups', payload)
  return res.data
}

export async function unlockAiUserAccount(payload: { uuid: string }): Promise<any> {
  const res = await http.post('/aiUser/unlockAccount', payload)
  return res.data
}
