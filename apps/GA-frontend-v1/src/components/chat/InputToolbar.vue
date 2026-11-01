<template>
  <transition name="poker-slide">
    <div class="input-toolbar" v-if="effectiveVisible" :class="{ 'has-expanded-panel': isTodoExpanded && currentMainMode === 'todo' && todoList && todoList.length > 0 }">
      <transition name="panel-slide">
        <div class="todo-list-panel" ref="todoListPanelRef" v-if="isTodoExpanded && currentMainMode === 'todo' && todoList && todoList.length > 0">
          <div v-for="(todo, index) in todoList" :key="index" class="todo-list-item" :class="[todo.status, { 'selected': selectedTodo && selectedTodo === todo }]" @click="selectTodo(todo)">
            <span style="opacity: 0.5;">{{ index + 1 }}.</span>
            <span>{{ todo.content }}</span>
          </div>
        </div>
      </transition>

      <div class="toolbar-main-row">
        <transition name="toolbar-fade" mode="out-in">
          <div v-if="currentMainMode === 'compression'" class="toolbar-compression-panel" key="compression">
            <span v-if="isCompressingContext" class="compression-spinner" aria-hidden="true"></span>
            <img
              v-else
              :src="compressionUnselectedIcon"
              class="toolbar-compression-inline-icon"
              alt="Compression"
            />
            <span class="toolbar-compression-text">{{ compressionPrimaryText }}</span>
            <span v-if="compressionSecondaryText" class="toolbar-compression-divider">·</span>
            <span v-if="compressionSecondaryText" class="toolbar-compression-meta">{{ compressionSecondaryText }}</span>
          </div>

          <div v-else-if="currentMainMode === 'artifact'" class="artifact-history-row" key="artifact">
            <div class="artifact-history-label" v-if="!isOrchestratorMode">CANVAS</div>
            <div v-if="artifacts && artifacts.length > 0" class="artifact-list-container">
              <div class="scroll-mask mask-left" :class="{ visible: showLeftMask }" @click="scrollLeft">
                <div class="scroll-btn">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="15 18 9 12 15 6"></polyline>
                  </svg>
                </div>
              </div>
              <div class="artifact-list" ref="artifactListRef" @scroll="handleScroll" @wheel.passive.stop="handleWheel">
                <button
                  v-for="art in artifacts"
                  :key="art.id"
                  :data-id="art.id"
                  class="artifact-mini-btn"
                  :class="{ 'active': activeArtifactId === art.id }"
                  @click="handleArtifactClick(art, $event)"
                  :title="art.title"
                >
                  <div class="artifact-icon-wrapper" v-if="art.type === 'image' && art.url">
                    <img :src="art.url" class="artifact-icon-img" />
                  </div>
                  <div class="artifact-icon-wrapper" v-else>
                    <span v-html="getArtifactIcon(art.type)" class="artifact-icon-svg"></span>
                  </div>
                  <span class="artifact-mini-title">{{ art.title }}</span>
                </button>
              </div>
              <div class="scroll-mask mask-right" :class="{ visible: showRightMask }" @click="scrollRight">
                <div class="scroll-btn">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                </div>
              </div>
            </div>
            <div v-else class="artifact-empty-placeholder"></div>
          </div>

          <div v-else-if="currentMainMode === 'stage'" class="toolbar-stage-info" key="stage">
            <span class="stage-label">执行阶段:</span>
            <div class="stage-content-wrapper">
              <transition name="slide-up" mode="out-in">
                <span :key="currentStage" class="stage-content">{{ currentStage }}</span>
              </transition>
            </div>
          </div>

          <div v-else-if="currentMainMode === 'todo' && displayTodo" class="toolbar-stage-info toolbar-todo-info" key="todo">
            <span class="stage-label">当前任务:</span>
            <div class="stage-content-wrapper">
              <transition name="slide-up">
                <div :key="displayTodo.content" class="todo-content-group" :class="{ 'clickable': canExpand }" @click="toggleTodoExpand">
                  <span class="stage-content todo-content" :class="displayTodo.status">{{ displayTodo.content }}</span>
                  <button v-if="canExpand" class="input-bar-expand-btn" @click.stop="toggleTodoExpand" :title="isTodoExpanded ? '收起任务清单' : '展开任务清单'">
                    <img :src="isTodoExpanded ? expandIcon : retractIcon" width="13" height="13" />
                  </button>
                </div>
              </transition>
            </div>
          </div>
        </transition>

          <div class="toolbar-actions">
          <div class="toolbar-toggle-group" v-if="availableModes.length > 1">
            <button
              v-if="availableModes.includes('compression')"
              class="toolbar-toggle-btn"
              :class="{ active: currentMainMode === 'compression' }"
              @click="toolbarViewMode = 'compression'"
              title="显示压缩结果"
            >
              <div class="icon-container stage-icon compression-icon-box">
                <img :src="compressionIcon" class="toolbar-icon" :class="{ visible: currentMainMode === 'compression' }" alt="Compression" />
                <img :src="compressionUnselectedIcon" class="toolbar-icon" :class="{ visible: currentMainMode !== 'compression' }" alt="Compression" />
              </div>
            </button>
            <a-tooltip v-if="availableModes.includes('artifact')" placement="top">
              <template #title>显示画布</template>
              <button
                class="toolbar-toggle-btn"
                :class="{ active: currentMainMode === 'artifact' }"
                @click="toolbarViewMode = 'artifact'"
              >
                <div class="icon-container stage-icon canvas-icon-box">
                  <img :src="canvasSelectedToolbarIcon" class="toolbar-icon" :class="{ visible: currentMainMode === 'artifact' }" alt="Canvas" />
                  <img :src="canvasIcon" class="toolbar-icon" :class="{ visible: currentMainMode !== 'artifact' }" alt="Canvas" />
                </div>
              </button>
            </a-tooltip>
            <button
              v-if="availableModes.includes('stage')"
              class="toolbar-toggle-btn"
              :class="{ active: currentMainMode === 'stage' }"
              @click="toolbarViewMode = 'stage'"
              title="显示执行阶段"
            >
              <div class="icon-container stage-icon">
                <img :src="stageIcon" class="toolbar-icon" :class="{ visible: currentMainMode === 'stage' }" alt="Stage" />
                <img :src="stageUnselectedIcon" class="toolbar-icon" :class="{ visible: currentMainMode !== 'stage' }" alt="Stage" />
              </div>
            </button>
            <a-tooltip v-if="availableModes.includes('todo')" placement="top">
              <template #title>显示任务清单</template>
              <button
                class="toolbar-toggle-btn"
                :class="{ active: currentMainMode === 'todo' }"
                @click="toolbarViewMode = 'todo'"
              >
                <div class="icon-container todo-icon">
                  <img :src="todoIcon" class="toolbar-icon" :class="{ visible: currentMainMode === 'todo' }" alt="Todo" />
                  <img :src="todoUnselectedIcon" class="toolbar-icon" :class="{ visible: currentMainMode !== 'todo' }" alt="Todo" />
                </div>
              </button>
            </a-tooltip>
          </div>

          <button class="toolbar-close-btn" @click="closeToolbar">
            <svg width="9" height="9" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M10 2L2 10M2 2L10 10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup lang="ts">
