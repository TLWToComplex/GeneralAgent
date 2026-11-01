<template>
  <MessageSelection v-if="shouldShowMessage" :message-id="messageId" :is-selection-mode="isSelectionMode || false"
    :is-selected="isSelected || false" :selection-position="selectionPosition || 'none'"
    @selection-changed="handleSelectionChanged">
    <div :class="['message', messageClass, { 'is-editing': isEditMode }]">
      <div class="message-avatar">
        <a-avatar v-if="isUserMessage && userAvatarUrl" :src="userAvatarUrl" :style="avatarStyle" :size="35" />
        <a-avatar v-else-if="isUserMessage" :style="avatarStyle" :size="35">
          {{ userAvatarText }}
        </a-avatar>
        <template v-else>
          <template v-if="shouldUseAgentIdentity">
            <a-avatar v-if="agentAvatar" :src="agentAvatar" :style="agentAvatarStyle" :size="35" />
            <div v-else-if="isOrchestratorAgent" class="assistant-avatar-icon orchestrator-avatar">
              <OrchestratorIcon class="message-avatar-icon" style="width: 20px; height: 33px;" />
            </div>
            <a-avatar v-else :style="agentAvatarStyle" :size="35">
              {{ agentName ? agentName.charAt(0).toUpperCase() : 'A' }}
            </a-avatar>
          </template>
          <template v-else>
            <div v-if="shouldShowIcon(currentModelName, 'qwen')" class="assistant-avatar-icon"
              :style="{ backgroundColor: 'transparent' }">
              <QwenIcon class="message-avatar-icon" />
            </div>
            <div v-else-if="shouldShowIcon(currentModelName, 'deepseek')" class="assistant-avatar-icon"
              :style="{ backgroundColor: 'transparent' }">
              <DeepSeekIcon class="message-avatar-icon" />
            </div>
            <div v-else-if="resolveGlmIcon(currentModelName) === 'zai'" class="assistant-avatar-icon"
              :style="{ backgroundColor: 'transparent' }">
              <ZaiIcon class="message-avatar-icon" />
            </div>
            <div v-else-if="resolveGlmIcon(currentModelName) === 'zhipu'" class="assistant-avatar-icon"
              :style="{ backgroundColor: 'transparent' }">
              <ZhipuIcon class="message-avatar-icon" />
            </div>
            <a-avatar v-else :style="assistantAvatarStyle" :size="35">{{ assistantAvatarText }}</a-avatar>
          </template>
        </template>
      </div>
      <div class="message-content" ref="messageContentRef">
        <div class="message-role">{{ displayName }}</div>

        <div v-if="(message.files && message.files.length > 0) || displayPendingCaptureCards.length > 0"
          class="message-files">
          <div v-if="displayPendingCaptureCards.length > 0" class="message-pending-capture-list">
            <div v-for="file in displayPendingCaptureCards" :key="file.key" class="message-pending-capture-card"
              :class="{ 'is-dissolving': isPendingCaptureDissolving }">
              <div class="message-pending-capture-visual">
                <div class="message-pending-capture-shimmer"></div>
                <div class="message-pending-capture-particles" aria-hidden="true">
                  <span v-for="particle in pendingCaptureParticles" :key="`${file.key}-particle-${particle.id}`" :style="{
                    '--particle-origin-x': particle.originX,
                    '--particle-origin-y': particle.originY,
                    '--particle-x': particle.targetX,
                    '--particle-y': particle.targetY,
                    '--particle-scale': particle.scale,
                    '--particle-size': particle.size,
                    '--particle-delay': particle.delay
                  }"></span>
                </div>
                <div class="message-pending-capture-bar">
                  <span></span><span></span><span></span>
                </div>
                <div class="message-pending-capture-lines">
                  <div class="message-pending-capture-line w-74"></div>
                  <div class="message-pending-capture-line w-52"></div>
                  <div class="message-pending-capture-line w-66"></div>
                </div>
                <div class="message-pending-capture-badge">正在截取网页页面</div>
              </div>
            </div>
          </div>
          <ImageGallery :images="messageImageFiles"
            :should-apply-screenshot-reveal-class="shouldApplyScreenshotRevealClass"
            :is-screenshot-reveal-active="isScreenshotRevealActive"
            @image-click="handleImageFileClick" />

          <template v-for="entry in messageDocumentFiles" :key="`file-${entry.index}-${entry.file.name}`">
            <ArtifactCard :title="entry.file.name" :lang="getFileExtension(entry.file.name)" :is-complete="true"
              :icon="getIconHtml(entry.file)" :id="getFileArtifactId(entry.index)"
              :is-selected="activeArtifactId === getFileArtifactId(entry.index)"
              @click.stop="handleFileClick(entry.file, entry.index)" />
          </template>
        </div>

        <template v-if="!isEditMode">
          <component :is="showTaskProcessFold ? 'details' : 'div'" v-if="hasProcessContent"
            :class="{ 'message-process': showTaskProcessFold }" @toggle="handleProcessToggle($event, 'task')" @click.stop>
            <summary v-if="showTaskProcessFold" class="message-process-summary">
              <span>{{ taskProcessLabel }}</span>
              <svg class="message-process-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                <path d="m4.5 3 3 3-3 3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </summary>
            <!-- 折叠即卸载：收起时 body 不挂组件树 -->
            <div v-if="!showTaskProcessFold || processDetailsOpen['task']"
              :class="{ 'message-process-body': showTaskProcessFold }">
              <div v-if="showStandaloneReasoning" class="reasoning-content tr" @click.stop>
                <ThinkingState :active="!standaloneReasoningDone" :expanded="standaloneExpanded"
                  :duration="standaloneLabelSuffix" @toggle="toggleTr(standaloneReasoningPanelKey)" />
                <div class="tr-collapsible" :inert="!standaloneExpanded" :class="{ 'is-collapsed': !standaloneExpanded }">
                  <!-- 折叠即卸载：收起动画跑完后整棵内容子树移出组件树，流式期间不再渲染/测量 -->
                  <div v-if="isTrRendered(standaloneReasoningPanelKey)" class="tr-inner">
                    <div :ref="el => setTrViewportRef(standaloneReasoningPanelKey, el)" class="tr-viewport"
                      :class="{ 'is-scroll': standaloneExpanded, 'hide-scrollbar': !trSbVisible[standaloneReasoningPanelKey] }"
                      :style="{
                        height: getTrViewH(standaloneReasoningPanelKey) + 'px',
                        maskImage: getTrMask(standaloneReasoningPanelKey, standaloneExpanded),
                        WebkitMaskImage: getTrMask(standaloneReasoningPanelKey, standaloneExpanded)
                      }" @scroll="onTrScroll(standaloneReasoningPanelKey, $event)"
                      @wheel.passive="onTrUserScrollIntent(standaloneReasoningPanelKey)"
                      @touchstart.passive="onTrUserScrollIntent(standaloneReasoningPanelKey)"
                      @touchmove.passive="onTrUserScrollIntent(standaloneReasoningPanelKey)">
                      <div class="tr-stream" :ref="el => setTrStreamRef(standaloneReasoningPanelKey, el)"
                        :style="{ transform: `translateY(${getTrTranslate(standaloneReasoningPanelKey, standaloneExpanded)}px)` }">
                        <div class="reasoning-text">
                          <MarkdownRenderer :content="message.reasoning_content || ''" :role="message.role"
                            :is-reasoning="true" :is-streaming="message.isStreaming" use-external-image-viewer
                            @image-click="handleImageClick" @open-artifact="handleOpenArtifact" />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <TodoListDisplay v-if="shouldUseOrchestratorRendering && message.todos" :todos="message.todos" />
              <OrchestrateToolCallDisplay v-if="!useOrchestratorBlocks && shouldUseOrchestratorRendering" :message="message" />
              <template v-for="section in taskProcessSections" :key="section.key">
                <div v-if="section.type === 'content'" class="message-text">
                  <MarkdownRenderer :content="section.content" :role="message.role" :active-artifact-id="activeArtifactId" disable-artifacts
                    :message-id="messageId" :is-streaming="message.role === 'assistant' && message.isStreaming"
                    use-external-image-viewer @image-click="handleImageClick" @open-artifact="handleOpenArtifact" />
                </div>
                <component :is="useAgentProcessUI ? 'details' : 'div'" v-else
                  :class="{ 'message-process-group': useAgentProcessUI }" @toggle="handleProcessToggle($event, section.key)" @click.stop>
                  <summary v-if="useAgentProcessUI" class="message-process-summary">
                    <span :class="{ 'pb-shimmer': isProcessSectionActive(section) }">{{ getProcessSectionSummary(section) }}</span>
                    <svg class="message-process-chevron" width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                      <path d="m4.5 3 3 3-3 3" stroke="currentColor" stroke-width="1.25" stroke-linecap="round" stroke-linejoin="round" />
                    </svg>
                  </summary>
                  <!-- 折叠即卸载：收起时 body 不挂组件树 -->
                  <div v-if="!useAgentProcessUI || processDetailsOpen[section.key]"
                    :class="{ 'message-process-group-body': useAgentProcessUI }">
                    <template v-for="{ block, index } in section.entries" :key="getOrchestratorBlockKey(block, index)">
                      <OrchestrateToolCallDisplay v-if="block.type === 'tools'" :message="message"
                        :tool-calls="getToolCallsForBlock(block)" />
                      <div v-else-if="block.type === 'reasoning'" class="reasoning-content tr" @click.stop>
                        <ThinkingState :active="isReasoningBlockThinking(index)"
                          :expanded="isBlockExpanded(getOrchestratorBlockKey(block, index))"
                          :duration="getBlockLabelSuffix(getOrchestratorBlockKey(block, index))"
                          @toggle="toggleTr(getOrchestratorBlockKey(block, index))" />
                        <div class="tr-collapsible" :inert="!isBlockExpanded(getOrchestratorBlockKey(block, index))"
                          :class="{ 'is-collapsed': !isBlockExpanded(getOrchestratorBlockKey(block, index)) }">
                          <!-- 折叠即卸载：收起动画跑完后整棵内容子树移出组件树，流式期间不再渲染/测量 -->
                          <div v-if="isTrRendered(getOrchestratorBlockKey(block, index))" class="tr-inner">
                            <div :ref="el => setTrViewportRef(getOrchestratorBlockKey(block, index), el)" class="tr-viewport"
                              :class="{
                                'is-scroll': isBlockExpanded(getOrchestratorBlockKey(block, index)),
                                'hide-scrollbar': !trSbVisible[getOrchestratorBlockKey(block, index)]
                              }" :style="{
                                height: getTrViewH(getOrchestratorBlockKey(block, index)) + 'px',
                                maskImage: getTrMask(getOrchestratorBlockKey(block, index), isBlockExpanded(getOrchestratorBlockKey(block, index))),
                                WebkitMaskImage: getTrMask(getOrchestratorBlockKey(block, index), isBlockExpanded(getOrchestratorBlockKey(block, index)))
                              }" @scroll="onTrScroll(getOrchestratorBlockKey(block, index), $event)"
                              @wheel.passive="onTrUserScrollIntent(getOrchestratorBlockKey(block, index))"
                              @touchstart.passive="onTrUserScrollIntent(getOrchestratorBlockKey(block, index))"
                              @touchmove.passive="onTrUserScrollIntent(getOrchestratorBlockKey(block, index))">
                              <div class="tr-stream" :ref="el => setTrStreamRef(getOrchestratorBlockKey(block, index), el)"
                                :style="{ transform: `translateY(${getTrTranslate(getOrchestratorBlockKey(block, index), isBlockExpanded(getOrchestratorBlockKey(block, index)))}px)` }">
                                <div class="reasoning-text">
                                  <MarkdownRenderer :content="block.content" :role="message.role" :is-reasoning="true"
                                    :is-streaming="message.role === 'assistant' && message.isStreaming"
                                    use-external-image-viewer @image-click="handleImageClick"
                                    @open-artifact="handleOpenArtifact" />
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </template>
                  </div>
                </component>
              </template>
            </div>
          </component>
          <template v-if="useOrchestratorBlocks">
            <div v-for="(block, index) in taskAnswerBlocks" :key="`answer-${index}`" class="message-text">
              <MarkdownRenderer :content="block.content" :role="message.role" :active-artifact-id="activeArtifactId"
                :message-id="messageId" :is-streaming="message.role === 'assistant' && message.isStreaming"
                use-external-image-viewer @image-click="handleImageClick" @open-artifact="handleOpenArtifact" />
            </div>
          </template>
          <template v-else>
            <div class="message-text" :class="{ 'is-thinking-placeholder': showLoadingRipple }"
              v-if="shouldShowMessageText">
              <template v-if="showUserPlainText">
                <div class="plain-text">{{ message.display_content || message.content }}</div>
              </template>
              <template v-else-if="showLoadingRipple">
                <ThinkingState active :collapsible="false" :label="loadingPlaceholderLabel" />
              </template>
              <template v-else>
                <MarkdownRenderer :content="message.display_content || message.content" :role="message.role"
                  :active-artifact-id="activeArtifactId" :message-id="messageId"
                  :is-streaming="message.role === 'assistant' && message.isStreaming" use-external-image-viewer
                  @image-click="handleImageClick" @open-artifact="handleOpenArtifact" />
              </template>
            </div>
          </template>
        </template>

        <div v-if="!isEditMode && isAgentWaiting" class="agent-waiting-status" role="status" aria-live="polite">
          <span class="pb-shimmer">{{ agentWaitingLabel }}</span>
        </div>

        <OrchestrateToolCallDisplay v-if="!shouldUseOrchestratorRendering" :message="message" />

        <div v-if="message.role === 'assistant' && (message as any).isStopped" class="stop-tip">
          已停止输出
        </div>

        <div
          v-if="message.role === 'assistant' && (message as any).kb_citations && (message as any).kb_citations.length > 0 && !message.isStreaming"
          class="kb-citations-collapse">
          <a-collapse v-model:activeKey="activeCitationPanels" destroy-inactive-panel @change="handleCitationCollapseChange">
            <a-collapse-panel header="知识引用" key="kb">
              <div class="kb-citations-stage" ref="kbPanelRoot">
                <div class="kb-citations-summary">
                  <span class="kb-summary-text">共 {{ citationOverview.total }} 条引用</span>
                  <span class="kb-summary-divider">·</span>
                  <span class="kb-summary-text">{{ citationOverview.sourceCount }} 个来源</span>
                  <span class="kb-summary-divider">·</span>
                  <span class="kb-summary-text">平均相关度 {{ citationOverview.averageRelevance }}</span>
                </div>
                <div v-for="(item, idx) in formattedKbCitations" :key="item.__key" class="kb-citation-card"
                  :data-key="item.__key">
                  <div class="kb-citation-header">
                    <div class="kb-citation-main">
                      <span class="kb-citation-caption">片段 {{ formatCitationIndex(idx + 1) }}</span>
                      <div class="kb-citation-title-line">
                        <span class="kb-citation-title">{{ getCitationSourceName(item) }}</span>
                      </div>
                      <div class="kb-citation-path">{{ item?.metadata?.source || '未知来源' }}</div>
                    </div>
                    <a-button v-if="getCitationFileUrl(item)" type="default" size="small" class="kb-preview-button"
                      :loading="filePreviewLoading[item.__key]" :disabled="filePreviewLoading[item.__key]"
                      @click.stop="handlePreviewFileInCanvas(item)">
                      <template #icon>
                        <img :src="canvasIcon" class="kb-preview-icon" alt="Canvas" />
                      </template>
                      Canvas 浏览
                    </a-button>
                  </div>
                  <div class="kb-citation-meta-row">
                    <div class="kb-citation-meta-pill">
                      <span class="kb-citation-meta-val">{{ getCitationTypeLabel(item) }}</span>
                    </div>
                    <div v-if="getCitationRelevance(item) !== null" class="kb-citation-meta-pill">
                      <span class="kb-citation-meta-key">相关度</span>
                      <span class="kb-citation-meta-val">{{ formatCitationPercent(getCitationRelevance(item)) }}</span>
                    </div>
                    <div v-if="getCitationScore(item) !== null" class="kb-citation-meta-pill">
                      <span class="kb-citation-meta-key">检索分</span>
                      <span class="kb-citation-meta-val">{{ formatCitationNumeric(getCitationScore(item)) }}</span>
                    </div>
                    <div class="kb-citation-meta-pill">
                      <span class="kb-citation-meta-key">段落</span>
                      <span class="kb-citation-meta-val">{{ item.__lines.length }}</span>
                    </div>
                  </div>
                  <div v-if="getCitationEntities(item).length > 0" class="kb-citation-tags">
                    <span v-for="entity in getCitationEntities(item).slice(0, 3)" :key="entity" class="kb-citation-tag">
                      {{ entity }}
                    </span>
                    <span v-if="getCitationEntities(item).length > 3" class="kb-citation-tag is-muted">
                      +{{ getCitationEntities(item).length - 3 }}
                    </span>
                  </div>
                  <div class="kb-citation-excerpt-shell">
                    <div class="kb-citation-content" :class="{ clamped: !expandedCitation[item.__key] }">
                      <div v-for="(ln, li) in item.__lines" :key="li" class="kb-quote-line">
                        <span class="kb-quote-copy">{{ ln }}</span>
                      </div>
                    </div>
                  </div>
                  <div class="kb-citation-footer">
                    <div class="kb-citation-footprint">
                      <span class="kb-citation-footprint-label">{{ getCitationRelevanceText(item) }}</span>
                    </div>
                    <div class="kb-citation-actions">
                      <a-button type="link" size="small" class="kb-expand-button"
                        @click.stop="toggleCitationExpand(item.__key)">
                        {{ expandedCitation[item.__key] ? '收起' : '展开全文' }}
                      </a-button>
                    </div>
                  </div>
                </div>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </div>

        <InterruptCard v-if="shouldUseOrchestratorRendering && message.interrupt" :message="message" />

        <MessageActions :message="message" @edit-mode-changed="handleEditModeChanged"
          @selection-mode-changed="handleSelectionModeChanged" />
      </div>


      <simple-image-viewer v-model:open="imageViewerOpen" :image-url="currentImageUrl" :image-alt="currentImageAlt"
        :images="conversationImages" />
    </div>
  </MessageSelection>
