<template>
  <div class="message-actions">
    <!-- 编辑模式 -->
    <template v-if="isEditMode && message.role === 'user'">
      <div class="edit-container" @click.stop>
        <a-textarea
          v-model:value="editContent"
          :auto-size="{ minRows: 1, maxRows: 6 }"
          placeholder="输入您想提问的问题"
          class="edit-input"
          @keydown="handleKeydown"
        />
        <div class="edit-actions">
          <button @click="cancelEdit" class="cancel-btn">取消</button>
          <button @click="confirmEdit" class="confirm-btn">确认</button>
        </div>
      </div>
    </template>

    <!-- 用户消息工具栏 -->
    <div v-if="message.role === 'user' && message.content && !isEditMode" class="message-toolbar">
      <button 
        class="toolbar-btn copy-btn" 
        @click.stop="copyUserMessage"
        title="复制消息内容"
      >
        <CopyIcon width="14" height="14" />
        <span class="btn-text">复制</span>
      </button>
      <button 
        v-if="shouldShowEditButton"
        class="toolbar-btn edit-btn" 
        @click.stop="toggleEditMode"
        title="编辑消息"
      >
        <EditIcon width="14" height="14" />
        <span class="btn-text">编辑</span>
      </button>
      <button 
        v-if="!chatStore.isProcessing && !isAnyAssistantStreaming"
        class="toolbar-btn share-btn" 
        @click.stop="shareMessage"
        title="分享消息"
      >
        <ShareIcon width="14" height="14" />
        <span class="btn-text">分享</span>
      </button>
    </div>

    <!-- 智能体消息工具栏 -->
    <div v-if="message.role === 'assistant' && shouldShowAssistantToolbar" 
         :class="['message-toolbar', { 'last-assistant-toolbar': isLastAssistantMessage, 'is-playing': isCurrentMessageActive }]">
      <div v-if="showAssistantModelInfo" class="assistant-model-badge" :title="assistantModelDisplayName">
        <component :is="assistantModelIconComponent" v-if="assistantModelIconComponent" class="assistant-model-icon" />
        <span class="assistant-model-name">{{ assistantModelDisplayName }}</span>
      </div>
      <span v-if="showAssistantModelInfo" class="toolbar-divider"></span>
      <button 
        class="toolbar-btn copy-btn" 
        @click.stop="copyAssistantMessage"
        title="复制消息内容"
      >
        <CopyIcon width="14" height="14" />
        <span class="btn-text">复制</span>
      </button>
      <button 
        v-if="isLastAssistantMessage"
        class="toolbar-btn retry-btn" 
        @click.stop="retryMessage"
        title="重试生成"
      >
        <RetryIcon width="14" height="14" />
        <span class="btn-text">重试</span>
      </button>
      <button
        v-if="!message.isStreaming && !chatStore.isProcessing && message.content && shouldShowReadButton"
        class="toolbar-btn read-btn" 
        :class="{ 'is-playing': isCurrentMessageActive }"
        @click.stop="readMessage"
        :title="isCurrentMessageActive ? '停止朗读' : '朗读消息'"
        :style="{ '--audio-volume': audioVolume }"
      >
        <div v-if="isCurrentMessageActive" class="visualizer-overlay">
          <AudioPlayingIcon 
            :analyser="analyser"
            :is-playing="isSpeaking"
          />
        </div>

        <div class="btn-content-placeholder" :style="{ visibility: isCurrentMessageActive ? 'hidden' : 'visible' }">
          <SoundOutlined style="font-size: 14px;" />
          <span class="btn-text">朗读</span>
        </div>
      </button>
      <button
        v-if="!message.isStreaming && !chatStore.isProcessing"
        class="toolbar-btn share-btn" 
        @click.stop="shareMessage"
        title="分享消息"
      >
        <ShareIcon width="14" height="14" />
        <span class="btn-text">分享</span>
      </button>

      <span v-if="showAssistantContextBadge" class="toolbar-divider"></span>
      <a-popover
        v-if="showAssistantContextBadge"
        placement="top"
        trigger="hover"
        overlayClassName="context-usage-popover"
      >
        <template #content>
          <div class="context-usage-card">
            <div class="context-usage-title">上下文使用率</div>
            <div class="context-usage-value">{{ assistantContextPopoverValue }}</div>
            <div v-if="contextCompressionDescription" class="context-usage-description">
              {{ contextCompressionDescription }}
            </div>
            <button
              type="button"
              class="context-usage-action"
              :disabled="isCompressingContext"
              @click.stop="handleCompressContext"
            >
              {{ isCompressingContext ? '压缩中...' : '压缩' }}
            </button>
          </div>
        </template>
        <button
          type="button"
          class="context-usage-trigger"
          :title="assistantContextTitle"
          @click.stop
        >
          <span class="context-usage-ring" aria-hidden="true">
            <svg viewBox="0 0 20 20" class="context-usage-ring-svg">
              <circle
                class="context-usage-ring-track"
                cx="10"
                cy="10"
                r="7"
              />
              <circle
                class="context-usage-ring-progress"
                cx="10"
                cy="10"
                r="7"
                :style="assistantContextRingStyle"
              />
            </svg>
          </span>
          <span class="context-usage-trigger-text">{{ assistantContextPercentText }}</span>
        </button>
      </a-popover>
      <span class="toolbar-divider" style="width: 1px; height: 16px; background: #e2e8f0; margin: 0 8px;"/>

      <button 
        class="toolbar-btn like-btn" 
        :class="{ 'is-active': message.liked }"
        title="点赞" 
        @click.stop="handleLike" 
        style="padding: 6px; margin-right: 6px; margin-left: 4px;"
      >
        <LikeFilled v-if="message.liked" style="font-size: 14px; color: #ff4d4f;" />
        <LikeOutlined v-else style="font-size: 14px;"/>
      </button>
      <button 
        class="toolbar-btn dislike-btn" 
        :class="{ 'is-active': message.disliked }"
        title="点踩" 
        @click.stop="handleDislike" 
        style="padding: 6px;"
      >
        <DislikeFilled v-if="message.disliked" style="font-size: 14px; color: #595959;" />
        <DislikeOutlined v-else style="font-size: 14px;"/>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useChatStore } from '@/stores/chat-store'
