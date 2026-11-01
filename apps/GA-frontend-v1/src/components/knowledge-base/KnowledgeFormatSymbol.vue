<template>
  <span v-if="loading && !formats.length" class="kw-format-symbol kw-symbol-loading" role="status" aria-label="正在加载文档格式" aria-busy="true">
    <span class="kw-symbol-placeholder" aria-hidden="true"></span>
  </span>
  <span v-else-if="formats.length" class="kw-format-symbol" role="img" :aria-label="`收录格式：${formatNames}`" :title="formatNames">
    <span v-for="format in formats.slice(0, 3)" :key="format.label" class="kw-symbol-page" :class="`is-${format.kind}`" aria-hidden="true">
      <span class="kw-symbol-label">{{ format.label }}</span>
      <span class="kw-symbol-lines"></span>
    </span>
  </span>
  <span v-else class="kw-empty-symbol" role="img" aria-label="空知识库">
    <span class="kw-symbol-page kw-empty-page" aria-hidden="true">
      <span class="kw-empty-plus"></span>
      <span class="kw-empty-rule"></span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'
const props = withDefaults(defineProps<{ formats?: Array<{ label: string; kind: string }>; loading?: boolean }>(), { formats: () => [], loading: false })
const formatNames = computed(() => props.formats.map(format => format.label).join(' · '))
</script>

<style scoped>
.kw-empty-symbol { position: relative; display: inline-flex; align-items: center; width: 48px; height: 32px; padding-left: 2px; flex-shrink: 0; }
.kw-empty-symbol::before {
  content: ''; position: absolute; left: 6px; top: -5px;
  width: 38px; height: 40px; box-sizing: border-box;
  border: 1px solid #dce4f1; border-radius: 3px 8px 3px 3px;
  background: #edf2fa; transform: rotate(5deg);
}
.kw-format-symbol { display: inline-flex; align-items: center; height: 32px; padding-left: 2px; flex-shrink: 0; }
.kw-symbol-placeholder { display: block; width: 44px; height: 44px; border-radius: 3px 8px 3px 3px; background: #edf1f8; transform: rotate(-5deg); }
.kw-symbol-page {
  --format-ink: #a0a0a0;
  display: flex; flex-direction: column; justify-content: center; gap: 5px;
  box-sizing: border-box; width: 44px; height: 44px; padding: 7px 5px;
  border: 1px solid color-mix(in srgb, var(--format-ink) 25%, white);
  border-radius: 3px 8px 3px 3px;
  background: linear-gradient(145deg, white, color-mix(in srgb, var(--format-ink) 7%, white));
  color: var(--format-ink); box-shadow: 0 2px 4px #5367890a; transform: rotate(-5deg);
}
.kw-symbol-page + .kw-symbol-page { margin-left: -7px; transform: translateY(-2px) rotate(3deg); }
.kw-symbol-page:nth-child(3) { transform: translateY(1px) rotate(9deg); }
.kw-symbol-page.kw-empty-page {
  --format-ink: #8498ba;
  position: relative; align-items: center; gap: 8px;
}
.kw-empty-plus { position: relative; width: 12px; height: 12px; }
.kw-empty-plus::before, .kw-empty-plus::after {
  content: ''; position: absolute; background: currentColor; border-radius: 1px;
}
.kw-empty-plus::before { width: 12px; height: 1px; left: 0; top: 5.5px; }
.kw-empty-plus::after { width: 1px; height: 12px; left: 5.5px; top: 0; }
.kw-empty-rule { width: 16px; height: 1px; background: currentColor; opacity: .3; }
.is-pdf { --format-ink: #e94848; }
.is-word { --format-ink: #2b579a; }
.is-sheet { --format-ink: #217346; }
.is-slides { --format-ink: #d24726; }
.is-image { --format-ink: #4a8dff; }
.is-markdown { --format-ink: #ff7232; }
.kw-symbol-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; font-weight: 600; line-height: 12px; letter-spacing: .1px; }
.kw-symbol-lines { height: 8px; width: 19px; opacity: .35; background: repeating-linear-gradient(to bottom, currentColor 0 1px, transparent 1px 4px); }
/* 表格图标：1px 外框 + 两竖一横分隔线，组成 3 列 2 行的干净网格；
   比 repeating 渐变更清晰，小尺寸下不会因非整除出现缺边、断线 */
.is-sheet .kw-symbol-lines {
  box-sizing: border-box;
  border: 1px solid currentColor;
  border-radius: 1px;
  background:
    linear-gradient(currentColor 0 0) 33% 0 / 1px 100% no-repeat,
    linear-gradient(currentColor 0 0) 67% 0 / 1px 100% no-repeat,
    linear-gradient(currentColor 0 0) 0 50% / 100% 1px no-repeat;
}
.is-slides .kw-symbol-lines, .is-image .kw-symbol-lines { border: 1px solid currentColor; background: linear-gradient(140deg, transparent 45%, currentColor 46% 52%, transparent 53%); }
</style>
