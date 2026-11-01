<template>
  <div class="security-container">
    <div class="page-header">
      <h2>账户安全</h2>
      <p>管理您的账户安全设置</p>
    </div>
    
    <div class="security-content">
      <div class="settings-section">
        <h3>密码</h3>
        <div class="setting-item">
          <div class="setting-label">
            <span>修改密码</span>
            <p class="setting-description">定期更改密码以确保账户安全</p>
          </div>
          <div class="setting-action">
            <button @click="showChangePassword" class="change-password-btn">修改密码</button>
          </div>
        </div>
      </div>
      
      <div class="settings-section">
        <h3>账户操作</h3>
        <div class="setting-item">
          <div class="setting-label">
            <span>注销账户</span>
            <p class="setting-description">
              注销您的账户将删除所有数据
            </p>
          </div>
          <div class="setting-action">
            <button @click="showDeleteConfirm" class="delete-account-btn">注销账户</button>
          </div>
        </div>
      </div>
    </div>
  </div>
  
  <!-- 注销账户审批式两步确认弹窗（垂直居中） -->
  <!-- 注销账户审批式两步确认弹窗 -->
  <a-modal
    v-model:open="deleteConfirmVisible"
    :footer="null"
    centered
    :maskClosable="false"
    :destroyOnClose="true"
    :closable="true"
    :width="480"
    class="delete-confirm-modal"
  >
    <div class="delete-modal-body">
      <!-- 步骤条 -->
      <div class="steps-container">
        <div class="step-item" :class="{ active: deleteConfirmStep === 0, completed: deleteConfirmStep > 0 }">
          <div class="step-icon">1</div>
          <span class="step-text">风险告知</span>
        </div>
        <div class="step-line"></div>
        <div class="step-item" :class="{ active: deleteConfirmStep === 1 }">
          <div class="step-icon">2</div>
          <span class="step-text">最终确认</span>
        </div>
      </div>

      <!-- 第一步：风险告知 -->
      <div v-if="deleteConfirmStep === 0" class="step-content">
        <!-- 1. 警告部分 -->
        <div class="warning-banner">
          <WarningOutlined class="warning-icon" />
          <div class="warning-text">
            <h4>高风险操作警告</h4>
            <p>此操作将永久删除账户，无法恢复</p>
          </div>
        </div>

        <!-- 2. 操作后果部分 -->
        <div class="consequence-section">
          <h4 class="section-title">注销账户将导致以下后果：</h4>
          <ul class="consequence-list">
            <li>
              <UserDeleteOutlined class="list-icon" />
              <span>个人资料、偏好设置将被永久移除</span>
            </li>
            <li>
              <MessageOutlined class="list-icon" />
              <span>所有聊天记录、附件及导入内容将失效</span>
            </li>
            <li>
              <ApiOutlined class="list-icon" />
              <span>MCP服务器绑定与模型配置将全部失效</span>
            </li>
          </ul>
        </div>

        <!-- 3. 按钮和选择部分 -->
        <div class="action-section">
          <div 
            class="custom-checkbox-wrapper" 
            :class="{ checked: hasAcknowledgedRisk }"
            @click="hasAcknowledgedRisk = !hasAcknowledgedRisk"
          >
            <div class="custom-checkbox">
              <svg v-if="hasAcknowledgedRisk" class="check-icon" viewBox="0 0 12 10">
                <polyline points="1.5 6 4.5 9 10.5 1"></polyline>
              </svg>
            </div>
            <span class="checkbox-label">我已阅读并理解风险</span>
          </div>

          <div class="modal-actions">
            <a-button @click="handleDeleteConfirmCancel" class="cancel-btn">取消</a-button>
            <a-button 
              type="primary" 
              danger 
              :disabled="!canProceedStep0" 
              @click="handleDeleteConfirmNext"
              class="next-btn"
            >
              继续
            </a-button>
          </div>
        </div>
      </div>

      <!-- 第二步：最终确认 -->
      <div v-else class="step-content step-2-redesign">
        <div class="security-header">
          <div class="icon-wrapper-pulse">
            <SafetyCertificateOutlined class="confirm-icon-pulse" />
          </div>
          <h3>安全验证</h3>
          <p class="subtitle">为了您的账户安全，请完成以下验证</p>
        </div>

        <div class="account-card">
          <div 
            class="avatar-placeholder"
            :style="{ 
              backgroundColor: userAvatar ? 'transparent' : userAvatarBg,
              color: userAvatarTextColor
            }"
          >
            <img v-if="userAvatar" :src="userAvatar" class="avatar-img" />
            <template v-else>
              {{ userIdentifier[0] ? userIdentifier[0].toUpperCase() : 'U' }}
            </template>
          </div>
          <div class="account-info">
            <span class="label">即将注销账户</span>
            <span class="value">{{ userIdentifier }}</span>
          </div>
        </div>

        <div class="verification-section">
          <div class="input-group-row">
            <span class="input-prefix">确认操作</span>
            <a-input 
              v-model:value="confirmationText" 
              placeholder="输入 '注销' " 
              :status="confirmationText && !isConfirmInputValid ? 'error' : ''"
              class="confirm-input-refined"
            >
              <template #suffix>
                <CheckCircleOutlined v-if="isConfirmInputValid" style="color: #52c41a" />
              </template>
            </a-input>
          </div>
        </div>

        <div class="action-footer">
          <div class="checkbox-wrapper final-check-inline">
            <div 
              class="custom-checkbox-wrapper danger-mode" 
              :class="{ checked: isFinalConfirmChecked }"
              @click="isFinalConfirmChecked = !isFinalConfirmChecked"
            >
              <div class="custom-checkbox">
                <svg v-if="isFinalConfirmChecked" class="check-icon" viewBox="0 0 12 10">
                  <polyline points="1.5 6 4.5 9 10.5 1"></polyline>
                </svg>
              </div>
              <span class="checkbox-label">确认放弃账户</span>
            </div>
          </div>

          <div class="modal-actions inline-actions">
            <a-button @click="handleDeleteConfirmCancel" class="cancel-btn">返回</a-button>
            <a-button 
              type="primary" 
              danger 
              :disabled="!isFinalActionEnabled" 
              @click="handleDeleteConfirmFinal"
              class="delete-btn"
              :loading="false"
            >
              注销 {{ finalBtnCountdown > 0 ? `(${finalBtnCountdown}s)` : '' }}
            </a-button>
          </div>
        </div>
      </div>
    </div>
  </a-modal>

  <!-- 修改密码弹窗 -->
  <a-modal
    v-model:open="changePwdVisible"
    title="修改密码"
    centered
    :maskClosable="false"
    :destroyOnClose="true"
    :closable="true"
    :width="500"
    class="change-password-modal"
  >
    <div class="confirm-modal-content">
      <div class="form-item">
        <div class="form-label required">当前密码</div>
        <a-input-password
          v-model:value="oldPassword"
          placeholder="请输入当前密码"
          :status="showOldError ? 'error' : undefined"
        />
        <div v-if="showOldError" class="form-error">请输入当前密码</div>
      </div>
      <div class="form-item">
        <div class="form-label required">新密码</div>
        <a-input-password
          v-model:value="newPassword"
          placeholder="请输入新密码"
          :status="showNewError ? 'error' : undefined"
        />
        <div v-if="showNewError" class="form-error">{{ PASSWORD_COMPLEXITY_MESSAGE }}，{{ PASSWORD_USERNAME_MESSAGE }}，且不可与当前密码相同</div>
      </div>
      <div class="form-item">
        <div class="form-label required">确认新密码</div>
        <a-input-password
          v-model:value="confirmPassword"
          placeholder="请再次输入新密码"
          :status="showConfirmError ? 'error' : undefined"
        />
        <div v-if="showConfirmError" class="form-error">两次输入的新密码不一致</div>
      </div>
    </div>
    <template #footer>
      <div class="modal-footer change-password-footer">
        <a-button class="change-password-action-btn change-password-cancel-btn" @click="handleChangeCancel">取消</a-button>
        <a-button class="change-password-action-btn change-password-confirm-btn" type="primary" :disabled="!isChangeValid || changeLoading" :loading="changeLoading" @click="handleChangeConfirm">修改</a-button>
      </div>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { deleteUser, changePassword } from '@/services/aiUser';
