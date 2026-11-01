<template>
  <div 
    ref="markdownContentRef" 
    :class="['markdown-renderer', {
      'assistant-content': role === 'assistant',
      'tool-content': role === 'tool',
      'user-content': role === 'user'
    }]"
    @click="handleClick"
  >
    <div class="markdown-content" ref="markdownInnerRef"></div>
    
    <simple-image-viewer
      v-model:open="imageViewerOpen"
      :image-url="currentImageUrl"
      :image-alt="currentImageAlt"
    />
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, onUnmounted, ref, watch, createVNode, render, shallowRef } from 'vue';
import MarkdownIt from 'markdown-it';
import katex from 'markdown-it-katex';
import hljs from 'highlight.js/lib/core';
import javascript from 'highlight.js/lib/languages/javascript';
import typescript from 'highlight.js/lib/languages/typescript';
import python from 'highlight.js/lib/languages/python';
import java from 'highlight.js/lib/languages/java';
import c from 'highlight.js/lib/languages/c';
import cpp from 'highlight.js/lib/languages/cpp';
import csharp from 'highlight.js/lib/languages/csharp';
import go from 'highlight.js/lib/languages/go';
import rust from 'highlight.js/lib/languages/rust';
import php from 'highlight.js/lib/languages/php';
import ruby from 'highlight.js/lib/languages/ruby';
import kotlin from 'highlight.js/lib/languages/kotlin';
import swift from 'highlight.js/lib/languages/swift';
import scala from 'highlight.js/lib/languages/scala';
import dart from 'highlight.js/lib/languages/dart';
import sql from 'highlight.js/lib/languages/sql';
import json from 'highlight.js/lib/languages/json';
import bash from 'highlight.js/lib/languages/bash';
import css from 'highlight.js/lib/languages/css';
import xml from 'highlight.js/lib/languages/xml';
import markdown from 'highlight.js/lib/languages/markdown';
import yaml from 'highlight.js/lib/languages/yaml';
import diff from 'highlight.js/lib/languages/diff';
import dockerfile from 'highlight.js/lib/languages/dockerfile';
import powershell from 'highlight.js/lib/languages/powershell';
import ini from 'highlight.js/lib/languages/ini';
import makefile from 'highlight.js/lib/languages/makefile';
import plaintext from 'highlight.js/lib/languages/plaintext';
import 'highlight.js/styles/atom-one-light.css';

hljs.registerLanguage('javascript', javascript);
hljs.registerLanguage('typescript', typescript);
hljs.registerLanguage('python', python);
hljs.registerLanguage('java', java);
hljs.registerLanguage('c', c);
hljs.registerLanguage('cpp', cpp);
hljs.registerLanguage('csharp', csharp);
hljs.registerLanguage('go', go);
hljs.registerLanguage('rust', rust);
hljs.registerLanguage('php', php);
hljs.registerLanguage('ruby', ruby);
hljs.registerLanguage('kotlin', kotlin);
hljs.registerLanguage('swift', swift);
hljs.registerLanguage('scala', scala);
hljs.registerLanguage('dart', dart);
hljs.registerLanguage('sql', sql);
hljs.registerLanguage('json', json);
hljs.registerLanguage('bash', bash);
hljs.registerLanguage('shell', bash);
hljs.registerLanguage('sh', bash);
hljs.registerLanguage('css', css);
hljs.registerLanguage('xml', xml);
hljs.registerLanguage('html', xml);
hljs.registerLanguage('markdown', markdown);
hljs.registerLanguage('md', markdown);
hljs.registerLanguage('yaml', yaml);
hljs.registerLanguage('yml', yaml);
hljs.registerLanguage('diff', diff);
hljs.registerLanguage('dockerfile', dockerfile);
hljs.registerLanguage('docker', dockerfile);
hljs.registerLanguage('powershell', powershell);
hljs.registerLanguage('ini', ini);
hljs.registerLanguage('toml', ini);
hljs.registerLanguage('makefile', makefile);
hljs.registerLanguage('plaintext', plaintext);
hljs.registerLanguage('text', plaintext);
hljs.registerLanguage('txt', plaintext);
import SimpleImageViewer from '@/components/chat/SimpleImageViewer.vue';
import 'katex/dist/katex.min.css';
import { stackMarkdownImages } from '@/utils/imageStack';
import ImageGallery from '@/components/chat/ImageGallery.vue';
import NotificationService from '@/utils/NotificationService';
import { type Artifact, parseArtifactsFromContent, extractFileNameFromSource } from '@/utils/artifactParser';
import { copyText } from '@/utils/clipboard';
import ArtifactCard from './ArtifactCard.vue';
import MarkdownSvg from '@/assets/image/svg/Markdown.svg';
import WordSvg from '@/assets/image/svg/Word.svg';
import PdfSvg from '@/assets/image/svg/pdf-icon.svg';
import TxtSvg from '@/assets/image/svg/Txt.svg';
import ExcelSvg from '@/assets/image/svg/Excel.svg';
import PptSvg from '@/assets/image/svg/PPT.svg';
import JsonSvg from '@/assets/image/svg/json.svg';
import { useThrottleFn } from '@vueuse/core';
import { MarkdownRenderCache } from '@/utils/markdownRenderCache';

interface Props {
  content: string;
  role?: 'user' | 'assistant' | 'tool' | 'system';
  isStreaming?: boolean;
  isReasoning?: boolean;
  activeArtifactId?: string;
  messageId?: string;
  disableArtifacts?: boolean;
  useExternalImageViewer?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  role: 'assistant',
  isStreaming: false,
  isReasoning: false,
  activeArtifactId: '',
  messageId: 'render',
  disableArtifacts: false,
  useExternalImageViewer: false
});

const emit = defineEmits<{
  (e: 'open-artifact', payload: { code: string; lang: string; id?: string; title?: string; isComplete?: boolean; autoOpen?: boolean }): void;
  (e: 'image-click', payload: { imageUrl: string; imageAlt?: string }): void;
}>();

// A stream almost never revisits an old prefix. Retain only the latest result.
const renderedContentCache = new MarkdownRenderCache(1, 1024 * 1024);
const highlightCache = new MarkdownRenderCache();
const codeBlockCache = new MarkdownRenderCache();
const artifactPropsBySlot = new WeakMap<Element, Record<string, unknown>>();
let disposed = false;
let highlightFrame: number | null = null;
const copyStateMap = new Map<string, number>();
const hasActiveCopyStates = ref(false);
const renderedContent = shallowRef(''); 
const autoOpenedDocxIds = new Set<string>();
const autoOpenedPdfIds = new Set<string>();
const autoOpenedMapIds = new Set<string>();

const imageViewerOpen = ref(false);
const currentImageUrl = ref('');
const currentImageAlt = ref('');

