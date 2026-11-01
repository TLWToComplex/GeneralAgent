/* ============================================================================
   环境类型补充（纯类型，无任何运行时代码）

   .vue 的通配声明在 src/shims-vue.d.ts，这里补 v-html 的指令类型与环境变量类型。
   ========================================================================== */

/// <reference types="vite/client" />

/*
 * 环境变量类型。
 *
 * 必须写在 declare global 里：vite/client 的 ImportMetaEnv 是「全局脚本」上下文下的
 * 接口声明，而本文件末尾有 `export {}`（是模块），模块内直接写 interface 只会声明一个
 * 模块内类型，顶不到 import.meta.env 上。vite/client 本身带 `[key: string]: any` 索引
 * 签名，所以不声明也能过类型检查（值是 any），这里显式声明是为了拿到 string|undefined
 * 与「改了名字会被检查出来」。
 */
declare global {
  interface ImportMetaEnv {
    /**
     * 后端接口前缀，见 src/constants.ts。
     * 留空（默认）= 同源相对路径：开发走 vite.config.ts 的 server.proxy，
     * 生产由 nginx / 统一入口转发 /captcha 与 /aiUser。
     */
    readonly VITE_API_BASE?: string

    /**
     * 前置代理（proxy/）的基地址，见 src/constants.ts 与 src/lib/dsh.ts。
     * 留空（默认）= 同机不同端口：取当前页面的 host、不带端口（proxy 固定听 80）。
     * 前端与 proxy 不同机器时填完整源，例如 https://dsh.example.com
     */
    readonly VITE_DSH_PROXY_BASE?: string
  }
}

/*
 * 把 v-html 注册成「全局指令」，让模板类型检查认得它。

 * 背景：本项目的卡片 / 表格 / 抽屉 / 提示条内容是沿用原型那把字符串拼装函数
 * （card / kv / regCardsHtml …）生成的，视图层用 v-html 输出，所以有大量 v-html 用法。
 * vue-tsc 检查模板时会把 v-html 解析成 __VLS_directives.vHtml，
 * 而它只查 `GlobalDirectives` 这个接口；Vue 运行时虽然内置了 v-html，
 * 却没有为它补上类型，于是每个 v-html 都会报 TS2339「Property 'vHtml' does not exist」。
 *
 * 接口的真正声明处是 @vue/runtime-core（vue 只是 export * 转出），
 * 增强它即可。运行时用的是 Vue 自带的 v-html，不依赖任何自定义指令实现。
 *
 * 末尾那行 `export {}` 是必须的：没有它，本文件是「全局脚本」，
 * `declare module '@vue/runtime-core'` 会被当成环境模块**声明**而不是增强，
 * 从而顶掉真实的 @vue/runtime-core 包，连带让 vue 的 star-export 链塌掉
 * （满屏 `Module '"vue"' has no exported member 'watch'`）。
 * 加上它就变成模块，声明自动转为模块增强。
 */
declare module '@vue/runtime-core' {
  interface GlobalDirectives {
    /** 写入元素 innerHTML（值已在生成端经过 esc() 转义） */
    vHtml: string
  }
}

export {}