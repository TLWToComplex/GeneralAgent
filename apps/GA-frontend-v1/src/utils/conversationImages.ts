import type { Message } from '@/types/mcp';

export interface ConversationImageItem {
  key: string;
  url: string;
  alt: string;
  name: string;
  source: 'file' | 'markdown' | 'html' | 'input';
  messageIndex: number;
  messageId: string;
  role: Message['role'];
}

const IMAGE_FILE_RE = /\.(png|jpe?g|gif|webp|bmp|svg|avif)$/i;

/** 图片扩展名列表（用于URL提取） */
const IMAGE_EXTENSIONS = 'png|jpe?g|gif|webp|bmp';
/** 匹配URL末尾的图片扩展名 */
const IMAGE_EXT_URL_RE = new RegExp(`\\.(?:${IMAGE_EXTENSIONS})(?:$|[?#])`, 'i');

export function isImageFile(file: any): boolean {
  // 历史图片问答记录只有图片链接，用显式标记兜底识别
  if (file?.isFileImage === true) return true;
  const name = String(file?.name || '').toLowerCase();
  const type = String(file?.type || '').toLowerCase();
  return type.startsWith('image/') || IMAGE_FILE_RE.test(name);
}

export function getImagePreviewUrl(file: any): string {
  return String(
    file?.imagePreviewUrl ||
    file?.imageDataUrl ||
    file?.dataUrl ||
    file?.previewUrl ||
    file?.url ||
    ''
  ).trim();
}

function getMessageIdentity(message: Message, index: number): string {
  return String(message.uiKey || message.id || `message-${index}`);
}

function normalizeImageUrl(rawUrl: string): string {
  const trimmed = String(rawUrl || '').trim();
  if (!trimmed) return '';
  const unwrapped = trimmed.startsWith('<') && trimmed.endsWith('>')
    ? trimmed.slice(1, -1).trim()
    : trimmed;

  if (!unwrapped || /^javascript:/i.test(unwrapped)) {
    return '';
  }

  return unwrapped;
}