const markdownContentRef = ref<HTMLElement | null>(null);
const markdownInnerRef = ref<HTMLElement | null>(null);

const md = new MarkdownIt({
  html: !props.isReasoning && props.role !== 'user',
  linkify: false,
  typographer: true,
  breaks: true,
  highlight: () => ''
}).use(katex, {
  throwOnError: false,
  errorColor: '#cc0000',
  strict: false,
  trust: true,
  fleqn: false,
  leqno: false,
  minRuleThickness: 0.04,
  colorIsTextColor: false,
  maxSize: Infinity,
  maxExpand: 1000,
  globalGroup: false,
  macros: {
    '\\RR': '\\mathbb{R}',
    '\\NN': '\\mathbb{N}',
    '\\ZZ': '\\mathbb{Z}',
    '\\QQ': '\\mathbb{Q}',
    '\\CC': '\\mathbb{C}',
    '\\PP': '\\mathbb{P}',
    '\\EE': '\\mathbb{E}',
    '\\FF': '\\mathbb{F}',
    '\\HH': '\\mathbb{H}',
    '\\implies': '\\Rightarrow',
    '\\iff': '\\Leftrightarrow',
    '\\land': '\\wedge',
    '\\lor': '\\vee',
    '\\lnot': '\\neg',
    '\\argmax': '\\operatorname{argmax}',
    '\\argmin': '\\operatorname{argmin}',
    '\\sgn': '\\operatorname{sgn}',
    '\\Tr': '\\operatorname{Tr}',
    '\\rank': '\\operatorname{rank}',
    '\\diag': '\\operatorname{diag}',
    '\\dd': '\\mathrm{d}',
    '\\dv': '\\frac{\\mathrm{d}#1}{\\mathrm{d}#2}',
    '\\pdv': '\\frac{\\partial#1}{\\partial#2}',
    '\\Var': '\\operatorname{Var}',
    '\\Cov': '\\operatorname{Cov}',
    '\\Corr': '\\operatorname{Corr}'
  }
});

md.inline.ruler.push('footnote_ref', (state, silent) => {
  const max = state.posMax;
  const start = state.pos;
  
  // Check for [^
  if (state.src.charCodeAt(start) !== 0x5B /* [ */) return false;
  if (state.src.charCodeAt(start + 1) !== 0x5E /* ^ */) return false;
  
  // Find closing ]
  let pos = start + 2;
  while (pos < max) {
    if (state.src.charCodeAt(pos) === 0x5D /* ] */) break;
    pos++;
  }
  
  if (pos >= max) return false; // No closing ]
  
  const content = state.src.slice(start + 2, pos);
  if (!/^\d+$/.test(content)) return false; 
  
  if (!silent) {
    const token = state.push('html_inline', '', 0);
    token.content = `<sup class="citation-ref">[${content}]</sup>`;
  }
  
  state.pos = pos + 1;
  return true;
});

watch([() => props.isReasoning, () => props.role], ([isReasoning, role]) => {
  md.set({ html: !isReasoning && role !== 'user' });
});

md.renderer.rules.link_open = (tokens, idx, options, _env, self) => {
  const token = tokens[idx];
  token.attrSet('target', '_blank');
  token.attrSet('rel', 'noopener noreferrer');
  return self.renderToken(tokens, idx, options);
};

const defaultImageRenderer = md.renderer.rules.image || function (tokens, idx, options, _env, self) {
  return self.renderToken(tokens, idx, options);
};

md.renderer.rules.image = (tokens, idx, options, _env, self) => {
  const token = tokens[idx];
  const srcIndex = token.attrIndex('src');
  
  if (!token.attrs) return defaultImageRenderer(tokens, idx, options, _env, self);
  
  const src = token.attrs[srcIndex][1];
  const altIndex = token.attrIndex('alt');
  const alt = altIndex >= 0 && token.attrs ? token.attrs[altIndex][1] : '';
  
  token.attrSet('class', 'clickable-image');
  token.attrSet('data-src', src);
  token.attrSet('data-alt', alt);
  
  return defaultImageRenderer(tokens, idx, options, _env, self);
};

function decodeHtml(html: string): string {
  const textarea = document.createElement('textarea');
  textarea.innerHTML = html;
  return textarea.value;
}

