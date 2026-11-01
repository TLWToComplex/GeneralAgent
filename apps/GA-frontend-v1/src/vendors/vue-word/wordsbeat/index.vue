<template>

  <div
    ref="rootRef"
    class="word-container-pro"
    :class="{ 'word-container-pro--embedded': props.embedded }"
  >

    <div ref="ribbonRef" class="custom-ribbon-tabs">
      <div class="tabs-nav">
        <div class="tab-btn" :class="{ active: activeTab === '1' }" @click="activeTab = '1'">开始</div>
        <div class="tab-btn" :class="{ active: activeTab === '2' }" @click="activeTab = '2'">插入</div>
        <div class="tab-btn" :class="{ active: activeTab === '3' }" @click="activeTab = '3'">视图</div>
        <div class="tab-btn" :class="{ active: activeTab === '4' }" @click="activeTab = '4'">审阅</div>
        <div class="tab-btn" :class="{ active: activeTab === '5' }" @click="activeTab = '5'">公文模式</div>
        <div v-if="!props.embedded" class="tab-btn" :class="{ active: activeTab === '7' }" @click="activeTab = '7'">导入/导出</div>
        <div class="tabs-nav-right">
          <button
            v-if="isCanvasFullscreen && !isCanvasExiting"
            class="tabs-exit-fullscreen-btn header-icon-btn header-icon-btn--fullscreen"
            type="button"
            title="退出全屏 (Esc)"
            @click="requestExitCanvasFullscreen"
          >
            <svg class="header-fs-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M4 14h6v6M20 10h-6V4M14 10l7-7M10 14l-7 7" />
            </svg>
          </button>
          <button
            v-if="isCanvasFullscreen && !isCanvasExiting"
            class="tabs-exit-fullscreen-btn header-icon-btn"
            type="button"
            title="导出文档"
            @click="exportCurrentDocx()"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
          </button>
        </div>
      </div>
      <div
        class="tabs-content-shell"
        :class="{
          'has-scroll-controls': props.embedded && isToolbarOverflowing,
          'can-scroll-start': canToolbarScrollStart,
          'can-scroll-end': canToolbarScrollEnd
        }"
      >
      <button
        v-if="props.embedded && isToolbarOverflowing && canToolbarScrollStart"
        class="toolbar-scroll-btn toolbar-scroll-btn--left"
        type="button"
        aria-label="向左查看更多工具"
        @click="scrollToolbar('left')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <div ref="tabsContentRef" class="tabs-content" @scroll="updateToolbarScrollState">

        <div class="tab-pane" v-show="activeTab === '1'">
          <div class="menu" editor-component="menu">
            <div class="menu-item">
              <div class="menu-item__save" @click="saveToLocal(true)" title="保存 (Ctrl+S)"><i></i></div>

              <div class="menu-item__undo"><i></i></div>
              <div class="menu-item__redo"><i></i></div>
              <div class="menu-item__painter" title="格式刷(双击可连续使用)"><i></i></div>
              <div class="menu-item__format" title="清除格式"><i></i></div>
            </div>

            <div class="menu-item">
              <div class="menu-item__font">
                <span class="select" title="字体">
                  <span class="select__label">微软雅黑</span>
                  <span class="select__caret" aria-hidden="true"></span>
                </span>
                <div class="options">
                  <ul>
                    <li data-family="Microsoft YaHei" style="font-family:'Microsoft YaHei';">微软雅黑</li>
                    <li data-family="华文宋体" style="font-family:'华文宋体';">华文宋体</li>
                    <li data-family="华文黑体" style="font-family:'华文黑体';">华文黑体</li>
                    <li data-family="华文仿宋" style="font-family:'华文仿宋';">华文仿宋</li>
                    <li data-family="华文楷体" style="font-family:'华文楷体';">华文楷体</li>
                    <li data-family="华文琥珀" style="font-family:'华文琥珀';">华文琥珀</li>
                    <li data-family="华文楷体" style="font-family:'华文楷体';">华文楷体</li>
                    <li data-family="华文隶书" style="font-family:'华文隶书';">华文隶书</li>
                    <li data-family="华文新魏" style="font-family:'华文新魏';">华文新魏</li>
                    <li data-family="华文行楷" style="font-family:'华文行楷';">华文行楷</li>
                    <li data-family="华文中宋" style="font-family:'华文中宋';">华文中宋</li>
                    <li data-family="华文彩云" style="font-family:'华文彩云';">华文彩云</li>
                    <li data-family="Arial" style="font-family:'Arial';">Arial</li>
                    <li data-family="Segoe UI" style="font-family:'Segoe UI';">Segoe UI</li>
                    <li data-family="Ink Free" style="font-family:'Ink Free';">Ink Free</li>
                    <li data-family="Fantasy" style="font-family:'Fantasy';">Fantasy</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__size">
                <span class="select" title="字体">
                  <span class="select__label">小四</span>
                  <span class="select__caret" aria-hidden="true"></span>
                </span>
                <div class="options">
                  <ul>
                    <li data-size="56">初号</li>
                    <li data-size="48">小初</li>
                    <li data-size="34">一号</li>
                    <li data-size="32">小一</li>
                    <li data-size="29">二号</li>
                    <li data-size="24">小二</li>
                    <li data-size="21">三号</li>
                    <li data-size="20">小三</li>
                    <li data-size="18">四号</li>
                    <li data-size="16">小四</li>
                    <li data-size="14">五号</li>
                    <li data-size="12">小五</li>
                    <li data-size="10">六号</li>
                    <li data-size="8">小六</li>
                    <li data-size="7">七号</li>
                    <li data-size="6">八号</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__size-add"><i></i></div>
              <div class="menu-item__size-minus"><i></i></div>
              <div class="menu-item__bold"><i></i></div>
              <div class="menu-item__italic"><i></i></div>
              <div class="menu-item__underline">
                <i></i><span class="select"><span class="select__caret" aria-hidden="true"></span></span>
                <div class="options">
                  <ul>
                    <li data-decoration-style='solid'><i></i></li>
                    <li data-decoration-style='double'><i></i></li>
                    <li data-decoration-style='dashed'><i></i></li>
                    <li data-decoration-style='dotted'><i></i></li>
                    <li data-decoration-style='wavy'><i></i></li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__strikeout" title="删除线(Ctrl+Shift+X)"><i></i></div>
              <div class="menu-item__superscript"><i></i></div>
              <div class="menu-item__subscript"><i></i></div>
              <div class="menu-item__color" title="字体颜色"><i></i><span></span><input type="color" id="color" /></div>
              <div class="menu-item__highlight" title="高亮"><i></i><span></span><input type="color" id="highlight"></div>
            </div>

            <div class="menu-item">
              <div class="menu-item__title">
                <i></i><span class="select" title="切换标题"><span class="select__label">正文</span><span class="select__caret" aria-hidden="true"></span></span>
                <div class="options">
                  <ul>
                    <li style="font-size:14px;">正文</li>
                    <li data-level="first" style="font-size:18px; font-weight: bold;">标题1</li>
                    <li data-level="second" style="font-size:17px; font-weight: bold;">标题2</li>
                    <li data-level="third" style="font-size:16px; font-weight: bold;">标题3</li>
                    <li data-level="fourth" style="font-size:15px; font-weight: bold;">标题4</li>
                    <li data-level="fifth" style="font-size:14px; font-weight: bold;">标题5</li>
                    <li data-level="sixth" style="font-size:14px; font-weight: bold;">标题6</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__left"><i></i></div>
              <div class="menu-item__center"><i></i></div>
              <div class="menu-item__right"><i></i></div>
              <div class="menu-item__alignment"><i></i></div>
              <div class="menu-item__justify"><i></i></div>
              <div class="menu-item__first-line-indent">
                <i title="首行缩进"></i>
                <div class="options">
                  <ul>
                    <li data-firstlineindent="0">无</li>
                    <li data-firstlineindent="1">1 字符</li>
                    <li data-firstlineindent="2">2 字符</li>
                    <li data-firstlineindent="3">3 字符</li>
                    <li data-firstlineindent="4">4 字符</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__indent-minus" title="减少缩进"><i></i></div>
              <div class="menu-item__indent-add" title="增加缩进"><i></i></div>
              <div class="menu-item__row-margin">
                <i title="行间距"></i>
                <div class="options">
                  <ul>
                    <li data-rowmargin='1'>1</li>
                    <li data-rowmargin="1.25">1.25</li>
                    <li data-rowmargin="1.5">1.5</li>
                    <li data-rowmargin="1.75">1.75</li>
                    <li data-rowmargin="2">2</li>
                    <li data-rowmargin="2.5">2.5</li>
                    <li data-rowmargin="3">3</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__p-spacing-before">
                <i title="段前间距"></i>
                <div class="options">
                  <ul>
                    <li data-pspacing-before="0">0</li>
                    <li data-pspacing-before="0.5">0.5</li>
                    <li data-pspacing-before="1.0">1.0</li>
                    <li data-pspacing-before="1.2">1.2</li>
                    <li data-pspacing-before="1.5">1.5</li>
                    <li data-pspacing-before="2.0">2.0</li>
                    <li data-pspacing-before="2.5">2.5</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__p-spacing-after">
                <i title="段后间距"></i>
                <div class="options">
                  <ul>
                    <li data-pspacing-after="0">0</li>
                    <li data-pspacing-after="0.5">0.5</li>
                    <li data-pspacing-after="1.0">1.0</li>
                    <li data-pspacing-after="1.2">1.2</li>
                    <li data-pspacing-after="1.5">1.5</li>
                    <li data-pspacing-after="2.0">2.0</li>
                    <li data-pspacing-after="2.5">2.5</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__list">
                <i></i>
                <div class="options">
                  <ul>
                    <li><label>取消列表</label></li>
                    <li data-list-type="ol" data-list-style='decimal'><label>有序列表：</label>
                      <ol>
                        <li>________</li>
                      </ol>
                    </li>
                    <li data-list-type="ul" data-list-style='checkbox'><label>复选框列表：</label>
                      <ul style="list-style-type: '☑️ ';">
                        <li>________</li>
                      </ul>
                    </li>
                    <li data-list-type="ul" data-list-style='disc'><label>实心圆点列表：</label>
                      <ul style="list-style-type: disc;">
                        <li>________</li>
                      </ul>
                    </li>
                    <li data-list-type="ul" data-list-style='circle'><label>空心圆点列表：</label>
                      <ul style="list-style-type: circle;">
                        <li>________</li>
                      </ul>
                    </li>
                    <li data-list-type="ul" data-list-style='square'><label>空心方块列表：</label>
                      <ul style="list-style-type: '☐ ';">
                        <li>________</li>
                      </ul>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="tab-pane" v-show="activeTab === '2'">
          <div class="menu" editor-component="menu">
            <div class="menu-item">
              <div class="menu-item__table"><i title="表格"></i></div>
              <div class="menu-item__table__collapse">
                <div class="table-collapse__header">
                  <div class="table-title">
                    <span class="table-select"></span>
                    <span class="table-label">插入表格</span>
                  </div>
                  <button class="table-close" type="button" aria-label="关闭">×</button>
                </div>
                <div class="table-panel"></div>
                <div class="table-custom">
                  <input type="number" min="1" max="20" value="3" class="table-custom-rows" />
                  <span>×</span>
                  <input type="number" min="1" max="20" value="3" class="table-custom-cols" />
                  <button class="table-custom-btn">插入</button>
                </div>
              </div>
              <div class="menu-item__image">
                <i title="图片"></i><input type="file" id="image" accept=".png, .jpg, .jpeg, .svg, .gif">
              </div>
              <div class="menu-item__hyperlink"><i title="超链接"></i></div>
              <div class="menu-item__separator">
                <i title="分割线"></i>
                <div class="options">
                  <ul>
                    <li data-separator='0,0'><i></i></li>
                    <li data-separator="1,1"><i></i></li>
                    <li data-separator="3,1"><i></i></li>
                    <li data-separator="4,4"><i></i></li>
                    <li data-separator="7,3,3,3"><i></i></li>
                    <li data-separator="6,2,2,2,2,2"><i></i></li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__codeblock" title="代码块"><i></i></div>
              <div class="menu-item__page-break" title="分页符"><i></i></div>
              <div class="menu-item__control">
                <i title="控件"></i>
                <div class="options">
                  <ul>
                    <li data-control='text'>文本</li>
                    <li data-control="number">数值</li>
                    <li data-control="select">列举</li>
                    <li data-control="date">日期</li>
                    <li data-control="checkbox">复选框</li>
                    <li data-control="radio">单选框</li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__checkbox" title="复选框"><i></i></div>
              <div class="menu-item__radio" title="单选框"><i></i></div>
              <div class="menu-item__latex" title="LateX"><i></i></div>
              <div class="menu-item__date">
                <i title="日期"></i>
                <div class="options">
                  <ul>
                    <li data-format="yyyy-MM-dd"></li>
                    <li data-format="yyyy-MM-dd hh:mm:ss"></li>
                  </ul>
                </div>
              </div>
              <div class="menu-item__block" title="内容块"><i></i></div>
            </div>
          </div>
        </div>

        <div class="tab-pane" v-show="activeTab === '3'">
          <div class="menu" editor-component="menu">
            <div class="menu-item">
              <div class="menu-item__catalog catalog-mode" title="显示/隐藏目录"><i></i></div>

              <div class="menu-item__scale-minus page-scale-minus" title="缩小(Ctrl+-)"><i></i>
              </div>
              <span class="menu-item__scale-percentage page-scale-percentage" title="点击复原(Ctrl+0)">100%</span>
              <div class="menu-item__scale-add page-scale-add" title="放大(Ctrl+=)"><i></i></div>

              <div class="menu-item__fullscreen fullscreen" title="全屏显示(F11)"><i></i></div>
              <div class="menu-item__option editor-option" title="编辑器设置"><i></i></div>
            </div>
          </div>
        </div>

        <div class="tab-pane" v-show="activeTab === '4'">
          <div class="menu" editor-component="menu">
            <div class="menu-item">
              <div class="menu-item__search" data-menu="search">
                <i></i>
              </div>
              <div class="menu-item__search__collapse" data-menu="search">
                <div class="menu-item__search__collapse__search">
                  <input type="text" />
                  <label class="search-result"></label>
                  <div class="arrow-left"><i></i></div>
                  <div class="arrow-right"><i></i></div>
                  <span>×</span>
                </div>
                <div class="menu-item__search__collapse__replace">
                  <input type="text">
                  <button>替换</button>
                </div>
                <div class="menu-item__search__collapse__option">
                  <div class="search-option-item"><input type="checkbox" id="option-reg" checked /><label
                      for="option-reg">正则</label></div>
                  <div class="search-option-item"><input type="checkbox" id="option-case" checked /><label
                      for="option-case">忽略大小写</label></div>
                  <div class="search-option-item"><input type="checkbox" id="option-selection" /><label
                      for="option-selection">选定内容查找</label></div>
                </div>
              </div>

              <div class="menu-item__watermark">
                <i title="水印(添加、删除)"></i>
                <div class="options">
                  <ul>
                    <li data-menu="add">添加水印</li>
                    <li data-menu="delete">删除水印</li>
                  </ul>
                </div>
              </div>

              <div class="menu-item__print" data-menu="print">
                <i></i>
              </div>
            </div>
          </div>
        </div>

        <div class="tab-pane" v-show="activeTab === '5'">
          <div class="menu">
            <div class="menu-item">
              <div class="menu-item__redline" :class="{ active: redLineMenuVisible }" title="插入分隔红线">
                <i @click.stop="redLineMenuVisible = !redLineMenuVisible"></i>

                <div class="options" :class="{ visible: redLineMenuVisible }">
                  <ul>
                    <li @click="insertRedLine('standard')">
                      <div class="line-preview"></div>标准红线
                    </li>
                    <li @click="insertRedLine('thick')">
                      <div class="line-preview thick"></div>加粗红线
                    </li>
                    <li @click="insertRedLine('double')">
                      <div class="line-preview double"></div>双红线(文头线)
                    </li>
                    <li @click="insertRedLine('dashed')">
                      <div class="line-preview dashed"></div>虚线红线
                    </li>
                    <li @click="insertRedLine('custom')" class="custom-trigger"><i></i>自定义样式...</li>
                  </ul>
                </div>
              </div>

              <div class="menu-item__template" @click="showTemplateModal" title="公文模版画廊">
                <i></i>
              </div>
              <div class="menu-item__save-template" @click="saveCustomTemplate" title="存为自定义模版">
                <i></i>
              </div>
            </div>
          </div>
        </div>

        <div v-if="!props.embedded" class="tab-pane" v-show="activeTab === '7'">
          <div class="menu">
            <div class="menu-item">
              <div class="menu-item__import" @click="triggerImportWord" title="导入文稿 (.docx)">
                导入
              </div>
              <input type="file" ref="fileInputRef" accept=".docx" style="display: none" @change="handleImportWord" />

              <div class="menu-item__export" @click="handleExportWord" title="导出为 Word">
                导出
              </div>
            </div>
          </div>
        </div>



      </div>
      <button
        v-if="props.embedded && isToolbarOverflowing && canToolbarScrollEnd"
        class="toolbar-scroll-btn toolbar-scroll-btn--right"
        type="button"
        aria-label="向右查看更多工具"
        @click="scrollToolbar('right')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
      </div>
    </div>


    <div class="catalog" editor-component="catalog" v-show="isCatalogShow">
      <div class="catalog__header">
        <span>目录</span>
        <div class="catalog__header__close"><i></i></div>
      </div>
      <div class="catalog__main"></div>
    </div>
    <div ref="editorHostRef" :class="['editor', editorContainerClass]">
      <Transition name="doc-error-fade">
        <div v-if="docFormatError" class="doc-format-error-overlay" key="doc-format-error">
          <div class="doc-format-error-card">
            <div class="doc-format-error-icon">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/>
                <line x1="12" y1="8" x2="12" y2="12"/>
                <line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            <h3 class="doc-format-error-title">格式不支持</h3>
            <p class="doc-format-error-message">{{ docFormatError }}</p>
          </div>
        </div>
      </Transition>
    </div>
    <div class="comment" editor-component="comment"></div>
    <div ref="footerRef" class="footer" editor-component="footer">
      <div>
        <div class="catalog-mode" title="目录">
          <i></i>
        </div>
        <div class="page-mode">
          <i title="页面模式(分页、连页)"></i>
          <div class="options">
            <ul>
              <li data-page-mode="paging" class="active">分页</li>
              <li data-page-mode="continuity">连页</li>
            </ul>
          </div>
        </div>
        <div class="status-group">
          <span>可见页码：<span class="page-no-list">1</span></span>
          <span>页面：<span class="page-no">1</span>/<span class="page-size">1</span></span>
        </div>
        <div class="status-group">
          <span>字数：<span class="word-count">0</span></span>
        </div>
        <div class="status-group">
          <span>行：<span class="row-no">0</span></span>
          <span>列：<span class="col-no">0</span></span>
        </div>
        <div class="status-group save-status">
          <i :class="{ saving: isSaving }"></i>
          <span>{{ isSaving ? '保存中...' : (lastSavedTime ? '已保存 ' + lastSavedTime : '未保存') }}</span>
        </div>
      </div>
      <div class="editor-mode" title="编辑模式(编辑、清洁、只读、表单、设计、涂鸦)">编辑模式</div>
      <div>
        <div class="page-scale-minus" title="缩小(Ctrl+-)">
          <i></i>
        </div>
        <span class="page-scale-percentage" title="显示比例(点击可复原Ctrl+0)">100%</span>
        <div class="page-scale-add" title="放大(Ctrl+=)">
          <i></i>
        </div>
        <div class="paper-size">
          <i title="纸张类型"></i>
          <div class="options">
            <ul>
              <li data-paper-size="794*1123" class="active">A4</li>
              <li data-paper-size="1593*2251">A2</li>
              <li data-paper-size="1125*1593">A3</li>
              <li data-paper-size="565*796">A5</li>
              <li data-paper-size="412*488">5号信封</li>
              <li data-paper-size="450*866">6号信封</li>
              <li data-paper-size="609*862">7号信封</li>
              <li data-paper-size="862*1221">9号信封</li>
              <li data-paper-size="813*1266">法律用纸</li>
              <li data-paper-size="813*1054">信纸</li>
            </ul>
          </div>
        </div>
        <div class="paper-direction">
          <i title="纸张方向"></i>
          <div class="options">
            <ul>
              <li data-paper-direction="vertical" class="active">纵向</li>
              <li data-paper-direction="horizontal">横向</li>
            </ul>
          </div>
        </div>
        <div class="paper-margin" title="页边距"><i></i></div>
      </div>
    </div>

    <!-- 模版大库弹窗 -->
    <a-modal
      v-model:open="templateModalVisible"
      title="公文模版库画廊"
      :footer="null"
      width="600px"
      :maskClosable="false"
      wrap-class-name="wordsbeat-a-modal wordsbeat-template-gallery-modal"
      :zIndex="30000"
      centered
      @cancel="templateModalVisible = false"
    >
      <div class="template-gallery">
        <div class="template-card" v-for="(item, index) in templates" :key="index" @click="applyTemplate(item.id)"
          style="position: relative;">
          <div class="delete-btn" v-if="item.id.startsWith('custom_')" @click.stop="deleteCustomTemplate(item.id)"
            title="删除模版">×</div>
          <div class="template-cover">
            <div class="mock-doc" :class="item.type">
              <div class="head" v-if="item.type === 'red-head' || item.type === 'report'">{{ item.type === 'red-head' ?
                '发文'
                : '报告' }}</div>
              <div class="head" v-if="item.type === 'meeting'">纪要</div>
              <div class="line"
                v-if="item.id === 'standard' || item.id === 'notice' || item.id === 'decision' || item.id === 'announcement'"
                style="background: #ff0000; height: 2px; margin: 5px 0;"></div>
              <div class="line" v-if="item.id === 'double'"
                style="border-top: 1px solid #ff0000; border-bottom: 2px solid #ff0000; height: 4px; margin: 5px 0;">
              </div>
              <div class="mock-text mock-text-1"></div>
              <div class="mock-text mock-text-2"></div>
              <div class="mock-text mock-text-3"></div>
            </div>
          </div>
          <div class="template-title">{{ item.name }}</div>
        </div>
      </div>
      <div class="wordsbeat-modal-actions">
        <a-button class="wordsbeat-modal-btn wordsbeat-modal-btn--cancel" @click="templateModalVisible = false">取消</a-button>
        <a-button type="primary" class="wordsbeat-modal-btn wordsbeat-modal-btn--confirm" @click="templateModalVisible = false">确定</a-button>
      </div>
    </a-modal>
  </div>