import NotificationService from '@/utils/NotificationService'
import CopyIcon from '@/components/icons/CopyIcon.vue'
import EditIcon from '@/components/icons/EditIcon.vue'
import RetryIcon from '@/components/icons/RetryIcon.vue'
import ShareIcon from '@/components/icons/ShareIcon.vue'
import { LikeOutlined, LikeFilled, DislikeOutlined, DislikeFilled, SoundOutlined } from '@ant-design/icons-vue'
import AudioPlayingIcon from '@/components/icons/AudioPlayingIcon.vue'
import QwenIcon from '@/components/icons/llm/qwen.vue'
import DeepSeekIcon from '@/components/icons/llm/deepseek.vue'
import ZhipuIcon from '@/components/icons/llm/zhipu.vue'
import ZaiIcon from '@/components/icons/llm/zai.vue'
import type { Message } from '@/types'
import { copyText } from '@/utils/clipboard'
import StorageService from '@/utils/StorageService'
import { eventBus } from '@/utils/EventBus'
import { useWorkspaceStorage } from '@/composables/useWorkspaceStorage'
import TTSService from '@/services/TTSService'
import { getTtsServer } from '@/utils/RuntimeConfig'
import { shouldShowModelIcon } from '@/utils/modelIcon'
import { formatContextTokenCount } from '@/utils/contextMetrics'
import confetti from 'canvas-confetti'

interface Props {
  message: Message
}

const props = defineProps<Props>()

// 定义事件
const emit = defineEmits<{
  editModeChanged: [isEditMode: boolean]
  selectionModeChanged: [action: boolean | string | { action: string, messageId: string | null }]
}>()

