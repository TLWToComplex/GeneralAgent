<template>
  <div class="nf-wrapper">
    <video ref="bgVideoRef" class="background-video" autoplay muted loop playsinline preload="auto" :poster="bgPoster">
      <source :src="bgVideo" type="video/mp4" />
    </video>
    <div class="not-found-simple">
      <div class="center">
        <div class="content" role="main" aria-labelledby="nf-title">
          <div class="content-inner">
            <div class="code" aria-hidden="true">404</div>
            <h1 id="nf-title" class="title">该页面不可用</h1>
            <p class="desc">链接可能错误或已失效。请返回首页继续使用。</p>
            <div class="actions">
              <a-button class="brand-button" size="large" shape="circle" @click="goHome">
                <template #icon><LeftOutlined /></template>
              </a-button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { LeftOutlined } from '@ant-design/icons-vue'
import bgVideo from '@/assets/video/mp4/background.mp4'
import bgPoster from '@/assets/image/jpg/background.jpg'
import { ref } from 'vue'

defineOptions({ name: 'NotFoundView' })

const router = useRouter()
const goHome = () => router.push('/')

const bgVideoRef = ref<HTMLVideoElement | null>(null)
</script>

<style scoped>
.not-found-simple {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  position: relative;
  z-index: 1;
}

.center {
  width: 100%;
}

.content {
  margin: 0 auto;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent !important;
}

.code {
  font-size: 120px;
  line-height: 1;
  letter-spacing: -6px;
  margin-bottom: 30px;
  background: linear-gradient(90deg, #1f80ff 0%, #6ec8ff 100%);
  -webkit-background-clip: text;
  background-clip: text;
}

.background-video {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  object-fit: cover;
  z-index: 0;
  pointer-events: none;
}

.code {
  color: transparent;
  -webkit-text-fill-color: transparent;
}

.title {
  font-size: 25px;
  font-weight: 700;
  color: #1f1f1f;
  margin: 0 0 15px;
}

.desc {
  margin: 12px 0 30px;
  font-size: 14px;
  color: #5b5b5b;
}

.actions {
  display: inline-flex;
  gap: 12px;
}

.brand-button {
  background: linear-gradient(90deg, #1677ff, #53a5ff);
  color: #ffffff;
  border: none;
  border-radius: 50%;
  width: 44px !important;
  height: 44px !important;
  padding: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(22, 119, 255, 0.25);
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}

.brand-button:hover {
  color: #ffffff;
  filter: brightness(1.06);
  box-shadow: 0 14px 28px rgba(22, 119, 255, 0.28);
  transform: translateY(-1px);
}

.brand-button:active {
  color: #ffffff;
  filter: brightness(0.96);
  transform: translateY(0);
  box-shadow: 0 8px 18px rgba(22, 119, 255, 0.22);
}

.brand-button:focus-visible {
  color: #ffffff;
  outline: none;
  box-shadow: 0 0 0 3px rgba(22, 119, 255, 0.3);
}
</style>