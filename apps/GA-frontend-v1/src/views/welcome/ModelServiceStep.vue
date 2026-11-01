<template>
  <!-- 第二步：配置模型服务页面 -->
  <div class="step-content" style="margin-top: 50px;">
    <!-- 进度指示器 -->
    <div class="progress-section" :class="{ 'animate': showContent }">
      <div class="progress-dots">
        <div class="dot completed"></div>
        <div class="dot-line"></div>
        <div class="dot active"></div>
        <div class="dot-line"></div>
        <div class="dot"></div>
        <div class="dot-line"></div>
        <div class="dot"></div>
      </div>
      <div class="progress-text">配置模型服务</div>
    </div>

    <!-- 标题区域 -->
    <div class="title-section" :class="{ 'animate': showContent }">
      <h1 class="setup-title">添加模型服务</h1>
      <p class="setup-description">
        配置您的AI模型服务提供商，开始使用MCP Host
      </p>
    </div>

    <!-- 表单区域 -->
    <div class="form-section" :class="{ 'animate': showContent }">
      <a-form :model="formData" :rules="rules" ref="formRef" layout="vertical" class="setup-form">
        <!-- 服务商头像 -->
        <div class="avatar-section">
          <a-dropdown :trigger="['click']" placement="bottom">
            <div class="avatar-container">
              <div
                class="avatar-display"
                :class="{ 'with-image': formData.avatar, 'no-border': formData.providerIcon && !formData.avatar }"
                :style="formData.avatar ? { backgroundColor: '#ffffff' } : { backgroundColor: formData.providerIcon ? 'transparent' : formData.backgroundColor }"
              >
                <img v-if="formData.avatar" :src="formData.avatar" class="avatar-image" alt="" />
                <SiliconCloudIcon v-else-if="formData.providerIcon === 'siliconcloud'" class="provider-icon" />
                <BaiLianIcon v-else-if="formData.providerIcon === 'bailian'" class="provider-icon" />
                <BaiduCloudIcon v-else-if="formData.providerIcon === 'baiducloud'" class="provider-icon" />
                <span v-else class="avatar-text">{{ formData.icon }}</span>
              </div>
            </div>
            <template #overlay>
              <a-menu>
                <a-menu-item key="upload" @click="triggerFileInput">
                  <span>上传图片</span>
                </a-menu-item>
                <a-menu-item key="reset" @click="resetAvatar">
                  <span>重置头像</span>
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
          <input type="file" ref="fileInputRef" style="display: none;" accept="image/*" @change="handleFileUpload" />
        </div>

        <!-- 服务商名称 -->
        <a-form-item label="服务商名称" name="name" required>
          <a-input v-model:value="formData.name" placeholder="例如：硅基流动、阿里云百炼、百度智能云" size="large" autocomplete="username" />
        </a-form-item>

        <!-- API密钥 -->
        <a-form-item label="API密钥" name="apiKey" required>
          <a-input-password
            v-model:value="formData.apiKey"
            placeholder="请输入API密钥"
            size="large"
            :disabled="formData.noApiKeyRequired"
            autocomplete="current-password"
            id="form_item_apiKey_input"
          />
          <a-form-item-rest>
            <a-checkbox v-model:checked="formData.noApiKeyRequired" style="margin-top: 8px;" id="form_item_apiKey_checkbox">
              无需API密钥（私有化部署模型）
            </a-checkbox>
          </a-form-item-rest>
        </a-form-item>

        <!-- API地址 -->
        <a-form-item label="API地址" name="apiUrl" required>
          <a-input v-model:value="formData.apiUrl" placeholder="例如：https://api.openai.com" size="large" autocomplete="url" />
          <a-form-item-rest>
            <div class="api-preview" v-if="formData.apiUrl">
              <span class="preview-label">预览：</span>
              <span class="preview-url" :title="apiPreviewUrl">{{ apiPreviewUrl }}</span>
            </div>
            <div class="api-preview" v-else>
              <span class="preview-label">提示：</span>
              <span class="preview-url">{{ '请输入模型服务地址' }}</span>
            </div>
          </a-form-item-rest>
        </a-form-item>

        <!-- 模型配置 -->
        <a-form-item label="模型ID" name="modelId" required>
          <a-input v-model:value="formData.modelId" placeholder="模型ID，例如：gpt-4o" size="large" id="form_item_model_id" />
        </a-form-item>
      </a-form>
    </div>

    <!-- 按钮区域 -->
    <div class="action-section" :class="{ 'animate': showContent }">
      <div class="nav-pill">
        <a-tooltip title="返回上一步" placement="top">
          <a-button type="text" shape="circle" class="nav-icon-btn" @click="handleCancel">
            <template #icon><ArrowLeftOutlined /></template>
          </a-button>
        </a-tooltip>
        <div class="nav-divider"></div>
        <a-button type="primary" shape="round" class="nav-primary-btn" @click="handleNext">
          下一步
          <ArrowRightOutlined />
        </a-button>
      </div>
      <div class="sub-actions">
        <a class="skip-link" @click="triggerJsonImport">导入模型服务配置</a>
        <input type="file" ref="jsonFileInputRef" style="display: none;" accept="application/json,.json" @change="handleJsonImport" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, toRefs } from 'vue';
