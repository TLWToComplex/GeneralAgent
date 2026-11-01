<template>
  <div class="welcome-background" :class="{ 'welcome-home': currentStep === 1 }">
    <video class="background-video" autoplay muted loop playsinline :poster="bgPoster">
      <source :src="bgVideo" type="video/mp4" />
    </video>
    <div class="welcome-container" :class="{ 'fade-out': isTransitioning, 'exit-fade-out': isExiting }">
      <WelcomeStep
        v-if="currentStep === 1"
        :show-content="showContent"
        :is-transitioning="isTransitioning"
        :image-loaded="imageLoaded"
        :logo-image="logoImage"
        @start="handleStart"
      />

      <UserProfileStep
        v-else-if="currentStep === 2"
        :show-content="showContent"
        :initial-data="profileFormData"
        @prev="handleCancel"
        @next="onProfileStepNext"
      />

      <div v-else-if="currentStep === 3" class="step-content complete-step">
        <div class="progress-section" :class="{ animate: showContent }">
          <div class="progress-dots">
            <div class="dot completed"></div>
            <div class="dot-line completed"></div>
            <div class="dot completed"></div>
            <div class="dot-line completed"></div>
            <div class="dot completed"></div>
          </div>
          <div class="progress-text completed">资料确认</div>
        </div>

        <div class="title-section" :class="{ animate: showContent }">
          <h1 class="complete-title">确认个人资料</h1>
          <p class="complete-description">确认无误后开始使用系统</p>
        </div>

        <div v-if="configSummary" class="summary-section" :class="{ animate: showContent }">
          <div class="config-card user-profile-card" :class="{ 'animate-card': showContent }" style="padding: 32px 24px;">
            <div class="card-header" style="justify-content: center; flex-direction: column; text-align: center; gap: 16px; margin-bottom: 24px;">
              <div class="avatar-display" style="width: 88px; height: 88px; margin: 0 auto; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12); border: 3px solid #fff; border-radius: 50%; overflow: hidden;">
                <img :src="profileFormData.avatar" alt="avatar" class="avatar-image" style="width: 100%; height: 100%; object-fit: cover;" />
              </div>
              <div class="card-title" style="text-align: center;">
                <h3 style="font-size: 20px; margin-bottom: 4px;">{{ configSummary.realname }}</h3>
                <p style="color: #8c8c8c; font-size: 14px;">请核对以下信息</p>
              </div>
            </div>
            <div class="card-content" style="background: #fafafa; padding: 20px; border-radius: 12px; border: 1px solid #f0f0f0;">
              <div class="config-item">
                <span class="config-label">姓名</span>
                <span class="config-value">{{ configSummary.realname }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">联系方式</span>
                <span class="config-value">{{ configSummary.contact || '未填写' }}</span>
              </div>
              <div class="config-item">
                <span class="config-label">用户组</span>
                <span class="config-value">
                  <div class="group-tags" style="display: flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end;">
                    <a-tag v-for="name in configSummary.groupNames" :key="name" color="blue" style="margin-inline-end: 0;">{{ name }}</a-tag>
                  </div>
                </span>
              </div>
            </div>
          </div>
        </div>

        <div class="action-section" :class="{ animate: showContent }" style="margin-top: 40px; position: static; transform: translateY(0);">
          <div class="nav-pill">
            <a-tooltip title="返回上一步" placement="top">
              <a-button type="text" shape="circle" class="nav-icon-btn" @click="handleCompleteCancel">
                <template #icon><ArrowLeftOutlined /></template>
              </a-button>
            </a-tooltip>
            <div class="nav-divider"></div>
            <a-button type="primary" shape="round" class="nav-primary-btn" :loading="submitting" @click="handleComplete">
              开始使用
              <CheckOutlined />
            </a-button>
          </div>
        </div>
      </div>

      <div v-else-if="currentStep === 4" class="step-content final-welcome-step rose-demo" :class="{ animate: showContent }">
        <div class="frame"> 
          <svg viewBox="0 0 100 100" fill="none" aria-hidden="true"> 
            <defs>
              <linearGradient id="roseGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#54aeff" />
                <stop offset="100%" stop-color="#5475ff" />
              </linearGradient>
            </defs>
            <g ref="groupRef"> 
              <path ref="pathRef" stroke="url(#roseGradient)" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"></path> 
            </g> 
          </svg> 
        </div> 
        <div class="meta"> 
          <div class="title">欢迎使用</div> 
        </div> 
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { ArrowLeftOutlined, CheckOutlined } from '@ant-design/icons-vue';
import NotificationService from '@/utils/NotificationService';
import { updateUser, syncAiUserGroups, type UpdateUserPayload } from '@/services/aiUser';
import { STORAGE_KEYS, ROUTES } from '@/config/constants';
import bgVideo from '@/assets/video/mp4/background.mp4';
import bgPoster from '@/assets/image/jpg/background.jpg';
import logoImage from '@/assets/ga-logo.svg';
import WelcomeStep from '@/views/welcome/WelcomeStep.vue';
import UserProfileStep from '@/views/welcome/UserProfileStep.vue';

interface UserProfileFormData {
  realname: string;
  contact: string;
  avatar: string;
  groupIds: string[];
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

const router = useRouter();
const currentStep = ref(1);
const isTransitioning = ref(false);
const isExiting = ref(false);
const showContent = ref(false);
const imageLoaded = ref(false);
const submitting = ref(false);
const defaultAvatar = bgPoster as unknown as string;

// Rose Two Refs & Logic
const groupRef = ref<SVGGElement | null>(null);
const pathRef = ref<SVGPathElement | null>(null);
let animationFrameId: number;

const SVG_NS = 'http://www.w3.org/2000/svg';
const roseConfig = {
  name: "Rose Two", 
  tag: "r = a cos(2θ)", 
  rotate: true, 
  particleCount: 140, 
  trailSpan: 0.68, 
  durationMs: 5500, 
  rotationDurationMs: 28000, 
  pulseDurationMs: 4300, 
  strokeWidth: 4.6, 
  roseA: 9.2, 
  roseABoost: 0.6, 
  roseBreathBase: 0.72, 
  roseBreathBoost: 0.28, 
  roseScale: 3.25, 
  formula(config: any) { 
    return [ 
      `r(t) = (${config.roseA.toFixed(1)} + ${config.roseABoost.toFixed(2)}s)(${config.roseBreathBase.toFixed(2)} + ${config.roseBreathBoost.toFixed(2)}s) cos(2t)`, 
      `x(t) = 50 + cos t · r(t) · ${config.roseScale.toFixed(2)}`, 
      `y(t) = 50 + sin t · r(t) · ${config.roseScale.toFixed(2)}`, 
    ].join("\n"); 
  }, 
  point(progress: number, detailScale: number, config: any) { 
    const t = progress * Math.PI * 2; 
    const a = config.roseA + detailScale * config.roseABoost; 
    const r = a * (config.roseBreathBase + detailScale * config.roseBreathBoost) * Math.cos(2 * t); 
    return { 
      x: 50 + Math.cos(t) * r * config.roseScale, 
      y: 50 + Math.sin(t) * r * config.roseScale, 
    }; 
  }, 
};

function normalizeProgress(progress: number) { 
  return ((progress % 1) + 1) % 1; 
} 
function getDetailScale(time: number) { 
  const pulseProgress = (time % roseConfig.pulseDurationMs) / roseConfig.pulseDurationMs; 
  const pulseAngle = pulseProgress * Math.PI * 2; 
  return 0.52 + ((Math.sin(pulseAngle + 0.55) + 1) / 2) * 0.48; 
} 
function getRotation(time: number) { 
  if (!roseConfig.rotate) return 0; 
  return -((time % roseConfig.rotationDurationMs) / roseConfig.rotationDurationMs) * 360; 
} 
function buildPath(detailScale: number, steps = 480) { 
  return Array.from({ length: steps + 1 }, (_, index) => { 
    const point = roseConfig.point(index / steps, detailScale, roseConfig); 
    return `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(2)} ${point.y.toFixed(2)}`; 
  }).join(' '); 
} 
// Interpolate color between blue (#54aeff) and purple (#5475ff)
function interpolateColor(ratio: number) {
  const c1 = { r: 84, g: 174, b: 255 }; // #54aeff
  const c2 = { r: 84, g: 117, b: 255 }; // #5475ff
  
  const r = Math.round(c1.r + (c2.r - c1.r) * ratio);
  const g = Math.round(c1.g + (c2.g - c1.g) * ratio);
  const b = Math.round(c1.b + (c2.b - c1.b) * ratio);
  
  return `rgb(${r}, ${g}, ${b})`;
}

function getParticle(index: number, progress: number, detailScale: number) { 
  const tailOffset = index / (roseConfig.particleCount - 1); 
  const point = roseConfig.point(normalizeProgress(progress - tailOffset * roseConfig.trailSpan), detailScale, roseConfig); 
  const fade = Math.pow(1 - tailOffset, 0.56); 
  return { 
    x: point.x, 
    y: point.y, 
    radius: 0.9 + fade * 2.7, 
    opacity: 0.04 + fade * 0.96, 
    color: interpolateColor(1 - tailOffset) // Head (fade=1) is c2, Tail (fade=0) is c1
  }; 
} 

function startRoseAnimation() {
  if (!groupRef.value || !pathRef.value) return;
  const group = groupRef.value;
  const path = pathRef.value;

  path.setAttribute('stroke-width', String(roseConfig.strokeWidth)); 
  
  const existingCircles = group.querySelectorAll('circle');
  existingCircles.forEach(c => c.remove());

  const particles = Array.from({ length: roseConfig.particleCount }, () => { 
    const circle = document.createElementNS(SVG_NS, 'circle'); 
    group.appendChild(circle); 
    return circle; 
  }); 

  const startedAt = performance.now(); 
  
  function render(now: number) { 
    const time = now - startedAt; 
    const progress = (time % roseConfig.durationMs) / roseConfig.durationMs; 
    const detailScale = getDetailScale(time); 
    
    if (groupRef.value) groupRef.value.setAttribute('transform', `rotate(${getRotation(time)} 50 50)`); 
    if (pathRef.value) pathRef.value.setAttribute('d', buildPath(detailScale)); 
    
    particles.forEach((node, index) => { 
      const particle = getParticle(index, progress, detailScale); 
      node.setAttribute('cx', particle.x.toFixed(2)); 
      node.setAttribute('cy', particle.y.toFixed(2)); 
      node.setAttribute('r', particle.radius.toFixed(2)); 
      node.setAttribute('opacity', particle.opacity.toFixed(3)); 
      node.setAttribute('fill', particle.color);
    }); 
    animationFrameId = requestAnimationFrame(render); 
  } 
  animationFrameId = requestAnimationFrame(render); 
}

watch(currentStep, async (newVal) => {
  if (newVal === 4) {
    await nextTick();
    startRoseAnimation();
    
    // Wait 4 seconds, then fade out and enter system
    setTimeout(() => {
      isExiting.value = true;
      setTimeout(() => {
        goToChat();
      }, 1000); // 1 second for fade out
    }, 4000);
  }
});

const preloadImage = new Image();
preloadImage.src = logoImage;
preloadImage.onload = () => {
  imageLoaded.value = true;
};

const profileFormData = ref<UserProfileFormData>({
  realname: '',
  contact: '',
  avatar: defaultAvatar,
  groupIds: []
});

const configSummary = ref<{
  realname: string;
  contact: string;
  groupNames: string[];
} | null>(null);

const safeString = (value: unknown) => String(value || '').trim();

const getStoredUserProfile = (): StoredUserProfile => {
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
  } catch {
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

onMounted(() => {
  if (preloadImage.complete) {
    imageLoaded.value = true;
  }

  const storedProfile = getStoredUserProfile();
  profileFormData.value = {
    realname: storedProfile.realname || '',
    contact: storedProfile.contact || '',
    avatar: storedProfile.avatar || defaultAvatar,
    groupIds: []
  };

  setTimeout(() => {
    showContent.value = true;
  }, 100);
});

onUnmounted(() => {
  if (animationFrameId) {
    cancelAnimationFrame(animationFrameId);
  }
});
const switchStep = async (nextStep: number) => {
  isTransitioning.value = true;
  showContent.value = false;

  await new Promise((resolve) => setTimeout(resolve, 300));

  currentStep.value = nextStep;
  
  await nextTick();
  await new Promise((resolve) => setTimeout(resolve, 50));
  
  isTransitioning.value = false;

  setTimeout(() => {
    showContent.value = true;
  }, 100);
};

const handleStart = async () => {
  await switchStep(2);
};

const handleCancel = async () => {
  await switchStep(1);
};

const onProfileStepNext = async (data: UserProfileFormData, groupNames: string[]) => {
  profileFormData.value = { ...data };
  configSummary.value = {
    realname: data.realname,
    contact: data.contact,
    groupNames: groupNames
  };

  await switchStep(3);
};

const handleCompleteCancel = async () => {
  await switchStep(2);
};

const saveUserConfiguration = async () => {
  const storedProfile = getStoredUserProfile();
  if (!storedProfile.uuid) {
    throw new Error('用户 UUID 缺失');
  }

  const payload: UpdateUserPayload = {
    uuid: storedProfile.uuid,
    realname: profileFormData.value.realname.trim(),
    additional_info: {
      avatar: profileFormData.value.avatar || defaultAvatar,
      avatarBackground: '#ffffff',
      avatarTextColor: '#ffffff'
    }
  };

  if (storedProfile.username) {
    payload.update_by = storedProfile.username;
  }

  const response = await updateUser(payload);
  const userData = response?.data || response?.user || response || {};
  const additionalInfo = userData?.additional_info && typeof userData.additional_info === 'object'
    ? userData.additional_info
    : {};

  const profileData: StoredUserProfile = {
    username: safeString(userData?.username) || storedProfile.username,
    email: safeString(userData?.email) || storedProfile.email,
    avatar: safeString(userData?.avatar) || safeString(additionalInfo?.avatar) || profileFormData.value.avatar || defaultAvatar,
    avatarBackground: safeString(userData?.avatarBackground) || safeString(additionalInfo?.avatarBackground) || '#ffffff',
    avatarTextColor: safeString(userData?.avatarTextColor) || safeString(additionalInfo?.avatarTextColor) || '#ffffff',
    uuid: safeString(userData?.uuid) || storedProfile.uuid,
    realname: safeString(userData?.realname) || profileFormData.value.realname.trim(),
    contact: safeString(userData?.contact) || profileFormData.value.contact.trim()
  };

  localStorage.setItem('user-profile', JSON.stringify(profileData));
  localStorage.setItem(STORAGE_KEYS.NEED_UPDATE_MSG, 'false');
  window.dispatchEvent(new CustomEvent('user-info-updated'));
};

const handleComplete = async () => {
  try {
    submitting.value = true;
    await saveUserConfiguration();

    const storedProfile = getStoredUserProfile();
    if (storedProfile.uuid && profileFormData.value.groupIds && profileFormData.value.groupIds.length > 0) {
      await syncAiUserGroups({
        user_group_map: {
          [storedProfile.uuid]: profileFormData.value.groupIds
        }
      });
    }

    NotificationService.success('个人资料保存成功');
    await switchStep(4);
  } catch (error) {
    console.error('保存首次登录资料失败:', error);
    NotificationService.error('保存个人资料失败，请稍后重试');
  } finally {
    submitting.value = false;
  }
};

const isRouting = ref(false);

const goToChat = async () => {
  if (isRouting.value) return;
  isRouting.value = true;
  await router.push(ROUTES.CHAT);
};

// onMounted and onUnmounted removed from here because they are already defined above
</script>

<style scoped>
@import '@/assets/styles/welcome.css';

@font-face {
  font-family: 'SmileySansOblique';
  src: url('../assets/fonts/SmileySans-Oblique.woff2') format('woff2');
  font-display: swap;
}

:deep(.ant-form-item-label > label) {
  color: #262626;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  font-size: 14px;
}

:deep(.ant-input),
:deep(.ant-textarea) {
  border-radius: 10px;
  border: 1px solid #e8e8e8;
  padding: 8px 15px;
  font-size: 14px;
  transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}

:deep(.ant-input:focus),
:deep(.ant-textarea:focus) {
  border-color: #1890ff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.1);
}

.complete-step {
  margin-top: 25px;
}

.user-profile-card {
  text-align: left;
}

</style>
