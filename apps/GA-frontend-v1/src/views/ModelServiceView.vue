<template>
  <div class="settings-content">
    <!-- 中间服务列表 -->
    <div class="middle-section">
      <draggable v-model="servicesList" class="service-list ant-list ant-list-split" :item-key="getServiceKey" :animation="200" :disabled="isLoading || isReadonly"
        @end="onServiceOrderChange">
        <template #item="{ element: item }">
          <div class="service-item ant-list-item" :class="{ 'selected': getServiceKey(item) === selectedService }"
            @click="handleServiceClick(item)">
            <div class="service-icon-wrapper">
              <div :class="['service-icon', item.iconClass]"
                :style="{ backgroundColor: item.providerIcon ? 'transparent' : (item.backgroundColor || '#ffffff') }">
                <img v-if="item.avatar" :src="item.avatar" class="service-icon-image" alt="" />
                <SiliconCloudIcon v-else-if="item.providerIcon === 'siliconcloud'" class="provider-icon" />
                <BaiLianIcon v-else-if="item.providerIcon === 'bailian'" class="provider-icon" />
                <BaiduCloudIcon v-else-if="item.providerIcon === 'baiducloud'" class="provider-icon" />
                <span v-else>{{ item.iconText }}</span>
              </div>
              <div class="service-name" :title="item.name">{{ item.name }}</div>
              <div class="drag-handle" :class="{ disabled: isReadonly }">
                <MenuOutlined style="color: #6285e1" />
              </div>
            </div>
          </div>
        </template>
      </draggable>

      <div v-if="isLoading" class="list-loading-overlay">
        <div class="list-loading-content">
          <LoadingOutlined spin style="font-size: 24px; color: #1890ff" />
          <div class="list-loading-text">正在加载…</div>
        </div>
      </div>

      <!-- 添加按钮放在列表底部 -->
      <div class="add-button-container">
        <button class="action-btn add-button" style="border: 1px solid rgb(225, 231, 235);" @click="showAddProviderModal" :disabled="isReadonly">
          <PlusOutlined />
          添加
        </button>
      </div>
    </div>

    <!-- 右侧内容区域 -->
    <div class="right-content">
      <div v-if="isLoading" class="loading-content">
        <div class="loading-inner">
          <LoadingOutlined spin style="font-size: 32px; color: #1890ff" />
          <div class="loading-text">正在加载…</div>
        </div>
      </div>
      <div v-else-if="selectedService && selectedService !== ''" class="api-section">
        <div class="header">
          <div class="header-left">
            <div v-if="currentServiceData && (currentServiceData.avatar || currentServiceData.backgroundColor || currentServiceData.providerIcon)"
              class="service-header-icon" :style="{
                backgroundColor: currentServiceData.providerIcon ? 'transparent' : (currentServiceData.backgroundColor || '#ffffff')
              }">
              <img v-if="currentServiceData.avatar" :src="currentServiceData.avatar" class="service-header-icon-image"
                alt="" />
              <SiliconCloudIcon v-else-if="currentServiceData.providerIcon === 'siliconcloud'" class="provider-icon" />
              <BaiLianIcon v-else-if="currentServiceData.providerIcon === 'bailian'" class="provider-icon" />
              <BaiduCloudIcon v-else-if="currentServiceData.providerIcon === 'baiducloud'" class="provider-icon" />
              <span v-else>{{ getServiceIconText(selectedService) }}</span>
             </div>
             <span class="header-title">{{ selectedServiceName }}</span>
             <EditOutlined class="edit-icon" :class="{ disabled: isReadonly }" @click="showEditProviderModal" />
           </div>
          <div class="header-right">
            <button class="action-btn secondary" @click="exportCurrentServiceConfig">
              <ExportOutlined />导出配置
            </button>
            <button class="action-btn primary" @click="handleSaveServiceClick" :disabled="isReadonly">
              <SaveOutlined />保存配置
            </button>
            <button class="action-btn danger" @click="showDeleteServiceModal" :disabled="isReadonly">
              <DeleteOutlined />删除服务
            </button>
          </div>
         </div>

         <a-divider />

         <div v-if="isReadonly" class="readonly-tip">
           <div class="readonly-tip-content">
             <div class="readonly-tip-title">只读模式</div>
             <div class="readonly-tip-text">当前账号非管理用户，仅可查看和导出模型服务配置，不能新增、编辑、删除或调整顺序。</div>
           </div>
         </div>

         <div class="api-section">
           <div class="section-title">API 密钥</div>
           <div class="api-key-container">
             <a-input-password v-model:value="serviceData.apiKey" placeholder="请输入API密钥" :disabled="isReadonly || noApiKeyRequired" />
             <a-checkbox v-model:checked="noApiKeyRequired" style="margin-top: 8px;" :disabled="isReadonly">
               无需API密钥（私有化部署模型）
             </a-checkbox>
           </div>

           <div class="section-title">API 地址</div>
           <div class="api-url-container">
            <a-input v-model:value="serviceData.apiUrl" placeholder="请输入API地址" :disabled="isReadonly" />
            <div class="api-url-preview">{{ apiPreviewUrl }}</div>
          </div>

          <div class="models-section">
            <div class="section-title-container">
              <span class="title-text">模型</span>
              <button class="action-btn primary" @click="showAddModelModal" :disabled="isReadonly">
                <PlusOutlined />
                添加模型
              </button>
            </div>

            <div class="model-cards">
              <template v-for="group in serviceModels" :key="group.id">
                <div v-for="model in group.models" :key="model.id" class="model-card">
                  <div class="model-card-header">
                    <div :class="['model-icon', model.icon || 'default']"
                      :style="{ backgroundColor: (shouldShowIcon(model.name, 'qwen') || shouldShowIcon(model.name, 'deepseek') || shouldShowIcon(model.name, 'glm')) ? 'transparent' : undefined }">
                      <QwenIcon v-if="shouldShowIcon(model.name, 'qwen')" class="model-icon-svg"
                        :style="{ backgroundColor: 'transparent' }" />
                      <DeepSeekIcon v-else-if="shouldShowIcon(model.name, 'deepseek')" class="model-icon-svg"
                        :style="{ backgroundColor: 'transparent' }" />
                      <ZaiIcon v-else-if="shouldShowIcon(model.name, 'glm') && model.name.toLowerCase().includes('z')"
                        class="model-icon-svg" :style="{ backgroundColor: 'transparent' }" />
                      <ZhipuIcon v-else-if="shouldShowIcon(model.name, 'glm')" class="model-icon-svg"
                        :style="{ backgroundColor: 'transparent' }" />
                      <span v-else>{{ model.iconText }}</span>
                    </div>
                    <div class="model-info">
                      <div class="model-name" :title="model.name">{{ model.name }}</div>
                      <div class="model-id" :title="model.id">{{ model.id }}</div>
                    </div>
                    <div class="model-actions">
                      <SettingOutlined class="action-icon" :class="{ disabled: isReadonly }" @click="showEditModelModal(model)" />
                      <a-popconfirm v-if="!isReadonly" title="确定要删除此模型吗？" ok-text="删除" cancel-text="取消"
                        overlayClassName="custom-delete-popconfirm"
                        :okButtonProps="{ class: 'custom-btn confirm-btn' }"
                        :cancelButtonProps="{ class: 'custom-btn cancel-btn' }"
                        @confirm="confirmDeleteModel(group.id, model.id)">
                        <DeleteOutlined class="action-icon delete-icon" />
                      </a-popconfirm>
                      <DeleteOutlined v-else class="action-icon delete-icon disabled" />
                    </div>
                  </div>
                  <div class="model-card-footer" v-if="(model.types && model.types.length) || model.contextSize">
                    <div class="model-types">
                      <span
                        v-for="type in model.types"
                        :key="type"
                        class="model-type-tag"
                        :class="type"
                      >
                        {{ getModelTypeLabel(type) }}
                      </span>
                      <span v-if="model.contextSize" class="model-type-tag context-size-tag">
                        {{ formatContextSize(model.contextSize) }}
                      </span>
                    </div>
                  </div>
                </div>
              </template>
            </div>

            <!-- 模型为空时的提示 -->
            <div v-if="serviceModels.length === 0" class="empty-models-tip">
              <div class="empty-background"></div>
              <div class="empty-icon">
                <AppstoreAddOutlined style="font-size: 30px;" />
              </div>
              <p class="empty-text">您还没有添加任何模型</p>
              <p class="empty-desc">请点击右上方"添加"按钮来添加模型</p>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-content">
        <div class="empty-icon">
          <SettingOutlined style="font-size: 30px;" />
        </div>
        <h3 class="empty-title">请配置模型服务</h3>
        <p class="empty-description">请在左侧选择或添加一个模型服务，并配置相关API信息和模型。</p>
        <a-button type="primary" @click="showAddProviderModal" :disabled="isReadonly">
          <template #icon>
            <PlusOutlined />
          </template>
          添加模型服务
        </a-button>
      </div>
    </div>

    <!-- 添加供应商模态窗口 -->
    <AddProviderModal v-model:open="addProviderModalVisible" :avatar-colors="avatarColors"
      @confirm="handleAddProviderConfirm" @cancel="addProviderModalVisible = false" />

    <!-- 添加模型模态窗 -->
    <AddModelModal v-model:open="addModelModalVisible" @confirm="handleAddModelConfirm"
      @cancel="addModelModalVisible = false" />

    <!-- 编辑模型模态窗 -->
    <EditModelModal v-model:open="editModelModalVisible" :model="editingModel" @confirm="handleEditModelConfirm"
      @cancel="editModelModalVisible = false" />

    <!-- 编辑供应商模态窗口 -->
    <EditProviderModal v-model:open="editProviderModalVisible" :provider="currentProviderData"
      :avatar-colors="avatarColors" @confirm="handleEditProviderConfirm" @cancel="editProviderModalVisible = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, createVNode, watch, onBeforeUnmount, nextTick } from 'vue';
