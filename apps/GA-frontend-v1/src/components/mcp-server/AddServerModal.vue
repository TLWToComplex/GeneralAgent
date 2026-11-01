<template>
  <a-modal
      v-model:open="visible"
      title="添加MCP服务器"
      :footer="null"
      width="550px"
      :maskClosable="false"
      class="add-mcp-server-modal"
      centered
      @cancel="handleCancel"
  >
    <div class="server-form">
      <div class="form-item">
        <div class="form-label required">服务器名称</div>
        <a-input
            v-model:value="formData.name"
            placeholder="请输入服务器名称"
            :status="showNameError ? 'error' : undefined"
        />
        <div v-if="showNameError" class="form-error">请输入服务器名称</div>
      </div>

      <div class="form-item">
        <div class="form-label">服务器描述</div>
        <a-textarea
            v-model:value="formData.description"
            placeholder="请输入服务器描述"
            :auto-size="{ minRows: 3, maxRows: 3 }"
        />
      </div>

      <div class="form-item">
        <div class="visibility-form-label-row">
          <div class="form-label required">可见范围</div>
          <div
            class="bi-visibility-segment"
            :class="{ 'is-readonly': !canEditVisibility }"
            :data-active="formData.visibility"
            role="tablist"
            aria-label="可见范围"
          >
            <button
              type="button"
              class="bi-visibility-segment-option"
              :class="{ active: formData.visibility === 'private' }"
              :aria-pressed="formData.visibility === 'private'"
              :disabled="!canEditVisibility"
              @click="updateVisibility('private')"
            >
              个人使用
            </button>
            <button
              type="button"
              class="bi-visibility-segment-option"
              :class="{ active: formData.visibility === 'public' }"
              :aria-pressed="formData.visibility === 'public'"
              :disabled="!canEditVisibility"
              @click="updateVisibility('public')"
            >
              公开共享
            </button>
          </div>
        </div>
        <div v-if="showVisibilityError" class="form-error">请选择可见范围</div>
      </div>

      <div v-if="canEditVisibility && formData.visibility === 'public'" class="form-item">
        <div class="form-label required">可访问用户组</div>
        <a-select
          v-model:value="formData.permissionGroupIds"
          mode="multiple"
          :options="permissionGroupOptions"
          :loading="permissionGroupLoading"
          :disabled="permissionGroupLoading"
          :virtual="false"
          popupClassName="user-group-select-dropdown"
          max-tag-count="responsive"
          placeholder="请选择用户组"
          style="width: 100%"
          @change="handlePermissionGroupsChange"
        />
        <div v-if="showPermissionGroupsError" class="form-error">请选择至少一个用户组</div>
        <div v-else class="form-help">公开后仅这些用户组可访问该 MCP 服务器</div>
      </div>

      <div class="form-item">
        <div class="form-label required">服务器类型</div>
        <a-select v-model:value="formData.type" style="width: 100%">
          <a-select-option value="sse">服务器发送事件 (SSE)</a-select-option>
          <a-select-option value="streamableHttp">可流式传输的HTTP</a-select-option>
        </a-select>
      </div>

      <div class="form-item">
        <div class="form-label required">服务器URL</div>
        <a-input
            v-model:value="formData.url"
            placeholder="请输入服务器URL"
            :status="showUrlError ? 'error' : undefined"
        />
        <div v-if="showUrlError" class="form-error">请输入有效的服务器URL</div>
      </div>

      <div class="form-item">
        <div class="form-label">请求头</div>
        <div class="headers-list">
          <div v-for="(header, index) in headersList" :key="index" class="header-row">
            <a-input
                v-model:value="header.key"
                placeholder="Key"
                class="header-input header-key"
            />
            <a-input
                v-model:value="header.value"
                placeholder="Value"
                class="header-input header-value"
            />
            <button class="header-remove-btn" @click="removeHeader(index)">
              <span class="header-remove-icon">
                <CloseOutlined style="font-size: 11px;"/>
              </span>
            </button>
          </div>
          <button class="header-add-btn" @click="addHeader">
            <span class="header-add-icon">+</span>
            <span>添加请求头</span>
          </button>
        </div>
      </div>

      <div class="form-item">
        <div class="form-label">超时（秒）</div>
        <a-input-number
            v-model:value="formData.timeout"
            :min="1"
            :max="300"
            :step="1"
            style="width: 100%"
        />
      </div>

      <div class="form-actions">
        <div class="left-actions">
          <div class="mcp-test-section">
            <a-button
                @click="handleTestConnection"
                :loading="testLoading"
                class="mcp-test-button"
                :class="{ 'mcp-test-success': testResult === 'success', 'mcp-test-error': testResult === 'error' }"
            >
              <template #icon>
                <div class="mcp-test-icon-wrapper">
                      <span class="mcp-test-icon" v-if="!testLoading">
                        <svg v-if="testResult === 'success'" class="mcp-success-icon" viewBox="0 0 24 24" width="12"
                             height="12">
                          <path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                        </svg>
                        <svg v-else-if="testResult === 'error'" class="mcp-error-icon" viewBox="0 0 24 24" width="12"
                             height="12">
                          <path fill="currentColor"
                                d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                        <div v-else class="mcp-skeleton-dot"></div>
                      </span>
                  <div v-if="testLoading" class="mcp-loading-spinner">
                    <div class="mcp-spinner-ring"></div>
                  </div>
                </div>
              </template>
              <span class="mcp-button-text">{{ testButtonText }}</span>
            </a-button>
            <a-tooltip
                v-if="testResult && isTextTruncated"
                :title="testResultText"
                placement="top"
            >
                <span
                    ref="testResultRef"
                    class="mcp-test-result"
                    :class="testResultClass"
                >
                  {{ testResultText }}
                </span>
            </a-tooltip>
            <span
                v-else-if="testResult"
                ref="testResultRef"
                class="mcp-test-result"
                :class="testResultClass"
            >
                {{ testResultText }}
              </span>
          </div>
        </div>
        <div class="right-actions">
          <button class="custom-btn cancel-btn" @click="triggerJsonImport">导入配置</button>
          <button class="custom-btn cancel-btn" @click="handleCancel">取消</button>
          <button class="custom-btn confirm-btn" @click="handleConfirm" :disabled="loading">
            {{ loading ? '添加中...' : '添加' }}
          </button>
        </div>
      </div>
      <!-- 隐藏的导入文件输入 -->
      <input
        type="file"
        ref="jsonInputRef"
        style="display: none;"
        accept="application/json,.json"
        @change="handleJsonImport"
      />
    </div>
  </a-modal>