function getArtifactCardIcon(type: string): string {
  
  const normalizedType = (type || '').toLowerCase();

  if (normalizedType === 'markdown' || normalizedType === 'md') {
    return `<img src="${MarkdownSvg}" alt="Markdown" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'docx' || normalizedType === 'doc') {
    return `<img src="${WordSvg}" alt="Word" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'pdf') {
    return `<img src="${PdfSvg}" alt="PDF" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'text' || normalizedType === 'txt') {
    return `<img src="${TxtSvg}" alt="TXT" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'csv' || normalizedType === 'xls' || normalizedType === 'xlsx') {
    return `<img src="${ExcelSvg}" alt="Excel" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'ppt' || normalizedType === 'pptx') {
    return `<img src="${PptSvg}" alt="PPT" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'mermaid') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="3" width="6" height="6" rx="1"></rect><rect x="3" y="15" width="6" height="6" rx="1"></rect><rect x="15" y="15" width="6" height="6" rx="1"></rect><path d="M12 9v3"></path><path d="M12 12H6v3"></path><path d="M12 12h6v3"></path></svg>`;
  }
  if (normalizedType === 'html') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><line x1="3" y1="9" x2="21" y2="9"></line><line x1="9" y1="21" x2="9" y2="9"></line></svg>`;
  }
  if (normalizedType === 'svg') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="14.31" y1="8" x2="20.05" y2="17.94"></line><line x1="9.69" y1="8" x2="21.17" y2="8"></line><line x1="7.38" y1="12" x2="13.12" y2="2.06"></line><line x1="9.69" y1="16" x2="3.95" y2="6.06"></line><line x1="14.31" y1="16" x2="2.83" y2="16"></line><line x1="16.62" y1="12" x2="10.88" y2="21.94"></line></svg>`;
  }
  if (normalizedType === 'json') {
    return `<img src="${JsonSvg}" alt="JSON" style="width: 24px; height: 24px;" />`;
  }
  if (normalizedType === 'url') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>`;
  }

  if (normalizedType === 'map') {
    return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>`;
  }

  return `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`;
}

function setupCodeBlockRenderer(artifacts: Artifact[] = []) {
  md.renderer.rules.fence = (tokens: any, idx: any) => {
    const token = tokens[idx];
    const info = token.info ? token.info.trim() : '';
    let lang = info.split(/\s+/g)[0] || '';
    if (lang === 'md') lang = 'markdown'; // Normalize md to markdown

    const codeKey = `${JSON.stringify(lang)}:${token.content}`;
    if (!lang.startsWith('artifact:')) {
      const cached = codeBlockCache.get(codeKey);
      if (cached !== undefined) return cached;
    }
    const code = decodeHtml(token.content.trim());
    
    if (lang.startsWith('artifact:')) {
      const artifactId = lang.replace('artifact:', '').trim();
      const artifact = artifacts.find(a => a.id === artifactId);
      
      if (artifact) {
          if (props.isReasoning || artifact.isInThinking || props.role === 'user') {
              // Fall back to standard code block
          } else {
              const isComplete = !props.isStreaming ? true : artifact.isComplete;
              
              const type = artifact.type;
              let title = artifact.title || 'Code Snippet';
              let iconSvg = getArtifactCardIcon(type);
              
              if (type === 'mermaid') {
                 title = 'Mermaid';
              } else if (type === 'html') {
                 title = 'Web Preview';
              } else if (type === 'svg') {
                 title = 'SVG Image';
              } else if (type === 'json') {
                 const raw = (artifact.title || artifact.content || '').toString();
                 title = extractFileNameFromSource(raw).replace(/\.json$/i, '').replace(/\s+/g, '') || 'JSON 文件';
              } else if (type === 'markdown') {
                 title = 'Markdown';
              } else if (type === 'docx') {
                 const raw = (artifact.title || artifact.content || '').toString();
                 title = extractFileNameFromSource(raw).replace(/\.docx$/i, '').replace(/\s+/g, '') || 'Word 文档';
              } else if (type === 'pdf') {
                 const raw = (artifact.title || artifact.content || '').toString();
                 title = extractFileNameFromSource(raw).replace(/\.pdf$/i, '').replace(/\s+/g, '') || 'PDF 文档';
              } else if (type === 'map') {
                 title = artifact.title || '地图';
              }

              return `<div class="artifact-card-wrapper">
                <div class="artifact-component-slot"
                  data-lang="${type}" 
                  data-code="${encodeURIComponent(artifact.content as string)}" 
                  data-title="${title}" 
                  data-icon="${encodeURIComponent(iconSvg)}"
                  data-is-complete="${isComplete}"
                  data-id="${artifact.id}"
                ></div>
              </div>`;
          }
      }
    }

    const lineCount = code.split('\n').length;
    let gutter = '';
    for (let i = 1; i <= lineCount; i++) gutter += `<span>${i}</span>`;

    const html = `<div class="code-block-wrapper" data-lang="${lang}" data-code="${encodeURIComponent(code)}">
      <div class="code-block-header">
        <span class="code-file">
          <svg class="code-icon" viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><path d="m8 6-6 6 6 6M16 6l6 6-6 6" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span class="code-language">${lang || 'text'}</span>
        </span>
        <button class="code-copy-button" data-copy-state="ready" aria-label="复制代码">
          <svg class="code-copy-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="9" width="11" height="11" rx="2.5"/><path d="M5 15a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2"/></svg>
          <svg class="code-copied-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m4.5 12.75 6 6 9-13.5"/></svg>
          <span class="code-copy-text">复制</span>
        </button>
      </div>
      <div class="code-body">
        <div class="code-lines">
          <div class="code-gutter" aria-hidden="true">${gutter}</div>
          <pre class="code-pre"><code class="chat-hljs pending-highlight ${lang}">${md.utils.escapeHtml(code)}</code></pre>
        </div>
      </div>
    </div>`;
    // Artifact placeholders depend on streaming/role state; do not cache them here.
    if (!lang.startsWith('artifact:')) codeBlockCache.set(codeKey, html);
    return html;
  };
}

type FenceState = {
  marker: '`' | '~';
  length: number;
};

function parseOpeningFence(line: string): FenceState | null {
  const trimmed = line.trimStart();
  const marker = trimmed[0];
  if (marker !== '`' && marker !== '~') return null;

  let length = 0;
  while (trimmed[length] === marker) length += 1;
  if (length < 3) return null;

  const suffix = trimmed.slice(length);
  if (marker === '`' && suffix.includes('`')) return null;

  return { marker: marker as '`' | '~', length };
}

function parseClosingFence(line: string, activeFence: FenceState): { indent: string; runLength: number; suffix: string } | null {
  const indentLength = line.length - line.trimStart().length;
  const indent = line.slice(0, indentLength);
  const trimmed = line.trimStart();

  if (!trimmed.startsWith(activeFence.marker)) return null;

  let runLength = 0;
  while (trimmed[runLength] === activeFence.marker) runLength += 1;
  if (runLength < activeFence.length) return null;

  return {
    indent,
    runLength,
    suffix: trimmed.slice(runLength)
  };
}

