<template>
  <div class="canvas-panel-container">
    <div class="canvas-panel-placeholder" v-if="isFullScreen || isExiting" :style="placeholderStyle"></div>
    <div
      class="canvas-panel"
      :class="{
        'fullscreen-mode': isFullScreen && !isExiting,
        'hide-fullscreen-header': shouldHideHeaderInFullscreen,
        'is-animating': isAnimating
      }"
      :style="panelStyle"
      ref="panelRef"
    >
    <div class="canvas-header" :class="{ 'url-browser-mode': activeArtifact?.type === 'url' }">
      <div class="header-left">
        <!-- URL 类型：浏览器导航栏样式 -->
        <template v-if="activeArtifact?.type === 'url'">
          <div class="url-browser-bar" :class="{ 'is-capturing': isScreenshoting }">
            <div v-if="isScreenshoting" class="url-browser-capture-line"></div>
            <button
              class="url-browser-nav-btn screenshot-btn"
              :class="{ 'is-capturing': isScreenshoting }"
              :title="isScreenshoting ? '正在生成快照' : '截图'"
              :disabled="isScreenshoting"
              @click="handleScreenshot"
            >
              <span v-if="isScreenshoting" class="screenshot-btn-sheen"></span>
              <img src="@/assets/icons/screenshot.svg" class="screenshot-icon-img" alt="截图" />
            </button>
            <div class="url-browser-nav-btns">
              <button class="url-browser-nav-btn" title="刷新" @click="refreshUrlPreview">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="23 4 23 10 17 10"></polyline>
                  <polyline points="1 20 1 14 7 14"></polyline>
                  <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10"></path>
                  <path d="M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                </svg>
              </button>
            </div>
            <div class="url-browser-address" :class="{ 'is-capturing': isScreenshoting }">
              <span v-if="isScreenshoting" class="url-browser-address-flow"></span>
              <svg class="url-browser-globe-icon" :class="{ 'is-capturing': isScreenshoting }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              <input
                ref="urlInputRef"
                class="url-browser-input"
                :class="{ 'is-capturing': isScreenshoting }"
                v-model="editableUrl"
                @keydown.enter="navigateUrl"
                @blur="navigateUrl"
                @focus="selectUrlInput"
                spellcheck="false"
              />
              <button class="url-browser-open-btn" title="在新标签页中打开" @click="openInNewTab">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
              </button>
              <span v-if="isScreenshoting" class="url-browser-capture-status">正在生成快照</span>
            </div>
          </div>
        </template>
        <!-- 其他类型：普通标题 -->
        <template v-else>
          <h3 class="title">
            <span v-if="titleIcon" v-html="titleIcon" class="title-icon"></span>
            <span class="title-text">{{ activeArtifact?.title || 'Canvas' }}</span>
          </h3>
          <span v-if="activeArtifact && !activeArtifact.isComplete" class="status-badge">
            生成中 <LoadingOutlined style="font-size: 10px;" />
          </span>
        </template>
      </div>

      <div class="header-center">
        <div v-if="showViewTabs" class="view-tabs" :class="{ 'is-code-mode': viewMode === 'code' }">
          <div class="tab-glider"></div>
          <button :class="{ active: viewMode === 'preview' }" @click="viewMode = 'preview'" title="预览">预览</button>
          <button :class="{ active: viewMode === 'code' }" @click="viewMode = 'code'" title="代码">代码</button>
        </div>
        <div v-if="activeArtifact?.type === 'docx'" class="view-tabs" :class="{ 'is-edit-mode': docxTabMode === 'edit' }">
          <div class="tab-glider"></div>
          <button :class="{ active: docxTabMode === 'preview' }" @click="docxTabMode = 'preview'" title="预览">预览</button>
          <button :class="{ active: docxTabMode === 'edit' }" @click="docxTabMode = 'edit'" title="编辑">编辑</button>
        </div>
      </div>

      <div class="header-right">
        <template v-if="viewMode === 'code' && !isCodeAtBottom">
          <div class="actions-group">
            <button class="header-icon-btn" @click="scrollToBottom" title="滚动到底部">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="7 13 12 18 17 13"></polyline>
                <polyline points="7 6 12 11 17 6"></polyline>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="activeArtifact && activeArtifact.type === 'docx'">
          <div class="actions-group">
            <button
              :class="['header-icon-btn', 'header-icon-btn--fullscreen', { 'is-active': isDocxFullscreenActive }]"
              @click="toggleFullScreen"
              :title="isDocxFullscreenActive ? '退出全屏 (Esc)' : '全屏浏览'"
            >
              <svg class="header-fs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="docxFullscreenIconPath" />
              </svg>
            </button>
            <button class="header-icon-btn" @click="downloadDocx" title="导出文档">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>
        <template v-if="isExcelArtifact">
          <div class="actions-group">
            <button
              :class="['header-icon-btn', 'header-icon-btn--fullscreen', { 'is-active': isDocxFullscreenActive }]"
              @click="toggleFullScreen"
              :title="isDocxFullscreenActive ? '退出全屏 (Esc)' : '全屏浏览'"
            >
              <svg class="header-fs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="docxFullscreenIconPath" />
              </svg>
            </button>
            <button class="header-icon-btn" @click="downloadExcel" title="导出 Excel">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>
        <template v-if="isPptArtifact">
          <div class="actions-group">
            <div class="screening-btn-group" @click.stop>
              <button class="screening-main-btn" @click="startScreening(false)" title="从当前页开始放映">
                <img :src="slideshowIcon" class="screening-icon" alt="放映" />
              </button>
              <button class="screening-arrow-btn" @click="screeningDropdownVisible = !screeningDropdownVisible" title="幻灯片放映">
                <svg width="8" height="8" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 1l4 4 4-4"/>
                </svg>
              </button>
              <div v-if="screeningDropdownVisible" class="screening-dropdown-menu" @click.stop>
                <div class="screening-dropdown-item" @click="startScreening(true)">
                  <img :src="slideshowIcon" class="screening-icon" alt="放映" />
                  <span>从头开始</span>
                </div>
                <div class="screening-dropdown-item" @click="startScreening(false)">
                  <img :src="slideshowIcon" class="screening-icon" alt="放映" />
                  <span>从当前页开始</span>
                </div>
              </div>
            </div>
            <div class="vertical-divider"></div>
            <button
              :class="['header-icon-btn', 'header-icon-btn--fullscreen', { 'is-active': isDocxFullscreenActive }]"
              @click="toggleFullScreen"
              :title="isDocxFullscreenActive ? '退出全屏 (Esc)' : '全屏浏览'"
            >
              <svg class="header-fs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="docxFullscreenIconPath" />
              </svg>
            </button>
            <button class="header-icon-btn" @click="exportPpt" title="导出 PPT">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>
        <template v-if="isTxtArtifact">
          <div class="actions-group">
            <button class="header-icon-btn" @click="downloadTxt" title="下载 TXT">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>
        <template v-if="activeArtifact && activeArtifact.type === 'pdf' && pdfUrl">
          <div class="actions-group">
            <button class="header-icon-btn" @click="downloadPdf" title="下载 PDF">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="unsupportedFilePreviewKind">
          <div class="actions-group">
            <button class="header-icon-btn" @click="downloadUnsupportedFile" :title="unsupportedFileDownloadTitle">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="activeArtifact && (activeArtifact.type === 'html' || activeArtifact.type === 'svg')">
          <div class="actions-group">
            <button class="header-icon-btn" @click="refreshPreview" title="刷新预览">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M23 4v6h-6"></path>
                <path d="M1 20v-6h6"></path>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
              </svg>
            </button>
            <button class="header-icon-btn" @click="downloadHtmlOrSvg" title="下载文件">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="activeArtifact && activeArtifact.type === 'json'">
          <div class="actions-group">
            <button class="header-icon-btn" @click="copyJsonContent" title="复制 JSON">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
            <button class="header-icon-btn" @click="downloadJson" title="下载 JSON">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="activeArtifact && activeArtifact.type === 'markdown'">
          <div class="actions-group">
            <button class="header-icon-btn" @click="copyMarkdown" title="复制 Markdown">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
            </button>
            <button class="header-icon-btn" @click="downloadMarkdown" title="下载 Markdown">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="activeArtifact && activeArtifact.type === 'url'">
          <div class="actions-group">
            <button
              :class="['header-icon-btn', 'header-icon-btn--fullscreen', { 'is-active': isDocxFullscreenActive }]"
              @click="toggleFullScreen"
              :title="isDocxFullscreenActive ? '退出全屏 (Esc)' : '全屏浏览'"
            >
              <svg class="header-fs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="docxFullscreenIconPath" />
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>

        <template v-if="activeArtifact && activeArtifact.type === 'map'">
          <div class="actions-group">
            <button
              :class="['header-icon-btn', 'header-icon-btn--fullscreen', { 'is-active': isDocxFullscreenActive }]"
              @click="toggleFullScreen"
              :title="isDocxFullscreenActive ? '退出全屏 (Esc)' : '全屏浏览'"
            >
              <svg class="header-fs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path :d="docxFullscreenIconPath" />
              </svg>
            </button>
          </div>
          <div class="vertical-divider"></div>
        </template>
        
        <button class="close-btn" @click="handleCloseCanvas" title="关闭 Canvas">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M18 6L6 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M6 6L18 18" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </div>
    
    <div class="canvas-content" ref="canvasContentRef">
      <Transition name="fade" mode="out-in">
        <div v-if="!activeArtifact" class="empty-state" key="empty">
          <p>Canvas Content Area</p>
        </div>
        
        <div v-else class="content-wrapper" key="content">
          <div v-if="(activeArtifact.type === 'html' || activeArtifact.type === 'svg') && (!activeArtifact.isComplete || htmlLoading || isPendingSvg) && viewMode === 'preview'" class="html-loading">
            <CreativeLoading text="正在渲染预览..." />
          </div>
          <Transition name="slide-fade" mode="out-in">
            <!-- Preview Mode -->
            <div v-if="viewMode === 'preview'" class="preview-container" key="preview">
              <Transition name="scale-fade" mode="out-in">
                <MermaidRenderer 
                  v-if="activeArtifact.type === 'mermaid'"
                  ref="mermaidRendererRef"
                  :key="`mermaid-${activeArtifact.id}`"
                  :content="artifactTextContent" 
                  :is-complete="activeArtifact.isComplete"
                  :id="activeArtifact.id"
                  :is-full-screen="isFullScreen"
                  :is-exiting="isExiting"
                  @toggle-fullscreen="toggleFullScreen"
                />
                <div v-else-if="activeArtifact.type === 'docx' && docxLoading && docxTabMode === 'preview'" class="text-preview" :key="`docx-loading-${activeArtifact.id}`">
                  正在加载 Word 文档...
                </div>
                <div v-else-if="activeArtifact.type === 'docx' && docxError && docxTabMode === 'preview'" class="text-preview" :key="`docx-error-${activeArtifact.id}`">
                  <div class="docx-fetch-error">{{ docxError }}</div>
                </div>
                <DocxPreview
                  v-else-if="activeArtifact.type === 'docx' && docxTabMode === 'preview'"
                  :key="`docx-preview-${activeArtifact.id}`"
                  :content="docxSource"
                  :artifactId="activeArtifact.id"
                  :title="activeArtifact.title"
                  :suspend="effectiveSuspend"
                />
                <WordCanvasFullUI
                  v-else-if="activeArtifact.type === 'docx' && docxTabMode === 'edit'"
                  ref="wordCanvasEditorRef"
                  :key="`docx-editor-${activeArtifact.id}`"
                  :source="docxSource"
                  :title="activeArtifact.title"
                  :suspend="effectiveSuspend"
                />
                <CameraCanvasUI
                  v-else-if="activeArtifact.type === 'map'"
                  ref="cameraCanvasUIRef"
                  :key="`camera-canvas-${activeArtifact.id}`"
                  :content="artifactTextContent"
                  :is-complete="activeArtifact.isComplete"
                  :id="activeArtifact.id"
                  :title="activeArtifact.title"
                  :suspend="effectiveSuspend"
                  @toggle-fullscreen="toggleFullScreen"
                />
                <div v-else-if="isExcelArtifact" class="excel-canvas-wrapper" :class="{ 'has-fullscreen-header': isFullScreen && !isExiting }" :key="`excel-wrapper-${activeArtifact.id}`">
                  <div v-if="isFullScreen && !isExiting" class="excel-fullscreen-header">
                    <span class="excel-fullscreen-title">
                      <img :src="excelIcon" class="excel-fs-icon" alt="" />
                      {{ activeArtifact.title || 'Excel' }}
                    </span>
                    <div class="excel-fullscreen-actions">
                      <button @click="downloadExcel" class="header-icon-btn" title="下载 Excel">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                      </button>
                      <button @click="toggleFullScreen" class="header-icon-btn" title="退出全屏 (Esc)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <ExcelCanvasFullUI
                    ref="excelCanvasRef"
                    :key="`excel-editor-${activeArtifact.id}`"
                    :source="excelSource"
                    :title="activeArtifact.title"
                    :suspend="effectiveSuspend"
                  />
                </div>
                <div v-else-if="isPptArtifact" class="ppt-canvas-wrapper" :class="{ 'has-fullscreen-header': isFullScreen && !isExiting }" :key="`ppt-wrapper-${activeArtifact.id}`">
                  <div v-if="isFullScreen && !isExiting" class="ppt-fullscreen-header">
                    <span class="ppt-fullscreen-title">
                      <img :src="pptIcon" class="ppt-fs-icon" alt="" />
                      {{ activeArtifact.title || 'PPT' }}
                    </span>
                    <div class="actions-group">
                      <div class="screening-btn-group" @click.stop>
                        <button class="screening-main-btn" @click="startScreening(false)" title="从当前页开始放映">
                          <img :src="slideshowIcon" class="screening-icon" alt="放映" />
                        </button>
                        <button class="screening-arrow-btn" @click="screeningDropdownVisible = !screeningDropdownVisible" title="幻灯片放映">
                          <svg width="8" height="8" viewBox="0 0 10 6" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M1 1l4 4 4-4"/>
                          </svg>
                        </button>
                        <div v-if="screeningDropdownVisible" class="screening-dropdown-menu" @click.stop>
                          <div class="screening-dropdown-item" @click="startScreening(true)">
                            <img :src="slideshowIcon" class="screening-icon" alt="放映" />
                            <span>从头开始</span>
                          </div>
                          <div class="screening-dropdown-item" @click="startScreening(false)">
                            <img :src="slideshowIcon" class="screening-icon" alt="放映" />
                            <span>从当前页开始</span>
                          </div>
                        </div>
                      </div>
                      <div class="vertical-divider"></div>
                      <button
                        class="header-icon-btn"
                        @click="toggleFullScreen"
                        :title="isDocxFullscreenActive ? '退出全屏 (Esc)' : '全屏浏览'"
                      >
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path :d="docxFullscreenIconPath" />
                        </svg>
                      </button>
                      <button class="header-icon-btn" @click="exportPpt" title="导出 PPT">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                          <polyline points="7 10 12 15 17 10"></polyline>
                          <line x1="12" y1="15" x2="12" y2="3"></line>
                        </svg>
                      </button>
                    </div>
                  </div>
                  <PptCanvasFullUI
                    ref="pptCanvasRef"
                    :key="`ppt-editor-${activeArtifact.id}`"
                    :source="pptSource"
                    :title="activeArtifact.title"
                    :suspend="effectiveSuspend"
                  />
                </div>
                <TxtCanvasEditor
                  v-else-if="isTxtArtifact"
                  ref="txtCanvasEditorRef"
                  :key="`txt-editor-${activeArtifact.id}`"
                  :source="txtSource"
                  @change="handleTxtChange"
                />
                <div v-else-if="activeArtifact.type === 'pdf' && pdfUrl" class="html-preview" :key="`pdf-${activeArtifact.id}`">
                  <iframe :src="pdfUrl + '#view=FitH'" class="preview-iframe" type="application/pdf"></iframe>
                </div>
                <div v-else-if="activeArtifact.type === 'pdf' && pdfError" class="text-preview" :key="`pdf-error-${activeArtifact.id}`">
                  <div class="docx-fetch-error">{{ pdfError }}</div>
                </div>
                <div v-else-if="activeArtifact.type === 'pdf'" class="text-preview" :key="`pdf-loading-${activeArtifact.id}`">
                  正在加载 PDF...
                </div>
                <div
                  v-else-if="activeArtifact.type === 'url'"
                  class="url-preview"
                  :class="{
                    'is-capturing': isScreenshoting,
                    'is-sending': screenshotAnimationPhase === 'sending'
                  }"
                  :key="`url-${activeArtifact.id}-${urlRefreshKey}`"
                >
                  <div v-if="isScreenshoting" class="url-preview-capture-veil"></div>
                  <div
                    v-if="showScreenshotOverlay"
                    class="url-preview-capture-overlay"
                    :class="[`phase-${screenshotAnimationPhase}`]"
                    aria-hidden="true"
                  >
                    <div class="capture-soft-light"></div>
                    <div class="capture-status-chip">{{ screenshotStatusText }}</div>
                    <div v-if="screenshotAnimationPhase === 'sending'" class="capture-send-ghost"></div>
                  </div>
                  <iframe
                    ref="urlIframeRef"
                    :src="currentBrowseUrl"
                    class="url-preview-iframe"
                    sandbox="allow-scripts allow-modals allow-forms allow-popups allow-same-origin allow-pointer-lock"
                    allow="camera; microphone; clipboard-read; clipboard-write; fullscreen"
                    @load="onUrlIframeLoad"
                  ></iframe>
                </div>
                <div v-else-if="(activeArtifact.type === 'html' || activeArtifact.type === 'svg') && htmlError" class="text-preview" :key="`html-error-${activeArtifact.id}`">
                  <div class="docx-fetch-error">{{ htmlError }}</div>
                </div>
                <div v-else-if="activeArtifact.type === 'html' || activeArtifact.type === 'svg'" class="html-preview" :key="`html-${activeArtifact.id}-${refreshKey}`">
                  <iframe v-if="activeArtifact.isComplete && iframeReady && htmlPreviewUrl" :src="htmlPreviewUrl" class="preview-iframe" sandbox="allow-scripts allow-modals allow-forms allow-popups allow-same-origin" allow="camera; microphone; clipboard-read; clipboard-write"></iframe>
                  <iframe v-else-if="activeArtifact.isComplete && iframeReady" :srcdoc="previewContent" class="preview-iframe" sandbox="allow-scripts allow-modals allow-forms allow-popups allow-same-origin" allow="camera; microphone; clipboard-read; clipboard-write"></iframe>
                  <div class="html-controls">
                    <button @click="toggleFullScreen" class="control-btn" :title="(isFullScreen && !isExiting) ? '退出全屏' : '全屏浏览'">
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
                </div>
                <div v-else-if="unsupportedFilePreviewKind" class="text-preview unsupported-preview" :key="`unsupported-${activeArtifact.id}`">
                  <div class="unsupported-preview-card">
                    <div class="unsupported-preview-hero">
                      <div class="unsupported-preview-icon-shell">
                        <img class="unsupported-preview-icon" :src="unsupportedFilePreviewIconSrc" :alt="unsupportedFilePreviewKind" />
                      </div>
                      <div class="unsupported-preview-glow"></div>
                    </div>
                    <div class="unsupported-preview-title">暂不支持该文件类型预览</div>
                    <div class="unsupported-preview-desc">{{ unsupportedFilePreviewDescription }}</div>
                  </div>
                </div>
                <div v-else-if="activeArtifact.type === 'markdown' && markdownError" class="text-preview" :key="`md-error-${activeArtifact.id}`">
                  <div class="docx-fetch-error">{{ markdownError }}</div>
                </div>
                <div v-else-if="activeArtifact.type === 'markdown' && markdownLoading" class="text-preview" :key="`md-loading-${activeArtifact.id}`">
                  正在加载 Markdown...
                </div>
                <div v-else-if="activeArtifact.type === 'markdown' || activeArtifact.type === 'text'" class="text-preview markdown-preview" :key="`md-${activeArtifact.id}`" ref="markdownPreviewRef" @scroll="checkMarkdownScroll" @wheel="handleMarkdownWheel">
                    <MarkdownRenderer :content="artifactTextContent" role="assistant" :disable-artifacts="true" />
                 </div>
                <div v-else class="text-preview" :key="`text-${activeArtifact.id}`">
                   <pre>{{ artifactTextContent }}</pre>
                </div>
              </Transition>
            </div>

            <!-- Code Mode -->
            <div v-else class="code-container" key="code">
               <CodeEditor 
                 ref="codeEditorRef"
                 v-model="editableTextContent" 
                 :language="activeArtifact.type" 
                 :key="activeArtifact.id"
                 @scroll-status="handleScrollStatus"
               />
            </div>
          </Transition>
        </div>
      </Transition>
    </div>

  </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onUnmounted, watch, onMounted, nextTick } from 'vue';
