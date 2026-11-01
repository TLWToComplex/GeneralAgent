<template>
  <div class="server-config-section">
    <div class="section-title required">名称</div>
    <div class="server-name-container">
      <a-input v-model:value="formData.name" placeholder="请输入服务器名称" :disabled="isFormReadonly" />
    </div>
    
    <div class="section-title">描述</div>
    <div class="server-description-container">
      <a-textarea
          v-model:value="formData.description"
          placeholder="请输入服务器描述"
          :auto-size="{ minRows:3, maxRows:3 }"
          :disabled="isFormReadonly"
      />
    </div>

    <div class="server-visibility-container">
      <div class="section-title required inline-title">可见范围</div>
      <div
        class="bi-visibility-segment"
        :class="{ 'is-readonly': !canEditVisibility || isFormReadonly }"
        :data-active="formData.visibility"
        role="tablist"
        aria-label="可见范围"
      >
        <button
          type="button"
          class="bi-visibility-segment-option"
          :class="{ active: formData.visibility === 'private' }"
          :aria-pressed="formData.visibility === 'private'"
          :disabled="!canEditVisibility || isFormReadonly"
          @click="updateVisibility('private')"
        >
          个人使用
        </button>
        <button
          type="button"
          class="bi-visibility-segment-option"
          :class="{ active: formData.visibility === 'public' }"
          :aria-pressed="formData.visibility === 'public'"
          :disabled="!canEditVisibility || isFormReadonly"
          @click="updateVisibility('public')"
        >
          公开共享
        </button>
      </div>
    </div>

    <div v-if="canEditVisibility && formData.visibility === 'public'">
      <div class="section-title required">可访问用户组</div>
      <div class="server-permission-groups-container">
        <a-select
          v-model:value="formData.permissionGroupIds"
          mode="multiple"
          :options="permissionGroupOptions"
          :loading="permissionGroupsLoading"
          :disabled="permissionGroupsLoading"
          :virtual="false"
          popupClassName="user-group-select-dropdown"
          max-tag-count="responsive"
          placeholder="请选择用户组"
          style="width: 100%"
          @change="handlePermissionGroupsChange"
        />
        <div class="field-help">公开后仅这些用户组可访问该 MCP 服务器</div>
      </div>
    </div>
    
    <div class="section-title required">类型</div>
    <div class="server-type-container">
      <a-select v-model:value="formData.type" style="width: 100%" :disabled="isFormReadonly">
        <a-select-option value="sse">服务器发送事件 (SSE)</a-select-option>
        <a-select-option value="streamableHttp">可流式传输的HTTP</a-select-option>
      </a-select>
    </div>
    
    <div class="section-title required">URL</div>
    <div class="server-url-container">
      <a-input v-model:value="formData.url" placeholder="请输入服务器URL" :disabled="isFormReadonly" />
    </div>
    
    <div class="section-title">请求头</div>
    <div class="server-headers-container">
      <a-textarea 
        v-model:value="headersInput" 
        placeholder="请输入请求头，格式为：'名称: 值'"
        :auto-size="{ minRows: 3, maxRows: 3 }"
        :disabled="isFormReadonly"
      />
    </div>
    
    <div class="section-title">超时（秒）</div>
    <div class="server-timeout-container">
      <a-input-number v-model:value="formData.timeout" :min="1" :max="300" :step="1" style="width: 100%" :disabled="isFormReadonly" />
    </div>
    <div v-if="isFormReadonly" class="field-help readonly-help">公开共享的 MCP 服务器仅 admin 可编辑或删除</div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import '@/assets/styles/user-group-select.css';
import type { ServerData } from './types';
import { listAiUserGroups, type UserGroupItem } from '@/services/aiPermission';

interface Props {
  modelValue: ServerData;
  readonly?: boolean;
}

interface Emits {
  (e: 'update:modelValue', value: ServerData): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const permissionGroupsLoading = ref(false);
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
const isFormReadonly = computed(() => !!props.readonly);
const normalizePermissionGroupSelectionValues = (values: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(values) ? values : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

const formData = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
});

