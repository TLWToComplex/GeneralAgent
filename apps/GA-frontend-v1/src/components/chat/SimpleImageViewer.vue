<template>
  <Teleport to="body">
    <Transition name="simple-image-modal-transition" @after-leave="handleAfterLeave">
      <div v-if="visible" class="simple-image-modal" @click.self="closeModal">
        <div class="simple-image-modal__backdrop"></div>
        <div class="simple-image-modal__panel" role="dialog" aria-modal="true" :aria-label="activeImageAlt || '图片查看器'">
          <div class="image-viewer-header">
            <Transition name="image-viewer-status-transition" mode="out-in">
              <div v-if="hasMultipleImages || activeImageName" :key="`${activeImageUrl}-${currentIndex}`" class="image-viewer-status">
                <span v-if="hasMultipleImages" class="image-viewer-counter">{{ currentIndex + 1 }} / {{ normalizedImages.length }}</span>
                <span class="image-viewer-name">{{ activeImageName }}</span>
              </div>
            </Transition>
            <div class="button-group">
              <button @click="closeModal" class="simple-image-close-btn" type="button">
                <CloseOutlined />
              </button>
            </div>
          </div>

          <button
            v-if="hasMultipleImages"
            class="image-viewer-nav image-viewer-nav--prev"
            type="button"
            aria-label="上一张图片"
            @click.stop="showPrevImage"
          >
            <LeftOutlined />
          </button>

          <button
            v-if="hasMultipleImages"
            class="image-viewer-nav image-viewer-nav--next"
            type="button"
            aria-label="下一张图片"
            @click.stop="showNextImage"
          >
            <RightOutlined />
          </button>

          <div class="image-viewer-content" ref="contentRef">
            <Transition name="viewer-image-transition" mode="out-in">
              <img
                :key="activeImageUrl"
                :src="activeImageUrl"
                :alt="activeImageAlt"
                class="viewer-image"
                :style="imageStyle"
                @mousedown="startDrag"
                @mouseup="endDrag"
                @mousemove="onDrag"
                @mouseleave="endDrag"
                draggable="false"
              />
            </Transition>
          </div>

          <div class="image-viewer-bottom">
            <div class="image-toolbar">
              <button @click="zoomIn" class="toolbar-btn" title="放大" type="button">
                <ZoomInOutlined />
              </button>
              <button @click="zoomOut" class="toolbar-btn" title="缩小" type="button">
                <ZoomOutOutlined />
              </button>
              <button @click="resetZoom" class="toolbar-btn" title="重置" type="button">
                <RedoOutlined />
              </button>
              <div class="divider"></div>
              <button @click="rotateLeft" class="toolbar-btn" title="向左旋转" type="button">
                <RotateLeftOutlined />
              </button>
              <button @click="rotateRight" class="toolbar-btn" title="向右旋转" type="button">
                <RotateRightOutlined />
              </button>
              <div class="divider"></div>
              <button @click="flipHorizontal" class="toolbar-btn" title="水平翻转" type="button">
                <SwapOutlined />
              </button>
              <button @click="flipVertical" class="toolbar-btn" title="垂直翻转" type="button">
                <SwapOutlined class="vertical-swap" />
              </button>
              <div class="divider"></div>
              <button @click="downloadImage" class="toolbar-btn" title="下载图片" type="button">
                <DownloadOutlined />
              </button>
            </div>

            <div v-if="hasMultipleImages" class="image-thumbnail-strip">
              <button
                class="image-thumbnail-page-btn image-thumbnail-page-btn--prev"
                :class="{ 'is-disabled': !canPageLeft }"
                type="button"
                aria-label="向左翻页缩略图"
                @click.stop="scrollThumbnailPage('left')"
              >
                <LeftOutlined />
              </button>
              <div ref="thumbnailStripRef" class="image-thumbnail-viewport" @scroll="updateThumbnailPagination">
                <div class="image-thumbnail-track">
                  <button
                    v-for="(image, index) in normalizedImages"
                    :key="image.key || `${image.url}-${index}`"
                    type="button"
                    class="image-thumbnail-item"
                    :class="{ 'is-active': index === currentIndex }"
                    :aria-label="`切换到图片 ${image.name || image.alt || index + 1}`"
                    @click.stop="selectImage(index)"
                  >
                    <img :src="image.url" :alt="image.alt || image.name || '图片缩略图'" class="image-thumbnail" />
                  </button>
                </div>
              </div>
              <button
                class="image-thumbnail-page-btn image-thumbnail-page-btn--next"
                :class="{ 'is-disabled': !canPageRight }"
                type="button"
                aria-label="向右翻页缩略图"
                @click.stop="scrollThumbnailPage('right')"
              >
                <RightOutlined />
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue';
import {
  CloseOutlined,
  DownloadOutlined,
  LeftOutlined,
  RedoOutlined,
  RightOutlined,
  RotateLeftOutlined,
  RotateRightOutlined,
  SwapOutlined,
  ZoomInOutlined,
  ZoomOutOutlined
} from '@ant-design/icons-vue';

