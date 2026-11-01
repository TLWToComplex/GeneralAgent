/* ============================================================================
   认证接口封装 —— 对应后端的 /captcha 与 /aiUser/* 接口。

   字段名、响应结构与后端 README 的「接口契约」一一对应，改动前先对文档。
   ========================================================================== */

import { get, post } from '@/api/http'

/* ---------------------------------------------------------------- 图形验证码 */

/** GET /captcha 的 data 部分 */
export interface CaptchaData {
  /** 验证码 ID，登录时原样回传 */
  captchaId: string
  /** data:image/png;base64,...，可直接塞给 <img src> */
  captchaImage: string
}

interface CaptchaResponse {
  code: number
  message: string
  data: CaptchaData
}

/**
 * 取一张图形验证码。
 *
 * 注意后端是**一次性使用**：无论校验通过与否，提交后该 captchaId 立即作废，
 * 因此每次登录失败都必须重新获取（见 LoginView 的 refreshCaptcha）。
 */
export async function fetchCaptcha(): Promise<CaptchaData> {
  const body = await get<CaptchaResponse>('/captcha', { auth: false })
  return body.data
}

/* ---------------------------------------------------------------- 登录 */

/** 登录用户信息（后端把 additional_info 平铺到顶层，故用索引签名兜住未知字段） */
export interface LoginUser {
  id?: number
  uuid?: string
  username: string
  email?: string | null
  realname?: string | null
  create_time?: string | null
  is_del?: number
  last_login_time?: string | null
  last_password_change?: string | null
  /** realname 为空时为 true（老项目语义：提示用户补全姓名） */
  needUpdateMsg?: boolean
  [key: string]: unknown
}

interface LoginResponse {
  status: string
  message: string
  user: LoginUser
  token: string
  /** 密码超过 N 天未更新：后端只提醒不阻断（老项目口径） */
  passwordExpiredWarning: boolean
}

export interface LoginPayload {
  username: string
  password: string
  captchaId: string
  captchaCode: string
}

/**
 * 本地账号登录。
 *
 * @throws {ApiError} 失败文案直接来自后端（验证码错误 / 密码错误还剩N次机会 /
 *   账号已锁定请N分钟后重试 / 超过30天未登录已被锁定 …），页面按文案透出即可。
 */
export async function login(payload: LoginPayload): Promise<LoginResponse> {
  return post<LoginResponse>('/aiUser/login', payload, { auth: false })
}

/* ---------------------------------------------------------------- 未接入的接口
   后端还有 POST /aiUser/changePassword（需登录）与 POST /aiUser/unlockAccount（需 admin），
   本轮只做「登录打通」，因此暂不封装：等改密/解锁页面开工时在这里加，
   保持「接口封装只出现在本文件」的约定。
   ---------------------------------------------------------------------------- */