const chatStore = useChatStore()

const KB_ENABLED_KEY = 'kb-enabled'
const KB_SELECTED_NAMES_KEY = 'kb-selected-names'
const isKbEnabled = useWorkspaceStorage<boolean>(KB_ENABLED_KEY, false)
const selectedKbNames = useWorkspaceStorage<string[]>(KB_SELECTED_NAMES_KEY, [])

const showAssistantModelInfo = computed(() => {
  return props.message.role === 'assistant' && isLastAssistantMessage.value && !!assistantModelDisplayName.value
})

const resolveModelName = (modelValue: unknown): string => {
  if (!modelValue) return ''
  if (typeof modelValue === 'string') return modelValue.trim()
  if (typeof modelValue === 'object') {
    const modelObj = modelValue as Record<string, any>
    return String(
      modelObj.name ||
      modelObj.modelName ||
      modelObj.model ||
      modelObj.id ||
      ''
    ).trim()
  }
  return String(modelValue).trim()
}

const assistantModelDisplayName = computed<string>(() => {
  const activeAgent = StorageService.getActiveAgent()
  const agentType = activeAgent?.basic?.type || activeAgent?.config?.basic?.type
  if (!['assistant', 'deepagent', 'orchestrator'].includes(agentType)) return ''

  const agentModelName = resolveModelName(activeAgent?.config?.model) || resolveModelName(activeAgent?.model) || resolveModelName(activeAgent?.basic?.model)
  if (!agentModelName) return ''

  const modelMap = new Map<string, string>((chatStore as any).availableModels?.map((item: any) => [String(item.id), String(item.name)]))
  return modelMap.get(agentModelName) || agentModelName
})

const assistantModelIconComponent = computed(() => {
  const target = String(assistantModelDisplayName.value || '').toLowerCase()
  if (shouldShowModelIcon(target, 'qwen')) return QwenIcon
  if (shouldShowModelIcon(target, 'deepseek')) return DeepSeekIcon
  if (target.includes('glm')) return target.includes('z') ? ZaiIcon : ZhipuIcon
  return null
})

const assistantContextMetrics = computed(() => {
  if (props.message.role !== 'assistant') return null
  return props.message.contextMetrics || null
})

const hasAssistantContextWindow = computed(() => {
  const contextWindow = assistantContextMetrics.value?.contextWindow
  return typeof contextWindow === 'number' && contextWindow > 0
})

const showAssistantContextBadge = computed(() => {
  return isLastAssistantMessage.value && !!assistantContextMetrics.value
})

const assistantContextPercentText = computed(() => {
  const metrics = assistantContextMetrics.value
  if (!metrics) return ''
  if (metrics.mode === 'pending') return '--'
  return `${Math.max(0, metrics.utilization * 100).toFixed(0)}%`
})

const assistantContextPopoverValue = computed(() => {
  const metrics = assistantContextMetrics.value
  if (!metrics) return ''
  if (!hasAssistantContextWindow.value) return `${assistantContextPercentText.value}`
  if (metrics.mode === 'pending') return `等待 usage`
  return `${assistantContextPercentText.value}`
})

const assistantContextRingStyle = computed(() => {
  const metrics = assistantContextMetrics.value
  const ratio = Math.max(0, Math.min(1, metrics?.utilization || 0))
  const circumference = 2 * Math.PI * 7
  return {
    strokeDasharray: `${circumference.toFixed(2)} ${circumference.toFixed(2)}`,
    strokeDashoffset: `${(circumference * (1 - ratio)).toFixed(2)}`
  }
})

