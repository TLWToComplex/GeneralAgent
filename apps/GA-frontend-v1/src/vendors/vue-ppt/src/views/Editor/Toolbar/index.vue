<template>
  <div class="toolbar" :class="{ collapsed: !showToolbar }">
    <div class="toolbar-header">
      <span class="toolbar-title">{{ currentTitle }}</span>
      <div class="toolbar-close" @click="closeToolbar">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"></line>
          <line x1="6" y1="6" x2="18" y2="18"></line>
        </svg>
      </div>
    </div>
    <div class="content">
      <component :is="currentPanelComponent"></component>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { computed, watch } from 'vue'
import { storeToRefs } from 'pinia'
import { useMainStore } from '@/store'
import { ToolbarStates } from '@/types/toolbar'

import ElementStylePanel from './ElementStylePanel/index.vue'
import ElementPositionPanel from './ElementPositionPanel.vue'
import ElementAnimationPanel from './ElementAnimationPanel.vue'
import SlideDesignPanel from './SlideDesignPanel/index.vue'
import SlideAnimationPanel from './SlideAnimationPanel.vue'
import MultiPositionPanel from './MultiPositionPanel.vue'
import MultiStylePanel from './MultiStylePanel.vue'

const mainStore = useMainStore()
const { toolbarState, showToolbar } = storeToRefs(mainStore)

const setToolbarState = (value: ToolbarStates) => {
  mainStore.setToolbarState(value)
}

const closeToolbar = () => {
  mainStore.setShowToolbar(false)
}

const titleMap: Record<ToolbarStates, string> = {
  [ToolbarStates.EL_STYLE]: '样式',
  [ToolbarStates.EL_POSITION]: '位置',
  [ToolbarStates.EL_ANIMATION]: '动画',
  [ToolbarStates.SLIDE_DESIGN]: '设计',
  [ToolbarStates.SLIDE_ANIMATION]: '切换',
  [ToolbarStates.MULTI_STYLE]: '样式（多选）',
  [ToolbarStates.MULTI_POSITION]: '位置（多选）',
}

const currentTitle = computed(() => titleMap[toolbarState.value] || '设计')

const currentPanelComponent = computed(() => {
  const panelMap = {
    [ToolbarStates.EL_STYLE]: ElementStylePanel,
    [ToolbarStates.EL_POSITION]: ElementPositionPanel,
    [ToolbarStates.EL_ANIMATION]: ElementAnimationPanel,
    [ToolbarStates.SLIDE_DESIGN]: SlideDesignPanel,
    [ToolbarStates.SLIDE_ANIMATION]: SlideAnimationPanel,
    [ToolbarStates.MULTI_STYLE]: MultiStylePanel,
    [ToolbarStates.MULTI_POSITION]: MultiPositionPanel,
  }
  return panelMap[toolbarState.value] || null
})
</script>

<style lang="scss" scoped>
.toolbar {
  border-left: solid 1px $borderColor;
  background-color: #fff;
  display: flex;
  flex-direction: column;
  position: relative;
  transition: width 0.2s ease;
  width: 260px;
  flex-shrink: 0;
  overflow: hidden;

  &.collapsed {
    width: 0;
    border-left: none;
  }
}

.toolbar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 10px;
  border-bottom: 1px solid $borderColor;
  height: 40px;
}

.toolbar-title {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  flex: 1;
}

.toolbar-close {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  border-radius: 50%;
  color: #666;
  flex-shrink: 0;
  margin-left: 4px;

  &:hover {
    background: #f5f5f5;
    color: #333;
  }

  svg {
    transition: transform 0.2s ease;
  }
}

.content {
  padding: 12px;
  font-size: 13px;
  flex: 1;

  @include overflow-overlay;
}
</style>