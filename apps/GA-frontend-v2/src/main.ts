/* ============================================================================
   应用入口 —— 替代原型「每页一个 html + 一个 js」的加载方式。

   原型是两个独立静态页：index.html（登录）+ console.html（控制台），
   各自引自己的 CSS 与脚本。Vue 里合成一个 SPA：
     · 登录页 → /login
     · 控制台 → /console/*（七个页面挂在同一个外壳下）
   全局样式在 App.vue 里按路由挂载，避免把 console.css 的规则带到登录页。
   ========================================================================== */

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import { router } from './router'
import { useAuthStore } from './stores/auth'
import { loadRuntimeConfig, runtimeConfig, runtimeConfigError, runtimeConfigLoaded, skipLogin, skipLoginUser } from './config/runtime'

/*
 * 启动顺序上有一件必须保证的事：**运期配置要先于路由挂载加载完**。
 *
 * 原因：配置里有后端地址与 proxy 地址，而路由守卫会立刻向后端发 /aiUser/me、
 * 登录页会立刻拉验证码。若配置还没回来，这些请求就带着默认地址发出去 ——
 * 症状是"刷新页面偶尔连不上后端"，且很难复现。
 *
 * 为什么用 .then() 而不是更直观的顶层 await：
 *   顶层 await 会把入口变成 async module，而本项目 build.target 是
 *   chrome87/edge88/es2020/firefox78/safari14，**不支持**顶层 await
 *   （实测报错：Top-level await is not available in the configured target environment）。
 *   为一个 5KB 的配置读取把浏览器基线抬到 chrome89/safari15 不划算，
 *   所以改成 promise 链 —— 顺序保证一模一样，兼容性不变。
 *
 * loadRuntimeConfig() 自身**永不抛错**（拉不到就退回默认值），所以 .finally 必然执行；
 * 但仍显式兜一层 catch，避免"配置模块将来某次改动引入 reject → 整页白屏"。
 */
loadRuntimeConfig()
  .then(reportConfig)
  .catch((err: unknown) => {
    console.error('[GA] 运期配置加载出现意外异常，按默认值启动：', err)
  })
  .finally(bootstrap)

/** 启动诊断：只说明情况，绝不阻断启动 */
function reportConfig(): void {
  if (!runtimeConfigLoaded) {
    console.warn(
      `[GA] 运期配置未生效，使用默认值启动：${runtimeConfigError ?? '未知原因'}。` +
        '如需指定后端/代理地址，请挂载 config/config.json。',
    )
  }
  /*
   * 免登录开关：默认关。开了就在控制台留一条显式日志 —— 页面表现是"没有登录页"，
   * 光看界面容易误以为是坏了/被改过，日志能把原因和身份来源说清楚。
   */
  if (skipLogin()) {
    console.warn(
      `[GA] 免登录模式已开启（config/config.json 的 skipLogin=true）：跳过登录页，` +
        `以「${skipLoginUser()}」的身份进入控制台，接口不携带令牌（建议仅内网演示/联调使用）。`,
    )
  }
  if (import.meta.env.DEV) {
    console.info('[GA] 运期配置 =', runtimeConfig())
  }
}

function bootstrap(): void {
  const pinia = createPinia()
  const app = createApp(App).use(pinia)

  /*
   * 登录态必须在路由挂载前恢复：
   *   · 路由守卫要据此判定 /console/* 是否放行（刷新深链时尤其关键）；
   *   · 同时把「取令牌 / 401 处理」注册进 HTTP 层（见 stores/auth.ts）。
   * 这里显式传入 pinia 实例，不依赖"当前活动 pinia"这一隐式状态。
   */
  useAuthStore(pinia).restore()

  app.use(router).mount('#app')
}