</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue';
import Editor, { ElementType, PaperDirection, type IElement } from './canvas-editor';
import { bindEditorUI } from './official-ui/menu-bindings';
import { parseDocxToElements } from './utils/docxImporter';
import { exportDocxFile } from './utils/docxExporter';
import { Dialog } from './official-ui/components/dialog/Dialog';
import { Modal } from 'ant-design-vue';
import { debounce } from './official-ui/utils';
import { dbService } from './utils/db';
import './official-ui/style.css';

type DocxSource = string | ArrayBuffer | ArrayBufferView | null | undefined;
const DOCX_MIME = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';

const props = withDefaults(
  defineProps<{
    source?: DocxSource
    title?: string
    embedded?: boolean
    suspend?: boolean
  }>(),
  {
    source: null,
    title: 'document.docx',
    embedded: false,
    suspend: false
  }
);

const isCatalogShow = ref(false);
let instance: Editor | null = null;
const templateModalVisible = ref(false);
const redLineMenuVisible = ref(false);
const activeTab = ref('1');
const isCanvasFullscreen = ref(false);
const isCanvasExiting = ref(false);
const fileInputRef = ref<HTMLInputElement | null>(null);
const editorHostRef = ref<HTMLDivElement | null>(null);
const rootRef = ref<HTMLDivElement | null>(null);
const ribbonRef = ref<HTMLDivElement | null>(null);
const tabsContentRef = ref<HTMLDivElement | null>(null);
const footerRef = ref<HTMLDivElement | null>(null);
const docFormatError = ref('');

