<template>
  <div class="export-button-wrapper">
    <!-- 选择模式下使用工具按钮样式 -->
    <button 
      v-if="isSelectionMode"
      class="tool-btn export-tool-btn"
      @click="showExportConfirmWithFormat('pdf')"
      :disabled="!hasSelection"
      title="导出选中消息为PDF"
    >
      <PDFIcon class="tool-icon" />
      <span class="tool-text">导出PDF</span>
    </button>
    
    <!-- 非选择模式下使用原有样式 -->
    <a-tooltip v-else placement="top">
      <template #title>
        <span>导出对话</span>
      </template>
      <a-button 
        class="export-button" 
        size="large" 
        type="text" 
        @click="showExportConfirmWithFormat('pdf')"
      >
        <PDFIcon style="width: 23px; height: 23px; margin-left: -7px; margin-top: 1px;"/>
      </a-button>
    </a-tooltip>

    <!-- 导出确认对话框 -->
  <a-modal
      v-model:open="confirmVisible"
      :footer="null"
      :mask-closable="!exporting && !previewMode"
      :closable="!exporting && !previewMode"
      :width="previewMode ? '100%' : '480px'"
      :wrap-class-name="previewMode ? 'full-modal' : ''"
      class="export-modal"
      centered
      @afterClose="handleModalClose"
  >
    <!-- 预览区域 - 完全控制DOM结构 -->
    <div v-if="previewMode" class="preview-container">
      <!-- 模态窗标题 -->
      <div class="modal-custom-title preview-header">
        <div class="preview-title">PDF效果预览</div>
        <div class="preview-info">缩放比例: {{ scaleValue }}% · 纸张大小: {{ paperSize.toUpperCase() }} (1:1.414)</div>
        <div class="preview-actions-header">
          <a-button class="export-action-btn export-preview-btn" @click="closePreview">返回对话</a-button>
          <a-button class="export-action-btn export-confirm-btn" type="primary" @click="exportChat">导出PDF</a-button>
        </div>
      </div>

      <!-- 预览内容区域 -->
      <div class="preview-content-area">
        <!-- 加载状态 - 添加过渡动画 -->
        <transition name="fade">
          <div v-if="previewLoading" class="preview-loading">
            <a-spin :indicator="loadingIcon" tip="正在生成预览..."></a-spin>
          </div>
        </transition>

        <!-- 预览内容 - 只在不加载时显示 -->
        <transition name="fade">
          <div v-if="!previewLoading" class="preview-content">
            <!-- 预览画布 -->
            <div class="preview-canvas-container">
              <!-- 直接渲染预览内容 -->
              <div class="preview-canvas" v-html="previewContent"></div>
              <!-- 添加纸张尺寸标签 -->
              <div class="paper-size-label">{{ paperSize.toUpperCase() }}</div>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <!-- 导出设置表单 -->
    <template v-else>
      <!-- 模态窗标题 -->
      <div class="modal-custom-title">{{ 
        (temporaryIsSelectionMode || props.isSelectionMode) ? '导出选中消息' : '导出对话记录' 
      }}</div>

      <!-- 导出说明 -->
      <div class="export-description">
        <p v-if="(temporaryIsSelectionMode || props.isSelectionMode)">
          已选中 <strong>{{ 
            (temporarySelectedMessages.length > 0 ? temporarySelectedMessages : props.selectedMessages)?.length || 0 
          }}</strong> 条消息 
          ({{ selectedUserMessages }} 条用户消息，{{ selectedAIMessages }} 条智能体消息<span v-if="selectedSystemMessages > 0">，{{ selectedSystemMessages }} 条系统消息</span>)
        </p>
        <p v-else>您可以将当前对话导出为不同格式，便于保存和分享。</p>
      </div>

      <!-- 导出选项 -->
      <div class="export-container">
        <!-- 导出格式选择 -->
        <div class="format-selector">
          <a-radio-group v-model:value="exportFormat" button-style="solid" class="format-group">
            <a-radio-button value="pdf">PDF文档</a-radio-button>
            <a-radio-button value="text">纯文本</a-radio-button>
            <a-radio-button value="markdown">Markdown</a-radio-button>
          </a-radio-group>
        </div>

        <!-- 通用选项 -->
        <div class="option-group">
          <a-checkbox v-model:checked="includeThinking">包含思考过程</a-checkbox>
          <a-checkbox v-model:checked="includeToolCalls">包含工具调用内容</a-checkbox>
          <a-checkbox 
            v-model:checked="includeSystemMessages" 
            v-if="exportFormat !== 'text' && !(temporaryIsSelectionMode || props.isSelectionMode)"
          >
            包含系统消息
          </a-checkbox>
        </div>

        <!-- 格式特定选项 -->
        <div class="format-options">
          <!-- PDF专用选项 -->
          <div v-if="exportFormat === 'pdf'" class="format-specific-options">
            <div class="option-row">
              <span class="option-label">质量：</span>
              <a-radio-group v-model:value="exportQuality" class="option-control">
                <a-radio value="normal">普通</a-radio>
                <a-radio value="high">高质量</a-radio>
              </a-radio-group>
            </div>
            <div class="option-row">
              <span class="option-label">纸张：</span>
              <a-select v-model:value="paperSize" class="option-control paper-select">
                <a-select-option value="a4">A4 (210×297mm)</a-select-option>
                <a-select-option value="a3">A3 (297×420mm)</a-select-option>
                <a-select-option value="a5">A5 (148×210mm)</a-select-option>
                <a-select-option value="b4">B4 (250×353mm)</a-select-option>
                <a-select-option value="b5">B5 (176×250mm)</a-select-option>
              </a-select>
            </div>
            <div class="option-row">
              <span class="option-label">缩放：</span>
              <div class="option-control scale-control">
                <a-slider
                    v-model:value="scaleValue"
                    :min="50"
                    :max="150"
                    :step="5"
                    class="scale-slider"
                />
                <a-input-number
                    v-model:value="scaleValue"
                    :min="50"
                    :max="150"
                    :step="5"
                    class="scale-input"
                    addon-after="%"
                />
              </div>
            </div>
            <div class="option-row">
              <span class="option-label">版权：</span>
              <a-select v-model:value="copyrightPosition" class="option-control paper-select">
                <a-select-option value="page-bottom">每页底部</a-select-option>
                <a-select-option value="last-page">最后一页</a-select-option>
              </a-select>
            </div>
          </div>

          <!-- 纯文本专用选项 -->
          <div v-if="exportFormat === 'text'" class="format-specific-options">
            <div class="option-row">
              <a-checkbox v-model:checked="includeRoleLabels">包含角色标签</a-checkbox>
            </div>
            <div class="option-row">
              <a-checkbox v-model:checked="simplifyContent">简化内容（移除格式）</a-checkbox>
            </div>
          </div>

          <!-- Markdown专用选项 -->
          <div v-if="exportFormat === 'markdown'" class="format-specific-options">
            <div class="option-row">
              <a-checkbox v-model:checked="includeCodeblockSyntax">保留代码块语法高亮</a-checkbox>
            </div>
            <div class="option-row">
              <a-checkbox v-model:checked="includeMetadata">包含元数据头</a-checkbox>
            </div>
          </div>
        </div>

        <!-- 导出提示 -->
        <div class="export-tips" v-if="exportFormat === 'pdf'">
          <a-alert
              message="高质量导出可能需要更长时间，文件体积也会更大，缩放比例影响内容在页面上的大小，可根据内容多少调整。"
              type="info"
              :show-icon="false"
          />
        </div>

        <div class="export-tips" v-else-if="exportFormat === 'text'">
          <a-alert
              message="纯文本格式保留原始内容，但会丢失格式和样式。适合需要进一步编辑或处理文本的场景。"
              type="info"
              :show-icon="false"
          />
        </div>

        <div class="export-tips" v-else>
          <a-alert
              message="Markdown格式保留文本格式和代码高亮，便于在支持Markdown的平台上分享。"
              type="info"
              :show-icon="false"
          />
        </div>
      </div>

      <!-- 进度条 - 修改为不再与表单互斥显示 -->
      <div class="progress-container" v-if="exporting">
        <a-progress :percent="exportProgress" status="active" :stroke-color="{ from: '#108ee9', to: '#87d068' }"/>
        <div class="progress-text">{{ exportProgressText }}</div>
      </div>

      <div class="modal-footer">
        <a-button class="export-action-btn export-cancel-btn" @click="confirmVisible = false" :disabled="exporting">取消</a-button>
        <a-button
            v-if="exportFormat === 'pdf'"
            type="default"
            @click="showPreview"
            :disabled="exporting"
            class="export-action-btn export-preview-btn"
        >
          预览
        </a-button>
        <a-button class="export-action-btn export-confirm-btn" type="primary" @click="exportChat" :disabled="exporting">
          导出
        </a-button>
      </div>
    </template>
  </a-modal>
  </div>