</template>

<script setup lang="ts">
import ImageGallery from './ImageGallery.vue';
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue';
import type { ComputedRef } from 'vue';
import type { Message, OrchestratorBlock, PendingInputImage, ToolCall } from '@/types/mcp';
import '@/assets/styles/message.css';
import '@/assets/styles/markdown.css';
import MarkdownRenderer from '@/components/common/MarkdownRenderer.vue';
import SimpleImageViewer from './SimpleImageViewer.vue';
import ArtifactCard from '@/components/common/ArtifactCard.vue';
import ThinkingState from './process/ThinkingState.vue';
import { useAgentProgress } from '@/composables/useAgentProgress';
import { readTaskTiming, formatTaskDuration } from '@/utils/taskTiming';
import { groupProcessBlocks, summarizeProcessTools, type ProcessSection } from '@/utils/conversationProcess';
import OrchestrateToolCallDisplay from './OrchestrateToolCallDisplay.vue';
import TodoListDisplay from './TodoListDisplay.vue';
import InterruptCard from './InterruptCard.vue';
import MessageActions from './MessageActions.vue';
import MessageSelection from './MessageSelection.vue';
import EventBus, { MCP_EVENTS } from '@/utils/EventBus';
import StorageService from '@/utils/StorageService';
import { resolveAgentAvatar } from '@/utils/agentAvatar';
import NotificationService from '@/utils/NotificationService';
import { useChatStore } from '@/stores/chat-store';
import QwenIcon from '@/components/icons/llm/qwen.vue';
import DeepSeekIcon from '@/components/icons/llm/deepseek.vue';
import ZhipuIcon from '@/components/icons/llm/zhipu.vue';
import ZaiIcon from '@/components/icons/llm/zai.vue';
import OrchestratorIcon from '@/components/icons/OrchestratorIcon.vue';
import canvasIcon from '@/assets/image/svg/canvas.svg';
import WordSvg from '@/assets/image/svg/Word.svg';
import PdfSvg from '@/assets/image/svg/pdf-icon.svg';
import TxtSvg from '@/assets/image/svg/Txt.svg';
import MarkdownSvg from '@/assets/image/svg/Markdown.svg';
import ExcelSvg from '@/assets/image/svg/Excel.svg';
import PptSvg from '@/assets/image/svg/PPT.svg';
import CadSvg from '@/assets/image/svg/CAD.svg';
import bgPoster from '@/assets/image/jpg/background.jpg';
import { getAgentType, isAgentRenderingType } from '@/utils/agentMode';
import { shouldShowModelIcon } from '@/utils/modelIcon';
import { extractImagesFromMessages, getImagePreviewUrl, isImageFile, mergeViewerImages } from '@/utils/conversationImages';
import { getApiBaseUrl } from '@/utils/RuntimeConfig';
import { downloadKnowledgeBaseDoc } from '@/services/knowledgeBase';
import { isRetrievingKnowledgeBase } from '@/composables/promptEnhancers';

const props = defineProps<{
  message: Message;
  messageIndex: number;
  isSelectionMode?: boolean;
  isSelected?: boolean;
  selectionPosition?: 'none' | 'single' | 'first' | 'middle' | 'last';
  activeArtifactId?: string;
}>();

const chatStore = useChatStore();
const isUserMessage = computed(() => props.message.role === 'user');

const activeAgent = ref<any>(null);
function loadActiveAgent() {
  activeAgent.value = StorageService.getActiveAgent();
}

// 历史消息若已携带所属智能体配置，应优先按消息自身归属渲染，
// 避免切换到其他会话后被当前全局 activeAgent 覆盖头像与名称。
const renderAgent = computed(() => props.message.agentConfig || activeAgent.value || null);

const agentType = computed(() => {
  return getAgentType(renderAgent.value);
});

const isOrchestratorAgent = computed(() => {
  return agentType.value === 'orchestrator';
});

// 普通模型回复也会生成分块；名称和头像只依据智能体配置判断。
const shouldUseAgentIdentity = computed(() => isAgentRenderingType(agentType.value));
// 普通模型也有 orchestratorBlocks，不能用分块是否存在判断智能体模式。
const useAgentProcessUI = computed(() => props.message.role === 'assistant' && shouldUseAgentIdentity.value);
// 生成时直接展示过程；流式结束后才创建默认收起的外层任务折叠。
const showTaskProcessFold = computed(() => useAgentProcessUI.value && !props.message.isStreaming);
const { isWaiting: isAgentWaiting, waitingLabel: agentWaitingLabel } = useAgentProgress(
  () => props.message, () => useAgentProcessUI.value
);

const orchestratorBlocks = computed(() => props.message.orchestratorBlocks || []);
// 历史消息恢复时可能未激活智能体，此时仍需按消息自身的结构化数据走 deepagent 渲染
const hasOrchestratorPayload = computed(() => {
  return props.message.role === 'assistant' && orchestratorBlocks.value.length > 0;
});

const shouldUseOrchestratorRendering = computed(() => {
  return shouldUseAgentIdentity.value || hasOrchestratorPayload.value;
});
const useOrchestratorBlocks = computed(() => {
  return shouldUseOrchestratorRendering.value && props.message.role === 'assistant' && orchestratorBlocksToRender.value.length > 0;
});
const reasoningBlocksToRender = computed(() => {
  if (!shouldUseOrchestratorRendering.value) {
    return [];
  }
  return orchestratorBlocksToRender.value.filter((block): block is Extract<OrchestratorBlock, { type: 'reasoning' }> => {
    return block.type === 'reasoning' && !!block.content?.trim();
  });
});
const hasReasoningBlocks = computed(() => reasoningBlocksToRender.value.length > 0);
const standaloneReasoningPanelKey = 'reasoning-standalone';
const showStandaloneReasoning = computed(() => {
  return props.message.role === 'assistant'
    && !!props.message.reasoning_content?.trim()
    && !hasReasoningBlocks.value;
});
const orchestratorToolCallMap = computed(() => {
  const map = new Map<string, ToolCall>();
  (props.message.tool_calls || []).forEach(t => map.set(t.id, t));
  return map;
});
const orchestratorBlocksToRender = computed(() => {
  if (!shouldUseOrchestratorRendering.value) {
    return [];
  }
  return orchestratorBlocks.value.filter(block => {
    if (block.type === 'tools') return block.toolCallIds.length > 0;
    return !!block.content;
  });
});
// 外层收起整个任务过程，内部正文保持普通文本，思考和工具各用自己的标题。
// 最后一段非正文块之后的内容作为最终回答；保留前缀索引供思考面板使用。
const taskProcessEnd = computed(() => {
  const blocks = orchestratorBlocksToRender.value;
  for (let index = blocks.length - 1; index >= 0; index--) {
    if (blocks[index].type !== 'content') return index + 1;
  }
  return 0;
});
const taskProcessBlocks = computed(() => orchestratorBlocksToRender.value.slice(0, taskProcessEnd.value));
const taskAnswerBlocks = computed(() => orchestratorBlocksToRender.value.slice(taskProcessEnd.value)
  .filter((block): block is Extract<OrchestratorBlock, { type: 'content' }> => block.type === 'content'));

const taskProcessSections = computed(() => groupProcessBlocks(taskProcessBlocks.value));
function isProcessSectionActive(section: Extract<ProcessSection, { type: 'process' }>) {
  if (!useAgentProcessUI.value || !props.message.isStreaming || props.message.interrupt
    || (props.message as Message & { isStopped?: boolean }).isStopped) return false;
  const last = section.entries[section.entries.length - 1];
  return last?.index === orchestratorBlocksToRender.value.length - 1;
}

function getProcessSectionSummary(section: Extract<ProcessSection, { type: 'process' }>) {
  const tools = section.toolCallIds.map(id => orchestratorToolCallMap.value.get(id))
    .filter((tool): tool is ToolCall => !!tool);
  const summary = summarizeProcessTools(tools, !!props.message.isStreaming);
  const last = section.entries[section.entries.length - 1];
  if (summary) {
    if (last && isReasoningBlockThinking(last.index)) return `${summary} · 正在思考`;
    return summary;
  }
  if (section.toolCallIds.length > 0) return `工具调用 ${section.toolCallIds.length} 次`;
  return last && isReasoningBlockThinking(last.index) ? '正在思考' : '思考过程';
}

// 优先使用请求生命周期记录；本地计时只用于兼容没有时间字段的流。
const taskStartedAt = ref<number | null>(null);
const taskElapsedSeconds = ref(0);
let taskTimer: ReturnType<typeof setInterval> | undefined;
function stopTaskTimer() {
  if (taskTimer !== undefined) clearInterval(taskTimer);
  taskTimer = undefined;
}
watch(() => useAgentProcessUI.value && props.message.isStreaming, (streaming) => {
  stopTaskTimer();
  if (streaming) {
    taskStartedAt.value = props.message.taskStartedAt ?? Date.now();
    taskElapsedSeconds.value = 0;
    taskTimer = setInterval(() => {
      taskElapsedSeconds.value = Math.floor((Date.now() - taskStartedAt.value!) / 1000);
    }, 1000);
  } else if (taskStartedAt.value !== null) {
    taskElapsedSeconds.value = Math.floor((Date.now() - taskStartedAt.value) / 1000);
  }
}, { immediate: true });
onUnmounted(stopTaskTimer);
const taskProcessLabel = computed(() => {
  const saved = readTaskTiming(props.message);
  if (saved && !props.message.isStreaming) {
    return `任务耗时 ${formatTaskDuration(saved.taskStartedAt, saved.taskFinishedAt)}`;
  }
  if (taskStartedAt.value === null) return props.message.isStreaming ? '任务进行中' : '任务过程';
  const seconds = taskElapsedSeconds.value;
  const duration = seconds >= 60 ? `${Math.floor(seconds / 60)}m ${seconds % 60}s` : `${seconds}s`;
  return `${props.message.isStreaming ? '任务进行中' : '任务耗时'} ${duration}`;
});
const hasProcessContent = computed(() => props.message.role === 'assistant' && (
  showStandaloneReasoning.value
  || taskProcessBlocks.value.length > 0
  || (!useOrchestratorBlocks.value && !!props.message.tool_calls?.length)
  || (shouldUseOrchestratorRendering.value && !!props.message.todos?.length)
));
// ---- details 折叠即卸载：收起的 body 不挂组件树，展开时才渲染 ----
const processDetailsOpen = reactive<Record<string, boolean>>({});
function handleProcessToggle(event: Event, key: string) {
  const open = (event.target as HTMLDetailsElement).open;
  processDetailsOpen[key] = open;
  if (!open) return;
  nextTick(() => {
    getReasoningPanelKeys().forEach(panelKey => {
      const viewport = trViewportEls.get(panelKey);
      if (viewport) updateTrFades(panelKey, viewport);
    });
    document.dispatchEvent(new CustomEvent('mcp-panel-expanded', {
      detail: { message: props.message, isManualExpand: true }
    }));
  });
}

