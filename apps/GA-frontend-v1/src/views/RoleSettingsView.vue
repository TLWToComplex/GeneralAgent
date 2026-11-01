<template>
  <div class="role-settings">
    <!-- 现代化头部区域 -->
    <div class="rs-page-header">
      <div class="rs-header-main">
        <div class="rs-header-content">
          <h1 class="rs-page-title">角色设置</h1>
          <p class="rs-page-description">为对话设置全局系统提示词，支持插入动态变量与预览渲染效果</p>
        </div>
      </div>
      <div class="rs-header-actions">
        <button class="action-btn secondary" @click="formatTemplate" title="智能格式化：规范标点、优化排版、统一列表格式">
          <UnorderedListOutlined />
          格式化
        </button>
        <button class="action-btn secondary" @click="applyRecommendedTemplate">
          <ReloadOutlined />
          重置模板
        </button>
        <button class="action-btn primary" @click="handleSave">
          <SaveOutlined />
          保存配置
        </button>
      </div>
    </div>

    <!-- 主内容区域 -->
    <div class="content-grid">
      <!-- 编辑器卡片 -->
      <div class="editor-card">
        <div class="rs-card-header" style="padding: 10px 16px;">
          <div class="card-title-group">
            <h3 class="card-title">提示词编辑</h3>
            <span class="char-counter" title="Token计算基于GPT-4编码，不同平台可能略有差异">{{ estimatedTokens }} tokens</span>
          </div>
        </div>
        <div class="editor-container">
          <textarea v-model="systemMessageInput" class="prompt-editor"
            placeholder="在此编辑系统提示词，可使用变量如 ${date}、${time}、${model_name}&#10;&#10;示例：&#10;你是一名专业的AI助手。&#10;当前时间：${datetime}&#10;使用模型：${model_name}"></textarea>
        </div>
      </div>

      <!-- 右侧面板 -->
  <div class="side-panel">
    <!-- 预览卡片 -->
    <div class="preview-card">
      <div class="rs-card-header">
        <h3 class="card-title">实时预览</h3>
      </div>
      <div class="preview-container">
        <Transition name="preview-fade">
          <div v-show="overlayVisible" class="preview-loading">
            <a-spin :indicator="spinIndicator" />
            <span class="loading-text">正在渲染...</span>
          </div>
        </Transition>
        <Transition name="preview-content-fade" appear>
          <MarkdownRenderer v-if="processedPreview && markdownReady" :content="processedPreview" role="system" class="preview-content" />
        </Transition>
      </div>
    </div>

        <!-- 变量卡片 -->
        <div class="variables-card">
          <div class="rs-card-header">
            <h3 class="card-title">可用变量</h3>
            <span class="variable-count">{{ supportedVariables.length }} 个</span>
          </div>
          <div class="variables-container">
            <div class="variable-grid">
              <div v-for="v in supportedVariables" :key="v.key" class="variable-item">
                <div class="variable-header">
                  <span class="variable-name">${{ v.key }}</span>
                </div>
                <div class="variable-description">{{ v.label }}</div>
                <div class="variable-value">{{ getVariableCurrentValue(v.key) }}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, defineAsyncComponent, h } from 'vue';
import { useChatStore } from '@/stores/chat-store';
import NotificationService from '@/utils/NotificationService';
import { useSystemPromptVariables } from '@/composables/useSystemPromptVariables';
import { UnorderedListOutlined, ReloadOutlined, SaveOutlined, LoadingOutlined } from '@ant-design/icons-vue';
import StorageService, { STORAGE_KEYS } from '@/utils/StorageService';
import { getPrompt, updatePrompt } from '@/services/aiPrompt';
// 异步加载 MarkdownRenderer，减少初始加载体积
const MarkdownRenderer = defineAsyncComponent(() => import('@/components/common/MarkdownRenderer.vue'));

defineOptions({
  name: 'RoleSettingsView'
});

const chatStore = useChatStore();
const { supportedVariables, processSystemPrompt } = useSystemPromptVariables();

const saving = ref(false);
const systemMessageInput = ref<string>(chatStore.systemMessage || '');
const currentTime = ref(new Date());
const markdownReady = ref(false);
const overlayVisible = computed(() => !markdownReady.value);
const spinIndicator = h(LoadingOutlined, {
  style: { fontSize: '24px' },
  spin: true,
});

// Token计算相关
const encoding = ref<any>(null);
let timeUpdateInterval: NodeJS.Timeout | null = null;

