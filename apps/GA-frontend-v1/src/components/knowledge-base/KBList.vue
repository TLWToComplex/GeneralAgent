<template>
  <div class="knowledge-list-section">
    <div class="section-header">
      <h3 class="section-title">我的知识库</h3>
      <div class="section-actions">
        <div class="permission-filter" role="group" aria-label="权限筛选">
          <span class="permission-filter-indicator" :style="permissionIndicatorStyle"></span>
          <button
            class="permission-filter-btn"
            :class="{ active: modelPermissionFilter === 'public' }"
            @click="modelPermissionFilter = 'public'"
            :aria-pressed="modelPermissionFilter === 'public'"
          >
            共享
          </button>
          <button
            class="permission-filter-btn"
            :class="{ active: modelPermissionFilter === 'private' }"
            @click="modelPermissionFilter = 'private'"
            :aria-pressed="modelPermissionFilter === 'private'"
          >
            个人
          </button>
        </div>
        <div class="custom-search-wrapper">
          <SearchOutlined class="search-icon" />
          <input
            v-model="modelSearch"
            placeholder="搜索知识库"
            class="custom-input"
          />
        </div>
      </div>
    </div>

    <div ref="knowledgeGridRef" class="knowledge-grid">
      <div v-if="kbListLoading" class="list-loading">
        <a-spin :indicator="loadingIndicator" />
        <div class="loading-text">正在加载知识库列表...</div>
      </div>
      <template v-else>
        <div
          v-for="kb in filteredKnowledgeBases"
          :key="kb.id"
          :ref="(el) => setKnowledgeCardRef(kb.id, el as HTMLElement | null)"
          class="knowledge-card"
          :class="{ active: selectedKnowledgeBase?.id === kb.id }"
          :tabindex="selectedKnowledgeBase?.id === kb.id ? 0 : -1"
          @click="onSelect(kb)"
        >
          <div class="card-header">
            <div class="card-actions">
              <a-dropdown overlayClassName="kb-card-dropdown">
                <template #overlay>
                  <a-menu class="kb-card-menu">
                    <a-menu-item
                      @click.stop="$emit('edit', kb)"
                      :disabled="isEditDisabled(kb)"
                      class="kb-card-menu-item"
                    >
                      <EditOutlined/>
                      编辑知识库
                    </a-menu-item>
                    <a-menu-item
                      @click.stop="$emit('delete', kb)"
                      :disabled="isDeleteDisabled(kb)"
                      danger
                      class="kb-card-menu-item"
                    >
                      <DeleteOutlined/>
                      删除知识库
                    </a-menu-item>
                  </a-menu>
                </template>
                <MoreOutlined class="more-btn" @click.stop/>
              </a-dropdown>
            </div>
          </div>
          <div class="card-content">
            <div class="kb-title-row">
              <h4 class="kb-name" :title="kb.name">{{ kb.name }}</h4>
              <span class="kb-permission-tag" :class="`is-${resolvePermissionCode(kb)}`">
                {{ resolvePermissionLabel(kb) }}
              </span>
            </div>
            <p class="kb-description" :title="kb.description || '暂无描述'">{{ kb.description || '暂无描述' }}</p>
            <div class="kb-stats-wrapper">
              <div class="kb-stats">
                <span class="stat-item stat-docs" :title="`${kb.documentCount || 0} 个文档`">
                  <FileTextOutlined/>
                  <span class="stat-text">{{ kb.documentCount || 0 }} 个文档</span>
                </span>
                <span class="stat-item stat-date" :title="formatDate(kb.updatedAt)">
                  <ClockCircleOutlined/>
                  <span class="stat-text">{{ formatDate(kb.updatedAt) }}</span>
                </span>
                <span v-if="kb.vsType" class="stat-item stat-vs" :title="String(kb.vsType)">
                  <span class="stat-text">索引: {{ kb.vsType }}</span>
                </span>
                <span v-if="kb.embedModel" class="stat-item stat-embed" :title="String(kb.embedModel)">
                  <span class="stat-text">嵌入模型: {{ kb.embedModel }}</span>
                </span>
              </div>
              <a-tooltip v-if="kb.includeKg" placement="top">
                <template #title>
                  <span v-if="activeKgTaskKbNames?.has(kb.name)">该图谱库中有文档正在抽取或排队中</span>
                  <span v-else>已启用知识图谱</span>
                </template>
                <div 
                  class="kg-tag" 
                  :class="{ disabled: activeKgTaskKbNames?.has(kb.name) }" 
                  @click.stop="activeKgTaskKbNames?.has(kb.name) ? null : $emit('openKgModal', kb)"
                >
                  <ShareAltOutlined />
                </div>
              </a-tooltip>
            </div>
          </div>
        </div>

        <div v-if="knowledgeBases.length === 0" class="empty-state">
          <div class="empty-icon-ring">
            <FolderOpenOutlined/>
          </div>
          <h3>未创建知识库</h3>
          <p>创建您的第一个知识库，构建大模型知识体系</p>
        </div>

        <div v-else-if="filteredKnowledgeBases.length === 0" class="empty-state">
          <div class="empty-icon-ring">
            <SearchOutlined/>
          </div>
          <h3>未找到相关知识库</h3>
          <p>试试调整搜索关键词或清空搜索条件</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { ClockCircleOutlined, DeleteOutlined, EditOutlined, FileTextOutlined, FolderOpenOutlined, MoreOutlined, SearchOutlined, ShareAltOutlined } from '@ant-design/icons-vue'

