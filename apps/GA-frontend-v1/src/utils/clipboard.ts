export async function copyText(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {}

  try {
    const win: any = window as any
    if (win.clipboardData && typeof win.clipboardData.setData === 'function') {
      return win.clipboardData.setData('Text', text)
    }
  } catch {}

  try {
    const span = document.createElement('span')
    span.textContent = text
    span.style.whiteSpace = 'pre'
    span.style.position = 'fixed'
    span.style.left = '-9999px'
    document.body.appendChild(span)
    const range = document.createRange()
    range.selectNodeContents(span)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
    let success = false
    try {
      success = document.execCommand('copy')
    } catch {
      success = false
    }
    selection?.removeAllRanges()
    document.body.removeChild(span)
    if (success) return true
  } catch {}

  try {
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.setAttribute('readonly', 'true')
    textarea.style.position = 'fixed'
    textarea.style.left = '-9999px'
    textarea.style.top = '0'
    document.body.appendChild(textarea)
    textarea.focus()
    textarea.select()
    const success = document.execCommand('copy')
    document.body.removeChild(textarea)
    return !!success
  } catch {
    return false
  }
}