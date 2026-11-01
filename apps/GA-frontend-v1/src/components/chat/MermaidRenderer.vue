<template>
    <div class="mermaid-wrapper" ref="wrapper" @mousedown="onMouseDown">
    <div class="controls">
      <button @click="() => { zoomOut(); triggerLiquidEffect(); }" class="control-btn" title="缩小 (-)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      <button @click="() => { zoomIn(); triggerLiquidEffect(); }" class="control-btn" title="放大 (+)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
      </button>
      <div class="divider"></div>
      <button @click="() => { forceFit(); triggerLiquidEffect(); }" class="control-btn" title="适应屏幕 (Space)">
        <img :src="FitToScreenSvg" class="control-icon" alt="Fit to Screen" />
      </button>
      
      <div class="download-wrapper" ref="downloadWrapper">
        <button @click="toggleDownloadMenu" class="control-btn" :class="{ active: isDownloadMenuOpen }" title="下载">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
            <polyline points="7 10 12 15 17 10"></polyline>
            <line x1="12" y1="15" x2="12" y2="3"></line>
          </svg>
        </button>
        
        <Transition name="menu-pop">
          <div v-if="isDownloadMenuOpen" class="download-options">
            <button @click="() => { downloadSvg(); closeDownloadMenu(); }" class="menu-item">
              <span class="menu-text">SVG</span>
            </button>
            <button @click="() => { downloadPng(); closeDownloadMenu(); }" class="menu-item">
              <span class="menu-text">PNG</span>
            </button>
          </div>
        </Transition>
      </div>

      <div class="divider"></div>
      <button @click="() => { toggleFullScreen(); triggerLiquidEffect(); }" class="control-btn" :title="(isFullScreen && !isExiting) ? '退出全屏 (Esc)' : '全屏浏览 (F)'">
        <Transition name="icon-switch">
          <svg v-if="!isFullScreen || isExiting" key="enter" class="fs-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7" />
          </svg>
          <svg v-else key="exit" class="fs-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7" />
          </svg>
        </Transition>
      </button>
    </div>

    <svg style="position: absolute; width: 0; height: 0; pointer-events: none;">
      <defs>
        <filter id="liquid-glass-filter" x="-50%" y="-50%" width="200%" height="200%" color-interpolation-filters="sRGB">
          <feTurbulence ref="turbulenceRef" type="turbulence" baseFrequency="0.01 0.013" numOctaves="2" seed="1" result="noise" />
          <feGaussianBlur in="noise" stdDeviation="2.3" result="smoothedNoise" />
          <feSpecularLighting in="smoothedNoise" surfaceScale="7.5" specularConstant="0.35" specularExponent="26" lighting-color="#ffffff" result="highlights">
            <fePointLight x="80" y="40" z="260" />
          </feSpecularLighting>
          <feComposite in="highlights" in2="SourceAlpha" operator="in" result="highlightsMasked" />
          <feDisplacementMap ref="displacementRef" in="SourceGraphic" in2="smoothedNoise" scale="1.2" xChannelSelector="R" yChannelSelector="G" result="distorted" />
          <feBlend in="highlightsMasked" in2="distorted" mode="screen" />
        </filter>
      </defs>
    </svg>

    <div v-if="error && isComplete" class="error-panel">
      <div class="error-header" @click="isErrorExpanded = !isErrorExpanded">
        <div class="error-summary">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="error-icon">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
            <line x1="12" y1="9" x2="12" y2="13"></line>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          <span class="error-text-summary">{{ error }}</span>
        </div>
        <div class="header-actions">
          <button v-if="!hasRequestedFix" @click.stop="fixError" class="fix-btn-new" :disabled="isFixing" :class="{ 'is-fixing': isFixing }">
            <div class="fix-content">
              <svg v-if="!isFixing" width="14" height="14" viewBox="0 0 1024 1024" fill="currentColor" class="fix-icon">
                <path d="M714.4 544.576l-85.6-26.08c-80.48-24.704-143.776-89.44-167.488-172.832l-25.12-89.472a36.064 36.064 0 0 0-23.744-24.672 34.24 34.24 0 0 0-26.976 2.784c-8.384 4.672-14.4 12.576-17.216 21.888l-25.6 88.96c-23.68 82.944-86.976 148.16-167.456 172.864l-85.6 26.112c-14.912 4.64-25.6 18.624-25.6 34.912 0 15.84 10.24 30.304 25.12 34.944l86.528 27.04c80 24.672 142.368 89.44 166.56 171.904l25.6 88.96c4.16 15.392 18.144 26.112 33.92 26.112 15.84 0 29.792-10.72 33.984-26.08l25.6-88.992c23.712-82.464 86.528-147.2 166.08-172.384l87.008-27.008c15.36-4.672 25.6-19.104 25.12-34.944a35.2 35.2 0 0 0-25.12-34.016z m233.984-285.888l-33.984-10.24a152.384 152.384 0 0 1-101.888-105.28l-10.24-35.424a15.36 15.36 0 0 0-10.688-11.2h-0.448a15.968 15.968 0 0 0-19.552 11.68l-10.24 35.392a153.28 153.28 0 0 1-101.888 105.28l-33.952 10.24a16.48 16.48 0 0 0-11.648 15.872c0 7.424 4.672 13.504 11.648 15.84l34.432 10.688a153.76 153.76 0 0 1 101.44 104.832l10.208 35.424a15.904 15.904 0 0 0 30.72 0l10.24-35.424a152.864 152.864 0 0 1 101.408-104.832l34.432-10.688A16.928 16.928 0 0 0 960 275.008c0-7.936-4.64-14.464-11.616-16.32z" p-id="23296"></path>
              </svg>
              <svg v-else class="fix-loading-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <g class="fix-loading-spin">
                  <circle cx="12" cy="12" r="10" stroke-dasharray="42 60" stroke-linecap="round" />
                </g>
              </svg>
              <span>{{ isFixing ? '修复中...' : '自动修复' }}</span>
            </div>
          </button>
          <div class="divider-vertical" v-if="!hasRequestedFix"></div>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="chevron-icon" :class="{ rotated: isErrorExpanded }">
            <polyline points="6 9 12 15 18 9"></polyline>
          </svg>
        </div>
      </div>
      
      <div class="error-details-wrapper" :class="{ expanded: isErrorExpanded }">
        <div class="error-details-inner">
          <div class="error-full-text">{{ error }}</div>
        </div>
      </div>
    </div>

    <div ref="container" class="mermaid-container" :class="{ dragging: isDraggingState, ready: isReady, 'smooth-transform': isSmooth }">
      <div ref="mermaidInner" class="mermaid-svg"></div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted, onUnmounted, nextTick } from 'vue';
