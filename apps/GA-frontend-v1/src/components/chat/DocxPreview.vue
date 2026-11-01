<template>
  <div ref="rootRef" class="docx-container-scroll" v-show="!suspend">
    <div ref="docxContainerRef" class="docx-render-root"></div>
    <div v-if="loading" class="docx-loading">渲染中...</div>
    <Transition name="doc-error-fade">
      <div v-if="error" class="docx-error-overlay" key="doc-error">
        <div class="docx-error-card">
          <div class="docx-error-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>
          <h3 class="docx-error-title">格式不支持</h3>
          <p class="docx-error-message">{{ error }}</p>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import { renderAsync } from 'docx-preview';

const props = defineProps<{
  content: ArrayBuffer | ArrayBufferView | string | null
  artifactId?: string
  title?: string
  suspend?: boolean
}>();

const rootRef = ref<HTMLElement | null>(null);
const docxContainerRef = ref<HTMLElement | null>(null);
const loading = ref(false);
const error = ref('');
const isRendering = ref(false);
const lastRenderedKey = ref<string>('');
const lastScale = ref(1);

let pendingRender = false;
let resizeObserver: ResizeObserver | null = null;
let rafId: number | null = null;
let scaleRafId: number | null = null;
let idleId: number | null = null;
let renderTimer: number | null = null;

const clearContainer = () => {
  const el = docxContainerRef.value;
  if (!el) return;
  el.innerHTML = '';
};

const scheduleRender = () => {
  if (props.suspend) {
    pendingRender = true;
    return;
  }
  if (rafId !== null) return;
  rafId = requestAnimationFrame(() => {
    rafId = null;
    const run = () => {
      void doRender();
    };
    const idle = (window as any).requestIdleCallback as ((cb: () => void, opts?: { timeout: number }) => number) | undefined;
    const cancelIdle = (window as any).cancelIdleCallback as ((id: number) => void) | undefined;
    if (idle) {
      if (idleId !== null && cancelIdle) {
        cancelIdle(idleId);
      }
      idleId = idle(() => {
        idleId = null;
        run();
      }, { timeout: 600 });
    } else {
      if (renderTimer !== null) {
        window.clearTimeout(renderTimer);
      }
      renderTimer = window.setTimeout(() => {
        renderTimer = null;
        run();
      }, 320);
    }
  });
};

const scheduleScale = () => {
  if (props.suspend) return;
  if (scaleRafId !== null) return;
  scaleRafId = requestAnimationFrame(() => {
    scaleRafId = null;
    updateScale();
  });
};

const updateScale = () => {
  const root = rootRef.value;
  const container = docxContainerRef.value;
  if (!root || !container) return;
  if (props.suspend) return;
  const wrapper = container.querySelector('.docx-wrapper') as HTMLElement | null;
  const section = container.querySelector('section.docx') as HTMLElement | null;
  if (!wrapper || !section) return;

  const pageWidth = section.offsetWidth;
  if (!pageWidth) return;

  const cs = getComputedStyle(wrapper);
  const paddingLeft = parseFloat(cs.paddingLeft || '0') || 0;
  const paddingRight = parseFloat(cs.paddingRight || '0') || 0;
  const rootWidth = Math.max(root.getBoundingClientRect().width, 0);
  const availableWidth = Math.max(rootWidth, 0);
  const wrapperWidth = pageWidth + paddingLeft + paddingRight;
  const scale = Math.min(1, availableWidth / wrapperWidth);
  if (Math.abs(scale - lastScale.value) < 0.005) return;

  wrapper.style.display = 'block';
  wrapper.style.position = 'static';
  wrapper.style.marginLeft = 'auto';
  wrapper.style.marginRight = 'auto';
  wrapper.style.boxSizing = 'border-box';
  wrapper.style.width = `${wrapperWidth}px`;
  wrapper.style.transform = '';
  wrapper.style.transformOrigin = '';
  wrapper.style.willChange = '';
  wrapper.style.setProperty('zoom', `${scale}`);

  section.style.transform = '';
  section.style.transformOrigin = '';
  section.style.marginLeft = '0';
  section.style.marginRight = '0';
  lastScale.value = scale;
};

/**
 * 检测 ArrayBuffer 是否为 ZIP 格式（.docx 基于 ZIP，.doc 是 CFBF 格式）
 * ZIP 文件的前 4 字节是 0x50 0x4B 0x03 0x04（即 "PK\x03\x04"）
 */
const isZipFormat = (buffer: ArrayBuffer | SharedArrayBuffer): boolean => {
  if (buffer.byteLength < 4) return false;
  const view = new Uint8Array(buffer, 0, 4);
  return view[0] === 0x50 && view[1] === 0x4b && view[2] === 0x03 && view[3] === 0x04;
};

