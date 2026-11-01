<template>
  <div class="history-rail">
    <div class="history-rail-top">
      <div class="history-brand">
        <img :src="logoImage" alt="logo" class="history-brand-logo" />
        <div class="history-brand-copy">
          <div class="history-brand-name">{{ systemName }}</div>
        </div>
        <div class="history-brand-actions">
          <a-tooltip placement="bottom">
            <template #title>搜索</template>
            <button type="button" class="history-icon-btn" @click="openSearchModal">
              <img :src="searchNavIcon" alt="搜索" class="history-icon-btn-img" />
            </button>
          </a-tooltip>
          <a-tooltip placement="bottom">
            <template #title>折叠侧栏</template>
            <button type="button" class="history-icon-btn" @click="emit('collapse')">
              <img :src="sidebarCollapseIcon" alt="折叠侧栏" class="history-icon-btn-img" />
            </button>
          </a-tooltip>
        </div>
      </div>

      <div class="history-nav">
        <button type="button" class="history-nav-item" @click="emit('new-chat')">
          <img :src="newChatNavIcon" alt="新对话" class="history-nav-item-icon history-nav-item-icon-lg" />
          <span>新对话</span>
        </button>
        <button type="button" class="history-nav-item" :class="{ active: activeWorkspace === 'agents' }" :aria-pressed="activeWorkspace === 'agents'" @click="emit('open-agent')">
          <img :src="agentNavIcon" alt="智能体" class="history-nav-item-icon" />
          <span>智能体</span>
        </button>
        <button
          type="button"
          class="history-nav-item"
          :class="{ active: activeWorkspace === 'delivery' }"
          :aria-pressed="activeWorkspace === 'delivery'"
          @click="emit('open-delivery')"
        >
          <img :src="vectorNavIcon" alt="交付中心" class="history-nav-item-icon" />
          <span>交付中心</span>
        </button>
        <button
          type="button"
          class="history-nav-item"
          :class="{ active: activeWorkspace === 'knowledge' }"
          :aria-pressed="activeWorkspace === 'knowledge'"
          @click="emit('open-knowledge')"
        >
          <img :src="knowledgeNavIcon" alt="知识库" class="history-nav-item-icon history-nav-item-icon-lg" />
          <span>知识库</span>
        </button>
      </div>
    </div>

    <div class="history-projects">
      <div class="history-list" @scroll="handleListScroll">
        <div class="history-section-head history-agent-heading">
          <button type="button" class="history-agent-heading-toggle" :aria-expanded="agentSectionExpanded" :aria-label="agentSectionExpanded ? '折叠 Agent 分组' : '展开 Agent 分组'" @click="toggleAgentSection">
            <span class="history-section-title">Agent</span>
            <svg class="history-agent-heading-chevron" :class="{ collapsed: !agentSectionExpanded }" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path d="m4.5 2.5 3.5 3.5-3.5 3.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
            </svg>
          </button>
          <a-tooltip placement="bottom">
            <template #title>管理智能体</template>
            <button type="button" class="history-agent-add" aria-label="管理智能体" @click="emit('open-agent')">
              <!-- config-nav.svg 内联：fill 用 currentColor，跟随按钮常态灰色与 hover 变色 -->
              <svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M15 13.25c.455 0 .835-.001 1.145.02.317.022.617.068.907.189.674.279 1.21.814 1.489 1.488.12.29.167.59.188.907.009.121.011.253.014.396H21a.75.75 0 0 1 0 1.5h-2.256a8 8 0 0 1-.015.395 2.8 2.8 0 0 1-.188.907 2.75 2.75 0 0 1-1.489 1.489c-.29.12-.59.166-.907.188-.31.021-.69.02-1.145.02s-.835.001-1.146-.02a2.8 2.8 0 0 1-.907-.188 2.75 2.75 0 0 1-1.488-1.489c-.12-.29-.167-.59-.189-.907-.02-.31-.02-.69-.02-1.145s0-.836.02-1.146c.022-.317.069-.617.189-.907.279-.674.814-1.21 1.488-1.488.29-.12.59-.167.907-.189.31-.021.69-.02 1.146-.02m0 1.5c-.476 0-.796 0-1.043.017-.24.017-.359.045-.436.077-.306.127-.55.371-.677.677-.031.077-.06.195-.077.436-.016.247-.017.567-.017 1.043 0 .475 0 .795.017 1.043.017.24.046.358.078.435.126.306.37.55.676.677.077.032.195.06.436.077.247.017.567.018 1.043.018s.795-.001 1.043-.018c.24-.016.358-.045.435-.077.307-.127.55-.37.677-.677.032-.077.06-.195.077-.435.017-.248.018-.568.018-1.043 0-.476-.001-.796-.018-1.043-.016-.24-.045-.359-.077-.436a1.25 1.25 0 0 0-.677-.677c-.077-.031-.195-.06-.435-.077A17 17 0 0 0 15 14.75m-6 1.5a.75.75 0 0 1 0 1.5H3a.75.75 0 0 1 0-1.5zm0-13c.455 0 .835-.001 1.145.02.317.022.617.068.908.189.673.279 1.209.814 1.488 1.488.12.29.167.59.188.907.021.31.02.69.02 1.146s.001.835-.02 1.145a2.8 2.8 0 0 1-.188.907 2.75 2.75 0 0 1-1.489 1.489c-.29.12-.59.166-.907.188-.31.021-.69.02-1.145.02s-.835.001-1.146-.02a2.8 2.8 0 0 1-.907-.188 2.75 2.75 0 0 1-1.488-1.489c-.12-.29-.167-.59-.189-.907q-.01-.182-.013-.395H3a.75.75 0 0 1 0-1.5h2.257q.003-.215.013-.396c.022-.317.069-.617.189-.907.279-.674.814-1.21 1.488-1.488.29-.12.59-.167.907-.189.31-.021.69-.02 1.146-.02m0 1.5c-.476 0-.796 0-1.043.017-.24.017-.359.045-.436.077-.306.127-.55.371-.677.677-.031.077-.06.195-.077.436A17 17 0 0 0 6.75 7c0 .475 0 .795.017 1.043.017.24.046.358.077.435.127.306.371.55.677.677.077.032.195.06.436.077.247.017.567.018 1.043.018s.795-.001 1.043-.018c.24-.016.358-.045.435-.077.307-.127.55-.37.677-.677.032-.077.06-.195.077-.435.017-.248.018-.568.018-1.043 0-.476-.001-.796-.018-1.043-.016-.24-.045-.359-.077-.436a1.25 1.25 0 0 0-.677-.677c-.077-.032-.195-.06-.435-.077A17 17 0 0 0 9 4.75m12 1.5a.75.75 0 0 1 0 1.5h-6a.75.75 0 0 1 0-1.5z" />
              </svg>
            </button>
          </a-tooltip>
        </div>
        <p v-if="agentSectionExpanded && !historySections.some(section => section.isAgent)" class="history-agent-empty">使用智能体后，对话会收纳在这里</p>
        <template v-if="agentSectionExpanded && loading && sortedItems.length === 0">
          <div v-for="index in 6" :key="index" class="history-line-skeleton"></div>
        </template>

        <section v-for="section in historySections" v-show="!section.isAgent || agentSectionExpanded" :key="`${section.isAgent ? 'agent' : 'section'}-${section.id}`" class="history-group">
          <div v-if="section.isAgent" class="history-agent-row" :class="{ 'menu-open': openAgentMenuId === section.id }">
          <button
            v-if="section.isAgent"
            type="button"
            class="history-agent-toggle"
            :aria-expanded="expandedAgentIds.has(section.id)"
            :aria-controls="`agent-history-${section.id}`"
            @click="toggleAgentGroup(section.id)"
          >
            <img :src="expandedAgentIds.has(section.id) ? agentOpenIcon : agentCloseIcon" alt="" class="history-nav-item-icon" />
            <span class="history-agent-name" :title="section.title">{{ section.title }}</span>
          </button>
          <div class="history-agent-actions">
            <!-- 菜单展开时隐藏 tooltip，避免和弹出的操作菜单叠在一起 -->
            <a-tooltip placement="bottom" title="更多操作" :open="activeAgentMenuTooltipId === section.id && shouldShowAgentMenuTooltip(section.id)">
              <button
                type="button"
                class="history-agent-action"
                :class="{ visible: openAgentMenuId === section.id }"
                aria-label="智能体菜单"
                :aria-expanded="openAgentMenuId === section.id"
                aria-haspopup="menu"
                @mouseenter="handleAgentMenuTooltipMouseEnter(section.id)"
                @mouseleave="handleAgentMenuTooltipMouseLeave(section.id)"
                @click.stop="toggleAgentMenu($event, section.id)"
              >
                <EllipsisOutlined />
              </button>
            </a-tooltip>
            <a-tooltip placement="bottom">
              <template #title>新对话</template>
              <button type="button" class="history-agent-action" :disabled="!section.available" aria-label="与此智能体开始新对话" @click.stop="emit('agent-new-chat', section.id)"><img class="history-agent-new-chat-icon" :src="newChatNav2Icon" alt="" /></button>
            </a-tooltip>
          </div>
          <Teleport to="body">
            <Transition name="history-menu-pop">
              <div
                v-if="openAgentMenuId === section.id"
                class="history-line-menu"
                :style="agentMenuStyle"
                role="menu"
                aria-label="智能体操作"
                @click.stop
              >
                <button type="button" class="history-menu-item" role="menuitem" :disabled="!section.available" @click="handleAgentNewChat(section.id)">
                  <img :src="newChatNav2Icon" alt="" class="history-menu-item-icon" />
                  <span>新对话</span>
                </button>

                <div class="history-menu-divider" role="separator"></div>
                <button type="button" class="history-menu-item" role="menuitem" :disabled="!section.available" @click="handleAgentManage(section.id)">
                  <img :src="agentNavIcon" alt="" class="history-menu-item-icon" />
                  <span>管理智能体</span>
                </button>
              </div>
            </Transition>
          </Teleport>
          </div>
          <div v-else class="history-section-head history-agent-heading">
            <button type="button" class="history-agent-heading-toggle" :aria-expanded="recentSectionExpanded" aria-controls="recent-history-list" :aria-label="recentSectionExpanded ? '折叠最近对话' : '展开最近对话'" @click="toggleRecentSection">
              <span class="history-section-title">最近对话</span>
              <svg class="history-agent-heading-chevron" :class="{ collapsed: !recentSectionExpanded }" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                <path d="m4.5 2.5 3.5 3.5-3.5 3.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
          </div>
          <div v-show="section.isAgent ? expandedAgentIds.has(section.id) : recentSectionExpanded" :id="section.isAgent ? `agent-history-${section.id}` : 'recent-history-list'" :class="{ 'history-agent-children': section.isAgent }">
            <TransitionGroup name="history-reorder" tag="div" class="history-line-list">
            <div
              v-for="item in section.items"
              :key="item.id"
              :role="editingId === item.id || item.summaryPending ? undefined : 'button'"
              :tabindex="editingId === item.id || item.summaryPending ? -1 : 0"
              class="history-line"
              :class="{
                active: activeWorkspace === 'chat' && !item.summaryPending && item.sessionThreadId && item.sessionThreadId === activeSessionThreadId,
                editing: editingId === item.id,
                'summary-pending': item.summaryPending,
                'rename-settling': renameSettlingId === item.id
              }"
              @click="handleSelectItem(item)"
              @mouseenter="scheduleHoverCard(item, $event)"
              @mouseleave="hideHoverCard()"
              @keydown.enter.self.prevent="handleSelectItem(item)"
              @keydown.space.self.prevent="handleSelectItem(item)"
            >
              <div v-if="item.summaryPending" class="history-line-summary-skeleton" aria-label="正在生成对话摘要"></div>

              <input
                v-else-if="editingId === item.id"
                :ref="setRenameInputRef"
                v-model="editingTitle"
                type="text"
                class="history-line-rename-input"
                aria-label="编辑对话摘要"
                maxlength="200"
                @click.stop
                @keydown.enter.stop.prevent="submitRename(item)"
                @keydown.esc.stop.prevent="cancelRename"
                @blur="cancelRename"
              />

              <template v-else>
                <div class="history-line-main">
                  <span class="history-line-title">{{ item.title || '新对话' }}</span>
                  <div class="history-line-action" :class="{ 'is-running': isSessionRunning(item), 'menu-open': openMenuId === item.id }">
                    <span v-if="isSessionRunning(item)" class="history-task-loading" role="status" aria-label="任务执行中" title="任务执行中"></span>
                  <button
                    type="button"
                    class="history-line-more"
                    :class="{ visible: openMenuId === item.id }"
                    :aria-expanded="openMenuId === item.id"
                    aria-haspopup="menu"
                    aria-label="更多操作"
                    @click.stop="toggleMenu($event, item.id)"
                  >
                    <EllipsisOutlined />
                  </button>
                  </div>
                </div>

                <Teleport to="body">
                  <Transition name="history-menu-pop">
                    <div
                      v-if="openMenuId === item.id"
                      class="history-line-menu"
                      :style="menuStyle"
                      role="menu"
                      aria-label="对话操作"
                      @click.stop
                    >
                      <button type="button" class="history-menu-item" role="menuitem" @click="handleRename(item)">
                        <img :src="renameNavIcon" alt="" class="history-menu-item-icon" />
                        <span>重命名</span>
                      </button>

                      <div class="history-menu-divider" role="separator"></div>
                      <button type="button" class="history-menu-item danger" role="menuitem" @click="handleDelete(item)">
                        <img :src="deleteNavIcon" alt="" class="history-menu-item-icon danger" />
                        <span>删除</span>
                      </button>
                    </div>
                  </Transition>
                </Teleport>
              </template>
            </div>
            </TransitionGroup>
            <p v-if="section.isAgent && section.items.length === 0" class="history-agent-empty">暂无对话记录</p>
          </div>
        </section>

        <div v-if="recentSectionExpanded && !loading && sortedItems.length === 0" class="history-empty">
          <div class="history-empty-visual" aria-hidden="true">
            <img :src="historyEmptyOrbit" alt="" class="history-empty-orbit" />
          </div>
          <div class="history-empty-title">暂无对话记录</div>
          <p class="history-empty-description">创建一个新对话，灵感就会从这里开始</p>
        </div>
      </div>
    </div>

    <div class="history-account-wrap">
      <div
        class="history-account"
        role="button"
        tabindex="0"
        aria-haspopup="menu"
        :aria-expanded="accountMenuOpen"
        @click.stop="toggleAccountMenu"
        @keydown.enter.prevent="toggleAccountMenu"
        @keydown.space.prevent="toggleAccountMenu"
      >
        <div class="history-account-avatar" :style="avatarStyle">
          <img v-if="userAvatar" :src="userAvatar" alt="" class="history-account-image" />
          <span v-else>{{ userInitial }}</span>
        </div>
        <div class="history-account-copy">
          <div class="history-account-name">{{ userName }}</div>
          <div class="history-account-email">{{ userEmail }}</div>
        </div>
      </div>

      <Transition name="account-menu-pop">
        <div v-if="accountMenuOpen" class="account-menu" role="menu" aria-label="账户菜单" @click.stop>
          <div class="account-menu-user">
            <div class="account-menu-avatar" :style="avatarStyle">
              <img v-if="userAvatar" :src="userAvatar" alt="" class="account-menu-avatar-image" />
              <span v-else>{{ userInitial }}</span>
            </div>
            <div class="account-menu-user-copy">
              <div class="account-menu-user-name">{{ userName }}</div>
              <div class="account-menu-user-type">{{ userEmail }}</div>
            </div>
          </div>

          <div class="account-menu-list">
            <button type="button" class="account-menu-item" role="menuitem" @click="navigateAndClose(ROUTES.ACCOUNT)">
              <svg class="am-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="8" r="5" />
                <path d="M20 21a8 8 0 0 0-16 0" />
              </svg>
              <span>账户</span>
            </button>
            <button type="button" class="account-menu-item" role="menuitem" @click="navigateAndClose(ROUTES.SETTINGS)">
              <svg class="am-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="M20 7h-9" />
                <path d="M14 17H5" />
                <circle cx="17" cy="17" r="3" />
                <circle cx="7" cy="7" r="3" />
              </svg>
              <span>设置</span>
            </button>
          </div>

          <div class="account-menu-divider" role="separator"></div>

          <button type="button" class="account-menu-item danger" role="menuitem" @click="handleLogout">
            <svg class="am-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" x2="9" y1="12" y2="12" />
            </svg>
            <span>退出登录</span>
          </button>
        </div>
      </Transition>
    </div>

    <Teleport to="body">
      <Transition name="search-modal-fade">
        <div v-if="searchModalOpen" class="search-modal-overlay" @click.self="closeSearchModal">
          <Transition name="search-modal-pop" appear>
            <div v-if="searchModalOpen" class="search-modal" role="dialog" aria-modal="true" aria-label="搜索对话">
            <div class="search-modal-header">
              <img :src="searchNavIcon" alt="" class="search-modal-header-icon" />
              <input
                ref="searchInputRef"
                v-model="searchQuery"
                type="text"
                class="search-modal-input"
                placeholder="搜索对话..."
                aria-label="搜索对话"
              />
              <button type="button" class="search-modal-close" aria-label="关闭" @click="closeSearchModal">
                <CloseOutlined />
              </button>
            </div>

            <div class="search-modal-toolbar">
              <button v-if="!isSearching" type="button" class="search-modal-tab" @click="handleNewChatFromSearch">
                <img :src="newChatNavIcon" alt="" class="search-modal-tab-icon" />
                <span>新对话</span>
              </button>
              <div class="search-modal-tabs" role="tablist" aria-label="对话分类">
                <button
                  type="button"
                  role="tab"
                  class="search-modal-tab"
                  :class="{ active: searchTab === 'agent' }"
                  :aria-selected="searchTab === 'agent'"
                  @click="searchTab = 'agent'"
                >
                  <img :src="agentNavIcon" alt="" class="search-modal-tab-icon" />
                  <span>Agent</span>
                  <span v-if="agentResultCount > 0" class="search-modal-tab-count">{{ agentResultCount }}</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  class="search-modal-tab"
                  :class="{ active: searchTab === 'recent' }"
                  :aria-selected="searchTab === 'recent'"
                  @click="searchTab = 'recent'"
                >
                  <span>普通对话</span>
                  <span v-if="recentResultCount > 0" class="search-modal-tab-count">{{ recentResultCount }}</span>
                </button>
              </div>
            </div>

            <div class="search-modal-body">
              <section
                v-for="section in activeSearchSections"
                :key="`search-${section.isAgent ? 'agent' : 'recent'}-${section.id}`"
                class="search-group"
              >
                <button
                  v-if="section.isAgent"
                  type="button"
                  class="search-group-head"
                  :aria-expanded="!searchCollapsedAgentIds.has(section.id)"
                  :aria-controls="`search-agent-group-${section.id}`"
                  @click="toggleSearchAgentGroup(section.id)"
                >
                  <img :src="searchCollapsedAgentIds.has(section.id) ? agentCloseIcon : agentOpenIcon" alt="" class="search-group-head-icon" />
                  <span class="search-group-title" :title="section.title">{{ section.title }}</span>
                </button>
                <div
                  v-show="!section.isAgent || !searchCollapsedAgentIds.has(section.id)"
                  :id="section.isAgent ? `search-agent-group-${section.id}` : undefined"
                  :class="{ 'search-group-list-agent': section.isAgent }"
                >
                  <button
                    v-for="item in section.items"
                    :key="item.id"
                    type="button"
                    class="search-result"
                    @click="handleSearchSelect(item)"
                  >
                    <span class="search-result-icon" aria-hidden="true">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                      </svg>
                    </span>
                    <span class="search-result-copy">
                      <span class="search-result-title">{{ item.title }}</span>
                      <span v-if="item.sessionThreadId" class="search-result-preview">{{ item.sessionThreadId }}</span>
                    </span>
                    <span class="search-result-time">{{ formatSearchItemTime(item) }}</span>
                  </button>
                </div>
              </section>

              <div v-if="activeSearchSections.length === 0" class="search-modal-empty">
                <span class="search-modal-empty-icon" aria-hidden="true">
                  <img :src="searchNavIcon" alt="" />
                </span>
                <span class="search-modal-empty-title">{{ isSearching ? '未找到相关对话' : searchTab === 'agent' ? '暂无智能体对话' : '暂无历史对话' }}</span>
              </div>
            </div>
            </div>
          </Transition>
        </div>
      </Transition>
    </Teleport>

    <Teleport to="body">
      <Transition name="history-hover-pop">
        <div
          v-if="hoverCardItem"
          ref="hoverCardRef"
          class="history-hover-card"
          :style="hoverCardStyle"
          role="tooltip"
          aria-hidden="true"
        >
          <div class="history-hover-title">{{ hoverCardItem.title }}</div>
          <div class="history-hover-meta">
            <img v-if="hoverAgentName" :src="agentCloseIcon" alt="" class="history-hover-meta-icon" />
            <!-- 知识库问答：沿用侧栏知识库图标造型，stroke 用 currentColor 跟随 meta 灰色 -->
            <svg v-else-if="hoverCardItem.chatType === 'kb_chat'" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="1.75" y="0.75" width="12.5" height="14.5" rx="1.75" />
              <path d="M8.25 0.75V6.25L10.25 4.75L12.25 6.25V0.75" />
              <path d="M4.75 9.75H9.25M4.75 12.25H7.75" />
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
            </svg>
            <span class="history-hover-meta-text">{{ hoverDisplayName }}</span>
            <span v-if="hoverTypeLabel" class="history-hover-tag">{{ hoverTypeLabel }}</span>
          </div>
          <div v-if="hoverUpdatedText" class="history-hover-meta">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="3" y="4" width="18" height="17" rx="2" />
              <path d="M16 2v4M8 2v4M3 10h18" />
            </svg>
            <span class="history-hover-meta-text">更新于 {{ hoverUpdatedText }}</span>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onDeactivated, onUnmounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { Modal } from 'ant-design-vue';
