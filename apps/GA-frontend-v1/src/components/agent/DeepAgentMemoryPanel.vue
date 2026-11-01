<template>
  <div class="deepagent-memory-panel">
    <div class="agent-model-section-header">
      <h3>记忆</h3>
      <p>管理历史对话中的上下文记忆</p>
    </div>

    <div class="memory-card deepagent-memory-switch-card">
      <div class="memory-card-content">
        <div class="memory-card-header">
          <span class="memory-card-title">开启记忆</span>
        </div>
        <div class="memory-card-desc">
          允许GeneralAgent记住你历史对话中的相关上下文
        </div>
      </div>
      <a-switch :checked="enabled" class="memory-switch" @change="handleEnabledChange" />
    </div>

    <div v-if="!enabled" class="deepagent-memory-empty">
      <div class="deepagent-memory-empty-title">记忆未开启</div>
      <div class="deepagent-memory-empty-desc">开启并保存智能体后，后端会创建默认记忆文件</div>
    </div>

    <div v-else-if="!agentUuid" class="deepagent-memory-empty">
      <div class="deepagent-memory-empty-title">记忆文件</div>
      <div class="deepagent-memory-empty-desc">开启记忆并创建 DeepAgent 后，可查看和编辑记忆文件</div>
    </div>

    <div v-else class="deepagent-memory-manager">
      <div class="deepagent-memory-toolbar">
        <div class="deepagent-memory-toolbar-title">
          <span>记忆文件</span>
          <span>{{ files.length }} 个文件</span>
        </div>
        <div class="deepagent-memory-toolbar-actions">
          <a-tooltip title="刷新记忆">
            <a-button class="deepagent-memory-icon-btn" type="text" shape="circle" :loading="loading" @click="loadMemoryFiles">
              <template #icon><ReloadOutlined /></template>
            </a-button>
          </a-tooltip>
          <a-tooltip title="下载记忆">
            <a-button class="deepagent-memory-icon-btn" type="text" shape="circle" :loading="downloading" @click="handleDownload">
              <template #icon><DownloadOutlined /></template>
            </a-button>
          </a-tooltip>
          <a-dropdown :trigger="['click']">
            <a-button class="deepagent-memory-icon-btn" type="text" shape="circle">
              <template #icon><MoreOutlined /></template>
            </a-button>
            <template #overlay>
              <a-menu class="deepagent-memory-action-menu">
                <a-menu-item key="reset" danger :disabled="resetting" @click="handleReset">
                  <RollbackOutlined />
                  重置记忆
                </a-menu-item>
              </a-menu>
            </template>
          </a-dropdown>
        </div>
      </div>

      <a-spin :spinning="loading">
        <div class="deepagent-memory-workspace">
          <div class="deepagent-memory-file-list">
            <button
              v-for="file in files"
              :key="file.name"
              type="button"
              :class="['deepagent-memory-file', { active: selectedFileName === file.name }]"
              @click="selectFile(file.name)"
            >
              <span class="deepagent-memory-file-name">{{ file.name }}</span>
              <span class="deepagent-memory-file-meta">{{ formatFileMeta(file) }}</span>
            </button>
          </div>

          <div class="deepagent-memory-editor">
            <div class="deepagent-memory-editor-header">
              <div>
                <div class="deepagent-memory-current">{{ selectedFileName || '记忆文件' }}</div>
                <div class="deepagent-memory-path" :title="selectedFile?.sandboxPath || selectedFile?.containerPath">
                  {{ selectedFile?.sandboxPath || selectedFile?.containerPath || '暂无路径' }}
                </div>
              </div>
              <a-button
                class="deepagent-memory-save-btn"
                type="primary"
                size="small"
                :disabled="!selectedFileName || !dirty"
                :loading="saving"
                @click="handleSave"
              >
                <img src="@/assets/icons/save-icon.svg" class="deepagent-memory-save-icon" alt="保存" />
                <span>保存</span>
              </a-button>
            </div>

            <a-textarea
              v-model:value="draftContent"
              class="deepagent-memory-textarea"
              :auto-size="false"
              :disabled="!selectedFileName"
              placeholder="选择一个记忆文件后编辑内容"
            />
          </div>
        </div>
      </a-spin>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Modal } from 'ant-design-vue'
import {
  DownloadOutlined,
  MoreOutlined,
  ReloadOutlined,
  RollbackOutlined
} from '@ant-design/icons-vue'
import NotificationService from '@/utils/NotificationService'
import {
  downloadAiMemory,
  getAiMemory,
  listAiMemory,
  resetAiMemory,
  updateAiMemory,
  type AiMemoryFile
} from '@/services/aiMemory'

