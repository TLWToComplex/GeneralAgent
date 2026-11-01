<template>
  <div class="middle-section">
    <draggable 
      v-model="serverList" 
      class="service-list ant-list ant-list-split"
      item-key="name"
      :animation="200"
      :disabled="props.loading"
      @end="$emit('save')"
    >
      <template #item="{element: item}">
        <div 
          class="service-item ant-list-item"
          :class="{ 'selected': (item.id || item.name) === selectedServer }"
          @click="$emit('select', item)"
        >
          <div class="service-icon-wrapper">
            <span class="service-type-tag" :class="getTypeTagClass(item.type)">
              {{ getTypeTagText(item.type) }}
            </span>
              <div class="service-name" :title="item.name">{{ item.name }}</div>
            <div class="drag-handle">
              <MenuOutlined style="color: #6285e1"/>
            </div>
          </div>
        </div>
      </template>
    </draggable>
    
    <div v-if="props.loading" class="list-loading-overlay">
      <div class="list-loading-content">
        <LoadingOutlined spin style="font-size: 24px; color: #1890ff" />
        <div class="list-loading-text">正在加载…</div>
      </div>
    </div>

    <!-- 添加按钮放在列表底部 -->
    <div class="add-button-container">
      <button class="action-btn add-button" @click="$emit('add')">
        <PlusOutlined />
        添加
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { PlusOutlined, MenuOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import draggable from 'vuedraggable';
import type { ServerListItem } from './types';

interface Props {
  servers: ServerListItem[];
  selectedServer: string;
  loading?: boolean;
}

interface Emits {
  (e: 'update:servers', servers: ServerListItem[]): void;
  (e: 'select', server: ServerListItem): void;
  (e: 'add'): void;
  (e: 'save'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const serverList = computed({
  get: () => props.servers,
  set: (value) => emit('update:servers', value)
});

const getTypeTagText = (type?: string) => {
  if (type === 'streamableHttp') return 'HTTP';
  return 'SSE';
};

const getTypeTagClass = (type?: string) => ({
  'tag-http': type === 'streamableHttp',
  'tag-sse': type !== 'streamableHttp'
});
</script>

<style scoped>
.middle-section {
  width: 220px;
  border-right: 1px solid #f0f0f0;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  position: relative;
}

.service-list {
  padding: 8px 5px;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

:deep(.ant-list-item) {
  padding: 8px 16px;
  margin-bottom: 4px;
}

:deep(.ant-list-split .ant-list-item) {
  border-block-end: 1px solid rgba(255, 255, 255, 0);
}

.service-icon-wrapper {
  display: flex;
  align-items: center;
  width: 100%;
  position: relative;
}

.service-item {
  padding-top: 12px;
  padding-bottom: 12px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.service-item.selected {
  background-color: #e6f4ff !important;
  border-radius: 12px !important;
}

.service-item:hover {
  background-color: #f5f5f5;
  border-radius: 12px;
}

.service-item.selected:hover {
  background-color: #e6f4ff !important;
  border-radius: 12px !important;
}

.service-name {
  font-size: 14px;
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.service-type-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 18px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 10px;
  letter-spacing: 0.2px;
  font-weight: 600;
  line-height: 1;
  margin-right: 8px;
  margin-left: -6px;
  border: 1px solid transparent;
  box-sizing: border-box;
}

.service-type-tag.tag-sse {
  color: #0f62fe;
  background: linear-gradient(180deg, #eef5ff 0%, #e1edff 100%);
  border-color: #bfd6ff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.service-type-tag.tag-http {
  color: #7c3aed;
  background: linear-gradient(180deg, #f5efff 0%, #ede2ff 100%);
  border-color: #dcc7ff;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}

.drag-handle {
  cursor: move;
  opacity: 0;
  transition: opacity 0.3s ease;
  color: #1677ff;
  margin-left: 8px;
}

.service-item:hover .drag-handle {
  opacity: 1;
}

.add-button-container {
  padding: 16px;
  border-top: 1px solid #f0f0f0;
  position: sticky;
  bottom: 0;
  background-color: #fff;
  z-index: 1;
  margin-top: auto;
}

.action-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
}

.add-button {
  width: 100%;
  justify-content: center;
  background: #ffffff;
  border: 1px solid #e1e7eb;
  color: #374151;
}

.add-button:hover {
  background: #e5e7eb;
  transform: translateY(-1px);
}

.list-loading-overlay {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  background: rgba(255,255,255,0.6);
  pointer-events: all;
}
.list-loading-content { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.list-loading-text { font-size: 13px; color: #666; }
</style>
