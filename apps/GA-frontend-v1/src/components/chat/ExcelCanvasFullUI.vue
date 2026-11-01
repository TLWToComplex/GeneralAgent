<template>
  <div ref="rootRef" class="excel-canvas-full-ui">
    <div class="excel-surface">
      <div :id="containerId" class="excel-host"></div>
      <div v-if="loading" class="excel-overlay">正在加载表格...</div>
      <div v-if="error" class="excel-error">{{ error }}</div>
    </div>
  </div>
</template>

<script lang="ts">
// window.luckysheet 是全局单例，同一时刻只能有一个实例。
// 记录当前持有单例的组件容器 id，避免聊天画布与交付中心预览等多实例并存时相互误销毁。
let activeLuckysheetContainerId: string | null = null;
</script>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch, nextTick } from 'vue';
import Excel from 'exceljs';
import LuckyExcel from 'luckyexcel';
import '@vue-excel/dist/plugins/css/pluginsCss.css';
import '@vue-excel/dist/plugins/plugins.css';
import '@vue-excel/dist/css/luckysheet.css';
import '@vue-excel/dist/assets/iconfont/iconfont.css';
import luckysheetPluginUrl from '@vue-excel/dist/plugins/js/plugin.js?url';
import luckysheetUmdUrl from '@vue-excel/dist/luckysheet.umd.js?url';
import { exportExcel } from '@vue-excel/utils/export';
import { isFunction } from '@vue-excel/utils/is';

type ExcelSource = string | ArrayBuffer | ArrayBufferView | null | undefined;

const props = defineProps<{
  source?: ExcelSource;
  suspend?: boolean;
  title?: string;
}>();

const emit = defineEmits<{
  (e: 'error', message: string): void;
  (e: 'ready'): void;
}>();

const containerId = `luckysheet-${Math.random().toString(36).slice(2, 10)}`;
const rootRef = ref<HTMLElement | null>(null);
const loading = ref(false);
const error = ref('');
const lastSourceKey = ref('');
const initialized = ref(false);
let layoutResizeObserver: ResizeObserver | null = null;
let toolbarRestoreTimers: number[] = [];
let luckysheetRuntimePromise: Promise<void> | null = null;
let syncRafId: number | null = null;
let lastSyncTime = 0;
const SYNC_THROTTLE_MS = 16;
let toolbarRestored = false;
let toolbarShellInstance: {
  shell: HTMLElement;
  toolbar: HTMLElement;
  dispose: () => void;
} | null = null;
let originalWorkbookBuffer: ArrayBuffer | null = null;
let initialLuckysheetSnapshot: any[] | null = null;

const EXCEL_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
const DEFAULT_EXCEL_ZOOM_RATIO = 1;

const cloneBuffer = (buffer: ArrayBuffer) => buffer.slice(0);

const deepCloneJson = <T,>(value: T): T => JSON.parse(JSON.stringify(value));

const normalizeSheetZoom = (sheets: any[] | undefined | null) => {
  if (!Array.isArray(sheets)) return [];
  return sheets.map((sheet) => {
    const normalizedSheet = sheet && typeof sheet === 'object' ? sheet : {};
    const normalizedConfig =
      normalizedSheet.config && typeof normalizedSheet.config === 'object' ? normalizedSheet.config : {};

    return {
      ...normalizedSheet,
      zoomRatio: DEFAULT_EXCEL_ZOOM_RATIO,
      config: {
        ...normalizedConfig,
        sheetViewZoom: DEFAULT_EXCEL_ZOOM_RATIO
      }
    };
  });
};

const getExportFileName = (fileName?: string) => {
  const rawName = fileName?.trim() || props.title?.trim() || 'spreadsheet.xlsx';
  if (/\.xlsx$/i.test(rawName)) return rawName;
  if (/\.xls$/i.test(rawName)) return rawName.replace(/\.xls$/i, '.xlsx');
  return `${rawName}.xlsx`;
};

const triggerBufferDownload = (buffer: ArrayBuffer, fileName: string, mimeType = EXCEL_MIME_TYPE) => {
  const blob = new Blob([buffer], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  setTimeout(() => URL.revokeObjectURL(url), 0);
};

const fetchSourceBuffer = async (url: string) => {
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`Excel 文件读取失败 (${response.status})`);
  }
  return await response.arrayBuffer();
};

