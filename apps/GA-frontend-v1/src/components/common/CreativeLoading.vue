<template>
  <div class="html-assembler-loading">
    <div class="scene">
      <!-- 模拟的浏览器窗口 -->
      <div class="browser-window">
        <div class="browser-header">
          <div class="window-controls">
            <span class="control red"></span>
            <span class="control yellow"></span>
            <span class="control green"></span>
          </div>
          <div class="address-bar"></div>
        </div>
        <div class="browser-body">
          <!-- 动态组装的 UI 骨架 -->
          <div class="ui-header block-anim"></div>
          <div class="ui-container">
            <div class="ui-sidebar block-anim delay-1"></div>
            <div class="ui-content">
              <div class="ui-hero block-anim delay-2"></div>
              <div class="ui-lines">
                <div class="ui-line w-full block-anim delay-3"></div>
                <div class="ui-line w-80 block-anim delay-4"></div>
                <div class="ui-line w-60 block-anim delay-5"></div>
              </div>
            </div>
          </div>
          
          <!-- 扫描光效 -->
          <div class="scan-line"></div>
        </div>
      </div>

      <!-- 漂浮的代码符号粒子 -->
      <div class="floating-symbol s1">&lt;/&gt;</div>
      <div class="floating-symbol s2">div</div>
      <div class="floating-symbol s3">#css</div>
      <div class="floating-symbol s4">{ }</div>
      
      <!-- 底部阴影 -->
      <div class="window-shadow"></div>
    </div>

    <div class="loading-status" v-if="text">
      <span class="status-text">{{ text }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  text?: string;
}>();
</script>

<style scoped>
.html-assembler-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 32px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.scene {
  position: relative;
  width: 160px;
  height: 120px;
  perspective: 1000px;
}

/* 浏览器窗口主体 */
.browser-window {
  position: relative;
  width: 100%;
  height: 100%;
  background: #ffffff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 
    0 10px 30px -10px rgba(0, 0, 0, 0.1),
    0 4px 6px -4px rgba(0, 0, 0, 0.05),
    0 0 0 1px rgba(0, 0, 0, 0.05);
  transform: rotateX(10deg) rotateY(-10deg);
  animation: float-window 6s ease-in-out infinite;
  z-index: 2;
  transition: all 0.3s ease;
}

.browser-header {
  height: 20px;
  background: #f1f5f9;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  padding: 0 8px;
  gap: 8px;
}

.window-controls {
  display: flex;
  gap: 4px;
}

.control {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.red { background: #ef4444; }
.yellow { background: #f59e0b; }
.green { background: #10b981; }

.address-bar {
  flex: 1;
  height: 8px;
  background: #ffffff;
  border-radius: 4px;
  border: 1px solid #e2e8f0;
}

.browser-body {
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: calc(100% - 20px);
  position: relative;
  background: #fff;
}

/* UI 骨架块 */
.block-anim {
  background: #e2e8f0;
  border-radius: 4px;
  opacity: 0;
  animation: assemble-in 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.ui-header {
  width: 100%;
  height: 12px;
  background: #dbeafe; /* Blue-100 */
}

.ui-container {
  display: flex;
  gap: 8px;
  flex: 1;
}

.ui-sidebar {
  width: 25%;
  height: 100%;
  background: #f1f5f9; /* Slate-100 */
}

.ui-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ui-hero {
  width: 100%;
  height: 30px;
  background: #f3e8ff; /* Purple-100 */
}

.ui-lines {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ui-line {
  height: 4px;
  background: #e2e8f0;
}

.w-full { width: 100%; }
.w-80 { width: 80%; }
.w-60 { width: 60%; }

/* 动画延迟 */
.delay-1 { animation-delay: 0.1s; }
.delay-2 { animation-delay: 0.2s; }
.delay-3 { animation-delay: 0.3s; }
.delay-4 { animation-delay: 0.4s; }
.delay-5 { animation-delay: 0.5s; }

/* 扫描光效 */
.scan-line {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    to bottom,
    transparent 0%,
    rgba(59, 130, 246, 0.1) 50%,
    transparent 100%
  );
  transform: translateY(-100%);
  animation: scan 2s linear infinite;
  pointer-events: none;
}

/* 底部阴影 */
.window-shadow {
  position: absolute;
  bottom: -20px;
  left: 50%;
  transform: translateX(-50%) rotateX(60deg);
  width: 140px;
  height: 20px;
  background: radial-gradient(ellipse at center, rgba(0,0,0,0.15) 0%, rgba(0,0,0,0) 70%);
  z-index: 1;
  animation: shadow-breath 6s ease-in-out infinite;
}

/* 漂浮符号 */
.floating-symbol {
  position: absolute;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
  font-weight: bold;
  color: #64748b;
  background: rgba(255, 255, 255, 0.9);
  padding: 4px 8px;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
  border: 1px solid rgba(0,0,0,0.05);
  z-index: 3;
  opacity: 0;
  animation: float-in-out 4s ease-in-out infinite;
}

.s1 { top: -10px; right: -20px; color: #3b82f6; animation-delay: 0s; }
.s2 { bottom: 20px; left: -30px; color: #8b5cf6; animation-delay: 1.5s; }
.s3 { bottom: -10px; right: -10px; color: #10b981; animation-delay: 2.5s; }
.s4 { top: 30px; left: -25px; color: #f59e0b; animation-delay: 1s; }

/* 文本状态 */
.status-text {
  font-size: 14px;
  font-weight: 500;
  color: #475569;
  letter-spacing: 0.5px;
  background: linear-gradient(90deg, #475569 0%, #94a3b8 50%, #475569 100%);
  background-size: 200% 100%;
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
  animation: text-shimmer 2s linear infinite;
}

/* Keyframes */
@keyframes float-window {
  0%, 100% { transform: rotateX(10deg) rotateY(-10deg) translateY(0); }
  50% { transform: rotateX(10deg) rotateY(-10deg) translateY(-10px); }
}

@keyframes shadow-breath {
  0%, 100% { transform: translateX(-50%) rotateX(60deg) scale(1); opacity: 0.8; }
  50% { transform: translateX(-50%) rotateX(60deg) scale(0.8); opacity: 0.5; }
}

@keyframes assemble-in {
  0% { opacity: 0; transform: translateY(10px) scale(0.95); }
  20% { opacity: 1; transform: translateY(0) scale(1); }
  80% { opacity: 1; transform: translateY(0) scale(1); }
  90% { opacity: 0; transform: translateY(-5px) scale(1.02); }
  100% { opacity: 0; transform: translateY(-5px) scale(1.02); }
}

@keyframes scan {
  0% { transform: translateY(-100%); opacity: 0; }
  20% { opacity: 1; }
  80% { opacity: 1; }
  100% { transform: translateY(200%); opacity: 0; }
}

@keyframes float-in-out {
  0% { transform: translateY(10px); opacity: 0; }
  20% { transform: translateY(0); opacity: 1; }
  80% { transform: translateY(-10px); opacity: 1; }
  100% { transform: translateY(-20px); opacity: 0; }
}

@keyframes text-shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
</style>
