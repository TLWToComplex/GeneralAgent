<template>
  <section class="delivery-center delivery-center-workspace" :class="{ 'is-reading': selectedFile, 'is-turning': turn.active }" aria-label="交付中心">
    <div class="dc-workspace">
      <header class="dc-masthead">
        <div class="dc-heading">
          <span class="dc-mark" aria-hidden="true"><i></i><i></i><i></i></span>
          <div>
            <h1>交付中心</h1>
            <p>从一段对话，到一份作品。</p>
          </div>
        </div>
      </header>

      <div class="dc-layout">
        <div class="dc-catalog">
          <div class="dc-index-bar">
            <div ref="categoryList" class="dc-categories" role="group" aria-label="文件分类">
              <span class="dc-tab-slider" aria-hidden="true"></span>
              <button v-for="category in categories" :key="category.key"
                :class="{ active: typeFilter === category.key }" :aria-pressed="typeFilter === category.key"
                @click="typeFilter = category.key">{{ category.label }}<sup v-if="categoryCount(category.key)">{{
                  categoryCount(category.key) }}</sup></button>
            </div>
            <div class="dc-index-side">
              <span class="dc-collection-note" aria-live="polite">{{ loading ? '正在归集…' : `${files.length} 份文件，来自
                ${sessionCount} 段对话` }}</span>
              <a-pagination v-if="visibleSessions.length > pageSize" class="dc-index-pager" v-model:current="page"
                :total="visibleSessions.length" :page-size="pageSize" :show-size-changer="false" size="small" />
              <div class="dc-search-tools">
                <label class="dc-search">
                  <SearchOutlined /><input v-model="search" type="search" placeholder="寻找文件或对话" aria-label="搜索交付文件" />
                </label>
                <button class="dc-icon-button dc-refresh" :disabled="busy" aria-label="刷新交付文件" title="刷新"
                  @click="refresh">
                  <ReloadOutlined :spin="busy" />
                </button>
              </div>
            </div>
            <span v-if="refreshing" class="dc-refresh-progress" aria-hidden="true"></span>
          </div>

          <div ref="catalogScroll" class="dc-catalog-scroll" :class="{ 'is-refreshing': refreshing }">
            <div v-if="loading" class="dc-state" role="status">
              <LoadingOutlined spin />
              <h3>正在整理交付档案</h3>
              <p>文件与它的来处，一起留存。</p>
            </div>
            <div v-else-if="error" class="dc-state" role="alert">
              <ExclamationCircleOutlined />
              <h3>暂时无法获取文件</h3>
              <p>{{ error }}</p><button class="dc-button" @click="refresh">重新加载</button>
            </div>
            <div v-else-if="!visibleFiles.length" class="dc-state">
              <FolderOpenOutlined />
              <h3>{{ files.length ? '没有找到匹配的文件' : '为下一份作品，留个位置' }}</h3>
              <p>{{ files.length ? '试试其他关键词，或调整筛选条件。' : 'Agent 生成的文件会按对话归集在这里。' }}</p><button v-if="files.length"
                class="dc-button" @click="resetFilters">清除筛选</button>
            </div>
            <div v-else class="dc-archive">
              <article v-for="(session, index) in pagedSessions" :key="session.id" class="dc-dossier"
                :class="{ 'contains-selection': selectedFile?.sessionId === session.source.sessionId }">
                <header class="dc-dossier-heading">
                  <span class="dc-folio-number" aria-hidden="true">{{ String((page - 1) * pageSize + index +
                    1).padStart(2, '0') }}</span>
                  <div class="dc-dossier-meta">
                    <div class="dc-agent"><img :src="agentCloseIcon" alt="" class="dc-agent-icon" /><span
                        :title="session.source.agentName">{{ session.source.agentName }}</span></div>
                    <button class="dc-origin"
                      :title="`${session.source.conversationTitle}\n${session.source.sessionId}`"
                      @click="openConversation(session.source)"><span>{{ session.source.conversationTitle }}</span>
                      <ArrowUpRightOutlined />
                    </button>
                    <span class="dc-dossier-count">{{ session.files.length }} 份交付文件</span>
                  </div>
                </header>
                <div class="dc-documents">
                  <div v-for="file in session.files" :key="file.id" class="dc-document"
                    :class="[file.kind, { selected: selectedFile?.id === file.id }]">
                    <button :ref="el => setFileButton(file.id, el)" class="dc-document-open"
                      :aria-label="`预览 ${file.name}`" :aria-pressed="selectedFile?.id === file.id"
                      @click="openPreview(file)">
                      <span class="dc-document-top"><img class="dc-format" :src="fileTypeIcon(file)"
                          :alt="file.extension.toUpperCase() || 'FILE'"
                          :title="file.extension.toUpperCase() || 'FILE'" /></span>
                      <span class="dc-document-name" :title="file.name">{{ displayName(file) }}</span>
                      <span class="dc-document-bottom"><span>{{ categoryLabel(file.kind) }}</span><span
                          class="dc-open-hint">{{ selectedFile?.id === file.id ? '正在阅读' : '展开阅读' }}
                          <ArrowRightOutlined />
                        </span></span>
                    </button>
                    <button class="dc-document-download dc-icon-button" :disabled="downloading.has(file.id)"
                      :aria-label="`下载 ${file.name}`" :title="`下载 ${file.name}`" @click="download(file)">
                      <LoadingOutlined v-if="downloading.has(file.id)" spin />
                      <img v-else class="dc-download-icon" :src="downloadNavIcon" alt="" />
                    </button>
                  </div>
                </div>
              </article>
            </div>
          </div>
        </div>

        <section v-if="selectedFile" class="dc-reader" :class="{ 'is-fading': readerFading }" aria-label="文件阅读区" :aria-busy="previewLoading">
          <div class="dc-reader-tools">
            <button class="dc-back" @click="closePreview">
              <ArrowLeftOutlined /><span>返回交付中心</span>
            </button>
            <div class="dc-reader-actions">
              <button class="dc-button dc-download" @click="openConversation(selectedFile)">
                <CommentOutlined /><span>回到对话</span>
              </button>
              <button class="dc-button dc-download" :disabled="downloading.has(selectedFile.id)"
                @click="download(selectedFile)">
                <LoadingOutlined v-if="downloading.has(selectedFile.id)" spin />
                <DownloadOutlined v-else /><span>{{ downloading.has(selectedFile.id) ? '下载中' : '下载文档' }}</span>
              </button>
            </div>
          </div>
          <header class="dc-reader-heading">
            <h2 ref="readerTitle" tabindex="-1">{{ displayName(selectedFile) }}</h2>
            <p><span class="dc-reader-format" :class="selectedFile.kind">{{ selectedFile.extension.toUpperCase() ||
              'FILE' }}</span><span class="dc-meta-dot">·</span><span>{{ selectedFile.agentName }}</span><span
                class="dc-meta-dot">·</span><span :title="selectedFile.conversationTitle">{{
                  selectedFile.conversationTitle }}</span></p>
          </header>
          <div class="dc-reading-surface"
            :class="{ 'is-image': selectedFile.kind === 'image', 'is-text': isTextFile(selectedFile) && !isMarkdownFile(selectedFile) }">
            <div class="dc-reading-scroll">
              <div v-if="previewLoading" class="dc-state" role="status">
                <div class="dc-paper-loading" aria-hidden="true"><i></i><i></i><i></i></div>
                <p>正在展开文件…</p>
              </div>
              <div v-else-if="previewError" class="dc-state" role="alert">
                <ExclamationCircleOutlined />
                <h3>这份文件暂时无法展开</h3>
                <p>{{ previewError }}</p>
                <div class="dc-state-actions"><button class="dc-button"
                    @click="openPreview(selectedFile)">重试</button><button class="dc-button"
                    :disabled="downloading.has(selectedFile.id)" @click="download(selectedFile)">下载文件</button></div>
              </div>
              <DocxPreview v-else-if="selectedFile.extension === 'docx' && previewBuffer" :key="selectedFile.id"
                :content="previewBuffer" :artifact-id="selectedFile.id" />
              <!-- Excel / PPT 复用 Canvas 同款画布，组件内部自带加载与错误态。 -->
              <div v-else-if="isOfficeCanvasFile(selectedFile) && previewBuffer" class="dc-office-canvas">
                <ExcelCanvasFullUI v-if="isExcelFile(selectedFile)" :key="`excel-${selectedFile.id}`"
                  :source="previewBuffer" :title="selectedFile.name" />
                <PptCanvasFullUI v-else :key="`ppt-${selectedFile.id}`" :source="previewBuffer"
                  :title="selectedFile.name" />
              </div>
              <iframe v-else-if="selectedFile.extension === 'html' || selectedFile.extension === 'htm'"
                :srcdoc="previewText" sandbox="" referrerpolicy="no-referrer" title="HTML 文件预览"></iframe>
              <iframe v-else-if="selectedFile.extension === 'pdf' && previewUrl" :src="previewUrl"
                title="PDF 文件预览"></iframe>
              <img v-else-if="selectedFile.kind === 'image' && previewUrl" :src="previewUrl" :alt="selectedFile.name" />
              <div v-else-if="isMarkdownFile(selectedFile)" class="dc-markdown-content">
                <MarkdownRenderer :key="selectedFile.id" :content="previewText" role="assistant"
                  :disable-artifacts="true" />
              </div>
              <div v-else-if="isTextFile(selectedFile)" class="dc-text-content">
                <pre>{{ previewText }}</pre>
              </div>
              <div v-else class="dc-state">
                <component :is="fileIcon(selectedFile.kind)" />
                <h3>这份文件，适合在应用中打开</h3>
                <p>{{ selectedFile.extension.toUpperCase() }} 暂不支持在线阅读，下载后即可查看完整内容。</p><button class="dc-button"
                  :disabled="downloading.has(selectedFile.id)" @click="download(selectedFile)">
                  <DownloadOutlined /> 下载文件
                </button>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>

    <!-- 抽页过场：一张纸扫过整个视口，在完全遮住画面的中点切换布局，读者看不到排版跳变。
         传送到 body 是为了脱离工作区的层叠上下文与容器，让纸张真正铺满全屏；
         Teleport 仍留在根 section 内，避免父级 Transition 收到多根节点。 -->
    <Teleport to="body">
      <div v-if="turn.active" class="dc-page-turn" :class="{ 'is-back': turn.dir === -1 }" aria-hidden="true">
        <div class="dc-page-turn-sheet">
          <div class="dc-page-turn-label">
            <span class="dc-page-turn-format">{{ turn.format }}</span>
            <span class="dc-page-turn-name">{{ turn.name }}</span>
            <span class="dc-page-turn-note">{{ turn.note }}</span>
          </div>
        </div>
      </div>
    </Teleport>
  </section>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { FolderOpenOutlined, SearchOutlined, ReloadOutlined, LoadingOutlined, ExclamationCircleOutlined, FileOutlined, FileTextOutlined, FileExcelOutlined, FilePptOutlined, FileImageOutlined, CodeOutlined, CommentOutlined, ArrowUpOutlined as ArrowUpRightOutlined, ArrowRightOutlined, ArrowLeftOutlined, DownloadOutlined } from '@ant-design/icons-vue'