import mermaid from 'mermaid';
import FitToScreenSvg from '@/assets/image/svg/fit_to_screen.svg';
import { useArtifactStore } from '@/stores/artifactStore';
import { useChatStore } from '@/stores/chat-store';
import NotificationService from '@/utils/NotificationService';

const props = defineProps<{
  content: string;
  isComplete?: boolean;
  id?: string;
  isFullScreen?: boolean;
  isExiting?: boolean;
}>();

const emit = defineEmits<{
  (e: 'toggle-fullscreen'): void;
}>();

const artifactStore = useArtifactStore();
const chatStore = useChatStore();
const isFixing = ref(false);
const hasRequestedFix = ref(false);

const wrapper = ref<HTMLElement | null>(null);
const container = ref<HTMLElement | null>(null);
const mermaidInner = ref<HTMLElement | null>(null);
const turbulenceRef = ref<SVGElement | null>(null);
const displacementRef = ref<SVGElement | null>(null);

const transform = reactive({ x: 0, y: 0, scale: 1 });
const error = ref<string | null>(null);

const toggleFullScreen = () => {
  emit('toggle-fullscreen');
};

const handleKeyDown = (e: KeyboardEvent) => {
  // Ignore if user is typing in an input
  const target = e.target as HTMLElement;
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) || target.isContentEditable) {
    return;
  }

  // Prevent default browser zoom for + and - if needed, but usually those are Ctrl +/-
  // We'll handle plain keys and some common variations

  switch (e.key) {
    case 'Escape':
      if (props.isFullScreen) {
        toggleFullScreen();
        triggerLiquidEffect();
      }
      break;
    case '=':
    case '+':
      zoomIn();
      triggerLiquidEffect();
      e.preventDefault();
      break;
    case '-':
    case '_':
      zoomOut();
      triggerLiquidEffect();
      e.preventDefault();
      break;
    case ' ':
    case '0':
    case 'r':
    case 'R':
      forceFit();
      triggerLiquidEffect();
      e.preventDefault();
      break;
    case 'f':
    case 'F':
      toggleFullScreen();
      triggerLiquidEffect();
      e.preventDefault();
      break;
    case 'ArrowUp':
      transform.y += 40;
      updateDOM();
      e.preventDefault();
      break;
    case 'ArrowDown':
      transform.y -= 40;
      updateDOM();
      e.preventDefault();
      break;
    case 'ArrowLeft':
      transform.x += 40;
      updateDOM();
      e.preventDefault();
      break;
    case 'ArrowRight':
      transform.x -= 40;
      updateDOM();
      e.preventDefault();
      break;
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleKeyDown);
  if (wrapper.value) {
    wrapper.value.addEventListener('wheel', onWheel, { passive: false });
  }
});

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeyDown);
  if (wrapper.value) {
    wrapper.value.removeEventListener('wheel', onWheel);
  }
});

// Initialize error from store if available to prevent flashing
if (props.id) {
  const storedError = artifactStore.getError(props.id);
  if (storedError) {
    error.value = storedError;
  }
}

// Initialize fix state from store
if (props.id) {
  hasRequestedFix.value = artifactStore.getFixRequested(props.id);
}

