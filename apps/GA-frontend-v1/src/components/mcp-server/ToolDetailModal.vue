<template>
  <transition name="tool-modal">
    <div v-if="visible && tool" class="tool-detail-overlay" @click.self="handleCancel">
      <div class="tool-detail-window">
      <div class="tool-top">
        <div class="tool-top-left">
          <div class="tool-mark">
            <span>{{ tool.name.charAt(0).toUpperCase() }}</span>
          </div>
          <div class="tool-top-text">
            <div class="tool-name">{{ tool.name }}</div>
            <div class="tool-id">ID · {{ tool.id }}</div>
          </div>
        </div>
        <div class="tool-top-right">
          <a-button class="tool-close" type="text" @click="handleCancel">
            <template #icon><CloseOutlined/></template>
          </a-button>
        </div>
      </div>

      <div class="tool-info-row">
        <div class="tool-description-card">
          <div class="card-title">描述</div>
          <p class="card-text">{{ getCleanDescription(tool?.description) }}</p>
        </div>
        <div class="tool-summary-card">
          <div class="card-title">概览</div>
          <div class="summary-grid">
            <div class="summary-item">
              <span>参数</span>
              <strong>{{ paramCount }}</strong>
            </div>
            <div class="summary-item">
              <span>必填</span>
              <strong>{{ requiredCount }}</strong>
            </div>
          </div>
        </div>
      </div>

      <div class="tool-body">
        <div v-if="parameters && paramCount > 0" class="params-layout">
          <div class="params-list">
            <div class="list-header">
              <div class="list-title">参数清单</div>
              <div class="list-subtitle">共 {{ paramCount }} 项</div>
            </div>
            <div class="param-cards">
              <div v-for="key in parameterKeys" :key="key" class="param-card">
                <div class="param-card-head">
                  <div class="param-card-name">{{ key }}</div>
                  <div class="param-card-meta">
                    <span class="type-pill">{{ getParamType(key.toString()) }}</span>
                    <span v-if="isParamRequired(key.toString())" class="required-pill">必填</span>
                  </div>
                </div>
                <div class="param-card-desc">{{ getParamDescription(key.toString()) }}</div>
              </div>
            </div>
          </div>
          <div class="params-structure">
            <div class="structure-header">
              <span>参数结构</span>
            </div>
            <pre class="structure-json chat-hljs" v-html="formatToolParameters"></pre>
          </div>
        </div>
        <div v-else-if="loading" class="loading-parameters">
          <a-spin />
          <span>正在加载参数信息...</span>
        </div>
        <div v-else class="no-parameters">
          <span>此工具没有参数信息</span>
        </div>
      </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue';
import hljs from 'highlight.js';
import { CloseOutlined } from '@ant-design/icons-vue';

interface ToolInfo {
  id: string;
  name: string;
  description?: string;
}

interface Props {
  open: boolean;
  tool: ToolInfo | null;
  parameters: Record<string, any> | null;
  loading?: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'cancel'): void;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const emit = defineEmits<Emits>();

const visible = ref(false);

// 监听props变化
watch(() => props.open, (newVal) => {
  visible.value = newVal;
});

// 监听visible变化
watch(visible, (newVal) => {
  emit('update:open', newVal);
});

// 格式化工具参数
const formatToolParameters = computed(() => {
  if (!props.parameters) return '';
  try {
    const jsonStr = JSON.stringify(props.parameters, null, 2);
    // 使用 highlight.js 对 JSON 进行高亮
    return hljs.highlight(jsonStr, { language: 'json' }).value;
  } catch (e) {
    return JSON.stringify(props.parameters);
  }
});

// 获取参数属性
const getParameterProperties = () => {
  if (!props.parameters || !props.parameters.properties) {
    return {};
  }
  return props.parameters.properties;
};

const parameterKeys = computed(() => Object.keys(getParameterProperties() || {}));

const paramCount = computed(() => parameterKeys.value.length);

