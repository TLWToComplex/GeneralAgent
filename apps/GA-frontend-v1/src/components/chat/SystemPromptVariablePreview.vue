<template>
  <div class="variable-preview-container">
    <!-- 只显示预览内容 -->
    <template v-if="showOnlyPreview">
      <div class="preview-panel">
        <div class="preview-header-simple">
          <h4 class="section-title">
            系统提示词预览
          </h4>
          <span class="comparison-count">{{ processedPrompt.length }} 字符</span>
        </div>

        <div class="preview-content">
          <div class="preview-comparison">
            <div class="comparison-section">
              <div class="comparison-content processed">{{ processedPrompt || '暂无系统提示词内容' }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- 只显示变量信息 -->
    <template v-else-if="showOnlyVariables">
      <!-- 主控制面板 -->
      <div class="control-panel">
        <div class="panel-header">
          <div class="header-info">
            <h3 class="panel-title">系统提示词变量</h3>
            <span class="variable-count">
              检测到 {{ variableInfo.variables.length }} 个变量
            </span>
          </div>
        </div>

        <!-- 检测到的变量 -->
        <div v-if="variableInfo.hasVariables" class="detected-variables-panel">
          <div class="detected-variables-content">
            <div class="variable-grid">
              <div
                  v-for="variable in variableInfo.variables"
                  :key="variable"
                  class="variable-card"
                  :class="{ 'supported': isSupportedVariable(variable), 'unsupported': !isSupportedVariable(variable) }"
              >
                <div class="variable-name" :title="variable">{{ variable }}</div>
                <div class="variable-desc" :title="getVariableDescription(variable)">{{ getVariableDescription(variable) }}</div>
                <div class="variable-status">
                  <span v-if="isSupportedVariable(variable)" class="status-badge supported">支持</span>
                  <span v-else class="status-badge unsupported">未知</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        <!-- 无变量时的占位UI -->
        <div v-else class="no-variables-placeholder">
          <div class="placeholder-content">
            <div class="placeholder-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <div class="placeholder-text">
              <p class="placeholder-title">暂无变量</p>
              <p class="placeholder-desc">当前系统提示词中未检测到变量</p>
            </div>
          </div>
        </div>
      </div>

      <!-- 支持的变量类型 -->
      <div class="supported-variables-panel">
        <div class="panel-header-simple">
          <h4 class="section-title">
            支持的变量类型
          </h4>
        </div>

        <div class="supported-variables-content">
          <div class="variables-showcase">
            <div
                v-for="variable in supportedVariables"
                :key="variable.key"
                class="showcase-card"
            >
              <div class="showcase-header">
                <span class="showcase-variable">{{ variable.key }}</span>
                <span class="showcase-value" :title="getVariableCurrentValue(variable.key)">{{ getVariableCurrentValue(variable.key) }}</span>
              </div>
              <div class="showcase-desc" :title="getVariableDescription(variable.key)">{{ getVariableDescription(variable.key) }}</div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import {computed, ref, onMounted, onUnmounted} from 'vue';
import {useSystemPromptVariables} from '@/composables/useSystemPromptVariables';

interface Props {
  systemPrompt: string;
  showOnlyPreview?: boolean;
  showOnlyVariables?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  showOnlyPreview: false,
  showOnlyVariables: false
});

const {
  hasVariables,
  extractVariables,
  supportedVariables,
  processSystemPrompt
} = useSystemPromptVariables();

// 用于触发时间变量更新的响应式变量
const currentTime = ref(new Date());
let timeUpdateInterval: NodeJS.Timeout | null = null;

// 缓存上一次的时间值，用于性能优化
const lastTimeValues = ref<Record<string, string>>({});

// 检查时间变量是否需要更新
const shouldUpdateTimeVariable = (variable: string, newValue: string): boolean => {
  const lastValue = lastTimeValues.value[variable];
  if (lastValue !== newValue) {
    lastTimeValues.value[variable] = newValue;
    return true;
  }
  return false;
};

// 启动定时器
onMounted(() => {
  // 初始化缓存
  const now = new Date();
  const timeVariables = ['date', 'time', 'datetime', 'timestamp', 'year', 'month', 'day'];
  timeVariables.forEach(variable => {
    lastTimeValues.value[variable] = getTimeValue(variable, now);
  });

  timeUpdateInterval = setInterval(() => {
    const newTime = new Date();
    let hasChanges = false;

    // 检查是否有任何时间变量发生变化
    timeVariables.forEach(variable => {
      const newValue = getTimeValue(variable, newTime);
      if (shouldUpdateTimeVariable(variable, newValue)) {
        hasChanges = true;
      }
    });

    if (hasChanges) {
      currentTime.value = newTime;
    }
  }, 1000);
});

onUnmounted(() => {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
  }
});

const getTimeValue = (variable: string, date: Date): string => {
  switch (variable.toLowerCase()) {
    case 'date':
      return date.toLocaleDateString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit'
      }).replace(/\//g, '-');
    case 'time':
      return date.toLocaleTimeString('zh-CN', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    case 'datetime':
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      }).replace(/\//g, '-');
    case 'timestamp':
      return date.getTime().toString();
    case 'year':
      return date.getFullYear().toString();
    case 'month':
      return (date.getMonth() + 1).toString().padStart(2, '0');
    case 'day':
      return date.getDate().toString().padStart(2, '0');
    default:
      return '';
  }
};

const variableInfo = computed(() => {
  if (!props.systemPrompt) {
    return {hasVariables: false, variables: []};
  }

  return {
    hasVariables: hasVariables(props.systemPrompt),
    variables: extractVariables(props.systemPrompt)
  };
});

