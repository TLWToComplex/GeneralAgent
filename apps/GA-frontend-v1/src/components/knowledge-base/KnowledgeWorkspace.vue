<template>
  <section class="kb-workspace" aria-label="知识库工作区">
    <div class="kw-body">
      <!-- 刷新后要恢复上次停留的文档目录：列表数据回来之前只渲染占位骨架，
           避免先闪一下知识库书架、再自动跳进文档目录 -->
      <div v-if="restoringDetail" class="kw-reading" aria-busy="true" aria-label="正在打开上次的知识库">
        <nav class="kw-reading-nav" aria-hidden="true">
          <span class="kw-restoring-hint">正在打开上次的知识库…</span>
        </nav>
        <div class="kw-reading-layout">
          <aside class="kw-bookmark" aria-hidden="true">
            <div class="kw-bookmark-symbol"><KnowledgeFormatSymbol /></div>
            <div class="kw-skeleton"><span></span><span></span><span></span></div>
          </aside>
          <div class="kw-reading-sheet">
            <div class="kw-shelf">
              <div v-for="item in 3" :key="item" class="kw-skeleton"><span></span><span></span><span></span></div>
            </div>
          </div>
        </div>
      </div>
      <Transition v-else :css="false" @enter="enterWorkspace" @leave="leaveWorkspace" @enter-cancelled="cancelMotion"
        @leave-cancelled="cancelMotion">
        <div v-if="!detailOpen || !displayedKnowledgeBase" key="library" class="kw-library" :inert="isTransitioning">
          <header class="kw-intro">
            <h1>知识，触手可及</h1>
            <p>收藏一份资料，为下一次对话积累答案。</p>
          </header>

          <div class="kw-search-dock">
            <label class="kw-search-field">
              <SearchOutlined />
              <input v-model="search" type="search" placeholder="寻找你的知识库…" aria-label="搜索知识库" />
            </label>
            <div class="kw-dock-bottom">
              <div ref="scopeEl" class="kw-scope" role="group" aria-label="知识库分类">
                <span ref="scopeIndicator" class="kw-scope-indicator" aria-hidden="true"></span>
                <button type="button" :class="{ active: permissionFilter === 'public' }"
                  :aria-pressed="permissionFilter === 'public'" @click="emit('update:permissionFilter', 'public')">
                  <TeamOutlined /> 团队共享
                </button>
                <button type="button" :class="{ active: permissionFilter === 'private' }"
                  :aria-pressed="permissionFilter === 'private'" @click="emit('update:permissionFilter', 'private')">
                  <UserOutlined /> 个人知识
                </button>
              </div>
              <span class="kw-dock-count" aria-live="polite">{{ loading ? '正在整理资料…' : error ? '暂时无法连接' :
                `${knowledgeBases.length} 个知识库 · ${documentCount} 篇文档` }}</span>
            </div>
          </div>

          <div class="kw-shelf-toolbar">
            <div class="kw-shelf-heading"><span class="kw-shelf-title">{{ search.trim() ? '找到的知识库' : permissionFilter === 'public' ? '与团队一起积累'
              : '留给自己的知识空间' }}</span><span v-if="!loading && !error" class="kw-result-count">{{
                visibleKnowledgeBases.length }}</span></div>
            <div class="kw-shelf-actions">
              <a-dropdown :trigger="['click']" placement="bottomLeft" overlayClassName="kw-sort-dropdown">
                <button type="button" class="kw-sort-trigger" :aria-label="`知识库排序：${sortLabel}`" aria-haspopup="menu">
                  <span>{{ sortLabel }}</span>
                  <DownOutlined class="kw-sort-caret" />
                </button>
                <template #overlay>
                  <a-menu class="kw-sort-menu" :selectedKeys="[sortBy]" @click="onSortSelect">
                    <a-menu-item key="date">最近创建</a-menu-item>
                    <a-menu-item key="name">按名称</a-menu-item>
                    <a-menu-item key="documents">文档最多</a-menu-item>
                  </a-menu>
                </template>
              </a-dropdown>
              <button type="button" class="kw-icon-button" title="刷新知识库" aria-label="刷新知识库" :disabled="loading || refreshing"
                @click="emit('refresh')">
                <ReloadOutlined :spin="loading || refreshing" />
              </button>
              <button v-if="isAdmin" type="button" class="kw-icon-button" title="检索配置" aria-label="检索配置"
                @click="emit('config')">
                <SettingOutlined />
              </button>
              <button type="button" class="kw-create-button" @click="emit('create')">
                <PlusOutlined /> 新建知识库
              </button>
            </div>
          </div>

          <div ref="scrollContainer" class="kw-library-scroll" :class="{ 'hide-scrollbar': listHideScrollbar }"
            role="region" aria-label="知识库列表" tabindex="0" @scroll.passive="showListScrollbarDuringScroll"
            @pointermove="onListPointerMove" @pointerleave="onListPointerLeave">
            <!-- 溶解期（!loading && skeletonLeaving）骨架不占位地叠在内容之上原地渐隐 -->
            <div v-if="loading || skeletonLeaving" class="kw-shelf" :class="{ 'kw-shelf-ghost': !loading }"
              :aria-busy="loading || undefined" :aria-label="loading ? '正在加载知识库' : undefined"
              :aria-hidden="loading ? undefined : 'true'">
              <div v-for="item in 3" :key="item" class="kw-skeleton"><span></span><span></span><span></span></div>
            </div>
            <template v-if="!loading">
            <div v-if="error" class="kw-empty" role="alert">
              <ExclamationCircleOutlined class="kw-empty-icon" />
              <h2>暂时无法打开知识库</h2>
              <p>{{ error }}</p><button type="button" class="kw-create-button" @click="emit('refresh')">
                <ReloadOutlined /> 重新加载
              </button>
            </div>
            <div v-else-if="visibleKnowledgeBases.length === 0" class="kw-empty">
              <SearchOutlined v-if="search.trim()" class="kw-empty-icon" />
              <div v-else class="kw-empty-symbol-hero" aria-hidden="true">
                <KnowledgeFormatSymbol :formats="[]" />
              </div>
              <h2>{{ search.trim() ? '还没有找到这份知识' : permissionFilter === 'private' ? '你的知识，从这里开始' : '等待团队的第一份知识' }}</h2>
              <p>{{ search.trim() ? '试试名称中的其他关键词，或清空搜索。' : '创建知识库，把零散的资料收进同一个地方。' }}</p>
              <button v-if="search.trim()" type="button" class="kw-create-button" @click="search = ''">清空搜索</button>
              <button v-else type="button" class="kw-create-button" @click="emit('create')">
                <PlusOutlined /> 新建知识库
              </button>
            </div>
            <div v-else class="kw-shelf">
              <article v-for="(kb, index) in visibleKnowledgeBases" :key="kb.id" :data-kb-id="kb.id" class="kw-folio" :class="{ 'has-documents': kb.documentCount > 0 }">
                <span class="kw-folio-tab" aria-hidden="true">{{ String(index + 1).padStart(2, '0') }}</span>
                <span v-if="kb.documentCount > 0" class="kw-folder-sheets" aria-hidden="true">
                  <span v-for="format in folioFormats(kb).slice(0, 3)" :key="format.label" class="kw-format-page" :class="`is-${format.kind}`" aria-hidden="true">
                    <span class="kw-format-label">{{ format.label }}</span>
                    <span class="kw-format-lines"></span>
                  </span>
                </span>
                <div class="kw-folio-cover">
                  <div class="kw-folio-top">
                    <KnowledgeFormatSymbol class="kw-folio-symbol" :loading="formatsLoading(kb)" :formats="kb.documentCount > 0 ? folioFormats(kb) : []" />
                    <span class="kw-visibility">
                      <TeamOutlined v-if="kb.permissionCode === 'public'" />
                      <LockOutlined v-else />{{ kb.permissionCode === 'public' ? '共享' : '个人' }}
                    </span>
                    <a-dropdown :trigger="['click']" placement="bottomRight">
                      <button type="button" class="kw-icon-button kw-more" :aria-label="`${kb.name}的更多操作`">
                        <MoreOutlined />
                      </button>
                      <template #overlay><a-menu><a-menu-item :disabled="!canManage(kb)" @click="emit('edit', kb)">
                            <EditOutlined /> 编辑知识库
                          </a-menu-item><a-menu-item danger :disabled="!canManage(kb)" @click="emit('delete', kb)">
                            <DeleteOutlined /> 删除知识库
                          </a-menu-item></a-menu></template>
                    </a-dropdown>
                  </div>
                  <button type="button" class="kw-folio-open" :aria-label="`打开知识库：${kb.name}`"
                    @click="openKnowledgeBase(kb, $event)">
                    <h2 :title="kb.name">{{ kb.name }}</h2>
                    <p>{{ kb.description || '还没有添加简介，打开看看这里收录的文档。' }}</p>
                  </button>
                  <div class="kw-folio-bottom">
                    <span><strong>{{ kb.documentCount || 0 }}</strong> 篇文档</span>
                    <button v-if="kb.includeKg" type="button" class="kw-graph-chip"
                      :disabled="activeKgTaskKbNames?.has(kb.name)"
                      :title="activeKgTaskKbNames?.has(kb.name) ? '图谱正在处理中' : '查看知识图谱'" @click="emit('graph', kb)">
                      <DeploymentUnitOutlined /><span>{{ activeKgTaskKbNames?.has(kb.name) ? '整理中' : '知识图谱' }}</span>
                    </button>
                    <ArrowUpOutlined class="kw-open-arrow" aria-hidden="true" />
                  </div>
                </div>
              </article>
              <button v-if="!search.trim()" type="button" class="kw-new-folio" @click="emit('create')"><span
                  class="kw-new-icon">
                  <PlusOutlined />
                </span><strong>留一处，给新的知识</strong><span>新建知识库</span></button>
            </div>
            </template>
          </div>
          <p class="kw-library-note">资料在这里沉淀，灵感在对话中发生。</p>
        </div>

        <div v-else ref="readingView" key="reading" class="kw-reading"
          :inert="isTransitioning">
          <nav class="kw-reading-nav" aria-label="知识库导航"><button type="button" @click="closeKnowledgeBase">
              <ArrowLeftOutlined /> 返回知识空间
            </button></nav>
          <div class="kw-reading-layout">
            <aside class="kw-bookmark" aria-label="当前知识库信息">
              <div class="kw-bookmark-symbol"><KnowledgeFormatSymbol :loading="formatsLoading(displayedKnowledgeBase)" :formats="displayedKnowledgeBase.documentCount > 0 ? folioFormats(displayedKnowledgeBase) : []" /></div>
              <h1>{{ displayedKnowledgeBase.name }}</h1>
              <p>{{ displayedKnowledgeBase.description || '把有价值的资料留在这里，随时取用。' }}</p>
              <div class="kw-bookmark-count"><strong>{{ displayedKnowledgeBase.documentCount || 0
                  }}</strong><span>篇文档已收录</span>
              </div>
              <div class="kw-bookmark-info"><span>
                  <TeamOutlined v-if="displayedKnowledgeBase.permissionCode === 'public'" />
                  <LockOutlined v-else />{{ displayedKnowledgeBase.permissionCode === 'public' ? '团队共享' : '个人知识库' }}
                </span><span>{{ shortDate(displayedKnowledgeBase.updatedAt) }} 创建</span></div>
              <div class="kw-bookmark-actions">
                <button v-if="canManage(displayedKnowledgeBase)" type="button"
                  @click="emit('edit', displayedKnowledgeBase)">
                  <EditOutlined /> 编辑信息
                </button>
                <button v-if="displayedKnowledgeBase.includeKg" type="button"
                  :disabled="activeKgTaskKbNames?.has(displayedKnowledgeBase.name)"
                  @click="emit('graph', displayedKnowledgeBase)">
                  <DeploymentUnitOutlined /> {{ activeKgTaskKbNames?.has(displayedKnowledgeBase.name) ? '图谱整理中' :
                  '探索知识图谱' }}
                </button>
                <button type="button" :disabled="loading || refreshing" @click="emit('refresh')">
                  <ReloadOutlined :spin="loading || refreshing" /> 刷新文档
                </button>
              </div>
            </aside>
            <div class="kw-reading-sheet">
              <div v-if="error" class="kw-detail-error" role="alert">{{ error }}<button type="button"
                  @click="emit('refresh')">重试</button></div>
              <slot :knowledge-base="displayedKnowledgeBase" :loading="displayedDocsLoading" :error="displayedDocsError" />
            </div>
          </div>
        </div>
      </Transition>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ArrowLeftOutlined, ArrowUpOutlined, DeleteOutlined, DeploymentUnitOutlined, DownOutlined, EditOutlined, ExclamationCircleOutlined, LockOutlined, MoreOutlined, PlusOutlined, ReloadOutlined, SearchOutlined, SettingOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons-vue'