interface KnowledgeBase {
  id: string
  name: string
  description?: string
  permissionCode?: 'private' | 'public'
  documentCount: number
  updatedAt: Date | string
  vsType?: string
  embedModel?: string
  includeKg?: boolean
}

import { formatDate } from '@/utils/formatters'
import { canManageKnowledgeBase } from '@/composables/useKnowledgeBaseAccess'

const props = defineProps<{
  knowledgeBases: KnowledgeBase[]
  kbListLoading: boolean
  selectedKnowledgeBase: KnowledgeBase | null
  searchKeyword: string
  permissionFilter: 'private' | 'public'
  loadingIndicator: any
  activeKgTaskKbNames?: Set<string>
  isCurrentUserAdmin?: boolean
}>()

const emit = defineEmits(['update:searchKeyword', 'update:permissionFilter', 'select', 'edit', 'delete', 'openKgModal'])

const modelSearch = computed({
  get: () => props.searchKeyword,
  set: (v: string) => emit('update:searchKeyword', v)
})

const modelPermissionFilter = computed({
  get: () => props.permissionFilter,
  set: (v: 'private' | 'public') => emit('update:permissionFilter', v)
})

const permissionIndicatorStyle = computed(() => {
  const index = modelPermissionFilter.value === 'private' ? 1 : 0
  return {
    transform: `translateX(${index * 100}%)`
  }
})

const resolvePermissionCode = (kb: KnowledgeBase): 'private' | 'public' => kb.permissionCode === 'public' ? 'public' : 'private'
const resolvePermissionLabel = (kb: KnowledgeBase) => resolvePermissionCode(kb) === 'public' ? '共享' : '个人'
// 编辑 / 删除共享知识库仅 admin 可用，与个人知识库保持一致；与聊天页工作区共用同一判定
const canManageKb = (kb: KnowledgeBase) => canManageKnowledgeBase(kb, !!props.isCurrentUserAdmin)
const isEditDisabled = (kb: KnowledgeBase) => !canManageKb(kb)
const isDeleteDisabled = (kb: KnowledgeBase) => !canManageKb(kb)

const filteredKnowledgeBases = computed(() => {
  if (!props.searchKeyword) return props.knowledgeBases
  const q = props.searchKeyword.toLowerCase()
  return props.knowledgeBases.filter(kb =>
    kb.name.toLowerCase().includes(q) || (kb.description?.toLowerCase().includes(q) ?? false)
  )
})

const knowledgeGridRef = ref<HTMLElement | null>(null)
const knowledgeCardRefs = new Map<string, HTMLElement>()

const setKnowledgeCardRef = (kbId: string, el: HTMLElement | null) => {
  if (!el) {
    knowledgeCardRefs.delete(kbId)
    return
  }
  knowledgeCardRefs.set(kbId, el)
}

const scrollToSelectedKnowledgeBaseCard = async () => {
  const selectedId = props.selectedKnowledgeBase?.id
  if (!selectedId) return
  const existsInFilteredList = filteredKnowledgeBases.value.some((kb) => kb.id === selectedId)
  if (!existsInFilteredList) return

  await nextTick()
  const cardEl = knowledgeCardRefs.get(selectedId)
  if (!cardEl) return

  cardEl.scrollIntoView({
    behavior: 'smooth',
    block: 'nearest'
  })
  cardEl.focus({ preventScroll: true })
}

watch(
  () => [props.selectedKnowledgeBase?.id || '', filteredKnowledgeBases.value.map((kb) => kb.id).join(',')],
  async () => {
    await scrollToSelectedKnowledgeBaseCard()
  },
  { flush: 'post' }
)

const onSelect = (kb: KnowledgeBase) => emit('select', kb)
</script>