const assistantContextTitle = computed(() => {
  const metrics = assistantContextMetrics.value
  if (!metrics) return ''
  if (!hasAssistantContextWindow.value) {
    return [
      `当前上下文占用: ${metrics.promptTokens} tokens`,
      '未配置模型上下文大小',
      `统计方式: ${metrics.mode === 'exact' ? '接口返回 usage' : '前端本地预估'}`
    ].join('\n')
  }
  if (metrics.mode === 'pending') {
    return [
      `上下文窗口: ${metrics.contextWindow} tokens`,
      'Token统计: 等待模型返回 usage',
      '统计方式: 仅使用接口返回 usage，不做前端估算'
    ].join('\n')
  }
  return [
    `上下文占用: ${metrics.promptTokens} / ${metrics.contextWindow} tokens`,
    `消息占用: ${metrics.messagesTokens} tokens`,
    `${metrics.mode === 'exact' ? '文本占用' : '文本预估'}: ${metrics.textTokens} tokens`,
    `${metrics.mode === 'exact' ? '图片占用' : '图片预估'}: ${metrics.imageTokens} tokens`,
    `工具Schema占用: ${metrics.toolsTokens} tokens`,
    `可用输入预算: ${metrics.usableInputTokens} tokens`,
    `输出预留: ${metrics.reservedOutputTokens} tokens`,
    `安全边界: ${metrics.safetyMarginTokens} tokens`,
    `统计方式: ${metrics.mode === 'exact' ? '接口返回 usage' : '前端本地预估'}`
  ].join('\n')
})

const isCompressingContext = computed(() => !!chatStore.isCompressingContext)

const contextCompressionDescription = computed(() => {
  const info = chatStore.contextCompressionInfo
  if (!info) return ''
  const reduced = formatContextTokenCount(info.reducedTokens)
  const keptSuffix = info.keptMessageCount > 0 ? `，保留最近 ${info.keptMessageCount} 条` : ''
  const fileSuffix = info.hasCompressedFiles ? '，并压缩文档上下文' : ''
  return `已减少 ${reduced}${keptSuffix}${fileSuffix}`
})

async function handleCompressContext() {
  if (isCompressingContext.value) return
  await chatStore.compressConversationContext()
}

// 编辑模式状态
const isEditMode = ref(false)
const editContent = ref('')

const shouldShowReadButton = computed(() => {
  return !!getTtsServer();
});

// TTS 状态
const isSpeaking = TTSService.isSpeaking
const currentPlayingMessageId = TTSService.currentPlayingMessageId
const analyser = TTSService.analyser
const audioVolume = ref(0);

// 计算音量用于阴影效果
let volumeAnimationFrame: number | null = null;
const updateVolume = () => {
  if (isCurrentMessageActive.value && isSpeaking.value && analyser.value) {
    const dataArray = new Uint8Array(analyser.value.frequencyBinCount);
    analyser.value.getByteFrequencyData(dataArray);
    
    // 计算平均音量
    let sum = 0;
    // 只取人声主要频段 (前30个bin，约5kHz)
    const binCount = Math.min(30, dataArray.length);
    for (let i = 0; i < binCount; i++) {
      sum += dataArray[i];
    }
    const avg = sum / binCount;
    // 平滑处理: 0.8 * old + 0.2 * new
    audioVolume.value = audioVolume.value * 0.8 + (avg / 255) * 0.2;
    
    volumeAnimationFrame = requestAnimationFrame(updateVolume);
  } else {
    audioVolume.value = 0;
    if (volumeAnimationFrame) {
      cancelAnimationFrame(volumeAnimationFrame);
      volumeAnimationFrame = null;
    }
  }
};

const isCurrentMessageActive = computed(() => {
  const messageId = (props.message as any).uiKey || (props.message as any).id;
  return currentPlayingMessageId.value === messageId;
});

// 监听播放状态变化
import { watch, onUnmounted } from 'vue';

watch([isCurrentMessageActive, isSpeaking], ([isActive, speaking]) => {
  if (isActive && speaking) {
    updateVolume();
  } else {
    audioVolume.value = 0;
    if (volumeAnimationFrame) {
      cancelAnimationFrame(volumeAnimationFrame);
      volumeAnimationFrame = null;
    }
  }
});