const ensurePermissionGroupsLoaded = async () => {
  if (!canEditVisibility.value || permissionGroupsLoaded.value || permissionGroupsLoading.value) return;
  permissionGroupsLoading.value = true;
  try {
    availablePermissionGroups.value = await listAiUserGroups();
    permissionGroupsLoaded.value = true;
  } catch {
    availablePermissionGroups.value = [];
  } finally {
    permissionGroupsLoading.value = false;
  }
};

const updateVisibility = (visibility: ServerData['visibility']) => {
  if (!canEditVisibility.value || isFormReadonly.value) return;
  if (formData.value.visibility === 'public') {
    permissionGroupDraftIds.value = normalizePermissionGroupSelectionValues(formData.value.permissionGroupIds);
  }
  formData.value.visibility = visibility;
  if (visibility !== 'public') {
    formData.value.permissionGroupIds = [];
  } else {
    formData.value.permissionGroupIds = normalizePermissionGroupSelectionValues(permissionGroupDraftIds.value);
    ensurePermissionGroupsLoaded();
  }
};

const handlePermissionGroupsChange = (values: string[]) => {
  formData.value.permissionGroupIds = normalizePermissionGroupSelectionValues(values);
  permissionGroupDraftIds.value = formData.value.permissionGroupIds.slice();
};

watch(
  () => formData.value.id,
  () => {
    permissionGroupDraftIds.value = formData.value.visibility === 'public'
      ? normalizePermissionGroupSelectionValues(formData.value.permissionGroupIds)
      : [];
  },
  { immediate: true }
);

watch(
  () => [formData.value.visibility, JSON.stringify(formData.value.permissionGroupIds)] as const,
  ([newVisibility]) => {
    if (newVisibility === 'public' && canEditVisibility.value) {
      permissionGroupDraftIds.value = normalizePermissionGroupSelectionValues(formData.value.permissionGroupIds);
      ensurePermissionGroupsLoaded();
    }
  },
  { immediate: true }
);

// 绑定请求头输入到 headers 数组
const headersInput = computed<string>({
  get: () => {
    const list = Array.isArray(formData.value.headers)
      ? formData.value.headers
      : (formData.value.headers && typeof formData.value.headers === 'object'
        ? Object.entries(formData.value.headers as Record<string, unknown>)
          .filter(([key, value]) => key.trim().length > 0 && typeof value === 'string')
          .map(([key, value]) => ({ key: key.trim(), value: value as string }))
        : []);
    return list.map(h => `${h.key}: ${h.value}`).join('\n');
  },
  set: (text: string) => {
    const lines = (text || '').split(/\r?\n/);
    const headers: Array<{ key: string; value: string }> = [];
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const sepIndex = trimmed.indexOf('=') >= 0 ? trimmed.indexOf('=') : trimmed.indexOf(':');
      if (sepIndex <= 0) continue;
      const key = trimmed.substring(0, sepIndex).trim();
      const value = trimmed.substring(sepIndex + 1).trim();
      if (key && value) headers.push({ key, value });
    }
    formData.value.headers = headers;
  }
});

</script>

<style scoped>
.section-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 8px;
  margin-top: 16px;
}

.section-title.required::before {
  content: '*';
  color: #ff4d4f;
  margin-right: 4px;
}

.server-name-container,
.server-description-container,
.server-permission-groups-container,
.server-type-container,
.server-url-container,
.server-headers-container,
.server-timeout-container {
  margin-bottom: 16px;
}

.server-visibility-container {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.inline-title {
  margin: 0;
  flex: 0 0 auto;
}

.field-help {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: 4px;
}

.bi-visibility-segment {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  flex-shrink: 0;
  margin-left: auto;
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

@media (max-width: 640px) {
  .server-visibility-container {
    align-items: flex-start;
    flex-direction: column;
  }

  .bi-visibility-segment {
    margin-left: 0;
  }
}
</style>
