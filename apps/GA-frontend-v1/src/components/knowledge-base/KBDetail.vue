<template>
  <div class="knowledge-detail-section">
    <div class="detail-header">
      <h3 class="detail-title">{{ title || selectedKnowledgeBase?.name || '未选择知识库' }}</h3>
      <div class="detail-actions">
        <div class="custom-search-wrapper">
          <SearchOutlined class="search-icon" />
          <input
            v-model="modelDocumentSearch"
            placeholder="搜索文档"
            class="custom-input"
          />
        </div>
        <div v-if="canBulkHandleDocuments" class="bulk-group" :class="{ active: bulkMode, animating }" role="group" aria-label="批量处理" ref="bulkGroupEl">
          <button class="bulk-btn-origin" :class="{ compact: bulkMode }" @click="toggleBulkMode" :aria-pressed="bulkMode" :title="bulkMode ? '取消操作' : '批量处理'" :aria-label="bulkMode ? '退出批量处理' : '批量处理'">
            <svg v-if="!bulkMode" class="bulk-origin-icon" viewBox="0 0 1024 1024" width="18" height="18" aria-hidden="true">
              <path d="M768 102.4H307.2c-44.8 0-83.2 38.4-83.2 83.2v32c-25.6 0-51.2 25.6-51.2 51.2v608c0 25.6 25.6 51.2 51.2 51.2h460.8c25.6 0 51.2-25.6 51.2-51.2h32c44.8 0 83.2-38.4 83.2-83.2V185.6c0-44.8-38.4-83.2-83.2-83.2z m-96 755.2H236.8v-576h435.2v576z m115.2-70.4c0 12.8-6.4 19.2-19.2 19.2h-32V268.8c0-25.6-25.6-51.2-51.2-51.2H288v-32c0-12.8 6.4-19.2 19.2-19.2H768c12.8 0 19.2 6.4 19.2 19.2v601.6z" fill="currentColor"></path>
              <path d="M435.2 684.8l185.6-185.6-44.8-44.8-140.8 140.8L352 512l-44.8 44.8 128 128z" fill="currentColor"></path>
            </svg>
            <CloseOutlined v-else />
            <span v-show="showBulkText && !bulkMode" class="bulk-origin-text">批量处理</span>
          </button>
          <button v-if="bulkMode" class="bulk-btn" @click="onBulkDownload" :disabled="!hasSelection" aria-label="批量下载"
            title="批量下载">
            <DownloadOutlined />
          </button>
          <button v-if="bulkMode" class="bulk-btn danger" @click="onBulkDelete" :disabled="!hasSelection"
            aria-label="批量删除" title="批量删除">
            <DeleteOutlined />
          </button>
        </div>
        <button v-if="canUploadToSelectedKb" class="action-btn upload-doc-btn" @click="$emit('upload')">
          <UploadOutlined />
          上传文档
        </button>
      </div>
    </div>

    <div class="document-list">
      <div class="list-header">
        <div class="list-title-group">
          <span class="list-title">文档列表</span>
        </div>
        <div class="list-tools">
          <button v-if="bulkMode" class="select-toggle" :class="{ active: isAllSelected, indeterminate: hasSelection && !isAllSelected }" @click="toggleSelectAll" :aria-pressed="isAllSelected" :title="isAllSelected ? '取消' : '全选当前列表'">
            <span class="select-check">
              <span class="select-check-dot" :class="{ visible: isAllSelected }"></span>
              <span class="select-indeterminate" :class="{ visible: hasSelection && !isAllSelected }"></span>
            </span>
            <span class="select-text">
              <span class="select-text-inner" :class="{ active: isAllSelected }">{{ isAllSelected ? '取消' : '全选' }}</span>
            </span>
          </button>
          <span class="document-count">共 {{ selectedKnowledgeBase?.documents?.length || 0 }} 个文档</span>
          <div class="sort-control">
            <span class="sort-label">排序:</span>
            <div class="sort-segmented" role="group" aria-label="排序方式">
              <button class="sort-button" :class="{ active: sortBy === 'created' }" @click="sortBy = 'created'"
                :aria-pressed="sortBy === 'created'" title="按上传时间排序">
                <CalendarOutlined />
              </button>
              <button class="sort-button" :class="{ active: sortBy === 'no' }" @click="sortBy = 'no'"
                :aria-pressed="sortBy === 'no'" title="按文档编号排序">
                <OrderedListOutlined />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="document-items" ref="documentItemsEl">
        <div v-if="docsLoading" class="kb-document-skeleton" role="status" aria-label="正在加载文档" aria-busy="true">
          <div v-for="page in 3" :key="page" class="kb-document-placeholder" aria-hidden="true"><i></i><span><b></b><b></b></span></div>
          <p>正在取出文件夹中的文档…</p>
        </div>
        <div v-else-if="docsError && !selectedKnowledgeBase?.documents?.length" class="kb-docs-error" role="alert">
          <p>{{ docsError }}</p><button type="button" @click="emit('retry')">重新加载</button>
        </div>
        <template v-else>
          <div v-if="docsError" class="kb-docs-error" role="alert"><span>刷新失败，暂时显示已有文档。{{ docsError }}</span><button type="button" @click="emit('retry')">重试</button></div>
          <template v-if="(selectedKnowledgeBase?.documents?.length || 0) > 0 && filteredDocuments.length > 0">
            <div
              v-for="item in sortedDocumentItems"
              :key="item.doc.id"
              :ref="el => setDocumentItemRef(item.doc.id, el)"
              class="document-item"
              :class="[
                {
                  'is-processing': item.isProcessing,
                  'in-viewport': item.isInViewport,
                  'fx-processing': item.isProcessing && item.isInViewport,
                  'fx-running': item.kgState?.state === 'running' && item.isInViewport
                },
                item.kgState ? 'kg-state-' + item.kgState.state : ''
              ]"
              :style="item.progressStyle"
              @click="$emit('preview', item.doc)"
            >
              <div class="doc-bottom-progress-bar"></div>
              <div class="doc-check" :class="{ visible: bulkMode }">
                <a-checkbox :checked="item.selected" @update:checked="onDocUpdateChecked(item.doc.id, $event)" @click.stop />
              </div>
              <div class="doc-icon">
                <img :src="iconSrcByExt(item.doc.ext)" alt="file icon" class="doc-icon-img" />
              </div>
              <div class="doc-info">
                <div class="doc-name-row">
                  <div class="doc-name" :title="item.doc.name">
                    {{ item.doc.name }}
                  </div>
                  <span
                    v-if="item.kgState"
                    class="kg-state-chip"
                    :class="`is-${item.kgState.state}`"
                  >
                    {{ item.kgState.label }}
                  </span>
                </div>
                <div class="doc-meta-wrapper">
                  <Transition name="fade-status">
                    <div v-if="item.kgState" class="doc-kg-status-line" :key="'status-' + item.doc.id">
                      <span v-if="item.kgState.state === 'running'" class="kg-running-spinner"></span>
                      <span v-else class="kg-running-dot"></span>
                      <span class="kg-status-text">{{ item.kgState.message }}</span>
                      <span class="kg-status-pct">{{ item.kgState.progress }}%</span>
                    </div>
                    <div v-else class="doc-meta" :key="'meta-' + item.doc.id">
                      <span>{{ formatFileSize(item.doc.size) }}</span>
                      <span>{{ formatDate(item.doc.uploadedAt) }}</span>
                    </div>
                  </Transition>
                </div>
                <div class="doc-foot">
                  <div class="doc-badges">
                    <span v-if="item.doc.loader" class="badge-soft" :title="item.doc.loader">{{ item.doc.loader }}</span>
                    <span v-if="item.doc.splitter" class="badge-soft" :title="item.doc.splitter">{{ item.doc.splitter }}</span>
                    <span v-if="item.doc.docsCount !== undefined" class="badge-soft" :title="`切片数量 ${item.doc.docsCount}`">切片数量 {{ item.doc.docsCount }}</span>
                    <span v-if="item.doc.customDocs" class="badge-soft" title="自定义文档">自定义文档</span>
                    <span class="badge-soft" title="文件夹">文件夹</span>
                    <span class="badge-soft" title="向量库">向量库</span>
                    <template v-if="selectedKnowledgeBase?.includeKg && item.doc.graphStatus">
                      <span v-if="item.doc.graphStatus.completed" class="badge-soft" title="图谱库">图谱库</span>
                      <span v-else-if="!item.isProcessing" class="badge-soft badge-warning" title="未抽取出实体">
                        未抽取出实体
                      </span>
                    </template>
                  </div>
                </div>
              </div>
              <div class="doc-actions">
                <button class="icon-btn square" @click.stop="$emit('preview', item.doc)" aria-label="预览" title="预览">
                  <FileSearchOutlined class="icon-btn icon" />
                </button>
                <button class="icon-btn square" @click.stop="$emit('download', item.doc)" aria-label="下载" title="下载">
                  <DownloadOutlined class="icon-btn icon" />
                </button>
                <button
                  class="icon-btn square danger"
                  @click.stop="onDeleteClick(item.doc)"
                  :disabled="!canUploadToSelectedKb || item.isLocked"
                  aria-label="删除"
                  :title="!canUploadToSelectedKb ? '共享知识库仅 admin 可删除文档' : item.isLocked ? '图谱抽取未完成，暂不可删除' : '删除'"
                >
                  <DeleteOutlined class="icon-btn icon" />
                </button>
              </div>
            </div>
          </template>
          <div v-else-if="(selectedKnowledgeBase?.documents?.length || 0) > 0 && filteredDocuments.length === 0"
            class="empty-state small">
            <div class="empty-icon-ring">
              <SearchOutlined />
            </div>
            <h3>未找到匹配的文档</h3>
            <p>试试调整搜索关键词或清空搜索条件</p>
          </div>
          <div v-else class="empty-state small">
            <div class="empty-icon-ring">
              <FileTextOutlined />
            </div>
            <h3>{{ selectedKnowledgeBase ? '该知识库暂无文档' : '请选择左侧知识库' }}</h3>
            <p v-if="selectedKnowledgeBase && canUploadToSelectedKb">点击右上角"上传文档"添加文件，或拖拽文件上传</p>
            <p v-else-if="selectedKnowledgeBase">共享知识库仅 admin 可上传文档</p>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, nextTick, watch, onMounted, onBeforeUnmount } from 'vue'
