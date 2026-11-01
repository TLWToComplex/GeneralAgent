<template>
<div v-if="messageImageFiles.length > 0" class="message-image-gallery" :class="{
            'is-multi': hasMultipleImageFiles,
            'is-screenshot-reveal': shouldApplyScreenshotRevealClass
          }">
            <div v-if="hasMultipleImageFiles" class="message-image-stage"
              :class="{ 'is-switching': isMessageImageSwitching }">
              <div class="message-image-stage-stack">
                <button v-for="card in visibleImageCards" :key="card.index" type="button"
                  :ref="element => setCardElement(card.index, element)"
                  :tabindex="Math.abs(card.offset) > 1 ? -1 : 0"
                  :aria-hidden="Math.abs(card.offset) > 1"
                  class="message-image-card" :class="getMessageImageCardClasses(card)"
                  :style="getMessageImageCardStyle(card)"
                  :aria-label="card.index === activeMessageImageIndex ? `查看图片 ${card.file.name || card.index + 1}` : `切换到图片 ${card.file.name || card.index + 1}`"
                  @click.stop="handleMessageImageCardClick(card)">
                  <span class="message-image-card-glow"></span>
                  <img :src="getImagePreviewUrl(card.file)" :alt="card.file.name || 'image'"
                    class="message-inline-image is-stacked" />
                </button>
              </div>
              <div class="message-image-stage-shadow"></div>
            </div>

            <button v-else type="button" class="message-image-single"
              @click.stop="handleImageFileClick(messageImageFiles[0])">
              <img :src="getImagePreviewUrl(messageImageFiles[0])" :alt="messageImageFiles[0]?.name || 'image'"
                class="message-inline-image" />
            </button>
            <div v-if="isScreenshotRevealActive" class="message-image-reveal-flash" aria-hidden="true"></div>

            <div class="message-image-meta-bar">
              <span v-if="hasMultipleImageFiles" class="message-image-counter">
                {{ activeMessageImageIndex + 1 }} / {{ messageImageFiles.length }}
              </span>
              <span class="message-image-name">
                {{ activeMessageImage?.name || (messageImageFiles.length > 1 ? `${messageImageFiles.length} 张图片` : '图片')
                }}
              </span>
            </div>

            <div v-if="hasMultipleImageFiles" class="message-image-dots" role="group" aria-label="图片切换">
              <button v-for="(file, index) in messageImageFiles" :key="index" type="button"
                class="message-image-dot" :class="{ 'is-active': index === activeMessageImageIndex }"
                :aria-label="`切换到图片 ${file.name || index + 1}`" :aria-pressed="index === activeMessageImageIndex"
                @click.stop="handleMessageImageDotClick(index)"></button>
            </div>
          </div>
</template>
<script setup lang="ts">
import { computed, ref, watch, onUnmounted, nextTick } from 'vue';
import { getImagePreviewUrl } from '@/utils/conversationImages';
const props = withDefaults(defineProps<{
  images: Array<{ name?: string; url?: string; [key: string]: any }>;
  shouldApplyScreenshotRevealClass?: boolean;
  isScreenshotRevealActive?: boolean;
}>(), { shouldApplyScreenshotRevealClass: false, isScreenshotRevealActive: false });
const emit = defineEmits<{ (event: 'image-click', image: any): void }>();
const messageImageFiles = computed(() => props.images);
const messageImageEntries = computed(() => props.images.map((file, index) => ({ file, index })));
const hasMultipleImageFiles = computed(() => props.images.length > 1);
const activeMessageImageIndex = ref(0);
const isMessageImageSwitching = ref(false);
const cardElements = new Map<number, HTMLElement>();
const cardAnimations = new Map<number, Animation>();
let motionRevision = 0;
function setCardElement(index: number, element: unknown) {
  if (element instanceof HTMLElement) cardElements.set(index, element);
  else cardElements.delete(index);
}
function cancelMotion() {
  motionRevision++;
  cardAnimations.forEach(animation => animation.cancel());
  cardAnimations.clear();
  isMessageImageSwitching.value = false;
}
const handleImageFileClick = (file: any) => emit('image-click', file);
onUnmounted(cancelMotion);
const getDefaultImageIndex = (length: number) => {
  if (length <= 1) return 0;
  return Math.floor(length / 2);
};

const clampMessageImageIndex = (index: number) => {
  const total = messageImageFiles.value.length;
  if (total <= 0) return 0;
  return Math.min(Math.max(index, 0), total - 1);
};

watch(() => messageImageFiles.value.length, (length, prevLength) => {
  cancelMotion();
  if (!length) {
    activeMessageImageIndex.value = 0;
    return;
  }

  if (!prevLength) {
    activeMessageImageIndex.value = getDefaultImageIndex(length);
    return;
  }

  activeMessageImageIndex.value = clampMessageImageIndex(activeMessageImageIndex.value);
}, { immediate: true });