import { listChatRecordFiles, type ChatRecordFileGroup } from '@/services/aiChatRecord'
import { fetchDeliveryFile } from '@/services/deliveryFiles'
import { useWorkspaceStorage } from '@/composables/useWorkspaceStorage'
import DocxPreview from '@/components/chat/DocxPreview.vue'
import agentCloseIcon from '@/assets/image/svg/agent-close.svg'
import downloadNavIcon from '@/assets/image/svg/download-nav.svg'
// 与聊天里的 artifact 卡片共用同一套文件图标。
import WordSvg from '@/assets/image/svg/Word.svg'
import PdfSvg from '@/assets/image/svg/pdf-icon.svg'
import TxtSvg from '@/assets/image/svg/Txt.svg'
import MarkdownSvg from '@/assets/image/svg/Markdown.svg'
import ExcelSvg from '@/assets/image/svg/Excel.svg'
import PptSvg from '@/assets/image/svg/PPT.svg'
import JsonSvg from '@/assets/image/svg/json.svg'
import CodeSvg from '@/assets/image/svg/Code.svg'
import CadSvg from '@/assets/image/svg/CAD.svg'
import ZipSvg from '@/assets/image/svg/Zip.svg'
import ImageSvg from '@/assets/image/svg/image.svg'
// Markdown 排版与 Canvas 预览共用同一套全局样式。
import '@/assets/styles/markdown.css'

