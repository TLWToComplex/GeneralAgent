<template>
  <a-modal
    v-model:open="visible"
    title="编辑模型"
    :footer="null"
    width="550px"
    :maskClosable="false"
    class="edit-model-modal"
    centered
    @cancel="handleCancel"
  >
    <div class="add-model-form">
      <div class="form-item row-item">
        <div class="form-label required">模型ID</div>
        <div class="form-control" style="display: flex; gap: 8px;">
          <a-input v-model:value="formData.id" disabled style="background:#f5f5f5;" />
          <a-button class="custom-btn cancel-btn copy-btn" @click="handleCopyModelId">复制</a-button>
        </div>
      </div>
      
      <div class="form-item row-item">
        <div class="form-label required">模型名称</div>
        <div class="form-control">
          <a-input v-model:value="formData.name" placeholder="请输入模型名称" />
        </div>
      </div>

      <div class="form-item row-item">
        <div class="form-label required context-size-label">上下文大小</div>
        <div class="form-control">
          <div class="context-size-panel">
            <div class="context-size-input-row">
              <a-input-number
                v-model:value="contextSizeValue"
                :min="1"
                :precision="0"
                class="context-size-number"
                placeholder="请输入上下文长度"
              />
              <a-select v-model:value="contextSizeUnit" class="context-size-unit">
                <a-select-option value="K">K</a-select-option>
                <a-select-option value="M">M</a-select-option>
              </a-select>
            </div>
            <div class="context-size-presets">
              <button
                v-for="preset in contextSizePresets"
                :key="preset.value"
                type="button"
                class="context-size-preset"
                :class="{ active: formData.contextSize === preset.value }"
                @click="selectContextSizePreset(preset.value)"
              >
                {{ preset.label }}
              </button>
            </div>
            <div class="form-help-text">
              建议按模型官方标称填写，保存时会自动换算为整数，例如 1M = 1000000。
            </div>
          </div>
        </div>
      </div>

      <div class="form-item row-item">
        <div class="form-label required">模型类型</div>
        <div class="form-control">
          <div class="model-type-panel">
            <a-checkbox-group
              v-model:value="formData.types"
              class="model-type-options"
              :options="modelTypeOptions"
            />
          </div>
        </div>
      </div>
      
      <div class="form-actions">
        <a-button class="custom-btn cancel-btn" @click="handleCancel">取消</a-button>
        <a-button class="custom-btn confirm-btn" @click="handleConfirm">确定</a-button>
      </div>
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import NotificationService from '@/utils/NotificationService';
import { copyText } from '@/utils/clipboard';
import { MODEL_CONTEXT_SIZE_PRESETS, MODEL_TYPE_OPTIONS, type ContextSizeUnit } from './types';

interface EditModelFormData {
  id: string;
  name: string;
  types: string[];
  contextSize: number;
}

interface ModelData {
  id: string;
  name: string;
  types?: string[];
  contextSize?: number;
}

interface Props {
  open: boolean;
  model: ModelData | null;
}