import { useRouter, useRoute } from 'vue-router';
import { ROUTES } from '@/config/constants';
import NotificationService from '@/utils/NotificationService';
import { 
  CheckCircleOutlined,
  WarningOutlined,
  UserDeleteOutlined,
  MessageOutlined,
  ApiOutlined,
  SafetyCertificateOutlined
} from '@ant-design/icons-vue';
import bgPoster from '@/assets/image/jpg/background.jpg';
import { broadcastGlobalLogout } from '@/utils/TabScopeService';
import {
  isPasswordComplexEnough,
  doesPasswordContainUsername,
  PASSWORD_COMPLEXITY_MESSAGE,
  PASSWORD_USERNAME_MESSAGE
} from '@/utils/passwordPolicy';

defineOptions({
  name: 'SecurityView'
});

const router = useRouter();
const route = useRoute();

// 单个居中弹窗 + 两步确认流程
const deleteConfirmVisible = ref(false);
const deleteConfirmStep = ref(0);
const hasAcknowledgedRisk = ref(false);
const confirmationText = ref('');
const userProfileRef = ref<any | null>(null);
const userIdentifier = computed(() => {
  const p = userProfileRef.value;
  return p?.username || p?.email || (p?.uuid ? `UUID: ${p.uuid}` : '当前账户');
});
const userAvatar = computed(() => {
  const p = userProfileRef.value;
  if (!p) return '';
  const isAllEmpty = !p.avatar && !p.avatarBackground && !p.avatarTextColor;
  return p.avatar || (isAllEmpty ? (bgPoster as unknown as string) : '');
});
const userAvatarBg = computed(() => {
  if (userAvatar.value) return 'transparent';
  return userProfileRef.value?.avatarBackground || '#ff4d4f';
});
const userAvatarTextColor = computed(() => {
  return userAvatar.value ? undefined : (userProfileRef.value?.avatarTextColor || '#fff');
});
const canProceedStep0 = computed(() => hasAcknowledgedRisk.value);
const isConfirmInputValid = computed(() => {
  const val = confirmationText.value.trim().toLowerCase();
  return val === '注销' || val === 'delete';
});
const isFinalConfirmChecked = ref(false);
const finalBtnCountdown = ref(0); // 秒
const isFinalActionEnabled = computed(() => isConfirmInputValid.value && isFinalConfirmChecked.value && finalBtnCountdown.value === 0);

