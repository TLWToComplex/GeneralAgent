<template>
  <a-modal v-model:open="modelOpen" centered :width="800"
    :maskClosable="!(slicesLoading || slicesSaving)" :keyboard="!(slicesLoading || slicesSaving)"
    :closable="!(slicesLoading || slicesSaving)" :wrap-class-name="'slices-modal-wrapper'">
    <template #title>
      <div class="modal-title-ellipsis" :title="`文档切片 - ${viewingDocName}`">
        文档切片 - {{ viewingDocName }}
      </div>
    </template>
    <div class="slices-modal">
      <div v-if="slicesLoading" class="slices-loading">
        <a-spin :indicator="loadingIndicator" />
        <div class="loading-text">正在加载切片...</div>
      </div>
      <template v-else>
        <div class="slices-toolbar">
          <div class="left">
            <span class="doc-count">共 {{ docSlices.length }} 个切片</span>
          </div>
          <div class="right">
            <div class="custom-search-wrapper">
              <SearchOutlined class="search-icon" />
              <input v-model="modelSliceSearch" placeholder="搜索切片内容..." class="custom-input" />
            </div>
          </div>
        </div>

        <div v-if="unsavedCount > 0" class="unsaved-banner">
          有 {{ unsavedCount }} 处未保存修改
        </div>

        <div v-if="filteredSlices.length === 0" class="slices-empty">暂无切片数据</div>
        <div v-else ref="slicesListRef" class="slices-list">
          <div v-for="s in filteredSlices" :key="s.__key" class="slice-card">
            <div class="slice-header">
              <div class="title">切片 {{ s.__index + 1 }}</div>
              <div class="actions">
                <button v-if="!isEditing(s.__index)" class="btn-text small" @click="startEditSlice(s.__index)">
                  <EditOutlined /> 编辑
                </button>
                <template v-else>
                  <button class="btn-text small" @click="saveEditSlice(s.__index)">
                    <CheckOutlined /> 保存
                  </button>
                  <button class="btn-text small danger" :disabled="slicesSaving" @click="cancelEditSlice(s.__index)">
                    <CloseOutlined /> 取消
                  </button>
                </template>
                <button class="btn-text small" @click="copySlice(s.__index)">
                  <CopyOutlined /> 复制
                </button>
                <button class="btn-text small" :disabled="!isSliceCollapsible(s.__index)"
                  @click="toggleExpandSlice(s.__index)">
                  <template v-if="isExpanded(s.__index)">
                    <UpOutlined style="margin-right: -2px;" /> 收起
                  </template>
                  <template v-else>
                    <DownOutlined style="margin-right: -2px;" /> 展开
                  </template>
                </button>
              </div>
            </div>
            <div class="slice-meta">
              <span v-if="s.metadata?.source" class="meta">来源: {{ s.metadata.source }}</span>
              <span v-if="s.score !== undefined" class="meta">评分: {{ s.score }}</span>
              <span v-if="s.metadata?.pk !== undefined" class="meta">标识: {{ s.metadata.pk }}</span>
            </div>
            <div class="slice-content" :ref="(el) => setSliceContentRef(el, s.__index)"
              :class="{ expanded: isExpanded(s.__index), collapsible: isSliceCollapsible(s.__index), 'non-collapsible': !isSliceCollapsible(s.__index) }">
              <template v-if="isEditing(s.__index)">
                <a-textarea v-model:value="editingStates[s.__index].draft" :auto-size="{ minRows: 4, maxRows: 10 }"
                  class="slice-textarea" />
              </template>
              <template v-else>
                <pre class="slice-text">{{ s.page_content }}</pre>
              </template>
            </div>
          </div>
        </div>
      </template>
    </div>
    <template #footer>
      <div class="slices-footer">
        <a-button v-if="unsavedCount >= 2" type="primary" :disabled="slicesLoading || slicesSaving"
          @click="saveAllSlices">保存全部</a-button>
      </div>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch, nextTick, onMounted, onUnmounted } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { CheckOutlined, CloseOutlined, CopyOutlined, DownOutlined, EditOutlined, UpOutlined, SearchOutlined } from '@ant-design/icons-vue'
import NotificationService from '@/utils/NotificationService'
import { copyText } from '@/utils/clipboard'
import { searchKnowledgeBaseDocs, updateKnowledgeBaseDocs } from '@/services/knowledgeBase'
import { getCachedRetrievalConfig } from '@/services/aiSystemConfig'

