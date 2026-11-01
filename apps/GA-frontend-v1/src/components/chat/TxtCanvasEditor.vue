<template>
  <div class="txt-canvas-editor">
    <textarea
      ref="textareaRef"
      v-model="textValue"
      class="txt-editor-textarea"
      wrap="soft"
      spellcheck="false"
      placeholder="TXT 内容为空"
      @input="handleInput"
      @click="updateCursorStatus"
      @keyup="updateCursorStatus"
      @mouseup="updateCursorStatus"
      @select="updateCursorStatus"
      @focus="updateCursorStatus"
    ></textarea>

    <div class="txt-editor-statusbar">
      <div class="txt-editor-statusgroup">
        <span class="txt-editor-statusitem txt-editor-statusitem--linecol">行 {{ cursorLine }}，列 {{ cursorColumn }}</span>
        <span class="txt-editor-statusdivider" aria-hidden="true"></span>
        <span class="txt-editor-statusitem txt-editor-statusitem--chars">{{ charCount }} 个字符</span>
        <span class="txt-editor-statusdivider" aria-hidden="true"></span>
        <span class="txt-editor-statusitem txt-editor-statusitem--mode">纯文本</span>
      </div>

      <div class="txt-editor-statusgroup txt-editor-statusgroup--right">
        <span class="txt-editor-statusdivider" aria-hidden="true"></span>
        <span class="txt-editor-statusitem txt-editor-statusitem--zoom">100%</span>
        <span class="txt-editor-statusdivider" aria-hidden="true"></span>
        <span class="txt-editor-statusitem txt-editor-statusitem--lineending">{{ lineEndingLabel }}</span>
        <span class="txt-editor-statusdivider" aria-hidden="true"></span>
        <div ref="encodingMenuRef" class="txt-editor-encoding">
          <button
            type="button"
            class="txt-editor-encoding-trigger"
            :class="{ 'is-open': isEncodingMenuOpen }"
            title="切换文本编码"
            @click="toggleEncodingMenu"
          >
            {{ currentEncodingLabel }}
          </button>

          <Transition name="txt-encoding-menu">
            <div v-if="isEncodingMenuOpen" class="txt-editor-encoding-menu">
              <button
                v-for="option in encodingOptions"
                :key="option.value"
                type="button"
                class="txt-editor-encoding-option"
                :class="{ 'is-active': selectedEncoding === option.value }"
                @click="selectEncoding(option.value)"
              >
                <span class="txt-editor-encoding-option-label">{{ option.label }}</span>
                <span class="txt-editor-encoding-option-desc">{{ option.description }}</span>
              </button>
            </div>
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue';

type TxtSource = string | ArrayBuffer | ArrayBufferView | null | undefined;
type SupportedEncoding = 'utf-8' | 'utf-16le' | 'utf-16be';
type LineEnding = 'crlf' | 'lf';

const props = defineProps<{
  source?: TxtSource;
}>();

const emit = defineEmits<{
  (e: 'change', value: string): void;
}>();

const encodingOptions: Array<{ value: SupportedEncoding; label: string; description: string }> = [
  { value: 'utf-8', label: 'UTF-8', description: '通用文本编码' },
  { value: 'utf-16le', label: 'UTF-16 LE', description: '小端字节序' },
  { value: 'utf-16be', label: 'UTF-16 BE', description: '大端字节序' }
];

const textareaRef = ref<HTMLTextAreaElement | null>(null);
const encodingMenuRef = ref<HTMLElement | null>(null);
const textValue = ref('');
const selectedEncoding = ref<SupportedEncoding>('utf-8');
const isEncodingMenuOpen = ref(false);
const lineEnding = ref<LineEnding>('crlf');
const cursorLine = ref(1);
const cursorColumn = ref(1);
const originalBinarySource = ref<Uint8Array | null>(null);
const originalTextSource = ref('');
const isDirty = ref(false);

const charCount = computed(() => textValue.value.length);
const currentEncodingLabel = computed(() => (
  encodingOptions.find(option => option.value === selectedEncoding.value)?.label || 'UTF-8'
));
const lineEndingLabel = computed(() => (
  lineEnding.value === 'crlf' ? 'Windows (CRLF)' : 'LF'
));

const toUint8Array = (source: Exclude<TxtSource, string | null | undefined>) => {
  if (source instanceof ArrayBuffer) {
    return new Uint8Array(source);
  }
  return new Uint8Array(source.buffer, source.byteOffset, source.byteLength);
};

