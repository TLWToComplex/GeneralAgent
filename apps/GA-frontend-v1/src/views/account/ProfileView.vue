<template>
  <div class="profile-container">
    <div class="page-header">
      <h2>个人资料</h2>
      <p>管理您的个人资料信息</p>
    </div>

    <div class="profile-content">
      <div class="settings-section">
        <div class="setting-item">
          <div class="setting-label">
            <span>头像</span>
          </div>
          <div class="setting-value">
            <div class="avatar-config">
              <div class="avatar-preview-container">
                <div class="avatar-preview">
                  <a-avatar
                      :size="40"
                      class="user-avatar"
                      :src="avatarPreviewSrc"
                      :style="{ backgroundColor: avatarPreviewBg, color: avatarPreviewTextColor }"
                      @click="handleAvatarUpload"
                      title="更换照片"
                  >
                    <template v-if="!avatarUrl">{{ avatarText }}</template>
                  </a-avatar>
                  <button
                      v-if="avatarUrl"
                      class="remove-avatar-btn"
                      @click="clearAvatarImage"
                      aria-label="移除头像"
                  >
                    <CloseOutlined style="color: white; font-size: 10px;"/>
                  </button>
                </div>
              </div>
              <div class="avatar-controls">
                <div class="control-row">
                  <div class="control-actions-btn">
                    <button class="upload-avatar-btn" @click="handleAvatarUpload" title="上传照片" style="cursor: pointer;">
                      <UploadImage style="width: 20px; height: 20px; color: #a6a6a6;" />
                    </button>
                  </div>
                  <input
                      ref="fileInput"
                      accept="image/*"
                      style="display: none"
                      type="file"
                      @change="onFileChange"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 头像背景（仅文字头像时显示） -->
        <div class="setting-item" v-if="!hasAvatarImage">
          <div class="setting-label">
            <span>头像背景</span>
          </div>
          <div class="setting-value">
            <div class="control-actions">
              <div class="color-swatches">
                <button
                    v-for="c in presetColors"
                    :key="c"
                    class="color-swatch"
                    :style="{ backgroundColor: c, outline: avatarBg === c ? '2px solid #1890ff' : 'none' }"
                    @click="onPresetColorSelect(c)"
                    aria-label="选择颜色"
                />
              </div>
              <div
                  class="color-input-wrapper"
                  role="button"
                  aria-label="打开颜色选择器"
                  tabindex="0"
                  @click="openAvatarBgPicker"
                  @keydown.enter="openAvatarBgPicker"
              >
                <div class="color-input-display"></div>
                <input type="color" v-model="avatarBg" ref="avatarBgInput" class="color-input-hidden"/>
              </div>
              <a-input v-model:value="avatarBg" style="width: 120px; border-radius: 12px;"/>
            </div>
          </div>
        </div>

        <!-- 头像文字颜色（仅文字头像时显示） -->
        <div class="setting-item" v-if="!hasAvatarImage">
          <div class="setting-label">
            <span>头像文字颜色</span>
          </div>
          <div class="setting-value">
            <div class="control-actions">
              <div class="color-swatches">
                <button
                    v-for="c in presetColors"
                    :key="c"
                    class="color-swatch"
                    :style="{ backgroundColor: c, outline: avatarTextColor === c ? '2px solid #1890ff' : 'none' }"
                    @click="onPresetTextColorSelect(c)"
                    aria-label="选择颜色"
                />
              </div>
              <div
                  class="color-input-wrapper"
                  role="button"
                  aria-label="打开颜色选择器"
                  tabindex="0"
                  @click="openAvatarTextPicker"
                  @keydown.enter="openAvatarTextPicker"
              >
                <div class="color-input-display"></div>
                <input type="color" v-model="avatarTextColor" ref="avatarTextColorInput" class="color-input-hidden"/>
              </div>
              <a-input v-model:value="avatarTextColor" style="width: 120px; border-radius: 12px;"/>
            </div>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span>用户名</span>
          </div>
          <div class="setting-value">
            <a-input v-model:value="formState.username" style="width: 450px;"/>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span>真实姓名</span>
          </div>
          <div class="setting-value">
            <a-input v-model:value="formState.realname" style="width: 450px;"/>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span>邮箱</span>
          </div>
          <div class="setting-value">
            <a-input v-model:value="formState.email" type="email" style="width: 450px;"/>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span>手机号</span>
          </div>
          <div class="setting-value">
            <a-input v-model:value="profileExtra.contact" style="width: 450px;" placeholder="请输入手机号"/>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span>用户组</span>
          </div>
          <div class="setting-value group-display-wrapper">
            <div class="group-display-content">
              <div v-if="groupLoading" class="group-display-hint">正在加载用户组...</div>
              <div v-else-if="currentUserGroups.length" class="group-tag-list">
                <a-tag v-for="group in currentUserGroups" :key="group.group_id" color="blue">
                  {{ group.group_name }}
                </a-tag>
              </div>
              <div v-else class="group-display-hint">当前未分配用户组</div>
              <div class="group-display-tip">用户组由管理员分配，当前页面不可修改</div>
            </div>
          </div>
        </div>
      </div>

      <div class="settings-section">
        <div class="setting-item">
          <div class="setting-label">
          </div>
          <div class="setting-action">
            <button v-if="isFormChanged" @click="resetProfile" class="reset-info-btn" :disabled="savingProfile || loadingProfile">重置信息</button>
            <button @click="saveProfile" class="update-info-btn" :disabled="savingProfile || loadingProfile">
              {{ savingProfile ? '保存中...' : '更新信息' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, reactive, onMounted, onActivated, computed } from 'vue';
import { useRoute } from 'vue-router';
import {CloseOutlined} from '@ant-design/icons-vue';
import UploadImage from '@/components/icons/UploadImage.vue';
import NotificationService from '@/utils/NotificationService';
import {
  getAiUserRecord,
  updateUser,
  type AiUserRecord,
  type UpdateUserPayload,
  type UserGroupInfo
} from '@/services/aiUser';

defineOptions({
  name: 'ProfileView',
  components: {
    UploadImage
  }
});

interface FormState {
  username: string;
  email: string;
  realname: string;
}

interface StoredUserProfile {
  username: string;
  email: string;
  avatar: string;
  avatarBackground: string;
  avatarTextColor: string;
  uuid: string;
  realname?: string;
  contact?: string;
  address?: string;
}

const formState = reactive<FormState>({
  username: '',
  email: '',
  realname: ''
});

const route = useRoute();

const DEFAULT_AVATAR_BG = '#1890ff';
const DEFAULT_AVATAR_TEXT_COLOR = '#ffffff';
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const MOBILE_PATTERN = /^1[3-9]\d{9}$/;
const MIN_REALNAME_LENGTH = 3;

const userUuid = ref<string>('');
const loadingProfile = ref(false);
const savingProfile = ref(false);
const groupLoading = ref(false);
const currentUserGroups = ref<UserGroupInfo[]>([]);

const avatarUrl = ref<string>('');
const avatarBg = ref<string>('');
const avatarTextColor = ref<string>('');
const fileInput = ref<HTMLInputElement | null>(null);
const avatarBgInput = ref<HTMLInputElement | null>(null);
const avatarTextColorInput = ref<HTMLInputElement | null>(null);

const originalData = reactive({
  uuid: '',
  username: '',
  email: '',
  realname: '',
  contact: '',
  avatar: '',
  avatarBackground: '',
  avatarTextColor: ''
});

const profileExtra = reactive({
  contact: ''
});

// 计算表单是否发生变化
const isFormChanged = computed(() => {
  return (
    userUuid.value !== originalData.uuid ||
    formState.username !== originalData.username ||
    formState.email !== originalData.email ||
    formState.realname !== originalData.realname ||
    profileExtra.contact !== originalData.contact ||
    avatarUrl.value !== originalData.avatar ||
    avatarBg.value !== originalData.avatarBackground ||
    avatarTextColor.value !== originalData.avatarTextColor
  );
});

const avatarText = computed(() => {
  const displayName = formState.realname.trim() || formState.username.trim();
  return displayName ? displayName.charAt(0).toUpperCase() : 'U';
});

const hasAvatarImage = computed(() => Boolean(avatarUrl.value));
const avatarPreviewSrc = computed(() => avatarUrl.value || '');
const avatarPreviewBg = computed(() => {
  if (hasAvatarImage.value) return '#ffffff';
  if (avatarBg.value === 'transparent') return 'transparent';
  return avatarBg.value || DEFAULT_AVATAR_BG;
});
const avatarPreviewTextColor = computed(() => {
  return hasAvatarImage.value ? undefined : (avatarTextColor.value || DEFAULT_AVATAR_TEXT_COLOR);
});

const presetColors = ['transparent', '#ffffff', '#1890ff', '#722ed1', '#eb2f96', '#faad14', '#13c2c2', '#52c41a', '#2f54eb', '#fa541c'];

const safeString = (value: unknown) => String(value ?? '').trim();

const normalizeAdditionalInfo = (value: unknown): Record<string, any> => {
  if (value && typeof value === 'object' && !Array.isArray(value)) {
    return value as Record<string, any>;
  }
  return {};
};

const getStoredProfile = (): StoredUserProfile => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) {
      return {
        username: '',
        email: '',
        avatar: '',
        avatarBackground: '',
        avatarTextColor: '',
        uuid: ''
      };
    }

    const parsed = JSON.parse(raw);
    return {
      username: safeString(parsed?.username),
      email: safeString(parsed?.email),
      avatar: safeString(parsed?.avatar),
      avatarBackground: safeString(parsed?.avatarBackground),
      avatarTextColor: safeString(parsed?.avatarTextColor),
      uuid: safeString(parsed?.uuid),
      realname: safeString(parsed?.realname),
      contact: safeString(parsed?.contact),
      address: safeString(parsed?.address)
    };
  } catch (error) {
    console.error('读取本地用户信息失败:', error);
    return {
      username: '',
      email: '',
      avatar: '',
      avatarBackground: '',
      avatarTextColor: '',
      uuid: ''
    };
  }
};