</template>

<script setup lang="ts">
import {ref, watch, computed, nextTick} from 'vue';
import '@/assets/styles/user-group-select.css';
import NotificationService from '@/utils/NotificationService';
import type {ServerData} from './types';
import { testMcpServerConnection } from '@/services/mcpServer';
import { CloseOutlined } from '@ant-design/icons-vue';
import { listAiUserGroups, type UserGroupItem } from '@/services/aiPermission';

interface ServerFormData {
  name: string;
  description: string;
  type: string;
  url: string;
  timeout: number;
  visibility: 'private' | 'public';
  permissionGroupIds: string[];
}

interface Props {
  open: boolean;
  loading?: boolean;
}

interface Emits {
  (e: 'update:open', value: boolean): void;

  (e: 'confirm', data: ServerData): void;

  (e: 'cancel'): void;
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
});

const emit = defineEmits<Emits>();

const visible = ref(false);
const showNameError = ref(false);
const showUrlError = ref(false);
const showVisibilityError = ref(false);
const showPermissionGroupsError = ref(false);
const testLoading = ref(false);
const testResult = ref<'success' | 'error' | null>(null);
const testErrorMessage = ref('');
const testResultRef = ref<HTMLElement>();
const isTextTruncated = ref(false);
const headersList = ref<Array<{ key: string; value: string }>>([]);
const jsonInputRef = ref<HTMLInputElement | null>(null);
const permissionGroupLoading = ref(false);
const permissionGroupsLoaded = ref(false);
const availablePermissionGroups = ref<UserGroupItem[]>([]);
const permissionGroupDraftIds = ref<string[]>([]);
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
const canEditVisibility = computed(() => isCurrentUserAdmin.value);
const permissionGroupOptions = computed(() =>
  availablePermissionGroups.value.map((group) => ({
    label: group.name,
    value: group.uuid
  }))
);
const normalizePermissionGroupSelectionValues = (values: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(values) ? values : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

const formData = ref<ServerFormData>({
  name: '',
  description: '',
  type: 'sse',
  url: '',
  timeout: 60,
  visibility: 'private',
  permissionGroupIds: []
});

// 计算属性
const testResultClass = computed(() => {
  if (testResult.value === 'success') return 'test-success';
  if (testResult.value === 'error') return 'test-error';
  return '';
});

const testResultText = computed(() => {
  if (testResult.value === 'success') return '连接成功';
  if (testResult.value === 'error') return testErrorMessage.value || '连接失败';
  return '';
});

const testButtonText = computed(() => {
  if (testLoading.value) return '连接中...';
  if (testResult.value === 'success') return '重新测试';
  if (testResult.value === 'error') return '重试连接';
  return '测试连接';
});

// 监听器
watch(() => props.open, (newVal) => {
  visible.value = newVal;
  if (newVal) {
    resetForm();
    if (canEditVisibility.value) {
      ensurePermissionGroupsLoaded();
    }
  }
});

watch(visible, (newVal) => {
  emit('update:open', newVal);
});

watch(() => formData.value.url, () => {
  testResult.value = null;
  testErrorMessage.value = '';
});

watch(() => formData.value.visibility, (newVisibility) => {
  if (newVisibility) {
    showVisibilityError.value = false;
  }
  if (newVisibility === 'public' && canEditVisibility.value) {
    permissionGroupDraftIds.value = normalizePermissionGroupSelectionValues(formData.value.permissionGroupIds);
    ensurePermissionGroupsLoaded();
  }
});

watch(testResultText, async () => {
  if (testResult.value) {
    await nextTick();
    checkTextTruncation();
  }
});

// 方法
const checkTextTruncation = () => {
  if (testResultRef.value) {
    isTextTruncated.value = testResultRef.value.scrollHeight > testResultRef.value.clientHeight;
  }
};

const ensurePermissionGroupsLoaded = async () => {
  if (!canEditVisibility.value || permissionGroupsLoaded.value || permissionGroupLoading.value) return;
  permissionGroupLoading.value = true;
  try {
    availablePermissionGroups.value = await listAiUserGroups();
    permissionGroupsLoaded.value = true;
  } catch {
    availablePermissionGroups.value = [];
  } finally {
    permissionGroupLoading.value = false;
  }
};

const resetForm = () => {
  formData.value = {
    name: '',
    description: '',
    type: 'sse',
    url: '',
    timeout: 60,
    visibility: 'private',
    permissionGroupIds: []
  };
  permissionGroupDraftIds.value = [];
  headersList.value = [];
  if (jsonInputRef.value) jsonInputRef.value.value = '';
  showNameError.value = false;
  showUrlError.value = false;
  showVisibilityError.value = false;
  showPermissionGroupsError.value = false;
  testResult.value = null;
  testErrorMessage.value = '';
};

const validateForm = () => {
  showNameError.value = !formData.value.name.trim();
  showUrlError.value = !formData.value.url.trim();
  showVisibilityError.value = !formData.value.visibility;
  showPermissionGroupsError.value = canEditVisibility.value
    && formData.value.visibility === 'public'
    && formData.value.permissionGroupIds.length === 0;
  return !showNameError.value
    && !showUrlError.value
    && !showVisibilityError.value
    && !showPermissionGroupsError.value;
};

const updateVisibility = (visibility: ServerFormData['visibility']) => {
  if (!canEditVisibility.value) return;
  if (formData.value.visibility === 'public') {
    permissionGroupDraftIds.value = normalizePermissionGroupSelectionValues(formData.value.permissionGroupIds);
  }
  formData.value.visibility = visibility;
  if (visibility !== 'public') {
    formData.value.permissionGroupIds = [];
    showPermissionGroupsError.value = false;
  } else {
    formData.value.permissionGroupIds = normalizePermissionGroupSelectionValues(permissionGroupDraftIds.value);
    ensurePermissionGroupsLoaded();
  }
  showVisibilityError.value = false;
};

const handlePermissionGroupsChange = (values: string[]) => {
  formData.value.permissionGroupIds = normalizePermissionGroupSelectionValues(values);
  permissionGroupDraftIds.value = formData.value.permissionGroupIds.slice();
  showPermissionGroupsError.value = false;
};

const handleConfirm = () => {
  const isValid = validateForm();

  if (!isValid) {
    return;
  }

  if (testResult.value !== 'success') {
    NotificationService.info('建议先测试连接确保服务器可用');
    return;
  }

  const headersArr = headersList.value.filter(h => h.key.trim() && h.value.trim());
  const permissionGroupIds = Array.from(
    new Set(
      (formData.value.permissionGroupIds || []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

  const payload: ServerData = {
    id: undefined,
    name: formData.value.name,
    description: formData.value.description,
    type: formData.value.type,
    url: formData.value.url,
    timeout: formData.value.timeout,
    visibility: canEditVisibility.value ? formData.value.visibility : 'private',
    permissionGroupIds: canEditVisibility.value && formData.value.visibility === 'public' ? permissionGroupIds : [],
    headers: headersArr,
    tools: []
  };
  emit('confirm', payload);
};

const isValidUrl = (url: string): boolean => {
  try {
    const urlObj = new URL(url);
    return urlObj.protocol === 'http:' || urlObj.protocol === 'https:';
  } catch {
    return false;
  }
};

const handleTestConnection = async () => {
  const url = formData.value.url.trim();

  if (!url) {
    NotificationService.info('请先输入服务器URL');
    return;
  }

  if (!isValidUrl(url)) {
    testResult.value = 'error';
    testErrorMessage.value = '请输入有效的URL地址';
    NotificationService.error(testErrorMessage.value);
    return;
  }

  testLoading.value = true;
  testResult.value = null;
  testErrorMessage.value = '';

  try {
    const headersObj: Record<string, string> = {};
    headersList.value.forEach(h => {
      if (h.key.trim()) headersObj[h.key.trim()] = h.value;
    });

    const payload = {
      server_name: formData.value.name || '未命名服务器',
      url: url,
      type: formData.value.type === 'streamableHttp' ? 'streamable_http' : 'sse',
      headers: headersObj
    };

    await testMcpServerConnection(payload);
    
    // 假设后端成功时返回特定的 code 或状态，这里按常见情况处理，如果是通过抛错判断则不需要特殊处理 code
    // 如果后端成功返回（没有抛出 4xx/5xx 错误或业务错误）
    testResult.value = 'success';
    testErrorMessage.value = '连接成功';
    NotificationService.success('MCP服务器连接成功');

    await nextTick();
    checkTextTruncation();
  } catch (error: any) {
    testResult.value = 'error';
    
    // 如果后端返回了具体的错误信息，优先使用
    const errorMsg = error?.response?.data?.message || error.message || '连接失败，请确认这是一个有效的MCP服务器';
    testErrorMessage.value = errorMsg;

    NotificationService.error(`连接失败: ${testErrorMessage.value}`);

    await nextTick();
    checkTextTruncation();
  } finally {
    testLoading.value = false;
  }
};

const addHeader = () => {
  headersList.value.push({ key: '', value: '' });
};

const removeHeader = (index: number) => {
  headersList.value.splice(index, 1);
};

const handleCancel = () => {
  visible.value = false;
  emit('cancel');
};

// 导入/导出JSON
const triggerJsonImport = () => {
  jsonInputRef.value?.click();
};

const handleJsonImport = async (e: Event) => {
  try {
    const input = e.target as HTMLInputElement;
    const file = input.files && input.files[0];
    if (!file) return;

    const text = await file.text();
    const parsed = JSON.parse(text);

    // 基础类型判断：若看起来是模型服务配置，则阻止在MCP模态导入
    const isModelServiceJson = !!parsed.provider
      || !!(parsed.config && (parsed.config.apiUrl || parsed.config.models || parsed.config.apiKey))
      || parsed.type === 'OpenAI'
      || Array.isArray(parsed.models);
    if (isModelServiceJson) {
      NotificationService.error('检测到模型服务配置，请在“模型服务”页面导入该JSON');
      return;
    }

    const rawConfig = parsed.config || parsed.server || parsed;
    const normalizeImportedVisibility = (source: any): 'private' | 'public' => {
      const candidate = String(
        source?.visibility
        || source?.permissionCode
        || source?.permission_code
        || ''
      ).trim().toLowerCase();
      return canEditVisibility.value && candidate === 'public' ? 'public' : 'private';
    };
    const normalizeImportedPermissionGroupIds = (...sources: any[]): string[] =>
      Array.from(
        new Set(
          sources.flatMap((source) => {
            const candidates: unknown[] = Array.isArray(source?.permissionGroupIds)
              ? source.permissionGroupIds
              : Array.isArray(source?.permission_group_ids)
                ? source.permission_group_ids
                : [];
            return candidates.filter(
              (groupId: unknown): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
            );
          })
        )
      );

    formData.value.name = rawConfig.name || formData.value.name || '';
    formData.value.description = rawConfig.description ?? formData.value.description ?? '';
    formData.value.type = rawConfig.type || formData.value.type || 'sse';
    formData.value.url = rawConfig.url || formData.value.url || '';
    formData.value.timeout = typeof rawConfig.timeout === 'number' ? rawConfig.timeout : (formData.value.timeout ?? 60);
    formData.value.visibility = normalizeImportedVisibility(rawConfig) === 'public'
      ? 'public'
      : normalizeImportedVisibility(parsed);
    formData.value.permissionGroupIds = canEditVisibility.value
      ? normalizeImportedPermissionGroupIds(rawConfig, parsed, parsed.config, parsed.server)
      : [];

    // 规范化headers并填充到文本域，支持顶层与嵌套（server/config）两种位置
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

    headersList.value = headersArr;
    // 必填项检查与提示
    const missing: string[] = [];
    if (!formData.value.name.trim()) missing.push('name');
    if (!formData.value.url.trim()) missing.push('url');
    if (!rawConfig.type) missing.push('type');
    if (missing.length) {
      NotificationService.warning(`JSON缺少必要字段：${missing.join(', ')}，请手动补充后再测试连接`);
    } else {
      NotificationService.success('配置已导入到表单');
    }
  } catch (err) {
    console.error('[AddServerModal] 导入配置失败:', err);
    NotificationService.error('导入配置失败，请检查文件结构');
  } finally {
    const input = e.target as HTMLInputElement;
    if (input) input.value = '';
  }
};

// 移除导出功能，模态仅保留导入
</script>

<style scoped>
.server-form {
  padding: 8px;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  margin-bottom: 8px;
  font-weight: 500;
  font-size: 14px;
}

.form-label.required::before {
  content: '*';
  color: #ff4d4f;
  margin-right: 4px;
}

.visibility-form-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.form-error {
  color: #ff4d4f;
  font-size: 12px;
  margin-top: 4px;
}

.form-help {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: 4px;
}

.bi-visibility-segment {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  flex-shrink: 0;
  position: relative;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 10px;
  background: #f5f5f5;
  isolation: isolate;
  overflow: hidden;
}

.bi-visibility-segment::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: calc(50% - 3px);
  height: calc(100% - 4px);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08), 0 6px 18px rgba(15, 23, 42, 0.06);
  transform: translateX(0);
  transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.28s ease, background 0.28s ease;
  z-index: 0;
}

.bi-visibility-segment[data-active='public']::before {
  transform: translateX(calc(100% + 2px));
}

.bi-visibility-segment.is-readonly {
  background: linear-gradient(135deg, #f4f6fb 0%, #eef2f8 100%);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.24);
}

.bi-visibility-segment.is-readonly::before {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(243, 246, 251, 0.9));
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 4px 12px rgba(15, 23, 42, 0.05);
}

.bi-visibility-segment.is-readonly::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 10px;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(148, 163, 184, 0.12));
  z-index: 2;
}

