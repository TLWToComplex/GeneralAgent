<template>
  <div 
    class="input-container" 
    :class="{ 'welcome-active': isWelcomeActive }"
  >
    <div
      class="input-stack-wrapper"
      :class="{ 'is-agent-mode': isAgentModeVisualActive }"
      ref="inputStackWrapperRef"
    >
      <InputToolbar
          v-if="!isWelcomeActive"
          :current-stage="currentStage"
          :current-todo="currentTodo"
          :todo-list="todoList"
          :artifacts="artifactHistory"
          :active-artifact-id="activeArtifactId"
          :is-orchestrator-mode="activeAgentType === 'orchestrator'"
          :is-compressing-context="isCompressingContext"
          :compression-status-text="compressionStatusText"
          :compression-info="chatStore.contextCompressionInfo"
          @visibility-change="(visible) => {
            showInputToolbar = visible;
            emit('toolbar-visibility-change', visible);
          }"
          @expand-change="(expanded) => emit('toolbar-expand-change', expanded)"
          @panel-height-change="(height) => emit('toolbar-panel-height-change', height)"
          @open-artifact="(payload) => emit('open-artifact', payload)"
      />
      
      <div class="input-agent-shell" :class="{ 'is-agent-mode': isAgentModeVisualActive, 'is-agent-init': isAgentInitPending }">
        <div class="agent-mode-banner-shell" :class="{ 'is-visible': shouldShowAgentModeBanner }">
          <div class="agent-mode-banner">
            <div class="agent-mode-banner-left">
              <img :src="AgentSelectedSvg" class="agent-mode-banner-icon" alt="Agent selected" />
              <span class="agent-mode-banner-title">{{ agentModeDisplayName }}</span>
            </div>
            <div class="agent-mode-banner-right">
              <transition name="agent-state-swap">
                <div v-if="isAgentInitPending" key="agent-init" class="agent-init-state">
                  <img :src="AgentAnimSvg" class="agent-init-icon" alt="" />
                  <span>智能体初始化中</span>
                </div>
                <button
                  v-else
                  key="agent-exit"
                  type="button"
                  class="agent-mode-exit-btn"
                  @click="exitAssistantMode"
                >
                  <img :src="ExitAgentSvg" class="agent-mode-exit-icon" alt="" />
                  退出智能体模式
                </button>
              </transition>
            </div>
          </div>
        </div>

        <div class="input-bar-outer" :class="{ 'is-dragging': isDragging || isProcessingDrop }">
        
        <transition name="drag-scale">
          <div v-if="isDragging || isProcessingDrop" class="drag-upload-overlay" :class="{ 'is-processing': isProcessingDrop }">
            <div class="drag-visual-core">
              <div class="pulse-ring"></div>
              <div class="pulse-ring delay-1"></div>
              <div class="pulse-ring delay-2" :class="draggedFileType"></div>
              
              <div v-for="(item, index) in draggedItems" 
                   :key="item.id"
                   class="icon-magnet" 
                   :class="[item.type, { 'is-stacked': draggedItems.length > 1 }]"
                   :style="{
                      '--index': index,
                      '--total': draggedItems.length,
                      '--offset': index - (draggedItems.length - 1) / 2
                   }"
              >
                <img v-if="item.type === 'pdf'" :src="PdfSvg" class="drag-file-icon" alt="PDF" />
                <img v-else-if="item.type === 'word'" :src="WordSvg" class="drag-file-icon" alt="Word" />
                <img v-else-if="item.type === 'txt'" :src="TxtSvg" class="drag-file-icon" alt="TXT" />
                <img v-else-if="item.type === 'md'" :src="MarkdownSvg" class="drag-file-icon" alt="MD" />
                <img v-else-if="item.type === 'csv'" :src="ExcelSvg" class="drag-file-icon" alt="CSV" />
                <img v-else-if="item.type === 'ppt'" :src="PptSvg" class="drag-file-icon" alt="PPT" />
                <img v-else-if="item.type === 'zip'" :src="ZipSvg" class="drag-file-icon" alt="ZIP" />
                <div v-else-if="item.type === 'image'" class="drag-image-shell">
                  <UploadImage class="drag-image-icon" />
                </div>
                <PaperclipIcon v-else class="drag-icon" />
              </div>
              
              <!-- 传输光束 -->
              <div class="transfer-beam" :class="draggedFileType"></div>
            </div>
            <span class="drag-text">
              {{ isProcessingDrop ? '正在接收文件...' : '释放文件以上传' }}
            </span>
            <div class="particles">
              <span v-for="n in 8" :key="n" class="particle" :class="draggedFileType" :style="{ '--i': n }"></span>
            </div>
          </div>
        </transition>

        <transition name="content-fade" mode="out-in">
          <div v-if="!isSelectionMode" key="input-content" class="input-content" :class="{ 'sending': isClearingForSend }">
          <div class="image-strip-shell" :class="{ 'has-images': selectedImageFiles.length > 0 }">
            <div v-show="showImageStrip" class="image-strip-container">
              <button
                type="button"
                class="image-strip-scroll-btn image-strip-scroll-btn--left"
                :class="{ visible: showImageLeftMask }"
                aria-label="向左滚动图片列表"
                @click="scrollImageStripLeft"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
              </button>
              <transition-group
                name="image-strip-item"
                tag="div"
                class="image-strip-list"
                ref="imageStripListRef"
                appear
                @scroll="handleImageStripScroll"
                @before-leave="onBeforeImageLeave"
                @after-leave="onAfterImageLeave"
              >
                <div v-for="file in selectedImageFiles" :key="file.id" class="image-strip-item" :class="{ 'is-uploading': isImageUploading(file) }" :data-file-type="'image'">
                  <button type="button" class="image-strip-preview" @click="openImageViewer(file)" :aria-label="`查看图片 ${file.name}`">
                    <img :src="file.imagePreviewUrl" :alt="file.name" class="image-strip-image" />
                    <div v-if="isImageUploading(file)" class="image-strip-uploading">
                      <span class="image-strip-uploading-text">{{ file.uploadStatus === 'parsing' ? '上传中…' : `上传中 ${file.uploadProgress}%` }}</span>
                      <span class="image-strip-uploading-bar" :style="{ width: (file.uploadStatus === 'parsing' ? 100 : file.uploadProgress) + '%' }"></span>
                    </div>
                  </button>
                  <button v-if="file.uploadStatus !== 'uploading' && file.uploadStatus !== 'parsing'" class="image-strip-remove" @click="removeFile(selectedFiles.findIndex(item => item.id === file.id))">
                    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" class="remove-icon-svg">
                      <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </button>
                </div>
              </transition-group>
              <button
                type="button"
                class="image-strip-scroll-btn image-strip-scroll-btn--right"
                :class="{ visible: showImageRightMask }"
                aria-label="向右滚动图片列表"
                @click="scrollImageStripRight"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </button>
            </div>
          </div>

          <div class="file-list-container" :class="{ 'has-files': selectedDocumentFiles.length > 0 }">
            <div class="scroll-mask mask-left" :class="{ visible: showFileLeftMask }" @click="scrollFileLeft">
              <div class="scroll-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="15 18 9 12 15 6"></polyline>
                </svg>
              </div>
            </div>
            <transition-group 
              name="file-preview-card" 
              tag="div" 
              class="file-list-wrapper" 
              ref="fileListRef"
              @scroll="handleFileScroll"
              @before-leave="onBeforeLeave"
            >
              <div v-for="file in selectedDocumentFiles" :key="file.id" class="file-preview-card" :class="{ 'is-uploading': file.uploadStatus === 'uploading' || file.uploadStatus === 'parsing' }" :data-file-type="getFileExtension(file.name).toLowerCase()">
                <div v-if="file.uploadStatus === 'uploading' || file.uploadStatus === 'parsing'" 
                     class="progress-bar-bg" 
                     :style="{ width: (file.uploadStatus === 'parsing' ? 100 : file.uploadProgress) + '%' }"></div>
                
                <div class="file-icon-wrapper">
                    <img :src="getFileIcon(file.name)" :alt="getFileExtension(file.name).toUpperCase()" style="width: 24px; height: 24px;" />
                  </div>
                  <div class="file-info">
                    <span class="file-name" :title="file.name">{{ file.name }}</span>
                    <div class="file-meta">
                      <span v-if="file.uploadStatus === 'uploading'" class="upload-status">上传中...{{ file.uploadProgress }}%</span>
                      <span v-else-if="file.uploadStatus === 'parsing'" class="upload-status">解析中...</span>
                      <span v-else class="file-ext">{{ getFileExtension(file.name) }}</span>
                      
                      <span class="file-meta-sep">·</span>
                      <span class="file-size">{{ formatFileSize(file.size) }}</span>
                      
                      <template v-if="file.uploadStatus === 'success' && file.parseResult?.summary?.total_tokens">
                        <span class="file-meta-sep">·</span>
                        <span class="file-size">{{ formatWordCount(file.parseResult.summary.total_tokens) }}</span>
                      </template>
                    </div>
                  </div>

                  <button v-if="file.uploadStatus !== 'uploading' && file.uploadStatus !== 'parsing'" class="remove-file-btn" @click="removeFile(selectedFiles.findIndex(item => item.id === file.id))">
                    <svg width="10" height="10" viewBox="0 0 16 16" fill="none">
                      <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                  </button>
              </div>
            </transition-group>
            <div class="scroll-mask mask-right" :class="{ visible: showFileRightMask }" @click="scrollFileRight">
              <div class="scroll-btn">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="9 18 15 12 9 6"></polyline>
                </svg>
              </div>
            </div>
          </div>

            <a-textarea
                v-model:value="inputMessage"
                :placeholder="inputPlaceholder"
                :disabled="!isInputEnabled"
                @keydown="handleKeyPress"
                @paste="handlePaste"
                @focus="handleInputFocus"
                @blur="handleInputBlur"
                class="input-bar-textarea"
                :auto-size="{ minRows: isWelcomeActive ? 2 : 1, maxRows: 5 }"
            />
            <div class="input-bar-btn-row">
              <div class="input-left-buttons">
                <a-tooltip v-if="showKnowledgeBaseButton" placement="top" :title="hasSelectedKnowledgeBase || isKbAvailabilityChecking ? null : isKnowledgeBaseEmpty ? '去创建知识库' : '知识库'">
                  <div class="kb-toggle-control" :class="{ 'kb-toggle-control--selected': shouldShowSelectedKnowledgeBaseState, 'kb-toggle-control--open': knowledgeBaseDropdownVisible, 'kb-toggle-control--no-entrance': !kbToggleEntranceActive, 'kb-toggle-control--empty': isKnowledgeBaseEmpty, 'kb-toggle-control--checking': isKbAvailabilityChecking }">
                    <button
                      class="kb-toggle-button"
                      :class="{
                        'kb-toggle-button--selected': shouldShowSelectedKnowledgeBaseState,
                        'kb-toggle-button--open': knowledgeBaseDropdownVisible,
                        'kb-toggle-button--loading': isTogglingKnowledgeBase,
                      }"
                      :disabled="isTogglingKnowledgeBase || isKbAvailabilityChecking"
                      :aria-busy="isTogglingKnowledgeBase || isKbAvailabilityChecking"
                      @click="handleKnowledgeBaseClick"
                    >
                      <div class="kb-toggle-content">
                        <div class="kb-toggle-icon-shell" :class="{ 'kb-toggle-icon-shell--selected': shouldShowSelectedKnowledgeBaseState, 'kb-toggle-icon-shell--loading': isTogglingKnowledgeBase }">
                          <span v-if="isTogglingKnowledgeBase || isKbAvailabilityChecking" class="kb-toggle-loading-spinner" aria-hidden="true"></span>
                          <PlusOutlined v-else-if="isKnowledgeBaseEmpty" class="kb-icon kb-icon-plus" :style="{ width: '12px', height: '12px', fontSize: '12px', color: '#7c8aa5' }" />
                          <RagIcon v-else class="kb-icon" :style="{ width: '18px', height: '18px', color: shouldShowSelectedKnowledgeBaseState ? '#5365e0' : '#5f6f96' }" />
                        </div>
                        <div class="kb-toggle-copy">
                          <div class="kb-toggle-idle-panel">
                            <span class="kb-toggle-idle-text">{{ kbToggleIdleText }}</span>
                          </div>
                        </div>
                      </div>
                    </button>
                    <div class="kb-toggle-active-slot">
                      <a-dropdown
                        v-model:open="knowledgeBaseDropdownVisible"
                        :trigger="['click']"
                        placement="bottomLeft"
                        overlayClassName="kb-dropdown-overlay-custom"
                        @openChange="handleKnowledgeBaseDropdownChange"
                      >
                        <button class="kb-toggle-active-wrapper" type="button" @click.stop>
                          <span class="kb-toggle-selector-text kb-toggle-active-panel">
                            <span class="kb-toggle-active-copy">
                              <span class="kb-toggle-server-text">{{ displayKnowledgeBaseName }}</span>
                            </span>
                            <DownOutlined class="kb-toggle-dropdown-icon" :style="{ transform: knowledgeBaseDropdownVisible ? 'rotate(180deg)' : 'rotate(0)' }" />
                          </span>
                        </button>
                        <template #overlay>
                          <a-menu class="kb-simple-menu">
                            <div class="kb-menu-shell">
                              <div class="kb-menu-header">
                                <div class="kb-menu-header-copy">
                                  <span class="kb-menu-kicker">RAG SPACE</span>
                                  <span class="kb-menu-heading">选择检索范围</span>
                                </div>
                                <div class="kb-menu-filter-shell">
                                  <div class="kb-menu-filter" role="group" aria-label="知识库权限筛选">
                                    <span class="kb-menu-filter-indicator" :style="kbPermissionIndicatorStyle"></span>
                                    <button
                                      class="kb-menu-filter-btn"
                                      :class="{ 'kb-menu-filter-btn--active': kbPermissionFilter === 'public' }"
                                      type="button"
                                      @click.stop="setKnowledgeBasePermissionFilter('public')"
                                    >
                                      公开
                                    </button>
                                    <button
                                      class="kb-menu-filter-btn"
                                      :class="{ 'kb-menu-filter-btn--active': kbPermissionFilter === 'private' }"
                                      type="button"
                                      @click.stop="setKnowledgeBasePermissionFilter('private')"
                                    >
                                      个人
                                    </button>
                                  </div>
                                </div>
                              </div>
                              <div class="kb-menu-actions">
                                <button
                                  class="kb-menu-action-btn kb-menu-action-btn--select"
                                  type="button"
                                  @click.stop="selectAllKnowledgeBases"
                                  :disabled="kbList.length === 0"
                                >
                                  全选
                                </button>
                                <button
                                  class="kb-menu-action-btn kb-menu-action-btn--deselect"
                                  type="button"
                                  @click.stop="deselectAllKnowledgeBases"
                                  :disabled="selectedKnowledgeBaseNames.length === 0"
                                >
                                  取消全选
                                </button>
                              </div>
                              <div class="kb-menu-divider"></div>
                              <div class="kb-menu-body" :class="{ 'kb-menu-body--scrollable': !shouldShowKnowledgeBaseLoading && kbList.length > 0 }">
                                <div v-if="shouldShowKnowledgeBaseLoading" class="kb-menu-msg kb-menu-msg--loading">
                                  <a-spin size="small" /> <span style="margin-left: 8px;">正在连接知识库...</span>
                                </div>
                                <div v-else-if="kbList.length === 0" class="kb-menu-msg">
                                  {{ knowledgeBaseEmptyText }}
                                </div>
                                <template v-else>
                                  <a-menu-item
                                    v-for="kb in kbList"
                                    :key="kb.id"
                                    @click="selectKnowledgeBase(kb)"
                                    :class="{ 'kb-menu-item--selected': selectedKnowledgeBaseNames.includes(kb.name) }"
                                  >
                                    <div class="kb-menu-item-content">
                                      <div class="kb-menu-item-main">
                                        <div class="kb-menu-title-row">
                                          <span class="kb-menu-title">{{ kb.name }}</span>
                                          <span
                                            class="kb-menu-permission-tag"
                                            :class="`kb-menu-permission-tag--${resolveKnowledgeBasePermission(kb)}`"
                                          >
                                            {{ resolveKnowledgeBasePermission(kb) === 'public' ? '公开' : '个人' }}
                                          </span>
                                        </div>
                                        <span class="kb-menu-subtitle">{{ selectedKnowledgeBaseNames.includes(kb.name) ? '当前检索域' : '点击加入当前对话' }}</span>
                                      </div>
                                      <span class="kb-menu-item-badge" :class="{ 'kb-menu-item-badge--selected': selectedKnowledgeBaseNames.includes(kb.name) }">
                                        <svg v-if="selectedKnowledgeBaseNames.includes(kb.name)" class="check-icon" viewBox="0 0 12 12" fill="none">
                                          <path d="M10 3L4.5 8.5L2 6" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                                        </svg>
                                        <span v-else>+</span>
                                      </span>
                                    </div>
                                  </a-menu-item>
                                </template>
                              </div>
                            </div>
                          </a-menu>
                        </template>
                      </a-dropdown>
                    </div>
                  </div>
                </a-tooltip>
                <a-tooltip v-else-if="selectedAgentName" placement="top">
                  <template #title>
                    <span>Agent</span>
                  </template>
                  <button class="agent-button" :class="{ 'has-selected-agent': !!selectedAgentName }" @click="openAgentPicker">
                    <div class="agent-content">
                      <img :src="AgentSvg" class="agent-icon-img" alt="Agent" />
                      <div class="server-info" :class="{ 'is-visible': !!selectedAgentName }" :aria-hidden="!selectedAgentName">
                        <div class="divider"></div>
                        <span class="server-text">已开启智能体</span>
                      </div>
                    </div>
                  </button>
                </a-tooltip>
              </div>

              <div class="input-right-buttons">
                <a-tooltip v-if="showNewChatButton" placement="top">
                  <template #title>
                    <span>新对话</span>
                  </template>
                  <a-button class="new-chat-button" size="large" type="text" @click="initNewChat">
                    <NewChatIcon style="width: 25px; height: 25px; margin-top: -1px;"/>
                  </a-button>
                </a-tooltip>

                <a-tooltip v-if="showNewChatButton" placement="top">
                  <template #title>
                    <span>画布</span>
                  </template>
                  <a-button class="canvas-button" size="large" type="text" @click="toggleInputToolbar">
                    <img :src="showInputToolbar ? CanvasSelectedSvg : CanvasSvg" style="width: 26px; height: 26px; margin-left: 2px;" alt="Canvas"/>
                  </a-button>
                </a-tooltip>

                <export-button v-if="showNewChatButton"/>

                <a-tooltip v-if="showKnowledgeBaseButton || !selectedAgentName" placement="top">
                  <template #title>
                    <span>智能体</span>
                  </template>
                  <button class="agent-button" :class="{ 'has-selected-agent': !!selectedAgentName }" @click="openAgentPicker">
                    <div class="agent-content">
                      <img :src="AgentSvg" class="agent-icon-img" alt="Agent" />
                      <div class="server-info" :class="{ 'is-visible': !!selectedAgentName }" :aria-hidden="!selectedAgentName">
                        <div class="divider"></div>
                        <span class="server-text">已开启智能体</span>
                      </div>
                    </div>
                  </button>
                </a-tooltip>

                <transition name="upload-btn">
                  <div v-if="activeAgentType !== 'orchestrator'" class="upload-btn-wrapper">
                    <a-tooltip placement="top">
                      <template #title>
                        <span>上传文件</span>
                      </template>
                      <a-button class="upload-button" size="large" type="text" @click="triggerWordUpload">
                        <PaperclipIcon style="width: 20px; height: 20px;"/>
                      </a-button>
                    </a-tooltip>
                  </div>
                </transition>
                <!-- 图片上传入口仅在普通对话下展示，DeepAgent 模式下移除 -->
                <transition name="upload-btn">
                  <div v-if="activeAgentType === 'assistant'" class="upload-btn-wrapper">
                    <a-tooltip placement="top">
                      <template #title>
                        <span>上传图片</span>
                      </template>
                      <a-button class="upload-button" size="large" type="text" @click="triggerImageUpload">
                        <UploadImage style="width: 20px; height: 20px; margin-top: -1px; margin-right: -2px;"/>
                      </a-button>
                    </a-tooltip>
                  </div>
                </transition>
                <!-- 普通对话按 fileAccept 限制文档类型；DeepAgent 支持全部文件格式 -->
                <input
                    ref="wordUploadInputRef"
                    type="file"
                    multiple
                    :accept="fileAccept"
                    style="display: none;"
                    @change="handleWordUploadChange"
                />
                <input
                    ref="imageUploadInputRef"
                    type="file"
                    multiple
                    accept="image/*"
                    style="display: none;"
                    @change="handleImageUploadChange"
                />
    
                <a-divider type="vertical" style="height: 30px;"/>
    
                <button
                    class="custom-send-button"
                    :disabled="isButtonDisabled"
                    @click="handleButtonClick"
                    :class="{ 
                      'send-state': !isAgentInitPending && !chatStore.isProcessing && !isSubmitting && !isWaitingForResponse && !isFileProcessing,
                      'processing-state': (chatStore.isProcessing || isSubmitting) && !isFileProcessing,
                      'waiting-state': isAgentInitPending || isWaitingForResponse || isFileProcessing,
                      'transition-state': isTransitioning
                    }"
                >
                  <transition name="icon-fade">
                    <div v-if="isAgentInitPending" class="loading-spinner" key="agent-init"></div>
                    <template v-else-if="!chatStore.isProcessing && !isSubmitting && !isWaitingForResponse && !isFileProcessing">
                      <VoiceWaveIcon v-if="isVoiceInputActive" :loading="isConnecting" :level="audioLevel" :frequency="audioFrequency" class="voice-wave-icon" key="voice-wave"/>
                      <SendIcon v-else-if="inputMessage.trim().length > 0 || selectedFiles.length > 0 || !isAsrConfigured" class="send-button-icon" key="send"/>
                      <VoiceIcon v-else class="voice-button-icon" key="voice"/>
                    </template>
                    <template v-else-if="!isWaitingForResponse && !isFileProcessing">
                      <StopIcon class="stop-button-icon" key="stop"/>
                    </template>
                    <div v-else class="loading-spinner" key="loading"></div>
                  </transition>
                </button>
              </div>
            </div>
          </div>
    
          <div v-else key="selection-content" class="selection-content">
            <div class="selection-buttons-container">
              <button
                  class="toolbar-btn select-all-btn"
                  @click="handleToggleAll"
                  title="全选/取消全选"
              >
                <div class="custom-checkbox" :class="{ 'selected': isAllSelected, 'indeterminate': hasSelection && !isAllSelected }">
                  <div class="checkbox-inner">
                    <svg v-if="isAllSelected" class="check-icon" viewBox="0 0 12 12" fill="none">
                      <path d="M10 3L4.5 8.5L2 6" stroke="white" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                    <div v-else-if="hasSelection && !isAllSelected" class="indeterminate-icon"></div>
                  </div>
                </div>
                <span class="btn-text">全选</span>
              </button>
    
              <div class="toolbar-center">
                <button
                    class="tool-btn copy-tool-btn"
                    @click="handleCopySelected"
                    :disabled="!hasSelection"
                    title="复制选中的对话内容"
                >
                  <CopyIcon class="tool-icon"/>
                  <span class="tool-text">复制文本</span>
                </button>
    
                <export-button
                    :is-selection-mode="true"
                    :has-selection="hasSelection"
                    :selected-messages="props.selectedMessages"
                    class="selection-export-btn"
                />
    
                <button
                    class="tool-btn text-export-tool-btn"
                    @click="handleExportText"
                    :disabled="!hasSelection"
                    title="导出选中消息为文本文档"
                >
                  <TextIcon class="tool-icon" style="width: 16px; height: 16px;"/>
                  <span class="tool-text">导出文本</span>
                </button>
                
                <button
                    class="tool-btn markdown-export-tool-btn"
                    @click="handleExportMarkdown"
                    :disabled="!hasSelection"
                    title="导出选中消息为Markdown文档"
                >
                  <MarkdownIcon class="tool-icon" style="width: 16px; height: 16px;"/>
                  <span class="tool-text">导出MD文档</span>
                </button>
              </div>
    
              <button
                  class="toolbar-btn cancel-btn"
                  @click="handleCancelSelection"
                  title="退出选择模式"
              >
                <svg class="cancel-icon" viewBox="0 0 16 16" fill="none">
                  <path d="M12 4L4 12M4 4l8 8" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                <span class="btn-text">取消</span>
              </button>
            </div>
          </div>
        </transition>
        </div>

      </div>

      <div v-if="shouldShowQuickPhrases" class="agent-quick-phrases" role="group" aria-label="常用提问">
        <div class="agent-quick-phrases-header">
          <span class="agent-quick-phrases-title">常用提问</span>
          <div class="agent-quick-phrases-header-right">
            <span class="agent-quick-phrases-count">共 {{ visibleQuickPhrases.length }} 条提问</span>
            <div v-if="totalQuickPhrasePages > 1" class="agent-quick-phrases-pager">
              <button
                type="button"
                class="agent-quick-phrases-page-btn"
                :disabled="quickPhrasePage === 0"
                aria-label="上一页"
                @click="quickPhrasePage--"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="m15 18-6-6 6-6" />
                </svg>
              </button>
              <span class="agent-quick-phrases-page-indicator">{{ quickPhrasePage + 1 }} / {{ totalQuickPhrasePages }}</span>
              <button
                type="button"
                class="agent-quick-phrases-page-btn"
                :disabled="quickPhrasePage >= totalQuickPhrasePages - 1"
                aria-label="下一页"
                @click="quickPhrasePage++"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="m9 18 6-6-6-6" />
                </svg>
              </button>
            </div>
          </div>
        </div>
        <button
          v-for="(phrase, index) in pagedQuickPhrases"
          :key="`agent-phrase-${phrase}`"
          type="button"
          class="agent-quick-phrase-btn"
          :style="{ animationDelay: `${120 + index * 90}ms` }"
          @click="handleQuickPhraseClick(phrase)"
        >
          <span class="agent-quick-phrase-text">{{ phrase }}</span>
          <svg
            class="agent-quick-phrase-arrow"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M17 17 7 7" />
            <path d="M7 17V7h10" />
          </svg>
        </button>
      </div>
    </div>

    <SimpleImageViewer
      v-model:open="showImageViewer"
      :image-url="previewImageUrl"
      :image-alt="previewImageTitle"
      :images="inputViewerImages"
    />

    <a-modal
      v-model:open="uploadConfirmVisible"
      :footer="null"
      :width="520"
      :mask-closable="!isConfirmUploading"
      :keyboard="!isConfirmUploading"
      :closable="!isConfirmUploading"
      centered
      :wrap-class-name="uploadConfirmWrapClass"
      @cancel="cancelPendingDocumentUpload"
    >
      <div class="upload-process-modal">
        <div v-if="uploadConfirmSource === 'drop'" class="upload-process-burst" aria-hidden="true">
          <span v-for="n in 12" :key="n" class="upload-process-particle" :style="{ '--i': n }"></span>
        </div>

        <div class="upload-process-header">
          <div class="upload-process-icon">
            <PaperclipIcon />
          </div>
          <div class="upload-process-heading">
            <h3>选择文档解析方式</h3>
            <p>上传前确认本次文档的处理方式</p>
          </div>
        </div>

        <div class="upload-process-file-panel">
          <div class="upload-process-file-head">
            <span>待上传文件</span>
            <span>{{ pendingDocumentFiles.length }} 个 · {{ formatFileSize(pendingDocumentTotalSize) }}</span>
          </div>
          <div class="upload-process-file-list">
            <div
              v-for="file in pendingDocumentFiles"
              :key="`${file.name}-${file.size}`"
              class="upload-process-file-item"
            >
              <img :src="getFileIcon(file.name)" :alt="getFileExtension(file.name).toUpperCase()" />
              <span class="upload-process-file-name" :title="file.name">{{ file.name }}</span>
              <span class="upload-process-file-size">{{ formatFileSize(file.size) }}</span>
            </div>
          </div>
        </div>

        <div class="upload-process-classification">
          <div class="upload-process-classification-meta">
            <div class="upload-process-classification-label">文件密级</div>
            <div class="upload-process-classification-hint">用于标识本次上传文档的保密等级</div>
          </div>
          <div
            class="upload-process-classification-group"
            :class="{ 'is-internal': pendingClassification === 'internal', 'is-empty': !pendingClassification }"
          >
            <div class="upload-process-classification-indicator"></div>
            <button
              type="button"
              class="upload-process-classification-btn"
              :class="{ 'is-active': pendingClassification === 'public' }"
              @click="pendingClassification = 'public'"
            >
              非密
            </button>
            <button
              type="button"
              class="upload-process-classification-btn"
              :class="{ 'is-active': pendingClassification === 'internal' }"
              @click="pendingClassification = 'internal'"
            >
              内部
            </button>
          </div>
        </div>

        <div class="upload-process-choice-grid">
          <button
            type="button"
            class="upload-process-choice"
            :class="{ 'is-selected': pendingProcessType === 'langchain' }"
            @click="pendingProcessType = 'langchain'"
          >
            <span class="upload-process-choice-mark"></span>
            <span class="upload-process-choice-main">
              <span class="upload-process-choice-title">普通解析</span>
              <span class="upload-process-choice-desc">适合常规文档读取，速度更轻快</span>
            </span>
          </button>

          <button
            type="button"
            class="upload-process-choice"
            :class="{ 'is-selected': pendingProcessType === 'mineru' }"
            @click="pendingProcessType = 'mineru'"
          >
            <span class="upload-process-choice-mark"></span>
            <span class="upload-process-choice-main">
              <span class="upload-process-choice-title">深度解析</span>
              <span class="upload-process-choice-desc">适合复杂 PDF、版式和图文内容</span>
            </span>
          </button>
        </div>

        <div class="upload-process-actions">
          <button
            type="button"
            class="upload-process-cancel"
            :disabled="isConfirmUploading"
            @click="cancelPendingDocumentUpload"
          >
            取消
          </button>
          <button
            type="button"
            class="upload-process-submit"
            :disabled="isConfirmUploading"
            @click="confirmDocumentUpload"
          >
            {{ isConfirmUploading ? '上传中...' : '上传' }}
          </button>
        </div>
      </div>
    </a-modal>
    <a-modal
      v-model:open="classificationModalVisible"
      :footer="null"
      :width="440"
      :mask-closable="false"
      :keyboard="false"
      centered
      wrap-class-name="upload-process-modal-wrap"
      @cancel="cancelFileClassificationModal"
    >
      <div class="upload-process-modal file-classification-modal">
        <div class="upload-process-header">
          <div class="upload-process-icon">
            <PaperclipIcon />
          </div>
          <div class="upload-process-heading">
            <h3>选择文件密级</h3>
            <p>{{ classificationModalMode === 'screenshot' ? '选择本次截图的保密等级' : '选择本次上传文件的保密等级' }}</p>
          </div>
        </div>

        <div class="upload-process-file-panel">
          <div class="upload-process-file-head">
            <span>{{ classificationModalMode === 'screenshot' ? '待发送截图' : '待上传文件' }}</span>
            <span>{{ classificationPendingFiles.length }} 个 · {{ formatFileSize(classificationPendingTotalSize) }}</span>
          </div>
          <div class="upload-process-file-list">
            <div
              v-for="file in classificationPendingFiles"
              :key="`${file.name}-${file.size}`"
              class="upload-process-file-item"
            >
              <img :src="getFileIcon(file.name)" :alt="getFileExtension(file.name).toUpperCase()" />
              <span class="upload-process-file-name" :title="file.name">{{ file.name }}</span>
              <span class="upload-process-file-size">{{ formatFileSize(file.size) }}</span>
            </div>
          </div>
        </div>

        <div class="upload-process-classification">
          <div class="upload-process-classification-meta">
            <div class="upload-process-classification-label">文件密级</div>
            <div class="upload-process-classification-hint">用于标识本次上传文件的保密等级</div>
          </div>
          <div
            class="upload-process-classification-group"
            :class="{ 'is-internal': classificationModalValue === 'internal', 'is-empty': !classificationModalValue }"
          >
            <div class="upload-process-classification-indicator"></div>
            <button
              type="button"
              class="upload-process-classification-btn"
              :class="{ 'is-active': classificationModalValue === 'public' }"
              @click="classificationModalValue = 'public'"
            >
              非密
            </button>
            <button
              type="button"
              class="upload-process-classification-btn"
              :class="{ 'is-active': classificationModalValue === 'internal' }"
              @click="classificationModalValue = 'internal'"
            >
              内部
            </button>
          </div>
        </div>

        <div class="upload-process-actions">
          <button
            type="button"
            class="upload-process-cancel"
            :disabled="classificationUploading"
            @click="cancelFileClassificationModal"
          >
            取消
          </button>
          <button
            type="button"
            class="upload-process-submit"
            :disabled="classificationUploading"
            @click="confirmFileClassificationModal"
          >
            {{ classificationUploading ? '上传中...' : classificationModalSubmitText }}
          </button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import RagIcon from '../icons/RagIcon.vue';