const doRender = async () => {
  const content = props.content;
  const container = docxContainerRef.value;
  if (!content || !container) {
    clearContainer();
    loading.value = false;
    error.value = '';
    lastRenderedKey.value = '';
    return;
  }
  if (props.suspend) {
    pendingRender = true;
    return;
  }

  const contentLength = typeof content === 'string' ? content.length : content.byteLength;
  const key = `${props.artifactId || ''}:${contentLength}`;
  if (key === lastRenderedKey.value && container.innerHTML) {
    return;
  }

  if (isRendering.value) {
    pendingRender = true;
    return;
  }

  isRendering.value = true;
  pendingRender = false;

  error.value = '';
  loading.value = true;
  await nextTick();

  try {
    clearContainer();

    // 检测是否为 .doc 格式（非 ZIP），提前拦截并显示友好提示
    if (content instanceof ArrayBuffer || ArrayBuffer.isView(content)) {
      const buffer = content instanceof ArrayBuffer ? content : content.buffer.slice(content.byteOffset, content.byteOffset + content.byteLength);
      if (!isZipFormat(buffer)) {
        throw new Error('不支持预览 .doc 格式文档。请将文件转换为 .docx 格式后再进行预览。');
      }
    }

    await renderAsync(content, container, undefined, {
      className: 'docx',
      inWrapper: true,
      ignoreWidth: false,
      ignoreHeight: false
    });

    lastRenderedKey.value = key;
    scheduleScale();
  } catch (e: any) {
    error.value = (e && typeof e.message === 'string' && e.message) ? e.message : 'Word 文档渲染失败';
  } finally {
    loading.value = false;
    isRendering.value = false;
  }

  if (pendingRender) {
    pendingRender = false;
    scheduleRender();
  }
};

watch(
  () => [props.content, props.artifactId],
  () => {
    scheduleRender();
  },
  { immediate: true }
);

watch(
  () => props.suspend,
  (value) => {
    if (!value) {
      scheduleRender();
      scheduleScale();
    }
  }
);

onMounted(() => {
  const el = rootRef.value;
  if (el) {
    resizeObserver = new ResizeObserver(() => {
      scheduleScale();
    });
    resizeObserver.observe(el);
  }
});

onUnmounted(() => {
  if (rafId !== null) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
  if (idleId !== null) {
    const cancelIdle = (window as any).cancelIdleCallback as ((id: number) => void) | undefined;
    if (cancelIdle) cancelIdle(idleId);
    idleId = null;
  }
  if (renderTimer !== null) {
    window.clearTimeout(renderTimer);
    renderTimer = null;
  }
  if (scaleRafId !== null) {
    cancelAnimationFrame(scaleRafId);
    scaleRafId = null;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  clearContainer();
});
</script>

<style scoped>
.docx-container-scroll {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  background: #f1f5f9;
  min-height: 0;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
  contain: layout paint;
}

.docx-container-scroll:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.docx-container-scroll::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.docx-container-scroll::-webkit-scrollbar-track {
  background-color: transparent;
}

.docx-container-scroll::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.docx-container-scroll:hover::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
}

.docx-container-scroll::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, 0.25);
}

.docx-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(241, 245, 249, 0.8);
  color: #64748b;
  font-size: 13px;
  z-index: 2;
}

/* === 错误提示过渡动画 === */
.doc-error-fade-enter-active,
.doc-error-fade-leave-active {
  transition: opacity 0.25s ease;
}

.doc-error-fade-enter-from,
.doc-error-fade-leave-to {
  opacity: 0;
}

.docx-error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(241, 245, 249, 0.95);
  backdrop-filter: blur(4px);
  z-index: 10;
  padding: 24px;
}

.docx-error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  max-width: 380px;
  padding: 40px 32px;
  text-align: center;
}

.docx-error-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
}

.docx-error-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.docx-error-message {
  margin: 0;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}

.docx-render-root {
  position: relative;
  background: transparent;
  width: 100%;
  min-height: 100%;
  contain: layout paint;
}

:deep(.docx-render-root .docx-wrapper) {
  height: auto;
  overflow: visible;
  max-height: none;
  background: #f1f5f9;
  padding: 30px;
}

:deep(.docx-render-root .docx-wrapper > section.docx) {
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.15);
  margin-bottom: 24px;
  background-color: white;
}

:deep(.docx-render-root .docx-wrapper > section.docx:last-child) {
  margin-bottom: 0;
}
</style>