const processedPrompt = computed(() => {
  if (!props.systemPrompt) {
    return '';
  }

  currentTime.value;

  return processSystemPrompt(props.systemPrompt);
});

const isSupportedVariable = (variable: string): boolean => {
  return supportedVariables.value.some(v => v.key === variable.toLowerCase());
};

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

const getVariableCurrentValue = (variable: string): string => {
  const now = currentTime.value;

  const timeValue = getTimeValue(variable, now);
  if (timeValue) {
    return timeValue;
  }

  const testPrompt = `\${${variable}}`;
  const processed = processSystemPrompt(testPrompt);
  return processed === testPrompt ? '无法获取' : processed;
};
</script>

<style scoped>
.variable-preview-container {
  padding: 0;
  margin: 0;
  overflow: hidden;
  transition: all 0.3s ease;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.variable-preview-container:hover {
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.08);
}

.control-panel {
  flex-shrink: 0;
  margin-bottom: 15px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding-left: 12px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.panel-title {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  margin: 0;
}

.variable-count {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 10px;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(59, 130, 246, 0.3);
}

.modern-toggle input {
  display: none;
}

.detected-variables-panel {
  margin-top: 10px;
}

.detected-variables-content {
  height: 200px;
  overflow-y: auto;
  position: relative;
  padding: 0 5px 0 12px;
}

.section-title {
  display: flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  color: #374151;
  flex-shrink: 0;
}

.variable-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 8px;
  padding-top: 1px;
}

.variable-card {
  background: white;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 8px;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
  max-width: 174px;
}

.variable-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px -4px rgba(0, 0, 0, 0.15);
}

.variable-name {
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.variable-desc {
  font-size: 11px;
  color: #64748b;
  margin-bottom: 7px;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  height: calc(1.3em * 2);
}

.variable-status {
  display: flex;
  justify-content: flex-end;
}

.status-badge {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.status-badge.supported {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.status-badge.unsupported {
  background: rgba(245, 158, 11, 0.1);
  color: #d97706;
}

.supported-variables-panel {
  flex-shrink: 0;
}

.panel-header-simple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s ease;
  padding: 0 12px 4px;
}

.preview-header-simple {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
  transition: all 0.2s ease;
}

.supported-variables-content {
  animation: slideDown 0.3s ease;
  height: 250px;
  overflow-y: auto;
  position: relative;
  padding: 0 5px 0 12px;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.variables-showcase {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 8px;
  padding-top: 1px;
  padding-bottom: 1px;
}

.showcase-card {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid #ebf3ff;
  border-radius: 6px;
  padding: 8px;
  transition: all 0.3s ease;
}

.showcase-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.showcase-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.showcase-variable {
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #3b82f6;
  background: rgba(59, 130, 246, 0.1);
  padding: 1px 4px;
  border-radius: 3px;
}

.showcase-value {
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 11px;
  color: #059669;
  background: rgba(16, 185, 129, 0.1);
  padding: 1px 4px;
  border-radius: 3px;
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.showcase-desc {
  font-size: 11px;
  color: #64748b;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  height: calc(1.3em * 2);
}

.preview-panel {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-content {
  animation: slideDown 0.3s ease;
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.preview-comparison {

  min-height: 0;
}

.comparison-section {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.comparison-count {
  font-size: 10px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 1px 4px;
  border-radius: 3px;
  margin-top: -5px;
}

.comparison-content {
  padding: 8px;
  font-size: 12px;
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-word;
  height: 205px;
  overflow-y: auto;
  min-height: 0;
}

.comparison-content.processed {
  color: #374151;
}

@media (max-width: 768px) {
  .panel-header {
    flex-direction: column;
    gap: 16px;
    align-items: stretch;
  }

  .header-info {
    justify-content: space-between;
  }

  .variable-grid {
    grid-template-columns: 1fr;
  }

  .variables-showcase {
    grid-template-columns: 1fr;
  }

  .preview-comparison {
    grid-template-columns: 1fr;
    gap: 12px;
  }
}

.comparison-content::-webkit-scrollbar,
.detected-variables-content::-webkit-scrollbar,
.supported-variables-content::-webkit-scrollbar {
  width: 6px;
}

.comparison-content::-webkit-scrollbar-track,
.detected-variables-content::-webkit-scrollbar-track,
.supported-variables-content::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.comparison-content::-webkit-scrollbar-thumb,
.detected-variables-content::-webkit-scrollbar-thumb,
.supported-variables-content::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}

.comparison-content::-webkit-scrollbar-thumb:hover,
.detected-variables-content::-webkit-scrollbar-thumb:hover,
.supported-variables-content::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}

.no-variables-placeholder {
  margin-left: 12px;
  margin-top: 10px;
  height: 200px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: linear-gradient(135deg, #fafbfc 0%, #f8fafc 100%);
  transition: all 0.3s ease;
}

.no-variables-placeholder:hover {
  border-color: #cbd5e1;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.placeholder-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  text-align: center;
  opacity: 0.6;
  transition: all 0.3s ease;
}

.placeholder-content:hover {
  opacity: 0.8;
  transform: translateY(-2px);
}

.placeholder-icon {
  width: 48px;
  height: 48px;
  color: #94a3b8;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 2px dashed #e2e8f0;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s ease;
}

.placeholder-content:hover .placeholder-icon {
  border-color: #cbd5e1;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  color: #64748b;
}

.placeholder-icon svg {
  width: 24px;
  height: 24px;
}

.placeholder-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.placeholder-title {
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
  margin: 0;
}

.placeholder-desc {
  font-size: 12px;
  color: #94a3b8;
  margin: 0;
  line-height: 1.4;
}
</style>