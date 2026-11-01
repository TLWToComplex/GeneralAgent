<template>
  <div class="config-section basic-info-section">
    <div class="agent-model-section-header basic-info-header">
      <h3>智能体信息</h3>
      <p>配置智能体的基本信息</p>
    </div>
    <a-form :model="basicConfig" layout="vertical" class="form-content basic-info-form">
      <a-form-item class="bi-avatar-form-item">
        <section class="avatar-studio" aria-label="智能体头像" :aria-busy="isUploading">
          <div class="avatar-studio-body">
            <div class="avatar-studio-preview" aria-label="当前头像预览">
              <div class="avatar-studio-current-wrap">
                <div class="avatar-studio-current" :style="{ backgroundColor: basicConfig.avatar ? 'transparent' : (basicConfig.themeColor || '#5275db') }">
                  <img v-if="basicConfig.avatar" :src="basicConfig.avatar" alt="当前智能体头像" />
                  <span v-else>{{ basicConfig.icon || basicConfig.name?.charAt(0) || 'A' }}</span>
                </div>
                <a-dropdown :trigger="['click']" placement="bottomRight" overlayClassName="avatar-studio-dropdown" :disabled="isFormReadonly || isUploading">
                  <button type="button" class="avatar-studio-edit" :aria-label="isUploading ? '头像上传中' : '编辑头像'" :disabled="isFormReadonly || isUploading">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 20h9" /><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z" /></svg>
                  </button>
                  <template #overlay>
                    <a-menu class="avatar-studio-menu">
                      <a-menu-item key="upload" :disabled="isUploading" @click="triggerFileInput">上传图片</a-menu-item>
                      <a-menu-item key="reset" :disabled="isUploading" @click="resetAvatar">重置头像</a-menu-item>
                    </a-menu>
                  </template>
                </a-dropdown>
              </div>
              <span class="avatar-studio-preview-label">{{ isUploading ? '上传中' : '当前头像' }}</span>
            </div>
            <div class="avatar-studio-picker">
              <div class="avatar-studio-tabs" role="group" aria-label="头像风格">
                <button v-for="style in avatarStyles" :key="style.value" type="button" :class="{ active: avatarStyle === style.value }" :aria-pressed="avatarStyle === style.value" @click="changeAvatarStyle(style.value)">{{ style.label }}</button>
              </div>
              <div v-if="avatarStyle === 'text'" class="avatar-studio-colors" role="group" aria-label="选择文字头像背景色">
                <button v-for="color in visibleAvatarColors" :key="color" type="button" class="avatar-studio-color" :class="{ selected: isTextColorActive(color) }" :style="{ '--swatch': color }" :disabled="isFormReadonly || isUploading" :aria-label="'文字头像背景色 ' + color" :aria-pressed="isTextColorActive(color)" @click="selectTextColor(color)">
                  <span v-if="isTextColorActive(color)" class="avatar-studio-color-check" aria-hidden="true"><svg width="14" height="14" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="m2 6 2.5 2.5L10 3" /></svg></span>
                </button>
                <button type="button" class="avatar-studio-more" aria-label="换一组颜色" @click="refreshAvatarPresets">More</button>
              </div>
              <div v-else class="avatar-studio-presets" role="group" aria-label="选择头像">
                <button v-for="preset in visibleAvatarPresets" :key="preset.image" type="button" class="avatar-studio-preset" :class="{ selected: basicConfig.avatar === preset.image }" :disabled="isFormReadonly || isUploading" :aria-label="preset.label" :aria-pressed="basicConfig.avatar === preset.image" @click="selectPreset(preset)">
                  <img :src="preset.image" alt="" />
                  <span v-if="basicConfig.avatar === preset.image" class="avatar-studio-check" aria-hidden="true"><svg width="9" height="9" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.2"><path d="m2 6 2.5 2.5L10 3" /></svg></span>
                </button>
                <button type="button" class="avatar-studio-more" aria-label="换一组头像" @click="refreshAvatarPresets">More</button>
              </div>
            </div>
          </div>
          <input type="file" ref="fileInputRef" hidden accept="image/*" @change="handleFileUpload" />
        </section>
      </a-form-item>

      <a-form-item label="智能体名称" :validate-status="errors.name ? 'error' : undefined" :help="errors.name ? '请输入智能体名称' : undefined" required>
        <a-input v-model:value="basicConfig.name" :disabled="isFormReadonly" placeholder="例如：产品经理、前端工程师、产品运营等" style="border-radius: 8px !important;"/>
      </a-form-item>

      <a-form-item label="智能体描述" :validate-status="errors.description ? 'error' : undefined" :help="errors.description ? '请输入智能体描述' : undefined" required>
        <a-input v-model:value="basicConfig.description" :disabled="isFormReadonly" placeholder="请输入智能体描述信息" style="border-radius: 8px !important;"/>
      </a-form-item>

      <transition name="bi-visibility-fade" appear>
        <a-form-item
          required
          class="bi-visibility-form-item"
          :validate-status="errors.visibility ? 'error' : undefined"
          :help="errors.visibility ? '请选择可见范围' : undefined"
        >
          <div class="bi-visibility-row">
            <div class="ant-form-item-label bi-visibility-inline-label">
              <label class="ant-form-item-required" title="可见范围">可见范围</label>
            </div>
            <div
              class="bi-visibility-segment"
              :class="{ 'is-readonly': !canEditVisibility }"
              :data-active="basicConfig.visibility"
              role="tablist"
              aria-label="可见范围"
            >
              <button
                type="button"
                class="bi-visibility-segment-option"
                :class="{ active: basicConfig.visibility === 'private' }"
                :aria-pressed="basicConfig.visibility === 'private'"
                :disabled="!canEditVisibility || isFormReadonly"
                @click="updateVisibility('private')"
              >
                个人使用
              </button>
              <button
                type="button"
                class="bi-visibility-segment-option"
                :class="{ active: basicConfig.visibility === 'public' }"
                :aria-pressed="basicConfig.visibility === 'public'"
                :disabled="!canEditVisibility || isFormReadonly"
                @click="updateVisibility('public')"
              >
                公开共享
              </button>
            </div>
          </div>
        </a-form-item>
      </transition>

      <a-form-item
        v-if="canEditVisibility && basicConfig.visibility === 'public'"
        required
        class="bi-permission-groups-form-item"
        label="可访问用户组"
        :validate-status="errors.permissionGroups ? 'error' : undefined"
        :help="errors.permissionGroups ? '请选择至少一个用户组' : '公开后仅这些用户组可访问该智能体'"
      >
        <a-select
          mode="multiple"
          :value="permissionGroups"
          :options="permissionGroupOptions"
          :loading="permissionGroupLoading"
          :disabled="permissionGroupLoading || isFormReadonly"
          :virtual="false"
          popupClassName="user-group-select-dropdown"
          max-tag-count="responsive"
          placeholder="请选择用户组"
          style="width: 100%;"
          @change="handlePermissionGroupsChange"
        />
      </a-form-item>

      <a-form-item label="智能体类型" :validate-status="errors.type ? 'error' : undefined" :help="errors.type ? '请选择智能体类型' : undefined" required>
        <div class="bi-type-selection">
          <div
            v-for="option in typeOptions"
            :key="option.value"
            class="bi-type-card"
            :class="[option.cardClass, { active: basicConfig.type === option.value }]"
            @click="selectType(option.value)"
          >
            <div class="bi-card-glow"></div>
            <div class="bi-card-top">
              <div class="bi-card-icon-wrapper" :class="option.iconClass">
                <svg v-if="option.value === 'assistant'" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"></path>
                </svg>
                <svg v-else-if="option.value === 'deepagent'" xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M12 3l2.2 4.8L19 10l-4.8 2.2L12 17l-2.2-4.8L5 10l4.8-2.2L12 3z"></path>
                  <path d="M19 15l.9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15z"></path>
                </svg>
                <svg v-else xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="18" cy="18" r="3"></circle>
                  <circle cx="6" cy="6" r="3"></circle>
                  <path d="M6 21V9a9 9 0 0 0 9 9"></path>
                </svg>
              </div>
              <div class="bi-selection-indicator"></div>
            </div>
            <div class="bi-card-info">
              <div class="bi-card-title">{{ option.title }}</div>
              <div class="bi-card-desc">{{ option.description }}</div>
            </div>
          </div>
        </div>
      </a-form-item>

    </a-form>
  </div>
