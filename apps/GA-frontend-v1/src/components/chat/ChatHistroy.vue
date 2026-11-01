<template>
  <div v-if="messages.length > 0" class="chat-history-container" :class="chatWindowStyle === 'conversation' ? 'conversation-mode' : 'document-mode'">
    <div ref="chatContainer" class="chat-messages" :class="{ 'toolbar-visible': inputToolbarVisible }" :style="chatMessagesStyle" @wheel.passive="onWheel">
      <div ref="chatContentWrapper" class="chat-content-wrapper">
        <chat-message
            v-for="(message, index) in renderedMessages"
            :key="getMessageKey(message)"
            :message="message"
            :message-index="index"
            :is-selection-mode="isSelectionMode"
            :is-selected="selectedMessages.has(getMessageId(message))"
            :selection-position="getSelectionPosition(message, index)"
            :active-artifact-id="activeArtifactId"
            @selection-changed="handleMessageSelection"
            @selection-mode-changed="handleSelectionModeChanged"
            @open-artifact="handleOpenArtifact"
        />
      </div>
    </div>

    <!-- 滚动到底部按钮 -->
    <div v-if="showScrollButton" class="scroll-to-bottom" :class="{ 'visible': scrollButtonVisible, 'toolbar-active': inputToolbarVisible, 'panel-expanded': inputToolbarExpanded }" :style="scrollButtonStyle">
      <a-button type="primary" shape="circle" @click="scrollToBottomManually" class="scroll-button">
        <template #icon><DownOutlined /></template>
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Message } from '@/types/mcp';
import { useChatStore } from '@/stores/chat-store';
import { DownOutlined } from '@ant-design/icons-vue';
import ChatMessage from '@/components/chat/ChatMessage.vue';
import NotificationService from '@/utils/NotificationService';
import { copyText } from '@/utils/clipboard';
import { isNestedScrollTarget } from '@/utils/scrollTarget';
import StorageService from '@/utils/StorageService';
import { yieldToBrowser } from '@/utils/yieldToBrowser';

type ChatWindowStyle = 'document' | 'conversation';
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useThrottleFn, useDebounceFn } from '@vueuse/core';

const emit = defineEmits<{
  'selection-mode-changed': [isSelectionMode: boolean]
  'all-selected-changed': [isAllSelected: boolean, hasSelection: boolean]
  'selection-changed': [messageId: string, selected: boolean]
  'open-artifact': [payload: { code: any; lang: string; id?: string; title?: string; isComplete?: boolean; downloadUrl?: string; autoOpen?: boolean }]
}>();

function handleOpenArtifact(payload: { code: any; lang: string; id?: string; title?: string; isComplete?: boolean; downloadUrl?: string; autoOpen?: boolean }) {
  emit('open-artifact', payload);
}

const props = defineProps<{
  historySessionId?: string;
  isAgentMode?: boolean;
  inputToolbarVisible?: boolean;
  inputToolbarExpanded?: boolean;
  inputToolbarPanelHeight?: number;
  inputHeight?: number;
  activeArtifactId?: string;
}>();

const scrollButtonStyle = computed(() => {
  const inputH = props.inputHeight || 0;
  let bottom = 120;
  const nonAgentBottomCompensation = props.isAgentMode ? 0 : 12;

  if (inputH > 0) {
     bottom = inputH + 20; 
  }

  if (props.inputToolbarVisible) {
      bottom += 35;
  }

  if (props.inputToolbarExpanded) {
    const height = props.inputToolbarPanelHeight || 0;
    bottom += height;
  }

  // 非 agent 模式让回底按钮更靠近底部；agent 模式保持现状
  bottom = Math.max(0, bottom - nonAgentBottomCompensation);
  
  if (inputH > 0 || props.inputToolbarExpanded || props.inputToolbarVisible) {
      return { bottom: `${bottom}px` };
  }
  
  return {};
});

const chatMessagesStyle = computed(() => {
    const inputH = props.inputHeight || 0;
    let paddingBottom = 130;
    const nonAgentPaddingCompensation = props.isAgentMode ? 0 : 26;

    if (inputH > 0) {
        paddingBottom = inputH + 5;
    }
    
    if (props.inputToolbarVisible) {
        paddingBottom += 30;
    }

    if (props.inputToolbarExpanded) {
        const height = props.inputToolbarPanelHeight || 0;
        paddingBottom += height;
    }

    // 非 agent 模式收紧消息区与输入框底部留白；agent 模式保持现状
    paddingBottom = Math.max(0, paddingBottom - nonAgentPaddingCompensation);

    if (inputH > 0 || props.inputToolbarExpanded || props.inputToolbarVisible) {
        return { paddingBottom: `${paddingBottom}px` };
    }

    return {};
});

