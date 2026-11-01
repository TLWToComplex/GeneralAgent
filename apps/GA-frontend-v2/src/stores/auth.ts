/* ============================================================================
   登录态 store —— 令牌、当前用户、会话失效处理

   职责边界：
     · 本 store 是「登录态」的唯一来源（令牌 / 用户信息 / 是否已登录）；
     · HTTP 层不 import 本 store，而是由本 store 在创建时把「取令牌」与
       「401 处理」注册进 src/api/http.ts（configureHttp），避免循环依赖；
     · 页面跳转（回登录页）由本 store 负责，守卫（router/index.ts）只读状态。

   持久化：令牌与用户信息写 localStorage（键名见 constants.ts）。
   刷新页面后先 restore() 再判定登录态，刷深链不会被踢回登录页。

   会话有效期：后端 JWT 默认 1 小时，且 JWT_SECRET_KEY 未显式配置时后端每次重启都会
   让已签发令牌失效（见后端 README「部署注意事项」）。因此这里做两层兜底：
     1. 本地解出 exp 提前判定过期（省掉一次必然 401 的请求）；
     2. 任何接口返回 401 → 清登录态 + 回登录页（而不是当成普通报错弹提示）。

   免登录模式（config.json 的 skipLogin，见 src/config/runtime.ts）：
     · 只在**启动**时判定（restore()），不参与运行中热切换；
     · 本地已有有效令牌时优先用令牌（那是真身份，展示名/进 dsh 的用户名都更准），
       没有再落一个本地身份：`isAuthenticated` 为真、user 用 skipLoginUser() 合成；
     · **不发令牌**（getToken 返回 null）—— 免登录下没有真令牌可发。
       这同时消掉了「被 401 弹回登录页」：http.ts 只在**带着令牌**被拒时才回调
       onUnauthorized（见 src/api/http.ts），没发令牌就不会触发；
     · 因此 401 只会让页面按接口报错显示，不会把人踢到登录页（免登录下本来也没有登录页）。
   ========================================================================== */

import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { configureHttp } from '@/api/http'
import type { LoginUser } from '@/api/auth'
import { TOKEN_KEY, USER_KEY } from '@/constants'
import { skipLogin, skipLoginUser } from '@/config/runtime'

