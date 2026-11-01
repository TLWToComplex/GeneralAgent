/* ============================================================================
   .vue 单文件组件的类型声明（Vite 构建也依赖这条通配声明）

   注意：这里**不能**同时写模块增强。
   在一个全局脚本里对某模块做增强后，TypeScript 会把该脚本当成模块，
   之后再出现的同名 `declare module 'vue'` 会从「增强」变成「覆盖声明」，
   导致 `import type { ComponentPublicInstance } from 'vue'` 报
   TS2694「Namespace 'vue' has no exported member」。
   所以 v-html 的补丁放在 src/env.d.ts，增强的是接口的真正声明处
   @vue/runtime-core（vue 只是 export * 转出）。
   ========================================================================== */

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}