<template>
  <div class="page-header">
    <div class="header-main">
      <div class="header-content">
        <h1 class="page-title">知识库</h1>
        <p class="page-description">管理您的知识库，上传文档、创建知识集合，为AI对话提供专业知识支持</p>
      </div>
    </div>
    <div class="header-actions">
      <button v-if="isAdmin" class="action-btn secondary" @click="$emit('config')">
        <SettingOutlined/>
        检索配置
      </button>
      <button class="action-btn secondary" @click="$emit('refresh')">
        <ReloadOutlined/>
        刷新
      </button>
      <button class="action-btn primary" @click="$emit('create')">
        <PlusOutlined/>
        创建知识库
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ReloadOutlined, PlusOutlined, SettingOutlined } from '@ant-design/icons-vue'

defineProps<{
  isAdmin?: boolean
}>()

defineEmits<{
  refresh: []
  create: []
  config: []
}>()
</script>