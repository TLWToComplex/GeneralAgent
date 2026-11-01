import StorageService from './StorageService';

/**
 * 系统提示词变量处理工具类
 * 用于处理系统提示词中的动态变量替换
 */
export class SystemPromptVariables {
  private static readonly VARIABLE_PATTERN = /\$\{([^}]+)}/g;

  /**
   * 获取当前日期 (YYYY-MM-DD 格式)
   */
  private static getCurrentDate(): string {
    const now = new Date();
    return now.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit'
    }).replace(/\//g, '-');
  }

  /**
   * 获取当前时间 (HH:MM:SS 格式)
   */
  private static getCurrentTime(): string {
    const now = new Date();
    return now.toLocaleTimeString('zh-CN', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  /**
   * 获取当前日期时间 (YYYY-MM-DD HH:MM:SS 格式)
   */
  private static getCurrentDateTime(): string {
    const now = new Date();
    return now.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    }).replace(/\//g, '-');
  }

  /**
   * 获取当前时间戳
   */
  private static getCurrentTimestamp(): string {
    return Date.now().toString();
  }

  /**
   * 获取当前年份
   */
  private static getCurrentYear(): string {
    return new Date().getFullYear().toString();
  }

  /**
   * 获取当前月份
   */
  private static getCurrentMonth(): string {
    return (new Date().getMonth() + 1).toString().padStart(2, '0');
  }

  /**
   * 获取当前日
   */
  private static getCurrentDay(): string {
    return new Date().getDate().toString().padStart(2, '0');
  }

  /**
   * 获取当前选择的模型名称
   */
  private static getCurrentModelName(): string {
    const modelName = StorageService.getApiConfig()?.model;
    return modelName || '未选择模型';
  }

  /**
   * 变量映射表
   */
  private static readonly VARIABLE_MAP: Record<string, () => string> = {
    'date': SystemPromptVariables.getCurrentDate,
    'time': SystemPromptVariables.getCurrentTime,
    'datetime': SystemPromptVariables.getCurrentDateTime,
    'timestamp': SystemPromptVariables.getCurrentTimestamp,
    'year': SystemPromptVariables.getCurrentYear,
    'month': SystemPromptVariables.getCurrentMonth,
    'day': SystemPromptVariables.getCurrentDay,
    'model_name': SystemPromptVariables.getCurrentModelName,
  };

  /**
   * 处理系统提示词中的变量替换
   * @param systemPrompt 原始系统提示词
   * @returns 处理后的系统提示词
   */
  public static processVariables(systemPrompt: string): string {
    if (!systemPrompt) {
      return systemPrompt;
    }

    return systemPrompt.replace(this.VARIABLE_PATTERN, (match, variableName) => {
      const trimmedName = variableName.trim().toLowerCase();
      const handler = this.VARIABLE_MAP[trimmedName];
      
      if (handler) {
        try {
          return handler();
        } catch (error) {
          console.warn(`处理系统提示词变量 ${variableName} 时出错:`, error);
          return match; // 出错时返回原始变量
        }
      } else {
        return match; // 未知变量返回原始内容
      }
    });
  }

  /**
   * 检查文本中是否包含变量
   * @param text 要检查的文本
   * @returns 是否包含变量
   */
  public static hasVariables(text: string): boolean {
    return this.VARIABLE_PATTERN.test(text);
  }

  /**
   * 获取文本中的所有变量名
   * @param text 要分析的文本
   * @returns 变量名数组
   */
  public static extractVariables(text: string): string[] {
    const matches = text.match(this.VARIABLE_PATTERN);
    if (!matches) return [];
    
    return matches.map(match => {
        return match.slice(2, -1).trim();
    });
  }

  /**
   * 获取支持的变量列表
   * @returns 支持的变量名数组
   */
  public static getSupportedVariables(): string[] {
    return Object.keys(this.VARIABLE_MAP);
  }

  /**
   * 验证变量名是否支持
   * @param variableName 变量名
   * @returns 是否支持
   */
  public static isVariableSupported(variableName: string): boolean {
    return variableName.toLowerCase() in this.VARIABLE_MAP;
  }
}