import type { FormInstance } from 'ant-design-vue';
import { ArrowLeftOutlined, ArrowRightOutlined } from '@ant-design/icons-vue';
import NotificationService from '@/utils/NotificationService';
import { ImageCompressor } from '@/utils/ImageCompressor';
import SiliconCloudIcon from '@/components/icons/llm/siliconcloud.vue';
import BaiLianIcon from '@/components/icons/llm/bailian.vue';
import BaiduCloudIcon from '@/components/icons/llm/baiducloud.vue';

type ProviderIcon = 'siliconcloud' | 'bailian' | 'baiducloud';
interface WelcomeFormData {
  name: string;
  icon: string;
  avatar: string;
  backgroundColor: string;
  apiKey: string;
  apiUrl: string;
  modelId: string;
  modelName: string;
  noApiKeyRequired: boolean;
  providerIcon?: ProviderIcon;
  models?: Record<string, any>;
}

const props = defineProps<{ showContent: boolean; initialData?: WelcomeFormData }>();
const { showContent, initialData } = toRefs(props);
const emit = defineEmits<{ (e: 'prev'): void; (e: 'next', data: WelcomeFormData): void }>();

const formRef = ref<FormInstance>();
const fileInputRef = ref<HTMLInputElement | null>(null);
const jsonFileInputRef = ref<HTMLInputElement | null>(null);

// 用于生成随机颜色的颜色数组
const avatarColors = [
  '#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1',
  '#13c2c2', '#eb2f96', '#fa541c', '#a0d911', '#2f54eb'
];

// 模型服务表单数据
const formData = ref<WelcomeFormData>({
  name: '',
  icon: 'A',
  avatar: '',
  backgroundColor: '',
  apiKey: '',
  apiUrl: '',
  modelId: '',
  modelName: '',
  noApiKeyRequired: false,
  providerIcon: undefined,
  models: undefined
});

watch(initialData, (val) => {
  if (val) {
    formData.value = { ...formData.value, ...val };
  }
}, { deep: true, immediate: true });

// 模型服务表单验证规则
const rules = reactive({
  name: [
    { required: true, message: '请输入服务商名称' }
  ],
  apiKey: [
    { required: true, message: '请输入API密钥或勾选"无需API密钥"' }
  ],
  apiUrl: [
    { required: true, message: '请输入API地址' }
  ],
  modelId: [
    { required: true, message: '请输入模型ID' }
  ],
  modelName: [
    { required: true, message: '请输入模型名称' }
  ]
});

// 生成随机颜色
const getRandomColor = () => {
  const randomIndex = Math.floor(Math.random() * avatarColors.length);
  return avatarColors[randomIndex];
};

// 根据服务商名称解析供应商图标类型
const resolveProviderIcon = (name: string): ProviderIcon | undefined => {
  if (!name) return undefined;
  if (name.includes('硅基流动')) return 'siliconcloud';
  if (name.includes('阿里云百炼')) return 'bailian';
  if (name.includes('百度智能云')) return 'baiducloud';
  return undefined;
};