const isErrorExpanded = ref(false);
const fixError = async () => {
  if (!error.value || isFixing.value) return;
  
  isFixing.value = true;
  const prompt = `以下的 mermaid 代码存在错误:
\`\`\`mermaid
${props.content}
\`\`\`
Error message: ${error.value}
Please fix the mermaid code.`;
  
  try {
    await chatStore.sendMessage(prompt);
    hasRequestedFix.value = true;
    if (props.id) {
      artifactStore.setFixRequested(props.id, true);
    }
  } finally {
    isFixing.value = false;
  }
};

watch(() => props.content, () => {
  hasRequestedFix.value = false;
  if (props.id) {
    artifactStore.setFixRequested(props.id, false);
  }
});

watch(error, (newVal) => {
  if (props.id) {
    if (newVal) {
      artifactStore.setError(props.id, newVal);
    } else {
      artifactStore.clearError(props.id);
    }
  }
}, { immediate: true });

watch(() => props.id, (newId) => {
  if (newId && error.value) {
    artifactStore.setError(newId, error.value);
  }
});

const isDraggingState = ref(false);
let isDragging = false;
let startX = 0;
let startY = 0;
let rafId: number | null = null;
let zoomRafId: number | null = null;
let liquidRafId: number | null = null;
let idleLiquidRafId: number | null = null;

const liquidBase = {
  freqX: 0.01,
  freqY: 0.013,
  idleScale: 1.2
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const setLiquidParams = (freqX: number, freqY: number, scale: number) => {
  if (!turbulenceRef.value || !displacementRef.value) return;
  turbulenceRef.value.setAttribute('baseFrequency', `${freqX} ${freqY}`);
  displacementRef.value.setAttribute('scale', `${scale}`);
};

const stopIdleLiquid = () => {
  if (idleLiquidRafId) {
    cancelAnimationFrame(idleLiquidRafId);
    idleLiquidRafId = null;
  }
};

const startIdleLiquid = () => {
  if (idleLiquidRafId) return;
  const startTime = performance.now();

  const animate = (currentTime: number) => {
    const t = currentTime - startTime;

    const freqX = liquidBase.freqX + 0.0009 * Math.sin(t / 1100);
    const freqY = liquidBase.freqY + 0.0012 * Math.cos(t / 1400);
    const scale =
      liquidBase.idleScale +
      0.45 * Math.sin(t / 1600 + 1.1) +
      0.25 * Math.cos(t / 2400);

    setLiquidParams(
      clamp(freqX, 0.006, 0.03),
      clamp(freqY, 0.006, 0.03),
      clamp(scale, 0.6, 2.6)
    );

    idleLiquidRafId = requestAnimationFrame(animate);
  };

  idleLiquidRafId = requestAnimationFrame(animate);
};

const triggerLiquidEffect = () => {
    if (liquidRafId) cancelAnimationFrame(liquidRafId);
    stopIdleLiquid();
    
    if (turbulenceRef.value) {
      turbulenceRef.value.setAttribute('seed', Math.floor(Math.random() * 1000).toString());
    }

    const startTime = performance.now();
    const duration = 1700;
    
    const animate = (currentTime: number) => {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      
      const impact = Math.sin(progress * Math.PI) * Math.exp(-progress * 5.5);
      
      const settle = Math.sin(progress * Math.PI * 4) * Math.exp(-progress * 2.2);
      
      const wave = (impact * 1.4) + (settle * 0.7);
      
      if (turbulenceRef.value && displacementRef.value) {
        const energy = Math.abs(wave);

        const freqX =
          liquidBase.freqX +
          (0.0032 * energy) +
          (0.0011 * wave);
        const freqY =
          liquidBase.freqY +
          (0.0038 * energy) -
          (0.0010 * wave);

        const scale =
          liquidBase.idleScale +
          (10.5 * energy);

        setLiquidParams(
          clamp(freqX, 0.006, 0.03),
          clamp(freqY, 0.006, 0.03),
          clamp(scale, 0, 14)
        );
      }
      
      if (progress < 1) {
        liquidRafId = requestAnimationFrame(animate);
      } else {
        setLiquidParams(liquidBase.freqX, liquidBase.freqY, liquidBase.idleScale);
        startIdleLiquid();
        liquidRafId = null;
      }
    };
    
    liquidRafId = requestAnimationFrame(animate);
  };

mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: { htmlLabels: true, curve: 'basis' },
  suppressErrorRendering: true
});

const isReady = ref(false);
const isSmooth = ref(false);

const updateDOM = () => {
  if (container.value) {
    container.value.style.transform = `translate(${transform.x}px, ${transform.y}px) scale(${transform.scale})`;
  }
};

