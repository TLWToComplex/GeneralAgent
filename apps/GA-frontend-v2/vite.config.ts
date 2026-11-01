import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

/**
 * 本地联调用的后端地址。
 * 只在 `npm run dev` 时生效；打包产物里不含任何后端地址
 * （前端代码只写相对路径，见 src/constants.ts 的 API_BASE）。
 */
const DEV_BACKEND = process.env.VITE_DEV_BACKEND ?? 'http://127.0.0.1:8038'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    /*
     * 开发期把后端接口前缀转发到后端服务：
     *   · 前端代码里只出现 /captcha、/aiUser 这类相对路径，开发与生产同一套代码；
     *   · 绕开跨域（后端 CORS 是 allow_origins=["*"] + allow_credentials=False，
     *     发 Bearer 头本身够用，但走代理更接近生产形态）。
     *
     * 这里**故意不转发 /internal**：那是给前置代理调的内部接口
     * （GET /internal/dsh/route，需共享密钥），不该让浏览器经 dev server 够到。
     * 需要调它就用 curl 直连后端（见后端 README）。
     */
    proxy: {
      '/captcha': { target: DEV_BACKEND, changeOrigin: true },
      '/aiUser': { target: DEV_BACKEND, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})