import { DownOutlined, PlusOutlined } from '@ant-design/icons-vue';
import {computed, ref, watch, onMounted, onUnmounted, onActivated, onDeactivated, nextTick} from 'vue';
import { useKnowledgeBaseStore } from '@/stores/knowledgeBaseStore';
import { v4 as uuidv4 } from 'uuid';
import { FileUploadService, type FileProcessType, type UploadResponse } from '@/utils/FileUploadService';
import {useChatStore} from '@/stores/chat-store';
import { listKnowledgeBases, type KnowledgeBasePermissionCode, type KnowledgeBaseVM } from '@/services/knowledgeBase';
import { fetchAndCacheRetrievalConfig } from '@/services/aiSystemConfig';
import { useASR } from '@/composables/useASR';
import SendIcon from '@/components/icons/SendIcon.vue';
import VoiceIcon from '@/components/icons/VoiceIcon.vue';
import VoiceWaveIcon from '@/components/icons/VoiceWaveIcon.vue';
import StopIcon from '@/components/icons/StopIcon.vue';
import NewChatIcon from "@/components/icons/NewChatIcon.vue";
import CanvasSvg from '@/assets/image/svg/canvas.svg';
import CanvasSelectedSvg from '@/assets/image/svg/canvas-selected.svg';
import AgentSvg from '@/assets/image/svg/agent.svg';
import AgentSelectedSvg from '@/assets/image/svg/agent_selected.svg';
import AgentAnimSvg from '@/assets/image/svg/agent-anim.svg';
import ExitAgentSvg from '@/assets/image/svg/exit-agent.svg';
import PaperclipIcon from '@/components/icons/PaperclipIcon.vue';
import UploadImage from '@/components/icons/UploadImage.vue';
import WordSvg from '@/assets/image/svg/Word.svg';
import PdfSvg from '@/assets/image/svg/pdf-icon.svg';
import TxtSvg from '@/assets/image/svg/Txt.svg';
import MarkdownSvg from '@/assets/image/svg/Markdown.svg';
import ExcelSvg from '@/assets/image/svg/Excel.svg';
import PptSvg from '@/assets/image/svg/PPT.svg';
import ZipSvg from '@/assets/image/svg/Zip.svg';
import CadSvg from '@/assets/image/svg/CAD.svg';
import ImageSvg from '@/assets/image/svg/image.svg';
import UnknownSvg from '@/assets/image/svg/Unknown.svg';
import CopyIcon from '@/components/icons/CopyIcon.vue';
import TextIcon from '@/components/icons/TextIcon.vue';
import MarkdownIcon from '@/components/icons/MarkdownIcon.vue';
import ExportButton from '../chat/ExportButton.vue';
import InputToolbar from './InputToolbar.vue';
import SimpleImageViewer from './SimpleImageViewer.vue';
import { http } from '@/utils/http';
import NotificationService from '@/utils/NotificationService';
import StorageService from '@/utils/StorageService';
import { eventBus } from '@/utils/EventBus';
import { getAsrServer, getFileUploadMaxSize } from '@/utils/RuntimeConfig';
import { parseArtifactsFromContent, type Artifact } from '@/utils/artifactParser';
import { extractImagesFromMessages, mergeViewerImages, type ConversationImageItem } from '@/utils/conversationImages';
import { useWorkspaceStorage } from '@/composables/useWorkspaceStorage';
import { estimateImageTokensFromMetadata } from '@/utils/contextMetrics';
import {
  consumeKbToggleEntranceActive,
  getKbListCacheAt,
  getKbListCacheShared,
  invalidateKbListCacheShared,
  setKbListCacheShared,
} from '@/composables/useChatInputKnowledgeBaseState';

interface Props {
  isSelectionMode?: boolean;
  isAllSelected?: boolean;
  hasSelection?: boolean;
  selectedMessages?: any[];
  isWelcomeActive?: boolean;
}

const emit = defineEmits<{
  'toggle-all': []
  'cancel-selection': []
  'copy-selected': []
  'export-text': []
  'export-markdown': []
  'toggle-canvas': []
  'new-chat': []
  'toolbar-visibility-change': [visible: boolean]
  'toolbar-expand-change': [expanded: boolean]
  'toolbar-panel-height-change': [height: number]
  'input-height-change': [height: number]
  'message-submit': [sessionThreadId: string, knowledgeBaseEnabled?: boolean]
  'open-artifact': [payload: { code: Artifact['content']; lang: string; id?: string; isComplete?: boolean; title?: string; downloadUrl?: string; autoOpen?: boolean }]
}>()

const notifyHistorySummaryPending = () => {
  const sessionThreadId = (chatStore.sessionThreadId || '').trim();
  if (sessionThreadId) emit('message-submit', sessionThreadId,
    isKnowledgeBaseEnabled.value && selectedKnowledgeBaseNames.value.length > 0);
};

const inputStackWrapperRef = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;
// 高度上报合帧 + 阈值去抖：出现期间 banner/外壳自身有 0.36s 过渡，
// 逐帧上报会让父级不断改写消息列表的 padding-bottom，形成持续全列表重排。
let heightReportRaf = 0;
let pendingReportHeight = 0;
let lastReportedHeight = -1;
const flushHeightReport = () => {
  heightReportRaf = 0;
  if (lastReportedHeight >= 0 && Math.abs(pendingReportHeight - lastReportedHeight) < 1) return;
  lastReportedHeight = pendingReportHeight;
  emit('input-height-change', pendingReportHeight);
};
const {
  isVoiceActive,
  isConnecting,
  speechRecognitionState,
  startRecording,
  stopRecording,
  audioLevel,
  audioFrequency
} = useASR({
  serverAddress: getAsrServer(),
  onError: (msg) => {
    console.error('ASR Error:', msg);
    NotificationService.error(msg instanceof Error ? msg.message : String(msg));
    isVoiceInputActive.value = false;
  },
  onSuccess: () => {
  }
});

const textBeforeRecording = ref('');

watch(isVoiceActive, (active) => {
  if (active) {
    textBeforeRecording.value = inputMessage.value;
  } else {
    if (isVoiceInputActive.value) {
      isVoiceInputActive.value = false;
    }
  }
});

watch(() => speechRecognitionState.value.lastRecognizedText + speechRecognitionState.value.pendingOnlineText, (asrText) => {
  if (isVoiceActive.value) {
    inputMessage.value = textBeforeRecording.value + asrText;
  }
});

onMounted(() => {
  if (inputStackWrapperRef.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        pendingReportHeight = entry.contentRect.height;
      }
      if (heightReportRaf) return;
      heightReportRaf = requestAnimationFrame(flushHeightReport);
    });
    resizeObserver.observe(inputStackWrapperRef.value);
  }
  
  // 仅在挂载时获取一次知识库列表
  fetchKnowledgeBases();
});

onUnmounted(() => {
  if (heightReportRaf) {
    cancelAnimationFrame(heightReportRaf);
    heightReportRaf = 0;
  }
  if (resizeObserver) {
    resizeObserver.disconnect();
    resizeObserver = null;
  }
  chatStore.setPendingInputImages([]);
});

const props = withDefaults(defineProps<Props & {
  activeArtifactId?: string;
}>(), {
  isSelectionMode: false,
  isAllSelected: false,
  hasSelection: false,
  selectedMessages: () => [],
  isWelcomeActive: false,
  activeArtifactId: '',
});

const inputMessage = ref('');
const showSendIcon = ref(true);
const isVoiceInputActive = ref(false);
const isSubmitting = ref(false);
const isClearingForSend = ref(false);
const isTransitioning = ref(false);
const pendingScreenshotCardId = ref<string | null>(null);
const pendingScreenshotMessageKey = ref<string | null>(null);
const isScreenshotCapturing = ref(false);
const SCREENSHOT_MESSAGE_TRANSITION_MS = 640;
const chatStore = useChatStore();
const knowledgeBaseStore = useKnowledgeBaseStore();
const isCompressingContext = computed(() => !!chatStore.isCompressingContext);
const compressionStatusText = computed(() => {
  if (!isCompressingContext.value) return '';
  return '正在压缩上下文，请稍候...';
});
const showInputToolbar = ref(false);
watch(
  () => [isCompressingContext.value, chatStore.contextCompressionInfo],
  ([isCompressing, compressionInfo]) => {
    if (isCompressing || compressionInfo) {
      showInputToolbar.value = true;
    }
  },
  { deep: true }
);
const KB_ENABLED_WORKSPACE_KEY = 'kb-enabled';
const KB_PERMISSION_FILTER_WORKSPACE_KEY = 'kb-permission-filter';
const KB_SELECTED_NAMES_WORKSPACE_KEY = 'kb-selected-names';
// 增强检索按钮可用性快照缓存：进入界面首帧按快照还原"是否有知识库"，
// 避免先显示"启用检索增强"、静默请求返回后才跳变为空态；
// 每次可用性检查确认后写回快照（见下方 watch）
const KB_AVAILABILITY_SNAPSHOT_KEY = 'mcp-kb-availability-snapshot';
type KnowledgeBaseAvailabilitySnapshot = { hasAny: boolean; checkedAt: number };
const readKnowledgeBaseAvailabilitySnapshot = (): KnowledgeBaseAvailabilitySnapshot | null => {
  const snapshot = StorageService.get<KnowledgeBaseAvailabilitySnapshot>(KB_AVAILABILITY_SNAPSHOT_KEY);
  if (!snapshot || typeof snapshot.hasAny !== 'boolean') return null;
  return snapshot;
};
const kbAvailabilitySnapshot = readKnowledgeBaseAvailabilitySnapshot();

const isKnowledgeBaseEnabled = useWorkspaceStorage<boolean>(KB_ENABLED_WORKSPACE_KEY, false);
const knowledgeBaseDropdownVisible = ref(false);
const isLoadingKbList = ref(false);
const isTogglingKnowledgeBase = ref(false);
const kbList = ref<KnowledgeBaseVM[]>([]);
const hasAnyKnowledgeBase = ref(kbAvailabilitySnapshot?.hasAny ?? false);
// 是否已完成过一次可用性检查；未完成（如首次加载中）时不判定为空，避免误显示虚线态；
// 有快照缓存时视为已检查，首帧直接按快照还原按钮状态
const kbAvailabilityChecked = ref(kbAvailabilitySnapshot !== null);
// 可用性确认变化后写回快照，供下次进入界面首帧还原
watch([hasAnyKnowledgeBase, kbAvailabilityChecked], ([hasAny, checked]) => {
  if (!checked) return;
  StorageService.set<KnowledgeBaseAvailabilitySnapshot>(KB_AVAILABILITY_SNAPSHOT_KEY, {
    hasAny,
    checkedAt: Date.now()
  });
});
const kbPermissionFilter = useWorkspaceStorage<KnowledgeBasePermissionCode>(KB_PERMISSION_FILTER_WORKSPACE_KEY, 'public');
const selectedKnowledgeBaseNames = useWorkspaceStorage<string[]>(KB_SELECTED_NAMES_WORKSPACE_KEY, []);
const hasSelectedKnowledgeBase = computed(() => selectedKnowledgeBaseNames.value.length > 0);
const shouldShowSelectedKnowledgeBaseState = computed(() => isKnowledgeBaseEnabled.value && (hasSelectedKnowledgeBase.value || knowledgeBaseDropdownVisible.value));
// 确认无知识库时进入虚线空态（首次加载中不判定为空）
const isKnowledgeBaseEmpty = computed(() => kbAvailabilityChecked.value && !hasAnyKnowledgeBase.value);
// 首次加载且无可用性快照：检查完成前按钮保持加载态，避免先渲染"启用检索增强"再跳变
const isKbAvailabilityChecking = computed(() => !kbAvailabilityChecked.value);
// 空态时按钮文案直接提示"暂无知识库"
const kbToggleIdleText = computed(() => {
  if (isTogglingKnowledgeBase.value) return '正在开启…';
  if (isKbAvailabilityChecking.value) return '正在加载…';
  if (isKnowledgeBaseEmpty.value) return '暂无知识库';
  return '启用检索增强';
});
const kbPermissionIndicatorStyle = computed(() => ({
  transform: `translateX(${kbPermissionFilter.value === 'private' ? '100%' : '0%'})`
}));
const knowledgeBaseEmptyText = computed(() => kbPermissionFilter.value === 'public' ? '暂无公开知识库' : '暂无个人知识库');
const shouldShowKnowledgeBaseLoading = computed(() => isLoadingKbList.value);

const displayKnowledgeBaseName = computed(() => {
  if (selectedKnowledgeBaseNames.value.length === 0) return '未选择知识库';
  if (selectedKnowledgeBaseNames.value.length === 1) return selectedKnowledgeBaseNames.value[0];
  return `已选择 ${selectedKnowledgeBaseNames.value.length} 个`;
});

const resolveKnowledgeBasePermission = (kb: KnowledgeBaseVM): KnowledgeBasePermissionCode => (
  kb.permissionCode === 'private' ? 'private' : 'public'
);
const getOppositeKnowledgeBasePermission = (permissionCode: KnowledgeBasePermissionCode): KnowledgeBasePermissionCode => (
  permissionCode === 'public' ? 'private' : 'public'
);

// 知识库列表缓存：通过一次无参请求拉取全部知识库后，供展示/校验/全选等场景复用，避免频繁请求
// 缓存位于模块级（见上方 <script> 块），欢迎态/底部态两个实例共享，
// 状态切换或新对话重建实例时不会丢失
const KB_LIST_CACHE_TTL = 30000;

const isKnowledgeBaseCacheFresh = () => getKbListCacheShared() !== null && Date.now() - getKbListCacheAt() < KB_LIST_CACHE_TTL;

const invalidateKnowledgeBaseCache = () => {
  invalidateKbListCacheShared();
};

const splitKnowledgeBasesByPermission = (list: KnowledgeBaseVM[]) => {
  const publicList: KnowledgeBaseVM[] = [];
  const privateList: KnowledgeBaseVM[] = [];
  for (const kb of list) {
    if (resolveKnowledgeBasePermission(kb) === 'private') {
      privateList.push(kb);
    } else {
      publicList.push(kb);
    }
  }
  return { publicList, privateList };
};

// 一次无参请求拉取全部可访问知识库并更新缓存
const refreshKnowledgeBaseCache = async () => {
  const allList = await listKnowledgeBases();
  const { publicList, privateList } = splitKnowledgeBasesByPermission(allList);
  const cache = { public: publicList, private: privateList };
  setKbListCacheShared(cache);
  return cache;
};

const ensureKnowledgeBaseCache = async () => {
  if (isKnowledgeBaseCacheFresh()) {
    return getKbListCacheShared()!;
  }
  return refreshKnowledgeBaseCache();
};

// 入场动画仅在页面首次加载时播放一次；
// 欢迎态/底部态切换或新对话重建实例时不再重播
const kbToggleEntranceActive = consumeKbToggleEntranceActive();

const clearKnowledgeBaseSelectionState = () => {
  isKnowledgeBaseEnabled.value = false;
  knowledgeBaseDropdownVisible.value = false;
  selectedKnowledgeBaseNames.value = [];
};

const disableKnowledgeBaseForAgentMode = () => {
  isKnowledgeBaseEnabled.value = false;
  knowledgeBaseDropdownVisible.value = false;
};

const refreshKnowledgeBaseAvailability = async (
  permissionCode: KnowledgeBasePermissionCode = kbPermissionFilter.value,
  currentList?: KnowledgeBaseVM[]
) => {
  if (Array.isArray(currentList) && currentList.length > 0) {
    hasAnyKnowledgeBase.value = true;
    kbAvailabilityChecked.value = true;
    return true;
  }

  const fallbackPermission = getOppositeKnowledgeBasePermission(permissionCode);
  const cache = await ensureKnowledgeBaseCache();
  const fallbackList = cache[fallbackPermission];
  hasAnyKnowledgeBase.value = fallbackList.length > 0;
  kbAvailabilityChecked.value = true;
  return hasAnyKnowledgeBase.value;
};

const syncSelectedKnowledgeBaseNames = async (
  permissionCode: KnowledgeBasePermissionCode = kbPermissionFilter.value,
  currentList: KnowledgeBaseVM[] = kbList.value
) => {
  if (selectedKnowledgeBaseNames.value.length === 0) {
    return;
  }

  const oppositePermission = getOppositeKnowledgeBasePermission(permissionCode);
  const cache = await ensureKnowledgeBaseCache();
  const oppositeList = cache[oppositePermission];
  const availableNames = new Set<string>([
    ...currentList.map((kb) => kb.name),
    ...oppositeList.map((kb) => kb.name)
  ]);
  const validSelectedNames = selectedKnowledgeBaseNames.value.filter((name) => availableNames.has(name));
  if (validSelectedNames.length !== selectedKnowledgeBaseNames.value.length) {
    selectedKnowledgeBaseNames.value = validSelectedNames;
    if (validSelectedNames.length === 0) {
      isKnowledgeBaseEnabled.value = false;
    }
  }
};

const fetchKnowledgeBases = async (permissionCode: KnowledgeBasePermissionCode = kbPermissionFilter.value) => {
  isLoadingKbList.value = true;
  try {
    const cache = await ensureKnowledgeBaseCache();
    const list = permissionCode === 'public' ? cache.public : cache.private;
    kbList.value = list;
    await syncSelectedKnowledgeBaseNames(permissionCode, list);
    const hasKnowledgeBase = await refreshKnowledgeBaseAvailability(permissionCode, list);

    if (!hasKnowledgeBase && list.length === 0) {
      clearKnowledgeBaseSelectionState();
      return;
    }

    // 如果启用了知识库但没有选中的，尝试选择第一个
    if (isKnowledgeBaseEnabled.value && selectedKnowledgeBaseNames.value.length === 0) {
      if (list.length > 0) {
        selectedKnowledgeBaseNames.value = [list[0].name];
      } else {
        isKnowledgeBaseEnabled.value = false;
      }
    }
  } catch (error) {
    console.error('Failed to fetch knowledge bases:', error);
    // 失败时也要结束首帧检测态，避免按钮一直停留在"正在检测…"
    kbAvailabilityChecked.value = true;
    NotificationService.error('获取知识库列表失败');
  } finally {
    isLoadingKbList.value = false;
  }
};

