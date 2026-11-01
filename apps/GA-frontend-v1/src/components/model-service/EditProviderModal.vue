<template>
  <a-modal
    v-model:open="visible"
    title="编辑模型服务"
    :footer="null"
    width="430px"
    :maskClosable="false"
    class="provider-modal"
    style="top: 220px"
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
        <a-button class="custom-btn cancel-btn" @click="handleCancel">取消</a-button>
        <a-button class="custom-btn confirm-btn" @click="handleConfirm">保存</a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { ImageCompressor } from '@/utils/ImageCompressor';
import NotificationService from '@/utils/NotificationService';
import SiliconCloudIcon from '@/components/icons/llm/siliconcloud.vue';
import BaiLianIcon from '@/components/icons/llm/bailian.vue';
import BaiduCloudIcon from '@/components/icons/llm/baiducloud.vue';

interface EditProviderFormData {
  name: string;
  type: string;
  icon: string;
  avatar: string;
  backgroundColor: string;
  originalName: string;
  providerIcon?: 'siliconcloud' | 'bailian' | 'baiducloud';
}

interface ProviderData {
  name: string;
  iconText: string;
  avatar?: string;
  backgroundColor?: string;
  providerIcon?: 'siliconcloud' | 'bailian' | 'baiducloud';
}

interface Props {
  open: boolean;
  provider: ProviderData | null;
  avatarColors: string[];
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'confirm', data: EditProviderFormData): void;
  (e: 'cancel'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const showNameError = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);

const formData = ref<EditProviderFormData>({
  name: '',
  type: 'OpenAI',
  icon: 'P',
  avatar: '',
  backgroundColor: '',
  originalName: '',
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
  if (newVal && props.provider) {
    formData.value = {
      name: props.provider.name,
      type: 'OpenAI',
      icon: props.provider.iconText || props.provider.name.charAt(0).toUpperCase(),
      avatar: props.provider.avatar || '',
      backgroundColor: props.provider.backgroundColor || getRandomColor(),
      originalName: props.provider.name,
      providerIcon: props.provider?.providerIcon
    };
  }
});

// 监听visible变化
watch(visible, (newVal) => {
  emit('update:open', newVal);
});

// 监听名称变化更新头像文字和提供商图标
watch(() => formData.value.name, (newName) => {
  if (!formData.value.avatar && newName) {
    formData.value.icon = newName.charAt(0).toUpperCase();
  }
  formData.value.providerIcon = resolveProviderIcon(newName);
});

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
    if (!formData.value.icon && !formData.value.avatar) {
      formData.value.icon = formData.value.name.charAt(0).toUpperCase();
    }
    const providerIcon = resolveProviderIcon(formData.value.name);
    emit('confirm', { ...formData.value, providerIcon });
  }
};

const handleCancel = () => {
  visible.value = false;
  showNameError.value = false;
  emit('cancel');
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
  justify-content: flex-end;
  margin-top: 32px;
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
  color: #ffffff;
}

.cancel-btn {
  border-color: #d9d9d9;
}

.confirm-btn {
  background-color: #1677ff;
  border-color: #1677ff;
}

.form-error {
  color: #ff4d4f;
  font-size: 12px;
  margin-top: 4px;
}

:deep(.avatar-dropdown) {
  min-width: 100px;
}

:deep(.confirm-btn:hover) {
  background-color: #4096ff;
  border-color: #4096ff;
}
</style>

<style>
.provider-modal .ant-modal-content {
  border-radius: 20px !important;
}
</style>