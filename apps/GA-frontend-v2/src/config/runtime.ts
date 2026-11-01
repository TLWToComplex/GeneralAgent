/* ============================================================================
   运期配置 —— 从 public/config/config.json 读取

   为什么要这么做（而不是继续用 import.meta.env）：
     Vite 的 import.meta.env.VITE_* 是**构建期替换**的 —— 值会被直接内联进打包后的
     JS。后果是同一个镜像换不了环境：改后端地址或 proxy 地址就得重新 build。
     Docker 部署里这很别扭：镜像本该一份走多个环境，配置应该在启动/挂载时给。

     所以改成运期读取：config.json 是 public/ 下的静态文件，构建时原样拷进 dist/。
     容器里把它挂进来即可，**不需要重建镜像**：
       docker run -v /opt/GA/config.json:/usr/share/nginx/html/config/config.json ...
     改完刷新页面生效（没有构建、没有重启容器）。

   加载时机：必须在 router 挂载**之前** await 完（见 main.ts）。
     否则首次请求（例如路由守卫里的 /aiUser/me 或登录页拉验证码）会先带着默认值发出去，
     等配置回来时请求已经发错了 —— 表现出来就是"刷新页面偶尔连不上后端"。

   设计取舍：
     · **失败不阻塞。** 拉不到 config.json（404 / 网络错 / JSON 语法错）就用内置默认值
       继续启动，并在控制台说明原因。宁可跑默认值也不能白屏 —— 前端拉不到配置时
       后端往往也在抖，这时候给整页报错反而更糟。
     · **只用 JSON，不用 JS。** proxy/ 那边的 config.js 是 CommonJS 模块（能写注释、
       算表达式），那是给 node 读的；前端这份要能被任意 nginx 直接当静态文件吐出来，
       所以用纯 JSON。代价是写不了注释 —— 字段说明都放在本文件与 README 里。
     · **默认值只在本文件。** public/config/config.json 里那份是给运维抄的起点，
       代码不读它以外的任何来源；两边不一致时以挂在容器里那份为准。
     · 仍然保留 VITE_API_BASE / VITE_DSH_PROXY_BASE 作为兜底：老部署没挂 config.json
       时行为与改动前完全一致，不会因为这次改动把线上打挂。
     · **免登录开关也是运期配置。** 内网演示 / 联调时不想每次输账号，把 config.json 的
       `skipLogin` 改成 true、刷新页面即可 —— 与「一个镜像走多环境」是同一个诉求：
       「要不要登录」属于部署形态，不该在构建期写死。默认 false（与改动前行为一致）。
       ⚠️ 它只跳过**前端登录页**，不等于后端放行：接口该 401 还是 401
       （免登录模式下不发送令牌，因此 401 不会把人踢回登录页，页面按接口报错处理）。
   ========================================================================== */

/** config.json 的形状。所有字段可省略，省略即用默认值。 */
export interface RuntimeConfig {
  /** 后端接口前缀。空 = 同源相对路径（走 nginx 或 vite dev proxy 转发） */
  apiBase: string
  /** 前置代理（proxy/）基地址。空 = 按当前页面 host 推导，不带端口 */
  dshProxyBase: string
  /** 进 dsh 控制台时携带用户名的查询参数名。**必须与 proxy/server.js 一致** */
  dshUsernameParam: string
  /** 「记住账号」的 localStorage 键名。登录页与退出登录共用，必须一致 */
  loginRememberKey: string
  /** 免登录开关：true = 不弹登录页，直接进控制台。默认 false（与改动前一致） */
  skipLogin: boolean
  /** 免登录模式下的用户名：顶栏展示名 + 进 dsh 控制台带的 username。空 = guest */
  skipLoginUser: string
}

/** 配置文件位置（相对站点根）。放进 public/config/，构建后是 dist/config/ */
const CONFIG_URL = 'config/config.json'

/** 网络/解析失败的等待上限。配置就在本机，超过这个时间基本可以断定是拿不到了 */
const TIMEOUT_MS = 5000

/** 免登录模式没配用户名时的兜底（顶栏展示 + dsh 控制台 username） */
const DEFAULT_SKIP_LOGIN_USER = 'guest'

/**
 * 内置默认值。有意与改动前的行为一致：
 *   · apiBase 空 → 同源相对路径；
 *   · dshProxyBase 空 → 同机不同端口（取 host 不带端口）。
 * 同时把老的 VITE_* 环境变量当兜底，保证没挂 config.json 的老部署行为不变。
 */
function defaults(): RuntimeConfig {
  const env = (import.meta.env ?? {}) as Record<string, string | undefined>
  return {
    apiBase: env.VITE_API_BASE ?? '',
    dshProxyBase: env.VITE_DSH_PROXY_BASE ?? '',
    dshUsernameParam: 'username',
    loginRememberKey: 'aiPlatform.lastUser',
    skipLogin: false,
    skipLoginUser: '',
  }
}

