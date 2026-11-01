<template>
  <div class="word-canvas-full-ui">
    <!-- .doc 格式不支持提示 -->
    <div v-if="isDocFormat" class="doc-format-notice">
      <div class="doc-notice-card">
        <div class="doc-notice-icon">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <h3 class="doc-notice-title">不支持编辑 .doc 格式</h3>
        <p class="doc-notice-message">请将文件转换为 .docx 格式后再进行编辑，或切换到"预览"标签页查看。</p>
      </div>
    </div>
    <VueWordEditor
      v-else
      ref="wordRef"
      :source="source"
      :title="title"
      :suspend="suspend"
      :embedded="true"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import VueWordEditor from '@vue-word/index.vue';

type WordSource = string | ArrayBuffer | ArrayBufferView | null | undefined;

const props = defineProps<{
  source?: WordSource;
  title?: string;
  suspend?: boolean;
}>();

const wordRef = ref<any>(null);

/**
 * 检测 ArrayBuffer 是否为 ZIP 格式（.docx 基于 ZIP，.doc 是 CFBF 格式）
 */
const isZipFormat = (buffer: ArrayBuffer | SharedArrayBuffer): boolean => {
  if (buffer.byteLength < 4) return false;
  const view = new Uint8Array(buffer, 0, 4);
  return view[0] === 0x50 && view[1] === 0x4b && view[2] === 0x03 && view[3] === 0x04;
};

const isDocFormat = computed(() => {
  const source = props.source;
  if (!source) return false;
  // 如果是 ArrayBuffer，检测格式
  if (source instanceof ArrayBuffer || ArrayBuffer.isView(source)) {
    const buffer = source instanceof ArrayBuffer ? source : source.buffer.slice(source.byteOffset, source.byteOffset + source.byteLength);
    return !isZipFormat(buffer);
  }
  // 如果是 URL 字符串，从扩展名判断
  if (typeof source === 'string') {
    const lower = source.toLowerCase();
    if (lower.endsWith('.doc') && !lower.endsWith('.docx')) {
      return true;
    }
  }
  return false;
});

const exportDocx = async (fileName?: string) => {
  await wordRef.value?.exportCurrentDocx?.(fileName || 'document.docx');
};

defineExpose({
  exportDocx
});
</script>

<style scoped>
.word-canvas-full-ui {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.doc-format-notice {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(241, 245, 249, 0.95);
  backdrop-filter: blur(4px);
  z-index: 10;
  padding: 24px;
}

.doc-notice-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  max-width: 380px;
  padding: 40px 32px;
  text-align: center;
}

.doc-notice-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
}

.doc-notice-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.doc-notice-message {
  margin: 0;
  font-size: 14px;
  color: #64748b;
  line-height: 1.6;
}
</style>