/**
 * 检测 ArrayBuffer 是否为 ZIP 格式（.docx 基于 ZIP，.doc 是 CFBF 格式）
 * ZIP 文件的前 4 字节是 0x50 0x4B 0x03 0x04（即 "PK\x03\x04"）
 */
const isZipFormat = (buffer: ArrayBuffer): boolean => {
  if (buffer.byteLength < 4) return false;
  const view = new Uint8Array(buffer, 0, 4);
  return view[0] === 0x50 && view[1] === 0x4b && view[2] === 0x03 && view[3] === 0x04;
};
const editorContainerClass = `word-editor-scroll-${Math.random().toString(16).slice(2)}`;
let saveHotkeyHandler: ((e: KeyboardEvent) => void) | null = null;
let layoutObserver: ResizeObserver | null = null;
let toolbarScrollAnimationFrame: number | null = null;
let toolbarScrollTarget = 0;
const CANVAS_FULLSCREEN_TOGGLE_EVENT = 'canvas-fullscreen-toggle-request';
const CANVAS_FULLSCREEN_CHANGE_EVENT = 'canvas-fullscreen-change';

const lastSavedTime = ref('');
const isSaving = ref(false);
const DRAFT_KEY = 'wordsbeat_draft_data';
const isToolbarOverflowing = ref(false);
const canToolbarScrollStart = ref(false);
const canToolbarScrollEnd = ref(false);
let latestImportRequestId = 0;
let lastImportedSourceKey = '';
let currentDocxFileName = 'document.docx';
let currentPageLayout: DocxPageLayout | null = null;

watch(
  () => props.embedded,
  embedded => {
    if (embedded && activeTab.value === '7') {
      activeTab.value = '1';
    }
    void nextTick(() => {
      syncLayoutMetrics();
      updateToolbarScrollState();
    });
  },
  { immediate: true }
);

watch(activeTab, () => {
  void nextTick(() => {
    stopToolbarScrollAnimation();
    tabsContentRef.value?.scrollTo({ left: 0, behavior: 'auto' });
    syncLayoutMetrics();
    updateToolbarScrollState();
  });
});

const normalizeDocxFileName = (value?: string, fallback = 'document.docx') => {
  if (!value) return fallback;
  const trimmed = value.trim();
  if (!trimmed) return fallback;
  return trimmed.toLowerCase().endsWith('.docx') ? trimmed : `${trimmed}.docx`;
};

const buildSourceKey = (source: DocxSource) => {
  if (!source) return '';
  if (typeof source === 'string') return `url:${source.trim()}`;
  if (source instanceof ArrayBuffer) return `buf:${source.byteLength}`;
  return `view:${source.byteLength}`;
};

const toArrayBuffer = (value: Exclude<DocxSource, string | null | undefined>) => {
  if (value instanceof ArrayBuffer) return value;
  return value.buffer.slice(value.byteOffset, value.byteOffset + value.byteLength) as ArrayBuffer;
};

const resolveDocxArrayBuffer = async (source: DocxSource): Promise<ArrayBuffer | null> => {
  if (!source) return null;
  if (typeof source !== 'string') return toArrayBuffer(source);
  const url = source.trim();
  if (!url) return null;
  const response = await fetch(url, {
    credentials: 'omit',
    cache: 'no-store'
  });
  if (!response.ok) {
    throw new Error(`文档加载失败 (${response.status})`);
  }
  return await response.arrayBuffer();
};

type DocxPageLayout = {
  width: number;
  height: number;
  margins: [number, number, number, number];
  direction: PaperDirection;
};

const dxaToPx = (value: number) => Math.round(value / 15);

const parseDocxPageLayout = async (arrayBuffer: ArrayBuffer): Promise<DocxPageLayout | null> => {
  try {
    const zip = await import('jszip');
    const JSZip = zip.default;
    const docxZip = await JSZip.loadAsync(arrayBuffer);
    const docData = await docxZip.file('word/document.xml')?.async('text');
    if (!docData) return null;

    const xmlDoc = new DOMParser().parseFromString(docData, 'text/xml');
    const sectPrList = Array.from(xmlDoc.getElementsByTagName('w:sectPr'));
    const sectPr = sectPrList[sectPrList.length - 1];
    if (!sectPr) return null;

    const pgSz = sectPr.getElementsByTagName('w:pgSz')[0];
    const pgMar = sectPr.getElementsByTagName('w:pgMar')[0];
    const rawWidth = Number(pgSz?.getAttribute('w:w')) || 11906;
    const rawHeight = Number(pgSz?.getAttribute('w:h')) || 16838;
    const orient = pgSz?.getAttribute('w:orient');
    const width = dxaToPx(rawWidth);
    const height = dxaToPx(rawHeight);

    return {
      width: orient === 'landscape' ? Math.max(width, height) : Math.min(width, height),
      height: orient === 'landscape' ? Math.min(width, height) : Math.max(width, height),
      margins: [
        dxaToPx(Number(pgMar?.getAttribute('w:top')) || 1440),
        dxaToPx(Number(pgMar?.getAttribute('w:right')) || 1440),
        dxaToPx(Number(pgMar?.getAttribute('w:bottom')) || 1440),
        dxaToPx(Number(pgMar?.getAttribute('w:left')) || 1440)
      ],
      direction: orient === 'landscape' ? PaperDirection.HORIZONTAL : PaperDirection.VERTICAL
    };
  } catch (error) {
    console.warn('DOCX 页面设置解析失败:', error);
    return null;
  }
};

const applyDocxPageLayout = (layout: DocxPageLayout | null) => {
  if (!instance || !layout) return;
  currentPageLayout = layout;
  instance.command.executePaperDirection?.(layout.direction);
  instance.command.executePaperSize?.(layout.width, layout.height);
  instance.command.executeSetPaperMargin?.(layout.margins);
};

const resetEditorDocument = () => {
  if (!instance) return;
  currentPageLayout = null;
  instance.command.executeSetValue({ main: [] });
};

const importDocxFromSource = async (source: DocxSource, fileName = props.title || 'document.docx') => {
  if (!instance) return;
  const requestId = ++latestImportRequestId;
  const sourceKey = buildSourceKey(source);
  currentDocxFileName = normalizeDocxFileName(fileName);
  docFormatError.value = '';

  if (!source) {
    lastImportedSourceKey = '';
    resetEditorDocument();
    return;
  }

  if (sourceKey && sourceKey === lastImportedSourceKey) {
    return;
  }

  // 先清空可视内容，避免加载慢时短暂显示上一份文档。
  resetEditorDocument();

  try {
    const arrayBuffer = await resolveDocxArrayBuffer(source);
    if (!arrayBuffer || requestId !== latestImportRequestId) return;

    // 检测是否为 .doc 格式（非 ZIP），提前拦截并显示友好提示
    if (!isZipFormat(arrayBuffer)) {
      docFormatError.value = '不支持编辑 .doc 格式文档。请将文件转换为 .docx 格式后再进行编辑。';
      return;
    }

    const pageLayout = await parseDocxPageLayout(arrayBuffer);
    if (requestId !== latestImportRequestId) return;
    applyDocxPageLayout(pageLayout);

    const file = new File([arrayBuffer], currentDocxFileName, { type: DOCX_MIME });
    try {
      const elements = await parseDocxToElements(file);
      if (requestId !== latestImportRequestId) return;
      instance.command.executeSetValue({ main: elements }, { isSetCursor: false });
      lastImportedSourceKey = sourceKey;
    } catch (err) {
      if (requestId !== latestImportRequestId) return;
      console.error('DOCX 解析失败，回退内置导入:', err);
      // @ts-ignore
      instance.command.executeImportDocx?.({ arrayBuffer });
      lastImportedSourceKey = sourceKey;
    }
  } catch (err) {
    if (requestId !== latestImportRequestId) return;
    console.error('DOCX 加载失败:', err);
  }
};

