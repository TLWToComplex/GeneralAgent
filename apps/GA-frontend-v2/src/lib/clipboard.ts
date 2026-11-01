/* ============================================================================
   复制到剪贴板

   安装流程里全是「粘到终端 / 粘进配置文件」的命令与片段，所以整页的复制按钮
   都走这里。

   为什么不用 navigator.clipboard 一把梭：
   `navigator.clipboard` 只在**安全上下文**（https 或 localhost）里可用，
   而本控制台在内网里就是 http://172.16.x.x，属于非安全上下文，
   clipboard.writeText 直接是 undefined。所以这里先试标准 API，
   失败回落到「隐藏 textarea + document.execCommand('copy')」的老办法。

   返回值表示是否复制成功，调用方据此给提示（不要静默失败）。
   ========================================================================== */

function legacyCopy(text: string): boolean {
  if (typeof document === 'undefined') return false
  const ta = document.createElement('textarea')
  ta.value = text
  /* 放在视口内但不可见：display:none / visibility:hidden 会让 execCommand 失效 */
  ta.setAttribute('readonly', 'readonly')
  ta.style.position = 'fixed'
  ta.style.top = '0'
  ta.style.left = '0'
  ta.style.width = '1px'
  ta.style.height = '1px'
  document.body.appendChild(ta)
  ta.select()
  ta.setSelectionRange(0, ta.value.length)
  let ok = false
  try {
    ok = document.execCommand('copy')
  } catch {
    ok = false
  }
  document.body.removeChild(ta)
  return ok
}

export async function copyText(text: string): Promise<boolean> {
  const clip = navigator.clipboard
  if (clip && typeof clip.writeText === 'function') {
    try {
      await clip.writeText(text)
      return true
    } catch {
      /* 非安全上下文 / 权限被拒：往下走老办法 */
    }
  }
  return legacyCopy(text)
}