import { type Artifact, extractFileNameFromSource } from '@/utils/artifactParser';
import { captureScreenshot } from '@/services/screenshot';
import type WordCanvasFullUIComp from './WordCanvasFullUI.vue';
import type ExcelCanvasFullUIComp from './ExcelCanvasFullUI.vue';
import type PptCanvasFullUIComp from './PptCanvasFullUI.vue';
import type TxtCanvasEditorComp from './TxtCanvasEditor.vue';
import { LoadingOutlined } from '@ant-design/icons-vue';
import { getHtmlPreviewContent } from '@/utils/htmlPreview';
import { defineAsyncComponent } from 'vue';
import wordIcon from '@/assets/image/svg/Word.svg';
import pdfIcon from '@/assets/image/svg/pdf-icon.svg';
import markdownIcon from '@/assets/image/svg/Markdown.svg';
import txtIcon from '@/assets/image/svg/Txt.svg';
import excelIcon from '@/assets/image/svg/Excel.svg';
import pptIcon from '@/assets/image/svg/PPT.svg';
import slideshowIcon from '@/assets/image/svg/slideshow.svg';
import jsonIcon from '@/assets/image/svg/json.svg';
import NotificationService from '@/utils/NotificationService';
import CreativeLoading from '@/components/common/CreativeLoading.vue';

const MarkdownRenderer = defineAsyncComponent(() => import('@/components/common/MarkdownRenderer.vue'));
const CameraCanvasUI = defineAsyncComponent(() => import('./CameraCanvasUI.vue'));
const CodeEditor = defineAsyncComponent(() => import('./CodeEditor.vue'));
const MermaidRenderer = defineAsyncComponent(() => import('./MermaidRenderer.vue'));
const WordCanvasFullUI = defineAsyncComponent(() => import('./WordCanvasFullUI.vue'));
const DocxPreview = defineAsyncComponent(() => import('./DocxPreview.vue'));
const ExcelCanvasFullUI = defineAsyncComponent(() => import('./ExcelCanvasFullUI.vue'));
const PptCanvasFullUI = defineAsyncComponent(() => import('./PptCanvasFullUI.vue'));
const TxtCanvasEditor = defineAsyncComponent(() => import('./TxtCanvasEditor.vue'));
const props = defineProps<{
  suspendDocx?: boolean
}>();

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'screenshot-start'): void
  (e: 'screenshot', file: File): void
}>();
const activeArtifact = ref<Artifact | null>(null);
const viewMode = ref<'preview' | 'code'>('preview');
const docxTabMode = ref<'preview' | 'edit'>('preview');
const refreshKey = ref(0);
const urlRefreshKey = ref(0);
const urlInputRef = ref<HTMLInputElement | null>(null);
const urlIframeRef = ref<HTMLIFrameElement | null>(null);
const currentBrowseUrl = ref('');
const editableUrl = ref('');
const isScreenshoting = ref(false);
const screenshotAnimationPhase = ref<'idle' | 'capturing' | 'sending'>('idle');
const screenshotStatusText = computed(() => screenshotAnimationPhase.value === 'sending' ? '已发送' : '正在截取当前画面');
const showScreenshotOverlay = computed(() => screenshotAnimationPhase.value !== 'idle');
const pdfUrl = ref<string>('');
const pdfError = ref('');
const docxBuffer = ref<ArrayBuffer | null>(null);
const docxLoading = ref(false);
const docxError = ref('');
const htmlLoading = ref(false);
const htmlError = ref('');
const htmlRemoteContent = ref('');
const markdownLoading = ref(false);
const markdownError = ref('');
const markdownRemoteContent = ref('');
const svgRemoteContent = ref('');
const jsonRemoteContent = ref('');
const isFullScreen = ref(false);
const isExiting = ref(false);
const isAnimating = ref(false);
// 全屏进入/退出动画期间也视为挂起：让 Excel/PPT 等重型子组件在这 0.6s 内
// 跳过每帧 resize / 工具栏重建，动画结束后再统一刷新一次。不影响动画视觉。
const effectiveSuspend = computed(() => Boolean(props.suspendDocx) || isAnimating.value);
const panelStyle = ref<Record<string, string>>({});
const placeholderStyle = ref<Record<string, string>>({});
const panelRef = ref<HTMLElement | null>(null);
const canvasContentRef = ref<HTMLElement | null>(null);
const mermaidRendererRef = ref<any>(null);
const codeEditorRef = ref<any>(null);
const wordCanvasEditorRef = ref<InstanceType<typeof WordCanvasFullUIComp> | null>(null);
const excelCanvasRef = ref<InstanceType<typeof ExcelCanvasFullUIComp> | null>(null);
const pptCanvasRef = ref<InstanceType<typeof PptCanvasFullUIComp> | null>(null);
const txtCanvasEditorRef = ref<InstanceType<typeof TxtCanvasEditorComp> | null>(null);
const cameraCanvasUIRef = ref<{ fitToScreen?: () => void } | null>(null);