const chatStore = useChatStore();
const chatContainer = ref<HTMLElement | null>(null);
const isAutoScroll = ref<boolean>(true);
const showScrollButton = ref<boolean>(false);
const scrollButtonVisible = ref<boolean>(false);

const isSelectionMode = ref(false)
const selectedMessages = ref<Set<string>>(new Set())

const initialPrefs = StorageService.get<{ chatWindowStyle?: ChatWindowStyle }>('mcp-user-preferences') || {}
const chatWindowStyle = ref<ChatWindowStyle>(initialPrefs.chatWindowStyle ?? 'conversation')

let uiKeySeed = 0;
function createUiKey(): string {
  uiKeySeed += 1;
  const uuid = (globalThis as any)?.crypto?.randomUUID?.();
  if (typeof uuid === 'string' && uuid) return uuid;
  return `${Date.now()}-${uiKeySeed}-${Math.random().toString(16).slice(2)}`;
}

const lastScrollTop = ref(0);
const lastScrollHeight = ref(0);

const STRICT_BOTTOM_EPS = 50;
const autoScrollLockUntil = ref(0);
const suppressScrollHandler = ref(false);
const userScrolling = ref(false);
let userScrollDebounceTimer: number | null = null;
const isAutoScrolling = ref(false);
const hoveringScrollbar = ref(false);

const pointerDown = ref(false);
const lastPointerPos = ref<{ x: number; y: number }>({ x: 0, y: 0 });
const SCROLLBAR_GUTTER_WIDTH = 20;
function isPointerInScrollbarGutter(el: HTMLElement): boolean {
  const rect = el.getBoundingClientRect();
  const x = lastPointerPos.value.x;
  const y = lastPointerPos.value.y;
  const withinY = y >= rect.top && y <= rect.bottom;
  const withinGutterX = x >= rect.right - SCROLLBAR_GUTTER_WIDTH && x <= rect.right;
  return withinY && withinGutterX;
}

function isAtStrictBottom(el: HTMLElement) {
  const distance = Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight);
  return distance <= STRICT_BOTTOM_EPS;
}

const chatContentWrapper = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;
let pendingScrollRAF: number | null = null;
let gradualScrollRAF: number | null = null;

function snapToBottom(el: HTMLElement) {
  const targetTop = Math.max(0, el.scrollHeight - el.clientHeight);
  el.scrollTop = targetTop;
}

function stopGradualScrollToBottom() {
  if (gradualScrollRAF !== null) {
    cancelAnimationFrame(gradualScrollRAF);
    gradualScrollRAF = null;
  }
}

function animateScrollToBottom(duration = 420) {
  if (!chatContainer.value) return;
  if (shouldSuppressScroll()) return;

  const el = chatContainer.value;
  const startTop = el.scrollTop;
  const targetTop = Math.max(0, el.scrollHeight - el.clientHeight);

  if (targetTop - startTop <= 1) {
    snapToBottom(el);
    hideScrollButtonDebounced();
    return;
  }

  stopGradualScrollToBottom();
  isAutoScrolling.value = true;
  suppressScrollHandler.value = true;
  if (scrollbarHideTimer) {
    clearTimeout(scrollbarHideTimer);
    scrollbarHideTimer = null;
  }
  el.classList.add('hide-scrollbar');

  const startTime = performance.now();
  const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3);

  const step = (now: number) => {
    if (!chatContainer.value) {
      stopGradualScrollToBottom();
      isAutoScrolling.value = false;
      return;
    }

    const currentEl = chatContainer.value;
    const latestTargetTop = Math.max(0, currentEl.scrollHeight - currentEl.clientHeight);
    const progress = Math.min((now - startTime) / duration, 1);
    const eased = easeOutCubic(progress);
    const nextTop = startTop + (latestTargetTop - startTop) * eased;

    suppressScrollHandler.value = true;
    currentEl.scrollTop = nextTop;
    lastScrollTop.value = currentEl.scrollTop;
    lastScrollHeight.value = currentEl.scrollHeight;

    if (progress < 1 && Math.abs(latestTargetTop - currentEl.scrollTop) > 1) {
      gradualScrollRAF = requestAnimationFrame(step);
      return;
    }

    suppressScrollHandler.value = true;
    snapToBottom(currentEl);
    hideScrollButtonDebounced();
    isAutoScrolling.value = false;
    gradualScrollRAF = null;
  };

  gradualScrollRAF = requestAnimationFrame(step);
}