import { PlusOutlined, SettingOutlined, DeleteOutlined, ExclamationCircleOutlined, AppstoreAddOutlined, EditOutlined, MenuOutlined, ExportOutlined, SaveOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import { Modal } from 'ant-design-vue';
import NotificationService from '@/utils/NotificationService';
import { useChatStore } from '@/stores/chat-store';
import { onBeforeRouteLeave } from 'vue-router';
import draggable from 'vuedraggable';
import StorageService from '@/utils/StorageService';
import { listPlatformModels, reorderPlatformModels, addPlatformModel, deletePlatformModel, updatePlatformModel } from '@/services/aiPlatformModel';
import { updateAiAgent, listAiAgents } from '@/services/aiAgent';

// 导入组件
import AddProviderModal from '@/components/model-service/AddProviderModal.vue';
import AddModelModal from '@/components/model-service/AddModelModal.vue';
import EditModelModal from '@/components/model-service/EditModelModal.vue';
import EditProviderModal from '@/components/model-service/EditProviderModal.vue';

// 导入LLM图标组件
import QwenIcon from '@/components/icons/llm/qwen.vue';
import DeepSeekIcon from '@/components/icons/llm/deepseek.vue';
import ZhipuIcon from '@/components/icons/llm/zhipu.vue';
import ZaiIcon from '@/components/icons/llm/zai.vue';
import SiliconCloudIcon from '@/components/icons/llm/siliconcloud.vue';
import BaiLianIcon from '@/components/icons/llm/bailian.vue';
import BaiduCloudIcon from '@/components/icons/llm/baiducloud.vue';
import { shouldShowModelIcon } from '@/utils/modelIcon';

// 导入类型
import type { Model, ModelGroup, ServiceData, ServiceListItem, ProviderFormData, EditProviderFormData, ModelFormData, EditModelFormData, ProviderData, ModelData } from '@/components/model-service/types';
import { formatContextSize } from '@/components/model-service/types';

// 定义组件名以便keep-alive能够识别
defineOptions({
  name: 'ModelServiceView'
});

// 用于生成随机颜色的颜色数组
const avatarColors = [
  '#1890ff', // 蓝色
  '#52c41a', // 绿色
  '#faad14', // 黄色
  '#f5222d', // 红色
  '#722ed1', // 紫色
  '#13c2c2', // 青色
  '#eb2f96', // 粉色
  '#fa541c', // 橙色
  '#a0d911', // 淡绿色
  '#2f54eb'  // 深蓝色
];

// 本地存储键
const PROVIDERS_STORAGE_KEY = 'mcp-providers';
const MODELS_STORAGE_KEY = 'mcp-models';

// 服务数据存储
const serviceDataMap = ref<Record<string, ServiceData>>({});
const serviceDetailsMap = ref<Record<string, ServiceData>>({});

// 当前选中的服务
const selectedService = ref('');

// 精简后的服务列表
const servicesList = ref<ServiceListItem[]>([]);

// 表单状态跟踪
const hasUnsavedChanges = ref(false);
const originalFormData = ref<string>('');
const isDeleting = ref(false);
const isLoading = ref(true);
const isAddingNewService = ref(false);

// 当前服务的数据
const serviceData = ref<{
  apiKey: string;
  apiUrl: string;
  models: Record<string, ModelGroup>;
  avatar?: string;
  backgroundColor?: string;
}>({
  apiKey: '',
  apiUrl: '',
  models: {}
});

// 当前服务的模型组
const serviceModels = ref<ModelGroup[]>([]);

// 跟踪是否无需API密钥
const noApiKeyRequired = ref(false);
const getCurrentUsername = () => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) return '';
    const profile = JSON.parse(raw);
    return String(profile?.username || '').trim();
  } catch (_) {
    return '';
  }
};
const isCurrentUserAdmin = computed(() => getCurrentUsername().toLowerCase() === 'admin');
const isReadonly = computed(() => !isCurrentUserAdmin.value);

// 模态窗口状态
const addProviderModalVisible = ref(false);
const addModelModalVisible = ref(false);
const editModelModalVisible = ref(false);
const editProviderModalVisible = ref(false);

const getServiceKey = (service?: Partial<ServiceListItem> | null) => {
  if (!service) return '';
  return String(service.id || service.name || '');
};

const findServiceByKey = (serviceKey: string) => {
  if (!serviceKey) return undefined;
  return servicesList.value.find(s => getServiceKey(s) === serviceKey || s.name === serviceKey);
};

const getServiceDetail = (serviceKey: string) => {
  const serviceItem = findServiceByKey(serviceKey);
  if (!serviceItem) return null;
  return serviceDetailsMap.value[getServiceKey(serviceItem)] || serviceDataMap.value[serviceItem.name] || null;
};