import { type KnowledgeBaseVM, type KnowledgeBasePermissionCode } from '@/services/knowledgeBase'
import { canManageKnowledgeBase } from '@/composables/useKnowledgeBaseAccess'
import { parseDate, toTimestamp } from '@/utils/formatters'
import KnowledgeFormatSymbol from './KnowledgeFormatSymbol.vue'
import { loadKbDocs } from '@/composables/useKnowledgeBaseCache'

const props = defineProps<{
  knowledgeBases: KnowledgeBaseVM[]
  selectedKnowledgeBase: KnowledgeBaseVM | null
  loading: boolean
  // 已有缓存、正在后台静默刷新：保留现有卡片，仅用顶部进度条提示
  refreshing?: boolean
  docsLoading?: boolean
  docsError?: string
  error: string
  searchKeyword: string
  permissionFilter: KnowledgeBasePermissionCode
  isAdmin: boolean
  activeKgTaskKbNames?: Set<string>
}>()
const emit = defineEmits<{
  back: []
  close: []
  create: []
  refresh: []
  config: []
  select: [kb: KnowledgeBaseVM]
  edit: [kb: KnowledgeBaseVM]
  delete: [kb: KnowledgeBaseVM]
  graph: [kb: KnowledgeBaseVM]
  'update:searchKeyword': [value: string]
  'update:permissionFilter': [value: KnowledgeBasePermissionCode]
}>()