onUnmounted(() => {
  if (volumeAnimationFrame) {
    cancelAnimationFrame(volumeAnimationFrame);
  }
});

const readMessage = () => {
  const messageId = (props.message as any).uiKey || (props.message as any).id;
  
  if (isCurrentMessageActive.value) {
    TTSService.stop();
    return;
  }

  if (props.message.content) {
    TTSService.speak(props.message.content, messageId);
  }
}

const handleLike = (event: MouseEvent) => {
  // 如果已经是点赞状态，则取消点赞
  if (props.message.liked) {
    props.message.liked = false
    return
  }

  // 如果当前是点踩状态，取消点踩
  if (props.message.disliked) {
    props.message.disliked = false
  }

  // 设置为点赞状态
  props.message.liked = true

  // 获取点击位置作为彩带发射源
  const rect = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const x = (rect.left + rect.width / 2) / window.innerWidth
  const y = (rect.top + rect.height / 2) / window.innerHeight

  const colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96']

  // 基础粒子
  confetti({
    particleCount: 40,
    spread: 50,
    origin: { x, y },
    colors: colors,
    shapes: ['circle', 'square'],
    scalar: 0.8,
    startVelocity: 20,
    decay: 0.9,
    ticks: 60,
    zIndex: 2000
  })

  // 模拟长丝带（通过自定义形状）
  // 创建一个细长的矩形作为丝带
  const ribbon = confetti.shapeFromPath({ path: 'M0 0 L10 0 L10 30 L0 30 Z' })

  confetti({
    particleCount: 10,
    spread: 50,
    origin: { x, y },
    colors: colors,
    shapes: [ribbon],
    scalar: 1.2,
    gravity: 0.6, // 飘得慢一点
    drift: 0,
    ticks: 80, // 存活时间更长
    startVelocity: 25,
    zIndex: 2000
  })

  // 弹出通知
  NotificationService.info('已收到您的反馈')
}

const handleDislike = (event: MouseEvent) => {
  // 如果已经是点踩状态，则取消点踩
  if (props.message.disliked) {
    props.message.disliked = false
    return
  }

  // 如果当前是点赞状态，取消点赞
  if (props.message.liked) {
    props.message.liked = false
  }

  // 设置为点踩状态
  props.message.disliked = true

  const btn = event.currentTarget as HTMLElement

  // 1. 按钮抖动动画
  btn.classList.add('shake-anim')
  setTimeout(() => {
    btn.classList.remove('shake-anim')
  }, 500)

  // 2. 冒泡效果
  const rect = btn.getBoundingClientRect()
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  
  // 基础颜色 - 灰色系
  const colors = ['#8c8c8c', '#595959', '#262626', '#bfbfbf']
  
  // 创建多个气泡
  const bubbleCount = 3 + Math.floor(Math.random() * 3) // 3-5个气泡
  
  for (let i = 0; i < bubbleCount; i++) {
    const bubble = document.createElement('div')
    
    // 随机决定是心碎还是圆点 (70% 心碎)
    const isHeart = Math.random() > 0.3
    bubble.textContent = isHeart ? '💔' : ''
    
    // 样式设置
    bubble.style.position = 'fixed'
    bubble.style.left = `${centerX}px`
    bubble.style.top = `${centerY}px`
    bubble.style.zIndex = '10000'
    bubble.style.pointerEvents = 'none'
    bubble.style.fontSize = `${12 + Math.random() * 12}px` // 12-24px
    bubble.style.opacity = '0'
    
    if (!isHeart) {
      // 圆点样式
      const size = 4 + Math.random() * 6
      bubble.style.width = `${size}px`
      bubble.style.height = `${size}px`
      bubble.style.borderRadius = '50%'
      bubble.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)]
    }
    
    document.body.appendChild(bubble)
    
    // 随机动画参数
    const xOffset = (Math.random() - 0.5) * 100 // 水平偏移 -50px 到 50px
    const yOffset = -60 - Math.random() * 80 // 垂直上浮 60px 到 140px
    const duration = 1000 + Math.random() * 1000 // 1s - 2s
    const delay = Math.random() * 200 // 0 - 200ms 延迟
    const rotation = (Math.random() - 0.5) * 60 // 旋转
    
    // Web Animation API
    const anim = bubble.animate([
      { 
        opacity: 0, 
        transform: `translate(-50%, -50%) scale(0.5) rotate(0deg)` 
      },
      { 
        opacity: 0.8 + Math.random() * 0.2, 
        transform: `translate(calc(-50% + ${xOffset * 0.3}px), calc(-50% + ${yOffset * 0.4}px)) scale(1) rotate(${rotation * 0.5}deg)`,
        offset: 0.4
      },
      { 
        opacity: 0, 
        transform: `translate(calc(-50% + ${xOffset}px), calc(-50% + ${yOffset}px)) scale(${isHeart ? 1.2 : 0.5}) rotate(${rotation}deg)` 
      }
    ], {
      duration: duration,
      delay: delay,
      easing: 'cubic-bezier(0.215, 0.61, 0.355, 1)' // easeOutCubic
    })
    
    anim.onfinish = () => {
      bubble.remove()
    }
  }

  // 弹出通知
  NotificationService.info('已收到您的反馈')
}