type SliceItem = {
  page_content: string
  metadata?: { source?: string; pk?: number | string;[key: string]: any }
  type?: string
  id?: string
  score?: number
}

interface KnowledgeBase { name: string }

const props = defineProps<{
  open: boolean
  viewingDocName: string
  selectedKnowledgeBase: KnowledgeBase | null
  loadingIndicator: any
}>()

const emit = defineEmits(['update:open'])

const modelOpen = computed({
  get: () => props.open,
  set: (v: boolean) => emit('update:open', v)
})

// 内部状态
const slicesLoading = ref<boolean>(false)
const slicesSaving = ref<boolean>(false)
const sliceSearchKeyword = ref<string>('')
const docSlices = ref<SliceItem[]>([])
const expandedSlices = ref<Set<number>>(new Set())
type EditingState = { editing: boolean; draft: string; prevExpanded?: boolean }
const editingStates = ref<Record<number, EditingState>>({})
const contentRefs = ref<Record<number, HTMLElement | null>>({})
const collapsibleStates = ref<Record<number, boolean>>({})
const slicesListRef = ref<HTMLElement | null>(null)
const hoveringScrollbar = ref(false)
const pointerDown = ref(false)
const lastPointerPos = ref<{ x: number; y: number }>({ x: 0, y: 0 })
const SCROLLBAR_GUTTER_WIDTH = 20
let scrollbarHideTimer: number | null = null

const modelSliceSearch = computed({
  get: () => sliceSearchKeyword.value,
  set: (v: string) => { sliceSearchKeyword.value = v }
})

const filteredSlices = computed(() => {
  const q = sliceSearchKeyword.value.trim().toLowerCase()
  return docSlices.value
    .map((s, i) => ({ ...s, __index: i, __key: s.id ?? `${i}` }))
    .filter(s => {
      if (!q) return true
      const text = `${s.page_content}\n${JSON.stringify(s.metadata || {})}`.toLowerCase()
      return text.includes(q)
    })
})

const unsavedCount = computed(() => {
  return Object.entries(editingStates.value)
    .filter(([idx, st]) => st.editing && st.draft !== (docSlices.value[Number(idx)]?.page_content || ''))
    .length
})

const isExpanded = (idx: number) => expandedSlices.value.has(idx)
const toggleExpandSlice = (idx: number) => {
  const s = expandedSlices.value
  if (s.has(idx)) s.delete(idx); else s.add(idx)
  expandedSlices.value = new Set(s)
  nextTick(() => recalcCollapsible())
}

const setSliceContentRef = (el: Element | ComponentPublicInstance | null, idx: number) => {
  let node: HTMLElement | null = null
  if (el && (el as any).nodeType) {
    node = el as HTMLElement
  } else if (el && (el as any).$el) {
    node = (el as any).$el as HTMLElement
  }
  contentRefs.value[idx] = node
}

const calcIsCollapsible = (idx: number) => {
  const el = contentRefs.value[idx]
  if (el && !isExpanded(idx)) {
    return el.scrollHeight > el.clientHeight + 1
  }
  const text = docSlices.value[idx]?.page_content || ''
  const lineCount = (text.match(/\n/g) || []).length + 1
  return text.length > 300 || lineCount > 6
}

const recalcCollapsible = () => {
  const next: Record<number, boolean> = {}
  for (let i = 0; i < docSlices.value.length; i++) {
    next[i] = calcIsCollapsible(i)
  }
  collapsibleStates.value = next
}

const isSliceCollapsible = (idx: number) => {
  const v = collapsibleStates.value[idx]
  return typeof v === 'boolean' ? v : calcIsCollapsible(idx)
}

const isPointerInScrollbarGutter = (el: HTMLElement) => {
  const rect = el.getBoundingClientRect()
  const x = lastPointerPos.value.x
  const y = lastPointerPos.value.y
  const withinY = y >= rect.top && y <= rect.bottom
  const withinGutterX = x >= rect.right - SCROLLBAR_GUTTER_WIDTH && x <= rect.right
  return withinY && withinGutterX
}

const showScrollbarDuringScroll = () => {
  if (!slicesListRef.value) return
  const el = slicesListRef.value
  el.classList.remove('hide-scrollbar')
  if (scrollbarHideTimer) {
    clearTimeout(scrollbarHideTimer)
    scrollbarHideTimer = null
  }
  if (
    (pointerDown.value && isPointerInScrollbarGutter(el)) ||
    hoveringScrollbar.value
  ) {
    return
  }
  scrollbarHideTimer = window.setTimeout(() => {
    slicesListRef.value?.classList.add('hide-scrollbar')
    scrollbarHideTimer = null
  }, 600)
}

