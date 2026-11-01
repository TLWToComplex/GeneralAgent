<template>
  <div class="step-content profile-step">
    <div class="progress-section" :class="{ animate: showContent }">
      <div class="progress-dots">
        <div class="dot completed"></div>
        <div class="dot-line completed"></div>
        <div class="dot active"></div>
        <div class="dot-line"></div>
        <div class="dot"></div>
      </div>
      <div class="progress-text">补充用户信息</div>
    </div>

    <div class="title-section" :class="{ animate: showContent }">
      <h1 class="setup-title">完善个人资料</h1>
      <p class="setup-description">首次登录请补充姓名、联系方式和头像信息</p>
    </div>

    <div class="form-section" :class="{ animate: showContent }">
      <a-form ref="formRef" :model="formData" :rules="rules" layout="vertical" class="setup-form">
        <div class="avatar-upload-section">
          <div class="avatar-wrapper">
            <div class="avatar-preview">
              <img :src="formData.avatar" alt="avatar" class="avatar-image" />
            </div>
            
            <a-dropdown placement="bottomLeft" :trigger="['click']">
              <a-button shape="circle" type="primary" class="avatar-edit-btn">
                <template #icon><UploadImage style="width: 16px; height: 16px;" /></template>
              </a-button>
              <template #overlay>
                <a-menu>
                  <a-menu-item key="upload" @click="handleAvatarUpload">
                    更换头像
                  </a-menu-item>
                  <a-menu-item key="reset" @click="resetAvatar" :disabled="formData.avatar === defaultAvatar">
                    恢复默认头像
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
          </div>

          <input
            ref="fileInput"
            type="file"
            accept="image/*"
            style="display: none;"
            @change="onFileChange"
          />
        </div>

        <a-form-item label="姓名" name="realname" required>
          <a-input v-model:value="formData.realname" placeholder="请输入姓名" size="large" />
        </a-form-item>

        <a-form-item label="联系方式" name="contact" required>
          <a-input v-model:value="formData.contact" placeholder="请输入联系方式" size="large" />
        </a-form-item>

        <a-form-item label="用户组" name="groupIds" required class="readonly-group-form-item">
          <div class="readonly-group-box" :class="{ loading: groupsLoading }">
            <a-spin v-if="groupsLoading" size="small" />
            <template v-else-if="defaultGroupDisplays.length">
              <a-tag
                v-for="group in defaultGroupDisplays"
                :key="group.value"
                color="blue"
                class="readonly-group-tag"
              >
                {{ group.label }}
              </a-tag>
            </template>
            <span v-else class="readonly-group-placeholder">当前未配置默认用户组</span>
          </div>
        </a-form-item>

      </a-form>
    </div>

    <div class="action-section" :class="{ animate: showContent }">
      <div class="nav-pill">
        <a-tooltip title="返回上一步" placement="top">
          <a-button type="text" shape="circle" class="nav-icon-btn" @click="handlePrev">
            <template #icon><ArrowLeftOutlined /></template>
          </a-button>
        </a-tooltip>
        <div class="nav-divider"></div>
        <a-button type="primary" shape="round" class="nav-primary-btn" @click="handleNext">
          下一步
          <ArrowRightOutlined />
        </a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch, toRefs, onMounted } from 'vue';
import type { FormInstance } from 'ant-design-vue';
import { ArrowLeftOutlined, ArrowRightOutlined } from '@ant-design/icons-vue';
import UploadImage from '@/components/icons/UploadImage.vue';
import NotificationService from '@/utils/NotificationService';
import bgPoster from '@/assets/image/jpg/background.jpg';
import { getDefaultAiUserGroup, listAiUserGroups } from '@/services/aiPermission';

interface UserProfileFormData {
  realname: string;
  contact: string;
  avatar: string;
  groupIds: string[];
}

const props = defineProps<{
  showContent: boolean;
  initialData?: UserProfileFormData;
}>();

const { showContent, initialData } = toRefs(props);
const emit = defineEmits<{
  (e: 'prev'): void;
  (e: 'next', data: UserProfileFormData, groupNames: string[]): void;
}>();

const defaultAvatar = bgPoster as unknown as string;
const formRef = ref<FormInstance>();
const fileInput = ref<HTMLInputElement | null>(null);
const formData = reactive<UserProfileFormData>({
  realname: '',
  contact: '',
  avatar: defaultAvatar,
  groupIds: []
});

const groupOptions = ref<{ label: string; value: string }[]>([]);
const groupsLoading = ref(false);
const defaultGroupId = ref('');

const applyDefaultUserGroups = () => {
  formData.groupIds = defaultGroupId.value ? [defaultGroupId.value] : [];
};

const defaultGroupDisplays = computed(() => (
  formData.groupIds
    .map((id) => {
      const option = groupOptions.value.find(opt => opt.value === id);
      return {
        value: id,
        label: option?.label || id
      };
    })
    .filter(group => group.value)
));