const markdownPreviewRef = ref<HTMLElement | null>(null);
const originalRect = ref<DOMRect | null>(null);
const iframeReady = ref(false);
const isCodeAtBottom = ref(true);
const isMarkdownAtBottom = ref(true);
const isMarkdownAutoScroll = ref(true);
const CANVAS_FULLSCREEN_TOGGLE_EVENT = 'canvas-fullscreen-toggle-request';
const CANVAS_FULLSCREEN_CHANGE_EVENT = 'canvas-fullscreen-change';
const FULLSCREEN_ENTER_ICON_PATH = 'M15 3h6v6M9 21H3v-6M21 3l-7 7M3 21l7-7';
const FULLSCREEN_EXIT_ICON_PATH = 'M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7';
const isDocxFullscreenActive = computed(() => isFullScreen.value && !isExiting.value);
const shouldHideHeaderInFullscreen = computed(() => {
  if (!isFullScreen.value || isExiting.value) return false;
  if (activeArtifact.value?.type === 'url') return false;
  if (activeArtifact.value?.type === 'map') return false;
  return activeArtifact.value?.type !== 'docx' || docxTabMode.value !== 'preview';
});
const docxFullscreenIconPath = computed(() => (
  isDocxFullscreenActive.value ? FULLSCREEN_EXIT_ICON_PATH : FULLSCREEN_ENTER_ICON_PATH
));
const isTxtArtifact = computed(() => {
  const type = activeArtifact.value?.type?.toLowerCase() || '';
  const ext = getArtifactFileExtension(activeArtifact.value?.title);
  return type === 'text' || type === 'txt' || ext === 'txt';
});

const isExcelArtifact = computed(() => {
  const type = activeArtifact.value?.type?.toLowerCase() || '';
  const ext = getArtifactFileExtension(activeArtifact.value?.title);
  return type === 'xls' || type === 'xlsx' || ext === 'xls' || ext === 'xlsx';
});

const isPptArtifact = computed(() => {
  const type = activeArtifact.value?.type?.toLowerCase() || '';
  const ext = getArtifactFileExtension(activeArtifact.value?.title);
  return type === 'ppt' || type === 'pptx' || ext === 'ppt' || ext === 'pptx';
});

function handleCloseCanvas() {
  stopUrlPolling();
  // 退出全屏模式，确保下次打开为非全屏状态
  if (isFullScreen.value) {
    isFullScreen.value = false;
    isExiting.value = false;
    isAnimating.value = false;
    panelStyle.value = {};
    originalRect.value = null;
  }
  emit('close');
}

function refreshUrlPreview() {
  currentBrowseUrl.value = editableUrl.value;
  urlRefreshKey.value++;
}

let urlPollTimer: ReturnType<typeof setInterval> | null = null;

function trySyncIframeUrl() {
  try {
    const iframe = urlIframeRef.value;
    if (!iframe?.contentWindow) return;
    const newUrl = iframe.contentWindow.location.href;
    if (newUrl && newUrl !== 'about:blank' && newUrl !== editableUrl.value) {
      editableUrl.value = newUrl;
    }
  } catch {
    // 跨域 iframe 无法读取 URL，静默忽略
  }
}

function onUrlIframeLoad() {
  trySyncIframeUrl();
}

function startUrlPolling() {
  stopUrlPolling();
  urlPollTimer = setInterval(trySyncIframeUrl, 800);
}

function stopUrlPolling() {
  if (urlPollTimer) {
    clearInterval(urlPollTimer);
    urlPollTimer = null;
  }
}

function navigateUrl() {
  const url = editableUrl.value.trim();
  if (!url) {
    // 如果地址栏为空，恢复为当前浏览的 URL
    editableUrl.value = currentBrowseUrl.value;
    return;
  }
  // 自动补全 https://
  const normalizedUrl = /^https?:\/\//i.test(url) ? url : `https://${url}`;
  currentBrowseUrl.value = normalizedUrl;
  editableUrl.value = normalizedUrl;
  urlRefreshKey.value++;
}

function openInNewTab() {
  const url = editableUrl.value.trim() || currentBrowseUrl.value;
  if (!url) return;
  const normalizedUrl = /^https?:\/\//i.test(url) ? url : `https://${url}`;
  window.open(normalizedUrl, '_blank');
}

function selectUrlInput() {
  urlInputRef.value?.select();
}

// 监听 artifact 变化，初始化 URL 并启停轮询
watch(() => activeArtifact.value?.id, (newId) => {
  stopUrlPolling();
  if (newId && activeArtifact.value?.type === 'url') {
    const raw = (activeArtifact.value?.url || activeArtifact.value?.content || '') as string;
    currentBrowseUrl.value = raw;
    editableUrl.value = raw;
    setTimeout(() => {
      startUrlPolling();
    }, 500);
  }
}, { immediate: true });


const isTextLikeArtifactType = (type?: string) => {
  const normalizedType = (type || '').toLowerCase().trim();
  return ['markdown', 'md', 'text', 'txt', 'csv', 'html', 'svg', 'json'].includes(normalizedType);
};

const decodeTextArtifactContent = (content: Artifact['content']) => {
  if (typeof content === 'string') return content;

  try {
    if (content instanceof ArrayBuffer) {
      return new TextDecoder('utf-8').decode(new Uint8Array(content));
    }
    if (ArrayBuffer.isView(content)) {
      return new TextDecoder('utf-8').decode(
        new Uint8Array(content.buffer, content.byteOffset, content.byteLength)
      );
    }
  } catch (error) {
    console.warn('解码文本类 Canvas 内容失败:', error);
  }

  return '';
};

const handleScrollStatus = (atBottom: boolean) => {
  isCodeAtBottom.value = atBottom;
};

const handleMarkdownWheel = (e: WheelEvent) => {
  // 如果向上滚动，取消自动滚动
  if (e.deltaY < 0) {
    isMarkdownAutoScroll.value = false;
  }
};

const checkMarkdownScroll = () => {
  if (!markdownPreviewRef.value) return;
  
  const { scrollTop, scrollHeight, clientHeight } = markdownPreviewRef.value;
  // 容差设为 20px
  const atBottom = scrollHeight - scrollTop - clientHeight <= 20;
  
  isMarkdownAtBottom.value = atBottom;
  
  // 如果滚动到了底部，恢复自动滚动
  if (atBottom) {
    isMarkdownAutoScroll.value = true;
  }
};

const scrollToBottom = () => {
  if (codeEditorRef.value) {
    codeEditorRef.value.scrollToBottom();
  }
};

watch(codeEditorRef, (newEditor) => {
  if (newEditor && viewMode.value === 'code' && activeArtifact.value && !activeArtifact.value.isComplete) {
    setTimeout(() => {
      newEditor.scrollToBottom();
    }, 100);
  }
});

watch(markdownPreviewRef, async (el) => {
  if (el) {
    await nextTick();
    checkMarkdownScroll();
  }
});

watch(
  () => [activeArtifact.value?.id, activeArtifact.value?.isComplete],
  (newVal, oldVal) => {
      const [newId, isComplete] = newVal;
      const [oldId] = oldVal || [];
      
      const type = activeArtifact.value?.type;
      if (type !== 'html' && type !== 'svg') return;

      // Reset on ID change or incomplete
      if (newId !== oldId || !isComplete) {
          iframeReady.value = false;
      }
      
      if (isComplete) {
          // Add delay to ensure DOM readiness and transition completion
          // This fixes the issue where iframe sometimes doesn't render initially
          if (!iframeReady.value) {
              setTimeout(() => {
                  iframeReady.value = true;
              }, 100);
          }
      }
  },
  { immediate: true }
);

const toggleFullScreen = async () => {
  if (!panelRef.value) return;
  if (isExiting.value) return;

  if (!isFullScreen.value) {
    // Enter Fullscreen
    isExiting.value = false;
    const rect = panelRef.value.getBoundingClientRect();
    originalRect.value = rect;

    placeholderStyle.value = {
      width: `${rect.width}px`,
      height: `${rect.height}px`
    };

    // Mark animating to apply performance CSS hints
    isAnimating.value = true;

    panelStyle.value = {
      position: 'fixed',
      top: `${rect.top}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`,
      height: `${rect.height}px`,
      zIndex: '1003',
      boxSizing: 'border-box',
      borderRadius: '16px',
      transition: 'top 0.6s cubic-bezier(0.22, 1, 0.36, 1), left 0.6s cubic-bezier(0.22, 1, 0.36, 1), width 0.6s cubic-bezier(0.22, 1, 0.36, 1), height 0.6s cubic-bezier(0.22, 1, 0.36, 1), border-radius 0.6s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.6s cubic-bezier(0.22, 1, 0.36, 1)',
      boxShadow: '0 0 0 0 rgba(0,0,0,0)',
      backgroundColor: '#fff'
    };
    panelRef.value.offsetHeight;

    requestAnimationFrame(() => {
      isFullScreen.value = true;
      panelStyle.value.top = '0px';
      panelStyle.value.left = '0px';
      panelStyle.value.width = '100vw';
      panelStyle.value.height = '100vh';
      panelStyle.value.borderRadius = '0px';
      panelStyle.value.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.25)';
      if (activeArtifact.value?.type === 'mermaid' && mermaidRendererRef.value?.fitToScreen) {
        mermaidRendererRef.value.fitToScreen(true, window.innerWidth, window.innerHeight);
      }
      if (cameraCanvasUIRef.value?.fitToScreen) {
        cameraCanvasUIRef.value.fitToScreen();
      }
    });

    setTimeout(() => {
      if (panelStyle.value.willChange) {
        delete panelStyle.value.willChange;
      }
      isAnimating.value = false;
    }, 600);

  } else {
    // Exit Fullscreen
    if (!originalRect.value) {
      isFullScreen.value = false;
      panelStyle.value = {};
      return;
    }

    isExiting.value = true;
    isAnimating.value = true;
    panelStyle.value.top = '0px';
    panelStyle.value.left = '0px';
    panelStyle.value.width = '100vw';
    panelStyle.value.height = '100vh';
    panelStyle.value.borderRadius = '0px';
    panelStyle.value.transition = 'top 0.6s cubic-bezier(0.22, 1, 0.36, 1), left 0.6s cubic-bezier(0.22, 1, 0.36, 1), width 0.6s cubic-bezier(0.22, 1, 0.36, 1), height 0.6s cubic-bezier(0.22, 1, 0.36, 1), border-radius 0.6s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.6s cubic-bezier(0.22, 1, 0.36, 1)';
    panelStyle.value.boxShadow = '0 25px 50px -12px rgba(0, 0, 0, 0.25)';
    panelRef.value.offsetHeight;

    requestAnimationFrame(() => {
      panelStyle.value.top = `${originalRect.value!.top}px`;
      panelStyle.value.left = `${originalRect.value!.left}px`;
      panelStyle.value.width = `${originalRect.value!.width}px`;
      panelStyle.value.height = `${originalRect.value!.height}px`;
      panelStyle.value.borderRadius = '16px';
      panelStyle.value.boxShadow = '0 0 0 0 rgba(0,0,0,0)';
      if (activeArtifact.value?.type === 'mermaid' && mermaidRendererRef.value?.fitToScreen) {
        mermaidRendererRef.value.fitToScreen(true, originalRect.value!.width, originalRect.value!.height);
      }
      if (cameraCanvasUIRef.value?.fitToScreen) {
        cameraCanvasUIRef.value.fitToScreen();
      }
    });

    setTimeout(() => {
      panelStyle.value.transition = 'none';
      if (panelStyle.value.willChange) {
        delete panelStyle.value.willChange;
      }
      isFullScreen.value = false;
      isAnimating.value = false;
      requestAnimationFrame(() => {
        panelStyle.value = {};
        isExiting.value = false;
      });
      if (activeArtifact.value?.type === 'mermaid' && mermaidRendererRef.value?.fitToScreen) {
        mermaidRendererRef.value.fitToScreen(true);
      }
    }, 600);
  }
};