const activeMessageImage = computed(() => {
  return messageImageFiles.value[clampMessageImageIndex(activeMessageImageIndex.value)] || null;
});

type MessageImageCardSlot = 'far-left' | 'left' | 'center' | 'right' | 'far-right';

const getCircularImageIndex = (index: number, total: number) => {
  if (total <= 0) return 0;
  return ((index % total) + total) % total;
};

// Keep DOM order and card identity stable, including cards passing behind the deck.
const visibleImageCards = computed(() => {
  const total = messageImageFiles.value.length;
  return messageImageEntries.value.map(({ file, index }) => {
    let offset = index - activeMessageImageIndex.value;
    if (total > 2) {
      offset = getCircularImageIndex(offset, total);
      if (offset > total / 2) offset -= total;
    }
    const slot: MessageImageCardSlot = offset === 0 ? 'center' : offset === -1 ? 'left' : offset === 1 ? 'right' : offset < 0 ? 'far-left' : 'far-right';
    return { file, index, slot, offset };
  });
});

async function setActiveMessageImageIndex(index: number) {
  const nextIndex = clampMessageImageIndex(index);
  if (nextIndex === activeMessageImageIndex.value) return;
  // Sample before cancelling: interrupted motion starts at the visible position.
  const previous = new Map(visibleImageCards.value.map(card => {
    const element = cardElements.get(card.index);
    const style = element ? getComputedStyle(element) : null;
    return [card.index, { offset: card.offset, transform: style?.transform, opacity: style?.opacity }];
  }));
  cancelMotion();
  const revision = motionRevision;
  activeMessageImageIndex.value = nextIndex;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduceMotion) return;
  isMessageImageSwitching.value = true;
  await nextTick();
  if (revision !== motionRevision) return;
  const animations: Animation[] = [];
  visibleImageCards.value.forEach(card => {
    const element = cardElements.get(card.index);
    const from = previous.get(card.index);
    if (!element || !from?.transform) return;
    if (Math.abs(from.offset) > 1 && Math.abs(card.offset) > 1) return;
    const target = getComputedStyle(element);
    const frames: Keyframe[] = [{ transform: from.transform, opacity: from.opacity }];
    // A wrapping card follows the back of the deck instead of crossing its face.
    if (from.offset * card.offset < 0 && Math.abs(from.offset - card.offset) > 1) {
      frames.push({ transform: 'translate3d(-50%, 22px, -180px) scale(0.76) rotateZ(0deg)', opacity: 0.12, offset: 0.5 });
    }
    frames.push({ transform: target.transform, opacity: target.opacity });
    const animation = element.animate(frames, { duration: 460, easing: 'cubic-bezier(0.22, 0.72, 0.2, 1)' });
    cardAnimations.set(card.index, animation);
    animations.push(animation);
  });
  await Promise.allSettled(animations.map(animation => animation.finished));
  if (revision !== motionRevision) return;
  cardAnimations.clear();
  isMessageImageSwitching.value = false;
}

const setActiveMessageImageCircular = (index: number) => {
  const total = messageImageFiles.value.length;
  void setActiveMessageImageIndex(total > 2 ? getCircularImageIndex(index, total) : index);
};

const handleMessageImageCardClick = (card: { file: any; index: number; slot: MessageImageCardSlot }) => {
  if (card.slot === 'center' || card.index === activeMessageImageIndex.value) {
    handleImageFileClick(messageImageFiles.value[card.index]);
    return;
  }

  if (card.slot === 'left') {
    setActiveMessageImageCircular(activeMessageImageIndex.value - 1);
    return;
  }

  if (card.slot === 'right') {
    setActiveMessageImageCircular(activeMessageImageIndex.value + 1);
    return;
  }

  if (card.slot === 'far-left') {
    setActiveMessageImageCircular(activeMessageImageIndex.value - 2);
    return;
  }

  if (card.slot === 'far-right') {
    setActiveMessageImageCircular(activeMessageImageIndex.value + 2);
    return;
  }

  setActiveMessageImageCircular(card.index);
};

const handleMessageImageDotClick = (index: number) => {
  if (messageImageFiles.value.length > 2) {
    setActiveMessageImageCircular(index);
    return;
  }

  setActiveMessageImageIndex(index);
};

const getMessageImageCardClasses = (card: { slot: MessageImageCardSlot; index: number }) => {
  return {
    'is-active': card.slot === 'center',
    'is-far-left': card?.slot === 'far-left',
    'is-left': card?.slot === 'left',
    'is-right': card?.slot === 'right',
    'is-far-right': card?.slot === 'far-right'
  };
};