.bi-visibility-segment-option {
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #111827;
  font-size: 12px;
  font-weight: 500;
  line-height: 28px;
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), color 0.2s ease, opacity 0.2s ease;
}

.bi-visibility-segment-option:hover {
  color: #111827;
  transform: translateY(-0.5px);
}

.bi-visibility-segment-option.active {
  color: #111827;
  transform: translateY(-0.5px) scale(0.985);
}

.bi-visibility-segment-option:not(.active) {
  opacity: 0.82;
}

.bi-visibility-segment-option:active {
  transform: scale(0.97);
}

.bi-visibility-segment-option:disabled {
  cursor: not-allowed;
  color: #64748b;
  opacity: 0.82;
  transform: none;
}

.bi-visibility-segment.is-readonly .bi-visibility-segment-option.active {
  color: #334155;
  font-weight: 600;
  transform: none;
}

.bi-visibility-segment.is-readonly .bi-visibility-segment-option:not(.active) {
  color: #94a3b8;
  opacity: 1;
}

.bi-visibility-segment.is-readonly .bi-visibility-segment-option:hover {
  transform: none;
}

.headers-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.header-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-input {
  flex: 1;
}

.header-key {
  flex: 1;
}

.header-value {
  flex: 1.5;
}

.header-remove-btn {
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #999;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.header-remove-btn:hover {
  background: #fff1f0;
  color: #ff4d4f;
}

