export interface Artifact {
  id: string;
  type: string;
  title: string;
  content: string | ArrayBuffer | any;
  isComplete: boolean;
  isInThinking?: boolean;
  url?: string;
  downloadUrl?: string;
  startIndex?: number;
  endIndex?: number;
}

export type TextArtifact = Omit<Artifact, 'content'> & { content: string };

/** 自动预览只接受助手正文，工具原始输出和思考内容不是交付产物。 */
export const parseAutoOpenArtifacts = (content: string, msgId: string, role: string): TextArtifact[] => {
  if (role !== 'assistant') return [];
  return parseArtifactsFromContent(content, msgId).filter(artifact => !artifact.isInThinking);
};

/** 与聊天气泡一致：最后一个思考/工具块之后才是回答。流式期间同样按此截取，保证代码能边生成边预览。 */
export const getCanvasAnswerContent = (message: {
  role: string;
  content?: unknown;
  orchestratorBlocks?: Array<{ type: string; content?: string; toolCallIds?: string[] }>;
}): string => {
  if (message.role !== 'assistant') return '';
  const blocks = message.orchestratorBlocks?.filter(block =>
    block.type === 'tools' ? !!block.toolCallIds?.length : !!block.content);
  if (!blocks?.length) return typeof message.content === 'string' ? message.content : '';
  let answerStart = blocks.length;
  while (answerStart > 0 && blocks[answerStart - 1].type === 'content') answerStart--;
  return blocks.slice(answerStart).map(block => block.content || '').join('\n\n');
};

const FILE_NAME_QUERY_KEYS = ['file_path', 'filepath', 'filename', 'name', 'path'];

/**
 * 从链接/URL 中提取文件名。
 * 优先读取查询参数中携带的文件名（如 /download?file_path=xxx.docx），
 * 否则回退到路径最后一段。
 */