// 判断是否为最后一个智能体消息
const isLastAssistantMessage = computed(() => {
  if (props.message.role !== 'assistant') {
    return false
  }
  
  const messages = chatStore.messages
  const currentIndex = messages.findIndex(msg => msg === props.message)
  
  if (currentIndex === -1) {
    return false
  }
  
  // 检查当前消息之后是否还有其他智能体消息
  for (let i = currentIndex + 1; i < messages.length; i++) {
    if (messages[i].role === 'assistant') {
      return false
    }
  }
  
  return true
})

// 判断是否为最后一个用户消息
const isLastUserMessage = computed(() => {
  if (props.message.role !== 'user') {
    return false
  }
  
  const messages = chatStore.messages
  const currentIndex = messages.findIndex(msg => msg === props.message)
  
  if (currentIndex === -1) {
    return false
  }
  
  // 检查当前消息之后是否还有其他用户消息
  for (let i = currentIndex + 1; i < messages.length; i++) {
    if (messages[i].role === 'user') {
      return false
    }
  }
  
  return true
})

// 判断是否有任一智能体消息处于流式请求状态
const isAnyAssistantStreaming = computed(() => {
  const messages = chatStore.messages
  for (let i = 0; i < messages.length; i++) {
    const m = messages[i] as any
    if (m.role === 'assistant' && m.isStreaming) {
      return true
    }
  }
  return false
})

// 判断是否应该显示编辑按钮（考虑请求状态）
const shouldShowEditButton = computed(() => {
  return isLastUserMessage.value && !chatStore.isProcessing && !isAnyAssistantStreaming.value
})

// 判断是否应该显示智能体消息工具栏
const shouldShowAssistantToolbar = computed(() => {
  if (props.message.role !== 'assistant') {
    return false
  }
  
  // 如果正在流式传输，不显示工具栏
  if (props.message.isStreaming) {
    return false
  }
  
  // 如果有内容且内容不为空，显示工具栏
  if (props.message.content && props.message.content.trim()) {
    return true
  }
  
  return false
})

// 复制用户消息
async function copyUserMessage() {
  await copyText(props.message.content)
  NotificationService.success('已复制到剪贴板')
}

// 复制智能体消息
async function copyAssistantMessage() {
  await copyText(props.message.content)
  NotificationService.success('已复制到剪贴板')
}

// 分享消息
function shareMessage() {
  emit('selectionModeChanged', { action: 'share', messageId: (props.message as any).uiKey || (props.message as any).id })
}