const getToolCallsForBlock = (block: OrchestratorBlock) => {
  if (block.type !== 'tools') return [];
  return block.toolCallIds.map(id => orchestratorToolCallMap.value.get(id)).filter(Boolean) as ToolCall[];
};
const getOrchestratorBlockKey = (block: OrchestratorBlock, index: number) => {
  if (block.type === 'tools') return `tools-${block.toolCallIds.join('-')}-${index}`;
  if (block.type === 'reasoning') return `reasoning-${index}`;
  return `content-${index}`;
};
const getReasoningPanelKeys = () => {
  if (hasReasoningBlocks.value) {
    return orchestratorBlocksToRender.value
      .map((block, index) => block.type === 'reasoning' ? getOrchestratorBlockKey(block, index) : null)
      .filter((key): key is string => !!key);
  }
  return showStandaloneReasoning.value ? [standaloneReasoningPanelKey] : [];
};
// ---- 思考块（完全对齐 aicss.dev Thinking + Reasoning）----
// 正文或工具调用一旦开始输出，思考即视为已完成
const isStandaloneReasoningThinking = computed(() => {
  if (props.message.role !== 'assistant' || !props.message.isStreaming || isAgentWaiting.value) return false;
  return !(props.message.content || '').trim() && !(props.message.tool_calls?.length);
});

// 思考用时记录：key 为面板 key，start/end 为时间戳
const reasoningTiming = reactive<Record<string, { start: number; end: number | null }>>({});

function recordReasoningStart(key: string) {
  if (!reasoningTiming[key]) {
    reasoningTiming[key] = { start: Date.now(), end: null };
  }
}

function recordReasoningEnd(key: string) {
  const t = reasoningTiming[key];
  if (t && t.end === null) t.end = Date.now();
}

function getReasoningElapsedS(key: string) {
  const t = reasoningTiming[key];
  if (!t || t.end === null) return 0;
  return Math.max(1, Math.round((t.end - t.start) / 1000));
}

watch(isStandaloneReasoningThinking, (thinking) => {
  if (thinking) recordReasoningStart(standaloneReasoningPanelKey);
  else recordReasoningEnd(standaloneReasoningPanelKey);
}, { immediate: true });

// 仅当消息仍在流式输出且该块是当前最后一个块（正在生成的思考块）时视为"思考中"
const isReasoningBlockThinking = (blockIndex: number) => {
  if (props.message.role !== 'assistant' || !props.message.isStreaming || isAgentWaiting.value) return false;
  const blocks = orchestratorBlocksToRender.value;
  return blocks[blockIndex]?.type === 'reasoning' && blocks[blocks.length - 1] === blocks[blockIndex];
};

// 跟踪每个编排思考块的用时（开始思考 → 不再思考）
const prevBlockThinking = new Map<string, boolean>();

watch(() => orchestratorBlocksToRender.value.map((b, i) =>
  b.type === 'reasoning' ? `${getOrchestratorBlockKey(b, i)}:${isReasoningBlockThinking(i) ? '1' : '0'}` : ''
).join('|'), () => {
  orchestratorBlocksToRender.value.forEach((block, index) => {
    if (block.type !== 'reasoning') return;
    const key = getOrchestratorBlockKey(block, index);
    const thinking = isReasoningBlockThinking(index);
    if (thinking) {
      recordReasoningStart(key);
    } else if (prevBlockThinking.get(key)) {
      recordReasoningEnd(key);
    }
    prevBlockThinking.set(key, thinking);
  });
}, { immediate: true });

// ---- 视口几何（原版常量：MAX_H=180 / FADE=16）----
const TR_MAX_H = 180;
const TR_FADE = 16;

const trContentH = reactive<Record<string, number>>({});
const trFadeTop = reactive<Record<string, boolean>>({});
const trFadeBottom = reactive<Record<string, boolean>>({});
const trViewportEls = new Map<string, HTMLElement>();
const trObservers = new Map<string, ResizeObserver>();
const trObservedTargets = new Map<string, HTMLElement>();

// ---- 折叠即卸载：思考内容只在展开时挂载，收起动画跑完后整棵子树移出组件树 ----
// .tr-collapsible 的过渡为 380ms，留一点余量再卸载，避免内容在动画中途消失
const TR_UNMOUNT_DELAY = 420;
const trRendered = reactive<Record<string, boolean>>({});
const trUnmountTimers = new Map<string, number>();

function isTrRendered(key: string) {
  return !!trRendered[key];
}

function syncTrRendered(key: string, expanded: boolean) {
  const pending = trUnmountTimers.get(key);
  if (expanded) {
    if (pending) {
      clearTimeout(pending);
      trUnmountTimers.delete(key);
    }
    trRendered[key] = true;
    return;
  }
  // 从未渲染过、或已在排队卸载，都不必重复计时
  if (!trRendered[key] || pending) return;
  trUnmountTimers.set(key, window.setTimeout(() => {
    trUnmountTimers.delete(key);
    trRendered[key] = false;
  }, TR_UNMOUNT_DELAY));
}

// 必须测量内层 .tr-stream 的真实高度：视口自身高度被 min(h, 180) 约束，
// 而 scrollHeight >= clientHeight 恒成立，用视口测量会导致高度只增不减，
// 内容变短后留下永久空白
function measureTrContentH(viewport: HTMLElement): number {
  const stream = viewport.firstElementChild as HTMLElement | null;
  return stream ? stream.offsetHeight : viewport.scrollHeight;
}

function setTrViewportRef(key: string, el: unknown) {
  if (el instanceof HTMLElement) {
    trViewportEls.set(key, el);
    if (trRendered[key]) trContentH[key] = measureTrContentH(el);
  } else {
    trViewportEls.delete(key);
  }
}

/**
 * 观察目标改由 .tr-stream 自己上报：内容随折叠卸载、展开重建，
 * 元素实例每次都不同，挂在视口上会观察到已脱离文档的旧节点。
 */
function setTrStreamRef(key: string, el: unknown) {
  const stream = el instanceof HTMLElement ? el : null;
  if (!stream) {
    trObservers.get(key)?.disconnect();
    trObservers.delete(key);
    trObservedTargets.delete(key);
    return;
  }
  if (trObservedTargets.get(key) === stream) return;
  trObservers.get(key)?.disconnect();
  const observer = new ResizeObserver(() => {
    const viewport = trViewportEls.get(key);
    // 折叠卸载期间不写回高度，保留上次测量值，避免展开瞬间视口塌陷成一帧空白
    if (!stream.isConnected || !trRendered[key] || !viewport) return;
    trContentH[key] = measureTrContentH(viewport);
    maybeStickTrToBottom(key);
  });
  observer.observe(stream);
  trObservers.set(key, observer);
  trObservedTargets.set(key, stream);
  const viewport = trViewportEls.get(key);
  if (viewport && trRendered[key]) trContentH[key] = measureTrContentH(viewport);
}

// ---- 滚动条：与 chat-history 同一套逻辑，滚动时显形，闲置 600ms 后隐藏 ----
const TR_SB_HIDE_DELAY = 600;
// 取不到值即视为隐藏，所以刚展开时不会先闪一下滚动条
const trSbVisible = reactive<Record<string, boolean>>({});
const trSbTimers = new Map<string, number>();

function showTrScrollbar(key: string) {
  trSbVisible[key] = true;
  const prev = trSbTimers.get(key);
  if (prev) clearTimeout(prev);
  trSbTimers.set(key, window.setTimeout(() => {
    trSbVisible[key] = false;
    trSbTimers.delete(key);
  }, TR_SB_HIDE_DELAY));
}

// ---- 展开态流式钉底：对齐 chat-history 的滚动逻辑 ----
const TR_STICK_EPS = 50;       // 对应 STRICT_BOTTOM_EPS：距底部 50px 内视为"仍在底部"
const TR_AUTO_LOCK_MS = 800;   // 对应 autoScrollLockUntil：用户滚动后 800ms 内不恢复自动跟随
const TR_USER_SCROLL_MS = 150; // 对应 userScrolling 的 150ms 防抖窗口
// 对应 isAutoScroll：缺省（undefined）视为跟随，用户上滚后置 false，滚回底部恢复
const trFollowBottom = reactive<Record<string, boolean>>({});
const trLastScrollTop = new Map<string, number>();   // 对应 lastScrollTop
const trAutoLockUntil = new Map<string, number>();   // 对应 autoScrollLockUntil
const trUserScrolling = new Set<string>();           // 对应 userScrolling
const trUserScrollTimers = new Map<string, number>();
const trProgrammaticScroll = new Set<string>();      // 对应 suppressScrollHandler
const trPendingStickRAF = new Map<string, number>(); // 对应 pendingScrollRAF

// 对应 isAtStrictBottom
function isTrAtBottom(el: HTMLElement) {
  return Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) <= TR_STICK_EPS;
}

// 对应 snapToBottom
function trSnapToBottom(el: HTMLElement) {
  el.scrollTop = Math.max(0, el.scrollHeight - el.clientHeight);
}

// 依滚动位置重算上下渐隐。底部留 4px 容差：缩放或 DPI 缩放下 scrollTop
// 是小数、scrollHeight 取整，1px 容差会把"已在底部"误判为"不在底部"，
// 导致底部渐隐一直盖住最后一行
function updateTrFades(key: string, el: HTMLElement) {
  trFadeTop[key] = el.scrollTop > 1;
  trFadeBottom[key] = el.scrollHeight - el.scrollTop - el.clientHeight > 4;
}

// key 对应的面板是否正在思考（仅思考中的面板需要钉底跟随）
function isTrPanelThinking(key: string): boolean {
  if (key === standaloneReasoningPanelKey) return isStandaloneReasoningThinking.value;
  const index = orchestratorBlocksToRender.value.findIndex(
    (block, i) => block.type === 'reasoning' && getOrchestratorBlockKey(block, i) === key
  );
  return index >= 0 && isReasoningBlockThinking(index);
}

function shouldTrFollow(key: string) {
  return trFollowBottom[key] !== false && isTrPanelThinking(key) && getTrExpanded(key);
}

// 对应 scrollToBottom 中的程序滚动：打标记、不触发滚动条显形
function trStickNow(key: string) {
  const el = trViewportEls.get(key);
  if (!el) return;
  trProgrammaticScroll.add(key);
  trSnapToBottom(el);
  trLastScrollTop.set(key, el.scrollTop);
  // 钉底后立刻按新位置重算渐隐，不等 scroll 事件（scrollTop 未变化时不会派发）
  updateTrFades(key, el);
  // 兜底清理：scrollTop 未变化时不会派发 scroll 事件，下一帧移除标记
  requestAnimationFrame(() => trProgrammaticScroll.delete(key));
}

// 对应 stopGradualScrollToBottom
function cancelTrStick(key: string) {
  const raf = trPendingStickRAF.get(key);
  if (raf !== undefined) {
    cancelAnimationFrame(raf);
    trPendingStickRAF.delete(key);
  }
}

// 对应 scheduleScrollToBottom：rAF 合帧 + 一次下一帧兜底吸附，处理布局晚于滚动长高的情况
function scheduleTrStick(key: string) {
  cancelTrStick(key);
  trPendingStickRAF.set(key, requestAnimationFrame(() => {
    trPendingStickRAF.delete(key);
    if (!shouldTrFollow(key)) return;
    trStickNow(key);
    requestAnimationFrame(() => {
      if (shouldTrFollow(key)) trStickNow(key);
    });
  }));
}

function maybeStickTrToBottom(key: string) {
  if (!shouldTrFollow(key)) return;
  const el = trViewportEls.get(key);
  if (!el) return;
  // 与 chat-history 的 ResizeObserver 一致：跟随时只要没贴着底就立刻吸附。
  // 这里不能用 TR_STICK_EPS（50px，那是"用户是否滚回底部"的判据）——
  // 否则流式增长时会滞留最多 50px，最后一两行被视口下沿裁掉
  if (el.scrollHeight - el.scrollTop - el.clientHeight <= 2) return;
  trStickNow(key);
  scheduleTrStick(key);
}

// 对应 onUserScrollIntent/onWheel：滚轮、触摸视为用户滚动意图
function onTrUserScrollIntent(key: string) {
  const el = trViewportEls.get(key);
  // 折叠态或不可滚动时，滚轮实际作用在外层聊天列表，不干预
  if (!el || !getTrExpanded(key) || el.scrollHeight <= el.clientHeight) return;
  trUserScrolling.add(key);
  const prev = trUserScrollTimers.get(key);
  if (prev) clearTimeout(prev);
  trUserScrollTimers.set(key, window.setTimeout(() => {
    trUserScrolling.delete(key);
    trUserScrollTimers.delete(key);
  }, TR_USER_SCROLL_MS));
  cancelTrStick(key);
  trAutoLockUntil.set(key, Date.now() + TR_AUTO_LOCK_MS);
  if (!isTrAtBottom(el)) trFollowBottom[key] = false;
  showTrScrollbar(key);
}

onUnmounted(() => {
  trObservers.forEach(observer => observer.disconnect());
  trObservers.clear();
  trUnmountTimers.forEach(timer => clearTimeout(timer));
  trUnmountTimers.clear();
  trSbTimers.forEach(timer => clearTimeout(timer));
  trSbTimers.clear();
  trUserScrollTimers.forEach(timer => clearTimeout(timer));
  trUserScrollTimers.clear();
  trPendingStickRAF.forEach(raf => cancelAnimationFrame(raf));
  trPendingStickRAF.clear();
});

function getTrViewH(key: string) {
  const h = trContentH[key] || 0;
  return Math.min(h, TR_MAX_H);
}

// 思考流自动跟随：内容超高且非用户手动展开时，视口钉住底部
function getTrTranslate(key: string, expanded: boolean) {
  if (expanded) return 0;
  const h = trContentH[key] || 0;
  return h > TR_MAX_H ? TR_MAX_H - TR_FADE - h : 0;
}

function getTrMask(key: string, expanded: boolean) {
  const capped = (trContentH[key] || 0) > TR_MAX_H;
  if (!capped) return 'none';
  // 用户手动展开且内容超高 → 原生滚动，渐隐跟随滚动位置；否则（自动跟随）上下常显渐隐
  const scrollable = expanded;
  const showTop = scrollable ? !!trFadeTop[key] : true;
  const showBottom = scrollable ? !!trFadeBottom[key] : true;
  return `linear-gradient(to bottom, transparent 0, #000 ${showTop ? TR_FADE : 0}px, #000 calc(100% - ${showBottom ? TR_FADE : 0}px), transparent 100%)`;
}

// 对应 onChatScroll：消费程序滚动标记 → 底部恢复跟随 → 上滚脱离跟随
function onTrScroll(key: string, event: Event) {
  const el = event.target as HTMLElement;
  if (!el) return;
  // 渐隐跟随滚动位置重算（程序钉底同样要更新，否则到底后底部渐隐不会消失）
  updateTrFades(key, el);
  const scrollTop = el.scrollTop;
  // 对应 suppressScrollHandler：程序钉底触发的滚动，消费标记后直接返回
  if (trProgrammaticScroll.has(key)) {
    trProgrammaticScroll.delete(key);
    trLastScrollTop.set(key, scrollTop);
    return;
  }
  const isScrollingUp = scrollTop < (trLastScrollTop.get(key) ?? scrollTop);
  trLastScrollTop.set(key, scrollTop);
  if (isTrAtBottom(el)) {
    // 滚回底部恢复跟随；锁定窗口内暂不恢复（对应 autoScrollLockUntil）
    if (Date.now() > (trAutoLockUntil.get(key) ?? 0)) trFollowBottom[key] = true;
  } else if (trUserScrolling.has(key) || isScrollingUp) {
    trFollowBottom[key] = false;
  }
  showTrScrollbar(key);
}

