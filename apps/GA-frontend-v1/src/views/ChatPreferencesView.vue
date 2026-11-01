<template>
  <div class="chat-preferences-container">
    <div class="preferences-header">
      <h2>聊天偏好设置</h2>
      <p>自定义您的聊天体验</p>
    </div>
    
    <!-- 偏好设置项 -->
    <a-form layout="vertical" :model="formState" class="preferences-form">
      <div class="preferences-content">
        <!-- 聊天窗口样式移到首位 -->
        <div class="preference-item">
          <div class="preference-info">
            <h3>聊天窗口样式</h3>
            <p>切换聊天视图样式</p>
          </div>
          <a-form-item style="margin: 0;">
            <div class="image-radio-group" >
              <div class="image-radio-item">
                <a-radio value="document" :checked="formState.chatWindowStyle === 'document'" @change="handleChatWindowStyleChange">
                  <div class="image-thumb">
                    <img :src="docsImg" alt="文档模式" />
                  </div>
                </a-radio>
                <div class="image-option-label">文档模式</div>
              </div>
              <div class="image-radio-item">
                <a-radio value="conversation" :checked="formState.chatWindowStyle === 'conversation'" @change="handleChatWindowStyleChange">
                  <div class="image-thumb">
                    <img :src="chatImg" alt="对话模式" />
                  </div>
                </a-radio>
                <div class="image-option-label">对话模式</div>
              </div>
            </div>
          </a-form-item>
        </div>

        <div class="preference-item">
          <div class="preference-info">
            <h3>自动折叠思考过程</h3>
            <p>在助手完成思考过程后自动折叠思考过程面板</p>
          </div>
          <a-form-item style="margin: 0;">
            <a-switch 
              :checked="formState.autoCollapseReasoning" 
              @change="handleAutoCollapseReasoningChange"
            />
          </a-form-item>
        </div>
        <div class="preference-item">
          <div class="preference-info">
            <h3>自动折叠工具调用思考过程</h3>
            <p>在开始调用工具时自动折叠思考过程面板</p>
          </div>
          <a-form-item style="margin: 0;">
            <a-switch 
              :checked="formState.autoCollapseToolPanels" 
              @change="handleAutoCollapseToolPanelsChange"
            />
          </a-form-item>
        </div>
        <div class="preference-item">
          <div class="preference-info">
            <h3>自动折叠工具调用参数与结果面板</h3>
            <p>在调用结果完成后自动折叠工具的参数与执行结果面板</p>
          </div>
          <a-form-item style="margin: 0;">
            <a-switch 
              :checked="formState.autoCollapseToolDetailsOnComplete" 
              @change="handleAutoCollapseToolDetailsOnCompleteChange"
            />
          </a-form-item>
        </div>
        <div class="preference-item">
          <div class="preference-info">
            <h3>用户消息使用 Markdown 渲染</h3>
            <p>启用后，您的消息以 Markdown 格式显示，关闭则为纯文本</p>
          </div>
          <a-form-item style="margin: 0;">
            <a-switch 
              :checked="formState.renderUserMessageMarkdown" 
              @change="handleRenderUserMessageMarkdownChange"
            />
          </a-form-item>
        </div>
      </div>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive } from 'vue';
import { Modal } from 'ant-design-vue';
import StorageService from '@/utils/StorageService';
import { getUserPreferences, updateUserPreferences } from '@/services/aiUserPreferences';
import { useChatStore } from '@/stores/chat-store';
import chatImg from '@/assets/image/webp/chatmode_chat_light.webp';
import docsImg from '@/assets/image/webp/chatmode_docs_light.webp';

// 定义组件名
defineOptions({
  name: 'ChatPreferencesView'
});

// 获取聊天store实例
const chatStore = useChatStore();

// 定义用户偏好设置存储键
const USER_PREFERENCES_KEY = 'mcp-user-preferences';

// 优先在组件创建时就从本地存储初始化，避免刷新后单选框闪切
interface UserPreferences {
  autoCollapseReasoning?: boolean;
  autoCollapseToolPanels?: boolean;
  autoCollapseToolDetailsOnComplete?: boolean;
  renderUserMessageMarkdown?: boolean;
  chatWindowStyle?: 'document' | 'conversation';
}

const initialPreferences = ((): UserPreferences => {
  try {
    return StorageService.get<UserPreferences>(USER_PREFERENCES_KEY) || {};
  } catch {
    return {};
  }
})();

// 表单状态（同步初始值，确保首次渲染即为用户选择的样式）
const formState = reactive({
  autoCollapseReasoning: initialPreferences.autoCollapseReasoning ?? false,
  autoCollapseToolPanels: initialPreferences.autoCollapseToolPanels ?? false,
  autoCollapseToolDetailsOnComplete: initialPreferences.autoCollapseToolDetailsOnComplete ?? false,
  renderUserMessageMarkdown: initialPreferences.renderUserMessageMarkdown ?? true,
  chatWindowStyle: initialPreferences.chatWindowStyle ?? 'conversation'
});