// 是否停留在某个知识库的文档目录：持久化到 localStorage，刷新后回到离开前的位置
const DETAIL_OPEN_STORAGE_KEY = 'kb-workspace-detail-open'
const readStoredDetailOpen = (): boolean => {
  try {
    return localStorage.getItem(DETAIL_OPEN_STORAGE_KEY) === 'true'
  } catch {
    return false
  }
}
const persistDetailOpen = (open: boolean) => {
  try {
    localStorage.setItem(DETAIL_OPEN_STORAGE_KEY, String(open))
  } catch { /* localStorage 不可用时忽略 */ }
}
const detailOpen = ref(readStoredDetailOpen())
// 刷新恢复中：离开前停在文档目录时，列表数据回来之前只渲染占位骨架（见模板 restoringDetail 分支）
const restoringDetail = ref(detailOpen.value)
const sortBy = ref('date')
const sortOptions = [
  { value: 'date', label: '最近创建' },
  { value: 'name', label: '按名称' },
  { value: 'documents', label: '文档最多' },
] as const
const sortLabel = computed(() => sortOptions.find(option => option.value === sortBy.value)?.label ?? '最近创建')
const onSortSelect = ({ key }: { key: string | number }) => {
  sortBy.value = String(key)
}
const scopeEl = ref<HTMLElement | null>(null)
const scopeIndicator = ref<HTMLElement | null>(null)
const syncScopeIndicator = (animate: boolean) => {
  const scope = scopeEl.value
  const indicator = scopeIndicator.value
  if (!scope || !indicator) return
  const active = scope.querySelector<HTMLElement>('button.active')
  if (!active) return
  const place = () => {
    indicator.style.transform = `translateX(${active.offsetLeft}px)`
    indicator.style.width = `${active.offsetWidth}px`
    indicator.style.top = `${active.offsetTop}px`
    indicator.style.height = `${active.offsetHeight}px`
  }
  if (!animate || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    indicator.style.setProperty('transition', 'none', 'important')
    place()
    return
  }
  // 带 !important 是为了抵消上方 .kb-workspace :deep(*) 的 transition: none !important
  indicator.style.setProperty('transition', 'transform .45s cubic-bezier(.34,1.3,.64,1), width .45s cubic-bezier(.34,1.3,.64,1)', 'important')
  place()
}
onMounted(() => syncScopeIndicator(false))
watch(() => props.permissionFilter, () => syncScopeIndicator(true), { flush: 'post' })
const scrollContainer = ref<HTMLElement | null>(null)
const readingView = ref<HTMLElement | null>(null)
const isTransitioning = ref(false)
// 滚动条默认隐藏，滚动时短暂显示（与 chat-history 的逻辑一致）
const listHideScrollbar = ref(true)
const hoveringListScrollbar = ref(false)
let listScrollbarHideTimer: number | null = null
const showListScrollbarDuringScroll = () => {
  listHideScrollbar.value = false
  if (listScrollbarHideTimer) {
    clearTimeout(listScrollbarHideTimer)
    listScrollbarHideTimer = null
  }
  if (hoveringListScrollbar.value) return
  listScrollbarHideTimer = window.setTimeout(() => {
    listHideScrollbar.value = true
    listScrollbarHideTimer = null
  }, 600)
}
const isPointerInListGutter = (event: PointerEvent) => {
  const el = scrollContainer.value
  if (!el) return false
  const rect = el.getBoundingClientRect()
  return event.clientY >= rect.top && event.clientY <= rect.bottom
    && event.clientX >= rect.right - 20 && event.clientX <= rect.right
}
const onListPointerMove = (event: PointerEvent) => {
  const inGutter = isPointerInListGutter(event)
  if (inGutter === hoveringListScrollbar.value) return
  hoveringListScrollbar.value = inGutter
  if (inGutter) {
    listHideScrollbar.value = false
    if (listScrollbarHideTimer) {
      clearTimeout(listScrollbarHideTimer)
      listScrollbarHideTimer = null
    }
  } else {
    showListScrollbarDuringScroll()
  }
}
const onListPointerLeave = () => {
  if (!hoveringListScrollbar.value) return
  hoveringListScrollbar.value = false
  showListScrollbarDuringScroll()
}
const search = computed({ get: () => props.searchKeyword, set: (value: string) => emit('update:searchKeyword', value) })
const documentCount = computed(() => props.knowledgeBases.reduce((count, kb) => count + (kb.documentCount || 0), 0))
type FolioFormat = { label: string; kind: string }
const formatPreviews = ref<Record<string, FolioFormat[]>>({})
const formatKey = (kb: KnowledgeBaseVM) => JSON.stringify([kb.id, kb.name, kb.documentCount])
const formatRequests = new Map<string, Promise<FolioFormat[]>>()
const documentFormats = (documents: Array<{ name: string; ext?: string }>): FolioFormat[] => {
  const formats = new Map<string, FolioFormat>()
  for (const document of documents) {
    const ext = (document.ext || document.name.split('.').slice(1).pop() || '').replace(/^\./, '').toLowerCase()
    const kind = ext === 'pdf' ? 'pdf' : ['doc', 'docx', 'odt'].includes(ext) ? 'word'
      : ['xls', 'xlsx', 'csv', 'tsv', 'ods'].includes(ext) ? 'sheet'
        : ['ppt', 'pptx', 'odp'].includes(ext) ? 'slides'
          : ['png', 'jpg', 'jpeg', 'bmp', 'webp', 'gif', 'svg'].includes(ext) ? 'image'
            : ['md', 'markdown'].includes(ext) ? 'markdown' : 'text'
    const label = ext ? ext.toUpperCase() : 'FILE'
    formats.set(label, { label, kind })
  }
  return [...formats.values()]
}
const folioFormats = (kb: KnowledgeBaseVM): FolioFormat[] => {
  return kb.documents.length ? documentFormats(kb.documents) : formatPreviews.value[formatKey(kb)] || []
}
const formatsLoading = (kb: KnowledgeBaseVM) => kb.documentCount > 0 && !kb.documents.length && !formatPreviews.value[formatKey(kb)]
// 列表接口不含格式；仅为非空库补齐目录元数据，限制并发并丢弃过期结果。
watch([() => props.knowledgeBases, () => props.refreshing], async (_, __, onCleanup) => {
  let stale = false
  onCleanup(() => { stale = true })
  if (props.refreshing) return
  const pending = props.knowledgeBases.filter(kb => kb.documentCount > 0 && !kb.documents.length)
  let next = 0
  await Promise.all(Array.from({ length: Math.min(3, pending.length) }, async () => {
    while (!stale && next < pending.length) {
      const kb = pending[next++]!
      const key = formatKey(kb)
      try {
        let request = formatRequests.get(key)
        if (!request) {
          request = loadKbDocs(kb.name).then(documentFormats)
          formatRequests.set(key, request)
          void request.finally(() => { if (formatRequests.get(key) === request) formatRequests.delete(key) }).catch(() => {})
        }
        const formats = await request
        if (!stale) formatPreviews.value[key] = formats.length ? formats : [{ label: 'FILE', kind: 'text' }]
      } catch {
        // 失败才使用通用标识；已有结果继续保留，刷新不会闪回占位。
        if (!stale && !formatPreviews.value[key]) formatPreviews.value[key] = [{ label: 'FILE', kind: 'text' }]
      }
    }
  }))
}, { immediate: true })
const visibleKnowledgeBases = computed(() => {
  const query = search.value.trim().toLocaleLowerCase()
  return props.knowledgeBases.filter(kb => !query || `${kb.name} ${kb.description || ''}`.toLocaleLowerCase().includes(query)).sort((a, b) => {
    if (sortBy.value === 'name') return a.name.localeCompare(b.name, 'zh-CN')
    if (sortBy.value === 'documents') return (b.documentCount || 0) - (a.documentCount || 0)
    return toTimestamp(b.updatedAt) - toTimestamp(a.updatedAt)
  })
})
// 与设置页知识库共用同一判定：共享库仅 admin 可编辑 / 删除
const canManage = (kb: KnowledgeBaseVM) => canManageKnowledgeBase(kb, props.isAdmin)
const shortDate = (date: Date) => {
  const parsed = parseDate(date)
  return parsed ? new Intl.DateTimeFormat('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit' }).format(parsed) : '日期未知'
}
let libraryScrollTop = 0
let documentsNeedReveal = false
const sceneSnapshot = ref<{ kb: KnowledgeBaseVM; loading: boolean; error: string } | null>(null)
const displayedKnowledgeBase = computed(() => sceneSnapshot.value?.kb ?? props.selectedKnowledgeBase)
const displayedDocsLoading = computed(() => sceneSnapshot.value?.loading ?? !!props.docsLoading)
const displayedDocsError = computed(() => sceneSnapshot.value?.error ?? props.docsError ?? '')
const freezeScene = () => {
  const kb = props.selectedKnowledgeBase
  if (kb) sceneSnapshot.value = { kb: { ...kb, documents: [...kb.documents] }, loading: !!props.docsLoading, error: props.docsError || '' }
}
let openingFolio: HTMLElement | null = null
let openingSource: HTMLElement | null = null
const sharedElementClones = new Set<HTMLElement>()
let openingCoverBounds: DOMRect | null = null
let openingFromKeyboard = false
const surfaceAnimations = new Map<Element, Set<Animation>>()
type Motion = { element: Element | null; frames: Keyframe[]; duration: number; delay?: number; easing?: string; direction?: PlaybackDirection }
const clearOpeningFolio = () => {
  openingFolio?.remove()
  sharedElementClones.forEach(clone => clone.remove())
  sharedElementClones.clear()
  openingSource?.style.removeProperty('visibility')
  openingFolio = null
  openingSource = null
  openingCoverBounds = null
}
// Capture before Vue replaces the library; for closing, capture the newly rendered
// card after restoring the list's scroll position instead of using stale coordinates.
const captureFolio = (source: HTMLElement) => {
  const workspace = source.closest<HTMLElement>('.kb-workspace')
  const cover = source.querySelector<HTMLElement>('.kw-folio-cover')
  if (!workspace || !cover || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  clearOpeningFolio()
  // 入场动画可能还在播放（只取消卡片自身的，不动内页图标）：
  // 否则量到的是带位移的几何，克隆体会从偏下的位置起飞
  source.getAnimations().forEach(animation => animation.cancel())
  const bounds = source.getBoundingClientRect()
  const host = workspace.getBoundingClientRect()
  const clone = source.cloneNode(true) as HTMLElement
  openingCoverBounds = cover.getBoundingClientRect()
  clone.classList.add('kw-opening-folio')
  clone.setAttribute('aria-hidden', 'true')
  clone.inert = true
  Object.assign(clone.style, {
    left: `${bounds.left - host.left}px`, top: `${bounds.top - host.top}px`,
    width: `${bounds.width}px`, height: `${bounds.height}px`,
  })
  workspace.appendChild(clone)
  openingFolio = clone
  openingSource = source
  source.style.visibility = 'hidden'
}
const openKnowledgeBase = (kb: KnowledgeBaseVM, event: MouseEvent) => {
  if (isTransitioning.value) return
  libraryScrollTop = scrollContainer.value?.scrollTop || 0
  openingFromKeyboard = event.detail === 0
  const source = (event.currentTarget as HTMLElement).closest<HTMLElement>('.kw-folio')
  if (source) captureFolio(source)
  documentsNeedReveal = true
  emit('select', kb)
  detailOpen.value = true
}
const closeKnowledgeBase = () => {
  if (isTransitioning.value) return
  freezeScene()
  documentsNeedReveal = false
  detailOpen.value = false
  emit('close')
}
const cancelMotion = (element: Element) => {
  surfaceAnimations.get(element)?.forEach(animation => animation.cancel())
  element.querySelectorAll('.document-items').forEach(list => {
    surfaceAnimations.get(list)?.forEach(animation => animation.cancel())
  })
}
const animateScene = async (root: Element, motions: Motion[]) => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  cancelMotion(root)
  const animations = new Set<Animation>()
  surfaceAnimations.set(root, animations)
  isTransitioning.value = true
  try {
    motions.forEach(({ element, frames, duration, delay = 0, easing = 'cubic-bezier(.22,1,.36,1)', direction = 'normal' }) => {
      if (element) animations.add(element.animate(frames, {
        duration, delay, easing, direction, fill: 'both',
      }))
    })
    await Promise.allSettled(Array.from(animations, animation => animation.finished))
  } finally {
    animations.forEach(animation => animation.cancel())
    if (surfaceAnimations.get(root) === animations) surfaceAnimations.delete(root)
    isTransitioning.value = surfaceAnimations.size > 0
  }
}
// A response arriving during the fold is committed only after the scene settles.
// The short content reveal never locks navigation and never reruns the folder.
const revealDocuments = () => {
  const root = readingView.value
  if (!detailOpen.value || !documentsNeedReveal || sceneSnapshot.value || props.docsLoading || !root) return
  documentsNeedReveal = false
  const list = root.querySelector('.document-items')
  if (!list || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  const children = Array.from(list.querySelectorAll('.document-item, .kb-docs-error')).slice(0, 8)
  const animations = new Set<Animation>()
  surfaceAnimations.set(list, animations)
  for (const [index, child] of (children.length ? children : [list]).entries()) {
    animations.add(child.animate([{ opacity: 0, transform: 'translateY(10px)' }, { opacity: 1, transform: 'translateY(0)' }], {
      duration: 220, delay: index * 18, easing: 'cubic-bezier(.22,1,.36,1)', fill: 'both',
    }))
  }
  void Promise.allSettled([...animations].map(animation => animation.finished)).finally(() => {
    animations.forEach(animation => animation.cancel())
    if (surfaceAnimations.get(list) === animations) surfaceAnimations.delete(list)
  })
}
// 骨架 → 数据：一次交叉溶解。骨架原地渐隐，卡片在它化开的途中接着渐显，
// 全程只动透明度，不做位移和倾斜。只在 loading 落下的这一刻播一次：
// 从文档目录返回书架时卡片同样会重新挂载，但那由文件夹过场接管，不重复播放。
const skeletonLeaving = ref(false)
const dissolveShelf = () => {
  const root = scrollContainer.value
  if (!root || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    skeletonLeaving.value = false
    return
  }
  const ghost = root.querySelector<HTMLElement>('.kw-shelf-ghost')
  const cards = Array.from(root.querySelectorAll<HTMLElement>('.kw-shelf:not(.kw-shelf-ghost) > .kw-folio, .kw-shelf:not(.kw-shelf-ghost) > .kw-new-folio, .kw-empty'))
  if (!ghost && !cards.length) {
    skeletonLeaving.value = false
    return
  }
  const animations = new Set<Animation>()
  surfaceAnimations.set(root, animations)
  if (ghost) {
    const fade = ghost.animate([{ opacity: 1 }, { opacity: 0 }], {
      duration: 220, easing: 'cubic-bezier(.4,0,1,1)', fill: 'both',
    })
    animations.add(fade)
    // 骨架一化开就撤走，别让它空占着叠放层等到卡片全部显影
    void fade.finished.then(() => {
      skeletonLeaving.value = false
      fade.cancel()
    }).catch(() => {})
  }
  cards.forEach((card, index) => {
    const animation = card.animate([{ opacity: 0 }, { opacity: 1 }], {
      // 90ms 的错开让卡片在骨架还剩一半时就接手，两段叠起来看是连续的一次溶解
      duration: 420, delay: 90 + Math.min(index, 9) * 26, easing: 'cubic-bezier(.33,1,.68,1)', fill: 'both',
    })
    animations.add(animation)
    // 单张卡片显影完就撤销填充，hover 抬升不必等整排播完（cancel 会让 finished 落空，忽略即可）
    void animation.finished.then(() => animation.cancel()).catch(() => {})
  })
  void Promise.allSettled([...animations].map(animation => animation.finished)).finally(() => {
    skeletonLeaving.value = false
    animations.forEach(animation => animation.cancel())
    if (surfaceAnimations.get(root) === animations) surfaceAnimations.delete(root)
  })
}
// 用 pre（默认）时机置起 skeletonLeaving：骨架要与卡片在同一次渲染里共存，
// 否则骨架先被销毁，交叉溶解就退化成一段空白的先后切换。
watch(() => props.loading, (loading, previous) => {
  if (loading) {
    // 溶解途中又开始加载：收场上一次的动画，骨架回到正常占位状态
    if (skeletonLeaving.value && scrollContainer.value) {
      skeletonLeaving.value = false
      cancelMotion(scrollContainer.value)
    }
    return
  }
  if (!previous) return
  skeletonLeaving.value = true
  void nextTick(dissolveShelf)
})
const FOLDER_DURATION = 620
const FOLDER_EASING = 'cubic-bezier(.4,0,.2,1)'
const folderMotions = (reading: Element, closing: boolean): Motion[] => {
  const folio = openingFolio
  const from = openingCoverBounds
  const sheet = reading.querySelector<HTMLElement>('.kw-reading-sheet')
  const workspace = folio?.parentElement
  if (!folio || !from || !sheet || !workspace) return []
  const to = sheet.getBoundingClientRect()
  const host = workspace.getBoundingClientRect()
  const motions: Motion[] = []
  const add = (element: Element | null, frames: Keyframe[]) => {
    motions.push({ element, frames, duration: FOLDER_DURATION, easing: FOLDER_EASING, direction: closing ? 'reverse' : 'normal' })
  }
  add(sheet, [
    { transformOrigin: 'top left', transform: `translate(${from.left - to.left}px, ${from.top - to.top}px) scale(${from.width / to.width}, ${from.height / to.height})` },
    { transformOrigin: 'top left', transform: 'translate(0,0) scale(1,1)' },
  ])
  add(folio, [
    { transformOrigin: 'top left', transform: 'translate(0,0) scale(1,1)', opacity: 1 },
    { opacity: 0, offset: .38 },
    { transformOrigin: 'top left', transform: `translate(${to.left - from.left}px, ${to.top - from.top}px) scale(${to.width / from.width}, ${to.height / from.height})`, opacity: 0 },
  ])
  // The same five elements travel in both directions. They live outside the
  // resizing cover so the typography and format sheets never get stretched.
  const pairs = [
    ['.kw-folio-symbol', '.kw-bookmark-symbol > span'],
    ['.kw-folio-open h2', '.kw-bookmark h1'],
    ['.kw-folio-open p', '.kw-bookmark > p'],
    ['.kw-folio-bottom strong', '.kw-bookmark-count strong'],
    ['.kw-visibility', '.kw-bookmark-info > span:first-child'],
  ]
  // Batch geometry/style reads before creating any layer. Only transform and
  // opacity change during playback; font metrics and text wrapping stay fixed.
  const styleKeys = ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'color', 'display', 'alignItems', 'gap', 'whiteSpace', 'padding', 'boxSizing'] as const
  const snapshot = (node: HTMLElement) => {
    const style = getComputedStyle(node)
    return { node, rect: node.getBoundingClientRect(), styles: Object.fromEntries(styleKeys.map(key => [key, style[key]])), font: parseFloat(style.fontSize) || 14 }
  }
  const measured = pairs.flatMap(([cardSelector, detailSelector]) => {
    const cardPart = folio.querySelector<HTMLElement>(cardSelector!)
    const detailPart = reading.querySelector<HTMLElement>(detailSelector!)
    return cardPart && detailPart ? [{ start: snapshot(cardPart), end: snapshot(detailPart) }] : []
  })
  const rowNodes = Array.from(sheet.querySelectorAll<HTMLElement>('.document-item, .kb-document-placeholder'))
  const rowBounds = rowNodes.map(node => ({ node, rect: node.getBoundingClientRect() })).filter(({ rect }) => rect.bottom > to.top && rect.top < to.bottom).slice(0, 8)
  const paperBounds = Array.from(folio.querySelectorAll<HTMLElement>('.kw-folder-sheets .kw-format-page')).map(node => ({ node, rect: node.getBoundingClientRect() }))
  for (const { start, end } of measured) {
    const symbol = start.node.classList.contains('kw-folio-symbol')
    const ratio = symbol ? end.rect.width / Math.max(1, start.rect.width) : end.font / start.font
    const makeGhost = (entry: typeof start) => {
      const ghost = entry.node.cloneNode(true) as HTMLElement
      Object.assign(ghost.style, entry.styles, {
        position: 'absolute', left: `${entry.rect.left - host.left}px`, top: `${entry.rect.top - host.top}px`,
        width: `${entry.rect.width}px`, height: `${entry.rect.height}px`, margin: '0',
        transformOrigin: 'top left', pointerEvents: 'none', zIndex: '11', overflow: symbol ? 'visible' : 'hidden',
        visibility: 'visible', willChange: 'transform, opacity',
      })
      ghost.setAttribute('aria-hidden', 'true')
      ghost.inert = true
      workspace.appendChild(ghost)
      sharedElementClones.add(ghost)
      return ghost
    }
    const outgoing = makeGhost(start)
    const incoming = makeGhost(end)
    const dx = end.rect.left - start.rect.left
    const dy = end.rect.top - start.rect.top
    add(outgoing, [
      { transform: 'translate3d(0,0,0) scale(1)', opacity: 1 },
      { opacity: 0, offset: .72 },
      { transform: `translate3d(${dx}px,${dy}px,0) scale(${ratio})`, opacity: 0 },
    ])
    add(incoming, [
      { transform: `translate3d(${-dx}px,${-dy}px,0) scale(${1 / ratio})`, opacity: 0 },
      { opacity: 0, offset: .22 },
      { transform: 'translate3d(0,0,0) scale(1)', opacity: 1 },
    ])
    start.node.style.visibility = 'hidden'
    add(end.node, [{ visibility: 'hidden' }, { visibility: 'hidden' }])
  }
  // The actual sheets tucked inside the folder fan out into the first document
  // rows (or equally sized loading placeholders). Reverse playback tucks them in.
  paperBounds.slice(0, 3).forEach(({ node, rect }, index) => {
    const row = rowBounds[index]
    if (!row) return
    const paper = document.createElement('div')
    paper.className = 'kw-travelling-paper'
    Object.assign(paper.style, { left: `${row.rect.left - host.left}px`, top: `${row.rect.top - host.top}px`, width: `${row.rect.width}px`, height: `${row.rect.height}px` })
    paper.setAttribute('aria-hidden', 'true')
    workspace.appendChild(paper)
    sharedElementClones.add(paper)
    const dx = rect.left - row.rect.left
    const dy = rect.top - row.rect.top
    const initial = `translate3d(${dx}px,${dy}px,0) scale(${rect.width / row.rect.width},${rect.height / row.rect.height}) rotate(${index * 2 - 2}deg)`
    add(paper, [
      { transform: initial, opacity: 0 },
      { transform: initial, opacity: 0, offset: .08 + index * .04 },
      { transform: `translate3d(${dx * .65}px,${dy * .65 - 22 - index * 8}px,0) scale(.65,.8) rotate(${index - 1}deg)`, opacity: .95, offset: .42 + index * .04 },
      { transform: 'translate3d(0,0,0) scale(1,1) rotate(0deg)', opacity: .85, offset: .78 + index * .04 },
      { transform: 'translate3d(0,0,0) scale(1,1) rotate(0deg)', opacity: 0 },
    ])
    add(node, [{ opacity: 1 }, { opacity: 0, offset: .4 }, { opacity: 0 }])
  })
  for (const control of folio.querySelectorAll('.kw-folio-top, .kw-folio-open, .kw-folio-bottom')) {
    add(control, [{ opacity: 1 }, { opacity: 0, offset: .2 }, { opacity: 0 }])
  }
  for (const child of sheet.children) {
    add(child, [{ opacity: 0 }, { opacity: 0, offset: .48 }, { opacity: 1 }])
  }
  rowBounds.forEach(({ node }, index) => {
    add(node, [
      { opacity: 0, transform: 'translate3d(0,18px,0)' },
      { opacity: 0, transform: 'translate3d(0,18px,0)', offset: .5 + index * .025 },
      { opacity: 1, transform: 'translate3d(0,0,0)' },
    ])
  })
  for (const extra of reading.querySelectorAll('.kw-bookmark-count > span, .kw-bookmark-info > span:last-child, .kw-bookmark-actions, .kw-reading-nav')) {
    add(extra, [{ opacity: 0, transform: 'translateY(6px)' }, { opacity: 0, offset: .7 }, { opacity: 1, transform: 'translateY(0)' }])
  }
  return motions
}
const enterWorkspace = async (element: Element, done: () => void) => {
  try {
    if (element.classList.contains('kw-library')) {
      if (scrollContainer.value) scrollContainer.value.scrollTop = libraryScrollTop
      await animateScene(element, [{ element, frames: [{ opacity: 0 }, { opacity: 0, offset: .8 }, { opacity: 1 }], duration: FOLDER_DURATION, easing: FOLDER_EASING }])
    } else {
      freezeScene()
      await nextTick()
      const motions = folderMotions(element, false)
      if (motions.length) {
        documentsNeedReveal = displayedDocsLoading.value
        try { await animateScene(element, motions) } finally {
          clearOpeningFolio()
          sceneSnapshot.value = null
          await nextTick()
          revealDocuments()
        }
      } else {
        await animateScene(element, [{ element, frames: [{ opacity: 0 }, { opacity: 1 }], duration: 180 }])
        sceneSnapshot.value = null
        await nextTick()
        revealDocuments()
      }
    }
  } finally { done() }
}
const leaveWorkspace = async (element: Element, done: () => void) => {
  ; (element as HTMLElement).inert = true
  try {
    if (element.classList.contains('kw-reading')) {
      freezeScene()
      documentsNeedReveal = false
      // Vue mounts the incoming library in this same update. Wait for its real
      // geometry, including responsive layout and the restored scroll position.
      await nextTick()
      const workspace = element.closest('.kb-workspace')
      const card = Array.from(workspace?.querySelectorAll<HTMLElement>('.kw-library .kw-folio') || [])
        .find(item => item.dataset.kbId === props.selectedKnowledgeBase?.id)
      if (card && scrollContainer.value) {
        const list = scrollContainer.value.getBoundingClientRect()
        const bounds = card.getBoundingClientRect()
        if (bounds.bottom > list.bottom || bounds.top < list.top) {
          scrollContainer.value.scrollTop += bounds.top - list.top - 12
          libraryScrollTop = scrollContainer.value.scrollTop
        }
      }
      if (card) captureFolio(card)
      const motions = folderMotions(element, true)
      try {
        await animateScene(element, motions.length ? motions : [{ element, frames: [{ opacity: 1 }, { opacity: 0 }], duration: 180 }])
      } finally { clearOpeningFolio(); sceneSnapshot.value = null }
    } else {
      await animateScene(element, [{ element, frames: [{ opacity: 1 }, { opacity: 0 }], duration: 300 }])
    }
  } finally { done() }
}
watch([() => props.docsLoading, () => props.docsError], () => revealDocuments(), { flush: 'post' })
watch(isTransitioning, busy => {
  if (!busy && openingFromKeyboard && detailOpen.value) {
    openingFromKeyboard = false
    readingView.value?.querySelector<HTMLButtonElement>('.kw-reading-nav button')?.focus({ preventScroll: true })
  }
}, { flush: 'post' })
onBeforeUnmount(() => {
  clearOpeningFolio()
  surfaceAnimations.forEach(animations => animations.forEach(animation => animation.cancel()))
  surfaceAnimations.clear()
  if (listScrollbarHideTimer) {
    clearTimeout(listScrollbarHideTimer)
    listScrollbarHideTimer = null
  }
})
watch(detailOpen, open => {
  persistDetailOpen(open)
  if (!open && scrollContainer.value) scrollContainer.value.scrollTop = libraryScrollTop
  if (!open) syncScopeIndicator(false)
}, { flush: 'post' })
watch(() => props.permissionFilter, () => {
  detailOpen.value = false
  restoringDetail.value = false
})
watch([search, sortBy, () => props.permissionFilter], () => {
  libraryScrollTop = 0
  scrollContainer.value?.scrollTo({ top: 0 })
})
watch(() => props.selectedKnowledgeBase, kb => { if (!kb) detailOpen.value = false })
// 刷新恢复：知识库列表一旦就绪就一次性定好落点（文档目录 / 书架），
// 占位骨架直接换成目标视图，不再出现“书架 → 文档目录”的二次跳转
watch([() => props.knowledgeBases, () => props.selectedKnowledgeBase, () => props.error], () => {
  if (!restoringDetail.value) return
  restoringDetail.value = false
  if (props.selectedKnowledgeBase) {
    // 恢复进来的文档目录同样补上文档入场动画
    documentsNeedReveal = true
  } else {
    detailOpen.value = false
  }
})
</script>