import { CloseOutlined, EllipsisOutlined } from '@ant-design/icons-vue';
import agentNavIcon from '@/assets/image/svg/agent-icon-nav.svg';
import agentOpenIcon from '@/assets/image/svg/agent-open.svg';
import agentCloseIcon from '@/assets/image/svg/agent-close.svg';
import historyEmptyOrbit from '@/assets/image/png/history-empty-orbit-v2.png';
import vectorNavIcon from '@/assets/image/svg/icon-vector-nav.svg';
import knowledgeNavIcon from '@/assets/image/svg/knowledge-nav.svg';
import logoImage from '@/assets/ga-logo.svg';
import newChatNavIcon from '@/assets/image/svg/new-chat-nav.svg';
import newChatNav2Icon from '@/assets/image/svg/new-chat-nav-2.svg';
import searchNavIcon from '@/assets/image/svg/search-nav.svg';
import renameNavIcon from '@/assets/image/svg/rename-nav.svg';
import deleteNavIcon from '@/assets/image/svg/delete-nav.svg';
import sidebarCollapseIcon from '@/assets/image/svg/sidebar-collapse.svg';
import { getSystemName } from '@/utils/RuntimeConfig';
import StorageService from '@/utils/StorageService';
import { broadcastGlobalLogout } from '@/utils/TabScopeService';
import { ROUTES } from '@/config/constants';
import { useChatStore } from '@/stores/chat-store';