// 初始化编码器（异步动态导入，避免首屏阻塞）
const initEncoding = async () => {
  try {
    const mod = await import('js-tiktoken');
    encoding.value = mod.getEncoding('cl100k_base');
  } catch (error) {
    console.error('编码器初始化失败:', error);
  }
};

// Token计数功能 - 使用js-tiktoken准确计算处理后的内容
const estimatedTokens = computed(() => {
  if (!systemMessageInput.value || !encoding.value) return 0;

  try {
    // 使用处理后的内容计算token，包含变量替换
    const processedText = processedPreview.value || systemMessageInput.value.trim();
    return encoding.value.encode(processedText).length;
  } catch (error) {
    console.error('Token计算错误:', error);
    return 0;
  }
});

// 实时预览，包含时间更新
const processedPreview = computed(() => {
  // 创建一个临时的变量处理函数，使用当前时间
  const tempText = systemMessageInput.value.replace(/\$\{datetime}/g, currentTime.value.toLocaleString('zh-CN'));
  return processSystemPrompt(tempText);
});

// 获取变量当前值，时间变量使用实时时间
function getVariableCurrentValue(variable: string): string {
  if (variable === 'datetime') {
    return currentTime.value.toLocaleString('zh-CN');
  }
  return processSystemPrompt(`\${${variable}}`);
}

function formatTemplate() {
  const originalText = systemMessageInput.value;
  if (!originalText.trim()) {
    NotificationService.info('内容为空，无需格式化');
    return;
  }

  let formattedText = originalText;
  let changes = 0;

  // 1. 基础清理：移除行尾空格
  const beforeTrimming = formattedText;
  formattedText = formattedText.split('\n').map(line => line.replace(/\s+$/g, '')).join('\n');
  if (formattedText !== beforeTrimming) changes++;

  // 2. 标点符号规范化
  const beforePunctuation = formattedText;
  // 统一中文标点
  formattedText = formattedText
    .replace(/，\s+/g, '，')  // 中文逗号后不需要空格
    .replace(/。\s+/g, '。')  // 中文句号后不需要空格
    .replace(/：\s+/g, '：')  // 中文冒号后不需要空格
    .replace(/；\s+/g, '；')  // 中文分号后不需要空格
    .replace(/！\s+/g, '！')  // 中文感叹号后不需要空格
    .replace(/？\s+/g, '？')  // 中文问号后不需要空格
    // 英文标点后添加空格（如果后面直接跟字符）
    .replace(/([,.;!?])([^\s\n])/g, '$1 $2')
    // 英文冒号后添加空格
    .replace(/:([^\s\n])/g, ': $1');
  if (formattedText !== beforePunctuation) changes++;

  // 3. 中英文混排优化
  const beforeMixedText = formattedText;
  formattedText = formattedText
    // 中文与英文/数字之间添加空格
    .replace(/([\u4e00-\u9fff])([a-zA-Z0-9])/g, '$1 $2')
    .replace(/([a-zA-Z0-9])([\u4e00-\u9fff])/g, '$1 $2')
    // 中文与变量之间添加空格
    .replace(/([\u4e00-\u9fff])(\$\{[^}]+})/g, '$1 $2')
    .replace(/(\$\{[^}]+})([\u4e00-\u9fff])/g, '$1 $2')
    // 避免重复空格
    .replace(/\s{2,}/g, ' ');
  if (formattedText !== beforeMixedText) changes++;

  // 4. 列表项格式统一
  const beforeList = formattedText;
  formattedText = formattedText
    // 统一使用 "- " 作为列表标记
    .replace(/^\s*[•·*]\s+/gm, '- ')
    .replace(/^\s*-\s{2,}/gm, '- ')
    // 数字列表格式统一
    .replace(/^\s*(\d+)[.)]\s+/gm, '$1. ')
    // 确保列表项前有适当缩进
    .replace(/^-\s+/gm, '- ')
    .replace(/^(\d+\.)\s+/gm, '$1 ');
  if (formattedText !== beforeList) changes++;

  // 5. 段落整理
  const beforeParagraph = formattedText;
  formattedText = formattedText
    // 合并多余空行（3个或以上空行合并为2个）
    .replace(/\n{3,}/g, '\n\n')
    // 确保列表项之间只有一个空行
    .replace(/(\n- .+)\n{2,}(\n- )/g, '$1\n$2')
    .replace(/(\n\d+\. .+)\n{2,}(\n\d+\. )/g, '$1\n$2')
    // 去除首尾空白
    .trim();
  if (formattedText !== beforeParagraph) changes++;

  // 6. 智能缩进处理
  const beforeIndent = formattedText;
  const lines = formattedText.split('\n');
  const processedLines = lines.map(line => {
    // 如果是列表项，确保正确缩进
    if (line.match(/^\s*- /)) {
      return line.replace(/^\s*- /, '- ');
    }
    if (line.match(/^\s*\d+\. /)) {
      return line.replace(/^\s*(\d+\. )/, '$1');
    }
    // 移除行首多余空格（保留有意义的缩进）
    if (line.match(/^\s{4,}/)) {
      return line.replace(/^\s+/, '  '); // 最多保留2个空格的缩进
    }
    return line;
  });
  formattedText = processedLines.join('\n');
  if (formattedText !== beforeIndent) changes++;

  // 应用格式化结果
  systemMessageInput.value = formattedText;

  // 显示格式化统计信息
  if (changes > 0) {
    const stats = {
      lines: formattedText.split('\n').length,
      chars: formattedText.length,
      changes: changes
    };
    NotificationService.success(`格式化完成！处理了 ${stats.changes} 项改进，共 ${stats.lines} 行，${stats.chars} 个字符`);
  } else {
    NotificationService.info('内容格式已规范，无需再次调整');
  }
}

