<template>
  <div class="auth-wrapper">
    <video class="background-video" autoplay muted loop playsinline :poster="bgPoster">
      <source :src="bgVideo" type="video/mp4"/>
    </video>
    <div class="auth-page auth-login">
      <div class="brand">
        <img :src="logoPng" alt="logo" class="welcome-logo-img" :class="{ loaded: imageLoaded }"/>
        <span class="logo-text" :class="{ loaded: imageLoaded }">{{ systemName }}</span>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h1>欢迎回来</h1>
          <p>请输入用户名、密码和验证码登录到您的账户</p>
        </div>

        <a-form :model="loginForm" :rules="rules" layout="vertical" @finish="onSubmit">
          <a-form-item name="username" label="用户名">
            <a-input v-model:value="loginForm.username" placeholder="请输入用户名" autocomplete="username"/>
          </a-form-item>

          <a-form-item name="password" label="密码">
            <a-input-password v-model:value="loginForm.password" placeholder="请输入密码" autocomplete="current-password"/>
          </a-form-item>

          <a-form-item name="captchaCode" label="验证码" class="captcha-form-item">
            <div class="captcha-row">
              <div class="captcha-input-wrap">
                <a-input
                  v-model:value="loginForm.captchaCode"
                  placeholder="请输入验证码"
                  autocomplete="off"
                />
              </div>
              <div class="captcha-actions">
                <button
                  type="button"
                  class="captcha-trigger"
                  :disabled="captchaLoading"
                  @click="openCaptchaPreview"
                >
                  <img v-if="captchaImage" :src="captchaImage" alt="验证码图片" class="captcha-image"/>
                  <span v-else class="captcha-placeholder">{{ captchaLoading ? '加载中...' : '获取验证码' }}</span>
                  <span class="captcha-zoom-hint" aria-hidden="true">
                    <ZoomInOutlined />
                  </span>
                </button>
                <button
                  type="button"
                  class="captcha-refresh-btn"
                  :disabled="captchaLoading"
                  @click="refreshCaptcha()"
                >
                  <ReloadOutlined />
                </button>
              </div>
            </div>
            <div class="captcha-tip-row">
              <div class="captcha-tip">若您看不清，可点击图片放大查看</div>
            </div>
          </a-form-item>

          <div class="panel-actions">
            <a-checkbox v-model:checked="loginForm.remember">保持登录</a-checkbox>
            <a-button type="link" style="padding: 4px 0 !important;" disabled>忘记密码？</a-button>
          </div>

          <a-button type="primary" block :loading="submitting" html-type="submit">登录</a-button>

          <div class="switch-link">
            <span>还没有账户？</span>
            <a-button type="link" class="switch-link-btn" @click="goRegister">立即注册</a-button>
          </div>
        </a-form>
      </div>
      
      <Teleport to="body">
        <Transition name="captcha-preview-fade">
          <div
            v-if="captchaPreviewOpen"
            class="captcha-preview-mask"
            @click.self="captchaPreviewOpen = false"
          >
            <div class="captcha-preview-card" role="dialog" aria-modal="true" aria-label="图片验证码">
              <div class="captcha-preview-header">
                <div>
                  <div class="captcha-preview-title">图片验证码</div>
                  <div class="captcha-preview-subtitle">请核对字符后点击确认继续登录</div>
                </div>
                <button
                  type="button"
                  class="captcha-preview-close"
                  @click="captchaPreviewOpen = false"
                >
                  <CloseOutlined />
                </button>
              </div>
              <div class="captcha-preview-body">
                <div class="captcha-preview-frame">
                  <img
                    v-if="captchaImage"
                    :src="captchaImage"
                    alt="放大后的验证码图片"
                    class="captcha-preview-image"
                  />
                  <div v-else class="captcha-preview-placeholder">
                    {{ captchaLoading ? '验证码加载中...' : '暂无验证码，请刷新后重试' }}
                  </div>
                </div>

                <div class="captcha-preview-input-wrap">
                  <a-input
                    id="captcha-preview-input"
                    v-model:value="loginForm.captchaCode"
                    size="large"
                    placeholder="请输入验证码"
                    autocomplete="off"
                    class="captcha-preview-input"
                  />
                </div>

                <div class="captcha-preview-meta">
                  <span>请按照图中的字符顺序输入</span>
                  <span>若仍看不清，可直接换一张</span>
                </div>
              </div>
              <div class="captcha-preview-actions">
                <a-button
                  class="captcha-modal-btn captcha-modal-cancel-btn"
                  :loading="captchaLoading"
                  @click="refreshCaptcha()"
                >
                  更换
                </a-button>
                <a-button
                  class="captcha-modal-btn captcha-modal-confirm-btn"
                  @click="captchaPreviewOpen = false"
                >
                  确认
                </a-button>
              </div>
            </div>
          </div>
        </Transition>
      </Teleport>

      <!-- 版权信息 -->
      <div v-if="copyrightText" class="auth-copyright">
        Copyright
        <CopyrightCircleOutlined/>
        {{ copyrightText }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {ref, onMounted, computed, h} from 'vue';
import {useRouter} from 'vue-router';
import logoPng from '@/assets/ga-logo.svg';
import NotificationService from '@/utils/NotificationService';
import StorageService from '@/utils/StorageService';
import { getPrompt } from '@/services/aiPrompt';
import { getCaptcha, login } from '@/services/aiUser';
import { listPlatformModels } from '@/services/aiPlatformModel';
import { listMcpServers } from '@/services/mcpServer';
import { listAiAgents } from '@/services/aiAgent';
import {ROUTES, STORAGE_KEYS} from '@/config/constants';
import { Button, notification } from 'ant-design-vue';
import bgVideo from '@/assets/video/mp4/background.mp4';
import bgPoster from '@/assets/image/jpg/background.jpg';
import {CloseOutlined, CopyrightCircleOutlined, ReloadOutlined, ZoomInOutlined} from '@ant-design/icons-vue';
import { getCopyright, getSystemName } from '@/utils/RuntimeConfig';

const router = useRouter();

const imageLoaded = ref(false);
const captchaLoading = ref(false);
const captchaImage = ref('');
const captchaPreviewOpen = ref(false);

const PASSWORD_EXPIRED_NOTIFICATION_KEY = 'password-expired-warning';

const showPasswordExpiredNotification = () => {
  notification.warning({
    key: PASSWORD_EXPIRED_NOTIFICATION_KEY,
    message: '密码更新提醒',
    description: '为保障您的账户安全，当前密码已超过90天未更新。建议您前往账户安全中心完成密码修改。',
    duration: 0,
    btn: () =>
      h(
        Button,
        {
          type: 'primary',
          size: 'small',
          onClick: async () => {
            notification.close(PASSWORD_EXPIRED_NOTIFICATION_KEY);
            await router.push({
              path: `${ROUTES.ACCOUNT}/security`,
              query: { openChangePassword: '1' }
            });
          }
        },
        { default: () => '立即修改' }
      )
  });
};

onMounted(() => {
  const img = new Image();
  img.src = logoPng as unknown as string;
  img.onload = () => (imageLoaded.value = true);
  void refreshCaptcha();
});

const submitting = ref(false);
const loginForm = ref({
  username: '',
  password: '',
  captchaId: '',
  captchaCode: '',
  remember: true // 默认勾选保持登录
});

const rules = {
  username: [
    {required: true, message: '请输入用户名'},
    {
      trigger: 'blur'
    }
  ],
  password: [
    {required: true, message: '请输入密码'},
    {
      trigger: 'blur'
    }
  ],
  captchaCode: [
    {required: true, message: '请输入验证码'},
    {
      trigger: 'blur'
    }
  ]
};

async function refreshCaptcha(silent = false) {
  try {
    captchaLoading.value = true;
    const captcha = await getCaptcha();
    if (!captcha?.captchaId || !captcha?.captchaImage) {
      throw new Error('验证码数据不完整');
    }
    loginForm.value.captchaId = captcha.captchaId;
    loginForm.value.captchaCode = '';
    captchaImage.value = captcha.captchaImage;
  } catch (error) {
    loginForm.value.captchaId = '';
    captchaImage.value = '';
    if (!silent) {
      NotificationService.warning('验证码加载失败，请点击图片重试');
    }
  } finally {
    captchaLoading.value = false;
  }
}

async function openCaptchaPreview() {
  if (!captchaImage.value && !captchaLoading.value) {
    await refreshCaptcha(true);
  }
  if (captchaImage.value) {
    captchaPreviewOpen.value = true;
  }
}

async function onSubmit() {
  try {
    submitting.value = true;
    if (!loginForm.value.captchaId) {
      await refreshCaptcha();
      return;
    }
    const payload = {
      username: loginForm.value.username.trim(),
      password: loginForm.value.password,
      captchaId: loginForm.value.captchaId,
      captchaCode: loginForm.value.captchaCode.trim()
    };

    // 使用运行时基础地址，调用后端登录接口
    const res = await login(payload);
    const loginData = (res as any)?.data ?? res;
    const needUpdateMsg = !!(
      loginData?.needUpdateMsg
      ?? loginData?.user?.needUpdateMsg
      ?? (res as any)?.needUpdateMsg
      ?? (res as any)?.user?.needUpdateMsg
    );
    const passwordExpiredWarning = !!(
      loginData?.passwordExpiredWarning
      ?? loginData?.user?.passwordExpiredWarning
      ?? (res as any)?.passwordExpiredWarning
      ?? (res as any)?.user?.passwordExpiredWarning
    );

    NotificationService.success('登录成功');

    // 可根据后端实际返回存储 token / 用户信息
    const accessToken = loginData?.token ?? loginData?.accessToken ?? (res as any)?.token;
    if (accessToken) {
      // 根据用户选择写入（未勾选仅写入会话，勾选则同时持久化）
      StorageService.setAccessToken(accessToken, !!loginForm.value.remember);
    }

    // 使用接口返回的用户信息直接填充运行态与本地存储（不做硬编码默认图）
    const userData = loginData?.user ?? (res as any)?.user;
    if (userData) {
      const additionalInfo = userData.additional_info && typeof userData.additional_info === 'object'
        ? userData.additional_info
        : {};
      const userProfile = {
        username: userData.username || '',
        email: userData.email || '',
        avatar: userData.avatar ?? additionalInfo.avatar ?? '',
        avatarBackground: userData.avatarBackground ?? additionalInfo.avatarBackground ?? '',
        avatarTextColor: userData.avatarTextColor ?? additionalInfo.avatarTextColor ?? '',
        uuid: userData.uuid || '',
        realname: userData.realname || '',
        contact: userData.contact || '',
        address: userData.address || ''
      };
      localStorage.setItem('user-profile', JSON.stringify(userProfile));
      // 通知其他组件刷新用户信息
      window.dispatchEvent(new CustomEvent('user-info-updated'));
    }

    localStorage.setItem(STORAGE_KEYS.NEED_UPDATE_MSG, JSON.stringify(needUpdateMsg));

    try {
      const list = await getPrompt();
      const first = list[0] || '';
      if (first.trim()) {
        StorageService.setSystemMessage(first.trim());
      }
    } catch (_) {}

    const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
    const fetchAndPopulateModels = async () => {
      try {
        const arr = await listPlatformModels();
        const providers = arr.map((item: any) => ({
          name: item.name,
          iconClass: 'custom',
          iconText: (item.name || 'P').charAt(0).toUpperCase(),
          avatar: item.avatar?.url || '',
          backgroundColor: item.backgroundColor || undefined,
          providerIcon: item.providerIcon
        }));
        const modelsMap: Record<string, any> = {};
        arr.forEach((item: any) => {
          const groupsRecord: Record<string, any> = {};
          (item.models || []).forEach((g: any) => {
            groupsRecord[g.id] = {
              id: g.id,
              name: g.name || g.id,
              models: (g.models || []).map((m: any) => ({ id: m.id, name: m.name || m.id, iconText: m.iconText || (m.name || 'M').charAt(0).toUpperCase(), types: m.types || [] }))
            };
          });
          modelsMap[item.name] = {
            apiKey: item.credentials?.apiKey || (item.noApiKeyRequired ? 'sk-no-key' : ''),
            apiUrl: sanitizeUrl(item.connection?.apiBaseUrl),
            models: groupsRecord,
            avatar: item.avatar?.url || '',
            backgroundColor: item.backgroundColor || undefined,
            noApiKeyRequired: !!item.noApiKeyRequired,
            providerIcon: item.providerIcon,
            type: item.type || 'OpenAI'
          };
        });
        localStorage.setItem('mcp-providers', JSON.stringify(providers));
        localStorage.setItem('mcp-models', JSON.stringify(modelsMap));
        return arr.length;
      } catch (e) {
        return 0;
      }
    };

    const fetchAndPopulateMcpServers = async () => {
      try {
        const res = await listMcpServers();
        const arr: any[] = Array.isArray(res?.data) ? res.data : [];
        const serversList = arr.map((item: any) => ({ id: item.id, name: item.name }));
        const serversData: Record<string, any> = {};
        const normalizeHeaders = (headers: unknown) => Array.isArray(headers)
          ? headers.filter((h: any) => h && typeof h.key === 'string' && typeof h.value === 'string')
          : (headers && typeof headers === 'object'
            ? Object.entries(headers as Record<string, unknown>)
              .filter(([key, value]) => key.trim().length > 0 && typeof value === 'string')
              .map(([key, value]) => ({ key: key.trim(), value: value as string }))
            : []);
        arr.forEach((item: any) => {
          serversData[item.id] = {
            id: item.id,
            uuid: item.uuid,
            name: item.name || '',
            description: item.description || '',
            type: item.type || 'sse',
            url: sanitizeUrl(item.url || ''),
            timeout: typeof item.timeout === 'number' ? item.timeout : 60,
            headers: normalizeHeaders(item.headers),
            tools: Array.isArray(item.tools) ? item.tools.map((t: any) => ({ id: t.id, name: t.name, description: t.description || '' })) : []
          };
        });
        localStorage.setItem('mcp-servers-list', JSON.stringify(serversList));
        localStorage.setItem('mcp-servers-data', JSON.stringify(serversData));
        document.dispatchEvent(new CustomEvent('mcp-server-config-changed'));
      } catch (e) {}
    };

    const fetchAndPopulateAgents = async () => {
      try {
        const res = await listAiAgents();
        const arr: any[] = Array.isArray(res?.data) ? res.data : [];
        const mapped = arr.map((item: any) => {
          const m = item.config?.model || {};
          const basicConfig = {
            ...(item.config?.basic || {}),
            type: item.config?.basic?.type || item.agent_type || 'assistant',
            visibility: item.config?.basic?.visibility || item.visibility || 'private'
          };
          const skills = Array.isArray(item.skills) ? item.skills : (Array.isArray(item.config?.skills) ? item.config.skills : []);
          const normalizedModel = {
            service: m.service,
            name: m.name,
            temperature: typeof m.temperature === 'number' ? m.temperature : 0.7,
            top_p: typeof m.topP === 'number' ? m.topP : (typeof m.top_p === 'number' ? m.top_p : 1.0),
            presence_penalty: typeof m.presencePenalty === 'number' ? m.presencePenalty : (typeof m.presence_penalty === 'number' ? m.presence_penalty : 0),
            frequency_penalty: typeof m.frequencyPenalty === 'number' ? m.frequencyPenalty : (typeof m.frequency_penalty === 'number' ? m.frequency_penalty : 0),
            apiKey: m.apiKey,
            apiUrl: sanitizeUrl(m.apiUrl)
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
      } catch (e) {}
    };

    await fetchAndPopulateModels();
    await fetchAndPopulateMcpServers();
    await fetchAndPopulateAgents();
    if (needUpdateMsg) {
      await router.push(ROUTES.WELCOME);
    } else {
      await router.push(ROUTES.CHAT);
    }
    if (passwordExpiredWarning) {
      showPasswordExpiredNotification();
    }
  } catch (e: any) {
    console.error('登录失败:', e);
    await refreshCaptcha(true);
  } finally {
    submitting.value = false;
  }
}

function goRegister() {
  router.push(ROUTES.REGISTER);
}

// 计算属性获取系统名称
const systemName = computed(() => {
  return getSystemName();
});

// 计算属性获取copyright文本
const copyrightText = computed(() => {
  return getCopyright();
});
</script>

<style scoped>
@import '@/assets/styles/auth-pages.css';

.panel {
  max-width: 456px;
}

.panel-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.captcha-row {
  display: flex;
  align-items: stretch;
  gap: 12px;
}

.captcha-actions {
  display: flex;
  align-items: stretch;
  gap: 8px;
}

.captcha-input-wrap {
  flex: 1;
  min-width: 0;
}

.captcha-trigger {
  width: 110px;
  min-width: 110px;
  height: 32px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: #fff;
  overflow: hidden;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
  position: relative;
  isolation: isolate;
}

.captcha-trigger:hover:not(:disabled) {
  border-color: #4096ff;
  box-shadow: 0 0 0 2px rgba(5, 145, 255, 0.1);
}

.captcha-trigger:disabled {
  cursor: wait;
  background: #fafafa;
}

.captcha-image,
.captcha-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.captcha-image {
  object-fit: contain;
}

.captcha-zoom-hint {
  position: absolute;
  inset: 0;
  border-radius: 0;
  background: rgba(17, 24, 39, 0.32);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
  z-index: 1;
  border: none;
}

.captcha-trigger:hover:not(:disabled) .captcha-zoom-hint {
  opacity: 1;
}

.captcha-zoom-hint :deep(svg) {
  font-size: 15px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.24));
}

.captcha-refresh-btn {
  width: 32px;
  min-width: 32px;
  height: 32px;
  padding: 0;
  border: transparent;
  border-radius: 8px;
  background: #f8fafc;
  color: #475467;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.captcha-refresh-btn:hover:not(:disabled) {
  background: #eeeeee;
  color: #344054;
}

.captcha-refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.captcha-refresh-btn :deep(svg) {
  font-size: 14px;
}

.captcha-placeholder {
  color: #667085;
  font-size: 13px;
}

.captcha-tip {
  margin-top: 8px;
  font-weight: 400;
  color: #8a8a8a;
  font-size: 12px;
  line-height: 1.4;
}

.captcha-tip-row {
  display: flex;
  justify-content: flex-end;
}

.captcha-row :deep(.ant-input) {
  height: 32px;
}

.captcha-preview-fade-enter-active,
.captcha-preview-fade-leave-active {
  transition: opacity 0.22s ease;
}

.captcha-preview-fade-enter-from,
.captcha-preview-fade-leave-to {
  opacity: 0;
}

.captcha-preview-fade-enter-active .captcha-preview-card,
.captcha-preview-fade-leave-active .captcha-preview-card {
  transition:
    transform 0.26s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.22s ease,
    filter 0.26s cubic-bezier(0.22, 1, 0.36, 1);
}

.captcha-preview-fade-enter-from .captcha-preview-card {
  opacity: 0;
  transform: translateY(8px) scale(0.988);
  filter: blur(6px);
}

.captcha-preview-fade-leave-to .captcha-preview-card {
  opacity: 0;
  transform: translateY(6px) scale(0.992);
  filter: blur(3px);
}

.captcha-preview-mask {
  position: fixed;
  inset: 0;
  z-index: 1200;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.42);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

.captcha-preview-card {
  width: min(92vw, 445px);
  border-radius: 18px;
  padding: 18px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(226, 232, 240, 0.95);
  box-shadow: 0 20px 48px rgba(15, 23, 42, 0.16);
  transform-origin: center center;
  filter: blur(0);
  will-change: transform, opacity, filter;
}

.captcha-preview-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.captcha-preview-title {
  color: #101828;
  font-size: 16px;
  font-weight: 500;
  line-height: 1.4;
  letter-spacing: 0.01em;
}

.captcha-preview-subtitle {
  margin-top: 4px;
  color: #667085;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
}

.captcha-preview-close {
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  background: rgba(248, 250, 252, 0.92);
  color: #475467;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.captcha-preview-close:hover {
  color: #101828;
  background: #fff;
}

.captcha-preview-body {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.captcha-preview-frame {
  border-radius: 18px;
  padding: 16px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.96) 0%, rgba(255, 255, 255, 0.96) 100%);
  border: 1px solid rgba(226, 232, 240, 0.9);
  display: flex;
  align-items: center;
  justify-content: center;
}

.captcha-preview-image {
  display: block;
  width: 100%;
  max-width: 100%;
  height: auto;
  object-fit: contain;
  image-rendering: auto;
  filter: drop-shadow(0 10px 24px rgba(15, 23, 42, 0.12));
  border-radius: 16px;
}

.captcha-preview-placeholder {
  color: #667085;
  font-size: 13px;
  font-weight: 400;
  text-align: center;
  line-height: 1.6;
}

.captcha-preview-meta {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  color: #667085;
  font-size: 12px;
  font-weight: 400;
  line-height: 1.5;
}

.captcha-preview-input-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 2px;
}