// API地址预览
const apiPreviewUrl = computed(() => {
  let base = formData.value.apiUrl?.trim() || '';
  if (!base) return '';

  while (base.endsWith('/')) base = base.slice(0, -1);

  if (base.includes('/chat/completions')) {
    if (base.endsWith('/chat/completions')) {
      return base;
    }
    const index = base.indexOf('/chat/completions');
    const baseUrl = base.substring(0, index);
    if (baseUrl.endsWith('/v1') || baseUrl.includes('/v1/')) {
      return baseUrl + '/chat/completions';
    } else {
      return baseUrl + '/v1/chat/completions';
    }
  } else if (base.endsWith('/v1/chat')) {
    return base + '/completions';
  } else if (base.endsWith('/v1')) {
    return base + '/chat/completions';
  }
  return base + '/v1/chat/completions';
});

// 监听模型ID变化，同步更新模型名称
watch(() => formData.value.modelId, (newModelId) => {
  if (newModelId) {
    formData.value.modelName = newModelId;
  }
});

// 监听名称变化更新头像文字
watch(() => formData.value.name, (newName) => {
  if (!formData.value.avatar && newName) {
    formData.value.icon = newName.charAt(0).toUpperCase();
  }
  formData.value.providerIcon = resolveProviderIcon(newName);
});

// 监听无需API密钥选项
watch(() => formData.value.noApiKeyRequired, (newValue) => {
  if (newValue) {
    formData.value.apiKey = 'sk-no-key';
    // 当勾选"无需API密钥"时，清除API密钥字段的验证错误
    if (formRef.value) {
      formRef.value.clearValidate('apiKey');
    }
  } else if (formData.value.apiKey === 'sk-no-key') {
    formData.value.apiKey = '';
    // 当取消勾选时，重新验证API密钥字段
    if (formRef.value) {
      formRef.value.validateFields(['apiKey']);
    }
  }
});

// 文件上传处理
const triggerFileInput = () => {
  if (fileInputRef.value) {
    fileInputRef.value.click();
  }
};

const handleFileUpload = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    const file = target.files[0];

    try {
      // 使用ImageCompressor压缩图片
      const compressedDataUrl = await ImageCompressor.compress(file, {
        maxSize: 1024,
        quality: 0.7,
        smallFileThreshold: 100 * 1024 // 100KB
      });

      formData.value.avatar = compressedDataUrl;
    } catch (error) {
      NotificationService.error(error instanceof Error ? error.message : '图片上传失败');
    }
  }
};

const resetAvatar = () => {
  formData.value.avatar = '';
  formData.value.icon = formData.value.name.charAt(0).toUpperCase() || 'A';
  formData.value.providerIcon = resolveProviderIcon(formData.value.name);
  formData.value.backgroundColor = getRandomColor();
};

onMounted(() => {
  if (!formData.value.backgroundColor && !formData.value.avatar) {
    formData.value.backgroundColor = getRandomColor();
  }
});

// 上一步
function handleCancel() {
  emit('prev');
}

// 下一步
async function handleNext() {
  if (!formRef.value) return;

  try {
    // 清除表单数据前后的空格
    formData.value.name = formData.value.name.trim();
    formData.value.apiKey = formData.value.apiKey.trim();
    formData.value.apiUrl = formData.value.apiUrl.trim();
    formData.value.modelId = formData.value.modelId.trim();
    formData.value.modelName = formData.value.modelName.trim();

    // 动态设置API密钥字段的验证规则
    // 如果用户勾选了"无需API密钥"，则API密钥字段不需要验证
    const originalApiKeyRules = [...rules.apiKey];
    if (formData.value.noApiKeyRequired) {
      rules.apiKey = [];
    }

    await formRef.value.validate();

    // 恢复原始验证规则
    rules.apiKey = originalApiKeyRules;

    emit('next', { ...formData.value });
  } catch (error) {
    console.error('表单验证失败:', error);
  }
}

// 触发导入 JSON
const triggerJsonImport = () => {
  if (jsonFileInputRef.value) {
    jsonFileInputRef.value.click();
  }
};

