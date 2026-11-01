import type { Message } from '@/types/mcp';

const MAX_HISTORY_CHARS = 16000;
const MAX_FILE_CHARS = 6000;
const MESSAGE_SNIPPET_LIMIT = 320;
const MAX_LOCAL_BULLETS = 8;

function normalizeText(text: string): string {
  return text.replace(/\s+/g, ' ').trim();
}

function truncateText(text: string, limit: number): string {
  const normalized = normalizeText(text);
  if (normalized.length <= limit) return normalized;
  return `${normalized.slice(0, Math.max(0, limit - 1))}...`;
}

function describeMessage(message: Message): string {
  const roleLabel = message.role === 'user'
    ? '用户'
    : message.role === 'assistant'
      ? '助手'
      : message.role === 'tool'
        ? '工具'
        : '系统';

  const contentParts: string[] = [];
  if (message.display_content) {
    contentParts.push(String(message.display_content));
  } else if (message.content) {
    contentParts.push(String(message.content));
  }

  if (message.reasoning_content) {
    contentParts.push(`思考: ${message.reasoning_content}`);
  }

  if (Array.isArray(message.tool_calls) && message.tool_calls.length > 0) {
    const toolNames = message.tool_calls
      .map((call) => call?.function?.name)
      .filter(Boolean)
      .join(', ');
    if (toolNames) {
      contentParts.push(`调用工具: ${toolNames}`);
    }
  }

  if (message.role === 'tool' && message.tool_call_id) {
    contentParts.push(`tool_call_id: ${message.tool_call_id}`);
  }

  return `${roleLabel}: ${truncateText(contentParts.join(' | '), MESSAGE_SNIPPET_LIMIT)}`;
}

export function buildCompressionInput(
  messages: Message[],
  fileContexts: Array<{ filename: string; content: string }>
): string {
  const historyLines: string[] = [];
  let historyChars = 0;

  for (const message of messages) {
    const line = describeMessage(message);
    if (!line) continue;
    const nextLength = historyChars + line.length + 1;
    if (nextLength > MAX_HISTORY_CHARS) break;
    historyLines.push(line);
    historyChars = nextLength;
  }

  const fileLines: string[] = [];
  let fileChars = 0;
  for (const file of fileContexts) {
    const excerpt = truncateText(file.content || '', 800);
    const line = `文档 ${file.filename}: ${excerpt}`;
    const nextLength = fileChars + line.length + 1;
    if (nextLength > MAX_FILE_CHARS) break;
    fileLines.push(line);
    fileChars = nextLength;
  }

  const sections: string[] = [];
  if (historyLines.length > 0) {
    sections.push('以下是需要压缩的历史对话：');
    sections.push(historyLines.join('\n'));
  }
  if (fileLines.length > 0) {
    sections.push('以下是会话中已注入的文档内容摘录：');
    sections.push(fileLines.join('\n'));
  }

  return sections.join('\n\n');
}

export function buildLocalCompressionSummary(
  messages: Message[],
  fileContexts: Array<{ filename: string; content: string }>
): string {
  const bullets = messages
    .filter((message) => message.role !== 'system')
    .slice(0, MAX_LOCAL_BULLETS)
    .map((message) => `- ${describeMessage(message)}`);

  const fileBullets = fileContexts
    .slice(0, 3)
    .map((file) => `- 文档 ${file.filename}: ${truncateText(file.content || '', 180)}`);

  const sections: string[] = [
    '以下为已压缩的历史上下文，请在后续对话中延续这些信息：'
  ];

  if (bullets.length > 0) {
    sections.push('对话摘要：');
    sections.push(bullets.join('\n'));
  }

  if (fileBullets.length > 0) {
    sections.push('文档摘要：');
    sections.push(fileBullets.join('\n'));
  }

  sections.push('请继续沿用上述目标、事实和约束回答后续问题。');
  return sections.join('\n');
}
