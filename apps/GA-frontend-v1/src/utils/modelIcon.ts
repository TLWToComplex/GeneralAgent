export function isQwenFamily(modelIdOrName?: string): boolean {
  const normalized = (modelIdOrName || '').toLowerCase();
  return normalized.includes('qwen') || normalized.includes('qwq');
}

export function shouldShowModelIcon(modelName: string, iconType: string): boolean {
  const normalizedName = (modelName || '').toLowerCase();
  const normalizedIconType = iconType.toLowerCase();

  if (normalizedIconType === 'qwen') {
    return isQwenFamily(normalizedName);
  }

  return normalizedName.includes(normalizedIconType);
}