interface ViewerImageItem {
  url: string;
  alt?: string;
  name?: string;
  key?: string;
}

const props = defineProps<{
  open: boolean;
  imageUrl: string;
  imageAlt?: string;
  images?: ViewerImageItem[];
}>();

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void;
}>();

const scale = ref(0.92);
const rotate = ref(0);
const flipX = ref(false);
const flipY = ref(false);
const translateX = ref(0);
const translateY = ref(0);

const isDragging = ref(false);
const dragStartX = ref(0);
const dragStartY = ref(0);
const startTranslateX = ref(0);
const startTranslateY = ref(0);

const contentRef = ref<HTMLDivElement | null>(null);

const rendered = ref(false);
const visible = ref(false);
const currentIndex = ref(0);
const thumbnailStripRef = ref<HTMLDivElement | null>(null);
const canPageLeft = ref(false);
const canPageRight = ref(false);

const normalizedImages = computed<ViewerImageItem[]>(() => {
  const items = Array.isArray(props.images)
    ? props.images
      .filter((item): item is ViewerImageItem => !!item?.url)
      .map(item => ({
        url: item.url,
        alt: item.alt || item.name || '图片',
        name: item.name || item.alt || '图片',
        key: item.key
      }))
    : [];

  if (!items.length && props.imageUrl) {
    return [{
      url: props.imageUrl,
      alt: props.imageAlt || '图片',
      name: props.imageAlt || '图片',
      key: props.imageUrl
    }];
  }

  if (props.imageUrl && !items.some(item => item.url === props.imageUrl)) {
    return [{
      url: props.imageUrl,
      alt: props.imageAlt || '图片',
      name: props.imageAlt || '图片',
      key: props.imageUrl
    }, ...items];
  }

  return items;
});

const hasMultipleImages = computed(() => normalizedImages.value.length > 1);

const activeImage = computed(() => {
  return normalizedImages.value[currentIndex.value] || {
    url: props.imageUrl,
    alt: props.imageAlt || '图片',
    name: props.imageAlt || '图片',
    key: props.imageUrl
  };
});

const activeImageUrl = computed(() => activeImage.value?.url || props.imageUrl || '');
const activeImageAlt = computed(() => activeImage.value?.alt || props.imageAlt || '图片');
const activeImageName = computed(() => activeImage.value?.name || activeImageAlt.value);

const imageStyle = computed(() => {
  return {
    transform: `translate3d(${translateX.value}px, ${translateY.value}px, 0) scale(${scale.value * (flipX.value ? -1 : 1)}, ${scale.value * (flipY.value ? -1 : 1)}) rotate(${rotate.value}deg)`,
    transition: isDragging.value ? 'none' : 'transform 0.3s ease, opacity 220ms ease, filter 220ms ease',
    transformOrigin: 'center center'
  };
});