let countdownTimer: any = null;
const resetFinalCountdown = () => {
  if (countdownTimer) {
    clearInterval(countdownTimer);
    countdownTimer = null;
  }
  finalBtnCountdown.value = 0;
};

// 当进入第二步且满足输入与勾选条件时，启动倒计时
watch([deleteConfirmStep, isConfirmInputValid, isFinalConfirmChecked], ([step, valid, checked]) => {
  if (step === 1 && valid && checked) {
    if (!countdownTimer) {
      finalBtnCountdown.value = 3;
      countdownTimer = setInterval(() => {
        if (finalBtnCountdown.value <= 1) {
          resetFinalCountdown();
        } else {
          finalBtnCountdown.value -= 1;
        }
      }, 1000);
    }
  } else {
    resetFinalCountdown();
  }
});

// 显示删除确认对话框（单一弹窗，审批式两步）
const showDeleteConfirm = () => {
  deleteConfirmStep.value = 0;
  deleteConfirmVisible.value = true;
  hasAcknowledgedRisk.value = false;
  confirmationText.value = '';
  isFinalConfirmChecked.value = false;
  resetFinalCountdown();
  try {
    const userProfileStr = localStorage.getItem('user-profile');
    userProfileRef.value = userProfileStr ? JSON.parse(userProfileStr) : null;
  } catch (e) {
    userProfileRef.value = null;
  }
};