interface ChatHistoryRecord {
  id: string;
  sessionThreadId: string;
  title: string;
  preview: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
  chatType: string;
  agentId: string;
  summaryPending?: boolean;
}

interface Props {
  items?: ChatHistoryRecord[];
  loading?: boolean;
  runningSessionIds?: string[];
  total?: number;
  activeSessionThreadId?: string;
  activeWorkspace?: 'chat' | 'knowledge' | 'delivery' | 'agents';
}

type UserProfile = {
  username?: string;
  email?: string;
  avatar?: string;
  avatarBackground?: string;
  avatarTextColor?: string;
};

const props = withDefaults(defineProps<Props>(), {
  items: () => [],
  loading: false,
  runningSessionIds: () => [],
  total: 0,
  activeSessionThreadId: '',
  activeWorkspace: 'chat'
});

const isSessionRunning = (item: ChatHistoryRecord) => props.runningSessionIds.includes(item.sessionThreadId);

const emit = defineEmits<{
  (e: 'collapse'): void;
  (e: 'open-agent'): void;
  (e: 'agent-new-chat', agentId: string): void;
  (e: 'manage-agent', agentId: string): void;
  (e: 'open-knowledge'): void;
  (e: 'open-delivery'): void;
  (e: 'new-chat'): void;
  (e: 'select', item: ChatHistoryRecord): void;
  (e: 'rename', item: ChatHistoryRecord, summary: string): void;
  (e: 'delete', item: ChatHistoryRecord): void;
}>();

const openMenuId = ref<string | null>(null);
const openAgentMenuId = ref<string | null>(null);
const activeAgentMenuTooltipId = ref<string | null>(null);
const suppressedAgentMenuTooltipId = ref<string | null>(null);
const menuStyle = ref<Record<string, string>>({});
const agentMenuStyle = ref<Record<string, string>>({});
const editingId = ref<string | null>(null);
const editingTitle = ref('');
const renameInputRef = ref<HTMLInputElement | null>(null);
const renameSettlingId = ref<string | null>(null);
let renameSettleFrame = 0;

function setRenameInputRef(element: unknown) {
  renameInputRef.value = element as HTMLInputElement | null;
}

function handleSelectItem(item: ChatHistoryRecord) {
  if (editingId.value === item.id || item.summaryPending) return;
  emit('select', item);
}

const searchModalOpen = ref(false);
const searchQuery = ref('');
const searchInputRef = ref<HTMLInputElement | null>(null);

function openSearchModal() {
  searchQuery.value = '';
  searchTab.value = agentResultCount.value > 0 ? 'agent' : 'recent';
  searchModalOpen.value = true;
  hideHoverCard();
  void nextTick(() => searchInputRef.value?.focus());
}

function closeSearchModal() {
  searchModalOpen.value = false;
}

function handleSearchSelect(item: ChatHistoryRecord) {
  closeSearchModal();
  if (historySections.value.some(section => section.isAgent && section.items.some(record => record.id === item.id))) {
    agentSectionExpanded.value = true;
  } else {
    recentSectionExpanded.value = true;
  }
  emit('select', item);
}

function handleNewChatFromSearch() {
  closeSearchModal();
  emit('new-chat');
}

function onSearchDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeSearchModal();
}

watch(searchModalOpen, (value) => {
  if (value) {
    document.addEventListener('keydown', onSearchDocumentKeydown);
  } else {
    document.removeEventListener('keydown', onSearchDocumentKeydown);
  }
});

const DAY_MS = 86400000;

const isSearching = computed(() => searchQuery.value.trim() !== '');

const searchResults = computed<ChatHistoryRecord[]>(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return sortedItems.value.filter((item) => {
    if (item.summaryPending) return false;
    if (!query) return true;
    return item.title.toLowerCase().includes(query) || item.preview.toLowerCase().includes(query);
  });
});

// 搜索结果沿用左侧栏的分组，再按 Agent / 普通对话拆成两个标签页。
const searchSections = computed(() => {
  const matchedIds = new Set(searchResults.value.map(item => item.id));
  const sections: { id: string; title: string; isAgent: boolean; items: ChatHistoryRecord[] }[] = [];
  for (const section of historySections.value) {
    const items = section.items.filter(item => matchedIds.has(item.id));
    if (items.length > 0) sections.push({ id: section.id, title: section.title, isAgent: section.isAgent, items });
  }
  return sections;
});

const searchTab = ref<'agent' | 'recent'>('agent');
const agentSearchSections = computed(() => searchSections.value.filter(section => section.isAgent));
const recentSearchSections = computed(() => searchSections.value.filter(section => !section.isAgent));
const activeSearchSections = computed(() => (searchTab.value === 'agent' ? agentSearchSections.value : recentSearchSections.value));
const agentResultCount = computed(() => agentSearchSections.value.reduce((total, section) => total + section.items.length, 0));
const recentResultCount = computed(() => recentSearchSections.value.reduce((total, section) => total + section.items.length, 0));