// 处理 JSON 导入到模型服务欢迎表单
const handleJsonImport = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  try {
    const file = target.files && target.files[0];
    if (!file) return;
    const text = await file.text();
    const data = JSON.parse(text);

    // 若看起来是 MCP 服务器配置，则阻止在此导入
    const looksLikeMcpServer = !!data.server
      || !!data.url
      || Array.isArray(data.headers)
      || (data.server && (data.server.url || data.server.type))
      || data.type === 'sse' || data.type === 'streamableHttp';
    if (looksLikeMcpServer) {
      NotificationService.error('检测到MCP服务器配置，请在“MCP服务器”页面或欢迎页第三步导入');
      return;
    }

    // 支持两种结构：{ name, type, provider, config } 或扁平 { name, apiKey, apiUrl, models, ... }
    const name: string = data.name || data.provider?.name || '';
    if (!name) {
      NotificationService.error('导入失败：缺少服务名称');
      return;
    }

    // 提取服务数据
    const configObj = data.config && typeof data.config === 'object' ? data.config : null;
    const modelsRaw = (configObj ? configObj.models : (data.models || {})) || {};

    // 归并 models 为对象映射
    const modelsMap: Record<string, any> = Array.isArray(modelsRaw)
      ? (modelsRaw as any[]).reduce((acc: Record<string, any>, g: any) => { acc[g.id] = g; return acc; }, {})
      : modelsRaw;

    // 选择一个模型ID作为当前模型（取第一个组的第一个模型）
    let selectedModelId = '';
    const groupKeys = Object.keys(modelsMap);
    if (groupKeys.length) {
      const firstGroup = modelsMap[groupKeys[0]];
      if (firstGroup?.models && firstGroup.models.length) {
        selectedModelId = firstGroup.models[0].id || firstGroup.models[0].name || '';
      } else {
        selectedModelId = firstGroup?.id || firstGroup?.name || '';
      }
    }

    const apiKey = (configObj ? configObj.apiKey : data.apiKey) || '';
    const apiUrl = (configObj ? configObj.apiUrl : data.apiUrl) || '';
    const noApiKeyRequired = !!(configObj ? configObj.noApiKeyRequired : data.noApiKeyRequired);

    // 供应商图标与头像
    const providerInfo = data.provider || {};
    const providerIcon = providerInfo.providerIcon || (configObj ? configObj.providerIcon : data.providerIcon) || resolveProviderIcon(name);
    const avatar = providerInfo.avatar || (configObj ? configObj.avatar : data.avatar) || '';
    const backgroundColor = providerInfo.backgroundColor || (configObj ? configObj.backgroundColor : data.backgroundColor) || getRandomColor();

    // 填充表单
    formData.value.name = name;
    formData.value.icon = (providerInfo.iconText || name.charAt(0).toUpperCase());
    formData.value.avatar = avatar;
    formData.value.backgroundColor = avatar ? '#ffffff' : backgroundColor;
    formData.value.providerIcon = providerIcon as ProviderIcon | undefined;
    formData.value.apiKey = noApiKeyRequired ? 'sk-no-key' : (apiKey || '');
    formData.value.apiUrl = apiUrl || '';
    formData.value.noApiKeyRequired = !!noApiKeyRequired;
    formData.value.modelId = selectedModelId || (data.modelId || '');
    formData.value.modelName = formData.value.modelId || '';
    formData.value.models = modelsMap;

    // 校验与提示
    const warnings: string[] = [];
    const hasApiUrl = !!formData.value.apiUrl && formData.value.apiUrl.trim().length > 0;
    const hasModelId = !!formData.value.modelId && formData.value.modelId.trim().length > 0;
    if (!hasApiUrl) warnings.push('apiUrl');
    if (!hasModelId && !Object.keys(modelsMap).length) warnings.push('modelId/models');
    if (!formData.value.noApiKeyRequired && !(formData.value.apiKey && formData.value.apiKey.trim())) warnings.push('apiKey');
    if (warnings.length) {
      NotificationService.warning(`JSON缺少关键配置：${warnings.join(', ')}。请补齐后再继续`);
    } else {
      NotificationService.success('配置已导入');
    }
  } catch (error) {
    console.error('导入配置失败:', error);
    NotificationService.error('导入配置失败，请检查文件格式');
  } finally {
    if (target) target.value = '';
  }
};
</script>

<style scoped>
@import '@/assets/styles/welcome.css';
</style>