function shouldSuppressScroll(): boolean {
  if (messages.value.length === 0) return false;
  const lastMsg = messages.value[messages.value.length - 1];
  
  if (lastMsg.role === 'assistant') {
    const content = lastMsg.content || '';
    
    const backtickMatches = content.match(/```/g);
    if (!backtickMatches || backtickMatches.length % 2 === 0) {
      return false;
    }

    const lastOpenIndex = content.lastIndexOf('```');
    if (lastOpenIndex !== -1) {
       const followingText = content.slice(lastOpenIndex + 3, lastOpenIndex + 50).trim().toLowerCase();
       
       if (['mermaid', 'html', 'svg'].some(t => followingText.startsWith(t))) {
         return true;
       }
    }
  }
  return false;
}

function scheduleScrollToBottom() {
  if (!chatContainer.value) return;
  
  if (shouldSuppressScroll()) {
    return;
  }

  if (pendingScrollRAF !== null) {
    cancelAnimationFrame(pendingScrollRAF);
  }
  pendingScrollRAF = requestAnimationFrame(() => {
    try {
      const el = chatContainer.value!;
      isAutoScrolling.value = true;
      if (scrollbarHideTimer) { clearTimeout(scrollbarHideTimer); scrollbarHideTimer = null; }
      el.classList.add('hide-scrollbar');
      suppressScrollHandler.value = true;
      snapToBottom(el);
      // 仅做一次下一帧兜底，避免连续多帧读写布局造成卡顿
      requestAnimationFrame(() => {
        if (!isAutoScroll.value || !chatContainer.value) return;
        snapToBottom(chatContainer.value);
      });

      lastScrollTop.value = el.scrollTop;
      lastScrollHeight.value = el.scrollHeight;
    } finally {
      pendingScrollRAF = null;
    }
  });
}

function setupResizeObserver() {
  if (!chatContentWrapper.value || typeof ResizeObserver === 'undefined') return;
  
  resizeObserver = new ResizeObserver(() => {
    if (isAutoScroll.value && chatContainer.value) {
      chatContainer.value.scrollTop = chatContainer.value.scrollHeight;
      
      scheduleScrollToBottom();
    }

    handleResizeForScrollButton();
  }); 
  
  resizeObserver.observe(chatContentWrapper.value);
}

const handleResizeForScrollButton = useThrottleFn(() => {
    if (chatContainer.value) {
      const { scrollTop, scrollHeight, clientHeight } = chatContainer.value;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
      const atStrictBottom = distanceFromBottom <= STRICT_BOTTOM_EPS;
      const noOverflow = scrollHeight <= clientHeight;
      if (noOverflow || atStrictBottom) {
        hideScrollButtonDebounced();
      }
    }
}, 16);

let hideDebounceTimer: number | null = null;
const BUTTON_FADE_MS = 180;
function showScrollButtonNow() {
  if (hideDebounceTimer) {
    clearTimeout(hideDebounceTimer);
    hideDebounceTimer = null;
  }
  showScrollButton.value = true;
  requestAnimationFrame(() => {
    scrollButtonVisible.value = true;
  });
}
function hideScrollButtonDebounced(delay = 120) {
  if (hideDebounceTimer) {
    clearTimeout(hideDebounceTimer);
  }
  scrollButtonVisible.value = false;
  hideDebounceTimer = window.setTimeout(() => {
    showScrollButton.value = false;
    hideDebounceTimer = null;
  }, Math.max(delay, BUTTON_FADE_MS));
}

let scrollbarHideTimer: number | null = null;
function showScrollbarDuringScroll() {
  if (!chatContainer.value) return;
  chatContainer.value.classList.remove('hide-scrollbar');
  if (scrollbarHideTimer) {
    clearTimeout(scrollbarHideTimer);
    scrollbarHideTimer = null;
  }
  if (
    (pointerDown.value && isPointerInScrollbarGutter(chatContainer.value)) ||
    hoveringScrollbar.value
  ) {
    return;
  }
  scrollbarHideTimer = window.setTimeout(() => {
    chatContainer.value?.classList.add('hide-scrollbar');
    scrollbarHideTimer = null;
  }, 600);
}

function getMessageKey(message: Message): string {
  return message.uiKey as string;
}

function getMessageId(message: Message): string {
  if (message.id) return message.id;
  if (message.uiKey) return message.uiKey;

  const filteredMessages = messages.value
  const index = filteredMessages.indexOf(message)
  const role = message.role
  const messageRef = message.content + message.role + index
  return `msg-${role}-${index}-${messageRef.length}`
}

function getSelectionPosition(message: Message, index: number): 'none' | 'single' | 'first' | 'middle' | 'last' {
  const messageId = getMessageId(message)
  const isSelected = selectedMessages.value.has(messageId)
  
  if (!isSelected) {
    return 'none'
  }
  
  const prevMessage = messages.value[index - 1]
  const nextMessage = messages.value[index + 1]
  
  const isPrevSelected = prevMessage ? selectedMessages.value.has(getMessageId(prevMessage)) : false
  const isNextSelected = nextMessage ? selectedMessages.value.has(getMessageId(nextMessage)) : false
  
  if (!isPrevSelected && !isNextSelected) {
    return 'single' 
  } else if (!isPrevSelected && isNextSelected) {
    return 'first' 
  } else if (isPrevSelected && isNextSelected) {
    return 'middle' 
  } else if (isPrevSelected && !isNextSelected) {
    return 'last' 
  }
  
  return 'single'
}

const messages = computed(() => {
  const originalMessages = chatStore.messages;

  if (originalMessages.length === 0) {
    return [];
  }

  return originalMessages.filter((current) => {
    if (current.role === 'tool' || current.role === 'system') {
      return false;
    }

    if (!current.uiKey) {
      current.uiKey = createUiKey();
    }

    return true;
  });
});

// 加载历史时分批挂载，避免 Markdown、代码块和 artifact 卡片在一次更新中占满主线程。
const renderedMessageCount = ref(Infinity);
const renderedMessages = computed(() => messages.value.slice(0, renderedMessageCount.value));
let historyRenderVersion = 0;
let historyRenderTask: Promise<void> = Promise.resolve();
// 分批挂载进行中标记：期间抑制输入框高度变化触发的滚动补偿，
// 渲染任务结束时会统一滚到底部，避免与逐批 DOM 挂载争抢主线程。
let historyRenderingActive = false;

watch([messages, () => props.historySessionId, () => chatStore.sessionThreadId], ([items, sessionId]) => {
  const version = ++historyRenderVersion;
  if (!sessionId) {
    renderedMessageCount.value = Infinity;
    historyRenderTask = Promise.resolve();
    historyRenderingActive = false;
    return;
  }
  renderedMessageCount.value = 0;
  if (sessionId !== chatStore.sessionThreadId) {
    historyRenderTask = Promise.resolve();
    historyRenderingActive = false;
    return;
  }
  historyRenderTask = (async () => {
    historyRenderingActive = true;
    let batchSize = 2;
    while (renderedMessageCount.value < items.length) {
      await yieldToBrowser();
      if (version !== historyRenderVersion) return;
      const started = performance.now();
      renderedMessageCount.value = Math.min(items.length, renderedMessageCount.value + batchSize);
      await nextTick();
      // 较重的消息降为逐条挂载，短消息最多每批 8 条。
      batchSize = performance.now() - started > 8 ? 1 : Math.min(8, batchSize + 1);
    }
    await yieldToBrowser();
    if (version !== historyRenderVersion) return;
    historyRenderingActive = false;
    scrollToBottom(true);
  })();
}, { immediate: true });

async function waitForHistoryRender() {
  // 若期间数据源发生替换，等待最新批次，而不是过期的渲染任务。
  let task: Promise<void>;
  do {
    task = historyRenderTask;
    await task;
  } while (task !== historyRenderTask);
}

onUnmounted(() => { ++historyRenderVersion; });

const selectedMessageObjects = computed(() => {
  return messages.value.filter(message => selectedMessages.value.has(getMessageId(message)))
})

const isAllSelected = computed(() => {
  const totalMessages = messages.value.length
  const selectedCount = selectedMessages.value.size
  return totalMessages > 0 && selectedCount === totalMessages
})

const hasSelection = computed(() => {
  return selectedMessages.value.size > 0
})

watch([isAllSelected, hasSelection], ([allSelected, hasSelected]) => {
  emit('all-selected-changed', allSelected, hasSelected)
}, { immediate: true })

function onMessageCreated(event: CustomEvent) {
  if (event.detail && event.detail.message) {
    nextTick(() => {
      if (isAutoScroll.value) {
        scrollToBottom();
      } else {
        showScrollButton.value = true; 
        setTimeout(() => {
          scrollButtonVisible.value = true;
        }, 100);
      }
    });
  }
}

function onMessageUpdated(event: CustomEvent) {
  if (event.detail && event.detail.message) {
    nextTick(() => {
      if (isAutoScroll.value) {
        setTimeout(() => {
          scrollToBottom();
        }, 50);
      } else {
        showScrollButton.value = true;
        scrollButtonVisible.value = true;
      }
    });
  }
}

function onPanelExpanded(event: CustomEvent) {
  if (event.detail && event.detail.message) {

    
    if (isAutoScroll.value && chatContainer.value && isAtStrictBottom(chatContainer.value)) {
      setTimeout(() => {
        scrollToBottom();
      }, 300);
    } else {
      if (!isAutoScroll.value) {
        showScrollButtonNow();
      }
    }
  }
}

const checkBottomAfterScroll = useDebounceFn(() => {
  if (chatContainer.value && isAtStrictBottom(chatContainer.value)) {
    hideScrollButtonDebounced();
    if (Date.now() > autoScrollLockUntil.value) {
      isAutoScroll.value = true;
    }
    isAutoScrolling.value = false;
  }
}, 150);

const onChatScroll = useThrottleFn(() => {
  if (!chatContainer.value) return;

  checkBottomAfterScroll();

  if (suppressScrollHandler.value) {
    suppressScrollHandler.value = false;
    return;
  }

  const { scrollTop, scrollHeight, clientHeight } = chatContainer.value;
  const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
  const isAtStrictBottom = distanceFromBottom <= STRICT_BOTTOM_EPS;
  const isScrollingUp = scrollTop < lastScrollTop.value;
  
  lastScrollTop.value = scrollTop;
  lastScrollHeight.value = scrollHeight;
  
  if (isAtStrictBottom) {
    hideScrollButtonDebounced();
    if (Date.now() > autoScrollLockUntil.value) {
      isAutoScroll.value = true;
    }
    isAutoScrolling.value = false;
    return;
  }
  
  if (userScrolling.value || isScrollingUp) {
    isAutoScroll.value = false;
    showScrollButtonNow();
    if (!isAutoScrolling.value) {
      showScrollbarDuringScroll();
    }
    return;
  }
  
  if (!isAutoScroll.value && !showScrollButton.value) {
    showScrollButtonNow();
  }
}, 30); 

const onUserScrollIntent = useThrottleFn((event: Event) => {
  if (!chatContainer.value || isNestedScrollTarget(event, chatContainer.value)) return;
  userScrolling.value = true;
  stopGradualScrollToBottom();
  isAutoScrolling.value = false;
  autoScrollLockUntil.value = Date.now() + 800; 
  if (chatContainer.value && !isAtStrictBottom(chatContainer.value)) {
    isAutoScroll.value = false;
    showScrollButtonNow();
  }
  showScrollbarDuringScroll();
  if (userScrollDebounceTimer) {
    clearTimeout(userScrollDebounceTimer);
  }
  userScrollDebounceTimer = window.setTimeout(() => {
    userScrolling.value = false;
  }, 150);
}, 30);

function onUserScrollKey(e: KeyboardEvent) {
  if (!chatContainer.value || isNestedScrollTarget(e, chatContainer.value)) return;
  const key = e.key;
  if (key === 'ArrowUp' || key === 'PageUp' || key === 'Home') {
    if (chatContainer.value) {
      const { scrollHeight, clientHeight } = chatContainer.value;
      if (scrollHeight <= clientHeight) return;
    }
    isAutoScroll.value = false;
    showScrollButtonNow();
    autoScrollLockUntil.value = Date.now() + 800;
    showScrollbarDuringScroll();
  } else if (key === 'ArrowDown' || key === 'PageDown' || key === 'End') {
    if (chatContainer.value && isAtStrictBottom(chatContainer.value)) {
      isAutoScroll.value = true;
      hideScrollButtonDebounced();
    }
  }
}

function onWheel(e: WheelEvent) {
  if (!chatContainer.value) return;
  if (isNestedScrollTarget(e, chatContainer.value)) return;
  
  const { scrollHeight, clientHeight } = chatContainer.value;
  if (scrollHeight <= clientHeight) return;

  if (e.deltaY < 0) {
    stopGradualScrollToBottom();
    isAutoScrolling.value = false;
    if (isAutoScroll.value) {
      isAutoScroll.value = false;
      showScrollButtonNow();
    }
    autoScrollLockUntil.value = Date.now() + 800;
  }
}

function scrollToBottomManually() {
  scrollToBottom(true, true);
  isAutoScroll.value = true;
  hideScrollButtonDebounced();
}

function onForceScrollToBottom(event: Event) {
  const customEvent = event as CustomEvent<{ smooth?: boolean }>;
  const smooth = customEvent.detail?.smooth ?? true;

  isAutoScroll.value = true;
  nextTick(() => {
    if (smooth) {
      animateScrollToBottom();
    } else {
      scrollToBottom(true, false);
    }
    hideScrollButtonDebounced();
  });
}

function hideScrollButton() {
  hideScrollButtonDebounced();
}

function onPointerDown(e: PointerEvent) {
  pointerDown.value = true;
  lastPointerPos.value = { x: e.clientX, y: e.clientY };
  if (chatContainer.value && isPointerInScrollbarGutter(chatContainer.value)) {
    showScrollbarDuringScroll();
  }
}
function onPointerUp(e: PointerEvent) {
  lastPointerPos.value = { x: e.clientX, y: e.clientY };
  pointerDown.value = false;
  if (chatContainer.value && isPointerInScrollbarGutter(chatContainer.value)) {
    showScrollbarDuringScroll();
  }
}
function onPointerMove(e: PointerEvent) {
  lastPointerPos.value = { x: e.clientX, y: e.clientY };
  if (!chatContainer.value) return;
  const inGutter = isPointerInScrollbarGutter(chatContainer.value);
  if (inGutter) {
    hoveringScrollbar.value = true;
    chatContainer.value.classList.remove('hide-scrollbar');
    if (scrollbarHideTimer) {
      clearTimeout(scrollbarHideTimer);
      scrollbarHideTimer = null;
    }
  } else {
    if (hoveringScrollbar.value) {
      hoveringScrollbar.value = false;
      showScrollbarDuringScroll();
    }
  }
}

function handleUserPreferencesChanged(event: Event) {
  const customEvent = event as CustomEvent;
  const detail = customEvent.detail;
  
  if (detail.preference === 'all') {
    if (detail.value && typeof detail.value.chatWindowStyle !== 'undefined') {
      chatWindowStyle.value = detail.value.chatWindowStyle;
    }
  } else if (detail.preference === 'chatWindowStyle') {
    chatWindowStyle.value = detail.value;
  }
}

onMounted(() => {
  document.addEventListener('mcp-message-created', onMessageCreated as EventListener);
  document.addEventListener('mcp-message-updated', onMessageUpdated as EventListener);
  document.addEventListener('mcp-panel-expanded', onPanelExpanded as EventListener);
  document.addEventListener('hide-scroll-button', hideScrollButton as EventListener);
  document.addEventListener('chat-force-scroll-to-bottom', onForceScrollToBottom as EventListener);
  window.addEventListener('user-preferences-changed', handleUserPreferencesChanged as EventListener);

  nextTick(() => {
    if (chatContainer.value) {
      lastScrollTop.value = chatContainer.value.scrollTop;
      lastScrollHeight.value = chatContainer.value.scrollHeight;
      isAutoScroll.value = isAtStrictBottom(chatContainer.value);

      if (chatStore.messages.length <= 2 && chatStore.isProcessing) {
        isAutoScroll.value = true;
        scrollToBottom();
      }

      setupResizeObserver();

      chatContainer.value.addEventListener('scroll', onChatScroll);

      chatContainer.value.addEventListener('wheel', onUserScrollIntent as EventListener, { passive: true } as any);
      chatContainer.value.addEventListener('touchstart', onUserScrollIntent as EventListener, { passive: true } as any);
      chatContainer.value.addEventListener('touchmove', onUserScrollIntent as EventListener, { passive: true } as any);
    }
  });

  document.addEventListener('keydown', onUserScrollKey as EventListener);
  document.addEventListener('pointerdown', onPointerDown as EventListener);
  document.addEventListener('pointerup', onPointerUp as EventListener);
  document.addEventListener('pointermove', onPointerMove as EventListener);
});

onUnmounted(() => {
  document.removeEventListener('mcp-message-created', onMessageCreated as EventListener);
  document.removeEventListener('mcp-message-updated', onMessageUpdated as EventListener);
  document.removeEventListener('mcp-panel-expanded', onPanelExpanded as EventListener);
  document.removeEventListener('hide-scroll-button', hideScrollButton as EventListener);
  document.removeEventListener('chat-force-scroll-to-bottom', onForceScrollToBottom as EventListener);
  window.removeEventListener('user-preferences-changed', handleUserPreferencesChanged as EventListener);
  document.removeEventListener('keydown', onUserScrollKey as EventListener);
  document.removeEventListener('pointerdown', onPointerDown as EventListener);
  document.removeEventListener('pointerup', onPointerUp as EventListener);
  document.removeEventListener('pointermove', onPointerMove as EventListener);

  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }

  stopGradualScrollToBottom();

  if (chatContainer.value) {
    chatContainer.value.removeEventListener('scroll', onChatScroll);
    chatContainer.value.removeEventListener('wheel', onUserScrollIntent as EventListener);
    chatContainer.value.removeEventListener('touchstart', onUserScrollIntent as EventListener);
    chatContainer.value.removeEventListener('touchmove', onUserScrollIntent as EventListener);
  }
  
  if (inputHeightScrollRaf) {
    cancelAnimationFrame(inputHeightScrollRaf);
    inputHeightScrollRaf = 0;
  }
});