// 重试消息生成
function retryMessage() {
  emit('selectionModeChanged', false);
  
  if (props.message.role !== 'assistant') {
    return
  }
  
  const messages = chatStore.messages
  const currentIndex = messages.findIndex(msg => msg === props.message)
  
  if (currentIndex === -1) {
    return
  }
  
  let userMessageIndex = -1
  for (let i = currentIndex - 1; i >= 0; i--) {
    if (messages[i].role === 'user') {
      userMessageIndex = i
      break
    }
  }
  
  if (userMessageIndex === -1) {
    NotificationService.error('未找到对应的用户问题')
    return
  }
  
  const userMessage = messages[userMessageIndex]

  const activeAgent = StorageService.getActiveAgent()
  const agentType = (activeAgent?.basic?.type) || (activeAgent?.config?.basic?.type) || 'assistant'
  
  // 构造知识库配置，用于重试时重新执行检索
  const kbConfig = {
    enabled: isKbEnabled.value,
    kbNames: selectedKbNames.value
  }

  if (agentType !== 'orchestrator') {
    chatStore.truncateMessagesTo(userMessageIndex - 1)
    // 普通对话重试时，通知关闭 Canvas 并清理 toolbar 状态
    eventBus.emit('chat-retry-cleanup')
  }

  // 在编排式智能体模式下，移除当前轮智能体回复
  if (agentType === 'orchestrator') {
    const removeFn = (chatStore as any).removeAssistantMessageAt;
    if (typeof removeFn === 'function') {
      removeFn(currentIndex);
    } else {
      chatStore.truncateMessagesTo(userMessageIndex - 1);
    }
    const retryFn = (chatStore as any).retryAssistant;
    if (typeof retryFn === 'function') {
      retryFn();
      return;
    }
    // 若没有 retry 方法，兜底为重新发送用户消息
    if (userMessage.content) {
      chatStore.sendMessage(userMessage.content, userMessage.files);
    }
    return;
  }

  if (userMessage.content) {
    chatStore.sendMessage(userMessage.content, userMessage.files, kbConfig)
  }
}

// 处理键盘事件
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    confirmEdit()
  }
}

// 切换编辑模式
function toggleEditMode() {
  if (props.message.role !== 'user') {
    return
  }
  
  isEditMode.value = !isEditMode.value
  emit('editModeChanged', isEditMode.value)
  
  if (isEditMode.value) {
    editContent.value = props.message.content || ''
    // 下一帧聚焦到输入框
    nextTick(() => {
      const textarea = document.querySelector('.edit-input textarea') as HTMLTextAreaElement
      if (textarea) {
        textarea.focus()
        // 将光标移到文本末尾
        textarea.setSelectionRange(textarea.value.length, textarea.value.length)
      }
    })
  }
}

// 取消编辑
function cancelEdit() {
  isEditMode.value = false
  editContent.value = ''
  emit('editModeChanged', false)
}

// 确认编辑并重新发送
function confirmEdit() {
  if (!editContent.value.trim()) {
    NotificationService.error('消息内容不能为空')
    return
  }
  
  const messages = chatStore.messages
  const currentIndex = messages.findIndex(msg => msg === props.message)
  
  if (currentIndex === -1) {
    return
  }
  
  // 截断消息列表到当前用户消息之前
  chatStore.truncateMessagesTo(currentIndex - 1)
  
  // 关闭编辑模式
  isEditMode.value = false
  emit('editModeChanged', false)
  
  // 发送编辑后的消息
  chatStore.sendMessage(
    editContent.value.trim(),
    props.message.files,
    undefined,
    props.message.turn_id ? { turnId: props.message.turn_id } : undefined
  )
  
  // 清空编辑内容
  editContent.value = ''
}
</script>

<style scoped>
.message-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  position: relative;
}

.assistant-model-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #1f2937;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  margin-right: 5px;
  background-color: #e4eaff;
  padding: 4px 8px;
  border-radius: 8px;
}

.assistant-model-icon {
  width: 17px;
  height: 17px;
  flex: 0 0 auto;
}