const buildProfileSnapshot = (storedProfile: StoredUserProfile, record: AiUserRecord | null) => {
  const additionalInfo = normalizeAdditionalInfo(record?.additional_info);

  return {
    uuid: safeString(record?.uuid) || storedProfile.uuid,
    username: safeString(record?.username) || storedProfile.username,
    email: safeString(record?.email) || storedProfile.email,
    realname: safeString(record?.realname) || safeString(additionalInfo.realname) || safeString(storedProfile.realname),
    contact: safeString(record?.contact) || safeString(additionalInfo.contact) || safeString(storedProfile.contact),
    avatar: safeString(record?.avatar) || safeString(additionalInfo.avatar) || storedProfile.avatar,
    avatarBackground: safeString(record?.avatarBackground) || safeString(additionalInfo.avatarBackground) || storedProfile.avatarBackground,
    avatarTextColor: safeString(record?.avatarTextColor) || safeString(additionalInfo.avatarTextColor) || storedProfile.avatarTextColor
  };
};

const applyProfileSnapshot = (snapshot: ReturnType<typeof buildProfileSnapshot>) => {
  userUuid.value = snapshot.uuid;
  formState.username = snapshot.username;
  formState.email = snapshot.email;
  formState.realname = snapshot.realname;
  profileExtra.contact = snapshot.contact;
  avatarUrl.value = snapshot.avatar;
  avatarBg.value = snapshot.avatarBackground;
  avatarTextColor.value = snapshot.avatarTextColor;
};

