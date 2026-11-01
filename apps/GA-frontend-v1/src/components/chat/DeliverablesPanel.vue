<template>
  <div class="deliverables-panel">
    <div class="deliverables-header">
      <div class="deliverables-header-left">
        <div class="deliverables-title">
          <span class="deliverables-title-text">交付面板</span>
          <span v-if="files.length" class="deliverables-count">{{ files.length }} 个文件</span>
        </div>
      </div>
      <div class="deliverables-header-right">
        <button class="deliverables-close" type="button" title="关闭" @click="emit('close')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="deliverables-banner">
      <img class="deliverables-banner-art" :src="bannerIcon" alt="" draggable="false" />
      <div class="deliverables-banner-content">
        <div class="deliverables-banner-texts">
          <p class="deliverables-banner-title">集中管理与预览你生成的文件</p>
          <p class="deliverables-banner-sub">支持多种文件类型，快速预览与下载</p>
        </div>
      </div>
    </div>

    <div class="deliverables-toolbar">
      <div class="deliverables-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="deliverables-tab"
          :class="{ 'is-active': activeTab === tab.value }"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="deliverables-toolbar-right">
        <div class="deliverables-search">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <input v-model="keyword" type="text" placeholder="搜索文件名或内容关键词" />
        </div>
        <button class="deliverables-tool-btn" :disabled="loading" :title="loading ? '加载中' : '刷新'" @click="refresh">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :class="{ 'is-spinning': loading }">
            <path d="M23 4v6h-6"></path>
            <path d="M1 20v-6h6"></path>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"></path>
            <path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
          </svg>
        </button>
      </div>
    </div>

    <div class="deliverables-body">
      <div v-if="loading && files.length === 0" class="deliverables-state">
        <CreativeLoading text="正在加载交付物..." />
      </div>

      <div v-else-if="files.length === 0" class="deliverables-state deliverables-empty">
        <div class="deliverables-empty-icon">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
          </svg>
        </div>
        <p class="deliverables-empty-title">暂无交付物</p>
        <p class="deliverables-empty-sub">对话生成的文档、表格、演示文稿等会出现在这里</p>
      </div>

      <div v-else-if="list.length === 0" class="deliverables-state deliverables-empty">
        <p class="deliverables-empty-title">未找到匹配的文件</p>
        <p class="deliverables-empty-sub">试试切换分类或修改搜索关键词</p>
      </div>

      <div v-else class="deliverables-list">
        <div
          v-for="item in list"
          :key="item.file.path"
          class="deliverable-item"
          :class="{ 'is-previewable': canPreview(item.file) }"
          @click="openPreview(item.file)"
        >
          <div class="deliverable-icon">
            <img v-if="fileIcon(item.file)" :src="fileIcon(item.file)" alt="" />
            <span v-else class="deliverable-icon-fallback">{{ fileExt(item.file.filename) }}</span>
          </div>
          <div class="deliverable-meta">
            <div class="deliverable-name-row">
              <span class="deliverable-name" :title="item.file.filename">{{ item.file.filename }}</span>
              <span class="deliverable-type" :class="`deliverable-type--${item.category.tone}`">{{ item.category.label }}</span>
            </div>
            <div class="deliverable-sub">
              <template v-if="item.sizeText">
                <span class="deliverable-size">{{ item.sizeText }}</span>
                <span class="deliverable-dot">·</span>
              </template>
              <span v-if="item.file.path" class="deliverable-path" :title="item.file.path">{{ item.file.path }}</span>
            </div>
          </div>
          <button class="deliverable-download" :title="'下载 ' + item.file.filename" @click.stop="download(item.file)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="7 10 12 15 17 10"></polyline>
              <line x1="12" y1="15" x2="12" y2="3"></line>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useSandboxFilesStore, type SandboxFile } from '@/stores/sandboxFilesStore';
import { getFileIconSrc } from '@/utils/fileIcon';
import StorageService from '@/utils/StorageService';
import CreativeLoading from '@/components/common/CreativeLoading.vue';
import bannerIcon from '@/assets/image/png/deliverable_banner_icon.png';

defineOptions({
  name: 'DeliverablesPanel'
});

const emit = defineEmits<{
  (e: 'preview', file: SandboxFile): void
  (e: 'close'): void
}>();

const store = useSandboxFilesStore();
const files = computed(() => store.files);
const loading = computed(() => store.loading);

const PREVIEWABLE_EXTS = ['doc', 'docx', 'pdf', 'txt', 'md', 'markdown', 'html', 'htm', 'svg', 'json', 'xls', 'xlsx', 'csv', 'ppt', 'pptx'];

const fileExt = (filename: string) => {
  const clean = (filename || '').split('?')[0].split('#')[0];
  const idx = clean.lastIndexOf('.');
  if (idx < 0 || idx === clean.length - 1) return '';
  return clean.slice(idx + 1).toLowerCase();
};

const fileIcon = (file: SandboxFile) => getFileIconSrc(file.filename);

