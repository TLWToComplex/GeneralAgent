<template>
  <div class="config-card modal-compact">
    <div class="card-header">
      <div class="title-area">
        <h3>知识库设置</h3>
        <p>为当前智能体配置独立的知识库策略</p>
      </div>
      <div class="header-actions">
        <a-switch :checked="localKnowledgeConfig.enabled" @change="onEnabledChange" />
      </div>
    </div>

    <div class="card-divider"></div>

    <div class="card-body content-scroll">
      <div class="body-mask" v-if="!localKnowledgeConfig.enabled">
        <div class="mask-content" v-if="kbOptions.length === 0">
          <div class="mask-title">未创建知识库</div>
          <div class="mask-sub">请先前往设置创建或导入知识库</div>
          <button class="create-kb-button" style="margin-top: 8px;"
            @click="goToKnowledgeBaseAndCreateModal">创建知识库</button>
        </div>
        <div class="mask-content" v-else>
          <div class="mask-title">知识库未启用</div>
          <div class="mask-sub">开启后可选择知识库与检索模式</div>
        </div>
      </div>

      <a-form :model="localKnowledgeConfig" layout="vertical" class="form-content compact-form">
        <div class="form-grid">
          <!-- 选择知识库 -->
          <div class="grid-item">
            <a-form-item label="选择知识库">
              <div class="kb-row">
                <a-select class="kb-select" :disabled="!localKnowledgeConfig.enabled" :loading="kbLoading"
                  v-model:value="localKnowledgeConfig.selectedKnowledge" mode="multiple" placeholder="请选择知识库"
                  :dropdownMatchSelectWidth="false" show-search allow-clear @change="onSelectedKnowledgeChange">
                  <a-select-option v-for="kb in kbOptions" :key="kb" :value="kb">
                    {{ kb }}
                  </a-select-option>
                </a-select>
              </div>
              <span class="hint">选择后将应用到当前智能体的检索，可多选</span>
            </a-form-item>
          </div>

          <!-- 检索模式 -->
          <div class="grid-item">
            <a-form-item label="检索模式">
              <a-radio-group :disabled="!localKnowledgeConfig.enabled"
                v-model:value="localKnowledgeConfig.retrievalMode" @change="onRetrievalModeChange"
                class="radio-condensed">
                <a-radio value="semantic">语义检索</a-radio>
              </a-radio-group>
              <div class="hint">
                语义检索：基于知识库内容的智能检索，适用于需要理解上下文的查询。
              </div>
            </a-form-item>
          </div>

          <div class="grid-item">
            <a-form-item label="知识库概览">
              <div v-if="normalizeSelectedKnowledge(localKnowledgeConfig.selectedKnowledge).length > 0 && selectedKbDetail()" class="kb-summary-card">
                <div class="kb-name" v-if="selectedKbDetail()!.name">
                  {{ selectedKbDetail()!.name }}
                </div>
                <div class="kb-meta">
                  创建时间：{{ formatDate(selectedKbDetail()!.updatedAt) }}
                </div>

                <div class="kb-summary-row">
                  <div class="kb-chip">文档数: {{ selectedKbDetail()!.documentCount }}</div>
                  <div class="kb-chip" v-if="selectedKbDetail()!.vsType">向量库: {{ selectedKbDetail()!.vsType }}</div>
                  <div class="kb-chip" v-if="selectedKbDetail()!.embedModel">嵌入模型: {{ selectedKbDetail()!.embedModel }}
                  </div>
                </div>

                <div class="kb-docs">
                  <div class="kb-docs-header">
                    <span style="font-weight: bold;">知识文档</span>
                    <button v-if="kbFilesLoading || kbFiles.length > 0" @click="goToKnowledgeBaseAndOpenUploadModal" class="add-doc-button-header">添加文档</button>
                  </div>
                  <div v-if="kbFilesLoading" class="kb-docs-loading">
                    <LoadingOutlined spin class="loading-icon" />
                    <span class="loading-text">正在加载知识文档...</span>
                  </div>
                  <template v-else>
                    <div v-if="kbFiles.length > 0" class="kb-docs-list">
                      <div v-for="d in kbFiles" :key="d.id" class="kb-doc-item">
                        <div class="kb-doc-main">
                          <div class="kb-doc-name" :title="d.name">{{ d.name }}</div>
                          <div class="kb-doc-meta">
                            <span>{{ (d.size / 1024).toFixed(1) }} KB</span>
                            <span>{{ formatDate(d.uploadedAt) }}</span>
                            <span v-if="d.loader">{{ d.loader }}</span>
                            <span v-if="d.docsCount !== undefined">切片 {{ d.docsCount }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                    <div v-else class="kb-docs-empty">
                      <div>该知识库暂无文档</div>
                      <button @click="goToKnowledgeBaseAndOpenUploadModal" class="add-doc-button">
                        添加文档
                      </button>
                    </div>
                  </template>
                </div>
              </div>
              <div v-else class="kb-summary-card empty">请选择上方知识库以查看概览</div>
            </a-form-item>
          </div>
        </div>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, watch, onUnmounted, onActivated } from 'vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import NotificationService from '@/utils/NotificationService';