const getMessageImageCardStyle = (card: { slot: MessageImageCardSlot; index: number }) => {
  const slotMap: Record<MessageImageCardSlot, {
    translateX: number;
    translateY: number;
    scale: number;
    rotate: number;
    opacity: number;
    blur: number;
    zIndex: number;
  }> = {
    'far-left': { translateX: -146, translateY: 18, scale: 0.72, rotate: -13, opacity: 0, blur: 0.4, zIndex: 10 },
    'left': { translateX: -76, translateY: 10, scale: 0.86, rotate: -10, opacity: 0.72, blur: 0, zIndex: 22 },
    'center': { translateX: 0, translateY: 0, scale: 0.96, rotate: 0, opacity: 1, blur: 0, zIndex: 38 },
    'right': { translateX: 76, translateY: 10, scale: 0.86, rotate: 10, opacity: 0.72, blur: 0, zIndex: 22 },
    'far-right': { translateX: 146, translateY: 18, scale: 0.72, rotate: 13, opacity: 0, blur: 0.4, zIndex: 10 }
  };

  const slotStyle = slotMap[card.slot] || slotMap.center;

  return {
    '--card-translate-x': `${slotStyle.translateX}px`,
    '--card-translate-y': `${slotStyle.translateY}px`,
    '--card-scale': String(slotStyle.scale),
    '--card-rotate': `${slotStyle.rotate}deg`,
    '--card-opacity': String(slotStyle.opacity),
    '--card-blur': `${slotStyle.blur}px`,
    '--card-depth': card.slot === 'center' ? '48px' : Math.abs(slotStyle.translateX) > 100 ? '-120px' : '0px'
  };
};

</script>
<style scoped>
.message-image-gallery {
  position: relative;
  width: 235px;
  max-width: 235px;
  align-self: flex-start;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px 12px 10px;
  border-radius: 32px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0) 52%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.96));
  box-shadow:
    0 18px 40px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  box-sizing: border-box;
  overflow: hidden;
  animation: message-image-gallery-enter 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: transform, opacity;
}

:global(.message-user) .message-image-gallery {
  align-self: flex-end;
  margin-left: auto;
}

.message-image-gallery.is-screenshot-reveal {
  animation: screenshot-image-reveal 0.8s cubic-bezier(0.2, 0.8, 0.2, 1) both;
}

.message-image-gallery.is-screenshot-reveal .message-inline-image {
  animation: screenshot-image-clarify 0.86s cubic-bezier(0.22, 1, 0.36, 1) both;
}

.message-image-reveal-flash {
  position: absolute;
  inset: 12px;
  border-radius: 24px;
  background:
    linear-gradient(125deg, rgba(255, 255, 255, 0) 18%, rgba(255, 255, 255, 0.72) 46%, rgba(255, 255, 255, 0) 72%),
    radial-gradient(circle at center, rgba(191, 219, 254, 0.34), rgba(191, 219, 254, 0) 68%);
  mix-blend-mode: screen;
  pointer-events: none;
  opacity: 0;
  animation: screenshot-reveal-flash 0.9s ease-out forwards;
  z-index: 4;
}

.message-image-gallery.is-multi {
  gap: 6px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
  overflow: visible;
}

.message-image-stage {
  position: relative;
  width: 100%;
  height: 236px;
  overflow: visible;
  isolation: isolate;
  perspective: 1200px;
}

.message-image-stage-stack {
  position: relative;
  width: 100%;
  height: 100%;
  transform-style: preserve-3d;
}

.message-image-stage-shadow {
  position: absolute;
  left: 50%;
  bottom: 6px;
  width: 170px;
  height: 26px;
  transform: translateX(-50%);
  background: radial-gradient(circle, rgba(15, 23, 42, 0.18) 0%, rgba(15, 23, 42, 0) 72%);
  filter: blur(14px);
  pointer-events: none;
  z-index: 0;
  transition: transform 0.42s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.42s ease, filter 0.42s ease;
}

.message-image-stage.is-switching .message-image-stage-shadow {
  transform: translateX(-50%) scale(1.08);
  opacity: 0.94;
  filter: blur(16px);
}

.message-image-card {
  position: absolute;
  top: 18px;
  left: 50%;
  width: 196px;
  height: 184px;
  padding: 0;
  border: none;
  border-radius: 30px;
  background: transparent;
  overflow: hidden;
  cursor: pointer;
  z-index: 1;
  opacity: var(--card-opacity);
  transform:
    translate3d(calc(-50% + var(--card-translate-x)), var(--card-translate-y), var(--card-depth)) scale(var(--card-scale)) rotateZ(var(--card-rotate));
  filter: blur(var(--card-blur)) saturate(0.97);
  transition: box-shadow 180ms ease, filter 180ms ease;
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.14);
  will-change: transform, filter, opacity;
  backface-visibility: hidden;
  transform-style: preserve-3d;
}