const cloneUint8Array = (source: Exclude<TxtSource, string | null | undefined>) => {
  const bytes = toUint8Array(source);
  return new Uint8Array(bytes);
};

const inferLineEnding = (value: string): LineEnding => {
  if (value.includes('\r\n')) return 'crlf';
  if (value.includes('\n') || value.includes('\r')) return 'lf';
  return 'crlf';
};

const normalizeLineEndings = (value: string, target: LineEnding) => {
  const normalized = value.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
  return target === 'crlf' ? normalized.replace(/\n/g, '\r\n') : normalized;
};

const decodeTxtSource = (source: TxtSource, encoding: SupportedEncoding) => {
  if (!source) return '';
  if (typeof source === 'string') return source;

  try {
    return new TextDecoder(encoding).decode(toUint8Array(source));
  } catch {
    return '';
  }
};

const applySourceText = (encoding: SupportedEncoding) => {
  if (originalBinarySource.value) {
    const decoded = decodeTxtSource(originalBinarySource.value, encoding);
    textValue.value = decoded;
    lineEnding.value = inferLineEnding(decoded);
    return;
  }

  textValue.value = originalTextSource.value;
  lineEnding.value = inferLineEnding(originalTextSource.value);
};

const encodeText = (value: string, encoding: SupportedEncoding) => {
  if (encoding === 'utf-8') {
    return new TextEncoder().encode(value);
  }

  const byteLength = value.length * 2 + 2;
  const bytes = new Uint8Array(byteLength);

  if (encoding === 'utf-16le') {
    bytes[0] = 0xff;
    bytes[1] = 0xfe;
    for (let i = 0; i < value.length; i += 1) {
      const code = value.charCodeAt(i);
      const offset = 2 + i * 2;
      bytes[offset] = code & 0xff;
      bytes[offset + 1] = code >> 8;
    }
    return bytes;
  }

  bytes[0] = 0xfe;
  bytes[1] = 0xff;
  for (let i = 0; i < value.length; i += 1) {
    const code = value.charCodeAt(i);
    const offset = 2 + i * 2;
    bytes[offset] = code >> 8;
    bytes[offset + 1] = code & 0xff;
  }
  return bytes;
};

const updateCursorStatus = () => {
  const textarea = textareaRef.value;
  if (!textarea) return;

  const selectionStart = textarea.selectionStart ?? 0;
  const textBeforeCursor = textValue.value.slice(0, selectionStart);
  const lines = textBeforeCursor.split('\n');
  cursorLine.value = lines.length;
  cursorColumn.value = ((lines[lines.length - 1] || '').length) + 1;
};

const closeEncodingMenu = () => {
  isEncodingMenuOpen.value = false;
};

const toggleEncodingMenu = () => {
  isEncodingMenuOpen.value = !isEncodingMenuOpen.value;
};

const selectEncoding = (encoding: SupportedEncoding) => {
  selectedEncoding.value = encoding;
  closeEncodingMenu();
};

const handleClickOutside = (event: MouseEvent) => {
  const target = event.target as Node | null;
  if (!target || !encodingMenuRef.value) return;
  if (!encodingMenuRef.value.contains(target)) {
    closeEncodingMenu();
  }
};

watch(
  () => props.source,
  async source => {
    if (typeof source === 'string' && isDirty.value && source === textValue.value) {
      await nextTick();
      updateCursorStatus();
      return;
    }

    if (source instanceof ArrayBuffer || ArrayBuffer.isView(source)) {
      originalBinarySource.value = cloneUint8Array(source);
      originalTextSource.value = '';
      applySourceText(selectedEncoding.value);
    } else {
      originalBinarySource.value = null;
      originalTextSource.value = decodeTxtSource(source, selectedEncoding.value);
      applySourceText(selectedEncoding.value);
    }

    isDirty.value = false;
    await nextTick();
    updateCursorStatus();
  },
  { immediate: true }
);

watch(selectedEncoding, async encoding => {
  if (!isDirty.value) {
    applySourceText(encoding);
  }

  await nextTick();
  updateCursorStatus();
});

onMounted(() => {
  window.addEventListener('mousedown', handleClickOutside);
});

onUnmounted(() => {
  window.removeEventListener('mousedown', handleClickOutside);
});

const handleInput = () => {
  isDirty.value = true;
  updateCursorStatus();
  emit('change', textValue.value);
};

