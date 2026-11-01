<template>
  <div class="editor-wrapper">
    <div ref="editorContainer" class="code-editor-container"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue';
import * as monaco from 'monaco-editor';
import 'monaco-editor/esm/vs/editor/editor.main';

// Import workers
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import CssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import HtmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import TsWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';

self.MonacoEnvironment = {
  getWorker(_, label) {
    if (label === 'json') {
      return new JsonWorker();
    }
    if (label === 'css' || label === 'scss' || label === 'less') {
      return new CssWorker();
    }
    if (label === 'html' || label === 'handlebars' || label === 'razor') {
      return new HtmlWorker();
    }
    if (label === 'typescript' || label === 'javascript') {
      return new TsWorker();
    }
    return new EditorWorker();
  }
};

const props = defineProps<{
  modelValue: string;
  language?: string;
  readOnly?: boolean;
}>();

const emit = defineEmits(['update:modelValue', 'scroll-status']);

const editorContainer = ref<HTMLElement | null>(null);
let editor: monaco.editor.IStandaloneCodeEditor | null = null;
const isAtBottom = ref(true);

const checkScrollPosition = () => {
  if (!editor) return;
  const scrollTop = editor.getScrollTop();
  const scrollHeight = editor.getScrollHeight();
  const layoutInfo = editor.getLayoutInfo();
  const height = layoutInfo.height;
  
  // Check if user is near the bottom (tolerance of 50px)
  const newIsAtBottom = (scrollTop + height) >= (scrollHeight - 50);
  
  if (isAtBottom.value !== newIsAtBottom) {
    isAtBottom.value = newIsAtBottom;
    emit('scroll-status', newIsAtBottom);
  }
};

const scrollToBottom = () => {
  if (!editor) return;
  const lineCount = editor.getModel()!.getLineCount();
  editor.revealLine(lineCount);
  // Immediate check
  checkScrollPosition();
};

defineExpose({
  scrollToBottom
});

// Map common aliases to Monaco language IDs
const getMonacoLanguage = (lang: string | undefined): string => {
  if (!lang) return 'plaintext';
  const l = lang.toLowerCase();
  const map: Record<string, string> = {
    'js': 'javascript',
    'ts': 'typescript',
    'py': 'python',
    'rb': 'ruby',
    'cs': 'csharp',
    'cpp': 'cpp',
    'c++': 'cpp',
    'h': 'cpp',
    'hpp': 'cpp',
    'c': 'c',
    'go': 'go',
    'rs': 'rust',
    'java': 'java',
    'kt': 'kotlin',
    'sh': 'shell',
    'bash': 'shell',
    'zsh': 'shell',
    'yaml': 'yaml',
    'yml': 'yaml',
    'json': 'json',
    'xml': 'xml',
    'html': 'html',
    'css': 'css',
    'scss': 'scss',
    'less': 'less',
    'md': 'markdown',
    'markdown': 'markdown',
    'sql': 'sql',
    'dockerfile': 'dockerfile',
    'docker': 'dockerfile',
    'vue': 'html', // Fallback for Vue to HTML for basic highlighting
    'mermaid': 'mermaid', // Will be registered below
    'php': 'php',
    'swift': 'swift',
    'm': 'objective-c',
    'mm': 'objective-c',
    'objc': 'objective-c',
    'r': 'r',
    'dart': 'dart',
    'lua': 'lua',
    'pl': 'perl',
    'pm': 'perl',
    'scala': 'scala',
    'ex': 'elixir',
    'exs': 'elixir',
    'hs': 'haskell',
    'clj': 'clojure',
    'cljs': 'clojure',
    'cljc': 'clojure',
    'edn': 'clojure',
    'vb': 'vb',
    'fs': 'fsharp',
    'fsi': 'fsharp',
    'fsx': 'fsharp',
    'ps1': 'powershell',
    'psm1': 'powershell',
    'graphql': 'graphql',
    'gql': 'graphql',
    'mk': 'makefile',
    'makefile': 'makefile',
    'bat': 'bat',
    'cmd': 'bat',
    'ini': 'ini',
    'properties': 'ini',
  };
  return map[l] || l;
};