// 用户手动展开状态；折叠统一同步到 activeReasoningPanels（沿用自动折叠偏好与滚动锚点事件机制）
const trOpen = reactive<Record<string, boolean>>({});

function toggleTr(key: string) {
  const next = !(trOpen[key] || activeReasoningPanels.value.includes(key));
  if (next) {
    // 展开瞬间先清掉折叠态的常显渐隐，随后按真实滚动位置重算
    trFadeTop[key] = false;
    trFadeBottom[key] = false;
    if (isTrPanelThinking(key)) {
      // 思考中的面板展开：恢复钉底跟随（等展开渲染完成后再吸到底部）
      trFollowBottom[key] = true;
      trAutoLockUntil.delete(key);
      nextTick(() => {
        maybeStickTrToBottom(key);
        const el = trViewportEls.get(key);
        if (el) updateTrFades(key, el);
      });
    } else {
      const el = trViewportEls.get(key);
      if (el) {
        el.scrollTop = 0;
        updateTrFades(key, el);
      }
    }
  }
  trOpen[key] = next;
  const nextKeys = activeReasoningPanels.value.filter(k => k !== key);
  if (next) nextKeys.push(key);
  updateReasoningPanels(nextKeys);
}

// 每个面板的展开态：思考中与完成后均可折叠（点击头部切换）
const trExpandedComputed = new Map<string, ComputedRef<boolean>>();

function getTrExpanded(key: string) {
  let c = trExpandedComputed.get(key);
  if (!c) {
    c = computed(() => trOpen[key] || activeReasoningPanels.value.includes(key));
    trExpandedComputed.set(key, c);
  }
  return c.value;
}

// Motion preferences only affect CSS animation; completion follows the stream state.
const standaloneReasoningDone = computed(() => !isStandaloneReasoningThinking.value);
const standaloneExpanded = computed(() => getTrExpanded(standaloneReasoningPanelKey));
const standaloneLabelSuffix = computed(() => {
  const seconds = getReasoningElapsedS(standaloneReasoningPanelKey);
  return seconds > 0 ? `${seconds}s` : '';
});

function isBlockExpanded(key: string) {
  return getTrExpanded(key);
}

function getBlockLabelSuffix(key: string) {
  const seconds = getReasoningElapsedS(key);
  return seconds > 0 ? `${seconds}s` : '';
}

const agentName = computed(() => {
  return renderAgent.value?.basic?.name || renderAgent.value?.config?.basic?.name || 'Assistant';
});

const agentAvatar = computed(() => {
  return resolveAgentAvatar(renderAgent.value?.basic?.avatar || renderAgent.value?.config?.basic?.avatar);
});



const agentAvatarStyle = computed(() => {
  const color = renderAgent.value?.basic?.themeColor || renderAgent.value?.config?.basic?.themeColor || '#722ed1';
  return { backgroundColor: agentAvatar.value ? '#ffffff' : color, color: '#fff' };
});

const userProfile = ref<{ username?: string; avatar?: string; avatarBackground?: string; avatarTextColor?: string }>({});
function loadUserProfile() {
  try {
    const profileData = localStorage.getItem('user-profile');
    if (profileData) {
      const p = JSON.parse(profileData);
      userProfile.value.username = p.username || 'user';
      userProfile.value.avatar = p.avatar ?? '';
      userProfile.value.avatarBackground = p.avatarBackground ?? '';
      userProfile.value.avatarTextColor = p.avatarTextColor ?? '';
    } else {
      userProfile.value.username = 'user';
      userProfile.value.avatar = '';
      userProfile.value.avatarBackground = '';
      userProfile.value.avatarTextColor = '';
    }
  } catch (e) {
    userProfile.value.username = 'user';
    userProfile.value.avatar = '';
    userProfile.value.avatarBackground = '';
    userProfile.value.avatarTextColor = '';
  }
}

function handleUserPreferencesChanged(event: Event) {
  const customEvent = event as CustomEvent;
  const detail = customEvent.detail;

  if (detail.preference === 'all') {
    if (detail.value && typeof detail.value.renderUserMessageMarkdown !== 'undefined') {
      renderUserMarkdownEnabled.value = detail.value.renderUserMessageMarkdown;
    }
  } else if (detail.preference === 'renderUserMessageMarkdown') {
    renderUserMarkdownEnabled.value = detail.value;
  }
}

onMounted(() => {
  loadUserProfile();
  loadActiveAgent();
  window.addEventListener('user-info-updated', loadUserProfile);
  window.addEventListener('active-agent-updated', loadActiveAgent);

  window.addEventListener('user-preferences-changed', handleUserPreferencesChanged as EventListener);

  if (isAutoCapturedScreenshotMessage.value && isLatestUserMessage.value && chatStore.isProcessing) {
    triggerScreenshotReveal();
  }
});

onUnmounted(() => {
  window.removeEventListener('user-info-updated', loadUserProfile);
  window.removeEventListener('active-agent-updated', loadActiveAgent);
  window.removeEventListener('user-preferences-changed', handleUserPreferencesChanged as EventListener);
  clearPendingCaptureExitTimer();
  clearScreenshotRevealTimer();
});

const isAllEmpty = computed(() => !userProfile.value.avatar && !userProfile.value.avatarBackground && !userProfile.value.avatarTextColor);
const userAvatarUrl = computed(() => userProfile.value.avatar || (isAllEmpty.value ? (bgPoster as unknown as string) : ''));
const userAvatarBg = computed(() => userAvatarUrl.value ? '#ffffff' : (userProfile.value.avatarBackground || '#1890ff'));
const userAvatarTextColor = computed(() => userAvatarUrl.value ? undefined : (userProfile.value.avatarTextColor || '#ffffff'));
const userAvatarText = computed(() => {
  const name = userProfile.value.username || 'user';
  return name.charAt(0);
});

const avatarStyle = computed(() => {
  if (isUserMessage.value) {
    return { backgroundColor: userAvatarBg.value, color: userAvatarTextColor.value as any };
  }
  return { backgroundColor: avatarColor.value, color: '#fff' };
});

const currentModelId = computed(() => props.message.model || chatStore.model || '');
const currentModel = computed(() => {
  const modelId = currentModelId.value;
  if (!modelId) return null;

  const models = chatStore.availableModels || [];
  const serviceProvider = chatStore.selectedModelService || '';
  return models.find(model =>
    model.id === modelId && (!serviceProvider || model.serviceProvider === serviceProvider)
  ) || models.find(model => model.id === modelId) || null;
});
const currentModelName = computed(() => currentModel.value?.name || currentModelId.value);
const shouldShowIcon = (modelName: string, iconType: string) => {
  return shouldShowModelIcon(modelName, iconType);
};

const resolveGlmIcon = (modelIdOrName: string): 'zai' | 'zhipu' | null => {
  const s = (modelIdOrName || '').toLowerCase();
  if (!s.includes('glm')) return null;
  if (s.includes('glm') && s.includes('z')) return 'zai';
  return 'zhipu';
};

const assistantAvatarStyle = computed(() => {
  const name = currentModelName.value || '';
  const useIcon = shouldShowIcon(name, 'qwen') || shouldShowIcon(name, 'deepseek') || shouldShowIcon(name, 'glm');
  return { backgroundColor: useIcon ? 'transparent' : avatarColor.value, color: '#fff' };
});

const assistantAvatarText = computed(() => {
  const name = currentModelName.value || '';
  return name ? name.charAt(0).toUpperCase() : 'M';
});

const displayName = computed(() => {
  if (props.message.role === 'user') {
    return userProfile.value.username || 'user';
  }
  if (props.message.role === 'assistant') {
    if (shouldUseAgentIdentity.value) {
      return agentName.value;
    }
    return currentModelName.value || 'assistant';
  }
  return props.message.role;
});

const emit = defineEmits<{
  'selection-changed': [messageId: string, selected: boolean];
  'selection-mode-changed': [action: boolean | string | { action: string, messageId: string | null }];
  'open-artifact': [payload: { code: string | ArrayBuffer; lang: string; id?: string; title?: string; isComplete?: boolean; downloadUrl?: string; autoOpen?: boolean }];
}>();

function handleOpenArtifact(payload: { code: string | ArrayBuffer; lang: string; id?: string; title?: string; isComplete?: boolean; downloadUrl?: string; autoOpen?: boolean }) {
  emit('open-artifact', payload);
}

const getFileArtifactId = (index: number) => {
  return `${messageId.value}-file-${index}`;
};

const messageFiles = computed(() => Array.isArray(props.message.files) ? props.message.files : []);
const messageFileEntries = computed(() => messageFiles.value.map((file, index) => ({ file, index })));
const messageImageEntries = computed(() => messageFileEntries.value.filter(entry => !entry.file.isCapturePending && isImageFile(entry.file)));
const messageImageFiles = computed(() => messageImageEntries.value.map(entry => entry.file));
const messageDocumentFiles = computed(() => messageFileEntries.value.filter(entry => !entry.file.isCapturePending && !isImageFile(entry.file)));
const conversationImages = computed(() => {
  const viewerPendingImages = (chatStore.pendingInputImages || []).filter((item): item is any => !!(item as PendingInputImage).url);
  return mergeViewerImages(
    extractImagesFromMessages(chatStore.messages || []),
    viewerPendingImages
  );
});

const pendingCaptureCards = computed(() => {
  if (props.message.role !== 'user') return [] as PendingInputImage[];

  return (chatStore.pendingInputImages || []).filter((item): item is PendingInputImage => {
    return 'isCapturePending' in item
      && !!item.isCapturePending
      && !!item.pendingMessageKey
      && item.pendingMessageKey === props.message.uiKey;
  });
});
const displayPendingCaptureCards = ref<PendingInputImage[]>([]);
const isPendingCaptureDissolving = ref(false);
let pendingCaptureExitTimer: number | null = null;
const pendingCaptureParticles = [
  { id: 1, originX: '18%', originY: '18%', targetX: '-56px', targetY: '-54px', scale: '0.72', size: '8px', delay: '0ms' },
  { id: 2, originX: '34%', originY: '15%', targetX: '-22px', targetY: '-72px', scale: '0.68', size: '7px', delay: '22ms' },
  { id: 3, originX: '52%', originY: '12%', targetX: '0px', targetY: '-86px', scale: '0.78', size: '8px', delay: '36ms' },
  { id: 4, originX: '70%', originY: '16%', targetX: '28px', targetY: '-66px', scale: '0.7', size: '7px', delay: '18ms' },
  { id: 5, originX: '84%', originY: '20%', targetX: '58px', targetY: '-42px', scale: '0.82', size: '9px', delay: '46ms' },
  { id: 6, originX: '16%', originY: '34%', targetX: '-68px', targetY: '-10px', scale: '0.76', size: '8px', delay: '30ms' },
  { id: 7, originX: '32%', originY: '32%', targetX: '-38px', targetY: '-24px', scale: '0.58', size: '6px', delay: '14ms' },
  { id: 8, originX: '50%', originY: '34%', targetX: '0px', targetY: '-34px', scale: '0.66', size: '7px', delay: '52ms' },
  { id: 9, originX: '68%', originY: '32%', targetX: '40px', targetY: '-18px', scale: '0.64', size: '6px', delay: '28ms' },
  { id: 10, originX: '84%', originY: '36%', targetX: '76px', targetY: '2px', scale: '0.8', size: '8px', delay: '40ms' },
  { id: 11, originX: '14%', originY: '52%', targetX: '-82px', targetY: '6px', scale: '0.88', size: '9px', delay: '10ms' },
  { id: 12, originX: '30%', originY: '50%', targetX: '-42px', targetY: '12px', scale: '0.62', size: '7px', delay: '34ms' },
  { id: 13, originX: '50%', originY: '52%', targetX: '0px', targetY: '24px', scale: '0.6', size: '6px', delay: '56ms' },
  { id: 14, originX: '70%', originY: '50%', targetX: '46px', targetY: '16px', scale: '0.7', size: '7px', delay: '26ms' },
  { id: 15, originX: '86%', originY: '54%', targetX: '88px', targetY: '12px', scale: '0.92', size: '9px', delay: '48ms' },
  { id: 16, originX: '20%', originY: '72%', targetX: '-56px', targetY: '50px', scale: '0.82', size: '8px', delay: '20ms' },
  { id: 17, originX: '38%', originY: '76%', targetX: '-14px', targetY: '68px', scale: '0.7', size: '7px', delay: '42ms' },
  { id: 18, originX: '56%', originY: '74%', targetX: '12px', targetY: '72px', scale: '0.76', size: '8px', delay: '24ms' },
  { id: 19, originX: '72%', originY: '72%', targetX: '42px', targetY: '58px', scale: '0.8', size: '8px', delay: '38ms' },
  { id: 20, originX: '84%', originY: '76%', targetX: '74px', targetY: '52px', scale: '0.94', size: '9px', delay: '16ms' }
] as const;

const AUTO_CAPTURE_PROMPT = '请帮我查看截图中的内容';
const isLatestUserMessage = computed(() => {
  const messages = chatStore.messages || [];
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i]?.role === 'user') {
      return messages[i] === props.message;
    }
  }
  return false;
});
const isAutoCapturedScreenshotMessage = computed(() => {
  if (props.message.role !== 'user' || messageImageFiles.value.length === 0) {
    return false;
  }

  const content = `${props.message.display_content || ''}${props.message.content || ''}`;
  if (content.includes(AUTO_CAPTURE_PROMPT)) {
    return true;
  }

  return messageImageFiles.value.some(file => /^screenshot[_-]/i.test(String(file?.name || '')));
});
const isScreenshotRevealActive = ref(false);
const hasPlayedScreenshotReveal = ref(false);
const shouldApplyScreenshotRevealClass = computed(() => isScreenshotRevealActive.value || hasPlayedScreenshotReveal.value);
let screenshotRevealTimer: number | null = null;

function clearPendingCaptureExitTimer() {
  if (pendingCaptureExitTimer !== null) {
    window.clearTimeout(pendingCaptureExitTimer);
    pendingCaptureExitTimer = null;
  }
}

function clearScreenshotRevealTimer() {
  if (screenshotRevealTimer !== null) {
    window.clearTimeout(screenshotRevealTimer);
    screenshotRevealTimer = null;
  }
}

function triggerScreenshotReveal() {
  clearScreenshotRevealTimer();
  isScreenshotRevealActive.value = true;
  hasPlayedScreenshotReveal.value = true;
  screenshotRevealTimer = window.setTimeout(() => {
    isScreenshotRevealActive.value = false;
    screenshotRevealTimer = null;
  }, 920);
}