function syncCurrentIndex(preferredUrl?: string) {
  const total = normalizedImages.value.length;
  if (!total) {
    currentIndex.value = 0;
    return;
  }

  const targetIndex = preferredUrl
    ? normalizedImages.value.findIndex(item => item.url === preferredUrl)
    : -1;

  if (targetIndex >= 0) {
    currentIndex.value = targetIndex;
    return;
  }

  if (currentIndex.value >= total) {
    currentIndex.value = total - 1;
  }
}

watch(() => props.open, (newVal) => {
  if (newVal) {
    rendered.value = true;
    visible.value = true;
    syncCurrentIndex(props.imageUrl);
    nextTick(() => {
      resetZoom();
      updateThumbnailPagination();
      scrollActiveThumbnailIntoView('auto');
    });
  } else if (rendered.value) {
    visible.value = false;
  }
}, { immediate: true });

watch(() => props.imageUrl, (newUrl) => {
  syncCurrentIndex(newUrl);
  if (props.open) {
    resetZoom();
  }
});

watch(normalizedImages, (newImages) => {
  const total = newImages.length;
  if (!total) {
    currentIndex.value = 0;
    return;
  }

  const currentUrl = activeImageUrl.value;
  const currentImageIndex = currentUrl
    ? newImages.findIndex(item => item.url === currentUrl)
    : -1;

  if (currentImageIndex >= 0) {
    currentIndex.value = currentImageIndex;
    return;
  }

  syncCurrentIndex(props.imageUrl);
});

function zoomIn() {
  scale.value *= 1.2;
}

function zoomOut() {
  scale.value /= 1.2;
  if (scale.value < 0.1) scale.value = 0.1;
}

function resetZoom() {
  scale.value = 0.72;
  rotate.value = 0;
  flipX.value = false;
  flipY.value = false;
  translateX.value = 0;
  translateY.value = 0;
}

function rotateLeft() {
  rotate.value -= 90;
}

function rotateRight() {
  rotate.value += 90;
}

function flipHorizontal() {
  flipX.value = !flipX.value;
}

function flipVertical() {
  flipY.value = !flipY.value;
}

function selectImage(index: number) {
  if (!normalizedImages.value.length) return;
  currentIndex.value = ((index % normalizedImages.value.length) + normalizedImages.value.length) % normalizedImages.value.length;
  resetZoom();
}

function showPrevImage() {
  selectImage(currentIndex.value - 1);
}

function showNextImage() {
  selectImage(currentIndex.value + 1);
}

function updateThumbnailPagination() {
  const el = thumbnailStripRef.value;
  if (!el) {
    canPageLeft.value = false;
    canPageRight.value = false;
    return;
  }

  const maxScrollLeft = Math.max(el.scrollWidth - el.clientWidth, 0);
  canPageLeft.value = el.scrollLeft > 4;
  canPageRight.value = el.scrollLeft < maxScrollLeft - 4;
}

function scrollThumbnailPage(direction: 'left' | 'right') {
  const el = thumbnailStripRef.value;
  if (!el) return;

  const distance = Math.max(el.clientWidth * 0.72, 180);
  const delta = direction === 'left' ? -distance : distance;
  el.scrollBy({
    left: delta,
    behavior: 'smooth'
  });
}

function scrollActiveThumbnailIntoView(behavior: ScrollBehavior = 'smooth') {
  const el = thumbnailStripRef.value;
  if (!el) return;

  const activeButton = el.querySelector('.image-thumbnail-item.is-active') as HTMLElement | null;
  activeButton?.scrollIntoView({
    behavior,
    inline: 'center',
    block: 'nearest'
  });
}

function handleWheel(event: WheelEvent) {
  event.preventDefault();
  if (event.deltaY < 0) {
    scale.value *= 1.1;
  } else {
    scale.value /= 1.1;
    if (scale.value < 0.1) scale.value = 0.1;
  }
}