</template>

<script setup lang="ts">
import {computed, h, nextTick, onMounted, onUnmounted, ref, watch} from 'vue';
import {useChatStore} from '@/stores/chat-store';
import PDFIcon from "@/components/icons/PdfIcon.vue";
import {type PaperSize, PdfExporter, PdfPreviewGenerator} from '@/services/pdf';
import NotificationService from '@/utils/NotificationService';
import {LoadingOutlined} from '@ant-design/icons-vue';
import '@/assets/styles/export-button.css';

// 定义Props
interface Props {
  isSelectionMode?: boolean;
  hasSelection?: boolean;
  selectedMessages?: any[];
}

const props = withDefaults(defineProps<Props>(), {
  isSelectionMode: false,
  hasSelection: false,
  selectedMessages: () => []
});

const chatStore = useChatStore();
const confirmVisible = ref(false);
const exporting = ref(false);

// 临时存储选中的消息（用于处理自定义事件）
const temporarySelectedMessages = ref<any[]>([]);
const temporaryIsSelectionMode = ref(false);

// 加载图标
const loadingIcon = h(LoadingOutlined, {style: {fontSize: '24px'}});

// 导出格式和选项
const exportFormat = ref('pdf'); // 默认PDF格式
const includeThinking = ref(false); // 默认不包含思考过程
const includeToolCalls = ref(false); // 默认不包含工具调用内容
const includeSystemMessages = ref(false); // 默认不包含系统消息
const exportQuality = ref('high'); // 默认使用高质量导出
const paperSize = ref('a4'); // 默认A4纸张
const includeRoleLabels = ref(true); // 默认包含角色标签
const simplifyContent = ref(false); // 默认不简化内容
const includeCodeblockSyntax = ref(true); // 默认保留代码块语法高亮
const includeMetadata = ref(true); // 默认包含元数据头
const scaleValue = ref(100); // 默认缩放比例100%
const copyrightPosition = ref('last-page'); // 默认版权位置：最后一页