watch(pendingCaptureCards, (cards, previousCards) => {
  if (cards.length > 0) {
    clearPendingCaptureExitTimer();
    isPendingCaptureDissolving.value = false;
    displayPendingCaptureCards.value = cards.slice();
    return;
  }

  if (previousCards && previousCards.length > 0) {
    clearPendingCaptureExitTimer();
    displayPendingCaptureCards.value = previousCards.slice();
    isPendingCaptureDissolving.value = true;
    pendingCaptureExitTimer = window.setTimeout(() => {
      displayPendingCaptureCards.value = [];
      isPendingCaptureDissolving.value = false;
      pendingCaptureExitTimer = null;
    }, 560);
    return;
  }

  displayPendingCaptureCards.value = [];
}, { immediate: true });

watch(isAutoCapturedScreenshotMessage, (enabled, previousEnabled) => {
  if (enabled && !previousEnabled && !hasPlayedScreenshotReveal.value) {
    triggerScreenshotReveal();
  }
});

function openConversationImage(imageUrl: string, imageAlt: string = '', preferredSource?: 'file' | 'markdown' | 'html') {
  const currentMessageMatchIndex = conversationImages.value.findIndex(item => {
    if (item.url !== imageUrl || item.messageIndex !== props.messageIndex) return false;
    return preferredSource ? item.source === preferredSource : true;
  });

  const fallbackIndex = conversationImages.value.findIndex(item => item.url === imageUrl);
  const resolvedIndex = currentMessageMatchIndex >= 0 ? currentMessageMatchIndex : fallbackIndex;
  const resolvedImage = resolvedIndex >= 0 ? conversationImages.value[resolvedIndex] : null;

  currentImageUrl.value = resolvedImage?.url || imageUrl;
  currentImageAlt.value = imageAlt || resolvedImage?.alt || '图片';
  imageViewerOpen.value = true;
}

function handleImageFileClick(file: any) {
  const previewUrl = getImagePreviewUrl(file);
  if (!previewUrl) return;
  openConversationImage(previewUrl, file?.name || '图片', 'file');
}

async function handleFileClick(file: any, index: number, options?: { autoOpen?: boolean }) {
  // CAD 图纸只上传不解析，无内容可预览：手动点击时提示，发送时的自动打开则静默跳过
  const clickedName = (file?.name || '').toLowerCase();
  if (clickedName.endsWith('.dwg') || clickedName.endsWith('.dxf')) {
    if (!options?.autoOpen) {
      NotificationService.info('CAD 图纸（DWG/DXF）暂不支持在线预览');
    }
    return;
  }

  if (!isImageFile(file)) {
    sessionStorage.setItem('shouldOpenInputToolbar', 'true');
    setTimeout(() => {
      window.dispatchEvent(new CustomEvent('open-input-toolbar'));
    }, 200);
  }

  const artifactId = getFileArtifactId(index);

  let content = '';
  const isBuffer = file.content instanceof ArrayBuffer || ArrayBuffer.isView(file.content) || Object.prototype.toString.call(file.content) === '[object ArrayBuffer]';
  if (file.content && isBuffer) {
    const name = (file.name || '').toLowerCase();
    let lang = 'markdown';
    if (name.endsWith('.pdf')) {
      lang = 'pdf';
    } else if (name.endsWith('.doc') || name.endsWith('.docx')) {
      lang = 'docx';
    } else if (name.endsWith('.txt')) {
      lang = 'text';
    } else if (name.endsWith('.csv')) {
      lang = 'csv';
    } else if (name.endsWith('.xls') || name.endsWith('.xlsx')) {
      lang = 'xlsx';
    } else if (name.endsWith('.ppt') || name.endsWith('.pptx')) {
      lang = 'pptx';
    }

    emit('open-artifact', {
      code: file.content as any,
      lang: lang,
      title: file.name,
      id: artifactId,
      autoOpen: options?.autoOpen
    });
    return;
  }

  if (file.parseResult && file.parseResult.document_chunks) {
    content = file.parseResult.document_chunks.map((c: any) => c.content).join('\n\n');
  } else if (file.content && typeof file.content === 'string') {
    content = file.content;
  }

  const name = (file.name || '').toLowerCase();
  let type = 'markdown';
  if (name.endsWith('.doc') || name.endsWith('.docx')) {
    type = 'docx';
  } else if (name.endsWith('.pdf')) {
    type = 'pdf';
  } else if (name.endsWith('.txt')) {
    type = 'text';
  } else if (name.endsWith('.csv')) {
    type = 'csv';
  } else if (name.endsWith('.xls') || name.endsWith('.xlsx')) {
    type = 'xlsx';
  } else if (name.endsWith('.ppt') || name.endsWith('.pptx')) {
    type = 'pptx';
  }

  // 历史会话中的文件只带下载链接（path），点击时拉取内容后再预览
  const fileUrl = file.path || file.url;
  if (!content && fileUrl) {
    try {
      const res = await fetch(fileUrl);
      if (res.ok) {
        const buffer = await res.arrayBuffer();
        emit('open-artifact', {
          code: buffer,
          lang: type,
          title: file.name,
          id: artifactId,
          autoOpen: options?.autoOpen
        });
        return;
      }
    } catch {
      // 拉取失败走下方兜底提示
    }
  }

  emit('open-artifact', {
    code: content || '无法预览文件内容',
    lang: type,
    title: file.name,
    id: artifactId,
    autoOpen: options?.autoOpen
  });
}

const getFileExtension = (filename: string) => {
  if (!filename) return 'FILE';
  const ext = filename.split('.').pop();
  return ext ? ext.toUpperCase() : 'FILE';
};

const getIconHtml = (file: any) => {
  if (!file) {
    return '';
  }

  const name = (file.name || '').toLowerCase();

  if (name.endsWith('.docx') || name.endsWith('.doc')) {
    return encodeURIComponent(`<img src="${WordSvg}" alt="Word" style="width: 24px; height: 24px;" />`);
  }
  if (name.endsWith('.pdf')) {
    return encodeURIComponent(`<img src="${PdfSvg}" alt="PDF" style="width: 24px; height: 24px;" />`);
  }
  if (name.endsWith('.txt')) {
    return encodeURIComponent(`<img src="${TxtSvg}" alt="TXT" style="width: 24px; height: 24px;" />`);
  }
  if (name.endsWith('.md')) {
    return encodeURIComponent(`<img src="${MarkdownSvg}" alt="Markdown" style="width: 24px; height: 24px;" />`);
  }
  if (name.endsWith('.ppt') || name.endsWith('.pptx')) {
    return encodeURIComponent(`<img src="${PptSvg}" alt="PPT" style="width: 24px; height: 24px;" />`);
  }
  if (name.endsWith('.csv') || name.endsWith('.xls') || name.endsWith('.xlsx')) {
    return encodeURIComponent(`<img src="${ExcelSvg}" alt="Excel" style="width: 24px; height: 24px;" />`);
  }
  if (name.endsWith('.dwg') || name.endsWith('.dxf')) {
    return encodeURIComponent(`<img src="${CadSvg}" alt="CAD" style="width: 24px; height: 24px;" />`);
  }
  return encodeURIComponent(`<img src="${WordSvg}" alt="File" style="width: 24px; height: 24px;" />`);
};

const messageId = computed(() => {
  // 优先 uiKey，避免服务端补全/替换 id 后 artifactId 漂移导致重复打开
  if (props.message.uiKey) return props.message.uiKey;
  if (props.message.id) return props.message.id;

  const role = props.message.role
  const index = props.messageIndex
  const messageRef = props.message.content + props.message.role + index
  return `msg-${role}-${index}-${messageRef.length}`
})

const isErrorMessage = computed(() => {
  const content = props.message.content || ''
  return content.includes('请求过程中出现错误') || content.includes('Connection error')
})

const shouldShowMessageText = computed(() => {
  return !!props.message.content || (props.message.role === 'assistant' && props.message.isStreaming);
});

const latestStreamingAssistantMessage = computed(() => {
  const messages = chatStore.messages || [];
  for (let i = messages.length - 1; i >= 0; i--) {
    const currentMessage = messages[i];
    if (currentMessage.role === 'assistant' && currentMessage.isStreaming) {
      return currentMessage;
    }
  }
  return null;
});

const isCurrentStreamingAssistant = computed(() => {
  const latestMessage = latestStreamingAssistantMessage.value;
  if (!latestMessage || props.message.role !== 'assistant' || !props.message.isStreaming) return false;

  if (latestMessage === props.message) return true;

  const latestIdentity = latestMessage.uiKey || latestMessage.id;
  const currentIdentity = props.message.uiKey || props.message.id;
  return !!latestIdentity && latestIdentity === currentIdentity;
});

const showLoadingRipple = computed(() => {
  if (!isCurrentStreamingAssistant.value || isAgentWaiting.value) return false;
  const hasContent = !!props.message.content;
  const hasTools = props.message.tool_calls && props.message.tool_calls.length > 0;
  const hasReasoning = !!props.message.reasoning_content;
  return !hasContent && !hasTools && !hasReasoning && !isErrorMessage.value;
});

// 知识库检索在途时，等待占位表述为检索而非「正在思考」
const loadingPlaceholderLabel = computed(() => (isRetrievingKnowledgeBase.value ? '正在检索知识库' : ''));

const showUserPlainText = computed(() => {
  return props.message.role === 'user' && !renderUserMarkdownEnabled.value;
});

const activeReasoningPanels = ref<string[]>([]);
const activeCitationPanels = ref<string[]>([]);

// 折叠即卸载的唯一同步点：展开态（手动 trOpen 或自动 activeReasoningPanels）变化时，
// 展开的面板立即挂载内容，收起的面板等折叠动画跑完再卸载（toggleTr 会同步写两边）
watch(activeReasoningPanels, (keys) => {
  const set = new Set(keys);
  const allKeys = new Set([...Object.keys(trRendered), ...keys]);
  allKeys.forEach(k => syncTrRendered(k, !!trOpen[k] || set.has(k)));
}, { immediate: true });

const imageViewerOpen = ref(false);
const currentImageUrl = ref('');
const currentImageAlt = ref('');

function handleImageClick(payload: string | { imageUrl: string; imageAlt?: string }) {
  const imageUrl = typeof payload === 'string' ? payload : payload.imageUrl;
  const imageAlt = typeof payload === 'string' ? '' : (payload.imageAlt || '');
  if (!imageUrl) return;
  openConversationImage(imageUrl, imageAlt);
}

const messageContentRef = ref<HTMLElement | null>(null);

const isEditMode = ref(false);

const USER_PREFERENCES_KEY = 'mcp-user-preferences';
const renderUserMarkdownEnabled = ref(true);

onMounted(() => {
  const preferences = StorageService.get<{ renderUserMessageMarkdown?: boolean }>(USER_PREFERENCES_KEY) || {};
  renderUserMarkdownEnabled.value = preferences.renderUserMessageMarkdown ?? true;
});

const expandedCitation = ref<Record<string, boolean>>({});
const kbPanelRoot = ref<HTMLElement | null>(null);
let measureScheduled = false;
const CLAMP_PX = 180;
/** 记录本消息是否已自动打开过 Canvas（防止重复触发） */
const kbAutoOpenedFlag = ref(false);

function toggleCitationExpand(key: string) {
  expandedCitation.value = { ...expandedCitation.value, [key]: !expandedCitation.value[key] };
}

function measureOverflow() {
  if (!activeCitationPanels.value.includes('kb')) return;
  const root = kbPanelRoot.value;
  if (!root) return;
  const items = root.querySelectorAll('.kb-citation-card');
  items.forEach((item) => {
    const content = item.querySelector('.kb-citation-content') as HTMLElement | null;
    if (!content) return;
    const overflow = content.scrollHeight > CLAMP_PX + 1;
    if (overflow) item.classList.add('has-overflow');
    else item.classList.remove('has-overflow');
  });
}

function scheduleMeasure() {
  if (measureScheduled) return;
  measureScheduled = true;
  requestAnimationFrame(() => {
    measureScheduled = false;
    measureOverflow();
  });
}

function normalizeCitationText(s: string): string {
  let t = s || '';
  t = t.replace(/\r\n?/g, '\n');
  t = t.replace(/[ \t]+\n/g, '\n');
  t = t.replace(/^\n+|\n+$/g, '');
  return t;
}

const formattedKbCitations = computed(() => {
  const list = ((props.message as any).kb_citations || []) as Array<any>;
  // 使用 chatStore.messages 中的真实索引（而非 v-for 的 messageIndex），
  // 因为 ChatHistory 过滤了 tool/system 消息，导致 v-for 索引与原始数组索引不一致
  const storeMsgIdx = chatStore.messages.indexOf(props.message);
  return list.map((it, i) => {
    const raw = (it?.page_content || '').trim();
    const key = `kb-${storeMsgIdx >= 0 ? storeMsgIdx : props.messageIndex}-${i}`;
    const text = normalizeCitationText(raw);
    const lines = text
      .split(/\n{2,}/)
      .map(s => s.trim())
      .filter(s => s.length > 0);
    return { ...it, __key: key, __text: text, __lines: lines };
  });
});

function getCitationSourceName(it: any): string {
  const source = String(it?.metadata?.source || '').trim();
  if (!source) return '未知来源';
  const parts = source.split(/[\\/]/);
  return parts[parts.length - 1] || source;
}

function getCitationTypeLabel(it: any): string {
  const typeValue = String(it?.type || '').trim().toLowerCase();
  if (typeValue === 'document') return '文档片段';
  if (typeValue === 'chunk') return '检索切片';
  if (typeValue === 'passage') return '文本段';
  return typeValue ? typeValue.toUpperCase() : '知识条目';
}

function getCitationEntities(it: any): string[] {
  const entities = it?.metadata?.entities;
  return Array.isArray(entities)
    ? entities.map(entity => String(entity).trim()).filter(Boolean)
    : [];
}

function getCitationScore(it: any): number | null {
  const s = typeof it?.metadata?.score === 'number' ? it.metadata.score : it?.score;
  return typeof s === 'number' ? s : null;
}

function getCitationRelevance(it: any): number | null {
  const value = it?.metadata?.relevance_score;
  return typeof value === 'number' ? value : null;
}

function formatCitationPercent(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '--';
  const normalized = value <= 1 ? value * 100 : value;
  return `${normalized.toFixed(normalized >= 100 ? 0 : 1)}%`;
}

function formatCitationNumeric(value: number | null): string {
  if (value === null || Number.isNaN(value)) return '--';
  return value >= 100 ? value.toFixed(0) : value.toFixed(2).replace(/\.00$/, '');
}

function getCitationRelevanceLevel(it: any): 'high' | 'medium' | 'low' {
  const relevance = getCitationRelevance(it);
  if (relevance === null) return 'low';
  if (relevance >= 0.8) return 'high';
  if (relevance >= 0.6) return 'medium';
  return 'low';
}

function getCitationRelevanceText(it: any): string {
  const level = getCitationRelevanceLevel(it);
  if (level === 'high') return '高匹配';
  if (level === 'medium') return '中匹配';
  return '基础匹配';
}