<style scoped>
.kb-workspace {
  position: relative;
  --kw-text: #333e55;
  --kw-muted: #8490a5;
  --kw-accent: #566bb4;
  min-width: 0;
  min-height: 0;
  flex: 1;
  display: flex;
  color: var(--kw-text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

.kb-workspace button,
.kb-workspace input,
.kb-workspace select {
  font: inherit;
}

/* Keep reused document controls and loading states static in this workspace. */
.kb-workspace :deep(*),
.kb-workspace :deep(*::before),
.kb-workspace :deep(*::after) {
  animation: none !important;
  transition: none !important;
  scroll-behavior: auto !important;
}

/* loading 图标带 !important 是为了抵消上方 .kb-workspace :deep(*) 的 animation: none !important，
   否则 a-spin 的指示图标（.anticon-spin）无法旋转 */
.kb-workspace :deep(.anticon-spin) {
  animation: loadingCircle 1s infinite linear !important;
}

/* 以下 transition 带 !important 是为了抵消上方 .kb-workspace :deep(*) 的 transition: none !important，
   让批量处理按钮的收展、行复选框滑入与全选按钮的状态切换与设置界面知识库保持一致 */
.kb-workspace :deep(.bulk-btn-origin) {
  transition: width 0.28s ease, background-color 0.2s ease !important;
}

.kb-workspace :deep(.doc-check) {
  transition: width 0.28s ease, opacity 0.28s ease, margin-right 0.28s ease, margin-inline-end 0.28s ease !important;
}

.kb-workspace :deep(.select-toggle) {
  transition: background-color 0.2s ease, color 0.2s ease, transform 0.2s ease !important;
}

.kb-workspace :deep(.select-check) {
  transition: background-color 0.2s ease !important;
}

.kb-workspace :deep(.select-check-dot),
.kb-workspace :deep(.select-indeterminate),
.kb-workspace :deep(.select-text-inner) {
  transition: opacity 0.18s ease, transform 0.18s ease !important;
}

/* 文档行复选框（antd a-checkbox）的勾选动画：上面的 animation/transition: none !important
   会把 antd 原生的「底色描边过渡 + 对勾弹入 + 选中波纹」全部关掉，这里按 antd 默认 motion token
   （motionDurationFast 0.1s / Mid 0.2s / Slow 0.3s、motionEaseInBack / motionEaseOutBack）
   逐项还原，勾选观感与设置界面知识库一致 */
.kb-workspace :deep(.doc-check .ant-checkbox-inner) {
  transition: all 0.3s !important;
}

/* 对勾取消勾选时收回：motionDurationFast + motionEaseInBack */
.kb-workspace :deep(.doc-check .ant-checkbox-inner::after) {
  transition: all 0.1s cubic-bezier(0.71, -0.46, 0.88, 0.6), opacity 0.1s !important;
}

/* 对勾勾上时弹入：motionDurationMid + motionEaseOutBack，延迟 motionDurationFast */
.kb-workspace :deep(.doc-check .ant-checkbox-checked .ant-checkbox-inner::after) {
  transition: all 0.2s cubic-bezier(0.12, 0.4, 0.29, 1.46) 0.1s !important;
}

/* 选中瞬间的波纹环：antd 的 animation-name 带 cssinjs hash，静态 CSS 引用不到，
   改用文件末尾等价的 kwCheckboxEffect 复刻（scale 1→1.6、opacity .5→0） */
.kb-workspace :deep(.doc-check .ant-checkbox-checked::after) {
  animation: kwCheckboxEffect 0.3s ease-in-out backwards !important;
  transition: all 0.3s !important;
}

.kb-workspace button {
  cursor: pointer;
}

.kb-workspace button:disabled {
  cursor: not-allowed;
  opacity: .5;
}

.kb-workspace button:focus-visible,
.kb-workspace select:focus-visible {
  outline: 2px solid #869acb;
  outline-offset: 4px;
}

.kw-body {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  width: 100%;
  min-height: 0;
  overflow: hidden;
}

.kw-body>.kw-library,
.kw-body>.kw-reading {
  grid-area: 1 / 1;
  width: 100%;
  min-width: 0;
}

.kw-body>.kw-library {
  position: relative;
  z-index: 1;
}

.kw-body>.kw-reading {
  position: relative;
  z-index: 2;
}

.kw-library {
  /* 供 .kw-library-scroll 复用：滚动条槽位与自身左右内边距等宽，保证外扩后不会被 .kw-body 裁切 */
  --kw-side-pad: 28px;
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
  min-height: 0;
  max-width: 1080px;
  padding: 32px var(--kw-side-pad) 16px;
  margin: 0 auto;
}

.kw-intro,
.kw-search-dock,
.kw-shelf-toolbar,
.kw-library-note {
  flex-shrink: 0;
}

.kw-search-dock {
  width: 100%;
}

.kw-library-scroll {
  flex: 1;
  min-height: 0;
  margin: 0 -8px;
  /* 右侧只外扩出一条滚动条槽位（上限 16px，且不超过 .kw-library 的内边距，避免被 .kw-body 裁切）：
     滚动条落在内容列之外，同时与卡片保持原先的 8px 间距 */
  margin-right: calc(-1 * min(var(--kw-side-pad, 8px), 16px));
  /* 顶部内边距为第一行卡片 hover 时纸张上移预留净空（卡片 -5px、纸张再 -7px、
     --sheet-lift 最多 -10px，纸顶会探到卡片顶之上约 20px），
     否则超出滚动口的部分会被 overflow 裁切，看起来像被遮盖；
     与 .kw-shelf-toolbar 收窄的下外边距合计，保持原有视觉间距 */
  padding: 14px 8px 11px;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  /* 始终预留滚动条槽位：滚动条出现/消失都不改变内容宽度，卡片不会重新排布 */
  scrollbar-gutter: stable;
  scrollbar-width: thin;
}

.kw-library-scroll::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.kw-library-scroll::-webkit-scrollbar-track {
  background-color: transparent;
}

.kw-library-scroll::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, .15);
  border-radius: 3px;
  transition: background-color .2s ease;
}