watch(
  () => [...messages.value],
  async () => {
    await nextTick();
    if (!chatContainer.value) return;

    const container = chatContainer.value;
    const prevHeight = lastScrollHeight.value || container.scrollHeight;
    const wasAtStrictBottom = (prevHeight - lastScrollTop.value - container.clientHeight) <= STRICT_BOTTOM_EPS;

    if (isAutoScroll.value && wasAtStrictBottom) {
      scrollToBottom();
    } else {
      if (!isAutoScroll.value) {
        showScrollButtonNow();
      }
    }

    lastScrollHeight.value = chatContainer.value.scrollHeight;
    lastScrollTop.value = chatContainer.value.scrollTop;
  },
  { deep: true }
);

function scrollToBottom(ignoreSuppression = false, smooth = false) {
  if (!chatContainer.value) return;
  
  if (!ignoreSuppression && shouldSuppressScroll()) {
    return;
  }
  
  try {
    const el = chatContainer.value;
    const scrollHeight = el.scrollHeight;
    
    suppressScrollHandler.value = true;
    isAutoScrolling.value = true;
    if (scrollbarHideTimer) { clearTimeout(scrollbarHideTimer); scrollbarHideTimer = null; }
    el.classList.add('hide-scrollbar');
    
    el.scroll({
      top: scrollHeight,
      behavior: smooth ? 'smooth' : 'instant'
    });
    
    if (!smooth) {
      el.scrollTop = scrollHeight;
    }

    if (!smooth) {
      scheduleScrollToBottom();
    }

    lastScrollTop.value = el.scrollTop;
    lastScrollHeight.value = el.scrollHeight;
  } catch (e) {
    console.error('滚动失败:', e);
    
    if (chatContainer.value) {
      const el = chatContainer.value;
      suppressScrollHandler.value = true;
      el.scrollTop = el.scrollHeight;
      lastScrollTop.value = el.scrollTop;
      lastScrollHeight.value = el.scrollHeight;
    }
  }
}