const fitToScreen = (forceContain = false, targetWidth?: number, targetHeight?: number) => {
  if (!wrapper.value || !container.value || !mermaidInner.value) return;
  const svg = mermaidInner.value.querySelector('svg');
  if (!svg) return;

  const viewBox = svg.getAttribute('viewBox')?.split(/\s+|,/);
  let width = 0, height = 0;

  if (viewBox && viewBox.length === 4) {
    width = parseFloat(viewBox[2]);
    height = parseFloat(viewBox[3]);
  } else {
    try {
      const bbox = svg.getBBox();
      width = bbox.width;
      height = bbox.height;
    } catch (e) {
      return;
    }
  }

  if (!width || !height) return;

  svg.setAttribute('width', `${width}`);
  svg.setAttribute('height', `${height}`);
  svg.style.width = `${width}px`;
  svg.style.height = `${height}px`;

  const containerWidth = targetWidth || wrapper.value.clientWidth;
  const containerHeight = targetHeight || wrapper.value.clientHeight;
  const padding = 40;

  const scaleX = (containerWidth - padding) / width;
  const scaleY = (containerHeight - padding) / height;
  let scale = Math.min(scaleX, scaleY);

  if (forceContain) {
    scale = Math.min(Math.max(scale, 0.1), 5);
    transform.scale = scale;
    transform.x = (containerWidth - width * scale) / 2;
    transform.y = (containerHeight - height * scale) / 2;
  } else {
    const minReadableScale = 0.8;
    let targetScale = scale;
    
    if (targetScale < minReadableScale) {
      targetScale = minReadableScale;
    }
    
    targetScale = Math.min(targetScale, 1.5);
    
    transform.scale = targetScale;
    
    if (targetScale > scaleX) {
      transform.x = padding / 2;
    } else {
      transform.x = (containerWidth - width * targetScale) / 2;
    }

    if (targetScale > scaleY) {
      transform.y = padding / 2;
    } else {
      transform.y = (containerHeight - height * targetScale) / 2;
    }
  }

  updateDOM();
  
};

const forceFit = async () => {
  isSmooth.value = true;
  await nextTick();
  fitToScreen(true);
};
const onResize = () => {
  isSmooth.value = false;
  fitToScreen(true);
};

const smartFixMermaid = (code: string) => {
  if (!code) return '';
  let lines = code.split('\n');
  let lastLineIndex = lines.length - 1;
  while (lastLineIndex >= 0 && !lines[lastLineIndex].trim()) lastLineIndex--;
  if (lastLineIndex < 0) return code;
  
  let lastLine = lines[lastLineIndex];
  let trimmedLast = lastLine.trim();
  const pairs: Record<string, string> = { '(': ')', '[': ']', '{': '}', '>': '' };
  const stack: string[] = [];
  
  for (let char of trimmedLast) {
    if ('([{'.includes(char)) stack.push(char);
    else if (')]}'.includes(char)) {
      const last = stack[stack.length - 1];
      if (last && pairs[last] === char) stack.pop();
    }
  }
  
  while (stack.length) {
    const open = stack.pop();
    if (open) {
      lastLine += (open === '(' ? ')' : open === '[' ? ']' : '}');
    }
  }
  
  if (/(-{1,}|\.{1,}-{1,}|={1,})[>]?$/.test(trimmedLast)) {
    if (!trimmedLast.endsWith('>')) lastLine += '>';
    lastLine += ' pending_node((...))';
  }
  
  if ((code.match(/subgraph/g) || []).length > (code.match(/\bend\b/g) || []).length) {
    lines.push('end');
  }
  
  lines[lastLineIndex] = lastLine;
  return lines.join('\n');
};

const isGanttDiagram = (code: string) => {
  return /^\s*gantt\b/m.test(code);
};