// 仅在新缓存存在时从共享缓存填充列表，不发起网络请求；
// 网络请求推迟到用户点击按钮/打开下拉时
const hydrateKnowledgeBasesFromCache = (permissionCode: KnowledgeBasePermissionCode = kbPermissionFilter.value) => {
  if (!isKnowledgeBaseCacheFresh()) {
    return false;
  }
  const cache = getKbListCacheShared()!;
  const list = permissionCode === 'public' ? cache.public : cache.private;
  kbList.value = list;
  return true;
};

const syncKnowledgeBaseState = async () => {
  if (!isKnowledgeBaseEnabled.value) {
    knowledgeBaseDropdownVisible.value = false;
    return;
  }

  // 页面载入时如果增强检索已开启，获取最新检索参数配置
  fetchAndCacheRetrievalConfig().catch(() => {});

  // 挂载/状态切换/新对话不主动请求知识库列表：
  // 启用状态与已选名称已持久化，直接沿用；有可用缓存时仅做本地校验
  if (!hydrateKnowledgeBasesFromCache()) {
    return;
  }

  const list = kbList.value;
  await syncSelectedKnowledgeBaseNames(kbPermissionFilter.value, list);
  const hasKnowledgeBase = await refreshKnowledgeBaseAvailability(kbPermissionFilter.value, list);

  if (!hasKnowledgeBase && list.length === 0) {
    clearKnowledgeBaseSelectionState();
    return;
  }

  if (selectedKnowledgeBaseNames.value.length === 0 && list.length > 0) {
    selectedKnowledgeBaseNames.value = [list[0].name];
  }
};

const handleKnowledgeBaseListUpdated = () => {
  invalidateKnowledgeBaseCache();
  void fetchKnowledgeBases();
};

onMounted(() => {
  eventBus.on('knowledge-base-list-updated', handleKnowledgeBaseListUpdated);
});

onActivated(() => {
  knowledgeBaseDropdownVisible.value = false;
  void syncKnowledgeBaseState();
});

onDeactivated(() => {
  knowledgeBaseDropdownVisible.value = false;
});

onUnmounted(() => {
  eventBus.off('knowledge-base-list-updated', handleKnowledgeBaseListUpdated);
});

const handleKnowledgeBaseClick = async () => {
  if (isTogglingKnowledgeBase.value) {
    return;
  }

  // 空态：切换到聊天界面的知识库工作区，并弹出创建知识库模态框
  if (isKnowledgeBaseEmpty.value) {
    knowledgeBaseStore.setKbNameToOpenUploadModal('__create_new_kb__');
    window.dispatchEvent(new CustomEvent('open-knowledge-workspace'));
    return;
  }

  if (isKnowledgeBaseEnabled.value) {
    isKnowledgeBaseEnabled.value = false;
    knowledgeBaseDropdownVisible.value = false;
    return;
  }

  // Turning on: fetch all knowledge bases in one request, select all by default
  isTogglingKnowledgeBase.value = true;
  isLoadingKbList.value = true;
  try {
    const cache = await refreshKnowledgeBaseCache();
    const publicList = cache.public;
    const privateList = cache.private;

    const allList = [...publicList, ...privateList];

    if (allList.length === 0) {
      clearKnowledgeBaseSelectionState();
      // 同步可用性状态并写回快照，避免按钮停留在可开启的假象状态
      hasAnyKnowledgeBase.value = false;
      kbAvailabilityChecked.value = true;
      NotificationService.warning('暂无知识库，请先创建知识库');
      isLoadingKbList.value = false;
      return;
    }

    // Show the current filter's list in the dropdown, or the one that has data
    const currentList = kbPermissionFilter.value === 'public' ? publicList : privateList;
    kbList.value = currentList.length > 0 ? currentList : (publicList.length > 0 ? publicList : privateList);

    hasAnyKnowledgeBase.value = true;
    isKnowledgeBaseEnabled.value = true;
    // Select all knowledge bases (both public and private) by default
    selectedKnowledgeBaseNames.value = allList.map((kb) => kb.name);
    // 开启增强检索时，获取最新检索参数配置
    fetchAndCacheRetrievalConfig().catch(() => {});
  } catch (error) {
    console.error('Failed to fetch knowledge bases:', error);
    NotificationService.error('获取知识库列表失败');
  } finally {
    isLoadingKbList.value = false;
    isTogglingKnowledgeBase.value = false;
  }
};

const handleKnowledgeBaseDropdownChange = (visible: boolean) => {
  if (visible) {
    // 列表近期已拉取过（如刚启用时），打开下拉不再重复请求
    if (isKnowledgeBaseCacheFresh()) {
      return;
    }
    fetchKnowledgeBases();
  } else {
    if (selectedKnowledgeBaseNames.value.length === 0) {
      isKnowledgeBaseEnabled.value = false;
    }
  }
};

const setKnowledgeBasePermissionFilter = async (permissionCode: KnowledgeBasePermissionCode) => {
  if (kbPermissionFilter.value === permissionCode) {
    return;
  }
  kbPermissionFilter.value = permissionCode;
  // 下拉刚打开时列表通常已是最新缓存，直接切换展示，无需再次请求
  const cache = await ensureKnowledgeBaseCache();
  kbList.value = permissionCode === 'public' ? cache.public : cache.private;
};

const deselectAllKnowledgeBases = () => {
  selectedKnowledgeBaseNames.value = [];
};

const selectAllKnowledgeBases = async () => {
  try {
    const cache = await ensureKnowledgeBaseCache();
    const allList = [...cache.public, ...cache.private];
    selectedKnowledgeBaseNames.value = allList.map(kb => kb.name);
    if (allList.length > 0) {
      isKnowledgeBaseEnabled.value = true;
    }
  } catch (error) {
    console.error('Failed to select all knowledge bases:', error);
    NotificationService.error('获取全部知识库列表失败');
  }
};

const selectKnowledgeBase = (kb: KnowledgeBaseVM) => {
  const index = selectedKnowledgeBaseNames.value.indexOf(kb.name);
  if (index > -1) {
    selectedKnowledgeBaseNames.value.splice(index, 1);
  } else {
    selectedKnowledgeBaseNames.value.push(kb.name);
    isKnowledgeBaseEnabled.value = true;
  }
};

watch(isKnowledgeBaseEnabled, (newValue) => {
  if (newValue) {
    if (kbList.value.length === 0) {
      fetchKnowledgeBases();
    } else if (selectedKnowledgeBaseNames.value.length === 0) {
      selectedKnowledgeBaseNames.value = [kbList.value[0].name];
    }
  } else {
    knowledgeBaseDropdownVisible.value = false;
  }
});

const selectedFiles = ref<Array<{
  id: string;
  name: string; 
  size: number; 
  content: ArrayBuffer; 
  uploadStatus: 'idle' | 'uploading' | 'parsing' | 'success' | 'error';
  uploadProgress: number;
  parseResult?: UploadResponse;
  isFileImage?: boolean;
  isCapturePending?: boolean;
  imagePreviewUrl?: string;
  imageWidth?: number;
  imageHeight?: number;
  imageTokenEstimate?: number;
  file?: File;
  turnId?: string;
}>>([]);

const uploadConfirmVisible = ref(false);
const isConfirmUploading = ref(false);
const pendingDocumentFiles = ref<File[]>([]);
// 普通对话混合上传时，图片需等文档确认弹窗关闭后再弹密级窗，此处暂存待处理图片
const pendingImageFilesAfterConfirm = ref<File[]>([]);
const pendingProcessType = ref<FileProcessType>('langchain');
const pendingClassification = ref<'public' | 'internal' | undefined>(undefined);
const uploadConfirmSource = ref<'picker' | 'drop'>('picker');

// 通用「选择文件密级」弹窗：DeepAgent 与普通对话上传图片/文档时共用
const classificationModalVisible = ref(false);
const classificationUploading = ref(false);
const classificationPendingFiles = ref<File[]>([]);
const classificationModalValue = ref<'public' | 'internal' | undefined>(undefined);
const classificationPendingTotalSize = computed(() => {
  return classificationPendingFiles.value.reduce((total, file) => total + file.size, 0);
});
// upload：选文件后继续走上传流程；screenshot：截图发送前确认，取消即中止发送
const classificationModalMode = ref<'upload' | 'screenshot'>('upload');
const classificationModalResolver = ref<((value: 'public' | 'internal' | undefined) => void) | null>(null);
const classificationModalSubmitText = computed(() => {
  return classificationModalMode.value === 'screenshot' ? '发送' : '上传';
});
const pendingDocumentTotalSize = computed(() => {
  return pendingDocumentFiles.value.reduce((total, file) => total + file.size, 0);
});
const uploadConfirmWrapClass = computed(() => {
  return uploadConfirmSource.value === 'drop'
    ? 'upload-process-modal-wrap upload-process-modal-wrap--drop'
    : 'upload-process-modal-wrap';
});

const selectedImageFiles = computed(() => selectedFiles.value.filter(file => file.isFileImage));
const selectedDocumentFiles = computed(() => selectedFiles.value.filter(file => !file.isFileImage));
const isImageUploading = (file: { uploadStatus?: string }) => file.uploadStatus === 'uploading' || file.uploadStatus === 'parsing';
// 保持 image-strip-container 可见直到 sending 动画完全结束，避免 v-show 掐断 transition-group 的 leave 动画
const showImageStrip = computed(() => selectedImageFiles.value.length > 0 || isClearingForSend.value);
const inputImages = computed<ConversationImageItem[]>(() => {
  return selectedImageFiles.value
    .filter(file => !!file.imagePreviewUrl)
    .map(file => {
      const url = String(file.imagePreviewUrl || '').trim();
      return {
        key: file.id,
        url,
        alt: file.name || '图片',
        name: file.name || '图片',
        source: 'input' as const,
        messageIndex: -1,
        messageId: 'chat-input',
        role: 'user' as const
      };
    })
    .filter(image => !!image.url);
});
const inputViewerImages = computed(() => {
  return mergeViewerImages(
    extractImagesFromMessages(chatStore.messages || []),
    inputImages.value
  );
});
const showImageViewer = ref(false);
const previewImageUrl = ref('');
const previewImageTitle = ref('');

watch(inputImages, (images) => {
  chatStore.setPendingInputImages(images);
}, { immediate: true });

const removeSelectedFileById = (fileId: string) => {
  const fileIndex = selectedFiles.value.findIndex(file => file.id === fileId);
  if (fileIndex === -1) return;

  const fileToRemove = selectedFiles.value[fileIndex];
  if (fileToRemove?.isCapturePending && pendingScreenshotCardId.value === fileId) {
    pendingScreenshotCardId.value = null;
  }
  if (fileToRemove?.isFileImage && fileToRemove.imagePreviewUrl) {
    URL.revokeObjectURL(fileToRemove.imagePreviewUrl);
  }

  selectedFiles.value.splice(fileIndex, 1);
};

const hasDeepAgentConversationMessages = () => {
  const messages = chatStore.messages || [];
  return messages.some(message => message.role === 'user' || message.role === 'assistant' || message.role === 'tool');
};

const hasDeepAgentSandboxActivity = () => {
  return selectedFiles.value.length > 0 || hasDeepAgentConversationMessages();
};

/**
 * 释放 DeepAgent 沙箱：请求由 store 后台静默发出，函数同步返回，
 * 不阻塞调用方（退出智能体 / 新建对话 / 删除文件后可立即继续操作），也不弹错误提示。
 */
const releaseDeepAgentSandbox = (options: { resetSessionThreadId?: boolean; force?: boolean } = {}) => {
  const { resetSessionThreadId = false, force = false } = options;

  if (activeAgentType.value !== 'deepagent' || !chatStore.sessionThreadId) {
    return;
  }

  // 正在执行任务时不释放沙箱，让任务继续后台执行
  if (chatStore.isProcessing) {
    return;
  }

  if (!force && !hasDeepAgentSandboxActivity()) {
    return;
  }

  const currentSessionThreadId = chatStore.sessionThreadId;
  chatStore.releaseSandboxContainer(currentSessionThreadId);

  // 释放请求已带上原会话 ID，可立即换新 ID，无需等待后端返回
  if (resetSessionThreadId && chatStore.sessionThreadId === currentSessionThreadId) {
    chatStore.regenerateSessionThreadId();
  }
};

// 文件列表滚动逻辑
const fileListRef = ref<any>(null);
const showFileLeftMask = ref(false);
const showFileRightMask = ref(false);
const imageStripListRef = ref<any>(null);
const showImageLeftMask = ref(false);
const showImageRightMask = ref(false);

const getFileListEl = () => {
  const val = fileListRef.value;
  return (val && '$el' in val ? val.$el : val) as HTMLElement | null;
};

const getImageStripListEl = () => {
  const val = imageStripListRef.value;
  return (val && '$el' in val ? val.$el : val) as HTMLElement | null;
};

const checkFileScroll = () => {
  const el = getFileListEl();
  if (!el || !el.scrollWidth) return;
  const { scrollLeft, scrollWidth, clientWidth } = el;
  showFileLeftMask.value = scrollLeft > 0;
  showFileRightMask.value = scrollLeft + clientWidth < scrollWidth - 1;
};

const handleFileScroll = () => {
  checkFileScroll();
};

const checkImageStripScroll = () => {
  const el = getImageStripListEl();
  if (!el || !el.scrollWidth) {
    showImageLeftMask.value = false;
    showImageRightMask.value = false;
    return;
  }

  const { scrollLeft, scrollWidth, clientWidth } = el;
  showImageLeftMask.value = scrollLeft > 2;
  showImageRightMask.value = scrollLeft + clientWidth < scrollWidth - 2;
};

const handleImageStripScroll = () => {
  checkImageStripScroll();
};

const handleFileWheel = (e: WheelEvent) => {
  e.preventDefault();
  const el = getFileListEl();
  if (el) {
    el.scrollLeft += e.deltaY;
  }
};

const handleImageStripWheel = (e: WheelEvent) => {
  const el = getImageStripListEl();
  if (!el) return;

  const primaryDelta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
  if (!primaryDelta) return;

  e.preventDefault();
  el.scrollLeft += primaryDelta;
  checkImageStripScroll();
};

watch(() => {
  const val = fileListRef.value;
  return (val && '$el' in val ? val.$el : val) as HTMLElement | null;
}, (newEl, oldEl) => {
  if (oldEl) {
    oldEl.removeEventListener('wheel', handleFileWheel);
  }
  if (newEl) {
    newEl.addEventListener('wheel', handleFileWheel, { passive: false });
  }
});

watch(() => {
  const val = imageStripListRef.value;
  return (val && '$el' in val ? val.$el : val) as HTMLElement | null;
}, (newEl, oldEl) => {
  if (oldEl) {
    oldEl.removeEventListener('wheel', handleImageStripWheel);
  }
  if (newEl) {
    newEl.addEventListener('wheel', handleImageStripWheel, { passive: false });
    nextTick(checkImageStripScroll);
  }
});

onUnmounted(() => {
  const el = getFileListEl();
  if (el) {
    el.removeEventListener('wheel', handleFileWheel);
  }
  const imageEl = getImageStripListEl();
  if (imageEl) {
    imageEl.removeEventListener('wheel', handleImageStripWheel);
  }
});

const scrollFileLeft = () => {
  const el = getFileListEl();
  if (el) {
    el.scrollBy({ left: -200, behavior: 'smooth' });
  }
};

const scrollFileRight = () => {
  const el = getFileListEl();
  if (el) {
    el.scrollBy({ left: 200, behavior: 'smooth' });
  }
};

const scrollImageStripLeft = () => {
  const el = getImageStripListEl();
  if (el) {
    el.scrollBy({ left: -Math.max(el.clientWidth * 0.72, 160), behavior: 'smooth' });
  }
};

const scrollImageStripRight = () => {
  const el = getImageStripListEl();
  if (el) {
    el.scrollBy({ left: Math.max(el.clientWidth * 0.72, 160), behavior: 'smooth' });
  }
};

watch(() => selectedFiles.value, () => {
  nextTick(() => {
    checkFileScroll();
    checkImageStripScroll();
  });
}, { deep: true });

watch(selectedImageFiles, () => {
  nextTick(() => {
    const shell = document.querySelector('.image-strip-shell') as HTMLElement | null;
    if (shell) {
      shell.style.maxHeight = shell.classList.contains('has-images') ? '120px' : '0px';
    }
    checkImageStripScroll();
  });
});

watch(fileListRef, (el) => {
  if (el) {
    checkFileScroll();
  }
});

watch(imageStripListRef, (el) => {
  if (el) {
    checkImageStripScroll();
  }
});

const toggleInputToolbar = () => {
  window.dispatchEvent(new CustomEvent('toggle-input-toolbar'));
};

const wordUploadInputRef = ref<HTMLInputElement | null>(null);
const imageUploadInputRef = ref<HTMLInputElement | null>(null);

const triggerWordUpload = () => {
  wordUploadInputRef.value?.click();
};

const triggerImageUpload = () => {
  imageUploadInputRef.value?.click();
};

const scheduleBackgroundTask = (task: () => void) => {
  const requestIdle = (globalThis as any)?.requestIdleCallback;
  if (typeof requestIdle === 'function') {
    requestIdle(() => task(), { timeout: 500 });
    return;
  }
  setTimeout(task, 0);
};

const collectImageMetadata = (fileId: string, file: File, previewUrl: string) => {
  scheduleBackgroundTask(() => {
    const image = new Image();
    image.onload = () => {
      const fileItem = selectedFiles.value.find(item => item.id === fileId);
      if (!fileItem) return;

      const width = image.naturalWidth || 0;
      const height = image.naturalHeight || 0;
      fileItem.imageWidth = width;
      fileItem.imageHeight = height;
      fileItem.imageTokenEstimate = estimateImageTokensFromMetadata({
        size: file.size,
        width,
        height
      });
    };
    image.onerror = () => {
      const fileItem = selectedFiles.value.find(item => item.id === fileId);
      if (!fileItem) return;

      fileItem.imageTokenEstimate = estimateImageTokensFromMetadata({
        size: file.size
      });
    };
    image.src = previewUrl;
  });
};

// DeepAgent 模式下图片只上传到沙箱，前端不做内容解析，仅回写 parseResult 供发送时提取沙箱文件名
const uploadDeepAgentImageFile = async (file: File, fileId: string, classification?: 'public' | 'internal') => {
  try {
    const sourceFile = selectedFiles.value.find(f => f.id === fileId);
    const response = await FileUploadService.uploadDeepAgentFile(file, chatStore.sessionThreadId, (progress) => {
      const currentFile = selectedFiles.value.find(f => f.id === fileId);
      if (currentFile) {
        currentFile.uploadProgress = progress;
      }
    }, classification, sourceFile?.turnId);

    const uploadedFile = selectedFiles.value.find(f => f.id === fileId);
    if (uploadedFile) {
      uploadedFile.uploadStatus = 'success';
      uploadedFile.parseResult = response;
    }
  } catch (error) {
    console.error('DeepAgent image upload failed:', error);
    removeSelectedFileById(fileId);
    NotificationService.error(`图片 ${file.name} 上传失败`);
  }
};

const processImageFiles = (files: File[], fileClassification?: 'public' | 'internal') => {
  const isDeepAgent = activeAgentType.value === 'deepagent';

  // 普通对话的图片由视觉模型直接解析，先做模型能力校验，避免用户选完密级才被告知不支持
  if (!isDeepAgent && !hasVisionModel.value) {
    files.forEach((file) => {
      NotificationService.warning(`文件 ${file.name} 格式不支持，请使用支持图片问答的模型后再上传图片`);
    });
    return;
  }

  // DeepAgent 与普通对话均需先确认文件密级；DeepAgent 的密级会随文件一起提交到沙箱
  if (!fileClassification) {
    openFileClassificationModal(files);
    return;
  }

  files.forEach((file) => {
    if (!isImageFile(file)) {
      NotificationService.warning(`${file.name} 不是有效的图片文件`);
      return;
    }

    const maxSize = 10;
    const isLtLimit = file.size < maxSize * 1024 * 1024;
    if (!isLtLimit) {
      NotificationService.info(`图片 ${file.name} 大小超过 ${maxSize}MB`);
      return;
    }

    const isDuplicate = selectedFiles.value.some(f => f.name === file.name && f.size === file.size);
    if (isDuplicate) {
      NotificationService.warning(`图片 ${file.name} 已存在`);
      return;
    }

    const fileId = uuidv4();
    const imagePreviewUrl = URL.createObjectURL(file);

    const fileItem = {
      id: fileId,
      name: file.name,
      size: file.size,
      content: new ArrayBuffer(0),
      uploadStatus: (isDeepAgent ? 'uploading' : 'success') as 'uploading' | 'success',
      uploadProgress: isDeepAgent ? 0 : 100,
      isFileImage: true,
      imagePreviewUrl,
      imageTokenEstimate: estimateImageTokensFromMetadata({ size: file.size }),
      file,
      ...(isDeepAgent ? { turnId: getOrCreateUploadTurnId() } : {})
    };

    selectedFiles.value.push(fileItem);
    collectImageMetadata(fileId, file, imagePreviewUrl);

    if (isDeepAgent) {
      void uploadDeepAgentImageFile(file, fileId, fileClassification);
    }
  });
};

const openDocumentUploadConfirm = (files: File[], source: 'picker' | 'drop' = 'picker') => {
  if (files.length === 0) return;
  pendingDocumentFiles.value = files;
  pendingClassification.value = undefined;
  uploadConfirmSource.value = source;
  uploadConfirmVisible.value = true;
};

const cancelPendingDocumentUpload = () => {
  if (isConfirmUploading.value) return;
  uploadConfirmVisible.value = false;
  pendingDocumentFiles.value = [];
  pendingClassification.value = undefined;
  pendingImageFilesAfterConfirm.value = [];
};

// 普通对话：文档走「解析方式」弹窗、图片走「文件密级」弹窗，混合上传时串行打开避免弹窗叠加
const startNormalUpload = (files: File[], source: 'picker' | 'drop') => {
  const imageFiles = files.filter(file => isImageFile(file));
  const documentFiles = files.filter(file => !isImageFile(file));

  if (documentFiles.length > 0) {
    pendingImageFilesAfterConfirm.value = imageFiles;
    openDocumentUploadConfirm(documentFiles, source);
    return;
  }

  if (imageFiles.length > 0) {
    processImageFiles(imageFiles);
  }
};

// 文档确认弹窗关闭后，再为暂存的图片弹出密级确认
const flushPendingImageFiles = async () => {
  const imageFiles = pendingImageFilesAfterConfirm.value;
  pendingImageFilesAfterConfirm.value = [];
  if (imageFiles.length === 0) return;
  await nextTick();
  processImageFiles(imageFiles);
};

const openFileClassificationModal = (files: File[]) => {
  if (files.length === 0) return;
  classificationModalMode.value = 'upload';
  classificationPendingFiles.value = files;
  classificationModalValue.value = undefined;
  classificationModalVisible.value = true;
};

// 截图场景：等待用户确认密级，取消或关闭弹窗时返回 undefined
const requestScreenshotClassification = (file: File): Promise<'public' | 'internal' | undefined> => {
  classificationModalMode.value = 'screenshot';
  classificationPendingFiles.value = [file];
  classificationModalValue.value = undefined;
  classificationModalVisible.value = true;
  return new Promise((resolve) => {
    classificationModalResolver.value = resolve;
  });
};

const resolveClassificationModal = (value: 'public' | 'internal' | undefined) => {
  const resolver = classificationModalResolver.value;
  classificationModalResolver.value = null;
  if (!resolver) return;
  resolver(value);
};

const cancelFileClassificationModal = () => {
  if (classificationUploading.value) return;
  classificationModalVisible.value = false;
  classificationPendingFiles.value = [];
  resolveClassificationModal(undefined);
};

const confirmFileClassificationModal = async () => {
  if (classificationPendingFiles.value.length === 0) {
    classificationModalVisible.value = false;
    resolveClassificationModal(undefined);
    return;
  }

  if (!classificationModalValue.value) {
    NotificationService.warning('请选择文件密级');
    return;
  }

  const filesToUpload = [...classificationPendingFiles.value];
  const classification = classificationModalValue.value;

  // 截图：密级由 handleScreenshot 拿到后继续上传/发送
  if (classificationModalMode.value === 'screenshot') {
    classificationPendingFiles.value = [];
    classificationModalVisible.value = false;
    resolveClassificationModal(classification);
    return;
  }

  classificationUploading.value = true;

  try {
    classificationModalVisible.value = false;
    if (activeAgentType.value === 'deepagent') {
      // DeepAgent：密级随文件一起提交到沙箱，文档与图片由 processFiles 内部分流
      processFiles(filesToUpload, undefined, classification);
    } else {
      // 普通对话：图片仅在本地读取，密级作为上传前的合规确认
      processImageFiles(filesToUpload, classification);
    }
    classificationPendingFiles.value = [];
  } finally {
    classificationUploading.value = false;
  }
};