const selectedServiceItem = computed(() => findServiceByKey(selectedService.value) || null);
const selectedServiceName = computed(() => selectedServiceItem.value?.name || '');

// 编辑模型相关状态
const editingModel = ref<ModelData | null>(null);

// 当前供应商数据（用于编辑）
const currentProviderData = computed<ProviderData | null>(() => {
  if (!selectedService.value) return null;

  const currentService = selectedServiceItem.value;
  if (!currentService) return null;

  return {
    name: currentService.name,
    iconText: currentService.iconText,
    avatar: currentService.avatar,
    backgroundColor: currentService.backgroundColor,
    providerIcon: currentService.providerIcon
  };
});

// 计算当前服务的数据
const currentServiceData = computed(() => {
  if (!selectedService.value) return null;

  // 从服务列表中找到当前服务
  const serviceItem = selectedServiceItem.value;
  // 从服务数据映射中找到详细数据
  const serviceData = getServiceDetail(selectedService.value);

  if (!serviceItem && !serviceData) return null;

  // 合并数据
  return {
    ...(serviceItem || {}),
    ...(serviceData || {})
  };
});

// 获取服务图标文字
const getServiceIconText = (serviceName: string) => {
  const service = findServiceByKey(serviceName);
  const displayName = service?.name || serviceName;
  return service ? service.iconText : displayName.charAt(0).toUpperCase();
};

import { MODEL_TYPE_OPTIONS } from '@/components/model-service/types';

// 获取模型类型标签
const getModelTypeLabel = (typeValue: string) => {
  const option = MODEL_TYPE_OPTIONS.find(opt => opt.value === typeValue);
  return option ? option.label : typeValue;
};

// 触发模型列表变更事件
const triggerModelsChangedEvent = () => {
  // 先刷新chatStore中的模型列表
  const chatStore = useChatStore();
  chatStore.refreshModelList();

  // 然后触发自定义事件
  window.dispatchEvent(new Event('mcp-models-changed'));
};

const normalizeApiModelGroups = (item: any): any[] => {
  const rawModels = Array.isArray(item?.models) ? item.models : [];
  if (rawModels.length === 0) return [];
  if (Array.isArray(rawModels[0]?.models)) {
    return rawModels;
  }
  return [{
    id: item.id || item.name || 'default',
    name: item.name || item.id || 'default',
    models: rawModels
  }];
};

const reloadFromServer = async (): Promise<number> => {
  try {
    const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
    const arr = await listPlatformModels();
    const nextServices: ServiceListItem[] = arr.map((item: any) => ({
      id: item.id,
      name: item.name,
      iconClass: 'custom',
      iconText: (item.name || 'P').charAt(0).toUpperCase(),
      avatar: item.avatar?.url || '',
      backgroundColor: item.backgroundColor || undefined,
      providerIcon: item.providerIcon || resolveProviderIcon(item.name)
    }));
    const nextMap: Record<string, ServiceData> = {} as any;
    const nextDetailsMap: Record<string, ServiceData> = {} as any;
    arr.forEach((item: any) => {
      const groupsRecord: Record<string, ModelGroup> = {} as any;
      const normalizedGroups = normalizeApiModelGroups(item);
      normalizedGroups.forEach((g: any) => {
        groupsRecord[g.id] = {
          id: g.id,
          name: g.name || g.id,
          models: (g.models || []).map((m: any) => ({
            id: m.id,
            name: m.name || m.id,
            iconText: m.iconText || (m.name || 'M').charAt(0).toUpperCase(),
            types: m.types || [],
            contextSize: typeof m.contextSize === 'number'
              ? m.contextSize
              : (typeof m.context_size === 'number' ? m.context_size : undefined)
          }))
        };
      });
      const detail = {
        apiKey: item.credentials?.apiKey || (item.noApiKeyRequired ? 'sk-no-key' : ''),
        apiUrl: sanitizeUrl(item.connection?.apiBaseUrl),
        models: groupsRecord,
        modelsArray: normalizedGroups.map((g: any) => ({
          id: g.id,
          name: g.name || g.id,
          models: (g.models || []).map((m: any) => ({
            id: m.id,
            name: m.name || m.id,
            iconText: m.iconText || (m.name || 'M').charAt(0).toUpperCase(),
            types: m.types || [],
            contextSize: typeof m.contextSize === 'number'
              ? m.contextSize
              : (typeof m.context_size === 'number' ? m.context_size : undefined)
          }))
        })),
        avatar: item.avatar?.url || '',
        backgroundColor: item.backgroundColor || undefined,
        type: item.type || 'OpenAI',
        noApiKeyRequired: !!item.noApiKeyRequired,
        providerIcon: item.providerIcon || resolveProviderIcon(item.name)
      } as any;
      nextMap[item.name] = detail;
      nextDetailsMap[getServiceKey({ id: item.id, name: item.name })] = detail;
    });
    servicesList.value = nextServices;
    serviceDataMap.value = nextMap;
    serviceDetailsMap.value = nextDetailsMap;
    saveData();
    return arr.length;
  } catch (e) { return 0; }
};

const handleSaveServiceClick = async () => {
  if (isReadonly.value) return;
  await saveServiceData(false);
};

// 服务顺序变更后，调用后端接口保存顺序并刷新列表
const onServiceOrderChange = async () => {
  if (isReadonly.value) return;
  try {
    const ids = servicesList.value.map((s: any) => s.id).filter((id: any) => !!id);
    if (ids.length !== servicesList.value.length) {
      NotificationService.warning('服务ID未加载，正在刷新列表');
      await reloadFromServer();
      return;
    }
    await reorderPlatformModels(ids);
    await reloadFromServer();
  } catch (e) {
    NotificationService.error('更新服务顺序失败');
  }
};

// 获取当前表单数据的字符串表示
const getCurrentFormDataString = () => {
  return JSON.stringify({
    apiKey: serviceData.value.apiKey,
    apiUrl: serviceData.value.apiUrl,
    models: serviceData.value.models,
    serviceModels: serviceModels.value,
    noApiKeyRequired: noApiKeyRequired.value
  });
};

// 检查表单是否有实际内容
const hasFormContent = () => {
  const hasApiKey = serviceData.value.apiKey && serviceData.value.apiKey.trim() !== '' && serviceData.value.apiKey !== 'sk-no-key';
  const hasApiUrl = serviceData.value.apiUrl && serviceData.value.apiUrl.trim() !== '';
  const hasModels = serviceModels.value.length > 0;

  return noApiKeyRequired.value || hasApiKey || hasApiUrl || hasModels;
};

// 检查是否有未保存的更改或空表单需要提醒
const checkUnsavedChanges = () => {
  // 如果正在删除服务，不检查未保存更改
  if (isDeleting.value) {
    return false;
  }

  const currentData = getCurrentFormDataString();
  hasUnsavedChanges.value = originalFormData.value !== currentData;
  return hasUnsavedChanges.value;
};

// 检查是否需要显示确认框（包括空表单提醒）
const shouldShowConfirm = () => {
  // 如果正在删除服务，不显示确认框
  if (isDeleting.value) {
    return false;
  }

  // 如果有未保存的更改，显示确认框
  if (checkUnsavedChanges()) {
    return true;
  }

  // 如果表单为空且有选中的服务，也显示确认框提醒
  return (selectedService.value && !hasFormContent() && !isAddingNewService.value);
};