function applyRecommendedTemplate() {
  systemMessageInput.value = [
    '你是一名专业且可靠的 AI 助手。',
    '',
    '当前日期时间：${datetime}',
    '当前模型：${model_name}',
    '',
    '请遵循以下规范：',
    '- 回答简洁明了，必要时提供步骤和示例',
    '- 若缺少信息请主动询问再继续',
    '- 标注重要注意事项与限制'
  ].join('\n');
}

async function handleSave() {
  try {
    saving.value = true;
    await updatePrompt({
      prompt: systemMessageInput.value
    });
    try {
      const list = await getPrompt();
      const first = list[0] || '';
      if (first.trim()) {
        const text = first.trim();
        StorageService.setSystemMessage(text);
        chatStore.setSystemMessage(text);
        systemMessageInput.value = text;
      }
    } catch (_) {}
    NotificationService.success('已保存系统提示词');
  } catch (e) {
    NotificationService.error('保存失败，请重试');
  } finally {
    saving.value = false;
  }
}

// 生命周期钩子 - 启动时间更新定时器
onMounted(() => {
  // 延迟初始化编码器，避免影响视图切换的初次渲染
  setTimeout(() => {
    initEncoding();
  }, 0);

  // 预加载异步 MarkdownRenderer，移除对 Suspense 的依赖
  import('@/components/common/MarkdownRenderer.vue')
    .then(() => {
      markdownReady.value = true;
    })
    .catch(() => {
      // 即使失败也不阻塞遮罩，避免长时间显示
      markdownReady.value = true;
    });

  (async () => {
    const cached = (StorageService.getSystemMessage() || '').trim();
    if (cached) {
      systemMessageInput.value = cached;
      chatStore.setSystemMessage(cached);
      return;
    }
    const prefs = (StorageService.get(STORAGE_KEYS.USER_PREFERENCES) || {}) as any;
    const prompt = typeof prefs.prompt === 'string' ? prefs.prompt.trim() : '';
    if (prompt) {
      StorageService.setSystemMessage(prompt);
      chatStore.setSystemMessage(prompt);
      systemMessageInput.value = prompt;
    }
  })();

  // 每秒更新时间
  timeUpdateInterval = setInterval(() => {
    currentTime.value = new Date();
  }, 1000);
});

// 生命周期钩子 - 清理定时器
onUnmounted(() => {
  if (timeUpdateInterval) {
    clearInterval(timeUpdateInterval);
    timeUpdateInterval = null;
  }
});

// 移除编辑时的短暂渲染指示，仅在首屏加载时显示遮罩
</script>

<style scoped>
.role-settings {
  height: 95vh;
  background: #ffffff;
  padding: 24px 30px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

 .rs-page-header {
  background: #ffffff;
  padding: 0 0 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}
.rs-header-main {
  display: flex;
  align-items: center;
  gap: 16px;
}
.rs-page-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0 0 4px 0;
}
.rs-page-description {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
  line-height: 1.4;
}
.rs-header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* 简洁按钮系统 */
.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
}