/** 归一化：非字符串/空白一律退回默认值，并去掉尾部斜杠 */
function pick(raw: unknown, fallback: string): string {
  if (typeof raw !== 'string') return fallback
  const t = raw.trim()
  return t || fallback
}

/**
 * 布尔开关的容错解析。
 * config.json 是手写的：写成真布尔最好，写成 "true" / "1" / "yes" / "on" 也认；
 * 认不出来（缺字段、写错、null）就用默认值 —— 开关类配置**不能因为写错就变成开启**。
 */
function flag(raw: unknown, fallback: boolean): boolean {
  if (typeof raw === 'boolean') return raw
  if (typeof raw === 'number') return raw !== 0
  if (typeof raw === 'string') {
    const t = raw.trim().toLowerCase()
    if (['true', '1', 'yes', 'on', '是', '开'].includes(t)) return true
    if (['false', '0', 'no', 'off', '否', '关'].includes(t)) return false
  }
  return fallback
}

let current: RuntimeConfig = defaults()

/** 读当前配置。任何地方要用配置都走这个函数 —— 不要缓存到模块顶层变量，
    否则加载完成后拿到的还是默认值。 */
export function runtimeConfig(): RuntimeConfig {
  return current
}

/* 下面这几个是给调用方用的便捷读取函数。
   刻意保持与改动前 constants.ts 里的**同名**（只是从常量变成函数），
   这样 diff 只体现"多了一对括号"，review 时一眼能看出语义没变。 */

/** 后端接口前缀。空 = 同源相对路径 */
export function apiBase(): string {
  return current.apiBase.trim()
}

/** 前置代理基地址。空 = 由 dshProxyBase() 按当前页面 host 推导 */
export function proxyBaseConfig(): string {
  return current.dshProxyBase.trim()
}

/** 进 dsh 控制台携带用户名的查询参数名 */
export function dshUsernameParam(): string {
  return current.dshUsernameParam
}

/** 「记住账号」的 localStorage 键名 */
export function rememberKey(): string {
  return current.loginRememberKey
}

/**
 * 免登录开关。true = 不弹登录页，直接以 `skipLoginUser()` 的身份进控制台。
 *
 * 读取时机：只在启动时（stores/auth.ts 的 restore()）读一次 —— 与其他运期配置一样
 * 「改完 config.json 刷新页面生效」，不做运行中热切换。
 */
export function skipLogin(): boolean {
  return current.skipLogin
}

/** 免登录模式下的用户名（空则返回 guest）。顶栏展示与 dsh 控制台 username 都用它 */
export function skipLoginUser(): string {
  return current.skipLoginUser.trim() || DEFAULT_SKIP_LOGIN_USER
}

/** 是否已经成功读到 config.json（诊断/测试用） */
export let runtimeConfigLoaded = false

/** 拉取失败的原因，成功后为 null（诊断用） */
export let runtimeConfigError: string | null = null

/**
 * 加载 config.json。**必须在 app.mount() 之前 await**。
 * 永不抛错：任何失败都退回默认值，只在控制台说明。
 */
export async function loadRuntimeConfig(): Promise<RuntimeConfig> {
  const base = defaults()
  try {
    const ctl = typeof AbortController !== 'undefined' ? new AbortController() : null
    const timer = ctl ? setTimeout(() => ctl.abort(), TIMEOUT_MS) : null
    let res: Response
    try {
      /* no-store + 时间戳：改完配置刷新页面就要生效，不能被中间层缓存住 */
      res = await fetch(`${CONFIG_URL}?t=${Date.now()}`, {
        cache: 'no-store',
        signal: ctl ? ctl.signal : undefined,
      })
    } finally {
      if (timer) clearTimeout(timer)
    }

    if (!res.ok) {
      /* 404 是**预期**情况：没挂 config.json 就用默认值，不当错误刷屏 */
      runtimeConfigError = res.status === 404 ? `未提供 ${CONFIG_URL}（用默认值）` : `HTTP ${res.status}`
      current = base
      return current
    }

    const raw = (await res.json()) as Record<string, unknown>
    current = {
      apiBase: pick(raw.apiBase, base.apiBase),
      dshProxyBase: pick(raw.dshProxyBase, base.dshProxyBase),
      dshUsernameParam: pick(raw.dshUsernameParam, base.dshUsernameParam),
      loginRememberKey: pick(raw.loginRememberKey, base.loginRememberKey),
      skipLogin: flag(raw.skipLogin, base.skipLogin),
      skipLoginUser: pick(raw.skipLoginUser, base.skipLoginUser),
    }
    runtimeConfigLoaded = true
    runtimeConfigError = null
    return current
  } catch (err) {
    /* 拉不到就退回默认值，绝不阻塞启动。原因留在这里供排查。 */
    runtimeConfigError = err instanceof Error ? err.message : String(err)
    current = base
    return current
  }
}