const handleDeleteConfirmCancel = () => {
  if (deleteConfirmStep.value === 1) {
    deleteConfirmStep.value = 0;
    confirmationText.value = '';
    isFinalConfirmChecked.value = false;
    resetFinalCountdown();
  } else {
    deleteConfirmVisible.value = false;
    deleteConfirmStep.value = 0;
    hasAcknowledgedRisk.value = false;
    confirmationText.value = '';
    isFinalConfirmChecked.value = false;
    resetFinalCountdown();
  }
};

const handleDeleteConfirmNext = () => {
  deleteConfirmStep.value = 1;
};

const handleDeleteConfirmFinal = async () => {
  await handleDeleteAccount();
  deleteConfirmVisible.value = false;
  deleteConfirmStep.value = 0;
  isFinalConfirmChecked.value = false;
  resetFinalCountdown();
};

// 处理账户删除
const handleDeleteAccount = async () => {
  try {
    // 从本地存储获取用户UUID
    const userProfileStr = localStorage.getItem('user-profile');
    if (!userProfileStr) {
      NotificationService.error('用户信息不存在，请重新登录');
      await router.push(ROUTES.LOGIN);
      return;
    }

    const userProfile = JSON.parse(userProfileStr);
    const uuid = userProfile.uuid;

    if (!uuid) {
      NotificationService.error('用户UUID不存在，请重新登录');
      await router.push(ROUTES.LOGIN);
      return;
    }

    // 调用删除账户接口
    const loadingMsg = NotificationService.loading('正在注销账户...', 0);
    
    try {
      await deleteUser({ uuid });
      
      // 关闭加载提示
      NotificationService.close(loadingMsg);
      
      NotificationService.success('账户已成功注销');
      broadcastGlobalLogout('account-deleted');
    } catch (error) {
      // 关闭加载提示
      NotificationService.close(loadingMsg);
      
      console.error('注销账户失败:', error);
      NotificationService.error('注销账户失败，请稍后重试');
      throw error;
    }
  } catch (error) {
    console.error('注销账户失败:', error);
    NotificationService.error('注销账户失败，请稍后重试');
    throw error;
  }
};

// 修改密码
const changePwdVisible = ref(false);
const oldPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const changeLoading = ref(false);
const showOldError = ref(false);
const showNewError = ref(false);
const showConfirmError = ref(false);
const currentUsername = computed(() => {
  try {
    const raw = localStorage.getItem('user-profile');
    const profile = raw ? JSON.parse(raw) : null;
    return String(profile?.username || '').trim();
  } catch {
    return '';
  }
});
const isChangeValid = computed(() => {
  const oldOk = !!oldPassword.value.trim();
  const nextPassword = newPassword.value.trim();
  const newOk =
    isPasswordComplexEnough(nextPassword) &&
    !doesPasswordContainUsername(nextPassword, currentUsername.value) &&
    newPassword.value !== oldPassword.value;
  const confirmOk = confirmPassword.value === newPassword.value && !!confirmPassword.value.trim();
  return oldOk && newOk && confirmOk;
});

const resetChangeForm = () => {
  oldPassword.value = '';
  newPassword.value = '';
  confirmPassword.value = '';
  showOldError.value = false;
  showNewError.value = false;
  showConfirmError.value = false;
};

const showChangePassword = () => {
  resetChangeForm();
  changePwdVisible.value = true;
};