onMounted(async () => {
  groupsLoading.value = true;
  try {
    const [groups, defaultGroup] = await Promise.all([
      listAiUserGroups(),
      getDefaultAiUserGroup()
    ]);
    groupOptions.value = groups.map((g: { name: string; uuid: string }) => ({ label: g.name, value: g.uuid }));
    defaultGroupId.value = String(defaultGroup?.uuid || '').trim();
    applyDefaultUserGroups();
  } catch (error) {
    console.error('Failed to load user groups', error);
    defaultGroupId.value = '';
    applyDefaultUserGroups();
  } finally {
    groupsLoading.value = false;
  }
});

watch(
  initialData,
  (val) => {
    if (!val) return;
    formData.realname = val.realname || '';
    formData.contact = val.contact || '';
    formData.avatar = val.avatar || defaultAvatar;
    applyDefaultUserGroups();
  },
  { immediate: true, deep: true }
);

const rules = {
  realname: [
    { required: true, message: '请输入姓名' },
    { min: 2, message: '姓名至少需要 2 个字符' }
  ],
  contact: [
    { required: true, message: '请输入联系方式' },
    { pattern: /^1[3-9]\d{9}$/, message: '请输入正确的联系方式' }
  ],
  groupIds: [
    {
      required: true,
      type: 'array',
      validator: (_rule: unknown, value: string[]) => {
        if (!value || value.length === 0) {
          return Promise.reject('请先在用户组管理中配置默认用户组');
        }
        return Promise.resolve();
      }
    }
  ]
};

const handleAvatarUpload = () => {
  fileInput.value?.click();
};

const resetAvatar = () => {
  formData.avatar = defaultAvatar;
  if (fileInput.value) {
    fileInput.value.value = '';
  }
};

const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (!file) return;

  if (!file.type.startsWith('image/')) {
    NotificationService.error('请选择图片文件');
    target.value = '';
    return;
  }

  if (file.size > 2 * 1024 * 1024) {
    NotificationService.error('图片大小不能超过2MB');
    target.value = '';
    return;
  }

  const reader = new FileReader();
  reader.onload = (e) => {
    formData.avatar = String(e.target?.result || defaultAvatar);
  };
  reader.readAsDataURL(file);
};

const handlePrev = () => {
  emit('prev');
};

const handleNext = async () => {
  try {
    await formRef.value?.validate();
    applyDefaultUserGroups();
    if (!formData.groupIds.length) {
      NotificationService.warning('请先在用户组管理中配置默认用户组');
      return;
    }
    const groupNames = formData.groupIds.map(id => {
      const option = groupOptions.value.find(opt => opt.value === id);
      return option?.label || id;
    }).filter(Boolean);
    
    emit('next', {
      realname: formData.realname.trim(),
      contact: formData.contact.trim(),
      avatar: formData.avatar || defaultAvatar,
      groupIds: formData.groupIds
    }, groupNames);
  } catch {
    NotificationService.warning('请先完善必填信息');
  }
};
</script>

<style scoped>
@import '@/assets/styles/welcome.css';

.profile-step {
  margin-top: 20px;
}

.avatar-upload-section {
  display: flex;
  justify-content: center;
  margin-bottom: 24px;
}

.avatar-wrapper {
  position: relative;
  width: 96px;
  height: 96px;
}

.avatar-preview {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  overflow: hidden;
  border: 3px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.16);
  background: #ffffff;
}

.avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.avatar-edit-btn {
  position: absolute;
  right: -4px;
  bottom: -4px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-section {
  display: flex;
  justify-content: center;
  margin-top: 80px;
}

.readonly-group-form-item :deep(.ant-form-item-label > label) {
  cursor: default;
}

.readonly-group-box {
  min-height: 40px;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 4px 6px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.74);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95);
  color: #475569;
  cursor: not-allowed;
}

.readonly-group-box.loading {
  justify-content: center;
}

.readonly-group-tag {
  margin-inline-end: 0;
  border-radius: 8px;
  padding: 2px 10px;
  line-height: 22px;
}

.readonly-group-placeholder {
  color: #94a3b8;
  font-size: 14px;
}

:deep(.compact-tags-select .ant-select-selector) {
  padding: 1px 7px !important;
  border-radius: 12px !important;
}

:deep(.compact-tags-select .ant-select-selection-placeholder) {
  font-size: 14px;
}

:deep(.compact-tags-select .ant-select-selection-item) {
  height: 24px;
  line-height: 22px;
  margin-top: 4px;
  margin-bottom: 4px;
  background: #f0f5ff;
  border: 1px solid #adc6ff;
  border-radius: 6px;
  color: #1d39c4;
  font-size: 13px;
  padding: 0 8px;
}

:deep(.compact-tags-select .ant-select-selection-item-remove) {
  color: #85a5ff;
}

:deep(.compact-tags-select .ant-select-selection-item-remove:hover) {
  color: #2f54eb;
}
</style>