const handlePaste = (e: ClipboardEvent) => {
  const clipboardData = e.clipboardData;
  if (!clipboardData) return;

  const imageFiles: File[] = [];
  const items = clipboardData.items;
  for (let i = 0; i < (items?.length || 0); i++) {
    const item = items[i];
    if (item.kind === 'file' && item.type.startsWith('image/')) {
      const file = item.getAsFile();
      if (file) imageFiles.push(file);
    }
  }
  if (imageFiles.length === 0) {
    Array.from(clipboardData.files || []).forEach(file => {
      if (file.type.startsWith('image/')) imageFiles.push(file);
    });
  }

  // 没有图片时不拦截，保持默认的文本粘贴行为
  if (imageFiles.length === 0) return;

  e.preventDefault();
  e.stopPropagation();

  if (activeAgentType.value === 'orchestrator') return;

  processImageFiles(imageFiles);
};

const isDragging = ref(false);
const isProcessingDrop = ref(false);
const draggedItems = ref<Array<{ id: string; type: 'pdf' | 'word' | 'txt' | 'md' | 'csv' | 'ppt' | 'zip' | 'image' | 'unknown' }>>([]);

const draggedFileType = computed(() => {
  if (draggedItems.value.length === 0) return 'unknown';
  // 如果所有文件类型相同，则使用该类型的主题色
  const firstType = draggedItems.value[0].type;
  if (firstType !== 'unknown' && draggedItems.value.every(i => i.type === firstType)) {
    return firstType;
  }
  // 混合类型使用默认（紫色）主题
  return 'unknown';
});

const getDragItemTypeFromMime = (mime: string, name = ''): 'pdf' | 'word' | 'txt' | 'md' | 'csv' | 'ppt' | 'zip' | 'image' | 'unknown' => {
  const lowerName = name.toLowerCase();
  const lowerMime = mime.toLowerCase();

  if (lowerMime.startsWith('image/')) return 'image';
  if (lowerMime === 'application/pdf' || lowerName.endsWith('.pdf')) return 'pdf';
  if (lowerMime.includes('word') || lowerMime.includes('officedocument') || lowerName.endsWith('.doc') || lowerName.endsWith('.docx')) return 'word';
  if (lowerName.endsWith('.txt')) return 'txt';
  if (lowerName.endsWith('.md')) return 'md';
  if (lowerName.endsWith('.ppt') || lowerName.endsWith('.pptx') || lowerMime.includes('powerpoint') || lowerMime.includes('presentationml')) return 'ppt';
  if (
    lowerName.endsWith('.csv') ||
    lowerName.endsWith('.xls') ||
    lowerName.endsWith('.xlsx') ||
    lowerMime.includes('excel') ||
    lowerMime.includes('spreadsheetml')
  ) return 'csv';
  if (activeAgentType.value === 'deepagent' && (lowerName.endsWith('.zip') || lowerMime === 'application/zip' || lowerMime === 'application/x-zip-compressed')) return 'zip';
  return 'unknown';
};

const detectDragItems = (e: DragEvent) => {
  const items: Array<{ id: string; type: 'pdf' | 'word' | 'txt' | 'md' | 'csv' | 'ppt' | 'zip' | 'image' | 'unknown' }> = [];
  
  if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
    // 限制最多显示3个，形成扑克牌效果
    const count = Math.min(e.dataTransfer.items.length, 3);
    for (let i = 0; i < count; i++) {
      const item = e.dataTransfer.items[i];
      let type: 'pdf' | 'word' | 'txt' | 'md' | 'csv' | 'ppt' | 'zip' | 'image' | 'unknown' = 'unknown';
      
      if (item.kind === 'file') {
        type = getDragItemTypeFromMime(item.type, item.getAsFile()?.name || '');
      }
      items.push({ id: uuidv4(), type });
    }
  } else {
    // 降级处理：如果没有 items 信息，默认显示一个未知文件
    items.push({ id: uuidv4(), type: 'unknown' });
  }
  return items;
};

const getDragItemsFromFiles = (files: FileList) => {
  const items: Array<{ id: string; type: 'pdf' | 'word' | 'txt' | 'md' | 'csv' | 'ppt' | 'zip' | 'image' | 'unknown' }> = [];
  const count = Math.min(files.length, 3);
  
  for (let i = 0; i < count; i++) {
    const file = files[i];
    items.push({ id: uuidv4(), type: getFileTypeFromFile(file) });
  }
  return items;
};

const getFileTypeFromFile = (file: File): 'pdf' | 'word' | 'txt' | 'md' | 'csv' | 'ppt' | 'zip' | 'image' | 'unknown' => {
  if (file.type.startsWith('image/')) return 'image';
  const name = file.name.toLowerCase();
  if (name.endsWith('.pdf')) return 'pdf';
  if (name.endsWith('.docx') || name.endsWith('.doc')) return 'word';
  if (name.endsWith('.txt')) return 'txt';
  if (name.endsWith('.md')) return 'md';
  if (name.endsWith('.ppt') || name.endsWith('.pptx')) return 'ppt';
  if (name.endsWith('.csv') || name.endsWith('.xls') || name.endsWith('.xlsx')) return 'csv';
  if (activeAgentType.value === 'deepagent' && name.endsWith('.zip')) return 'zip';
  return 'unknown';
};

// 当前轮次的 turn_id：上传文档时即生成（同一次发送前上传的所有文档共用），
// 发送时直接复用，保证「上传接口 / 消息历史 / 请求 payload」用的是同一个 id；发送后重置
let pendingUploadTurnId = '';
const getOrCreateUploadTurnId = () => {
  if (!pendingUploadTurnId) {
    pendingUploadTurnId = uuidv4();
  }
  return pendingUploadTurnId;
};

// DWG/DXF 属于 CAD 图纸，仅需上传到沙箱供 CAD 智能体使用，前端不做内容解析：
// 既不读取文件内容（避免大体积二进制占用内存），也不进入「解析中」状态
const isCadFile = (name: string) => name.endsWith('.dwg') || name.endsWith('.dxf');

// 统一上传入口不限制格式，图片文件据此分流到图片处理流程
const isImageFile = (file: File) => file.type.startsWith('image/') || isImageFileName(file.name);

const uploadCadFileOnly = async (file: File, fileId: string, fileClassification?: 'public' | 'internal') => {
  try {
    const sourceFile = selectedFiles.value.find(f => f.id === fileId);
    const response = await FileUploadService.uploadDeepAgentFile(file, chatStore.sessionThreadId, (progress) => {
      const currentFile = selectedFiles.value.find(f => f.id === fileId);
      if (currentFile) {
        currentFile.uploadProgress = progress;
      }
    }, fileClassification, sourceFile?.turnId);

    const uploadedFile = selectedFiles.value.find(f => f.id === fileId);
    if (uploadedFile) {
      uploadedFile.uploadStatus = 'success';
      uploadedFile.parseResult = response;
    }
  } catch (error) {
    console.error('CAD file upload failed:', error);
    removeSelectedFileById(fileId);
    NotificationService.error(`文件 ${file.name} 上传失败`);
  }
};

const processFiles = (files: File[], processType?: FileProcessType, fileClassification?: 'public' | 'internal') => {
  for (const file of files) {
    // 拖拽等入口混入的图片交给图片流程处理，文档流程不接收图片
    if (isImageFile(file)) {
      processImageFiles([file], fileClassification);
      continue;
    }

    const name = (file.name || '').toLowerCase();

    // 普通对话仅支持常见文档类型；DeepAgent 支持全部文件格式（不做格式限制）
    if (activeAgentType.value !== 'deepagent') {
      const allowedExts = ['.docx', '.doc', '.pdf', '.txt', '.md', '.csv', '.xls', '.xlsx', '.ppt', '.pptx'];
      if (!allowedExts.some(ext => name.endsWith(ext))) {
        NotificationService.warning(`文件 ${file.name} 格式不支持，仅支持 Word、PDF、TXT、Markdown、CSV、Excel、PPT 文件`);
        continue;
      }
    }

    const maxSize = getFileUploadMaxSize();
    const isLtLimit = file.size / 1024 / 1024 < maxSize;
    if (!isLtLimit) {
      NotificationService.info(`文件 ${file.name} 大小超过 ${maxSize}MB`);
      continue;
    }

    const isDuplicate = selectedFiles.value.some(f => f.name === file.name && f.size === file.size);
    if (isDuplicate) {
      NotificationService.warning(`文件 ${file.name} 已存在`);
      continue;
    }

    const fileId = uuidv4();
    const fileItem: any = {
      id: fileId,
      name: file.name,
      size: file.size,
      content: new ArrayBuffer(0),
      uploadStatus: 'uploading',
      uploadProgress: 0,
      turnId: getOrCreateUploadTurnId()
    };

    selectedFiles.value.push(fileItem);

    // CAD 图纸只上传到沙箱，不走 FileReader 读取与解析流程（仅 DeepAgent 有沙箱）
    if (activeAgentType.value === 'deepagent' && isCadFile(name)) {
      void uploadCadFileOnly(file, fileId, fileClassification);
      continue;
    }

    const reader = new FileReader();
    reader.onload = async () => {
      const result = reader.result;
      const targetFile = selectedFiles.value.find(f => f.id === fileId);
      
      if (!targetFile) return;

      if (!(result instanceof ArrayBuffer)) {
        NotificationService.error(`文件 ${file.name} 读取失败`);
        removeSelectedFileById(fileId);
        return;
      }

      targetFile.content = result;

      try {
        if (activeAgentType.value === 'deepagent') {
            const response = await FileUploadService.uploadDeepAgentFile(file, chatStore.sessionThreadId, (progress) => {
                const currentFile = selectedFiles.value.find(f => f.id === fileId);
                if (currentFile) {
                    currentFile.uploadProgress = progress;
                    if (progress === 100) {
                        currentFile.uploadStatus = 'parsing';
                    }
                }
            }, fileClassification, targetFile.turnId);
            const currentFile = selectedFiles.value.find(f => f.id === fileId);
            if (currentFile) {
                currentFile.uploadStatus = 'success';
                currentFile.parseResult = response;
            }
        } else {
            const conversationId = uuidv4();
            
            const response = await FileUploadService.uploadFile(file, conversationId, processType ?? pendingProcessType.value, (progress) => {
                const currentFile = selectedFiles.value.find(f => f.id === fileId);
                if (currentFile) {
                    currentFile.uploadProgress = progress;
                    if (progress === 100) {
                        currentFile.uploadStatus = 'parsing';
                    }
                }
            }, chatStore.sessionThreadId, fileItem.turnId);

            const currentFile = selectedFiles.value.find(f => f.id === fileId);
            if (currentFile) {
                currentFile.uploadStatus = 'success';
                currentFile.parseResult = response;
            }
        }
      } catch (error) {
        console.error('File upload failed:', error);
        removeSelectedFileById(fileId);
        NotificationService.error(`文件 ${file.name} 上传/解析失败`);
      }
    };
    
    reader.onerror = () => {
      NotificationService.error(`文件 ${file.name} 读取失败`);
      removeSelectedFileById(fileId);
    };
    reader.readAsArrayBuffer(file);
  }
};

const confirmDocumentUpload = async () => {
  if (pendingDocumentFiles.value.length === 0) {
    uploadConfirmVisible.value = false;
    return;
  }

  if (!pendingClassification.value) {
    NotificationService.warning('请选择文件密级');
    return;
  }

  const filesToUpload = [...pendingDocumentFiles.value];
  const selectedProcessType = pendingProcessType.value;

  isConfirmUploading.value = true;

  try {
    uploadConfirmVisible.value = false;
    processFiles(filesToUpload, selectedProcessType);
    pendingDocumentFiles.value = [];
    await flushPendingImageFiles();
  } finally {
    isConfirmUploading.value = false;
  }
};

const handleWordUploadChange = (e: Event) => {
  const input = e.target as HTMLInputElement | null;
  const files = input?.files;
  if (!files || files.length === 0) return;

  // 不限制文件格式，图片由后续 startNormalUpload / processFiles 分流到图片处理流程
  const fileList = Array.from(files);

  if (activeAgentType.value === 'deepagent') {
    // DeepAgent 下文件需先确认密级，确认后上传到沙箱
    openFileClassificationModal(fileList);
  } else {
    startNormalUpload(fileList, 'picker');
  }

  if (input) input.value = '';
};

// 普通对话专用图片上传入口：仅选择图片，走统一的密级确认与图片处理流程
const handleImageUploadChange = (e: Event) => {
  const input = e.target as HTMLInputElement | null;
  const files = input?.files;
  if (!files || files.length === 0) return;

  processImageFiles(Array.from(files));

  if (input) input.value = '';
};

const dragCounter = ref(0);

const resetDragState = () => {
  dragCounter.value = 0;
  if (!isProcessingDrop.value) {
    isDragging.value = false;
    draggedItems.value = [];
  }
};

const getDragTypes = (e: DragEvent) => {
  const types = e.dataTransfer?.types;
  if (!types) return [] as string[];
  return Array.from(types as any);
};

const hasDragType = (e: DragEvent, type: string) => {
  const types = e.dataTransfer?.types;
  if (!types) return false;
  if (typeof (types as any).contains === 'function') {
    return (types as any).contains(type);
  }
  return getDragTypes(e).includes(type);
};

const hasDraggedFiles = (e: DragEvent) => {
  const dt = e.dataTransfer;
  if (!dt) return false;
  if (dt.items && dt.items.length > 0) {
    return Array.from(dt.items).some((item) => item.kind === 'file');
  }
  return !!dt.files && dt.files.length > 0;
};

const shouldIgnoreGlobalDragEvent = (e: DragEvent) => {
  const target = e.target;
  if (!(target instanceof Element)) return false;
  return !!target.closest('.ant-modal-root, .ant-modal-wrap, .ant-modal, .upload-modal');
};

const handleDragEnter = (e: DragEvent) => {
  e.preventDefault();
  if (activeAgentType.value === 'orchestrator') return;
  if (shouldIgnoreGlobalDragEvent(e)) {
    resetDragState();
    return;
  }
  dragCounter.value++;
  
  const hasFiles = hasDraggedFiles(e);
  const isWebContent = hasDragType(e, 'text/html');

  if (hasFiles && !isWebContent && !isProcessingDrop.value) {
    isDragging.value = true;
    if (draggedItems.value.length === 0) {
      draggedItems.value = detectDragItems(e);
    }
  }
};

const handleDragOver = (e: DragEvent) => {
  e.preventDefault();
  if (shouldIgnoreGlobalDragEvent(e)) {
    resetDragState();
  }
};

const handleDragLeave = (e: DragEvent) => {
  e.preventDefault();
  if (shouldIgnoreGlobalDragEvent(e)) {
    resetDragState();
    return;
  }
  dragCounter.value--;
  
  if (dragCounter.value <= 0) {
    dragCounter.value = 0;
    if (!isProcessingDrop.value) {
      isDragging.value = false;
      draggedItems.value = [];
    }
  }
};

const handleDrop = (e: DragEvent) => {
  e.preventDefault();
  e.stopPropagation();
  if (activeAgentType.value === 'orchestrator') return;
  if (shouldIgnoreGlobalDragEvent(e)) {
    resetDragState();
    return;
  }
  dragCounter.value = 0;
  
  if (hasDragType(e, 'text/html')) {
    isDragging.value = false;
    draggedItems.value = [];
    return;
  }

  const files = e.dataTransfer?.files;
  
  if (files && files.length > 0) {
    isDragging.value = false;
    isProcessingDrop.value = true;
    
    draggedItems.value = getDragItemsFromFiles(files);
    
    requestAnimationFrame(() => {
      const droppedFiles = Array.from(files);

      if (activeAgentType.value === 'deepagent') {
        // DeepAgent 下图片与文档共用同一个密级确认弹窗，确认后由 processFiles 内部分流
        openFileClassificationModal(droppedFiles);
      } else {
        startNormalUpload(droppedFiles, 'drop');
      }
      setTimeout(() => {
        isProcessingDrop.value = false;
        draggedItems.value = [];
      }, 300);
    });
  } else {
    isDragging.value = false;
    draggedItems.value = [];
  }
};

const openImageViewer = (file: { imagePreviewUrl?: string; name: string }) => {
  if (!file.imagePreviewUrl) return;
  previewImageUrl.value = file.imagePreviewUrl;
  previewImageTitle.value = file.name;
  showImageViewer.value = true;
};

const removeFile = async (index: number) => {
  const fileToRemove = selectedFiles.value[index];
  
  // 清理图片的 Object URL
  if (fileToRemove?.isFileImage && fileToRemove?.imagePreviewUrl) {
    URL.revokeObjectURL(fileToRemove.imagePreviewUrl);
  }
  
  const shouldReleaseSandboxAfterRemoval =
    activeAgentType.value === 'deepagent' &&
    selectedFiles.value.length === 1 &&
    !hasDeepAgentConversationMessages();
  
  // 沙箱内实际存储的文件名以上传响应为准，可能与本地文件名不同
  const sandboxFileName = (fileToRemove?.parseResult as any)?.data?.filename || fileToRemove?.name;

  if (activeAgentType.value === 'deepagent' && sandboxFileName && chatStore.sessionThreadId) {
    try {
      await http.delete(`/skill/api/files/${encodeURIComponent(sandboxFileName)}`, undefined, {
        params: {
          session_thread_id: chatStore.sessionThreadId
        }
      });
    } catch (error) {
      console.error('Failed to remove file from deepagent:', error);
    }
  }

  selectedFiles.value.splice(index, 1);

  if (shouldReleaseSandboxAfterRemoval) {
    releaseDeepAgentSandbox({ resetSessionThreadId: true, force: true });
  }
};

const formatFileSize = (bytes: number) => {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
};

const formatWordCount = (count: number) => {
  if (!count) return '';
  if (count < 1000) return `约 ${count} 字`;
  if (count < 10000) return `约 ${(count / 1000).toFixed(1)} 千字`;
  return `约 ${(count / 10000).toFixed(1)} 万字`;
};

const onBeforeLeave = (el: Element) => {
  if (!(el instanceof HTMLElement)) return;
  if (isClearingForSend.value) return;

  const rect = el.getBoundingClientRect();
  const fileType = el.dataset.fileType || 'unknown';

  createParticleEffect(rect, fileType);
};

const onBeforeImageLeave = (el: Element) => {
  if (!(el instanceof HTMLElement)) return;
  if (isClearingForSend.value) return;

  const rect = el.getBoundingClientRect();
  createParticleEffect(rect, 'image');
};

let sendingLeaveTimer: ReturnType<typeof setTimeout> | null = null;
const onAfterImageLeave = () => {
  // transition-group 的每个元素离开后都会触发，使用防抖确保所有元素动画完成后才重置
  if (!isClearingForSend.value) return;
  if (sendingLeaveTimer) clearTimeout(sendingLeaveTimer);
  sendingLeaveTimer = setTimeout(() => {
    if (isClearingForSend.value && selectedImageFiles.value.length === 0) {
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          isClearingForSend.value = false;
        });
      });
    }
    sendingLeaveTimer = null;
  }, 50);
};

const createParticleEffect = (rect: DOMRect, type: string) => {
  const colors: Record<string, string[]> = {
    'pdf': ['#FF4D4F', '#FF7875', '#FFCCC7'],
    'word': ['#1890FF', '#40A9FF', '#BAE7FF'],
    'image': ['#13C2C2', '#36CFC9', '#B5F5EC'],
    'doc': ['#1890FF', '#40A9FF', '#BAE7FF'],
    'docx': ['#1890FF', '#40A9FF', '#BAE7FF'],
    'xls': ['#52C41A', '#73D13D', '#B7EB8F'],
    'xlsx': ['#52C41A', '#73D13D', '#B7EB8F'],
    'ppt': ['#FA8C16', '#FFA940', '#FFE7BA'],
    'pptx': ['#FA8C16', '#FFA940', '#FFE7BA'],
    'default': ['#8C8C8C', '#BFBFBF', '#F0F0F0']
  };
  
  const palette = (colors[type] || colors['default']) as string[];
  const particleCount = type === 'image' ? 54 : 40;
  
  const globalDrift = (Math.random() - 0.5) * 50;
  const isImageType = type === 'image';

  for (let i = 0; i < particleCount; i++) {
    const particle = document.createElement('div');
    const color = palette[Math.floor(Math.random() * palette.length)];
    const size = Math.random() * 4 + 2;
    
    const isOrbit = type === 'image' ? Math.random() < 0.58 : Math.random() < 0.4;
    
    let x, y;
    if (isOrbit) {
      const angle = Math.random() * Math.PI * 2;
      const radius = Math.min(rect.width, rect.height) * 0.4;
      x = rect.left + rect.width / 2 + Math.cos(angle) * radius;
      y = rect.top + rect.height / 2 + Math.sin(angle) * radius;
    } else {
      const r1 = Math.random();
      const r2 = Math.random();
      x = rect.left + rect.width / 2 + (r1 - 0.5) * rect.width * 0.6;
      y = rect.top + rect.height / 2 + (r2 - 0.5) * rect.height * 0.6;
    }
    
    particle.style.position = 'fixed';
    particle.style.left = `${x}px`;
    particle.style.top = `${y}px`;
    particle.style.width = `${size}px`;
    particle.style.height = `${size}px`;
    particle.style.backgroundColor = color;
    particle.style.borderRadius = '50%';
    particle.style.pointerEvents = 'none';
    particle.style.zIndex = '1';
    particle.style.opacity = isOrbit ? '0.6' : '0.7';
    particle.style.boxShadow = `0 0 ${size}px ${color}`; 
    
    document.body.appendChild(particle);
    
    let keyframes: Keyframe[] = [];
    let options: KeyframeAnimationOptions = {};
    
    if (isOrbit) {
      const startAngle = Math.atan2(y - (rect.top + rect.height / 2), x - (rect.left + rect.width / 2));
      const rotationSpeed = (Math.random() > 0.5 ? 1 : -1) * (Math.PI + Math.random() * Math.PI); 
      const lift = isImageType ? 75 + Math.random() * 25 : 60 + Math.random() * 40;
      const expand = isImageType ? 28 + Math.random() * 26 : 20 + Math.random() * 30; 
      
      const steps = 10;
      keyframes = [];
      for (let j = 0; j <= steps; j++) {
        const p = j / steps;
        const currentAngle = startAngle + rotationSpeed * p;
        const currentRadius = (Math.min(rect.width, rect.height) * 0.4) + expand * p; 
        
        const targetX = (rect.left + rect.width / 2) + Math.cos(currentAngle) * currentRadius;
        const targetY = (rect.top + rect.height / 2) + Math.sin(currentAngle) * currentRadius - lift * p;
        
        keyframes.push({
          transform: `translate(${targetX - x}px, ${targetY - y}px) scale(${1 - p * 0.5})`,
          opacity: (1 - p) * 0.6,
          offset: p
        });
      }
      
      options = {
        duration: isImageType ? 760 + Math.random() * 220 : 500 + Math.random() * 300,
        easing: 'linear',
        fill: 'forwards'
      };
      
    } else {
      const lift = 80 + Math.random() * 60;
      const waveAmp = 20 + Math.random() * 20;
      const waveFreq = (Math.random() * 2 + 1) * Math.PI;
      const phase = Math.random() * Math.PI * 2;
      
      const steps = 10;
      keyframes = [];
      for (let j = 0; j <= steps; j++) {
        const p = j / steps;
        
        const dy = -lift * p;
        
        const dx = Math.sin(phase + p * waveFreq) * waveAmp * p + globalDrift * p;
        
        keyframes.push({
          transform: `translate(${dx}px, ${dy}px) scale(${1 - p * 0.3})`,
          opacity: 0.7 * (1 - p * p),
          offset: p
        });
      }
      
      options = {
        duration: isImageType ? 760 + Math.random() * 220 : 600 + Math.random() * 400,
        delay: Math.random() * 50,
        easing: 'linear',
        fill: 'forwards'
      };
    }

    const animation = particle.animate(keyframes, options);
    
    animation.onfinish = () => {
      particle.remove();
    };
  }
};

const getFileExtension = (filename: string) => {
  if (!filename) return '';
  const ext = filename.split('.').pop();
  return ext ? ext.toUpperCase() : '';
};

const IMAGE_EXTS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'];
const isImageFileName = (filename: string) => IMAGE_EXTS.some(ext => (filename || '').toLowerCase().endsWith(ext));

const getFileIcon = (filename: string) => {
  const name = (filename || '').toLowerCase();
  if (isImageFileName(name)) return ImageSvg;
  if (name.endsWith('.pdf')) return PdfSvg;
  if (name.endsWith('.docx') || name.endsWith('.doc')) return WordSvg;
  if (name.endsWith('.txt')) return TxtSvg;
  if (name.endsWith('.md')) return MarkdownSvg;
  if (name.endsWith('.ppt') || name.endsWith('.pptx')) return PptSvg;
  if (name.endsWith('.csv') || name.endsWith('.xls') || name.endsWith('.xlsx')) return ExcelSvg;
  if (name.endsWith('.zip')) return ZipSvg;
  if (isCadFile(name)) return CadSvg;
  // 其余未识别的类型统一使用灰色虚线问号图标
  return UnknownSvg;
};

const isSelectionMode = computed(() => props.isSelectionMode);

const selectedAgentName = ref<string | null>(null);
const activeAgentModelState = ref<{ name: string; service: string }>({ name: '', service: '' });
const activeAgentType = ref<'assistant' | 'orchestrator' | 'deepagent'>('assistant');

// 普通对话文件上传仅支持常见文档；DeepAgent 支持全部文件格式（不限制 accept）
const fileAccept = computed(() => {
  if (activeAgentType.value === 'deepagent') return undefined;
  return '.docx,.pdf,.doc,.txt,.md,.csv,.xls,.xlsx,.ppt,.pptx';
});