import { ref, watch, computed, nextTick, onMounted, onUnmounted } from 'vue';
import type { Artifact } from '@/utils/artifactParser';
import type { ContextCompressionInfo } from '@/types/mcp';
import stageIcon from '@/assets/image/svg/stage.svg';
import stageUnselectedIcon from '@/assets/image/svg/stage_unselected.svg';
import todoIcon from '@/assets/image/svg/ToDo_List.svg';
import todoUnselectedIcon from '@/assets/image/svg/ToDo_List_unselected.svg';
import canvasIcon from '@/assets/image/svg/canvas.svg';
import canvasSelectedToolbarIcon from '@/assets/image/svg/canvas-selected-toolbar.svg';
import compressionIcon from '@/assets/image/svg/compression.svg';
import compressionUnselectedIcon from '@/assets/image/svg/compression_unselected.svg';
import expandIcon from '@/assets/image/svg/expand.svg';
import retractIcon from '@/assets/image/svg/retract.svg';
import markdownIcon from '@/assets/image/svg/Markdown.svg';
import wordIcon from '@/assets/image/svg/Word.svg';
import excelIcon from '@/assets/image/svg/Excel.svg';
import pdfIcon from '@/assets/image/svg/pdf-icon.svg';
import txtIcon from '@/assets/image/svg/Txt.svg';
import pptIcon from '@/assets/image/svg/PPT.svg';
import jsonIcon from '@/assets/image/svg/json.svg';
import { formatContextTokenCount } from '@/utils/contextMetrics';
import { eventBus } from '@/utils/EventBus';
import { getApiBaseUrl } from '@/utils/RuntimeConfig';