const onPointerDown = (e: PointerEvent) => {
  pointerDown.value = true
  lastPointerPos.value = { x: e.clientX, y: e.clientY }
  if (slicesListRef.value && isPointerInScrollbarGutter(slicesListRef.value)) {
    showScrollbarDuringScroll()
  }
}

const onPointerUp = (e: PointerEvent) => {
  lastPointerPos.value = { x: e.clientX, y: e.clientY }
  pointerDown.value = false
  if (slicesListRef.value && isPointerInScrollbarGutter(slicesListRef.value)) {
    showScrollbarDuringScroll()
  }
}

const onPointerMove = (e: PointerEvent) => {
  lastPointerPos.value = { x: e.clientX, y: e.clientY }
  if (!slicesListRef.value) return
  const inGutter = isPointerInScrollbarGutter(slicesListRef.value)
  if (inGutter) {
    hoveringScrollbar.value = true
    slicesListRef.value.classList.remove('hide-scrollbar')
    if (scrollbarHideTimer) {
      clearTimeout(scrollbarHideTimer)
      scrollbarHideTimer = null
    }
  } else if (hoveringScrollbar.value) {
    hoveringScrollbar.value = false
    showScrollbarDuringScroll()
  }
}

const isEditing = (idx: number) => !!editingStates.value[idx]?.editing
const startEditSlice = (idx: number) => {
  const current = docSlices.value[idx]
  const wasExpanded = isExpanded(idx)
  editingStates.value[idx] = { editing: true, draft: current?.page_content || '', prevExpanded: wasExpanded }
  const s = expandedSlices.value
  s.add(idx)
  expandedSlices.value = new Set(s)
  nextTick(() => recalcCollapsible())
}
const cancelEditSlice = (idx: number) => {
  const st = editingStates.value[idx]
  if (!st) return
  const s = new Set(expandedSlices.value)
  if (st.prevExpanded) s.add(idx); else s.delete(idx)
  expandedSlices.value = s
  editingStates.value[idx] = { editing: false, draft: '' }
}
const saveEditSlice = async (idx: number) => {
  const st = editingStates.value[idx]
  if (!st) return
  const original = docSlices.value[idx]
  const hasChange = original && st.draft !== original.page_content

  if (!hasChange) {
    const prev = st.prevExpanded
    const s = new Set(expandedSlices.value)
    if (prev) s.add(idx); else s.delete(idx)
    expandedSlices.value = s
    editingStates.value[idx] = { editing: false, draft: '' }
    NotificationService.info('无修改需要保存')
    return
  }

  if (!props.selectedKnowledgeBase) {
    NotificationService.warning('未选择知识库，无法保存')
    return
  }
  const kbName = props.selectedKnowledgeBase.name
  const fileName = props.viewingDocName
  if (!fileName) {
    NotificationService.warning('未选择文档，无法保存')
    return
  }

  const updatedDocs = docSlices.value.map((s, i) => ({
    page_content: i === idx ? st.draft : s.page_content,
    type: s.type,
    metadata: s.metadata
  }))
  const docsObject = { [fileName]: updatedDocs }

  const loadingKey = NotificationService.loading('正在保存切片...', 0)
  slicesSaving.value = true
  try {
    await updateKnowledgeBaseDocs({
      knowledge_base_name: kbName,
      file_names: [fileName],
      override_custom_docs: false,
      chunk_size: 750,
      chunk_overlap: 150,
      zh_title_enhance: false,
      docs: docsObject
    })
    NotificationService.close(loadingKey)
    docSlices.value[idx].page_content = st.draft
    const prev = st.prevExpanded
    const s = new Set(expandedSlices.value)
    if (prev) s.add(idx); else s.delete(idx)
    expandedSlices.value = s
    editingStates.value[idx] = { editing: false, draft: '' }
    NotificationService.success('切片已保存并同步至知识库')
  } catch (error: any) {
    NotificationService.close(loadingKey)
    console.error('保存切片失败:', error)
    const msg = typeof error?.message === 'string' ? error.message : '保存切片失败'
    NotificationService.error(msg)
  } finally {
    slicesSaving.value = false
  }
}