import type { KnowledgeBaseFileVM, KnowledgeBaseVM } from '@/services/knowledgeBase';
import { listKnowledgeBaseFiles, listKnowledgeBases } from '@/services/knowledgeBase';
import { fetchAndCacheRetrievalConfig } from '@/services/aiSystemConfig';
import { eventBus } from '@/utils/EventBus';
import { useRouter } from 'vue-router';
import { useKnowledgeBaseStore } from '@/stores/knowledgeBaseStore';
import { formatDate, toTimestamp } from '@/utils/formatters';

interface KnowledgeConfig {
  enabled: boolean;
  selectedKnowledge: string[];
  retrievalMode: string;
}

interface FormErrors {
  name: boolean;
  description: boolean;
  modelService: boolean;
  modelName: boolean;
}

interface Props {
  knowledgeConfig: KnowledgeConfig;
  errors: FormErrors;
}

interface Emits {
  (e: 'update:knowledgeConfig', value: KnowledgeConfig): void;

  (e: 'update:errors', value: Partial<FormErrors>): void;

  (e: 'close-modal'): void;
}

// 组件属性和事件
const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// 本地状态
const localKnowledgeConfig = ref<KnowledgeConfig>({ ...props.knowledgeConfig });
const kbOptions = ref<string[]>([]);
const kbList = ref<KnowledgeBaseVM[]>([]);
const kbLoading = ref<boolean>(false);
const kbFiles = ref<KnowledgeBaseFileVM[]>([]);
const kbFilesLoading = ref<boolean>(false);

watch(
  () => props.knowledgeConfig,
  (newConfig) => {
    localKnowledgeConfig.value = { ...newConfig };
  },
  { deep: true }
);

// 加载知识库列表
async function loadKnowledgeBases() {
  kbLoading.value = true;
  try {
    const list = await listKnowledgeBases();
    kbList.value = list;
    kbOptions.value = list.map((kb) => kb.name);
  } catch (e) {
    console.error(e);
    NotificationService.error(`加载知识库列表失败：${(e as Error).message}`);
  } finally {
    kbLoading.value = false;
  }
}

onMounted(async () => {
  await loadKnowledgeBases();
  // 加载后根据当前配置与可用知识库进行校正
  const selectedList = normalizeSelectedKnowledge(localKnowledgeConfig.value.selectedKnowledge);
  const enabled = localKnowledgeConfig.value.enabled;
  const validSelectedList = selectedList.filter(name => kbOptions.value.includes(name));

  // 如果启用了知识库，但选中的知识库都不存在（可能被删除），则自动关闭知识库功能，并清空选择
  if (enabled && selectedList.length > 0 && validSelectedList.length === 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      enabled: false,
      selectedKnowledge: []
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    NotificationService.warning('所选知识库已被删除，已自动关闭知识库功能');
  }

  // 如果启用了知识库但当前知识库列表为空，则关闭
  if (enabled && kbOptions.value.length === 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      enabled: false,
      selectedKnowledge: []
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    NotificationService.warning('知识库列表为空，已自动关闭知识库功能');
  }

  // 只要选中的知识库依然存在（无论是否启用），加载第一个选中知识库的最近文档用于概览展示
  if (validSelectedList.length > 0) {
    await loadSelectedKbFiles(validSelectedList[0]);
  }

  // 未启用也默认选中第一个知识库
  if (selectedList.length === 0 && kbOptions.value.length > 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      selectedKnowledge: [kbOptions.value[0]]
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    await loadSelectedKbFiles(kbOptions.value[0]);
  }

  // 监听知识库列表更新事件
  eventBus.on('knowledge-base-list-updated', loadKnowledgeBases);
});

onActivated(async () => {
  await loadKnowledgeBases();
  const selectedList = normalizeSelectedKnowledge(localKnowledgeConfig.value.selectedKnowledge);
  if (selectedList.length === 0 && kbOptions.value.length > 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      selectedKnowledge: [kbOptions.value[0]]
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
  }
  const latestSelectedList = normalizeSelectedKnowledge(localKnowledgeConfig.value.selectedKnowledge);
  if (latestSelectedList.length > 0) {
    await loadSelectedKbFiles(latestSelectedList[0]);
  }
});