const handleCanvasFullscreenToggleRequest = () => {
  if (activeArtifact.value?.type !== 'docx') return;
  void toggleFullScreen();
};

const handleEscKey = (e: KeyboardEvent) => {
  if (e.key === 'Escape' && isFullScreen.value) {
    toggleFullScreen();
  }
};

// 截图功能：捕获 Canvas 内容并发送给 ChatInput
let screenshotSuccessTimer: ReturnType<typeof setTimeout> | null = null;

function clearScreenshotSuccessTimer() {
  if (screenshotSuccessTimer) {
    clearTimeout(screenshotSuccessTimer);
    screenshotSuccessTimer = null;
  }
}

const handleScreenshot = async () => {
  if (isScreenshoting.value) return;

  const target = canvasContentRef.value;
  const targetUrl = currentBrowseUrl.value;

  if (!target) {
    NotificationService.warning('无法获取 Canvas 内容');
    return;
  }

  if (!targetUrl) {
    NotificationService.warning('没有可截图的 URL');
    return;
  }

  const rect = target.getBoundingClientRect();
  const width = Math.round(rect.width);
  const height = Math.round(rect.height);

  console.log('[Screenshot] canvas-content 容器尺寸:', {
    clientWidth: target.clientWidth,
    clientHeight: target.clientHeight,
    offsetWidth: target.offsetWidth,
    offsetHeight: target.offsetHeight,
    boundingRect: { width, height },
  });

  clearScreenshotSuccessTimer();
  emit('screenshot-start');
  isScreenshoting.value = true;
  screenshotAnimationPhase.value = 'capturing';

  try {
    const blob = await captureScreenshot({
      url: targetUrl,
      width,
      height,
      isfullpage: false,
    });

    if (!blob || blob.size === 0) {
      NotificationService.warning('截图生成失败：返回空数据');
      screenshotAnimationPhase.value = 'idle';
      return;
    }

    const timestamp = new Date().getTime();
    const file = new File([blob], `screenshot_${timestamp}.png`, { type: 'image/png' });
    screenshotAnimationPhase.value = 'sending';
    await emit('screenshot', file);
    screenshotSuccessTimer = setTimeout(() => {
      screenshotAnimationPhase.value = 'idle';
      screenshotSuccessTimer = null;
    }, 720);
  } catch (error) {
    console.error('截图失败:', error);
    screenshotAnimationPhase.value = 'idle';
    NotificationService.error('截图失败，请稍后重试');
  } finally {
    isScreenshoting.value = false;
  }
};

onMounted(() => {
  window.addEventListener('keydown', handleEscKey);
  window.addEventListener(CANVAS_FULLSCREEN_TOGGLE_EVENT, handleCanvasFullscreenToggleRequest);
  document.addEventListener('click', closeScreeningDropdown);
});

watch(() => activeArtifact.value, async (newVal) => {
  if (pdfUrl.value && pdfUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(pdfUrl.value);
  }
  pdfUrl.value = '';
  pdfError.value = '';
  docxBuffer.value = null;
  docxLoading.value = false;
  docxError.value = '';
  htmlLoading.value = false;
  htmlError.value = '';
  htmlRemoteContent.value = '';
  markdownLoading.value = false;
  markdownError.value = '';
  markdownRemoteContent.value = '';
  svgRemoteContent.value = '';
  jsonRemoteContent.value = '';

  if (!newVal || !newVal.content) {
    return;
  }

  if (newVal.type === 'docx') {
    const source = (newVal.url || (typeof newVal.content === 'string' ? newVal.content.trim() : '')).trim();
    if (!isRemoteUrl(source)) {
      return;
    }

    docxLoading.value = true;
    try {
      const response = await fetch(source, {
        credentials: 'omit',
        cache: 'no-store'
      });
      if (!response.ok) {
        throw new Error(`文档加载失败 (${response.status})`);
      }
      const contentType = response.headers.get('content-type') || '';
      if (contentType && !/octet-stream|wordprocessingml|zip|msword/i.test(contentType)) {
        console.warn('返回的内容类型可能不是有效的Word文档:', contentType);
      }
      docxBuffer.value = await response.arrayBuffer();
    } catch (error) {
      docxError.value = error instanceof Error ? error.message : 'Word 文档加载失败';
    } finally {
      docxLoading.value = false;
    }
    return;
  }

  if (newVal.type === 'pdf' && newVal.content) {
    try {
      const blob = await resolvePdfBlob(newVal);
      pdfUrl.value = URL.createObjectURL(blob);
    } catch (error) {
      pdfError.value = error instanceof Error ? error.message : 'PDF 预览失败';
    }
    return;
  }

  if (newVal.type === 'html') {
    const source = (newVal.url || (typeof newVal.content === 'string' ? newVal.content.trim() : '')).trim();
    if (!isRemoteUrl(source)) {
      return;
    }

    htmlLoading.value = true;
    try {
      htmlRemoteContent.value = await fetchHtmlAsText(source);
    } catch (error) {
      htmlError.value = error instanceof Error ? error.message : 'HTML 预览失败';
    } finally {
      htmlLoading.value = false;
    }
    return;
  }

  if (newVal.type === 'markdown') {
    const source = (newVal.url || (typeof newVal.content === 'string' ? newVal.content.trim() : '')).trim();
    if (!isRemoteUrl(source)) {
      return;
    }

    markdownLoading.value = true;
    try {
      markdownRemoteContent.value = await fetchMarkdownAsText(source);
    } catch (error) {
      markdownError.value = error instanceof Error ? error.message : 'Markdown 预览失败';
    } finally {
      markdownLoading.value = false;
    }
    return;
  }

  if (newVal.type === 'svg') {
    const source = (newVal.url || (typeof newVal.content === 'string' ? newVal.content.trim() : '')).trim();
    if (!isRemoteUrl(source)) {
      return;
    }

    htmlLoading.value = true;
    try {
      svgRemoteContent.value = await fetchSvgAsText(source);
    } catch (error) {
      htmlError.value = error instanceof Error ? error.message : 'SVG 预览失败';
    } finally {
      htmlLoading.value = false;
    }
    return;
  }

  if (newVal.type === 'json') {
    const source = (newVal.url || (typeof newVal.content === 'string' ? newVal.content.trim() : '')).trim();
    if (!isRemoteUrl(source)) {
      return;
    }

    htmlLoading.value = true;
    try {
      jsonRemoteContent.value = await fetchJsonAsText(source);
    } catch (error) {
      htmlError.value = error instanceof Error ? error.message : 'JSON 预览失败';
    } finally {
      htmlLoading.value = false;
    }
    return;
  }
}, { immediate: true });

onUnmounted(() => {
  stopUrlPolling();
  clearScreenshotSuccessTimer();
  window.removeEventListener('keydown', handleEscKey);
  window.removeEventListener(CANVAS_FULLSCREEN_TOGGLE_EVENT, handleCanvasFullscreenToggleRequest);
  document.removeEventListener('click', closeScreeningDropdown);
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value);
  }
});

watch(
  [isFullScreen, isExiting],
  ([fullScreen, exiting]) => {
    window.dispatchEvent(
      new CustomEvent(CANVAS_FULLSCREEN_CHANGE_EVENT, {
        detail: { isFullScreen: fullScreen, isExiting: exiting }
      })
    );
  },
  { immediate: true }
);

const refreshPreview = () => {
  refreshKey.value++;
};

const copyMarkdown = async () => {
  if (!activeArtifact.value || !artifactTextContent.value) return;
  
  try {
    await navigator.clipboard.writeText(artifactTextContent.value);
    NotificationService.success('已复制到剪贴板');
  } catch (err) {
    NotificationService.error('复制失败');
    console.error('Failed to copy text: ', err);
  }
};