const normalizeRichText = (cell: any) => {
  if (!Array.isArray(cell?.ct?.s)) return null;
  return cell.ct.s.map((segment: any) => ({
    v: segment?.v ?? '',
    ff: segment?.ff ?? null,
    fc: segment?.fc ?? null,
    bl: segment?.bl ?? null,
    it: segment?.it ?? null,
    fs: segment?.fs ?? null,
    cl: segment?.cl ?? null,
    ul: segment?.ul ?? null
  }));
};

const pickComparableCell = (cell: any) => {
  if (!cell) return null;
  return {
    v: cell.v ?? null,
    m: cell.m ?? null,
    f: cell.f ?? null,
    bg: cell.bg ?? null,
    ff: cell.ff ?? null,
    fc: cell.fc ?? null,
    bl: cell.bl ?? null,
    it: cell.it ?? null,
    fs: cell.fs ?? null,
    cl: cell.cl ?? null,
    ul: cell.ul ?? null,
    vt: cell.vt ?? null,
    ht: cell.ht ?? null,
    tb: cell.tb ?? null,
    tr: cell.tr ?? null,
    fa: cell.ct?.fa ?? null,
    richText: normalizeRichText(cell)
  };
};

const pickComparableSheet = (sheet: any) => ({
  name: sheet?.name ?? '',
  order: sheet?.order ?? null,
  status: sheet?.status ?? null,
  data: Array.isArray(sheet?.data)
    ? sheet.data.map((row: any[]) => (Array.isArray(row) ? row.map((cell: any) => pickComparableCell(cell)) : []))
    : []
});

const buildSheetsDigest = (sheets: any[]) => JSON.stringify((sheets || []).map((sheet) => pickComparableSheet(sheet)));

const getCellPlainText = (cell: any) => {
  const richText = normalizeRichText(cell);
  if (!richText) return null;
  return richText.map((segment: { v: string }) => segment.v || '').join('');
};

const getCellValueForExcel = (cell: any) => {
  if (!cell) return null;
  if (cell.f) {
    return { formula: cell.f, result: cell.v ?? null };
  }
  const plainText = getCellPlainText(cell);
  if (plainText !== null) return plainText;
  if (Object.prototype.hasOwnProperty.call(cell, 'v')) return cell.v ?? null;
  return null;
};

const exportFontNameMap: Record<number, string> = {
  0: '微软雅黑',
  1: '宋体（Song）',
  2: '黑体（ST Heiti）',
  3: '楷体（ST Kaiti）',
  4: '仿宋（ST FangSong）',
  5: '新宋体（ST Song）',
  6: '华文新魏',
  7: '华文行楷',
  8: '华文隶书',
  9: 'Arial',
  10: 'Times New Roman',
  11: 'Tahoma',
  12: 'Verdana'
};

const toExcelFill = (bg?: string | null) => {
  if (!bg) return null;
  return {
    type: 'pattern' as const,
    pattern: 'solid' as const,
    fgColor: { argb: bg.replace('#', '') }
  };
};

const toExcelFont = (cell: any) => {
  if (!cell) return null;
  return {
    ...(cell.ff !== undefined && cell.ff !== null
      ? { name: typeof cell.ff === 'number' ? exportFontNameMap[cell.ff] || '微软雅黑' : cell.ff }
      : {}),
    ...(cell.fs !== undefined && cell.fs !== null ? { size: cell.fs } : {}),
    ...(cell.fc ? { color: { argb: String(cell.fc).replace('#', '') } } : {}),
    ...(cell.bl !== undefined && cell.bl !== null ? { bold: Boolean(cell.bl) } : {}),
    ...(cell.it !== undefined && cell.it !== null ? { italic: Boolean(cell.it) } : {}),
    ...(cell.ul !== undefined && cell.ul !== null ? { underline: Boolean(cell.ul) } : {}),
    ...(cell.cl !== undefined && cell.cl !== null ? { strike: Boolean(cell.cl) } : {})
  };
};