function handleKeydown(event: KeyboardEvent) {
  if (!props.open) return;

  if (event.key === 'Escape') {
    closeModal();
    return;
  }

  if (!hasMultipleImages.value) return;

  if (event.key === 'ArrowLeft') {
    event.preventDefault();
    showPrevImage();
  } else if (event.key === 'ArrowRight') {
    event.preventDefault();
    showNextImage();
  }
}

watch(contentRef, (newEl, oldEl) => {
  if (oldEl) oldEl.removeEventListener('wheel', handleWheel);
  if (newEl) newEl.addEventListener('wheel', handleWheel, { passive: false });
});

watch(currentIndex, () => {
  nextTick(() => {
    scrollActiveThumbnailIntoView();
    updateThumbnailPagination();
  });
});

watch(normalizedImages, () => {
  nextTick(() => {
    updateThumbnailPagination();
  });
});

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    window.addEventListener('keydown', handleKeydown);
    window.addEventListener('resize', updateThumbnailPagination);
  } else {
    window.removeEventListener('keydown', handleKeydown);
    window.removeEventListener('resize', updateThumbnailPagination);
  }
});

onUnmounted(() => {
  if (contentRef.value) contentRef.value.removeEventListener('wheel', handleWheel);
  window.removeEventListener('keydown', handleKeydown);
  window.removeEventListener('resize', updateThumbnailPagination);
});

function startDrag(event: MouseEvent) {
  isDragging.value = true;
  dragStartX.value = event.clientX;
  dragStartY.value = event.clientY;
  startTranslateX.value = translateX.value;
  startTranslateY.value = translateY.value;
  event.preventDefault();
}

function onDrag(event: MouseEvent) {
  if (!isDragging.value) return;
  translateX.value = startTranslateX.value + (event.clientX - dragStartX.value);
  translateY.value = startTranslateY.value + (event.clientY - dragStartY.value);
  event.preventDefault();
}

function endDrag() {
  isDragging.value = false;
}

function downloadImage() {
  try {
    const getFileExtension = (url: string): string => {
      const pathname = new URL(url, window.location.href).pathname;
      const filename = pathname.split('/').pop() || '';
      const extension = filename.split('.').pop();
      if (extension && ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg'].includes(extension.toLowerCase())) {
        return extension;
      }
      return 'png';
    };

    const xhr = new XMLHttpRequest();
    xhr.open('GET', activeImageUrl.value, true);
    xhr.responseType = 'blob';

    xhr.onload = function() {
      if (this.status === 200) {
        const contentType = xhr.getResponseHeader('Content-Type') || '';
        let extension: string;
        if (contentType.includes('image/')) {
          extension = contentType.split('/')[1].split(';')[0];
        } else {
          extension = getFileExtension(activeImageUrl.value);
        }

        const blob = new Blob([this.response], { type: contentType || 'image/png' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        let filename = activeImageName.value || 'image';
        if (!filename.includes('.')) {
          filename = `${filename}.${extension}`;
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      }
    };

    xhr.send();
  } catch (error) {
    console.error('下载图片失败:', error);
    fallbackDownload();
  }
}

function fallbackDownload() {
  const link = document.createElement('a');
  link.href = activeImageUrl.value;
  const urlParts = activeImageUrl.value.split('/');
  link.download = urlParts[urlParts.length - 1].split('?')[0] || 'image.png';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

function closeModal() {
  emit('update:open', false);
}

function handleAfterLeave() {
  rendered.value = false;
}

defineExpose({});
</script>

<style scoped>
.simple-image-modal {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: stretch;
  justify-content: stretch;
}

.simple-image-modal-transition-enter-active,
.simple-image-modal-transition-leave-active {
  transition: opacity 180ms ease;
  pointer-events: none;
}

.simple-image-modal-transition-enter-from {
  opacity: 1;
}

.simple-image-modal-transition-leave-to {
  opacity: 0;
}

.simple-image-modal-transition-enter-active .simple-image-modal__panel,
.simple-image-modal-transition-leave-active .simple-image-modal__panel {
  transition:
    transform 180ms cubic-bezier(0.4, 0, 0.2, 1),
    opacity 180ms ease;
  will-change: transform, opacity;
}

.simple-image-modal-transition-enter-from .simple-image-modal__panel,
.simple-image-modal-transition-leave-to .simple-image-modal__panel {
  opacity: 0;
  transform: scale(0.92);
}

.simple-image-modal__backdrop {
  position: absolute;
  inset: 0;
  background-color: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(14px) saturate(140%);
  -webkit-backdrop-filter: blur(14px) saturate(140%);
  transition: opacity 180ms ease;
}

.simple-image-modal-transition-leave-to .simple-image-modal__backdrop {
  opacity: 0;
}

.simple-image-modal-transition-enter-active .simple-image-modal__backdrop,
.simple-image-modal-transition-leave-active .simple-image-modal__backdrop {
  transition: opacity 180ms ease;
}

.simple-image-modal__panel {
  position: relative;
  z-index: 1;
  display: block;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  transform-origin: center center;
}

.image-viewer-header {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  z-index: 18;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 16px;
  padding: 16px 16px 0;
  box-sizing: border-box;
}

.button-group {
  display: flex;
  gap: 12px;
  flex: 0 0 auto;
}

.simple-image-close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 12px;
  border: none;
  background-color: rgba(255, 255, 255, 0.76);
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
  color: #333;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.simple-image-close-btn:hover {
  background-color: rgba(255, 255, 255, 1);
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.12);
  transform: translateY(-1px);
}

.simple-image-close-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);
}