import type { CSSProperties } from 'vue'
import { DeleteOutlined, DownloadOutlined, FileSearchOutlined, FileTextOutlined, UploadOutlined, CalendarOutlined, OrderedListOutlined, CloseOutlined, SearchOutlined } from '@ant-design/icons-vue'
import PdfSvg from '@/assets/image/svg/pdf-icon.svg'
import WordSvg from '@/assets/image/svg/Word.svg'
import ExcelSvg from '@/assets/image/svg/Excel.svg'
import MarkdownSvg from '@/assets/image/svg/Markdown.svg'
import TxtSvg from '@/assets/image/svg/Txt.svg'
import { formatDate, formatFileSize, toTimestamp } from '@/utils/formatters'
import NotificationService from '@/utils/NotificationService'
import { canManageKnowledgeBase } from '@/composables/useKnowledgeBaseAccess'
import type { KnowledgeGraphTaskStatus } from '@/services/knowledgeBase'

interface Document {
  id: string
  name: string
  size: number
  uploadedAt: Date | string
  ext?: string
  loader?: string
  docsCount?: number
  splitter?: string
  customDocs?: boolean
  no?: number
  graphStatus?: {
    completed: boolean
    errorMsg: string
  }
}
interface KnowledgeBase {
  id: string
  name: string
  includeKg?: boolean
  permissionCode?: 'private' | 'public'
  documents?: Document[]
}

