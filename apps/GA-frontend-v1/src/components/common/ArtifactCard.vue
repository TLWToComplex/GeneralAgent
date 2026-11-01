<template>
  <div class="artifact-card" :class="{ 'selected': isSelected, 'has-error': hasError }" @click="handleClick">
    <div class="artifact-icon-box">
      <div v-if="hasError" style="color: #ef4444; display: flex;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
      </div>
      <LoadingOutlined v-else-if="!isComplete" />
      <div v-else class="artifact-icon-content" v-html="decodedIcon"></div>
    </div>
    <div class="artifact-content">
      <div class="artifact-title" :class="{ 'text-error': hasError }">{{ title }}</div>
      <div class="artifact-meta">
        <span class="artifact-type">CANVAS-{{ (lang || 'TEXT').toUpperCase() }}</span>
        <span v-if="hasError" class="status-badge error">
          渲染出错
        </span>
        <span v-else-if="!isComplete" class="status-badge">
          生成中 <LoadingOutlined style="font-size: 10px;" />
        </span>
      </div>
    </div>
    <div class="artifact-action">
      <button v-if="downloadUrl && ((lang || '').toLowerCase() === 'docx')" class="artifact-download" @click="downloadDocx" title="下载文档">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
      </button>
      <button v-if="downloadUrl && ((lang || '').toLowerCase() === 'json')" class="artifact-download" @click="downloadJson" title="下载 JSON">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
      </button>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import { useArtifactStore } from '@/stores/artifactStore';

const props = withDefaults(defineProps<{
  lang?: string;
  code?: string;
  title?: string;
  icon?: string;
  isComplete?: boolean;
  isSelected?: boolean;
  id?: string;
}>(), {
  isComplete: true,
  isSelected: false
});

const emit = defineEmits<{
  (e: 'open-artifact', payload: { code: string; lang: string; id?: string; title?: string }): void
}>();

const artifactStore = useArtifactStore();
const isMapArtifact = computed(() => (props.lang || '').toLowerCase() === 'map');
const hasError = computed(() => {
  if (!props.id) return false;
  return !!artifactStore.getError(props.id);
});

const decodedCode = computed(() => {
  if (!props.code) return '';
  try {
    return decodeURIComponent(props.code);
  } catch {
    return props.code;
  }
});

const downloadUrl = computed(() => {
  const lang = (props.lang || '').toLowerCase();
  if (lang !== 'docx' && lang !== 'json') return '';
  const url = decodedCode.value.trim();
  if (!url) return '';
  const isUrlLike = /^https?:\/\//i.test(url) || url.startsWith('/');
  return isUrlLike ? url : '';
});

const downloadDocx = (e: MouseEvent) => {
  e.stopPropagation();
  if (!downloadUrl.value) return;
  const a = document.createElement('a');
  a.href = downloadUrl.value;
  a.download = `${props.title || 'document'}.docx`;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const downloadJson = (e: MouseEvent) => {
  e.stopPropagation();
  if (!downloadUrl.value) return;
  const a = document.createElement('a');
  a.href = downloadUrl.value;
  a.download = `${props.title || 'data'}.json`;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const decodedIcon = computed(() => {
    if (!props.icon) return '';
    try {
        return decodeURIComponent(props.icon);
    } catch {
        return props.icon;
    }
})

const handleClick = (e: MouseEvent) => {
  e.stopPropagation();
  emit('open-artifact', {
    code: decodedCode.value,
    lang: props.lang || '',
    id: props.id,
    title: props.title || ''
  });
};
</script>

<style scoped>
.artifact-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background-color: white;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
  max-width: 310px;
  min-width: 300px;
  text-align: left;
  box-sizing: border-box;
}

.artifact-card.selected {
  border-color: 1px solid #3b82f6;
  background-color: #eff6ff;
  box-shadow: 0 0 0 1px #3b82f6;
}

.artifact-card:hover {
  box-shadow: 0 8px 25px -8px rgba(0, 0, 0, 0.1), 0 6px 15px -6px rgba(0, 0, 0, 0.05);
  transform: translateY(-1px);
}

.artifact-card.selected:hover {
  border-color: 1px solid #2563eb;
  background-color: #eff6ff;
  box-shadow: 0 0 0 1px #2563eb, 0 8px 25px -8px rgba(0, 0, 0, 0.1);
}

.artifact-icon-box {
  width: 40px;
  height: 40px;
  background-color: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  flex-shrink: 0;
  transition: color 0.2s;
  box-shadow: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  overflow: hidden;
}

.artifact-icon-content {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  line-height: 0;
}

.artifact-icon-content img,
.artifact-icon-content svg {
  width: 24px !important;
  height: 24px !important;
  max-width: 24px !important;
  max-height: 24px !important;
  margin: 0 !important;
  display: block !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  transform: none !important;
}

.artifact-card:hover .artifact-icon-box {
  color: #2563eb;
}

.artifact-content {
  flex: 1;
  min-width: 0;
}

.artifact-title {
  font-size: 0.875rem;
  font-weight: 500;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.artifact-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

.artifact-type {
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.artifact-action {
  color: #94a3b8;
  transition: color 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.artifact-card:hover .artifact-action {
  color: #3b82f6;
}

.artifact-download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: #e0f2fe;
  color: #2563eb;
  cursor: pointer;
  border-radius: 8px;
  transition: background-color 0.2s, border-color 0.2s, color 0.2s, box-shadow 0.2s;
}

.artifact-download:hover {
  background-color: #bfdbfe;
  border-color: #93c5fd;
  color: #1d4ed8;
  box-shadow: 0 6px 14px -8px rgba(37, 99, 235, 0.6);
}

.status-badge {
  font-size: 11px;
  color: #3b82f6;
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 6px;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.artifact-card.has-error {
  border: 1px solid #fecaca;
  background-color: #fef2f2;
}

.artifact-card.has-error:hover {
  border: 1px solid #f87171;
  box-shadow: 0 0 0 1px #f87171, 0 8px 25px -8px rgba(239, 68, 68, 0.1);
}

.artifact-card.selected.has-error {
  border: 1px solid #ef4444;
  background-color: #fef2f2;
  box-shadow: 0 0 0 1px #ef4444;
}

.artifact-card.selected.has-error:hover {
  border: 1px solid #dc2626;
  box-shadow: 0 0 0 1px #dc2626, 0 8px 25px -8px rgba(239, 68, 68, 0.1);
}

.artifact-card.has-error .artifact-icon-box {
  background-color: #fee2e2;
  border-color: #fecaca;
  color: #ef4444;
}

.text-error {
  color: #ef4444 !important;
}

.status-badge.error {
  color: #ef4444;
  background: #fee2e2;
}
</style>