// 显示确认对话框（仅当存在历史消息时显示）
const showConfirmDialog = (callback: () => void) => {
  const count = Array.isArray((chatStore as any).messages)
    ? (chatStore as any).messages.length
    : (((chatStore as any).messages?.value?.length) ?? 0);

  if (count <= 0) {
    chatStore.clearChat();
    window.dispatchEvent(new CustomEvent('clear-canvas'));
    callback();
    return;
  }

  Modal.confirm({
    title: '确认更改设置',
    content: '更改此设置将会清空当前对话内容，是否继续？',
    okText: '确认',
    cancelText: '取消',
    centered: true,
    class: 'chat-preferences-confirm',
    onOk: () => {
      chatStore.clearChat();
      window.dispatchEvent(new CustomEvent('clear-canvas'));
      callback();
    }
  });
};

// 处理开关状态变化（思考过程）
const handleAutoCollapseReasoningChange = (checked: boolean | string | number) => {
  showConfirmDialog(() => {
    // 更新表单状态
    formState.autoCollapseReasoning = !!checked;
    // 保存设置到本地存储
    saveUserPreferences({ autoCollapseReasoning: !!checked });
  });
};

// 处理开关状态变化（工具调用思考过程面板）
const handleAutoCollapseToolPanelsChange = (checked: boolean | string | number) => {
  showConfirmDialog(() => {
    // 更新表单状态
    formState.autoCollapseToolPanels = !!checked;
    saveUserPreferences({ autoCollapseToolPanels: !!checked });
  });
};

// 处理开关状态变化（工具参数与结果面板完成后自动折叠）
const handleAutoCollapseToolDetailsOnCompleteChange = (checked: boolean | string | number) => {
  showConfirmDialog(() => {
    // 更新表单状态
    formState.autoCollapseToolDetailsOnComplete = !!checked;
    saveUserPreferences({ autoCollapseToolDetailsOnComplete: !!checked });
  });
};

// 处理开关状态变化（用户消息Markdown渲染）
const handleRenderUserMessageMarkdownChange = (checked: boolean | string | number) => {
  formState.renderUserMessageMarkdown = !!checked;
  saveUserPreferences({ renderUserMessageMarkdown: !!checked });
};

// 处理聊天窗口样式变化
const handleChatWindowStyleChange = (e: any) => {
  const value = e?.target?.value ?? e;
  const nextValue = value === 'conversation' ? 'conversation' : 'document';
  formState.chatWindowStyle = nextValue as 'document' | 'conversation';
  saveUserPreferences({ chatWindowStyle: nextValue as 'document' | 'conversation' });
};

// 定义用户偏好设置类型（已上移）

// 保存用户偏好设置到本地存储
const saveUserPreferences = async (preferences: Partial<UserPreferences>) => {
  try {
    const raw = localStorage.getItem('user-profile');
    const userId = raw ? (JSON.parse(raw).uuid || '') : '';
    if (!userId) return;
    const defaultPrefs = {
      autoCollapseReasoning: false,
      autoCollapseToolPanels: false,
      autoCollapseToolDetailsOnComplete: true,
      renderUserMessageMarkdown: true,
      chatWindowStyle: 'conversation'
    } as UserPreferences;
    const existingPreferences = (StorageService.get(USER_PREFERENCES_KEY) || {}) as UserPreferences;
    const base = { ...defaultPrefs, ...existingPreferences } as UserPreferences;
    const next = { ...base, ...preferences } as UserPreferences;
    await updateUserPreferences({ userId, preferences: next });
    const res = await getUserPreferences();
    const serverPrefs = ((res?.data?.preferences) || {}) as Partial<UserPreferences>;
    const merged = { ...base, ...serverPrefs } as UserPreferences;
    localStorage.setItem(USER_PREFERENCES_KEY, JSON.stringify(merged));
    formState.autoCollapseReasoning = !!merged.autoCollapseReasoning;
    formState.autoCollapseToolPanels = !!merged.autoCollapseToolPanels;
    formState.autoCollapseToolDetailsOnComplete = !!merged.autoCollapseToolDetailsOnComplete;
    formState.renderUserMessageMarkdown = !!merged.renderUserMessageMarkdown;
    formState.chatWindowStyle = (merged.chatWindowStyle === 'document' ? 'document' : 'conversation');
    window.dispatchEvent(new CustomEvent('user-preferences-changed', { detail: { preference: 'all', value: merged } }));
  } catch (error) {
  }
};