// 与 Canvas 使用同一渲染组件，保证 Markdown 效果一致；异步加载不影响交付中心首屏。
const MarkdownRenderer = defineAsyncComponent(() => import('@/components/common/MarkdownRenderer.vue'))
// Excel / PPT 同样复用 Canvas 的画布组件，异步加载避免首屏拖入 Luckysheet 等大体积依赖。
const ExcelCanvasFullUI = defineAsyncComponent(() => import('@/components/chat/ExcelCanvasFullUI.vue'))
const PptCanvasFullUI = defineAsyncComponent(() => import('@/components/chat/PptCanvasFullUI.vue'))

defineOptions({ name: 'DeliveryCenterView' })
const props = defineProps<{ conversations?: Array<{ sessionThreadId: string; title: string; chatType?: string; agentId?: string }> }>()
const emit = defineEmits<{ 'open-conversation': [record: { sessionThreadId: string; agentId: string; chatType?: string }] }>()
type Kind = 'document' | 'sheet' | 'slides' | 'image' | 'code' | 'other'
interface DeliveryFile { id: string; name: string; path: string; extension: string; kind: Kind; agentId: string; agentName: string; sessionId: string; conversationTitle: string; chatType?: string }
const groups = ref<ChatRecordFileGroup[]>([])
const loading = ref(true), error = ref(''), search = ref(''), typeFilter = ref('all'), page = ref(1)
// refreshing 表示已有列表在原位静默更新，避免整屏切换到加载占位造成闪烁。
const refreshing = ref(false)
const busy = computed(() => loading.value || refreshing.value)
const pageSize = 10
const categories = [{ key: 'all', label: '全部' }, { key: 'document', label: '文档' }, { key: 'sheet', label: '表格' }, { key: 'slides', label: '演示' }, { key: 'image', label: '图片' }, { key: 'code', label: '代码 / 网页' }, { key: 'other', label: '其他' }]
function fileKind(ext: string): Kind {
  if (['doc', 'docx', 'pdf', 'txt', 'md', 'markdown', 'rtf', 'odt'].includes(ext)) return 'document'
  if (['xlsx', 'xls', 'csv', 'tsv', 'ods'].includes(ext)) return 'sheet'
  if (['ppt', 'pptx', 'odp'].includes(ext)) return 'slides'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'avif'].includes(ext)) return 'image'
  if (['html', 'htm', 'js', 'ts', 'jsx', 'tsx', 'json', 'py', 'css', 'vue', 'xml', 'yaml', 'yml', 'sql', 'sh'].includes(ext)) return 'code'
  return 'other'
}
const files = computed<DeliveryFile[]>(() => {
  const seen = new Set<string>()
  const summaries = new Map((props.conversations || []).map(item => [item.sessionThreadId, item]))
  return groups.value.flatMap(group => (group.files || []).flatMap(file => {
    const id = JSON.stringify([group.agent_id, group.session_thread_id, file.path])
    if (seen.has(id)) return []
    seen.add(id)
    const extension = file.name.includes('.') ? file.name.split('.').pop()!.toLowerCase() : ''
    const summary = summaries.get(group.session_thread_id)
    return [{ ...file, id, extension, kind: fileKind(extension), agentId: group.agent_id, agentName: group.agent_name || '未命名 Agent', sessionId: group.session_thread_id, conversationTitle: summary?.title || `对话 ${group.session_thread_id.slice(0, 8)}`, chatType: summary?.chatType }]
  }))
})
const sessionCount = computed(() => new Set(files.value.map(file => file.sessionId)).size)
const searchedFiles = computed(() => files.value.filter(file => [file.name, file.agentName, file.conversationTitle, file.sessionId].join(' ').toLocaleLowerCase().includes(search.value.trim().toLocaleLowerCase())))
const visibleFiles = computed(() => searchedFiles.value.filter(file => typeFilter.value === 'all' || file.kind === typeFilter.value))
// 将同一 Agent、同一对话中的文件作为一份档案，分页不会拆散来源。
const visibleSessions = computed(() => {
  const sessions = new Map<string, { id: string; source: DeliveryFile; files: DeliveryFile[] }>()
  for (const file of visibleFiles.value) {
    const id = JSON.stringify([file.agentId, file.sessionId])
    const session = sessions.get(id)
    if (session) session.files.push(file)
    else sessions.set(id, { id, source: file, files: [file] })
  }
  return [...sessions.values()]
})
const pagedSessions = computed(() => visibleSessions.value.slice((page.value - 1) * pageSize, page.value * pageSize))
const fileStem = (name: string) => name.lastIndexOf('.') > 0 ? name.slice(0, name.lastIndexOf('.')) : name
// 代码 / 网页文件保留扩展名（如 index.html），其余文件仍只显示主干名。
const displayName = (file: DeliveryFile) => file.kind === 'code' ? file.name : fileStem(file.name)
const fileButtons = new Map<string, HTMLButtonElement>()
function setFileButton(id: string, element: unknown) {
  if (element instanceof HTMLButtonElement) fileButtons.set(id, element)
  else fileButtons.delete(id)
}
const readerTitle = ref<HTMLElement | null>(null)
const catalogScroll = ref<HTMLElement | null>(null)
let archiveScrollTop = 0
watch([search, typeFilter], () => { page.value = 1 })
watch(() => visibleSessions.value.length, count => { page.value = Math.max(1, Math.min(page.value, Math.ceil(count / pageSize))) })
const categoryCount = (kind: string) => searchedFiles.value.filter(file => kind === 'all' || file.kind === kind).length
// 页签滑块：测量激活项的位置与尺寸写入 CSS 变量，让高亮胶囊在页签间弹性滑动。
const categoryList = ref<HTMLElement | null>(null)
function updateTabSlider() {
  const list = categoryList.value
  if (!list) return
  const active = list.querySelector<HTMLButtonElement>('button.active')
  if (!active) return
  list.style.setProperty('--tab-x', `${active.offsetLeft}px`)
  list.style.setProperty('--tab-y', `${active.offsetTop}px`)
  list.style.setProperty('--tab-w', `${active.offsetWidth}px`)
  list.style.setProperty('--tab-h', `${active.offsetHeight}px`)
  list.classList.add('slider-ready')
}
let tabSliderObserver: ResizeObserver | null = null
// 计数上标随归集结果出现/消失、阅读态切换都会改变页签尺寸，用 ResizeObserver 跟随重测。
watch([typeFilter, () => searchedFiles.value.length], () => void nextTick(updateTabSlider))
onMounted(() => {
  updateTabSlider()
  if (categoryList.value) {
    tabSliderObserver = new ResizeObserver(updateTabSlider)
    tabSliderObserver.observe(categoryList.value)
  }
})
onUnmounted(() => { tabSliderObserver?.disconnect(); tabSliderObserver = null })
const categoryLabel = (kind: string) => categories.find(category => category.key === kind)?.label || '其他'
const fileIcon = (kind: Kind) => ({ document: FileTextOutlined, sheet: FileExcelOutlined, slides: FilePptOutlined, image: FileImageOutlined, code: CodeOutlined, other: FileOutlined })[kind]
// 扩展名 → artifact 卡片同款图标；查不到时退回该分类的通用图标。
const EXTENSION_ICONS: Record<string, string> = {
  pdf: PdfSvg,
  doc: WordSvg, docx: WordSvg, rtf: WordSvg, odt: WordSvg,
  txt: TxtSvg, md: MarkdownSvg, markdown: MarkdownSvg,
  xls: ExcelSvg, xlsx: ExcelSvg, csv: ExcelSvg, tsv: ExcelSvg, ods: ExcelSvg,
  ppt: PptSvg, pptx: PptSvg, odp: PptSvg,
  json: JsonSvg, dwg: CadSvg, dxf: CadSvg,
  zip: ZipSvg, rar: ZipSvg, '7z': ZipSvg, tar: ZipSvg, gz: ZipSvg,
  png: ImageSvg, jpg: ImageSvg, jpeg: ImageSvg, gif: ImageSvg, webp: ImageSvg, svg: ImageSvg, bmp: ImageSvg, avif: ImageSvg
}
const KIND_ICONS: Record<Kind, string> = { document: WordSvg, sheet: ExcelSvg, slides: PptSvg, image: ImageSvg, code: CodeSvg, other: TxtSvg }
const fileTypeIcon = (file: DeliveryFile) => EXTENSION_ICONS[file.extension] || KIND_ICONS[file.kind]
function resetFilters() { search.value = ''; typeFilter.value = 'all' }
async function refresh() {
  // 已有档案时保留列表原位更新；首次加载与失败重试才显示整屏占位。
  const silent = !error.value && groups.value.length > 0
  if (silent) refreshing.value = true
  else { loading.value = true; error.value = '' }
  try { groups.value = await listChatRecordFiles() }
  catch (err) {
    const text = err instanceof Error ? err.message : '请检查网络后重试'
    if (silent) message.error(text)
    else error.value = text
  }
  finally { loading.value = false; refreshing.value = false; restore() }
}
function openConversation(file: DeliveryFile) { emit('open-conversation', { sessionThreadId: file.sessionId, agentId: file.agentId, chatType: file.chatType }) }
const selectedFile = ref<DeliveryFile | null>(null), previewLoading = ref(false), previewError = ref(''), previewText = ref(''), previewUrl = ref(''), previewBuffer = ref<ArrayBuffer | null>(null)
// 记录当前预览文件的 id（按标签页存于 sessionStorage），刷新后据此恢复阅读态。
const persistedPreviewId = useWorkspaceStorage<string | null>('delivery-preview-file-id', null)
watch(selectedFile, file => { persistedPreviewId.value = file?.id ?? null })
let previewController: AbortController | null = null
const downloadControllers = new Set<AbortController>()
const downloading = ref(new Set<string>())
const isTextFile = (file: DeliveryFile) => ['txt', 'md', 'markdown', 'csv', 'tsv', 'js', 'ts', 'jsx', 'tsx', 'json', 'py', 'css', 'vue', 'xml', 'yaml', 'yml', 'sql', 'sh'].includes(file.extension)
const isMarkdownFile = (file: DeliveryFile) => ['md', 'markdown'].includes(file.extension)
// 与 Canvas 的 isExcelArtifact / isPptArtifact 判定范围保持一致。
const isExcelFile = (file: DeliveryFile) => ['xls', 'xlsx'].includes(file.extension)
const isPptFile = (file: DeliveryFile) => ['ppt', 'pptx'].includes(file.extension)
const isOfficeCanvasFile = (file: DeliveryFile) => isExcelFile(file) || isPptFile(file)
function clearPreview() {
  previewController?.abort()
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''; previewText.value = ''; previewBuffer.value = null; previewError.value = ''; previewLoading.value = false
}
/* 抽页过场：纸张扫过整个视口，中点（画面被完全遮住时）才切换布局与内容。 */
const TURN_MS = 880
const turn = ref({ active: false, dir: 1 as 1 | -1, format: '', name: '', note: '' })
let turnTimers: number[] = []
function clearTurnTimers() { turnTimers.forEach(timer => window.clearTimeout(timer)); turnTimers = [] }
function runTurn(dir: 1 | -1, label: { format: string; name: string; note: string }, swap: () => void) {
  clearTurnTimers()
  // 减少动效偏好下直接切换，不留空白等待。
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false) { swap(); return }
  turn.value = { active: true, dir, ...label }
  // 与 dc-page-turn 关键帧 39%~61% 的停留段对齐，此刻画面被纸完全遮住。
  turnTimers.push(window.setTimeout(swap, TURN_MS * 0.5))
  turnTimers.push(window.setTimeout(() => { turn.value.active = false }, TURN_MS + 60))
}
/* 阅读态内切换文档的渐隐渐显：透明度降为 0 后才换内容，读者看不到排版跳变。 */
// 比 .is-fading 的 .18s 渐隐过渡稍长，掉帧时也确保已完全透明再切换。
const READER_FADE_MS = 210
const readerFading = ref(false)
let readerFadeTimer = 0
function swapPreview(file: DeliveryFile) {
  clearPreview(); selectedFile.value = file
  void nextTick(() => {
    readerTitle.value?.focus({ preventScroll: true })
    fileButtons.get(file.id)?.scrollIntoView({ block: 'nearest' })
  })
  void loadPreview(file)
}
function closePreview() {
  if (turn.value.active || readerFading.value) return
  const id = selectedFile.value?.id
  runTurn(-1, { format: 'ARCHIVE', name: '交付中心', note: '正在归回档案' }, async () => {
    clearPreview()
    selectedFile.value = null
    await nextTick()
    if (catalogScroll.value) catalogScroll.value.scrollTop = archiveScrollTop
    if (id) fileButtons.get(id)?.focus({ preventScroll: true })
  })
}
function openPreview(file: DeliveryFile) {
  if (turn.value.active || readerFading.value) return
  if (!selectedFile.value) archiveScrollTop = catalogScroll.value?.scrollTop || 0
  // 已在阅读态时切换文档：不再播放抽页过场，只让阅读区渐隐、换内容后渐显。
  if (selectedFile.value) {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false) { swapPreview(file); return }
    readerFading.value = true
    readerFadeTimer = window.setTimeout(() => {
      swapPreview(file)
      // 等新内容渲染提交后再起一帧开始渐显，避免重挂载卡住动画的起始帧。
      void nextTick(() => requestAnimationFrame(() => { readerFading.value = false }))
    }, READER_FADE_MS)
    return
  }
  runTurn(1, { format: file.extension.toUpperCase() || 'FILE', name: displayName(file), note: '正在抽出文件' }, () => swapPreview(file))
}
async function loadPreview(file: DeliveryFile) {
  if (!(isTextFile(file) || file.kind === 'image' || isOfficeCanvasFile(file) || ['docx', 'pdf', 'html', 'htm'].includes(file.extension))) return
  const controller = new AbortController(); previewController = controller; previewLoading.value = true
  try {
    const blob = await fetchDeliveryFile(file.path, controller.signal)
    if (blob.size > 30 * 1024 * 1024) throw new Error('文件超过 30 MB，请下载后查看')
    const buffer = await blob.arrayBuffer()
    if (controller.signal.aborted) return
    if (file.extension === 'docx' || isOfficeCanvasFile(file)) previewBuffer.value = buffer
    else if (isTextFile(file) || ['html', 'htm'].includes(file.extension)) {
      const content = new TextDecoder().decode(buffer)
      // 禁止生成网页发起外部资源请求或运行脚本。
      previewText.value = ['html', 'htm'].includes(file.extension) ? `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; font-src data:">${content}` : content
    } else {
      const mime = file.extension === 'pdf' ? 'application/pdf' : ({ svg: 'image/svg+xml', jpg: 'image/jpeg' } as Record<string, string>)[file.extension] || `image/${file.extension}`
      previewUrl.value = URL.createObjectURL(new Blob([buffer], { type: mime }))
    }
  } catch (err) { if (!controller.signal.aborted) previewError.value = err instanceof Error ? err.message : '文件预览失败' }
  finally { if (!controller.signal.aborted) previewLoading.value = false }
}
async function download(file: DeliveryFile) {
  if (downloading.value.has(file.id)) return
  downloading.value.add(file.id)
  const controller = new AbortController(); downloadControllers.add(controller)
  try {
    const blob = await fetchDeliveryFile(file.path, controller.signal)
    const url = URL.createObjectURL(blob), anchor = document.createElement('a')
    anchor.href = url; anchor.download = file.name; document.body.appendChild(anchor); anchor.click(); anchor.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch (err) { if (!controller.signal.aborted) message.error(err instanceof Error ? err.message : '下载失败，请重试') }
  finally { downloading.value.delete(file.id); downloadControllers.delete(controller) }
}
function restore() {
  // 已在阅读、记录为空或列表加载失败时都不处理，保留记录待下次成功加载再恢复。
  if (selectedFile.value || error.value) return
  const id = persistedPreviewId.value
  if (!id) return
  const file = files.value.find(item => item.id === id)
  if (!file) {
    // 确有档案却找不到该文件（被删除或切换会话）才清除记录；空列表可能只是这次没取到。
    if (groups.value.length) persistedPreviewId.value = null
    return
  }
  clearPreview()
  selectedFile.value = file
  void loadPreview(file)
  void nextTick(() => readerTitle.value?.focus({ preventScroll: true }))
}

onMounted(refresh)
onUnmounted(() => { clearTurnTimers(); window.clearTimeout(readerFadeTimer); clearPreview(); downloadControllers.forEach(controller => controller.abort()) })
</script>
<style scoped>
@import '../assets/styles/delivery-center.css';
</style>