watch(() => chatStore.isProcessing, (isProcessing) => {
  if (isProcessing && isSelectionMode.value) {
    isSelectionMode.value = false
    selectedMessages.value.clear()
  }
})

function handleSelectionModeChanged(action: boolean | string | { action: string, messageId: string | null }) {
  if (typeof action === 'object' && (action.action === 'toggle' || action.action === 'share')) {
    
    if (action.action === 'share') {
      isSelectionMode.value = true;
    } else {
      isSelectionMode.value = !isSelectionMode.value
    }
    
    if (isSelectionMode.value && action.messageId) {
      selectedMessages.value.clear()
      selectedMessages.value.add(action.messageId)
    } else if (!isSelectionMode.value) {
      selectedMessages.value.clear()
    }
  } else if (action === 'toggle') {
    isSelectionMode.value = !isSelectionMode.value
    if (!isSelectionMode.value) {
      selectedMessages.value.clear()
    }
  } else {
    isSelectionMode.value = action as boolean
    if (!isSelectionMode.value) {
      selectedMessages.value.clear()
    }
  }
  
  emit('selection-mode-changed', isSelectionMode.value)
}

watch(() => props.inputToolbarVisible, (visible) => {
  if (visible && isAutoScroll.value) {
    nextTick(() => {
      scrollToBottom(true);
    });
  }
});