const props = defineProps<{
  currentStage: string;
  currentTodo: any;
  todoList?: any[];
  artifacts?: Artifact[];
  activeArtifactId?: string;
  isOrchestratorMode?: boolean;
  isCompressingContext?: boolean;
  compressionStatusText?: string;
  compressionInfo?: ContextCompressionInfo | null;
}>();

const emit = defineEmits<{
  'visibility-change': [visible: boolean]
  'expand-change': [expanded: boolean]
  'panel-height-change': [height: number]
  'open-artifact': [payload: { code: Artifact['content']; lang: string; id?: string; isComplete?: boolean; title?: string; downloadUrl?: string; autoOpen?: boolean }]
}>();

const getArtifactIcon = (type: string) => {
    const t = (type || '').toLowerCase();
    if (t === 'markdown' || t === 'md') return `<img src="${markdownIcon}" style="width: 14px; height: 14px;" />`;
    if (t === 'docx' || t === 'doc') return `<img src="${wordIcon}" style="width: 14px; height: 14px;" />`;
    if (t === 'pptx' || t === 'ppt') return `<img src="${pptIcon}" style="width: 14px; height: 14px;" />`;
    if (t === 'xlsx' || t === 'xls') return `<img src="${excelIcon}" style="width: 14px; height: 14px;" />`;
    if (t === 'pdf') return `<img src="${pdfIcon}" style="width: 14px; height: 14px;" />`;
    if (t === 'txt' || t === 'text') return `<img src="${txtIcon}" style="width: 14px; height: 14px;" />`;
    
    // SVG strings for others
    if (t === 'mermaid') {
        return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #9333ea"><rect x="9" y="3" width="6" height="6" rx="1"></rect><rect x="3" y="15" width="6" height="6" rx="1"></rect><rect x="15" y="15" width="6" height="6" rx="1"></rect><path d="M12 9v3"></path><path d="M12 12H6v3"></path><path d="M12 12h6v3"></path></svg>`;
    }
    if (t === 'html') {
        return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #ea580c"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`;
    }
    if (t === 'json') {
        return `<img src="${jsonIcon}" style="width: 14px; height: 14px;" />`;
    }

    // Default code icon
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="color: #64748b"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`;
}

const visible = ref(false);
const toolbarViewMode = ref<'artifact' | 'stage' | 'todo' | 'compression'>('artifact');
const isTodoExpanded = ref(false);
const selectedTodo = ref<any>(null);
const todoListPanelRef = ref<HTMLElement | null>(null);
const allowEmptyVisible = ref(false);
/** 首次自动打开工具栏时自动选中第一个 artifact 并触发 Canvas */
const hasAutoOpenedCanvasForCurrentArtifacts = ref(false);

const hasContent = computed(() => {
  const hasArtifacts = !!(props.artifacts && props.artifacts.length > 0);
  return !!props.currentStage || !!props.currentTodo || hasArtifacts || !!props.isCompressingContext || !!props.compressionInfo;
});

const effectiveVisible = computed(() => {
  return visible.value && (hasContent.value || allowEmptyVisible.value);
});

const showCompressionSelector = computed(() => {
  return !!props.isCompressingContext || !!props.compressionInfo;
});

const displayCompressionStatusText = computed(() => {
  if (props.isCompressingContext) {
    return props.compressionStatusText || '正在压缩上下文，请稍候...';
  }

  const info = props.compressionInfo;
  if (!info) {
    return props.compressionStatusText || '';
  }

  const fileSuffix = info.hasCompressedFiles ? '，文档已压缩' : '';
  const keptSuffix = info.keptMessageCount > 0 ? `，保留 ${info.keptMessageCount} 条` : '';
  return `已减少 ${formatContextTokenCount(info.reducedTokens)}，压缩 ${info.compressedMessageCount} 条${keptSuffix}${fileSuffix}`;
});

const compressionPrimaryText = computed(() => {
  if (props.isCompressingContext) {
    return '正在压缩上下文';
  }
  return props.compressionInfo ? '上下文压缩完成' : '上下文压缩';
});

const compressionSecondaryText = computed(() => {
  if (props.isCompressingContext) {
    return props.compressionStatusText || '请稍候...';
  }
  return displayCompressionStatusText.value;
});

// Artifact scroll logic
const artifactListRef = ref<HTMLElement | null>(null);
const showLeftMask = ref(false);
const showRightMask = ref(false);

const checkScroll = () => {
  const el = artifactListRef.value;
  if (!el) return;
  const { scrollLeft, scrollWidth, clientWidth } = el;
  showLeftMask.value = scrollLeft > 0;
  showRightMask.value = scrollLeft + clientWidth < scrollWidth - 1;
};

const handleScroll = () => {
  checkScroll();
};

const handleWheel = (e: WheelEvent) => {
  if (artifactListRef.value) {
    artifactListRef.value.scrollLeft += e.deltaY;
  }
};

const scrollLeft = () => {
  if (artifactListRef.value) {
    artifactListRef.value.scrollBy({ left: -150, behavior: 'smooth' });
  }
};

const scrollRight = () => {
  if (artifactListRef.value) {
    artifactListRef.value.scrollBy({ left: 150, behavior: 'smooth' });
  }
};

const scrollToCenter = (target: HTMLElement) => {
  if (!artifactListRef.value) return;
  
  const container = artifactListRef.value;
  const containerRect = container.getBoundingClientRect();
  const targetRect = target.getBoundingClientRect();
  
  const currentScrollLeft = container.scrollLeft;
  const offset = targetRect.left - containerRect.left - (containerRect.width - targetRect.width) / 2;
  
  container.scrollTo({
    left: currentScrollLeft + offset,
    behavior: 'smooth'
  });
};

// 画布侧只认 http(s) 绝对地址（docx/xlsx/pptx 都靠它拉取文件），相对路径需补上 API base
const toAbsoluteFileUrl = (value: string): string => {
  if (!value || /^https?:\/\//i.test(value)) return value;
  const base = getApiBaseUrl() || '';
  return `${base}${value.startsWith('/') ? value : `/${value}`}`;
};

// 历史消息里的文件常常只保留下载地址，content 会是占位文案；
// 此时必须回退到 url/downloadUrl，否则画布会把占位文案当成文件内容去加载。
const resolveArtifactCode = (art: Artifact): Artifact['content'] => {
  const content = art.content;
  if (content instanceof ArrayBuffer || ArrayBuffer.isView(content)) return content;

  const text = typeof content === 'string' ? content.trim() : '';
  if (text && text !== '无法预览文件内容') return content;

  const link = art.url?.trim() || art.downloadUrl?.trim() || '';
  return link ? toAbsoluteFileUrl(link) : content;
};

const handleArtifactClick = (art: Artifact, e: MouseEvent) => {
  emit('open-artifact', { 
    code: resolveArtifactCode(art), 
    lang: art.type, 
    id: art.id, 
    isComplete: art.isComplete, 
    title: art.title,
    downloadUrl: art.downloadUrl || art.url
  });
  
  const target = e.currentTarget as HTMLElement;
  if (target) {
    scrollToCenter(target);
  }
};

watch(artifactListRef, (el) => {
  if (el) {
    checkScroll();
  }
});

watch(() => props.artifacts, () => {
  nextTick(() => {
    checkScroll();
  });
}, { deep: true });

watch(() => effectiveVisible.value, (val) => {
    if (val) {
        nextTick(checkScroll);
    }
});

// Watch activeArtifactId to scroll to the active button
watch(() => props.activeArtifactId, (newId) => {
  if (newId && artifactListRef.value) {
    nextTick(() => {
      const activeBtn = artifactListRef.value?.querySelector(`[data-id="${newId}"]`) as HTMLElement;
      if (activeBtn) {
        scrollToCenter(activeBtn);
      }
    });
  }
}, { immediate: true });

const emitHeightChange = () => {
  nextTick(() => {
    if (todoListPanelRef.value) {
      const height = todoListPanelRef.value.offsetHeight;
      emit('panel-height-change', height);
    } else {
      emit('panel-height-change', 0);
    }
  });
};

const handleOpenTodoToolbar = (e: CustomEvent) => {
  const todo = e.detail?.todo;
  // 1. 确保工具栏可见
  visible.value = true;
  allowEmptyVisible.value = false;
  // 2. 切换到任务视图
  toolbarViewMode.value = 'todo';
  // 3. 展开任务列表
  isTodoExpanded.value = true;
  // 4. 尝试选中对应的任务
  if (todo && props.todoList) {
    // 尝试查找匹配的任务（内容和状态相同）
    const match = props.todoList.find(t => t.content === todo.content && t.status === todo.status);
    if (match) {
      selectedTodo.value = match;
    } else {
      // 如果没找到精确匹配，直接设置（可能不会高亮，但保留了意图）
      selectedTodo.value = todo;
    }
  }
  emit('expand-change', true);
};

const handleOpenInputToolbar = () => {
  sessionStorage.removeItem('shouldOpenInputToolbar');
  visible.value = true;
  allowEmptyVisible.value = true;
  isTodoExpanded.value = false;
  selectedTodo.value = null;
  // 打开时优先展示“有数据”的视图：画布有产物优先，否则退回任务清单/执行阶段/压缩
  if (props.artifacts && props.artifacts.length > 0) {
    toolbarViewMode.value = 'artifact';
  } else if (displayTodo.value) {
    toolbarViewMode.value = 'todo';
  } else if (props.currentStage) {
    toolbarViewMode.value = 'stage';
  } else if (showCompressionSelector.value) {
    toolbarViewMode.value = 'compression';
  } else {
    toolbarViewMode.value = 'artifact';
  }
  emit('expand-change', false);
};

const handleToggleInputToolbar = () => {
  if (effectiveVisible.value) {
    closeToolbar();
    return;
  }
  handleOpenInputToolbar();
};

const handleRetryCleanup = () => {
  visible.value = false;
  hasAutoOpenedCanvasForCurrentArtifacts.value = false;
};

onMounted(() => {
  window.addEventListener('open-todo-toolbar', handleOpenTodoToolbar as EventListener);
  window.addEventListener('open-input-toolbar', handleOpenInputToolbar as EventListener);
  window.addEventListener('toggle-input-toolbar', handleToggleInputToolbar as EventListener);
  eventBus.on('chat-retry-cleanup', handleRetryCleanup);

  // 检查是否有挂起的打开请求
  if (sessionStorage.getItem('shouldOpenInputToolbar') === 'true') {
    handleOpenInputToolbar();
  }
});

onUnmounted(() => {
  window.removeEventListener('open-todo-toolbar', handleOpenTodoToolbar as EventListener);
  window.removeEventListener('open-input-toolbar', handleOpenInputToolbar as EventListener);
  window.removeEventListener('toggle-input-toolbar', handleToggleInputToolbar as EventListener);
  eventBus.off('chat-retry-cleanup', handleRetryCleanup);
});

const displayTodo = computed(() => {
  return selectedTodo.value || props.currentTodo;
});

const availableModes = computed<Array<'artifact' | 'stage' | 'todo' | 'compression'>>(() => {
  const modes: Array<'artifact' | 'stage' | 'todo' | 'compression'> = [];
  if (showCompressionSelector.value) {
    modes.push('compression');
  }
  if ((props.artifacts && props.artifacts.length > 0) || allowEmptyVisible.value) {
    modes.push('artifact');
  }
  if (props.currentStage) {
    modes.push('stage');
  }
  if (displayTodo.value) {
    modes.push('todo');
  }
  return modes;
});

const currentMainMode = computed<'artifact' | 'stage' | 'todo' | 'compression'>(() => {
  if (availableModes.value.includes(toolbarViewMode.value)) {
    return toolbarViewMode.value;
  }
  return availableModes.value[0] || 'artifact';
});

// Watch currentTodo changes to reset selection if needed, or just let user stay on selection
watch(() => props.currentTodo, (newVal) => {
  if (newVal && newVal !== selectedTodo.value) {
     selectedTodo.value = null;
  }
});

const selectTodo = (todo: any) => {
    selectedTodo.value = todo;
};

const canExpand = computed(() => {
  return props.todoList && props.todoList.length > 1;
});

const closeToolbar = () => {
  visible.value = false;
  isTodoExpanded.value = false;
  selectedTodo.value = null;
  allowEmptyVisible.value = false;
  hasAutoOpenedCanvasForCurrentArtifacts.value = false;
  emit('expand-change', false);
};

const toggleTodoExpand = () => {
  if (canExpand.value) {
    isTodoExpanded.value = !isTodoExpanded.value;
    emit('expand-change', isTodoExpanded.value);
  }
};

watch(
  () => [props.currentStage, props.currentTodo, props.artifacts?.length || 0],
  ([newStage, newTodo, newArtifactCount], [oldStage, oldTodo, oldArtifactCount]) => {
    const hasAnyContent = !!newStage || !!newTodo || newArtifactCount > 0;
    const wasInvisible = !visible.value;
    if (hasAnyContent && wasInvisible) {
      visible.value = true;
      // 工具栏首次出现且有 artifact 时，自动选中第一个并打开 Canvas
      const artifacts = props.artifacts;
      if (
        artifacts &&
        artifacts.length > 0 &&
        !hasAutoOpenedCanvasForCurrentArtifacts.value &&
        toolbarViewMode.value === 'artifact'
      ) {
        hasAutoOpenedCanvasForCurrentArtifacts.value = true;
        const firstArtifact = artifacts[0];
        nextTick(() => {
          emit('open-artifact', {
            code: firstArtifact.content,
            lang: firstArtifact.type,
            id: firstArtifact.id,
            isComplete: firstArtifact.isComplete,
            title: firstArtifact.title,
            autoOpen: true
          });
        });
      }
    }

    // 当内容清空时重置自动打开标记
    if (!hasAnyContent) {
      hasAutoOpenedCanvasForCurrentArtifacts.value = false;
    }

    const stageChanged = newStage !== oldStage;
    const artifactChanged = newArtifactCount !== oldArtifactCount;
    const newTodoObj = newTodo && typeof newTodo === 'object' ? newTodo : null;
    const oldTodoObj = oldTodo && typeof oldTodo === 'object' ? oldTodo : null;
    const todoChanged = !!newTodo && (
      !oldTodo ||
      newTodoObj?.content !== oldTodoObj?.content ||
      newTodoObj?.status !== oldTodoObj?.status
    );

    if (todoChanged) {
      toolbarViewMode.value = 'todo';
    } else if (stageChanged) {
      toolbarViewMode.value = 'stage';
    } else if (artifactChanged && !newStage && !newTodo) {
      toolbarViewMode.value = 'artifact';
    }

    if (!availableModes.value.includes(toolbarViewMode.value)) {
      toolbarViewMode.value = availableModes.value[0] || 'artifact';
    }
  }
);

watch(
  () => props.artifacts,
  (newArtifacts, oldArtifacts) => {
    const count = newArtifacts?.length || 0;
    const oldCount = oldArtifacts?.length || 0;

    if (count === 0) {
      return;
    }

    // 工具栏可见且处于 artifact 模式时，新增 artifact 自动选中最新的并打开 Canvas
    if (
      effectiveVisible.value &&
      currentMainMode.value === 'artifact' &&
      count > oldCount &&
      oldCount > 0
    ) {
      const latestArtifact = newArtifacts![newArtifacts!.length - 1];
      nextTick(() => {
        emit('open-artifact', {
          code: latestArtifact.content,
          lang: latestArtifact.type,
          id: latestArtifact.id,
          isComplete: latestArtifact.isComplete,
          title: latestArtifact.title,
          autoOpen: true
        });
        // 滚动到最新的 mini-btn 并居中
        const newBtn = artifactListRef.value?.querySelector(`[data-id="${latestArtifact.id}"]`) as HTMLElement;
        if (newBtn) {
          scrollToCenter(newBtn);
        }
      });
    }
  },
  { deep: true }
);

watch(currentMainMode, (mode) => {
  if (mode !== 'todo' && isTodoExpanded.value) {
    isTodoExpanded.value = false;
    emit('expand-change', false);
  }
});

// 监听工具栏可见性变化并通知父组件
watch(() => effectiveVisible.value, (val) => {
  emit('visibility-change', val);
}, { immediate: true });

watch(() => props.isCompressingContext, (isCompressing) => {
  if (isCompressing) {
    visible.value = true;
    toolbarViewMode.value = 'compression';
  }
});

watch(() => props.compressionInfo, (info) => {
  if (info) {
    visible.value = true;
    toolbarViewMode.value = 'compression';
  }
});

// 监听影响面板高度的状态变化
watch(
  [() => isTodoExpanded.value, () => currentMainMode.value, () => props.todoList],
  () => {
    emitHeightChange();
  },
  { deep: true, flush: 'post' }
);
</script>

<style scoped>
@import '@/assets/styles/chat-input.css';

.toolbar-fade-enter-active,
.toolbar-fade-leave-active {
  transition: opacity 0.22s ease, transform 0.22s ease;
}

.toolbar-fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.toolbar-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

.icon-container {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stage-icon {
  width: 12px;
  height: 12px;
}

.todo-icon {
  width: 20px;
  height: 20px;
}

.toolbar-icon {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0;
  transform: scale(0.8) rotate(-15deg);
}

.toolbar-icon.visible {
  opacity: 1;
  transform: scale(1) rotate(0deg);
}

.canvas-icon-box {
  width: 16px;
  height: 16px;
}

.compression-icon-box {
  width: 19px;
  height: 19px;
  margin-top: -1px;
}

.toolbar-close-btn svg {
  display: block;
  transform-origin: center;
  transform-box: fill-box;
  transition: transform 0.2s ease;
}

.toolbar-close-btn:hover {
  transform: none;
}

.toolbar-close-btn:hover svg {
  transform: rotate(90deg);
}

.todo-content-group.clickable {
  cursor: pointer;
}

.artifact-history-row {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 10px;
}

.artifact-list-container {
  flex: 1;
  min-width: 0;
  position: relative;
  display: flex;
  align-items: center;
  height: 100%;
  overflow: hidden;
}

.artifact-list {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior: contain;
  padding: 0 4px;
  width: 100%;
  scrollbar-width: none; /* Firefox */
  -ms-overflow-style: none; /* IE/Edge */
}

.artifact-list::-webkit-scrollbar {
  display: none; /* Chrome/Safari/Opera */
}

.scroll-mask {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 60px;
  pointer-events: none;
  z-index: 10;
  transition: opacity 0.2s ease;
  opacity: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.scroll-mask.visible {
  opacity: 1;
  pointer-events: auto;
}

.scroll-btn {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: white;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  color: #64748b;
  transition: all 0.2s;
  z-index: 11;
}

.scroll-btn svg {
  width: 10px;
  height: 10px;
}

.scroll-mask:hover .scroll-btn {
  border-color: #cbd5e1;
  color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
  transform: scale(1.1);
}

.mask-left {
  left: 0;
  background: linear-gradient(to right, rgba(255,255,255,1) 30%, rgba(255,255,255,0.9) 50%, rgba(255,255,255,0) 100%);
  justify-content: flex-start;
  padding-left: 2px;
}

.mask-right {
  right: 0;
  background: linear-gradient(to left, rgba(255,255,255,1) 30%, rgba(255,255,255,0.9) 50%, rgba(255,255,255,0) 100%);
  justify-content: flex-end;
  padding-right: 2px;
}

.artifact-history-label {
  font-size: 10px;
  font-weight: 700;
  color: #9ca3af;
  letter-spacing: 0.08em;
  flex-shrink: 0;
  user-select: none;
}

.toolbar-compression-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  display: inline-flex;
  gap: 8px;
  padding: 6px 12px;
  white-space: nowrap;
  overflow: hidden;
}

.toolbar-compression-text {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.toolbar-compression-inline-icon {
  width: 19px;
  height: 19px;
  flex: 0 0 auto;
  margin-top: -3px;
  margin-right: -4px;
}

.toolbar-compression-meta {
  min-width: 0;
  font-size: 12px;
  color: #64748b;
  overflow: hidden;
  text-overflow: ellipsis;
}

.toolbar-compression-divider {
  color: #cbd5e1;
  flex: 0 0 auto;
}

.compression-spinner {
  width: 12px;
  height: 12px;
  border-radius: 999px;
  border: 1.5px solid rgba(59, 130, 246, 0.18);
  border-top-color: #3b82f6;
  animation: compression-spin 0.9s linear infinite;
  flex: 0 0 auto;
}

@keyframes compression-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.artifact-mini-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 9px;
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
  flex-shrink: 0;
  height: 28px;
  line-height: 1;
}

.artifact-mini-btn:hover {
  border: 1px solid #60a5fa;
  box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
}

.artifact-mini-btn.active {
    border: 1px solid #3b82f6;
    background-color: #eff6ff;
}

.artifact-mini-btn.active:hover {
    border: 1px solid #2563eb;
    background-color: #eff6ff;
}

.artifact-icon-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    margin-left: -3px;
}

.artifact-icon-img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.artifact-icon-svg {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    line-height: 0;
}

.artifact-icon-svg img,
.artifact-icon-svg svg {
    display: block;
}

.artifact-mini-title {
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 12px;
  font-weight: 500;
  line-height: 16px;
  color: #334155;
}
</style>