const hasInitConfig = (code: string) => {
  return /%%\s*\{init:/m.test(code);
};

const getPreferredGanttWidth = () => {
  const base = wrapper.value?.clientWidth || 0;
  const scaled = Math.ceil(base * 1.6);
  return Math.min(Math.max(scaled, 1200), 6000);
};

const buildGanttCode = (baseCode: string, width: number, hasInit: boolean) => {
  if (hasInit) return baseCode;
  return `%%{init: {"gantt": {"useWidth": ${width}}}}%%\n${baseCode}`;
};

const isNegativeWidthError = (e: any) => {
  const message = typeof e?.message === 'string' ? e.message : '';
  return message.includes('attribute width') && message.includes('negative value');
};

const runWithSuppressedMermaidWarnings = async <T>(fn: () => Promise<T>) => {
  const originalWarn = console.warn;
  console.warn = (...args: any[]) => {
    const msg = typeof args[0] === 'string' ? args[0] : '';
    if (msg.includes('Do not assign mappings to elements without corresponding data') && msg.includes('label')) {
      return;
    }
    originalWarn(...args);
  };
  try {
    return await fn();
  } finally {
    console.warn = originalWarn;
  }
};

const renderWithFallback = async (
  id: string,
  baseCode: string,
  renderCode: string,
  isGantt: boolean,
  hasInit: boolean,
  preferredWidth: number
) => {
  try {
    return await runWithSuppressedMermaidWarnings(() => mermaid.render(id, renderCode));
  } catch (e: any) {
    if (isGantt && !hasInit && isNegativeWidthError(e)) {
      const fallbackWidth = Math.min(preferredWidth * 2, 8000);
      if (fallbackWidth > preferredWidth) {
        const fallbackCode = buildGanttCode(baseCode, fallbackWidth, hasInit);
        return await runWithSuppressedMermaidWarnings(() => mermaid.render(id, fallbackCode));
      }
    }
    throw e;
  }
};

const render = async () => {
  if (!mermaidInner.value || !props.content) return;
  
  if (isRendering) {
    hasPendingRender = true;
    return;
  }

  isRendering = true;
  hasPendingRender = false;
  
  try {
    isSmooth.value = false;
    const baseCode = smartFixMermaid(props.content);
    const gantt = isGanttDiagram(baseCode);
    const hasInit = hasInitConfig(baseCode);
    const preferredWidth = gantt ? getPreferredGanttWidth() : 1024;
    const renderCode = gantt ? buildGanttCode(baseCode, preferredWidth, hasInit) : baseCode;

    try {
      await mermaid.parse(renderCode);
    } catch (e: any) {
      if (!props.isComplete) {
        // 如果未完成且解析失败，不报错，保持原状
        return;
      }
      error.value = e.message;
      return;
    }

    const id = `mermaid-${Date.now()}-${Math.floor(Math.random() * 1000)}`;
    let tempContainer: HTMLElement | null = null;

    try {
      let sandbox = document.getElementById('mermaid-sandbox-container');
      if (!sandbox) {
        sandbox = document.createElement('div');
        sandbox.id = 'mermaid-sandbox-container';
        Object.assign(sandbox.style, {
          position: 'fixed',
          top: '-9999px',
          left: '-9999px',
          width: '1px',
          height: '1px',
          overflow: 'hidden',
          visibility: 'hidden',
          zIndex: '-9999',
          pointerEvents: 'none',
          contain: 'strict'
        });
        document.body.appendChild(sandbox);
      }

      tempContainer = document.createElement('div');
      Object.assign(tempContainer.style, {
        display: 'block',
        width: `${preferredWidth}px`,
        height: '768px'
      });
      
      const element = document.createElement('div');
      element.id = id;
      tempContainer.appendChild(element);
      sandbox.appendChild(tempContainer);

      const { svg } = await renderWithFallback(id, baseCode, renderCode, gantt, hasInit, preferredWidth);
      
      if (mermaidInner.value) {
        mermaidInner.value.innerHTML = svg;
        error.value = null;
        if (!isReady.value) {
          requestAnimationFrame(() => {
            isReady.value = true;
          });
        }
        nextTick(() => fitToScreen(true));
      }
    } catch (e: any) {
      if (props.isComplete) {
        const message = typeof e?.message === 'string' ? e.message : '';
        if (gantt && message.includes('attribute width') && message.includes('negative value')) {
          error.value = 'Gantt 图任务时间区间异常导致宽度为负，请检查 dateFormat、起止日期顺序、after 引用与任务时长';
        } else {
          error.value = e.message;
        }
      }
    } finally {
      if (tempContainer && tempContainer.parentElement) {
        tempContainer.parentElement.removeChild(tempContainer);
      }
    }
  } finally {
    isRendering = false;
    // 如果在渲染期间有新的请求，立即处理
    if (hasPendingRender) {
      render();
    }
  }
};

let isRendering = false;
let hasPendingRender = false;

watch(() => [props.content, props.isComplete], () => {
  render();
}, { immediate: true });

const onMouseDown = (e: MouseEvent) => {
  if (!wrapper.value) return;
  if ((e.target as HTMLElement).closest('.controls')) return;
  
  if (zoomRafId) {
    cancelAnimationFrame(zoomRafId);
    zoomRafId = null;
  }

  isDragging = true;
  isDraggingState.value = true;
  isSmooth.value = false;
  startX = e.clientX - transform.x;
  startY = e.clientY - transform.y;
  wrapper.value.style.cursor = 'grabbing';
  window.addEventListener('mousemove', onMove);
  window.addEventListener('mouseup', onUp);
};

const onMove = (e: MouseEvent) => {
  if (!isDragging) return;
  
  if (rafId) return;

  rafId = requestAnimationFrame(() => {
    transform.x = e.clientX - startX;
    transform.y = e.clientY - startY;
    updateDOM();
    rafId = null;
  });
};

const onUp = () => {
  isDragging = false;
  isDraggingState.value = false;
  if (wrapper.value) wrapper.value.style.cursor = 'grab';
  window.removeEventListener('mousemove', onMove);
  window.removeEventListener('mouseup', onUp);
  if (rafId) {
    cancelAnimationFrame(rafId);
    rafId = null;
  }
};

const onWheel = (e: WheelEvent) => {
  e.preventDefault();
  if (!wrapper.value) return;

  if (zoomRafId) {
    cancelAnimationFrame(zoomRafId);
    zoomRafId = null;
  }

  isSmooth.value = false;
  
  const wrapperRect = wrapper.value.getBoundingClientRect();
  const mouseX = e.clientX - wrapperRect.left;
  const mouseY = e.clientY - wrapperRect.top;
  
  const oldScale = transform.scale;
  const factor = e.deltaY > 0 ? 0.9 : 1.1;
  let newScale = oldScale * factor;
  
  // 限制缩放范围
  newScale = Math.min(Math.max(0.1, newScale), 10);
  
  // 计算新的偏移量，使鼠标下的点保持不动
  // 公式: newPos = mousePos - (mousePos - oldPos) * (newScale / oldScale)
  transform.x = mouseX - (mouseX - transform.x) * (newScale / oldScale);
  transform.y = mouseY - (mouseY - transform.y) * (newScale / oldScale);
  transform.scale = newScale;

  updateDOM();
};

const animateZoom = (targetScaleFactor: number) => {
  if (!wrapper.value) return;
  
  isSmooth.value = false;
  
  const startScale = transform.scale;
  const endScale = Math.min(Math.max(startScale * targetScaleFactor, 0.1), 10);
  
  if (Math.abs(endScale - startScale) < 0.001) return;

  const startTime = performance.now();
  const duration = 300;
  
  const w = wrapper.value.clientWidth;
  const h = wrapper.value.clientHeight;
  const centerX = w / 2;
  const centerY = h / 2;
  
  const startX = transform.x;
  const startY = transform.y;
  
  const scaleRatio = endScale / startScale;
  const endX = centerX - (centerX - startX) * scaleRatio;
  const endY = centerY - (centerY - startY) * scaleRatio;
  
  if (zoomRafId) {
     cancelAnimationFrame(zoomRafId);
  }

  const animate = (currentTime: number) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // Ease out cubic
    const ease = 1 - Math.pow(1 - progress, 3);
    
    const currentScale = startScale + (endScale - startScale) * ease;
    const currentX = startX + (endX - startX) * ease;
    const currentY = startY + (endY - startY) * ease;
    
    transform.scale = currentScale;
    transform.x = currentX;
    transform.y = currentY;
    
    updateDOM();
    
    if (progress < 1) {
      zoomRafId = requestAnimationFrame(animate);
    } else {
      zoomRafId = null;
    }
  };
  
  zoomRafId = requestAnimationFrame(animate);
};