/* 未滚动时隐藏滑块，滚动/悬停在滚动条区域时显示（与 chat-history 一致） */
.kw-library-scroll.hide-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  transition: background-color .2s ease;
}

.kw-library-scroll.hide-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, .15);
}

.kw-library-scroll.hide-scrollbar::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, .25);
}

.kw-library-scroll.hide-scrollbar {
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color .2s ease;
}

.kw-library-scroll:not(.hide-scrollbar) {
  scrollbar-color: rgba(0, 0, 0, .15) transparent;
  transition: scrollbar-color .2s ease;
}

.kw-library-scroll:focus-visible {
  outline: 2px solid #869acb;
  outline-offset: -2px;
  border-radius: 12px;
}

.kw-intro {
  text-align: center;
  margin-bottom: 28px;
}

.kw-intro h1 {
  font-family: 'SmileySansOblique', 'Microsoft YaHei', sans-serif;
  font-size: 36px;
  line-height: 1.45;
  font-weight: 400;
  color: #303b58;
  letter-spacing: 1px;
  margin: 0 0 10px;
}

.kw-intro p {
  margin: 0;
  font-size: 13px;
  color: #8591a5;
  letter-spacing: .5px;
}

.kw-search-dock {
  max-width: 640px;
  padding: 18px 20px 12px;
  margin: 0 auto 40px;
  background: rgba(255, 255, 255, .92);
  border: 1px solid rgba(255, 255, 255, .9);
  border-radius: 24px;
  box-shadow: 0 5px 16px #53658b0a, 0 2px 5px #53658b04;
}

.kw-search-dock:focus-within {
  box-shadow: 0 8px 26px #53658b10, 0 0 0 2px #7089ca15;
}

.kw-search-field {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 5px;
  height: 32px;
  color: #9aa6bb;
}

.kw-search-field>.anticon {
  font-size: 19px;
}

.kw-search-field input {
  flex: 1;
  width: 100%;
  min-width: 0;
  border: 0;
  outline: none;
  color: #414e69;
  background: transparent;
  font-size: 14px;
}

.kw-search-field input::placeholder {
  color: #a4aec0;
}

.kw-dock-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  margin-top: 16px;
}

.kw-scope {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 3px;
  border-radius: 12px;
  background: #f5f7fc;
}

.kw-scope-indicator {
  position: absolute;
  left: 0;
  border-radius: 9px;
  background: linear-gradient(120deg, #e3eafd, #dce5fa);
  box-shadow: inset 0 1px 1px #fff, 0 2px 6px #6b7eaf26;
  pointer-events: none;
  overflow: hidden;
  will-change: transform;
}

/* 缓慢流动的高光带，与画布/交付中心 Tab 滑块的极光效果一致 */
.kw-scope-indicator::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(115deg, transparent 25%, rgba(96, 165, 250, .18) 50%, transparent 75%);
  background-size: 220% 100%;
  /* !important 是为了抵消上方 .kb-workspace :deep(*) 的 animation: none !important */
  animation: kw-scope-aurora 3.2s ease-in-out infinite alternate !important;
}

@keyframes kw-scope-aurora {
  from { background-position: 120% 0; }
  to { background-position: -20% 0; }
}

