<template>
  <div class="message-selection-wrapper" :class="{ 'selection-active': isSelectionMode }">
    <!-- 选择模式下的圆形选择框 -->
    <div v-if="isSelectionMode" class="selection-checkbox-container">
      <div class="selection-checkbox">
        <div 
          class="custom-radio"
          :class="{ 'selected': isSelected }"
          @click.stop="handleRadioClick"
        >
          <svg v-if="isSelected" class="check-icon" viewBox="0 0 16 16" fill="none">
            <path d="M13.5 4.5L6 12L2.5 8.5" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
    </div>
    
    <!-- 原始消息内容 -->
    <div 
      class="message-content"
      :class="{ 
        'clickable': isSelectionMode, 
        'selected': isSelected,
        'selection-single': isSelected && selectionPosition === 'single',
        'selection-first': isSelected && selectionPosition === 'first',
        'selection-middle': isSelected && selectionPosition === 'middle',
        'selection-last': isSelected && selectionPosition === 'last'
      }"
      @click="handleMessageClick"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">

interface Props {
  messageId: string
  isSelectionMode: boolean
  isSelected: boolean
  selectionPosition?: 'none' | 'single' | 'first' | 'middle' | 'last'
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'selection-changed': [messageId: string, selected: boolean]
}>()

function handleRadioClick() {
  emit('selection-changed', props.messageId, !props.isSelected)
}

function handleMessageClick() {
  if (props.isSelectionMode) {
    emit('selection-changed', props.messageId, !props.isSelected)
  }
}
</script>