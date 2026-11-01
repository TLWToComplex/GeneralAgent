/* ============================================================================
   进入 dsh 控制台（前置代理）的入口

   链路：
     控制台点「新建会话」
       → 新标签页打开 <proxy>/?username=<当前登录用户>
       → proxy 向后端查映射（GET /internal/dsh/route）确认「用户存在 + 已登记 + 未停用」
       → proxy 落一个自己的签名 cookie 并 302 到去掉 username 的同一地址
       → 之后所有请求（含 WebSocket）反代到该用户的 dsh 实例

   为什么要 302：浏览器对子资源（JS/CSS/API）和 WebSocket 不会带父页面的查询串，
   所以 proxy 必须把用户名落成 cookie 才能识别后续请求；顺带也让 dsh 自己看不到这个参数。

   ⚠️ 已知取舍：用户名放在 URL 上**可伪造**（谁都能换成别人的用户名直接进对方实例）。
   这一版按需求先这样。改成一次性票据时，只需要改本文件的 dshConsoleUrl() 与
   proxy/server.js 的 resolveUser()，其余链路不动。
   ========================================================================== */

import { dshUsernameParam, proxyBaseConfig } from '@/config/runtime'

/**
 * 代理基地址：配置优先，否则按「同机不同端口」推导 —— 只取 hostname，
 * 不带端口（proxy 固定听 80）。若页面本身是 https，则推导出 https，
 * 那种情况下 proxy 必须已经在 TLS 后面（或显式配 config.json 的 dshProxyBase）。
 */
export function dshProxyBase(): string {
  const configured = proxyBaseConfig()
  if (configured) return configured.replace(/\/+$/, '')
  if (typeof window === 'undefined') return ''
  const { protocol, hostname } = window.location
  return `${protocol}//${hostname}`
}

/** 该用户进入 dsh 控制台的完整地址 */
export function dshConsoleUrl(username: string): string {
  const base = dshProxyBase()
  return `${base}/?${dshUsernameParam()}=${encodeURIComponent(username)}`
}

/**
 * 新标签页打开 dsh 控制台。
 *
 * 用 window.open（而不是 <a target="_blank">）是为了能判断"是否被拦截"：
 * 被拦时返回 null，可以提示用户手动打开。打开后立刻切断 opener，
 * 避免 dsh 页面通过 window.opener 反向操作控制台（反向 tabnabbing）。
 */
export function openDshConsole(username: string): { ok: boolean; url: string } {
  const url = dshConsoleUrl(username)
  if (typeof window === 'undefined') return { ok: false, url }
  const win = window.open(url, '_blank')
  if (win) {
    try {
      win.opener = null
    } catch {
      /* 跨源时个别浏览器不让写，忽略：noopener 语义已由上面的 window.open 尽力保证 */
    }
  }
  return { ok: win !== null, url }
}