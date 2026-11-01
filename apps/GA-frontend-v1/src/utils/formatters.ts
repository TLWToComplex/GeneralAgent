export type DateLike = Date | string | number | null | undefined

const INVALID_DATE_TEXT = new Set(['', 'null', 'undefined', 'invalid date', 'nan'])

export const parseDate = (date: DateLike): Date | null => {
  if (date == null) return null

  if (date instanceof Date) {
    return Number.isNaN(date.getTime()) ? null : new Date(date.getTime())
  }

  if (typeof date === 'string') {
    const trimmed = date.trim()
    if (INVALID_DATE_TEXT.has(trimmed.toLowerCase())) return null
    const normalized = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(trimmed)
      ? trimmed.replace(' ', 'T')
      : trimmed
    const parsed = new Date(normalized)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  const parsed = new Date(date)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export const toTimestamp = (date: DateLike): number => {
  const parsed = parseDate(date)
  return parsed ? parsed.getTime() : 0
}

export const formatDate = (date: DateLike): string => {
  const parsed = parseDate(date)
  if (!parsed) return '--'
  const d = new Date(parsed.getTime())
  d.setHours(d.getHours() + 8)
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  }).format(d)
}

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}