const props = defineProps<{
  title?: string
  selectedKnowledgeBase: KnowledgeBase | null
  docsLoading: boolean
  docsError?: string
  documentSearchKeyword: string
  loadingIndicator: any
  kgTasks?: KnowledgeGraphTaskStatus[]
  kgPendingDocNameMap?: Record<string, boolean>
  isCurrentUserAdmin?: boolean
}>()

const emit = defineEmits(['retry', 'update:documentSearchKeyword', 'upload', 'preview', 'download', 'delete', 'bulk-download', 'bulk-delete'])

// 共享（public）知识库仅 admin 可写（上传 / 删除 / 批量处理）；个人知识库不受限制。
// 与设置页、聊天页工作区共用同一判定
const canWriteSelectedKb = computed(() =>
  !!props.selectedKnowledgeBase && canManageKnowledgeBase(props.selectedKnowledgeBase, !!props.isCurrentUserAdmin)
)
const canUploadToSelectedKb = canWriteSelectedKb
const canBulkHandleDocuments = canWriteSelectedKb

type KgDocState = {
  state: 'running' | 'pending' | 'waiting'
  progress: number
  message: string
  label: string
}

type SortedDocumentItem = {
  doc: Document
  kgState?: KgDocState
  isProcessing: boolean
  isLocked: boolean
  isInViewport: boolean
  selected: boolean
  progressStyle?: CSSProperties
}