const syncOriginalData = (snapshot: ReturnType<typeof buildProfileSnapshot>) => {
  originalData.uuid = snapshot.uuid;
  originalData.username = snapshot.username;
  originalData.email = snapshot.email;
  originalData.realname = snapshot.realname;
  originalData.contact = snapshot.contact;
  originalData.avatar = snapshot.avatar;
  originalData.avatarBackground = snapshot.avatarBackground;
  originalData.avatarTextColor = snapshot.avatarTextColor;
};

const persistProfile = (snapshot: ReturnType<typeof buildProfileSnapshot>, storedProfile: StoredUserProfile) => {
  const nextProfile: StoredUserProfile = {
    ...storedProfile,
    username: snapshot.username,
    email: snapshot.email,
    contact: snapshot.contact,
    avatar: snapshot.avatar,
    avatarBackground: snapshot.avatarBackground,
    avatarTextColor: snapshot.avatarTextColor,
    uuid: snapshot.uuid,
    realname: snapshot.realname
  };

  localStorage.setItem('user-profile', JSON.stringify(nextProfile));
};

const hydrateProfile = (storedProfile: StoredUserProfile, record: AiUserRecord | null) => {
  const snapshot = buildProfileSnapshot(storedProfile, record);
  applyProfileSnapshot(snapshot);
  syncOriginalData(snapshot);
  persistProfile(snapshot, storedProfile);
};

