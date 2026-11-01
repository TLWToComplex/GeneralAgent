<template>
  <div class="config-section">
    <div class="agent-model-section-header">
      <h3>模型设置</h3>
      <p>配置智能体使用的AI模型</p>
    </div>
    <a-form :model="localModelConfig" layout="vertical" class="form-content">
      <a-form-item label="模型服务" required>
        <a-select v-model:value="localModelConfig.service" style="width: 100%" placeholder="请选择模型服务"
          @popupScroll="() => true" @change="handleServiceChange">
          <a-select-option v-for="provider in Object.keys(modelGroups)" :key="provider" :value="provider">
            {{ provider }}
          </a-select-option>
        </a-select>
        <div v-if="Object.keys(modelGroups).length === 0" style="font-size: 12px; color: #999; margin-top: 8px;">
          暂无可用模型服务，请先<a href="/settings/model-service" @click="handleModelSettingsLink"
            style="color: #1890ff; text-decoration: none;">配置模型服务</a>
        </div>
      </a-form-item>

      <a-form-item label="模型名称" required>
        <a-select v-model:value="localModelConfig.name" style="width: 100%" :disabled="!localModelConfig.service"
          placeholder="请选择模型名称" @popupScroll="() => true" @change="handleModelNameChange">
          <a-select-option v-for="model in (localModelConfig.service ? modelGroups[localModelConfig.service] : [])"
            :key="model.id" :value="model.name">
            {{ model.name }}
          </a-select-option>
        </a-select>
      </a-form-item>

      <a-divider  style="margin-top: 0; margin-bottom: 20px;"/>

      <div class="agent-model-section-header">
        <h3>模型参数设置</h3>
        <p>调整模型的参数，以优化AI回答的风格和质量</p>
      </div>

      <a-form-item class="horizontal-form-item">
        <div class="parameter-row">
          <div class="parameter-label">
            <a-flex vertical>
              <a-flex class="model-title">
                <span class="parameter-title">创意活跃度</span>
                <div class="parameter-name">temperature</div>
              </a-flex>
              <div class="model-disc">
                数值越大，回答越有创意和想象力；数值越小，回答越严谨
              </div>
            </a-flex>
          </div>
          <div class="parameter-control">
            <div class="temperature-control">
              <a-slider v-model:value="localModelConfig.temperature" :min="0" :max="2" :step="0.1"
                :marks="{ 0: '0', 0.7: '0.7', 2: '2' }" @change="handleTemperatureChange" />
            </div>
          </div>
        </div>
      </a-form-item>

      <a-form-item class="horizontal-form-item">
        <div class="parameter-row">
          <div class="parameter-label">
            <a-flex vertical>
              <a-flex class="model-title">
                <span class="parameter-title">思维开放度</span>
                <div class="parameter-name">top_p</div>
              </a-flex>
              <div class="model-disc">
                考虑多少种可能性，值越大，接受更多可能的回答；值越小，倾向选择最可能的回答。不推荐和创意活跃度一起更改
              </div>
            </a-flex>
          </div>
          <div class="parameter-control">
            <div class="temperature-control">
              <a-slider v-model:value="localModelConfig.top_p" :min="0" :max="1" :step="0.1"
                :marks="{ 0: '0', 0.5: '0.5', 1: '1' }" @change="handleTopPChange" />
            </div>
          </div>
        </div>
      </a-form-item>

      <a-form-item class="horizontal-form-item">
        <div class="parameter-row">
          <div class="parameter-label">
            <a-flex vertical>
              <a-flex class="model-title">
                <span class="parameter-title">表述发散度</span>
                <div class="parameter-name">presence_penalty</div>
              </a-flex>
              <div class="model-disc">
                值越大，越倾向不同的表达方式，避免概念重复；值越小，越倾向使用重复的概念或叙述，表达更具一致性
              </div>
            </a-flex>
          </div>
          <div class="parameter-control">
            <div class="temperature-control">
              <a-slider v-model:value="localModelConfig.presence_penalty" :min="-2" :max="2" :step="0.1"
                :marks="{ '-2': '-2', 0: '0', 2: '2' }" @change="handlePresencePenaltyChange" />
            </div>
          </div>
        </div>
      </a-form-item>

      <a-form-item class="horizontal-form-item">
        <div class="parameter-row">
          <div class="parameter-label">
            <a-flex vertical>
              <a-flex class="model-title">
                <span class="parameter-title">词汇丰富度</span>
                <div class="parameter-name">frequency_penalty</div>
              </a-flex>
              <div class="model-disc">
                值越大，用词越丰富多样；值越低，用词更朴实简单
              </div>
            </a-flex>
          </div>
          <div class="parameter-control">
            <div class="temperature-control">
              <a-slider v-model:value="localModelConfig.frequency_penalty" :min="-2" :max="2" :step="0.1"
                :marks="{ '-2': '-2', 0: '0', 2: '2' }" @change="handleFrequencyPenaltyChange" />
            </div>
          </div>
        </div>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';

// 定义接口
interface ModelConfig {
  service: string | undefined;
  name: string | undefined;
  temperature: number;
  top_p: number;
  presence_penalty: number;
  frequency_penalty: number;
}

interface FormErrors {
  name: boolean;
  description: boolean;
  modelService: boolean;
  modelName: boolean;
}

interface Props {
  modelConfig: ModelConfig;
  errors: FormErrors;
  modelGroups: Record<string, any[]>;
}

interface Emits {
  (e: 'update:modelConfig', value: ModelConfig): void;
  (e: 'update:errors', value: Partial<FormErrors>): void;
}

// 组件属性和事件
const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const router = useRouter();

// 本地状态
const localModelConfig = ref<ModelConfig>({ ...props.modelConfig });

// 监听props变化，更新本地状态
watch(
  () => props.modelConfig,
  (newConfig) => {
    localModelConfig.value = { ...newConfig };
  },
  { deep: true }
);

// 处理模型服务变化
const handleServiceChange = () => {
  // 当服务变化时，重置模型名称
  if (localModelConfig.value.service !== props.modelConfig.service) {
    localModelConfig.value.name = '';
  }
  updateModelConfig();
};

// 处理模型名称变化
const handleModelNameChange = () => {
  updateModelConfig();
  // 清除模型名称错误
  emit('update:errors', { modelName: false });
};

// 处理温度参数变化
const handleTemperatureChange = () => {
  updateModelConfig();
};

// 处理Top P参数变化
const handleTopPChange = () => {
  updateModelConfig();
};

// 处理存在惩罚变化
const handlePresencePenaltyChange = () => {
  updateModelConfig();
};

// 处理频率惩罚变化
const handleFrequencyPenaltyChange = () => {
  updateModelConfig();
};

// 更新模型配置
const updateModelConfig = () => {
  emit('update:modelConfig', { ...localModelConfig.value });
};

// 处理模型设置链接点击
const handleModelSettingsLink = (e: MouseEvent) => {
  e.preventDefault();
  router.push('/settings/model-service');
};
</script>