const downloadTxt = (fileName = 'document.txt') => {
  const normalizedText = normalizeLineEndings(textValue.value, lineEnding.value);
  const encodedContent = encodeText(normalizedText, selectedEncoding.value);
  const blob = new Blob([encodedContent], {
    type: `text/plain;charset=${selectedEncoding.value}`
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

defineExpose({
  downloadTxt,
  focus: () => textareaRef.value?.focus(),
  getText: () => textValue.value,
  getEncoding: () => selectedEncoding.value,
  getLineEnding: () => lineEnding.value
});
</script>

<style scoped>
.txt-canvas-editor {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.txt-editor-textarea {
  width: 100%;
  flex: 1;
  min-height: 0;
  padding: 6px 10px 8px 10px;
  border: none;
  outline: none;
  resize: none;
  box-sizing: border-box;
  background: #ffffff;
  color: #000000;
  font-size: 14px;
  line-height: 1.35;
  font-family: 'Lucida Console', Consolas, 'Courier New', monospace;
  font-weight: 400;
  letter-spacing: 0;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow-x: hidden;
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
  caret-color: #000000;
}

.txt-editor-textarea:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.txt-editor-textarea::placeholder {
  color: #808080;
}

.txt-editor-textarea::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.txt-editor-textarea::-webkit-scrollbar-track {
  background-color: transparent;
}

.txt-editor-textarea::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.txt-editor-textarea:hover::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
}

.txt-editor-textarea::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, 0.25);
}

.txt-editor-statusbar {
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 18px;
  padding: 0 10px;
  border-top: 1px solid #e5e7eb;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  flex-shrink: 0;
}

.txt-editor-statusgroup {
  display: flex;
  align-items: center;
  gap: 0;
  min-width: 0;
  overflow: hidden;
}

.txt-editor-statusgroup--right {
  margin-left: auto;
  justify-content: flex-end;
  overflow: visible;
}

.txt-editor-statusitem {
  white-space: nowrap;
  padding: 0 12px;
  box-sizing: border-box;
  line-height: 30px;
}

.txt-editor-statusitem--linecol {
  min-width: 108px;
}

.txt-editor-statusitem--chars {
  min-width: 88px;
}

.txt-editor-statusitem--mode {
  min-width: 72px;
  text-align: center;
}

.txt-editor-statusitem--zoom {
  min-width: 58px;
  text-align: center;
}

.txt-editor-statusitem--lineending {
  min-width: 146px;
}

.txt-editor-statusdivider {
  width: 1px;
  height: 12px;
  background: #d7dee8;
  flex-shrink: 0;
}

.txt-editor-encoding {
  display: inline-flex;
  align-items: center;
  position: relative;
  min-width: 78px;
}

.txt-editor-encoding-trigger {
  border: none;
  outline: none;
  background: transparent;
  color: #334155;
  font-size: 12px;
  font-family: inherit;
  cursor: pointer;
  padding: 0 12px;
  min-width: 78px;
  text-align: center;
  line-height: 30px;
  transition: color 0.18s ease;
  box-sizing: border-box;
}

.txt-editor-encoding-trigger:hover {
  color: #2563eb;
}

.txt-editor-encoding-menu {
  position: absolute;
  right: 0;
  bottom: calc(100% + 12px);
  min-width: 164px;
  padding: 6px;
  border-radius: 14px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(246, 250, 255, 0.98));
  border: 1px solid rgba(148, 163, 184, 0.22);
  box-shadow:
    0 16px 40px rgba(15, 23, 42, 0.14),
    0 3px 12px rgba(59, 130, 246, 0.08);
  backdrop-filter: blur(14px);
  z-index: 30;
}

.txt-editor-encoding-option {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 2px;
  padding: 9px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.18s ease, transform 0.18s ease, color 0.18s ease;
}

.txt-editor-encoding-option:hover {
  background: rgba(59, 130, 246, 0.08);
}

.txt-editor-encoding-option.is-active {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.14), rgba(96, 165, 250, 0.1));
  box-shadow: inset 0 0 0 1px rgba(96, 165, 250, 0.28);
}

.txt-editor-encoding-option-label {
  color: #0f172a;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}

.txt-editor-encoding-option-desc {
  color: #64748b;
  font-size: 11px;
  line-height: 1.2;
}

.txt-encoding-menu-enter-active,
.txt-encoding-menu-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
  transform-origin: bottom right;
}

.txt-encoding-menu-enter-from,
.txt-encoding-menu-leave-to {
  opacity: 0;
  transform: translateY(4px) scale(0.96);
}
</style>
