/* ============================================================================
   静态服务器 —— 只为「预览构建产物 / 给无头浏览器喂页面」用，不参与应用本身。

   用法（在 web/ 目录下）：
     npm run serve:dist                 # http://127.0.0.1:4173
     node tools/serve-dist.mjs 4180     # 换端口

   两个注意点：
     1) 带 SPA 回退：找不到的路径一律返回 index.html（hash 路由其实用不到，
        但直接访问 /console/registry 这类路径时有用）。
     2) 一律发 no-store。否则重新构建后浏览器会拿旧的 index.html，
        再去请求已经被删掉的老 hash 资源，看到的是上一版页面 —— 这个坑踩过。
   ========================================================================== */
import { createServer } from 'node:http'
import { readFile, stat } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'

const port = Number(process.argv[2] || 4173)
const root = process.argv[3] || 'dist'

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json; charset=utf-8',
  '.woff2': 'font/woff2',
  '.ico': 'image/x-icon',
}

createServer(async (req, res) => {
  let p = decodeURIComponent((req.url || '/').split('?')[0])
  if (p.includes('..')) {
    res.writeHead(403).end('no')
    return
  }
  let file = join(root, normalize(p))
  try {
    const st = await stat(file)
    if (st.isDirectory()) file = join(file, 'index.html')
  } catch {
    file = join(root, 'index.html') /* SPA 回退 */
  }
  try {
    const body = await readFile(file)
    res.writeHead(200, {
      'content-type': MIME[extname(file)] || 'application/octet-stream',
      'cache-control': 'no-store, no-cache, must-revalidate',
      pragma: 'no-cache',
    })
    res.end(body)
  } catch {
    res.writeHead(404).end('404')
  }
}).listen(port, '127.0.0.1', () => {
  console.log(`serving ${root} at http://127.0.0.1:${port}/`)
})