.image-viewer-status {
  position: absolute;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  min-width: 0;
  max-width: min(56vw, 620px);
  padding: 8px 12px;
  border-radius: 9999px;
  background-color: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(10px) saturate(140%);
  -webkit-backdrop-filter: blur(10px) saturate(140%);
  color: #0f172a;
  box-shadow: 0 3px 12px rgba(15, 23, 42, 0.08);
  animation: imageViewerStatusFloat 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}

.image-viewer-counter {
  flex: 0 0 auto;
  color: #475569;
  font-size: 12px;
  font-weight: 600;
}

.image-viewer-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
  font-size: 12px;
  font-weight: 500;
  line-height: 15px;
}

.image-viewer-content {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  overflow: hidden;
  padding: 88px 92px 200px;
  cursor: grab;
  box-sizing: border-box;
}

.image-viewer-content:active {
  cursor: grabbing;
}

.viewer-image {
  max-width: min(92vw, 1400px);
  max-height: min(72vh, 820px);
  width: auto;
  height: auto;
  object-fit: contain;
  border-radius: 24px;
  user-select: none;
  transform-origin: center center;
  display: block;
  will-change: transform, opacity;
}

.viewer-image-transition-enter-active,
.viewer-image-transition-leave-active {
  transition:
    opacity 220ms ease,
    transform 280ms cubic-bezier(0.22, 1, 0.36, 1),
    filter 220ms ease;
}

.viewer-image-transition-enter-from,
.viewer-image-transition-leave-to {
  opacity: 0;
  transform: scale(0.96);
  filter: blur(6px);
}

.image-viewer-nav {
  position: absolute;
  top: 50%;
  z-index: 15;
  width: 48px;
  height: 48px;
  margin-top: -24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #0f172a;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background-color 0.2s ease;
}

.image-viewer-nav:hover {
  transform: translateY(-1px);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
}

.image-viewer-nav--prev {
  left: 28px;
}

.image-viewer-nav--next {
  right: 28px;
}

.image-viewer-nav :deep(svg) {
  font-size: 18px;
}

.image-viewer-bottom {
  position: absolute;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  width: min(84vw, 980px);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  z-index: 20;
  animation: imageViewerBottomRise 0.7s cubic-bezier(0.22, 1, 0.36, 1);
}