function shouldSplitFenceSuffix(suffix: string): boolean {
  const trimmed = suffix.trimStart();
  if (!trimmed) return false;

  if (/^\[[^\]\n]+?\]\((?:https?:\/\/|\/)/i.test(trimmed)) return true;
  if (/^https?:\/\//i.test(trimmed)) return true;
  if (/^[\u4e00-\u9fff]/.test(trimmed)) return true;
  if (/^(generated file|download|file|link|生成的文件|下载链接|文件|链接)/i.test(trimmed)) return true;

  return false;
}

function normalizeFenceBoundaries(content: string): string {
  if (!content) return '';

  const lines = content.split('\n');
  const normalizedLines: string[] = [];
  let activeFence: FenceState | null = null;

  for (const line of lines) {
    if (!activeFence) {
      normalizedLines.push(line);
      activeFence = parseOpeningFence(line);
      continue;
    }

    const closingFence = parseClosingFence(line, activeFence);
    if (!closingFence) {
      normalizedLines.push(line);
      continue;
    }

    if (!closingFence.suffix.trim()) {
      normalizedLines.push(line);
      activeFence = null;
      continue;
    }

    if (shouldSplitFenceSuffix(closingFence.suffix)) {
      normalizedLines.push(`${closingFence.indent}${activeFence.marker.repeat(closingFence.runLength)}`);
      normalizedLines.push(closingFence.suffix.trimStart());
      activeFence = null;
      continue;
    }

    normalizedLines.push(line);
  }

  return normalizedLines.join('\n');
}

function transformOutsideFences(content: string, transform: (segment: string) => string): string {
  if (!content) return '';

  const lines = content.split('\n');
  const segments: string[] = [];
  let plainLines: string[] = [];
  let fenceLines: string[] = [];
  let activeFence: FenceState | null = null;

  const flushPlain = () => {
    if (plainLines.length === 0) return;
    segments.push(transform(plainLines.join('\n')));
    plainLines = [];
  };

  const flushFence = () => {
    if (fenceLines.length === 0) return;
    segments.push(fenceLines.join('\n'));
    fenceLines = [];
  };

  for (const line of lines) {
    if (!activeFence) {
      const openingFence = parseOpeningFence(line);
      if (openingFence) {
        flushPlain();
        fenceLines.push(line);
        activeFence = openingFence;
        continue;
      }

      plainLines.push(line);
      continue;
    }

    fenceLines.push(line);
    const closingFence = parseClosingFence(line, activeFence);
    if (closingFence && !closingFence.suffix.trim()) {
      flushFence();
      activeFence = null;
    }
  }

  if (fenceLines.length > 0) {
    flushFence();
  }
  if (plainLines.length > 0) {
    flushPlain();
  }

  return segments.join('\n');
}

function compressNewlines(content: string): string {
  if (!content) return '';

  return transformOutsideFences(content, (segment) => {
    let processed = segment.replace(/\n{3,}/g, '\n\n');

    processed = processed.replace(/[:：]\s*\n\s*\n(\S)/g, ':\n$1');

    processed = processed.replace(/[:：]\s*\n\s*\n/g, ':\n');

    processed = processed.replace(/([^:：\n]+[:：][^\n]+)(\n\s*\n)([^:：\n]+[:：])/g, '$1\n$3');

    return processed;
  });
}

function convertBareImageUrls(content: string): string {
  const imgExts = 'png|jpg|jpeg|gif|webp|bmp';
  return transformOutsideFences(content, (segment) => {
    // Match bare image URLs not already inside markdown link/image syntax
    const re = new RegExp(
      `(?<![\\]\\(\\'"])https?://[^\\s<>"')\\]\\n]+?\\.(?:${imgExts})(?:\\?[^\\s<>"')\\]\\n]*?)?(?=[\\s.,;:!?\\)\\n]|$)`,
      'gim'
    );
    return segment.replace(re, (url) => {
      const filename = url.split('/').pop()?.split('?')[0] || 'image';
      return `![${filename}](${url})`;
    });
  });
}

function performRender(content: string) {
  if (!content) return '';

  const cacheKey = `${JSON.stringify([props.role, props.isReasoning, props.isStreaming,
    props.disableArtifacts, props.messageId])}:${content}`;
  const cached = renderedContentCache.get(cacheKey);
  if (cached !== undefined) return cached;

  try {
    const artifacts = props.disableArtifacts || props.isReasoning || props.role === 'tool'
      ? [] : parseArtifactsFromContent(content, props.messageId);
    
    if (props.isReasoning) {
        artifacts.forEach(a => a.isInThinking = true);
    }
    
    setupCodeBlockRenderer(artifacts);
    
    let result: string;
    
    if (props.role === 'tool') {
      try {
        const jsonObj = JSON.parse(content);
        const formattedJson = JSON.stringify(jsonObj, null, 2);
        result = md.render('```json\n' + formattedJson + '\n```');
      } catch (e) {
        result = md.render(content);
      }
    } else {
      let contentWithPlaceholders = content;
      
      if (!props.isReasoning && props.role !== 'user' && !props.disableArtifacts) {
          // 1. 先处理 block-level artifacts（非 URL 类型）
          const blockArtifacts = artifacts.filter(a => 
              ['mermaid', 'html', 'svg', 'markdown', 'docx', 'pdf', 'text', 'csv', 'xlsx', 'pptx', 'json', 'map'].includes(a.type) && 
              !a.isInThinking
          );
          const sortedBlockArtifacts = [...blockArtifacts].sort((a, b) => (b.startIndex || 0) - (a.startIndex || 0));
          
          for (const artifact of sortedBlockArtifacts) {
              if (typeof artifact.startIndex === 'number' && typeof artifact.endIndex === 'number') {
                  const placeholder = `\n\`\`\`artifact:${artifact.id}\n\`\`\`\n`;
                  
                  if (artifact.startIndex >= 0 && artifact.endIndex <= contentWithPlaceholders.length) {
                      contentWithPlaceholders = 
                          contentWithPlaceholders.substring(0, artifact.startIndex) + 
                          placeholder + 
                          contentWithPlaceholders.substring(artifact.endIndex);
                  }
              }
          }

          // 2. 处理 URL 和 image 类型 artifact — 仅在输出完整时才渲染内联 HTML
          const urlArtifacts = artifacts.filter(a => 
              (a.type === 'url' || a.type === 'image') && !a.isInThinking && a.isComplete
          );
          const sortedUrlArtifacts = [...urlArtifacts].sort((a, b) => (b.startIndex || 0) - (a.startIndex || 0));
          
          for (const artifact of sortedUrlArtifacts) {
              if (typeof artifact.startIndex === 'number' && typeof artifact.endIndex === 'number' && typeof artifact.content === 'string') {
                  const displayUrl = artifact.content;
                  let inlineHtml: string;
                  
                  if (artifact.type === 'image') {
                    // Image URL: render as inline image
                    inlineHtml = `<img src="${displayUrl}" alt="${artifact.title}" class="clickable-image inline-chat-image" data-src="${displayUrl}" data-alt="${artifact.title}" loading="lazy" />`;
                  } else {
                    // Regular URL: render as inline code + Canvas open button
                    inlineHtml = `<span class="url-inline-wrapper"><code class="url-inline-code">${md.utils.escapeHtml(displayUrl)}</code><a class="url-open-inline-btn" data-artifact-id="${artifact.id}" data-url="${encodeURIComponent(displayUrl)}" href="javascript:void(0)" title="在 Canvas 中打开"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M11 20H8A4 4 0 0 1 4 16V8A4 4 0 0 1 8 4H16A4 4 0 0 1 20 8V11"/><path d="M12.8 12.8 C12.55 12.15 13.1 11.6 13.75 11.85 L19.05 13.9 C19.9 14.22 19.95 15.42 19.15 15.82 L17.6 16.58 Q17.15 16.8 16.93 17.25 L16.1 18.9 C15.7 19.72 14.5 19.7 14.15 18.82 Z"/></svg></a></span>`;
                  }
                  
                  if (artifact.startIndex >= 0 && artifact.endIndex <= contentWithPlaceholders.length) {
                      contentWithPlaceholders = 
                          contentWithPlaceholders.substring(0, artifact.startIndex) + 
                          inlineHtml + 
                          contentWithPlaceholders.substring(artifact.endIndex);
                  }
              }
          }
      }

      // 3. 处理裸图片 URL，转换为 Markdown 图片语法
      contentWithPlaceholders = convertBareImageUrls(contentWithPlaceholders);

      const normalizedContent = normalizeFenceBoundaries(contentWithPlaceholders.replace(/\r\n?/g, '\n'));
      const processedContent = compressNewlines(normalizedContent);
      result = md.render(processedContent);
    }
    
    if (props.role === 'assistant' && !props.isReasoning) result = stackMarkdownImages(result);
    renderedContentCache.set(cacheKey, result);
    return result;
  } catch (e) {
    console.error('Markdown render error:', e);
    return content;
  }
}

const throttledRender = useThrottleFn((content: string) => {
  // A trailing throttle callback must not overwrite a completed/newer message.
  if (disposed || !props.isStreaming || content !== props.content) return;
  const result = performRender(content);
  renderedContent.value = result;
  
  nextTick(() => {
    updateDom(result);
    queueHighlighting();
    mountArtifactComponents();
    syncCopyButtonStates();
  });
}, 100);

watch([() => props.content, () => props.isStreaming], ([newContent, newIsStreaming]) => {
  if (newIsStreaming) {
    throttledRender(newContent);
  } else {
    const result = performRender(newContent);
    renderedContent.value = result;
    nextTick(() => {
      updateDom(result);
      queueHighlighting(); 
      mountArtifactComponents();
      syncCopyButtonStates();
    });
  }
}, { immediate: true });

function updateDom(newHtml: string) {
  if (disposed || !markdownInnerRef.value) return;
  
  const container = markdownInnerRef.value;

  const tempDiv = document.createElement('div');
  tempDiv.innerHTML = newHtml;
  
  const newNodes = Array.from(tempDiv.children);
  const oldNodes = Array.from(container.children);
  
  const len = Math.max(newNodes.length, oldNodes.length);
  
  for (let i = 0; i < len; i++) {
    const newNode = newNodes[i];
    const oldNode = oldNodes[i];
    
    if (!newNode) {
      if (oldNode) container.removeChild(oldNode);
      continue;
    }
    
    if (!oldNode) {
      container.appendChild(newNode);
      continue;
    }
    
    if (newNode.classList.contains('image-gallery-slot') && oldNode.classList.contains('image-gallery-slot') &&
        newNode.getAttribute('data-images') === oldNode.getAttribute('data-images')) continue;

    if (newNode.classList.contains('artifact-card-wrapper') && 
        oldNode.classList.contains('artifact-card-wrapper')) {
        
        const newSlot = newNode.querySelector('.artifact-component-slot');
        const oldSlot = oldNode.querySelector('.artifact-component-slot');
        
        if (newSlot && oldSlot) {
            Array.from(newSlot.attributes).forEach(attr => {
                if (oldSlot.getAttribute(attr.name) !== attr.value) {
                    oldSlot.setAttribute(attr.name, attr.value);
                }
            });
            Array.from(oldSlot.attributes).forEach(attr => {
                if (!newSlot.hasAttribute(attr.name)) {
                    oldSlot.removeAttribute(attr.name);
                }
            });
            
            continue;
        }
    }

    if (newNode.classList.contains('code-block-wrapper') && 
        oldNode.classList.contains('code-block-wrapper')) {
        
        const newCode = newNode.getAttribute('data-code');
        const oldCode = oldNode.getAttribute('data-code');
        const newLang = newNode.getAttribute('data-lang');
        const oldLang = oldNode.getAttribute('data-lang');
        
        if (newCode === oldCode && newLang === oldLang) {
             continue;
        }
    }
    
    if (newNode.outerHTML !== oldNode.outerHTML) {
        container.replaceChild(newNode, oldNode);
    }
  }
}

const gallerySlots = new Map<Element, string>();
function mountImageGalleries() {
  const container = markdownInnerRef.value;
  if (!container) return;
  for (const slot of gallerySlots.keys()) {
    if (!container.contains(slot)) { render(null, slot); gallerySlots.delete(slot); }
  }
  container.querySelectorAll<HTMLElement>('.image-gallery-slot').forEach(slot => {
    const data = slot.dataset.images || '[]';
    if (gallerySlots.get(slot) === data) return;
    const vnode = createVNode(ImageGallery, {
      images: JSON.parse(data),
      onImageClick: (image: { url: string; name: string }) => {
        emit('image-click', { imageUrl: image.url, imageAlt: image.name });
        if (!props.useExternalImageViewer) {
          currentImageUrl.value = image.url;
          currentImageAlt.value = image.name;
          imageViewerOpen.value = true;
        }
      }
    });
    render(vnode, slot);
    gallerySlots.set(slot, data);
  });
}

let highlightQueue: HTMLElement[] = [];
let isHighlighting = false;

function queueHighlighting() {
  if (!markdownContentRef.value) return;
  
  const pendingBlocks = markdownContentRef.value.querySelectorAll('.pending-highlight');
  const newBlocks = Array.from(pendingBlocks) as HTMLElement[];
  
  if (newBlocks.length === 0) return;

  highlightQueue = newBlocks;
  
  if (!isHighlighting) {
    processHighlightQueue();
  }
}

function processHighlightQueue() {
  highlightFrame = null;
  if (disposed) return;
  if (highlightQueue.length === 0) {
    isHighlighting = false;
    return;
  }

  isHighlighting = true;
  
  const deadline = performance.now() + 10; 
  
  while (highlightQueue.length > 0 && performance.now() < deadline) {
    const block = highlightQueue.shift();
    if (block && document.body.contains(block)) { // 确保元素还在 DOM 中
       highlightSingleBlock(block);
    }
  }

  if (highlightQueue.length > 0) {
    // 如果还有任务，安排在下一帧继续
    highlightFrame = requestAnimationFrame(processHighlightQueue);
  } else {
    isHighlighting = false;
  }
}

function highlightSingleBlock(block: HTMLElement) {
    const wrapper = block.closest('.code-block-wrapper') as HTMLElement;
    if (!wrapper) return;
    
    const lang = wrapper.dataset.lang || '';
    const encodedCode = wrapper.dataset.code || '';
    
    try {
      const code = decodeURIComponent(encodedCode);
      
      // 检查缓存
      const cacheKey = `${lang}:${code}`;
      const cached = highlightCache.get(cacheKey);
      if (cached !== undefined) {
          applyHighlightResult(block, cached);
          return;
      }

      // 同步高亮（因为已经分片了，这里同步执行不会卡死）
      let highlightedCode: string;
      try {
        if (lang && hljs.getLanguage(lang)) {
          highlightedCode = hljs.highlight(code, {language: lang, ignoreIllegals: true} as any).value;
        } else {
          const result = hljs.highlightAuto(code);
          highlightedCode = result.value;
        }
        
        highlightCache.set(cacheKey, highlightedCode);
        applyHighlightResult(block, highlightedCode);

      } catch (e) {
        // Fallback
        block.textContent = code;
        block.classList.remove('pending-highlight');
      }
      
    } catch (e) {
      console.warn('Failed to highlight code block:', e);
      block.classList.remove('pending-highlight');
    }
}

function applyHighlightResult(block: HTMLElement, html: string) {
    // 使用DocumentFragment避免多次DOM操作
    const fragment = document.createDocumentFragment();
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;
    
    while (tempDiv.firstChild) {
      fragment.appendChild(tempDiv.firstChild);
    }
    
    block.innerHTML = '';
    block.appendChild(fragment);
    block.classList.remove('pending-highlight');
}

// 废弃原有的同步全量高亮函数，保留空实现以防有遗漏调用
function highlightPendingCodeBlocks() {
    queueHighlighting();
}

// 处理代码复制按钮点击
function handleCopyButtonClick(e: MouseEvent) {
  const target = e.target as HTMLElement;
  const button = target?.closest?.('.code-copy-button') as HTMLElement | null;
  if (!button) return;
  if (button.dataset.copyState === 'copied') {
    return;
  }
  const codeBlockWrapper = button.closest('.code-block-wrapper');
  if (!codeBlockWrapper) return;
  const codeElement = codeBlockWrapper.querySelector('.code-pre code');
  if (!codeElement) return;
  const textToCopy = codeElement.textContent || '';

  copyText(textToCopy)
    .then((ok: boolean) => {
      if (ok) {
        updateCopyButtonState(button)
      } else {
        NotificationService.error('复制失败，请手动复制')
      }
    })
}

// 更新复制按钮状态
function updateCopyButtonState(button: HTMLElement) {
  setCopyButtonLabel(button, true);
  const wrapper = button.closest('.code-block-wrapper') as HTMLElement | null;
  if (wrapper) {
    const lang = wrapper.dataset.lang || '';
    const encodedCode = wrapper.dataset.code || '';
    let plainCode = '';
    try {
      plainCode = decodeURIComponent(encodedCode);
    } catch {
      plainCode = encodedCode;
    }
    const key = `${lang}:${plainCode}`;
    const expiry = Date.now() + 2000;
    copyStateMap.set(key, expiry);
    hasActiveCopyStates.value = true;
  }
  
  // 设置定时器恢复原始文字
  setTimeout(() => {
    setCopyButtonLabel(button, false);
    const wrapper2 = button.closest('.code-block-wrapper') as HTMLElement | null;
    if (wrapper2) {
      const lang2 = wrapper2.dataset.lang || '';
      const encodedCode2 = wrapper2.dataset.code || '';
      let plainCode2 = '';
      try {
        plainCode2 = decodeURIComponent(encodedCode2);
      } catch {
        plainCode2 = encodedCode2;
      }
      const key2 = `${lang2}:${plainCode2}`;
      copyStateMap.delete(key2);
    }
    let anyActive = false;
    const now = Date.now();
    for (const v of copyStateMap.values()) {
      if (v > now) { anyActive = true; break; }
    }
    hasActiveCopyStates.value = anyActive;
  }, 2000);
}

// 只更新按钮内的文字节点，保留图标 SVG
function setCopyButtonLabel(button: HTMLElement, copied: boolean) {
  button.dataset.copyState = copied ? 'copied' : 'ready';
  const textEl = button.querySelector('.code-copy-text');
  if (textEl) {
    textEl.textContent = copied ? '已复制' : '复制';
  } else {
    button.textContent = copied ? '已复制' : '复制';
  }
}

function syncCopyButtonStates() {
  if (!markdownContentRef.value) return;
  const wrappers = markdownContentRef.value.querySelectorAll('.code-block-wrapper');
  wrappers.forEach(wrapper => {
    const el = wrapper as HTMLElement;
    const lang = el.dataset.lang || '';
    const encodedCode = el.dataset.code || '';
    let plainCode = '';
    try {
      plainCode = decodeURIComponent(encodedCode);
    } catch {
      plainCode = encodedCode;
    }
    const key = `${lang}:${plainCode}`;
    const btn = el.querySelector('.code-copy-button') as HTMLElement | null;
    if (!btn) return;
    setCopyButtonLabel(btn, (copyStateMap.get(key) ?? 0) > Date.now());
  });
}

// 处理点击事件 - 使用事件委托
function handleClick(e: Event) {
  const target = e.target as HTMLElement;
  
  // 处理 URL 行内打开 Canvas 按钮点击（必须在通用链接处理之前）
  if (target && target.closest('.url-open-inline-btn')) {
    e.stopPropagation();
    e.preventDefault();
    const btn = target.closest('.url-open-inline-btn') as HTMLElement;
    if (btn) {
      const artifactId = btn.dataset.artifactId || '';
      let url = '';
      try {
        url = decodeURIComponent(btn.dataset.url || '');
      } catch { url = btn.dataset.url || ''; }
      emit('open-artifact', { code: url, lang: 'url', id: artifactId, title: '网页链接' });
    }
    return;
  }
  
  // 处理链接点击 - 阻止事件冒泡
  if (target && (target.tagName === 'A' || target.closest('a'))) {
    e.stopPropagation();
    return;
  }
  
	// 处理复制按钮点击
	if (target && target.closest('.code-copy-button')) {
		handleCopyButtonClick(e as MouseEvent);
		return;
	}
  
  // 处理图片点击
  if (target && target.classList.contains('clickable-image')) {
    const src = target.getAttribute('data-src');
    const alt = target.getAttribute('data-alt');
    
    if (src) {
      emit('image-click', {
        imageUrl: src,
        imageAlt: alt || '图片'
      });
      if (!props.useExternalImageViewer) {
        if (imageViewerOpen.value) return;
        currentImageUrl.value = src;
        currentImageAlt.value = alt || '图片';
        imageViewerOpen.value = true;
      }
      e.stopPropagation();
    }
    return;
  }
}

function handleArtifactOpen(payload: { code: string; lang: string; id?: string; title?: string; isComplete?: boolean; autoOpen?: boolean }) {
  if (props.disableArtifacts || props.isReasoning || props.role === 'tool') return;
  if (payload.autoOpen && props.isStreaming) return;
  emit('open-artifact', payload);
}

// 挂载 Artifact 卡片组件
function mountArtifactComponents() {
  mountImageGalleries();
  if (!markdownInnerRef.value) return;
  if (props.disableArtifacts || props.isReasoning || props.role === 'tool') return;

  const slots = markdownInnerRef.value.querySelectorAll('.artifact-component-slot');
  slots.forEach(slot => {
    // 注意：我们允许重新挂载以更新属性（props），Vue 的 render 函数会处理 diff

    const cardProps = {
      lang: slot.getAttribute('data-lang') || '',
      code: slot.getAttribute('data-code') || '',
      title: slot.getAttribute('data-title') || '',
      icon: slot.getAttribute('data-icon') || '',
      isComplete: slot.getAttribute('data-is-complete') !== 'false',
      onOpenArtifact: handleArtifactOpen,
      isSelected: slot.getAttribute('data-id') === props.activeArtifactId,
      id: slot.getAttribute('data-id') || ''
    };

    const previousProps = artifactPropsBySlot.get(slot);
    if (!previousProps || Object.entries(cardProps).some(([key, value]) => previousProps[key] !== value)) {
      const vnode = createVNode(ArtifactCard, cardProps);
      render(vnode, slot as Element);
      artifactPropsBySlot.set(slot, cardProps);
    }
    const lang = cardProps.lang.toLowerCase();
    const id = cardProps.id;
    // 不消费自动打开标记；流式结束重新挂载时才允许预览。
    if (props.isStreaming) return;
    if (lang === 'docx' && id && !autoOpenedDocxIds.has(id) && props.role !== 'user' && !props.isReasoning) {
      let decodedCode = cardProps.code;
      try {
        decodedCode = decodeURIComponent(cardProps.code);
      } catch {
        decodedCode = cardProps.code;
      }
      autoOpenedDocxIds.add(id);
      handleArtifactOpen({ code: decodedCode, lang: cardProps.lang, id, title: cardProps.title, isComplete: cardProps.isComplete, autoOpen: true });
    }
    if (lang === 'pdf' && id && !autoOpenedPdfIds.has(id) && props.role !== 'user' && !props.isReasoning) {
      let decodedCode = cardProps.code;
      try {
        decodedCode = decodeURIComponent(cardProps.code);
      } catch {
        decodedCode = cardProps.code;
      }
      autoOpenedPdfIds.add(id);
      handleArtifactOpen({ code: decodedCode, lang: cardProps.lang, id, title: cardProps.title, isComplete: cardProps.isComplete, autoOpen: true });
    }

    if (lang === 'map' && id && !autoOpenedMapIds.has(id) && props.role !== 'user' && !props.isReasoning) {
      let decodedCode = cardProps.code;
      try {
        decodedCode = decodeURIComponent(cardProps.code);
      } catch {
        decodedCode = cardProps.code;
      }
      autoOpenedMapIds.add(id);
      handleArtifactOpen({ code: decodedCode, lang: cardProps.lang, id, title: cardProps.title, isComplete: cardProps.isComplete, autoOpen: true });
    }
  });
}
 

function handlePointerDown(e: PointerEvent) {
  const target = e.target as HTMLElement;
  if (target && target.closest('.code-copy-button')) {
    handleCopyButtonClick(e as any as MouseEvent);
  }
}

// 监听 activeArtifactId 变化
watch(() => props.activeArtifactId, () => {
  if (markdownInnerRef.value) {
    // 重新挂载组件以更新状态
    mountArtifactComponents();
  }
});

// 监听角色变化，清理缓存
watch(() => props.role, () => {
  renderedContentCache.clear();
});

// 添加事件监听器
onMounted(() => {
  nextTick(() => {
    if (markdownContentRef.value) {

      // Remove custom event listener since we handle it via component props
      markdownContentRef.value.addEventListener('pointerdown', handlePointerDown, true);
      
      // Initial render and mount
      updateDom(renderedContent.value);
      nextTick(() => {
        highlightPendingCodeBlocks();
        mountArtifactComponents();
        syncCopyButtonStates();
      });
    }
  });
});

// 移除事件监听器和清理资源
onUnmounted(() => {
  disposed = true;
  for (const slot of gallerySlots.keys()) render(null, slot);
  gallerySlots.clear();
  if (highlightFrame !== null) cancelAnimationFrame(highlightFrame);
  highlightQueue = [];
  if (markdownContentRef.value) {

      // Removed: markdownContentRef.value.removeEventListener('open-artifact', handleArtifactOpen);
      markdownContentRef.value.removeEventListener('pointerdown', handlePointerDown, true);
    }
  
  // 清理缓存（可选，根据需要决定是否保留缓存）
  renderedContentCache.clear();
  highlightCache.clear();
  codeBlockCache.clear();
});
</script>

<style scoped>
:deep(.image-gallery-slot) { display: block; padding: 12px 66px; }
.markdown-renderer {
  position: relative;
}

/* 代码块优化样式 */
.pending-highlight {
  opacity: 0.9;
  transition: opacity 0.15s ease-out;
}

.code-block-wrapper {
  transition: box-shadow 0.2s ease;
}

/* 确保代码内容更新时不会产生布局抖动 */
.chat-hljs {
  font-family: 'Roboto Mono', Menlo, Monaco, Consolas, "Courier New", monospace;
  font-size: 14px;
  line-height: 1.5;
  color: #333;
  white-space: pre;
  display: block;
  width: 100%;
  min-height: 1.5em;
  
  /* 强制字体渲染稳定性 */
  -webkit-font-smoothing: subpixel-antialiased;
  -moz-osx-font-smoothing: auto;
  text-rendering: geometricPrecision;
  font-variant-ligatures: none;
  font-feature-settings: "liga" 0, "kern" 0, "calt" 0;
  font-kerning: none;
  font-synthesis: none;
  font-optical-sizing: none;

  letter-spacing: 0;
  word-spacing: 0;
  text-indent: 0;
  text-align: left;
  
  /* 强制布局稳定性 */
  contain: strict;
  transform: translate3d(0, 0, 0);
  backface-visibility: hidden;
  perspective: 1000px;
  
  /* 禁用所有可能的动画和过渡 */
  transition: none !important;
  animation: none !important;
  
  /* 强制GPU加速和像素对齐 */
  will-change: auto;
  image-rendering: pixelated;
  shape-rendering: crispEdges;
}

/* 代码块容器优化 */
.code-block-wrapper {
  position: relative;
  margin: 16px 0;
  border-radius: 8px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  overflow: hidden;
  
  /* 完全禁用过渡和动画 */
  transition: none !important;
  animation: none !important;
  
  /* 强制布局稳定性 */
  contain: strict;
  transform: translate3d(0, 0, 0);
  backface-visibility: hidden;
  
  /* 确保固定的布局行为 */
  display: block;
  width: 100%;
  box-sizing: border-box;
}

.code-pre {
  margin: 0;
  padding: 16px;
  background: transparent;
  border: none;
  font-size: inherit;
  line-height: inherit;
  color: inherit;
  white-space: pre;
  overflow-x: auto;
  
  /* 强制布局稳定性 */
  contain: strict;
  transform: translate3d(0, 0, 0);
  backface-visibility: hidden;
  
  /* 禁用过渡和动画 */
  transition: none !important;
  animation: none !important;
  
  /* 确保固定的布局行为 */
  display: block;
  width: 100%;
  box-sizing: border-box;
}

/* KaTeX 数学公式样式修复 */
.markdown-content :deep(.katex) {
  font-size: 1.1em !important;
  line-height: normal !important;
  display: inline-block !important;
  vertical-align: -0.25em !important;
  margin: 0 !important;
  padding: 0 !important;
}

.markdown-content :deep(.katex-display) {
  display: block !important;
  text-align: center !important;
  margin: 1em 0 !important;
  padding: 0.5em 0 !important;
  overflow-x: auto !important;
  overflow-y: hidden !important;
}

.markdown-content :deep(.katex-display > .katex) {
  display: inline-block !important;
  text-align: center !important;
  white-space: nowrap !important;
}

.markdown-content :deep(.katex .base) {
  display: inline-block !important;
  vertical-align: baseline !important;
  min-height: 1em !important;
  overflow: visible !important;
}

.markdown-content :deep(.katex .strut) {
  display: inline-block !important;
  min-height: 1em !important;
  height: auto !important;
  overflow: visible !important;
}

.markdown-content :deep(.katex .mord),
.markdown-content :deep(.katex .mop),
.markdown-content :deep(.katex .mbin),
.markdown-content :deep(.katex .mrel),
.markdown-content :deep(.katex .mopen),
.markdown-content :deep(.katex .mclose),
.markdown-content :deep(.katex .mpunct) {
  display: inline !important;
  vertical-align: baseline !important;
}

.markdown-content :deep(.katex .vlist-t) {
  display: inline-table !important;
  table-layout: fixed !important;
  border-collapse: collapse !important;
}

.markdown-content :deep(.katex .vlist-r) {
  display: table-row !important;
}

.markdown-content :deep(.katex .vlist) {
  display: table-cell !important;
  vertical-align: baseline !important;
  position: relative !important;
  min-height: 1em !important;
}

/* 修复分数和根号显示 */
.markdown-content :deep(.katex .frac-line) {
  border-bottom-width: 0.04em !important;
  border-bottom-style: solid !important;
  margin: 0.15em 0 !important;
}

/* 增加分数分子分母间距 */
.markdown-content :deep(.katex .mfrac > span) {
  margin: 0.1em 0 !important;
  padding: 0.05em 0 !important;
}

/* 修复上标下标中的分数显示 */
.markdown-content :deep(.katex .msupsub .mfrac) {
  font-size: 0.8em !important;
  line-height: 1.6 !important;
  margin: 0.15em 0 !important;
}

.markdown-content :deep(.katex .msupsub .frac-line) {
  margin: 0.1em 0 !important;
}

.markdown-content :deep(.katex .msupsub .mfrac > span) {
  margin: 0.08em 0 !important;
  padding: 0.05em 0 !important;
}

.markdown-content :deep(.katex .msupsub) {
  line-height: 2.2 !important;
  vertical-align: baseline !important;
  min-height: 2em !important;
  display: inline-block !important;
}

/* 确保上标下标有足够空间 */
.markdown-content :deep(.katex .msupsub > span) {
  display: block !important;
  line-height: 1.2 !important;
  margin: 0.05em 0 !important;
}

/* 优化指数部分的分数显示 */
.markdown-content :deep(.katex .msupsub .mfrac) {
  font-size: 0.7em !important;
  line-height: 1.2 !important;
  margin: 0.05em 0 !important;
  vertical-align: middle !important;
}

.markdown-content :deep(.katex .msupsub .mfrac .frac-line) {
  margin: 0.05em 0 !important;
  border-bottom-width: 0.03em !important;
}

.markdown-content :deep(.katex .msupsub .mfrac > span) {
  margin: 0.03em 0 !important;
  padding: 0.02em 0 !important;
  line-height: 1.1 !important;
}

/* 确保指数容器有足够高度 */
.markdown-content :deep(.katex .msupsub .mord) {
  min-height: 2.5em !important;
  display: inline-block !important;
  vertical-align: middle !important;
  line-height: 1.8 !important;
}

/* 为包含分数的上标提供更多空间 */
.markdown-content :deep(.katex .mord:has(.msupsub)) {
  line-height: 2.5 !important;
  min-height: 2.5em !important;
}

/* 确保整个公式有足够高度 */
.markdown-content :deep(p:has(.katex .msupsub .mfrac)) {
  line-height: 2.8 !important;
  min-height: 3em !important;
}

.markdown-content :deep(.katex .sqrt > .root) {
  margin-left: 0.27777778em !important;
  margin-right: -0.55555556em !important;
}

/* 确保数学公式不被其他样式影响 */
.markdown-content :deep(.katex *) {
  box-sizing: content-box !important;
  border: none !important;
  outline: none !important;
  background: transparent !important;
  margin: 0 !important;
  padding: 0 !important;
}

/* 为包含数学公式的段落添加足够的行高 */
.markdown-content p:has(.katex) {
  line-height: 1.8 !important;
}

@media (prefers-color-scheme: dark) {
  .pending-highlight {
    opacity: 0.8;
  }
  
  .markdown-content :deep(.katex) {
    color: #ffffff !important;
  }
}

:deep(.artifact-card-wrapper) {
  margin: 1rem 0;
}

:deep(.artifact-content) {
  flex: 1;
  min-width: 0;
}

:deep(.artifact-title) {
  font-size: 0.875rem;
  font-weight: 500;
  color: #334155;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:deep(.artifact-meta) {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 2px;
}

:deep(.artifact-type) {
  font-size: 0.75rem;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

:deep(.artifact-action) {
  color: #cbd5e1;
  transition: color 0.2s;
}

/* URL 行内代码样式 - 非文件类 URL 使用 markdown 行内代码样式 + 右侧打开 Canvas 图标 */
:deep(.url-inline-wrapper) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  vertical-align: middle;
  background: transparent;
  padding: 0;
  margin: 0;
}

/* 确保包裹 URL 的段落不会强制换行 */
:deep(p:has(> .url-inline-wrapper:only-child)),
:deep(p:has(> span.url-inline-wrapper:only-child)) {
  margin: 0;
  padding: 0;
  display: inline;
}

:deep(.url-inline-code) {
  display: inline-block;
  padding: 2px 6px 2px 6px;
  font-size: 0.875em;
  color: #334155;
  background-color: rgba(27, 31, 35, 0.05);
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-family: 'Roboto Mono', Menlo, Monaco, Consolas, monospace;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 300px;
  word-break: break-all;
}

:deep(.url-open-inline-btn) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #000000;
  cursor: pointer;
  text-decoration: none;
  flex-shrink: 0;
  box-sizing: border-box;
  overflow: visible;
}

:deep(.url-open-inline-btn svg) {
  transition: transform 0.15s;
}

:deep(.url-open-inline-btn:hover) {
  color: #000000;
}

:deep(.url-open-inline-btn:hover svg) {
  transform: scale(1.1);
}

:deep(.url-inline-wrapper:hover .url-inline-code) {
  background-color: rgba(27, 31, 35, 0.08);
  border-color: #cbd5e1;
}

/* 对话气泡中的内嵌图片样式 */
:deep(.inline-chat-image) {
  display: block;
  max-width: 100%;
  max-height: 400px;
  border-radius: 24px;
  margin: 8px 0;
  object-fit: contain;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  cursor: pointer;
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

:deep(.inline-chat-image:hover) {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  border-radius: 24px;
  transform: scale(1.005);
}
</style>
