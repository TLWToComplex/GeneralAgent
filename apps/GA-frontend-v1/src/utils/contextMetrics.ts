import { getEncoding } from 'js-tiktoken';
import type { ContextMetrics } from '@/types/mcp';
import { ConfigManager } from './ConfigManager';

const RESERVED_OUTPUT_RATIO = 0.2;
const SAFETY_MARGIN_RATIO = 0.08;
const MESSAGE_OVERHEAD_TOKENS = 4;
const ASSISTANT_PRIMING_TOKENS = 2;
const TOOL_SCHEMA_OVERHEAD_TOKENS = 12;
const UNKNOWN_IMAGE_TOKEN_COST = 256;

let encoding: ReturnType<typeof getEncoding> | null = null;

function getTokenizer() {
  if (!encoding) {
    encoding = getEncoding('cl100k_base');
  }
  return encoding;
}

function countTokens(text: string): number {
  if (!text) return 0;
  try {
    return getTokenizer().encode(text).length;
  } catch (error) {
    console.error('上下文Token计算失败:', error);
    return 0;
  }
}

export function estimateImageTokensFromMetadata(input: {
  size?: number;
  width?: number;
  height?: number;
  tokenEstimate?: number;
  url?: string;
}): number {
  if (typeof input.tokenEstimate === 'number' && Number.isFinite(input.tokenEstimate) && input.tokenEstimate > 0) {
    return Math.round(input.tokenEstimate);
  }

  const width = typeof input.width === 'number' && input.width > 0 ? input.width : 0;
  const height = typeof input.height === 'number' && input.height > 0 ? input.height : 0;
  if (width > 0 && height > 0) {
    const maxSide = Math.max(width, height);
    const area = width * height;
    if (maxSide <= 512 && area <= 512 * 512) return 128;
    if (maxSide <= 1024 && area <= 1024 * 1024) return 256;
    if (maxSide <= 2048 && area <= 2048 * 2048) return 384;
    if (maxSide <= 4096 && area <= 4096 * 4096) return 512;
    return 768;
  }

  const size = typeof input.size === 'number' && input.size > 0 ? input.size : 0;
  if (size > 0) {
    if (size <= 256 * 1024) return 128;
    if (size <= 1024 * 1024) return 256;
    if (size <= 2 * 1024 * 1024) return 384;
    if (size <= 5 * 1024 * 1024) return 512;
    return 768;
  }

  const imageUrl = String(input.url || '').trim();
  if (!imageUrl) return 0;
  return UNKNOWN_IMAGE_TOKEN_COST;
}

function estimateImageTokensFromUrl(url: string): number {
  return estimateImageTokensFromMetadata({ url });
}

function estimateMessageFileImageTokens(files: any[] | undefined): number {
  if (!Array.isArray(files) || files.length === 0) return 0;

  return files.reduce((sum, file) => {
    const isImage = file?.isFileImage || (typeof file?.name === 'string' && /\.(png|jpe?g|gif|webp|bmp|svg|avif)$/i.test(file.name));
    if (!isImage) return sum;
    return sum + estimateImageTokensFromMetadata({
      tokenEstimate: file?.imageTokenEstimate,
      size: file?.size,
      width: file?.imageWidth,
      height: file?.imageHeight,
      url: file?.imagePreviewUrl || file?.imageDataUrl || file?.dataUrl
    });
  }, 0);
}

