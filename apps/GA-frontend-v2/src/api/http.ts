/* ============================================================================
   HTTP 层 —— 后端接口调用的唯一出口。

   为什么要单独一层：后端的错误响应有两套形态（见后端 README 的「接口契约」）：
     · 业务失败：{"error": "验证码错误"}          —— 400 / 401 / 403 / 500
     · 越权失败：{"code": 403, "message": "..."}  —— 沿用老项目 admin_required
   两套都要能落到同一个 ApiError.message 上，页面才不用写两遍解析。

   另外统一处理：
     · Bearer 令牌注入（令牌由 stores/auth.ts 通过 configureHttp 注册进来，
       避免 http → store → api → http 的循环依赖）；
     · 401 会话失效回调（令牌到期 / 后端重启换了 JWT_SECRET_KEY / 账号被删）；
     · 网络层失败（后端没起、超时、跨域被拦）也抛 ApiError，不让 fetch 的
       TypeError 漏到页面上，否则用户只会看到一句 "Failed to fetch"。
   ========================================================================== */

import { apiBase } from '@/config/runtime'

/** 后端返回的错误体（三种已知形态，字段都可缺省） */
interface BackendErrorBody {
  error?: unknown
  message?: unknown
  code?: unknown
}

export class ApiError extends Error {
  /** HTTP 状态码；网络层失败时为 0 */
  readonly status: number
  /** 原始响应体（解析失败时为 null），便于排查 */
  readonly payload: unknown

  constructor(message: string, status: number, payload: unknown = null) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.payload = payload
  }

  /** 会话失效（令牌缺失/过期/无效）—— 调用方据此清登录态回登录页 */
  get isUnauthorized(): boolean {
    return this.status === 401
  }

  /** 网络层失败：请求根本没到后端（后端未启动、跨域、断网、超时） */
  get isNetworkError(): boolean {
    return this.status === 0
  }
}

/** :class:`ApiError` 的类型守卫（页面 catch 到 unknown 时用它收窄） */
export function isApiError(err: unknown): err is ApiError {
  return err instanceof ApiError
}

/* ---------------------------------------------------------------- 全局配置 */

type TokenGetter = () => string | null
type UnauthorizedHandler = () => void

let getToken: TokenGetter = () => null
let onUnauthorized: UnauthorizedHandler = () => {}

/**
 * 由 stores/auth.ts 在创建时调用：注册令牌来源与 401 处理器。
 * 这样 http 层不需要 import store，store 也不需要把令牌透传给每个接口函数。
 */
export function configureHttp(options: {
  getToken?: TokenGetter
  onUnauthorized?: UnauthorizedHandler
}): void {
  if (options.getToken) getToken = options.getToken
  if (options.onUnauthorized) onUnauthorized = options.onUnauthorized
}

/* ---------------------------------------------------------------- 请求实现 */

/** 组装完整 URL（apiBase 为空时就是同源相对路径）
 *
 * 每次请求都重新读配置（而不是模块加载时取一次）：config.json 是运期拉的，
 * 早于加载完成的请求会用默认值；这里按调用时机取值，加载完成后自然就对了。 */
function resolveUrl(path: string): string {
  const base = apiBase()
  if (!base) return path
  return `${base.replace(/\/+$/, '')}${path.startsWith('/') ? path : `/${path}`}`
}

/**
 * 从响应体里抽取给用户看的错误文案。
 * 优先级：error → message → code 拼装 → 按状态码兜底，保证永远有中文提示。
 */
function pickErrorMessage(body: BackendErrorBody | null, status: number): string {
  if (body) {
    if (typeof body.error === 'string' && body.error) return body.error
    if (typeof body.message === 'string' && body.message) return body.message
  }
  if (status === 400) return '请求参数不正确'
  if (status === 401) return '登录状态已失效，请重新登录'
  if (status === 403) return '没有访问权限'
  if (status === 404) return '请求的接口不存在'
  if (status === 501) return '服务端尚未启用该登录方式'
  if (status >= 500) return '服务器内部错误，请稍后重试'
  return `请求失败（HTTP ${status}）`
}

export interface RequestOptions {
  /** 请求体，传对象即可自动 JSON 序列化 */
  body?: unknown
  /** 是否携带 Bearer 令牌，默认 true */
  auth?: boolean
  /** 超时时间（毫秒），默认 15000 */
  timeoutMs?: number
  signal?: AbortSignal
}

/**
 * 发一个 JSON 请求并返回解析后的响应体。
 *
 * @throws {ApiError} 非 2xx、响应体不是 JSON、超时或网络失败
 */
export async function request<T>(method: string, path: string, options: RequestOptions = {}): Promise<T> {
  const { body, auth = true, timeoutMs = 15000 } = options

  const headers: Record<string, string> = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  let sentToken: string | null = null
  if (auth) {
    sentToken = getToken()
    if (sentToken) headers.Authorization = `Bearer ${sentToken}`
  }

  /* 超时：AbortController + 计时器；调用方自己的 signal 也要能中断 */
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(new DOMException('timeout', 'TimeoutError')), timeoutMs)
  const onExternalAbort = (): void => controller.abort()
  options.signal?.addEventListener('abort', onExternalAbort)

  let response: Response
  try {
    response = await fetch(resolveUrl(path), {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    })
  } catch (err) {
    // 区分「超时」与「请求没发出去」：前者给用户「请重试」，后者提示后端不可达
    const isTimeout = err instanceof DOMException && err.name === 'TimeoutError'
    throw new ApiError(
      isTimeout ? '请求超时，请稍后重试' : '无法连接后端服务，请确认服务已启动或网络可达',
      0,
      null,
    )
  } finally {
    window.clearTimeout(timer)
    options.signal?.removeEventListener('abort', onExternalAbort)
  }

  /* 响应体：后端契约里成功与失败都是 JSON；非 JSON 时按状态码兜底 */
  let parsed: unknown = null
  const text = await response.text()
  if (text) {
    try {
      parsed = JSON.parse(text)
    } catch {
      parsed = null
    }
  }

  if (!response.ok) {
    // 只有「带着令牌被拒」才算会话失效。登录接口本身也用 401 表达
    // 「验证码错误 / 密码错误 / 用户名无效」，那种 401 是业务失败，
    // 不能触发清登录态（否则登录页会被自己踢一次）。
    if (response.status === 401 && sentToken) {
      onUnauthorized()
    }
    throw new ApiError(
      pickErrorMessage(parsed as BackendErrorBody | null, response.status),
      response.status,
      parsed,
    )
  }

  return parsed as T
}

/** GET 快捷方式 */
export function get<T>(path: string, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
  return request<T>('GET', path, options)
}

/** POST 快捷方式 */
export function post<T>(path: string, body?: unknown, options: Omit<RequestOptions, 'body'> = {}): Promise<T> {
  return request<T>('POST', path, { ...options, body })
}