let inputHeightScrollRaf = 0;
watch(() => props.inputHeight, (newVal, oldVal) => {
  if ((newVal || 0) <= (oldVal || 0) || !isAutoScroll.value) return;
  // padding-bottom 已改为瞬时生效，下一帧对齐一次滚动位置即可，
  // 不再用 50ms 轮询跟随布局动画（每次都会强制同步布局）。
  if (historyRenderingActive) return;
  if (inputHeightScrollRaf) cancelAnimationFrame(inputHeightScrollRaf);
  inputHeightScrollRaf = requestAnimationFrame(() => {
    inputHeightScrollRaf = 0;
    if (isAutoScroll.value) scrollToBottom(true);
  });
});

function handleMessageSelection(messageId: string, selected: boolean) {
  if (selected) {
    selectedMessages.value.add(messageId)
  } else {
    selectedMessages.value.delete(messageId)
  }
  
  emit('selection-changed', messageId, selected)

  Array.from(selectedMessages.value).map(id => {
    const message = messages.value.find(msg => getMessageId(msg) === id)
    return {
      id,
      role: message?.role,
      content: message?.content?.substring(0, 100) + (message?.content && message.content.length > 100 ? '...' : '')
    }
  });
}

function selectAllMessages() {
  selectedMessages.value.clear()
  
  messages.value.forEach(message => {
    const messageId = getMessageId(message)
    selectedMessages.value.add(messageId)
  })
  
}