const onPresetColorSelect = (c: string) => {
  avatarBg.value = c;
};
const onPresetTextColorSelect = (c: string) => {
  avatarTextColor.value = c;
};

const openAvatarBgPicker = () => {
  if (avatarBgInput.value) {
    avatarBgInput.value.click();
  }
};

const openAvatarTextPicker = () => {
  if (avatarTextColorInput.value) {
    avatarTextColorInput.value.click();
  }
};

// 处理头像上传点击
const handleAvatarUpload = () => {
  if (fileInput.value) {
    fileInput.value.click();
  }
};

const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];

  if (file) {
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
      avatarUrl.value = e.target?.result as string;
    };
    reader.readAsDataURL(file);
  }
};

const clearAvatarImage = () => {
  avatarUrl.value = '';
  avatarBg.value = avatarBg.value || DEFAULT_AVATAR_BG;
  avatarTextColor.value = avatarTextColor.value || DEFAULT_AVATAR_TEXT_COLOR;
};

const loadProfile = async () => {
  const storedProfile = getStoredProfile();
  hydrateProfile(storedProfile, null);
  currentUserGroups.value = [];

  const recordQuery = storedProfile.uuid
    ? { uuid: storedProfile.uuid }
    : storedProfile.username
      ? { username: storedProfile.username }
      : null;

  if (!recordQuery) {
    return;
  }

  loadingProfile.value = true;
  groupLoading.value = true;
  try {
    const record = await getAiUserRecord(recordQuery);
    if (record) {
      hydrateProfile(storedProfile, record);
      currentUserGroups.value = record.groups;
    } else {
      currentUserGroups.value = [];
    }
  } catch (error) {
    console.error('加载用户信息失败:', error);
    currentUserGroups.value = [];
  } finally {
    loadingProfile.value = false;
    groupLoading.value = false;
  }
};

const validateProfileForm = (params: { username: string; email: string; realname: string; contact: string }) => {
  const { username, email, realname, contact } = params;

  if (!username) {
    NotificationService.warning('请输入用户名');
    return false;
  }
  if (!realname) {
    NotificationService.warning('请输入真实姓名');
    return false;
  }
  if (realname.length < MIN_REALNAME_LENGTH) {
    NotificationService.warning('真实姓名长度需大于2个字符');
    return false;
  }
  if (!contact) {
    NotificationService.warning('请输入手机号');
    return false;
  }
  if (!MOBILE_PATTERN.test(contact)) {
    NotificationService.warning('请输入正确的手机号');
    return false;
  }
  if (email && !EMAIL_PATTERN.test(email)) {
    NotificationService.warning('请输入正确的邮箱地址');
    return false;
  }

  return true;
};