.header-remove-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.header-add-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 32px;
  border: 1px dashed #d9d9d9;
  background: #fafafa;
  color: #666;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.header-add-btn:hover {
  border-color: #1677ff;
  color: #1677ff;
  background: #f0f5ff;
}

.header-add-icon {
  font-size: 16px;
  line-height: 1;
}

.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  margin-bottom: -10px;
}

.left-actions {
  display: flex;
  align-items: center;
}

.test-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mcp-test-section {
  display: flex;
  align-items: center;
  gap: 12px;
}

.right-actions {
  display: flex;
  align-items: center;
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
}

.confirm-btn {
  background: #1677ff;
  color: #ffffff;
  border: none;
}

.confirm-btn:hover {
  background-color: #4096ff;
}

.confirm-btn:disabled {
  background-color: #d9d9d9;
  color: rgba(0, 0, 0, 0.25);
  cursor: not-allowed;
}

.test-button {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 6px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  overflow: hidden;
  background: linear-gradient(90deg, #f0f8ff 25%, #e6f4ff 50%, #f0f8ff 75%);
  background-size: 200% 100%;
  border: 1px solid rgba(24, 144, 255, 0.2);
  box-shadow: 0 2px 4px rgba(24, 144, 255, 0.08);
  animation: skeleton-shimmer 2s ease-in-out infinite;
}

.mcp-test-button::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.4), transparent);
  transition: left 0.6s ease-out;
}