// 显示确认对话框
const showUnsavedChangesConfirm = (callback: () => void) => {
  const hasChanges = checkUnsavedChanges();
  const isEmpty = selectedService.value && !hasFormContent();

  let title = '确认操作';
  let content = '';

  if (hasChanges && isEmpty) {
    title = '未保存的更改';
    content = '您有未保存的表单更改，且当前服务配置为空，无法在对话中使用。确定要离开吗？';
  } else if (hasChanges) {
    title = '未保存的更改';
    content = '您有未保存的表单更改，确定要离开吗？';
  } else if (isEmpty) {
    title = '服务配置为空';
    content = '当前服务配置为空，无法在对话过程中使用该服务。确定要离开吗？';
  }

  Modal.confirm({
    title,
    icon: createVNode(ExclamationCircleOutlined),
    content,
    okText: '离开',
    okType: 'danger',
    cancelText: '取消',
    style: {
      top: '250px'
    },
    onOk() {
      hasUnsavedChanges.value = false;
      callback();
    },
    onCancel() {
      // 用户取消
    },
  });
};

// 重置表单状态
const resetFormState = () => {
  originalFormData.value = getCurrentFormDataString();
  hasUnsavedChanges.value = false;
};

// 显示删除服务的确认对话框
const showDeleteServiceModal = () => {
  if (isReadonly.value) return;
  if (!selectedService.value) return;

  Modal.confirm({
    title: '确认删除模型服务',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `确定要删除“${selectedServiceName.value}”吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk() {
      return confirmDeleteService();
    },
    onCancel() {
      // 取消删除
    },
  });
};

// 确认删除服务（后端接口）
const confirmDeleteService = async () => {
  if (isReadonly.value) return;
  if (!selectedService.value) return;

  isDeleting.value = true;
  try {
    const idx = servicesList.value.findIndex(s => getServiceKey(s) === selectedService.value);
    const serviceItem = servicesList.value[idx];
    const uuid = (serviceItem as any)?.id;
    const deletedServiceName = selectedServiceName.value;
    if (!uuid) {
      NotificationService.error('未找到服务ID，无法删除');
      isDeleting.value = false;
      return;
    }

    await deletePlatformModel({ uuid });

    const chatStore = useChatStore();
    const prevModel = chatStore.model;

    await reloadFromServer();

    // 重新选择服务
    let nextKey = '';
    if (idx !== -1 && servicesList.value.length > 0) {
      if (idx < servicesList.value.length) nextKey = getServiceKey(servicesList.value[idx]);
      if (!nextKey && servicesList.value.length > 0) nextKey = getServiceKey(servicesList.value[Math.max(0, idx - 1)]);
    }
    if (nextKey) {
      loadServiceData(nextKey);
    } else {
      selectedService.value = '';
      serviceData.value = { apiKey: '', apiUrl: '', models: {} };
      serviceModels.value = [];
      resetFormState();
    }

    // 校验当前模型是否仍可用
    chatStore.refreshModelList();
    const stillExists = chatStore.availableModels.some((m: any) => m.id === prevModel);
    if (!stillExists) {
      const first = chatStore.availableModels[0]?.id || '';
      chatStore.setModel(first || '');
      chatStore.applyConfig();
    }

    NotificationService.success('服务已删除');

    try {
      const allAgents = StorageService.getAgents();
      const updatedAgents = allAgents.map((agent: any) => {
        const m = agent?.config?.model || {};
        if (m.service === deletedServiceName) {
          return {
            ...agent,
            config: {
              ...agent.config,
              model: {
                ...m,
                service: '',
                name: '',
                apiKey: '',
                apiUrl: ''
              }
            }
          };
        }
        return agent;
      });
      StorageService.setAgents(updatedAgents);
      try { window.dispatchEvent(new CustomEvent('agents-updated', { detail: { agents: updatedAgents } })); } catch {}

      const changedAgents = updatedAgents.filter((a: any, i: number) => {
        const prev = allAgents[i];
        const pm = prev?.config?.model || {};
        const nm = a?.config?.model || {};
        return pm.service !== nm.service || pm.name !== nm.name || pm.apiKey !== nm.apiKey || pm.apiUrl !== nm.apiUrl;
      });
      try {
        await Promise.all(changedAgents.map((agent: any) => {
          const agentType = agent.agent_type || agent.config?.basic?.type || 'assistant';
          const isDeepAgent = agentType === 'deepagent';

          return updateAiAgent({
          uuid: agent.uuid,
          id: agent.id,
          name: agent.name,
          description: agent.description,
          themeColor: agent.themeColor,
          agent_type: agentType,
          ...(isDeepAgent ? {
            visibility: agent.visibility || agent.config?.basic?.visibility || 'private',
            skills: Array.isArray(agent.skills) ? agent.skills : (Array.isArray(agent.config?.skills) ? agent.config.skills : [])
          } : {}),
          config: agent.config
        });
        }));
      } catch {}

      try {
        const res = await listAiAgents();
        const arr: any[] = Array.isArray(res?.data) ? res.data : [];
        const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
        const mapped = arr.map((item: any) => {
          const mm = item.config?.model || {};
          const basicConfig = {
            ...(item.config?.basic || {}),
            type: item.config?.basic?.type || item.agent_type || 'assistant',
            visibility: item.config?.basic?.visibility || item.visibility || 'private'
          };
          const skills = Array.isArray(item.skills) ? item.skills : (Array.isArray(item.config?.skills) ? item.config.skills : []);
          const normalizedModel = {
            service: mm.service,
            name: mm.name,
            temperature: typeof mm.temperature === 'number' ? mm.temperature : 0.7,
            top_p: typeof mm.topP === 'number' ? mm.topP : (typeof mm.top_p === 'number' ? mm.top_p : 1.0),
            presence_penalty: typeof mm.presencePenalty === 'number' ? mm.presencePenalty : (typeof mm.presence_penalty === 'number' ? mm.presence_penalty : 0),
            frequency_penalty: typeof mm.frequencyPenalty === 'number' ? mm.frequencyPenalty : (typeof mm.frequency_penalty === 'number' ? mm.frequency_penalty : 0),
            apiKey: mm.apiKey,
            apiUrl: sanitizeUrl(mm.apiUrl)
          };
          return {
            id: item.id,
            name: item.name,
            description: item.description,
            themeColor: item.themeColor,
            uuid: item.uuid,
            agent_type: item.agent_type || basicConfig.type,
            visibility: item.visibility || basicConfig.visibility,
            skills,
            config: {
              basic: basicConfig,
              prompt: { ...(item.config?.prompt || {}) },
              model: normalizedModel,
              knowledge: { ...(item.config?.knowledge || {}) },
              mcp: { ...(item.config?.mcp || { enabledServerIdentifiers: [] }) },
              skills,
              phrases: Array.isArray(item.config?.phrases) ? item.config.phrases : []
            }
          } as any;
        });
        StorageService.setAgents(mapped);
        window.dispatchEvent(new Event('agents-updated'));
      } catch {}

      try {
        const activeAgent = StorageService.getActiveAgent();
        const am = activeAgent?.model || {};
        if (am.service === deletedServiceName) {
          const updatedActive = {
            ...activeAgent,
            model: { ...am, service: '', name: '', apiKey: '', apiUrl: '' }
          };
          StorageService.setActiveAgent(updatedActive);
          window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: updatedActive } }));
        }
      } catch {}
    } catch {}
  } catch (e) {
    NotificationService.error('删除失败，请稍后重试');
  } finally {
    isDeleting.value = false;
  }
};

// 加载本地存储的数据
const loadSavedData = () => {
  try {
    // 加载提供商列表
    const savedProviders = localStorage.getItem(PROVIDERS_STORAGE_KEY);
    if (savedProviders) {
      servicesList.value = JSON.parse(savedProviders);
    }

    // 加载服务数据
    const savedServiceData = localStorage.getItem(MODELS_STORAGE_KEY);
    if (savedServiceData) {
      serviceDataMap.value = JSON.parse(savedServiceData);
    }

    serviceDetailsMap.value = servicesList.value.reduce((acc, service) => {
      const key = getServiceKey(service);
      const detail = serviceDataMap.value[service.name];
      if (key && detail) {
        acc[key] = detail;
      }
      return acc;
    }, {} as Record<string, ServiceData>);

    // 默认选择第一个服务项或之前选择的服务
    if (servicesList.value.length > 0) {
      // 如果已有选中的服务且该服务存在于列表中
      if (selectedService.value && servicesList.value.some(s => getServiceKey(s) === selectedService.value)) {
        // 直接设置服务数据，不调用handleServiceClick
        const data = getServiceDetail(selectedService.value);
        if (data) {
          serviceData.value = {
            apiKey: data.apiKey || '',
            apiUrl: data.apiUrl || '',
            models: data.models || {}
          };
          serviceModels.value = (data as any).modelsArray || Object.values(data.models || {});
          noApiKeyRequired.value = data.noApiKeyRequired || false;
        }
      } else {
        // 否则选择第一个服务
        selectedService.value = getServiceKey(servicesList.value[0]);
        // 直接设置服务数据，不调用handleServiceClick
        const data = getServiceDetail(selectedService.value);
        if (data) {
          serviceData.value = {
            apiKey: data.apiKey || '',
            apiUrl: data.apiUrl || '',
            models: data.models || {}
          };
          serviceModels.value = Object.values(data.models || {});
          noApiKeyRequired.value = data.noApiKeyRequired || false;
        }
      }
    }
  } catch (e) {
    console.error('Failed to load saved configuration:', e);
  }
};

// 保存本地存储数据
const saveData = () => {
  try {
    localStorage.setItem(PROVIDERS_STORAGE_KEY, JSON.stringify(servicesList.value));
    localStorage.setItem(MODELS_STORAGE_KEY, JSON.stringify(serviceDataMap.value));

    // 保存后触发模型列表变更事件
    triggerModelsChangedEvent();
  } catch (e) {
    console.error('Failed to save configuration:', e);
  }
};

// 显示添加供应商的模态窗口
const showAddProviderModal = () => {
  if (isReadonly.value) return;
  addProviderModalVisible.value = true;
};

// 根据名称解析提供商图标类型
const resolveProviderIcon = (name: string): 'siliconcloud' | 'bailian' | 'baiducloud' | undefined => {
  if (!name) return undefined;
  if (name.includes('硅基流动')) return 'siliconcloud';
  if (name.includes('阿里云百炼')) return 'bailian';
  if (name.includes('百度智能云')) return 'baiducloud';
  return undefined;
};

// 处理添加供应商确认
const handleAddProviderConfirm = async (formData: ProviderFormData) => {
  // 设置添加新服务标志
  isAddingNewService.value = true;

  // 使用当前显示的背景色，而不是重新生成
  const backgroundColor = !formData.avatar ? formData.backgroundColor : undefined;
  const providerIcon = formData.providerIcon || resolveProviderIcon(formData.name);

  // 创建新的服务提供商对象
  const newService: ServiceListItem = {
    name: formData.name,
    iconClass: 'custom',
    iconText: formData.icon,
    avatar: formData.avatar,
    backgroundColor: backgroundColor,
    providerIcon: providerIcon
  };

  const toModelsArray = (models: Record<string, ModelGroup> | undefined) => {
    if (!models) return [] as any[];
    return Object.values(models).map(g => ({
      id: g.id,
      name: g.name,
      models: g.models.map(m => ({
        id: m.id,
        name: m.name,
        iconText: m.iconText,
        types: m.types || [],
        contextSize: m.contextSize,
        context_size: m.contextSize
      }))
    }));
  };
  const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();

  if (formData.serviceData) {
    // 兼容导入的模型结构：如为数组则转换为Map
    const imported = { ...formData.serviceData } as any;
    let modelsMap: Record<string, ModelGroup>;
    if (Array.isArray(imported.models)) {
      modelsMap = (imported.models as ModelGroup[]).reduce((acc: Record<string, ModelGroup>, g: ModelGroup) => { acc[g.id] = g; return acc; }, {});
    } else {
      modelsMap = imported.models || {};
    }

    try {
      const payload = {
        name: formData.name,
        type: formData.type || 'OpenAI',
        noApiKeyRequired: imported.noApiKeyRequired || false,
        connection: { apiBaseUrl: sanitizeUrl(imported.apiUrl) },
        credentials: { apiKey: imported.apiKey || '' },
        providerIcon,
        avatar: formData.avatar ? { url: sanitizeUrl(formData.avatar) } : undefined,
        backgroundColor: backgroundColor,
        models: toModelsArray(modelsMap)
      } as any;
      await addPlatformModel(payload);
      NotificationService.success('已创建模型服务');
    } catch (e) {}
  } else {
    try {
      const payload = {
        name: formData.name,
        type: formData.type || 'OpenAI',
        noApiKeyRequired: true,
        connection: { apiBaseUrl: '' },
        credentials: { apiKey: '' },
        providerIcon,
        avatar: formData.avatar ? { url: sanitizeUrl(formData.avatar) } : undefined,
        backgroundColor: backgroundColor,
        models: []
      } as any;
      await addPlatformModel(payload);
      NotificationService.success('已创建模型服务');
    } catch (e) {}
  }

  await reloadFromServer();

  const addedService = [...servicesList.value].reverse().find(s => s.name === newService.name) || servicesList.value[0];
  if (addedService) {
    selectedService.value = getServiceKey(addedService);
    loadServiceData(selectedService.value);
  }

  // 刷新模型列表
  const chatStore = useChatStore();
  chatStore.refreshModelList();

  // 触发模型列表变更事件
  triggerModelsChangedEvent();

  // 关闭模态窗口
  addProviderModalVisible.value = false;

  NotificationService.success('模型服务添加成功');

  // 滚动到新添加的项
  setTimeout(() => {
    const newItemElement = document.querySelector(`.service-item.selected`);
    if (newItemElement) {
      newItemElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
    // 重置添加新服务标志
    isAddingNewService.value = false;
  }, 100);
};

// 处理服务项点击
const handleServiceClick = (service: ServiceListItem) => {
  const serviceKey = getServiceKey(service);
  // 检查是否需要显示确认框
  if (shouldShowConfirm()) {
    showUnsavedChangesConfirm(() => {
      loadServiceData(serviceKey);
    });
  } else {
    loadServiceData(serviceKey);
  }
};

// 加载服务数据
const loadServiceData = (serviceKey: string) => {
  selectedService.value = serviceKey;
  const data = getServiceDetail(serviceKey);

  // 加载服务数据
  if (data) {
    serviceData.value = {
      apiKey: data.apiKey || '',
      apiUrl: data.apiUrl || '',
      models: data.models || {},
      avatar: data.avatar,
      backgroundColor: data.backgroundColor
    };

    // 转换模型组数据结构（优先使用服务端数组以保持顺序）
    serviceModels.value = (data as any).modelsArray || Object.values(data.models || {});

    // 设置是否需要API密钥的状态
    noApiKeyRequired.value = data.noApiKeyRequired || false;
  } else {
    // 初始化新服务数据
    serviceData.value = {
      apiKey: '',
      apiUrl: '',
      models: {},
      avatar: undefined,
      backgroundColor: undefined
    };
    serviceModels.value = [];
    noApiKeyRequired.value = false;
  }

  // 重置表单状态
  resetFormState();
};

// 添加路由守卫
onBeforeRouteLeave((_, __, next) => {
  if (shouldShowConfirm()) {
    showUnsavedChangesConfirm(() => {
      next();
    });
  } else {
    next();
  }
});

// 监听表单变更
watch(
  () => [serviceData.value.apiKey, serviceData.value.apiUrl, serviceData.value.models, serviceModels.value, noApiKeyRequired.value],
  () => {
    checkUnsavedChanges();
  },
  { deep: true }
);

// 监听页面刷新和关闭
onBeforeUnmount(() => {
  const handleBeforeUnload = (e: BeforeUnloadEvent) => {
    if (shouldShowConfirm()) {
      e.preventDefault();
      e.returnValue = '';
    }
  };

  window.addEventListener('beforeunload', handleBeforeUnload);

  return () => {
    window.removeEventListener('beforeunload', handleBeforeUnload);
  };
});

// 保存服务数据（调用后端更新）
const saveServiceData = async (force: boolean = false) => {
  if (isReadonly.value) return;
  if (!selectedService.value) return;

  // 配置完整性检查
  const hasApiKey = noApiKeyRequired.value || (serviceData.value.apiKey && serviceData.value.apiKey.trim() !== '');
  const hasApiUrl = serviceData.value.apiUrl && serviceData.value.apiUrl.trim() !== '';
  const hasModels = serviceModels.value.length > 0;

  // 检查所有必需配置是否完整
  if (!force && (!hasApiKey || !hasApiUrl || !hasModels)) {
    const missingItems = [];
    if (!hasApiKey) missingItems.push('API密钥');
    if (!hasApiUrl) missingItems.push('API地址');
    if (!hasModels) missingItems.push('模型配置');

    NotificationService.warning(`请完成以下配置后再保存：${missingItems.join('、')}`);
    return;
  }

  // 构造更新 payload
  const uuid = selectedServiceItem.value?.id;
  const selectedDetail = getServiceDetail(selectedService.value);
  const type = (selectedDetail?.type) || 'OpenAI';
  const providerIcon = selectedServiceItem.value?.providerIcon || selectedDetail?.providerIcon;
  const avatarUrl = serviceData.value.avatar;
  const bgColor = serviceData.value.backgroundColor;
  const apiBaseUrl = serviceData.value.apiUrl;
  const apiKeyVal = noApiKeyRequired.value ? '' : serviceData.value.apiKey;
  const modelsArray = serviceModels.value.map(g => ({
    id: g.id,
    name: g.name,
    models: g.models.map(m => ({
      id: m.id,
      name: m.name,
      iconText: m.iconText,
      types: m.types || [],
      contextSize: m.contextSize,
      context_size: m.contextSize
    }))
  }));

  const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
  const payload: any = {
    uuid,
    name: selectedServiceName.value,
    type,
    noApiKeyRequired: !!noApiKeyRequired.value,
    connection: { apiBaseUrl: sanitizeUrl(apiBaseUrl) },
    credentials: { apiKey: apiKeyVal },
    providerIcon,
    avatar: avatarUrl ? { url: sanitizeUrl(avatarUrl) } : undefined,
    backgroundColor: bgColor,
    models: modelsArray
  };

  try {
    await updatePlatformModel(payload);
    await reloadFromServer();
  } catch (e) {
    NotificationService.error('保存失败，请检查后重试');
    return;
  }

  // 获取当前选择的模型
  const chatStore = useChatStore();
  const currentModel = chatStore.model;

  // 检查当前选择的模型是否属于该服务
  let isCurrentModelFromThisService = false;

  // 遍历服务中的所有模型组和模型
  Object.values((getServiceDetail(selectedService.value)?.models) || {}).forEach(group => {
    group.models.forEach(model => {
      if (model.id === currentModel) {
        isCurrentModelFromThisService = true;
      }
    });
  });

  // 刷新列表后，如果当前选择的模型属于该服务，则同步配置并重新选择
  if (isCurrentModelFromThisService) {
    // 设置API配置 - 确保使用一致的数据源
    chatStore.setApiKey(getServiceDetail(selectedService.value)?.apiKey || '');
    chatStore.setApiBaseUrl(getServiceDetail(selectedService.value)?.apiUrl || '');

    // 立即应用配置以保存到mcp-client-api-config
    chatStore.applyConfig();

    // 重新应用配置
    setTimeout(() => {
      // 重新应用当前模型配置
      chatStore.applyConfig();

      // 刷新模型列表，确保其他组件能获取到最新配置
      chatStore.refreshModelList();

      // 触发模型列表变更事件
      triggerModelsChangedEvent();
    }, 100);
  } else {
    // 即使当前模型不属于该服务，也刷新模型列表
    chatStore.refreshModelList();

    // 触发模型列表变更事件
    triggerModelsChangedEvent();
  }

  // 重置表单状态
  resetFormState();

  // 同步智能体配置 - 将更新后的API配置同步到所有使用该服务的智能体
  try {
    const serviceName = selectedServiceName.value;
    if (serviceName) {
      // 获取当前更新后的API配置
      const currentDetail = getServiceDetail(selectedService.value);
      const updatedConfig = {
        apiKey: currentDetail?.apiKey || '',
        apiUrl: currentDetail?.apiUrl || ''
      };

      // 1. 同步所有智能体配置(mcp-agents)
      const allAgents = StorageService.getAgents();
      const updatedAgents = allAgents.map((agent: any) => {
        // 检查智能体是否使用了该模型服务
        if (agent.config?.model?.service === serviceName) {
          // 更新智能体中的API配置
          return {
            ...agent,
            config: {
              ...agent.config,
              model: {
                ...agent.config.model,
                ...updatedConfig
              }
            }
          };
        }
        return agent;
      });

      // 保存更新后的智能体列表
      StorageService.setAgents(updatedAgents);

      // 2. 同步当前活跃智能体配置(mcp-active-agent)
      const activeAgent = StorageService.getActiveAgent();
      if (activeAgent && activeAgent.model?.service === serviceName) {
        // 更新活跃智能体的API配置
        const updatedActiveAgent = {
          ...activeAgent,
          model: {
            ...activeAgent.model,
            ...updatedConfig
          }
        };

        // 保存更新后的活跃智能体
        StorageService.setActiveAgent(updatedActiveAgent);
      }
    }
  } catch (e) {
    console.error('同步智能体配置失败:', e);
  }

  NotificationService.success('配置已保存');
};

// 显示添加模型模态窗口
const showAddModelModal = () => {
  if (isReadonly.value) return;
  addModelModalVisible.value = true;
};

// 处理添加模型确认
const handleAddModelConfirm = async (formData: ModelFormData) => {
  if (isReadonly.value) return;
  // 检查模型组是否存在
  const groupId = formData.id.split('/')[0] || formData.id;
  const existingGroup = serviceModels.value.find(g => g.id === groupId);

  if (existingGroup) {
    // 添加到现有组
    existingGroup.models.push({
      id: formData.id,
      name: formData.name,
      iconText: formData.iconText,
      types: formData.types,
      contextSize: formData.contextSize
    });
  } else {
    // 创建新组
    serviceModels.value.push({
      id: groupId,
      name: groupId,
      models: [{
        id: formData.id,
        name: formData.name,
        iconText: formData.iconText,
        types: formData.types,
        contextSize: formData.contextSize
      }]
    });
  }

  await saveServiceData(true);
  addModelModalVisible.value = false;

  // 检查是否需要重新初始化聊天模型数据
  const chatStore = useChatStore();
  if (!chatStore.model) {
    chatStore.setModel(formData.id);
    chatStore.applyConfig();
  }

  // 刷新模型列表，确保选择模型的下拉列表更新
  chatStore.refreshModelList();

  // 触发模型列表变更事件
  triggerModelsChangedEvent();
};

// 确认删除模型
const confirmDeleteModel = async (groupId: string, modelId: string) => {
  if (isReadonly.value) return;
  const groupIndex = serviceModels.value.findIndex(g => g.id === groupId);
  if (groupIndex !== -1) {
    const modelIndex = serviceModels.value[groupIndex].models.findIndex(m => m.id === modelId);
    if (modelIndex !== -1) {
      // 获取将被删除的模型
      const deletedModel = serviceModels.value[groupIndex].models[modelIndex];

      // 从模型组中删除模型
      serviceModels.value[groupIndex].models.splice(modelIndex, 1);

      // 如果模型组为空，删除模型组
      if (serviceModels.value[groupIndex].models.length === 0) {
        serviceModels.value.splice(groupIndex, 1);
      }

      await saveServiceData(true);

      // 检查是否删除的是当前选中的模型
      const chatStore = useChatStore();
      if (chatStore.model === deletedModel.id) {
        // 强制重新验证模型选择
        setTimeout(() => {
          // 查找可用的其他模型
          if (chatStore.availableModels.length > 0) {
            // 选择第一个可用模型
            chatStore.setModel(chatStore.availableModels[0].id);
            chatStore.applyConfig();
          } else {
            // 如果没有可用模型，重置模型选择
            chatStore.setModel('');
          }
        }, 100); // 短暂延迟确保存储更新完成
      }

      // 刷新模型列表，确保选择模型的下拉列表更新
      chatStore.refreshModelList();

      // 触发模型列表变更事件
      triggerModelsChangedEvent();
    }
  }
};

// API地址相关
const apiPreviewUrl = computed(() => {
  let base = serviceData.value.apiUrl?.trim() || '';
  if (!base) return '/v1/chat/completions';
  // 去除末尾所有斜杠
  while (base.endsWith('/')) base = base.slice(0, -1);

  // 处理URL，显示实际会发送请求的URL
  if (base.includes('/chat/completions')) {
    // 如果URL中已经包含完整路径，直接返回
    if (base.endsWith('/chat/completions')) {
      return base;
    }
    // 找到/chat/completions的位置
    const index = base.indexOf('/chat/completions');
    // 截取到这个位置
    const baseUrl = base.substring(0, index);
    // 检查是否已经包含/v1路径
    if (baseUrl.endsWith('/v1') || baseUrl.includes('/v1/')) {
      return baseUrl + '/chat/completions';
    } else {
      return baseUrl + '/v1/chat/completions';
    }
  }
  // 如果URL以/v1/chat结尾
  else if (base.endsWith('/v1/chat')) {
    return base + '/completions';
  }
  // 如果URL以/v1结尾
  else if (base.endsWith('/v1')) {
    return base + '/chat/completions';
  }
  // 其他情况，添加完整路径
  return base + '/v1/chat/completions';
});

// 显示编辑模型模态窗口
const showEditModelModal = (model: Model) => {
  if (isReadonly.value) return;
  editingModel.value = { ...model };
  editModelModalVisible.value = true;
};

// 处理编辑模型确认
const handleEditModelConfirm = async (formData: EditModelFormData) => {
  if (isReadonly.value) return;
  if (!editingModel.value) return;

  // 更新模型数据
  const groupId = editingModel.value.id.split('/')[0] || editingModel.value.id;
  const groupIndex = serviceModels.value.findIndex(g => g.id === groupId);

  if (groupIndex !== -1) {
    const modelIndex = serviceModels.value[groupIndex].models.findIndex(m => m.id === editingModel.value!.id);
    if (modelIndex !== -1) {
      serviceModels.value[groupIndex].models[modelIndex].name = formData.name;
      serviceModels.value[groupIndex].models[modelIndex].types = formData.types;
      serviceModels.value[groupIndex].models[modelIndex].contextSize = formData.contextSize;
    }
  }

  await saveServiceData(true);

  // 刷新模型列表，确保选择模型的下拉列表更新
  const chatStore = useChatStore();
  chatStore.refreshModelList();

  // 触发模型列表变更事件
  triggerModelsChangedEvent();

  editModelModalVisible.value = false;
};

// 显示编辑供应商的模态窗口
const showEditProviderModal = () => {
  if (isReadonly.value) return;
  if (!selectedService.value) return;
  editProviderModalVisible.value = true;
};

// 处理编辑供应商确认
const handleEditProviderConfirm = async (formData: EditProviderFormData) => {
  if (isReadonly.value) return;
  const originalName = formData.originalName;
  const newName = formData.name;
  const providerIcon = formData.providerIcon || resolveProviderIcon(formData.name);

  const item = selectedServiceItem.value || servicesList.value.find(s => s.name === originalName);
  const uuid = (item as any)?.id;
  const current = getServiceDetail(selectedService.value) || { apiKey: '', apiUrl: '', models: {}, type: 'OpenAI', noApiKeyRequired: false } as any;
  const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
  const groupsArray = (Object.values(current.models || {}) as ModelGroup[]).map(g => ({
    id: g.id,
    name: g.name,
    models: (g.models || []).map(m => ({
      id: m.id,
      name: m.name,
      iconText: m.iconText,
      types: m.types || [],
      contextSize: m.contextSize,
      context_size: m.contextSize
    }))
  }));

  const payload: any = {
    uuid,
    name: newName,
    type: current.type || 'OpenAI',
    noApiKeyRequired: !!current.noApiKeyRequired,
    connection: { apiBaseUrl: sanitizeUrl(current.apiUrl) },
    credentials: { apiKey: current.noApiKeyRequired ? '' : (current.apiKey || '') },
    providerIcon,
    avatar: formData.avatar ? { url: sanitizeUrl(formData.avatar) } : undefined,
    backgroundColor: !formData.avatar ? formData.backgroundColor : undefined,
    models: groupsArray
  };

  try {
    await updatePlatformModel(payload);
    await reloadFromServer();
    const updatedService = servicesList.value.find(s => s.id === uuid) || [...servicesList.value].reverse().find(s => s.name === newName);
    if (updatedService) {
      selectedService.value = getServiceKey(updatedService);
      loadServiceData(selectedService.value);
    }
    const chatStore = useChatStore();
    chatStore.refreshModelList();
    triggerModelsChangedEvent();
    editProviderModalVisible.value = false;
    NotificationService.success('模型服务更新成功');
  } catch (e) {
    NotificationService.error('更新失败，请稍后重试');
  }
};

// 组件加载时获取保存的数据
onMounted(async () => {
  isLoading.value = true;
  const count = await reloadFromServer();
  if (!count) {
    loadSavedData();
  } else {
    if (!selectedService.value && servicesList.value.length > 0) {
      selectedService.value = getServiceKey(servicesList.value[0]);
      loadServiceData(selectedService.value);
    }
  }
  await nextTick(() => {
    resetFormState();
  });
  isLoading.value = false;
});

// 监听noApiKeyRequired的变化
watch(noApiKeyRequired, (newValue) => {
  if (newValue) {
    // 当选中"无需API密钥"时，设置默认值
    serviceData.value.apiKey = 'sk-no-key';
  } else {
    // 当取消选中时，如果当前值是默认值，则清空
    if (serviceData.value.apiKey === 'sk-no-key') {
      serviceData.value.apiKey = '';
    }
  }
});

// 判断是否应该显示特定图标
const shouldShowIcon = (modelName: string, iconType: string) => {
  return shouldShowModelIcon(modelName, iconType);
};

// 导出当前服务配置为JSON文件
const exportCurrentServiceConfig = () => {
  if (!selectedService.value) {
    NotificationService.warning('请先选择一个模型服务');
    return;
  }

  const name = selectedServiceName.value;
  const provider = selectedServiceItem.value;
  const config = getServiceDetail(selectedService.value) || {
    apiKey: serviceData.value.apiKey,
    apiUrl: serviceData.value.apiUrl,
    models: (() => {
      const map: Record<string, ModelGroup> = {} as any;
      serviceModels.value.forEach(group => { map[group.id] = group; });
      return map;
    })(),
    avatar: serviceData.value.avatar,
    backgroundColor: serviceData.value.backgroundColor,
    noApiKeyRequired: noApiKeyRequired.value,
    providerIcon: provider?.providerIcon
  } as ServiceData;

  const exportPayload = {
    name,
    type: (config as any).type || 'OpenAI',
    provider: provider ? {
      iconText: provider.iconText,
      avatar: provider.avatar,
      backgroundColor: provider.backgroundColor,
      providerIcon: provider.providerIcon
    } : undefined,
    config
  };

  try {
    const json = JSON.stringify(exportPayload, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcp-service-${name}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    NotificationService.success('配置已导出');
  } catch (e) {
    console.error('导出配置失败:', e);
    NotificationService.error('导出配置失败');
  }
};

</script>

<style scoped>
@import '@/assets/styles/model-service-view.css';

:deep(.ant-list-item) {
  padding: 8px 14px;
  margin-bottom: 4px;
}

:deep(.ant-list-split .ant-list-item) {
  border-block-end: 1px solid rgb(255 255 255 / 0%);
}

.model-actions :deep(.anticon) {
  font-size: 16px;
  transition: color 0.3s ease;
}

.model-actions :deep(.anticon:hover) {
  color: #1677ff;
}

.model-actions :deep(.anticon.disabled),
.edit-icon.disabled,
.drag-handle.disabled {
  color: #bfbfbf !important;
  cursor: not-allowed;
}

.service-header-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: bold;
  margin-right: 10px;
}

.service-header-icon-image {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

/* 让供应商图标填充服务图标容器与头部图标容器 */
.provider-icon {
  width: 100%;
  height: 100%;
}

.model-icon-svg {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: white;
}

.model-icon-svg :deep(svg) {
  width: 20px;
  height: 20px;
  fill: currentColor;
}

.model-icon-svg :deep(svg path) {
  fill: currentColor;
}

.header-right {
  display: flex;
  gap: 12px;
  align-items: center;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.readonly-tip {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow: 0 10px 24px -20px rgba(59, 130, 246, 0.55);
}

.readonly-tip-content {
  min-width: 0;
}

.readonly-tip-title {
  font-size: 14px;
  line-height: 1.4;
  font-weight: 600;
  color: #1d4ed8;
}

.readonly-tip-text {
  margin-top: 3px;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
}

.action-btn.primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: #f3f4f6;
  color: #374151;
}

.action-btn.secondary:hover {
  background: #e5e7eb;
}

.action-btn.danger {
  background: #ffeeee;
  color: #ff3939;
}

.action-btn.danger:hover {
  background: #ffc5c5;
}

.add-button-container .add-button {
  width: 100%;
  justify-content: center;
  background: #ffffff;
  border: 1px solid #e1e7eb;
  color: #374151;
}

.add-button-container .add-button:hover {
  background: #e5e7eb;
}
</style>
<style>
.middle-section { position: relative; }
.list-loading-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.6);
  pointer-events: all;
}
.list-loading-content { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.list-loading-text { font-size: 13px; color: #666; }
.right-content { position: relative; }
.loading-content {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
}
.loading-inner { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.loading-text { font-size: 13px; color: #666; }

.confirm-delete-modal .ant-modal-content {
  border-radius: 18px !important;
}

.confirm-delete-modal .ant-modal-confirm-title {
  font-size: 15px !important;
}

.confirm-delete-modal .ant-modal-confirm-content {
  font-size: 13px !important;
  line-height: 1.6 !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn {
  height: 28px !important;
  border-radius: 7px !important;
  font-size: 13px !important;
  padding: 0 16px !important;
  border: none !important;
  box-shadow: none !important;
  transition: all 0.3s !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-default {
  background-color: #f5f5f5 !important;
  color: #1a1a1a !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-default:hover {
  background-color: #e6e6e6 !important;
  color: #1a1a1a !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-primary {
  background: #ff5959 !important;
  color: #ffffff !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-primary:hover {
  background-color: #ff4040 !important;
  color: #ffffff !important;
}

/* 仅对删除模型的确认框修改圆角 */
.custom-delete-popconfirm .ant-popover-inner {
  border-radius: 16px !important;
}

/* 删除模型确认框按钮样式 */
.custom-delete-popconfirm .custom-btn {
  min-width: 60px !important;
  border-radius: 8px !important;
  height: 28px !important;
  font-size: 13px !important;
  font-weight: 400 !important;
  padding: 0 16px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  box-shadow: none !important;
  cursor: pointer !important;
  transition: all 0.3s !important;
}

.custom-delete-popconfirm .cancel-btn {
  background-color: #f5f5f5 !important;
  border: none !important;
  color: #1a1a1a !important;
}

.custom-delete-popconfirm .cancel-btn:hover {
  background-color: #e6e6e6 !important;
  color: #1a1a1a !important;
}

.custom-delete-popconfirm .confirm-btn {
  background: #ff4d4f !important;
  color: #ffffff !important;
  border: none !important;
}

.custom-delete-popconfirm .confirm-btn:hover {
  background-color: #ff7875 !important;
  color: #ffffff !important;
}
</style>