const documentItemsEl = ref<HTMLElement | null>(null)
const visibleDocIds = ref<Set<string>>(new Set())
const documentItemElements = new Map<string, HTMLElement>()
let documentItemsObserver: IntersectionObserver | null = null

const resolveObservedElement = (target: Element | { $el?: Element } | null): HTMLElement | null => {
  if (target instanceof HTMLElement) return target
  if (target && '$el' in target && target.$el instanceof HTMLElement) return target.$el
  return null
}

const disconnectDocumentItemsObserver = () => {
  if (documentItemsObserver) {
    documentItemsObserver.disconnect()
    documentItemsObserver = null
  }
}

const setVisibleDocId = (id: string, visible: boolean) => {
  const next = new Set(visibleDocIds.value)
  const changed = visible ? !next.has(id) : next.delete(id)
  if (!changed) return
  if (visible) next.add(id)
  visibleDocIds.value = next
}

const setDocumentItemRef = (id: string, el: Element | { $el?: Element } | null) => {
  const node = resolveObservedElement(el)
  const previous = documentItemElements.get(id)

  if (!node) {
    if (previous && documentItemsObserver) {
      documentItemsObserver.unobserve(previous)
    }
    documentItemElements.delete(id)
    setVisibleDocId(id, false)
    return
  }

  if (previous && previous !== node && documentItemsObserver) {
    documentItemsObserver.unobserve(previous)
  }

  node.dataset.docId = id
  documentItemElements.set(id, node)
  if (documentItemsObserver) {
    documentItemsObserver.observe(node)
  }
}

const refreshDocumentItemsObserver = async () => {
  await nextTick()

  disconnectDocumentItemsObserver()

  const currentIds = new Set(sortedDocuments.value.map(doc => doc.id))
  documentItemElements.forEach((_, id) => {
    if (!currentIds.has(id)) {
      documentItemElements.delete(id)
    }
  })

  if (currentIds.size === 0) {
    visibleDocIds.value = new Set()
    return
  }

  if (!documentItemsEl.value || typeof IntersectionObserver === 'undefined') {
    visibleDocIds.value = currentIds
    return
  }

  visibleDocIds.value = new Set()
  documentItemsObserver = new IntersectionObserver((entries) => {
    const next = new Set(visibleDocIds.value)
    let changed = false

    entries.forEach((entry) => {
      const id = (entry.target as HTMLElement).dataset.docId
      if (!id) return

      const isVisible = entry.isIntersecting || entry.intersectionRatio > 0
      if (isVisible) {
        if (!next.has(id)) {
          next.add(id)
          changed = true
        }
      } else if (next.delete(id)) {
        changed = true
      }
    })

    if (changed) {
      visibleDocIds.value = next
    }
  }, {
    root: documentItemsEl.value,
    threshold: 0.01
  })

  documentItemElements.forEach((node) => {
    if (currentIds.has(node.dataset.docId || '')) {
      documentItemsObserver?.observe(node)
    }
  })
}

const selectedIdSet = computed(() => new Set(selectedIds.value))
const pendingDocNameSet = computed(() => new Set(Object.keys(props.kgPendingDocNameMap || {})))
const activeTaskStateLookup = computed(() => {
  const direct = new Map<string, KgDocState>()
  const fallback: Array<{ message: string, state: KgDocState }> = []

  for (const task of props.kgTasks || []) {
    if (task.status !== 'running' && task.status !== 'pending') continue

    const state: KgDocState = task.status === 'running'
      ? {
          state: 'running',
          progress: Math.max(0, Math.min(100, Number(task.progress) || 0)),
          message: task.message || '正在抽取图谱',
          label: '抽取中'
        }
      : {
          state: 'pending',
          progress: Math.max(0, Math.min(99, Number(task.progress) || 0)),
          message: task.message || '已排队，等待前序文档完成',
          label: '排队中'
        }

    const fileName = task.file_name?.trim()
    if (fileName) {
      direct.set(fileName, state)
      continue
    }
    if (task.message) {
      fallback.push({ message: task.message, state })
    }
  }

  return { direct, fallback }
})