// 在组件卸载时取消事件监听
onUnmounted(() => {
  eventBus.off('knowledge-base-list-updated', loadKnowledgeBases);
});

function normalizeSelectedKnowledge(value: string[] | undefined | null): string[] {
  if (Array.isArray(value)) return value.filter(Boolean);
  return [];
}

async function onEnabledChange(checked: boolean) {
  if (checked) {
    if (kbOptions.value.length === 0) {
      const updated: KnowledgeConfig = {
        ...localKnowledgeConfig.value,
        enabled: false,
        selectedKnowledge: []
      };
      localKnowledgeConfig.value = updated;
      emit('update:knowledgeConfig', updated);
      NotificationService.warning('当前没有可用的知识库，无法启用');
      return;
    }
    // 开启增强检索时，获取最新检索参数配置
    fetchAndCacheRetrievalConfig().catch(() => {})
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      enabled: true
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    if (normalizeSelectedKnowledge(updated.selectedKnowledge).length === 0 && kbOptions.value.length > 0) {
      onSelectedKnowledgeChange([kbOptions.value[0]]);
    }
  } else {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      enabled: false
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
  }
}

function onSelectedKnowledgeChange(value: string[]) {
  const selectedList = normalizeSelectedKnowledge(value);
  const updated: KnowledgeConfig = {
    ...localKnowledgeConfig.value,
    selectedKnowledge: selectedList
  };
  localKnowledgeConfig.value = updated;
  emit('update:knowledgeConfig', updated);
  if (selectedList.length > 0) {
    loadSelectedKbFiles(selectedList[0]);
  } else {
    kbFiles.value = [];
  }
}

function onRetrievalModeChange(e: any) {
  const value = typeof e === 'string' ? e : e?.target?.value;
  const updated: KnowledgeConfig = {
    ...localKnowledgeConfig.value,
    retrievalMode: value || 'semantic'
  };
  localKnowledgeConfig.value = updated;
  emit('update:knowledgeConfig', updated);
}

watch(kbOptions, (opts) => {
  // 当知识库列表变化时，如果当前启用了知识库并且所选知识库都不存在，则自动关闭知识库功能
  const selectedList = normalizeSelectedKnowledge(localKnowledgeConfig.value.selectedKnowledge);
  const enabled = localKnowledgeConfig.value.enabled;
  const validSelectedList = selectedList.filter(name => opts.includes(name));
  if (enabled && selectedList.length > 0 && validSelectedList.length === 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      enabled: false,
      selectedKnowledge: []
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    NotificationService.warning('所选知识库已被删除，已自动关闭知识库功能');
    return;
  }
  if (enabled && opts.length === 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      enabled: false,
      selectedKnowledge: []
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    NotificationService.warning('知识库列表为空，已自动关闭知识库功能');
    return;
  }
  // 如果选中的知识库仍存在（无论是否启用），刷新第一个选中知识库的文档概览
  if (validSelectedList.length > 0) {
    loadSelectedKbFiles(validSelectedList[0]);
  }
  // 若没有选择，默认选中第一个
  if (selectedList.length === 0 && opts.length > 0) {
    const updated: KnowledgeConfig = {
      ...localKnowledgeConfig.value,
      selectedKnowledge: [opts[0]]
    };
    localKnowledgeConfig.value = updated;
    emit('update:knowledgeConfig', updated);
    loadSelectedKbFiles(opts[0]);
  }
});

watch(
  () => localKnowledgeConfig.value.selectedKnowledge,
  (value) => {
    const selectedList = normalizeSelectedKnowledge(value);
    if (selectedList.length > 0) {
      loadSelectedKbFiles(selectedList[0]);
    } else {
      kbFiles.value = [];
    }
  }
);

// 选中的知识库详情
function selectedKbDetail(): KnowledgeBaseVM | undefined {
  const selectedList = normalizeSelectedKnowledge(localKnowledgeConfig.value.selectedKnowledge);
  if (selectedList.length === 0) return undefined;
  return kbList.value.find(k => k.name === selectedList[0]);
}

async function loadSelectedKbFiles(name: string) {
  kbFilesLoading.value = true;
  try {
    const files = await listKnowledgeBaseFiles(name);
    kbFiles.value = files
      .slice()
      .sort((a, b) => (b.mtime ?? toTimestamp(b.uploadedAt)) - (a.mtime ?? toTimestamp(a.uploadedAt)))
      .slice(0, 5);
  } catch (e) {
    console.error(e);
    kbFiles.value = [];
  } finally {
    kbFilesLoading.value = false;
  }
}