.image-toolbar {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 9999px;
  user-select: none;
  background: transparent;
  border: none;
  box-shadow: none;
  isolation: isolate;
}

.image-toolbar::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  background: linear-gradient(
    135deg,
    rgba(255, 255, 255, 0.82) 0%,
    rgba(255, 255, 255, 0.76) 50%,
    rgba(248, 250, 252, 0.72) 100%
  );
  background-size: 200% 200%;
  animation: imageToolbarLiquidShift 10s ease-in-out infinite;
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow:
    0 5px 14px rgba(15, 23, 42, 0.11),
    inset 0 1px 0 rgba(255, 255, 255, 0.75);
  border-radius: 9999px;
}

@keyframes imageToolbarLiquidShift {
  0% {
    background-position: 30% 40%;
  }
  50% {
    background-position: 70% 60%;
  }
  100% {
    background-position: 30% 40%;
  }
}

.image-thumbnail-strip {
  position: relative;
  width: 100%;
  display: block;
  padding: 16px 12px 10px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.11);
  animation: imageThumbnailStripReveal 0.8s cubic-bezier(0.22, 1, 0.36, 1);
  overflow: hidden;
}

.image-thumbnail-viewport {
  width: 100%;
  min-width: 0;
  overflow-x: auto;
  overflow-y: hidden;
  scroll-behavior: smooth;
  scroll-padding-inline: 52px;
  scrollbar-width: none;
  -ms-overflow-style: none;
  mask-image: linear-gradient(90deg, transparent 0, #000 34px, #000 calc(100% - 34px), transparent 100%);
  -webkit-mask-image: linear-gradient(90deg, transparent 0, #000 34px, #000 calc(100% - 34px), transparent 100%);
  padding-top: 12px;
  padding-bottom: 14px;
  margin-top: -12px;
  margin-bottom: -14px;
}

.image-thumbnail-viewport::-webkit-scrollbar {
  display: none;
}

.image-thumbnail-track {
  width: max-content;
  min-width: 100%;
  margin: 0 auto;
  padding: 0 52px;
  box-sizing: border-box;
  display: flex;
  justify-content: center;
  gap: 10px;
}

.image-thumbnail-page-btn {
  position: absolute;
  top: 50%;
  z-index: 3;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 9999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94) 0%, rgba(248, 250, 252, 0.86) 100%);
  color: #334155;
  box-shadow:
    0 12px 26px rgba(15, 23, 42, 0.16),
    0 2px 8px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  cursor: pointer;
  transform: translateY(-50%);
  transition:
    transform 0.24s ease,
    box-shadow 0.24s ease,
    opacity 0.24s ease,
    background-color 0.24s ease;
  overflow: hidden;
}

.image-thumbnail-page-btn--prev {
  left: 14px;
}

.image-thumbnail-page-btn--next {
  right: 14px;
}

.image-thumbnail-page-btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 20%, rgba(59, 130, 246, 0.16) 0%, rgba(59, 130, 246, 0) 64%);
  opacity: 0;
  transition: opacity 0.24s ease;
}

.image-thumbnail-page-btn:hover:not(.is-disabled) {
  transform: translateY(-50%) scale(1.06);
  box-shadow:
    0 16px 30px rgba(15, 23, 42, 0.18),
    0 4px 10px rgba(59, 130, 246, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.84);
}

.image-thumbnail-page-btn:hover:not(.is-disabled)::before {
  opacity: 1;
}

.image-thumbnail-page-btn.is-disabled {
  opacity: 0.36;
  cursor: default;
  box-shadow:
    0 4px 12px rgba(15, 23, 42, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.55);
}

.image-thumbnail-page-btn :deep(svg) {
  position: relative;
  z-index: 1;
  font-size: 16px;
}

.image-thumbnail-item {
  position: relative;
  flex: 0 0 auto;
  width: 68px;
  height: 68px;
  padding: 0;
  border: 2px solid transparent;
  border-radius: 14px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: transform 0.28s ease, border-color 0.28s ease, box-shadow 0.28s ease, filter 0.28s ease;
  animation: imageThumbnailItemIn 0.5s cubic-bezier(0.22, 1, 0.36, 1);
}

