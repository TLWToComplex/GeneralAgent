<template>
  <div class="word-canvas-editor">
    <div class="word-canvas-toolbar">
      <button class="toolbar-btn" @click="triggerLocalUpload" title="上传本地 DOCX">上传</button>
      <input
        ref="urlInputRef"
        v-model="urlInput"
        type="text"
        class="toolbar-url"
        placeholder="输入 DOCX URL"
        @keyup.enter="handleLoadUrl"
      />
      <button class="toolbar-btn" @click="handleLoadUrl" title="从 URL 加载">加载 URL</button>
      <button class="toolbar-btn" @click="undo" title="撤销">撤销</button>
      <button class="toolbar-btn" @click="redo" title="重做">重做</button>
      <button class="toolbar-btn primary" @click="exportDocx()" title="导出当前文档">导出</button>
      <input ref="fileInputRef" type="file" accept=".docx" class="file-input" @change="handleLocalUpload" />
    </div>
    <div :class="['word-canvas-surface', surfaceClass]">
      <div ref="editorRef" class="word-canvas-host"></div>
      <div v-if="loading" class="word-overlay">正在加载文档...</div>
      <div v-if="error" class="word-error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';
import Editor from '@vue-word/canvas-editor';
import {
  exportEditorToDocx,
  importDocxIntoEditor,
  isUrlLikeDocxSource,
  normalizeDocxFileName
} from '@/services/word/wordAdapter';

type WordSource = string | ArrayBuffer | ArrayBufferView | null | undefined;

const props = defineProps<{
  source?: WordSource;
  artifactId?: string;
  title?: string;
  suspend?: boolean;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
  (e: 'ready'): void;
}>();

const editorRef = ref<HTMLDivElement | null>(null);
const fileInputRef = ref<HTMLInputElement | null>(null);
const urlInputRef = ref<HTMLInputElement | null>(null);
const loading = ref(false);
const error = ref('');
const urlInput = ref('');
const editorInstance = ref<any>(null);
const lastSourceKey = ref('');
const surfaceClass = `word-canvas-surface-${Math.random().toString(16).slice(2)}`;

const normalizedTitle = computed(() => normalizeDocxFileName(props.title || 'document.docx'));

const buildSourceKey = (source: WordSource) => {
  if (!source) return '';
  if (typeof source === 'string') return `url:${source.trim()}`;
  if (source instanceof ArrayBuffer) return `buf:${source.byteLength}`;
  return `view:${source.byteLength}`;
};

const setError = (message: string) => {
  error.value = message;
  emit('error', message);
};

const loadSource = async (source: WordSource, force = false) => {
  const editor = editorInstance.value;
  if (!editor || props.suspend) return;

  if (!source) {
    if (force) {
      editor.command.executeSetValue({ main: [] });
      lastSourceKey.value = '';
    }
    return;
  }

  const sourceKey = buildSourceKey(source);
  if (!force && sourceKey && sourceKey === lastSourceKey.value) return;

  loading.value = true;
  error.value = '';
  try {
    await importDocxIntoEditor(editor, source, normalizedTitle.value);
    lastSourceKey.value = sourceKey;
  } catch (err) {
    const message = err instanceof Error ? err.message : '文档加载失败';
    setError(message);
  } finally {
    loading.value = false;
  }
};

const triggerLocalUpload = () => {
  fileInputRef.value?.click();
};

const handleLocalUpload = async (event: Event) => {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  loading.value = true;
  error.value = '';
  try {
    await importDocxIntoEditor(editorInstance.value!, await file.arrayBuffer(), file.name);
    lastSourceKey.value = `file:${file.name}:${file.size}:${file.lastModified}`;
  } catch (err) {
    const message = err instanceof Error ? err.message : '本地文档导入失败';
    setError(message);
  } finally {
    loading.value = false;
    (event.target as HTMLInputElement).value = '';
  }
};

const handleLoadUrl = async () => {
  const url = urlInput.value.trim();
  if (!url) return;
  if (!isUrlLikeDocxSource(url)) {
    setError('URL 格式不正确');
    return;
  }
  await loadSource(url, true);
};

const exportDocx = async (fileName?: string) => {
  const editor = editorInstance.value;
  if (!editor) return;
  try {
    await exportEditorToDocx(editor, fileName || normalizedTitle.value);
  } catch (err) {
    const message = err instanceof Error ? err.message : '导出失败';
    setError(message);
  }
};

const undo = () => {
  editorInstance.value?.command.executeUndo?.();
};

const redo = () => {
  editorInstance.value?.command.executeRedo?.();
};

onMounted(async () => {
  await nextTick();
  if (!editorRef.value) return;
  editorInstance.value = new Editor(
    editorRef.value,
    { main: [] },
    {
      margins: [100, 120, 100, 120],
      scrollContainerSelector: `.${surfaceClass}`
    }
  );
  emit('ready');
  await loadSource(props.source, true);
});

watch(
  () => props.source,
  async source => {
    if (props.suspend) return;
    await loadSource(source, false);
  }
);

watch(
  () => [props.artifactId, props.suspend],
  async () => {
    if (props.suspend) return;
    await loadSource(props.source, true);
  }
);

onUnmounted(() => {
  editorInstance.value?.destroy();
});

defineExpose({
  exportDocx,
  loadSource,
  focus: () => {
    const container = editorInstance.value?.command.getContainer?.();
    container?.focus?.();
  }
});
</script>

<style scoped>
.word-canvas-editor {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.word-canvas-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid #e2e8f0;
  background: #ffffff;
}

.toolbar-btn {
  border: 1px solid #d0d7de;
  background: #fff;
  color: #334155;
  font-size: 12px;
  line-height: 1;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
}

.toolbar-btn.primary {
  color: #fff;
  background: #2563eb;
  border-color: #1d4ed8;
}

.toolbar-url {
  flex: 1;
  min-width: 160px;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  padding: 7px 10px;
  font-size: 12px;
}

.file-input {
  display: none;
}

.word-canvas-surface {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.word-canvas-host {
  min-height: 100%;
}

.word-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.85);
  color: #475569;
  font-size: 13px;
  z-index: 10;
}

.word-error {
  position: absolute;
  right: 12px;
  bottom: 12px;
  background: #fee2e2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 8px 10px;
  border-radius: 8px;
  font-size: 12px;
  z-index: 11;
}
</style>
