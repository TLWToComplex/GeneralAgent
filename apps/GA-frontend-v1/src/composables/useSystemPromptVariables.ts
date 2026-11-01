import { ref, computed } from 'vue';
import { SystemPromptVariables } from '@/utils/SystemPromptVariables';

/**
 * 系统提示词变量处理 composable
 */
export function useSystemPromptVariables() {
  const isProcessingEnabled = ref(true);

  /**
   * 处理系统提示词中的变量
   * @param systemPrompt 原始系统提示词
   * @returns 处理后的系统提示词
   */
  const processSystemPrompt = (systemPrompt: string): string => {
    if (!isProcessingEnabled.value || !systemPrompt) {
      return systemPrompt;
    }

    return SystemPromptVariables.processVariables(systemPrompt);
  };

  /**
   * 检查系统提示词是否包含变量
   * @param systemPrompt 系统提示词
   * @returns 是否包含变量
   */
  const hasVariables = (systemPrompt: string): boolean => {
    return SystemPromptVariables.hasVariables(systemPrompt);
  };

  /**
   * 获取系统提示词中的变量列表
   * @param systemPrompt 系统提示词
   * @returns 变量名数组
   */
  const extractVariables = (systemPrompt: string): string[] => {
    return SystemPromptVariables.extractVariables(systemPrompt);
  };

  /**
   * 获取支持的变量列表
   */
  const supportedVariables = computed(() => {
    const variables = SystemPromptVariables.getSupportedVariables();
    return variables.map(key => ({
      key,
      label: getVariableLabel(key)
    }));
  });

  /**
   * 获取变量的显示标签
   */
  const getVariableLabel = (key: string): string => {
    const labelMap: Record<string, string> = {
      'date': '当前日期',
      'time': '当前时间',
      'datetime': '当前日期时间',
      'timestamp': '时间戳',
      'year': '当前年份',
      'month': '当前月份',
      'day': '当前日期',
      'model_name': '模型名称'
    };
    return labelMap[key] || key;
  };

  /**
   * 启用/禁用变量处理
   * @param enabled 是否启用
   */
  const setProcessingEnabled = (enabled: boolean) => {
    isProcessingEnabled.value = enabled;
  };

  /**
   * 预览处理后的系统提示词
   * @param systemPrompt 原始系统提示词
   * @returns 预览结果
   */
  const previewProcessedPrompt = (systemPrompt: string) => {
    const processed = processSystemPrompt(systemPrompt);
    const variables = extractVariables(systemPrompt);
    
    return {
      original: systemPrompt,
      processed,
      variables,
      hasChanges: systemPrompt !== processed
    };
  };

  return {
    isProcessingEnabled,
    processSystemPrompt,
    hasVariables,
    extractVariables,
    supportedVariables,
    setProcessingEnabled,
    previewProcessedPrompt
  };
}