const defineCustomTheme = () => {
  monaco.editor.defineTheme('aisix-light', {
    base: 'vs',
    inherit: true,
    rules: [
      { token: 'comment', foreground: '6a9955', fontStyle: 'italic' },
      { token: 'comment.doc', foreground: '608b4e', fontStyle: 'italic' },
      { token: 'comment.line', foreground: '6a9955', fontStyle: 'italic' },
      { token: 'comment.block', foreground: '6a9955', fontStyle: 'italic' },
      { token: 'keyword', foreground: '0000ff', fontStyle: 'bold' },
      { token: 'string', foreground: 'a31515' },
      { token: 'string.doc', foreground: 'a31515' },
      { token: 'number', foreground: '098658' },
      { token: 'regexp', foreground: '811f3f' },
      { token: 'type', foreground: '267f99' },
      { token: 'class', foreground: '267f99' },
      { token: 'interface', foreground: '267f99' },
      { token: 'namespace', foreground: '267f99' },
      { token: 'function', foreground: '795e26' },
      { token: 'method', foreground: '795e26' },
      { token: 'variable', foreground: '001080' },
      { token: 'variable.predefined', foreground: '001080' },
      { token: 'identifier', foreground: '001080' },
      { token: 'parameter', foreground: '001080' },
      { token: 'tag', foreground: '800000' },
      { token: 'attribute.name', foreground: 'ff0000' },
      { token: 'attribute.value', foreground: '0000ff' },
      { token: 'delimiter', foreground: '000000' },
      { token: 'operator', foreground: '000000' },
      { token: '', foreground: '000000' } // Default foreground
    ],
    colors: {
      'editor.background': '#ffffff',
      'editor.foreground': '#000000',
      'editor.lineHighlightBackground': '#f0f0f0',
      'editorCursor.foreground': '#000000',
      'editorWhitespace.foreground': '#d3d3d3',
    }
  });
};

const registerMermaidLanguage = () => {
  const languages = monaco.languages.getLanguages();
  if (languages.some(l => l.id === 'mermaid')) return;

  monaco.languages.register({ id: 'mermaid' });
  monaco.languages.setMonarchTokensProvider('mermaid', {
    tokenizer: {
      root: [
        [/^graph|^flowchart|^sequenceDiagram|^classDiagram|^stateDiagram|^erDiagram|^gantt|^pie|^gitGraph/, 'keyword'],
        [/[a-zA-Z_][\w-]*/, 'identifier'],
        [/\[.*?\]/, 'string'],
        [/\(.*?\)|\{.*?\}|\>.*?\]/, 'string'],
        [/-->|---|==>|-.->|\.|\|/, 'operator'],
        [/".*?"/, 'string'],
        [/\d+/, 'number'],
        [/%%.*$/, 'comment'],
      ]
    }
  });
};

onMounted(() => {
  if (!editorContainer.value) return;

  defineCustomTheme();
  registerMermaidLanguage();

  editor = monaco.editor.create(editorContainer.value, {
    value: props.modelValue,
    language: getMonacoLanguage(props.language),
    theme: 'aisix-light',
    readOnly: props.readOnly || false,
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    padding: { top: 12, bottom: 8 },
    fontSize: 14,
    fontFamily: "'Menlo', 'Monaco', 'Courier New', monospace",
  });

  editor.onDidScrollChange(() => {
    checkScrollPosition();
  });

  editor.onDidChangeModelContent(() => {
    const value = editor?.getValue() || '';
    emit('update:modelValue', value);
    // Content change might change scroll height, so re-check
    // Using setTimeout to allow layout update
    setTimeout(checkScrollPosition, 0);
  });
});

watch(() => props.modelValue, (newValue, oldValue) => {
  if (editor && editor.getValue() !== newValue) {
    const prevVal = oldValue || '';
    const isAppending = newValue.startsWith(prevVal) && newValue.length > prevVal.length;

    const scrollTop = editor.getScrollTop();
    const scrollHeight = editor.getScrollHeight();
    const layoutInfo = editor.getLayoutInfo();
    const wasAtBottom = (scrollTop + layoutInfo.height) >= (scrollHeight - 50);

    editor.setValue(newValue);

    if (isAppending) {
      if (wasAtBottom) {
        const lineCount = editor.getModel()!.getLineCount();
        editor.revealLine(lineCount);
      } else {
        editor.setScrollTop(scrollTop);
      }
    }
    setTimeout(checkScrollPosition, 0);
  }
});

watch(() => props.language, (newLang) => {
  if (editor && newLang) {
    monaco.editor.setModelLanguage(editor.getModel()!, getMonacoLanguage(newLang));
  }
});

onUnmounted(() => {
  if (editor) {
    editor.dispose();
    editor = null;
  }
});
</script>

<style scoped>
.editor-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
}

.code-editor-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

</style>