const router = useRouter();
const knowledgeBaseStore = useKnowledgeBaseStore();

// 跳转到知识库页面并打开添加文档模态框
function goToKnowledgeBaseAndOpenUploadModal() {
  // 设置需要打开上传模态框的知识库名称
  const selectedList = normalizeSelectedKnowledge(localKnowledgeConfig.value.selectedKnowledge);
  if (selectedList.length > 0) {
    knowledgeBaseStore.setKbNameToOpenUploadModal(selectedList[0]);
    // 关闭当前模态框
    // 这里需要通过事件通知父组件关闭模态框
    emit('close-modal');
    // 跳转到知识库页面
    router.push('/settings/knowledge-base');
  }
}

// 跳转到知识库页面并打开创建知识库模态框
function goToKnowledgeBaseAndCreateModal() {
  // 设置需要打开创建模态框的标识
  knowledgeBaseStore.setKbNameToOpenUploadModal('__create_new_kb__');
  // 关闭当前模态框
  emit('close-modal');
  // 跳转到知识库页面
  router.push('/settings/knowledge-base');
}

</script>

<style scoped>
.config-card {
  background: #fff;
}

.modal-compact {
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 2;
  padding-bottom: 6px;
}

.title-area h3 {
  margin: 0 0 4px 0;
  font-size: 16px;
}

.title-area p {
  margin: 0;
  color: #666;
  font-size: 13px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-divider {
  height: 1px;
  background: #f0f0f0;
  margin: 6px 0 10px 0;
}

.card-body {
  position: relative;
}

.content-scroll {
  overflow-y: auto;
}

.compact-form :deep(.ant-form-item) {
  margin-bottom: 10px;
}

.form-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.grid-item {
  min-width: 0;
}

.kb-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-select {
  flex: 1;
}

.radio-condensed :deep(.ant-radio-wrapper) {
  margin-right: 8px;
}

.hint {
  display: block;
  color: #666;
  font-size: 12px;
  margin-top: 6px;
}

.body-mask {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(1px);
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.mask-content {
  text-align: center;
}

.mask-title {
  font-size: 14px;
  color: #444;
  font-weight: 600;
}

.mask-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #777;
}

.create-kb-button {
  margin-top: 8px;
  border: transparent;
  border-radius: 10px;
  background-color: #1677ff;
  color: #ffffff;
  padding: 6px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.create-kb-button:hover {
  background-color: #4096ff;
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(22, 119, 255, 0.3);
}

.kb-summary-card {
  padding: 12px;
  border: 1px solid #eee;
  border-radius: 10px;
  background: #fafafa;
  height: 329px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.kb-summary-card.empty {
  color: #777;
  font-size: 12px;
}

.kb-summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.kb-chip {
  display: inline-flex;
  align-items: center;
  padding: 4px 8px;
  font-size: 11px;
  color: #333;
  background: #f3f4f6;
  border-radius: 8px;
  margin-top: 5px;
  margin-bottom: 5px;
}

.kb-name {
  font-size: 14px;
  line-height: 1.5;
  font-weight: bold;
}

.kb-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #888;
}

.kb-docs {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.kb-docs-header {
  font-size: 13px;
  color: #333;
  margin-top: -10px;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kb-docs-header .add-doc-button {
  margin-top: 0;
}

.kb-docs-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 12px;
  color: #666;
  flex: 1;
  min-height: 0;
}

.loading-icon {
  font-size: 20px;
  color: rgb(22 119 255);
}

.kb-docs-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  color: #777;
  font-size: 12px;
  flex: 1;
  min-height: 0;
}

.kb-docs-empty div {
  margin-bottom: 0;
}

.add-doc-button-header {
  border: transparent;
  border-radius: 8px;
  background-color: transparent;
  color: #3f3f3f;
  padding: 4px 14px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid #dfdfdf;
}

.add-doc-button-header:hover {
  border: 1px solid #1677ff;
  color: #1677ff;
}

.add-doc-button {
  margin-top: 5px;
  border: transparent;
  border-radius: 10px;
  background-color: #1677ff;
  color: #ffffff;
  padding: 5px 16px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.add-doc-button:hover {
  background-color: #4096ff;
  box-shadow: 0 4px 8px rgba(22, 119, 255, 0.3);
}

.kb-docs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.kb-doc-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  border: 1px solid #eee;
  border-radius: 8px;
  background: #fff;
}

.kb-doc-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.kb-doc-name {
  font-size: 13px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.kb-doc-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.kb-docs-empty {
  font-size: 12px;
  color: #777;
}

.create-kb-option {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #1677ff;
}
</style>
