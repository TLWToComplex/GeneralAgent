<template>
  <div class="config-section">
    <div class="agent-model-section-header">
      <h3>编排式智能体配置</h3>
      <p>配置一个可用的智能体服务 URL</p>
    </div>
    <a-form layout="vertical" class="form-content">
      <a-form-item label="智能体服务URL" :validate-status="formErrors.orchestratorUrl ? 'error' : undefined" :help="formErrors.orchestratorUrl ? '请输入有效的智能体服务URL' : undefined" required>
        <a-input v-model:value="localConfig.serviceUrl" placeholder="请输入智能体服务URL" @change="onChange" />
        <span class="field-help">用于编排式智能体的对话服务入口地址</span>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { reactive, watch } from 'vue';

interface OrchestratorConfig {
  serviceUrl: string;
}

interface Props {
  orchestratorConfig: OrchestratorConfig;
  formErrors: Record<string, boolean>;
}

interface Emits {
  (e: 'update:orchestratorConfig', value: OrchestratorConfig): void;
  (e: 'update:errors', value: Partial<Record<string, boolean>>): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const localConfig = reactive<OrchestratorConfig>({
  serviceUrl: props.orchestratorConfig?.serviceUrl || ''
});

watch(() => props.orchestratorConfig, (cfg) => {
  if (cfg) {
    localConfig.serviceUrl = cfg.serviceUrl || '';
  }
}, { deep: true });

const onChange = () => {
  const url = (localConfig.serviceUrl || '').trim();
  emit('update:orchestratorConfig', { serviceUrl: url });
  emit('update:errors', { orchestratorUrl: !url });
};
</script>

<style scoped>
.field-help {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: #8c8c8c;
}
</style>