const tryOpenChangePasswordFromRoute = async () => {
  if (route.query.openChangePassword !== '1') {
    return;
  }

  showChangePassword();
  const nextQuery = { ...route.query };
  delete nextQuery.openChangePassword;
  await router.replace({
    path: route.path,
    query: nextQuery
  });
};

const handleChangeCancel = () => {
  changePwdVisible.value = false;
  resetChangeForm();
};

const validateChange = () => {
  showOldError.value = !oldPassword.value.trim();
  const nextPassword = newPassword.value.trim();
  showNewError.value = !(
    isPasswordComplexEnough(nextPassword) &&
    !doesPasswordContainUsername(nextPassword, currentUsername.value) &&
    newPassword.value !== oldPassword.value
  );
  showConfirmError.value = !(confirmPassword.value === newPassword.value && !!confirmPassword.value.trim());
  return !(showOldError.value || showNewError.value || showConfirmError.value);
};

const handleChangeConfirm = async () => {
  const ok = validateChange();
  if (!ok) return;
  const profileStr = localStorage.getItem('user-profile');
  if (!profileStr) {
    NotificationService.error('用户信息不存在，请重新登录');
    await router.push(ROUTES.LOGIN);
    return;
  }
  const profile = JSON.parse(profileStr);
  const uuid = profile?.uuid;
  if (!uuid) {
    NotificationService.error('用户UUID不存在，请重新登录');
    await router.push(ROUTES.LOGIN);
    return;
  }
  changeLoading.value = true;
  const key = NotificationService.loading('正在修改密码...', 0);
  try {
    await changePassword({ uuid, old_password: oldPassword.value, new_password: newPassword.value });
    NotificationService.close(key);
    NotificationService.success('密码修改成功，请重新登录');
    changePwdVisible.value = false;
    resetChangeForm();
    broadcastGlobalLogout('password-changed');
  } catch (e) {
    NotificationService.close(key);
    console.error('修改密码失败:', e);
    NotificationService.error('修改密码失败，请稍后重试');
  } finally {
    changeLoading.value = false;
  }
};

onMounted(() => {
  void tryOpenChangePasswordFromRoute();
});

watch(
  () => route.query.openChangePassword,
  (value) => {
    if (value === '1') {
      void tryOpenChangePasswordFromRoute();
    }
  }
);
</script>

<style scoped>
.security-container {
  padding: 24px 40px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
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
  margin-top: 32px;
}

.setting-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 30px 0;
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

.setting-description {
  font-size: 12px;
  color: #8c8c8c;
  margin-top: 4px;
  margin-bottom: 0;
}

.setting-action {
  margin-left: 16px;
}

.security-content {
  flex: 1;
}

/* Delete Modal Styles */
.delete-modal-body {
  padding: 10px 10px 0;
}

.steps-container {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 10px;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 1;
}

.step-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f0f0f0;
  color: #8c8c8c;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
  transition: all 0.3s;
}

.step-text {
  font-size: 12px;
  color: #8c8c8c;
  transition: all 0.3s;
}

.step-item.active .step-icon {
  background: #ff4d4f;
  color: #fff;
  box-shadow: 0 0 0 4px rgba(255, 77, 79, 0.1);
}

.step-item.active .step-text {
  color: #ff4d4f;
  font-weight: 500;
}

.step-item.completed .step-icon {
  background: #fff;
  border: 1px solid #ff4d4f;
  color: #ff4d4f;
}

.step-item.completed .step-text {
  color: #ff4d4f;
}

.step-line {
  flex: 1;
  height: 1px;
  background: #f0f0f0;
  margin: -20px 10px 0;
  max-width: 60px;
}

.warning-banner {
  background: #fff1f0;
  border: 1px solid #ffccc7;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: flex-start;
  margin-bottom: 15px;
  margin-top: 18px;
}

.warning-icon {
  font-size: 20px;
  color: #ff4d4f;
  margin-top: 2px;
  margin-right: 12px;
}