const exportCurrentDocx = async (fileName = currentDocxFileName) => {
  if (!instance) return;
  try {
    const data = instance.command.getValue() as
      | { main?: unknown; data?: { main?: unknown } }
      | null
      | undefined;
    const candidateMain = data?.data?.main ?? data?.main;
    const mainElements = (Array.isArray(candidateMain) ? candidateMain : []) as IElement[];
    await exportDocxFile(mainElements, normalizeDocxFileName(fileName), currentPageLayout ? {
      page: {
        width: currentPageLayout.width,
        height: currentPageLayout.height,
        margins: currentPageLayout.margins
      }
    } : undefined);
  } catch (err) {
    console.error('自定义导出失败，尝试降级:', err);
    // @ts-ignore
    if (instance.command.executeExportDocx) {
      // @ts-ignore
      instance.command.executeExportDocx({ fileName: normalizeDocxFileName(fileName) });
    } else {
      instance.command.executePrint();
    }
  }
};

const triggerImportWord = () => {
  fileInputRef.value?.click();
};

const handleExportWord = async () => {
  await exportCurrentDocx(currentDocxFileName);
};

const handleImportWord = async (e: Event) => {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file || !instance) return;


  await importDocxFromSource(await file.arrayBuffer(), file.name);
  (e.target as HTMLInputElement).value = '';
};

// 生成红线 SVG Base64
const createRedLineSVG = (style: string, options: any = {}) => {
  const color = options.color || '#ff0000';
  const width = 800; // 宽画布保证精度
  const strokeRatio = options.strokeWidth ? (Number(options.strokeWidth) / 2) : 1;
  let svg = '';
  let height = 10;

  if (style === 'standard') {
    height = 6 * strokeRatio + 4;
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" stroke="${color}" stroke-width="${2 * strokeRatio}"/></svg>`;
  } else if (style === 'thick') {
    height = 10 * strokeRatio + 4;
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" stroke="${color}" stroke-width="${5 * strokeRatio}"/></svg>`;
  } else if (style === 'double') {
    height = 20 * strokeRatio;
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
      <line x1="0" y1="${6 * strokeRatio}" x2="${width}" y2="${6 * strokeRatio}" stroke="${color}" stroke-width="${1.5 * strokeRatio}"/>
      <line x1="0" y1="${14 * strokeRatio}" x2="${width}" y2="${14 * strokeRatio}" stroke="${color}" stroke-width="${3 * strokeRatio}"/>
    </svg>`;
  } else if (style === 'dashed') {
    height = 6 * strokeRatio + 4;
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" stroke="${color}" stroke-width="${2 * strokeRatio}" stroke-dasharray="${8 * strokeRatio},${4 * strokeRatio}"/></svg>`;
  } else if (style === 'custom') {
    const strokeWidth = options.strokeWidth || 2;
    height = strokeWidth * 2 + 4;
    svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}"><line x1="0" y1="${height / 2}" x2="${width}" y2="${height / 2}" stroke="${color}" stroke-width="${strokeWidth}"/></svg>`;
  }

  const bytes = new TextEncoder().encode(svg);
  let binary = '';
  bytes.forEach(byte => {
    binary += String.fromCharCode(byte);
  });
  return `data:image/svg+xml;base64,${btoa(binary)}`;
};

const insertRedLine = (style: string) => {
  if (!instance) return;

  if (style === 'custom') {
    new Dialog({
      title: '自定义红线',
      data: [
        {
          type: 'select',
          label: '线条样式',
          name: 'style',
          value: 'standard',
          options: [
            { label: '标准单线', value: 'standard' },
            { label: '加粗单线', value: 'thick' },
            { label: '双红线', value: 'double' },
            { label: '虚线', value: 'dashed' }
          ]
        },
        {
          type: 'color',
          label: '线条颜色',
          name: 'color',
          value: '#ff0000',
          required: true
        },
        {
          type: 'number',
          label: '线条粗细',
          name: 'strokeWidth',
          value: '2',
          required: true
        }
      ],
      onConfirm: payload => {
        const selectedStyle = payload.find(p => p.name === 'style')?.value || 'standard';
        const color = payload.find(p => p.name === 'color')?.value || '#ff0000';
        const strokeWidth = Number(payload.find(p => p.name === 'strokeWidth')?.value || 2);

        const svgData = createRedLineSVG(selectedStyle, { color, strokeWidth });

        // 计算高度预览值
        let imgHeight = strokeWidth * 2;
        if (selectedStyle === 'double') imgHeight = strokeWidth * 6;
        if (selectedStyle === 'thick') imgHeight = strokeWidth * 4;

        // 使用 executeInsertElementList 确保前后的换行符也具备对齐属性，彻底解决居中问题
        instance!.command.executeInsertElementList([
          { value: '\n', rowFlex: 'center' },
          {
            type: ElementType.IMAGE,
            value: svgData,
            width: 600,
            height: imgHeight,
            rowFlex: 'center',
            title: 'redline'
          },
          { value: '\n', rowFlex: 'center' }
        ] as any);
      }
    });
    return;
  }

  // 预设样式直接插入
  const svgData = createRedLineSVG(style);
  let imgHeight = 5;
  if (style === 'double') imgHeight = 16;
  if (style === 'thick') imgHeight = 10;

  instance!.command.executeInsertElementList([
    { value: '\n', rowFlex: 'center' },
    {
      type: ElementType.IMAGE,
      value: svgData,
      width: 600,
      height: imgHeight,
      rowFlex: 'center',
      title: 'redline'
    },
    { value: '\n', rowFlex: 'center' }
  ] as any);
};

const defaultTemplates = [
  { id: 'standard', name: '标准发文(红头)', type: 'red-head' },
  { id: 'notice', name: '通知 (常用)', type: 'red-head' },
  { id: 'announcement', name: '公告', type: 'red-head' },
  { id: 'letter', name: '函 (正式)', type: 'report' },
  { id: 'report', name: '请示报告', type: 'report' },
  { id: 'meeting', name: '会议纪要', type: 'meeting' },
  { id: 'decision', name: '决定/决议', type: 'red-head' },
  { id: 'reply', name: '批复', type: 'report' }
];

const templates = ref<any[]>([...defaultTemplates]);

const loadCustomTemplates = () => {
  const customStr = localStorage.getItem('word_custom_templates');
  if (customStr) {
    try {
      const customTmpls = JSON.parse(customStr);
      templates.value = [...defaultTemplates, ...customTmpls];
    } catch (e) {
      console.error(e);
    }
  }
};

const saveCustomTemplate = () => {
  if (!instance) return;
  new Dialog({
    title: '保存自定义模版',
    data: [
      {
        type: 'text',
        label: '模版名称',
        name: 'name',
        value: '自定义模版',
        required: true,
        placeholder: '请输入模版名称'
      }
    ],
    onConfirm: payload => {
      const name = payload.find(item => item.name === 'name')?.value?.trim();
      if (!name) return;

      const currentData = instance?.command.getValue().data.main;
      const newTmpl = {
        id: 'custom_' + Date.now(),
        name,
        type: 'report',
        data: currentData
      };

      templates.value.push(newTmpl);
      const customTemplates = templates.value.filter(t => t.id.startsWith('custom_'));
      localStorage.setItem('word_custom_templates', JSON.stringify(customTemplates));
    }
  });
};

const deleteCustomTemplate = (id: string) => {
  Modal.confirm({
    title: '删除确认',
    content: '确定删除该自定义模版吗？',
    wrapClassName: 'wordsbeat-confirm-modal',
    zIndex: 30000,
    okText: '确定',
    cancelText: '取消',
    onOk: () => {
      templates.value = templates.value.filter(t => t.id !== id);
      const customTemplates = templates.value.filter(t => t.id.startsWith('custom_'));
      localStorage.setItem('word_custom_templates', JSON.stringify(customTemplates));
    }
  });
};

// 视图标签页功能已迁移至 official-ui/menu-bindings.ts


// 编辑器设置功能已迁移至 official-ui/menu-bindings.ts


const saveToLocal = async (manual = false) => {
  if (!instance) return;
  isSaving.value = true;
  try {
    const data = instance.command.getValue();
    // 存储数据核心部分
    const draftData = data.data;
    await dbService.set(DRAFT_KEY, draftData);

    const now = new Date();
    lastSavedTime.value = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    if (manual) {
      console.log('手动保存成功 (IndexedDB)');
    }
  } catch (e) {
    console.error('保存失败', e);
  } finally {
    setTimeout(() => {
      isSaving.value = false;
    }, 1000);
  }
};

const loadFromLocal = async () => {
  if (!instance) return;

  try {
    // 优先尝试从 IndexedDB 加载
    let draftData = await dbService.get<any>(DRAFT_KEY);

    // 如果 IndexedDB 为空，尝试从 localStorage 迁移 (处理旧版本数据)
    if (!draftData) {
      const oldDraft = localStorage.getItem(DRAFT_KEY);
      if (oldDraft) {
        try {
          const parsed = JSON.parse(oldDraft);
          draftData = parsed.data || parsed;
          console.log('检测到旧版 localStorage 草稿，正在迁移至 IndexedDB...');
          // 迁移后建议存入 IndexedDB
          await dbService.set(DRAFT_KEY, draftData);
          // 可选：清理 localStorage 以节省空间
          // localStorage.removeItem(DRAFT_KEY);
        } catch (e) {
          console.error('旧版草稿解析失败', e);
        }
      }
    }

    if (draftData) {
      // 兼容以前的包装格式
      const data = draftData.data || draftData;

      // 如果数据结构不包含 main，可能是一个空对象或错误对象，跳过
      if (!data || (!data.main && !data.header && !data.footer)) {
        console.warn('无效的草稿数据', data);
        return;
      }
      instance.command.executeSetValue(data);
      console.log('草稿已自洽恢复');
    }
  } catch (e) {
    console.error('恢复草稿失败', e);
  }
};