const requiredCount = computed(() => {
  if (!props.parameters || !Array.isArray(props.parameters.required)) {
    return 0;
  }
  return props.parameters.required.length;
});

// 获取参数类型
const getParamType = (key: string) => {
  if (!props.parameters || !props.parameters.properties || !props.parameters.properties[key]) {
    return '未知';
  }
  
  const param = props.parameters.properties[key];
  
  if (param.type) {
    if (param.type === 'array' && param.items && param.items.type) {
      return `${param.type}<${param.items.type}>`;
    }
    return param.type;
  }
  
  return '未知';
};

// 清理描述中的Args部分
const getCleanDescription = (description?: string): string => {
  if (!description) return '无描述信息';
  
  // 移除Args:及其后面的内容
  const argsIndex = description.indexOf('Args:');
  if (argsIndex !== -1) {
    return description.substring(0, argsIndex).trim();
  }
  
  // 移除其他可能的参数标记
  const argPatterns = [
    'Arguments:',
    'Parameters:',
    'Params:',
    'Input:'
  ];
  
  for (const pattern of argPatterns) {
    const index = description.indexOf(pattern);
    if (index !== -1) {
      return description.substring(0, index).trim();
    }
  }
  
  return description;
};

// 从描述中提取参数解释
const extractArgsExplanation = (description?: string): Record<string, string> => {
  if (!description) return {};
  
  const argsMap: Record<string, string> = {};
  let argsSection = '';
  
  // 查找Args部分
  const argsPatterns = ['Args:', 'Arguments:', 'Parameters:', 'Params:', 'Input:'];
  
  for (const pattern of argsPatterns) {
    const index = description.indexOf(pattern);
    if (index !== -1) {
      argsSection = description.substring(index + pattern.length).trim();
      break;
    }
  }
  
  if (!argsSection) return {};
  
  // 解析Args部分的每一行
  const lines = argsSection.split('\n');
  let currentKey = '';
  
  for (const line of lines) {
    const trimmedLine = line.trim();
    if (!trimmedLine) continue;
    
    // 检查是否是新参数定义（通常是"参数名: 描述"或"参数名 - 描述"的格式）
    const colonMatch = trimmedLine.match(/^(\w+):\s*(.+)$/);
    const dashMatch = trimmedLine.match(/^(\w+)\s+-\s+(.+)$/);
    
    if (colonMatch) {
      currentKey = colonMatch[1];
      argsMap[currentKey] = colonMatch[2];
    } else if (dashMatch) {
      currentKey = dashMatch[1];
      argsMap[currentKey] = dashMatch[2];
    } else if (currentKey) {
      // 如果不是新参数定义，且有当前参数，则将此行添加到当前参数的描述中
      argsMap[currentKey] += ' ' + trimmedLine;
    }
  }
  
  return argsMap;
};

// 获取参数描述，结合API文档和Args中的解释
const getParamDescription = (key: string) => {
  if (!props.parameters || !props.parameters.properties || !props.parameters.properties[key]) {
    return '';
  }
  
  const param = props.parameters.properties[key];
  const apiDesc = param.description || '';
  
  // 获取从描述中提取的Args解释
  const argsExplanations = extractArgsExplanation(props.tool?.description);
  const argsDesc = argsExplanations[key] || '';
  
  // 如果两者都有，则合并显示，否则显示其中一个
  if (apiDesc && argsDesc) {
    return `${apiDesc} - ${argsDesc}`;
  }
  
  return apiDesc || argsDesc || '';
};

// 判断参数是否必填
const isParamRequired = (key: string) => {
  if (!props.parameters || !props.parameters.required) {
    return false;
  }
  
  return props.parameters.required.includes(key);
};

const handleCancel = () => {
  visible.value = false;
  emit('cancel');
};
</script>

<style scoped>
.tool-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(0, 0, 0, 0.45);
}