// 导出进度相关
const exportProgress = ref(0);
const exportProgressText = ref('准备导出...');

// 预览相关
const previewMode = ref(false); // 是否为预览模式
const previewLoading = ref(false); // 预览是否正在加载
const previewContent = ref(''); // HTML预览内容

// 选中消息统计信息 - 支持临时选中的消息
const selectedUserMessages = computed(() => {
  const messages = temporarySelectedMessages.value.length > 0 ? temporarySelectedMessages.value : props.selectedMessages;
  if (!messages) return 0;
  return messages.filter(msg => msg.role === 'user').length;
});

const selectedAIMessages = computed(() => {
  const messages = temporarySelectedMessages.value.length > 0 ? temporarySelectedMessages.value : props.selectedMessages;
  if (!messages) return 0;
  return messages.filter(msg => msg.role === 'assistant').length;
});

const selectedSystemMessages = computed(() => {
  const messages = temporarySelectedMessages.value.length > 0 ? temporarySelectedMessages.value : props.selectedMessages;
  if (!messages) return 0;
  return messages.filter(msg => msg.role === 'system').length;
});

// 监听导出格式变化，重置相关选项
watch(exportFormat, (newFormat) => {
  if (newFormat === 'pdf') {
    exportQuality.value = 'high';
  }
});

