<template>
  <div class="env-var-config-panel">
    <div class="agent-model-section-header">
      <div class="header-text">
        <h3>环境变量</h3>
        <p>为 DeepAgent 配置运行时环境变量</p>
      </div>
      <button v-if="localEnvVars.length > 0" class="header-add-btn" type="button" @click="addEnvVar">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
          <path d="M12 5v14M5 12h14"/>
        </svg>
        <span>添加变量</span>
      </button>
    </div>

    <div class="env-var-config-form">
      <div class="env-var-list" v-if="localEnvVars.length > 0">
        <div
          v-for="(envVar, index) in localEnvVars"
          :key="index"
          class="env-var-item"
        >
          <div class="env-var-header">
            <div class="env-var-header-left">
              <span class="env-var-index">{{ String(index + 1).padStart(2, '0') }}</span>
              <span class="env-var-title">环境变量 {{ index + 1 }}</span>
            </div>
            <a-button
              type="text"
              class="env-var-delete-btn"
              @click="removeEnvVar(index)"
            >
              <DeleteOutlined />
            </a-button>
          </div>
          <div class="env-var-fields">
            <div class="env-var-field">
              <label class="env-var-label">变量名</label>
              <a-input
                v-model:value="envVar.key"
                placeholder="例如：API_KEY"
                class="env-var-key-input"
                @change="handleUpdate"
              />
            </div>
            <div class="env-var-field">
              <label class="env-var-label">变量值</label>
              <a-input
                v-model:value="envVar.value"
                placeholder="例如：sk-xxxxxxxxxx"
                class="env-var-value-input"
                @change="handleUpdate"
              />
            </div>
          </div>
        </div>
      </div>

      <div v-if="localEnvVars.length === 0" class="env-var-empty-state">
        <div class="empty-illustration">
          <div class="empty-card empty-card--back"></div>
          <div class="empty-card empty-card--front">
            <span></span>
            <span></span>
            <span></span>
          </div>
          <div class="empty-spark">+</div>
        </div>
        <p class="empty-title">暂无环境变量</p>
        <p class="empty-desc">为智能体配置运行时需要的环境变量</p>
        <button class="add-btn add-btn--primary" type="button" @click="addEnvVar">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M12 5v14M5 12h14"/>
          </svg>
          <span>新建环境变量</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { DeleteOutlined } from '@ant-design/icons-vue';

interface EnvVar {
  key: string;
  value: string;
}

const props = defineProps<{
  envVars: EnvVar[];
}>();

const emit = defineEmits<{
  'update:envVars': [envVars: EnvVar[]];
}>();

const localEnvVars = ref<EnvVar[]>([...props.envVars.map(e => ({ ...e }))]);

watch(
  () => props.envVars,
  (newEnvVars) => {
    localEnvVars.value = [...newEnvVars.map(e => ({ ...e }))];
  },
  { deep: true }
);

const addEnvVar = () => {
  localEnvVars.value.push({ key: '', value: '' });
  handleUpdate();
};

const removeEnvVar = (index: number) => {
  localEnvVars.value.splice(index, 1);
  handleUpdate();
};

const handleUpdate = () => {
  emit('update:envVars', [...localEnvVars.value]);
};
</script>

<style scoped>
.env-var-config-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.env-var-config-panel :deep(.agent-model-section-header) {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.env-var-config-panel :deep(.agent-model-section-header .header-text) {
  flex: 1;
  min-width: 0;

  h3 {
    margin: 0 0 4px 0;
  }

  p {
    margin: 0;
  }
}

.header-add-btn {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 10px;
  border: 1.5px solid #dce4f2;
  background: linear-gradient(180deg, #ffffff 0%, #f4f7fd 100%);
  color: #5a6a7a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px rgba(26, 86, 219, 0.04);

  svg {
    display: block;
  }

  &:hover {
    border-color: #4f7cff;
    color: #4f7cff;
    box-shadow: 0 2px 6px rgba(79, 124, 255, 0.12);
  }

  &:active {
    transform: scale(0.97);
  }
}

.env-var-config-form {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding-right: 4px;
}

.env-var-config-form::-webkit-scrollbar {
  width: 6px;
}

.env-var-config-form::-webkit-scrollbar-track {
  background: transparent;
}

.env-var-config-form::-webkit-scrollbar-thumb {
  background: rgba(0, 0, 0, 0.2);
  border-radius: 3px;
}

.env-var-config-form::-webkit-scrollbar-thumb:hover {
  background: rgba(0, 0, 0, 0.3);
}

.env-var-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 14px;
  padding-bottom: 14px;
}

.env-var-item {
  position: relative;
  display: flex;
  flex-direction: column;
  padding: 14px 16px 16px;
  border: 1px solid #e2eaf6;
  border-radius: 12px;
  background: linear-gradient(180deg, #f7f9fd 0%, #fafcff 100%);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.env-var-item:hover {
  border-color: #cdd8ee;
  box-shadow: 0 2px 8px rgba(26, 86, 219, 0.06);
}

.env-var-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 12px;
  margin-bottom: 14px;
  border-bottom: 1px solid #e4ecf7;
}

.env-var-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.env-var-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  background: #e8f0fe;
  color: #3b6fd4;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.3px;
  flex-shrink: 0;
}