const docKgStateMap = computed(() => {
  const map = new Map<string, KgDocState>()
  const docs = props.selectedKnowledgeBase?.documents || []
  const { direct, fallback } = activeTaskStateLookup.value

  docs.forEach(doc => {
    const directState = direct.get(doc.name)
    if (directState) {
      map.set(doc.id, directState)
      return
    }

    const fallbackState = fallback.find(item => item.message.includes(doc.name))?.state
    if (fallbackState) {
      map.set(doc.id, fallbackState)
      return
    }

    if (pendingDocNameSet.value.has(doc.name)) {
      map.set(doc.id, {
        state: 'waiting',
        progress: 0,
        message: '已提交图谱任务，等待调度',
        label: '待调度'
      })
    }
  })

  return map
})

const sortedDocumentItems = computed<SortedDocumentItem[]>(() =>
  sortedDocuments.value.map((doc) => {
    const kgState = docKgStateMap.value.get(doc.id)
    const isProcessing = !!kgState
    return {
      doc,
      kgState,
      isProcessing,
      isLocked: isProcessing,
      isInViewport: visibleDocIds.value.has(doc.id),
      selected: selectedIdSet.value.has(doc.id),
      progressStyle: isProcessing
        ? { '--doc-progress': `${kgState!.progress}%` } as CSSProperties
        : undefined
    }
  })
)

const isDocLocked = (doc: Document) => docKgStateMap.value.has(doc.id)
const onDeleteClick = (doc: Document) => {
  if (!canUploadToSelectedKb.value) {
    NotificationService.info('共享知识库仅 admin 可删除文档')
    return
  }
  if (isDocLocked(doc)) {
    NotificationService.info('该文档图谱抽取未完成，暂不可删除')
    return
  }
  emit('delete', doc)
}

const modelDocumentSearch = computed({
  get: () => props.documentSearchKeyword,
  set: (v: string) => emit('update:documentSearchKeyword', v)
})

const filteredDocuments = computed(() => {
  const docs = props.selectedKnowledgeBase?.documents || []
  const q = props.documentSearchKeyword.trim().toLowerCase()
  if (!q) return docs
  return docs.filter(doc =>
    doc.name.toLowerCase().includes(q) ||
    (doc.loader ? doc.loader.toLowerCase().includes(q) : false) ||
    (doc.splitter ? doc.splitter.toLowerCase().includes(q) : false)
  )
})

const sortBy = ref<'created' | 'no'>('created')

const sortedDocuments = computed(() => {
  const list = filteredDocuments.value.slice()
  if (sortBy.value === 'no') {
    return list.sort((a, b) => (a.no ?? 0) - (b.no ?? 0))
  }
  return list.sort((a, b) => toTimestamp(b.uploadedAt) - toTimestamp(a.uploadedAt))
})

const selectedIds = ref<string[]>([])
const selectableIds = computed(() => filteredDocuments.value.map(doc => doc.id))
const onDocUpdateChecked = (id: string, checked: boolean) => {
  const arr = selectedIds.value.slice()
  const i = arr.indexOf(id)
  if (checked && i < 0) arr.push(id)
  if (!checked && i >= 0) arr.splice(i, 1)
  selectedIds.value = arr
}
const hasSelection = computed(() => selectedIds.value.length > 0)
const isAllSelected = computed(() => selectableIds.value.length > 0 && selectableIds.value.every(id => selectedIdSet.value.has(id)))
const onBulkDownload = () => emit('bulk-download', selectedIds.value.slice())
const onBulkDelete = () => emit('bulk-delete', selectedIds.value.slice())
const bulkMode = ref(false)
const animating = ref(false)
const showBulkText = ref(true)
const bulkGroupEl = ref<HTMLElement | null>(null)
const toggleSelectAll = () => {
  const ids = selectableIds.value
  if (ids.length === 0) return
  if (isAllSelected.value) {
    const visibleIdSet = new Set(ids)
    selectedIds.value = selectedIds.value.filter(id => !visibleIdSet.has(id))
  } else {
    const merged = new Set(selectedIdSet.value)
    ids.forEach(id => merged.add(id))
    selectedIds.value = Array.from(merged)
  }
}
const toggleBulkMode = async () => {
  const el = bulkGroupEl.value
  const startWidth = el?.offsetWidth
  if (el && startWidth && startWidth > 0) {
    el.style.width = startWidth + 'px'
  }
  animating.value = true
  if (bulkMode.value) {
    showBulkText.value = true
    bulkMode.value = false
    selectedIds.value = []
  } else {
    showBulkText.value = false
    bulkMode.value = true
  }
  await nextTick()
  window.setTimeout(() => {
    if (el) {
      el.style.width = ''
    }
    animating.value = false
    // keep text visibility as set at toggle time
  }, 300)
}