export const extractFileNameFromSource = (value: string): string => {
  if (!value) return '';
  const queryIndex = value.search(/[?#]/);
  if (queryIndex >= 0) {
    const query = value.slice(queryIndex + 1).split(/[?#]/)[0];
    try {
      const params = new URLSearchParams(query);
      for (const key of FILE_NAME_QUERY_KEYS) {
        const raw = params.get(key);
        if (!raw) continue;
        // URLSearchParams 已做一次解码，这里只需取路径最后一段
        const segment = raw.split(/[\\/]/).filter(Boolean).pop();
        if (segment) return segment;
      }
    } catch {
      // 查询串异常时忽略，回退到路径解析
    }
  }
  const base = value.split('?')[0].split('#')[0];
  const segment = base.split('/').filter(Boolean).pop() || '';
  if (!segment) return '';
  try {
    return decodeURIComponent(segment);
  } catch {
    return segment;
  }
};

export const parseArtifactsFromContent = (content: string, msgId: string): TextArtifact[] => {
  // 仅针对 map fence 做字面量 \n 还原，避免误改普通消息、代码片段和 JSON 文本。
  if (content.includes('\\n```map') && !content.includes('\n')) {
    content = content
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\\\/g, '\\');
  }

  if (content.includes('\\n```map') && content.includes('\n')) {
    content = content
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\\\/g, '\\');
  }

  const artifacts: TextArtifact[] = [];
  const deriveFileTitle = (value: string, extension: string) => {
    if (!value) return '';
    const name = extractFileNameFromSource(value);
    if (!name) return '';
    const extRegex = new RegExp(`\\.${extension}$`, 'i');
    return name.replace(extRegex, '');
  };

  // 链接文本与 URL 中优先取带目标扩展名的那一侧作为文件名
  const pickFileTitle = (url: string, linkText: string, extension: string, defaultTitle: string) => {
    const extRegex = new RegExp(`\\.${extension}$`, 'i');
    const urlName = extractFileNameFromSource(url);
    const textName = extractFileNameFromSource(linkText);
    const preferred = extRegex.test(urlName)
      ? urlName
      : extRegex.test(textName)
        ? textName
        : urlName || textName;
    return preferred ? preferred.replace(extRegex, '') : defaultTitle;
  };

  // Identify think ranges
  const thinkRanges: [number, number][] = [];
  const thinkRegex = /<think>([\s\S]*?)(?:<\/think>|$)/g;
  let match;
  while ((match = thinkRegex.exec(content)) !== null) {
    thinkRanges.push([match.index, match.index + match[0].length]);
  }

  // Use a stack-based approach to handle nested code blocks (especially for Markdown)
  // Matches: Start of line (or string), 3+ backticks, optional lang, newline (or end)
  const fenceRegex = /(?:^|\n)(`{3,})([^\n]*)(?:\n|$)/g;
  
  let fenceMatch;
  let currentArtifact: Partial<TextArtifact> | null = null;
  let stack: string[] = []; // Stores the fence strings (e.g. "```")
  let contentStart = 0;
  let artifactCount = 0;
  let artifactStartIndex = 0;
  const fenceRanges: [number, number][] = [];
  let topLevelFenceStartIndex: number | null = null;

  while ((fenceMatch = fenceRegex.exec(content)) !== null) {
    const fullMatch = fenceMatch[0];
    const fence = fenceMatch[1];
    const rawLang = fenceMatch[2] || '';
    const lang = rawLang.trim();
    const matchIndex = fenceMatch.index;
    
    // Calculate where the content would start if this is an opening fence
    // We need to account for the leading newline if captured
    const prefixNewline = fullMatch.startsWith('\n');
    const absoluteStartIndex = matchIndex + (prefixNewline ? 1 : 0);
    
    // Determine if this is an Opening or Closing fence
    // A fence with empty lang is a closing fence if we are inside a block, 
    // OR a generic code block start if we are at top level (depth 0).
    // We prioritize closing behavior if depth > 0.
    
    if (stack.length === 0) {
      // Top level - Start of new artifact
      // Empty-lang fences are generic code blocks and should not open Canvas artifacts.
      const type = lang;
      // 清理 lang 字段：去除尾部非字母数字字符（tool 输出中 ```map" 或 ```map\ 可能是源代码转义残留）
      let normalizedType = type.trim().replace(/[^a-z0-9]+$/i, '').toLowerCase();
      if (normalizedType === 'md') normalizedType = 'markdown';
      if (normalizedType === 'txt') normalizedType = 'text';
      if (normalizedType === 'doc') normalizedType = 'docx';
      if (normalizedType === 'xls') normalizedType = 'xlsx';
      if (normalizedType === 'ppt') normalizedType = 'pptx';
      
      // Determine if artifact type is supported for Canvas rendering
      // We only support specific types; generic code blocks (Code Snippet) are excluded
      const supportedTypes = ['mermaid', 'html', 'svg', 'markdown', 'docx', 'pdf', 'text', 'csv', 'xlsx', 'pptx', 'url', 'json', 'map'];
      const isSupported = supportedTypes.includes(normalizedType);
      
      if (isSupported) {
          // Determine title
          let title = 'Code Snippet';
          if (normalizedType === 'mermaid') title = 'Mermaid';
          else if (normalizedType === 'html') title = 'Web Preview';
          else if (normalizedType === 'svg') title = 'SVG Image';
          else if (normalizedType === 'markdown') title = 'Markdown';
          else if (normalizedType === 'docx') title = 'Word 文档';
          else if (normalizedType === 'pdf') title = 'PDF 文档';
          else if (normalizedType === 'text') title = 'TXT 文档';
          else if (normalizedType === 'csv' || normalizedType === 'xlsx') title = 'Excel 文档';
          else if (normalizedType === 'pptx') title = 'PPT 文档';
          else if (normalizedType === 'url') title = '网页链接';
          else if (normalizedType === 'json') title = 'JSON 文件';
          else if (normalizedType === 'map') title = '地图';
          
          // Check if inside thinking block
          const isInThinking = thinkRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
          
          artifactStartIndex = absoluteStartIndex;
          
          currentArtifact = {
            id: `${msgId}-art-${artifactCount++}`,
            type: normalizedType,
            title,
            isComplete: false,
            isInThinking,
            startIndex: artifactStartIndex
          };
      } else {
          // Unsupported type (e.g. generic code block), do not create artifact
          currentArtifact = null;
      }
      
      if (topLevelFenceStartIndex === null) {
        topLevelFenceStartIndex = absoluteStartIndex;
      }

      stack.push(fence);
      contentStart = matchIndex + fullMatch.length;
      
    } else {
      // Inside an artifact
      const topFence = stack[stack.length - 1];
      
      // Check for closing condition
      // 1. Lang must be empty (standard closing fence)
      // 2. Fence length must be >= opening fence length
      if (lang.length === 0 && fence.length >= topFence.length) {
        stack.pop();
        
        if (stack.length === 0) {
          // Closed the top-level artifact
          const contentEnd = matchIndex;
          let blockContent = content.substring(contentStart, contentEnd);
          
          if (currentArtifact) {
            currentArtifact.content = blockContent;
            currentArtifact.isComplete = true;
            currentArtifact.endIndex = matchIndex + fullMatch.length;
            artifacts.push(currentArtifact as TextArtifact);
            currentArtifact = null;
          }
          if (topLevelFenceStartIndex !== null) {
            fenceRanges.push([topLevelFenceStartIndex, matchIndex + fullMatch.length]);
            topLevelFenceStartIndex = null;
          }
        }
      } else {
        // Nested block open
        // Push to stack to track nesting
        stack.push(fence);
      }
    }
  }
  
  // Handle incomplete artifact (streaming)
  if (currentArtifact && stack.length > 0) {
    const blockContent = content.substring(contentStart);
    currentArtifact.content = blockContent;
    currentArtifact.isComplete = false;
    currentArtifact.endIndex = content.length; // Assume end of content
    artifacts.push(currentArtifact as TextArtifact);
  }

  if (stack.length > 0 && topLevelFenceStartIndex !== null) {
    fenceRanges.push([topLevelFenceStartIndex, content.length]);
  }

  const linkRegex = /\[([^\]\n]+?)\]\(([^)\n]+)\)/gi;
  const inlineLinkRanges: [number, number][] = [];
  const artifactPatterns: Array<{ type: string; ext: string; defaultTitle: string }> = [
    { type: 'docx', ext: 'docx', defaultTitle: 'Word 文档' },
    { type: 'pdf', ext: 'pdf', defaultTitle: 'PDF 文档' },
    { type: 'html', ext: 'html?', defaultTitle: 'Web Preview' },
    { type: 'svg', ext: 'svg', defaultTitle: 'SVG Image' },
    { type: 'markdown', ext: 'md', defaultTitle: 'Markdown' },
    { type: 'text', ext: 'txt', defaultTitle: 'TXT 文档' },
    { type: 'csv', ext: 'csv', defaultTitle: 'Excel 文档' },
    { type: 'xlsx', ext: 'xlsx', defaultTitle: 'Excel 文档' },
    { type: 'pptx', ext: 'pptx', defaultTitle: 'PPT 文档' },
    { type: 'json', ext: 'json', defaultTitle: 'JSON 文件' },
    { type: 'image', ext: 'png', defaultTitle: 'PNG 图片' },
    { type: 'image', ext: 'jpg', defaultTitle: 'JPG 图片' },
    { type: 'image', ext: 'jpeg', defaultTitle: 'JPEG 图片' },
    { type: 'image', ext: 'gif', defaultTitle: 'GIF 图片' },
    { type: 'image', ext: 'webp', defaultTitle: 'WebP 图片' },
    { type: 'image', ext: 'bmp', defaultTitle: 'BMP 图片' },
  ];
  let linkMatch: RegExpExecArray | null;

  while ((linkMatch = linkRegex.exec(content)) !== null) {
    const fullMatch = linkMatch[0];
    const absoluteStartIndex = linkMatch.index;
    const matchEndIndex = linkMatch.index + fullMatch.length;
    if (absoluteStartIndex > 0 && content[absoluteStartIndex - 1] === '!') {
      continue;
    }

    const inThink = thinkRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inThink) continue;

    const inFence = fenceRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inFence) continue;

    inlineLinkRanges.push([absoluteStartIndex, matchEndIndex]);

    const linkText = linkMatch[1].trim();
    const url = linkMatch[2].trim();

    const matchedPattern = artifactPatterns.find(({ ext }) => {
      const pattern = new RegExp(`(?:\\.${ext})(?:$|[?#])`, 'i');
      return pattern.test(linkText) || pattern.test(url);
    });
    
    if (matchedPattern) {
      const artifactType = matchedPattern.type;
      const title = pickFileTitle(url, linkText, matchedPattern.ext, matchedPattern.defaultTitle);

      artifacts.push({
        id: `${msgId}-art-${artifactCount++}`,
        type: artifactType,
        title,
        content: url,
        isComplete: true,
        isInThinking: inThink,
        url: artifactType === 'html' || artifactType === 'markdown' || artifactType === 'svg' || artifactType === 'json' || artifactType === 'image' ? url : undefined,
        startIndex: absoluteStartIndex,
        endIndex: matchEndIndex
      });
    } else {
      // Non-file URL in markdown link - create url type artifact
      const urlObj = (() => {
        try {
          return new URL(url);
        } catch {
          return null;
        }
      })();
      if (urlObj) {
        const title = urlObj.hostname.replace(/^www\./, '') + urlObj.pathname;
        artifacts.push({
          id: `${msgId}-art-${artifactCount++}`,
          type: 'url',
          title,
          content: url,
          isComplete: true,
          isInThinking: inThink,
          url: url,
          startIndex: absoluteStartIndex,
          endIndex: matchEndIndex
        });
      }
    }
  }

  // 处理 HTML <a> 标签中的 URL
  const aTagRegex = /<a\s[^>]*href=["']([^"']+)["'][^>]*>([\s\S]*?)<\/a>/gi;
  let aTagMatch: RegExpExecArray | null;

  while ((aTagMatch = aTagRegex.exec(content)) !== null) {
    const fullMatch = aTagMatch[0];
    const url = aTagMatch[1];
    const linkText = aTagMatch[2].trim();
    const absoluteStartIndex = aTagMatch.index;
    const matchEndIndex = absoluteStartIndex + fullMatch.length;

    const inThink = thinkRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inThink) continue;

    const inFence = fenceRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inFence) continue;

    const urlObj = (() => {
      try {
        return new URL(url);
      } catch {
        return null;
      }
    })();
    if (!urlObj) continue;

    const matchedPattern = artifactPatterns.find(({ ext }) => {
      const pattern = new RegExp(`(?:\\.${ext})(?:$|[?#])`, 'i');
      return pattern.test(linkText) || pattern.test(url);
    });

    if (matchedPattern) {
      const title = pickFileTitle(url, linkText, matchedPattern.ext, matchedPattern.defaultTitle);
      artifacts.push({
        id: `${msgId}-art-${artifactCount++}`,
        type: matchedPattern.type,
        title,
        content: url,
        isComplete: true,
        isInThinking: false,
        url: matchedPattern.type === 'html' || matchedPattern.type === 'markdown' || matchedPattern.type === 'svg' || matchedPattern.type === 'json' || matchedPattern.type === 'image' ? url : undefined,
        startIndex: absoluteStartIndex,
        endIndex: matchEndIndex
      });
    } else {
      const title = urlObj.hostname.replace(/^www\./, '') + urlObj.pathname;
      artifacts.push({
        id: `${msgId}-art-${artifactCount++}`,
        type: 'url',
        title,
        content: url,
        isComplete: true,
        isInThinking: false,
        url: url,
        startIndex: absoluteStartIndex,
        endIndex: matchEndIndex
      });
    }
  }

  // 只处理被 `` ` `` 或 ``**`` 包裹的 URL，裸 URL 不处理
  // 匹配 `` `url` ``、`**url**`、`*url*` 三种格式
  const wrappedUrlRegex = /(?:`|\*\*?)(https?:\/\/[^\s<>]+?)(?:`|\*\*?)/gi;
  let wrappedUrlMatch: RegExpExecArray | null;

  while ((wrappedUrlMatch = wrappedUrlRegex.exec(content)) !== null) {
    const fullMatch = wrappedUrlMatch[0];
    const url = wrappedUrlMatch[1];
    const absoluteStartIndex = wrappedUrlMatch.index;
    const matchEndIndex = absoluteStartIndex + fullMatch.length;

    // 提取前后缀标记
    const prefix = content.slice(absoluteStartIndex, absoluteStartIndex + fullMatch.indexOf(url));
    const suffix = content.slice(absoluteStartIndex + fullMatch.indexOf(url) + url.length, matchEndIndex);
    
    // 检查前后标记是否一致（配对闭合）
    const isClosed = prefix === suffix;

    const inThink = thinkRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inThink) continue;

    const inFence = fenceRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inFence) continue;

    const inMarkdownLink = inlineLinkRanges.some(([start, end]) => absoluteStartIndex >= start && absoluteStartIndex < end);
    if (inMarkdownLink) continue;

    const urlObj = (() => {
      try {
        return new URL(url);
      } catch {
        return null;
      }
    })();
    if (!urlObj) continue;

    // 只有标记配对闭合时才认为 URL 完整
    const isComplete = isClosed;

    // Check if it matches file extension patterns (docx, pdf, html, md, txt, csv, xlsx, pptx, etc.)
    const matchedPattern = artifactPatterns.find(({ ext }) => {
      const pattern = new RegExp(`(?:\\.${ext})(?:$|[?#])`, 'i');
      return pattern.test(url);
    });

    if (matchedPattern) {
      // File URL artifact
      const title = deriveFileTitle(url, matchedPattern.ext) || matchedPattern.defaultTitle;
      artifacts.push({
        id: `${msgId}-art-${artifactCount++}`,
        type: matchedPattern.type,
        title,
        content: url,
        isComplete,
        isInThinking: false,
        url: url,
        startIndex: absoluteStartIndex,
        endIndex: matchEndIndex
      });
    } else {
      // Generic URL artifact
      const title = urlObj.hostname.replace(/^www\./, '') + urlObj.pathname;
      artifacts.push({
        id: `${msgId}-art-${artifactCount++}`,
        type: 'url',
        title,
        content: url,
        isComplete,
        isInThinking: false,
        url: url,
        startIndex: absoluteStartIndex,
        endIndex: matchEndIndex
      });
    }
  }

  return artifacts;
};