const downloadHtmlOrSvg = () => {
  if (!activeArtifact.value || !artifactTextContent.value) return;
  
  const isSvg = activeArtifact.value.type === 'svg';
  const mimeType = isSvg ? 'image/svg+xml' : 'text/html';
  const ext = isSvg ? 'svg' : 'html';
  const extRegex = isSvg ? /\.svg$/i : /\.html$/i;
  const rawTitle = activeArtifact.value.title?.trim() || 'download';
  const blob = new Blob([artifactTextContent.value], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = extRegex.test(rawTitle) ? rawTitle : `${rawTitle}.${ext}`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const copyJsonContent = async () => {
  if (!activeArtifact.value || !artifactTextContent.value) return;
  try {
    // Try to pretty-print before copying
    const parsed = JSON.parse(artifactTextContent.value);
    await navigator.clipboard.writeText(JSON.stringify(parsed, null, 2));
  } catch {
    await navigator.clipboard.writeText(artifactTextContent.value);
  }
  NotificationService.success('JSON 已复制到剪贴板');
};

const downloadJson = () => {
  if (!activeArtifact.value || !artifactTextContent.value) return;
  const rawTitle = activeArtifact.value.title?.trim() || 'download';
  const blob = new Blob([artifactTextContent.value], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = /\.json$/i.test(rawTitle) ? rawTitle : `${rawTitle}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const downloadMarkdown = () => {
  if (!activeArtifact.value || !artifactTextContent.value) return;
  
  const blob = new Blob([artifactTextContent.value], { type: 'text/markdown' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const rawTitle = activeArtifact.value.title?.trim() || 'download.md';
  a.download = /\.md$/i.test(rawTitle) ? rawTitle : `${rawTitle}.md`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const downloadDocx = async () => {
  const fileName = getArtifactDownloadFileName(activeArtifact.value);
  if (wordCanvasEditorRef.value) {
    await wordCanvasEditorRef.value.exportDocx(fileName);
    return;
  }

  const source = getArtifactDownloadSource(activeArtifact.value);
  if (!source) {
    NotificationService.error('当前 Word 文档暂无可下载内容');
    return;
  }

  try {
    await downloadArtifactBySource(
      source,
      fileName,
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    );
  } catch (error) {
    console.error('下载 Word 文档失败:', error);
    NotificationService.error('Word 文档下载失败');
  }
};

const downloadExcel = async () => {
  const source = getArtifactDownloadSource(activeArtifact.value);
  const fileName = getArtifactDownloadFileName(activeArtifact.value);
  const mimeType = getArtifactDownloadMimeType(activeArtifact.value);

  if (excelCanvasRef.value) {
    try {
      await excelCanvasRef.value.exportXlsx(fileName);
      return;
    } catch (error) {
      console.error('画布导出 Excel 失败，回退到原始文件下载:', error);
    }
  }

  if (source) {
    try {
      await downloadArtifactBySource(source, fileName, mimeType);
      return;
    } catch (error) {
      console.error('下载原始 Excel 文件失败:', error);
    }
  }

  NotificationService.error('当前 Excel 文件暂无可下载内容');
};

const exportPpt = () => {
  pptCanvasRef.value?.triggerExport();
};

const screeningDropdownVisible = ref(false);

const closeScreeningDropdown = () => {
  screeningDropdownVisible.value = false;
};

const startScreening = (fromStart: boolean) => {
  pptCanvasRef.value?.triggerScreening(fromStart);
  screeningDropdownVisible.value = false;
};

const downloadTxt = () => {
  const fileName = (() => {
    const rawTitle = activeArtifact.value?.title?.trim() || 'document.txt';
    return /\.txt$/i.test(rawTitle) ? rawTitle : `${rawTitle}.txt`;
  })();
  if (txtCanvasEditorRef.value) {
    txtCanvasEditorRef.value.downloadTxt(fileName);
    return;
  }

  const source = txtSource.value;
  const text = typeof source === 'string' ? source : '';
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

const downloadPdf = async () => {
  const source = getArtifactDownloadSource(activeArtifact.value) || pdfUrl.value;
  if (!source) {
    NotificationService.error('当前 PDF 暂无可下载内容');
    return;
  }

  const fileName = getArtifactDownloadFileName(activeArtifact.value);
  try {
    await downloadArtifactBySource(source, fileName, 'application/pdf');
  } catch (error) {
    console.error('下载 PDF 失败:', error);
    NotificationService.error('PDF 下载失败');
  }
};

const getArtifactDownloadExtension = (artifact: Artifact | null) => {
  if (!artifact) return '';
  const titleExt = getArtifactFileExtension(artifact.title);
  if (titleExt) return titleExt;
  const urlExt = getArtifactFileExtension(artifact.url);
  if (urlExt) return urlExt;
  const contentExt = typeof artifact.content === 'string' ? getArtifactFileExtension(artifact.content) : '';
  if (contentExt) return contentExt;

  const type = artifact.type?.toLowerCase() || '';
  if (type === 'markdown') return 'md';
  if (type === 'text') return 'txt';
  if (type === 'docx' || type === 'pdf' || type === 'html' || type === 'svg') return type;
  if (type === 'ppt' || type === 'pptx') return 'pptx';
  if (type === 'xls' || type === 'xlsx') return 'xlsx';
  if (type === 'csv') return 'csv';
  return '';
};

const getArtifactDownloadMimeType = (artifact: Artifact | null) => {
  const ext = getArtifactDownloadExtension(artifact);
  switch (ext) {
    case 'ppt':
      return 'application/vnd.ms-powerpoint';
    case 'pptx':
      return 'application/vnd.openxmlformats-officedocument.presentationml.presentation';
    case 'xls':
      return 'application/vnd.ms-excel';
    case 'xlsx':
      return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
    case 'csv':
      return 'text/csv;charset=utf-8';
    default:
      return 'application/octet-stream';
  }
};

const getArtifactDownloadFileName = (artifact: Artifact | null) => {
  if (!artifact) return 'download';
  const urlExt = getArtifactFileExtension(artifact.url);
  if (artifact.url && urlExt) {
    const fileName = extractFileNameFromSource(artifact.url);
    if (fileName) return fileName;
  }

  const rawTitle = artifact.title?.trim() || 'download';
  const ext = getArtifactDownloadExtension(artifact);
  if (!ext) return rawTitle;
  return new RegExp(`\\.${ext}$`, 'i').test(rawTitle) ? rawTitle : `${rawTitle}.${ext}`;
};

const getArtifactDownloadSource = (artifact: Artifact | null) => {
  if (!artifact) return null;
  if (artifact.downloadUrl?.trim()) return artifact.downloadUrl.trim();
  if (artifact.url?.trim()) return artifact.url.trim();
  if (typeof artifact.content === 'string') return artifact.content.trim();
  if (artifact.content instanceof ArrayBuffer || ArrayBuffer.isView(artifact.content)) {
    return artifact.content;
  }
  return null;
};

const triggerBrowserDownload = (href: string, fileName: string) => {
  const a = document.createElement('a');
  a.href = href;
  a.download = fileName;
  a.rel = 'noopener';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
};

const toArrayBuffer = (binary: ArrayBuffer | ArrayBufferView): ArrayBuffer => {
  if (binary instanceof ArrayBuffer) {
    return binary;
  }

  const view = new Uint8Array(binary.buffer, binary.byteOffset, binary.byteLength);
  return view.slice().buffer;
};

const downloadArtifactBinary = (binary: ArrayBuffer | ArrayBufferView, fileName: string, mimeType: string) => {
  const blob = new Blob([toArrayBuffer(binary)], { type: mimeType });
  const downloadUrl = URL.createObjectURL(blob);
  triggerBrowserDownload(downloadUrl, fileName);
  setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
};

const downloadArtifactBySource = async (source: string | ArrayBuffer | ArrayBufferView, fileName: string, mimeType: string) => {
  if (source instanceof ArrayBuffer || ArrayBuffer.isView(source)) {
    downloadArtifactBinary(source, fileName, mimeType);
    return;
  }

  if (!source) {
    throw new Error('下载链接为空');
  }

  if (/^(blob:|data:)/i.test(source)) {
    triggerBrowserDownload(source, fileName);
    return;
  }

  try {
    const response = await fetch(source, {
      credentials: 'omit',
      cache: 'no-store'
    });
    if (!response.ok) {
      throw new Error(`文件下载失败 (${response.status})`);
    }
    const responseType = response.headers.get('content-type') || mimeType;
    const blob = await response.blob();
    const downloadUrl = URL.createObjectURL(new Blob([blob], { type: responseType || mimeType }));
    triggerBrowserDownload(downloadUrl, fileName);
    setTimeout(() => URL.revokeObjectURL(downloadUrl), 0);
  } catch (error) {
    console.warn('Canvas 文件下载回退到浏览器默认下载:', error);
    triggerBrowserDownload(source, fileName);
  }
};

const unsupportedFileDownloadTitle = computed(() => {
  switch (unsupportedFilePreviewKind.value) {
    case 'EXCEL':
      return '下载 Excel';
    default:
      return '下载文件';
  }
});

const downloadUnsupportedFile = async () => {
  const source = getArtifactDownloadSource(activeArtifact.value);
  if (!source) {
    NotificationService.error('当前文件暂无可下载内容');
    return;
  }

  try {
    await downloadArtifactBySource(
      source,
      getArtifactDownloadFileName(activeArtifact.value),
      getArtifactDownloadMimeType(activeArtifact.value)
    );
  } catch (error) {
    console.error('下载文件失败:', error);
    NotificationService.error('文件下载失败');
  }
};

const artifactTextContent = computed(() => {
  if (activeArtifact.value?.type === 'html' && htmlRemoteContent.value) {
    return htmlRemoteContent.value;
  }
  if (activeArtifact.value?.type === 'markdown' && markdownRemoteContent.value) {
    return markdownRemoteContent.value;
  }
  if (activeArtifact.value?.type === 'svg' && svgRemoteContent.value) {
    return svgRemoteContent.value;
  }
  if (activeArtifact.value?.type === 'json' && jsonRemoteContent.value) {
    return jsonRemoteContent.value;
  }
  const c = activeArtifact.value?.content;
  if (typeof c === 'string') return c;
  if (!isTextLikeArtifactType(activeArtifact.value?.type)) return '';
  return decodeTextArtifactContent(c);
});

watch(artifactTextContent, async () => {
  if (
    activeArtifact.value?.type === 'markdown' &&
    markdownPreviewRef.value
  ) {
    await nextTick();
    if (isMarkdownAutoScroll.value) {
      markdownPreviewRef.value.scrollTop = markdownPreviewRef.value.scrollHeight;
    }
    checkMarkdownScroll();
  }
});

const editableTextContent = computed({
  get: () => artifactTextContent.value,
  set: (v: string) => {
    if (activeArtifact.value?.type === 'html' && htmlRemoteContent.value) {
      htmlRemoteContent.value = v;
      return;
    }
    if (activeArtifact.value?.type === 'markdown' && markdownRemoteContent.value) {
      markdownRemoteContent.value = v;
      return;
    }
    if (activeArtifact.value?.type === 'svg' && svgRemoteContent.value) {
      svgRemoteContent.value = v;
      return;
    }
    if (activeArtifact.value?.type === 'json' && jsonRemoteContent.value) {
      jsonRemoteContent.value = v;
      return;
    }
    if (activeArtifact.value && typeof activeArtifact.value.content === 'string') {
      activeArtifact.value.content = v;
    }
  }
});

const handleTxtChange = (value: string) => {
  if (activeArtifact.value) {
    activeArtifact.value.content = value;
  }
};

const getArtifactFileExtension = (value?: string) => {
  if (!value) return '';
  const cleanName = extractFileNameFromSource(value.trim()).toLowerCase();
  const lastDotIndex = cleanName.lastIndexOf('.');
  if (lastDotIndex < 0 || lastDotIndex === cleanName.length - 1) {
    return '';
  }
  return cleanName.slice(lastDotIndex + 1);
};

const unsupportedFilePreviewKind = computed(() => {
  const ext = getArtifactFileExtension(activeArtifact.value?.title);
  const type = activeArtifact.value?.type?.toLowerCase() || '';

  if (ext === 'csv' || type === 'csv') return 'EXCEL';

  return '';
});

const showViewTabs = computed(() => {
  const type = activeArtifact.value?.type?.toLowerCase();
  if (!type) return false;
  if (unsupportedFilePreviewKind.value) return false;
  return type !== 'docx' && type !== 'pdf' && type !== 'url' && type !== 'json' && type !== 'map'&& !isTxtArtifact.value && !isExcelArtifact.value && !isPptArtifact.value;
});

const unsupportedFilePreviewIconSrc = computed(() => {
  switch (unsupportedFilePreviewKind.value) {
    case 'EXCEL':
      return excelIcon;
    default:
      return txtIcon;
  }
});

const unsupportedFilePreviewDescription = computed(() => {
  switch (unsupportedFilePreviewKind.value) {
    case 'EXCEL':
      return 'Excel 文件暂时无法在 Canvas 中直接预览';
    default:
      return '当前 Canvas 暂不支持该文件类型预览';
  }
});

watch(unsupportedFilePreviewKind, (kind) => {
  if (kind && viewMode.value !== 'preview') {
    viewMode.value = 'preview';
  }
}, { immediate: true });

const docxSource = computed(() => {
  if (docxBuffer.value) return docxBuffer.value;
  const c = activeArtifact.value?.content;
  if (c instanceof ArrayBuffer || ArrayBuffer.isView(c)) return c;
  const fromContent = typeof c === 'string' ? c.trim() : '';
  const fromUrl = activeArtifact.value?.url?.trim() || '';
  return fromContent || fromUrl || null;
});

const excelSource = computed(() => {
  const c = activeArtifact.value?.content;
  if (c instanceof ArrayBuffer || ArrayBuffer.isView(c)) return c;
  const fromContent = typeof c === 'string' ? c.trim() : '';
  const fromUrl = activeArtifact.value?.url?.trim() || '';
  return fromContent || fromUrl || null;
});

const pptSource = computed(() => {
  const c = activeArtifact.value?.content;
  if (c instanceof ArrayBuffer || ArrayBuffer.isView(c)) return c;
  const fromContent = typeof c === 'string' ? c.trim() : '';
  const fromUrl = activeArtifact.value?.url?.trim() || '';
  return fromContent || fromUrl || null;
});

const txtSource = computed(() => activeArtifact.value?.content ?? '');

const fetchPdfAsBlob = async (url: string): Promise<Blob> => {
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`PDF 加载失败 (${response.status})`);
  }
  const contentType = response.headers.get('content-type') || '';
  if (contentType && !/pdf|octet-stream/i.test(contentType)) {
    throw new Error('返回内容不是 PDF 文件');
  }
  return await response.blob();
};

const fetchMarkdownAsText = async (url: string): Promise<string> => {
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`Markdown 加载失败 (${response.status})`);
  }
  return await response.text();
};

const fetchHtmlAsText = async (url: string): Promise<string> => {
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`HTML 加载失败 (${response.status})`);
  }
  return await response.text();
};

const fetchSvgAsText = async (url: string): Promise<string> => {
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`SVG 加载失败 (${response.status})`);
  }
  return await response.text();
};

const fetchJsonAsText = async (url: string): Promise<string> => {
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`JSON 加载失败 (${response.status})`);
  }
  return await response.text();
};

const isRemoteUrl = (value?: string) => {
  if (!value) return false;
  return /^https?:\/\//i.test(value.trim());
};

const arrayBufferToPdfBlob = (content: ArrayBuffer | ArrayBufferView): Blob => {
  return new Blob([toArrayBuffer(content)], { type: 'application/pdf' });
};

const resolvePdfBlob = async (artifact: Artifact): Promise<Blob> => {
  const content = artifact.content;

  if (content instanceof ArrayBuffer || ArrayBuffer.isView(content)) {
    return arrayBufferToPdfBlob(content);
  }

  const source = (artifact.url || (typeof content === 'string' ? content.trim() : '')).trim();
  if (!source) {
    throw new Error('PDF 链接为空');
  }

  return await fetchPdfAsBlob(source);
};

const isPendingSvg = computed(() => {
  if (activeArtifact.value?.type !== 'svg') return false;
  if (svgRemoteContent.value || htmlError.value) return false;
  const source = (activeArtifact.value.url || (typeof activeArtifact.value.content === 'string' ? activeArtifact.value.content.trim() : '')).trim();
  return isRemoteUrl(source);
});

const isPendingJson = computed(() => {
  if (activeArtifact.value?.type !== 'json') return false;
  if (jsonRemoteContent.value || htmlError.value) return false;
  const source = (activeArtifact.value.url || (typeof activeArtifact.value.content === 'string' ? activeArtifact.value.content.trim() : '')).trim();
  return isRemoteUrl(source);
});

const previewContent = computed(() => {
  if (!activeArtifact.value) return '';
  if (activeArtifact.value.type === 'svg' && isPendingSvg.value) {
    return '';
  }
  if (activeArtifact.value.type === 'json' && isPendingJson.value) {
    return '';
  }

  const content = artifactTextContent.value;

  if (activeArtifact.value.type === 'html' || activeArtifact.value.type === 'svg') {
    return getHtmlPreviewContent(content, activeArtifact.value.type as 'html' | 'svg');
  }

  return content;
});

const htmlPreviewUrl = computed(() => {
  const artifact = activeArtifact.value;
  if (!artifact || artifact.type !== 'html') return '';
  if (htmlRemoteContent.value) return '';
  const content = typeof artifact.content === 'string' ? artifact.content.trim() : '';
  const source = artifact.url?.trim() || content;
  return isRemoteUrl(source) ? source : '';
});

const deriveFileTitle = (value: string | undefined, extensionPattern: RegExp) => {
  if (!value) return '';
  const name = extractFileNameFromSource(value);
  if (!name) return '';
  return name.replace(extensionPattern, '');
};

const deriveDocxTitle = (value?: string) => deriveFileTitle(value, /\.docx$/i);
const derivePptTitle = (value?: string) => deriveFileTitle(value, /\.pptx?$/i);

const clearCanvas = () => {
  if (pdfUrl.value && pdfUrl.value.startsWith('blob:')) {
    URL.revokeObjectURL(pdfUrl.value);
  }
  clearScreenshotSuccessTimer();
  screenshotAnimationPhase.value = 'idle';
  activeArtifact.value = null;
  viewMode.value = 'preview';
  refreshKey.value = 0;
  pdfUrl.value = '';
  isFullScreen.value = false;
  isExiting.value = false;
  isAnimating.value = false;
  panelStyle.value = {};
  placeholderStyle.value = {};
  iframeReady.value = false;
  isCodeAtBottom.value = true;
  isMarkdownAtBottom.value = true;
  isMarkdownAutoScroll.value = true;
};

// Expose method to set artifact manually
const setArtifact = (code: Artifact['content'], lang: string, id?: string, isComplete: boolean = true, titleOverride?: string, downloadUrl?: string) => {
  let normalizedLang = lang.toLowerCase().trim();
  if (normalizedLang === 'txt') normalizedLang = 'text';
  if (normalizedLang === 'md') normalizedLang = 'markdown';
  const normalizedContent = isTextLikeArtifactType(normalizedLang) ? decodeTextArtifactContent(code) : code;
  const shouldPreferPreview =
    normalizedLang === 'docx' ||
    normalizedLang === 'ppt' ||
    normalizedLang === 'pptx' ||
    normalizedLang === 'pdf' ||
    normalizedLang === 'html' ||
    normalizedLang === 'svg' ||
    (normalizedLang === 'markdown' &&
      typeof normalizedContent === 'string' &&
      isRemoteUrl(normalizedContent.trim()));

  let title = 'Code Snippet';
  if (normalizedLang === 'mermaid') title = 'Mermaid';
  else if (normalizedLang === 'html') title = 'Web Preview';
  else if (normalizedLang === 'svg') title = 'SVG Image';
  else if (normalizedLang === 'json') title = 'JSON 文件';
  else if (normalizedLang === 'markdown') title = 'Markdown';
  else if (normalizedLang === 'docx') title = 'Word 文档';
  else if (normalizedLang === 'ppt' || normalizedLang === 'pptx') title = 'PPT 演示文稿';
  else if (normalizedLang === 'text') title = 'TXT 文档';
  else if (normalizedLang === 'url') title = '网页链接';
  else if (normalizedLang === 'map') title = '地图';
  if (titleOverride) title = titleOverride;
  if (normalizedLang === 'docx' && (!titleOverride || titleOverride === 'Word 文档')) {
    const fromCode = typeof code === 'string' ? deriveDocxTitle(code) : '';
    const fromUrl = activeArtifact.value?.url ? deriveDocxTitle(activeArtifact.value.url) : '';
    if (fromCode) title = fromCode;
    else if (fromUrl) title = fromUrl;
  }
  if ((normalizedLang === 'ppt' || normalizedLang === 'pptx') && (!titleOverride || titleOverride === 'PPT 演示文稿')) {
    const fromCode = typeof code === 'string' ? derivePptTitle(code) : '';
    const fromUrl = activeArtifact.value?.url ? derivePptTitle(activeArtifact.value.url) : '';
    if (fromCode) title = fromCode;
    else if (fromUrl) title = fromUrl;
  }
  

  const normalizedCode = typeof normalizedContent === 'string' ? normalizedContent.trim() : null;
  const artifactId = id || `manual-${Date.now()}`;

  // Check if content matches current artifact to prevent redundant animation
  if (activeArtifact.value && 
      activeArtifact.value.type.toLowerCase() === normalizedLang &&
      activeArtifact.value.id === artifactId) {
    
    // For ArrayBuffer content (docx, pdf), direct comparison is not trivial, so we assume update
    const currentContent = activeArtifact.value.content;
    const isBuffer = currentContent instanceof ArrayBuffer || ArrayBuffer.isView(currentContent);
    
    if (!isBuffer) {
        const currentContentStr = typeof currentContent === 'string' ? currentContent.trim() : null;
        if (currentContentStr !== null && normalizedCode !== null && currentContentStr === normalizedCode) {
          // Content is same, just update status and title if needed
          if (isComplete) activeArtifact.value.isComplete = true;
          if (activeArtifact.value.title !== title) activeArtifact.value.title = title;
          if (downloadUrl) activeArtifact.value.downloadUrl = downloadUrl;
          return;
        }
    }
  }

  if (activeArtifact.value && activeArtifact.value.id === artifactId) {
    const currentContent = activeArtifact.value.content;
    const currentIsBuffer = currentContent instanceof ArrayBuffer || ArrayBuffer.isView(currentContent);
    const incomingIsString = typeof normalizedContent === 'string';
    if ((normalizedLang === 'docx' || normalizedLang === 'ppt' || normalizedLang === 'pptx') && currentIsBuffer && incomingIsString) {
      activeArtifact.value.url = normalizedContent.trim();
      const derivedTitle = normalizedLang === 'docx' ? deriveDocxTitle(normalizedContent) : derivePptTitle(normalizedContent);
      if (derivedTitle) title = derivedTitle;
      activeArtifact.value.isComplete = isComplete;
      if (activeArtifact.value.title !== title) activeArtifact.value.title = title;
      if (downloadUrl) activeArtifact.value.downloadUrl = downloadUrl;
      viewMode.value = 'preview';
      return;
    }
    activeArtifact.value.content = normalizedContent;
    if ((normalizedLang === 'docx' || normalizedLang === 'ppt' || normalizedLang === 'pptx') && incomingIsString) {
      activeArtifact.value.url = normalizedContent.trim();
    } else if ((normalizedLang === 'html' || normalizedLang === 'svg') && incomingIsString && isRemoteUrl(normalizedContent.trim())) {
      activeArtifact.value.url = normalizedContent.trim();
    } else if (normalizedLang === 'html' || normalizedLang === 'svg') {
      activeArtifact.value.url = undefined;
    }
    activeArtifact.value.isComplete = isComplete;
    if (activeArtifact.value.title !== title) activeArtifact.value.title = title;
    activeArtifact.value.downloadUrl = downloadUrl;
  } else {
    activeArtifact.value = {
      id: artifactId,
      type: normalizedLang,
      title,
      content: normalizedContent,
      isComplete,
      downloadUrl,
      url:
        typeof normalizedContent === 'string' &&
        (normalizedLang === 'url' || normalizedLang === 'docx' || normalizedLang === 'ppt' || normalizedLang === 'pptx' || ((normalizedLang === 'html' || normalizedLang === 'svg') && isRemoteUrl(normalizedContent.trim())))
          ? normalizedContent.trim()
          : undefined
    };

    // 对以预览为主的产物，打开时优先进入预览模式；JSON 固定进入代码模式。
    if (normalizedLang === 'json') {
      viewMode.value = 'code';
    } else if (shouldPreferPreview || viewMode.value !== 'code') {
      viewMode.value = 'preview'; 
    }
  }
};

const titleIcon = computed(() => {
  if (!activeArtifact.value) return '';
  const type = activeArtifact.value.type.toLowerCase();
  const ext = getArtifactFileExtension(activeArtifact.value.title);
  
  if (type === 'mermaid') {
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><rect x="9" y="3" width="6" height="6" rx="1"></rect><rect x="3" y="15" width="6" height="6" rx="1"></rect><rect x="15" y="15" width="6" height="6" rx="1"></rect><path d="M12 9v3"></path><path d="M12 12H6v3"></path><path d="M12 12h6v3"></path></svg>`;
  }
  
  if (type === 'html') {
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><polyline points="16 18 22 12 16 6"></polyline><polyline points="8 6 2 12 8 18"></polyline></svg>`;
  }

  if (type === 'svg') {
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><circle cx="12" cy="12" r="10"></circle><line x1="14.31" y1="8" x2="20.05" y2="17.94"></line><line x1="9.69" y1="8" x2="21.17" y2="8"></line><line x1="7.38" y1="12" x2="13.12" y2="2.06"></line><line x1="9.69" y1="16" x2="3.95" y2="6.06"></line><line x1="14.31" y1="16" x2="2.83" y2="16"></line><line x1="16.62" y1="12" x2="10.88" y2="21.94"></line></svg>`;
  }

  if (type === 'json') {
    return `<img src="${jsonIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'docx') {
    return `<img src="${wordIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'markdown') {
    return `<img src="${markdownIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'pdf') {
    return `<img src="${pdfIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'text' || ext === 'txt') {
    return `<img src="${txtIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'ppt' || type === 'pptx' || ext === 'ppt' || ext === 'pptx') {
    return `<img src="${pptIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'xlsx' || type === 'xls' || type === 'csv' || ext === 'xls' || ext === 'xlsx' || ext === 'csv') {
    return `<img src="${excelIcon}" style="width: 14px; height: 14px;" />`;
  }

  if (type === 'map') {
    return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/><circle cx="12" cy="9" r="2.5"/></svg>`;
  }
  // Default code/text icon
  return `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="mr-2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>`;
});

defineExpose({ setArtifact, clearCanvas });
</script>

<style scoped>
.canvas-panel-container {
  height: 100%;
  width: 100%;
  position: relative;
}

.canvas-panel-placeholder {
  width: 100%;
  height: 100%;
  visibility: hidden;
}

.canvas-panel {
  height: 100%;
  background: #fff;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  box-sizing: border-box;
  border-radius: 16px;
  overflow: hidden;
  /* Add border for light mode visibility */
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.canvas-panel.fullscreen-mode {
  /* Ensure it sits on top of chat UI but below Luckysheet menus (1004) */
  z-index: 1003;
}

.canvas-panel.is-animating :deep(iframe) {
  pointer-events: none;
}

.canvas-panel.is-animating .ppt-canvas-wrapper,
.canvas-panel.is-animating .excel-canvas-wrapper {
  contain: layout paint style;
}

.canvas-panel.fullscreen-mode.hide-fullscreen-header .canvas-header {
  display: none;
}

.canvas-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}

.canvas-header {
  padding: 0 18px;
  height: 40px;
  flex-shrink: 0;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #ffffff;
  z-index: 10;
  position: relative;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1 1 0;
}

.header-center {
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.view-tabs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 8px;
  position: relative;
  isolation: isolate;
  min-width: 135px;
}

.tab-glider {
  position: absolute;
  top: 4px;
  left: 4px;
  bottom: 4px;
  width: calc(50% - 4px);
  background: white;
  border-radius: 6px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
  transition: transform 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
  z-index: -1;
  pointer-events: none;
}

.view-tabs.is-code-mode .tab-glider {
  transform: translateX(100%);
}

.view-tabs.is-edit-mode .tab-glider {
  transform: translateX(100%);
}

.view-tabs button {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 5px 8px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #64748b;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: color 0.2s, transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  z-index: 1;
}

.view-tabs button.active {
  color: #303030;
  transform: scale(1.05);
}

.view-tabs button:hover:not(.active) {
  color: #334155;
}

.title {
  margin: 0;
  font-size: 14px;
  color: #121212;
  display: flex;
  align-items: center;
  min-width: 0;
}

.title-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  flex: 0 1 auto;
}

.title-icon {
  display: flex;
  align-items: center;
  margin-right: 6px;
  color: #ea580c;
}

.status-badge {
  font-size: 11px;
  color: #3b82f6;
  background: #eff6ff;
  padding: 4px 8px;
  border-radius: 6px;
  white-space: nowrap;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.close-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 7px;
  color: #94a3b8;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  transition: all 0.2s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: #f1f5f9;
  color: #334155;
}

.header-right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  min-width: 0;
  flex: 1 1 0;
  height: 100%;
}

