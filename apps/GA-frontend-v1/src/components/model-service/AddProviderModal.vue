<template>
  <a-modal
    v-model:open="visible"
    title="添加模型服务"
    :footer="null"
    width="430px"
    :maskClosable="false"
    class="provider-modal"
    centered
    @cancel="handleCancel"
  >
    <div class="provider-form">
      <div class="form-item avatar-section">
        <a-dropdown :trigger="['click']" placement="bottom" overlay-class-name="avatar-dropdown">
          <div class="avatar-container" @click="e => e.preventDefault()">
            <div 
              class="avatar-display"
              :class="{ 'with-image': formData.avatar }"
              :style="
                (formData.providerIcon || (formData.name && (formData.name.includes('硅基流动') || formData.name.includes('阿里云百炼') || formData.name.includes('百度智能云'))))
                  ? { backgroundColor: 'transparent' }
                  : (formData.avatar ? { backgroundColor: '#ffffff' } : { backgroundColor: formData.backgroundColor })
              "
            >
              <!-- 优先显示供应商图标，其次显示上传图片，最后显示首字母 -->
              <SiliconCloudIcon v-if="formData.providerIcon === 'siliconcloud' || (formData.name && formData.name.includes('硅基流动'))" class="avatar-icon" />
              <BaiLianIcon v-else-if="formData.providerIcon === 'bailian' || (formData.name && formData.name.includes('阿里云百炼'))" class="avatar-icon" />
              <BaiduCloudIcon v-else-if="formData.providerIcon === 'baiducloud' || (formData.name && formData.name.includes('百度智能云'))" class="avatar-icon" />
              <img v-else-if="formData.avatar" :src="formData.avatar" class="avatar-image" alt=""/>
              <span v-else style="color: white;">{{ formData.icon }}</span>
            </div>
          </div>
          <template #overlay>
            <a-menu>
              <a-menu-item key="upload" @click="triggerFileInput">
                <span class="dropdown-option">图片上传</span>
              </a-menu-item>
              <a-menu-item key="reset" @click="resetAvatar">
                <span class="dropdown-option">重置头像</span>
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
        <!-- 隐藏的文件输入元素 -->
        <input 
          type="file" 
          ref="fileInputRef" 
          style="display: none;" 
          accept="image/*" 
          @change="handleFileUpload" 
        />
        <input 
          type="file" 
          ref="jsonFileInputRef" 
          style="display: none;" 
          accept="application/json,.json" 
          @change="handleJsonImport" 
        />
      </div>
      
      <div class="form-item">
        <div class="form-label">模型服务名称</div>
        <a-input 
          v-model:value="formData.name" 
          placeholder="例如：硅基流动、阿里云百炼、百度智能云"
          :status="showNameError ? 'error' : undefined"
        />
        <div v-if="showNameError" class="form-error">请输入模型服务名称</div>
      </div>
      
      <div class="form-item">
        <div class="form-label">模型数据格式</div>
        <a-select v-model:value="formData.type" style="width: 100%">
          <a-select-option value="OpenAI">OpenAI</a-select-option>
        </a-select>
      </div>
      
      <div class="form-actions">
        <div class="actions-left">
          <button class="custom-btn cancel-btn" @click="triggerJsonImport">导入配置</button>
        </div>
        <div class="actions-right">
          <button class="custom-btn cancel-btn" @click="handleCancel">取消</button>
          <button class="custom-btn confirm-btn" @click="handleConfirm">确定</button>
        </div>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { ImageCompressor } from '@/utils/ImageCompressor';
import BaiLianIcon from '@/components/icons/llm/bailian.vue';
import NotificationService from '@/utils/NotificationService';
import BaiduCloudIcon from '@/components/icons/llm/baiducloud.vue';
import SiliconCloudIcon from '@/components/icons/llm/siliconcloud.vue';
import type { ProviderFormData, ServiceData, ModelGroup } from '@/components/model-service/types';