function formatCitationIndex(value: number): string {
  return String(value).padStart(2, '0');
}

const citationOverview = computed(() => {
  const sources = new Set<string>();
  let relevanceSum = 0;
  let relevanceCount = 0;
  formattedKbCitations.value.forEach((item) => {
    const source = String(item?.metadata?.source || '').trim();
    if (source) sources.add(source);

    const relevance = getCitationRelevance(item);
    if (relevance !== null) {
      relevanceSum += relevance;
      relevanceCount += 1;
    }
  });

  return {
    total: formattedKbCitations.value.length,
    sourceCount: sources.size,
    averageRelevance: relevanceCount > 0 ? formatCitationPercent(relevanceSum / relevanceCount) : '--'
  };
});

watch(() => ((props.message as any).kb_citations || []).length, () => {
  scheduleMeasure();
}, { flush: 'post' });

watch(() => formattedKbCitations.value, () => {
  scheduleMeasure();
}, { flush: 'post' });

/** 当知识引用数据就绪时，自动在 Canvas 中打开第一个文件（不等待流式完成） */
watch(
  () => ({
    citations: formattedKbCitations.value,
    role: props.message.role
  }),
  ({ citations, role }) => {
    if (kbAutoOpenedFlag.value) return;
    if (role !== 'assistant') return;
    if (!citations || citations.length === 0) return;

    // 找第一个有有效文件 URL 的引用
    const firstWithFile = citations.find((item: any) => getCitationFileUrl(item));
    if (!firstWithFile) return;

    kbAutoOpenedFlag.value = true;
    // 延迟一帧确保 DOM 稳定后再触发
    nextTick(() => {
      handlePreviewFileInCanvas(firstWithFile, { autoOpen: true });
    });
  },
  { immediate: true }
);

onMounted(() => {
  nextTick(() => scheduleMeasure());
  window.addEventListener('resize', scheduleMeasure);
});

onUnmounted(() => {
  window.removeEventListener('resize', scheduleMeasure);
});

function handleCitationCollapseChange(keys: string[] | string) {
  const arr = Array.isArray(keys) ? (keys as string[]) : [keys as string];
  const isOpen = arr.includes('kb');
  if (isOpen) {
    setTimeout(() => scheduleMeasure(), 300);
  }
}