// 从服务器和本地存储加载用户偏好设置
const loadUserPreferences = async () => {
  try {
    // 先从服务器获取最新偏好
    const res = await getUserPreferences();
    const serverPrefs = ((res?.data?.preferences) || {}) as Partial<UserPreferences>;
    const localPrefs = StorageService.get<UserPreferences>(USER_PREFERENCES_KEY) || {};
    // 合并：服务器数据优先覆盖本地缓存
    const merged = { ...localPrefs, ...serverPrefs } as UserPreferences;

    // 更新本地存储
    localStorage.setItem(USER_PREFERENCES_KEY, JSON.stringify(merged));

    // 更新表单状态
    formState.autoCollapseReasoning = merged.autoCollapseReasoning ?? false;
    formState.autoCollapseToolPanels = merged.autoCollapseToolPanels ?? false;
    formState.autoCollapseToolDetailsOnComplete = merged.autoCollapseToolDetailsOnComplete ?? false;
    formState.renderUserMessageMarkdown = merged.renderUserMessageMarkdown ?? true;
    formState.chatWindowStyle = merged.chatWindowStyle ?? 'conversation';
  } catch (error) {
    console.error('从服务器加载用户偏好设置失败，回退到本地存储:', error);
    // API 失败时，回退到本地存储
    const preferences = StorageService.get<UserPreferences>(USER_PREFERENCES_KEY) || {};
    formState.autoCollapseReasoning = preferences.autoCollapseReasoning ?? false;
    formState.autoCollapseToolPanels = preferences.autoCollapseToolPanels ?? false;
    formState.autoCollapseToolDetailsOnComplete = preferences.autoCollapseToolDetailsOnComplete ?? false;
    formState.renderUserMessageMarkdown = preferences.renderUserMessageMarkdown ?? true;
    formState.chatWindowStyle = preferences.chatWindowStyle ?? 'conversation';
  }
};

onMounted(() => {
  loadUserPreferences();
});
</script>

<style scoped>
.chat-preferences-container {
  padding: 24px 30px;
  height: 100%;
  overflow-y: auto;
}

.preferences-header {
  margin-bottom: 24px;
}

.preferences-header h2 {
  margin-bottom: 8px;
  color: #1d1d1d;
  font-size: 18px;
  font-weight: 600;
}

.preferences-header p {
  color: #8c8c8c;
  font-size: 13px;
}

.preferences-content {
  border-bottom: 1px solid #f0f0f0;
}

.preference-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  border-bottom: 1px solid #f0f0f0;
}

.preference-item:last-child {
  border-bottom: none;
}

.preference-info h3 {
  margin: 0 0 4px 0;
  color: #1d1d1d;
  font-size: 14px;
  font-weight: 500;
}

.preference-info p {
  margin: 0;
  color: #8c8c8c;
  font-size: 12px;
}

:deep(.preferences-form .ant-form-item) {
  margin-bottom: 0;
}

.preference-item :deep(.ant-form-item) {
  margin-bottom: 0;
  display: flex;
  align-items: center;
}

.preference-item :deep(.ant-form-item .ant-form-item-control) {
  display: flex;
  align-items: center;
}

.preference-item :deep(.ant-form-item .ant-form-item-control-input) {
  min-height: 0;
}

.image-radio-group {
  display: flex;
  gap: 16px;
}

.image-radio-item {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.image-radio-item :deep(.ant-radio) {
  display: none;
}

.image-radio-item :deep(.ant-radio-wrapper) {
  padding: 8px;
  border: 1px solid #e5e5e5;
  border-radius: 16px;
  transition: all 0.2s ease;
  display: inline-flex;
}

.image-radio-item :deep(.ant-radio-wrapper:hover) {
  border-color: #69b1ff;
}

.image-radio-item :deep(.ant-radio-wrapper-checked) {
  border-color: #69b1ff;
  box-shadow: 0 5px 10px rgba(22, 119, 255, 0.12);
  background-color: #e6f4ff;
}

.image-radio-item img {
  width: 100%;
  height: 100%;
  display: block;
}

.image-option-label {
  margin-top: 8px;
  font-size: 12px;
  color: #595959;
}

.image-thumb {
  --thumb-width: 120px;
  --thumb-scale: 1.2;
  width: var(--thumb-width);
  height: calc(var(--thumb-width) * 0.625);
  overflow: hidden;
  border-radius: 6px;
}

.image-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transform: scale(var(--thumb-scale));
  transform-origin: center center;
}
</style>

<style>
.chat-preferences-confirm .ant-modal-confirm-btns {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.chat-preferences-confirm .ant-modal-confirm-btns .ant-btn {
  min-width: 75px;
  border-radius: 10px;
  height: 32px;
  font-size: 13px;
  font-weight: 400;
  padding: 0 20px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  cursor: pointer;
  transition: all 0.3s;
}

.chat-preferences-confirm .ant-modal-confirm-btns .ant-btn-default {
  background-color: #f5f5f5;
  border: none;
  color: #1a1a1a;
}

.chat-preferences-confirm .ant-modal-confirm-btns .ant-btn-default:hover {
  background-color: #e6e6e6;
  color: #1a1a1a;
  border-color: none;
}

.chat-preferences-confirm .ant-modal-confirm-btns .ant-btn-primary {
  background: #1677ff;
  color: #ffffff;
  border: none;
}

.chat-preferences-confirm .ant-modal-confirm-btns .ant-btn-primary:hover {
  background-color: #4096ff;
  color: #ffffff;
}

.chat-preferences-confirm .ant-modal-content {
  border-radius: 18px;
}
</style>