.assistant-model-name {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 15px;
}

.context-usage-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  border: none;
  background: transparent;
  cursor: pointer;
  padding: 0 2px;
  color: #6b7280;
  font-size: 12px;
  line-height: 1;
  white-space: nowrap;
  transition: color 0.2s ease;
}

.context-usage-trigger:hover {
  color: #374151;
}

.context-usage-ring {
  width: 18px;
  height: 18px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.context-usage-ring-svg {
  width: 18px;
  height: 18px;
  transform: rotate(-90deg);
}

.context-usage-ring-track,
.context-usage-ring-progress {
  fill: none;
  stroke-width: 2;
}

.context-usage-ring-track {
  stroke: #e5e7eb;
}

.context-usage-ring-progress {
  stroke: #9ca3af;
  stroke-linecap: round;
  transition: stroke-dashoffset 0.2s ease;
}

.context-usage-trigger-text {
  font-size: 14px;
  color: #494949;
  line-height: 1;
  margin-left: 2px;
}

.visualizer-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.btn-content-placeholder {
  display: flex;
  align-items: center;
  gap: 6px;
}

.message-toolbar {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px;
  border-radius: 8px;
  background: transparent;
  width: fit-content;
}

.last-assistant-toolbar {
  flex-wrap: wrap;
}

.toolbar-divider {
  flex: 0 0 auto;
  width: 1px;
  height: 16px;
  background: #e2e8f0;
  margin: 0 6px;
}

/* Icon transitions */
.icon-scale-enter-active,
.icon-scale-leave-active {
  transition: all 0.2s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.icon-scale-enter-from,
.icon-scale-leave-to {
  opacity: 0;
  transform: scale(0.5);
}

.icon-scale-enter-to,
.icon-scale-leave-from {
  opacity: 1;
  transform: scale(1);
}

/* Ensure icons are aligned properly during transition */
.toolbar-btn {
  position: relative;
  border: 1px solid transparent; /* Add transparent border to prevent layout shift */
  padding: 5px 9px; /* Reduce padding to compensate for border (original was 6px 10px) */
  transition: all 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); /* Slower, silkier easing */
  transform-origin: center;
}

.toolbar-btn .anticon, 
.toolbar-btn .audio-playing-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

/* Cool effect for the read button when playing */
.read-btn.is-playing {
  background: #ffffff;
  /* Keep border transparent (default) */
  color: #333;
  
  /* Pure shadow elevation, responsive to volume */
  box-shadow: 0 4px 16px rgba(0, 0, 0, calc(0.06 + var(--audio-volume) * 0.12));
  
  /* Subtle lift effect */
  transform: translateY(-1px);
}

.like-btn.is-active {
  color: #ff4d4f;
}

.dislike-btn.is-active {
  color: #595959;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  10%, 30%, 50%, 70%, 90% { transform: translateX(-2px); }
  20%, 40%, 60%, 80% { transform: translateX(2px); }
}

.shake-anim {
  animation: shake 0.4s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}
</style>

<style>
.context-usage-popover .ant-popover-inner {
  border-radius: 12px !important;
  padding: 0 !important;
}

.context-usage-card {
  min-width: 118px;
  padding: 10px 10px 9px;
  text-align: center;
}

.context-usage-title {
  font-size: 11px;
  line-height: 1.2;
  color: #94a3b8;
}

.context-usage-value {
  margin-top: 7px;
  font-size: 13px;
  line-height: 1.1;
  font-weight: 600;
  color: #4b5563;
}

.context-usage-action {
  width: 100%;
  margin-top: 8px;
  height: 26px;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.context-usage-action:disabled {
  cursor: not-allowed;
  opacity: 0.72;
}

.context-usage-description {
  margin-top: 7px;
  font-size: 11px;
  line-height: 1.4;
  color: #94a3b8;
}

.context-usage-action:hover {
  border-color: #cbd5e1;
  background: #f1f5f9;
  color: #334155;
}
</style>