function estimateContentTokens(content: unknown, options?: { includeImageParts?: boolean }): { tokens: number; imageTokens: number } {
  const includeImageParts = options?.includeImageParts !== false;
  if (typeof content === 'string') {
    return {
      tokens: countTokens(content),
      imageTokens: 0
    };
  }

  if (Array.isArray(content)) {
    return content.reduce((result, part) => {
      if (typeof part === 'string') {
        result.tokens += countTokens(part);
        return result;
      }
      if (!part || typeof part !== 'object') return result;
      const typedPart = part as Record<string, any>;
      if (typedPart.type === 'text') {
        result.tokens += countTokens(String(typedPart.text || ''));
        return result;
      }
      if (typedPart.type === 'image_url') {
        if (includeImageParts) {
          const imageUrl = String(typedPart.image_url?.url || '').trim();
          const imageTokens = estimateImageTokensFromUrl(imageUrl);
          result.imageTokens += imageTokens;
          result.tokens += imageTokens;
        }
        return result;
      }
      result.tokens += countTokens(JSON.stringify(typedPart));
      return result;
    }, { tokens: 0, imageTokens: 0 });
  }

  if (content && typeof content === 'object') {
    try {
      return {
        tokens: countTokens(JSON.stringify(content)),
        imageTokens: 0
      };
    } catch {
      return {
        tokens: 0,
        imageTokens: 0
      };
    }
  }

  return {
    tokens: countTokens(String(content || '')),
    imageTokens: 0
  };
}

function estimateToolCallTokens(toolCall: any): number {
  if (!toolCall || typeof toolCall !== 'object') return 0;
  let total = 6;
  total += countTokens(String(toolCall.id || ''));
  total += countTokens(String(toolCall.type || 'function'));
  total += countTokens(String(toolCall.function?.name || ''));
  total += countTokens(String(toolCall.function?.arguments || ''));
  return total;
}

function estimateMessageTokens(message: any): { total: number; imageTokens: number } {
  if (!message || typeof message !== 'object') return { total: 0, imageTokens: 0 };

  const fileImageTokens = estimateMessageFileImageTokens(message.files);
  const contentMetrics = estimateContentTokens(message.content, {
    includeImageParts: fileImageTokens === 0
  });
  let total = MESSAGE_OVERHEAD_TOKENS;
  total += countTokens(String(message.role || ''));
  total += contentMetrics.tokens + fileImageTokens;

  if (message.tool_call_id) {
    total += countTokens(String(message.tool_call_id)) + 2;
  }

  if (Array.isArray(message.tool_calls)) {
    total += message.tool_calls.reduce((sum: number, toolCall: any) => sum + estimateToolCallTokens(toolCall), 0);
  }

  return {
    total,
    imageTokens: contentMetrics.imageTokens + fileImageTokens
  };
}

function estimateToolsTokens(tools: any[]): number {
  if (!Array.isArray(tools) || tools.length === 0) return 0;

  let total = TOOL_SCHEMA_OVERHEAD_TOKENS;
  for (const tool of tools) {
    if (!tool || typeof tool !== 'object') continue;
    total += countTokens(String(tool.type || 'function'));
    total += countTokens(String(tool.function?.name || ''));
    total += countTokens(String(tool.function?.description || ''));
    if (tool.function?.parameters) {
      try {
        total += countTokens(JSON.stringify(tool.function.parameters));
      } catch {
        total += countTokens(String(tool.function.parameters));
      }
    }
  }
  return total;
}

export function resolveContextWindowForModel(modelId: string): number | undefined {
  const currentModel = ConfigManager
    .getInstance()
    .getAvailableModels()
    .find((model) => model.id === modelId);

  if (typeof currentModel?.contextSize === 'number' && currentModel.contextSize > 0) {
    return currentModel.contextSize;
  }

  return undefined;
}