.action-btn:hover {
  background: inherit;
  border-color: inherit;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
}

.action-btn.primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: #f3f4f6;
  color: #374151;
}

.action-btn.secondary:hover {
  background: #e5e7eb;
}

.action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }

  100% {
    transform: rotate(360deg);
  }
}

/* 主内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* 编辑器区域 */
.editor-card {
  display: flex;
  flex-direction: column;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  min-height: 0;
}

 .rs-card-header {
  padding: 12px 16px;
  border-bottom: 1px solid #e5e7eb;
  background: #f9fafb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
  border-top-right-radius: 12px;
  border-top-left-radius: 12px;
}

.card-title-group {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.char-counter {
  background: #ededed;
  color: #6b7280;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
  cursor: help;
}

.editor-container {
  flex: 1;
  padding: 0;
  min-height: 0;
}

.prompt-editor {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
  background: #ffffff;
  resize: none;
  padding: 16px;
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
}

.prompt-editor:focus {
  background: #ffffff;
}

.prompt-editor::placeholder {
  color: #9ca3af;
  line-height: 1.6;
}

/* 右侧面板 */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-height: 0;
}

.preview-card,
.variables-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.preview-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #6b7280;
  flex-direction: column;
  background: rgba(255, 255, 255, 0.6);
  z-index: 10;
  will-change: opacity;
  pointer-events: none;
}

.loading-text {
  position: relative;
  top: -2px;
}

.preview-card {
  flex: 1;
}

.variables-card {
  flex: 1;
}

.preview-container {
  flex: 1;
  padding: 0;
  position: relative;
  min-height: 240px;
}

.preview-content {
  height: 100%;
  overflow: auto;
  background: #ffffff;
  border-bottom-left-radius: 12px;
  border-bottom-right-radius: 12px;
  padding: 16px;
}

.preview-content :deep(.markdown-content) {
  font-size: 14px;
  line-height: 1.6;
  color: #374151;
}

.preview-content :deep(.markdown-content h1),
.preview-content :deep(.markdown-content h2),
.preview-content :deep(.markdown-content h3),
.preview-content :deep(.markdown-content h4),
.preview-content :deep(.markdown-content h5),
.preview-content :deep(.markdown-content h6) {
  color: #1f2937;
  margin-top: 1.5em;
  margin-bottom: 0.5em;
  font-weight: 600;
}

.preview-content :deep(.markdown-content h1) {
  font-size: 1.5em;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.3em;
}

.preview-content :deep(.markdown-content h2) {
  font-size: 1.3em;
}

.preview-content :deep(.markdown-content h3) {
  font-size: 1.1em;
}

.preview-content :deep(.markdown-content p) {
  margin-bottom: 1em;
  line-height: 1.7;
}

.preview-content :deep(.markdown-content ul),
.preview-content :deep(.markdown-content ol) {
  margin-bottom: 1em;
  padding-left: 1.5em;
}

.preview-content :deep(.markdown-content li) {
  margin-bottom: 0.3em;
  line-height: 1.6;
}

.preview-content :deep(.markdown-content code) {
  background: #f3f4f6;
  padding: 0.2em 0.4em;
  border-radius: 6px;
  font-size: 0.9em;
  color: #e11d48;
}

.preview-content :deep(.markdown-content pre) {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 1em;
  overflow-x: auto;
  margin-bottom: 1em;
}

.preview-content :deep(.markdown-content blockquote) {
  border-left: 4px solid #3b82f6;
  padding-left: 1em;
  margin: 1em 0;
  color: #6b7280;
  font-style: italic;
}

.variable-count {
  background: #ededed;
  color: #6b7280;
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 12px;
}

.variables-container {
  flex: 1;
  padding: 12px 16px 16px;
  overflow: auto;
  min-height: 0;
}

.variable-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.variable-item {
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 12px;
  transition: all 0.2s ease;
}

.variable-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.variable-name {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #3b82f6;
  background: #dbeafe;
  padding: 2px 6px;
  border-radius: 4px;
}

.variable-description {
  font-size: 13px;
  color: #6b7280;
  margin-bottom: 6px;
  font-weight: 500;
}

.variable-value {
  font-size: 12px;
  color: #464646;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  padding: 2px 0;
  border-radius: 4px;
  word-break: break-all;
}

/* 滚动条 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: #f3f4f6;
}

::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 3px;
}
</style>