const zoomIn = () => {
  animateZoom(1.2);
};

const zoomOut = () => {
  animateZoom(0.8);
};

const isDownloadMenuOpen = ref(false);
const downloadWrapper = ref<HTMLElement | null>(null);

const toggleDownloadMenu = () => {
  isDownloadMenuOpen.value = !isDownloadMenuOpen.value;
  triggerLiquidEffect();
};

const closeDownloadMenu = () => {
  isDownloadMenuOpen.value = false;
};

const handleClickOutside = (event: MouseEvent) => {
  if (downloadWrapper.value && !downloadWrapper.value.contains(event.target as Node)) {
    closeDownloadMenu();
  }
};

onMounted(() => {
  document.addEventListener('mousedown', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('mousedown', handleClickOutside);
});

const downloadSvg = () => {
  if (!props.isComplete) {
    NotificationService.info('Mermaid生成中，请稍后再试');
    return;
  }
  if (!mermaidInner.value) return;
  const blob = new Blob([mermaidInner.value.innerHTML], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `chart-${Date.now()}.svg`;
  a.click();
  URL.revokeObjectURL(url);
};

const downloadPng = async () => {
  if (!props.isComplete) {
    NotificationService.info('Mermaid生成中，请稍后再试');
    return;
  }
  if (!mermaidInner.value) return;
  const svg = mermaidInner.value.querySelector('svg');
  if (!svg) return;

  try {
    const clone = svg.cloneNode(true) as SVGElement;
    // Get dimensions or fallback
    const bbox = svg.getBBox();
    let width = bbox.width;
    let height = bbox.height;
    
    // Fallback if BBox is zero (sometimes happens if hidden)
    if (!width || !height) {
        width = parseFloat(svg.getAttribute('width') || '0');
        height = parseFloat(svg.getAttribute('height') || '0');
    }
    
    if (!width || !height) {
        // Last resort: parse viewbox
        const viewBox = svg.getAttribute('viewBox')?.split(/\s+|,/);
        if (viewBox && viewBox.length === 4) {
            width = parseFloat(viewBox[2]);
            height = parseFloat(viewBox[3]);
        }
    }

    if (!width || !height) {
        console.error('Cannot determine SVG dimensions');
        return;
    }

    const scale = 2; // High resolution
    const pixelWidth = Math.ceil(width * scale);
    const pixelHeight = Math.ceil(height * scale);

    clone.setAttribute('width', `${pixelWidth}`);
    clone.setAttribute('height', `${pixelHeight}`);
    clone.style.width = `${pixelWidth}px`;
    clone.style.height = `${pixelHeight}px`;
    
    // Add white background rect
    const bgRect = document.createElementNS("http://www.w3.org/2000/svg", "rect");
    bgRect.setAttribute("width", "100%");
    bgRect.setAttribute("height", "100%");
    bgRect.setAttribute("fill", "white");
    clone.insertBefore(bgRect, clone.firstChild);

    const svgData = new XMLSerializer().serializeToString(clone);
    // Use Base64 Data URI instead of Blob URL to avoid tainted canvas issues
    const svgBase64 = btoa(unescape(encodeURIComponent(svgData)));
    const url = `data:image/svg+xml;base64,${svgBase64}`;
    
    const img = new Image();
    img.crossOrigin = 'Anonymous';
    img.onload = () => {
      try {
        const canvas = document.createElement('canvas');
        canvas.width = pixelWidth;
        canvas.height = pixelHeight;
        const ctx = canvas.getContext('2d');
        if (ctx) {
          ctx.fillStyle = 'white';
          ctx.fillRect(0, 0, canvas.width, canvas.height);
          ctx.drawImage(img, 0, 0, pixelWidth, pixelHeight);
          
          const pngUrl = canvas.toDataURL('image/png');
          const a = document.createElement('a');
          a.href = pngUrl;
          a.download = `chart-${Date.now()}.png`;
          a.click();
        }
      } catch (err) {
        console.error('PNG export failed (likely tainted canvas):', err);
        // Fallback or notify user could go here
      }
    };
    img.onerror = (e) => {
        console.error('Image load failed:', e);
    };
    img.src = url;
  } catch (e) {
    console.error('PNG export setup failed:', e);
  }
};

watch(() => props.content, render, { immediate: true });

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  window.addEventListener('resize', onResize);
  
  if (wrapper.value) {
    resizeObserver = new ResizeObserver(() => {
      onResize();
    });
    resizeObserver.observe(wrapper.value);
  }

  if (props.content) {
    setTimeout(() => render(), 100);
  }

  startIdleLiquid();
});