watch(selectableIds, (ids) => {
  if (selectedIds.value.length > 0) {
    const selectableIdSet = new Set(ids)
    selectedIds.value = selectedIds.value.filter(id => selectableIdSet.has(id))
  }
})

// 当批量处理按钮被隐藏（如切换为共享库且非 admin）时，退出批量模式
watch(canBulkHandleDocuments, (canBulk) => {
  if (!canBulk && bulkMode.value) {
    bulkMode.value = false
    showBulkText.value = true
    selectedIds.value = []
  }
})

watch(
  () => props.selectedKnowledgeBase?.documents?.length ?? 0,
  (len) => {
    if (len === 0 && bulkMode.value) {
      bulkMode.value = false
      showBulkText.value = true
      selectedIds.value = []
    }
  }
)

watch(
  () => sortedDocuments.value.map(doc => doc.id).join('|'),
  () => {
    refreshDocumentItemsObserver()
  },
  { flush: 'post' }
)

onMounted(() => {
  refreshDocumentItemsObserver()
})

onBeforeUnmount(() => {
  disconnectDocumentItemsObserver()
})

const iconSrcByExt = (ext?: string) => {
  const e = (ext || '').toLowerCase()
  if (e === '.pdf') return PdfSvg
  if (e === '.doc' || e === '.docx') return WordSvg
  if (e === '.md' || e === '.markdown') return MarkdownSvg
  if (e === '.csv' || e === '.xls' || e === '.xlsx') return ExcelSvg
  return TxtSvg
}
</script>

<style scoped>
/* 搜索框样式 */
.custom-search-wrapper {
  display: flex;
  align-items: center;
  background-color: #f2f3f5;
  border-radius: 12px;
  padding: 8px 16px;
  border: 1px solid transparent;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  width: 150px;
}

.custom-search-wrapper:hover {
  background-color: #e5e7eb;
}

.custom-search-wrapper:focus-within {
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.search-icon {
  color: #999;
  font-size: 16px;
  margin-right: 8px;
}

.custom-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-size: 14px;
  color: #333;
}

.custom-input::placeholder {
  color: #bfbfbf;
}

.list-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  min-height: 32px;
  flex-wrap: nowrap;
}

.list-title-group {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.list-title {
  font-weight: 600;
  font-size: 14px;
}

.list-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  min-height: 32px;
}