const toExcelAlignment = (cell: any) => {
  if (!cell) return null;
  const verticalMap: Record<string | number, 'middle' | 'top' | 'bottom'> = {
    0: 'middle',
    1: 'top',
    2: 'bottom',
    default: 'top'
  };
  const horizontalMap: Record<string | number, 'center' | 'left' | 'right'> = {
    0: 'center',
    1: 'left',
    2: 'right',
    default: 'left'
  };
  const wrapTextMap: Record<string | number, boolean> = {
    0: false,
    1: false,
    2: true,
    default: false
  };
  const textRotationMap: Record<string | number, number | 'vertical'> = {
    0: 0,
    1: 45,
    2: -45,
    3: 'vertical',
    4: 90,
    5: -90,
    default: 0
  };

  return {
    vertical: verticalMap[cell.vt ?? 'default'] ?? verticalMap.default,
    horizontal: horizontalMap[cell.ht ?? 'default'] ?? horizontalMap.default,
    wrapText: wrapTextMap[cell.tb ?? 'default'] ?? wrapTextMap.default,
    textRotation: textRotationMap[cell.tr ?? 'default'] ?? textRotationMap.default
  };
};

const applyCellFormatting = (targetCell: any, sourceCell: any) => {
  if (!sourceCell) return;
  const fill = toExcelFill(sourceCell.bg);
  if (fill) {
    targetCell.fill = fill;
  }

  const font = toExcelFont(sourceCell);
  if (font && Object.keys(font).length > 0) {
    targetCell.font = {
      ...(targetCell.font || {}),
      ...font
    };
  }

  const alignment = toExcelAlignment(sourceCell);
  if (alignment) {
    targetCell.alignment = {
      ...(targetCell.alignment || {}),
      ...alignment
    };
  }

  if (sourceCell.ct?.fa) {
    targetCell.numFmt = sourceCell.ct.fa;
  }
};

const applySheetChangesToWorkbook = (workbook: any, sheets: any[]) => {
  const initialSheetsByName = new Map((initialLuckysheetSnapshot || []).map((sheet) => [sheet.name, sheet]));

  sheets.forEach((sheet, sheetIndex) => {
    const worksheet =
      workbook.getWorksheet(sheet.name) ||
      workbook.worksheets[sheetIndex] ||
      workbook.addWorksheet(sheet.name || `Sheet${sheetIndex + 1}`);

    if (sheet.name && worksheet.name !== sheet.name) {
      worksheet.name = sheet.name;
    }

    const initialSheet = initialSheetsByName.get(sheet.name) || initialLuckysheetSnapshot?.[sheetIndex];
    const currentRows = Array.isArray(sheet.data) ? sheet.data : [];
    const initialRows = Array.isArray(initialSheet?.data) ? initialSheet.data : [];
    const rowCount = Math.max(currentRows.length, initialRows.length);

    for (let rowIndex = 0; rowIndex < rowCount; rowIndex += 1) {
      const currentRow = Array.isArray(currentRows[rowIndex]) ? currentRows[rowIndex] : [];
      const initialRow = Array.isArray(initialRows[rowIndex]) ? initialRows[rowIndex] : [];
      const columnCount = Math.max(currentRow.length, initialRow.length);

      for (let columnIndex = 0; columnIndex < columnCount; columnIndex += 1) {
        const currentCell = currentRow[columnIndex];
        const initialCell = initialRow[columnIndex];
        const unchanged =
          JSON.stringify(pickComparableCell(currentCell)) === JSON.stringify(pickComparableCell(initialCell));

        if (unchanged) continue;

        const targetCell = worksheet.getCell(rowIndex + 1, columnIndex + 1);
        if (!currentCell) {
          targetCell.value = null;
          continue;
        }

        targetCell.value = getCellValueForExcel(currentCell);
        applyCellFormatting(targetCell, currentCell);
      }
    }
  });
};

const exportWorkbookFromOriginal = async (fileName: string) => {
  if (!originalWorkbookBuffer) {
    throw new Error('缺少原始 Excel 数据');
  }

  const workbook = new Excel.Workbook();
  await workbook.xlsx.load(cloneBuffer(originalWorkbookBuffer));
  const sheets = window.luckysheet.getAllSheets();
  applySheetChangesToWorkbook(workbook, sheets);
  const buffer = await workbook.xlsx.writeBuffer();
  triggerBufferDownload(buffer as ArrayBuffer, fileName);
};

const buildSourceKey = (source: ExcelSource) => {
  if (!source) return '';
  if (typeof source === 'string') return `url:${source.trim()}`;
  if (source instanceof ArrayBuffer) return `buf:${source.byteLength}`;
  return `view:${source.byteLength}`;
};

const setError = (message: string) => {
  error.value = message;
  emit('error', message);
};