.actions-group {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-right: 12px;
}

.screening-btn-group {
  position: relative;
  display: flex;
  align-items: center;
  height: 28px;
  border-radius: 6px;
  overflow: visible;
  background-color: #f1f5f9;
  margin-right: 12px;
}

.screening-main-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  padding: 0 10px;
  border: none;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 6px 0 0 6px;
}

.screening-main-btn:hover {
  color: #334155;
}

.screening-icon {
  width: 18px;
  height: 18px;
  display: block;
}

.screening-arrow-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  padding: 0 7px;
  border: none;
  border-left: 1px solid #e2e8f0;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
  border-radius: 0 6px 6px 0;
}

.screening-arrow-btn:hover {
  color: #334155;
}

.screening-btn-group:hover {
  background-color: #dfe6ec;
}

.screening-btn-group:hover .screening-main-btn,
.screening-btn-group:hover .screening-arrow-btn {
  color: #334155;
}

.screening-btn-group:hover .screening-arrow-btn {
  border-left-color: #cbd5e1;
}

.screening-dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  padding: 4px;
  z-index: 1000;
  min-width: 160px;
  white-space: nowrap;
}

.screening-dropdown-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 13px;
  color: #334155;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.15s;
}

.screening-dropdown-item:hover {
  background-color: #f1f5f9;
}