</template>

<script setup lang="ts">
import {computed, ref, watch} from 'vue';
import {Modal} from 'ant-design-vue';
import '@/assets/styles/user-group-select.css';
import {ImageCompressor} from '@/utils/ImageCompressor';
import NotificationService from '@/utils/NotificationService';
import { avatarFiles } from '@/utils/agentAvatar';
import defaultAgentAvatar from '@/assets/image/png/angent-bg.png';
import type {BasicConfig, FormErrors} from './AddAgentModal.vue';

 

// 定义组件属性
interface Props {
  basicConfig: BasicConfig;
  errors: FormErrors;
  editMode: boolean;
  canEditVisibility?: boolean;
  readonly?: boolean;
  agentData?: any;
  permissionGroupOptions?: Array<{ label: string; value: string }>;
  permissionGroups?: string[];
  permissionGroupLoading?: boolean;
}

// 定义组件事件
interface Emits {
  (e: 'update:basicConfig', value: BasicConfig): void;
  (e: 'update:errors', value: Partial<FormErrors>): void;
  (e: 'update:permission-groups', value: string[]): void;
  (e: 'delete', agentId: string): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const canEditVisibility = computed(() => !!props.canEditVisibility);
const isFormReadonly = computed(() => !!props.readonly);
const permissionGroupOptions = computed(() => props.permissionGroupOptions || []);
const permissionGroups = computed(() => props.permissionGroups || []);
const permissionGroupLoading = computed(() => !!props.permissionGroupLoading);
const permissionGroupDraftIds = ref<string[]>([]);
const typeOptions = [
  {
    value: 'assistant',
    title: '通用智能体',
    description: '适合日常对话、知识问答与常规工具调用。',
    iconClass: 'bi-assistant-bg',
    cardClass: 'bi-assistant-card'
  },
  {
    value: 'deepagent',
    title: 'DeepAgent',
    description: '更强调深度推理与多步分析，适合复杂问题拆解。',
    iconClass: 'bi-deepagent-bg',
    cardClass: 'bi-deepagent-card'
  },
  {
    value: 'orchestrator',
    title: '内置编排式智能体',
    description: '通过工作流编排处理复杂任务，适合服务协同。',
    iconClass: 'bi-orchestrator-bg',
    cardClass: 'bi-orchestrator-card'
  }
] as const;

const avatarStyles = [
  { value: 'text', label: '文字' },
  { value: 'industry', label: '行业' },
  { value: 'pixel', label: '像素' }, { value: 'linear', label: '线性' },
  { value: 'adventure', label: '冒险家' }, { value: 'lorelei', label: '洛蕾莱' },
] as const;
type AvatarStyle = typeof avatarStyles[number]['value'];
type AvatarPreset = { image: string; label: string };
// 文字头像可选背景色
const avatarTextColors = [
  '#3b82f6', '#6366f1', '#8b5cf6', '#ec4899',
  '#ef4444', '#f97316', '#f59e0b', '#10b981',
  '#14b8a6', '#06b6d4', '#0ea5e9', '#64748b',
] as const;
const avatarStyle = ref<AvatarStyle>('text');
const avatarOffset = ref(0);
const isUploading = ref(false);
const avatarPageSize = 5;
const avatarColorPageSize = 6;
const avatarCollections = Object.fromEntries(avatarStyles.map(style => {
  const entries = Object.entries(avatarFiles).filter(([file]) => file.includes('/' + style.value + '/'));
  // Interleave the supplied colors so each batch has varied expressions and colors.
  entries.sort(([a], [b]) => {
    const aName = a.split('/').pop()!;
    const bName = b.split('/').pop()!;
    if (style.value === 'linear') {
      const numberDiff = Number(aName.match(/\d+/)?.[0]) - Number(bName.match(/\d+/)?.[0]);
      if (numberDiff) return numberDiff;
    }
    return aName.localeCompare(bName, 'zh-CN', { numeric: true });
  });
  return [style.value, entries.map(([, image], index) => ({ image, label: style.label + '头像 ' + (index + 1) }))];
})) as Record<AvatarStyle, AvatarPreset[]>;
const visibleAvatarPresets = computed(() => {
  const presets = avatarCollections[avatarStyle.value];
  return Array.from({ length: Math.min(avatarPageSize, presets.length) }, (_, index) =>
    presets[(avatarOffset.value + index) % presets.length]);
});
const visibleAvatarColors = computed(() =>
  Array.from({ length: Math.min(avatarColorPageSize, avatarTextColors.length) }, (_, index) =>
    avatarTextColors[(avatarOffset.value + index) % avatarTextColors.length]));
const changeAvatarStyle = (style: AvatarStyle) => {
  avatarStyle.value = style;
  avatarOffset.value = 0;
  // 切到「文字」时清空图片头像，回落到名称首字母
  if (style === 'text' && props.basicConfig.avatar) {
    const name = (props.basicConfig.name || '').trim();
    emit('update:basicConfig', {
      ...props.basicConfig,
      avatar: '',
      icon: name ? name.charAt(0).toUpperCase() : 'A',
    });
  }
};
const refreshAvatarPresets = () => {
  if (avatarStyle.value === 'text') {
    avatarOffset.value = (avatarOffset.value + avatarColorPageSize) % Math.max(1, avatarTextColors.length);
    return;
  }
  const count = avatarCollections[avatarStyle.value].length;
  avatarOffset.value = (avatarOffset.value + avatarPageSize) % Math.max(1, count);
};
const selectPreset = (preset: AvatarPreset) => {
  if (isFormReadonly.value || isUploading.value) return;
  emit('update:basicConfig', { ...props.basicConfig, avatar: preset.image });
};
// 当前文字头像背景色是否命中该色块
const isTextColorActive = (color: string) =>
  !props.basicConfig.avatar && (props.basicConfig.themeColor || '').toLowerCase() === color.toLowerCase();
// 选择文字头像背景色，同时清空图片头像
const selectTextColor = (color: string) => {
  if (isFormReadonly.value || isUploading.value) return;
  const name = (props.basicConfig.name || '').trim();
  emit('update:basicConfig', {
    ...props.basicConfig,
    avatar: '',
    themeColor: color,
    icon: name ? name.charAt(0).toUpperCase() : 'A',
  });
};
watch(() => props.basicConfig.avatar, avatar => {
  if (!avatar) { avatarStyle.value = 'text'; return; }
  for (const style of avatarStyles) {
    if (style.value === 'text') continue;
    const index = avatarCollections[style.value].findIndex(preset => preset.image === avatar);
    if (index !== -1) {
      avatarStyle.value = style.value;
      avatarOffset.value = Math.floor(index / avatarPageSize) * avatarPageSize;
      break;
    }
  }
}, { immediate: true });

// 文件输入引用
const fileInputRef = ref<HTMLInputElement | null>(null);
const normalizePermissionGroupIds = (groupIds: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(groupIds) ? groupIds : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

// 监听名称变化更新头像文字
watch(() => props.basicConfig.name, (newName) => {
  if (!props.basicConfig.avatar && newName) {
    emit('update:basicConfig', {
      ...props.basicConfig,
      icon: newName.charAt(0).toUpperCase()
    });
  } else if (!props.basicConfig.avatar && !newName) {
    // 当名称为空时，设置默认图标
    emit('update:basicConfig', {
      ...props.basicConfig,
      icon: 'A'
    });
  }
});

watch(() => props.basicConfig.type, () => {
  emit('update:errors', { type: false, visibility: false });
});

watch(() => props.basicConfig.visibility, (newVisibility) => {
  if (newVisibility) {
    emit('update:errors', { visibility: false });
  }
  if (newVisibility === 'public') {
    permissionGroupDraftIds.value = normalizePermissionGroupIds(permissionGroups.value);
  }
});

watch(
  permissionGroups,
  (newGroups) => {
    if (props.basicConfig.visibility === 'public') {
      permissionGroupDraftIds.value = normalizePermissionGroupIds(newGroups);
    }
  },
  { immediate: true }
);

const selectType = (type: BasicConfig['type']) => {
  if (isFormReadonly.value) return;
  emit('update:basicConfig', {
    ...props.basicConfig,
    type,
    visibility: props.basicConfig.visibility || 'private'
  });
};

const updateVisibility = (visibility: BasicConfig['visibility']) => {
  if (!canEditVisibility.value || isFormReadonly.value) return;
  if (props.basicConfig.visibility === 'public') {
    permissionGroupDraftIds.value = normalizePermissionGroupIds(permissionGroups.value);
  }
  emit('update:basicConfig', {
    ...props.basicConfig,
    visibility
  });
  emit('update:permission-groups', visibility === 'public'
    ? normalizePermissionGroupIds(permissionGroupDraftIds.value)
    : []);
  emit('update:errors', { visibility: false });
};

const handlePermissionGroupsChange = (values: string[]) => {
  if (isFormReadonly.value) return;
  const normalizedValues = normalizePermissionGroupIds(values);
  permissionGroupDraftIds.value = normalizedValues.slice();
  emit('update:permission-groups', normalizedValues);
  emit('update:errors', { permissionGroups: false });
};

// 触发文件上传
const triggerFileInput = () => {
  if (isFormReadonly.value) return;
  if (fileInputRef.value) {
    fileInputRef.value.click();
  }
};

// 重置为默认头像
const resetAvatar = () => {
  if (isFormReadonly.value || isUploading.value) return;
  avatarStyle.value = 'text';
  avatarOffset.value = 0;
  emit('update:basicConfig', { ...props.basicConfig, avatar: defaultAgentAvatar });
};

// 处理文件上传
const handleFileUpload = async (event: Event) => {
  if (isFormReadonly.value) return;
  const target = event.target as HTMLInputElement;
  if (!isUploading.value && target.files && target.files.length > 0) {
    const file = target.files[0];
    isUploading.value = true;
    
    try {
      // 使用ImageCompressor压缩图片
      const compressedDataUrl = await ImageCompressor.compress(file, {
        maxSize: 1024,
        quality: 0.7,
        smallFileThreshold: 100 * 1024 // 100KB
      });
      
      // 更新头像
      emit('update:basicConfig', {
        ...props.basicConfig,
        avatar: compressedDataUrl
      });
    } catch (error) {
      NotificationService.error(error instanceof Error ? error.message : '图片上传失败');
    } finally {
      isUploading.value = false;
      target.value = '';
    }
  }
};

// 处理删除
const handleDelete = () => {
  if (isFormReadonly.value) {
    NotificationService.info('非 admin 用户不能删除共享智能体');
    return;
  }
  // 显示确认对话框
  Modal.confirm({
    title: '确认删除',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: '确定要删除这个智能体吗？此操作不可撤销。',
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: () => {
      if (props.agentData && props.agentData.id) {
        emit('delete', props.agentData.id);
      }
    },
    onCancel: () => {
      // 用户取消删除，不执行任何操作
    }
  });
};

// 暴露handleDelete方法给父组件
defineExpose({
  handleDelete
});
</script>
<style scoped>
/* 覆盖 antd 默认的 24px，仅作用于头像所在表单项 */
.basic-info-form :deep(.bi-avatar-form-item) { margin-bottom: 10px !important; }
.avatar-studio { padding: 2px 0 0; }
.avatar-studio-body { display: flex; align-items: center; justify-content: center; gap: 25px; }
.avatar-studio-preview { flex: 0 0 72px; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.avatar-studio-current-wrap { position: relative; width: 72px; height: 72px; }
.avatar-studio-current { display: flex; align-items: center; justify-content: center; width: 72px; height: 72px; border-radius: 50%; overflow: hidden; color: white; font-size: 30px; }
.avatar-studio-current img { width: 100%; height: 100%; object-fit: cover; }
.avatar-studio-edit { position: absolute; right: -1px; bottom: -1px; display: grid; place-items: center; box-sizing: border-box; width: 22px; height: 22px; padding: 0; border: 2px solid #fff; border-radius: 50%; background: #3b82f6; color: #fff; cursor: pointer; transition: background-color .2s ease; }
.avatar-studio-edit:hover:not(:disabled) { background: #2563eb; }
.avatar-studio-preview-label { color: #94a3b8; font-size: 11px; line-height: 15px; }
.avatar-studio-picker { min-width: 0; }
@media (max-width: 480px) { .avatar-studio-body { gap: 10px; align-items: flex-start; } }
.avatar-studio-tabs { display: flex; flex-wrap: wrap; gap: 5px; margin-bottom: 7px; width: 341px; justify-content: space-between; }
.avatar-studio-tabs button {
  height: 24px; padding: 0 10px; border: 1px solid #e5e7eb; border-radius: 999px;
  background: #fff; color: #64748b; font-size: 12px; font-weight: 500; line-height: 22px;
  white-space: nowrap; cursor: pointer; user-select: none; -webkit-tap-highlight-color: transparent;
  transition: color .2s cubic-bezier(.22, 1, .36, 1), background-color .2s cubic-bezier(.22, 1, .36, 1), border-color .2s cubic-bezier(.22, 1, .36, 1);
}
.avatar-studio-tabs button:hover:not(.active) { border-color: #bfdbfe; background: #f8fafc; color: #2563eb; }
.avatar-studio-tabs button.active { border-color: #3b82f6; background: #eff6ff; color: #1d4ed8; }
.avatar-studio-colors { display: flex; flex-wrap: nowrap; align-items: center; gap: 13px; box-sizing: border-box; width: 342px; height: 64px; max-width: 100%; padding: 5px; border: 1px solid #eef2f7; border-radius: 18px; background: #f8fafc; }
.avatar-studio-colors .avatar-studio-color:first-child { margin-left: auto; }
.avatar-studio-color { position: relative; box-sizing: border-box; flex: 0 0 30px; width: 30px; height: 30px; padding: 0; border: none; border-radius: 50%; background: var(--swatch); cursor: pointer; transition: transform .15s ease; }
.avatar-studio-color:hover:not(:disabled) { transform: scale(1.1); }
.avatar-studio-color.selected { transform: scale(1.15); }
.avatar-studio-color-check { position: absolute; inset: 0; display: grid; place-items: center; color: #fff; }
.avatar-studio-colors .avatar-studio-more { margin-left: 7px; }
.avatar-studio-presets { display: flex; flex-wrap: wrap; align-items: center; gap: 4px; width: fit-content; max-width: 100%; padding: 5px; border: 1px solid #eef2f7; border-radius: 18px; background: #f8fafc; }
.avatar-studio-preset { position: relative; box-sizing: border-box; flex: 0 0 52px; width: 52px; height: 52px; padding: 2px; border: 2px solid transparent; border-radius: 16px; background: transparent; cursor: pointer; transition: border-color .2s ease; }
.avatar-studio-preset img { display: block; width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }
.avatar-studio-preset:hover:not(:disabled) { border-color: #bfdbfe; }
.avatar-studio-preset.selected { border-color: #3b82f6; }
.avatar-studio-check { position: absolute; top: 2px; right: 2px; display: grid; place-items: center; width: 13px; height: 13px; border-radius: 50%; background: #3b82f6; color: #fff; }
.avatar-studio-more { box-sizing: border-box; flex: 0 0 48px; width: 48px; height: 48px; margin-left: 2px; border: 1px solid #e5e7eb; border-radius: 13px; background: transparent; color: #94a3b8; font-size: 10px; cursor: pointer; transition: color .2s ease, background-color .2s ease, border-color .2s ease; }
.avatar-studio-more:hover { border-color: #bfdbfe; background: #eff6ff; color: #2563eb; }
.avatar-studio button:focus-visible { outline: 2px solid #3b82f6; outline-offset: 2px; }
.avatar-studio button:disabled { cursor: not-allowed; opacity: .55; }

.bi-permission-groups-form-item :deep(.ant-form-item-explain) {
  font-size: 12px;
  margin-top: 5px;
  margin-bottom: -5px;
}
</style>