.env-var-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
}

.env-var-fields {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.env-var-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.env-var-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.env-var-key-input,
.env-var-value-input {
  font-size: 13px;
}

.env-var-key-input :deep(.ant-input),
.env-var-value-input :deep(.ant-input) {
  border: 1px solid #e4ecf7;
  border-radius: 8px;
  background: #f8fafd;
  height: 36px;
  padding: 0 12px;
  font-size: 13px;
  color: #1f2937;
  transition: all 0.2s ease;
}

.env-var-key-input :deep(.ant-input)::placeholder,
.env-var-value-input :deep(.ant-input)::placeholder {
  color: #b0b8c4;
}

.env-var-key-input :deep(.ant-input:focus),
.env-var-key-input :deep(.ant-input-focused),
.env-var-value-input :deep(.ant-input:focus),
.env-var-value-input :deep(.ant-input-focused) {
  border-color: #4f7cff;
  background: #ffffff;
  box-shadow: 0 0 0 2px rgba(79, 124, 255, 0.08);
}

.env-var-delete-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #9ca3af;
  cursor: pointer;
  transition: all 0.2s ease;
}

.env-var-delete-btn:hover {
  color: #f5222d;
}

.env-var-empty-state {
  flex: 1;
  width: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-illustration {
  position: relative;
  width: 72px;
  height: 72px;
  margin-bottom: 20px;
}

.empty-card {
  position: absolute;
  width: 48px;
  height: 64px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e8eef5 0%, #f0f5fa 100%);
  box-shadow: 0 2px 8px -2px rgba(0, 0, 0, 0.06);
}

.empty-card--back {
  transform: rotate(-8deg) translate(-6px, -4px);
  opacity: 0.6;
}

.empty-card--front {
  transform: rotate(4deg) translate(4px, 2px);
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px;
}

.empty-card--front span {
  display: block;
  height: 4px;
  border-radius: 2px;
  background: linear-gradient(90deg, #1677ff 0%, transparent 100%);
  opacity: 0.3;
}

.empty-card--front span:nth-child(1) {
  width: 70%;
}

.empty-card--front span:nth-child(2) {
  width: 100%;
}

.empty-card--front span:nth-child(3) {
  width: 50%;
}

.empty-spark {
  position: absolute;
  right: 4px;
  top: 4px;
  font-size: 18px;
  color: #1677ff;
  font-weight: 600;
  animation: spark-pulse 2s ease-in-out infinite;
}

@keyframes spark-pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 0.8;
  }
  50% {
    transform: scale(1.1);
    opacity: 1;
  }
}

.empty-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 6px 0;
}

.empty-desc {
  font-size: 13px;
  color: #6b7280;
  margin: 0 0 20px 0;
  line-height: 1.5;
}

.add-btn {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1.5px solid #e8eef5;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  color: #5a6a7a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  overflow: hidden;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.add-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(135deg, rgba(22, 119, 255, 0.06), transparent 50%);
  opacity: 0;
  transition: opacity 0.25s ease;
}

.add-btn::after {
  content: '';
  position: absolute;
  left: 50%;
  top: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(22, 119, 255, 0.08);
  transform: translate(-50%, -50%);
  transition: width 0.4s ease, height 0.4s ease;
}

.add-btn svg {
  position: relative;
  z-index: 1;
  transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.add-btn span {
  position: relative;
  z-index: 1;
}

.add-btn:hover {
  border-color: #bcd7ff;
  color: #1677ff;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px -4px rgba(22, 119, 255, 0.25);
}

.add-btn:hover::before {
  opacity: 1;
}

.add-btn:hover svg {
  transform: rotate(90deg);
}

.add-btn:active {
  transform: translateY(0);
}

.add-btn:active::after {
  width: 200px;
  height: 200px;
}

.add-btn--primary {
  min-width: 75px;
  height: 36px;
  padding: 0 16px;
  border: none;
  border-radius: 10px;
  color: #ffffff;
  background: linear-gradient(135deg, #1677ff 0%, #4096ff 100%);
  box-shadow: 0 2px 8px -2px rgba(22, 119, 255, 0.35);
  font-size: 13px;
  font-weight: 500;
  transition: box-shadow 0.25s ease, background 0.25s ease, color 0.25s ease, filter 0.25s ease;
}

.add-btn--primary::before {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.15), transparent 50%);
}

.add-btn--primary:hover {
  color: #ffffff;
  box-shadow: 0 4px 16px -4px rgba(22, 119, 255, 0.45);
  transform: translateY(-1px);
}

.add-btn--primary:hover svg {
  transform: none;
}
</style>