// 关闭模态窗时清理预览内容
const handleModalClose = () => {
  if (previewMode.value) {
    previewMode.value = false;
    previewLoading.value = false;
    previewContent.value = ''; // 清空预览内容
  }
  
  // 清理临时数据
  temporarySelectedMessages.value = [];
  temporaryIsSelectionMode.value = false;
};

// 显示导出确认对话框（带默认格式）
const showExportConfirmWithFormat = (defaultFormat: 'pdf' | 'text' | 'markdown' = 'pdf') => {
  // 检查是否正在生成对话
  if (chatStore.isProcessing) {
    NotificationService.info('请等待对话生成完成后再导出');
    return;
  }

  // 如果没有对话内容，提示用户
  if (chatStore.messages.length === 0) {
    NotificationService.info('当前没有对话内容可导出');
    return;
  }

  // 如果是选择模式，确保临时数据是最新的
  if (props.isSelectionMode) {
    // 强制更新临时数据为最新的props数据
    temporarySelectedMessages.value = props.selectedMessages ? [...props.selectedMessages] : [];
    temporaryIsSelectionMode.value = true;
    
  }
  
  // 检查选中状态
  const isCurrentSelectionMode = temporaryIsSelectionMode.value || props.isSelectionMode;
  const currentHasSelection = temporarySelectedMessages.value.length > 0 || props.hasSelection;
  
  if (isCurrentSelectionMode && !currentHasSelection) {
    NotificationService.info('请先选择要导出的消息');
    return;
  }

  // 设置默认导出格式
  exportFormat.value = defaultFormat;

  confirmVisible.value = true;
};

// 执行导出
const exportChat = async () => {
  if (previewMode.value) {
    previewMode.value = false; // 如果是从预览模式来的，先退出预览模式
  }

  try {
    // 设置导出状态
    exporting.value = true;
    exportProgress.value = 0;

    // 在导出前，确保临时数据是最新的
    if (props.isSelectionMode) {
      temporarySelectedMessages.value = props.selectedMessages ? [...props.selectedMessages] : [];
      temporaryIsSelectionMode.value = true;
      
    }

    // 如果是选择模式，设置选中的消息到导出器中
    const isCurrentSelectionMode = temporaryIsSelectionMode.value || props.isSelectionMode;
    const currentSelectedMessages = temporarySelectedMessages.value.length > 0 ? temporarySelectedMessages.value : props.selectedMessages;
    
    if (isCurrentSelectionMode && currentSelectedMessages && currentSelectedMessages.length > 0) {
      PdfExporter.setSelectedMessages(currentSelectedMessages);
      PdfPreviewGenerator.setSelectedMessages(currentSelectedMessages);
    } else {
      // 清除选中的消息，使用全部消息
      PdfExporter.clearSelectedMessages();
      PdfPreviewGenerator.clearSelectedMessages();
    }

    // 设置进度回调
    PdfExporter.setProgressCallback((progress) => {
      exportProgress.value = progress.percent;
      exportProgressText.value = progress.stage;
    });

    // 生成文件名，格式为：MCP对话记录_年月日时分秒.扩展名
    const now = new Date();
    const dateStr = `${now.getFullYear()}${(now.getMonth() + 1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}${now.getSeconds().toString().padStart(2, '0')}`;

    // 根据选择的格式执行不同的导出操作
    if (exportFormat.value === 'pdf') {
      const filename = `MCP对话记录_${dateStr}.pdf`;

      // 使用PDF导出方法

      await PdfExporter.exportPdf({
        format: 'pdf',
        quality: exportQuality.value as 'normal' | 'high',
        paperSize: paperSize.value as PaperSize,
        scale: scaleValue.value,
        copyrightPosition: copyrightPosition.value as 'page-bottom' | 'last-page',
        includeThinking: includeThinking.value,
        includeToolCalls: includeToolCalls.value,
        includeSystemMessages: includeSystemMessages.value
      }, filename);

      NotificationService.success('PDF导出成功');
    } else if (exportFormat.value === 'text') {
      const filename = `MCP对话记录_${dateStr}.txt`;

      // 导出纯文本

      await PdfExporter.exportText({
        format: 'text',
        includeThinking: includeThinking.value,
        includeSystemMessages: includeSystemMessages.value,
        includeToolCalls: includeToolCalls.value,
        includeRoleLabels: includeRoleLabels.value,
        simplifyContent: simplifyContent.value
      }, filename);

      NotificationService.success('纯文本导出成功');
    } else if (exportFormat.value === 'markdown') {
      const filename = `MCP对话记录_${dateStr}.md`;

      // 导出Markdown

      await PdfExporter.exportMarkdown({
        format: 'markdown',
        includeThinking: includeThinking.value,
        includeSystemMessages: includeSystemMessages.value,
        includeToolCalls: includeToolCalls.value,
        includeCodeblockSyntax: includeCodeblockSyntax.value,
        includeMetadata: includeMetadata.value
      }, filename);

      NotificationService.success('Markdown导出成功');
    }

    // 关闭对话框
    confirmVisible.value = false;
  } catch (error) {
    // 导出失败
    NotificationService.error('导出失败，请重试');
    console.error('导出错误:', error);
  } finally {
    // 无论成功失败，重置导出状态
    setTimeout(() => {
      exporting.value = false;
      exportProgress.value = 0;
    }, 500);
  }
};