const canPreview = (file: SandboxFile) => PREVIEWABLE_EXTS.includes(fileExt(file.filename));

const openPreview = (file: SandboxFile) => {
  if (canPreview(file)) {
    emit('preview', file);
    return;
  }
  download(file);
};

const download = (file: SandboxFile) => {
  const href = file.download_url;
  if (!href) return;
  const a = document.createElement('a');
  a.href = href;
  a.download = file.filename;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const refresh = () => {
  const sid = StorageService.getWorkspaceSessionThreadId();
  if (sid) {
    void store.fetchFiles(sid);
  }
};

const formatFileSize = (size: number) => {
  if (!size || size <= 0) return '';
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

type FileTone = 'doc' | 'sheet' | 'slide' | 'pdf' | 'text' | 'json' | 'image' | 'code' | 'zip' | 'other';

interface FileCategory {
  label: string;
  tone: FileTone;
}

const CATEGORY_BY_EXT: Record<string, FileCategory> = {
  doc: { label: 'Word', tone: 'doc' },
  docx: { label: 'Word', tone: 'doc' },
  xls: { label: '表格', tone: 'sheet' },
  xlsx: { label: '表格', tone: 'sheet' },
  csv: { label: '表格', tone: 'sheet' },
  ppt: { label: '演示', tone: 'slide' },
  pptx: { label: '演示', tone: 'slide' },
  pdf: { label: 'PDF', tone: 'pdf' },
  md: { label: '文本', tone: 'text' },
  markdown: { label: '文本', tone: 'text' },
  txt: { label: '文本', tone: 'text' },
  json: { label: 'JSON', tone: 'json' },
  png: { label: '图片', tone: 'image' },
  jpg: { label: '图片', tone: 'image' },
  jpeg: { label: '图片', tone: 'image' },
  gif: { label: '图片', tone: 'image' },
  webp: { label: '图片', tone: 'image' },
  bmp: { label: '图片', tone: 'image' },
  svg: { label: '图片', tone: 'image' },
  js: { label: '代码', tone: 'code' },
  ts: { label: '代码', tone: 'code' },
  py: { label: '代码', tone: 'code' },
  html: { label: '网页', tone: 'code' },
  htm: { label: '网页', tone: 'code' },
  css: { label: '代码', tone: 'code' },
  java: { label: '代码', tone: 'code' },
  zip: { label: '压缩包', tone: 'zip' },
  rar: { label: '压缩包', tone: 'zip' },
  '7z': { label: '压缩包', tone: 'zip' }
};

const fileCategory = (file: SandboxFile): FileCategory => {
  return CATEGORY_BY_EXT[fileExt(file.filename)] || { label: '文件', tone: 'other' };
};

type FilterTab = 'all' | 'doc' | 'slide' | 'sheet' | 'other';

const tabs: { label: string; value: FilterTab }[] = [
  { label: '全部文件', value: 'all' },
  { label: '办公文档', value: 'doc' },
  { label: '电子表格', value: 'sheet' },
  { label: '演示文稿', value: 'slide' },
  { label: '其他文件', value: 'other' }
];

const activeTab = ref<FilterTab>('all');
const keyword = ref('');

const FILTER_GROUP_BY_EXT: Record<string, Exclude<FilterTab, 'all'>> = {
  doc: 'doc',
  docx: 'doc',
  pdf: 'doc',
  txt: 'doc',
  md: 'doc',
  markdown: 'doc',
  ppt: 'slide',
  pptx: 'slide',
  xls: 'sheet',
  xlsx: 'sheet',
  csv: 'sheet'
};

const list = computed(() => {
  const kw = keyword.value.trim().toLowerCase();
  return files.value
    .filter((file) => {
      const group = FILTER_GROUP_BY_EXT[fileExt(file.filename)] || 'other';
      if (activeTab.value !== 'all' && group !== activeTab.value) return false;
      if (kw && !file.filename.toLowerCase().includes(kw)) return false;
      return true;
    })
    .map((file) => ({
      file,
      category: fileCategory(file),
      sizeText: formatFileSize(file.size)
    }));
});

onMounted(() => {
  const sid = StorageService.getWorkspaceSessionThreadId();
  if (sid && (store.loadedSessionId !== sid || store.files.length === 0)) {
    void store.fetchFiles(sid);
  }
});
</script>

<style scoped>
.deliverables-panel {
  height: 100%;
  width: 100%;
  background: #f8fafc;
  display: flex;
  flex-direction: column;
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(0, 0, 0, 0.1);
  box-sizing: border-box;
}

.deliverables-header {
  padding: 0 16px;
  height: 52px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  background: #ffffff;
  flex-shrink: 0;
}

.deliverables-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  flex: 1 1 0;
}

.deliverables-header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  min-width: 0;
  flex: 1 1 0;
  flex-shrink: 0;
}

.deliverables-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.deliverables-title-text {
  font-size: 14px;
  font-weight: 600;
  color: #121212;
}