onMounted(() => {
  nextTick(() => {
    if (!slicesListRef.value) return
    slicesListRef.value.classList.add('hide-scrollbar')
    slicesListRef.value.addEventListener('scroll', showScrollbarDuringScroll)
  })
  document.addEventListener('pointerdown', onPointerDown as EventListener)
  document.addEventListener('pointerup', onPointerUp as EventListener)
  document.addEventListener('pointermove', onPointerMove as EventListener)
})

onUnmounted(() => {
  slicesListRef.value?.removeEventListener('scroll', showScrollbarDuringScroll)
  document.removeEventListener('pointerdown', onPointerDown as EventListener)
  document.removeEventListener('pointerup', onPointerUp as EventListener)
  document.removeEventListener('pointermove', onPointerMove as EventListener)
  if (scrollbarHideTimer) {
    clearTimeout(scrollbarHideTimer)
    scrollbarHideTimer = null
  }
})

const saveAllSlices = async () => {
  let updated = 0
  Object.entries(editingStates.value).forEach(([k, st]) => {
    const idx = Number(k)
    if (st.editing && st.draft !== (docSlices.value[idx]?.page_content || '')) {
      docSlices.value[idx].page_content = st.draft
      const prev = st.prevExpanded
      const s = new Set(expandedSlices.value)
      if (prev) s.add(idx); else s.delete(idx)
      expandedSlices.value = s
      editingStates.value[idx] = { editing: false, draft: '' }
      updated++
    }
  })

  if (updated === 0) {
    NotificationService.info('无可保存的修改')
    return
  }

  if (!props.selectedKnowledgeBase) {
    NotificationService.warning('未选择知识库，无法保存')
    return
  }
  const kbName = props.selectedKnowledgeBase.name
  const fileName = props.viewingDocName
  if (!fileName) {
    NotificationService.warning('未选择文档，无法保存')
    return
  }

  const updatedDocs = docSlices.value.map((s) => ({
    page_content: s.page_content,
    type: s.type,
    metadata: s.metadata
  }))
  const docsObject = { [fileName]: updatedDocs }

  const loadingKey = NotificationService.loading('正在保存文档切片...', 0)
  slicesSaving.value = true
  try {
    await updateKnowledgeBaseDocs({
      knowledge_base_name: kbName,
      file_names: [fileName],
      override_custom_docs: false,
      chunk_size: 750,
      chunk_overlap: 150,
      zh_title_enhance: false,
      docs: docsObject
    })
    NotificationService.close(loadingKey)
    NotificationService.success('文档更新已保存')

    try {
      slicesLoading.value = true
      const retrievalConfig = getCachedRetrievalConfig()
      docSlices.value = await searchKnowledgeBaseDocs({
        knowledge_base_name: kbName,
        file_name: fileName,
        top_k: retrievalConfig.top_k,
        score_threshold: retrievalConfig.score_threshold
      })
      editingStates.value = {}
      expandedSlices.value = new Set()
      sliceSearchKeyword.value = ''
    } catch (e) {
      console.warn('保存后刷新切片失败:', e)
    } finally {
      slicesLoading.value = false
    }
  } catch (error: any) {
    NotificationService.close(loadingKey)
    console.error('保存文档切片失败:', error)
    const msg = typeof error?.message === 'string' ? error.message : '保存文档切片失败'
    NotificationService.error(msg)
  } finally {
    slicesSaving.value = false
  }
}

const copySlice = async (idx: number) => {
  const text = docSlices.value[idx]?.page_content || ''
  const ok = await copyText(text)
  if (ok) {
    NotificationService.success('切片内容已复制到剪贴板')
  } else {
    NotificationService.error('复制失败，请重试')
  }
}

// 打开时加载切片
watch(
  () => ({ open: props.open, kbName: props.selectedKnowledgeBase?.name, file: props.viewingDocName }),
  async (state) => {
    if (state.open && state.kbName && state.file) {
      try {
        slicesLoading.value = true
        const retrievalConfig = getCachedRetrievalConfig()
        docSlices.value = await searchKnowledgeBaseDocs({
          knowledge_base_name: state.kbName,
          file_name: state.file,
          top_k: retrievalConfig.top_k,
          score_threshold: retrievalConfig.score_threshold
        })
        editingStates.value = {}
        expandedSlices.value = new Set()
        sliceSearchKeyword.value = ''
        await nextTick()
        recalcCollapsible()
      } catch (error: any) {
        console.error('加载文档切片失败:', error)
        NotificationService.error(typeof error?.message === 'string' ? error.message : '加载文档切片失败')
        docSlices.value = []
      } finally {
        slicesLoading.value = false
      }
    }
  },
  { immediate: true }
)
</script>