// 预览PDF - 简化版本
const showPreview = async () => {
  if (exporting.value || previewLoading.value) {
    return;
  }

  try {
    // 在预览前，确保临时数据是最新的
    if (props.isSelectionMode) {
      temporarySelectedMessages.value = props.selectedMessages ? [...props.selectedMessages] : [];
      temporaryIsSelectionMode.value = true;
      
    }
    
    // 如果是选择模式，设置选中的消息到预览生成器中
    const isCurrentSelectionMode = temporaryIsSelectionMode.value || props.isSelectionMode;
    const currentSelectedMessages = temporarySelectedMessages.value.length > 0 ? temporarySelectedMessages.value : props.selectedMessages;
    
    if (isCurrentSelectionMode && currentSelectedMessages && currentSelectedMessages.length > 0) {
      PdfPreviewGenerator.setSelectedMessages(currentSelectedMessages);
    } else {
      // 清除选中的消息，使用全部消息
      PdfPreviewGenerator.clearSelectedMessages();
    }

    // 设置预览模式
    previewMode.value = true;
    previewLoading.value = true;

    // 等待DOM更新
    await nextTick();

    // 准备渲染预览

    // 等待模态窗完全展开
    await new Promise(resolve => setTimeout(resolve, 800));

    // 创建预览内容
    await generatePreviewContent();

    // 最后关闭加载状态
    previewLoading.value = false;

  } catch (error) {
    previewLoading.value = false;
    previewMode.value = false;
    NotificationService.error('生成预览失败，请重试');
    console.error('预览错误:', error);
  }
};

// 生成预览内容
const generatePreviewContent = async () => {
  try {
    // 使用 PdfPreviewGenerator 生成预览内容
    const previewConfig = {
      paperSize: paperSize.value as PaperSize,
      scale: scaleValue.value,
      copyrightPosition: copyrightPosition.value as 'page-bottom' | 'last-page',
      includeThinking: includeThinking.value,
      includeSystemMessages: includeSystemMessages.value,
      includeToolCalls: includeToolCalls.value
    };

    previewContent.value = await PdfPreviewGenerator.generatePreview(previewConfig);
    
  } catch (error) {
    console.error('生成预览内容失败:', error);
    NotificationService.error('生成预览内容失败');
  }
};

// 关闭预览
const closePreview = () => {
  previewMode.value = false;
  previewLoading.value = false;
  previewContent.value = ''; // 清空预览内容
};