const saveProfile = async () => {
  const uuid = userUuid.value.trim();
  const username = formState.username.trim();
  const email = formState.email.trim();
  const realname = formState.realname.trim();
  const contact = profileExtra.contact.trim();
  const hasAvatarChanges =
    avatarUrl.value !== originalData.avatar ||
    avatarBg.value !== originalData.avatarBackground ||
    avatarTextColor.value !== originalData.avatarTextColor;
  const hasContactChanges = contact !== originalData.contact;

  if (!uuid) {
    NotificationService.error('用户标识缺失，无法保存');
    return;
  }
  if (!validateProfileForm({ username, email, realname, contact })) {
    return;
  }
  if (!isFormChanged.value && !hasAvatarChanges && !hasContactChanges) {
    NotificationService.info('没有可保存的变更');
    return;
  }

  const storedProfile = getStoredProfile();
  const payload: UpdateUserPayload = {
    uuid
  };

  if (username !== originalData.username) {
    payload.username = username;
  }
  if (email !== originalData.email) {
    payload.email = email;
  }
  if (realname !== originalData.realname) {
    payload.realname = realname;
  }
  if (hasAvatarChanges || hasContactChanges) {
    payload.additional_info = {
      avatar: avatarUrl.value,
      avatarBackground: avatarUrl.value ? '#ffffff' : (avatarBg.value || DEFAULT_AVATAR_BG),
      avatarTextColor: avatarUrl.value ? (avatarTextColor.value || DEFAULT_AVATAR_TEXT_COLOR) : (avatarTextColor.value || DEFAULT_AVATAR_TEXT_COLOR),
      contact
    };
  }

  const updateBy = storedProfile.username || username;
  if (updateBy) {
    payload.update_by = updateBy;
  }

  try {
    savingProfile.value = true;
    await updateUser(payload);

    let record: AiUserRecord | null = null;
    try {
      record = await getAiUserRecord({ uuid });
    } catch (error) {
      console.error('刷新用户信息失败:', error);
    }

    if (record) {
      hydrateProfile(storedProfile, record);
      currentUserGroups.value = record.groups;
    } else {
      const snapshot = {
        uuid,
        username,
        email,
        realname,
        contact,
        avatar: avatarUrl.value,
        avatarBackground: avatarUrl.value ? '#ffffff' : (avatarBg.value || DEFAULT_AVATAR_BG),
        avatarTextColor: avatarTextColor.value || DEFAULT_AVATAR_TEXT_COLOR
      };
      applyProfileSnapshot(snapshot);
      syncOriginalData(snapshot);
      persistProfile(snapshot, storedProfile);
    }

    NotificationService.success('个人信息保存成功');
    window.dispatchEvent(new CustomEvent('user-info-updated'));
  } catch (error) {
    console.error('保存用户信息失败:', error);
    NotificationService.error('保存个人信息失败');
  } finally {
    savingProfile.value = false;
  }
};

const resetProfile = () => {
  formState.username = originalData.username;
  formState.email = originalData.email;
  formState.realname = originalData.realname;
  profileExtra.contact = originalData.contact;
  avatarUrl.value = originalData.avatar;
  avatarBg.value = originalData.avatarBackground;
  avatarTextColor.value = originalData.avatarTextColor;
  userUuid.value = originalData.uuid;
  NotificationService.success('个人信息已重置');
};

onMounted(() => {
  loadProfile();
});

onActivated(() => {
  if (route.path === '/account/profile') {
    loadProfile();
  }
});
</script>

<style scoped>
.profile-container {
  padding: 24px 40px;
  height: 100%;
  overflow-y: auto;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #1f1f1f;
}

.page-header p {
  color: #8c8c8c;
  font-size: 14px;
}

.settings-section {
  border-bottom: 1px solid #f0f0f0;
}

.settings-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.settings-section h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: #1f1f1f;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 0;
  border-bottom: 1px solid #f5f5f5;
}

.setting-item:last-child {
  border-bottom: none;
}

.setting-label {
  flex: 1;
}

.setting-label span {
  font-size: 14px;
  color: #1f1f1f;
  font-weight: 500;
}

.setting-value {
  flex: 2;
  display: flex;
  justify-content: flex-end;
}

.group-display-wrapper {
  align-items: center;
}

.group-display-content {
  width: 450px;
  min-height: 40px;
  padding: 10px 14px;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #fafafa;
}

.group-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.group-display-hint {
  color: #6b7280;
  font-size: 14px;
}

.group-display-tip {
  margin-top: 8px;
  color: #9ca3af;
  font-size: 12px;
}


.avatar-config {
  gap: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #ffffff;
  border-radius: 60px;
  border: 1px solid #ececec;
  padding: 7px 7px 6px;
}

.avatar-preview-container {
  position: relative;
}

.avatar-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  position: relative;
}