onUnmounted(() => {
  window.removeEventListener('resize', onResize);
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  stopIdleLiquid();
  if (liquidRafId) {
    cancelAnimationFrame(liquidRafId);
    liquidRafId = null;
  }
  if (zoomRafId) {
    cancelAnimationFrame(zoomRafId);
    zoomRafId = null;
  }
});

defineExpose({ setArtifact: () => {}, fitToScreen });
</script>

<style scoped>
.mermaid-wrapper {
  width: 100%;
  height: 100%;
  background-color: #fff;
  overflow: hidden;
  position: absolute;
  top: 0;
  left: 0;
  background-image: radial-gradient(#cbd5e1 1px, transparent 1px);
  background-size: 20px 20px;
  cursor: grab;
  transition: background-color 0.3s ease, backdrop-filter 0.3s ease, box-shadow 0.3s ease;
}

.mermaid-wrapper:active {
  cursor: grabbing;
}

:global(body > div[id^="mermaid-"]),
:global(body > div[id^="dmermaid"]) {
  visibility: hidden !important;
  position: fixed !important;
  top: -10000px !important;
  left: -10000px !important;
  pointer-events: none !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
}

.controls {
  position: absolute;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 9999px;
  z-index: 20;
  user-select: none;
  
  /* Liquid Glass Core Styles Moved to ::before */
  background: transparent;
  border: none;
  box-shadow: none;
  isolation: isolate;
}

.controls::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  
  background: linear-gradient(
    135deg, 
    rgba(255, 255, 255, 0.25) 0%, 
    rgba(255, 255, 255, 0.1) 50%, 
    rgba(255, 255, 255, 0.05) 100%
  );
  background-size: 200% 200%;
  animation: controlsLiquidShift 10s ease-in-out infinite;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 
    0 4px 12px rgba(0, 0, 0, 0.1),
    inset 0 0 12px rgba(255, 255, 255, 0.3),
    inset 0 0 4px rgba(255, 255, 255, 0.5);
  border-radius: 9999px;

  filter: url(#liquid-glass-filter);
}

@keyframes controlsLiquidShift {
  0% {
    background-position: 30% 40%;
  }
  50% {
    background-position: 70% 60%;
  }
  100% {
    background-position: 30% 40%;
  }
}

.control-btn {
  position: relative;
  z-index: 10;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: none;
  background: rgba(255, 255, 255, 0.1);
  color: #334155;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.6);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.control-btn:active {
  transform: translateY(0);
  background: rgba(255, 255, 255, 0.8);
}

.control-icon {
  width: 16px;
  height: 16px;
  object-fit: contain;
}

.divider {
  width: 1px;
  height: 16px;
  background-color: rgba(0, 0, 0, 0.3);
  margin: 0 4px;
  z-index: 99999;
}

.error-panel {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 30;
  max-width: 380px;
  background-color: #fef2f2;
  border: 1px solid #fee2e2;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  transition: all 0.3s ease;
}

.error-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  gap: 12px;
  cursor: pointer;
  background-color: #fef2f2;
  user-select: none;
}

.error-header:hover {
  background-color: #fee2e2;
}

.error-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  color: #ef4444;
}

.error-icon {
  flex-shrink: 0;
  opacity: 0.8;
}

.error-text-summary {
  font-size: 12px;
  font-family: monospace;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  color: #b91c1c;
  margin-top: 1px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #ef4444;
}

.divider-vertical {
  width: 1px;
  height: 12px;
  background-color: #fca5a5;
  margin: 0 2px;
  opacity: 0.5;
}

