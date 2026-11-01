/* ============================================================================
   Node 直接 import .vue —— 让没有浏览器的环境也能把页面渲染成真实 DOM
   （服务端渲染出来，用来核对结构 / 分类名 / 文案，无法替代像素级肉眼检查）

   用法（必须在 web/ 目录下执行）：
     node --experimental-strip-types --import ./tools/vue-loader.mjs tools/xxx.mjs

   在你的脚本里就可以：
     const { default: View } = await import('../src/views/registry/RegistryView.vue')
     const app = createSSRApp(View)
     app.use(createPinia())
     console.log(await renderToString(app))     // 真实 DOM

   三个必须点（都踩过坑）：
     1) 必须用 module.registerHooks。自己 export resolve/load 的方式在
        Node 24 的 --import 场景下不生效。
     2) compileScript 的 format 必须是 module-typescript，
        否则 --experimental-strip-types 不会剥掉类型注解。
     3) inlineTemplate + ssr：模板编进 script 里，直接 renderToString 就能出 DOM。
   ========================================================================== */
import module from 'node:module'
import { pathToFileURL, fileURLToPath } from 'node:url'
import { existsSync, readFileSync } from 'node:fs'
import { resolve as presolve } from 'node:path'
import { parse, compileScript } from 'vue/compiler-sfc'

const SRC = pathToFileURL(presolve('src') + '/').href

module.registerHooks({
  resolve(specifier, context, next) {
    /* @/foo → src/foo（Node 不认识 Vite 的别名） */
    if (specifier.startsWith('@/')) {
      let url = SRC + specifier.slice(2)
      if (!existsSync(new URL(url))) url += '.ts'
      return { url, shortCircuit: true }
    }
    /* 省略扩展名的相对导入补齐 .ts / .vue / /index.ts */
    if (specifier.startsWith('.') && context.parentURL) {
      const base = new URL(specifier, context.parentURL)
      if (!existsSync(fileURLToPath(base))) {
        for (const ext of ['.ts', '.vue', '/index.ts']) {
          const cand = new URL(base.href + ext)
          if (existsSync(fileURLToPath(cand))) return { url: cand.href, shortCircuit: true }
        }
      }
    }
    return next(specifier, context)
  },

  load(url, context, next) {
    if (!url.includes('.vue')) return next(url, context)
    const filename = fileURLToPath(url)
    const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
    const id = filename.replace(/[^\w]/g, '_')
    const script = compileScript(descriptor, { id, inlineTemplate: true, ssr: true })
    return { format: 'module-typescript', source: script.content, shortCircuit: true }
  },
})