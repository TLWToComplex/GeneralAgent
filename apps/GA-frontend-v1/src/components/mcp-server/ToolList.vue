<template>
  <div class="tools-section">
    <div v-if="loading" class="tools-state tools-loading">
      <AppstoreAddOutlined class="state-icon" />
      <div class="state-title">正在刷新工具列表...</div>
      <div class="state-desc">正在根据当前表单配置重新连接 MCP 服务并获取最新工具</div>
    </div>

    <template v-else>
      <div v-if="tools && tools.length > 0" class="tool-cards">
        <div v-for="(tool, index) in tools" :key="index" class="tool-card">
          <div class="tool-info">
            <div class="tool-card-header">
              <span class="tool-card-name">{{ tool.name }}</span>
            </div>
            <div class="tool-card-desc">{{ tool.description || '无描述' }}</div>
            <div class="tool-actions">
              <a-button type="link" @click="$emit('show-detail', tool)" class="tool-info-btn">
                查看详情
              </a-button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="tools-state empty-tools-tip">
        <AppstoreAddOutlined class="state-icon" />
        <p class="state-title">当前服务未返回任何工具</p>
        <p class="state-desc">请检查服务连接、表单配置、请求头设置，或确认该 MCP 服务已正确暴露工具列表</p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { AppstoreAddOutlined } from '@ant-design/icons-vue';
import type { ServerTool } from './types';

interface Props {
  tools: ServerTool[];
  loading?: boolean;
}

interface Emits {
  (e: 'show-detail', tool: ServerTool): void;
}

defineProps<Props>();
defineEmits<Emits>();
</script>

<style scoped>
.tools-section {
  margin-top: 0;
  width: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  padding-top: 14px;
  box-sizing: border-box;
}

.tool-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 12px;
  width: 100%;
  flex: 1;
  min-height: 0;
  align-content: start;
  padding-bottom: 6px;
  box-sizing: border-box;
}

.tool-card {
  border: 1px solid #e6ecff;
  border-radius: 12px;
  overflow: hidden;
  background-color: #ffffff;
  transition: all 0.3s ease;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tool-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  border-color: #c0cfff;
}

.tool-info {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 0 10px;
}

.tool-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.tool-card-name {
  color: #262626;
  font-weight: 500;
  font-size: 14px;
}

.tool-card-desc {
  color: #595959;
  font-size: 12px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin-bottom: 8px;
}

.tool-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

.tool-info-btn {
  padding: 4px 0;
}

.tools-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex: 1;
  width: 100%;
  min-height: 0;
  text-align: center;
  color: #8c8c8c;
  padding: 40px 24px;
  background-color: #fafafa;
  border-radius: 16px;
  border: 1px dashed #d9e2f2;
  box-sizing: border-box;
}

.tools-loading {
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
  border-style: solid;
}

.state-icon {
  margin-bottom: 16px;
  color: #3b82f6;
  font-size: 32px;
}

.state-title {
  font-size: 16px;
  color: #1f2937;
  font-weight: 600;
  margin-bottom: 8px;
}

.state-desc {
  max-width: 520px;
  font-size: 14px;
  line-height: 1.7;
  color: #6b7280;
}
</style>