export function estimateContextMetrics(payload: {
  model: string;
  messages: any[];
  tools?: any[];
  contextWindow?: number;
}): ContextMetrics {
  const contextWindow = payload.contextWindow && payload.contextWindow > 0
    ? payload.contextWindow
    : resolveContextWindowForModel(payload.model);
  const reservedOutputTokens = contextWindow && contextWindow > 0
    ? Math.max(1024, Math.round(contextWindow * RESERVED_OUTPUT_RATIO))
    : 0;
  const safetyMarginTokens = contextWindow && contextWindow > 0
    ? Math.max(512, Math.round(contextWindow * SAFETY_MARGIN_RATIO))
    : 0;
  const usableInputTokens = contextWindow && contextWindow > 0
    ? Math.max(0, contextWindow - reservedOutputTokens - safetyMarginTokens)
    : 0;
  const messageTotals = (payload.messages || []).reduce((sum, message) => {
    const metrics = estimateMessageTokens(message);
    sum.messagesTokens += metrics.total;
    sum.imageTokens += metrics.imageTokens;
    return sum;
  }, { messagesTokens: 0, imageTokens: 0 });
  const messagesTokens = messageTotals.messagesTokens;
  const imageTokens = messageTotals.imageTokens;
  const textTokens = Math.max(0, messagesTokens - imageTokens);
  const toolsTokens = estimateToolsTokens(payload.tools || []);
  const promptTokens = messagesTokens + toolsTokens + ASSISTANT_PRIMING_TOKENS;

  return {
    mode: 'estimated',
    model: payload.model,
    contextWindow,
    promptTokens,
    messagesTokens,
    textTokens,
    imageTokens,
    toolsTokens,
    reservedOutputTokens,
    safetyMarginTokens,
    usableInputTokens,
    utilization: contextWindow && contextWindow > 0 ? promptTokens / contextWindow : 0,
    messageCount: Array.isArray(payload.messages) ? payload.messages.length : 0,
    toolsCount: Array.isArray(payload.tools) ? payload.tools.length : 0
  };
}

export function createPendingContextMetrics(payload: {
  model: string;
  contextWindow?: number;
  messageCount?: number;
  toolsCount?: number;
}): ContextMetrics {
  const contextWindow = payload.contextWindow && payload.contextWindow > 0
    ? payload.contextWindow
    : resolveContextWindowForModel(payload.model);
  const reservedOutputTokens = contextWindow && contextWindow > 0
    ? Math.max(1024, Math.round(contextWindow * RESERVED_OUTPUT_RATIO))
    : 0;
  const safetyMarginTokens = contextWindow && contextWindow > 0
    ? Math.max(512, Math.round(contextWindow * SAFETY_MARGIN_RATIO))
    : 0;
  const usableInputTokens = contextWindow && contextWindow > 0
    ? Math.max(0, contextWindow - reservedOutputTokens - safetyMarginTokens)
    : 0;

  return {
    mode: 'pending',
    model: payload.model,
    contextWindow,
    promptTokens: 0,
    messagesTokens: 0,
    textTokens: 0,
    imageTokens: 0,
    toolsTokens: 0,
    reservedOutputTokens,
    safetyMarginTokens,
    usableInputTokens,
    utilization: 0,
    messageCount: payload.messageCount || 0,
    toolsCount: payload.toolsCount || 0
  };
}

export function withExactPromptUsage(
  metrics: ContextMetrics,
  usage?: {
    prompt_tokens?: number;
    prompt_tokens_details?: {
      text_tokens?: number;
      image_tokens?: number;
    };
  }
): ContextMetrics {
  if (!usage || typeof usage.prompt_tokens !== 'number' || usage.prompt_tokens <= 0) {
    return metrics;
  }

  const exactTextTokens = typeof usage.prompt_tokens_details?.text_tokens === 'number'
    ? usage.prompt_tokens_details.text_tokens
    : metrics.textTokens;
  const exactImageTokens = typeof usage.prompt_tokens_details?.image_tokens === 'number'
    ? usage.prompt_tokens_details.image_tokens
    : metrics.imageTokens;

  return {
    ...metrics,
    mode: 'exact',
    promptTokens: usage.prompt_tokens,
    messagesTokens: Math.max(0, exactTextTokens + exactImageTokens),
    textTokens: Math.max(0, exactTextTokens),
    imageTokens: Math.max(0, exactImageTokens),
    utilization: metrics.contextWindow && metrics.contextWindow > 0
      ? usage.prompt_tokens / metrics.contextWindow
      : 0
  };
}

export function formatContextTokenCount(value?: number): string {
  if (!value || value <= 0) return '0';
  if (value >= 1000000) {
    const amount = value / 1000000;
    return `${Number.isInteger(amount) ? amount : amount.toFixed(1).replace(/\.0$/, '')}M`;
  }
  if (value >= 1000) {
    const amount = value / 1000;
    return `${Number.isInteger(amount) ? amount : amount.toFixed(1).replace(/\.0$/, '')}K`;
  }
  return String(value);
}