// 关键词变化后，若当前标签页已无结果而另一侧有，则自动切过去。
watch(searchQuery, () => {
  if (searchTab.value === 'agent' && agentResultCount.value === 0 && recentResultCount.value > 0) searchTab.value = 'recent';
  else if (searchTab.value === 'recent' && recentResultCount.value === 0 && agentResultCount.value > 0) searchTab.value = 'agent';
});

// 弹窗内每个智能体分组可单独折叠，默认全部展开，与左侧栏的展开状态互不影响。
const searchCollapsedAgentIds = ref(new Set<string>());

function toggleSearchAgentGroup(id: string) {
  if (searchCollapsedAgentIds.value.has(id)) searchCollapsedAgentIds.value.delete(id);
  else searchCollapsedAgentIds.value.add(id);
}

const WEEK_LABELS = ['日', '一', '二', '三', '四', '五', '六'];

function formatSearchItemTime(item: ChatHistoryRecord): string {
  const date = safeDate(item.updatedAt || item.createdAt);
  if (!date) return '';
  const pad = (value: number) => String(value).padStart(2, '0');
  const clock = `${pad(date.getHours())}:${pad(date.getMinutes())}`;
  const now = new Date();
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  if (date.getTime() >= startOfToday - 7 * DAY_MS) return `周${WEEK_LABELS[date.getDay()]} ${clock}`;
  if (date.getFullYear() === now.getFullYear()) return `${date.getMonth() + 1}月${date.getDate()}日`;
  return `${date.getFullYear()}年${date.getMonth() + 1}月${date.getDate()}日`;
}

function computeMenuStyle(trigger: HTMLElement): Record<string, string> {
  const rect = trigger.getBoundingClientRect();
  const menuWidth = 148;
  const menuHeight = 83;
  const viewportGap = 8;
  const openUpward = rect.bottom + menuHeight + viewportGap > window.innerHeight;
  const left = Math.min(
    Math.max(viewportGap, rect.right - menuWidth),
    window.innerWidth - menuWidth - viewportGap
  );
  const preferredTop = openUpward ? rect.top - menuHeight - 6 : rect.bottom + 6;
  const top = Math.min(
    Math.max(viewportGap, preferredTop),
    window.innerHeight - menuHeight - viewportGap
  );
  return {
    left: `${left}px`,
    top: `${top}px`,
    transformOrigin: openUpward ? 'right bottom' : 'right top',
    '--history-menu-enter-y': openUpward ? '6px' : '-6px'
  };
}

function toggleMenu(event: MouseEvent, id: string) {
  if (openMenuId.value === id) {
    closeMenu();
    return;
  }
  hideHoverCard();
  menuStyle.value = computeMenuStyle(event.currentTarget as HTMLElement);
  openAgentMenuId.value = null;
  openMenuId.value = id;
}

function toggleAgentMenu(event: MouseEvent, id: string) {
  if (openAgentMenuId.value === id) {
    closeAgentMenu();
    return;
  }
  hideHoverCard();
  hideAgentMenuTooltip(id);
  clearAgentMenuTooltipSuppression(id);
  agentMenuStyle.value = computeMenuStyle(event.currentTarget as HTMLElement);
  openMenuId.value = null;
  openAgentMenuId.value = id;
}

function shouldShowAgentMenuTooltip(id: string) {
  return openAgentMenuId.value !== id && suppressedAgentMenuTooltipId.value !== id;
}

function handleAgentMenuTooltipMouseEnter(id: string) {
  if (!shouldShowAgentMenuTooltip(id)) return;
  activeAgentMenuTooltipId.value = id;
}

function handleAgentMenuTooltipMouseLeave(id: string) {
  hideAgentMenuTooltip(id);
  clearAgentMenuTooltipSuppression(id);
}

function hideAgentMenuTooltip(id?: string) {
  if (!id || activeAgentMenuTooltipId.value === id) {
    activeAgentMenuTooltipId.value = null;
  }
}

function suppressAgentMenuTooltip(id: string) {
  hideAgentMenuTooltip(id);
  suppressedAgentMenuTooltipId.value = id;
}

function clearAgentMenuTooltipSuppression(id?: string) {
  if (!id || suppressedAgentMenuTooltipId.value === id) {
    suppressedAgentMenuTooltipId.value = null;
  }
}

function closeMenu() {
  openMenuId.value = null;
}

function closeAgentMenu() {
  openAgentMenuId.value = null;
  hideAgentMenuTooltip();
}

function closeHistoryMenus() {
  closeMenu();
  closeAgentMenu();
}

function handleAgentNewChat(agentId: string) {
  suppressAgentMenuTooltip(agentId);
  (document.activeElement as HTMLElement | null)?.blur?.();
  closeAgentMenu();
  emit('agent-new-chat', agentId);
}

function handleAgentManage(agentId: string) {
  suppressAgentMenuTooltip(agentId);
  (document.activeElement as HTMLElement | null)?.blur?.();
  closeAgentMenu();
  emit('manage-agent', agentId);
}

const router = useRouter();
const route = useRoute();
const chatStore = useChatStore();

const accountMenuOpen = ref(false);

function toggleAccountMenu() {
  hideHoverCard();
  accountMenuOpen.value = !accountMenuOpen.value;
}

function closeAccountMenu() {
  accountMenuOpen.value = false;
}

function closeAllMenus() {
  closeHistoryMenus();
  closeAccountMenu();
}

// 悬停历史行时在其右侧弹出的详情卡片
const hoverCardItem = ref<ChatHistoryRecord | null>(null);
const hoverCardRef = ref<HTMLElement | null>(null);
const hoverCardStyle = ref<Record<string, string>>({});
const HOVER_SHOW_DELAY = 320;
const HOVER_CARD_WIDTH = 272;
const HOVER_CARD_FALLBACK_HEIGHT = 104;
let hoverShowTimer = 0;
let sidebarActive = true;

const hoverAgentName = computed(() => {
  const item = hoverCardItem.value;
  if (!item) return '';
  const agentId = String(item.agentId || '').trim();
  if (!agentId) return '';
  for (const agent of sidebarAgents.value) {
    const aliases = [agent.uuid, agent.id].map(value => String(value ?? '').trim());
    if (aliases.some(alias => alias && alias === agentId)) {
      return agent.name || agent.config?.basic?.name || '未命名智能体';
    }
  }
  return '';
});

// 后端 chat_type 全集，见 ChatView 的会话上报逻辑
const CHAT_TYPE_LABELS: Record<string, string> = {
  agent: '通用智能体',
  deepagent: '深度智能体',
  travel_planner: '旅行规划',
  kb_chat: '知识库问答',
  model: '普通对话'
};

const hoverDisplayName = computed(() => {
  const item = hoverCardItem.value;
  if (!item) return '';
  return hoverAgentName.value || CHAT_TYPE_LABELS[item.chatType] || '普通对话';
});

// 类型标签只在有智能体名时出现，否则会和主文案重复
const hoverTypeLabel = computed(() => {
  const item = hoverCardItem.value;
  if (!item || !hoverAgentName.value) return '';
  return CHAT_TYPE_LABELS[item.chatType] || '';
});