.mcp-test-button {
  position: relative;
  overflow: hidden;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
  font-size: 14px;
  padding: 6px 16px;
  border-radius: 10px;
  background-color: #f5f5f5c7;
  border: none;
  display: flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.mcp-test-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.18), 0 2px 6px rgba(24, 144, 255, 0.12);
  border-color: rgba(24, 144, 255, 0.4);
  animation-play-state: paused;
}

.mcp-test-button:hover::before {
  left: 100%;
}

.mcp-test-button:active {
  transform: translateY(0);
}

.mcp-test-button.mcp-test-success {
  background: linear-gradient(135deg, #52c41a, #73d13d);
  border-color: #52c41a;
  color: white;
  box-shadow: 0 2px 8px rgba(82, 196, 26, 0.3);
}

.mcp-test-button.mcp-test-error {
  background: linear-gradient(135deg, #ff4d4f, #ff7875);
  border-color: #ff4d4f;
  color: white;
  box-shadow: 0 2px 8px rgba(255, 77, 79, 0.3);
}

.mcp-test-icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
}

.mcp-test-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.mcp-skeleton-dot {
  width: 8px;
  height: 8px;
  background: linear-gradient(90deg, #1890ff, #40a9ff, #1890ff);
  background-size: 200% 100%;
  border-radius: 50%;
  animation: skeleton-shimmer 2s ease-in-out infinite;
}

.mcp-success-icon, .mcp-error-icon {
  animation: iconPop 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
}

.mcp-loading-spinner {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.mcp-spinner-ring {
  width: 14px;
  height: 14px;
  border: 2px solid transparent;
  border-top: 2px solid #1890ff;
  border-radius: 50%;
}

.mcp-button-text {
  font-weight: 500;
  transition: all 0.3s;
  color: #1890ff;
}

.mcp-test-button:hover .mcp-button-text {
  color: #096dd9;
}

.mcp-test-button.mcp-test-success .mcp-button-text,
.mcp-test-button.mcp-test-error .mcp-button-text {
  color: white;
}

.mcp-test-result {
  font-size: 12px;
  font-weight: 500;
  transition: all 0.3s;
  max-width: 100px;
  display: -webkit-box;
  line-clamp: 2;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
  word-break: break-word;
  cursor: help;
}

.mcp-test-result.test-success {
  color: #52c41a;
}

.mcp-test-result.test-error {
  color: #ff4d4f;
}

/* 动画定义 */
@keyframes skeleton-shimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

@keyframes iconPop {
  0% {
    transform: scale(0);
    opacity: 0;
  }
  50% {
    transform: scale(1.2);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

@media (max-width: 480px) {
  .mcp-test-section {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .mcp-test-result {
    font-size: 11px;
  }

  .right-actions {
    gap: 8px;
  }

  .right-actions .custom-btn {
    font-size: 13px;
    padding: 0 12px;
  }
}
</style>

<style>
.add-mcp-server-modal .ant-modal-content {
  border-radius: 25px;
}
</style>