const destroyLuckysheet = () => {
  try {
    if (typeof window !== 'undefined' && window.luckysheet && isFunction(window.luckysheet.destroy)) {
      window.luckysheet.destroy();
    }
  } catch (e) {
    // ignore destroy errors
  }
};

const loadClassicScript = (src: string) => {
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[data-vue-excel-src="${src}"]`);
    if (existing) {
      if (existing.dataset.loaded === 'true') {
        resolve();
        return;
      }
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.src = src;
    script.async = false;
    script.dataset.vueExcelSrc = src;
    script.addEventListener(
      'load',
      () => {
        script.dataset.loaded = 'true';
        resolve();
      },
      { once: true }
    );
    script.addEventListener('error', () => reject(new Error(`Failed to load ${src}`)), { once: true });
    document.head.appendChild(script);
  });
};

const loadLuckysheetRuntime = () => {
  if (typeof window === 'undefined') return Promise.resolve();
  if (window.luckysheet) return Promise.resolve();

  if (!luckysheetRuntimePromise) {
    luckysheetRuntimePromise = loadClassicScript(luckysheetPluginUrl)
      .then(() => loadClassicScript(luckysheetUmdUrl))
      .then(() => {
        if (!window.luckysheet) {
          throw new Error('Luckysheet runtime loaded, but window.luckysheet is unavailable.');
        }
      });
  }

  return luckysheetRuntimePromise;
};

const disposeToolbarShell = () => {
  if (toolbarShellInstance) {
    toolbarShellInstance.dispose();
    toolbarShellInstance = null;
  }
};

const setupExcelToolbarScroll = (toolbar: HTMLElement) => {
  // 避免重复创建
  if (toolbarShellInstance) {
    disposeToolbarShell();
  }

  // 隐藏原生滚动条但保留滚动能力
  toolbar.style.overflowX = 'auto';
  toolbar.style.overflowY = 'hidden';
  toolbar.style.whiteSpace = 'nowrap';
  toolbar.style.boxSizing = 'border-box';
  toolbar.style.display = 'block';
  toolbar.style.width = '100%';
  toolbar.style.maxWidth = '100%';
  toolbar.style.scrollbarWidth = 'none';
  (toolbar.style as any).msOverflowStyle = 'none';

  // 创建 shell 包装器
  const shell = document.createElement('div');
  shell.className = 'excel-toolbar-shell';

  toolbar.parentNode?.insertBefore(shell, toolbar);
  shell.appendChild(toolbar);

  // 创建左右置中滚动按钮
  const createScrollButton = (direction: 'left' | 'right') => {
    const btn = document.createElement('button');
    btn.className = `excel-toolbar-scroll-btn excel-toolbar-scroll-btn--${direction}`;
    btn.setAttribute('type', 'button');
    btn.setAttribute('aria-label', direction === 'left' ? '向左查看更多工具' : '向右查看更多工具');
    btn.innerHTML =
      direction === 'left'
        ? '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>'
        : '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>';
    shell.appendChild(btn);
    return btn;
  };

  const leftBtn = createScrollButton('left');
  const rightBtn = createScrollButton('right');

  let scrollAnimFrame: number | null = null;
  let scrollTarget = 0;

  const stopScrollAnimation = () => {
    if (scrollAnimFrame !== null) {
      cancelAnimationFrame(scrollAnimFrame);
      scrollAnimFrame = null;
    }
  };

  // 滚动状态追踪
  const updateShellState = () => {
    const maxScrollLeft = Math.max(0, toolbar.scrollWidth - toolbar.clientWidth);
    const scrollLeft = toolbar.scrollLeft;
    const overflowing = maxScrollLeft > 1;
    const canStart = scrollLeft > 1;
    const canEnd = scrollLeft < maxScrollLeft - 1;

    shell.classList.toggle('has-scroll-controls', overflowing);
    shell.classList.toggle('can-scroll-start', canStart);
    shell.classList.toggle('can-scroll-end', canEnd);
  };

  const scrollTo = (direction: 'left' | 'right') => {
    const step = Math.max(220, Math.floor(toolbar.clientWidth * 0.68));
    const baseLeft = scrollAnimFrame !== null ? scrollTarget : toolbar.scrollLeft;
    const nextLeft = direction === 'left' ? baseLeft - step : baseLeft + step;
    const maxScroll = Math.max(0, toolbar.scrollWidth - toolbar.clientWidth);
    scrollTarget = Math.min(Math.max(nextLeft, 0), maxScroll);

    stopScrollAnimation();

    const startLeft = toolbar.scrollLeft;
    const delta = scrollTarget - startLeft;
    if (Math.abs(delta) < 1) {
      toolbar.scrollLeft = scrollTarget;
      updateShellState();
      return;
    }

    const duration = Math.min(520, Math.max(280, Math.abs(delta) * 0.65));
    const startTime = performance.now();
    const easeInOutQuart = (t: number) =>
      t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2;

    const animTick = (timestamp: number) => {
      const progress = Math.min((timestamp - startTime) / duration, 1);
      toolbar.scrollLeft = startLeft + delta * easeInOutQuart(progress);
      updateShellState();
      if (progress < 1) {
        scrollAnimFrame = requestAnimationFrame(animTick);
      } else {
        toolbar.scrollLeft = scrollTarget;
        updateShellState();
        scrollAnimFrame = null;
      }
    };

    scrollAnimFrame = requestAnimationFrame(animTick);
  };

  leftBtn.addEventListener('click', () => scrollTo('left'));
  rightBtn.addEventListener('click', () => scrollTo('right'));

  toolbar.addEventListener('scroll', updateShellState, { passive: true });

  // ResizeObserver 监测容器变化
  let resizeObserver: ResizeObserver | null = null;
  if (typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => {
      // 全屏进入/退出动画期间工具栏宽度每帧变化，updateShellState 会读写布局造成
      // 每帧 layout thrash。suspend 期间跳过，动画结束后由 scheduleToolbarRestore 重算一次终态。
      if (props.suspend) return;
      updateShellState();
    });
    resizeObserver.observe(toolbar);
  }

  // 初始状态
  setTimeout(updateShellState, 60);

  toolbarShellInstance = {
    shell,
    toolbar,
    dispose: () => {
      stopScrollAnimation();
      resizeObserver?.disconnect();
      leftBtn.remove();
      rightBtn.remove();
      if (toolbar.parentNode === shell) {
        shell.parentNode?.insertBefore(toolbar, shell);
        shell.remove();
      }
    }
  };
};

const restoreLuckysheetToolbar = () => {
  if (typeof document === 'undefined') return;
  if (toolbarRestored) return;

  const host = document.getElementById(containerId);
  const toolbar = host?.querySelector<HTMLElement>('#luckysheet-wa-editor');
  if (!toolbar) return;

  toolbarRestored = true;
  setupExcelToolbarScroll(toolbar);
};

const scheduleToolbarRestore = () => {
  toolbarRestored = false;
  restoreLuckysheetToolbar();
  toolbarRestoreTimers.forEach((timer) => window.clearTimeout(timer));
  toolbarRestoreTimers = [80, 200].map((delay) => window.setTimeout(restoreLuckysheetToolbar, delay));
};

const syncLuckysheetLayout = () => {
  // 全屏进入/退出动画或组件被挂起期间，容器尺寸每帧变化会触发大量
  // luckysheet.resize() 与工具栏重建，是卡顿主因。此处直接跳过，
  // 待 suspend 恢复（动画结束）时由 watch(props.suspend) 统一刷新一次布局。
  if (props.suspend) return;
  if (syncRafId !== null) return;
  syncRafId = requestAnimationFrame(() => {
    syncRafId = null;
    const now = performance.now();
    if (now - lastSyncTime < SYNC_THROTTLE_MS) return;
    lastSyncTime = now;
    try {
      if (window.luckysheet && isFunction(window.luckysheet.resize)) {
        window.luckysheet.resize();
      }
      scheduleToolbarRestore();
    } catch (e) {
      // best-effort
    }
  });
};

const createLuckysheet = async (data?: any[], title?: string) => {
  await loadLuckysheetRuntime();
  destroyLuckysheet();
  const config: any = {
    container: containerId,
    lang: 'zh',
    zoomRatio: DEFAULT_EXCEL_ZOOM_RATIO,
    showinfobar: false,
    showtoolbar: true,
    showsheetbar: true,
    showbottombar: true
  };
  if (data && data.length > 0) {
    config.data = normalizeSheetZoom(data);
  }
  if (title) {
    config.title = title;
  }
  window.luckysheet.create(config);
  activeLuckysheetContainerId = containerId;
  scheduleToolbarRestore();
  syncLuckysheetLayout();
};

const loadFromArrayBuffer = async (buffer: ArrayBuffer, fileName?: string) => {
  return new Promise<void>((resolve, reject) => {
    originalWorkbookBuffer = cloneBuffer(buffer);
    const blob = new Blob([buffer]);
    const file = new File([blob], fileName || 'spreadsheet.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    });
    LuckyExcel.transformExcelToLucky(file, async (exportJson: any) => {
      if (!exportJson.sheets || exportJson.sheets.length === 0) {
        reject(new Error('无法读取 Excel 文件内容，可能是不支持的文件格式'));
        return;
      }
      const normalizedSheets = normalizeSheetZoom(exportJson.sheets);
      initialLuckysheetSnapshot = deepCloneJson(normalizedSheets);
      await createLuckysheet(normalizedSheets, exportJson.info?.name || fileName);
      resolve();
    });
  });
};

const loadFromUrl = async (url: string, name?: string) => {
  try {
    const buffer = await fetchSourceBuffer(url);
    await loadFromArrayBuffer(buffer, name);
  } catch (fetchError) {
    originalWorkbookBuffer = null;
    return new Promise<void>((resolve, reject) => {
      LuckyExcel.transformExcelToLuckyByUrl(url, name || 'spreadsheet.xlsx', async (exportJson: any) => {
        if (!exportJson.sheets || exportJson.sheets.length === 0) {
          reject(new Error('无法读取远程 Excel 文件内容'));
          return;
        }
        const normalizedSheets = normalizeSheetZoom(exportJson.sheets);
        initialLuckysheetSnapshot = deepCloneJson(normalizedSheets);
        await createLuckysheet(normalizedSheets, exportJson.info?.name || name);
        resolve();
      });
    });
  }
};

const loadSource = async (source: ExcelSource, force = false) => {
  if (props.suspend || !source) return;

  const sourceKey = buildSourceKey(source);
  if (!force && sourceKey && sourceKey === lastSourceKey.value) return;

  // 重新渲染前先清空旧文档，再显示 loading
  destroyLuckysheet();
  loading.value = true;
  error.value = '';
  originalWorkbookBuffer = null;
  initialLuckysheetSnapshot = null;
  try {
    if (source instanceof ArrayBuffer) {
      await loadFromArrayBuffer(source, props.title);
      lastSourceKey.value = sourceKey;
    } else if (ArrayBuffer.isView(source)) {
      const buffer = source.buffer.slice(source.byteOffset, source.byteOffset + source.byteLength) as ArrayBuffer;
      await loadFromArrayBuffer(buffer, props.title);
      lastSourceKey.value = sourceKey;
    } else if (typeof source === 'string') {
      const url = source.trim();
      if (/^https?:\/\//i.test(url)) {
        await loadFromUrl(url, props.title);
        lastSourceKey.value = sourceKey;
      } else {
        setError('无效的 Excel 文件链接');
      }
    }
  } catch (err) {
    const message = err instanceof Error ? err.message : 'Excel 文件加载失败';
    setError(message);
  } finally {
    loading.value = false;
  }
};

onMounted(async () => {
  await nextTick();
  if (typeof ResizeObserver !== 'undefined' && rootRef.value) {
    layoutResizeObserver = new ResizeObserver(() => syncLuckysheetLayout());
    layoutResizeObserver.observe(rootRef.value);
  }
  initialized.value = true;
  emit('ready');
  if (!props.suspend) {
    await createLuckysheet();
  }
  if (props.source) {
    await loadSource(props.source, true);
  }
});

watch(
  () => props.source,
  async (source) => {
    if (!initialized.value || props.suspend) return;
    await loadSource(source, false);
  }
);

watch(
  () => props.suspend,
  async (value) => {
    if (!value && initialized.value && props.source) {
      // 从暂停恢复时，先检查 source 是否变化；未变化且单例仍归属本实例则只刷新布局，不重新加载数据
      const sourceKey = buildSourceKey(props.source);
      if (sourceKey === lastSourceKey.value && activeLuckysheetContainerId === containerId) {
        await nextTick();
        // 仅在组件可见时刷新布局（关闭动画后 v-show 隐藏时无需 resize）
        if (rootRef.value?.offsetParent !== null) {
          // 立即刷新，不使用防抖
          try {
            if (window.luckysheet && isFunction(window.luckysheet.resize)) {
              window.luckysheet.resize();
            }
            scheduleToolbarRestore();
          } catch (e) {
            // best-effort
          }
        }
        return;
      }
      await loadSource(props.source, true);
    }
  }
);

onUnmounted(() => {
  layoutResizeObserver?.disconnect();
  layoutResizeObserver = null;
  if (syncRafId !== null) {
    cancelAnimationFrame(syncRafId);
    syncRafId = null;
  }
  toolbarRestoreTimers.forEach((timer) => window.clearTimeout(timer));
  toolbarRestoreTimers = [];
  disposeToolbarShell();
  // 仅当全局单例仍归属本实例时才销毁，避免误销毁其他实例（如聊天画布）新建的表格
  if (activeLuckysheetContainerId === containerId) {
    destroyLuckysheet();
    activeLuckysheetContainerId = null;
  }
});

const handleExport = async (fileName?: string) => {
  try {
    const sheets = window.luckysheet.getAllSheets();
    const name = getExportFileName(fileName);
    const hasEdits =
      initialLuckysheetSnapshot && buildSheetsDigest(sheets) !== buildSheetsDigest(initialLuckysheetSnapshot);

    if (originalWorkbookBuffer && !hasEdits) {
      triggerBufferDownload(cloneBuffer(originalWorkbookBuffer), name);
      return;
    }

    if (originalWorkbookBuffer && hasEdits) {
      try {
        await exportWorkbookFromOriginal(name);
        return;
      } catch (exportError) {
        console.warn('基于原始 Excel 回写导出失败，回退到 Luckysheet 导出:', exportError);
      }
    }

    await exportExcel(sheets, name.replace(/\.xlsx$/i, ''));
  } catch (err) {
    const message = err instanceof Error ? err.message : '导出失败';
    setError(message);
  }
};

defineExpose({
  exportXlsx: handleExport,
  loadSource
});
</script>

<style scoped>
.excel-canvas-full-ui {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  background: #f8fafc;
}

.excel-surface {
  position: relative;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.excel-host {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.excel-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.85);
  color: #475569;
  font-size: 13px;
  font-weight: 400;
  z-index: 10;
}

.excel-error {
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

::deep(.excel-host .luckysheet) {
  position: absolute !important;
  inset: 0 !important;
  width: 100% !important;
  height: 100% !important;
  margin: 0 !important;
  padding: 0 !important;
}

::deep(.excel-host #luckysheet-cell-main) {
  padding-bottom: 0 !important;
}

::deep(.excel-host #luckysheet-wa-editor) {
  display: block !important;
  width: 100% !important;
  max-width: 100% !important;
  height: 32px !important;
  box-sizing: border-box !important;
  overflow-x: auto !important;
  overflow-y: hidden !important;
  white-space: nowrap !important;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

::deep(.excel-host #luckysheet-wa-editor)::-webkit-scrollbar {
  display: none;
  width: 0 !important;
  height: 0 !important;
}

::deep(.excel-host #luckysheet-wa-editor button),
::deep(.excel-host #luckysheet-wa-editor .luckysheet-toolbar-button),
::deep(.excel-host #luckysheet-wa-editor .luckysheet-wa-editor-button),
::deep(.excel-host #luckysheet-wa-editor [role="button"]) {
  display: inline-block !important;
  vertical-align: middle !important;
}

::deep(.excel-host #luckysheet-wa-editor input),
::deep(.excel-host #luckysheet-wa-editor textarea),
::deep(.excel-host #luckysheet-wa-editor .luckysheet-wa-editor-input),
::deep(.excel-host #luckysheet-wa-editor .luckysheet-wa-editor-area) {
  display: inline-block !important;
  vertical-align: middle !important;
  min-width: 0 !important;
  max-width: 100% !important;
  box-sizing: border-box !important;
}
</style>

<!-- 非 scoped CSS，确保 Luckysheet 下拉菜单和 tooltip 在全屏时渲染在面板上层 -->
<style>
/* 修复公式栏下边框被 luckysheet-wa-calculate-size 遮挡的问题 */
.luckysheet-wa-calculate-size {
  z-index: 1 !important;
}

/* 收敛公式栏、列头和首行网格的边框，避免 1px 叠线侵入相邻 UI */
.excel-host .luckysheet-wa-calculate {
  border-bottom: 0 !important;
}

.excel-host .luckysheet-wa-calculate::after {
  z-index: 2 !important;
}

.excel-host .luckysheet-cols-h-cells-clip {
  top: 0 !important;
  border-bottom-color: #d4d4d4 !important;
}

/* 确保 Luckysheet 的所有弹出菜单 z-index 高于 Canvas 全屏面板 (1003) */
.luckysheet-cols-menu,
.luckysheet-filter-menu,
.luckysheet-filter-submenu,
.luckysheet-datavisual-skin-menu,
.luckysheet-rightgclick-menu,
#luckysheet-sheet-list {
  z-index: 1005 !important;
}

.luckysheet-scrollbar-ltr {
  z-index: 1005 !important;
}

/* 确保工具栏 tooltip 始终在最上层，不被任何元素遮盖 */
#luckysheet-tooltip-up {
  z-index: 99999 !important;
  position: absolute;
}

/* 全屏浏览时工具栏按钮水平居中 */
.excel-canvas-wrapper.has-fullscreen-header #luckysheet-wa-editor {
  text-align: center !important;
}

/* ====== Excel 工具栏左右滚动导航（参考 Word 模式设计）===== */
/* Shell 包装器 + 左右渐变 */
.excel-toolbar-shell {
  position: relative;
  z-index: 1;
  height: 32px;
  margin-top: 0;
}

.excel-toolbar-shell.has-scroll-controls::before,
.excel-toolbar-shell.has-scroll-controls::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 1px;
  width: 52px;
  pointer-events: none;
  z-index: 2;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.excel-toolbar-shell.has-scroll-controls::before {
  left: 0;
  background: linear-gradient(90deg, #fafafc 0 72%, rgba(250, 250, 252, 0.88) 86%, rgba(250, 250, 252, 0) 100%);
}

.excel-toolbar-shell.has-scroll-controls::after {
  right: 0;
  background: linear-gradient(270deg, #fafafc 0 72%, rgba(250, 250, 252, 0.88) 86%, rgba(250, 250, 252, 0) 100%);
}

.excel-toolbar-shell.can-scroll-start::before {
  opacity: 0.12;
}

.excel-toolbar-shell.can-scroll-end::after {
  opacity: 0.12;
}

.excel-toolbar-shell.has-scroll-controls.can-scroll-end {
  margin-top: 0;
}

/* 左右导航按钮 */
.excel-toolbar-shell > .excel-toolbar-scroll-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 20px;
  height: 20px;
  display: none;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(27, 46, 75, 0.1);
  border-radius: 999px !important;
  background: #fff;
  color: #2563eb;
  box-shadow: 0 4px 10px rgba(15, 23, 42, 0.1);
  cursor: pointer;
  z-index: 3;
  transition: all 0.2s ease;
  padding: 0;
  -webkit-appearance: none;
  appearance: none;
  overflow: hidden;
}

.excel-toolbar-shell.can-scroll-start .excel-toolbar-scroll-btn--left,
.excel-toolbar-shell.can-scroll-end .excel-toolbar-scroll-btn--right {
  display: flex;
}

.excel-toolbar-shell.can-scroll-start .excel-toolbar-scroll-btn--left::before,
.excel-toolbar-shell.can-scroll-end .excel-toolbar-scroll-btn--right::before {
  content: "";
  position: absolute;
  inset: 0;
  width: 44px;
  background: #fafafc;
  z-index: -1;
}

.excel-toolbar-shell.can-scroll-start .excel-toolbar-scroll-btn--left::before {
  left: -10px;
  right: auto;
}

.excel-toolbar-shell.can-scroll-end .excel-toolbar-scroll-btn--right::before {
  right: -10px;
  left: auto;
}

.excel-toolbar-scroll-btn:hover {
  transform: translateY(-50%) scale(1.05);
  box-shadow: 0 6px 14px rgba(15, 23, 42, 0.14);
}

.excel-toolbar-scroll-btn--left {
  left: 8px;
}

.excel-toolbar-scroll-btn--right {
  right: 8px;
}

.excel-toolbar-shell > .excel-toolbar-scroll-btn svg {
  width: 11px;
  height: 11px;
  display: block;
}

/* 隐藏 Luckysheet 内部 loading，使用 Canvas 统一的 CreativeLoading 代替 */
#luckysheetloadingdata {
  background: transparent !important;
  pointer-events: none !important;
}

#luckysheetloadingdata .luckysheetLoaderGif,
#luckysheetloadingdata > div > span {
  display: none !important;
}
</style>