// 当组件挂载时
onMounted(() => {
  
  // 监听显示导出对话框事件
  const handleShowExportDialog = (event: CustomEvent) => {
    const { isSelectionMode: selectionMode, selectedMessages: messages, defaultFormat } = event.detail;
    
    // 如果是选择模式，需要验证是否有选中的消息
    if (selectionMode) {
      if (!messages || messages.length === 0) {
        NotificationService.info('请先选择要导出的消息');
        return;
      }
      
      // 设置选中的消息
      // 由于我们无法直接设置props，我们需要通过其他方式来传递选中的消息
      // 这里我们可以临时存储选中的消息
      temporarySelectedMessages.value = messages;
      temporaryIsSelectionMode.value = true;
    }
    
    // 设置默认导出格式 - 直接调用showExportConfirmWithFormat
    if (defaultFormat) {
      showExportConfirmWithFormat(defaultFormat);
    } else {
      showExportConfirmWithFormat('pdf'); // 默认PDF格式
    }
  };
  
  document.addEventListener('show-export-dialog', handleShowExportDialog as EventListener);
  
  // 在组件卸载时移除事件监听
  onUnmounted(() => {
    document.removeEventListener('show-export-dialog', handleShowExportDialog as EventListener);
  });
});
</script>

<style scoped>
.export-modal :deep(.ant-modal-content) {
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
}

/* 隐藏原始标题 */
.export-modal :deep(.ant-modal-header) {
  display: none;
}

/* 调整内容区域的上边距 */
.export-modal :deep(.ant-modal-body) {
  padding-top: 24px;
}

.format-group :deep(.ant-radio-button-wrapper) {
  flex: 1;
  text-align: center;
}

.export-tips :deep(.ant-alert-description) {
  font-size: 12px;
}

.export-tips :deep(.ant-alert-info) {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%) !important;
  font-size: 13px !important;
  color: #1e40af !important;
}

.export-tips :deep(p) {
  margin-bottom: 5px;
}

.export-tips :deep(p:last-child) {
  margin-bottom: 0;
}

/* PDF页面容器样式 */
:deep(.pdf-pages-container) {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 20px 0 20px 0; /* 底部增加更多空间 */
  gap: 0; /* 减少页面之间的间距 */
}

/* 主容器样式 */
:deep(.pdf-main-container) {
  box-shadow: 0 0 15px rgba(0, 0, 0, 0.1); /* 恢复阴影效果 */
  border-radius: 2px;
  overflow: visible;
  margin-bottom: 20px; /* 增加底部间距 */
}

/* 内容容器样式 */
:deep(.pdf-content-container) {
  background-color: #f5f7fa;
}

/* 页面分隔线样式 */
:deep(.pdf-page-divider) {
  margin: 0;
  z-index: 10;
  border: none; /* 移除边框 */
}

/* 移除不再需要的样式 */
:deep(.pdf-page) {
  display: none;
}

:deep(.pdf-export-container) {
  background-color: #f5f7fa !important; /* 与导出PDF背景色保持一致 */
}

/* 移除导出时的页码样式 */
:deep(.page-number) {
  display: none;
}

/* 预览页码样式 */
:deep(.page-number-preview) {
  font-weight: 500;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  letter-spacing: 0.5px;
}

/* PDF预览中的代码框样式 - 移除shadow，使用border */
:deep(.pdf-main-container .code-block-wrapper) {
  box-shadow: none !important;
  border: 1px solid rgba(200, 220, 240, 0.4) !important;
}

/* PDF页面内容样式 */
:deep(.pdf-page-content) {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.full-modal :deep(.ant-modal-content) {
  border-radius: 0;
  box-shadow: none;
  height: 100%;
  display: flex;
  flex-direction: column;
}

/* 移除原来的标题相关样式 */
.full-modal :deep(.ant-modal-header) {
  display: none;
}

.full-modal :deep(.ant-modal-body) {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background-color: #f9f9f9;
}

.full-modal :deep(.ant-modal-footer) {
  border-top: 1px solid #f0f0f0;
  padding: 15px 20px;
  background-color: #f9f9f9;
}
</style>