.kw-scope button {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  padding: 7px 11px;
  border-radius: 9px;
  color: #8895ab;
  font-size: 12px;
  line-height: 1;
  background: transparent;
  white-space: nowrap;
  /* !important 是为了抵消上方 .kb-workspace :deep(*) 的 transition: none !important */
  transition: color .25s ease, transform .15s ease !important;
}

.kw-scope button:active {
  transform: scale(.96);
}

.kw-scope button :deep(.anticon) {
  transition: transform .25s ease !important;
}

.kw-scope button:hover:not(.active) {
  color: #5366a6;
}

.kw-scope button:hover:not(.active) :deep(.anticon) {
  transform: translateY(-1px);
}

.kw-scope button.active {
  color: #45538f;
  font-weight: 500;
}

/* 图标弹跳入场 */
.kw-scope button.active :deep(.anticon) {
  animation: kw-scope-icon-pop .45s cubic-bezier(.34, 1.56, .64, 1) !important;
}

@keyframes kw-scope-icon-pop {
  0% { transform: scale(.6) rotate(-8deg); }
  60% { transform: scale(1.18) rotate(3deg); }
  100% { transform: scale(1) rotate(0deg); }
}

@media (prefers-reduced-motion: reduce) {
  .kw-scope-indicator::before,
  .kw-scope button.active :deep(.anticon) {
    animation: none !important;
  }
}

.kw-dock-count {
  font-size: 12px;
  letter-spacing: .2px;
  color: #8f9cae;
  white-space: nowrap;
}

.kw-shelf-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 14px;
  /* 下外边距收窄：首行净空改由 .kw-library-scroll 的顶部内边距提供（那里不会被裁切） */
  margin: 0 4px 3px;
}

.kw-shelf-heading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: #7b889f;
  font-size: 12px;
}

.kw-shelf-title {
  font-size: 13px;
  color: #6b7994;
}

.kw-result-count {
  color: #a6b0c1;
  font-size: 11px;
}

.kw-shelf-actions {
  display: flex;
  align-items: center;
  gap: 5px;
}

.kw-sort-trigger {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #8795ac;
  border: none;
  padding: 6px;
  background: transparent;
  cursor: pointer;
}

.kw-sort-trigger:hover {
  color: #5366a6;
}

.kw-sort-caret {
  font-size: 10px;
  color: inherit;
}

.kw-icon-button {
  border: 0;
  background: transparent;
  color: #9aa5b8;
  width: 29px;
  height: 29px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  padding: 0;
}

.kw-icon-button:hover {
  color: #5265a5;
  background: #e9eef8;
}

.kw-create-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 9px 14px;
  margin-left: 8px;
  border: 1px solid #c6daff;
  border-radius: 12px;
  background: linear-gradient(130deg, #fffdfd, #e6ecfd);
  color: #5a6caa;
  font-size: 12px !important;
  box-shadow: 0 3px 9px #627bad0d, inset 0 1px 1px #fff;
  white-space: nowrap;
}

.kw-create-button:hover {
  box-shadow: 0 5px 15px #627bad1c;
}

.kw-shelf {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(min(238px, 100%), 1fr));
  column-gap: 26px;
  row-gap: 34px;
  padding: 10px 4px;
}

/* 溶解期的骨架：叠在刚显影的卡片之上原地渐隐。
   height:0 让它不占位（border-box 下仍会撑出 10px 的顶部内边距，
   正好与 .kw-shelf 的行起点对齐，再用等值负外边距抵消），
   于是骨架化开时卡片不会跟着上移一下。 */
.kw-shelf-ghost {
  position: relative;
  z-index: 2;
  height: 0;
  padding-bottom: 0;
  margin-bottom: -10px;
  overflow: visible;
  pointer-events: none;
}

/* transition 带 !important 是为了抵消上方 .kb-workspace :deep(*) 的 transition: none !important */
.kw-folio {
  position: relative;
  min-width: 0;
  isolation: isolate;
  padding-top: 22px;
  /* 纵向 flex：末行被“新建知识库”占位卡撑高时，封面能跟着填满整张卡，
     否则纸张层（相对 .kw-folio 定位）的底边会露在封面下方形成漏底 */
  display: flex;
  flex-direction: column;
  transition: transform .35s cubic-bezier(.22, 1, .36, 1) !important;
}

/* Keep the original folder's paper, tab and typography throughout the handoff. */
.kw-opening-folio {
  position: absolute;
  z-index: 10;
  margin: 0;
  pointer-events: none;
  transform: none;
  transform-origin: top left;
  will-change: transform, opacity;
  transition: none !important;
}



.kw-folio::before {
  content: '';
  position: absolute;
  inset: 9px 8px -5px;
  background: #ffffffa8;
  border: 1px solid #fff;
  border-radius: 19px;
  z-index: -1;
  transform: rotate(2deg);
  transition: transform .35s cubic-bezier(.22, 1, .36, 1) !important;
}

.kw-folio::after {
  content: '';
  position: absolute;
  inset: 3px 17px 5px 4px;
  background: #e8eef9;
  border: 1px solid #f9fbff;
  border-radius: 19px;
  z-index: -2;
  transform: rotate(-2deg);
  transition: transform .35s cubic-bezier(.22, 1, .36, 1) !important;
}

.kw-folio-tab {
  position: absolute;
  top: 0;
  left: 0;
  height: 35px;
  min-width: 96px;
  padding: 7px 26px;
  border-radius: 13px 17px 0 0;
  background: #dfe7f8;
  color: #8b9ac0;
  font-size: 10px;
  letter-spacing: 2px;
  text-align: center;
  /* letter-spacing 会在最后一个字符后多出 2px，居中时用等量的 text-indent 抵消，数字才真正居中 */
  text-indent: 2px;
}