function extractInlineImagesFromText(
  content: string,
  message: Message,
  messageIndex: number
): ConversationImageItem[] {
  if (!content || !content.trim()) return [];

  const messageId = getMessageIdentity(message, messageIndex);
  const images: ConversationImageItem[] = [];
  const seen = new Set<string>();

  const pushImage = (source: ConversationImageItem['source'], rawUrl: string, rawAlt: string, index: number) => {
    const url = normalizeImageUrl(rawUrl);
    if (!url) return;

    const alt = String(rawAlt || '').trim() || '图片';
    const dedupeKey = `${source}:${url}:${alt}`;
    if (seen.has(dedupeKey)) return;
    seen.add(dedupeKey);

    images.push({
      key: `${messageId}-${source}-${index}`,
      url,
      alt,
      name: alt,
      source,
      messageIndex,
      messageId,
      role: message.role
    });
  };

  const markdownImageRe = /!\[([^\]]*)\]\(\s*(<[^>]+>|[^)\s]+)(?:\s+["'][^"']*["'])?\s*\)/g;
  let markdownIndex = 0;
  let markdownMatch: RegExpExecArray | null;
  while ((markdownMatch = markdownImageRe.exec(content)) !== null) {
    pushImage('markdown', markdownMatch[2], markdownMatch[1], markdownIndex++);
  }

  const htmlImageRe = /<img\b[^>]*\bsrc=(['"])(.*?)\1[^>]*>/gi;
  let htmlIndex = 0;
  let htmlMatch: RegExpExecArray | null;
  while ((htmlMatch = htmlImageRe.exec(content)) !== null) {
    const tag = htmlMatch[0];
    const altMatch = tag.match(/\balt=(['"])(.*?)\1/i);
    pushImage('html', htmlMatch[2], altMatch?.[2] || '图片', htmlIndex++);
  }

  // 提取 Markdown 链接中的图片 URL: [text](http://.../image.ext)
  const mdLinkImageRe = new RegExp(
    `\\[([^\\]\\n]*?)\\]\\(\\s*(https?://[^)\\s]+?\\.(?:${IMAGE_EXTENSIONS})(?:\\?[^)\\s]*?)?)\\s*\\)`,
    'gi'
  );
  let mdLinkIndex = 0;
  let mdLinkMatch: RegExpExecArray | null;
  while ((mdLinkMatch = mdLinkImageRe.exec(content)) !== null) {
    const url = mdLinkMatch[2];
    // 跳过已经被 ![]() 语法捕获的 URL（markdownImageRe 已处理）
    const prevChar = content.charAt(mdLinkMatch.index - 1);
    if (prevChar === '!') continue;
    if (!IMAGE_EXT_URL_RE.test(url)) continue;
    pushImage('markdown', url, mdLinkMatch[1], mdLinkIndex++);
  }

  // 提取 HTML <a> 标签中的图片 URL: <a href="http://.../image.ext">text</a>
  const aTagImageRe = new RegExp(
    `<a\\s[^>]*href=["']((?:https?://)[^"']+?\\.(?:${IMAGE_EXTENSIONS})(?:\\?[^"']*?)?)["'][^>]*>([\\s\\S]*?)<\\/a>`,
    'gi'
  );
  let aTagIndex = 0;
  let aTagMatch: RegExpExecArray | null;
  while ((aTagMatch = aTagImageRe.exec(content)) !== null) {
    const url = aTagMatch[1];
    const alt = aTagMatch[2].replace(/<[^>]*>/g, '').trim();
    if (!IMAGE_EXT_URL_RE.test(url)) continue;
    pushImage('html', url, alt || '图片', aTagIndex++);
  }

  // 提取裸图片 URL 或被反引号/粗体标记包裹的图片 URL
  const bareImageUrlRe = new RegExp(
    `(?:^|\\s|[\`\\*])(https?://[^\\s<>"')\\]]+?\\.(?:${IMAGE_EXTENSIONS})(?:\\?[^\\s<>"')\\]]*?)?)(?=[\\s.,;:!?\`\\*\\)]|$)`,
    'gim'
  );
  let bareIndex = 0;
  let bareMatch: RegExpExecArray | null;
  while ((bareMatch = bareImageUrlRe.exec(content)) !== null) {
    const url = bareMatch[1];
    if (!IMAGE_EXT_URL_RE.test(url)) continue;
    const filename = url.split('/').pop()?.split('?')[0] || '图片';
    pushImage('markdown', url, filename, bareIndex++);
  }

  return images;
}

export function extractImagesFromMessage(message: Message, messageIndex: number): ConversationImageItem[] {
  const messageId = getMessageIdentity(message, messageIndex);
  const images: ConversationImageItem[] = [];

  const files = Array.isArray(message.files) ? message.files : [];
  files.forEach((file, fileIndex) => {
    if (!isImageFile(file)) return;

    const url = getImagePreviewUrl(file);
    if (!url) return;

    const name = String(file?.name || '').trim() || '图片';
    images.push({
      key: `${messageId}-file-${fileIndex}`,
      url,
      alt: name,
      name,
      source: 'file',
      messageIndex,
      messageId,
      role: message.role
    });
  });

  const textBlocks = [message.display_content, message.content, message.reasoning_content]
    .map(item => String(item || '').trim())
    .filter(Boolean);

  const uniqueTextBlocks = Array.from(new Set(textBlocks));
  uniqueTextBlocks.forEach((block) => {
    images.push(...extractInlineImagesFromText(block, message, messageIndex));
  });

  return images;
}

export function extractImagesFromMessages(messages: Message[]): ConversationImageItem[] {
  if (!Array.isArray(messages) || messages.length === 0) return [];
  return messages.flatMap((message, index) => extractImagesFromMessage(message, index));
}

export function mergeViewerImages(
  conversationImages: ConversationImageItem[],
  inputImages: ConversationImageItem[]
): ConversationImageItem[] {
  const merged: ConversationImageItem[] = [];
  const seen = new Set<string>();

  [...conversationImages, ...inputImages].forEach((image, index) => {
    const url = normalizeImageUrl(image?.url || '');
    if (!url) return;

    const alt = String(image?.alt || image?.name || '图片').trim() || '图片';
    const dedupeKey = `${image?.source || 'file'}:${url}:${alt}`;
    if (seen.has(dedupeKey)) return;
    seen.add(dedupeKey);

    merged.push({
      key: image?.key || `${image?.source || 'merged'}-${index}`,
      url,
      alt,
      name: String(image?.name || alt).trim() || alt,
      source: image?.source || 'file',
      messageIndex: image?.messageIndex ?? -1,
      messageId: image?.messageId || 'viewer-merged',
      role: image?.role || 'user'
    });
  });

  return merged;
}