.chevron-icon {
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  opacity: 0.6;
  width: 14px;
  height: 14px;
}

.chevron-icon.rotated {
  transform: rotate(180deg);
}

.error-details-wrapper {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  background-color: #fff1f2;
}

.error-details-wrapper.expanded {
  grid-template-rows: 1fr;
}

.error-details-inner {
  overflow: hidden;
  border-top: 1px solid #fee2e2;
  min-height: 0;
}

.error-full-text {
  font-family: monospace;
  font-size: 11px;
  color: #991b1b;
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
  max-height: 200px;
  overflow-y: auto;
  padding: 10px;
}

.fix-btn-new {
  background-color: #ffffff;
  color: #ef4444;
  border: 1px solid #fecaca;
  padding: 0 10px;
  height: 26px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  position: relative;
  overflow: hidden;
  min-width: 86px;
  user-select: none;
}

.fix-btn-new:hover:not(:disabled) {
  background-color: #fff1f2;
  border-color: #ef4444;
  color: #dc2626;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.15);
  transform: translateY(-0.5px);
}

.fix-btn-new:active:not(:disabled) {
  transform: translateY(0);
  background-color: #fee2e2;
  box-shadow: none;
}

.fix-btn-new:disabled {
  opacity: 0.8;
  cursor: wait;
  background-color: #ffffff;
  border-color: #e5e7eb;
  color: #9ca3af;
  box-shadow: none;
}

.fix-content {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  width: 100%;
  height: 100%;
}

.fix-icon {
  transition: transform 0.2s ease;
}

.fix-btn-new:hover .fix-icon {
  transform: rotate(15deg) scale(1.1);
}

.fix-loading-icon {
  flex-shrink: 0;
  display: block;
}

.fix-loading-spin {
  animation: spin 1s linear infinite;
  transform-origin: 12px 12px;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.mermaid-container {
  width: 100%;
  height: 100%;
  pointer-events: none;
  position: absolute;
  top: 0;
  left: 0;
  transform-origin: 0 0;
  min-width: 100%;
  min-height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: flex-start;
  opacity: 0;
  transition: opacity 0.1s ease-out;
}

.mermaid-container.ready {
  opacity: 1;
}

.mermaid-container.smooth-transform {
  transition: transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}

.mermaid-container.dragging {
  cursor: grabbing;
  transition: none;
}

.mermaid-svg {
  width: auto;
  height: auto;
  display: block;
  max-width: none;
  max-height: none;
}

:global(#dmermaid),
:global(#dmermaid-work-container),
:global(#mermaid-measure-text),
:global(#mermaid-tooltip),
:global(div[id^="dmermaid"]),
:global(div[id^="mermaid-measure"]) {
  visibility: hidden !important;
  position: fixed !important;
  top: -9999px !important;
  left: -9999px !important;
  pointer-events: none !important;
  z-index: -9999 !important;
  width: 1px !important;
  height: 1px !important;
  overflow: hidden !important;
  opacity: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

:deep(.mermaid-svg svg) {
  margin: 0 !important;
  display: block;
}

:deep(.node rect),
:deep(.node circle),
:deep(.node polygon),
:deep(.edgePath path),
:deep(.cluster rect),
:deep(.label) {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.mermaid-wrapper.fullscreen-mode {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 9999;
  border-radius: 0;
  background-color: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  animation: modal-enter 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes modal-enter {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.fs-icon {
  position: absolute;
  top: 8px;
  left: 8px;
}

.icon-switch-enter-active,
.icon-switch-leave-active {
  transition: opacity 0.3s ease;
}

.icon-switch-enter-from,
.icon-switch-leave-to {
  opacity: 0;
}

.icon-switch-enter-to,
.icon-switch-leave-from {
  opacity: 1;
}

.download-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.download-options {
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
  padding: 4px;
  border-radius: 12px;
  z-index: 100;
  min-width: 80px;
  gap: 2px;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08), inset 0 0 0 1px rgba(255, 255, 255, 0.4);
}

.download-options::after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%) rotate(45deg);
  width: 10px;
  height: 10px;
  background: inherit;
  backdrop-filter: inherit;
  -webkit-backdrop-filter: inherit;
  border-bottom: 1px solid rgba(255, 255, 255, 0.4);
  border-right: 1px solid rgba(255, 255, 255, 0.4);
  z-index: -1;
  box-shadow: 4px 4px 10px rgba(0, 0, 0, 0.05);
  border-radius: 0 0 2px 0;
}

.menu-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: #334155;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.2s ease;
  width: 100%;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.5);
  transform: scale(1.02);
}

.menu-item:active {
  transform: scale(0.98);
  background: rgba(255, 255, 255, 0.7);
}

/* Animations */
.menu-pop-enter-active,
.menu-pop-leave-active {
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.menu-pop-enter-from,
.menu-pop-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(10px) scale(0.95);
}

.control-btn.active {
  background: rgba(255, 255, 255, 0.6);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.05);
}
</style>