const props = defineProps<{
  enabled: boolean
  agentUuid?: string
}>()

const emit = defineEmits<{
  (e: 'update:enabled', value: boolean): void
}>()

const files = ref<AiMemoryFile[]>([])
const selectedFileName = ref('')
const draftContent = ref('')
const loading = ref(false)
const saving = ref(false)
const resetting = ref(false)
const downloading = ref(false)

const selectedFile = computed(() => files.value.find(file => file.name === selectedFileName.value))
const dirty = computed(() => draftContent.value !== (selectedFile.value?.content || ''))

const handleEnabledChange = (checked: boolean | string | number) => {
  emit('update:enabled', Boolean(checked))
}

const normalizeFiles = (value: unknown): AiMemoryFile[] => {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is AiMemoryFile => !!item && typeof item === 'object' && typeof (item as AiMemoryFile).name === 'string')
    .map((item) => ({
      ...item,
      content: typeof item.content === 'string' ? item.content : ''
    }))
}

const resolveMemoryContent = (payload: any): string | null => {
  if (typeof payload?.data?.content === 'string') return payload.data.content
  if (typeof payload?.data?.memory === 'string') return payload.data.memory
  if (typeof payload?.content === 'string') return payload.content
  if (typeof payload?.memory === 'string') return payload.memory
  return null
}

const loadMemoryFiles = async () => {
  if (!props.enabled || !props.agentUuid) return
  loading.value = true
  try {
    const response = await listAiMemory(props.agentUuid)
    const nextFiles = normalizeFiles(response?.data?.files)
    files.value = nextFiles
    if (!nextFiles.some(file => file.name === selectedFileName.value)) {
      selectedFileName.value = nextFiles[0]?.name || ''
    }
    draftContent.value = selectedFile.value?.content || ''
  } catch (error) {
    files.value = []
    selectedFileName.value = ''
    draftContent.value = ''
    console.error('Failed to load DeepAgent memory files:', error)
  } finally {
    loading.value = false
  }
}

const selectFile = async (fileName: string) => {
  if (selectedFileName.value === fileName) return
  selectedFileName.value = fileName
  draftContent.value = selectedFile.value?.content || ''

  if (!props.agentUuid) return
  try {
    const response = await getAiMemory(props.agentUuid, fileName)
    const content = resolveMemoryContent(response)
    if (content !== null) {
      const index = files.value.findIndex(file => file.name === fileName)
      if (index > -1) {
        files.value.splice(index, 1, { ...files.value[index], content })
      }
      draftContent.value = content
    }
  } catch (error) {
    console.error('Failed to load DeepAgent memory file:', error)
  }
}

const handleSave = async () => {
  if (!props.agentUuid || !selectedFileName.value) return
  saving.value = true
  try {
    await updateAiMemory({
      agent_uuid: props.agentUuid,
      file_name: selectedFileName.value,
      content: draftContent.value
    })
    const index = files.value.findIndex(file => file.name === selectedFileName.value)
    if (index > -1) {
      files.value.splice(index, 1, { ...files.value[index], content: draftContent.value })
    }
    NotificationService.success('记忆内容已保存')
  } finally {
    saving.value = false
  }
}

const handleReset = () => {
  if (!props.agentUuid) return
  Modal.confirm({
    title: '重置记忆',
    content: '确定要恢复 DeepAgent 的初始记忆内容吗？当前修改会被覆盖。',
    okText: '重置',
    cancelText: '取消',
    okButtonProps: { danger: true },
    centered: true,
    async onOk() {
      resetting.value = true
      try {
        await resetAiMemory(props.agentUuid!)
        await loadMemoryFiles()
        NotificationService.success('记忆已重置')
      } finally {
        resetting.value = false
      }
    }
  })
}

const handleDownload = async () => {
  if (!props.agentUuid) return
  downloading.value = true
  try {
    const { blob, filename } = await downloadAiMemory(props.agentUuid)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
  } finally {
    downloading.value = false
  }
}

const formatFileMeta = (file: AiMemoryFile) => {
  const size = typeof file.size === 'number' ? `${file.size} B` : `${file.content.length} 字符`
  if (!file.updatedAt) return size
  return `${size} · ${file.updatedAt.replace('T', ' ').slice(0, 16)}`
}

watch(
  () => [props.enabled, props.agentUuid],
  () => {
    if (props.enabled && props.agentUuid) {
      void loadMemoryFiles()
    } else {
      files.value = []
      selectedFileName.value = ''
      draftContent.value = ''
    }
  },
  { immediate: true }
)

onMounted(() => {
  if (props.enabled && props.agentUuid && files.value.length === 0) {
    void loadMemoryFiles()
  }
})
</script>