const handleWindowClick = () => {
  redLineMenuVisible.value = false;
};

let dropdownObserver: MutationObserver | null = null;
let dropdownScrollCleanup: (() => void) | null = null;

function syncLayoutMetrics() {
  const rootEl = rootRef.value;
  if (!rootEl) return;
  const ribbonHeight = ribbonRef.value?.offsetHeight ?? 105;
  const footerHeight = footerRef.value?.offsetHeight ?? 32;
  rootEl.style.setProperty('--word-ribbon-height', `${ribbonHeight}px`);
  rootEl.style.setProperty('--word-footer-height', `${footerHeight}px`);
}

function updateToolbarScrollState() {
  const tabsContentEl = tabsContentRef.value;
  if (!tabsContentEl || !props.embedded) {
    isToolbarOverflowing.value = false;
    canToolbarScrollStart.value = false;
    canToolbarScrollEnd.value = false;
    return;
  }
  const maxScrollLeft = Math.max(0, tabsContentEl.scrollWidth - tabsContentEl.clientWidth);
  const scrollLeft = tabsContentEl.scrollLeft;
  isToolbarOverflowing.value = maxScrollLeft > 1;
  canToolbarScrollStart.value = scrollLeft > 1;
  canToolbarScrollEnd.value = scrollLeft < maxScrollLeft - 1;
}

function stopToolbarScrollAnimation() {
  if (toolbarScrollAnimationFrame !== null) {
    cancelAnimationFrame(toolbarScrollAnimationFrame);
    toolbarScrollAnimationFrame = null;
  }
}

function animateToolbarScroll(targetLeft: number) {
  const tabsContentEl = tabsContentRef.value;
  if (!tabsContentEl) return;

  const maxScrollLeft = Math.max(0, tabsContentEl.scrollWidth - tabsContentEl.clientWidth);
  toolbarScrollTarget = Math.min(Math.max(targetLeft, 0), maxScrollLeft);
  stopToolbarScrollAnimation();

  const startLeft = tabsContentEl.scrollLeft;
  const delta = toolbarScrollTarget - startLeft;
  if (Math.abs(delta) < 1) {
    tabsContentEl.scrollLeft = toolbarScrollTarget;
    updateToolbarScrollState();
    return;
  }

  const duration = Math.min(520, Math.max(280, Math.abs(delta) * 0.65));
  const startTime = performance.now();
  const easeInOutQuart = (t: number) =>
    t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2;

  const step = (timestamp: number) => {
    const currentTabsContentEl = tabsContentRef.value;
    if (!currentTabsContentEl) {
      toolbarScrollAnimationFrame = null;
      return;
    }

    const progress = Math.min((timestamp - startTime) / duration, 1);
    currentTabsContentEl.scrollLeft = startLeft + delta * easeInOutQuart(progress);
    updateToolbarScrollState();

    if (progress < 1) {
      toolbarScrollAnimationFrame = requestAnimationFrame(step);
    } else {
      currentTabsContentEl.scrollLeft = toolbarScrollTarget;
      updateToolbarScrollState();
      toolbarScrollAnimationFrame = null;
    }
  };

  toolbarScrollAnimationFrame = requestAnimationFrame(step);
}

function scrollToolbar(direction: 'left' | 'right') {
  const tabsContentEl = tabsContentRef.value;
  if (!tabsContentEl) return;
  const step = Math.max(220, Math.floor(tabsContentEl.clientWidth * 0.68));
  const baseLeft =
    toolbarScrollAnimationFrame !== null ? toolbarScrollTarget : tabsContentEl.scrollLeft;
  const nextLeft = direction === 'left' ? baseLeft - step : baseLeft + step;
  animateToolbarScroll(nextLeft);
}

function setupLayoutObserver() {
  syncLayoutMetrics();
  updateToolbarScrollState();
  if (typeof ResizeObserver === 'undefined') return;
  layoutObserver?.disconnect();
  layoutObserver = new ResizeObserver(() => {
    syncLayoutMetrics();
    updateToolbarScrollState();
  });
  [rootRef.value, ribbonRef.value, tabsContentRef.value, footerRef.value].forEach(target => {
    if (target) {
      layoutObserver?.observe(target);
    }
  });
}

const setupDropdownFixedPositioning = () => {
  const tabsContent = document.querySelector<HTMLElement>('.tabs-content');
  if (!tabsContent) return;

  const updateDropdownPosition = (optionsEl: HTMLElement) => {
    const triggerEl = optionsEl.parentElement;
    if (!triggerEl) return;
    const viewportPadding = 8;
    const gap = 4;
    const rect = triggerEl.getBoundingClientRect();
    const dropdownWidth = optionsEl.offsetWidth || optionsEl.scrollWidth || 200;
    const dropdownHeight = optionsEl.offsetHeight || optionsEl.scrollHeight || 120;
    const maxLeft = Math.max(viewportPadding, window.innerWidth - dropdownWidth - viewportPadding);
    const minLeft = viewportPadding;
    let left = rect.left;
    if (left > maxLeft) {
      // 右侧空间不足时，回退为右对齐触发器
      left = rect.right - dropdownWidth;
    }
    left = Math.min(Math.max(left, minLeft), maxLeft);

    let top = rect.bottom + gap;
    const maxTop = window.innerHeight - dropdownHeight - viewportPadding;
    if (top > maxTop) {
      // 底部空间不足时，尝试向上展开
      top = rect.top - dropdownHeight - gap;
    }
    top = Math.min(Math.max(top, viewportPadding), Math.max(viewportPadding, maxTop));

    optionsEl.style.position = 'fixed';
    optionsEl.style.left = `${Math.round(left)}px`;
    optionsEl.style.top = `${Math.round(top)}px`;
    optionsEl.style.zIndex = '9999';
    optionsEl.style.maxWidth = `calc(100vw - ${viewportPadding * 2}px)`;
  };

  const resetDropdownPosition = (optionsEl: HTMLElement) => {
    optionsEl.style.position = '';
    optionsEl.style.left = '';
    optionsEl.style.top = '';
    optionsEl.style.zIndex = '';
    optionsEl.style.maxWidth = '';
  };

  dropdownObserver = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      if (mutation.type !== 'attributes' || mutation.attributeName !== 'class') continue;
      const el = mutation.target as HTMLElement;
      if (!el.classList.contains('options')) continue;
      if (el.classList.contains('visible')) {
        updateDropdownPosition(el);
      } else {
        resetDropdownPosition(el);
      }
    }
  });

  dropdownObserver.observe(tabsContent, {
    subtree: true,
    attributes: true,
    attributeFilter: ['class']
  });

  const handleScroll = () => {
    tabsContent.querySelectorAll<HTMLElement>('.options.visible').forEach((el) => {
      el.classList.remove('visible');
      resetDropdownPosition(el);
    });
  };

  tabsContent.addEventListener('scroll', handleScroll);

  dropdownScrollCleanup = () => {
    dropdownObserver?.disconnect();
    tabsContent.removeEventListener('scroll', handleScroll);
    dropdownObserver = null;
    dropdownScrollCleanup = null;
  };
};

const handleGlobalKeyDown = (evt: KeyboardEvent) => {
  if (evt.key === 'Escape') {
    // 强制尝试寻找并关闭图片预览器 (针对 canvas-editor 默认预览器)
    const viewer = document.querySelector('.ce-image-viewer');
    if (viewer) {
      const closeBtn = viewer.querySelector('.ce-image-viewer__close') as HTMLElement;
      if (closeBtn) {
        closeBtn.click();
      } else {
        viewer.remove();
      }
    }
  }
};

const handleCanvasFullscreenChange = (evt: Event) => {
  const customEvent = evt as CustomEvent<{ isFullScreen?: boolean; isExiting?: boolean }>;
  isCanvasFullscreen.value = !!customEvent.detail?.isFullScreen;
  isCanvasExiting.value = !!customEvent.detail?.isExiting;
};

const requestExitCanvasFullscreen = () => {
  if (!isCanvasFullscreen.value) return;
  window.dispatchEvent(new CustomEvent(CANVAS_FULLSCREEN_TOGGLE_EVENT));
};

onMounted(async () => {
  window.addEventListener('click', handleWindowClick);
  window.addEventListener('keydown', handleGlobalKeyDown);
  window.addEventListener(CANVAS_FULLSCREEN_CHANGE_EVENT, handleCanvasFullscreenChange as EventListener);
  loadCustomTemplates();
  await nextTick();
  const container = editorHostRef.value;
  if (!container) return;

  instance = new Editor(container, {
    main: [],
  }, {
    margins: [100, 120, 100, 120],
    historyMaxRecordCount: props.embedded ? 20 : 100,
    scrollContainerSelector: `.${editorContainerClass}`
  });

  try {
    bindEditorUI(instance);
  } catch (e) {
    console.error('Menu binding error:', e);
  }

  // Mount it on the window so UI actions finding window.__CANVAS_EDITOR_INSTANCE__ works
  (window as any).__CANVAS_EDITOR_INSTANCE__ = instance;
  (window as any).editor = instance;

  // 仅独立编辑器模式恢复草稿；嵌入 Canvas 模式应以传入 source 为准，避免短暂显示旧文档。
  if (!props.embedded) {
    void loadFromLocal();
  }
  if (props.source) {
    void importDocxFromSource(props.source, props.title);
  }

  // 嵌入 Canvas 场景不做草稿自动保存：大文档每次 getValue + IndexedDB 写入会明显拖慢编辑。
  if (!props.embedded) {
    const oldContentChange = instance.listener.contentChange;
    const autoSave = debounce(() => {
      saveToLocal(false);
    }, 5000);

    instance.listener.contentChange = () => {
      if (oldContentChange) oldContentChange();
      autoSave();
    };
  }

  // 快捷键 Ctrl+S 仅用于独立编辑器草稿保存；嵌入 Canvas 下避免全量快照造成卡顿。
  if (!props.embedded) {
    saveHotkeyHandler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveToLocal(true);
      }
    };
    window.addEventListener('keydown', saveHotkeyHandler);
  }

  setupDropdownFixedPositioning();
  setupLayoutObserver();
  syncLayoutMetrics();
});

watch(
  () => props.source,
  source => {
    if (!instance || props.suspend) return;
    void importDocxFromSource(source, props.title);
  }
);