.screening-dropdown-item svg {
  flex-shrink: 0;
  color: #64748b;
}

.vertical-divider {
  width: 1px;
  height: 18px;
  background-color: #e2e8f0;
  margin-right: 12px;
}

.header-icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: none;
  background: transparent;
  color: #64748b;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  overflow: hidden;
}

.header-icon-btn:hover {
  background-color: #f1f5f9;
  color: #334155;
  transform: translateY(-1px);
}

.header-icon-btn:active {
  transform: translateY(0);
}

.header-icon-btn--fullscreen.is-active:hover {
  background-color: #f1f5f9;
  color: #334155;
}

.canvas-content {
  flex: 1;
  overflow: hidden;
  position: relative;
  background: #f8fafc;
  min-height: 0;
}

.content-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.preview-container,
.code-container {
  width: 100%;
  height: 100%;
  overflow: hidden;
  position: relative;
  min-height: 0;
  flex: 1;
}

.preview-container {
  display: flex;
  flex-direction: column;
  position: relative;
  align-items: stretch;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #94a3b8;
  font-size: 14px;
}

.html-preview {
  width: 100%;
  height: 100%;
  background: white;
  position: relative;
}

.html-controls {
  position: absolute;
  bottom: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 9999px;
  z-index: 20;
}

.excel-canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  contain: layout style;
}

.excel-canvas-wrapper.has-fullscreen-header :deep(.excel-canvas-full-ui) {
  top: 30px !important;
}

.excel-fullscreen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 12px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  z-index: 30;
}

.excel-fullscreen-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #334155;
}

.excel-fs-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.excel-fullscreen-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.ppt-canvas-wrapper {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
  contain: layout style;
}

.ppt-canvas-wrapper.has-fullscreen-header :deep(.ppt-canvas-full-ui) {
  top: 30px !important;
}

.ppt-fullscreen-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 3px 12px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  z-index: 30;
}

.ppt-fullscreen-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 500;
  color: #334155;
}

.ppt-fs-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.ppt-fullscreen-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}

.control-btn {
  position: relative;
  z-index: 10;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  border: 1px solid rgba(255, 255, 255, 0.4);
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  color: #334155;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
}

.canvas-controls {
  position: absolute;
  bottom: 45px;
  right: 30px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border-radius: 9999px;
  z-index: 20;
  background: rgba(255, 255, 255, 0.65);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  animation: controls-pop-in 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes controls-pop-in {
  from {
    opacity: 0;
    transform: translateY(10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes capture-line-shift {
  0% {
    opacity: 0.36;
    transform: scaleX(0.82);
  }
  50% {
    opacity: 0.95;
    transform: scaleX(1);
  }
  100% {
    opacity: 0.36;
    transform: scaleX(0.82);
  }
}

@keyframes screenshot-button-breathe {
  0%, 100% {
    box-shadow:
      0 12px 32px rgba(74, 144, 226, 0.2),
      0 0 0 1px rgba(255, 255, 255, 0.18) inset;
    filter: brightness(0.99);
  }
  50% {
    box-shadow:
      0 14px 36px rgba(74, 144, 226, 0.28),
      0 0 0 1px rgba(255, 255, 255, 0.26) inset;
    filter: brightness(1.05);
  }
}

@keyframes screenshot-button-sheen {
  0% {
    transform: translateX(-130%);
    opacity: 0;
  }
  18% {
    opacity: 0.85;
  }
  55% {
    transform: translateX(130%);
    opacity: 0.55;
  }
  100% {
    transform: translateX(130%);
    opacity: 0;
  }
}

@keyframes address-flow-shift {
  0% {
    transform: translateX(-135%);
    opacity: 0;
  }
  20% {
    opacity: 0.85;
  }
  60% {
    transform: translateX(115%);
    opacity: 0.52;
  }
  100% {
    transform: translateX(115%);
    opacity: 0;
  }
}

@keyframes capture-status-breathe {
  0%, 100% {
    opacity: 0.66;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-0.5px);
  }
}

@keyframes preview-veil-breathe {
  0%, 100% {
    opacity: 0.82;
  }
  50% {
    opacity: 1;
  }
}

@keyframes capture-overlay-float {
  0%, 100% {
    transform: translateY(0) scale(1);
    opacity: 0.96;
  }
  50% {
    transform: translateY(-1px) scale(0.9985);
    opacity: 1;
  }
}

@keyframes capture-soft-light-drift {
  0% {
    transform: translate3d(-18%, 12%, 0) scale(0.94);
    opacity: 0;
  }
  20% {
    opacity: 0.55;
  }
  50% {
    transform: translate3d(10%, -2%, 0) scale(1.02);
    opacity: 0.68;
  }
  100% {
    transform: translate3d(24%, -14%, 0) scale(1.06);
    opacity: 0;
  }
}

@keyframes capture-particle-drift {
  0% {
    transform: translate3d(0, 0, 0) scale(0.92);
    opacity: 0;
  }
  18% {
    opacity: var(--particle-opacity);
  }
  50% {
    transform: translate3d(calc(var(--particle-drift-x) * 0.55), calc(var(--particle-drift-y) * 0.55), 0) scale(1);
    opacity: calc(var(--particle-opacity) * 0.92);
  }
  100% {
    transform: translate3d(var(--particle-drift-x), var(--particle-drift-y), 0) scale(0.96);
    opacity: 0;
  }
}

@keyframes capture-particle-send {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: var(--particle-opacity);
  }
  55% {
    opacity: calc(var(--particle-opacity) * 0.95);
  }
  100% {
    transform: translate3d(var(--particle-send-x), var(--particle-send-y), 0) scale(0.4);
    opacity: 0;
  }
}

@keyframes capture-status-chip-float {
  0%, 100% {
    transform: translate(-50%, 0);
    opacity: 0.78;
  }
  50% {
    transform: translate(-50%, -2px);
    opacity: 1;
  }
}

@keyframes capture-send-ghost-fly {
  0% {
    transform: translate3d(0, 0, 0) scale(1);
    opacity: 0;
  }
  15% {
    opacity: 0.5;
  }
  100% {
    transform: translate3d(132px, -108px, 0) scale(0.32);
    opacity: 0;
  }
}

.fs-icon {
  width: 18px;
  height: 18px;
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.header-fs-icon {
  width: 14px;
  height: 14px;
  display: block;
}

.icon-switch-enter-active,
.icon-switch-leave-active {
  transition: opacity 0.3s ease;
}

.icon-switch-enter-from,
.icon-switch-leave-to {
  opacity: 0;
}

.preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* URL 浏览器导航栏样式 */
.canvas-header.url-browser-mode {
  padding: 8px 16px;
  background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(248,249,250,0.95) 100%);
  backdrop-filter: blur(12px) saturate(1.3);
  -webkit-backdrop-filter: blur(12px) saturate(1.3);
  border-bottom: 1px solid rgba(0,0,0,0.06);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.url-browser-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  position: relative;
  isolation: isolate;
  transition: transform 0.28s ease, filter 0.28s ease;
}

.url-browser-bar.is-capturing {
  filter: saturate(1.03);
}

.url-browser-capture-line {
  position: absolute;
  top: -8px;
  left: 18px;
  right: 18px;
  height: 2px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(54, 209, 220, 0), rgba(91, 134, 229, 0.9), rgba(54, 209, 220, 0));
  opacity: 0.9;
  transform-origin: center;
  animation: capture-line-shift 1.8s ease-in-out infinite;
  pointer-events: none;
}

.url-browser-nav-btns {
  display: flex;
  align-items: center;
  gap: 1px;
  flex-shrink: 0;
  padding: 2px;
  border-radius: 10px;
}

.url-browser-nav-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.url-browser-nav-btn:hover {
  background: rgba(0,0,0,0.06);
  color: #334155;
  transform: scale(1.05);
}

.url-browser-nav-btn:active {
  transform: scale(0.95);
  background: rgba(0,0,0,0.1);
}

.url-browser-nav-btn.screenshot-btn {
  background:
    radial-gradient(circle at 24% 26%, rgba(255, 255, 255, 0.5), transparent 34%),
    linear-gradient(135deg, #36d1dc 0%, #5b86e5 50%, #4a90e2 100%);
  color: #ffffff;
  border-radius: 12px;
  box-shadow:
    0 10px 24px rgba(74, 144, 226, 0.2),
    0 3px 10px rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(10px) saturate(1.1);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
}

.url-browser-nav-btn.screenshot-btn:hover {
  transform: translateY(-1px);
  box-shadow:
    0 14px 30px rgba(74, 144, 226, 0.28),
    0 5px 14px rgba(255, 255, 255, 0.1);
  filter: brightness(1.03);
  background:
    radial-gradient(circle at 24% 26%, rgba(255, 255, 255, 0.5), transparent 34%),
    linear-gradient(135deg, #36d1dc 0%, #5b86e5 50%, #4a90e2 100%);
}

.url-browser-nav-btn.screenshot-btn:active {
  transform: translateY(0);
  filter: brightness(0.95);
}

.url-browser-nav-btn.screenshot-btn:disabled {
  cursor: default;
}

.url-browser-nav-btn.screenshot-btn.is-capturing {
  position: relative;
  overflow: hidden;
  transform: none;
  background:
    radial-gradient(circle at 22% 24%, rgba(255, 255, 255, 0.7), transparent 34%),
    linear-gradient(135deg, rgba(54, 209, 220, 0.92) 0%, rgba(91, 134, 229, 0.96) 55%, rgba(74, 144, 226, 0.92) 100%);
  box-shadow:
    0 12px 32px rgba(74, 144, 226, 0.24),
    0 0 0 1px rgba(255, 255, 255, 0.22) inset;
  animation: screenshot-button-breathe 1.9s ease-in-out infinite;
}

.screenshot-btn-sheen {
  position: absolute;
  inset: 1px;
  border-radius: inherit;
  background: linear-gradient(115deg, rgba(255, 255, 255, 0) 18%, rgba(255, 255, 255, 0.18) 44%, rgba(255, 255, 255, 0.5) 52%, rgba(255, 255, 255, 0.14) 60%, rgba(255, 255, 255, 0) 78%);
  transform: translateX(-130%);
  animation: screenshot-button-sheen 1.5s ease-in-out infinite;
  pointer-events: none;
}

.screenshot-icon-img {
  width: 20px;
  height: 20px;
  margin-bottom: 3px;
  display: block;
  position: relative;
  z-index: 1;
  transition: transform 0.28s ease, filter 0.28s ease, opacity 0.28s ease;
}

.url-browser-nav-btn.screenshot-btn.is-capturing .screenshot-icon-img {
  transform: translateY(-0.5px) scale(0.98);
  filter: drop-shadow(0 1px 4px rgba(255, 255, 255, 0.28));
}

.url-browser-address {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
  height: 34px;
  padding: 0 16px;
  background: #ffffff;
  border: 1px solid rgba(0,0,0,0.08);
  border-radius: 10px;
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.03);
  transition: all 0.28s ease;
  position: relative;
  overflow: hidden;
  isolation: isolate;
}

.url-browser-address:focus-within,
.url-browser-address:hover {
  border-color: rgba(0,0,0,0.15);
  box-shadow: inset 0 1px 3px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.06);
}

.url-browser-address.is-capturing {
  border-color: rgba(91, 134, 229, 0.18);
  box-shadow:
    inset 0 1px 3px rgba(0,0,0,0.05),
    0 0 0 1px rgba(255, 255, 255, 0.45),
    0 8px 18px rgba(91, 134, 229, 0.08);
  background: linear-gradient(180deg, rgba(255,255,255,0.98) 0%, rgba(248,250,255,0.96) 100%);
}

.url-browser-address-flow {
  position: absolute;
  inset: 0;
  border-radius: inherit;
  background: linear-gradient(110deg, rgba(255,255,255,0) 18%, rgba(213, 232, 255, 0.2) 38%, rgba(148, 201, 255, 0.34) 50%, rgba(213, 232, 255, 0.18) 62%, rgba(255,255,255,0) 80%);
  transform: translateX(-130%);
  animation: address-flow-shift 2.2s ease-in-out infinite;
  pointer-events: none;
  z-index: 0;
}

.url-browser-globe-icon {
  flex-shrink: 0;
  color: #94a3b8;
  position: relative;
  z-index: 1;
  transition: color 0.28s ease, filter 0.28s ease;
}

.url-browser-globe-icon.is-capturing {
  color: #6b88d8;
  filter: drop-shadow(0 0 8px rgba(107, 136, 216, 0.18));
}

.url-browser-input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13px;
  color: #475569;
  font-family: inherit;
  padding: 0;
  position: relative;
  z-index: 1;
  transition: color 0.28s ease, opacity 0.28s ease;
}