function clearAllSelection() {
  selectedMessages.value.clear()
}

function copySelectedMessages() {
  if (selectedMessages.value.size === 0) {
    return;
  }

  try {
    const allMessages = chatStore.messages; 
    const selectedMessagesList = messages.value
      .filter(message => selectedMessages.value.has(getMessageId(message)))
      .map(message => {
        let content = '';
        
        if (message.role === 'user') {
          content = `User: ${message.content}`;
        } else if (message.role === 'system') {
          content = `系统提示词:${message.content}`;
        } else if (message.role === 'assistant') {
          if (message.tool_calls && Array.isArray(message.tool_calls) && message.tool_calls.length > 0) {
            const toolCallsText = message.tool_calls.map(toolCall => {
              let toolText = '';
              
              if (toolCall.function?.arguments) {
                try {
                  const args = typeof toolCall.function.arguments === 'string' 
                    ? JSON.parse(toolCall.function.arguments) 
                    : toolCall.function.arguments;
                  toolText += `调用参数:\n${JSON.stringify(args, null, 2)}`;
                } catch (e) {
                  toolText += `调用参数:\n${toolCall.function.arguments}`;
                }
              }
              
              const toolResultMessage = allMessages.find(msg => 
                msg.role === 'tool' && msg.tool_call_id === toolCall.id
              );
              
              if (toolResultMessage && toolResultMessage.content) {
                toolText += `\n\n调用结果:\n${toolResultMessage.content}`;
              }
              
              return toolText;
            }).join('\n\n');
            
            if (message.content && message.content.trim()) {
              content = `${toolCallsText}\n\nAssistant: ${message.content}`;
            } else {
              content = toolCallsText;
            }
          } else {
            content = `Assistant: ${message.content || ''}`;
          }
        }
        
        content = content
          .replace(/\*\*(.*?)\*\*/g, '$1')
          .replace(/\*(.*?)\*/g, '$1')
          .replace(/`([^`]+)`/g, '$1')
          .replace(/```[\s\S]*?```/g, '')
          .replace(/#{1,6}\s/g, '')
          .replace(/\[([^\]]+)]\([^)]+\)/g, '$1')
          .replace(/!\[([^\]]*)]\([^)]+\)/g, '$1')
          .replace(/^\s*[-*+]\s/gm, '')
          .replace(/^\s*\d+\.\s/gm, '')
          .replace(/^\s*>\s/gm, '')
          .trim();
        
        return content;
      })
      .filter(content => content.trim() !== '')
      .join('\n\n'); 

    copyText(selectedMessagesList)
      .then(ok => {
        if (ok) {
          NotificationService.success('对话内容已复制到剪贴板')
        } else {
          NotificationService.error('复制失败，请手动复制')
        }
      })
  } catch (error) {
    console.error('复制对话内容时出错:', error);
  }
}


defineExpose({
  waitForHistoryRender,
  selectAllMessages,
  clearAllSelection,
  handleSelectionModeChanged,
  copySelectedMessages,
  selectedMessages,
  selectedMessageObjects
})
</script>

<style scoped>
@import '../../assets/styles/chat-history.css';

.scroll-button :deep(.anticon) {
  color: #495057;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}

.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
</style>