watch(
  () => props.title,
  title => {
    if (title) currentDocxFileName = normalizeDocxFileName(title);
  }
);

onUnmounted(() => {
  window.removeEventListener('click', handleWindowClick);
  window.removeEventListener('keydown', handleGlobalKeyDown);
  window.removeEventListener(CANVAS_FULLSCREEN_CHANGE_EVENT, handleCanvasFullscreenChange as EventListener);
  if (saveHotkeyHandler) {
    window.removeEventListener('keydown', saveHotkeyHandler);
    saveHotkeyHandler = null;
  }
  if (dropdownScrollCleanup) {
    dropdownScrollCleanup();
  }
  if (layoutObserver) {
    layoutObserver.disconnect();
    layoutObserver = null;
  }
  stopToolbarScrollAnimation();
  if (instance) {
    instance.destroy();
  }
});

const showTemplateModal = () => {
  templateModalVisible.value = true;
};

const applyTemplate = (id: string) => {
  if (!instance) return;
  let templateData: any[] = [];

  if (id.startsWith('custom_')) {
    const tmpl = templates.value.find(t => t.id === id);
    if (tmpl && tmpl.data) {
      templateData = tmpl.data;
    }
  } else if (id === 'notice') {
    templateData = [
      { value: '机 密\n', size: 16, font: '黑体' },
      { value: '中 飞 核 心 企 业 通 知\n\n', size: 38, font: '方正小标宋_GBK, 黑体', color: '#ff0000', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '中飞发〔2026〕88号\n\n', size: 16, font: '仿宋_GB2312', rowFlex: 'center' },
      { value: '关于加强五一期间值班工作的通知\n\n', size: 24, font: '方正小标宋_GBK, 黑体', rowFlex: 'center' },
      { value: '各所属单位、各部门：\n', size: 16, font: '仿宋_GB2312' },
      { value: '    为保障假期期间生产安全，现就有关要求通知如下...\n', size: 16, font: '仿宋_GB2312' },
      { value: '    一、高度重视安全生产...\n', size: 16, font: '仿宋_GB2312' },
      { value: '    二、严格落实值班制度...\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '中飞集团有限公司\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' },
      { value: '2026年4月10日\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' }
    ];
  } else if (id === 'announcement') {
    templateData = [
      { value: '公 告\n\n', size: 42, font: '方正小标宋_GBK, 黑体', color: '#ff0000', rowFlex: 'center' },
      { value: '2026年第3号\n\n', size: 16, font: '仿宋_GB2312', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '关于新产品正式上线的公告\n\n', size: 24, font: '方正小标宋_GBK, 黑体', rowFlex: 'center' },
      { value: '    经过多轮测试，我司自主研发的新一代编辑器产品现已正式上线...\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '特此公告。\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '中飞研发中心\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' },
      { value: '2026年4月10日\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' }
    ];
  } else if (id === 'letter') {
    templateData = [
      { value: '红 头 函 件\n\n', size: 36, font: '方正小标宋_GBK, 黑体', color: '#ff0000', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '致 [合作单位名称] 的商洽函\n\n', size: 22, font: '方正小标宋_GBK, 黑体', rowFlex: 'center' },
      { value: '[合作单位名称]：\n', size: 16, font: '仿宋_GB2312' },
      { value: '    感谢贵司长期以来对我司的大力支持。现就XXXX项目事宜商洽如下...\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '望复函为盼。\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '中飞项目部\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' }
    ];
  } else if (id === 'reply') {
    templateData = [
      { value: '官 方 批 复\n\n', size: 38, font: '方正小标宋_GBK, 黑体', color: '#ff0000', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '关于XX项目可行性研究报告的批复\n\n', size: 22, font: '方正小标宋_GBK, 黑体', rowFlex: 'center' },
      { value: '    你部《关于XX项目的请示》收悉。经研究，现批复如下：\n', size: 16, font: '仿宋_GB2312' },
      { value: '    原则同意该项目立项...\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '审批机关\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' }
    ];
  } else if (id === 'standard') {
    templateData = [
      { value: '【机密】\n', size: 16, font: '黑体', color: '#000000' },
      { value: 'X X 部 门 发 文\n\n\n', size: 36, font: '方正小标宋_GBK, 方正小标宋简体, 黑体', color: '#ff0000', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '关于XXXX工作指引的通知\n\n', size: 22, font: '方正小标宋_GBK, 方正小标宋简体, 黑体', rowFlex: 'center' },
      { value: '各部门、各单位：\n', size: 16, font: '仿宋_GB2312, 仿宋, SimSun' },
      { value: '    为了提高工作效率...\n\n', size: 16, font: '仿宋_GB2312, 仿宋, SimSun' },
      { value: '    特此通知。\n\n', size: 16, font: '仿宋_GB2312, 仿宋, SimSun' },
      { value: '单位落款\n', size: 16, font: '仿宋_GB2312, SimSun', rowFlex: 'right' },
      { value: '2026年4月7日\n', size: 16, font: '仿宋_GB2312, SimSun', rowFlex: 'right' }
    ];
  } else if (id === 'report') {
    templateData = [
      { value: 'X X 部 门 请 示 报 告\n\n\n', size: 36, font: '方正小标宋_GBK, 黑体', color: '#ff0000', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '关于XXXX的请示\n\n', size: 22, font: '方正小标宋_GBK, 黑体', rowFlex: 'center' },
      { value: '尊敬的领导：\n', size: 16, font: '仿宋_GB2312' },
      { value: '    现就近期工作汇报如下...\n\n', size: 16, font: '仿宋_GB2312' },
      { value: '汇报人：XXX\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' }
    ];
  } else if (id === 'meeting') {
    templateData = [
      { value: '会 议 纪 要\n\n', size: 36, font: '方正小标宋_GBK, 黑体', color: '#333', rowFlex: 'center' },
      { value: '第 [2026] 1 号\n\n', size: 16, font: '仿宋_GB2312', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard', { color: '#000000' }), width: 600, height: 4, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '时间：2026年4月7日\n', size: 16, font: '黑体' },
      { value: '地点：第一会议室\n', size: 16, font: '黑体' },
      { value: '参会人员：张三、李四、王五\n\n', size: 16, font: '黑体' },
      { value: '会议记录：\n', size: 16, font: '黑体' },
      { value: '    本次会议重点讨论了...\n\n', size: 16, font: '仿宋_GB2312' }
    ];
  } else if (id === 'decision') {
    templateData = [
      { value: '中 共 X X 委 员 会 决 定\n\n\n', size: 36, font: '方正小标宋_GBK, 黑体', color: '#ff0000', rowFlex: 'center' },
      { type: 'image', value: createRedLineSVG('standard'), width: 600, height: 6, rowFlex: 'center' },
      { value: '\n', size: 14 },
      { value: '关于同意实施XXX的决定\n\n', size: 22, font: '方正小标宋_GBK, 黑体', rowFlex: 'center' },
      { value: '    为进一步加强和改进工作...\n\n', size: 16, font: '仿宋_GB2312' },
      { value: 'X X 委 员 会\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' },
      { value: '2026年4月7日\n', size: 16, font: '仿宋_GB2312', rowFlex: 'right' }
    ];
  }

  if (templateData.length > 0) {
    instance.command.executeSetValue({ main: templateData });
  }
  templateModalVisible.value = false;
};

defineExpose({
  importDocxFromSource,
  exportCurrentDocx
});
</script>

<style scoped>
.word-container-pro {
  --biz-primary: #1b2e4b;
  --biz-primary-light: #2c4a7c;
  --biz-bg: #f8f9fb;
  --biz-bg-dark: #f0f2f5;
  --biz-text: #1d2129;
  --biz-text-secondary: #4e5969;
  --biz-border: #e5e6eb;
  --biz-shadow: 0 4px 10px rgba(0, 0, 0, 0.05);
  --word-ribbon-height: 105px;
  --word-footer-height: 32px;

  display: flex;
  flex-direction: column;
  height: 100vh;
  min-height: 0;
  box-sizing: border-box;
  background-color: var(--biz-bg);
  position: relative;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  container-type: inline-size;
}

.word-container-pro--embedded {
  height: 100%;
}

/* Ribbon GUI overrides */
.custom-ribbon-tabs {
  background-color: #f4f5f7;
  display: flex;
  flex-direction: column;
  position: relative;
  z-index: 100;
}

.tabs-nav {
  display: flex;
  align-items: center;
  padding: 4px 20px 0 20px;
  background-color: #fff;
  border-bottom: 1px solid var(--biz-border);
}

.tabs-nav-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  padding-bottom: 4px;
  gap: 8px;
}

.tabs-exit-fullscreen-btn {
  position: relative;
  overflow: hidden;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #64748b;
  padding: 0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.tabs-exit-fullscreen-btn:hover {
  background-color: #f1f5f9;
  transform: translateY(-1px);
}

.tabs-exit-fullscreen-btn .header-fs-icon {
  width: 14px;
  height: 14px;
  display: block;
}

.tab-btn {
  padding: 10px 20px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 500;
  color: var(--biz-text-secondary);
  border-bottom: 2px solid transparent;
  margin-right: 4px;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.tab-btn:hover {
  color: var(--biz-primary);
  background-color: rgba(27, 46, 75, 0.04);
}

.tab-btn.active {
  color: var(--biz-primary);
  border-bottom: 2px solid var(--biz-primary);
  background-color: #fff;
}

.tabs-content-shell {
  background-color: #fff;
  border-bottom: 1px solid var(--biz-border);
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.02);
  position: relative;
  overflow: visible;
  z-index: 1200;
}

.tabs-content {
  background-color: #fff;
  padding: 4px 20px;
  overflow-x: auto;
  position: relative;
  z-index: 1;
  scrollbar-width: none;
  -ms-overflow-style: none;
}

.tabs-content::-webkit-scrollbar {
  display: none;
}

.tabs-content-shell.has-scroll-controls::before,
.tabs-content-shell.has-scroll-controls::after {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  width: 52px;
  pointer-events: none;
  z-index: 2;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.tabs-content-shell.has-scroll-controls::before {
  left: 0;
  background: linear-gradient(90deg, #fff 0 72%, rgba(255, 255, 255, 0.88) 86%, rgba(255, 255, 255, 0) 100%);
}

.tabs-content-shell.has-scroll-controls::after {
  right: 0;
  background: linear-gradient(270deg, #fff 0 72%, rgba(255, 255, 255, 0.88) 86%, rgba(255, 255, 255, 0) 100%);
}

.tabs-content-shell.can-scroll-start::before {
  opacity: 1;
}

.tabs-content-shell.can-scroll-end::after {
  opacity: 1;
}

.tabs-content-shell.has-scroll-controls .tabs-content {
  padding-inline: 20px;
}

.tabs-content-shell > .toolbar-scroll-btn {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(27, 46, 75, 0.1);
  border-radius: 999px !important;
  background: rgba(255, 255, 255, 0.94);
  -webkit-appearance: none;
  appearance: none;
  overflow: hidden;
  color: var(--biz-primary);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
  cursor: pointer;
  z-index: 3;
  transition: all 0.2s ease;
}

.tabs-content-shell.can-scroll-start .toolbar-scroll-btn--left::before,
.tabs-content-shell.can-scroll-end .toolbar-scroll-btn--right::before {
  content: "";
  position: absolute;
  top: -14px;
  bottom: -14px;
  width: 52px;
  background: #fff;
  z-index: -1;
}

.tabs-content-shell.can-scroll-start .toolbar-scroll-btn--left::before {
  left: -12px;
}

.tabs-content-shell.can-scroll-end .toolbar-scroll-btn--right::before {
  right: -12px;
}

.toolbar-scroll-btn:hover {
  transform: translateY(-50%) scale(1.03);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.16);
}

.toolbar-scroll-btn--left {
  left: 10px;
}

.toolbar-scroll-btn--right {
  right: 10px;
}

.tabs-content-shell > .toolbar-scroll-btn svg {
  width: 12px;
  height: 12px;
}

.tab-pane {
  display: block;
  min-width: max-content;
}

.tab-pane[style*="display: none"] {
  display: none !important;
}

/* === 优化 tabs-content 内按钮样式 === */
.custom-ribbon-tabs .menu-item {
  height: 28px;
}

.custom-ribbon-tabs .menu-item>div:not([class*="__collapse"]) {
  min-width: 28px;
  height: 28px;
  margin: 0 3px;
  border-radius: 6px;
  border: 1px solid transparent;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
}

.custom-ribbon-tabs .menu-item>div:not([class*="__collapse"]):hover {
  background: rgba(27, 46, 75, 0.06);
  border-color: rgba(27, 46, 75, 0.08);
  box-shadow: 0 2px 6px rgba(27, 46, 75, 0.08);
}

.custom-ribbon-tabs .menu-item>div:not([class*="__collapse"]):active {
  box-shadow: none;
}

.custom-ribbon-tabs .menu-item>div:not([class*="__collapse"]).active {
  background: rgba(27, 46, 75, 0.12);
  border-color: rgba(27, 46, 75, 0.15);
  box-shadow: inset 0 1px 2px rgba(27, 46, 75, 0.06);
}

.custom-ribbon-tabs .menu-item i {
  width: 16px;
  height: 16px;
  transition: transform 0.2s ease;
}

.custom-ribbon-tabs .menu-item>div:hover i {
  transform: scale(1.05);
}

/* 下拉选择器类型按钮（字体、字号、标题、下划线、红线）重写 */
.custom-ribbon-tabs .menu-item .menu-item__font,
.custom-ribbon-tabs .menu-item .menu-item__size,
.custom-ribbon-tabs .menu-item .menu-item__title,
.custom-ribbon-tabs .menu-item .menu-item__underline,
.custom-ribbon-tabs .menu-item .menu-item__redline {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  box-sizing: border-box;
  min-width: 52px;
  height: 28px;
  padding: 0 8px;
  border-radius: 6px;
  border: 1px solid transparent;
}

.custom-ribbon-tabs .menu-item .menu-item__font:hover,
.custom-ribbon-tabs .menu-item .menu-item__size:hover,
.custom-ribbon-tabs .menu-item .menu-item__title:hover,
.custom-ribbon-tabs .menu-item .menu-item__underline:hover,
.custom-ribbon-tabs .menu-item .menu-item__redline:hover {
  border-color: rgba(27, 46, 75, 0.08);
}

.custom-ribbon-tabs .menu-item .menu-item__font {
  min-width: 104px;
  width: auto;
  flex: 0 0 auto;
}

.custom-ribbon-tabs .menu-item .menu-item__size {
  min-width: 72px;
  width: auto;
  flex: 0 0 auto;
}

.custom-ribbon-tabs .menu-item .menu-item__title {
  display: grid;
  grid-template-columns: 16px minmax(0, 1fr);
  column-gap: 6px;
  min-width: 96px;
  padding: 0 8px;
  width: auto;
  flex: 0 0 auto;
}

.custom-ribbon-tabs .menu-item .menu-item__underline,
.custom-ribbon-tabs .menu-item .menu-item__redline {
  min-width: 40px;
  padding: 0 8px;
}

/* 表格折叠面板：由内容撑开容器，避免被通用 menu-item 高度规则压缩 */
.custom-ribbon-tabs .menu-item .menu-item__table__collapse {
  height: auto !important;
  min-height: 0;
  max-height: none;
  overflow: visible;
  box-sizing: border-box;
  border-radius: 16px;
}

.custom-ribbon-tabs .menu-item .menu-item__table__collapse[style*="display: block"] {
  display: flex !important;
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.custom-ribbon-tabs .menu-item .menu-item__table__collapse .table-collapse__header,
.custom-ribbon-tabs .menu-item .menu-item__table__collapse .table-panel,
.custom-ribbon-tabs .menu-item .menu-item__table__collapse .table-custom {
  width: 100%;
  box-sizing: border-box;
  margin: 0;
}

.custom-ribbon-tabs .menu-item .menu-item__table__collapse .table-collapse__header {
  padding-bottom: 10px;
}

.custom-ribbon-tabs .menu-item .menu-item__table__collapse .table-custom {
  padding-top: 10px;
}

.custom-ribbon-tabs .menu-item .select {
  display: inline-flex;
  align-items: center;
  width: 100%;
  height: 28px;
  min-width: 0;
  line-height: 1;
  padding: 0;
  box-sizing: border-box;
  font-size: 13px;
  font-weight: 500;
  color: #1f2937;
}

.custom-ribbon-tabs .menu-item .select::after {
  content: none !important;
}

.custom-ribbon-tabs .menu-item .select__label {
  flex: 1;
  min-width: max-content;
  overflow: visible;
  text-overflow: clip;
  white-space: nowrap;
  line-height: 28px;
  text-align: left;
}

.custom-ribbon-tabs .menu-item .select__caret {
  flex: none;
  width: 12px;
  height: 28px;
  margin-left: 4px;
  position: relative;
}

.custom-ribbon-tabs .menu-item .select__caret::before {
  content: "";
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid #6b7280;
  transform: translate(-50%, -35%);
}

.custom-ribbon-tabs .menu-item .menu-item__title .select {
  width: 100%;
}

.custom-ribbon-tabs .menu-item .menu-item__title i {
  transform: none;
  justify-self: center;
}

.custom-ribbon-tabs .menu-item .menu-item__font .select,
.custom-ribbon-tabs .menu-item .menu-item__size .select {
  width: auto;
  min-width: max-content;
  padding-right: 0;
}

.custom-ribbon-tabs .menu-item .menu-item__title .select {
  width: auto;
  min-width: max-content;
}

.custom-ribbon-tabs .menu-item .menu-item__underline .select,
.custom-ribbon-tabs .menu-item .menu-item__redline .select {
  justify-content: center;
}

.custom-ribbon-tabs .menu-item .menu-item__underline .select__label,
.custom-ribbon-tabs .menu-item .menu-item__redline .select__label {
  display: none;
}

/* 分隔线更精致 */
.custom-ribbon-tabs .menu-divider {
  height: 18px;
  margin: 0 10px;
  background-color: #dde0e6;
}

/* === 优化结束 === */

.custom-ribbon-tabs .menu {
  position: relative !important;
  top: auto !important;
  z-index: 1201 !important;
  height: 44px !important;
  background: transparent !important;
  justify-content: flex-start !important;
  box-shadow: none !important;
  overflow: visible !important;
}

.menu-item .options {
  z-index: 1300 !important;
}

/* 右侧工具下拉防溢出：靠右对齐并限制宽度，避免超出屏幕 */
.custom-ribbon-tabs .menu-item .menu-item__redline .options,
.custom-ribbon-tabs .menu-item .menu-item__underline .options {
  left: auto;
  right: 0;
  max-width: min(260px, calc(100vw - 24px));
}

.footer .options,
.footer .options.visible {
  width: fit-content;
  min-width: 100px;
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(15px);
  font-size: 13px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
  border: 1px solid var(--biz-border, #e5e6eb);
  border-radius: 8px;
  z-index: 1300 !important;
}

.footer .options li {
  padding: 6px 10px;
  margin: 1px 0;
  user-select: none;
  transition: all .2s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 4px;
  white-space: nowrap;
}

.footer .options li:hover {
  background-color: rgba(27, 46, 75, 0.05);
  color: #1b2e4b;
}

.footer .options li.active {
  background-color: rgba(27, 46, 75, 0.1);
  color: #1b2e4b;
  font-weight: 500;
}

.footer .options ol,
.footer .options ul,
.footer .options dl {
  margin-bottom: 0;
}

.action-btn {
  margin: 0 4px;
}

.custom-action-bar {
  position: absolute;
  top: 15px;
  right: 20px;
  z-index: 100;
  display: flex;
  gap: 15px;
}

.action-btn {
  height: 30px;
  border-radius: 4px;
}

/* 覆盖样式 */
.menu {
  position: absolute;
}

.catalog {
  top: 60px;
}

.editor {
  position: relative;
  margin-top: 0px;
  height: calc(100vh - 90px);
  overflow-y: auto;
}

.editor>div {
  margin: 30px auto !important;
}

.footer {
  position: fixed;
  bottom: 0;
  width: 100%;
  height: 32px;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(12px) saturate(180%);
  -webkit-backdrop-filter: blur(12px) saturate(180%);
  border-top: 1px solid rgba(229, 230, 235, 0.5);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 11px;
  color: var(--biz-text-secondary);
  /* Keep footer below app-level overlays (modal masks, image viewer backdrops). */
  z-index: 900;
  box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
}

.footer>div {
  display: flex;
  align-items: center;
  gap: 12px;
}

.footer .status-group {
  display: flex;
  align-items: center;
  gap: 8px;
  border-right: 1px solid var(--biz-border);
  padding-right: 12px;
}

.footer .status-group:last-child {
  border-right: none;
}

.footer span {
  display: flex;
  align-items: center;
  gap: 2px;
  white-space: nowrap;
}

.footer .page-no-list,
.footer .page-no,
.footer .page-size,
.footer .word-count,
.footer .row-no,
.footer .col-no {
  font-weight: 600;
  color: var(--biz-primary);
}

/* 模版库试图展现样式 */
.template-gallery {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  padding: 10px;
}

.template-card {
  cursor: pointer;
  border: 1px solid #e8e8e8;
  border-radius: 24px;
  padding: 10px;
  transition: all 0.2s;
  background: #fdfdfd;
}

.template-card:hover {
  border-color: var(--biz-primary);
  box-shadow: 0 8px 20px rgba(27, 46, 75, 0.1);
  transform: translateY(-3px);
}

.delete-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: rgba(255, 0, 0, 0.7);
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 12px;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 10;
}

.template-card:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: rgba(255, 0, 0, 1);
  transform: scale(1.1);
}

.template-cover {
  width: 100%;
  height: 160px;
  background-color: #f0f2f5;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed #d9d9d9;
}

/* CSS 组合模拟封面的微观效果 */
.mock-doc {
  width: 80px;
  height: 110px;
  background: #fff;
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.1);
  padding: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.mock-doc .head {
  color: red;
  font-size: 12px;
  font-weight: bold;
  margin-top: 5px;
}

.mock-doc.meeting .head {
  color: #333;
}

.mock-doc .line {
  width: 90%;
  height: 2px;
  background-color: red;
  margin-top: 5px;
  margin-bottom: 10px;
}

.mock-doc .mock-text {
  width: 100%;
  height: 4px;
  background: #ccc;
  margin-bottom: 4px;
}

.mock-doc .mock-text-1 {
  width: 90%;
}

.mock-doc .mock-text-2 {
  width: 100%;
}

.mock-doc .mock-text-3 {
  width: 60%;
  align-self: flex-start;
}

.template-title {
  text-align: center;
  font-size: 14px;
  color: #333;
}

/* Fix catalog overlapping tabs */
.word-container-pro :deep(.catalog) {
  top: var(--word-ribbon-height) !important;
  bottom: var(--word-footer-height) !important;
  height: auto !important;
}

.word-container-pro .catalog {
  top: var(--word-ribbon-height) !important;
  bottom: var(--word-footer-height) !important;
  height: auto !important;
}

/* Fix content document gap */
.word-container-pro :deep(.editor > div) {
  margin: 40px auto 80px auto !important;
  box-shadow: 0 0 25px rgba(0, 0, 0, 0.08) !important;
  transition: box-shadow 0.3s ease;
}

.word-container-pro .editor>div {
  margin: 40px auto 80px auto !important;
  box-shadow: 0 0 25px rgba(0, 0, 0, 0.08) !important;
}

.word-container-pro .editor>div:hover {
  box-shadow: 0 0 35px rgba(0, 0, 0, 0.12) !important;
}

/* 图片预览器关闭按钮增强：强制显示并置顶 */
:deep(.ce-image-viewer),
.ce-image-viewer {
  z-index: 20000 !important;
}

:deep(.ce-image-viewer__close),
.ce-image-viewer__close {
  display: flex !important;
  visibility: visible !important;
  z-index: 20001 !important;
  cursor: pointer !important;
}

/* 如果预览器是在 body 下的全局元素 */
:global(.ce-image-viewer) {
  z-index: 20000 !important;
}

:global(.ce-image-viewer__close) {
  display: flex !important;
  visibility: visible !important;
  z-index: 20001 !important;
}

/* Make editor flex container aware of new bounds */
.word-container-pro .editor {
  flex: 1;
  overflow-y: auto;
  position: relative;
  box-sizing: border-box;
  scrollbar-gutter: stable both-edges;
}

/* 评论侧栏可能覆盖正文点击：空容器不参与命中，嵌入模式彻底禁用 */
.comment:empty {
  display: none !important;
  pointer-events: none !important;
}

.word-container-pro--embedded .comment {
  display: none !important;
  pointer-events: none !important;
}

/* Embedded in Canvas: avoid viewport-based layout (100vh/fixed footer). */
.word-container-pro--embedded {
  height: 100%;
  min-height: 0;
}

.word-container-pro--embedded .custom-ribbon-tabs {
  flex: 0 0 auto;
}

.word-container-pro--embedded .editor {
  height: auto !important;
  min-height: 0;
  flex: 1 1 auto;
}

.word-container-pro--embedded .footer {
  position: relative;
  bottom: auto;
  width: 100%;
  margin-top: auto;
}

.word-container-pro--embedded .catalog,
.word-container-pro--embedded :deep(.catalog) {
  position: absolute !important;
  left: 0 !important;
  right: auto !important;
  top: var(--word-ribbon-height) !important;
  bottom: var(--word-footer-height) !important;
  height: auto !important;
  z-index: 1200 !important;
}

@container (max-width: 980px) {
  .word-container-pro--embedded .tabs-nav {
    padding: 4px 12px 0;
  }

  .word-container-pro--embedded .tab-btn {
    padding: 10px 14px;
  }

  .word-container-pro--embedded .tabs-content {
    padding-inline: 12px;
  }

  .word-container-pro--embedded .tabs-content-shell.has-scroll-controls .tabs-content {
    padding-inline: 12px;
  }

  .word-container-pro--embedded .toolbar-scroll-btn--left {
    left: 6px;
  }

  .word-container-pro--embedded .toolbar-scroll-btn--right {
    right: 6px;
  }

  .word-container-pro--embedded .tabs-content-shell.can-scroll-start .toolbar-scroll-btn--left::before {
    left: -8px;
    width: 46px;
  }

  .word-container-pro--embedded .tabs-content-shell.can-scroll-end .toolbar-scroll-btn--right::before {
    right: -8px;
    width: 46px;
  }
}

/* === Footer 响应式布局优化：防止窄宽下元素重叠 === */
.word-container-pro .footer {
  height: 32px;
  min-height: 32px;
  display: flex;
  align-items: center;
  overflow: visible;
  flex-wrap: nowrap;
}

/* 隐藏滚动条但保留滚动功能 */
.word-container-pro .footer::-webkit-scrollbar {
  display: none;
}

/* 左侧区域：与右侧等宽，内容左对齐 */
.word-container-pro .footer > div:first-child {
  flex: 1 0 0;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
}

/* 状态组紧凑间距 */
.word-container-pro .footer .status-group {
  gap: 6px;
  padding-right: 8px;
  flex-shrink: 0;
}

/* editor-mode：左右等宽列将其推至正中间 */
.word-container-pro .footer .editor-mode {
  position: static !important;
  transform: none !important;
  left: auto !important;
  flex: 0 0 auto;
  padding: 0 10px;
  white-space: nowrap;
}

/* 右侧区域：与左侧等宽，内容右对齐 */
.word-container-pro .footer > div:last-child {
  flex: 1 0 0;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

/* === Footer 优化结束 === */

/* === .doc 格式错误提示 === */
.doc-error-fade-enter-active,
.doc-error-fade-leave-active {
  transition: opacity 0.25s ease;
}

.doc-error-fade-enter-from,
.doc-error-fade-leave-to {
  opacity: 0;
}

.doc-format-error-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(248, 250, 252, 0.95);
  backdrop-filter: blur(4px);
  z-index: 100;
  padding: 24px;
}

.doc-format-error-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  max-width: 320px;
  padding: 32px 24px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08), 0 1px 3px rgba(0, 0, 0, 0.06);
  text-align: center;
}

.doc-format-error-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #d97706;
}

.doc-format-error-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
}

.doc-format-error-message {
  margin: 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.6;
}
/* === .doc 格式错误提示结束 === */
</style>

<style>
.wordsbeat-a-modal .ant-modal-content {
  border-radius: 21px;
  padding: 0;
  overflow: hidden;
}

.wordsbeat-a-modal .ant-modal-header {
  margin: 0;
  padding: 24px 32px 16px;
  border-bottom: none;
}

.wordsbeat-a-modal .ant-modal-title {
  font-size: 16px;
  font-weight: 600;
  color: #151b26;
}

.wordsbeat-a-modal .ant-modal-close {
  top: 16px;
  right: 18px;
}

.wordsbeat-a-modal .ant-modal-body {
  padding: 8px 32px 0;
}

.wordsbeat-a-modal .ant-modal-footer {
  border-top: none;
  padding: 24px 32px 28px;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.wordsbeat-modal-actions {
  padding: 28px 0 22px;
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.wordsbeat-modal-btn {
  min-width: 75px;
  height: 32px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 400;
  padding: 0 20px;
  box-shadow: none;
}

.wordsbeat-modal-btn--cancel,
.wordsbeat-a-modal .ant-btn-default {
  background-color: #f5f5f5;
  border: none;
  color: #1a1a1a;
}

.wordsbeat-modal-btn--cancel:hover,
.wordsbeat-a-modal .ant-btn-default:hover {
  background-color: #e6e6e6;
  color: #1a1a1a;
}

.wordsbeat-modal-btn--confirm,
.wordsbeat-a-modal .ant-btn-primary {
  border: none;
  background: #1677ff;
  color: #fff;
}

.wordsbeat-modal-btn--confirm:hover,
.wordsbeat-a-modal .ant-btn-primary:hover {
  background: #4096ff;
  color: #fff;
}

.wordsbeat-template-gallery-modal .ant-modal-body {
  padding-top: 10px;
}

.wordsbeat-confirm-modal .ant-modal-content {
  border-radius: 21px;
}

.wordsbeat-confirm-modal .ant-modal-title {
  margin-left: 10px;
}

.wordsbeat-confirm-modal .ant-modal-confirm .ant-modal-body {
  padding: 0px;
}

.wordsbeat-confirm-modal .ant-modal-confirm-content {
  width: 100% !important;
  max-width: 100% !important;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 0px;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns .ant-btn {
  min-width: 75px;
  border-radius: 10px;
  height: 32px;
  font-size: 13px;
  font-weight: 400;
  padding: 0 20px;
  box-shadow: none;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns .ant-btn + .ant-btn {
  margin-left: 0;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns .ant-btn-default {
  background-color: #f5f5f5;
  border: none;
  color: #1a1a1a;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns .ant-btn-default:hover {
  background-color: #e6e6e6;
  color: #1a1a1a;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns .ant-btn-primary {
  border: none;
  background: #1677ff;
  color: #fff;
}

.wordsbeat-confirm-modal .ant-modal-confirm-btns .ant-btn-primary:hover {
  background: #4096ff;
  color: #fff;
}
</style>