.tool-detail-window {
  width: min(980px, 96vw);
  max-height: 88vh;
  background: #ffffff;
  border-radius: 22px;
  border: 1px solid #e5e7eb;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  gap: 14px;
  padding: 16px;
  overflow: hidden;
}

.tool-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: 18px;
  background: #f5f6f8;
  border: 1px solid #e5e7eb;
}

.tool-top-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.tool-mark {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e5e7eb;
  color: #374151;
  font-size: 18px;
  font-weight: 600;
  flex-shrink: 0;
}

.tool-top-text {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.tool-name {
  font-size: 16px;
  font-weight: 600;
  color: #374151;
  word-break: break-word;
}

.tool-id {
  font-size: 11px;
  color: #64748b;
}

.tool-top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}


.tool-close {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.tool-close:hover {
  background: rgba(15, 23, 42, 0.05);
}

.tool-close :deep(svg) {
  font-size: 12px;
}

.tool-info-row {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
  gap: 12px;
}

.tool-description-card,
.tool-summary-card {
  padding: 12px 14px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 8px 18px rgba(0, 0, 0, 0.06);
}

.card-title {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 8px;
}

.card-text {
  font-size: 12px;
  line-height: 1.6;
  color: #4b5563;
  margin: 0;
  word-break: break-word;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 10px;
  border-radius: 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 12px;
  color: #64748b;
}

.summary-item strong {
  color: #1f2937;
  font-weight: 600;
}

.tool-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.params-layout {
  display: grid;
  grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.6fr);
  gap: 12px;
  min-height: 0;
  height: 100%;
}

.params-list {
  display: flex;
  flex-direction: column;
  min-height: 0;
  gap: 10px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
}

.list-title {
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.list-subtitle {
  font-size: 11px;
  color: #64748b;
}

.param-cards {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-right: 2px;
}

.param-card {
  border-radius: 14px;
  padding: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.param-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.param-card-name {
  font-size: 12px;
  font-weight: 600;
  color: #1f2937;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
  word-break: break-word;
}

.param-card-meta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
}

.type-pill {
  padding: 2px 6px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #374151;
  border: 1px solid #e5e7eb;
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, Courier, monospace;
}

.required-pill {
  padding: 2px 6px;
  border-radius: 999px;
  background: #fef2f2;
  color: #ef4444;
  border: 1px solid #fecaca;
}

.param-card-desc {
  font-size: 12px;
  color: #475569;
  line-height: 1.55;
  word-break: break-word;
}

.params-structure {
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  border-radius: 18px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.structure-header {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.structure-json {
  flex: 1;
  margin: 0;
  font-family: 'Roboto Mono', Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 12px;
  line-height: 1.6;
  color: #374151;
  white-space: pre-wrap;
  word-break: break-all;
  background: #ffffff;
  border-radius: 14px;
  padding: 14px;
  border: 1px solid #e5e7eb;
  overflow: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.structure-json::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.structure-json::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.structure-json::-webkit-scrollbar-track {
  background-color: transparent;
}

.loading-parameters,
.no-parameters {
  height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #64748b;
  background: #ffffff;
  border-radius: 18px;
  border: 1px dashed #e5e7eb;
}

@media (max-width: 980px) {
  .tool-info-row,
  .params-layout {
    grid-template-columns: 1fr;
  }

  .tool-detail-window {
    max-height: 92vh;
  }
}

.tool-modal-enter-active,
.tool-modal-leave-active {
  transition: opacity 0.3s ease;
}

.tool-modal-enter-from,
.tool-modal-leave-to {
  opacity: 0;
}

.tool-modal-enter-active .tool-detail-window,
.tool-modal-leave-active .tool-detail-window {
  transition: transform 0.3s ease, opacity 0.3s ease;
}

.tool-modal-enter-from .tool-detail-window,
.tool-modal-leave-to .tool-detail-window {
  transform: scale(0.95);
  opacity: 0;
}
</style>