.sort-control {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sort-label {
  color: #666;
  font-size: 13px;
}

.document-count {
  color: #666;
  font-size: 13px;
}

.select-toggle {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 28px;
  padding: 0 10px;
  border-radius: 8px;
  border: none;
  background: #edf1f5;
  color: #4b5563;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.select-toggle:hover {
  background: #e3e8ef;
  color: #111827;
}

.select-toggle.active {
  background: #dbe7ff;
  color: #1e3a8a;
}

.select-toggle.indeterminate {
  background: #e7eef8;
  color: #1f2937;
}

.select-check {
  width: 14px;
  height: 14px;
  border-radius: 6px;
  border: none;
  background: rgba(255, 255, 255, 0.9);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 14px;
  position: relative;
  overflow: hidden;
  transition: background-color 0.2s ease;
}

.select-toggle.active .select-check {
  background: #1d4ed8;
}

.select-check-dot {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: #ffffff;
  opacity: 0;
  transform: scale(0.2);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.select-indeterminate {
  width: 7px;
  height: 2px;
  border-radius: 999px;
  background: #1d4ed8;
  position: absolute;
  opacity: 0;
  transform: scaleX(0.2);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.select-check-dot.visible {
  opacity: 1;
  transform: scale(1);
}

.select-indeterminate.visible {
  opacity: 1;
  transform: scaleX(1);
}

.select-toggle.active .select-indeterminate {
  background: #ffffff;
}

.select-text {
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
}

.select-text-inner {
  display: inline-block;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.select-text-inner.active {
  transform: translateY(0);
}

.select-toggle:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.35);
}

.sort-segmented {
  display: flex;
  border: 1px solid #e3e3e3;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  align-items: center;
  justify-content: center;
}

.sort-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: #9f9f9f;
  background: transparent;
  border: none;
  cursor: pointer;
}

.sort-button:hover {
  background: #f7fafc;
}

.sort-button.active {
  background: #f3f4f6;
  color: #444444;
}

.sort-button :deep(.anticon) {
  font-size: 16px;
}

.bulk-group {
  display: inline-flex;
  align-items: center;
  border: 1px solid #e3e3e3;
  background: #fff;
  border-radius: 12px;
  overflow: hidden;
}

.bulk-btn-origin {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 114px;
  height: 32px;
  border: none;
  background: transparent;
  color: #1f2937;
  cursor: pointer;
  gap: 4px;
  transition: width 0.28s ease, background-color 0.2s ease;
  overflow: hidden;
  white-space: nowrap;
}

.bulk-btn-origin:hover {
  background: #f3f4f6;
}

.bulk-btn-origin.compact {
  width: 38px;
}

/* “批量处理”四个字：按钮上没有显式字号（工作区布局会压到 12px），这里固定 13px；
   字形在行框内偏上，margin-top 1px 与 18px 图标做光学居中 */
.bulk-origin-text {
  font-size: 13px;
  margin-top: 1px;
}

.bulk-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 32px;
  border: none;
  background: transparent;
  color: #1f2937;
  cursor: pointer;
}

.bulk-btn:hover {
  background: #f3f4f6;
}

.bulk-btn-origin.compact:hover {
  background: #f3f4f6;
}

.bulk-btn[disabled] {
  opacity: 0.5;
  cursor: not-allowed;
}

.bulk-btn[disabled]:hover,
.bulk-btn-origin.compact[disabled]:hover,
.bulk-btn.danger[disabled]:hover {
  background: transparent;
  color: inherit;
}

.bulk-btn.danger {
  color: #ef4444;
}

.bulk-btn.danger:hover {
  background: #fee2e2;
  color: #ff4040;
}

.bulk-btn :deep(.anticon),
.bulk-btn-origin.compact :deep(.anticon) {
  font-size: 13px;
}

.doc-check {
  width: 0;
  opacity: 0;
  overflow: hidden;
  margin-right: -12px;
  margin-inline-end: -12px;
  pointer-events: none;
  flex: 0 0 auto;
  transition: width 0.28s ease, opacity 0.28s ease, margin-right 0.28s ease, margin-inline-end 0.28s ease;
}

.doc-check.visible {
  /* 与 knowledge-base.css 里放大后的圆形复选框（17px）保持一致，
     容器比复选框窄时 overflow: hidden 会把圆的侧边裁掉 */
  width: 17px;
  opacity: 1;
  margin-right: 0;
  margin-inline-end: 0;
  pointer-events: auto;
}

.document-item {
  content-visibility: auto;
  contain-intrinsic-size: 84px;
}
</style>

<style scoped>
.kb-document-skeleton { padding: 8px 12px; }
.kb-document-placeholder { display: flex; align-items: center; gap: 16px; min-height: 88px; padding: 18px 14px; border-bottom: 1px solid #eef1f7; }
.kb-document-placeholder i { width: 34px; height: 43px; flex: none; background: #edf1f9; border: 1px solid #dfe6f3; border-radius: 3px 10px 3px 3px; }
.kb-document-placeholder span { display: grid; gap: 12px; width: 55%; }
.kb-document-placeholder b { display: block; height: 9px; background: #edf1f7; border-radius: 4px; }
.kb-document-placeholder b + b { width: 58%; height: 6px; }
.kb-document-skeleton p { color: #8b99af; font-size: 12px; padding: 12px; }
.kb-docs-error { padding: 24px; color: #8b7180; font-size: 13px; }
.kb-docs-error button { margin-left: 12px; padding: 6px 12px; border: 1px solid #d6dfef; border-radius: 8px; background: #f5f7fc; color: #566bb4; cursor: pointer; }
</style>