/** 解析 JWT 的 exp（毫秒时间戳）；解析失败返回 null（按"不确定"处理） */
function readTokenExpiry(token: string): number | null {
  const payload = token.split('.')[1]
  if (!payload) return null
  try {
    // base64url → base64：JWT 用 -_ 且省略 padding，atob 认 +/ 且要求补齐
    const normalized = payload.replace(/-/g, '+').replace(/_/g, '/')
    const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
    // atob 对非 ASCII 会抛错；这里只需要 exp 数字，用 decodeURIComponent 兜住 UTF-8
    const json = decodeURIComponent(
      atob(padded)
        .split('')
        .map((c) => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`)
        .join(''),
    )
    const claims = JSON.parse(json) as { exp?: number }
    return typeof claims.exp === 'number' ? claims.exp * 1000 : null
  } catch {
    return null
  }
}

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key)
  } catch {
    return null // 隐私模式 / 存储被禁用
  }
}

function writeStorage(key: string, value: string | null): void {
  try {
    if (value === null) window.localStorage.removeItem(key)
    else window.localStorage.setItem(key, value)
  } catch {
    /* 隐私模式忽略：本次会话仍可用，只是刷新后需要重新登录 */
  }
}

export const useAuthStore = defineStore('auth', () => {
  /* ---------------------------------------------------------------- 状态 */
  const token = ref<string | null>(null)
  const user = ref<LoginUser | null>(null)
  /** 会话失效原因（被 401 踢出时写入，登录页可据此提示"请重新登录"） */
  const expiredNotice = ref('')
  /** 是否处于免登录模式（启动时按 config.json 定下，之后不变） */
  const skipLoginMode = ref(false)

  /* ---------------------------------------------------------------- 派生 */
  const isAuthenticated = computed(() => token.value !== null || skipLoginMode.value)

  /** 顶栏展示名：优先真实姓名，其次用户名 */
  const displayName = computed(() => {
    const u = user.value
    if (!u) return ''
    return (u.realname || '').trim() || u.username || ''
  })

  /** 顶栏头像字：取展示名首字 */
  const avatarText = computed(() => displayName.value.slice(0, 1) || '·')

  /** 是否为管理员（后端 unlockAccount 等接口按 username === 'admin' 判权） */
  const isAdmin = computed(() => (user.value?.username ?? '').toLowerCase() === 'admin')

  /* ---------------------------------------------------------------- 持久化 */
  function persist(): void {
    writeStorage(TOKEN_KEY, token.value)
    writeStorage(USER_KEY, user.value ? JSON.stringify(user.value) : null)
  }

  function clearPersisted(): void {
    writeStorage(TOKEN_KEY, null)
    writeStorage(USER_KEY, null)
  }

  /**
   * 落一个「免登录」用的本地身份：不写 localStorage、不发令牌。
   *
   * 为什么不写 localStorage：这不是一次真实登录。写进去等于在浏览器里留一个假登录态 ——
   * 下次把开关关掉，用户会带着这个从未被验证过的身份直接进控制台。开关关掉 + 刷新就回
   * 登录页，才是这个开关该有的语义。
   */
  function applySkipLogin(): void {
    skipLoginMode.value = true
    token.value = null
    const name = skipLoginUser()
    user.value = { username: name, realname: name, needUpdateMsg: false }
    expiredNotice.value = '' // 免登录下没有登录页，没人消费这条提示
    clearPersisted()
  }

  /**
   * 从 localStorage 恢复登录态；令牌已过期则直接清掉（视为未登录）。
   * 由 main.ts 在挂载路由前调用一次。
   *
   * 顺序：真令牌可用就用真令牌（免登录模式下也一样 —— 真身份更好），
   * 否则若配置开了 skipLogin 就落本地身份，跳过登录页。
   */
  function restore(): void {
    const savedToken = readStorage(TOKEN_KEY)
    const expiry = savedToken ? readTokenExpiry(savedToken) : null
    const usable = !!savedToken && (expiry === null || expiry > Date.now())

    if (savedToken && !usable) {
      clearPersisted()
      expiredNotice.value = '登录状态已过期，请重新登录'
    }

    if (usable && savedToken) {
      token.value = savedToken
      const savedUser = readStorage(USER_KEY)
      if (savedUser) {
        try {
          user.value = JSON.parse(savedUser) as LoginUser
        } catch {
          user.value = null // 脏数据：只影响展示名，不影响鉴权
        }
      }
      return
    }

    /* config.json 的 skipLogin=true：直接以本地身份进控制台 */
    if (skipLogin()) applySkipLogin()
  }

  /* ---------------------------------------------------------------- 动作 */
  /** 登录成功后落地登录态（由登录页在拿到后端响应后调用） */
  function setSession(nextToken: string, nextUser: LoginUser): void {
    token.value = nextToken
    user.value = nextUser
    expiredNotice.value = ''
    persist()
  }

  /** 清空登录态（退出登录、会话失效共用） */
  function clearSession(notice = ''): void {
    token.value = null
    user.value = null
    expiredNotice.value = notice
    clearPersisted()
    /* 免登录模式：清完立刻落回本地身份 —— 否则守卫会把人弹向一个并不存在的登录页 */
    if (skipLogin()) applySkipLogin()
  }

  /** 消费一次失效提示（登录页展示后调用，避免反复弹） */
  function consumeExpiredNotice(): string {
    const notice = expiredNotice.value
    expiredNotice.value = ''
    return notice
  }

  /**
   * 后端返回 401 时的统一处理：清登录态并回登录页。
   *
   * 这里用 location.hash 直接跳而不是 router.replace：HTTP 层是纯模块，
   * 拿不到 router 实例；而本项目用 hash 路由（createWebHashHistory），
   * 改 hash 与 router 的行为一致。已在登录页时不动，避免打断用户输入。
   */
  function handleUnauthorized(): void {
    if (!token.value) return
    clearSession('登录状态已失效，请重新登录')
    /* 免登录模式：没有登录页可回（上面 clearSession 已落回本地身份），继续用即可 */
    if (skipLogin()) return
    if (!window.location.hash.startsWith('#/login')) {
      window.location.hash = '#/login'
    }
  }

  /* 把令牌来源与 401 处理注册给 HTTP 层（本 store 首次被 use 时执行一次） */
  configureHttp({
    getToken: () => token.value,
    onUnauthorized: handleUnauthorized,
  })

  return {
    token,
    user,
    expiredNotice,
    isAuthenticated,
    /** 免登录模式（顶栏据此隐藏「退出」，见 AppTopbar.vue） */
    isSkipLogin: computed(() => skipLoginMode.value),
    displayName,
    avatarText,
    isAdmin,
    restore,
    setSession,
    clearSession,
    consumeExpiredNotice,
    handleUnauthorized,
  }
})