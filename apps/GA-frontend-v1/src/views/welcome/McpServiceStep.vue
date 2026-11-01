<template>
  <!-- 第三步：配置MCP服务页面 -->
  <div class="step-content">
    <!-- 进度指示器 -->
    <div class="progress-section" :class="{ 'animate': showContent }">
      <div class="progress-dots">
        <div class="dot completed"></div>
        <div class="dot-line completed"></div>
        <div class="dot completed"></div>
        <div class="dot-line"></div>
        <div class="dot active"></div>
        <div class="dot-line"></div>
        <div class="dot"></div>
      </div>
      <div class="progress-text">配置MCP服务</div>
    </div>

    <!-- 标题区域 -->
    <div class="title-section" :class="{ 'animate': showContent }">
      <h1 class="setup-title">添加MCP服务器</h1>
      <p class="setup-description">添加并配置您的MCP服务器，扩展AI能力</p>
    </div>

    <!-- 表单区域 -->
    <div class="form-section" :class="{ 'animate': showContent }">
      <a-form :model="mcpFormData" :rules="mcpRules" ref="mcpFormRef" layout="vertical" class="setup-form">
        <!-- 服务器名称 -->
        <a-form-item label="服务器名称" name="name" required>
          <a-input v-model:value="mcpFormData.name" placeholder="请输入服务器名称" size="large" />
        </a-form-item>

        <!-- 服务器描述 -->
        <a-form-item label="服务器描述" name="description">
          <a-textarea v-model:value="mcpFormData.description" placeholder="请输入服务器描述" :auto-size="{ minRows: 1, maxRows: 2 }" />
        </a-form-item>

        <!-- 服务器类型 -->
        <a-form-item label="服务器类型" name="type" required>
          <a-select v-model:value="mcpFormData.type">
            <a-select-option value="sse">服务器发送事件 (SSE)</a-select-option>
            <a-select-option value="streamableHttp">可流式传输的HTTP</a-select-option>
          </a-select>
        </a-form-item>

        <!-- 服务器URL -->
        <a-form-item label="服务器URL" name="url" required>
          <a-input v-model:value="mcpFormData.url" placeholder="请输入服务器URL" />
        </a-form-item>

        <!-- 请求头 -->
        <a-form-item label="请求头" name="headersText">
          <a-textarea v-model:value="mcpFormData.headersText" placeholder="请输入请求头，格式为：名称=值" :auto-size="{ minRows: 2, maxRows: 2 }" />
        </a-form-item>

        <!-- 超时设置 -->
        <a-form-item label="超时（秒）" name="timeout">
          <a-input-number v-model:value="mcpFormData.timeout" :min="1" :max="300" :step="1" style="width: 100%" size="large" />
        </a-form-item>
      </a-form>
    </div>

    <!-- 按钮区域 -->
    <div class="action-section" :class="{ 'animate': showContent }">
      <div class="nav-pill">
        <a-tooltip title="返回上一步" placement="top">
          <a-button type="text" shape="circle" class="nav-icon-btn" @click="handleMcpCancel">
            <template #icon><ArrowLeftOutlined /></template>
          </a-button>
        </a-tooltip>
        <div class="nav-divider"></div>
        <a-button type="primary" shape="round" class="nav-primary-btn" @click="handleMcpNext">
          下一步
          <ArrowRightOutlined />
        </a-button>
      </div>
      <div class="secondary-actions">
        <a class="skip-link" @click="triggerJsonImport">导入MCP服务配置</a>
        <a-divider type="vertical" />
        <a class="skip-link" @click="skipMcpConfig">跳过此步骤，稍后配置</a>
        <input type="file" ref="jsonInputRef" style="display: none;" accept="application/json,.json" @change="handleJsonImport" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, toRefs, watch } from 'vue';
import type { FormInstance } from 'ant-design-vue';
import { ArrowLeftOutlined, ArrowRightOutlined } from '@ant-design/icons-vue';
import NotificationService from '@/utils/NotificationService';

const props = defineProps<{ showContent: boolean; initialData?: { name: string; description: string; type: string; url: string; headersText: string; timeout: number } }>();
const { showContent, initialData } = toRefs(props);
const emit = defineEmits<{
  (e: 'prev'): void;
  (e: 'next', data: { name: string; description: string; type: string; url: string; headersText: string; timeout: number }): void;
  (e: 'skip'): void;
}>();

