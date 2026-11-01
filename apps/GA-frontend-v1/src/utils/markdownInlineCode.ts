function escapeBacktickRun(length: number): string {
  return Array.from({ length }, () => '\\`').join('')
}

function findClosingBacktickRun(line: string, start: number, run: string): number {
  let searchIndex = start
  while (searchIndex < line.length) {
    const foundIndex = line.indexOf(run, searchIndex)
    if (foundIndex === -1) {
      return -1
    }

    const prevChar = foundIndex > 0 ? line[foundIndex - 1] : ''
    const nextChar = foundIndex + run.length < line.length ? line[foundIndex + run.length] : ''

    if (prevChar !== '`' && nextChar !== '`') {
      return foundIndex
    }

    searchIndex = foundIndex + 1
  }

  return -1
}

function sanitizeInlineCodeOutsideFences(segment: string): string {
  return segment
    .split('\n')
    .map((line) => {
      let result = ''
      let index = 0

      while (index < line.length) {
        if (line[index] !== '`') {
          result += line[index]
          index += 1
          continue
        }

        let runLength = 1
        while (index + runLength < line.length && line[index + runLength] === '`') {
          runLength += 1
        }

        const run = '`'.repeat(runLength)
        const contentStart = index + runLength
        const closingIndex = findClosingBacktickRun(line, contentStart, run)

        if (closingIndex === -1) {
          result += escapeBacktickRun(runLength)
          index += runLength
          continue
        }

        result += line.slice(index, closingIndex + runLength)
        index = closingIndex + runLength
      }

      return result
    })
    .join('\n')
}

export function sanitizeMarkdownInlineCode(content: string): string {
  if (!content || !content.includes('`')) {
    return content
  }

  const fencePattern = /(```[\s\S]*?```|~~~[\s\S]*?~~~)/g
  const segments = content.split(fencePattern)

  return segments
    .map((segment) => {
      if (!segment) {
        return segment
      }

      if (/^(```|~~~)/.test(segment)) {
        return segment
      }

      return sanitizeInlineCodeOutsideFences(segment)
    })
    .join('')
}
