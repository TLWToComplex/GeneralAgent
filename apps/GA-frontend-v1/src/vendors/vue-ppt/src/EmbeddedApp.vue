<template>
  <div class="pptist-embedded" :class="{ 'screening-mode': screening }">
    <Screen v-if="screening" />
    <Editor v-else />
    <FullscreenSpin :loading="loading" :tip="loadingTip" :mask="false" />
    <div v-if="error" class="embedded-error">{{ error }}</div>
  </div>
</template>

<script lang="ts" setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { nanoid } from 'nanoid'
import { saveAs } from 'file-saver'
import useImport from '@/hooks/useImport'
import useScreening from '@/hooks/useScreening'
import { db, deleteDiscardedDB } from '@/utils/database'
import { useMainStore, useScreenStore, useSlidesStore, useSnapshotStore } from '@/store'

import Editor from '@/views/Editor/index.vue'
import Screen from '@/views/Screen/index.vue'
import FullscreenSpin from '@/components/FullscreenSpin.vue'

const PPTX_MIME = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
const HOST_SOURCE = 'aisix-host'
const EMBED_SOURCE = 'pptist-embed'
const HOST_LOAD_EVENT = 'ppt-load'
const HOST_CLEAR_EVENT = 'ppt-clear'
const HOST_EXPORT_EVENT = 'ppt-export'
const HOST_SCREENING_EVENT = 'ppt-screening'
const EMBED_READY_EVENT = 'ppt-ready'
const EMBED_LOADED_EVENT = 'ppt-loaded'
const EMBED_ERROR_EVENT = 'ppt-error'

type HostMessagePayload = {
  source?: string
  type?: string
  fileName?: string
  title?: string
  arrayBuffer?: ArrayBuffer
}

const mainStore = useMainStore()
const slidesStore = useSlidesStore()
const snapshotStore = useSnapshotStore()
const screenStore = useScreenStore()
const { screening } = storeToRefs(screenStore)
const { importPPTXFile } = useImport()
const { enterScreening, enterScreeningFromStart } = useScreening()

const loading = ref(true)
const error = ref('')

const loadingTip = computed(() => (
  error.value ? '演示文稿加载失败' : '演示文稿加载中，请稍等 ...'
))

const createEmptySlide = () => ({
  id: nanoid(10),
  elements: [],
})

const normalizeTitle = (value?: string) => {
  if (!value) return '未命名演示文稿'
  const base = value.split('?')[0].split('#')[0]
  const segment = base.split('/').filter(Boolean).pop() || value
  return segment.replace(/\.pptx?$/i, '') || '未命名演示文稿'
}

const postToParent = (type: string, payload: Record<string, unknown> = {}) => {
  window.parent?.postMessage({
    source: EMBED_SOURCE,
    type,
    ...payload,
  }, '*')
}

// 容器原始文件字节，未编辑时导出直接复用，避免重导出造成的样式/体积差异
let originalBlob: Blob | null = null

const resetWorkspace = async (title?: string) => {
  originalBlob = null
  await db.snapshots.clear()
  await db.writingBoardImgs.clear()
  slidesStore.setSlides([createEmptySlide()])
  slidesStore.updateSlideIndex(0)
  slidesStore.setTitle(normalizeTitle(title))
  screenStore.setScreening(false)
  mainStore.setActiveElementIdList([])
  mainStore.setHandleElementId('')
  mainStore.setActiveGroupElementId('')
  mainStore.updateSelectedSlidesIndex([])
  await snapshotStore.initSnapshotDatabase()
}

const handleLoad = async ({ arrayBuffer, fileName, title }: HostMessagePayload) => {
  if (!arrayBuffer) {
    error.value = '未收到可加载的 PPT 内容'
    postToParent(EMBED_ERROR_EVENT, { message: error.value })
    return
  }

  loading.value = true
  error.value = ''

  await resetWorkspace(title || fileName)

  const file = new File(
    [arrayBuffer],
    fileName || `${normalizeTitle(title)}.pptx`,
    { type: PPTX_MIME },
  )

  const success = await importPPTXFile([file], { cover: true })
  loading.value = false

  if (!success) {
    error.value = '无法正确读取 / 解析该文件'
    postToParent(EMBED_ERROR_EVENT, { message: error.value })
    return
  }

  originalBlob = new Blob([arrayBuffer], { type: PPTX_MIME })

  slidesStore.setTitle(normalizeTitle(title || fileName))
  postToParent(EMBED_LOADED_EVENT, {
    title: slidesStore.title,
    slideCount: slidesStore.slides.length,
  })
}

// 导入完成后快照指针稳定在 1（0=空白初始快照，1=导入快照）；
// 任何用户编辑都会推高指针，撤销回原状则回到 1
const isEdited = () => snapshotStore.snapshotCursor > 1

const handleExport = () => {
  if (!isEdited() && originalBlob) {
    saveAs(originalBlob, `${slidesStore.title}.pptx`)
    return
  }
  mainStore.setDialogForExport('pptx')
}

const handleMessage = async (event: MessageEvent<HostMessagePayload>) => {
  const payload = event.data
  if (!payload || payload.source !== HOST_SOURCE) return

  console.log('[PptEmbed] received message:', payload.type)

  if (payload.type === HOST_CLEAR_EVENT) {
    error.value = ''
    loading.value = false
    await resetWorkspace(payload.title)
    return
  }

  if (payload.type === HOST_LOAD_EVENT) {
    await handleLoad(payload)
  }

  if (payload.type === HOST_EXPORT_EVENT) {
    console.log('[PptEmbed] HOST_EXPORT_EVENT received, calling handleExport')
    handleExport()
  }

  if (payload.type === HOST_SCREENING_EVENT) {
    const fromStart = (payload as any).fromStart
    if (fromStart) {
      enterScreeningFromStart()
    } else {
      enterScreening()
    }
  }
}

onMounted(async () => {
  await deleteDiscardedDB()
  await resetWorkspace()
  loading.value = false
  window.addEventListener('message', handleMessage)
  postToParent(EMBED_READY_EVENT)
})

onUnmounted(() => {
  window.removeEventListener('message', handleMessage)
})
</script>

<style lang="scss" scoped>
.pptist-embedded {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  background: #f3f4f6;

  &.screening-mode {
    margin-top: 5px;
  }
}

.embedded-error {
  position: absolute;
  right: 16px;
  bottom: 16px;
  max-width: min(360px, calc(100% - 32px));
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  background: rgba(255, 255, 255, 0.96);
  color: #b91c1c;
  font-size: 13px;
  line-height: 1.5;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.08);
  z-index: 30;
}
</style>
