import StorageService from './StorageService';
import { getApiBaseUrl } from './RuntimeConfig';
import NotificationService from './NotificationService';
import { broadcastGlobalLogout } from './TabScopeService';

/**
 * HTTP请求工具
 * 封装通用的请求逻辑
 */

interface RequestOptions extends RequestInit {
  timeout?: number;
  params?: Record<string, string>;
  baseUrlOverride?: string;
  /** 请求被外部 signal 或超时取消时，静默失败（不弹错误提示）；也可直接传入触发取消的 AbortSignal */
  silentAbort?: boolean | AbortSignal;
  /** 请求失败时不弹全局错误提示（仍会抛出异常） */
  silentError?: boolean;
}

interface HttpResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: Headers;
}

const ANONYMOUS_ALLOWED_PATHS = new Set([
  '/aiUser/login',
  '/aiUser/add',
  '/captcha',
  '/aiUserPreferences/add'
]);

const AUTH_BLOCKED_MESSAGE = '当前未登录，除登录和注册外的接口已被禁用';

class HttpError extends Error {
  public status: number;
  public statusText: string;
  public data: any;

  constructor(message: string, status: number, statusText: string, data: any) {
    super(message);
    this.name = 'HttpError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

class RequestBlockedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'RequestBlockedError';
  }
}

/**
 * 请求被取消（外部 signal 或超时）时抛出的静默错误，不触发全局错误弹窗
 */
class AbortedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'AbortedError';
  }
}

export const isAbortedError = (error: unknown): boolean =>
  error instanceof AbortedError || (error instanceof Error && error.name === 'AbortedError');

const silentAbortSignals = new Set<AbortSignal>();

/**
 * 注册一个“静默取消”的 AbortSignal：由该 signal 取消的请求不会弹出网络异常提示。
 * 用于沙盒预热等后台请求被主动抢占取消的场景。
 */
export const registerSilentAbortSignal = (signal: AbortSignal): void => {
  silentAbortSignals.add(signal);
  signal.addEventListener('abort', () => silentAbortSignals.delete(signal), { once: true });
};

const shouldSilenceAbort = (options: RequestOptions): boolean => {
  const silentAbort = options.silentAbort;
  if (!silentAbort) return false;
  if (silentAbort === true) return true;
  return silentAbort.aborted || silentAbortSignals.has(silentAbort);
};

const looksLikeAbort = (error: unknown): boolean =>
  error instanceof Error && (error.name === 'AbortError' || error.message.includes('aborted') || error.message.includes('中止'));

/**
 * 统一构建用户友好的错误消息
 */
function buildErrorMessage(status: number, statusText: string, data: any, fallback: string): string {
  let backendMsg = '';
  if (data) {
    if (typeof data === 'string') {
      backendMsg = data;
    } else if (typeof data === 'object') {
      backendMsg = (data.message || data.error || '').toString();
    }
  }

  if (backendMsg) return backendMsg;

  switch (status) {
    case 400: return '请求参数有误，请检查后重试';
    case 401: return fallback || '认证失败，请稍后再试';
    case 403: return '无权访问，请检查权限';
    case 404: return '请求的资源不存在';
    case 408: return '请求超时，请稍后再试';
    case 429: return '请求过于频繁，请稍后再试';
    case 500: return '服务器开小差了，请稍后再试';
    case 502: return '网关错误，请稍后重试';
    case 503: return '服务不可用，请稍后重试';
    case 504: return '网关超时，请稍后再试';
    default:
      return fallback || `请求失败: ${status} ${statusText}`;
  }
}

/**
 * 超时控制
 * @param ms 超时时间(毫秒)
 */
const timeout = (ms: number, onTimeout?: () => void) => {
  return new Promise((_, reject) => {
    setTimeout(() => {
      onTimeout?.();
      reject(new Error(`请求超时: ${ms}ms`));
    }, ms);
  });
};

/**
 * 构建URL，添加查询参数
 * @param url 基础URL
 * @param params 查询参数
 */
const buildUrl = (url: string, params?: Record<string, string>): string => {
  if (!params) return url;
  
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    searchParams.append(key, value);
  });
  
  const queryString = searchParams.toString();
  if (queryString) {
    return `${url}${url.includes('?') ? '&' : '?'}${queryString}`;
  }
  
  return url;
};