/** 文本类型文件扩展名（支持直接获取文本内容后预览） */
const TEXT_BASED_EXTS = new Set(['txt', 'md', 'markdown', 'csv', 'json', 'xml', 'yaml', 'yml', 'log', 'py', 'js', 'ts', 'html', 'css', 'sh', 'bat', 'cfg', 'ini', 'conf', 'toml']);
/** 二进制文档类型，知识库预览时先拉取为 ArrayBuffer 再交给 Canvas */
const BINARY_PREVIEW_EXTS = new Set(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']);

/** 根据文件名 / 路径推断文件扩展名（小写） */
function getFileExtensionFromPath(filePath: string): string {
  const cleanPath = filePath.split('?')[0].split('#')[0];
  // 优先取最后一个路径段中的扩展名（如 /path/doc.docx → docx）
  const lastSlash = cleanPath.lastIndexOf('/');
  const fileName = cleanPath.slice(lastSlash + 1);
  const lastDot = fileName.lastIndexOf('.');
  if (lastDot < 0 || lastDot === fileName.length - 1) return '';
  return fileName.slice(lastDot + 1).toLowerCase();
}

/** 根据扩展名映射到 Canvas FileType */
function extToCanvasType(ext: string): string {
  switch (ext) {
    case 'doc':
    case 'docx': return 'docx';
    case 'pdf': return 'pdf';
    case 'txt': return 'text';
    case 'md':
    case 'markdown': return 'markdown';
    case 'csv': return 'csv';
    case 'xls':
    case 'xlsx': return 'xlsx';
    case 'ppt':
    case 'pptx': return 'pptx';
    case 'html':
    case 'htm': return 'html';
    default: return '';
  }
}

/** 将 file_path 解析为完整的可访问 URL */
function resolveFileUrl(filePath: string): string {
  if (/^https?:\/\//i.test(filePath)) return filePath;
  const base = getApiBaseUrl() || '';
  const normalizedPath = filePath.startsWith('/') ? filePath : `/${filePath}`;
  return `${base}${normalizedPath}`;
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

function textToArrayBuffer(text: string): ArrayBuffer {
  const encoded = new TextEncoder().encode(text);
  const buffer = new ArrayBuffer(encoded.byteLength);
  new Uint8Array(buffer).set(encoded);
  return buffer;
}

/** 将知识库下载接口返回的 Blob / 字符串统一转换为 ArrayBuffer */
async function downloadDataToArrayBuffer(data: Blob | string, headers?: Headers): Promise<ArrayBuffer> {
  if (data instanceof Blob) {
    return await data.arrayBuffer();
  }
  const textData = data as string;
  const contentType = headers?.get('content-type') || '';
  if (/^data:.*;base64,/i.test(textData)) {
    return base64ToArrayBuffer(textData.slice(textData.indexOf(',') + 1));
  }
  if (contentType.includes('text/')) {
    return textToArrayBuffer(textData);
  }
  try {
    return base64ToArrayBuffer(textData);
  } catch {
    return textToArrayBuffer(textData);
  }
}

/** 将知识库下载接口返回的 Blob / 字符串统一转换为文本 */
async function downloadDataToText(data: Blob | string): Promise<string> {
  if (typeof data === 'string') return data;
  return await data.text();
}

/**
 * 获取引用的文件下载 URL（用于实际获取文件内容），优先级：
 * 1. item.file_path（API 新返回的文件路径字段）
 * 2. item.metadata?.file_path（嵌套在 metadata 中）
 */
function getCitationDownloadUrl(item: any): string {
  return (item?.file_path || item?.metadata?.file_path || '').trim();
}

/**
 * 获取用于识别文件类型的名称（含扩展名），优先级：
 * 1. item.metadata?.source（已有的源文件名，最可靠）
 * 2. item.file_path（API 返回的路径）
 * 3. item.metadata?.file_path
 */
function getCitationFileName(item: any): string {
  return (item?.metadata?.source || item?.file_path || item?.metadata?.file_path || '').trim();
}

/**
 * 判断是否有可预览的文件（source 有值或 file_path 有值）
 */
function getCitationFileUrl(item: any): string {
  return (item?.file_path || item?.metadata?.file_path || item?.metadata?.source || '').trim();
}

const filePreviewLoading = ref<Record<string, boolean>>({});

async function handlePreviewFileInCanvas(item: any, options?: { autoOpen?: boolean }) {
  const downloadUrl = getCitationDownloadUrl(item);
  const fileName = getCitationFileName(item);
  const knowledgeBaseName = String(item?.knowledge_base_name || '').trim();
  const displayName = item?.metadata?.source
    ? item.metadata.source.split(/[\\/]/).pop() || 'unknown'
    : (downloadUrl || fileName).split(/[\\/]/).pop() || 'unknown';

  // 从文件名提取扩展名（而非 URL），确保类型识别正确
  const ext = getFileExtensionFromPath(fileName);
  const canvasType = extToCanvasType(ext);
  const citationKey = item.__key;

  // 有 file_path 时构造可访问 URL；否则用 metadata.source 构造 URL 兜底
  const fileUrl = downloadUrl
    ? resolveFileUrl(downloadUrl)
    : (fileName ? resolveFileUrl(fileName) : '');

  if (!downloadUrl && !fileName) return;

  filePreviewLoading.value = { ...filePreviewLoading.value, [citationKey]: true };
  try {
    // 历史知识引用缺少 file_path 时，改走知识库下载接口，避免把文件名直接拼到主 API 后导致 404
    if (!downloadUrl && knowledgeBaseName) {
      const { data, headers } = await downloadKnowledgeBaseDoc({
        knowledge_base_name: knowledgeBaseName,
        file_name: fileName,
        preview: true
      });

      if (TEXT_BASED_EXTS.has(ext)) {
        const textContent = await downloadDataToText(data);
        emit('open-artifact', {
          code: textContent,
          lang: canvasType || ext || 'text',
          title: displayName,
          id: citationKey,
          autoOpen: options?.autoOpen
        });
        return;
      }

      if (BINARY_PREVIEW_EXTS.has(ext)) {
        const arrayBuffer = await downloadDataToArrayBuffer(data, headers);
        emit('open-artifact', {
          code: arrayBuffer,
          lang: canvasType || ext || 'text',
          title: displayName,
          id: citationKey,
          autoOpen: options?.autoOpen
        });
        return;
      }

      const content = await downloadDataToText(data);
      emit('open-artifact', {
        code: content,
        lang: canvasType || ext || 'text',
        title: displayName,
        id: citationKey,
        autoOpen: options?.autoOpen
      });
      return;
    }

    const response = await fetch(fileUrl, { credentials: 'omit', cache: 'no-store' });
    if (!response.ok) {
      throw new Error(`文件加载失败 (${response.status})`);
    }

    if (TEXT_BASED_EXTS.has(ext)) {
      const textContent = await response.text();
      emit('open-artifact', {
        code: textContent,
        lang: canvasType || ext || 'text',
        title: displayName,
        id: citationKey,
        autoOpen: options?.autoOpen
      });
      return;
    }

    if (BINARY_PREVIEW_EXTS.has(ext)) {
      const arrayBuffer = await response.arrayBuffer();
      emit('open-artifact', {
        code: arrayBuffer,
        lang: canvasType || ext || 'text',
        title: displayName,
        id: citationKey,
        downloadUrl: fileUrl,
        autoOpen: options?.autoOpen
      });
      return;
    }

    emit('open-artifact', {
      code: fileUrl,
      lang: canvasType || ext || 'text',
      title: displayName,
      id: citationKey,
      autoOpen: options?.autoOpen
    });
  } catch (err) {
    console.error('获取知识库文件内容失败:', err);
    emit('open-artifact', {
      code: fileUrl,
      lang: canvasType || ext || 'text',
      title: displayName,
      id: citationKey,
      autoOpen: options?.autoOpen
    });
  } finally {
    filePreviewLoading.value = { ...filePreviewLoading.value, [citationKey]: false };
  }
}

function handleEditModeChanged(editMode: boolean) {
  isEditMode.value = editMode;
}

function handleSelectionModeChanged(action: boolean | string | { action: string, messageId: string | null }) {
  if (typeof action === 'object' && action.action === 'toggle') {
    emit('selection-mode-changed', { action: 'toggle', messageId: messageId.value })
  } else {
    emit('selection-mode-changed', action)
  }
}

const userCollapsedReasoning = ref(false);
const isAutoCollapseInProgress = ref(false);
const hasCollapsedAfterContentStart = ref(false);
const hasCollapsedAfterToolStart = ref(false);
const autoCollapsedReasoningPanels = ref<Record<string, boolean>>({});
let reasoningPanelInternalUpdateCount = 0;

function updateReasoningPanels(nextKeys: string[], internal = false, defer = false) {
  const applyUpdate = () => {
    if (internal) {
      reasoningPanelInternalUpdateCount += 1;
      isAutoCollapseInProgress.value = true;
    }
    activeReasoningPanels.value = nextKeys;
    if (internal) {
      Promise.resolve().then(() => {
        reasoningPanelInternalUpdateCount = Math.max(0, reasoningPanelInternalUpdateCount - 1);
        if (reasoningPanelInternalUpdateCount === 0) {
          isAutoCollapseInProgress.value = false;
        }
      });
    }
  };

  if (defer) {
    nextTick(() => applyUpdate());
    return;
  }

  applyUpdate();
}

function isAutoCollapseReasoningEnabled() {
  const preferences = StorageService.get<{ autoCollapseReasoning?: boolean }>('mcp-user-preferences');
  return preferences?.autoCollapseReasoning ?? false;
}

function shouldAutoCollapseCompletedReasoningPanels() {
  if (!props.message.isStreaming || !hasReasoningBlocks.value) return false;
  return isAutoCollapseReasoningEnabled();
}

function getCompletedReasoningPanelKeys() {
  if (!hasReasoningBlocks.value) return [];
  return orchestratorBlocksToRender.value
    .map((block, index) => {
      if (block.type !== 'reasoning') return null;
      return index < orchestratorBlocksToRender.value.length - 1
        ? getOrchestratorBlockKey(block, index)
        : null;
    })
    .filter((key): key is string => !!key);
}

watch(() => props.message.isStreaming, (isStreaming) => {
  if (getReasoningPanelKeys().length > 0) {
    if (isStreaming) {
      const shouldKeepClosed = !hasReasoningBlocks.value
        && (hasCollapsedAfterToolStart.value || hasCollapsedAfterContentStart.value);
      if (!shouldKeepClosed && !userCollapsedReasoning.value) {
        // 开启自动折叠时，已完成的思考面板初始即保持折叠，避免先展开再折叠
        const completedSet = isAutoCollapseReasoningEnabled()
          ? new Set(getCompletedReasoningPanelKeys())
          : null;
        const keysToExpand = getReasoningPanelKeys().filter(key => !completedSet?.has(key));
        updateReasoningPanels(keysToExpand, true);
        if (keysToExpand.length > 0) {
          document.dispatchEvent(new CustomEvent('mcp-panel-expanded', {
            detail: {
              message: props.message,
              isManualExpand: false
            }
          }));
        }
      }
    } else if (userCollapsedReasoning.value) {
      activeReasoningPanels.value = [];
    }
  }
}, { immediate: true });

watch(() => props.message.tool_calls, (toolCalls) => {
  if (
    !hasCollapsedAfterToolStart.value &&
    props.message.isStreaming &&
    toolCalls && Array.isArray(toolCalls) && toolCalls.length > 0
  ) {
    const preferences = StorageService.get<{ autoCollapseToolPanels?: boolean }>('mcp-user-preferences');
    const autoCollapseTools = preferences?.autoCollapseToolPanels ?? false;
    if (autoCollapseTools) {
      updateReasoningPanels([], true);
      hasCollapsedAfterToolStart.value = true;
    }
  }
}, { immediate: true, deep: true });

watch(() => props.message.reasoning_content, () => {
  if (props.message.isStreaming) {
    document.dispatchEvent(new CustomEvent('mcp-message-updated', {
      detail: { message: props.message }
    }));
  }
}, { immediate: false });

watch(activeReasoningPanels, (newVal: string[]) => {
  if (newVal.length === 0) {
    if (!isAutoCollapseInProgress.value) {
      userCollapsedReasoning.value = true;
    }
  }
  else if (newVal.length > 0) {
    userCollapsedReasoning.value = false;

    document.dispatchEvent(new CustomEvent('mcp-panel-expanded', {
      detail: {
        message: props.message,
        isManualExpand: true
      }
    }));

    setTimeout(() => {
      document.dispatchEvent(new CustomEvent('mcp-message-updated', {
        detail: { message: props.message }
      }));
    }, 300);
  }
});

const messageClass = computed(() => {
  return {
    'message-user': props.message.role === 'user',
    'message-assistant': props.message.role === 'assistant',
    'message-tool': props.message.role === 'tool',
    'message-system': props.message.role === 'system'
  };
});

const avatarColor = computed(() => {
  switch (props.message.role) {
    case 'user':
      return '#87d068';
    case 'assistant':
      return '#1890ff';
    case 'tool':
      return '#722ed1';
    case 'system':
      return '#fa8c16';
    default:
      return '#f56a00';
  }
});

const shouldShowMessage = computed(() => {
  const message = props.message;

  if (message.role === 'system') {
    return true;
  }

  if (message.role === 'user') {
    const hasText = !!(message.display_content || message.content);
    const hasFiles = messageFiles.value.length > 0;
    const hasPending = displayPendingCaptureCards.value.length > 0;
    return hasText || hasFiles || hasPending;
  }

  if (message.role === 'tool') {
    return true;
  }

  if (message.role === 'assistant') {
    if ((message as any).isStreaming) {
      return true;
    }
    const hasToolCalls = message.tool_calls && Array.isArray(message.tool_calls) && message.tool_calls.length > 0;
    return !!(message.content || message.reasoning_content || hasToolCalls);
  }

  return true;
});

function handleClick(e: Event) {
  const target = e.target as HTMLElement;

  if (target && target.classList.contains('clickable-image')) {
    if (imageViewerOpen.value) return;

    const src = target.getAttribute('data-src');
    const alt = target.getAttribute('data-alt');

    if (src) {
      currentImageUrl.value = src;
      currentImageAlt.value = alt || '图片';
      imageViewerOpen.value = true;
      e.stopPropagation();
    }
  }
}

function handleConversationComplete() {
  if (messageContentRef.value) {
    const cursors = messageContentRef.value.querySelectorAll('.typing-indicator');
    cursors.forEach(cursor => {
      (cursor as HTMLElement).style.display = 'none';
    });
  }

  // 清理观察器
  if (cursorObserver) {
    cursorObserver.disconnect();
    cursorObserver = null;
  }
}

onMounted(() => {
  const hasAutoOpened = ref(false);

  watch(() => props.message.files, (files) => {
    if (props.message.role !== 'user' || !files || files.length === 0) return;
    if (hasAutoOpened.value) return;

    const firstFile = files[0];
    if (!firstFile || isImageFile(firstFile)) return;

    // 历史消息中的文件只有下载链接（无本地内容），不自动展开，避免加载历史时触发请求
    if (!firstFile.content && !firstFile.parseResult && (firstFile.path || firstFile.url)) return;

    const msgs = chatStore.messages;
    const len = msgs.length;
    let isRecent = false;

    if (len > 0) {
      const last = msgs[len - 1];
      if (last === props.message || (last.id && last.id === props.message.id)) {
        isRecent = true;
      } else if (len > 1) {
        const secondLast = msgs[len - 2];
        if ((secondLast === props.message || (secondLast.id && secondLast.id === props.message.id)) && last.role === 'assistant') {
          isRecent = true;
        }
      }
    }

    if (isRecent) {
      hasAutoOpened.value = true;
      nextTick(() => {
        handleFileClick(firstFile, 0, { autoOpen: true });
      });
    }
  }, { immediate: true, deep: true });

  if (messageContentRef.value) {
    messageContentRef.value.addEventListener('click', handleClick);

    if (props.message.isStreaming) {
      setupCursorObserver();
    }
  }

  EventBus.on(MCP_EVENTS.CONVERSATION_COMPLETE, handleConversationComplete);
});

let cursorObserver: MutationObserver | null = null;

function setupCursorObserver() {
  if (!messageContentRef.value || cursorObserver) return;

  cursorObserver = new MutationObserver((mutations) => {
    let shouldUpdate = false;
    mutations.forEach((mutation) => {
      if (mutation.type === 'childList' || mutation.type === 'characterData') {
        shouldUpdate = true;
      }
    });

    if (shouldUpdate) {
      requestAnimationFrame(() => {
        optimizeCursorPosition();
      });
    }
  });

  const markdownContents = messageContentRef.value.querySelectorAll('.markdown-content');
  markdownContents.forEach(content => {
    cursorObserver?.observe(content, {
      childList: true,
      subtree: true,
      characterData: true
    });
  });
}

onUnmounted(() => {
  if (messageContentRef.value) {
    messageContentRef.value.removeEventListener('click', handleClick);
  }

  if (cursorObserver) {
    cursorObserver.disconnect();
    cursorObserver = null;
  }

  EventBus.off(MCP_EVENTS.CONVERSATION_COMPLETE, handleConversationComplete);
});

watch(() => props.message.isStreaming, (isStreaming) => {
  if (!isStreaming && cursorObserver) {
    cursorObserver.disconnect();
    cursorObserver = null;
  } else if (isStreaming && !cursorObserver) {
    nextTick(() => {
      setupCursorObserver();
    });
  }
});

watch(() => props.message.content, () => {
  if (
    !hasCollapsedAfterContentStart.value &&
    props.message.isStreaming &&
    props.message.content && props.message.content.trim()
  ) {
    if (isAutoCollapseReasoningEnabled()) {
      updateReasoningPanels([], true);
      hasCollapsedAfterContentStart.value = true;
    }
  }

  nextTick(() => {
    if (messageContentRef.value) {
      messageContentRef.value.removeEventListener('click', handleClick);
      messageContentRef.value.addEventListener('click', handleClick);

      optimizeCursorPosition();
    }
  });
}, { immediate: true });

watch(getReasoningPanelKeys, (newKeys, oldKeys) => {
  const autoCollapse = isAutoCollapseReasoningEnabled();
  if (!props.message.isStreaming) {
    // 开启自动折叠时，切换到历史会话后思考面板保持折叠状态
    if (!userCollapsedReasoning.value && !autoCollapse) {
      updateReasoningPanels([...newKeys], true);
    }
    return;
  }
  const shouldKeepClosed = !hasReasoningBlocks.value
    && (hasCollapsedAfterToolStart.value || hasCollapsedAfterContentStart.value);
  if (shouldKeepClosed || userCollapsedReasoning.value) return;
  const previousKeys = oldKeys || [];
  const completedSet = autoCollapse ? new Set(getCompletedReasoningPanelKeys()) : null;
  const newlyAddedKeys = newKeys.filter(key => !previousKeys.includes(key) && !completedSet?.has(key));
  const retainedKeys = activeReasoningPanels.value.filter(key => {
    return newKeys.includes(key) && !autoCollapsedReasoningPanels.value[key];
  });
  if (newlyAddedKeys.length === 0) {
    updateReasoningPanels(retainedKeys, true);
    return;
  }
  updateReasoningPanels([...retainedKeys, ...newlyAddedKeys], true);
}, { immediate: true });

watch(getCompletedReasoningPanelKeys, (completedKeys) => {
  if (!shouldAutoCollapseCompletedReasoningPanels()) return;
  const nextCompletedMap = { ...autoCollapsedReasoningPanels.value };
  let changed = false;
  const completedKeySet = new Set(completedKeys);
  const nextActiveKeys = activeReasoningPanels.value.filter((key) => {
    if (!completedKeySet.has(key)) return true;
    nextCompletedMap[key] = true;
    changed = true;
    return false;
  });
  const staleKeys = Object.keys(nextCompletedMap).filter(key => !getReasoningPanelKeys().includes(key));
  staleKeys.forEach((key) => {
    delete nextCompletedMap[key];
  });
  if (!changed && staleKeys.length === 0) return;
  autoCollapsedReasoningPanels.value = nextCompletedMap;
  updateReasoningPanels(nextActiveKeys, true, true);
}, { immediate: true });

watch(() => props.message.reasoning_content, () => {
  if (props.message.isStreaming) {
    nextTick(() => {
      optimizeCursorPosition();
    });
  }
});

function optimizeCursorPosition() {
  if (!messageContentRef.value || !props.message.isStreaming) return;

  const cursorContainers = messageContentRef.value.querySelectorAll('.markdown-content-with-cursor');
  cursorContainers.forEach(cursorContainer => {
    const markdownContent = cursorContainer.querySelector('.markdown-content');
    const typingIndicator = cursorContainer.querySelector('.typing-indicator') as HTMLElement;

    if (!markdownContent || !typingIndicator) return;

    typingIndicator.style.cssText = '';

    if (!markdownContent.textContent?.trim()) {
      typingIndicator.style.display = 'inline';
      return;
    }

    const lastCharRect = getLastCharacterRect(markdownContent);

    if (lastCharRect) {
      const containerRect = cursorContainer.getBoundingClientRect();

      typingIndicator.style.position = 'absolute';
      typingIndicator.style.left = `${lastCharRect.right - containerRect.left}px`;
      typingIndicator.style.top = `${lastCharRect.top - containerRect.top}px`;
      typingIndicator.style.height = `${lastCharRect.height}px`;
      typingIndicator.style.lineHeight = `${lastCharRect.height}px`;
      typingIndicator.style.display = 'inline';
      typingIndicator.style.zIndex = '999';
    } else {
      typingIndicator.style.display = 'inline';
    }
  });
}

function handleSelectionChanged(messageId: string, selected: boolean) {
  emit('selection-changed', messageId, selected)
}

function getLastCharacterRect(element: Element): DOMRect | null {
  const walker = document.createTreeWalker(
    element,
    NodeFilter.SHOW_TEXT,
    {
      acceptNode: (node) => {
        return node.textContent && node.textContent.trim() ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    }
  );

  let lastTextNode: Text | null = null;
  let currentNode;

  // 找到最后一个有内容的文本节点
  while ((currentNode = walker.nextNode())) {
    lastTextNode = currentNode as Text;
  }

  if (!lastTextNode) {
    return null;
  }

  const range = document.createRange();
  range.selectNodeContents(lastTextNode);
  range.collapse(false);

  const rects = range.getClientRects();
  const lastRect = rects[rects.length - 1];

  return lastRect || null;
}
</script>

<style scoped>
.agent-waiting-status {
  margin: 10px 0;
  color: var(--text-secondary, #808080);
  font-size: 13px;
  line-height: 24px;
}

.message-process {
  margin: 10px 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-color, rgba(128, 128, 128, 0.16));
}

.message-process-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  color: var(--text-secondary, #808080);
  font-size: 13px;
  line-height: 24px;
  cursor: pointer;
  list-style: none;
  user-select: none;
}

.message-process-summary::-webkit-details-marker {
  display: none;
}

.message-process-summary:hover {
  color: var(--text-primary, #333);
}

.message-process-summary:focus-visible {
  outline: 2px solid var(--text-secondary, #808080);
  outline-offset: 4px;
  border-radius: 4px;
}

.message-process-chevron {
  transition: transform 180ms ease;
}

.message-process[open] > .message-process-summary .message-process-chevron,
.message-process-group[open] > .message-process-summary .message-process-chevron {
  transform: rotate(90deg);
}

.message-process-group {
  margin: 5px 0;
}

.message-process-group-body {
  padding-left: 14px;
  border-left: 1px solid var(--border-color, rgba(128, 128, 128, 0.16));
}

.message-process-body {
  padding-top: 6px;
  min-width: 0;
}

@media (prefers-reduced-motion: reduce) {
  .message-process-chevron {
    transition: none;
  }
}

.typing-indicator {
  pointer-events: none;
}

/* ---- 思考块：aicss.dev Thinking + Reasoning 原版样式（宽度自适应消息区）---- */
.reasoning-content.tr {
  display: flex;
  flex-direction: column;
  width: 100%;
  font-family: "Inter", system-ui, sans-serif;
  /* 顶部间距统一在下方 .reasoning-content.tr / .is-thinking-placeholder 规则里维护 */
  animation: tr-block-in 320ms cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes tr-block-in {
  from {
    opacity: 0;
  }

  to {
    opacity: 1;
  }
}

.tr-collapsible {
  display: grid;
  grid-template-rows: 1fr;
  opacity: 1;
  transition: grid-template-rows 320ms cubic-bezier(0.22, 1, 0.36, 1),
    opacity 220ms ease;
}

.tr-collapsible.is-collapsed {
  grid-template-rows: 0fr;
  opacity: 0;
  pointer-events: none;
}

.tr-inner {
  min-height: 0;
  overflow: hidden;
}

/* viewport: grows with the content, then caps at 180px. While thinking
   the stream auto-scrolls behind a soft fade; once unfolded by the user
   it becomes natively scrollable and the fades follow the scroll position. */
.tr-viewport {
  margin-top: 6px;
  overflow: hidden;
  transition: height 360ms cubic-bezier(0.22, 1, 0.36, 1);
}

/* 展开后是原生滚动。滚动条逻辑与 chat-history 保持一致：
   闲置时滑块透明隐藏，滚动时才显形，停止 600ms 后淡出；
   指针压在滑块上靠 :hover 维持可见。
   折叠态不显示——那时视口是 overflow:hidden + translateY 自动跟随，
   滚动条和钉底会互相打架。 */
.tr-viewport.is-scroll {
  overflow-y: auto;
  scrollbar-width: thin;
}

.tr-viewport.is-scroll::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.tr-viewport.is-scroll::-webkit-scrollbar-track {
  background-color: transparent;
}

.tr-viewport.is-scroll::-webkit-scrollbar-thumb {
  background-color: var(--tr-sb, rgba(0, 0, 0, 0.15));
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.tr-viewport.is-scroll::-webkit-scrollbar-thumb:active {
  background-color: var(--tr-sb-active, rgba(0, 0, 0, 0.25));
}

.tr-viewport.is-scroll:not(.hide-scrollbar) {
  scrollbar-color: var(--tr-sb, rgba(0, 0, 0, 0.15)) transparent;
  transition: scrollbar-color 0.2s ease;
}

.tr-viewport.is-scroll.hide-scrollbar {
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
}

.tr-viewport.is-scroll.hide-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.2s ease;
}

.tr-viewport.is-scroll.hide-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: var(--tr-sb, rgba(0, 0, 0, 0.15));
}

.tr-viewport.is-scroll.hide-scrollbar::-webkit-scrollbar-thumb:active {
  background-color: var(--tr-sb-active, rgba(0, 0, 0, 0.25));
}

.tr-stream {
  display: flex;
  flex-direction: column;
  gap: 4px;
  transition: transform 560ms cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}

/* ---- 暗色主题适配（aicss 原版暗色变量）---- */
[data-theme='dark'] .reasoning-content.tr {
  --tre-label: #8a8a8a;
  --tre-verb: #b5b5b5;
  --tre-chevron: #8a8a8a;
  --tre-hover: #c3c3c3;
  --tr-sb: rgba(255, 255, 255, 0.15);
  --tr-sb-active: rgba(255, 255, 255, 0.25);
  /* 流光的波谷同样朝背景色淡出：暗色下自然变暗，亮色下自然变亮 */
  --tr-shine-base: #b5b5b5;
  --tr-shine-dim: rgba(181, 181, 181, 0.45);
}

[data-theme='dark'] .reasoning-text {
  color: #8a8a8a;
}

.reasoning-text :deep(.markdown-content),
.reasoning-text :deep(.markdown-content p),
.reasoning-text :deep(.markdown-content li),
.reasoning-text :deep(.markdown-content blockquote) {
  font-size: 13px;
  color: #61666b;
}

/* The reasoning viewport clips overflow for collapse/streaming,
   so code blocks need a little horizontal inset to keep their shadow visible. */
.reasoning-text :deep(.code-block-wrapper) {
  width: auto;
  margin-left: 8px;
  margin-right: 8px;
}

.reasoning-text :deep(.markdown-content p strong),
.reasoning-text :deep(.markdown-content p b),
.reasoning-text :deep(.markdown-content h1),
.reasoning-text :deep(.markdown-content h2),
.reasoning-text :deep(.markdown-content h3),
.reasoning-text :deep(.markdown-content h4),
.reasoning-text :deep(.markdown-content h5),
.reasoning-text :deep(.markdown-content h6) {
  /* 亮色下强调文字要比正文（#61666b）更深，才读得出层级 */
  color: #3d4245;
}

[data-theme='dark'] .reasoning-text :deep(.markdown-content),
[data-theme='dark'] .reasoning-text :deep(.markdown-content p),
[data-theme='dark'] .reasoning-text :deep(.markdown-content li),
[data-theme='dark'] .reasoning-text :deep(.markdown-content blockquote) {
  color: #8a8a8a;
}

[data-theme='dark'] .reasoning-text :deep(.markdown-content p strong),
[data-theme='dark'] .reasoning-text :deep(.markdown-content p b),
[data-theme='dark'] .reasoning-text :deep(.markdown-content h1),
[data-theme='dark'] .reasoning-text :deep(.markdown-content h2),
[data-theme='dark'] .reasoning-text :deep(.markdown-content h3),
[data-theme='dark'] .reasoning-text :deep(.markdown-content h4),
[data-theme='dark'] .reasoning-text :deep(.markdown-content h5),
[data-theme='dark'] .reasoning-text :deep(.markdown-content h6) {
  color: #b5b5b5;
}

.plain-text {
  white-space: pre-wrap;
  word-break: break-word;
}

.message-files {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 8px;
  width: 100%;
}

.message-pending-capture-list {
  width: 235px;
  max-width: 235px;
}

.message-pending-capture-card {
  width: 100%;
  padding: 12px;
  border-radius: 32px;
  border: 1px solid rgba(226, 232, 240, 0.95);
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0) 52%),
    linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.96));
  box-shadow:
    0 18px 40px rgba(15, 23, 42, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  box-sizing: border-box;
  overflow: hidden;
  animation: message-image-gallery-enter 0.55s cubic-bezier(0.22, 1, 0.36, 1);
}

.message-pending-capture-card.is-dissolving {
  pointer-events: none;
  animation: capture-pending-dissolve 0.56s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.message-pending-capture-visual {
  position: relative;
  width: 100%;
  height: 184px;
  border-radius: 24px;
  overflow: hidden;
  background: linear-gradient(180deg, #edf4ff 0%, #dbeafe 100%);
  border: 1px solid rgba(191, 219, 254, 0.78);
}

.message-pending-capture-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.message-pending-capture-particles span {
  position: absolute;
  left: var(--particle-origin-x, 50%);
  top: var(--particle-origin-y, 50%);
  width: var(--particle-size, 8px);
  height: var(--particle-size, 8px);
  border-radius: 999px;
  background: radial-gradient(circle at 35% 35%, rgba(255, 255, 255, 0.96), rgba(129, 140, 248, 0.88) 48%, rgba(59, 130, 246, 0.72));
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.28);
  opacity: 0;
  transform: translate(-50%, -50%) scale(0.24);
}

.message-pending-capture-card.is-dissolving .message-pending-capture-particles span {
  animation: capture-particle-drift 0.54s cubic-bezier(0.2, 0.82, 0.26, 1) forwards;
  animation-delay: var(--particle-delay, 0ms);
}

.message-pending-capture-shimmer {
  position: absolute;
  inset: -20%;
  background: linear-gradient(120deg, rgba(255, 255, 255, 0) 24%, rgba(255, 255, 255, 0.62) 48%, rgba(255, 255, 255, 0) 72%);
  transform: translateX(-100%);
  animation: capturePendingShimmer 1.8s ease-in-out infinite;
}

.message-pending-capture-bar {
  display: flex;
  gap: 5px;
  align-items: center;
  padding: 14px 14px 10px;
}

.message-pending-capture-bar span {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: rgba(110, 138, 179, 0.58);
}

.message-pending-capture-lines {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 8px 14px 0;
}

.message-pending-capture-line {
  height: 10px;
  border-radius: 999px;
  background: rgba(96, 165, 250, 0.18);
}

.message-pending-capture-line.w-74 {
  width: 74%;
}

.message-pending-capture-line.w-66 {
  width: 66%;
}

.message-pending-capture-line.w-52 {
  width: 52%;
}

.message-pending-capture-badge {
  position: absolute;
  left: 14px;
  right: 14px;
  bottom: 14px;
  padding: 8px 10px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.92);
  color: #184a84;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
  box-shadow: 0 8px 18px rgba(37, 99, 235, 0.1);
}

@media (prefers-reduced-motion: reduce) {

  .message-pending-capture-card,
  .message-image-gallery,
  .message-image-card,
  .message-image-card.is-active,
  .message-image-stage-shadow,
  .message-image-reveal-flash,
  .message-pending-capture-particles span {
    animation: none !important;
    transition: none !important;
  }

  .message-pending-capture-card.is-dissolving {
    opacity: 0;
  }
}






@keyframes capturePendingShimmer {
  0% {
    transform: translateX(-100%);
  }

  100% {
    transform: translateX(100%);
  }
}

@keyframes capture-pending-dissolve {
  0% {
    opacity: 1;
    transform: translateY(0) scale(1);
    filter: blur(0);
  }

  40% {
    opacity: 0.82;
    transform: translateY(-2px) scale(0.992);
    filter: blur(0.2px);
  }

  100% {
    opacity: 0;
    transform: translateY(-8px) scale(0.92);
    filter: blur(7px);
  }
}

@keyframes capture-particle-drift {
  0% {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.2);
  }

  12% {
    opacity: 0.96;
  }

  100% {
    opacity: 0;
    transform: translate(calc(-50% + var(--particle-x)), calc(-50% + var(--particle-y))) scale(var(--particle-scale));
  }
}










.document-card {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  max-width: 100%;
  min-width: 200px;
}

.document-card:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.doc-icon {
  width: 32px;
  height: 32px;
  margin-right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.doc-icon img {
  width: 24px;
  height: 24px;
}

.doc-info {
  flex: 1;
  min-width: 0;
}

.doc-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.doc-meta {
  font-size: 12px;
  color: #9ca3af;
}

.message-avatar-icon {
  width: 100%;
  height: 100%;
}

.assistant-avatar-icon {
  width: 35px;
  height: 35px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.message-assistant .message-avatar :deep(.ant-avatar.ant-avatar-image) {
  background-color: #ffffff !important;
}

/* 知识引用折叠容器与内容样式 */
.kb-citations-collapse {
  margin: 6px 0 6px 0;
}

.kb-citations-collapse :deep(.ant-collapse) {
  border: 1px solid #e7edf4;
  border-radius: 14px;
  overflow: hidden;
  background: #ffffff;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.03);
}

.kb-citations-collapse :deep(.ant-collapse-item) {
  border-bottom: 1px solid #edf2f7;
}

.kb-citations-collapse :deep(.ant-collapse-item:last-child) {
  border-bottom: none;
}

.kb-citations-collapse :deep(.ant-collapse-item:last-child),
.kb-citations-collapse :deep(.ant-collapse-item:last-child > .ant-collapse-header) {
  border-radius: 14px 14px 0 0;
}

.kb-citations-collapse :deep(.ant-collapse-header) {
  background:
    radial-gradient(circle at top left, rgba(112, 86, 255, 0.12), transparent 52%),
    radial-gradient(circle at right center, rgba(84, 140, 255, 0.09), transparent 46%),
    linear-gradient(135deg, rgba(252, 253, 255, 0.99), rgba(243, 247, 255, 0.98));
  padding: 12px 16px;
  color: #38508f;
  font-weight: 500;
  box-shadow: none;
}

.kb-citations-collapse :deep(.ant-collapse-header-text) {
  font-size: 13px;
  font-weight: 600;
  color: #1d3d88;
  letter-spacing: 0.01em;
}

.kb-citations-collapse :deep(.ant-collapse-expand-icon) {
  color: #6a7db4;
  font-size: 12px;
}

.kb-citations-collapse :deep(.ant-collapse-arrow) {
  font-size: 12px;
}

.kb-citations-collapse :deep(.ant-collapse-content) {
  border-top: 1px solid #e3ebf7;
}

.kb-citations-collapse :deep(.ant-collapse-content-box) {
  padding: 14px 16px 16px;
  background:
    radial-gradient(circle at top right, rgba(112, 86, 255, 0.05), transparent 38%),
    radial-gradient(circle at left bottom, rgba(84, 140, 255, 0.05), transparent 34%),
    linear-gradient(180deg, #fbfcff 0%, #f4f8ff 100%);
}

.kb-citations-stage {
  padding: 0;
  display: grid;
  gap: 10px;
}

.kb-citations-summary {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 2px;
  color: #60708e;
  font-size: 12px;
}

.kb-summary-text {
  white-space: nowrap;
}

.kb-summary-divider {
  color: #c8d4eb;
}

.kb-citation-card {
  padding: 14px 14px 12px;
  border-radius: 14px;
  border: 1px solid #e2ebf7;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(247, 250, 255, 0.98) 100%);
  box-shadow: none;
}

.kb-citation-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
}

.kb-citation-main {
  min-width: 0;
  flex: 1;
}

.kb-citation-caption {
  display: inline-flex;
  margin-bottom: 6px;
  font-size: 11px;
  color: #8a9aba;
  letter-spacing: 0.02em;
}

.kb-citation-title-line {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
}

.kb-citation-title {
  font-size: 15px;
  line-height: 1.4;
  font-weight: 600;
  color: #1f376d;
  word-break: break-word;
}

.kb-citation-path {
  margin-top: 6px;
  color: #8292b2;
  font-size: 12px;
  line-height: 1.5;
  word-break: break-word;
}

.kb-citation-relevance {
  flex-shrink: 0;
  padding-top: 1px;
  font-size: 12px;
  font-weight: 600;
  color: #4d6fff;
}

.kb-citation-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.kb-citation-meta-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 9px;
  border-radius: 9px;
  background: #f4f8ff;
  border: 1px solid #e2ebf8;
}

.kb-citation-meta-key {
  font-size: 12px;
  color: #8ea0bf;
}

.kb-citation-meta-val {
  font-size: 12px;
  font-weight: 600;
  color: #41567f;
}

.kb-citation-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.kb-citation-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 9px;
  border-radius: 999px;
  background: #f4f8ff;
  border: 1px solid #e2ebf8;
  color: #61759b;
  font-size: 12px;
}

.kb-citation-tag.is-muted {
  color: #93a3c2;
}

.kb-citation-excerpt-shell {
  margin-top: 12px;
  border-radius: 12px;
  border: 1px solid #e5edf8;
  background: linear-gradient(180deg, #fbfcff 0%, #f5f8fe 100%);
  overflow: hidden;
}

.kb-citation-content {
  font-size: 13px;
  white-space: pre-wrap;
  word-break: break-word;
  color: #41506b;
  line-height: 1.75;
  padding: 4px 0;
}

.kb-quote-line {
  padding: 12px 14px;
  border-bottom: 1px solid #e5edf8;
}

.kb-quote-copy {
  display: block;
}

.kb-quote-line:last-child {
  border-bottom: none;
}

.kb-citation-content.clamped {
  max-height: 188px;
  overflow: hidden;
  position: relative;
}

.kb-citation-content.clamped:after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 56px;
  background: linear-gradient(to bottom, rgba(251, 252, 255, 0), #f5f8fe);
}

.kb-citation-footer {
  margin-top: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.kb-citation-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.kb-preview-button {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  height: 28px;
  font-size: 12px;
  color: #2563eb;
  border: 1px solid #bfdbfe;
  border-radius: 8px;
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
  transition: all 0.2s ease;
}

.kb-preview-button:hover:not(:disabled) {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: linear-gradient(180deg, #dbeafe 0%, #bfdbfe 100%);
  box-shadow: 0 1px 4px rgba(37, 99, 235, 0.15);
}

.kb-preview-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.kb-preview-icon {
  width: 16px;
  height: 16px;
  display: block;
  filter: brightness(0) saturate(100%) invert(27%) sepia(98%) saturate(4058%) hue-rotate(213deg) brightness(97%) contrast(96%);
}

.kb-citation-footprint {
  color: #6c7fa1;
}

.kb-citation-footprint-label {
  font-size: 12px;
}

.kb-expand-button {
  padding-inline: 0;
  font-size: 12px;
  color: #2563eb;
}

.kb-expand-button:hover {
  color: #1d4ed8;
}

.kb-citation-card:not(.has-overflow) .kb-citation-content.clamped:after {
  display: none;
}

.kb-citation-card:not(.has-overflow) .kb-expand-button {
  display: none;
}

@media (max-width: 768px) {

  .kb-citation-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .kb-citations-collapse :deep(.ant-collapse-content-box) {
    padding: 14px;
  }

  .kb-citation-footer {
    flex-direction: column;
    align-items: flex-start;
  }

  .kb-citation-actions {
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
}

.orchestrator-avatar {
  background: linear-gradient(135deg, #a78bfa, #8b5cf6);
  color: white;
  box-shadow: 0 2px 6px rgba(139, 92, 246, 0.25);
  border: 1px solid rgba(255, 255, 255, 0.2);
}


/* 思考块与「正在思考」占位共用同一顶部间距：
   占位（.message-text.is-thinking-placeholder）会被真实的 .reasoning-content.tr 替换，
   两者间距不一致时头部会在思考开始的瞬间上下跳动。 */
.reasoning-content.tr,
.message-text.is-thinking-placeholder {
  margin-top: 12px;
}

.reasoning-content.tr {
  margin-bottom: 9px;
}

.tr-viewport {
  margin-left: 8px;
  padding-left: 16px;
  border-left: 1px solid var(--pb-rail);
}

.reasoning-text {
  box-sizing: border-box;
  padding: 12px 16px;
  border: 1px solid var(--pb-code-border);
  border-radius: 12px;
  background: var(--pb-code-bg);
}

@media (max-width: 600px) {
  .reasoning-text {
    padding: 10px 12px;
  }
}
</style>