.message-image-card:hover {
  filter: blur(0) saturate(1.04) brightness(1.02);
  box-shadow:
    0 20px 34px rgba(15, 23, 42, 0.18),
    0 0 0 1px rgba(255, 255, 255, 0.68) inset,
    0 0 0 6px rgba(99, 102, 241, 0.06);
}

.message-image-card.is-active {
  box-shadow:
    0 22px 42px rgba(15, 23, 42, 0.16),
    0 0 0 1px rgba(255, 255, 255, 0.62) inset;
}

.message-image-card.is-far-left,
.message-image-card.is-far-right {
  pointer-events: none;
}

.message-image-card-glow {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 50% 18%, rgba(255, 255, 255, 0.34), rgba(255, 255, 255, 0) 42%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0));
  pointer-events: none;
  z-index: 2;
  opacity: 0.72;
  transition: opacity 0.28s ease, transform 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}

.message-image-card:hover .message-image-card-glow {
  opacity: 1;
  transform: scale(1.02);
}

.message-image-single {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 0.92;
  padding: 0;
  border: none;
  background: transparent;
  border-radius: 24px;
  overflow: hidden;
  cursor: pointer;
  box-shadow: 0 14px 28px rgba(15, 23, 42, 0.12);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: transform, box-shadow;
}

.message-image-single:hover {
  transform: translateY(-2px);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.14);
}

.message-inline-image {
  display: block;
  width: 100%;
  height: 100%;
  max-width: 100%;
  max-height: none;
  object-fit: cover;
  object-position: center;
  border-radius: 16px;
  background: #f8fafc;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  transform: translateZ(0);
  backface-visibility: hidden;
  will-change: transform, opacity, filter;
}

.message-inline-image.is-stacked {
  width: 100%;
  height: 100%;
  max-height: none;
  border-radius: 30px;
}

.message-image-meta-bar {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 0;
  padding: 0 10px;
}

.message-image-gallery.is-multi .message-image-meta-bar {
  padding: 0 62px;
  margin-top: -20px;
}

.message-image-name {
  display: block;
  width: 100%;
  min-width: 0;
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
  text-align: center;
}

.message-image-counter {
  position: static;
  flex-shrink: 0;
  padding: 3px 9px;
  border-radius: 999px;
  background: rgba(15, 23, 42, 0.06);
  color: #475569;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.message-image-dots {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  min-height: 10px;
}

.message-image-gallery.is-multi .message-image-dots {
  padding-bottom: 2px;
}

.message-image-dot {
  width: 7px;
  height: 7px;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: rgba(100, 116, 139, 0.24);
  cursor: pointer;
  transition: transform 0.22s ease, background-color 0.22s ease, width 0.22s ease;
}

.message-image-dot:hover {
  transform: scale(1.15);
  background: rgba(59, 130, 246, 0.34);
}

.message-image-dot.is-active {
  width: 20px;
  background: linear-gradient(90deg, #7c93ff, #5b7cff);
}


@keyframes message-image-gallery-enter {
  0% {
    opacity: 0;
    transform: translateY(10px) scale(0.96);
  }

  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}


@keyframes screenshot-image-reveal {
  0% {
    opacity: 0.4;
    transform: translateY(12px) scale(0.95);
    filter: saturate(0.88);
  }

  55% {
    opacity: 1;
    transform: translateY(0) scale(1.015);
    filter: saturate(1.04);
  }

  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: saturate(1);
  }
}
@keyframes screenshot-image-clarify {
  0% {
    opacity: 0.18;
    filter: blur(10px) brightness(1.14) saturate(1.08);
    clip-path: inset(0 0 100% 0 round 20px);
  }

  50% {
    opacity: 0.88;
    filter: blur(2px) brightness(1.05) saturate(1.04);
  }

  100% {
    opacity: 1;
    filter: blur(0) brightness(1) saturate(1);
    clip-path: inset(0 0 0 0 round 20px);
  }
}
@keyframes screenshot-reveal-flash {
  0% {
    opacity: 0;
    transform: translateX(-28%);
  }

  18% {
    opacity: 0.92;
  }

  100% {
    opacity: 0;
    transform: translateX(34%);
  }
}
@media (prefers-reduced-motion: reduce) { .message-image-gallery, .message-image-card, .message-image-card.is-active, .message-image-stage-shadow, .message-image-reveal-flash { animation: none !important; transition: none !important; } }
@media (max-width: 768px) {
.message-image-gallery {
    width: 320px;
    max-width: 100%;
  }
.message-image-stage {
    height: 214px;
  }
.message-image-card {
    width: 176px;
    height: 164px;
  }
}
.message-image-gallery { line-height: normal; }
.message-image-card:focus-visible, .message-image-dot:focus-visible, .message-image-single:focus-visible { outline: 2px solid #6379dc; outline-offset: 4px; }
.message-image-gallery .message-inline-image { margin: 0; border: 0; box-shadow: none; }
</style>