const mcpFormRef = ref<FormInstance>();
const jsonInputRef = ref<HTMLInputElement | null>(null);
const mcpFormData = ref({
  name: '',
  description: '',
  type: 'sse',
  url: '',
  headersText: '',
  timeout: 60
});

watch(initialData, (val) => {
  if (val) {
    mcpFormData.value = { ...mcpFormData.value, ...val };
  }
}, { deep: true, immediate: true });

const mcpRules = reactive({
  name: [
    { required: true, message: '请输入服务器名称' }
  ],
  url: [
    { required: true, message: '请输入服务器URL' }
  ],
  type: [
    { required: true, message: '请选择服务器类型' }
  ]
});

function handleMcpCancel() {
  emit('prev');
}

async function handleMcpNext() {
  if (!mcpFormRef.value) return;

  try {
    // 清除MCP表单数据前后的空格
    mcpFormData.value.name = mcpFormData.value.name.trim();
    mcpFormData.value.description = mcpFormData.value.description.trim();
    mcpFormData.value.url = mcpFormData.value.url.trim();
    mcpFormData.value.headersText = mcpFormData.value.headersText.trim();

    await mcpFormRef.value.validate();

    emit('next', { ...mcpFormData.value });
  } catch (error) {
    console.error('MCP表单验证失败:', error);
  }
}

function skipMcpConfig() {
  emit('skip');
}

// 触发导入 JSON
const triggerJsonImport = () => {
  if (jsonInputRef.value) {
    jsonInputRef.value.click();
  }
};

// 处理 JSON 导入到 MCP 欢迎表单
const handleJsonImport = async (e: Event) => {
  const input = e.target as HTMLInputElement;
  try {
    const file = input.files && input.files[0];
    if (!file) return;
    const text = await file.text();
    const parsed = JSON.parse(text);

    // 若看起来是模型服务配置，则阻止在此导入
    const isModelServiceJson = !!parsed.provider
      || !!(parsed.config && (parsed.config.apiUrl || parsed.config.models || parsed.config.apiKey))
      || parsed.type === 'OpenAI'
      || Array.isArray(parsed.models);
    if (isModelServiceJson) {
      NotificationService.error('检测到模型服务配置，请在“模型服务”页面或欢迎页第二步导入');
      return;
    }

    const rawConfig = parsed.config || parsed.server || parsed;

    mcpFormData.value.name = rawConfig.name || mcpFormData.value.name || '';
    mcpFormData.value.description = rawConfig.description ?? mcpFormData.value.description ?? '';
    mcpFormData.value.type = rawConfig.type || mcpFormData.value.type || 'sse';
    mcpFormData.value.url = rawConfig.url || mcpFormData.value.url || '';
    mcpFormData.value.timeout = typeof rawConfig.timeout === 'number' ? rawConfig.timeout : (mcpFormData.value.timeout ?? 60);

    // 规范化 headers 并填充到文本域，支持对象或数组
    const normalizeHeaders = (source: any): { key: string; value: string }[] => {
      if (!source) return [];
      if (Array.isArray(source)) {
        return source
          .filter((h: any) => h && h.key && h.value)
          .map((h: any) => ({ key: String(h.key), value: String(h.value) }));
      }
      if (typeof source === 'object') {
        return Object.keys(source).map(k => ({ key: k, value: String(source[k]) }));
      }
      return [];
    };

    let headersArr: { key: string; value: string }[] = normalizeHeaders(rawConfig.headers);
    if (!headersArr.length) headersArr = normalizeHeaders(parsed.headers);
    if (!headersArr.length && parsed.config) headersArr = normalizeHeaders(parsed.config.headers);
    if (!headersArr.length && parsed.server) headersArr = normalizeHeaders(parsed.server.headers);
    mcpFormData.value.headersText = headersArr.map(h => `${h.key}: ${h.value}`).join('\n');

    const missing: string[] = [];
    if (!mcpFormData.value.name.trim()) missing.push('name');
    if (!mcpFormData.value.url.trim()) missing.push('url');
    if (!rawConfig.type) missing.push('type');
    if (missing.length) {
      NotificationService.warning(`JSON缺少必要字段：${missing.join(', ')}，请手动补充后再继续`);
    } else {
      NotificationService.success('配置已导入到表单');
    }
  } catch (err) {
    console.error('[Welcome-MCP] 导入配置失败:', err);
    NotificationService.error('导入配置失败，请检查文件结构');
  } finally {
    if (input) input.value = '';
  }
};
</script>

<style scoped>
@import '@/assets/styles/welcome.css';
</style>