const orchestratorUrl = ref<string>('');
const activeAgentPhrases = ref<string[]>([]);

const normalizeAgentPhrases = (phrases: unknown): string[] => {
  if (!Array.isArray(phrases)) return [];
  const seen = new Set<string>();
  const normalized: string[] = [];

  for (const item of phrases) {
    if (typeof item !== 'string') continue;
    const trimmed = item.trim();
    if (!trimmed || seen.has(trimmed)) continue;
    seen.add(trimmed);
    normalized.push(trimmed);
  }

  return normalized;
};

const visibleQuickPhrases = computed(() => {
  return activeAgentPhrases.value;
});

// 常用提问分页：限制列表高度，避免内容过多
const QUICK_PHRASE_PAGE_SIZE = 5;
const quickPhrasePage = ref(0);

const totalQuickPhrasePages = computed(() => {
  return Math.max(1, Math.ceil(visibleQuickPhrases.value.length / QUICK_PHRASE_PAGE_SIZE));
});

const pagedQuickPhrases = computed(() => {
  const start = quickPhrasePage.value * QUICK_PHRASE_PAGE_SIZE;
  return visibleQuickPhrases.value.slice(start, start + QUICK_PHRASE_PAGE_SIZE);
});

watch(visibleQuickPhrases, () => {
  quickPhrasePage.value = 0;
});

const shouldShowQuickPhrases = computed(() => {
  return props.isWelcomeActive && isAgentModeActive.value && visibleQuickPhrases.value.length > 0 && !isSelectionMode.value;
});

const handleQuickPhraseClick = async (phrase: string) => {
  const normalizedPhrase = phrase.trim();
  if (!normalizedPhrase) return;

  // 智能体初始化中：不触发发送，只把提问填入输入框，待初始化完成后再手动发送
  if (isAgentInitPending.value) {
    if (isVoiceInputActive.value) {
      isVoiceInputActive.value = false;
      await nextTick();
    }
    // 直接替换输入框内容，避免连续点击常用提问时文本累加
    inputMessage.value = normalizedPhrase;
    return;
  }

  if (isCompressingContext.value) {
    NotificationService.info('正在压缩上下文，请稍候后再发送常用提问');
    return;
  }
  if (chatStore.isProcessing || isSubmitting.value || isWaitingForResponse.value || isFileProcessing.value) {
    NotificationService.info('请等待当前回复完成后再发送常用提问');
    return;
  }

  if (isVoiceInputActive.value) {
    isVoiceInputActive.value = false;
    await nextTick();
  }

  inputMessage.value = normalizedPhrase;
  await nextTick();
  await sendMessage();
};

const currentStage = computed(() => {
  if (activeAgentType.value !== 'orchestrator' && activeAgentType.value !== 'deepagent') return '';
  
  const msgs = chatStore.messages;
  if (!msgs || msgs.length === 0) return '';
  
  for (let i = msgs.length - 1; i >= 0; i--) {
    const msg = msgs[i];
    if (msg.role === 'assistant' && msg.stage) {
      return msg.stage;
    }
  }
  return '';
});

const currentTodo = computed(() => {
  if (activeAgentType.value !== 'orchestrator' && activeAgentType.value !== 'deepagent') return null;
  const msgs = chatStore.messages;
  if (!msgs || msgs.length === 0) return null;

  for (let i = msgs.length - 1; i >= 0; i--) {
    const msg = msgs[i];
    if (msg.role === 'assistant' && msg.todos && msg.todos.length > 0) {
      const inProgress = msg.todos.find(t => t.status === 'in_progress');
      if (inProgress) return inProgress;
      const completed = [...msg.todos].reverse().find(t => t.status === 'completed');
      if (completed) return completed;
      return msg.todos[0];
    }
  }
  return null;
});

const todoList = computed(() => {
  if (activeAgentType.value !== 'orchestrator' && activeAgentType.value !== 'deepagent') return [];
  const msgs = chatStore.messages;
  if (!msgs || msgs.length === 0) return [];

  for (let i = msgs.length - 1; i >= 0; i--) {
    const msg = msgs[i];
    if (msg.role === 'assistant' && msg.todos && msg.todos.length > 0) {
      return msg.todos;
    }
  }
  return [];
});

  const artifactHistory = computed<Artifact[]>(() => {
  const msgs = chatStore.messages || [];
  const supported = new Set(['mermaid', 'html', 'svg', 'markdown', 'docx', 'pdf', 'text', 'csv', 'xlsx', 'pptx', 'url', 'json']);
  const seen = new Set<string>();
  const out: Artifact[] = [];

  for (let i = msgs.length - 1; i >= 0; i--) {
    const msg: any = msgs[i];
    if (!msg) continue;

    if (msg.role === 'user' && msg.files && msg.files.length > 0) {
        const msgId = (typeof msg.id === 'string' && msg.id) ? msg.id : (msg.uiKey || `msg-user-${i}`);

        for (let fileIndex = 0; fileIndex < msg.files.length; fileIndex++) {
            const file = msg.files[fileIndex];
            
            // 跳过图片文件，图片不走Canvas流程
            if (file.isFileImage) continue;

            // 跳过 CAD 图纸：只上传不解析，Canvas 无内容可预览
            if (isCadFile((file.name || '').toLowerCase())) continue;
            
            const fileKey = `file:${file.name}-${msgId}`;
            if (seen.has(fileKey)) continue;
            seen.add(fileKey);
            
            let content: any = '';
            const isBuffer = file.content instanceof ArrayBuffer || ArrayBuffer.isView(file.content) || Object.prototype.toString.call(file.content) === '[object ArrayBuffer]';

            if (file.content && isBuffer) {
                content = file.content;
            } else if (file.parseResult && file.parseResult.document_chunks) {
                content = file.parseResult.document_chunks.map((c: any) => c.content).join('\n\n');
            } else if (typeof file.content === 'string') {
                content = file.content;
            }
            
            const name = (file.name || '').toLowerCase();
            let type = 'markdown';
            if (name.endsWith('.docx') || name.endsWith('.doc')) type = 'docx';
            else if (name.endsWith('.pdf')) type = 'pdf';
            else if (name.endsWith('.txt')) type = 'text';
            else if (name.endsWith('.md')) type = 'markdown';
            else if (name.endsWith('.csv')) type = 'csv';
            else if (name.endsWith('.xls') || name.endsWith('.xlsx')) type = 'xlsx';
            else if (name.endsWith('.ppt') || name.endsWith('.pptx')) type = 'pptx';

            out.push({
                id: `${msgId}-file-${fileIndex}`,
                type: type,
                content: content || '无法预览文件内容',
                title: file.name,
                isComplete: true,
                url: typeof file.url === 'string' ? file.url : undefined
            });
            if (out.length >= 10) return out.reverse();
        }
    }

    if (msg.role !== 'assistant') continue;
    
    const role = msg.role;
    const content = msg.content || '';
    const messageRef = content + role + i;
    const generatedId = `msg-${role}-${i}-${messageRef.length}`;
    
    const msgId = (typeof msg.id === 'string' && msg.id) ? msg.id : (msg.uiKey || generatedId);
    const parts = parseArtifactsFromContent((msg.content || '') as string, msgId);

    for (let j = parts.length - 1; j >= 0; j--) {
      const art = parts[j];
      if (art.isInThinking) continue;
      
      const type = (art.type || '').toLowerCase().trim();
      if (!supported.has(type)) continue;
      
      // URL 来源仅在输出完整时才加入列表，避免流式行内代码未闭合导致 mini-btn 展示残缺链接
      if (art.url && !art.isComplete) continue;
      
      out.push(art);
      if (out.length >= 10) return out.reverse();
    }

    // 扫描 kb_citations 中的文件引用，纳入 artifact 列表
    const citations = (msg as any).kb_citations as any[] | undefined;
    if (citations && citations.length > 0) {
      const citationSeen = new Set<string>();
      // 从后往前 push，配合最终 reverse 保持 citations 原始顺序（k=0 排最前），
      // 确保 toolbar 首次自动选中与 KB auto-open 打开的是同一篇文档
      for (let k = citations.length - 1; k >= 0; k--) {
        const cit = citations[k];
        const source = (cit?.metadata?.source || '').trim();
        if (!source || source === '未知来源') continue;
        // 仅处理有明确文件扩展名的引用
        const extMatch = source.match(/\.([a-zA-Z0-9]+)$/);
        if (!extMatch) continue;
        const ext = extMatch[1].toLowerCase();
        const citType = (() => {
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
            default: return '';
          }
        })();
        if (!citType) continue;
        const fileId = `kb-${i}-${k}`;
        if (seen.has(fileId) || citationSeen.has(fileId)) continue;
        citationSeen.add(fileId);
        const downloadUrl = (cit?.file_path || cit?.metadata?.file_path || '').trim();
        // 历史会话恢复出的引用通常缺少 file_path，只有 metadata.source 与 knowledge_base_name，
        // 无法直接以 URL 预览（需走知识库下载接口，由 ChatMessage 的 citation 预览处理），
        // 这里跳过，避免 toolbar 生成一个拼文件名、点击后 404 的无效 artifact。
        if (!downloadUrl) continue;
        const fileName = source.split(/[\\/]/).pop() || source;
        out.push({
          id: fileId,
          type: citType,
          content: downloadUrl,
          title: fileName,
          isComplete: true,
          url: downloadUrl
        });
        if (out.length >= 10) return out.reverse();
      }
    }
  }

  return out.reverse();
});