.image-thumbnail-item:hover {
  transform: translateY(-4px) scale(1.03);
  border-color: rgba(59, 130, 246, 0.35);
}

.image-thumbnail-item.is-active {
  border-color: #3b82f6;
  box-shadow: 0 8px 18px rgba(59, 130, 246, 0.18);
  animation: imageThumbnailPulse 1.8s ease-in-out infinite;
}

.image-thumbnail-item::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent 0%, rgba(255, 255, 255, 0.35) 45%, transparent 100%);
  transform: translateX(-130%);
  pointer-events: none;
}

.image-thumbnail-item:hover::after {
  animation: imageThumbnailShine 0.7s ease;
}

.image-thumbnail {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.28s ease;
}

.image-thumbnail-item:hover .image-thumbnail,
.image-thumbnail-item.is-active .image-thumbnail {
  transform: scale(1.06);
}

.toolbar-btn {
  position: relative;
  z-index: 10;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: none;
  background: transparent;
  color: #334155;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.toolbar-btn:hover {
  background: rgba(255, 255, 255, 0.82);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.toolbar-btn:active {
  transform: translateY(0);
  background: rgba(255, 255, 255, 0.92);
}

.toolbar-btn :deep(svg) {
  font-size: 15px;
}

.divider {
  width: 1px;
  height: 14px;
  background-color: rgba(148, 163, 184, 0.55);
  margin: 0 3px;
  z-index: 10;
}

.vertical-swap {
  transform: rotate(90deg);
}

.image-viewer-status-transition-enter-active,
.image-viewer-status-transition-leave-active {
  transition:
    opacity 200ms ease,
    transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.image-viewer-status-transition-enter-from,
.image-viewer-status-transition-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-8px) scale(0.96);
}

@keyframes imageViewerStatusFloat {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(-10px) scale(0.96);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0) scale(1);
  }
}

@keyframes imageViewerBottomRise {
  0% {
    opacity: 0;
    transform: translateX(-50%) translateY(14px);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

@keyframes imageThumbnailStripReveal {
  0% {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes imageThumbnailItemIn {
  0% {
    opacity: 0;
    transform: translateY(8px) scale(0.94);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes imageThumbnailPulse {
  0%, 100% {
    box-shadow: 0 8px 18px rgba(59, 130, 246, 0.18);
  }
  50% {
    box-shadow: 0 11px 24px rgba(59, 130, 246, 0.28);
  }
}

@keyframes imageThumbnailShine {
  0% {
    transform: translateX(-130%);
  }
  100% {
    transform: translateX(130%);
  }
}

@media (max-width: 900px) {
  .image-viewer-content {
    padding: 88px 48px 194px;
  }

  .image-viewer-nav--prev {
    left: 14px;
  }

  .image-viewer-nav--next {
    right: 14px;
  }
}

@media (max-width: 640px) {
  .image-viewer-content {
    padding: 84px 20px 188px;
  }

  .viewer-image {
    max-height: min(64vh, 620px);
  }

  .image-viewer-nav {
    width: 42px;
    height: 42px;
    margin-top: -21px;
  }

  .image-viewer-status {
    max-width: calc(100vw - 136px);
  }

  .image-thumbnail-item {
    width: 58px;
    height: 58px;
    border-radius: 12px;
  }

  .image-thumbnail-strip {
    padding: 14px 10px 8px;
  }

  .image-thumbnail-page-btn {
    width: 36px;
    height: 36px;
  }

  .image-thumbnail-page-btn--prev {
    left: 10px;
  }

  .image-thumbnail-page-btn--next {
    right: 10px;
  }

  .image-thumbnail-viewport {
    scroll-padding-inline: 44px;
  }

  .image-thumbnail-track {
    padding: 0 44px;
  }
}
</style>