/**
 * 拼接基础地址与路径，确保只有一个斜杠
 * @param base 基础地址，如 http://127.0.0.1:8080
 * @param path 路径，如 /api/login 或 api/login
 */
const joinUrl = (base: string, path: string): string => {
  let b = (base || '').trim();
  let p = (path || '').trim();
  if (!b) return path;
  if (b.endsWith('/')) b = b.slice(0, -1);
  if (!p.startsWith('/')) p = '/' + p;
  return b + p;
};

const normalizeRequestPath = (url: string): string => {
  const value = (url || '').trim();
  if (!value) return '';

  try {
    if (/^https?:\/\//i.test(value)) {
      return new URL(value).pathname;
    }
    const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost';
    return new URL(value, origin).pathname;
  } catch {
    const withoutQuery = value.split('#')[0].split('?')[0].trim();
    if (!withoutQuery) return '';
    return withoutQuery.startsWith('/') ? withoutQuery : `/${withoutQuery}`;
  }
};

export const isAnonymousAllowedRequest = (url: string): boolean => {
  const path = normalizeRequestPath(url);
  return ANONYMOUS_ALLOWED_PATHS.has(path);
};

export const ensureAuthenticatedRequestAllowed = (url: string): void => {
  if (StorageService.getAccessToken() || isAnonymousAllowedRequest(url)) {
    return;
  }

  throw new RequestBlockedError(AUTH_BLOCKED_MESSAGE);
};

/**
 * 发送HTTP请求
 * @param url 请求URL
 * @param options 请求选项
 */
async function request<T = any>(url: string, options: RequestOptions = {}): Promise<HttpResponse<T>> {
  const { timeout: ms = 30000, params, silentAbort, silentError, ...fetchOptions } = options;
  const silenceAbort = shouldSilenceAbort({ silentAbort, ...fetchOptions });
  let timedOut = false;
  
  const isAbsolute = /^https?:\/\//i.test(url);
  const runtimeBase = options.baseUrlOverride ?? getApiBaseUrl();
  const resolvedUrl = !isAbsolute && runtimeBase ? joinUrl(runtimeBase, url) : url;
  const targetUrl = buildUrl(resolvedUrl, params);

  ensureAuthenticatedRequestAllowed(targetUrl);
  
  // 自动注入访问令牌到请求头
  const accessToken = StorageService.getAccessToken();
  if (accessToken) {
    const headers = new Headers(fetchOptions.headers || {});
    headers.set('Authorization', `Bearer ${accessToken}`);
    fetchOptions.headers = headers;
  }

  const controller = new AbortController();
  if (fetchOptions.signal) {
    const externalSignal = fetchOptions.signal;
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }
  fetchOptions.signal = controller.signal;
  
  try {
    const response = (Number.isFinite(ms) && ms > 0
      ? await Promise.race([
          fetch(targetUrl, fetchOptions),
          timeout(ms, () => { timedOut = true; controller.abort(); })
        ])
      : await fetch(targetUrl, fetchOptions)) as Response;
    
    let data: T;
    const contentType = response.headers.get('content-type');
    
    if (contentType?.includes('application/json')) {
      data = await response.json();
    } else if (contentType?.includes('text/')) {
      data = await response.text() as unknown as T;
    } else {
      data = await response.blob() as unknown as T;
    }
    
    // 拦截指定接口的特定错误返回，触发强制退出登录
    if (
      targetUrl.includes('/aiUser/record') && 
      data && 
      typeof data === 'object' && 
      (data as any).code === 404 && 
      (data as any).message === '用户不存在'
    ) {
      NotificationService.error('用户信息已失效，请重新登录');
      broadcastGlobalLogout('user-not-found');
      throw new HttpError('用户不存在', 404, 'Not Found', data);
    }
    
    // 拦截登录过期情况 (可能通过 HTTP 401 或是 200 返回 code 401/包含特定信息的 message)
    const isAuthPath = targetUrl.includes('/aiUser/login') || targetUrl.includes('/aiUser/add');
    if (!isAuthPath) {
      const isExpired = 
        response.status === 401 ||
        (data && typeof data === 'object' && (data as any).code === 401) ||
        (data && typeof data === 'object' && typeof (data as any).message === 'string' && 
          ((data as any).message.includes('过期') || (data as any).message.includes('未登录')));

      if (isExpired) {
        const msg = (data && typeof data === 'object' && typeof (data as any).message === 'string' && (data as any).message) || '登录信息已过期，请重新登录';
        NotificationService.error(msg);
        broadcastGlobalLogout('token-expired');
        throw new HttpError(msg, 401, 'Unauthorized', data);
      }
    }
    
    if (!response.ok) {
      const message = buildErrorMessage(
        response.status,
        response.statusText,
        data,
        `请求失败: ${response.status} ${response.statusText}`
      );
      
      if (!isAuthPath && (message.includes('过期') || message.includes('未登录') || message.includes('失效'))) {
        NotificationService.error(message);
        broadcastGlobalLogout('token-expired');
        throw new HttpError(message, response.status, response.statusText, data);
      }

      // 统一弹出错误提示（silentError 时跳过）
      if (!silentError) {
        NotificationService.error(message);
      }
      throw new HttpError(message, response.status, response.statusText, data);
    }
    
    return {
      data,
      status: response.status,
      statusText: response.statusText,
      headers: response.headers
    };
  } catch (error) {
    if (error instanceof HttpError) {
      // 已统一弹窗，直接抛出供上层逻辑处理
      throw error;
    }
    if (error instanceof RequestBlockedError) {
      throw error;
    }
    // 请求被取消（外部 signal 或超时）：仅在静默模式下跳过错误提示
    if (silenceAbort && (timedOut || looksLikeAbort(error))) {
      throw new AbortedError(timedOut ? `请求超时: ${ms}ms` : '请求已取消');
    }
    const message = `网络异常：${(error as Error).message}`;
    if (!silentError) {
      NotificationService.error(message);
    }
    throw new Error(message);
  }
}