.remove-avatar-btn {
  position: absolute;
  top: -5px;
  right: -5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background-color: #4873ff;
  border: 2px solid white;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

.remove-avatar-btn:hover {
  background-color: #375cd6;
}

.remove-avatar-btn svg {
  width: 16px;
  height: 16px;
}

.avatar-controls {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.control-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control-label {
  width: 64px;
  color: #1f1f1f;
}

.control-actions {
  gap: 8px;
  padding: 8px;
  display: flex;
  align-items: center;
  border-radius: 18px;
  border: 1px solid #e5e5e5;
}

.color-input {
  -webkit-appearance: none;
  appearance: none;
  width: 22px;
  height: 22px;
  padding: 0;
  border-radius: 50%;
  border: 1px solid #e5e5e5;
  background: conic-gradient(
      #ff0000,
      #ff7f00,
      #ffff00,
      #00ff00,
      #00ffff,
      #0000ff,
      #8b00ff,
      #ff0000
  );
  cursor: pointer;
}

.color-input:focus {
  outline: 2px solid #1890ff;
  outline-offset: 1px;
}

.color-input::-webkit-color-swatch-wrapper {
  padding: 0;
  border-radius: 50%;
}

.color-input::-webkit-color-swatch {
  border: none;
  border-radius: 50%;
  background: transparent;
}

/* Firefox */
.color-input::-moz-color-swatch {
  border: none;
  border-radius: 50%;
  background: transparent;
}

/* 自定义彩虹按钮包装 */
.color-input-wrapper {
  position: relative;
  width: 22px;
  height: 22px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  border: 1px solid #e5e5e5;
  cursor: pointer;
}

.color-input-wrapper:focus {
  outline: 2px solid #1890ff;
  outline-offset: 1px;
}

.color-input-display {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: conic-gradient(
      #ff0000,
      #ff7f00,
      #ffff00,
      #00ff00,
      #00ffff,
      #0000ff,
      #8b00ff,
      #ff0000
  );
}

.color-input-hidden {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  opacity: 0;
  pointer-events: none;
}

.color-swatches {
  display: flex;
  align-items: center;
  gap: 6px;
}

.color-swatch {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid #e5e5e5;
  cursor: pointer;
}

/* 透明色的特殊样式 */
.color-swatch[style*='transparent'] {
  background-image: linear-gradient(45deg, #e5e5e5 25%, transparent 25%),
  linear-gradient(-45deg, #e5e5e5 25%, transparent 25%),
  linear-gradient(45deg, transparent 75%, #e5e5e5 75%),
  linear-gradient(-45deg, transparent 75%, #e5e5e5 75%);
  background-size: 6px 6px;
  background-position: 0 0, 0 3px, 3px -3px, -3px 0;
}

/* 白色的特殊样式，添加边框以便区分 */
.color-swatch[style*='ffffff'] {
  border: 1px solid #d9d9d9;
}

.user-avatar {
  background-color: #ffffff;
  font-weight: bold;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid #f3f3f3;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.user-avatar:hover {
  transform: scale(1.05);
}

.user-avatar :deep(.ant-avatar-string) {
  color: inherit;
  font-size: 22px !important;
}

/* 添加针对头像图片的样式 */
.user-avatar :deep(.ant-avatar-image) {
  object-fit: cover;
  transition: transform 0.3s ease;
  width: 100%;
  height: 100%;
  object-position: center;
}

.user-avatar :deep(img) {
  object-fit: cover;
  transition: transform 0.3s ease;
  width: 100%;
  height: 100%;
  object-position: center;
}

.setting-action {
  margin-left: 16px;
}

.upload-avatar-btn {
  gap: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 35px;
  width: 35px;
  border-radius: 12px;
  background-color: #ffffff;
  border: none;
  transition: background-color 0.3s ease;
  cursor: pointer;
}

.upload-avatar-btn:hover {
  background-color: #f5f5f5;
}

.update-info-btn {
  background: #1677ff;
  color: #ffffff;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 400;
  font-size: 14px;
  border: none;
  cursor: pointer;
}

.update-info-btn:hover {
  background-color: #0958d9;
}

.reset-info-btn {
  background: #f3f4f6;
  color: #374151;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 400;
  font-size: 14px;
  border: none;
  cursor: pointer;
  margin-right: 10px;
}

.reset-info-btn:hover {
  background-color: #e5e7eb;
}
</style>
