<template>
  <div class="config-section">
    <div class="prompt-section-header">
      <h3>提示词设置</h3>
      <p>配置智能体的系统提示词</p>
    </div>
    <a-form :model="promptConfig" layout="vertical" class="form-content">
      <a-form-item label="系统提示词" class="compact-form-item">
        <a-textarea 
          v-model:value="localPromptConfig.systemPrompt" 
          placeholder="请输入系统提示词..." 
          :auto-size="{ minRows: 10, maxRows: 10 }"
          @change="handlePromptChange"
          style="font-size: 13px;"
        />
        <div class="prompt-info-and-token">
          <div class="prompt-info">
            <div class="prompt-info-text">系统提示词中可以使用${}来引用变量，例如：${date}</div>
          </div>
          <div class="token-counter">
            <span title="Token计算基于GPT-4编码，不同平台可能略有差异">Token: {{ tokenCount }}</span>
          </div>
        </div>
      </a-form-item>

      <a-form-item label="变量支持" class="compact-form-item" style="margin-top: 10px;">
        <!-- 支持的变量类型 -->
        <div class="supported-variables-panel">
          <div class="supported-variables-content">
            <div class="variables-showcase">
              <div 
                v-for="variable in SUPPORTED_VARIABLES" 
                :key="variable + forceUpdate" 
                class="showcase-card"
              >
                <div class="showcase-header">
                  <span class="showcase-variable">{{ variable }}</span>
                  <span class="showcase-value">{{ getVariableCurrentValue(variable) }}</span>
                </div>
                <div class="showcase-desc">{{ getVariableDescription(variable) }}</div>
              </div>
            </div>
          </div>
        </div>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import { getEncoding } from 'js-tiktoken';

// 定义接口
interface PromptConfig {
  systemPrompt: string;
  historyDepth?: number;
}

interface FormErrors {
  name: boolean;
  description: boolean;
  modelService: boolean;
  modelName: boolean;
}

interface Props {
  promptConfig: PromptConfig;
  errors: FormErrors;
  modelName: string | undefined;
}

interface Emits {
  (e: 'update:promptConfig', value: PromptConfig): void;
  (e: 'update:errors', value: Partial<FormErrors>): void;
}

// 组件属性和事件
const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// 本地状态
const localPromptConfig = ref<PromptConfig>({ ...props.promptConfig });
const forceUpdate = ref(0);
const updateTimer = ref<NodeJS.Timeout | null>(null);

// Token计算相关
let encoding: any = null;

// 初始化编码器
const initEncoding = () => {
  try {
    encoding = getEncoding('cl100k_base');
  } catch (error) {
    console.error('编码器初始化失败:', error);
  }
};

// 计算token数量
const tokenCount = computed(() => {
  if (!localPromptConfig.value.systemPrompt || !encoding) return 0;
  try {
    const text = localPromptConfig.value.systemPrompt.trim();
    return encoding.encode(text).length;
  } catch (error) {
    console.error('Token计算错误:', error);
    return 0;
  }
});

// 支持的变量类型
const SUPPORTED_VARIABLES = ['date', 'time', 'datetime', 'timestamp', 'year', 'month', 'day', 'model_name'];

// 监听props变化，更新本地状态
watch(
  () => props.promptConfig,
  (newConfig) => {
    localPromptConfig.value = { ...newConfig };
  },
  { deep: true, immediate: true }
);

// 处理提示词变化
const handlePromptChange = () => {
  emit('update:promptConfig', { ...localPromptConfig.value });
};

// 获取变量描述
const getVariableDescription = (variable: string): string => {
  const descriptions: Record<string, string> = {
    'date': '当前日期 (YYYY-MM-DD)',
    'time': '当前时间 (HH:MM:SS)',
    'datetime': '当前日期时间 (YYYY-MM-DD HH:MM:SS)',
    'timestamp': '当前时间戳',
    'year': '当前年份',
    'month': '当前月份',
    'day': '当前日期',
    'model_name': '当前选择的模型名称'
  };

  return descriptions[variable.toLowerCase()] || '未知变量';
};

// 获取变量当前值
const getVariableCurrentValue = (variable: string): string => {
  const now = new Date();

  switch (variable.toLowerCase()) {
    case 'date':
      return now.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).replace(/\//g, '-');
    case 'time':
      return now.toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    case 'datetime':
      return now.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).replace(/\//g, '-');
    case 'timestamp':
      return now.getTime().toString();
    case 'year':
      return now.getFullYear().toString();
    case 'month':
      return (now.getMonth() + 1).toString().padStart(2, '0');
    case 'day':
      return now.getDate().toString().padStart(2, '0');
    case 'model_name':
      return props.modelName || '未选择模型';
    default:
      return '未知变量';
  }
};

// 启动变量更新计时器
const startVariableUpdateTimer = () => {
  // 清除已有计时器
  if (updateTimer.value) {
    clearInterval(updateTimer.value);
  }
  
  // 设置新计时器，每秒更新一次时间相关变量
  updateTimer.value = setInterval(() => {
    forceUpdate.value++;
  }, 1000);
};

// 停止变量更新计时器
const stopVariableUpdateTimer = () => {
  if (updateTimer.value) {
    clearInterval(updateTimer.value);
    updateTimer.value = null;
  }
};

// 组件生命周期
onMounted(() => {
  initEncoding();
  startVariableUpdateTimer();
  localPromptConfig.value = { ...props.promptConfig };
});

onUnmounted(() => {
  stopVariableUpdateTimer();
});
</script>