.captcha-preview-input :deep(.ant-input) {
  height: 40px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.92);
  border-color: #d0d5dd;
  font-size: 13px;
  font-weight: 400;
  color: #344054;
}

.captcha-preview-input :deep(.ant-input:focus),
.captcha-preview-input :deep(.ant-input-focused) {
  border-color: #4096ff;
  box-shadow: 0 0 0 2px rgba(5, 145, 255, 0.12);
}

.captcha-preview-input :deep(.ant-input::placeholder) {
  color: #98a2b3;
  font-weight: 400;
}

.captcha-preview-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 16px;
}

.captcha-modal-btn {
  min-width: 75px;
  height: 32px;
  padding: 0 20px;
  border: none;
  border-radius: 10px;
  box-shadow: none;
  font-size: 13px;
  font-weight: 400;
  transition: all 0.3s;
}

.captcha-modal-cancel-btn {
  background-color: #ebebeb;
  color: #1a1a1a;
}

.captcha-modal-cancel-btn:hover {
  background-color: #d3d3d3 !important;
  color: #1a1a1a !important;
}

.captcha-modal-confirm-btn {
  background: #1677ff;
  color: #ffffff;
}

.captcha-modal-confirm-btn:hover {
  background-color: #4096ff !important;
  color: #ffffff !important;
}

.captcha-modal-confirm-btn:disabled,
.captcha-modal-confirm-btn[disabled] {
  background: #1677ff;
  color: #ffffff;
  opacity: 0.7;
}

@media (max-width: 640px) {
  .captcha-row {
    gap: 10px;
  }

  .captcha-trigger {
    width: 92px;
    min-width: 92px;
  }

  .captcha-preview-card {
    padding: 18px;
  }

  .captcha-preview-meta {
    flex-direction: column;
  }
}

:deep(.auth-login .ant-form-item) {
  margin-bottom: 20px;
}

.captcha-form-item :deep(.ant-form-item-explain),
.captcha-form-item :deep(.ant-form-item-extra) {
  display: none;
}

.captcha-form-item {
  margin-bottom: 3px !important;
}
</style>