<style scoped>
.modal-title-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 90%;
}

.slices-modal {
  display: flex;
  flex-direction: column;
  gap: 10px;
  height: 75vh;
}

.slices-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  height: 100%;
}

.loading-text {
  font-size: 12px;
  color: #666;
}

.slices-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.custom-search-wrapper {
  display: flex;
  align-items: center;
  background-color: #f2f3f5;
  border-radius: 12px;
  padding: 6px 12px;
  border: 1px solid transparent;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  width: 220px;
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
  font-size: 13px;
  color: #333;
}

.custom-input::placeholder {
  color: #bfbfbf;
}

.doc-count {
  font-size: 12px;
  color: #555;
}

.unsaved-banner {
  background: #fffbe6;
  border: 1px solid #ffe58f;
  color: #ad6800;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
}

.slices-empty {
  text-align: center;
  color: #777;
  font-size: 12px;
  padding: 20px;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

.slices-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable;
  flex: 1;
  min-height: 0;
  scrollbar-width: thin;
  margin-right: -15px;
  padding-right: 5px;
}

.slices-list::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.slices-list::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.slices-list::-webkit-scrollbar-track {
  background-color: transparent;
}

.slices-list.hide-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.2s ease;
}

.slices-list.hide-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.15);
}

.slices-list.hide-scrollbar::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, 0.25);
}

.slices-list.hide-scrollbar {
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
}

.slices-list:not(.hide-scrollbar) {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
  transition: scrollbar-color 0.2s ease;
}

.slice-card {
  border: 1px solid #eee;
  border-radius: 14px;
  background: #fff;
  padding: 10px;
}

.slice-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.slice-header .title {
  font-size: 13px;
  font-weight: 500;
  color: #333;
}

.slice-header .actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.slice-header .actions .btn-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border: none;
  background: transparent;
  color: #6b7280;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.slice-header .actions .btn-text.small {
  font-size: 12px;
}

.slice-header .actions .btn-text:hover {
  background: #eef6ff;
  color: #1f2937;
}

.slice-header .actions .btn-text.danger {
  color: #ef4444;
}

.slice-header .actions .btn-text.danger:hover {
  background: #fee2e2;
  color: #b91c1c;
}

.slice-header .actions .btn-text:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.slice-header .actions .btn-text:disabled:hover {
  background: transparent;
  color: #9ca3af;
}

.slice-header .actions :deep(.anticon) {
  display: inline-flex;
  align-items: center;
}

.btn-text.small {
  border: none;
  background: transparent;
  color: #1677ff;
  cursor: pointer;
  font-size: 12px;
  padding: 0 6px;
}

.btn-text.small.danger {
  color: #ff4d4f;
}

.btn-text.small:disabled {
  color: #999;
  cursor: not-allowed;
}

.slice-meta {
  margin-top: 6px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  font-size: 12px;
  color: #666;
}

.slice-content {
  margin-top: 8px;
  max-height: 180px;
  overflow: hidden;
}

.slice-content.collapsible:not(.expanded) {
  position: relative;
}

.slice-content.collapsible:not(.expanded) .slice-text {
  -webkit-mask-image: linear-gradient(to bottom, rgba(0,0,0,1) 70%, rgba(0,0,0,0) 100%);
  mask-image: linear-gradient(to bottom, rgba(0,0,0,1) 70%, rgba(0,0,0,0) 100%);
}

.slice-content.collapsible:not(.expanded)::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 36px;
  background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(255,255,255,1));
  pointer-events: none;
}

.slice-content.collapsible {
  cursor: default;
}

.slice-content.expanded {
  max-height: none;
  overflow: visible;
}

.slice-text {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.5;
}

.slice-textarea {
  width: 100%;
}

.slices-footer {
  display: flex;
  justify-content: flex-end;
}
</style>

<style>
.slices-modal-wrapper .ant-modal-content {
  border-radius: 24px;
}
.slices-modal-wrapper .ant-modal-close {
  border-radius: 8px !important;
  width: 25px !important;
  height: 25px !important;
  top: 17px;
  inset-inline-end: 17px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.slices-modal-wrapper .ant-modal-close-x {
  font-size: 12px !important;
  width: 25px !important;
  height: 25px !important;
  line-height: 25px !important;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
