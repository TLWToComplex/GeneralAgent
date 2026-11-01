<template>
  <div class="ppt-canvas-full-ui">
    <iframe
      ref="iframeRef"
      class="ppt-iframe"
      :src="embeddedUrl"
      title="PPT Canvas Preview"
      allowfullscreen
    ></iframe>
    <div v-if="error" class="ppt-error">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { normalizePptFileName, resolvePptSourceBuffer, type PptSource } from '@/services/ppt/pptAdapter';
import { createOfficeSourceKey } from '@/utils/officeSourceKey';

type PptCanvasSource = string | ArrayBuffer | ArrayBufferView | null | undefined;

const HOST_SOURCE = 'aisix-host';
const EMBED_SOURCE = 'pptist-embed';
const HOST_LOAD_EVENT = 'ppt-load';
const HOST_CLEAR_EVENT = 'ppt-clear';
const HOST_EXPORT_EVENT = 'ppt-export';
const HOST_SCREENING_EVENT = 'ppt-screening';
const EMBED_READY_EVENT = 'ppt-ready';
const EMBED_LOADED_EVENT = 'ppt-loaded';
const EMBED_ERROR_EVENT = 'ppt-error';

const props = defineProps<{
  source?: PptCanvasSource;
  artifactId?: string;
  title?: string;
  suspend?: boolean;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
  (e: 'ready'): void;
}>();

const iframeRef = ref<HTMLIFrameElement | null>(null);
const loading = ref(true);
const error = ref('');
const iframeReady = ref(false);
const lastSourceKey = ref('');
const loadVersion = ref(0);
const embeddedUrl = '/vendors/vue-ppt/embedded.html';

const normalizedTitle = computed(() => normalizePptFileName(props.title || 'presentation.pptx'));

const buildSourceKey = createOfficeSourceKey();

const postToIframe = (type: string, payload: Record<string, unknown> = {}, transfer: Transferable[] = []) => {
  const target = iframeRef.value?.contentWindow;
  if (!target) {
    console.warn('[PptCanvas] iframe target not ready');
    return;
  }
  target.postMessage(
    {
      source: HOST_SOURCE,
      type,
      ...payload
    },
    window.location.origin,
    transfer
  );
};

const clearError = () => {
  error.value = '';
};

const setError = (message: string) => {
  error.value = message;
  emit('error', message);
};

const loadSource = async (source: PptCanvasSource, force = false) => {
  if (props.suspend || !iframeReady.value) return;

  if (!source) {
    if (force) {
      lastSourceKey.value = '';
      clearError();
      loading.value = false;
      postToIframe(HOST_CLEAR_EVENT, { title: normalizedTitle.value });
    }
    return;
  }

  const sourceKey = buildSourceKey(source);
  if (!force && sourceKey && sourceKey === lastSourceKey.value) return;

  loading.value = true;
  clearError();
  const currentVersion = ++loadVersion.value;

  try {
    const arrayBuffer = await resolvePptSourceBuffer(source as PptSource);
    if (currentVersion !== loadVersion.value) return;

    // URL and typed-view resolution already produces an owned buffer. Only clone
    // a caller-owned ArrayBuffer, since transferring it would detach the source.
    const transferableBuffer = source instanceof ArrayBuffer ? arrayBuffer.slice(0) : arrayBuffer;
    postToIframe(
      HOST_LOAD_EVENT,
      {
        fileName: normalizedTitle.value,
        title: normalizedTitle.value,
        arrayBuffer: transferableBuffer
      },
      [transferableBuffer]
    );
    lastSourceKey.value = sourceKey;
  } catch (err) {
    if (currentVersion !== loadVersion.value) return;
    loading.value = false;
    const message = err instanceof Error ? err.message : '演示文稿加载失败';
    setError(message);
  }
};

const handleWindowMessage = async (event: MessageEvent<Record<string, any>>) => {
  if (event.source !== iframeRef.value?.contentWindow) return;
  if (!event.data || event.data.source !== EMBED_SOURCE) return;

  switch (event.data.type) {
    case EMBED_READY_EVENT:
      iframeReady.value = true;
      emit('ready');
      await loadSource(props.source, true);
      break;
    case EMBED_LOADED_EVENT:
      loading.value = false;
      clearError();
      break;
    case EMBED_ERROR_EVENT:
      loading.value = false;
      setError(typeof event.data.message === 'string' ? event.data.message : '演示文稿加载失败');
      break;
    default:
      break;
  }
};

// Vue batches a file's source/id changes into one import instead of two downloads
// and two competing workspace resets inside the embedded editor.
watch(
  () => [props.source, props.artifactId, props.suspend] as const,
  async ([source, artifactId, suspended], [, previousArtifactId]) => {
    if (suspended) return;
    await loadSource(source, artifactId !== previousArtifactId);
  }
);

onMounted(() => {
  window.addEventListener('message', handleWindowMessage);
});

onUnmounted(() => {
  loadVersion.value++;
  window.removeEventListener('message', handleWindowMessage);
});

defineExpose({
  reloadSource: async () => {
    await loadSource(props.source, true);
  },
  triggerExport: () => {
    postToIframe(HOST_EXPORT_EVENT);
  },
  triggerScreening: (fromStart = false) => {
    postToIframe(HOST_SCREENING_EVENT, { fromStart });
  }
});
</script>

<style scoped>
.ppt-canvas-full-ui {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background: #f8fafc;
}

.ppt-iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: none;
  background: #ffffff;
}

.ppt-error {
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