interface Props {
  open: boolean;
  avatarColors: string[];
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'confirm', data: ProviderFormData): void;
  (e: 'cancel'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const showNameError = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const jsonFileInputRef = ref<HTMLInputElement | null>(null);
const importedServiceData = ref<ServiceData | null>(null);

const formData = ref<ProviderFormData>({
  name: '',
  type: 'OpenAI',
  icon: 'P',
  avatar: '',
  backgroundColor: '',
  providerIcon: undefined
});

// 生成随机颜色
const getRandomColor = () => {
  const randomIndex = Math.floor(Math.random() * props.avatarColors.length);
  return props.avatarColors[randomIndex];
};

// 监听props变化
watch(() => props.open, (newVal) => {
  visible.value = newVal;
  if (newVal) {
    resetForm();
  }
});

// 监听visible变化
watch(visible, (newVal) => {
  emit('update:open', newVal);
});

// 监听名称变化更新头像文字（当未自动显示图标时）
watch(() => formData.value.name, (newName) => {
  if (!formData.value.avatar && newName) {
    formData.value.icon = newName.charAt(0).toUpperCase();
    // 同步 providerIcon
    formData.value.providerIcon = resolveProviderIcon(newName);
  }
});

const resetForm = () => {
  formData.value = {
    name: '',
    type: 'OpenAI',
    icon: 'P',
    avatar: '',
    backgroundColor: getRandomColor(),
    providerIcon: undefined
  };
  showNameError.value = false;
  if (fileInputRef.value) {
    fileInputRef.value.value = '';
  }
  if (jsonFileInputRef.value) {
    jsonFileInputRef.value.value = '';
  }
  importedServiceData.value = null;
};

const triggerFileInput = () => {
  if (fileInputRef.value) {
    fileInputRef.value.click();
  }
};

const triggerJsonImport = () => {
  if (jsonFileInputRef.value) {
    jsonFileInputRef.value.click();
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
  formData.value.icon = formData.value.name.charAt(0).toUpperCase() || 'P';
};

const validateForm = () => {
  if (!formData.value.name.trim()) {
    showNameError.value = true;
    return false;
  }
  showNameError.value = false;
  return true;
};

// 根据名称解析提供商图标类型
const resolveProviderIcon = (name: string): 'siliconcloud' | 'bailian' | 'baiducloud' | undefined => {
  if (!name) return undefined;
  if (name.includes('硅基流动')) return 'siliconcloud';
  if (name.includes('阿里云百炼')) return 'bailian';
  if (name.includes('百度智能云')) return 'baiducloud';
  return undefined;
};

const handleConfirm = () => {
  if (validateForm()) {
    // 如果没有设置图标，使用名称的第一个字符
    if (!formData.value.icon && !formData.value.avatar) {
      formData.value.icon = formData.value.name.charAt(0).toUpperCase();
    }
    const providerIcon = resolveProviderIcon(formData.value.name);
    emit('confirm', { ...formData.value, providerIcon, serviceData: importedServiceData.value ?? undefined });
  }
};

const handleCancel = () => {
  visible.value = false;
  emit('cancel');
};

// 处理JSON导入
const handleJsonImport = async (event: Event) => {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    const file = target.files[0];
    try {
      const text = await file.text();
      const data = JSON.parse(text);

      // 基础类型判断：若看起来是MCP服务器配置，则阻止在模型服务模态导入
      const looksLikeMcpServer = !!data.server
        || !!data.url
        || Array.isArray(data.headers)
        || (data.server && (data.server.url || data.server.type))
        || data.type === 'sse' || data.type === 'streamableHttp';
      if (looksLikeMcpServer) {
        NotificationService.error('检测到MCP服务器配置，请在“MCP服务器”页面导入该JSON');
        return;
      }

      // 支持两种结构：{ name, type, provider, config } 或扁平 { name, apiKey, apiUrl, models, ... }
      const name: string = data.name || data.provider?.name || '';
      if (!name) {
        NotificationService.error('导入失败：缺少服务名称');
        return;
      }

      let serviceData: ServiceData;
      if (data.config && typeof data.config === 'object') {
        serviceData = data.config as ServiceData;
      } else {
        const modelsRaw = data.models || {};
        const modelsMap: Record<string, ModelGroup> = Array.isArray(modelsRaw)
          ? (modelsRaw as ModelGroup[]).reduce((acc: Record<string, ModelGroup>, g: ModelGroup) => { acc[g.id] = g; return acc; }, {})
          : modelsRaw;

        serviceData = {
          apiKey: data.apiKey || '',
          apiUrl: data.apiUrl || '',
          models: modelsMap,
          avatar: data.avatar,
          backgroundColor: data.backgroundColor,
          type: data.type || 'OpenAI',
          noApiKeyRequired: data.noApiKeyRequired || false,
          providerIcon: data.providerIcon
        };
      }

      const providerInfo = data.provider || {};
      const providerIcon = providerInfo.providerIcon || serviceData.providerIcon || resolveProviderIcon(name);
      const avatar = providerInfo.avatar || serviceData.avatar || '';
      const backgroundColor = providerInfo.backgroundColor || serviceData.backgroundColor || getRandomColor();
      const iconText = providerInfo.iconText || name.charAt(0).toUpperCase();

      formData.value.name = name;
      formData.value.type = data.type || 'OpenAI';
      formData.value.icon = iconText;
      formData.value.avatar = avatar || '';
      formData.value.backgroundColor = avatar ? '#ffffff' : backgroundColor;
      formData.value.providerIcon = providerIcon;

      serviceData.providerIcon = providerIcon;
      importedServiceData.value = serviceData;
      // 必填项检查与提示
      const warnings: string[] = [];
      const hasApiUrl = !!serviceData.apiUrl && serviceData.apiUrl.trim().length > 0;
      const hasModels = serviceData.models && Object.keys(serviceData.models).length > 0;
      if (!hasApiUrl && !hasModels) warnings.push('apiUrl 或 models');
      if (!serviceData.noApiKeyRequired && !(serviceData.apiKey && serviceData.apiKey.trim())) warnings.push('apiKey');
      if (warnings.length) {
        NotificationService.warning(`JSON缺少关键配置：${warnings.join(', ')}。请补齐后再保存或测试`);
      } else {
        NotificationService.success('配置已导入');
      }
    } catch (error) {
      console.error('导入配置失败:', error);
      NotificationService.error('导入配置失败，请检查文件格式');
    }
  }
};
</script>

<style scoped>
.provider-form {
  padding: 0 10px;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  margin-bottom: 8px;
  font-weight: 500;
}

.avatar-section {
  display: flex;
  justify-content: center;
  margin: 0 0 24px;
}

.avatar-container {
  cursor: pointer;
}

.avatar-display {
  margin-top: 10px;
  width: 80px;
  height: 80px;
  background-color: #e9f0ff;
  border-radius: 22px;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 28px;
  font-weight: bold;
  color: white;
  border: 1px solid transparent;
  overflow: hidden;
}

.avatar-icon {
  width: 80px;
  height: 80px;
}

.avatar-image {
  width: 100%;
  height: 100%;
  border-radius: 15px;
  object-fit: cover;
}

.dropdown-option {
  display: block;
  padding: -3px 0;
  color: #333;
  font-size: 14px;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
}

.actions-right {
  display: flex;
  gap: 8px;
}

.custom-btn {
  min-width: 75px;
  border-radius: 10px;
  height: 32px;
  font-size: 13px;
  font-weight: 400;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  cursor: pointer;
  transition: all 0.3s;
}

.cancel-btn {
  background-color: #f5f5f5;
  border: none;
  color: #1a1a1a;
}

.cancel-btn:hover {
  background-color: #e6e6e6;
  color: #1a1a1a;
  border-color: none;
}

.confirm-btn {
  background: #1677ff;
  color: #ffffff;
  border: none;
}

.confirm-btn:hover {
  background-color: #4096ff;
}

.form-error {
  color: #ff4d4f;
  font-size: 12px;
  margin-top: 4px;
}

:deep(.avatar-dropdown) {
  min-width: 100px;
}
</style>