.deliverables-count {
  font-size: 11px;
  color: #94a3b8;
  background: #f1f5f9;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
}

.deliverables-close {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.deliverables-close:hover {
  background: #f1f5f9;
  color: #334155;
}

.deliverables-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 12px 16px 4px;
}

.deliverables-tabs {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.deliverables-tab {
  border: 1px solid #e2e8f0;
  background: #ffffff;
  padding: 5px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.deliverables-tab:hover {
  border-color: #cbd5e1;
  color: #334155;
}

.deliverables-tab.is-active {
  background: #dbe7fb;
  border-color: #dbe7fb;
  color: #2563eb;
  font-weight: 600;
}

.deliverables-toolbar-right {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
}

.deliverables-search {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  max-width: 220px;
  min-width: 0;
  height: 30px;
  padding: 0 10px;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  color: #94a3b8;
}

.deliverables-search input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 12px;
  color: #334155;
}

.deliverables-search input::placeholder {
  color: #94a3b8;
}

.deliverables-tool-btn {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.15s ease;
}

.deliverables-tool-btn:hover:not(:disabled) {
  background: #eef2f7;
  color: #334155;
}

.deliverables-tool-btn:disabled {
  cursor: default;
  opacity: 0.6;
}

.deliverables-tool-btn svg.is-spinning {
  animation: deliverables-spin 0.9s linear infinite;
}

.deliverables-banner {
  position: relative;
  flex-shrink: 0;
  margin: 12px 16px 0;
  height: 96px;
  border-radius: 12px;
  background: linear-gradient(100deg, #eaf1fe 0%, #dce8fb 100%);
  overflow: hidden;
}

.deliverables-banner-art {
  position: absolute;
  top: 50%;
  right: 40px;
  height: 120%;
  width: auto;
  transform: translateY(-50%);
  pointer-events: none;
  user-select: none;
}

.deliverables-banner-content {
  position: relative;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 30px;
}

.deliverables-banner-texts {
  min-width: 0;
}

.deliverables-banner-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #2563eb;
}

.deliverables-banner-sub {
  margin: 4px 0 0;
  font-size: 12px;
  color: #7b8ba8;
}

.deliverables-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background: #f8fafc;
}

.deliverables-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 24px;
}

.deliverables-empty-icon {
  width: 60px;
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 18px;
  background: #eef4ff;
  color: #94a3b8;
  margin-bottom: 6px;
}

.deliverables-empty-title {
  margin: 0;
  font-size: 14px;
  color: #475569;
  font-weight: 600;
}

.deliverables-empty-sub {
  margin: 0;
  font-size: 12px;
  color: #94a3b8;
  text-align: center;
}

.deliverables-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.deliverables-list::-webkit-scrollbar {
  width: 5px;
}

.deliverables-list::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
}

.deliverable-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.deliverable-item:hover {
  background: #f1f5f9;
}

.deliverable-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9px;
  background: #f8fafc;
  border: 1px solid #eef2f7;
  overflow: hidden;
}

.deliverable-icon img {
  width: 20px;
  height: 20px;
  object-fit: contain;
}

.deliverable-icon-fallback {
  font-size: 9px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.deliverable-meta {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.deliverable-name-row {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.deliverable-name {
  font-size: 13px;
  color: #1f2937;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
  flex-shrink: 1;
}

.deliverable-type {
  flex-shrink: 0;
  font-size: 10px;
  font-weight: 600;
  line-height: 1;
  padding: 3px 6px;
  border-radius: 6px;
  white-space: nowrap;
}

.deliverable-type--doc { color: #2563eb; background: #eff6ff; }
.deliverable-type--sheet { color: #059669; background: #ecfdf5; }
.deliverable-type--slide { color: #ea580c; background: #fff7ed; }
.deliverable-type--pdf { color: #dc2626; background: #fef2f2; }
.deliverable-type--text { color: #64748b; background: #f1f5f9; }
.deliverable-type--json { color: #0d9488; background: #f0fdfa; }
.deliverable-type--image { color: #9333ea; background: #faf5ff; }
.deliverable-type--code { color: #0891b2; background: #ecfeff; }
.deliverable-type--zip { color: #b45309; background: #fffbeb; }
.deliverable-type--other { color: #64748b; background: #f8fafc; }

.deliverable-sub {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 11px;
  color: #94a3b8;
}

.deliverable-size {
  flex-shrink: 0;
  white-space: nowrap;
  color: #94a3b8;
}

.deliverable-dot {
  flex-shrink: 0;
  color: #cbd5e1;
}

.deliverable-path {
  flex: 1;
  min-width: 0;
  font-size: 11px;
  color: #cbd5e1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.deliverable-download {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #94a3b8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
  opacity: 0;
}

.deliverable-item:hover .deliverable-download {
  opacity: 1;
}

.deliverable-download:hover {
  background: #e2e8f0;
  color: #334155;
}

@keyframes deliverables-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>