interface Emits {
  (e: 'update:open', value: boolean): void;
  (e: 'confirm', data: EditModelFormData): void;
  (e: 'cancel'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const visible = ref(false);
const contextSizePresets = MODEL_CONTEXT_SIZE_PRESETS;
const contextSizeValue = ref<number | null>(null);
const contextSizeUnit = ref<ContextSizeUnit>('K');

const formData = ref<EditModelFormData>({
  id: '',
  name: '',
  types: [],
  contextSize: 0
});

const modelTypeOptions = MODEL_TYPE_OPTIONS;

// 监听props变化
watch(() => props.open, (newVal) => {
  visible.value = newVal;
  if (newVal && props.model) {
    formData.value = {
      id: props.model.id,
      name: props.model.name,
      types: props.model.types ? [...props.model.types] : [],
      contextSize: props.model.contextSize || 0
    };
    normalizeContextSizeInputs(props.model.contextSize);
  }
});

// 监听visible变化
watch(visible, (newVal) => {
  emit('update:open', newVal);
});

watch([contextSizeValue, contextSizeUnit], () => {
  syncContextSize();
});

const normalizeContextSizeInputs = (contextSize?: number) => {
  if (contextSize && contextSize > 0) {
    if (contextSize >= 1000000 && contextSize % 1000000 === 0) {
      contextSizeValue.value = contextSize / 1000000;
      contextSizeUnit.value = 'M';
      return;
    }
    contextSizeValue.value = Number((contextSize / 1000).toFixed(0));
    contextSizeUnit.value = 'K';
    return;
  }
  contextSizeValue.value = null;
  contextSizeUnit.value = 'K';
};

const syncContextSize = () => {
  const value = contextSizeValue.value;
  if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) {
    formData.value.contextSize = 0;
    return;
  }
  const multiplier = contextSizeUnit.value === 'M' ? 1000000 : 1000;
  formData.value.contextSize = Math.round(value * multiplier);
};

const selectContextSizePreset = (contextSize: number) => {
  formData.value.contextSize = contextSize;
  normalizeContextSizeInputs(contextSize);
};

const handleCopyModelId = async () => {
  const ok = await copyText(formData.value.id)
  if (ok) {
    NotificationService.success('已复制到剪贴板')
  } else {
    NotificationService.error('复制失败，请手动复制')
  }
};

const validateForm = () => {
  if (!formData.value.name) {
    NotificationService.error('请输入模型名称');
    return false;
  }
  if (!formData.value.types.length) {
    NotificationService.error('请选择模型类型');
    return false;
  }
  if (!formData.value.contextSize) {
    NotificationService.error('请选择或输入上下文长度');
    return false;
  }
  return true;
};

const handleConfirm = () => {
  if (validateForm()) {
    emit('confirm', { ...formData.value });
  }
};

const handleCancel = () => {
  visible.value = false;
  emit('cancel');
};
</script>

<style scoped>
.add-model-form {
  padding: 0 10px;
  margin-top: 26px;
}

.form-item.row-item {
  display: flex;
  align-items: flex-start;
  gap: 20px;
  margin-bottom: 24px;
}

.form-label {
  flex: 0 0 82px;
  font-weight: 500;
  line-height: 32px;
  text-align: right;
}

.form-label.required::before {
  content: '* ';
  color: #ff4d4f;
}

.form-label.context-size-label {
  white-space: nowrap;
}

.form-control {
  flex: 1;
  min-width: 0;
}

.form-control :deep(.ant-input),
.form-control :deep(.ant-select),
.form-control :deep(.ant-checkbox-group-wrapper),
.form-control .model-type-panel {
  width: 100%;
  box-sizing: border-box;
}

.context-size-panel {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.context-size-input-row {
  display: flex;
  gap: 8px;
}

.context-size-number {
  flex: 1;
}

.context-size-unit {
  flex: 0 0 76px;
}

.context-size-presets {
  display: flex;
  flex-wrap: nowrap;
  gap: 6px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: none;
}

.context-size-presets::-webkit-scrollbar {
  display: none;
}

.context-size-preset {
  flex: 0 0 auto;
  border: 1px solid #dbe3f0;
  border-radius: 7px;
  background: #ffffff;
  color: #475569;
  padding: 4px 10px;
  font-size: 11px;
  line-height: 1.2;
  white-space: nowrap;
  cursor: pointer;
  transition: all 0.2s ease;
}

.context-size-preset:hover {
  border-color: #91a7ff;
  color: #364fc7;
  background: #fafbff;
}

.context-size-preset.active {
  border-color: #a5b4fc;
  color: #364fc7;
  background: #eef2ff;
}

.form-help-text {
  font-size: 11px;
  line-height: 1.5;
  color: #64748b;
}

.model-type-panel {
  border: none;
  background: transparent;
}

:deep(.model-type-options) {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

:deep(.model-type-options .ant-checkbox-wrapper) {
  margin-inline-start: 0;
  padding: 4px 12px;
  border-radius: 10px;
  border: 1px solid #e1e6f5;
  background: #ffffff;
  color: #475569;
  transition: all 0.2s ease;
}

:deep(.model-type-options .ant-checkbox-wrapper:hover) {
  border-color: #c7d2fe;
  color: #3b5bdb;
  box-shadow: 0 6px 12px rgba(59, 93, 219, 0.12);
  transform: translateY(-1px);
}

:deep(.model-type-options .ant-checkbox-wrapper-checked) {
  border-color: #a5b4fc;
  background: #eef2ff;
  color: #364fc7;
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

.copy-btn {
  margin-left: 0;
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

:deep(.edit-model-modal .ant-modal-content) {
  border-radius: 21px;
}
</style>

<style>
.edit-model-modal .ant-modal-content {
  border-radius: 21px !important;
}

.edit-model-modal .ant-modal-title {
  margin-left: 10px !important;
}
</style>