.warning-text h4 {
  margin: 0 0 4px;
  color: #1f1f1f;
  font-weight: 600;
  font-size: 15px;
}

.warning-text p {
  margin: 0;
  color: #ff4d4f;
  font-size: 13px;
}

/* 统一后的三段式布局样式 */
.consequence-section {
  background: #fcfcfc;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 12px;
}

.consequence-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.consequence-list li {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  color: #595959;
  font-size: 13px;
}

.consequence-list li:last-child {
  margin-bottom: 0;
}

.list-icon {
  margin-right: 10px;
  color: #8c8c8c;
  font-size: 14px;
}

.action-section {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
}

/* Custom Checkbox Styles - Final Polish */
.custom-checkbox-wrapper {
  display: flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
  transition: opacity 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.custom-checkbox-wrapper:hover {
  opacity: 0.9;
}

.custom-checkbox-wrapper:active .custom-checkbox {
  transform: scale(0.9);
}

.custom-checkbox {
  width: 14px;
  height: 14px;
  border: 1.5px solid #d9d9d9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background-color: #fff;
  position: relative;
  box-sizing: border-box;
}

.check-icon {
  width: 8px;
  height: 8px;
  fill: none;
  stroke: #fff;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 16;
  stroke-dashoffset: 16;
  animation: dash 0.3s cubic-bezier(0.65, 0, 0.45, 1) forwards 0.1s;
}

@keyframes dash {
  from { stroke-dashoffset: 16; }
  to { stroke-dashoffset: 0; }
}

/* Hover state for unchecked */
.custom-checkbox-wrapper:hover .custom-checkbox {
  border-color: #ff7875;
  background-color: #fff1f0;
}

/* Checked state */
.custom-checkbox-wrapper.checked .custom-checkbox {
  background-color: #ff4d4f;
  border-color: #ff4d4f;
  box-shadow: 0 0 0 3px rgba(255, 77, 79, 0.1);
  animation: checkboxPop 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

@keyframes checkboxPop {
  0% { transform: scale(0.8); }
  100% { transform: scale(1); }
}

.checkbox-label {
  font-size: 13px;
  color: #666;
  transition: color 0.3s;
}

.custom-checkbox-wrapper.checked .checkbox-label {
  color: #333;
  font-weight: 500;
}

/* Danger Mode Overrides */
.custom-checkbox-wrapper.danger-mode .checkbox-label {
  color: #cf1322;
}

.custom-checkbox-wrapper.danger-mode:hover .custom-checkbox {
  border-color: #ff4d4f;
}

.custom-checkbox-wrapper.danger-mode.checked .custom-checkbox {
  background-color: #f5222d;
  border-color: #f5222d;
  box-shadow: 0 0 0 3px rgba(245, 34, 45, 0.2);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  width: auto;
}

.cancel-btn, .next-btn, .delete-btn {
  min-width: 80px;
  border-radius: 10px;
  height: 34px;
  font-size: 14px;
  font-weight: 400;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
}

.cancel-btn {
  background-color: #f5f5f5;
  border: none;
  color: #595959;
}

.cancel-btn:hover {
  background-color: #e6e6e6;
  color: #262626;
  border-color: none;
}

/* 复选框容器（仅第二步使用） */
.checkbox-wrapper.final-check {
  margin-bottom: 30px;
  padding: 12px;
  background: #fff1f0;
  border: 1px solid #ffa39e;
  border-radius: 6px;
}

.checkbox-wrapper.final-check :deep(.ant-checkbox-wrapper) {
  color: #cf1322;
}

/* Step 2 Redesign */
.step-2-redesign {
  padding: 0 10px;
}

.security-header {
  text-align: center;
  margin-bottom: 12px;
}

.icon-wrapper-pulse {
  width: 56px;
  height: 56px;
  background: #fff1f0;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  position: relative;
}

.icon-wrapper-pulse::after {
  content: '';
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 1px solid #ff4d4f;
  animation: pulse-ring 2s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}

@keyframes pulse-ring {
  0% { transform: scale(0.9); opacity: 1; }
  100% { transform: scale(1.5); opacity: 0; }
}

.confirm-icon-pulse {
  font-size: 28px;
  color: #ff4d4f;
}

.security-header h3 {
  font-size: 18px;
  color: #1f1f1f;
  margin-bottom: 6px;
  font-weight: 600;
}

.subtitle {
  color: #8c8c8c;
  font-size: 13px;
  margin: 0;
}

.account-card {
  background: #f9f9f9;
  border: 1px solid #f0f0f0;
  border-radius: 16px;
  padding: 11px 16px;
  display: flex;
  align-items: center;
  margin-bottom: 18px;
}

.avatar-placeholder {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #ff4d4f;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 600;
  margin-right: 12px;
  flex-shrink: 0;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.account-info {
  display: flex;
  flex-direction: column;
}

.account-info .label {
  font-size: 12px;
  color: #8c8c8c;
  margin-bottom: 2px;
}

.account-info .value {
  font-size: 14px;
  font-weight: 500;
  color: #1f1f1f;
}

.verification-section {
  margin-bottom: 18px;
}

.input-group-row {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #d9d9d9;
  border-radius: 10px;
  padding: 4px 12px;
  transition: all 0.3s;
}

.input-group-row:focus-within {
  border-color: #ff4d4f;
  box-shadow: 0 0 0 2px rgba(255, 77, 79, 0.1);
}

.input-prefix {
  font-size: 13px;
  color: #595959;
  margin-right: 12px;
  white-space: nowrap;
  font-weight: 500;
}

.confirm-input-refined {
  border: none !important;
  box-shadow: none !important;
  padding-left: 0;
  flex: 1;
  font-size: 13px;
}

.confirm-input-refined :deep(input) {
  font-size: 13px !important;
}

.action-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.final-check-inline {
  display: flex;
  align-items: center;
}

.final-check-inline .custom-checkbox-wrapper {
  padding: 5px 12px;
  background: #fff1f0;
  border: 1px solid #ffa39e;
  border-radius: 10px;
  transition: all 0.3s;
}

.final-check-inline .custom-checkbox-wrapper:hover {
  border-color: #ff4d4f;
  background: #fff5f5;
}

.inline-actions {
  display: flex;
  gap: 12px;
}

.form-item { margin-bottom: 16px; }
.form-label { margin-bottom: 8px; font-weight: 500; font-size: 14px; }
.form-label.required::before { content: '*'; color: #ff4d4f; margin-right: 4px; }
.form-error { color: #ff4d4f; font-size: 12px; margin-top: 4px; }

.change-password-btn {
  background: #1677ff;
  color: #ffffff;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 400;
  font-size: 14px;
  border: none;
  cursor: pointer;
  margin-left: 10px;
}

.change-password-btn:hover {
  background-color: #006aff;
}

.delete-account-btn {
  background: #ff4d4f;
  color: #ffffff;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 400;
  font-size: 14px;
  border: none;
  cursor: pointer;
  margin-left: 10px;
}

.delete-account-btn:hover {
  background-color: #e53935;
}

:global(.delete-confirm-modal .ant-modal-content) {
  border-radius: 20px !important;
}

:global(.change-password-modal .ant-modal-content) {
  border-radius: 22px !important;
}

.change-password-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.change-password-action-btn {
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

.change-password-cancel-btn {
  background-color: #f5f5f5;
  border: none;
  color: #1a1a1a;
}

.change-password-cancel-btn:hover {
  background-color: #e6e6e6;
  color: #1a1a1a;
  border-color: none;
}

.change-password-confirm-btn {
  background: #1677ff;
  color: #ffffff;
  border: none;
}

.change-password-confirm-btn:hover {
  background-color: #4096ff;
  color: #ffffff;
}
</style>