/**
 * HTTP工具对象
 */
export const http = {
  /**
   * GET请求
   * @param url 请求URL
   * @param options 请求选项
   */
  get: <T = any>(url: string, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return request<T>(url, {
      method: 'GET',
      ...options
    });
  },
  
  /**
   * POST请求
   * @param url 请求URL
   * @param data 请求数据
   * @param options 请求选项
   */
  post: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return request<T>(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      },
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  },
  /**
   * POST表单（FormData）请求
   * 不设置 Content-Type，交由浏览器自动生成 multipart/form-data 边界
   */
  postForm: <T = any>(url: string, formData: FormData, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return request<T>(url, {
      method: 'POST',
      // 不要设置 'Content-Type'，否则会破坏 FormData 边界
      headers: {
        ...(options?.headers || {})
      },
      body: formData,
      ...options
    });
  },
  
  /**
   * PUT请求
   * @param url 请求URL
   * @param data 请求数据
   * @param options 请求选项
   */
  put: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return request<T>(url, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      },
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  },
  
  /**
   * DELETE请求
   * @param url 请求URL
   * @param options 请求选项
   */
  delete: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return request<T>(url, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      },
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  },
  
  /**
   * PATCH请求
   * @param url 请求URL
   * @param data 请求数据
   * @param options 请求选项
   */
  patch: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return request<T>(url, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        ...(options?.headers || {})
      },
      body: data ? JSON.stringify(data) : undefined,
      ...options
    });
  }
};

/**
 * 专用于知识库服务的 HTTP 客户端，统一使用 API_BASE_URL 转发
 */
export const httpKb = {
  get: <T = any>(url: string, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return http.get<T>(url, { ...(options || {}), baseUrlOverride: getApiBaseUrl() });
  },
  post: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return http.post<T>(url, data, { ...(options || {}), baseUrlOverride: getApiBaseUrl() });
  },
  
  /**
   * POST表单（FormData）请求（知识库服务）
   */
  postForm: <T = any>(url: string, formData: FormData, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return http.postForm<T>(url, formData, { ...(options || {}), baseUrlOverride: getApiBaseUrl() });
  },
  put: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return http.put<T>(url, data, { ...(options || {}), baseUrlOverride: getApiBaseUrl() });
  },
  delete: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return http.delete<T>(url, data, { ...(options || {}), baseUrlOverride: getApiBaseUrl() });
  },
  patch: <T = any>(url: string, data?: any, options?: RequestOptions): Promise<HttpResponse<T>> => {
    return http.patch<T>(url, data, { ...(options || {}), baseUrlOverride: getApiBaseUrl() });
  }
};