.kw-folio-cover {
  padding: 20px;
  background: linear-gradient(150deg, #fffffff5 5%, #ffffffb8 90%);
  border: 1px solid #ffffffd9;
  border-radius: 0 21px 21px 21px;
  box-shadow: 0 6px 16px #6279a30a;
  position: relative;
  /* 填满被网格拉伸后的卡片高度，盖住纸张层底边 */
  flex: 1;
  display: flex;
  flex-direction: column;
  transition: box-shadow .35s !important;
}

.kw-folio:hover,
.kw-folio:focus-within {
  transform: translateY(-5px);
}

.kw-folio:hover::before {
  transform: rotate(4deg) translate(1px, 2px);
}

.kw-folio:hover::after {
  transform: rotate(-3deg) translateY(-3px);
}

.kw-folio:hover .kw-folio-cover {
  box-shadow: 0 12px 28px #6177a515;
}

.kw-folio-top {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 16px;
}

.kw-folio-symbol {
  flex-shrink: 0;
}

.has-documents .kw-folio-tab {
  z-index: 1;
  display: grid;
  place-items: center;
  height: 22px;
  padding: 0 24px;
  font-size: 11px;
  line-height: 1;
  color: #657ba6;
}

/* 层叠顺序：页签(1) < 薄纸层(2) < 封面(3)，纸张可以压住页签，同时仍从封面后面探出来。 */
.has-documents .kw-folio-cover {
  z-index: 3;
  background: linear-gradient(150deg, #fff 5%, #f7f9fe 90%);
}

.kw-format-pages {
  display: flex;
  align-items: center;
  height: 32px;
  padding-left: 2px;
  flex-shrink: 0;
}

.kw-format-page {
  --format-ink: #76859e;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 5px;
  width: 44px;
  height: 44px;
  padding: 7px 5px;
  border: 1px solid color-mix(in srgb, var(--format-ink) 25%, white);
  border-radius: 3px 8px 3px 3px;
  background: linear-gradient(145deg, white, color-mix(in srgb, var(--format-ink) 7%, white));
  color: var(--format-ink);
  box-shadow: 0 2px 4px #5367890a;
  transform: rotate(-5deg);
}

.kw-format-page + .kw-format-page {
  margin-left: -7px;
  transform: translateY(-2px) rotate(3deg);
}

.kw-format-page:nth-child(3) {
  transform: translateY(1px) rotate(9deg);
}

.kw-format-page.is-pdf { --format-ink: #e94848; }
.kw-format-page.is-word { --format-ink: #2b579a; }
.kw-format-page.is-sheet { --format-ink: #217346; }
.kw-format-page.is-slides { --format-ink: #d24726; }
/* 与 assets/image/svg 中对应文件图标的主色一致。 */
.kw-format-page.is-image { --format-ink: #4a8dff; }
.kw-format-page.is-markdown { --format-ink: #ff7232; }
.kw-format-page.is-text { --format-ink: #a0a0a0; }

.kw-format-label {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 11px;
  font-weight: 600;
  line-height: 12px;
  letter-spacing: .1px;
}

.kw-format-lines {
  height: 8px;
  width: 19px;
  opacity: .35;
  background: repeating-linear-gradient(to bottom, currentColor 0 1px, transparent 1px 4px);
}

/* 表格图标：1px 外框 + 两竖一横分隔线，组成 3 列 2 行的干净网格；
   比 repeating 渐变更清晰，小尺寸下不会因非整除出现缺边、断线 */
.is-sheet .kw-format-lines {
  box-sizing: border-box;
  border: 1px solid currentColor;
  border-radius: 1px;
  background:
    linear-gradient(currentColor 0 0) 33% 0 / 1px 100% no-repeat,
    linear-gradient(currentColor 0 0) 67% 0 / 1px 100% no-repeat,
    linear-gradient(currentColor 0 0) 0 50% / 100% 1px no-repeat;
}

.is-slides .kw-format-lines,
.is-image .kw-format-lines {
  border: 1px solid currentColor;
  background: linear-gradient(140deg, transparent 45%, currentColor 46% 52%, transparent 53%);
}

/* 薄纸层夹在页签与封面之间：三张纸在文件夹口扇形叠放，中间一张探得更高、
   两侧向外倾斜并互相压叠，只把顶部露在封面上沿之外；
   左边界落在页签右侧偏内，最左边那张纸压住页签一角，序号仍然露在外面。 */
.kw-folder-sheets {
  position: absolute;
  inset: 2px 16px 8px 64px;
  z-index: 2;
  display: flex;
  /* 纸张不足三张时不拉满整行，居中收拢，避免出现一条横贯的色带 */
  justify-content: center;
  pointer-events: none;
}

.kw-folder-sheets .kw-format-page {
  --sheet-angle: -4deg;
  --sheet-lift: 0px;
  /* 固定占比宽度：三张刚好铺满扇形，一两张时保持纸张比例 */
  flex: 0 1 42%;
  min-width: 0;
  width: auto;
  height: 100%;
  margin: 0;
  /* 露出高度有限：收紧顶部内边距与间距，把空间让给表格网格 */
  padding: 4px 12px 6px;
  gap: 3px;
  justify-content: flex-start;
  border-radius: 12px 12px 8px 8px;
  background: linear-gradient(145deg, color-mix(in srgb, var(--format-ink) 85%, white), var(--format-ink));
  border-color: var(--format-ink);
  color: #fff;
  transform: translateY(var(--sheet-lift)) rotate(var(--sheet-angle));
  transform-origin: center bottom;
  transition: transform .35s cubic-bezier(.22, 1, .36, 1) !important;
}

.kw-folder-sheets .kw-format-page:nth-child(2) {
  --sheet-angle: -1deg;
  --sheet-lift: -10px;
  margin-left: -14%;
}

.kw-folder-sheets .kw-format-page:nth-child(3) {
  --sheet-angle: 3deg;
  margin-left: -14%;
}

/* 只有一张纸时摆正一点、抬得稍高，靠右插在文件夹口，像随手夹进去的一份文件 */
.kw-folder-sheets .kw-format-page:only-child {
  /* 靠右放置时顺势向右倾斜，与右侧边缘的动势一致 */
  --sheet-angle: 3deg;
  --sheet-lift: -8px;
  /* auto 外边距优先于 justify-content，把单张纸推到右侧 */
  margin-left: auto;
}

.kw-folder-sheets .kw-format-label {
  text-align: right;
}

.kw-folder-sheets .kw-format-lines {
  /* 加高并收窄：3 列 2 行的格子保持接近 2:1 的单元格比例，
     不再被压成挤在一起的扁条 */
  width: 58%;
  height: 14px;
}

.kw-folio:hover .kw-folder-sheets .kw-format-page,
.kw-folio:focus-within .kw-folder-sheets .kw-format-page {
  transform: translateY(calc(var(--sheet-lift) - 7px)) rotate(var(--sheet-angle));
}

@media (prefers-reduced-motion: reduce) {
  .kw-folder-sheets .kw-format-page {
    transition: none !important;
  }
}

.kw-visibility {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-left: auto;
  color: #8b98ae;
  font-size: 12px;
  font-weight: 500;
  letter-spacing: .2px;
}

.kw-visibility .anticon {
  font-size: 13px;
}

.kw-more {
  position: relative;
  z-index: 2;
  font-size: 17px;
  width: 22px;
}

.kw-folio-open {
  display: block;
  width: 100%;
  border: 0;
  padding: 0;
  background: none;
  text-align: left;
  color: inherit;
  /* 封面被撑高时吸收多余高度，把底部统计行压在封面底边 */
  flex: 1;
}

.kw-folio-open::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 0 21px 21px 21px;
}

.kw-folio-open h2 {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 17px;
  font-weight: 550;
  letter-spacing: .2px;
  margin: 0 0 9px;
  color: #46526b;
}

.kw-folio-open p {
  margin: 0;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 1;
  line-clamp: 1;
  overflow: hidden;
  overflow-wrap: anywhere;
  min-height: 24px;
  font-size: 13px;
  line-height: 1.8;
  color: #728199;
}

.kw-folio-bottom {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
  font-size: 10px;
  color: #9ba9bd;
}

.kw-folio-bottom strong {
  font-size: 17px;
  font-weight: 500;
  color: #778aab;
  margin-right: 3px;
  font-variant-numeric: tabular-nums;
}

.kw-graph-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  position: relative;
  z-index: 2;
  border: 0;
  border-radius: 6px;
  padding: 4px 6px;
  background: #edf2fc;
  color: #8b9dc6;
  font-size: 10px;
}

.kw-open-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  transform: rotate(45deg);
  margin-left: auto;
  font-size: 13px;
  color: #a9b6cc;
  transition: transform .3s, color .3s !important;
}

.kw-folio:hover .kw-open-arrow {
  transform: rotate(45deg) translateY(-3px);
  color: #7c92bf;
}

.kw-new-folio {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 192px;
  margin-top: 22px;
  background: #f7faff40;
  border: 1px dashed #cdd8ec;
  border-radius: 21px;
  color: #9eacc3;
}

.kw-new-folio:hover {
  border-color: #adbedb;
  background: #ffffff60;
}

.kw-new-icon {
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  margin-bottom: 6px;
  border: 1px solid #e0e8f5;
  border-radius: 13px;
  font-size: 19px;
  color: #96a9cb;
  background: #ffffff80;
}

.kw-new-folio strong {
  font-size: 12px;
  font-weight: 400;
}

.kw-new-folio>span:last-child {
  font-size: 10px;
  color: #b0bbcf;
}

/* 正常文档流中排在滚动区下方，不参与滚动，也不会被滚动条覆盖 */
.kw-library-note {
  margin: 16px 0 0;
  text-align: center;
  color: #a6b1c3;
  font-size: 10px;
  letter-spacing: 1px;
}

.kw-empty {
  min-height: 255px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  text-align: center;
  padding: 28px;
  gap: 12px;
}

.kw-empty-icon {
  font-size: 32px;
  color: #a2b2d4;
}

.kw-empty-symbol-hero {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 56px;
}

.kw-empty h2 {
  margin: 8px 0 0;
  font-size: 17px;
  font-weight: 500;
  color: #6f7f9c;
}

.kw-empty p {
  margin: 0 0 6px;
  font-size: 12px;
  color: #95a2ba;
}

.kw-empty .kw-create-button {
  margin: 0;
}

.kw-skeleton {
  height: 214px;
  padding: 24px;
  border-radius: 21px;
  background: #ffffff85;
}

.kw-skeleton span {
  display: block;
  width: 100%;
  height: 13px;
  margin-bottom: 22px;
  background: linear-gradient(90deg, #e8edf7 25%, #f4f7fc 50%, #e8edf7 75%);
  background-size: 200% 100%;
  border-radius: 5px;
  /* !important 是为了抵消上方 .kb-workspace :deep(*) 的 animation: none !important */
  animation: kw-skeleton-shimmer 1.6s ease-in-out infinite !important;
}

@keyframes kw-skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .kw-skeleton span {
    animation: none !important;
    background: #e8edf7;
  }
}

.kw-skeleton span:first-child {
  width: 34px;
  height: 34px;
  border-radius: 9px;
}

.kw-skeleton span:nth-child(2) {
  width: 60%;
}

.kw-reading {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px;
}

.kw-reading-nav {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  margin-bottom: 30px;
}

.kw-reading-nav button {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  background: none;
  border: 0;
  color: #8b9ab4;
  font-size: 14px;
}

.kw-reading-nav button:hover {
  color: #536aab;
}

.kw-restoring-hint {
  padding: 4px 0;
  color: #8b9ab4;
  font-size: 13px;
}

.kw-reading-layout {
  display: grid;
  flex: 1;
  min-height: 0;
  grid-template-columns: 205px minmax(0, 1fr);
  grid-template-rows: minmax(0, 1fr);
  gap: 30px;
}

.kw-bookmark {
  padding: 15px 8px;
  min-width: 0;
  min-height: 0;
  overflow-x: hidden;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-width: thin;
}

.kw-bookmark-symbol {
  display: flex;
  align-items: center;
  width: fit-content;
  min-height: 44px;
  margin-bottom: 22px;
}

.kw-bookmark h1 {
  margin: 0 0 12px;
  font-size: 23px;
  font-weight: 500;
  line-height: 1.6;
  color: #4a5a78;
  overflow-wrap: anywhere;
}

.kw-bookmark>p {
  font-size: 13px;
  line-height: 1.9;
  color: #728199;
  margin: 0;
  overflow-wrap: anywhere;
}

.kw-bookmark-count {
  display: flex;
  align-items: baseline;
  gap: 5px;
  padding: 23px 0 18px;
}

.kw-bookmark-count strong {
  font-size: 20px;
  font-weight: 500;
  color: #7f93b7;
}

.kw-bookmark-count span {
  font-size: 13px;
  color: #9daac0;
}

.kw-bookmark-info {
  display: flex;
  flex-direction: column;
  gap: 9px;
  color: #9aa8bf;
  font-size: 13px;
}

.kw-bookmark-info span:first-child {
  display: flex;
  gap: 6px;
  align-items: center;
}

.kw-bookmark-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 9px;
  margin-top: 25px;
}

/* 侧栏操作按钮（编辑信息 / 探索知识图谱 / 刷新文档）沿用 .kw-create-button 的浅蓝描边视觉 */
.kw-bookmark-actions button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 9px 14px;
  border: 1px solid #c6daff;
  border-radius: 12px;
  background: linear-gradient(130deg, #fffdfd, #e6ecfd);
  color: #5a6caa;
  font-size: 13px;
  box-shadow: 0 3px 9px #627bad0d, inset 0 1px 1px #fff;
  white-space: nowrap;
}

.kw-bookmark-actions button:hover {
  background: linear-gradient(130deg, #fffdfd, #e6ecfd);
  box-shadow: 0 5px 15px #627bad1c;
}

.kw-reading-sheet {
  position: relative;
  isolation: isolate;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background: #ffffffd9;
  border: 1px solid #fff;
  border-radius: 25px;
  box-shadow: 0 8px 26px #556c9d09;
}

.kw-detail-error {
  padding: 14px 20px;
  font-size: 12px;
  color: #a67753;
}

.kw-detail-error button {
  border: 0;
  background: none;
  color: inherit;
  text-decoration: underline;
}

.kw-reading-sheet :deep(.knowledge-detail-section) {
  flex: 1;
  padding: 24px;
  height: auto;
  min-height: 0;
  overflow: hidden;
  border-radius: 25px;
  background: transparent;
  box-shadow: none;
}

.kw-reading-sheet :deep(.detail-header),
.kw-reading-sheet :deep(.list-header) {
  flex-shrink: 0;
}

.kw-reading-sheet :deep(.detail-header) {
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 25px;
}

.kw-reading-sheet :deep(.detail-title) {
  font-size: 15px;
  font-weight: 500;
  color: #637694;
}

.kw-reading-sheet :deep(.detail-actions) {
  gap: 8px;
  flex-wrap: wrap;
  max-width: 100%;
}

/* 搜索文档输入框：与相邻的上传文档按钮 / 新建知识库按钮统一为同一套浅蓝描边视觉；
   align-self: stretch 让高度自动跟随同行按钮，无需硬编码 */
.kw-reading-sheet :deep(.custom-search-wrapper) {
  align-self: stretch;
  height: auto;
  min-height: 32px;
  width: 160px;
  min-width: 0;
  gap: 7px;
  padding: 0 12px;
  border: 1px solid #d8e3fb;
  border-radius: 12px;
  background: linear-gradient(130deg, #fffdfd, #f2f6fe);
  box-shadow: inset 0 1px 1px #fff;
}

.kw-reading-sheet :deep(.custom-search-wrapper:hover) {
  border-color: #c6daff;
  background: linear-gradient(130deg, #fffdfd, #eaf0fd);
}

.kw-reading-sheet :deep(.custom-search-wrapper:focus-within) {
  border-color: #a9c4ff;
  background: #fff;
  box-shadow: 0 3px 9px #627bad14, inset 0 1px 1px #fff;
}

.kw-reading-sheet :deep(.search-icon) {
  margin-right: 0;
  font-size: 12px;
  color: #93a3c0;
}

.kw-reading-sheet :deep(.custom-input) {
  font-size: 12px;
  color: #414e69;
}

.kw-reading-sheet :deep(.custom-input::placeholder) {
  color: #a4aec0;
}

/* 上传文档按钮沿用 .kw-create-button（新建知识库）的同一套视觉规范，
   这里逐项覆盖 .action-btn / .upload-doc-btn 的全局样式（border: none、font-weight: 500、height: 32px 等） */
.kw-reading-sheet :deep(.action-btn.upload-doc-btn) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  height: auto;
  padding: 9px 16px;
  border: 1px solid #c6daff;
  border-radius: 12px;
  background: linear-gradient(130deg, #fffdfd, #e6ecfd);
  color: #5a6caa;
  font-size: 13px;
  font-weight: normal;
  box-shadow: 0 3px 9px #627bad0d, inset 0 1px 1px #fff;
  white-space: nowrap;
}

.kw-reading-sheet :deep(.action-btn.upload-doc-btn:hover) {
  background: linear-gradient(130deg, #fffdfd, #e6ecfd);
  box-shadow: 0 5px 15px #627bad1c;
}

/* 批量处理按钮组沿用上传文档按钮的同一套浅蓝描边视觉（描边 #c6daff、12px 圆角、渐变底、同款阴影）。
   容器 align-self: stretch + 内部按钮 height: auto，高度自动跟随同行的上传文档按钮，无需硬编码；
   宽度沿用 KBDetail 的原值（114px / 38px）不在此处改动 */
.kw-reading-sheet :deep(.bulk-group) {
  align-self: stretch;
  border: 1px solid #c6daff;
  border-radius: 12px;
  background: linear-gradient(130deg, #fffdfd, #e6ecfd);
  box-shadow: 0 3px 9px #627bad0d, inset 0 1px 1px #fff;
}

.kw-reading-sheet :deep(.bulk-group:hover) {
  box-shadow: 0 5px 15px #627bad1c;
}

.kw-reading-sheet :deep(.bulk-btn-origin),
.kw-reading-sheet :deep(.bulk-btn) {
  align-self: stretch;
  height: auto;
  background: transparent;
  color: #5a6caa;
  font-size: 12px;
  font-weight: normal;
}

.kw-reading-sheet :deep(.bulk-btn-origin) {
  gap: 7px;
}

/* 关闭图标（CloseOutlined）字形撑满 em 框，同为 13px 时看着比下载 / 删除图标大，单独收到 11px 取平视觉体量；
   字形在 em 框内偏上，用 transform 下移 1px 与按钮中线对齐（不占布局，也不影响 width 收展过渡） */
.kw-reading-sheet :deep(.bulk-btn-origin.compact .anticon) {
  font-size: 11px;
  transform: translateY(1px);
}

/* hover 用比渐变底色更深的浅蓝铺底，保证在浅蓝渐变上有可感知的反馈；
   :not([disabled]) 是为了不和 KBDetail 里 disabled 态的透明背景规则抢优先级 */
.kw-reading-sheet :deep(.bulk-btn-origin:hover:not([disabled])),
.kw-reading-sheet :deep(.bulk-btn:hover:not([disabled])) {
  background: #d5e2fa;
}

/* 删除按钮保留红色系 hover，优先级高于上面的通用规则 */
.kw-reading-sheet :deep(.bulk-btn.danger:hover:not([disabled])) {
  background: #fbdada;
  color: #dc2626;
}

.kw-reading-sheet :deep(.list-header) {
  flex-wrap: wrap;
  gap: 10px;
}

/* 文档列表工具条：字号回升到与侧栏一致的 12-13px（标题略大以保留层级） */
.kw-reading-sheet :deep(.list-title) {
  color: #8a9ab4;
  font-size: 13px;
}

.kw-reading-sheet :deep(.document-count),
.kw-reading-sheet :deep(.sort-label) {
  color: #a2aec2;
  font-size: 12px;
}

.kw-reading-sheet :deep(.document-items) {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior-y: contain;
  scrollbar-width: thin;
  scrollbar-color: #d6deed transparent;
  gap: 12px;
}

/* 工作区列表比独立知识库页更紧凑：去掉全局 84px 的固定行高，压缩内边距与两行文字高度 */
.kw-reading-sheet :deep(.document-item) {
  flex-shrink: 0;
  padding: 9px 18px;
  min-height: 0;
  contain-intrinsic-size: 58px;
  border: 0;
  border-bottom: 1px solid #edf1f8;
  border-radius: 0;
  box-shadow: none;
  background: transparent;
}

.kw-reading-sheet :deep(.doc-name-row) {
  min-height: 20px;
}

.kw-reading-sheet :deep(.doc-meta-wrapper) {
  height: 20px;
}

.kw-reading-sheet :deep(.document-item:hover) {
  background: #f5f8fe;
  border-radius: 12px;
}

.kw-reading-sheet :deep(.doc-name) {
  color: #536784;
  font-size: 13px;
}

.kw-reading-sheet :deep(.doc-meta),
.kw-reading-sheet :deep(.badge-soft) {
  color: #8392ab;
  font-size: 11px;
}

.kw-reading-sheet :deep(.badge-soft) {
  background: #f2f5fa;
}

.kw-reading-sheet :deep(.doc-icon-img) {
  width: 30px;
  height: 34px;
}

.kw-reading-sheet :deep(.doc-foot) {
  display: none;
}

.kw-reading-sheet :deep(.empty-icon-ring) {
  background: #f0f4fc;
  box-shadow: none;
  color: #a3b2ce;
}

@media (max-width:700px) {
  .kw-reading-layout {
    grid-template-rows: auto minmax(0, 1fr);
  }

  .kw-bookmark {
    max-height: 30vh;
  }
}

@media (min-width:1500px) {
  .kw-library {
    padding-top: 45px;
  }

  .kw-shelf {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width:1100px) {
  .kw-library {
    --kw-side-pad: 12px;
    padding: 25px var(--kw-side-pad) 16px;
  }

  .kw-reading {
    padding: 22px 8px;
  }

  .kw-reading-layout {
    grid-template-columns: 170px minmax(0, 1fr);
    gap: 20px;
  }

  .kw-reading-sheet :deep(.knowledge-detail-section) {
    padding: 20px;
  }
}

@media (max-width:700px) {
  .kw-library {
    --kw-side-pad: 8px;
    padding: 18px var(--kw-side-pad);
  }

  .kw-intro h1 {
    font-size: 30px;
  }

  .kw-intro p {
    font-size: 11px;
  }

  .kw-search-dock {
    padding: 15px 12px 10px;
    margin-bottom: 28px;
    border-radius: 20px;
  }

  .kw-dock-bottom {
    align-items: flex-start;
    flex-direction: column;
    gap: 10px;
    margin-top: 12px;
  }

  .kw-dock-count {
    padding-left: 8px;
    font-size: 11px;
  }

  .kw-shelf-toolbar {
    flex-wrap: wrap;
    gap: 12px;
    margin-bottom: 18px;
  }

  .kw-shelf-actions {
    width: 100%;
  }

  .kw-create-button {
    margin-left: auto;
  }

  .kw-shelf {
    gap: 25px;
  }

  .kw-reading-layout {
    grid-template-columns: minmax(0, 1fr);
    gap: 18px;
  }

  .kw-reading-nav {
    margin-bottom: 10px;
  }

  .kw-bookmark {
    display: grid;
    grid-template-columns: auto minmax(0, 1fr);
    gap: 8px 15px;
    padding: 5px 0;
  }

  .kw-bookmark-symbol {
    width: auto;
    margin: 0;
    grid-row: span 2;
  }

  .kw-bookmark h1 {
    font-size: 20px;
    margin: 0;
  }

  .kw-bookmark>p {
    grid-column: 2;
    font-size: 12px;
  }

  .kw-bookmark-count {
    grid-column: 1/-1;
    padding: 6px 0;
  }

  .kw-bookmark-count strong {
    font-size: 18px;
  }

  .kw-bookmark-info {
    grid-column: 1/-1;
    flex-direction: row;
    flex-wrap: wrap;
  }

  .kw-bookmark-actions {
    grid-column: 1/-1;
    flex-direction: row;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 8px;
  }

  .kw-reading-sheet :deep(.detail-actions) {
    flex-basis: 100%;
  }

  .kw-reading-sheet :deep(.document-item) {
    flex-wrap: wrap;
  }

  .kw-reading-sheet :deep(.doc-actions) {
    margin-left: auto;
  }
}
</style>

<style>
/* Compositor-only travel layers, outside the clipped document scroller. */
.kb-workspace > .kw-travelling-paper { position: absolute; z-index: 9; pointer-events: none; transform-origin: top left; will-change: transform, opacity; border: 1px solid #dce5f4; border-radius: 7px 13px 7px 7px; background: linear-gradient(145deg,#fff,#f3f6fc); box-shadow: 0 5px 14px #536b9710; }
.kb-workspace > .kw-travelling-paper::after { content: ''; position: absolute; left: 18px; top: 22px; width: 45%; height: 18px; opacity: .45; background: repeating-linear-gradient(to bottom,#c8d5eb 0 2px,transparent 2px 9px); }

/* 复刻 antd 的 antCheckboxEffect（其真实名称带 cssinjs hash，静态 CSS 无法引用），
   供上方 .doc-check .ant-checkbox-checked::after 的选中波纹使用；放在非 scoped 块里避免被改写名称 */
@keyframes kwCheckboxEffect {
  0% { transform: scale(1); opacity: .5; }
  100% { transform: scale(1.6); opacity: 0; }
}
</style>
