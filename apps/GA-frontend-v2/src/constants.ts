/* ============================================================================
   全局常量
   ========================================================================== */

/**
 * 登录令牌（后端 JWT）的 localStorage 键名。
 *
 * 为什么放 localStorage 而不是 cookie：后端读的是 ``Authorization: Bearer``，
 * 不用 cookie 就不存在 CSRF 面，也不需要 SameSite 之类的跨域配置。
 * 代价是 XSS 可读 —— 本控制台不渲染用户可控 HTML（所有 v-html 内容都出自代码内的
 * 模板函数并经过 esc()），因此按此权衡落地。
 */
export const TOKEN_KEY = 'GA.token'

/** 登录用户信息（后端登录响应的 user 对象）的 localStorage 键名。 */
export const USER_KEY = 'GA.user'

/* ---------------------------------------------------------------------------
   原先这里还有 API_BASE / DSH_PROXY_BASE / DSH_USERNAME_PARAM / REMEMBER_KEY
   四个常量，值来自 import.meta.env.VITE_*。它们都是**构建期**替换的，所以同一个
   镜像换不了环境（改地址得重新 build），Docker 部署很不方便。

   现在这四项统一走运期配置 public/config/config.json，容器里挂载即可生效，
   读取入口在 src/config/runtime.ts：
     API_BASE            → apiBase()           （函数，加载完成后取值）
     DSH_PROXY_BASE      → proxyBaseConfig()
     DSH_USERNAME_PARAM  → dshUsernameParam()
     REMEMBER_KEY        → rememberKey()

   保留 TOKEN_KEY / USER_KEY 在这里：它们是**存储契约**（键名同时被写入浏览器数据，
   改了等于让所有已登录用户掉线），不是环境相关的部署参数，不适合放进会被随意
   挂载替换的配置文件里。
   --------------------------------------------------------------------------- */