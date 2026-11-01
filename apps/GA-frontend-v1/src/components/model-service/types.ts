// 模型服务相关类型定义

export const MODEL_TYPE_OPTIONS = [
  { label: '对话', value: 'dialogue' },
  { label: '视觉', value: 'vision' },
  { label: '推理', value: 'reasoning' },
  { label: '工具', value: 'tool' }
] as const;

export const MODEL_CONTEXT_SIZE_PRESETS = [
  { label: '32K', value: 32000 },
  { label: '64K', value: 64000 },
  { label: '128K', value: 128000 },
  { label: '160K', value: 160000 },
  { label: '200K', value: 200000 },
  { label: '256K', value: 256000 },
  { label: '1M', value: 1000000 }
] as const;

export type ContextSizeUnit = 'K' | 'M';

export function formatContextSize(value?: number): string {
  if (!value || value <= 0) return '';
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

export interface Model {
  id: string;
  name: string;
  icon?: string;
  iconText: string;
  types?: string[];
  contextSize?: number;
  avatar?: string;
}

export interface ModelGroup {
  id: string;
  name: string;
  models: Model[];
}

export interface ServiceData {
  apiKey: string;
  apiUrl: string;
  models: Record<string, ModelGroup>;
  modelsArray?: ModelGroup[];
  avatar?: string;
  backgroundColor?: string;
  type?: string;
  noApiKeyRequired?: boolean;
  // 新增：服务提供商图标类型（硅基流动/百炼/百度云）
  providerIcon?: 'siliconcloud' | 'bailian' | 'baiducloud';
}

export interface ServiceListItem {
  id?: string;
  name: string;
  iconClass: string;
  iconText: string;
  avatar?: string;
  backgroundColor?: string;
  // 新增：服务提供商图标类型（硅基流动/百炼/百度云）
  providerIcon?: 'siliconcloud' | 'bailian' | 'baiducloud';
}

export interface ProviderFormData {
  name: string;
  type: string;
  icon: string;
  avatar: string;
  backgroundColor: string;
  // 新增：服务提供商图标类型（硅基流动/百炼/百度云）
  providerIcon?: 'siliconcloud' | 'bailian' | 'baiducloud';
  // 新增：导入的完整服务配置（可选）
  serviceData?: ServiceData;
}

export interface EditProviderFormData extends ProviderFormData {
  originalName: string;
}

export interface ModelFormData {
  id: string;
  name: string;
  iconText: string;
  types: string[];
  contextSize: number;
}

export interface EditModelFormData {
  id: string;
  name: string;
  types: string[];
  contextSize: number;
}

export interface ProviderData {
  name: string;
  iconText: string;
  avatar?: string;
  backgroundColor?: string;
  // 新增：服务提供商图标类型（硅基流动/百炼/百度云）
  providerIcon?: 'siliconcloud' | 'bailian' | 'baiducloud';
}

export interface ModelData {
  id: string;
  name: string;
  types?: string[];
  contextSize?: number;
}