.url-browser-input.is-capturing {
  color: #5d6c86;
  opacity: 0.88;
}

.url-browser-open-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: #94a3b8;
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: all 0.2s ease;
}

.url-browser-open-btn:hover {
  background: rgba(99, 102, 241, 0.08);
  color: #6366f1;
}

.url-browser-open-btn:active {
  transform: scale(0.92);
}

.url-browser-capture-status {
  position: relative;
  z-index: 1;
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #6b7fc7;
  padding-left: 8px;
  white-space: nowrap;
  animation: capture-status-breathe 1.8s ease-in-out infinite;
}

.url-browser-input::selection {
  background: rgba(99, 102, 241, 0.2);
}

.canvas-header.url-browser-mode .header-left {
  flex: 1 1 0;
}

.canvas-header.url-browser-mode .header-right {
  flex: 1 1 0;
  margin-left: 0;
}

.url-preview {
  width: 100%;
  height: 100%;
  position: relative;
  overflow: hidden;
  transition: box-shadow 0.28s ease, transform 0.28s ease, filter 0.28s ease;
}

.url-preview.is-capturing {
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.42);
  filter: saturate(0.99) brightness(0.996);
}

.url-preview.is-capturing::after,
.url-preview.is-sending::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(circle at center, rgba(255,255,255,0) 52%, rgba(18, 31, 53, 0.045) 100%);
  z-index: 1;
}

.url-preview-capture-veil {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
  background: linear-gradient(180deg, rgba(255,255,255,0.035) 0%, rgba(242,247,255,0.1) 100%);
  backdrop-filter: blur(1.5px) saturate(1.01);
  -webkit-backdrop-filter: blur(1.5px) saturate(1.01);
  animation: preview-veil-breathe 2.6s ease-in-out infinite;
}

.url-preview-capture-overlay {
  position: absolute;
  inset: 0;
  z-index: 3;
  pointer-events: none;
  overflow: hidden;
  animation: capture-overlay-float 3.2s ease-in-out infinite;
}

.url-preview-capture-overlay.phase-sending {
  animation: none;
}

.capture-soft-light {
  position: absolute;
  inset: -18%;
  background:
    radial-gradient(circle at 32% 44%, rgba(255,255,255,0.34) 0%, rgba(255,255,255,0.16) 18%, rgba(255,255,255,0) 42%),
    radial-gradient(circle at 68% 56%, rgba(140, 220, 255, 0.22) 0%, rgba(140, 220, 255, 0) 36%);
  mix-blend-mode: screen;
  filter: blur(10px);
  opacity: 0;
  animation: capture-soft-light-drift 4.2s ease-in-out infinite;
}

.url-preview-capture-overlay.phase-sending .capture-soft-light {
  opacity: 0.24;
  animation-duration: 0.72s;
}

.capture-status-chip {
  position: absolute;
  left: 50%;
  bottom: 20px;
  transform: translateX(-50%);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  border-radius: 999px;
  background: rgba(255,255,255,0.62);
  border: 1px solid rgba(255,255,255,0.42);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(10px) saturate(1.1);
  -webkit-backdrop-filter: blur(10px) saturate(1.1);
  color: #173a63;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.02em;
  white-space: nowrap;
  animation: capture-status-chip-float 2.8s ease-in-out infinite;
  z-index: 2;
}

.url-preview-capture-overlay.phase-sending .capture-status-chip {
  animation: none;
  color: #184a84;
}

.capture-send-ghost {
  position: absolute;
  left: 50%;
  top: 50%;
  width: min(38%, 220px);
  aspect-ratio: 1.45;
  border-radius: 16px;
  transform: translate(-50%, -50%);
  background: linear-gradient(180deg, rgba(255,255,255,0.34) 0%, rgba(255,255,255,0.14) 100%);
  border: 1px solid rgba(255,255,255,0.48);
  box-shadow: 0 18px 38px rgba(15, 23, 42, 0.1);
  backdrop-filter: blur(14px) saturate(1.05);
  -webkit-backdrop-filter: blur(14px) saturate(1.05);
  animation: capture-send-ghost-fly 0.72s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.url-preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: #fff;
  transition: transform 0.28s ease, filter 0.28s ease;
}

.url-preview.is-capturing .url-preview-iframe {
  transform: scale(0.9985);
  filter: saturate(0.985) brightness(0.992);
}

.url-preview.is-sending .url-preview-iframe {
  transform: scale(1);
  filter: saturate(0.992) brightness(0.996);
}

.html-loading {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.85);
  z-index: 5;
}


.text-preview {
  padding: 16px;
  overflow: auto;
  height: 100%;
  width: 100%;
  flex: 1;
  min-height: 0;
  box-sizing: border-box;
  text-align: left;
  scrollbar-width: thin;
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
}

.text-preview:hover {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
}

.text-preview::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.text-preview::-webkit-scrollbar-track {
  background-color: transparent;
}

.text-preview::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.text-preview:hover::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
}

.text-preview::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, 0.25);
}

.markdown-preview {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  min-height: 0;
  -webkit-overflow-scrolling: touch;
}

.unsupported-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background:
    radial-gradient(circle at 50% 12%, rgba(59, 130, 246, 0.10), transparent 26%),
    linear-gradient(180deg, #fbfdff 0%, #f8fafc 100%);
}

.unsupported-preview-card {
  position: relative;
  width: min(420px, 100%);
  padding: 32px 28px 28px;
  text-align: center;
}

.unsupported-preview-card::before {
  content: '';
  position: absolute;
  top: -64px;
  left: 50%;
  transform: translateX(-50%);
  width: 180px;
  height: 180px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(96, 165, 250, 0.18) 0%, rgba(96, 165, 250, 0) 72%);
  pointer-events: none;
}

.unsupported-preview-hero {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 18px;
}

.unsupported-preview-icon-shell {
  position: relative;
  z-index: 1;
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 22px;
  background: linear-gradient(180deg, #ffffff 0%, #eef4ff 100%);
  border: 1px solid rgba(191, 219, 254, 0.95);
  box-shadow:
    0 10px 24px rgba(37, 99, 235, 0.12),
    inset 0 1px 0 rgba(255, 255, 255, 0.85);
}

.unsupported-preview-icon {
  width: 34px;
  height: 34px;
  object-fit: contain;
}

.unsupported-preview-glow {
  position: absolute;
  inset: auto;
  width: 108px;
  height: 108px;
  border-radius: 999px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.16) 0%, rgba(59, 130, 246, 0) 72%);
  filter: blur(4px);
}

.unsupported-preview-title {
  margin-top: 4px;
  color: #0f172a;
  font-size: 19px;
  line-height: 1.3;
  font-weight: 700;
}

.unsupported-preview-desc {
  margin: 10px auto 0;
  max-width: 280px;
  color: #64748b;
  font-size: 14px;
  line-height: 1.8;
}

.text-preview pre {
  margin: 0;
  font-family: monospace;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.docx-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  font-size: 13px;
}

.docx-fetch-error {
  color: #b91c1c;
  font-size: 13px;
  padding: 12px 8px;
}

/* Transitions */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.slide-fade-enter-active,
.slide-fade-leave-active {
  transition: opacity 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-fade-enter-from,
.slide-fade-leave-to {
  opacity: 0;
}

.scale-fade-enter-active,
.scale-fade-leave-active {
  transition: opacity 0.2s cubic-bezier(0.4, 0, 0.2, 1), transform 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.scale-fade-enter-from {
  opacity: 0;
  transform: scale(0.98);
}

.scale-fade-leave-to {
  opacity: 0;
  transform: scale(1.02);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 20;
  backdrop-filter: blur(10px);
}

/* Premium Loading Exit Animation */
.loading-leave-leave-active {
  transition: all 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  /* Ensure it stays on top while fading out */
  z-index: 20; 
  pointer-events: none;
}

.loading-leave-leave-to {
  opacity: 0;
  transform: scale(1.05);
  backdrop-filter: blur(0px); /* Transition blur out for smoothness */
}

/* Premium Content Entrance Animation */
.content-enter-enter-active {
  transition: all 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

.content-enter-enter-from {
  opacity: 0;
  transform: translateY(15px) scale(0.98);
  filter: blur(8px);
}

.content-enter-enter-to {
  opacity: 1;
  transform: translateY(0) scale(1);
  filter: blur(0px);
}

</style>