const hoverUpdatedText = computed(() => {
  const item = hoverCardItem.value;
  if (!item) return '';
  const date = safeDate(item.updatedAt || item.createdAt);
  if (!date) return '';
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}`;
});

function computeHoverCardStyle(trigger: HTMLElement, cardHeight: number): Record<string, string> {
  const rect = trigger.getBoundingClientRect();
  const viewportGap = 8;
  let left = rect.right + 10;
  if (left + HOVER_CARD_WIDTH > window.innerWidth - viewportGap) {
    left = Math.max(viewportGap, window.innerWidth - HOVER_CARD_WIDTH - viewportGap);
  }
  const top = Math.min(
    Math.max(viewportGap, rect.top - 6),
    window.innerHeight - cardHeight - viewportGap
  );
  return { left: `${left}px`, top: `${top}px` };
}

function scheduleHoverCard(item: ChatHistoryRecord, event: MouseEvent) {
  if (!sidebarActive) return;
  if (item.summaryPending || editingId.value === item.id) return;
  if (openMenuId.value || openAgentMenuId.value || accountMenuOpen.value || searchModalOpen.value) return;
  const trigger = event.currentTarget as HTMLElement;
  window.clearTimeout(hoverShowTimer);
  hoverShowTimer = window.setTimeout(() => {
    if (!sidebarActive || !trigger.isConnected || trigger.getClientRects().length === 0) return;
    if (openMenuId.value || openAgentMenuId.value || accountMenuOpen.value || searchModalOpen.value) return;
    if (item.summaryPending || editingId.value === item.id) return;
    hoverCardItem.value = item;
    hoverCardStyle.value = computeHoverCardStyle(trigger, HOVER_CARD_FALLBACK_HEIGHT);
    void nextTick(() => {
      const card = hoverCardRef.value;
      if (!sidebarActive || !trigger.isConnected || !card || hoverCardItem.value !== item) return;
      hoverCardStyle.value = computeHoverCardStyle(trigger, card.offsetHeight);
    });
  }, HOVER_SHOW_DELAY);
}

function hideHoverCard() {
  window.clearTimeout(hoverShowTimer);
  hoverCardItem.value = null;
}

function handleListScroll() {
  closeAllMenus();
  hideHoverCard();
}

function navigateAndClose(path: string) {
  hideHoverCard();
  closeAccountMenu();
  if (route.path !== path) void router.push(path);
}

let isLoggingOut = false;

async function handleLogout() {
  if (isLoggingOut) return;
  isLoggingOut = true;
  try {
    try {
      void chatStore.stopCurrentRequest();
    } catch {}
    try {
      chatStore.clearChat();
    } catch {}
    StorageService.clearForLogout();
    if (route.path !== ROUTES.LOGIN) {
      await router.replace(ROUTES.LOGIN);
    }
    broadcastGlobalLogout('manual');
  } finally {
    isLoggingOut = false;
  }
}

function onAccountDocumentClick() {
  closeAccountMenu();
}

function onAccountDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeAccountMenu();
}

watch(accountMenuOpen, (value) => {
  if (value) {
    document.addEventListener('click', onAccountDocumentClick);
    document.addEventListener('keydown', onAccountDocumentKeydown);
    window.addEventListener('resize', closeAccountMenu);
  } else {
    document.removeEventListener('click', onAccountDocumentClick);
    document.removeEventListener('keydown', onAccountDocumentKeydown);
    window.removeEventListener('resize', closeAccountMenu);
  }
});

async function handleRename(item: ChatHistoryRecord) {
  closeMenu();
  editingId.value = item.id;
  editingTitle.value = item.title;
  await nextTick();
  renameInputRef.value?.focus();
  renameInputRef.value?.select();
}

function submitRename(item: ChatHistoryRecord) {
  const summary = editingTitle.value.trim();
  if (!summary) {
    renameInputRef.value?.focus();
    return;
  }

  // 先锁住普通行的首两帧，避免 Enter 尚未抬起时重新挂载的行继承按压过渡。
  renameSettlingId.value = item.id;
  editingId.value = null;
  cancelAnimationFrame(renameSettleFrame);
  renameSettleFrame = requestAnimationFrame(() => {
    renameSettleFrame = requestAnimationFrame(() => {
      renameSettlingId.value = null;
    });
  });
  if (summary !== item.title) emit('rename', item, summary);
}

function cancelRename() {
  editingId.value = null;
  editingTitle.value = '';
}

function handleDelete(item: ChatHistoryRecord) {
  closeMenu();
  Modal.confirm({
    title: '确认删除对话',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: '确定要删除该历史对话记录吗？此操作不可恢复。',
    icon: null,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: () => emit('delete', item)
  });
}

const historyMenuOpen = computed(() => Boolean(openMenuId.value || openAgentMenuId.value));

function onDocumentClick() {
  closeHistoryMenus();
}

function onDocumentKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') closeHistoryMenus();
}

watch(historyMenuOpen, (value) => {
  if (value) {
    document.addEventListener('click', onDocumentClick);
    document.addEventListener('keydown', onDocumentKeydown);
    window.addEventListener('resize', closeHistoryMenus);
  } else {
    document.removeEventListener('click', onDocumentClick);
    document.removeEventListener('keydown', onDocumentKeydown);
    window.removeEventListener('resize', closeHistoryMenus);
  }
});

// KeepAlive 停用不会卸载组件，需主动清理 Teleport 浮层和延迟显示任务。
function clearSidebarOverlays() {
  hideHoverCard();
  closeAllMenus();
  closeSearchModal();
}

watch(() => route.fullPath, clearSidebarOverlays);

onActivated(() => {
  sidebarActive = true;
});

onDeactivated(() => {
  sidebarActive = false;
  clearSidebarOverlays();
});

onUnmounted(() => {
  sidebarActive = false;
  cancelAnimationFrame(renameSettleFrame);
  window.clearTimeout(hoverShowTimer);
  document.removeEventListener('click', onDocumentClick);
  document.removeEventListener('keydown', onDocumentKeydown);
  window.removeEventListener('resize', closeHistoryMenus);
  document.removeEventListener('click', onAccountDocumentClick);
  document.removeEventListener('keydown', onAccountDocumentKeydown);
  window.removeEventListener('resize', closeAccountMenu);
  document.removeEventListener('keydown', onSearchDocumentKeydown);
});

const systemName = computed(() => getSystemName() || 'MCP Client');

const userProfile = computed<UserProfile>(() => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) return {};
    return JSON.parse(raw) as UserProfile;
  } catch {
    return {};
  }
});

const userName = computed(() => (userProfile.value.username || '当前用户').trim() || '当前用户');
const userEmail = computed(() => (userProfile.value.email || '未配置邮箱').trim() || '未配置邮箱');
const userAvatar = computed(() => (userProfile.value.avatar || '').trim());
const userInitial = computed(() => userName.value.charAt(0).toUpperCase());
const avatarStyle = computed(() => ({
  backgroundColor: userProfile.value.avatarBackground || '#e5e7eb',
  color: userProfile.value.avatarTextColor || '#4b5563'
}));

const sortedItems = computed(() =>
  [...props.items].sort((a, b) => {
    const aTime = safeDate(a.updatedAt || a.createdAt)?.getTime() || 0;
    const bTime = safeDate(b.updatedAt || b.createdAt)?.getTime() || 0;
    return bTime - aTime;
  })
);

const sidebarAgents = ref(StorageService.getAgents() || []);
const expandedAgentIds = ref(new Set<string>(StorageService.get<string[]>('mcp-history-expanded-agent-ids', []) ?? []));
watch(expandedAgentIds, value => StorageService.set('mcp-history-expanded-agent-ids', [...value]), { deep: true });
const agentSectionExpanded = ref(StorageService.get<boolean>('mcp-history-agent-section-expanded', true) ?? true);
watch(agentSectionExpanded, value => StorageService.set('mcp-history-agent-section-expanded', value));
const recentSectionExpanded = ref(StorageService.get<boolean>('mcp-history-recent-section-expanded', true) ?? true);
watch(recentSectionExpanded, value => StorageService.set('mcp-history-recent-section-expanded', value));

function toggleRecentSection() {
  closeAllMenus();
  recentSectionExpanded.value = !recentSectionExpanded.value;
}

function toggleAgentSection() {
  closeAllMenus();
  agentSectionExpanded.value = !agentSectionExpanded.value;
}
const refreshSidebarAgents = () => { sidebarAgents.value = StorageService.getAgents() || []; };
window.addEventListener('agents-updated', refreshSidebarAgents);
onUnmounted(() => window.removeEventListener('agents-updated', refreshSidebarAgents));

const historySections = computed(() => {
  const groups = new Map<string, { id: string; title: string; isAgent: boolean; available: boolean; items: ChatHistoryRecord[] }>();
  const aliases = new Map<string, string>();
  for (const agent of sidebarAgents.value) {
    const id = String(agent.uuid || agent.id || '').trim();
    if (!id) continue;
    groups.set(id, { id, title: agent.name || agent.config?.basic?.name || '未命名智能体', isAgent: true, available: true, items: [] });
    for (const alias of [agent.uuid, agent.id]) {
      if (alias !== undefined && alias !== null && String(alias).trim()) aliases.set(String(alias).trim(), id);
    }
  }
  const recent = { id: 'recent', title: '最近对话', isAgent: false, available: false, items: [] as ChatHistoryRecord[] };
  for (const item of sortedItems.value) {
    const agentId = String(item.agentId || '').trim();
    const isAgentChat = ['agent', 'deepagent', 'travel_planner'].includes(item.chatType);
    if (!agentId && !isAgentChat) {
      recent.items.push(item);
      continue;
    }
    const id = aliases.get(agentId) || agentId || 'unresolved-agent';
    if (!groups.has(id)) groups.set(id, { id, title: agentId ? '已不可用的智能体' : '待识别智能体', isAgent: true, available: false, items: [] });
    groups.get(id)!.items.push(item);
  }
  return [...groups.values()].filter(group => group.items.length > 0).concat(recent);
});

function toggleAgentGroup(id: string) {
  closeAllMenus();
  if (expandedAgentIds.value.has(id)) expandedAgentIds.value.delete(id);
  else expandedAgentIds.value.add(id);
}

// 搜索或异步恢复会话时，自动展开当前会话所属的智能体。
watch([() => props.activeSessionThreadId, () => {
  if (!props.activeSessionThreadId) return;
  return historySections.value.find(group => group.isAgent && group.items.some(item => item.sessionThreadId === props.activeSessionThreadId))?.id;
}], ([, id]) => {
  if (id) {
    expandedAgentIds.value.add(id);
  }
}, { immediate: true });

function safeDate(value?: string): Date | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}
</script>

<style scoped>
.history-rail {
  --history-hover-background: rgba(57, 100, 254, 0.045);
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  padding: 12px 10px 14px;
  color: #22252b;
  background: #ffffff;
}

.history-rail::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  background:
    radial-gradient(circle 260px at top right, rgba(59, 130, 246, 0.22) 0%, rgba(59, 130, 246, 0.1) 45%, rgba(59, 130, 246, 0) 100%),
    radial-gradient(circle 240px at left bottom, rgba(124, 58, 237, 0.18) 0%, rgba(124, 58, 237, 0.08) 45%, rgba(124, 58, 237, 0) 100%);
  pointer-events: none;
}

.history-rail > * {
  position: relative;
  z-index: 1;
}

.history-rail-top {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.history-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 0 8px;
  margin-bottom: 5px;
}

.history-brand-logo {
  height: 30px;
  width: auto;
  border-radius: 10px;
  flex-shrink: 0;
}

.history-brand-copy {
  flex: 1;
  min-width: 0;
  height: 30px;
  display: flex;
  align-items: center;
}

.history-brand-name {
  font-size: 24px;
  line-height: 1;
  font-family: 'SmileySansOblique', sans-serif;
  color: #111827;
  white-space: nowrap;
  text-overflow: ellipsis;
  transform: translateY(2px);
}

.history-brand-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.history-icon-btn {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #7f8692;
  background: transparent;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    transform 0.15s ease;
}

.history-icon-btn:hover {
  background: #ffffff;
}

.history-icon-btn:active {
  transform: scale(0.94);
}

.history-icon-btn-img {
  width: 19px;
  height: 19px;
  display: block;
  filter: brightness(0.78);
}

.history-nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-nav-item {
  height: 36px;
  border: none;
  border-radius: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  background: transparent;
  color: #1a1a1a;
  font-size: 13px;
  cursor: pointer;
  text-align: left;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 0.15s ease,
    box-shadow 0.2s ease;
}

.history-nav-item :deep(.anticon) {
  font-size: 15px;
  color: #1a1a1a;
  flex-shrink: 0;
}

.history-nav-item-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: block;
}

.history-nav-item-icon-lg {
  width: 16px;
  height: 16px;
}

.history-nav-item.active {
  background: rgba(57, 100, 254, 0.1);
  color: #3964fe;
  font-weight: 600;
}

.history-nav-item.active .history-nav-item-icon {
  filter: invert(36%) sepia(100%) saturate(2448%) hue-rotate(220deg) brightness(100%) contrast(103%);
}

.history-nav-item:focus-visible {
  outline: 2px solid rgba(57, 100, 254, 0.45);
  outline-offset: 2px;
}

.history-nav-item:hover:not(.active) {
  background: rgba(57, 100, 254, 0.096);
}

.history-nav-item:active {
  background: rgba(57, 100, 254, 0.12);
  transform: scale(0.985);
}

.history-nav-item:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(57, 100, 254, 0.35);
}

.history-projects {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  margin-top: 14px;
}

.history-section-head {
  display: flex;
  align-items: center;
  padding: 0 12px;
  margin-bottom: 8px;
}

.history-section-title {
  font-size: 13px;
  color: #7c828d;
}

.history-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* 滚动条外扩进 .history-rail 的右内边距（10px），不占用列表内容宽度 */
  margin-right: -10px;
  padding-right: 2px;
  /* 槽位常驻：滚动条出现/消失都不改变内容宽度，列表不会重新排布 */
  scrollbar-gutter: stable;
  position: relative;
}

.history-list::-webkit-scrollbar {
  width: 6px;
}

.history-list::-webkit-scrollbar-track {
  background: transparent;
}

.history-list::-webkit-scrollbar-thumb {
  background: rgba(218, 231, 253, 0.7);
  border-radius: 999px;
  transition: background-color 0.3s ease-in-out;
}

.history-list::-webkit-scrollbar-thumb:hover {
  background-color: rgba(160, 190, 248, 0.8);
}

.history-group + .history-group {
  margin-top: 4px;
}

.history-group:last-of-type {
  margin-top: 5px;
}

.history-agent-heading {
  justify-content: space-between;
  min-height: 32px;
  padding: 0 5px 0 0;
  margin-bottom: 4px;
  border-radius: 9px;
  transition:
    background-color 0.2s ease,
    transform 0.15s ease;
}

/* 用 :focus-visible 而非 :focus-within：鼠标点击后按钮会保留焦点，
   否则高亮会一直挂着，直到点击别处才消失 */
.history-agent-heading:hover,
.history-agent-heading:has(:focus-visible) {
  background: var(--history-hover-background);
}

/* 按下反馈与 .history-agent-row 一致：整行底色加深 + 轻微缩放 */
.history-agent-heading:has(.history-agent-heading-toggle:active) {
  background: rgba(57, 100, 254, 0.12);
  transform: scale(0.985);
}

.history-agent-heading-toggle {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 6px;
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #7c828d;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.history-agent-heading-toggle:focus-visible {
  outline: 2px solid rgba(57, 100, 254, 0.5);
  outline-offset: -2px;
}

.history-agent-heading-chevron {
  width: 12px;
  height: 12px;
  opacity: 0;
  transform: rotate(90deg);
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.history-agent-heading-chevron.collapsed {
  opacity: 1;
  transform: rotate(0deg);
}

.history-agent-heading:hover .history-agent-heading-chevron,
.history-agent-heading:has(:focus-visible) .history-agent-heading-chevron {
  opacity: 1;
}

.history-agent-add {
  display: grid;
  place-items: center;
  width: 22px;
  height: 22px;
  flex-shrink: 0;
  padding: 0;
  border: 0;
  border-radius: 6px;
  color: #a7adb8;
  background: transparent;
  line-height: 1;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 110ms cubic-bezier(0.2, 0, 0, 1);
}

.history-agent-add svg {
  display: block;
  width: 14px;
  height: 14px;
}

.history-agent-toggle {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
  min-height: 36px;
  padding: 8px 12px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: inherit;
  font: inherit;
  font-size: 13px;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.18s ease;
}

.history-agent-toggle:hover,
.history-agent-add:hover {
  background: var(--history-hover-background);
}

/* 配置按钮目标小，hover 底色比通用行加深一档，反馈更明确 */
.history-agent-add:hover {
  background: rgba(57, 100, 254, 0.1);
}

/* 按下态与同为 22px 的 .history-line-more 保持一致 */
.history-agent-add:active {
  background: rgba(57, 100, 254, 0.2);
  color: #3964fe;
  transform: scale(0.88);
}

.history-agent-row {
  display: flex;
  align-items: center;
  border-radius: 9px;
  transition:
    background-color 0.2s ease,
    transform 0.15s ease;
}

.history-agent-row:hover,
.history-agent-row.menu-open {
  background: var(--history-hover-background);
}

.history-agent-row:has(.history-agent-toggle:active) {
  background: rgba(57, 100, 254, 0.12);
  transform: scale(0.985);
}

.history-agent-row:hover .history-agent-toggle,
.history-agent-row:focus-within .history-agent-toggle {
  background: transparent;
}

.history-agent-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  width: 0;
  opacity: 0;
  overflow: hidden;
  pointer-events: none;
}

.history-agent-row:hover .history-agent-actions,
.history-agent-row:has(.history-agent-action:focus-visible) .history-agent-actions,
.history-agent-row.menu-open .history-agent-actions {
  width: auto;
  padding-right: 5px;
  opacity: 1;
  overflow: visible;
  pointer-events: auto;
}

.history-agent-action {
  display: grid;
  place-items: center;
  flex-shrink: 0;
  width: 26px;
  height: 26px;
  padding: 5px;
  border: 0;
  border-radius: 6px;
  color: #7c828d;
  background: transparent;
  cursor: pointer;
}

.history-agent-new-chat-icon {
  display: block;
  width: 14px;
  height: 14px;
  object-fit: contain;
  opacity: 0.5;
}

/* 与配置按钮一致：小图标按钮 hover 底色比通用行加深一档 */
.history-agent-action:hover:not(:disabled) {
  background: rgba(57, 100, 254, 0.1);
}

.history-agent-action:focus-visible {
  outline: 2px solid rgba(57, 100, 254, 0.5);
}

.history-agent-action.visible {
  background: rgba(57, 100, 254, 0.12);
  color: #3964fe;
}

.history-agent-action:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

@media (hover: none) {
  .history-agent-actions {
    width: auto;
    padding-right: 5px;
    opacity: 1;
    overflow: visible;
    pointer-events: auto;
  }
}

.history-agent-toggle:focus-visible,
.history-agent-add:focus-visible {
  outline: 2px solid rgba(57, 100, 254, 0.5);
  outline-offset: -2px;
}

.history-agent-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.history-agent-children {
  margin: 3px 0 8px 20px;
  padding-left: 7px;
  border-left: 1px solid rgba(124, 130, 141, 0.22);
}

.history-agent-children .history-line {
  height: 34px;
  padding: 6px 8px;
  border-radius: 8px;
}

.history-agent-empty {
  margin: 0;
  padding: 9px 12px;
  color: #8b929d;
  font-size: 12px;
  line-height: 1.6;
}

.history-line {
  width: 100%;
  height: 36px;
  border: none;
  border-radius: 10px;
  background: transparent;
  padding: 8px 12px;
  text-align: left;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 0.15s ease,
  box-shadow 0.2s ease;
}

.history-line.editing {
  padding: 0;
  cursor: text;
  background: transparent;
  transform: none;
}

.history-line.summary-pending {
  padding: 0;
  cursor: default;
  pointer-events: none;
  overflow: hidden;
  background: transparent;
  transform: none;
}

.history-line-summary-skeleton {
  position: relative;
  overflow: hidden;
  width: 100%;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    rgba(226, 230, 238, 0.68) 0%,
    rgba(238, 241, 246, 0.82) 50%,
    rgba(226, 230, 238, 0.68) 100%
  );
}

.history-line-summary-skeleton::after {
  content: '';
  position: absolute;
  inset: 0 auto 0 -65%;
  width: 60%;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.78) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  opacity: 0;
  transform: translate3d(0, 0, 0);
  will-change: transform, opacity;
  animation: history-summary-shimmer 2.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

.history-line.rename-settling {
  transform: none;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}

.history-line-rename-input {
  width: 100%;
  height: 100%;
  box-sizing: border-box;
  border: 1px solid rgba(57, 100, 254, 0.72);
  border-radius: inherit;
  padding: 0 11px;
  outline: none;
  background: #ffffff;
  color: #20242c;
  font: inherit;
  font-size: 13px;
  line-height: 20px;
}

.history-line + .history-line {
  margin-top: 1px;
}

.history-line:hover {
  background: var(--history-hover-background);
}

.history-line-action {
  position: relative;
  flex: 0 0 22px;
  width: 22px;
  height: 22px;
  margin-left: 6px;
}
.history-line-action .history-line-more { margin-left: 0; }
.history-task-loading {
  position: absolute;
  inset: 0;
  margin: auto;
  width: 13px;
  height: 13px;
  box-sizing: border-box;
  border: 1.5px solid rgba(57, 100, 254, 0.2);
  border-top-color: #3964fe;
  border-radius: 50%;
  pointer-events: none;
  animation: history-task-spin 0.8s linear infinite;
}
.history-line .history-line-action.is-running .history-line-more { opacity: 0; }
.history-line:hover .history-line-action.is-running .history-line-more,
.history-line:focus-visible .history-line-action.is-running .history-line-more,
.history-line:has(.history-line-more:focus-visible) .history-line-action.is-running .history-line-more,
.history-line .history-line-action.is-running.menu-open .history-line-more { opacity: 1; }
.history-line:hover .history-task-loading,
.history-line:focus-visible .history-task-loading,
.history-line:has(.history-line-more:focus-visible) .history-task-loading,
.history-line-action.menu-open .history-task-loading { visibility: hidden; }
@keyframes history-task-spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .history-task-loading { animation: none; }
}
.history-line:hover .history-line-title { color: #3964fe; }

.history-line.active {
  background: rgba(57, 100, 254, 0.07);
}

.history-line:not(.editing):not(.rename-settling):active:not(:has(.history-line-more:active)) {
  background: rgba(57, 100, 254, 0.12);
  transform: scale(0.985);
}

.history-line.active .history-line-title {
  color: #5470d8;
  font-weight: 500;
}

.history-line:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(57, 100, 254, 0.28);
}

.history-line-main {
  display: flex;
  align-items: center;
  min-width: 0;
}

.history-line-title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 20px;
  color: #20242c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: color 0.2s ease;
}

.history-line-more {
  width: 22px;
  height: 22px;
  margin-left: 6px;
  flex-shrink: 0;
  border-radius: 6px;
  border: 0;
  padding: 0;
  background: transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #9aa1ab;
  cursor: pointer;
  opacity: 0;
  transition:
    opacity 0.15s ease,
    background-color 0.2s ease,
    color 0.2s ease,
    transform 110ms cubic-bezier(0.2, 0, 0, 1);
}

.history-line-more :deep(.anticon) {
  width: 14px;
  height: 14px;
  display: block;
  font-size: 14px;
}

.history-line:hover .history-line-more,
.history-line.active .history-line-more,
.history-line-more.visible {
  opacity: 1;
}

.history-line-more:hover,
.history-line-more.visible {
  background: rgba(57, 100, 254, 0.12);
  color: #3964fe;
}

.history-line-more:active {
  background: rgba(57, 100, 254, 0.2);
  transform: scale(0.88);
}

.history-line-menu {
  position: fixed;
  z-index: 1000;
  width: 148px;
  padding: 5px;
  overflow-y: auto;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  box-shadow:
    0 1px 2px rgba(17, 24, 39, 0.06),
    0 12px 32px rgba(17, 24, 39, 0.13);
  will-change: transform, opacity;
}

.history-menu-item {
  position: relative;
  width: 100%;
  min-height: 32px;
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 8px;
  border: none;
  border-radius: 7px;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  line-height: 18px;
  color: #26292f;
  text-align: left;
  cursor: pointer;
  transition:
    background-color 120ms ease,
    color 120ms ease;
}

.history-menu-item :deep(.anticon) {
  width: 15px;
  min-width: 15px;
  font-size: 15px;
  flex-shrink: 0;
}

.history-menu-item-icon {
  width: 14px;
  min-width: 14px;
  height: 14px;
  display: block;
  flex-shrink: 0;
}

.history-menu-item-icon.danger {
  width: 16px;
  min-width: 16px;
  height: 16px;
}

.history-menu-item span:not(.anticon) {
  flex: 1;
}

.history-menu-item:hover:not(:disabled) {
  background: #f4f5f7;
}

.history-menu-item:disabled {
  color: #b4bac4;
  cursor: not-allowed;
}

.history-menu-item:disabled .history-menu-item-icon {
  opacity: 0.5;
}

.history-menu-item.danger {
  color: #ff3b3f;
}

.history-menu-item.danger:hover {
  background: rgba(229, 72, 77, 0.08);
}

.history-menu-divider {
  height: 1px;
  margin: 3px 5px;
  background: #e9eaec;
}

.history-menu-pop-enter-active {
  transition:
    opacity 170ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 190ms cubic-bezier(0.16, 1, 0.3, 1);
}

.history-menu-pop-leave-active {
  pointer-events: none;
  transition:
    opacity 110ms ease-in,
    transform 130ms ease-in;
}

.history-menu-pop-enter-from,
.history-menu-pop-leave-to {
  opacity: 0;
  transform: translateY(var(--history-menu-enter-y, -6px)) scale(0.96);
}

/* 悬停详情卡片：白底圆角 + 阴影与 .history-line-menu 保持一致 */
.history-hover-card {
  position: fixed;
  z-index: 990;
  width: 272px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid rgba(17, 24, 39, 0.08);
  box-shadow:
    0 1px 2px rgba(17, 24, 39, 0.06),
    0 12px 32px rgba(17, 24, 39, 0.13);
  pointer-events: none;
  will-change: transform, opacity;
}

.history-hover-title {
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
  color: #20242c;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-all;
}

.history-hover-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  font-size: 12px;
  line-height: 16px;
  color: #8c8c8c;
}

.history-hover-meta svg,
.history-hover-meta-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
}

.history-hover-meta-icon {
  display: block;
  object-fit: contain;
}

.history-hover-meta-text {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.history-hover-tag {
  flex-shrink: 0;
  padding: 1px 8px;
  border-radius: 6px;
  background: #f0f1f3;
  font-size: 11px;
  line-height: 18px;
  color: #6b7280;
}

.history-hover-pop-enter-active {
  transition:
    opacity 160ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.history-hover-pop-leave-active {
  pointer-events: none;
  transition:
    opacity 100ms ease-in,
    transform 120ms ease-in;
}

.history-hover-pop-enter-from,
.history-hover-pop-leave-to {
  opacity: 0;
  transform: translateX(-6px) scale(0.97);
}

@media (prefers-reduced-motion: reduce) {
  .history-hover-pop-enter-active,
  .history-hover-pop-leave-active {
    transition: none;
  }
}

/*
 * 历史列表重排动画。
 * list_summary 刷新后条目按 update_time 重新排序，这里用 TransitionGroup 的 FLIP 位移，
 * 让“刚聊完的会话滑到顶部、其余条目依次补位”这个过程平滑可见。
 * 选择器写成 .history-line.history-reorder-* 是为了压过 .history-line 自带的 transform 过渡。
 */
.history-line-list {
  position: relative;
}

.history-line.history-reorder-move {
  transition: transform 420ms cubic-bezier(0.22, 1, 0.36, 1);
}

.history-line.history-reorder-enter-active {
  transition:
    opacity 240ms ease,
    transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}

.history-line.history-reorder-enter-from {
  opacity: 0;
  transform: translateY(-6px);
}

/* 离场条目脱离文档流，剩余条目才能立刻用 move 动画补位，而不是等它消失后跳一下 */
.history-line.history-reorder-leave-active {
  position: absolute;
  left: 0;
  transition:
    opacity 180ms ease,
    transform 180ms ease;
}

.history-line.history-reorder-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

@media (prefers-reduced-motion: reduce) {
  .history-line,
  .history-line-title,
  .history-line-more,
  .history-line-summary-skeleton,
  .history-line.history-reorder-move,
  .history-line.history-reorder-enter-active,
  .history-line.history-reorder-leave-active,
  .history-menu-pop-enter-active,
  .history-menu-pop-leave-active {
    transition: none;
  }

  .history-line:active {
    transform: none;
  }

  .history-line-more:active {
    transform: none;
  }
}

.history-empty {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, calc(-50% - 70px));
  width: calc(100% - 12px);
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #9aa1ab;
  font-size: 13px;
  text-align: center;
}

.history-empty-visual {
  width: 224px;
  height: 132px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: history-empty-float 4.8s ease-in-out infinite;
}

.history-empty-orbit {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  filter: opacity(0.88);
  animation: history-empty-breathe 3.6s ease-in-out infinite;
  margin-bottom: -15px;
}

.history-empty-title {
  color: #20242c;
  font-size: 15px;
  line-height: 1.4;
  font-weight: 600;
  letter-spacing: -0.01em;
}

.history-empty-description {
  max-width: 220px;
  margin: 3px 0 0;
  color: #8c93a0c7;
  font-size: 12px;
  line-height: 1.65;
}

.history-line-skeleton {
  height: 32px;
  border-radius: 10px;
  /* 与 .history-line 的 36px 行高对齐：32 + 4 = 36 */
  margin-bottom: 4px;
  background: linear-gradient(90deg, rgba(229, 231, 235, 0.72) 25%, rgba(255, 255, 255, 0.8) 50%, rgba(229, 231, 235, 0.72) 75%);
  background-size: 200% 100%;
  animation: rail-loading 2.2s ease-in-out infinite;
}

.history-account-wrap {
  position: relative;
  margin-top: 12px;
}

.history-account {
  padding: 8px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.history-account:hover {
  background: rgba(17, 24, 39, 0.045);
}

.history-account:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px rgba(57, 100, 254, 0.28);
}

.history-account-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
}

.history-account-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.history-account-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-account-name {
  font-size: 13px;
  font-weight: bold;
  color: #20242c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-content: space-around;
}

.history-account-email {
  font-size: 12px;
  color: #9aa1abe3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.account-menu {
  position: absolute;
  left: -2px;
  right: -2px;
  bottom: calc(100% + 6px);
  z-index: 60;
  padding: 8px;
  background: #ffffff;
  border: 1px solid rgba(17, 24, 39, 0.08);
  border-radius: 14px;
  box-shadow:
    0 1px 2px rgba(17, 24, 39, 0.06),
    0 12px 32px rgba(17, 24, 39, 0.13);
  max-height: calc(100vh - 96px);
  overflow-y: auto;
  transform-origin: 50% 100%;
}

.account-menu::-webkit-scrollbar {
  width: 5px;
}

.account-menu::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.4);
  border-radius: 999px;
}

.account-menu-user {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
}

.account-menu-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 700;
}

.account-menu-avatar-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.account-menu-user-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.account-menu-user-name {
  font-size: 14px;
  font-weight: 600;
  color: #17181c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.account-menu-user-type {
  font-size: 12px;
  color: #71717a;
}

.account-menu-list {
  display: flex;
  flex-direction: column;
  padding-top: 6px;
}

.account-menu-item {
  width: 100%;
  height: 34px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: #17181c;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.account-menu-item:hover {
  background: #f4f4f5;
}

.account-menu-item span {
  flex: 1;
  min-width: 0;
}

.account-menu-item.danger {
  color: #e5484d;
}

.account-menu-item.danger:hover {
  background: rgba(229, 72, 77, 0.08);
}

.account-menu-divider {
  height: 1px;
  margin: 6px 2px;
  background: #ececef;
}

.am-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: block;
}

.am-icon-xs {
  width: 14px;
  height: 14px;
}

.account-menu-pop-enter-active {
  transition:
    opacity 170ms cubic-bezier(0.16, 1, 0.3, 1),
    transform 190ms cubic-bezier(0.16, 1, 0.3, 1);
}

.account-menu-pop-leave-active {
  pointer-events: none;
  transition:
    opacity 110ms ease-in,
    transform 130ms ease-in;
}

.account-menu-pop-enter-from,
.account-menu-pop-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.97);
}

@media (prefers-reduced-motion: reduce) {
  .account-menu-pop-enter-active,
  .account-menu-pop-leave-active {
    transition: none;
  }
}

@keyframes rail-loading {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@keyframes history-summary-shimmer {
  0% {
    opacity: 0;
    transform: translate3d(0, 0, 0);
  }
  8% {
    opacity: 1;
  }
  84% {
    opacity: 1;
  }
  100% {
    opacity: 0;
    transform: translate3d(350%, 0, 0);
  }
}

@media (prefers-reduced-motion: reduce) {
  .history-line-summary-skeleton::after {
    animation: none;
    opacity: 0.45;
    transform: translate3d(175%, 0, 0);
  }
}

@keyframes history-empty-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@keyframes history-empty-breathe {
  0%,
  100% {
    opacity: 0.78;
    transform: scale(0.985);
  }
  50% {
    opacity: 1;
    transform: scale(1.015);
  }
}

@media (prefers-reduced-motion: reduce) {
  .history-empty-visual,
  .history-empty-orbit {
    animation: none;
  }
}

/* 搜索模态窗口 */
.search-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(255, 255, 255, 0.6);
}

.search-modal {
  width: 720px;
  max-width: 100%;
  height: min(600px, calc(100vh - 96px));
  display: flex;
  flex-direction: column;
  background: #f7f7f8;
  border: 1px solid rgba(17, 24, 39, 0.06);
  border-radius: 16px;
  box-shadow:
    0 1px 2px rgba(17, 24, 39, 0.05),
    0 18px 48px rgba(17, 24, 39, 0.16);
  overflow: hidden;
}

.search-modal-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 13px 16px;
  border-bottom: 1px solid #e8e8ea;
}

.search-modal-header-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: block;
  filter: brightness(0.6);
}

.search-modal-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-size: 14px;
  color: #20242c;
}

.search-modal-input::placeholder {
  color: #9aa1ab;
}

.search-modal-close {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border: none;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  color: #7f8692;
  font-size: 14px;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    transform 0.15s ease;
}

.search-modal-close:hover {
  background: #ececee;
  color: #20242c;
}

.search-modal-close:active {
  transform: scale(0.92);
}

.search-modal-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 10px 12px 0;
}

.search-modal-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}

.search-modal-tab {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border: none;
  border-radius: 999px;
  background: transparent;
  font-family: inherit;
  font-size: 13px;
  color: #6b7280;
  cursor: pointer;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}

.search-modal-tab:hover {
  background: #ececee;
  color: #20242c;
}

.search-modal-tab.active {
  background: #ffffff;
  color: #1a1a1a;
  font-weight: 600;
  box-shadow:
    inset 0 0 0 1px rgba(17, 24, 39, 0.05),
    0 1px 2px rgba(17, 24, 39, 0.08);
}

.search-modal-tab-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: block;
}

.search-modal-tab-count {
  min-width: 17px;
  height: 17px;
  padding: 0 5px;
  border-radius: 999px;
  background: #e8e8ea;
  font-size: 11px;
  line-height: 17px;
  font-weight: 500;
  text-align: center;
  color: #7f8692;
}

.search-modal-tab.active .search-modal-tab-count {
  background: rgba(57, 100, 254, 0.12);
  color: #3964fe;
}

.search-modal-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 10px 14px;
  display: flex;
  flex-direction: column;
}

.search-modal-body::-webkit-scrollbar {
  width: 5px;
}

.search-modal-body::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.4);
  border-radius: 999px;
}

.search-result {
  flex-shrink: 0;
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.search-result:hover {
  background: #ffffff;
}

.search-result-icon {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #e8e8ea;
  color: #6b7280;
}

.search-result-icon svg {
  width: 13px;
  height: 13px;
  display: block;
}

.search-result-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.search-result-title {
  font-size: 13px;
  line-height: 18px;
  font-weight: 600;
  color: #1a1a1a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-result-preview {
  font-size: 11px;
  line-height: 14px;
  color: #8c8c8c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-result-time {
  flex-shrink: 0;
  font-size: 12px;
  color: #8c8c8c;
}

.search-group {
  flex-shrink: 0;
}

.search-group + .search-group {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #ececee;
}

.search-group-head {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  min-height: 32px;
  padding: 4px 10px;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-family: inherit;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.18s ease;
}

.search-group-head:hover {
  background: #ececee;
}

.search-group-head:focus-visible {
  outline: 2px solid rgba(57, 100, 254, 0.5);
  outline-offset: -2px;
}

.search-group-head-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  display: block;
}

.search-group-title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  line-height: 18px;
  font-weight: 500;
  color: #4b515b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-group-list-agent {
  margin-left: 16px;
  padding-left: 8px;
  border-left: 1px solid rgba(124, 130, 141, 0.22);
}

.search-modal-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.search-modal-empty-icon {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #ececef;
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-modal-empty-icon img {
  width: 20px;
  height: 20px;
  opacity: 0.5;
}

.search-modal-empty-title {
  margin-top: 12px;
  font-size: 13px;
  color: #6b7280;
}

.search-modal-fade-enter-active {
  transition: opacity 180ms cubic-bezier(0.16, 1, 0.3, 1);
}

.search-modal-fade-leave-active {
  pointer-events: none;
  transition: opacity 120ms ease-in;
}

.search-modal-fade-enter-from,
.search-modal-fade-leave-to {
  opacity: 0;
}

.search-modal-pop-enter-active {
  transition: transform 200ms cubic-bezier(0.16, 1, 0.3, 1);
}

.search-modal-pop-leave-active {
  pointer-events: none;
  transition: transform 140ms ease-in;
}

.search-modal-pop-enter-from,
.search-modal-pop-leave-to {
  transform: scale(0.97);
}

@media (prefers-reduced-motion: reduce) {
  .search-modal-fade-enter-active,
  .search-modal-fade-leave-active,
  .search-modal-pop-enter-active,
  .search-modal-pop-leave-active {
    transition: none;
  }
}
</style>

<style>
.confirm-delete-modal .ant-modal-content {
  border-radius: 18px !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn {
  height: 30px !important;
  border-radius: 8px !important;
  font-size: 14px !important;
  padding: 0 20px !important;
  border: none !important;
  box-shadow: none !important;
  transition: all 0.3s !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-default {
  background-color: #f5f5f5 !important;
  color: #1a1a1a !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-default:hover {
  background-color: #e6e6e6 !important;
  color: #1a1a1a !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-primary {
  background: #ff5959 !important;
  color: #ffffff !important;
}

.confirm-delete-modal .ant-modal-confirm-btns .ant-btn-primary:hover {
  background-color: #ff4040 !important;
  color: #ffffff !important;
}
</style>