const updateSelectedAgent = () => {
  try {
    const activeAgent = StorageService.getActiveAgent();
    selectedAgentName.value = activeAgent?.basic?.name || null;
    activeAgentPhrases.value = normalizeAgentPhrases(activeAgent?.phrases || activeAgent?.config?.phrases);
    const m = (activeAgent as any)?.model || {};
    activeAgentModelState.value = {
      name: (typeof m.name === 'string' ? m.name : '') || '',
      service: (typeof m.service === 'string' ? m.service : '') || ''
    };
    const t = (activeAgent?.basic?.type) || (activeAgent?.config?.basic?.type) || 'assistant';
    activeAgentType.value = t;
    const url = (activeAgent?.orchestrator?.serviceUrl) || (activeAgent?.config?.orchestrator?.serviceUrl) || '';
    orchestratorUrl.value = (typeof url === 'string' ? url.replace(/`/g, '').trim() : '');
  } catch (e) {
    selectedAgentName.value = null;
    activeAgentPhrases.value = [];
    activeAgentModelState.value = { name: '', service: '' };
    activeAgentType.value = 'assistant';
    orchestratorUrl.value = '';
  }
};

const refreshActiveAgentModelState = () => {
  try {
    const activeAgent = StorageService.getActiveAgent();
    const m = (activeAgent as any)?.model || {};
    activeAgentModelState.value = {
      name: (typeof m.name === 'string' ? m.name : '') || '',
      service: (typeof m.service === 'string' ? m.service : '') || ''
    };
  } catch {
    activeAgentModelState.value = { name: '', service: '' };
  }
};

onMounted(() => {
  updateSelectedAgent();
  window.addEventListener('active-agent-updated', updateSelectedAgent as EventListener);
  window.addEventListener('agent-selection-changed', updateSelectedAgent as EventListener);
  window.addEventListener('agents-updated', updateSelectedAgent as EventListener);
  window.addEventListener('mcp-models-changed', refreshActiveAgentModelState as EventListener);

  window.addEventListener('dragenter', handleDragEnter);
  window.addEventListener('dragover', handleDragOver);
  window.addEventListener('dragleave', handleDragLeave);
  window.addEventListener('drop', handleDrop);

});

onUnmounted(() => {
  window.removeEventListener('active-agent-updated', updateSelectedAgent as EventListener);
  window.removeEventListener('agent-selection-changed', updateSelectedAgent as EventListener);
  window.removeEventListener('agents-updated', updateSelectedAgent as EventListener);
  window.removeEventListener('mcp-models-changed', refreshActiveAgentModelState as EventListener);
  
  window.removeEventListener('dragenter', handleDragEnter);
  window.removeEventListener('dragover', handleDragOver);
  window.removeEventListener('dragleave', handleDragLeave);
  window.removeEventListener('drop', handleDrop);

});

watch(
    () => [chatStore.isConfigured, chatStore.model],
    () => {
    },
    {immediate: true}
);

watch(
    () => chatStore.isProcessing,
    (isProcessing) => {
      if (isProcessing) {
        showSendIcon.value = false;
        isSubmitting.value = true;
        isTransitioning.value = true;
        setTimeout(() => {
          isTransitioning.value = false;
        }, 500);
      } else {
        setTimeout(() => {
          showSendIcon.value = true;
          isSubmitting.value = false;
        }, 100);
      }
    }
);

watch(isVoiceInputActive, (newVal) => {
  if (newVal) {
    startRecording();
  } else {
    stopRecording();
  }
});

const showNewChatButton = computed(() => {
  return chatStore.messages.length > 0;
});

const availableVisionModels = computed(() => {
  return (chatStore.availableModels || []).filter((model: any) => {
    const types = Array.isArray(model?.types) ? model.types : [];
    return types.includes('vision');
  });
});

const hasVisionModel = computed(() => availableVisionModels.value.length > 0);

const currentSelectedModel = computed(() => {
  const currentModelId = (chatStore.model || '').trim();
  if (!currentModelId) return null;
  return (chatStore.availableModels || []).find((model: any) => model.id === currentModelId) || null;
});

const isCurrentModelVision = computed(() => {
  const types = Array.isArray(currentSelectedModel.value?.types) ? currentSelectedModel.value.types : [];
  return types.includes('vision');
});

const isWaitingForResponse = computed(() => {
  const lastMessage = chatStore.messages[chatStore.messages.length - 1];
  return lastMessage &&
      lastMessage.role === 'assistant' &&
      lastMessage.isStreaming &&
      !lastMessage.content &&
      !(lastMessage.tool_calls && lastMessage.tool_calls.length > 0) &&
      !lastMessage.reasoning_content;
});

const isFileProcessing = computed(() => {
  return selectedFiles.value.some(f => f.uploadStatus === 'uploading' || f.uploadStatus === 'parsing');
});

watch(isWaitingForResponse, () => {
});

const isConfigReady = computed(() => {
  if (activeAgentType.value === 'orchestrator') {
    return !!orchestratorUrl.value;
  }

  const cfg: any = StorageService.getApiConfig();
  const hasPersist = !!(cfg && cfg.apiKey) && !!(cfg && cfg.apiBaseUrl) && !!(cfg && cfg.model);

  const unwrap = (r: any): any => (r && typeof r === 'object' && 'value' in r) ? unwrap(r.value) : r;
  const storeApiKey = unwrap(chatStore.apiKey);
  const storeBaseUrl = unwrap(chatStore.apiBaseUrl);
  const storeModel = unwrap(chatStore.model);
  const hasStore = !!(typeof storeApiKey === 'string' && storeApiKey.trim())
    && !!(typeof storeBaseUrl === 'string' && storeBaseUrl.trim())
    && !!(typeof storeModel === 'string' && storeModel.trim());

  return hasPersist || hasStore;
});

const hasActiveAgentMissingModel = computed(() => {
  if (activeAgentType.value === 'orchestrator') return false;
  const name = (activeAgentModelState.value.name || '').trim();
  const svc = (activeAgentModelState.value.service || '').trim();
  return !!selectedAgentName.value && (!name || !svc);
});

const isAsrConfigured = computed(() => {
  return !!getAsrServer();
});

// 知识库按钮始终展示（助手模式且未选中智能体时）：
// 无知识库或列表加载中不再隐藏，改用虚线空态样式表达
const showKnowledgeBaseButton = computed(() => {
  return activeAgentType.value === 'assistant' && !selectedAgentName.value;
});

const isAgentModeActive = computed(() => {
  return !!selectedAgentName.value;
});

watch(isAgentModeActive, (isActive) => {
  if (isActive) {
    disableKnowledgeBaseForAgentMode();
  }
});

const shouldShowAgentModeBanner = computed(() => {
  return !isSelectionMode.value && isAgentModeActive.value;
});

const isAgentModeVisualActive = computed(() => shouldShowAgentModeBanner.value);

const agentModeDisplayName = computed(() => {
  return selectedAgentName.value || '当前智能体';
});

const exitAssistantMode = () => {
  try {
    if (activeAgentType.value === 'deepagent') {
      // 沙箱释放后台静默进行，退出无需等待其返回
      releaseDeepAgentSandbox({ resetSessionThreadId: true, force: true });
    }

    StorageService.setSelectedAgent(null);
    StorageService.removeActiveAgent();
    StorageService.remove('mcp-original-config');

    chatStore.clearChat();
    window.dispatchEvent(new CustomEvent('clear-canvas'));
    window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: null } }));
    window.dispatchEvent(new CustomEvent('agent-selection-changed', { detail: { selected: false, agentId: null } }));
    window.dispatchEvent(new Event('agents-updated'));
  } catch (error) {
    console.error('Failed to exit assistant mode:', error);
    NotificationService.error('退出智能体模式失败，请稍后重试');
  }
}; 

// 智能体后台初始化中：输入框可继续输入，但禁止发送
const isAgentInitPending = computed(() => {
  return isAgentModeActive.value && chatStore.agentInitStatus === 'initializing';
});

const isButtonDisabled = computed(() => {
  return !isConfigReady.value || isWaitingForResponse.value || hasActiveAgentMissingModel.value || isFileProcessing.value || isCompressingContext.value || isScreenshotCapturing.value || isAgentInitPending.value;
});

const isInputEnabled = computed(() => {
  return isConfigReady.value && !hasActiveAgentMissingModel.value;
});

const inputPlaceholder = computed(() => {
  if (pendingScreenshotCardId.value) return '正在截取网页页面';
  if (isConnecting.value) return '正在连接语音识别服务';
  if (isVoiceInputActive.value) return '正在听取您的问题';
  if (isAgentInitPending.value) return '智能体初始化中，可以先输入问题…';
  return '请输入您想提问的问题';
});

const readFileAsDataUrl = (file: File) => {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(new Error(`读取图片 ${file.name} 失败`));
    reader.readAsDataURL(file);
  });
};

const createLocalImageFileItem = (file: File) => {
  const fileId = uuidv4();
  const imagePreviewUrl = URL.createObjectURL(file);

  return {
    id: fileId,
    name: file.name,
    size: file.size,
    content: new ArrayBuffer(0),
    uploadStatus: 'success' as const,
    uploadProgress: 100,
    isFileImage: true,
    imagePreviewUrl,
    imageTokenEstimate: estimateImageTokensFromMetadata({ size: file.size }),
    parseResult: undefined as UploadResponse | undefined,
    file
  };
};

const buildFilesToSendFromItems = async (items: Array<any>) => {
  if (items.length === 0) return undefined;

  const filesToSend = await Promise.all(items
    .filter(f => f.parseResult || f.isFileImage)
    .map(async f => {
      const imageDataUrl = f.isFileImage && f.file ? await readFileAsDataUrl(f.file) : undefined;
      return {
        name: f.name,
        size: f.size,
        type: f.type || f.file?.type,
        parseResult: f.parseResult,
        content: f.content,
        isFileImage: f.isFileImage,
        imagePreviewUrl: imageDataUrl || f.imagePreviewUrl,
        imageWidth: f.imageWidth,
        imageHeight: f.imageHeight,
        imageTokenEstimate: f.imageTokenEstimate,
        file: f.file,
        imageDataUrl
      };
    }));

  return filesToSend.length > 0 ? filesToSend : undefined;
};

const buildFilesToSend = async () => {
  return buildFilesToSendFromItems(selectedFiles.value);
};

const handleButtonClick = async () => {
  if (isAgentInitPending.value) {
    NotificationService.info('智能体初始化中，请稍候再发送');
    return;
  }

  if (isCompressingContext.value) {
    NotificationService.info('正在压缩上下文，请稍候后再发送消息');
    return;
  }

  if (isWaitingForResponse.value || isFileProcessing.value) {
    return;
  }

  const hasImageFiles = selectedFiles.value.some(f => f.isFileImage);
  // DeepAgent 的图片上传到沙箱由智能体自行处理，不走前端视觉模型，无需切换模型
  if (activeAgentType.value !== 'deepagent' && hasImageFiles && !isCurrentModelVision.value) {
    const firstVisionModel = availableVisionModels.value[0];
    if (!firstVisionModel) {
      NotificationService.warning('当前没有可用于图片问答的视觉模型');
      return;
    }
    
    if (firstVisionModel.serviceProvider) {
      chatStore.loadModelServiceConfig(firstVisionModel.serviceProvider, true);
    }
    chatStore.setModel(firstVisionModel.id);
    await nextTick();
  }

  if (isVoiceInputActive.value) {
    isVoiceInputActive.value = false;
    return;
  }

  if (!chatStore.isProcessing && !isSubmitting.value && inputMessage.value.trim().length === 0 && selectedFiles.value.length === 0) {
    isVoiceInputActive.value = true;
    return;
  }

  if (chatStore.isProcessing || isSubmitting.value) {
    if (activeAgentType.value === 'orchestrator') {
      NotificationService.info('内置编排式智能体模式下不支持打断对话');
      return;
    }
    await stopCurrentRequest();
  } else {
    sendMessage();
  }
};

const stopCurrentRequest = async () => {
  try {
    await chatStore.stopCurrentRequest();
    isSubmitting.value = false;
    showSendIcon.value = true;
    NotificationService.info('已中断当前问题请求');
  } catch (error) {
    console.error('中断请求时出错:', error);
    NotificationService.error('中断请求失败');
  }
};

const sendMessage = async () => {
  if (isCompressingContext.value) {
    NotificationService.info('正在压缩上下文，请稍候后再发送消息');
    return;
  }

  if (activeAgentType.value !== 'orchestrator') {
    if (hasActiveAgentMissingModel.value) {
      NotificationService.warning('前选中的智能体未配置模型，请为该智能体选择模型');
      window.dispatchEvent(new Event('open-agent-workspace'));
      return;
    }
    if (!chatStore.isConfigured) {
      NotificationService.warning('请配置 API 设置来开始聊天');
      return;
    }
    if (!chatStore.model) {
      NotificationService.warning('请先选择模型');
      return;
    }
  } else {
    if (!orchestratorUrl.value) {
      NotificationService.warning('请在智能体中配置编排式服务 URL');
      return;
    }
  }

  const hasSelectedFiles = selectedFiles.value.length > 0;
  const hasImageFiles = selectedFiles.value.some(f => f.isFileImage);
  const hasTextInput = !!inputMessage.value.trim();

  if (!hasTextInput && !hasSelectedFiles) {
    NotificationService.info('请输入您想提问的问题后，点击发送按钮进行提问！');
    return;
  }

  if (!chatStore.isProcessing && !isSubmitting.value) {
    isSubmitting.value = true;
    showSendIcon.value = false;

    let messageToSend = inputMessage.value.trim();
    if (!messageToSend) {
      if (hasImageFiles) {
        messageToSend = '请描述图片中的内容';
      } else if (hasSelectedFiles && selectedFiles.value.some(f => f.parseResult)) {
        messageToSend = '详细总结文档内容';
      }
    }
    
    inputMessage.value = '';

    const filesToSend = await buildFilesToSend();
    // 本轮对话的 turn_id：有附件时复用上传阶段生成的那一个，无附件时新建；
    // 发送后重置，保证下一轮生成新的
    const sendTurnId = getOrCreateUploadTurnId();
    pendingUploadTurnId = '';

    if (selectedFiles.value.length > 0) {
      const hadImages = selectedImageFiles.value.length > 0;
      isClearingForSend.value = true;
      await nextTick();
      selectedFiles.value = [];
      await nextTick();
      // 如果有图片，由 onAfterImageLeave 在图片 leave 动画完成后重置状态
      // 如果只有文档（无图片），使用 setTimeout 兜底
      if (!hadImages) {
        setTimeout(() => {
          if (isClearingForSend.value) {
            isClearingForSend.value = false;
          }
        }, 350);
      }
    } else {
      isClearingForSend.value = false;
    }

    const kbConfig = {
      enabled: isKnowledgeBaseEnabled.value,
      kbNames: selectedKnowledgeBaseNames.value
    };

    requestChatScrollToBottom(true);
    notifyHistorySummaryPending();
    chatStore.sendMessage(messageToSend, filesToSend, kbConfig, { turnId: sendTurnId }).finally(() => {
      setTimeout(() => {
        isSubmitting.value = false;
        showSendIcon.value = true;
      }, 100);
    });
  }
};

const handleInputFocus = () => {
  if (hasActiveAgentMissingModel.value) {
    NotificationService.warning('当前选中的智能体未配置模型，请为该智能体选择模型');
    window.dispatchEvent(new Event('open-agent-workspace'));
  }
  if (!chatStore.isConfigured) {
    NotificationService.warning('请配置 API 设置来开始聊天');
    // 仍显示提示文案以引导用户
  }

  if (!chatStore.model) {
    NotificationService.warning('请先选择模型');
    // 仍显示提示文案以引导用户
  }

  // 通知欢迎信息显示提示文案
  window.dispatchEvent(new CustomEvent('welcome-message-show-title'));
};

const handleInputBlur = () => {
  if (!inputMessage.value.trim()) {
    window.dispatchEvent(new CustomEvent('welcome-message-show-logo'));
  }
};

const requestChatScrollToBottom = (smooth = true) => {
  document.dispatchEvent(new CustomEvent('chat-force-scroll-to-bottom', {
    detail: { smooth }
  }));
};

const handleKeyPress = async (e: KeyboardEvent) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();

    if (isAgentInitPending.value) {
      NotificationService.info('智能体初始化中，请稍候再发送');
      return;
    }

    if (isCompressingContext.value) {
      NotificationService.info('正在压缩上下文，请稍候后再发送消息');
      return;
    }

    if (activeAgentType.value !== 'orchestrator') {
      if (hasActiveAgentMissingModel.value) {
        NotificationService.warning('当前选中的智能体未配置模型，请为该智能体选择模型');
        window.dispatchEvent(new Event('open-agent-workspace'));
        return;
      }
      if (!chatStore.isConfigured) {
        NotificationService.warning('请配置 API 设置来开始聊天');
        return;
      }
      if (!chatStore.model) {
        NotificationService.warning('请先选择模型');
        return;
      }
    } else {
      if (!orchestratorUrl.value) {
        NotificationService.warning('请在智能体中配置编排式服务 URL');
        return;
      }
    }

    const currentMessage = inputMessage.value;
    const hasSelectedFiles = selectedFiles.value.length > 0;
    const hasImageFiles = selectedFiles.value.some(f => f.isFileImage);
    const hasTextInput = !!currentMessage.trim();

    if (!hasTextInput && !hasSelectedFiles) {
      NotificationService.info('请输入您想提问的问题后，点击发送按钮进行提问！');
      return;
    }
    if (!chatStore.isProcessing && !isSubmitting.value) {
      isSubmitting.value = true;
      showSendIcon.value = false;
      
      let messageToSend = currentMessage.trim();
      if (!messageToSend) {
        if (hasImageFiles) {
          messageToSend = '请描述图片中的内容';
        } else if (hasSelectedFiles && selectedFiles.value.some(f => f.parseResult)) {
          messageToSend = '详细总结文档内容';
        }
      }
      
      inputMessage.value = '';

      const filesToSend = await buildFilesToSend();
      // 本轮对话的 turn_id：有附件时复用上传阶段生成的那一个，无附件时新建；
      // 发送后重置，保证下一轮生成新的
      const sendTurnId = getOrCreateUploadTurnId();
      pendingUploadTurnId = '';

      if (selectedFiles.value.length > 0) {
        const hadImages = selectedImageFiles.value.length > 0;
        isClearingForSend.value = true;
        await nextTick();
        selectedFiles.value = [];
        await nextTick();
        // 如果有图片，由 onAfterImageLeave 在图片 leave 动画完成后重置状态
        // 如果只有文档（无图片），使用 setTimeout 兜底
        if (!hadImages) {
          setTimeout(() => {
            if (isClearingForSend.value) {
              isClearingForSend.value = false;
            }
          }, 350);
        }
      } else {
        isClearingForSend.value = false;
      }

      const kbConfig = {
        enabled: isKnowledgeBaseEnabled.value,
        kbNames: selectedKnowledgeBaseNames.value
      };

      requestChatScrollToBottom(true);
      notifyHistorySummaryPending();
      chatStore.sendMessage(messageToSend, filesToSend, kbConfig, { turnId: sendTurnId }).finally(() => {
        setTimeout(() => {
          isSubmitting.value = false;
          showSendIcon.value = true;
        }, 100);
      });
    }
  }
};

watch(() => chatStore.sessionThreadId, () => {
  isSubmitting.value = false;
  showSendIcon.value = true;
});

const initNewChat = () => {
  const currentSessionId = String(chatStore.sessionThreadId || '').trim();
  const historySessionMeta = StorageService.getWorkspaceValue<Record<string, { agentId?: string; chatType?: string }>>(
    'history-session-meta',
    {}
  ) || {};
  const isCurrentSessionPersistedHistory = !!(currentSessionId && historySessionMeta[currentSessionId]);

  // 当前已经是一个空白的新对话 session 时，再次点击“新对话”不应重复换 session id。
  // 但如果这是一个被恢复出来的历史会话，即使当前消息区为空，也仍然要切到真正的新会话。
  if (chatStore.messages.length === 0 && !isCurrentSessionPersistedHistory) return;

  chatStore.detachCurrentConversation();

  // 优先恢复暂存草稿，再取当前智能体独立的备用上下文。
  // 已有内容的会话不会进入备用池；只释放这次确实离开的会话。
  const previousSessionId = chatStore.sessionThreadId;
  const warmSessionId = chatStore.resolveWarmSandboxSessionId();
  if (!warmSessionId || warmSessionId !== previousSessionId) {
    releaseDeepAgentSandbox();
  }

  if (warmSessionId) {
    chatStore.setSessionThreadId(warmSessionId);
    chatStore.clearChat({ regenerateSessionThreadId: false });
  } else {
    try {
      chatStore.clearChat({ regenerateSessionThreadId: true });
    } catch (e) {
      chatStore.clearChat({ regenerateSessionThreadId: true });
    }
  }
  emit('new-chat');
  inputMessage.value = '';
  document.dispatchEvent(new CustomEvent('hide-scroll-button'));
};

const openAgentPicker = () => {
  window.dispatchEvent(new Event('open-agent-picker'));
};

const handleToggleAll = () => {
  emit('toggle-all')
};

const handleCancelSelection = () => {
  emit('cancel-selection')
};

const handleCopySelected = () => {
  emit('copy-selected')
};

const handleExportText = () => {
  emit('export-text')
};

const handleExportMarkdown = () => {
  emit('export-markdown')
};

const beginScreenshotCapture = (messageKey?: string) => {
  isScreenshotCapturing.value = true;
  pendingScreenshotMessageKey.value = messageKey || null;
  return pendingScreenshotCardId.value;
};

const handleScreenshot = async (screenshotFile: File) => {
  const isDeepAgentScreenshot = activeAgentType.value === 'deepagent';

  if (!isDeepAgentScreenshot && !hasVisionModel.value) {
    NotificationService.warning('当前模型不支持图片，请切换到支持图片的模型');
    return;
  }

  const maxSize = 10;
  if (screenshotFile.size >= maxSize * 1024 * 1024) {
    NotificationService.info(`截图大小超过 ${maxSize}MB 限制`);
    return;
  }

  const pngScreenshotFile = new File(
    [screenshotFile],
    /\.png$/i.test(screenshotFile.name) ? screenshotFile.name : `${screenshotFile.name.replace(/\.[^.]+$/, '') || 'screenshot'}.png`,
    { type: 'image/png', lastModified: Date.now() }
  );

  // 截图与文件上传保持一致：发送前先确认密级，取消则中止本次截图
  isScreenshotCapturing.value = false;
  const screenshotClassification = await requestScreenshotClassification(pngScreenshotFile);
  if (!screenshotClassification) {
    pendingScreenshotCardId.value = null;
    pendingScreenshotMessageKey.value = null;
    return;
  }

  if (!isDeepAgentScreenshot && !isCurrentModelVision.value) {
    const firstVisionModel = availableVisionModels.value[0];
    if (!firstVisionModel) {
      NotificationService.warning('当前没有可用于图片问答的视觉模型');
      return;
    }
    if (firstVisionModel.serviceProvider) {
      chatStore.loadModelServiceConfig(firstVisionModel.serviceProvider, true);
    }
    chatStore.setModel(firstVisionModel.id);
    await nextTick();
  }

  if (chatStore.isProcessing || isSubmitting.value) {
    return;
  }

  isSubmitting.value = true;
  showSendIcon.value = false;

  let screenshotPreviewUrl = '';
  try {
    isScreenshotCapturing.value = false;
    let filesToSend: any[] | undefined;
    const screenshotFileItem = createLocalImageFileItem(pngScreenshotFile);
    screenshotPreviewUrl = screenshotFileItem.imagePreviewUrl || '';

    chatStore.setPendingInputImages(screenshotPreviewUrl ? [{
      key: screenshotFileItem.id,
      url: screenshotPreviewUrl,
      alt: pngScreenshotFile.name || '网页截图',
      name: pngScreenshotFile.name || '网页截图',
      source: 'input',
      messageIndex: -1,
      messageId: 'chat-input',
      role: 'user'
    }] : []);

    if (isDeepAgentScreenshot) {
      const uploadResponse = await FileUploadService.uploadDeepAgentFile(
        pngScreenshotFile,
        chatStore.sessionThreadId,
        undefined,
        screenshotClassification
      );
      screenshotFileItem.parseResult = uploadResponse;
      filesToSend = await buildFilesToSendFromItems([screenshotFileItem]);
    } else {
      filesToSend = await buildFilesToSendFromItems([screenshotFileItem]);
    }

    const kbConfig = {
      enabled: isKnowledgeBaseEnabled.value,
      kbNames: selectedKnowledgeBaseNames.value
    };

    requestChatScrollToBottom(true);
    await new Promise(resolve => {
      window.setTimeout(resolve, SCREENSHOT_MESSAGE_TRANSITION_MS);
    });
    notifyHistorySummaryPending();
    await chatStore.sendMessage(
      '请帮我查看截图中的内容',
      filesToSend,
      kbConfig,
      pendingScreenshotMessageKey.value ? { reuseUserMessageUiKey: pendingScreenshotMessageKey.value } : undefined
    );
  } finally {
    if (screenshotPreviewUrl) {
      URL.revokeObjectURL(screenshotPreviewUrl);
    }
    pendingScreenshotCardId.value = null;
    pendingScreenshotMessageKey.value = null;
    isScreenshotCapturing.value = false;
    chatStore.setPendingInputImages(inputImages.value);
    setTimeout(() => {
      isSubmitting.value = false;
      showSendIcon.value = true;
    }, 100);
  }
};

defineExpose({
  beginScreenshotCapture,
  handleScreenshot,
  initNewChat
});
</script>

<style scoped>
@import '@/assets/styles/chat-input.css';

.capture-pending-card {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(180deg, #eef4ff 0%, #dfefff 100%);
  border: 1px solid rgba(175, 201, 235, 0.72);
  box-shadow: 0 10px 24px rgba(59, 130, 246, 0.14);
}

.capture-pending-shimmer {
  position: absolute;
  inset: -20%;
  background: linear-gradient(120deg, rgba(255,255,255,0) 24%, rgba(255,255,255,0.6) 48%, rgba(255,255,255,0) 72%);
  transform: translateX(-100%);
  animation: capturePendingShimmer 1.8s ease-in-out infinite;
}

.capture-pending-browser-bar {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 8px 8px 6px;
}

.capture-pending-browser-bar span {
  width: 6px;
  height: 6px;
  border-radius: 999px;
  background: rgba(125, 149, 184, 0.62);
}

.capture-pending-body {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 4px 8px 0;
}

.capture-pending-line {
  height: 6px;
  border-radius: 999px;
  background: rgba(120, 162, 214, 0.22);
}

.capture-pending-line.w-72 { width: 72%; }
.capture-pending-line.w-64 { width: 64%; }
.capture-pending-line.w-48 { width: 48%; }

.capture-pending-badge {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 8px;
  padding: 4px 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.9);
  color: #225187;
  font-size: 10px;
  line-height: 1.2;
  font-weight: 700;
  text-align: center;
  box-shadow: 0 6px 12px rgba(37, 99, 235, 0.12);
}

.image-strip-item.is-capture-pending .image-strip-preview {
  cursor: default;
}

@keyframes capturePendingShimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.file-list-wrapper {
  display: flex;
  flex-wrap: nowrap;
  align-items: flex-start;
  gap: 8px;
  padding: 0;
  overflow-x: auto;
  scrollbar-width: none;
  -ms-overflow-style: none;
  margin-bottom: 0;
  transition: margin-bottom 0.3s ease;
  width: 100%;
  position: relative;
}

.file-list-container {
  position: relative;
  display: flex;
  align-items: flex-start;
  overflow: hidden;
  margin-bottom: 0;
  transition: margin-bottom 0.3s ease;
}

.file-list-container.has-files {
  margin-bottom: 2px;
}

:global(.upload-process-modal-wrap .ant-modal-content) {
  padding: 0;
  overflow: hidden;
  border-radius: 18px;
  box-shadow:
    0 24px 70px rgba(15, 23, 42, 0.22),
    0 8px 24px rgba(15, 23, 42, 0.12);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

:global(.upload-process-modal-wrap .ant-modal-body) {
  padding: 0;
}

:global(.upload-process-modal-wrap .ant-modal-close) {
  top: 18px;
  right: 18px;
}

:global(.upload-process-modal-wrap--drop .ant-modal-content) {
  transform-origin: 50% 100%;
  animation: uploadProcessDropEnter 0.52s cubic-bezier(0.16, 1, 0.3, 1) both;
}

:global(.upload-process-modal-wrap--drop .upload-process-header),
:global(.upload-process-modal-wrap--drop .upload-process-file-panel),
:global(.upload-process-modal-wrap--drop .upload-process-classification),
:global(.upload-process-modal-wrap--drop .upload-process-choice-grid),
:global(.upload-process-modal-wrap--drop .upload-process-actions) {
  animation: uploadProcessLayerEnter 0.42s cubic-bezier(0.16, 1, 0.3, 1) both;
}

:global(.upload-process-modal-wrap--drop .upload-process-header) {
  animation-delay: 0.08s;
}

:global(.upload-process-modal-wrap--drop .upload-process-file-panel) {
  animation-delay: 0.14s;
}

:global(.upload-process-modal-wrap--drop .upload-process-classification) {
  animation-delay: 0.18s;
}

:global(.upload-process-modal-wrap--drop .upload-process-choice-grid) {
  animation-delay: 0.22s;
}

:global(.upload-process-modal-wrap--drop .upload-process-actions) {
  animation-delay: 0.28s;
}

@keyframes uploadProcessDropEnter {
  0% {
    opacity: 0;
    transform: translateY(38px) scale(0.94);
  }

  58% {
    opacity: 1;
    transform: translateY(-4px) scale(1.01);
  }

  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes uploadProcessLayerEnter {
  0% {
    opacity: 0;
    transform: translateY(14px);
  }

  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

.upload-process-modal {
  position: relative;
  padding: 24px;
  background:
    linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
}

.upload-process-burst {
  position: absolute;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  border-radius: 18px;
  z-index: 0;
}

.upload-process-particle {
  position: absolute;
  left: 50%;
  bottom: 18px;
  width: 5px;
  height: 5px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.72);
  box-shadow: 0 0 14px rgba(37, 99, 235, 0.28);
  opacity: 0;
  transform:
    translate(-50%, 0)
    rotate(calc(var(--i) * 30deg))
    translateY(0)
    scale(0.45);
  animation: uploadProcessParticle 0.68s cubic-bezier(0.16, 1, 0.3, 1) both;
  animation-delay: calc(var(--i) * 0.014s);
}

.upload-process-particle:nth-child(3n) {
  background: rgba(20, 184, 166, 0.68);
  box-shadow: 0 0 14px rgba(20, 184, 166, 0.24);
}

.upload-process-particle:nth-child(4n) {
  width: 4px;
  height: 4px;
  background: rgba(96, 165, 250, 0.68);
}

@keyframes uploadProcessParticle {
  0% {
    opacity: 0;
    transform:
      translate(-50%, 0)
      rotate(calc(var(--i) * 30deg))
      translateY(0)
      scale(0.35);
  }

  18% {
    opacity: 1;
  }

  100% {
    opacity: 0;
    transform:
      translate(-50%, 0)
      rotate(calc(var(--i) * 30deg))
      translateY(-118px)
      scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  :global(.upload-process-modal-wrap--drop .ant-modal-content),
  :global(.upload-process-modal-wrap--drop .upload-process-header),
  :global(.upload-process-modal-wrap--drop .upload-process-modal),
  :global(.upload-process-modal-wrap--drop .upload-process-file-panel),
  :global(.upload-process-modal-wrap--drop .upload-process-classification),
  :global(.upload-process-modal-wrap--drop .upload-process-choice-grid),
  :global(.upload-process-modal-wrap--drop .upload-process-actions),
  .upload-process-particle {
    animation: none;
  }

  .upload-process-burst {
    display: none;
  }
}

.upload-process-header {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 14px;
  padding-right: 34px;
  margin-bottom: 20px;
}

.upload-process-icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  background:
    linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(20, 184, 166, 0.1));
  border: 1px solid rgba(37, 99, 235, 0.12);
  flex-shrink: 0;
}

.upload-process-icon :deep(svg) {
  width: 21px;
  height: 21px;
}

.upload-process-heading h3 {
  margin: 0;
  font-size: 18px;
  line-height: 1.35;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0;
}

.upload-process-heading p {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.5;
  color: #64748b;
}

.upload-process-file-panel {
  position: relative;
  z-index: 1;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid #e5e7eb;
  margin-bottom: 16px;
}

.upload-process-file-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
  font-size: 12px;
  color: #64748b;
}

.upload-process-file-head span:first-child {
  color: #111827;
  font-weight: 600;
}

.upload-process-file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 154px;
  overflow-y: auto;
  padding-right: 2px;
}

.upload-process-file-item {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 42px;
  padding: 9px 10px;
  border-radius: 11px;
  background: #f8fafc;
  border: 1px solid rgba(226, 232, 240, 0.9);
}

.upload-process-file-item img {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}

.upload-process-file-name {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.upload-process-file-size {
  flex-shrink: 0;
  font-size: 12px;
  color: #64748b;
}

.upload-process-choice-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.upload-process-choice {
  position: relative;
  display: flex;
  align-items: flex-start;
  min-height: 60px;
  padding: 10px 38px 10px 14px;
  text-align: left;
  border-radius: 15px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  cursor: pointer;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease,
    background 0.18s ease;
}

.upload-process-choice:hover {
  transform: translateY(-1px);
  border-color: #93c5fd;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.11);
}

.upload-process-choice.is-selected {
  border-color: #2563eb;
  background: linear-gradient(180deg, #eff6ff 0%, #ffffff 100%);
  box-shadow:
    0 12px 28px rgba(37, 99, 235, 0.14),
    inset 0 0 0 1px rgba(37, 99, 235, 0.08);
}

.upload-process-choice-mark {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 1.5px solid #cbd5e1;
  background: #ffffff;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.upload-process-choice.is-selected .upload-process-choice-mark {
  border-color: #2563eb;
  box-shadow: inset 0 0 0 5px #2563eb;
}

.upload-process-choice-main {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.upload-process-choice-title {
  font-size: 14px;
  line-height: 1.25;
  font-weight: 500;
  color: #303131;
}

.upload-process-choice-desc {
  font-size: 12px;
  line-height: 1.35;
  color: #64748b;
}

.upload-process-actions {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 18px;
}

.upload-process-cancel,
.upload-process-submit {
  min-width: 75px;
  height: 32px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 400;
  padding: 0 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    box-shadow 0.18s ease;
}

.upload-process-cancel {
  color: #1a1a1a;
  background: #e9e9e9;
  border: none;
}

.upload-process-cancel:hover {
  color: #1a1a1a;
  background: #dadada;
}

.upload-process-submit {
  color: #ffffff;
  background: #1677ff;
  border: none;
}

.upload-process-submit:hover {
  background: #4096ff;
}

.upload-process-cancel:disabled,
.upload-process-submit:disabled {
  cursor: not-allowed;
  opacity: 0.7;
}

.upload-process-classification {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  margin-top: 18px;
  margin-bottom: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.upload-process-classification-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.upload-process-classification-label {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  color: #475569;
  white-space: nowrap;
}

.upload-process-classification-hint {
  font-size: 12px;
  line-height: 1.4;
  color: #94a3b8;
  font-weight: 400;
}

.upload-process-classification-group {
  position: relative;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  padding: 2px;
  gap: 3px;
  background: rgba(241, 245, 249, 0.8);
  border-radius: 10px;
  box-shadow: inset 0 1px 3px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}

.upload-process-classification-indicator {
  position: absolute;
  top: 4px;
  left: 4px;
  height: calc(100% - 8px);
  width: calc(50% - 5px);
  background: #ffffff;
  border-radius: 7px;
  box-shadow:
    0 2px 8px rgba(37, 99, 235, 0.14),
    0 1px 3px rgba(15, 23, 42, 0.08);
  transition: transform 0.38s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease;
  will-change: transform;
  z-index: 0;
}

.upload-process-classification-group.is-empty .upload-process-classification-indicator {
  opacity: 0;
  transform: scale(0.9);
}

.upload-process-classification-group.is-internal .upload-process-classification-indicator {
  transform: translateX(calc(100% + 3px));
}

.upload-process-classification-btn {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  height: 30px;
  padding: 0 16px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 400;
  color: #64748b;
  transition: color 0.28s cubic-bezier(0.4, 0, 0.2, 1), transform 0.28s cubic-bezier(0.34, 1.56, 0.64, 1);
  user-select: none;
}

.upload-process-classification-btn:hover {
  color: #334155;
}

.upload-process-classification-btn.is-active {
  color: #2563eb;
  font-weight: 500;
  transform: scale(1.04);
}

.upload-process-classification-btn:active {
  transform: scale(0.96);
}

.file-classification-modal .upload-process-classification {
  margin-bottom: 0;
}

@media (max-width: 640px) {
  .upload-process-modal {
    padding: 20px;
  }

  .upload-process-choice-grid {
    grid-template-columns: 1fr;
  }

  .upload-process-classification {
    flex-direction: column;
    align-items: stretch;
  }

  .upload-process-classification-group {
    justify-content: space-between;
  }

  .upload-process-classification-btn {
    flex: 1;
  }

  .upload-process-actions {
    display: grid;
    grid-template-columns: 1fr 1fr;
  }
}

.image-strip-shell {
  min-height: 0;
  overflow: hidden;
  transition: max-height 0.32s cubic-bezier(0.22, 1, 0.36, 1), margin-bottom 0.32s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.24s ease;
  max-height: 0;
  opacity: 0;
  margin-bottom: 0;
}

.image-strip-shell.has-images {
  max-height: 120px;
  opacity: 1;
  margin-bottom: 6px;
}

.image-strip-container {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  overflow: hidden;
  border-radius: 14px;
}

.image-strip-list {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  overflow-x: auto;
  padding: 0 4px 2px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.image-strip-list::-webkit-scrollbar {
  display: none;
}

.image-strip-item {
  position: relative;
  flex: 0 0 auto;
  padding-top: 3px;
  overflow: visible;
}

.image-strip-item-move {
  transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}

.image-strip-item-enter-active,
.image-strip-item-leave-active {
  transition:
    opacity 0.28s ease,
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.28s ease;
}

.image-strip-item-enter-from,
.image-strip-item-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.92);
  filter: blur(4px);
}

.image-strip-item-enter-to,
.image-strip-item-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
  filter: blur(0);
}

.image-strip-item-leave-active {
  position: absolute;
}

.image-strip-list {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  overflow-x: auto;
  padding: 0 4px 2px;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.image-strip-list::-webkit-scrollbar {
  display: none;
}

.image-strip-item {
  position: relative;
  flex: 0 0 auto;
  padding-top: 3px;
  overflow: visible;
}

.image-strip-item-move {
  transition: transform 0.32s cubic-bezier(0.22, 1, 0.36, 1);
}

.image-strip-item-enter-active,
.image-strip-item-leave-active {
  transition:
    opacity 0.28s ease,
    transform 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.28s ease;
}

.image-strip-item-enter-from,
.image-strip-item-leave-to {
  opacity: 0;
  transform: translateY(10px) scale(0.92);
  filter: blur(4px);
}

.image-strip-item-enter-to,
.image-strip-item-leave-from {
  opacity: 1;
  transform: translateY(0) scale(1);
  filter: blur(0);
}

.image-strip-item-leave-active {
  position: absolute;
}

.image-strip-preview {
  position: relative;
  width: 72px;
  height: 72px;
  padding: 0;
  border: 1px solid rgba(99, 102, 241, 0.14);
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.06);
  transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
}

.image-strip-preview:hover {
  transform: translateY(-1px);
  border-color: rgba(99, 102, 241, 0.24);
}

.image-strip-preview:hover .image-strip-image {
  transform: scale(1.04);
}

.image-strip-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.18s ease;
}

.image-strip-uploading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 0 6px;
  background: rgba(15, 23, 42, 0.55);
  backdrop-filter: blur(1px);
}

.image-strip-uploading-text {
  font-size: 10px;
  line-height: 1.2;
  color: #ffffff;
  text-align: center;
  white-space: nowrap;
}

.image-strip-uploading-bar {
  display: block;
  width: 0;
  height: 3px;
  border-radius: 2px;
  background: #6366f1;
  transition: width 0.2s ease;
}

.image-strip-item.is-uploading .image-strip-preview {
  cursor: default;
}

.image-strip-item.is-uploading .image-strip-preview:hover {
  transform: none;
  border-color: rgba(99, 102, 241, 0.14);
}

.image-strip-item.is-uploading .image-strip-preview:hover .image-strip-image {
  transform: none;
}

.image-strip-remove {
  position: absolute;
  top: 0;
  right: -7px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 1px solid #ffffff;
  background: #000000;
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
  opacity: 0.95;
  z-index: 5;
  transition: transform 0.18s ease, opacity 0.18s ease, background 0.18s ease, color 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
}

.image-strip-remove:hover {
  transform: scale(1.08);
  opacity: 1;
  background: #ffffff;
  color: #000000;
  border-color: #ffffff;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.14);
}

.image-strip-remove :deep(svg) {
  width: 16px !important;
  height: 16px !important;
  display: block;
  flex-shrink: 0;
  transform: scale(0.7);
  transform-origin: center;
}

.image-strip-remove:hover :deep(svg) {
  transform: scale(0.7);
}

.image-strip-container::before,
.image-strip-container::after {
  content: '';
  position: absolute;
  top: 0;
  bottom: 0;
  width: 44px;
  z-index: 3;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.image-strip-container::before {
  left: 0;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.96) 0%, rgba(255, 255, 255, 0) 100%);
}

.image-strip-container::after {
  right: 0;
  background: linear-gradient(270deg, rgba(255, 255, 255, 0.96) 0%, rgba(255, 255, 255, 0) 100%);
}

.image-strip-container:has(.image-strip-scroll-btn--left.visible)::before,
.image-strip-container:has(.image-strip-scroll-btn--right.visible)::after {
  opacity: 1;
}

.image-strip-list {
  scroll-behavior: smooth;
  scroll-padding-inline: 42px;
  padding: 0 4px;
  box-sizing: border-box;
}

.image-strip-scroll-btn {
  position: absolute;
  top: 50%;
  z-index: 6;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 1px solid rgba(226, 232, 240, 0.72);
  border-radius: 9999px;
  background: rgba(255, 255, 255, 0.88);
  color: #475569;
  box-shadow:
    0 8px 18px rgba(15, 23, 42, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  cursor: pointer;
  opacity: 0;
  pointer-events: none;
  transform: translateY(-50%) scale(0.92);
  transition:
    opacity 0.2s ease,
    transform 0.2s ease,
    box-shadow 0.2s ease,
    color 0.2s ease;
}

.image-strip-scroll-btn.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(-50%) scale(1);
}

.image-strip-scroll-btn:hover {
  color: #2563eb;
  transform: translateY(-50%) scale(1.05);
  box-shadow:
    0 10px 22px rgba(37, 99, 235, 0.16),
    0 8px 18px rgba(15, 23, 42, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.88);
}

.image-strip-scroll-btn--left {
  left: 7px;
}

.image-strip-scroll-btn--right {
  right: 7px;
}

.image-strip-scroll-btn svg {
  display: block;
}

.upload-btn-wrapper {
  display: inline-flex;
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin-right: 0;
}

.upload-btn-enter-active {
  transition: 
    width 0.3s cubic-bezier(0.2, 0, 0, 1),
    margin-right 0.3s cubic-bezier(0.2, 0, 0, 1),
    opacity 0.2s 0.1s ease-out,
    transform 0.2s 0.1s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.upload-btn-leave-active {
  transition: 
    width 0.3s 0.05s cubic-bezier(0.2, 0, 0, 1),
    margin-right 0.3s 0.05s cubic-bezier(0.2, 0, 0, 1),
    opacity 0.1s ease-in,
    transform 0.1s ease-in;
}

.upload-btn-enter-from,
.upload-btn-leave-to {
  width: 0 !important;
  margin-right: -16px !important;
  opacity: 0;
  transform: scale(0.5);
}

.upload-btn-enter-to,
.upload-btn-leave-from {
  width: 40px;
  margin-right: 0;
  opacity: 1;
  transform: scale(1);
}

.scroll-mask {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 40px;
  pointer-events: none;
  z-index: 10;
  transition: opacity 0.2s ease;
  opacity: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.scroll-mask.visible {
  opacity: 1;
  pointer-events: auto;
}

.scroll-btn {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: white;
  border: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
  color: #64748b;
  transition: all 0.2s;
  z-index: 11;
  margin-top: -4px;
}

.scroll-btn svg {
  width: 10px;
  height: 10px;
}

.scroll-mask:hover .scroll-btn {
  border-color: #cbd5e1;
  color: #3b82f6;
  box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
  transform: scale(1.1);
}

.mask-left {
  left: 0;
  background: linear-gradient(to right, rgba(255,255,255,1) 20%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 100%);
  justify-content: flex-start;
  padding-left: 2px;
}

.mask-right {
  right: 0;
  background: linear-gradient(to left, rgba(255,255,255,1) 20%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 100%);
  justify-content: flex-end;
  padding-right: 2px;
}

.file-list-wrapper::-webkit-scrollbar {
  display: none;
}

.file-preview-card {
    position: relative !important;
    display: flex;
    align-items: center;
    padding: 6px;
    gap: 3px;
    background: #ffffff;
    border-radius: 12px;
    border: 1px solid rgba(0, 0, 0, 0.06);
    width: fit-content;
    max-width: 200px;
    margin-left: 2px;
    overflow: hidden !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.02);
    flex-shrink: 0;
}

.file-preview-card.is-uploading {
    background: #f5f5f5;
}

/* 图片卡片已移动到独立区域，避免撑高输入框 */

.progress-bar-bg {
    position: absolute !important;
    top: 0;
    left: 0;
    height: 100%;
    background-color: rgba(0, 0, 0, 0.06);
    transition: width 0.3s ease;
    z-index: 0 !important;
}

.file-preview-card > * {
    position: relative;
    z-index: 1;
}

.upload-status {
    font-size: 10px;
    color: #9ca3af;
    line-height: 1.2;
}

.no-animation-button:deep(.ant-btn) {
  transition: none !important;
}

.no-animation-button:deep(.ant-btn):hover,
.no-animation-button:deep(.ant-btn):focus,
.no-animation-button:deep(.ant-btn):active {
  transition: none !important;
  transform: none !important;
}

.no-animation-button:deep(.ant-btn-loading-icon) {
  animation: loadingCircle 1s infinite linear !important;
}

.no-animation-button:deep(.ant-spin-dot) {
  animation: antSpinMove 1s infinite linear alternate !important;
}

.no-animation-button:deep(.ant-spin-dot-item) {
  animation: antSpinRotate 1.2s infinite ease-in-out !important;
}

.selection-export-btn :deep(.export-button) {
  width: auto;
  height: 32px;
  padding: 6px 12px;
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.03) 0%, rgba(0, 0, 0, 0.05) 100%);
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  gap: 6px;
}

.selection-export-btn :deep(.export-button):hover {
  background: linear-gradient(135deg, #ebebeb 0%, #ebebeb 100%);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1),
  inset 0 1px 0 rgba(255, 255, 255, 0.2);
}

.selection-export-btn :deep(.export-button):active {
  transform: translateY(0);
  background: linear-gradient(135deg, #e0e0e0 0%, #e0e0e0 100%);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1),
  inset 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.1s ease;
}

.selection-export-btn.disabled :deep(.export-button) {
  opacity: 0.5;
  cursor: not-allowed;
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.02) 0%, rgba(0, 0, 0, 0.03) 100%);
  transform: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03),
  inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.selection-export-btn.disabled :deep(.export-button):hover {
  background: linear-gradient(135deg, rgba(0, 0, 0, 0.02) 0%, rgba(0, 0, 0, 0.03) 100%);
  transform: none;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03),
  inset 0 1px 0 rgba(255, 255, 255, 0.05);
}

.agent-button {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  height: 40px;
  width: 40px;
  min-width: 40px;
  max-width: 40px;
  border-radius: 12px;
  background:
    radial-gradient(circle at 24% 26%, rgba(255, 255, 255, 0.5), transparent 34%),
    linear-gradient(135deg, #ffb56b 0%, #ff8f97 42%, #8d79ff 76%, #5d65f6 100%);
  transition:
    width 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    min-width 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    max-width 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    padding 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.28s ease,
    box-shadow 0.28s ease,
    filter 0.28s ease;
  padding: 0 10px;
  margin: 0;
  position: relative;
  overflow: hidden;
  cursor: pointer;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  color: #ffffff;
  box-shadow:
    0 10px 24px rgba(15, 23, 42, 0.12),
    0 3px 10px rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px) saturate(1.1);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
  will-change: width, min-width, max-width, transform;
}

.agent-button:hover {
  transform: translateY(-1px);
  box-shadow:
    0 14px 30px rgba(15, 23, 42, 0.16),
    0 5px 14px rgba(255, 255, 255, 0.1);
  filter: brightness(1.03);
}

.agent-content {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  width: 100%;
  height: 100%;
  position: relative;
  z-index: 1;
  gap: 0;
  transition: gap 0.36s cubic-bezier(0.22, 1, 0.36, 1);
}

.agent-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.agent-icon-img {
  width: 20px;
  height: 20px;
  display: block;
  flex-shrink: 0;
  object-fit: contain;
  image-rendering: auto;
  filter: brightness(0) invert(1);
}

/* 当选中了智能体时显示蓝色样式并添加弹性动画 */
.agent-button.has-selected-agent {
  width: 143px;
  min-width: 143px;
  max-width: 143px;
  padding: 0 12px;
}

.agent-button.has-selected-agent:hover {
  box-shadow:
    0 16px 34px rgba(15, 23, 42, 0.18),
    0 6px 16px rgba(255, 255, 255, 0.12);
}

.kb-toggle-content {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex: 1;
  min-width: 0;
  height: 100%;
  gap: 8px;
}

.kb-toggle-control {
  display: inline-flex;
  align-items: stretch;
  width: 155px;
  min-width: 155px;
  max-width: 155px;
  position: relative;
  isolation: isolate;
  transition: filter 0.38s ease;
  transform-origin: left center;
  animation: kbToggleControlEnter 0.36s cubic-bezier(0.22, 1, 0.36, 1) both;
}

@keyframes kbToggleControlEnter {
  from {
    opacity: 0;
    transform: translate3d(-6px, 3px, 0) scale(0.96);
  }

  to {
    opacity: 1;
    transform: translate3d(0, 0, 0) scale(1);
  }
}

/* 非首次挂载的实例（状态切换/新对话重建）不重播入场动画 */
.kb-toggle-control--no-entrance {
  animation: none;
}

@media (prefers-reduced-motion: reduce) {
  .kb-toggle-control,
  .kb-toggle-icon-shell--loading,
  .kb-toggle-loading-spinner {
    animation: none;
  }
}

.kb-toggle-control--selected {
  filter: saturate(1.04);
}

/* 空态（细腻虚线）：确认无可用知识库时的引导样式，点击跳转知识库页面创建。
   仅外框保留一条柔和虚线；图标壳回归干净实底，避免"双重虚线"的杂乱感 */
.kb-toggle-control--empty .kb-toggle-button {
  border: 1px dashed rgba(110, 124, 148, 0.42);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(244, 247, 252, 0.72));
  box-shadow: none;
  cursor: pointer;
}

.kb-toggle-control--empty .kb-toggle-button::before {
  opacity: 0;
}

/* 空态按钮可点击：hover 时虚线微加深、背景提亮，提示可跳转创建 */
.kb-toggle-control--empty .kb-toggle-button:hover {
  border-color: rgba(110, 124, 148, 0.62) !important;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.94), rgba(240, 244, 250, 0.94)) !important;
  box-shadow: 0 6px 18px rgba(96, 108, 130, 0.12) !important;
}

.kb-toggle-control--empty .kb-toggle-icon-shell {
  background: rgba(255, 255, 255, 0.9);
  border: 1px dashed rgba(110, 124, 148, 0.35);
  box-shadow: none;
}

/* 空态加号图标 hover 时保持静止，不跟随默认 .kb-icon 的放大，避免视觉位移 */
.kb-toggle-control--empty .kb-toggle-button:hover .kb-icon-plus,
.kb-toggle-control--empty .kb-toggle-button--open .kb-icon-plus {
  transform: none;
}

.kb-toggle-control--empty .kb-toggle-idle-text {
  color: rgba(96, 108, 130, 0.9);
  letter-spacing: 0.3px;
}

/* 首次加载检测中（尚无可用性快照）：中性灰加载态，检查完成后落到真实状态，
   避免先渲染"启用检索增强"再跳变为空态；与蓝色"开启中"、虚线空态区分 */
.kb-toggle-control--checking .kb-toggle-button {
  cursor: wait;
  border: 1px dashed rgba(110, 124, 148, 0.42);
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.72), rgba(244, 247, 252, 0.72));
  box-shadow: none;
}

.kb-toggle-control--checking .kb-toggle-button::before {
  opacity: 0;
}

.kb-toggle-control--checking .kb-toggle-icon-shell {
  border: 1px dashed rgba(120, 132, 156, 0.35);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: none;
}

.kb-toggle-control--checking .kb-toggle-loading-spinner {
  border-color: rgba(120, 132, 156, 0.22);
  border-top-color: #8a96ad;
  border-right-color: #9aa5ba;
}

.kb-toggle-control--checking .kb-toggle-idle-text {
  color: rgba(110, 122, 144, 0.92);
}

.kb-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  transition: transform 0.25s ease, color 0.25s ease, opacity 0.25s ease;
}

.kb-toggle-button {
  display: flex;
  align-items: center;
  height: 40px !important;
  width: 100%;
  min-width: 155px;
  max-width: 155px;
  padding: 0 6px 0 6px;
  margin: 0;
  border-radius: 12px;
  border: 1px solid rgba(90, 114, 255, 0.14);
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.92), rgba(244, 247, 255, 0.96)),
    radial-gradient(circle at top left, rgba(113, 96, 255, 0.16), transparent 56%);
  box-shadow:
    0 12px 32px rgba(81, 108, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  transition:
    box-shadow 0.5s cubic-bezier(0.34, 1.15, 0.64, 1),
    border-color 0.5s ease,
    transform 0.5s cubic-bezier(0.34, 1.15, 0.64, 1),
    background 0.5s ease,
    padding 0.5s cubic-bezier(0.34, 1.15, 0.64, 1);
  position: relative;
  overflow: hidden;
  justify-content: flex-start;
  box-sizing: border-box !important;
  cursor: pointer;
  outline: none;
  font-family: inherit;
  font-size: 14px;
  color: inherit;
  text-align: left;
}

.kb-toggle-button::before {
  content: '';
  position: absolute;
  inset: auto;
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.45s ease;
}

.kb-toggle-button > .kb-toggle-content {
  position: relative;
  z-index: 1;
}

.kb-toggle-button::before {
  width: 88px;
  height: 88px;
  right: -34px;
  top: -36px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(116, 110, 255, 0.22) 0%, rgba(116, 110, 255, 0) 72%);
  opacity: 0.9;
}

.kb-toggle-button:hover {
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(239, 244, 255, 0.98)),
    radial-gradient(circle at top left, rgba(113, 96, 255, 0.22), transparent 60%) !important;
  border-color: rgba(89, 130, 255, 0.28);
  box-shadow:
    0 16px 36px rgba(81, 108, 255, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
}

.kb-toggle-button--loading,
.kb-toggle-button--loading:hover {
  cursor: wait;
  border-color: rgba(89, 130, 255, 0.3);
  background:
    linear-gradient(135deg, rgba(250, 252, 255, 0.98), rgba(238, 244, 255, 0.98)),
    radial-gradient(circle at top left, rgba(113, 96, 255, 0.22), transparent 60%) !important;
  box-shadow:
    0 14px 34px rgba(81, 108, 255, 0.13),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.kb-toggle-button--open {
  box-shadow:
    0 18px 40px rgba(78, 99, 255, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.95);
}

.kb-toggle-icon-shell {
  position: relative;
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.88), rgba(240, 244, 255, 0.96));
  border: 1px solid rgba(105, 123, 182, 0.18);
  box-shadow: 0 6px 14px rgba(68, 90, 156, 0.08);
  transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, transform 0.5s cubic-bezier(0.34, 1.15, 0.64, 1);
}

.kb-toggle-icon-shell--selected {
  /* 参考 .history-rail 的柔和背景：白底 + 右上蓝 / 左下紫淡径向光，弱化 AI 感 */
  background:
    radial-gradient(circle at 100% 0%, rgba(59, 130, 246, 0.26) 0%, rgba(59, 130, 246, 0.12) 45%, rgba(59, 130, 246, 0) 72%),
    radial-gradient(circle at 0% 100%, rgba(124, 58, 237, 0.22) 0%, rgba(124, 58, 237, 0.1) 45%, rgba(124, 58, 237, 0) 72%),
    #ffffff;
  border-color: rgba(99, 102, 241, 0.26);
  box-shadow: 0 8px 18px rgba(81, 108, 255, 0.14), inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition: background 0.3s ease, border-color 0.3s ease, box-shadow 0.3s ease, transform 0.3s ease;
}

.kb-toggle-icon-shell--loading {
  border-color: rgba(91, 122, 255, 0.28);
  background: linear-gradient(145deg, rgba(239, 244, 255, 0.98), rgba(228, 237, 255, 0.98));
  box-shadow: 0 8px 18px rgba(81, 108, 255, 0.15);
  animation: kbToggleLoadingPulse 1.25s ease-in-out infinite;
}

.kb-toggle-loading-spinner {
  width: 17px;
  height: 17px;
  border: 2px solid rgba(91, 111, 190, 0.22);
  border-top-color: #637bff;
  border-right-color: #7967ff;
  border-radius: 50%;
  box-sizing: border-box;
  animation: kbToggleLoadingSpin 0.72s linear infinite;
}

@keyframes kbToggleLoadingSpin {
  to {
    transform: rotate(360deg);
  }
}

@keyframes kbToggleLoadingPulse {
  0%, 100% {
    transform: scale(1);
  }

  50% {
    transform: scale(1.05);
  }
}

.kb-toggle-button:hover .kb-toggle-icon-shell,
.kb-toggle-button--open .kb-toggle-icon-shell {
  box-shadow: 0 10px 18px rgba(68, 90, 156, 0.12);
}

.kb-toggle-button:hover .kb-toggle-icon-shell--selected,
.kb-toggle-button--open .kb-toggle-icon-shell--selected {
  box-shadow: 0 12px 22px rgba(94, 101, 255, 0.22);
}

.kb-toggle-button:hover .kb-icon,
.kb-toggle-button--open .kb-icon {
  transform: scale(1.03);
}

/* 选中后悬浮不再放大/移动 */
.kb-toggle-button--selected:hover .kb-icon,
.kb-toggle-button--selected.kb-toggle-button--open .kb-icon {
  transform: scale(1);
}

.kb-toggle-button--selected:hover .kb-toggle-icon-shell,
.kb-toggle-button--selected.kb-toggle-button--open .kb-toggle-icon-shell {
  transform: translateY(0);
}

.kb-toggle-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: stretch;
  justify-content: center;
  gap: 3px;
  max-width: 210px;
  transform-origin: left center;
  transition:
    opacity 0.35s ease,
    transform 0.5s cubic-bezier(0.34, 1.15, 0.64, 1),
    max-width 0.5s cubic-bezier(0.34, 1.15, 0.64, 1);
}

.kb-toggle-button--selected {
  justify-content: flex-start;
  width: 42px;
  min-width: 42px;
  max-width: 42px;
  padding: 0 6px;
  border-radius: 12px 0 0 12px;
  border-right: none;
  border-color: rgba(83, 118, 255, 0.3);
  background:
    linear-gradient(135deg, rgba(243, 246, 255, 0.98), rgba(236, 244, 255, 0.98)),
    radial-gradient(circle at top left, rgba(84, 140, 255, 0.22), transparent 58%);
  transition:
    box-shadow 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.42s ease,
    transform 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    background 0.42s ease,
    width 0.48s cubic-bezier(0.2, 0.9, 0.2, 1),
    min-width 0.48s cubic-bezier(0.2, 0.9, 0.2, 1),
    max-width 0.48s cubic-bezier(0.2, 0.9, 0.2, 1),
    padding 0.42s cubic-bezier(0.22, 1, 0.36, 1);
}

.kb-toggle-button--selected .kb-toggle-content {
  justify-content: center;
  gap: 0;
}

.kb-toggle-button--selected:hover {
  border-color: rgba(70, 125, 255, 0.4);
  box-shadow:
    0 20px 42px rgba(73, 110, 255, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
  transform: translateY(0);
}

.kb-toggle-button--selected .kb-toggle-copy {
  max-width: 0;
  opacity: 0;
  transform: translateX(-6px) scale(0.98);
  transition:
    opacity 0.26s ease,
    transform 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    max-width 0.4s cubic-bezier(0.2, 0.9, 0.2, 1);
}

.kb-toggle-server-text {
  display: block;
  width: 100%;
  min-width: 0;
  max-width: 100%;
  font-size: 13px;
  font-weight: 600;
  line-height: 1.15;
  color: #17316b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-align: left;
}

.kb-toggle-selector-text {
  width: 100%;
  min-width: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  position: relative;
  z-index: 1;
}

.kb-toggle-active-panel,
.kb-toggle-idle-panel {
  width: 100%;
  display: flex;
  align-items: center;
  min-width: 0;
  box-sizing: border-box;
}

.kb-toggle-active-panel {
  gap: 8px;
  padding: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  min-height: 28px;
  height: 100%;
}

.kb-toggle-active-copy {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  transform-origin: left center;
  opacity: 0;
  transform: translateX(-6px) scale(0.98);
  transition: transform 0.5s cubic-bezier(0.34, 1.15, 0.64, 1), opacity 0.35s ease;
  will-change: transform, opacity;
  height: 100%;
}

.kb-toggle-idle-panel {
  min-height: 28px;
}

.kb-toggle-active-slot {
  display: flex;
  min-width: 0;
  overflow: hidden;
  width: 0;
  max-width: 0;
  opacity: 0;
  margin-left: -10px;
  transform: scale(0.95) translateX(-5px);
  transform-origin: left center;
  filter: blur(6px);
  pointer-events: none;
  transition:
    opacity 0.35s ease,
    margin-left 0.5s cubic-bezier(0.34, 1.15, 0.64, 1),
    transform 0.5s cubic-bezier(0.34, 1.15, 0.64, 1),
    filter 0.4s ease;
}

.kb-toggle-active-wrapper {
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 100%;
  height: 40px;
  margin-left: -1px;
  padding: 0 8px 0 8px;
  border: 1px solid rgba(83, 118, 255, 0.3);
  border-radius: 0 12px 12px 0;
  background:
    linear-gradient(135deg, rgba(243, 246, 255, 0.98), rgba(236, 244, 255, 0.98)),
    radial-gradient(circle at top left, rgba(84, 140, 255, 0.22), transparent 58%);
  box-shadow:
    0 12px 32px rgba(81, 108, 255, 0.08),
    inset 0 1px 0 rgba(255, 255, 255, 0.82);
  box-sizing: border-box;
  cursor: pointer;
  transition:
    box-shadow 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.42s ease,
    background 0.42s ease,
    transform 0.42s cubic-bezier(0.22, 1, 0.36, 1);
  outline: none;
  font-family: inherit;
  position: relative;
  overflow: hidden;
  transform-origin: left center;
  width: 100%;
}

.kb-toggle-dropdown-icon {
  flex-shrink: 0;
  transition: transform 0.28s ease;
}

.kb-toggle-active-wrapper::before {
  content: '';
  position: absolute;
  inset: auto;
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.45s ease;
}

.kb-toggle-active-wrapper::before {
  width: 88px;
  height: 88px;
  right: -34px;
  top: -36px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(116, 110, 255, 0.22) 0%, rgba(116, 110, 255, 0) 72%);
  opacity: 0.9;
}

.kb-toggle-active-wrapper:hover,
.kb-toggle-control--open .kb-toggle-active-wrapper {
  border-color: rgba(70, 125, 255, 0.4);
  box-shadow:
    0 20px 42px rgba(73, 110, 255, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.92);
}

.kb-toggle-control--selected .kb-toggle-button::before,
.kb-toggle-control--selected .kb-toggle-active-wrapper::before {
  transform: scale(1.05) translate3d(0, -2px, 0);
}

.kb-toggle-control--selected .kb-toggle-active-copy {
  transform: translateX(0);
  opacity: 1;
  transition: transform 0.36s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.28s ease;
}

.kb-toggle-control--selected .kb-toggle-active-slot {
  width: calc(155px - 42px + 1px);
  max-width: calc(155px - 42px + 1px);
  opacity: 1;
  margin-left: 0;
  transform: scale(1) translateX(0);
  filter: blur(0);
  pointer-events: auto;
  transition:
    width 0.4s cubic-bezier(0.2, 0.9, 0.2, 1),
    max-width 0.4s cubic-bezier(0.2, 0.9, 0.2, 1),
    opacity 0.28s ease,
    margin-left 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    filter 0.3s ease;
}

.kb-toggle-idle-text {
  font-size: 12px;
  color: rgba(84, 96, 137, 0.78);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-left: 8px;
}

.kb-toggle-content .server-info {
  width: 100%;
}

.mcp-server-icon {
  width: 23px;
  height: 23px;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.server-info {
  display: flex;
  align-items: center;
  min-width: 0;
  max-width: 0;
  overflow: hidden;
  opacity: 0;
  margin-left: 0;
  transform: translateX(-8px);
  transform-origin: left center;
  pointer-events: none;
  transition:
    max-width 0.42s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.24s ease,
    margin-left 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    transform 0.36s cubic-bezier(0.22, 1, 0.36, 1);
}

.agent-button.has-selected-agent .agent-content {
  gap: 8px;
}

.server-info.is-visible {
  max-width: 104px;
  opacity: 1;
  margin-left: 2px;
  transform: translateX(0);
  pointer-events: auto;
}

.divider {
  width: 1px;
  height: 15px;
  background-color: rgba(255, 255, 255, 0.42);
  margin-left: 0;
  margin-right: 8px;
  flex-shrink: 0;
}

.server-text {
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  white-space: nowrap;
  letter-spacing: -0.01em;
  text-shadow: 0 1px 8px rgba(255, 255, 255, 0.22);
  flex-shrink: 0;
}

.agent-name {
  height: 18px;
  display: flex;
  align-items: center;
  padding: 0 8px;
  font-size: 12px;
  font-weight: 600;
  color: #1890ff;
  background-color: #e6f4ff;
  border: 1px solid #80c4ff;
  border-radius: 10px;
  max-width: 240px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.input-agent-shell {
  width: calc(100% - 40px);
  max-width: 780px;
  min-width: 280px;
  margin: 0 auto;
  position: relative;
  z-index: 2;
  pointer-events: none;
  box-sizing: border-box;
  padding: 0;
  border: 1px solid transparent;
  border-radius: 20px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, rgba(247, 249, 253, 0) 100%);
  box-shadow: 0 0 0 rgba(149, 162, 201, 0);
  transition:
    padding 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.3s ease,
    border-radius 0.32s cubic-bezier(0.22, 1, 0.36, 1),
    background 0.38s ease,
    box-shadow 0.42s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.input-agent-shell .input-bar-outer {
  pointer-events: auto;
  width: 100%;
  max-width: none;
  min-width: 0;
  margin: 0;
  border-radius: 24px;
  border: 1px solid transparent;
  box-shadow: 0 2px 10px rgba(76, 94, 136, 0.06), 0 0 1px 1px rgba(255, 255, 255, 0.45) inset;
  transition:
    border-radius 0.34s cubic-bezier(0.22, 1, 0.36, 1),
    border-color 0.28s ease,
    box-shadow 0.34s ease;
}

/* Thin, feathered underglow follows the composer width in both chat modes. */
.input-agent-shell::after {
  content: '';
  position: absolute;
  z-index: -1;
  left: -6px;
  right: -6px;
  bottom: -10px;
  height: 18px;
  border-radius: 20px;
  background: linear-gradient(90deg,
    rgba(120, 168, 255, 0) 0%,
    rgba(120, 168, 255, 0.24) 5%,
    rgba(102, 142, 246, 0.38) 36%,
    rgba(137, 128, 239, 0.32) 57%,
    rgba(139, 189, 255, 0.28) 95%,
    rgba(139, 189, 255, 0) 100%);
  filter: blur(7px);
  pointer-events: none;
}

.input-agent-shell::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  pointer-events: none;
  opacity: 0;
  background: linear-gradient(
    115deg,
    rgba(255, 255, 255, 0) 18%,
    rgba(255, 255, 255, 0.18) 34%,
    rgba(255, 255, 255, 0.42) 48%,
    rgba(255, 255, 255, 0.08) 58%,
    rgba(255, 255, 255, 0) 72%
  );
  transform: translateX(-48%) skewX(-14deg);
  transition: opacity 0.28s ease;
}

:global([data-theme='dark']) .input-agent-shell::after {
  opacity: 0.65;
}

.input-agent-shell.is-agent-mode {
  padding: 7px 8px 8px;
  border-radius: 22px;
  border: 1px solid rgba(190, 202, 234, 0.34);
  background:
    radial-gradient(circle at 12% 88%, rgba(255, 172, 132, 0.12), transparent 44%),
    radial-gradient(circle at 88% 86%, rgba(120, 113, 255, 0.14), transparent 48%),
    linear-gradient(180deg, rgba(239, 245, 255, 0.96) 0%, rgba(229, 237, 251, 0.98) 100%);
  box-shadow: 0 10px 24px rgba(130, 146, 203, 0.11);
  backdrop-filter: blur(8px) saturate(1.06);
  -webkit-backdrop-filter: blur(8px) saturate(1.06);
  overflow: visible;
}

.input-agent-shell.is-agent-mode .input-bar-outer {
  border-radius: 16px;
  border: 1px solid rgba(188, 201, 236, 0.42);
  box-shadow: none;
}

/* ---- 智能体初始化中：壳体微呼吸 + 流光扫过 + 底晕呼吸 ---- */
.input-agent-shell.is-agent-mode.is-agent-init {
  animation: agent-init-shell-breathe 2.6s cubic-bezier(0.37, 0, 0.22, 1) infinite;
  will-change: transform, box-shadow, border-color;
}

.input-agent-shell.is-agent-mode.is-agent-init::before {
  opacity: 1;
  animation: agent-init-shell-sheen 2.8s cubic-bezier(0.37, 0, 0.22, 1) infinite;
}

.input-agent-shell.is-agent-mode.is-agent-init::after {
  animation: agent-init-underglow 2.25s ease-in-out infinite;
}

.input-agent-shell.is-agent-mode.is-agent-init .input-bar-outer {
  animation: agent-init-inner-breathe 2.6s cubic-bezier(0.37, 0, 0.22, 1) infinite;
}

@keyframes agent-init-shell-breathe {
  0%, 100% {
    border-color: rgba(190, 202, 234, 0.34);
    box-shadow: 0 10px 24px rgba(130, 146, 203, 0.11);
  }
  50% {
    border-color: rgba(176, 194, 240, 0.56);
    box-shadow:
      0 14px 32px rgba(122, 138, 203, 0.16),
      0 0 0 1px rgba(255, 255, 255, 0.26) inset;
  }
}

@keyframes agent-init-shell-sheen {
  0% {
    transform: translateX(-58%) skewX(-14deg);
    opacity: 0;
  }
  16% {
    opacity: 0.72;
  }
  52% {
    opacity: 0.34;
  }
  100% {
    transform: translateX(58%) skewX(-14deg);
    opacity: 0;
  }
}

@keyframes agent-init-inner-breathe {
  0%, 100% {
    border-color: rgba(188, 201, 236, 0.42);
    box-shadow: none;
  }
  50% {
    border-color: rgba(165, 184, 238, 0.74);
    box-shadow:
      0 0 0 1px rgba(255, 255, 255, 0.54) inset,
      0 0 0 3px rgba(139, 156, 236, 0.08);
  }
}

@keyframes agent-init-underglow {
  0%, 18% { opacity: 0.45; }
  50% { opacity: 1; }
  82%, 100% { opacity: 0.45; }
}

/* ---- banner 内初始化状态位：使用智能体图标动画 ---- */
/* grid 叠放同一单元格，让「初始化中」与「退出智能体模式」在原位交叉淡入淡出，避免宽度跳动 */
/* 两个状态锁定同一高度（以「退出智能体模式」为准），切换时 banner 不再发生高度变化 */
.agent-mode-banner-right {
  --agent-banner-action-h: 16px;
  display: grid;
  align-items: center;
  justify-items: end;
  flex-shrink: 0;
  height: var(--agent-banner-action-h);
}

.agent-mode-banner-right > * {
  grid-area: 1 / 1;
  height: var(--agent-banner-action-h);
}

.agent-state-swap-enter-active,
.agent-state-swap-leave-active {
  transition:
    opacity 0.24s ease,
    transform 0.24s cubic-bezier(0.22, 1, 0.36, 1);
}

.agent-state-swap-enter-from {
  opacity: 0;
  transform: translateY(3px);
}

.agent-state-swap-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

.agent-state-swap-leave-active {
  pointer-events: none;
}

@media (prefers-reduced-motion: reduce) {
  .agent-state-swap-enter-active,
  .agent-state-swap-leave-active {
    transition: opacity 0.12s linear;
  }

  .agent-state-swap-enter-from,
  .agent-state-swap-leave-to {
    transform: none;
  }
}

.agent-mode-banner-right .agent-init-state {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  line-height: 14px;
  color: #8a93a8;
  flex-shrink: 0;
}

/* 图标尺寸跟随锁定高度，避免撑高 banner */
.agent-init-icon {
  width: var(--agent-banner-action-h);
  height: var(--agent-banner-action-h);
  display: block;
  flex-shrink: 0;
}

@media (prefers-reduced-motion: reduce) {
  .input-agent-shell.is-agent-mode.is-agent-init,
  .input-agent-shell.is-agent-mode.is-agent-init .input-bar-outer,
  .input-agent-shell.is-agent-mode.is-agent-init::before,
  .input-agent-shell.is-agent-mode.is-agent-init::after {
    animation: none;
  }

  .input-agent-shell.is-agent-mode.is-agent-init::before {
    opacity: 0.2;
  }
}

.agent-mode-banner-shell {
  display: grid;
  grid-template-rows: 0fr;
  opacity: 0;
  pointer-events: none;
  overflow: hidden;
  transition:
    grid-template-rows 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.24s ease;
}

.agent-mode-banner-shell.is-visible {
  grid-template-rows: 1fr;
  opacity: 1;
  pointer-events: auto;
}

.agent-mode-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  padding: 2px 8px 6px;
  margin: 0;
  min-height: 20px;
  pointer-events: none;
  transform-origin: top center;
  transform: translateY(-3px);
  opacity: 0;
  transition:
    transform 0.36s cubic-bezier(0.22, 1, 0.36, 1),
    opacity 0.24s ease;
  overflow: clip;
  margin-top: -2px;
}

.agent-mode-banner-shell.is-visible .agent-mode-banner {
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}

.agent-mode-banner-left {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}

.agent-mode-banner-icon {
  width: 15px;
  height: 15px;
  opacity: 0.62;
  flex-shrink: 0;
  display: block;
  object-fit: contain;
  transform: translateY(0.7px);
  transition: opacity 0.24s ease;
}

.agent-mode-banner-title {
  font-size: 12px;
  color: #8a93a8;
  font-weight: 400;
  line-height: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.24s ease;
  display: inline-flex;
  align-items: center;
}

.agent-mode-exit-btn {
  border: none;
  background: transparent;
  color: #8a93a8;
  font-size: 12px;
  font-weight: 400;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  transition: color 0.2s ease;
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.agent-mode-exit-btn:hover {
  color: #707d99;
}

.agent-mode-exit-icon {
  display: block;
  width: 12px;
  height: 12px;
  flex-shrink: 0;
  opacity: 0.95;
  transition: filter 0.2s ease;
}

.agent-mode-exit-btn:hover .agent-mode-exit-icon {
  filter: brightness(0.85);
}

.input-agent-shell.is-agent-mode .agent-mode-banner-icon {
  opacity: 0.8;
}

.input-agent-shell.is-agent-mode .agent-mode-banner-title {
  color: #7983a0;
  line-height: 15px;
}

.input-stack-wrapper {
  flex-direction: column;
  align-items: center;
}

/* 文件预览卡片进出场动画 - 追求极致丝滑与华丽感 */
.file-preview-card-move {
  transition: transform 0.5s cubic-bezier(0.35, 1.35, 0.35, 1);
}

.file-preview-card-enter-active {
  transition: 
    opacity 0.5s cubic-bezier(0.2, 0.8, 0.2, 1),
    transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1),
    filter 0.5s ease-out,
    max-height 0.5s cubic-bezier(0.2, 0.8, 0.2, 1),
    margin-bottom 0.5s cubic-bezier(0.2, 0.8, 0.2, 1),
    padding 0.5s cubic-bezier(0.2, 0.8, 0.2, 1),
    border-width 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
  overflow: hidden;
  transform-origin: center bottom;
  will-change: transform, opacity, max-height, margin, filter;
  z-index: 1;
}

/* 优化后的退出动画：更高级的“凝缩消散”效果 */
.file-preview-card-leave-active {
  position: absolute !important;
  transition: 
    opacity 0.4s cubic-bezier(0.33, 1, 0.68, 1),
    transform 0.45s cubic-bezier(0.32, 0, 0.67, 0),
    filter 0.3s ease-out;
  overflow: hidden;
  transform-origin: center center;
  will-change: transform, opacity, filter;
  z-index: 0;
}

.file-preview-card-enter-from {
  opacity: 0;
  transform: perspective(1000px) translateY(20px) scale(0.85) rotateX(-15deg);
  filter: blur(8px);
  max-height: 0 !important;
  margin-bottom: 0 !important;
  padding-top: 0 !important;
  padding-bottom: 0 !important;
  border-width: 0 !important;
}

.file-preview-card-leave-to {
  opacity: 0;
  transform: perspective(1000px) scale(0.3) translateY(10px);
  filter: blur(12px) brightness(1.2);
}

.file-preview-card-enter-to,
.file-preview-card-leave-from {
  opacity: 1;
  transform: perspective(1000px) translateY(0) scale(1) rotateX(0);
  filter: blur(0);
  max-height: 60px;
}

/* 发送消息时禁用文件卡片的删除动画，改为瞬间消失 */
.input-content.sending .file-preview-card {
  transition: none !important;
  opacity: 0 !important;
  transform: none !important;
  max-height: 0 !important;
  margin-bottom: 0 !important;
  padding: 0 !important;
  border-width: 0 !important;
  pointer-events: none !important;
}

.input-content.sending .image-strip-item {
  transition: none !important;
  opacity: 0 !important;
  transform: none !important;
  filter: none !important;
  pointer-events: none !important;
}

.input-content.sending .image-strip-shell {
  transition: none !important;
  opacity: 0 !important;
  max-height: 0 !important;
  margin-bottom: 0 !important;
  pointer-events: none !important;
}

/* 拖拽状态样式 - 清爽通透风格 */
.input-bar-outer.is-dragging {
  border-color: transparent;
  background-color: #ffffff;
  /* 柔和的蓝紫光晕 + 极细边框 */
  box-shadow: 0 10px 30px rgba(167, 139, 250, 0.15), 0 0 0 1px rgba(226, 232, 240, 0.6);
  transform: scale(1.01);
  transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1);
}

.drag-upload-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 24px;
  background: linear-gradient(135deg, rgba(240, 249, 255, 0.92) 0%, rgba(255, 250, 240, 0.85) 50%, rgba(243, 232, 255, 0.92) 100%);
  backdrop-filter: blur(8px);
  border-radius: inherit;
  pointer-events: none;
  overflow: visible;
}

.drag-visual-core {
  position: relative;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-magnet {
  position: relative;
  z-index: 2;
  width: 40px;
  height: 40px;
  /* 冰晶般的浅色渐变背景 */
  background: linear-gradient(135deg, #e0f2fe 0%, #f3e8ff 100%);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 玻璃质感边框和阴影 */
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 20px rgba(196, 181, 253, 0.2), inset 0 0 15px rgba(255, 255, 255, 0.6);
  transform: rotate(-10deg);
  animation: magnet-float 2s ease-in-out infinite;
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.icon-magnet.is-stacked {
  position: absolute;
  /* 使用 CSS 变量实现扇形堆叠 */
  transform: translateX(calc(var(--offset) * 14px)) rotate(calc(var(--offset) * 8deg));
  z-index: calc(var(--index) + 10);
  animation: none; /* 堆叠时取消浮动动画，避免乱晃 */
  box-shadow: -2px 0 10px rgba(0,0,0,0.05), 0 8px 20px rgba(196, 181, 253, 0.2), inset 0 0 15px rgba(255, 255, 255, 0.6);
}

.drag-icon {
  width: 20px;
  height: 20px;
  /* 柔和的深蓝紫，保持可读性但低饱和 */
  color: #818cf8;
  filter: drop-shadow(0 2px 4px rgba(167, 139, 250, 0.15));
}

.drag-file-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
  filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.1));
  transition: all 0.3s ease;
}

/* PDF 红色主题 */
.icon-magnet.pdf {
  background: linear-gradient(135deg, #fef2f2 0%, #ffe4e6 100%);
  border-color: rgba(254, 202, 202, 0.8);
  box-shadow: 0 8px 20px rgba(254, 202, 202, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.6);
}

.icon-magnet.image {
  background: linear-gradient(135deg, #ecfeff 0%, #dcfce7 100%);
  border-color: rgba(165, 243, 252, 0.8);
  box-shadow: 0 8px 20px rgba(45, 212, 191, 0.18), inset 0 0 15px rgba(255, 255, 255, 0.7);
}

.pulse-ring.pdf {
  border-color: rgba(252, 165, 165, 0.4);
}

.pulse-ring.image {
  border-color: rgba(45, 212, 191, 0.42);
}

.transfer-beam.pdf {
  background: linear-gradient(to bottom, rgba(248, 113, 113, 1), rgba(248, 113, 113, 0));
}

.transfer-beam.image {
  background: linear-gradient(to bottom, rgba(20, 184, 166, 1), rgba(20, 184, 166, 0));
}

.drag-upload-overlay.is-processing .icon-magnet.pdf {
  background: #ef4444;
  border-color: #f87171;
  box-shadow: 0 0 30px rgba(239, 68, 68, 0.8);
}

.drag-upload-overlay.is-processing .icon-magnet.image {
  background: linear-gradient(135deg, #14b8a6, #22c55e);
  border-color: #5eead4;
  box-shadow: 0 0 34px rgba(20, 184, 166, 0.68);
}

.drag-upload-overlay.is-processing .particle.pdf {
  background: radial-gradient(circle at 30% 30%, #fca5a5, #ef4444) !important;
  box-shadow: 0 0 12px rgba(248, 113, 113, 0.6);
}

.drag-upload-overlay.is-processing .particle.image {
  background: radial-gradient(circle at 30% 30%, #99f6e4, #14b8a6) !important;
  box-shadow: 0 0 12px rgba(20, 184, 166, 0.55);
}

.drag-upload-overlay.is-processing .drag-image-icon {
  filter: drop-shadow(0 0 10px rgba(20, 184, 166, 0.55));
}

/* Word 蓝色主题 */
.icon-magnet.word {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-color: rgba(191, 219, 254, 0.8);
  box-shadow: 0 8px 20px rgba(191, 219, 254, 0.3), inset 0 0 15px rgba(255, 255, 255, 0.6);
}

.pulse-ring.word {
  border-color: rgba(147, 197, 253, 0.4);
}

.transfer-beam.word {
  background: linear-gradient(to bottom, rgba(59, 130, 246, 1), rgba(59, 130, 246, 0));
}

.drag-upload-overlay.is-processing .icon-magnet.word {
  background: #2563eb;
  border-color: #60a5fa;
  box-shadow: 0 0 30px rgba(37, 99, 235, 0.8);
}

.drag-upload-overlay.is-processing .particle.word {
  background: radial-gradient(circle at 30% 30%, #93c5fd, #2563eb) !important;
  box-shadow: 0 0 12px rgba(96, 165, 250, 0.6);
}

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 100%;
  height: 100%;
  border-radius: 14px;
  border: 2px solid;
  /* 极淡的边框颜色 */
  border-color: rgba(196, 181, 253, 0.4);
  opacity: 0;
  animation: pulse-wave 2s cubic-bezier(0.25, 0.46, 0.45, 0.94) infinite;
}

.pulse-ring.delay-1 { 
  animation-delay: 0.6s;
  border-color: rgba(186, 230, 253, 0.4);
}
.pulse-ring.delay-2 { 
  animation-delay: 1.2s;
  border-color: rgba(221, 214, 254, 0.4);
}

.drag-text {
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 0.5px;
  /* 更深的蓝紫色，提升可读性 */
  color: #4f46e5;
  background: none;
  -webkit-text-fill-color: initial;
  text-shadow: 0 2px 4px rgba(255, 255, 255, 0.5);
}

/* 粒子动画 */
.particles {
  position: absolute;
  width: 100%;
  height: 100%;
  top: 0;
  left: 0;
  overflow: visible;
  pointer-events: none;
}

.particle {
  position: absolute;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  opacity: 0;
  top: 50%;
  left: 50%;
  animation: particle-fly 2s ease-out infinite;
  animation-delay: calc(var(--i) * 0.2s);
}

/* 粒子颜色多色彩化 */
.particle:nth-child(1) { background: #60a5fa; } /* 蓝色 */
.particle:nth-child(2) { background: #f472b6; } /* 粉色 */
.particle:nth-child(3) { background: #34d399; } /* 绿色 */
.particle:nth-child(4) { background: #fbbf24; } /* 黄色 */
.particle:nth-child(5) { background: #818cf8; } /* 靛蓝 */
.particle:nth-child(6) { background: #f87171; } /* 红色 */
.particle:nth-child(7) { background: #22d3ee; } /* 青色 */
.particle:nth-child(8) { background: #a78bfa; } /* 紫色 */

@keyframes magnet-float {
  0%, 100% { transform: rotate(-10deg) translateY(0); box-shadow: 0 8px 20px rgba(196, 181, 253, 0.2), inset 0 0 15px rgba(255, 255, 255, 0.6); }
  50% { transform: rotate(-5deg) translateY(-4px); box-shadow: 0 12px 24px rgba(196, 181, 253, 0.25), inset 0 0 15px rgba(255, 255, 255, 0.6); }
}

@keyframes pulse-wave {
  0% { transform: translate(-50%, -50%) scale(0.8); opacity: 0.8; border-width: 2px; }
  100% { transform: translate(-50%, -50%) scale(2.5); opacity: 0; border-width: 0; }
}

@keyframes image-hover-breathe {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-1px) scale(1.04); }
}

@keyframes particle-fly {
  0% { transform: translate(-50%, -50%) rotate(calc(var(--i) * 45deg)) translateX(20px); opacity: 0; }
  50% { opacity: 0.6; }
  100% { transform: translate(-50%, -50%) rotate(calc(var(--i) * 45deg)) translateX(100px); opacity: 0; }
}

/* 进出场动画 */
.drag-scale-enter-active,
.drag-scale-leave-active {
  transition: all 0.4s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.drag-scale-enter-from,
.drag-scale-leave-to {
  opacity: 0;
  transform: scale(0.9) translateY(10px);
}

.drag-scale-enter-to,
.drag-scale-leave-from {
  opacity: 1;
  transform: scale(1) translateY(0);
}

:deep(.ant-dropdown-menu-item.kb-menu-item--selected),
:deep(.ant-menu-item.kb-menu-item--selected) {
  padding: 0 !important;
}

:deep(.ant-dropdown-menu-item-only-child) {
  padding: 0 !important;
}

/* 覆盖 ant-dropdown-menu-item 样式 */
:deep(.ant-dropdown-menu-item) {
  padding: 0 !important;
}

:deep(.ant-dropdown-menu-title-content) {
  margin-bottom: 8px;
}

:deep(.ant-dropdown-menu-item:last-child .ant-dropdown-menu-title-content) {
  margin-bottom: 0;
}

:deep(.ant-dropdown-menu-item:hover) {
  background-color: transparent !important;
}

/* 修正下拉菜单左侧与按钮外边框对齐（8px padding + 32px icon + 10px gap + 1px border = 51px） */
:global(.kb-dropdown-overlay-custom) {
  margin-left: -51px !important;
}

/* === 释放后的吸入/传输动画 === */

/* 1. 覆盖层状态变化 */
.drag-upload-overlay.is-processing {
  background: linear-gradient(135deg, rgba(240, 249, 255, 0.4) 0%, rgba(255, 250, 240, 0.3) 50%, rgba(243, 232, 255, 0.4) 100%);
  backdrop-filter: blur(2px);
  transition: all 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
}

/* 2. 核心图标吸入动画 */
.drag-upload-overlay.is-processing .drag-visual-core {
  animation: none; /* 停止悬浮动画 */
  transform: scale(0.1) translateY(60px); /* 缩小并向下移动 */
  opacity: 0;
  transition: transform 0.6s cubic-bezier(0.6, -0.28, 0.735, 0.045), opacity 0.5s ease 0.1s;
}

.drag-upload-overlay.is-processing .icon-magnet {
  background: #4f46e5; /* 变成高亮能量球 */
  border-color: #818cf8;
  box-shadow: 0 0 30px rgba(79, 70, 229, 0.8);
  transition: all 0.3s ease;
}

.drag-upload-overlay.is-processing .drag-icon {
  color: white;
  transform: scale(0.5);
  transition: all 0.3s ease;
}

.drag-image-shell {
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drag-image-icon {
  width: 22px;
  height: 22px;
  color: #0f766e;
  filter: drop-shadow(0 2px 4px rgba(20, 184, 166, 0.18));
  transition: all 0.3s ease;
}

.drag-upload-overlay.is-processing .pulse-ring {
  opacity: 0;
  transition: opacity 0.2s;
}

/* 3. 文字上浮消失 */
.drag-upload-overlay.is-processing .drag-text {
  transform: translateY(-20px);
  opacity: 0;
  transition: all 0.4s ease;
}

/* 4. 粒子内聚动画 (Implosion) */
.drag-upload-overlay.is-processing .particle {
  animation: particle-implode 0.6s cubic-bezier(0.6, 0.04, 0.98, 0.335) forwards !important;
  /* 强制所有粒子变成能量色 (默认) */
  background: radial-gradient(circle at 30% 30%, #a5b4fc, #4f46e5) !important;
  box-shadow: 0 0 12px rgba(99, 102, 241, 0.6);
}

/* 5. 传输光束 */
.transfer-beam {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, 0);
  width: 2px;
  height: 0;
  background: linear-gradient(to bottom, rgba(99, 102, 241, 1), rgba(99, 102, 241, 0));
  opacity: 0;
  z-index: 1;
  pointer-events: none;
}

.drag-upload-overlay.is-processing .transfer-beam {
  animation: beam-shoot 0.6s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: 0.1s;
}

.drag-upload-overlay .icon-magnet.image:hover,
.drag-upload-overlay .drag-image-icon {
  animation: image-hover-breathe 2.8s ease-in-out infinite;
}

@keyframes particle-implode {
  0% {
    transform: translate(-50%, -50%) rotate(calc(var(--i) * 45deg)) translateX(100px);
    opacity: 1;
    scale: 1;
  }
  100% {
    transform: translate(-50%, -50%) rotate(calc(var(--i) * 45deg)) translateX(0);
    opacity: 0;
    scale: 0.2;
  }
}

@keyframes beam-shoot {
  0% {
    height: 0;
    opacity: 1;
    width: 4px;
  }
  50% {
    height: 100px;
    opacity: 0.8;
    width: 2px;
  }
  100% {
    height: 155px;
    opacity: 0;
    width: 0;
    transform: translate(-50%, 20px);
  }
}
</style>
