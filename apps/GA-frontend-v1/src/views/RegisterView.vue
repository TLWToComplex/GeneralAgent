<template>
  <div class="auth-wrapper">
    <video class="background-video" autoplay muted loop playsinline :poster="bgPoster">
      <source :src="bgVideo" type="video/mp4"/>
    </video>
    <div class="auth-page auth-register">
      <div class="brand">
        <img :src="logoPng" alt="logo" class="welcome-logo-img" :class="{ loaded: imageLoaded }"/>
        <span class="logo-text" :class="{ loaded: imageLoaded }">{{ systemName }}</span>
      </div>

      <div class="panel">
        <div class="panel-header">
          <h1>创建账户</h1>
          <p>构建属于您的智能体应用</p>
        </div>

        <a-form :model="form" :rules="rules" layout="vertical" @finish="onSubmit">
          <a-form-item name="username" label="用户名">
            <a-input v-model:value="form.username" placeholder="请输入用户名" allow-clear autocomplete="username"/>
          </a-form-item>

          <a-form-item name="email" label="邮箱">
            <a-input v-model:value="form.email" placeholder="请输入邮箱地址" allow-clear autocomplete="email"/>
          </a-form-item>

          <a-form-item name="password" label="密码">
            <a-input-password v-model:value="form.password" placeholder="请输入密码" autocomplete="new-password"/>
          </a-form-item>

          <a-form-item name="confirm" label="确认密码">
            <a-input-password v-model:value="form.confirm" placeholder="请再次输入密码" autocomplete="new-password"/>
          </a-form-item>

          <a-button type="primary" block :loading="submitting" html-type="submit">注册</a-button>

          <div class="switch-link">
            <span>已经有账户？</span>
            <a-button type="link" class="switch-link-btn" @click="goLogin">直接登录</a-button>
          </div>
        </a-form>
      </div>
      
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
import {ref, onMounted, computed} from 'vue';
import {useRouter} from 'vue-router';
import logoPng from '@/assets/ga-logo.svg';
import NotificationService from '@/utils/NotificationService';
import {ROUTES} from '@/config/constants';
import bgVideo from '@/assets/video/mp4/background.mp4';
import bgPoster from '@/assets/image/jpg/background.jpg';
import {CopyrightCircleOutlined} from '@ant-design/icons-vue';
import { getCopyright, getSystemName } from '@/utils/RuntimeConfig';
import { register } from '@/services/aiUser';
import { addUserPreferences } from '@/services/aiUserPreferences';
import {
  isPasswordComplexEnough,
  doesPasswordContainUsername,
  PASSWORD_COMPLEXITY_MESSAGE,
  PASSWORD_USERNAME_MESSAGE
} from '@/utils/passwordPolicy';

const router = useRouter();
const imageLoaded = ref(false);

onMounted(() => {
  const img = new Image();
  img.src = logoPng as unknown as string;
  img.onload = () => (imageLoaded.value = true);
});

const submitting = ref(false);
const form = ref({
  username: '',
  email: '',
  password: '',
  confirm: ''
});

function isEmail(value: string): boolean {
  return /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/.test(value);
}

const rules = {
  username: [
    {required: true, message: '请输入用户名'},
    {trigger: 'blur'}
  ],
  email: [
    {required: true, message: '请输入邮箱'},
    {
      validator: (_: any, value: string) => {
        if (!value) return Promise.resolve();
        return isEmail(value) ? Promise.resolve() : Promise.reject('邮箱格式输入有误');
      },
      trigger: 'blur'
    }
  ],
  password: [
    {required: true, message: '请输入密码'},
    {
      validator: (_: any, value: string) => {
        if (!value) return Promise.resolve();
        if (!isPasswordComplexEnough(value)) {
          return Promise.reject(PASSWORD_COMPLEXITY_MESSAGE);
        }
        if (doesPasswordContainUsername(value, form.value.username)) {
          return Promise.reject(PASSWORD_USERNAME_MESSAGE);
        }
        return Promise.resolve();
      },
      trigger: 'blur'
    }
  ],
  confirm: [
    {required: true, message: '请确认密码'},
    {
      validator(_: any, value: string) {
        if (!value) return Promise.resolve();
        if (value !== form.value.password) return Promise.reject('两次输入的密码不一致');
        return Promise.resolve();
      },
      trigger: 'blur'
    }
  ]
};

async function onSubmit() {
  try {
    submitting.value = true;
    // 修改payload结构以匹配要求的格式
    const payload = {
      username: form.value.username.trim(),
      email: form.value.email.trim(),
      password: form.value.password,
      additional_info: {
        avatar: '',
        avatarBackground: '',
        avatarTextColor: ''
      }
    };

    const res = await register(payload);

    const recommendedTemplate = [
      '你是一名专业且可靠的 AI 助手。',
      '',
      '当前日期时间：${datetime}',
      '当前模型：${model_name}',
      '',
      '请遵循以下规范：',
      '- 回答简洁明了，必要时提供步骤和示例',
      '- 若缺少信息请主动询问再继续',
      '- 标注重要注意事项与限制'
    ].join('\n');

    try {
      const body = res as any;
      const userId =
        body?.user?.uuid ||
        body?.uuid ||
        body?.data?.user?.uuid ||
        body?.data?.uuid ||
        body?.user?.id ||
        body?.id ||
        body?.data?.user?.id ||
        body?.data?.id ||
        '';
      if (userId) {
        await addUserPreferences({
          userId,
          preferences: {
            prompt: recommendedTemplate,
            autoCollapseReasoning: true,
            autoCollapseToolPanels: true,
            autoCollapseToolDetailsOnComplete: true,
            renderUserMessageMarkdown: false,
            chatWindowStyle: 'conversation'
          }
        });
      }
    } catch (e) {
      console.error('初始化用户偏好失败:', e);
    }
    NotificationService.success('注册成功');
    await router.push(ROUTES.LOGIN);
  } catch (e: any) {
    console.error('注册失败:', e);
  } finally {
    submitting.value = false;
  }
}

function goLogin() {
  router.push(ROUTES.LOGIN);
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

:deep(.auth-register .ant-form-item) {
  margin-bottom: 20px;
}
</style>
