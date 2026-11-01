<template>
  <div class="knowledge-base" :class="{ 'knowledge-base-workspace': layout === 'workspace' }">
    <KnowledgeWorkspace
      v-if="layout === 'workspace'"
      :knowledge-bases="knowledgeBases"
      :selected-knowledge-base="selectedKnowledgeBase"
      :loading="kbListSkeletonVisible"
      :refreshing="kbListRefreshing"
      :docs-loading="docsLoading"
      :docs-error="docsError"
      :error="kbListError"
      :is-admin="isCurrentUserAdmin"
      :active-kg-task-kb-names="activeKgTaskKbNames"
      v-model:search-keyword="searchKeyword"
      v-model:permission-filter="kbPermissionFilter"
      @back="emit('back')"
      @refresh="refreshKnowledgeBase"
      @create="showCreateModal"
      @config="showRetrievalConfigModal"
      @select="selectKnowledgeBase"
      @close="closeKnowledgeWorkspace"
      @edit="editKnowledgeBase"
      @delete="deleteKnowledgeBase"
      @graph="handleOpenKgModal"
    >
      <template #default="{ knowledgeBase, loading, error }">
      <KBDetail
        :key="selectedKnowledgeBase?.id"
        title="收录的文档"
        :selectedKnowledgeBase="knowledgeBase"
        :docsLoading="loading"
        :docs-error="error"
        @retry="loadSelectedKnowledgeBaseFiles({ force: true })"
        v-model:documentSearchKeyword="documentSearchKeyword"
        :loadingIndicator="loadingIndicator"
        :kgTasks="kgTasks"
        :kgPendingDocNameMap="currentKgPendingDocNameMap"
        :isCurrentUserAdmin="isCurrentUserAdmin"
        @upload="showUploadModal"
        @preview="previewDocument"
        @download="downloadDocument"
        @delete="deleteDocument"
        @bulk-download="bulkDownloadDocuments"
        @bulk-delete="bulkDeleteDocuments"
      />
      </template>
    </KnowledgeWorkspace>
    <template v-else>
    <KBHeader :isAdmin="isCurrentUserAdmin" @refresh="refreshKnowledgeBase" @create="showCreateModal" @config="showRetrievalConfigModal" />

    <!-- 主内容区域 -->
    <div class="content-container">
      <!-- 知识库列表 -->
      <KBList
        :knowledgeBases="knowledgeBases"
        :kbListLoading="kbListLoading"
        :selectedKnowledgeBase="selectedKnowledgeBase"
        v-model:searchKeyword="searchKeyword"
        v-model:permissionFilter="kbPermissionFilter"
        :loadingIndicator="loadingIndicator"
        :activeKgTaskKbNames="activeKgTaskKbNames"
        :isCurrentUserAdmin="isCurrentUserAdmin"
        @select="selectKnowledgeBase"
        @edit="editKnowledgeBase"
        @delete="deleteKnowledgeBase"
        @openKgModal="handleOpenKgModal"
      />

      <KBDetail
        :key="selectedKnowledgeBase?.id"
        :selectedKnowledgeBase="selectedKnowledgeBase"
        :docsLoading="docsLoading"
        :docs-error="docsError"
        @retry="loadSelectedKnowledgeBaseFiles({ force: true })"
        v-model:documentSearchKeyword="documentSearchKeyword"
        :loadingIndicator="loadingIndicator"
        :kgTasks="kgTasks"
        :kgPendingDocNameMap="currentKgPendingDocNameMap"
        :isCurrentUserAdmin="isCurrentUserAdmin"
        @upload="showUploadModal"
        @preview="previewDocument"
        @download="downloadDocument"
        @delete="deleteDocument"
        @bulk-download="bulkDownloadDocuments"
        @bulk-delete="bulkDeleteDocuments"
      />
    </div>
    </template>

    <!-- 创建知识库模态框 -->
    <a-modal
        v-model:open="createModalVisible"
        centered
        :title="null"
        :footer="null"
        width="850px"
        :maskClosable="!creatingKb"
        :keyboard="!creatingKb"
        :closable="false"
        class="create-kb-modal-wrapper"
    >
      <div class="kb-layout">
        <!-- Sidebar -->
        <div class="kb-sidebar">
          <div class="sidebar-header">
            <h3>创建知识库</h3>
          </div>
          <div class="sidebar-menu-kb-model">
            <a-menu
              mode="inline"
              :selectedKeys="[currentStep]"
              style="border-inline-end: none;"
            >
              <a-menu-item key="basic" @click="currentStep = 'basic'">
                <template #icon><InfoCircleOutlined /></template>
                <span>基本信息</span>
              </a-menu-item>
              <a-menu-item key="model" @click="currentStep = 'model'">
                <template #icon><DeploymentUnitOutlined /></template>
                <span>模型配置</span>
              </a-menu-item>
              <a-menu-item key="graph" @click="currentStep = 'graph'">
                <template #icon><ShareAltOutlined /></template>
                <span>知识图谱</span>
              </a-menu-item>
            </a-menu>
          </div>
        </div>

        <!-- Content -->
        <div class="kb-content">
          <div class="content-header-area">
             <div class="header-title" v-if="currentStep === 'basic'">
                <h3>基本信息</h3>
                <p>设置知识库的名称和描述信息</p>
             </div>
             <div class="header-title" v-else-if="currentStep === 'model'">
                <h3>模型配置</h3>
                <p>配置向量数据库和 Embedding 模型</p>
             </div>
             <div class="header-title" v-else-if="currentStep === 'graph'">
                <h3>知识图谱</h3>
                <p>配置实体关系提取功能，自动从文本中提取实体和关系构建知识图谱</p>
             </div>
             <button class="close-btn" @click="onCreateModalCancel" :disabled="creatingKb">
                 <CloseOutlined style="font-size: 14px; color: #999;" />
             </button>
          </div>

          <div class="content-body">
            <a-form :model="createForm" layout="vertical" class="kb-form">
              <!-- Basic Info -->
              <div v-show="currentStep === 'basic'">
                <a-form-item label="知识库名称" required>
                  <a-input v-model:value="createForm.name" placeholder="请输入知识库名称" show-count :maxlength="50"/>
                </a-form-item>
                <a-form-item label="知识库描述" required>
                  <a-textarea v-model:value="createForm.description" placeholder="请输入知识库描述，便于智能体查找"
                              :auto-size="{ minRows: 4, maxRows: 6 }"
                              show-count
                              :maxlength="200"/>
                </a-form-item>
                <a-form-item required class="kb-visibility-form-item">
                  <div class="kb-visibility-row">
                    <div class="ant-form-item-label kb-visibility-inline-label">
                      <label class="ant-form-item-required" title="可见范围">可见范围</label>
                    </div>
                    <div
                      class="bi-visibility-segment"
                      :class="{ 'is-readonly': !canEditVisibility }"
                      :data-active="createForm.permissionCode"
                      role="tablist"
                      aria-label="可见范围"
                    >
                      <button
                        type="button"
                        class="bi-visibility-segment-option"
                        :class="{ active: createForm.permissionCode === 'private' }"
                        :aria-pressed="createForm.permissionCode === 'private'"
                        :disabled="!canEditVisibility"
                        @click="updateCreateVisibility('private')"
                      >
                        个人使用
                      </button>
                      <button
                        type="button"
                        class="bi-visibility-segment-option"
                        :class="{ active: createForm.permissionCode === 'public' }"
                        :aria-pressed="createForm.permissionCode === 'public'"
                        :disabled="!canEditVisibility"
                        @click="updateCreateVisibility('public')"
                      >
                        公开共享
                      </button>
                    </div>
                  </div>
                  <div v-if="!canEditVisibility" class="kb-form-help">{{ KB_VISIBILITY_ADMIN_ONLY_TIP }}</div>
                </a-form-item>
                <a-form-item
                  v-if="canEditVisibility && createForm.permissionCode === 'public'"
                  required
                  class="kb-permission-groups-form-item"
                  label="可访问用户组"
                >
                  <a-select
                    v-model:value="createForm.permissionGroupIds"
                    mode="multiple"
                    :options="permissionGroupOptions"
                    :loading="permissionGroupsLoading"
                    :disabled="permissionGroupsLoading"
                    :virtual="false"
            popupClassName="user-group-select-dropdown"
                    max-tag-count="responsive"
                    placeholder="请选择用户组"
                    style="width: 100%;"
                    @change="handleCreatePermissionGroupsChange"
                  />
                  <div class="kb-form-help">公开后仅这些用户组可访问该知识库</div>
                </a-form-item>
              </div>

              <!-- Model Config -->
              <div v-show="currentStep === 'model'">
                <a-form-item label="向量库类型" required>
                  <a-select v-model:value="createForm.vsType" placeholder="请选择向量库类型">
                    <a-select-option v-for="type in vectorStoreTypes" :key="type" :value="type">{{ type }}</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="Embedding模型" required>
                  <a-select v-model:value="createForm.embedModel" placeholder="请选择 Embedding 模型">
                    <a-select-option v-for="model in embeddingModels" :key="model" :value="model">{{ model }}</a-select-option>
                  </a-select>
                </a-form-item>
              </div>

              <!-- Knowledge Graph -->
              <div v-show="currentStep === 'graph'" class="graph-config-container">
                <div class="config-section" style="margin-bottom: -24px;">
                  <a-form-item>
                    <div class="section-row">
                      <div class="section-info">
                        <div class="section-title">启用实体关系提取</div>
                        <div class="section-desc">开启后将自动从文本中提取实体和关系</div>
                      </div>
                      <a-switch v-model:checked="createForm.enableGraphRag" />
                    </div>
                  </a-form-item>
                </div>

                <div class="config-divider" v-if="createForm.enableGraphRag"></div>

                <div v-if="createForm.enableGraphRag">
                  <a-form-item label="图数据库类型" required>
                    <a-select v-model:value="createForm.kgType" placeholder="请选择图数据库类型">
                      <a-select-option value="neo4j">neo4j</a-select-option>
                    </a-select>
                  </a-form-item>

                  <a-form-item class="top-aligned-label" required>
                    <template #label>
                      <div class="section-info">
                        <div class="section-title">实体类型</div>
                        <div class="section-desc">定义要提取的实体类型标签，多个标签用逗号分隔</div>
                      </div>
                    </template>
                    <div class="section-control-row">
                      <button class="generate-tags-btn" @click.prevent="generateRandomEntityTags">生成随机标签</button>
                      <a-select
                        v-model:value="createForm.allowedNodes"
                        mode="tags"
                        class="scrollable-tags-select"
                        style="width: 100%"
                        placeholder="输入实体类型，如：人物、地点、组织等"
                        :options="[]"
                        :token-separators="[',', '，']"
                      />
                    </div>
                  </a-form-item>

                  <a-form-item class="top-aligned-label" required>
                    <template #label>
                      <div class="section-info">
                        <div class="section-title">关系类型</div>
                        <div class="section-desc">定义要提取的关系类型标签，多个标签用逗号分隔</div>
                      </div>
                    </template>
                    <div class="section-control-row">
                      <button class="generate-tags-btn" @click.prevent="generateRandomRelationshipTags">生成随机标签</button>
                      <a-select
                        v-model:value="createForm.allowedRelationships"
                        mode="tags"
                        class="scrollable-tags-select"
                        style="width: 100%"
                        placeholder="输入关系类型，如：工作于、同事、朋友等"
                        :options="[]"
                        :token-separators="[',', '，']"
                      />
                    </div>
                  </a-form-item>
                  <a-form-item>
                    <template #label>
                      <div class="section-info">
                        <div class="section-title">示例文本</div>
                        <div class="section-desc">用于测试实体关系提取的示例文本</div>
                      </div>
                    </template>
                    <div class="section-control-col">
                      <a-textarea
                        v-model:value="createForm.exampleText"
                        placeholder="输入一段包含实体和关系的文本..."
                        :auto-size="{ minRows: 4, maxRows: 6 }"
                        show-count
                        :maxlength="5000"
                        style="width: 100%"
                      />
                    </div>
                  </a-form-item>
                  <a-form-item>
                    <div class="section-row">
                      <div class="section-info">
                        <div class="section-title">提取操作</div>
                        <div class="section-desc">执行实体关系提取或管理示例数据</div>
                      </div>
                      <button 
                        class="extract-btn"
                        :loading="isExtracting"
                        @click="handleExtract"
                      >
                        <template v-if="isExtracting">
                          <LoadingOutlined style="margin-right: 4px;" /> 提取中
                        </template>
                        <template v-else>
                          开始提取
                        </template>
                      </button>
                    </div>
                  </a-form-item>

                  <!-- 关系列表 -->
                  <div v-if="extractedRelationships.length > 0">
                    <a-divider />
                    
                    <!-- 关系列表 -->
                    <a-form-item>
                      <div class="section-row" style="flex-direction: column; align-items: stretch;">
                        <div class="section-info" style="margin-bottom: 16px;">
                          <div class="section-title">实体关系列表</div>
                          <div class="section-desc">定义实体之间的关系连接</div>
                        </div>
                        
                        <div class="relationship-list-container">
                          <div v-for="(rel, index) in extractedRelationships" :key="rel.id" class="relationship-row">
                            <a-select 
                              v-model:value="rel.head" 
                              class="rel-select"
                              :options="extractedEntities.map(e => ({ value: e.name, label: e.name }))"
                              show-search
                            />
                            <span class="rel-arrow">→</span>
                            <a-select 
                              v-model:value="rel.edge" 
                              class="rel-select"
                              :options="createForm.allowedRelationships.map(r => ({ value: r, label: r })).concat(rel.edge && !createForm.allowedRelationships.includes(rel.edge) ? [{ value: rel.edge, label: rel.edge }] : [])"
                              show-search
                            />
                            <span class="rel-arrow">→</span>
                            <a-select 
                              v-model:value="rel.tail" 
                              class="rel-select"
                              :options="extractedEntities.map(e => ({ value: e.name, label: e.name }))"
                              show-search
                            />
                            <a-button type="text" class="delete-btn" @click="removeRelationship(index)">
                              <template #icon><DeleteOutlined /></template>
                            </a-button>
                          </div>
                        </div>
                      </div>
                    </a-form-item>
                  </div>
                </div>
              </div>

            </a-form>
          </div>

          <div class="content-footer">
            <a-button class="custom-btn cancel-btn" @click="onCreateModalCancel" :disabled="creatingKb">取消</a-button>
            <a-button class="custom-btn confirm-btn" @click="handleCreateKnowledgeBase" :loading="creatingKb" style="width: 110px;">
              {{ creatingKb ? '创建中' : '创建知识库' }}
            </a-button>
          </div>
        </div>
      </div>
    </a-modal>

    <!-- 上传文档模态框 -->
    <a-modal
        v-model:open="uploadModalVisible"
        title="添加知识文件"
        @ok="handleUploadDocument"
        @cancel="resetUploadForm"
        centered
        :width="550"
        :confirmLoading="uploading"
        :maskClosable="!uploading"
        :keyboard="!uploading"
        :closable="!uploading"
        :cancelButtonProps="{ disabled: uploading }"
        okText="上传"
        cancelText="取消"
        class="upload-modal"
    >
      <div class="elegant-upload-wrapper">
        <div
          class="elegant-drop-area"
          :class="{
            'is-active': isUploadDragging,
            'is-disabled': uploading,
            'has-content': uploadFileList.length > 0
          }"
          @click="triggerUploadFileSelect"
          @dragenter.prevent.stop="handleUploadDragEnter"
          @dragover.prevent.stop="handleUploadDragOver"
          @dragleave.prevent.stop="handleUploadDragLeave"
          @drop.prevent.stop="handleUploadDrop"
        >
          <input
            ref="uploadFileInputRef"
            class="elegant-file-input"
            type="file"
            multiple
            accept=".txt,.md,.pdf,.docx,.doc,.csv,.xls,.xlsx,.pptx,.png,.jpg,.jpeg,.bmp"
            :disabled="uploading"
            @change="handleUploadFileInputChange"
          />
          
          <div class="elegant-upload-content">
            <div class="elegant-icon-ring">
              <LoadingOutlined v-if="uploading" class="modern-icon spinning" />
              <CloudUploadOutlined v-else />
            </div>
            <div class="elegant-text-group">
              <h4 class="elegant-main-text">{{ uploadDraggerText }}</h4>
              <p class="elegant-sub-text">{{ uploadDraggerHint }}</p>
            </div>
          </div>

          <!-- 将文件列表移入 elegant-drop-area 内部 -->
          <div v-if="uploadFileList.length > 0" class="innovative-file-list" @click.stop>
            <div
              v-for="file in uploadFileList"
              :key="String(file.uid || file.name)"
              class="innovative-file-row"
              :class="{ 'is-error': !!getUploadFileFailedReason(file) }"
            >
              <div class="innovative-file-icon">
                <CloseCircleOutlined v-if="getUploadFileFailedReason(file)" />
                <img
                  v-else-if="getFileIconSrc(file.name)"
                  :src="getFileIconSrc(file.name)"
                  :alt="`${file.name} icon`"
                  class="innovative-file-icon-img"
                />
                <FileOutlined v-else />
              </div>
              
              <div class="innovative-file-info">
                <span class="innovative-file-name" :title="file.name">{{ file.name }}</span>
                <div class="innovative-file-meta">
                  <span
                    v-if="getUploadFileFailedReason(file)"
                    class="innovative-file-error"
                    :title="getUploadFileFailedReason(file)"
                  >
                    {{ getUploadFileFailedReason(file) }}
                  </span>
                  <span v-else>
                    {{ formatUploadFileSize(file.size) }}
                  </span>
                </div>
              </div>

              <button
                type="button"
                class="innovative-file-action"
                :disabled="uploading"
                @click.stop.prevent="removeUploadFile(file)"
                title="移除"
              >
                <CloseOutlined />
              </button>
            </div>
          </div>
        </div>
      </div>

      <a-form layout="vertical" class="upload-modal-form" style="margin-top: 10px;">
        <a-form-item label="单段文本最大长度" required>
          <a-input-number
              v-model:value="uploadOptions.chunkSize"
              :min="1"
              :step="10"
              style="width: 100%"
          />
        </a-form-item>
        <a-form-item label="相邻文本重合长度" required>
          <a-input-number
              v-model:value="uploadOptions.chunkOverlap"
              :min="0"
              :max="1000"
              :step="5"
              style="width: 100%"
          />
        </a-form-item>
        <div class="upload-modal-classification">
          <div class="upload-modal-classification-meta">
            <div class="upload-modal-classification-label">文件密级</div>
            <div class="upload-modal-classification-hint">用于标识本次上传文档的保密等级</div>
          </div>
          <div
            class="upload-modal-classification-group"
            :class="{ 'is-internal': uploadOptions.classification === 'internal', 'is-empty': !uploadOptions.classification }"
          >
            <div class="upload-modal-classification-indicator"></div>
            <button
              type="button"
              class="upload-modal-classification-btn"
              :class="{ 'is-active': uploadOptions.classification === 'public' }"
              @click="uploadOptions.classification = 'public'"
            >
              非密
            </button>
            <button
              type="button"
              class="upload-modal-classification-btn"
              :class="{ 'is-active': uploadOptions.classification === 'internal' }"
              @click="uploadOptions.classification = 'internal'"
            >
              内部
            </button>
          </div>
        </div>

        <div class="upload-modal-zh-title-enhance">
          <label class="zh-title-enhance-label">
            <input
              type="checkbox"
              class="zh-title-enhance-checkbox"
              :checked="uploadOptions.zhTitleEnhance"
              @change="uploadOptions.zhTitleEnhance = ($event.target as HTMLInputElement).checked"
            />
            <span class="zh-title-enhance-indicator"></span>
            <span class="zh-title-enhance-text">开启中文标题增强 (仅对md格式文档有效)</span>
          </label>
        </div>
      </a-form>
    </a-modal>

    <!-- 编辑知识库信息模态框 -->
    <a-modal
        v-model:open="editModalVisible"
        title="编辑知识库信息"
        @cancel="onEditModalCancel"
        centered
        :maskClosable="!editingKbLoading"
        :keyboard="!editingKbLoading"
        :closable="!editingKbLoading"
        class="edit-kb-modal"
    >
      <a-form :model="editForm" layout="vertical">
        <a-form-item label="知识库名称" required>
          <a-input
            v-model:value="editForm.name"
            placeholder="请输入知识库名称"
            show-count
            :maxlength="50"
            :disabled="isSharedKnowledgeBaseReadonly || editingKbLoading"
          />
        </a-form-item>
        <a-form-item required class="kb-visibility-form-item">
          <div class="kb-visibility-row">
            <div class="ant-form-item-label kb-visibility-inline-label">
              <label class="ant-form-item-required" title="可见范围">可见范围</label>
            </div>
            <div
              class="bi-visibility-segment"
              :class="{ 'is-readonly': !canEditVisibility }"
              :data-active="editForm.permissionCode"
              role="tablist"
              aria-label="可见范围"
            >
              <button
                type="button"
                class="bi-visibility-segment-option"
                :class="{ active: editForm.permissionCode === 'private' }"
                :aria-pressed="editForm.permissionCode === 'private'"
                :disabled="!canEditVisibility || isSharedKnowledgeBaseReadonly"
                @click="updateEditVisibility('private')"
              >
                个人使用
              </button>
              <button
                type="button"
                class="bi-visibility-segment-option"
                :class="{ active: editForm.permissionCode === 'public' }"
                :aria-pressed="editForm.permissionCode === 'public'"
                :disabled="!canEditVisibility || isSharedKnowledgeBaseReadonly"
                @click="updateEditVisibility('public')"
              >
                公开共享
              </button>
            </div>
          </div>
          <div v-if="!canEditVisibility" class="kb-form-help">
            {{ isSharedKnowledgeBaseReadonly ? KB_SHARED_READONLY_TIP : KB_VISIBILITY_EDIT_ADMIN_ONLY_TIP }}
          </div>
        </a-form-item>
        <a-form-item
          v-if="canEditVisibility && editForm.permissionCode === 'public'"
          required
          class="kb-permission-groups-form-item"
          label="可访问用户组"
        >
          <a-select
            v-model:value="editForm.permissionGroupIds"
            mode="multiple"
            :options="permissionGroupOptions"
            :loading="permissionGroupsLoading"
            :disabled="permissionGroupsLoading || editingKbLoading || isSharedKnowledgeBaseReadonly"
            :virtual="false"
            popupClassName="permission-groups-dropdown"
            max-tag-count="responsive"
            placeholder="请选择用户组"
            style="width: 100%;"
            @change="handleEditPermissionGroupsChange"
          />
          <div class="kb-form-help">公开后仅这些用户组可访问该知识库</div>
        </a-form-item>
        <a-form-item label="知识库描述" required>
          <a-textarea
            v-model:value="editForm.description"
            placeholder="请输入知识库描述"
            :auto-size="{ minRows: 3, maxRows: 6 }"
            show-count
            :maxlength="200"
            :disabled="isSharedKnowledgeBaseReadonly || editingKbLoading"
          />
        </a-form-item>
      </a-form>
      <template #footer>
        <div class="edit-kb-footer">
          <a-button class="custom-btn cancel-btn" @click="onEditModalCancel" :disabled="editingKbLoading">取消</a-button>
          <a-button class="custom-btn confirm-btn" @click="handleUpdateKnowledgeBaseInfo" :loading="editingKbLoading" :disabled="isSharedKnowledgeBaseReadonly">保存</a-button>
        </div>
      </template>
    </a-modal>

    <!-- 文档切片查看模态框（封装组件） -->
    <SlicesModal
      v-model:open="slicesModalVisible"
      :viewingDocName="viewingDocName"
      :selectedKnowledgeBase="selectedKnowledgeBase"
      :loadingIndicator="loadingIndicator"
    />

    <!-- 检索配置模态框 -->
    <a-modal
      v-model:open="retrievalConfigModalVisible"
      centered
      title="检索参数配置"
      width="430px"
      :maskClosable="!retrievalConfigSaving"
      :keyboard="!retrievalConfigSaving"
      :closable="!retrievalConfigSaving"
      :footer="null"
      class="retrieval-config-modal"
    >
      <div class="retrieval-config-modal-body">
        <p class="retrieval-config-modal-desc">配置知识库检索时的参数，影响对话中增强检索的召回数量和精度</p>
        <a-form layout="vertical" style="margin-top: 16px;">
          <a-form-item label="Top K（召回数量）">
            <a-input-number
              v-model:value="retrievalConfig.top_k"
              :min="1"
              :max="20"
              :precision="0"
              placeholder="默认 3"
              style="width: 100%;"
            />
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">默认值：3  范围：1~20</div>
          </a-form-item>
          <a-form-item label="Score Threshold（相关性阈值）">
            <a-input-number
              v-model:value="retrievalConfig.score_threshold"
              :min="0"
              :max="1"
              :step="0.01"
              :precision="2"
              placeholder="默认 0.1"
              style="width: 100%;"
            />
            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">默认值：0.1  范围：0~1  值越高结果越精确</div>
          </a-form-item>
        </a-form>
        <div class="form-actions">
          <button class="custom-btn cancel-btn" @click="retrievalConfigModalVisible = false" :disabled="retrievalConfigSaving">取消</button>
          <button class="custom-btn confirm-btn" @click="saveRetrievalConfig" :disabled="retrievalConfigSaving">保存</button>
        </div>
      </div>
    </a-modal>

    <!-- 知识图谱全屏模态框 -->
    <a-modal
      v-model:open="kgModalVisible"
      :title="`知识图谱 - ${kgModalKb?.name}`"
      width="100%"
      wrapClassName="full-screen-modal"
      :footer="null"
      :destroyOnClose="true"
    >
      <div style="height: 100%;">
        <KnowledgeGraph v-if="kgModalVisible && kgModalKb" :knowledgeBaseName="kgModalKb.name" />
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import {computed, h, nextTick, onActivated, onDeactivated, onMounted, onUnmounted, ref, watch} from 'vue'
import '@/assets/styles/knowledge-base.css'
import '@/assets/styles/user-group-select.css'
import KBHeader from '@/components/knowledge-base/KBHeader.vue'
import KBList from '@/components/knowledge-base/KBList.vue'
import KBDetail from '@/components/knowledge-base/KBDetail.vue'
import SlicesModal from '@/components/knowledge-base/SlicesModal.vue'
import KnowledgeGraph from '@/components/knowledge-base/KnowledgeGraph.vue'
import KnowledgeWorkspace from '@/components/knowledge-base/KnowledgeWorkspace.vue'
import type {UploadFile} from 'ant-design-vue'
import {Modal} from 'ant-design-vue'
import NotificationService from '@/utils/NotificationService'
import {
  createKnowledgeBase,
  deleteKnowledgeBase as deleteKnowledgeBaseApi,
  deleteKnowledgeBaseDocs,
  downloadKnowledgeBaseDoc,
  listKnowledgeBaseFiles,
  listKnowledgeBases,
  updateKnowledgeBaseInfo,
  uploadKnowledgeBaseDocs,
  autoNodesAndRelationships,
  listAllKnowledgeGraphTask,
  UploadDocsError,
  type KnowledgeBasePermissionCode,
  type KnowledgeBaseFileVM,
  type KnowledgeGraphTaskStatus,
  type RemoteUploadDocsResponse
} from '@/services/knowledgeBase'
import { LoadingOutlined, InfoCircleOutlined, DeploymentUnitOutlined, CloseOutlined, ShareAltOutlined, DeleteOutlined, CloudUploadOutlined, FileOutlined, CloseCircleOutlined } from '@ant-design/icons-vue'
import { eventBus } from '@/utils/EventBus'
import { useKnowledgeBaseStore } from '@/stores/knowledgeBaseStore';
import StorageService from '@/utils/StorageService';
import { useChatStore } from '@/stores/chat-store';
import { updateAiAgent, listAiAgents } from '@/services/aiAgent';
import { listAiEntityAssignedGroups, listAiUserGroups, updateAiPermission, type UserGroupItem } from '@/services/aiPermission';
import {
  canManageKnowledgeBase,
  KB_DELETE_DOC_ADMIN_ONLY_TIP,
  KB_DELETE_KB_ADMIN_ONLY_TIP,
  KB_SHARED_READONLY_TIP,
  KB_UPLOAD_ADMIN_ONLY_TIP,
  KB_VISIBILITY_ADMIN_ONLY_TIP,
  KB_VISIBILITY_EDIT_ADMIN_ONLY_TIP,
} from '@/composables/useKnowledgeBaseAccess'
import {
  loadKbDocs,
  invalidateKbDocsCache,
  invalidateKbListCache,
  isKbDocsCacheFresh,
  isKbListCacheFresh,
  peekKbDocsCache,
  peekKbListCache,
  writeKbDocsCache,
  writeKbListCache,
} from '@/composables/useKnowledgeBaseCache'
import { getFileUploadMaxSize, getKbEmbeddingModels, getKbVectorStoreTypes, getKbUploadDefaultChunkSize } from '@/utils/RuntimeConfig'
import { getFileIconSrc } from '@/utils/fileIcon'
import { listAiSystemConfig, updateAiSystemConfig } from '@/services/aiSystemConfig'

const props = withDefaults(defineProps<{ layout?: 'settings' | 'workspace' }>(), { layout: 'settings' })
const emit = defineEmits<{ back: [] }>()

// 类型定义
interface Document {
  id: string
  name: string
  size: number
  uploadedAt: Date
  ext?: string
  version?: number
  loader?: string
  docsCount?: number
  splitter?: string
  inFolder?: boolean
  inDb?: boolean
  mtime?: number
  customDocs?: boolean
  no?: number
  graphStatus?: {
    completed: boolean
    errorMsg: string
  }
}

interface KnowledgeBase {
  id: string
  kbUuid?: string
  name: string
  description?: string
  permissionCode?: 'private' | 'public'
  permissionGroupIds?: string[]
  documentCount: number
  updatedAt: Date
  vsType?: string
  embedModel?: string
  includeKg?: boolean
  documents: Document[]
}

interface CreateForm {
  name: string
  description: string
  permissionCode: 'private' | 'public'
  permissionGroupIds: string[]
  vsType: string | null
  embedModel: string | null
  enableGraphRag: boolean
  kgType: string
  allowedNodes: string[]
  allowedRelationships: string[]
  exampleText: string
}

interface ExtractedEntity {
  id: string
  name: string
  type: string
  properties: string[]
}

interface ExtractedRelationship {
  id: string
  head: string
  head_type: string
  edge: string
  tail: string
  tail_type: string
}

interface PendingKnowledgeGraphDoc {
  submittedAt: number
  seenInTaskList: boolean
}

const SELECTED_KB_NAME_STORAGE_KEY = 'selected_knowledge_base_name'
const KB_PERMISSION_FILTER_STORAGE_KEY = 'selected_knowledge_base_permission_filter'
const readStoredKnowledgeBasePermissionFilter = (): KnowledgeBasePermissionCode => {
  try {
    const raw = localStorage.getItem(KB_PERMISSION_FILTER_STORAGE_KEY)
    return raw === 'private' ? 'private' : 'public'
  } catch (_) {
    return 'public'
  }
}

const persistKnowledgeBaseViewContext = (filter: KnowledgeBasePermissionCode, kbName?: string | null) => {
  try {
    localStorage.setItem(KB_PERMISSION_FILTER_STORAGE_KEY, filter)
    if (kbName && kbName.trim()) {
      localStorage.setItem(SELECTED_KB_NAME_STORAGE_KEY, kbName)
    } else {
      localStorage.removeItem(SELECTED_KB_NAME_STORAGE_KEY)
    }
  } catch (_) {}
}

// 响应式数据
const searchKeyword = ref<string>('')
const kbPermissionFilter = ref<KnowledgeBasePermissionCode>(readStoredKnowledgeBasePermissionFilter())
const pendingPreferredKnowledgeBaseName = ref<string | null>(null)
const isExtracting = ref<boolean>(false)
const selectedKnowledgeBase = ref<KnowledgeBase | null>(null)
const createModalVisible = ref<boolean>(false)
const uploadModalVisible = ref<boolean>(false)
const uploading = ref<boolean>(false)
const uploadFileList = ref<UploadFile[]>([])
const uploadFileFailedReasonMap = ref<Record<string, string>>({})
const uploadFileInputRef = ref<HTMLInputElement | null>(null)
const isUploadDragging = ref<boolean>(false)
const creatingKb = ref<boolean>(false)
const kgTasks = ref<KnowledgeGraphTaskStatus[]>([])
const kgPendingDocsByKnowledgeBase = ref<Record<string, Record<string, PendingKnowledgeGraphDoc>>>({})
const kgTaskStatusSnapshotByKnowledgeBase = ref<Record<string, Record<string, string>>>({})
let kgTasksInterval: any = null
let isDisposed = false
// 是否已完成过一次列表加载：用于 KeepAlive 激活时判断是否需要静默刷新
let hasLoadedKnowledgeBasesOnce = false
let knowledgeBaseListRequestId = 0
let selectedFilesRequestId = 0
let kgTasksRequestId = 0
let kgPollingGeneration = 0
const currentKgPendingDocNameMap = computed(() => {
  if (!selectedKnowledgeBase.value) return {}
  return Object.fromEntries(
    Object.keys(kgPendingDocsByKnowledgeBase.value[selectedKnowledgeBase.value.name] || {}).map(name => [name, true])
  )
})
const kgPendingDocGraceMs = 60000
const buildKgTaskKey = (task: KnowledgeGraphTaskStatus) => task.task_id || task.file_name
const isKgTaskActive = (status: string) => status === 'running' || status === 'pending'

const activeKgTaskKbNames = computed(() => {
  const names = new Set<string>()
  for (const [kbName, docs] of Object.entries(kgPendingDocsByKnowledgeBase.value)) {
    if (Object.keys(docs).length > 0) {
      names.add(kbName)
    }
  }
  for (const [kbName, statuses] of Object.entries(kgTaskStatusSnapshotByKnowledgeBase.value)) {
    if (Object.values(statuses).some(isKgTaskActive)) {
      names.add(kbName)
    }
  }
  return names
})


const applyFilesToSelectedKnowledgeBase = (files: KnowledgeBaseFileVM[]) => {
  if (!selectedKnowledgeBase.value) return
  selectedKnowledgeBase.value.documents = files.map(f => ({
    id: f.id,
    name: f.name,
    size: f.size,
    uploadedAt: f.uploadedAt,
    ext: f.ext,
    version: f.version,
    loader: f.loader,
    docsCount: f.docsCount,
    splitter: f.splitter,
    inFolder: f.inFolder,
    inDb: f.inDb,
    mtime: f.mtime,
    customDocs: f.customDocs,
    no: f.no,
    graphStatus: f.graphStatus
  }))
  selectedKnowledgeBase.value.documentCount = selectedKnowledgeBase.value.documents.length
}

const syncSelectedKnowledgeBaseDocumentCount = () => {
  if (!selectedKnowledgeBase.value) return
  const nextCount = selectedKnowledgeBase.value.documents.length
  selectedKnowledgeBase.value.documentCount = nextCount
  const kbIndex = knowledgeBases.value.findIndex(kb => kb.id === selectedKnowledgeBase.value?.id)
  if (kbIndex > -1) {
    knowledgeBases.value[kbIndex].documentCount = nextCount
  }
}

const wait = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const reconcileSelectedKnowledgeBaseFilesAfterDelete = async (deletedFileNames: string[]) => {
  if (!selectedKnowledgeBase.value || deletedFileNames.length === 0) return
  const kbName = selectedKnowledgeBase.value.name
  const deletedNameSet = new Set(deletedFileNames)
  const retryDelays = [150, 400, 900]
  let latestFiles: KnowledgeBaseFileVM[] | null = null

  for (const delay of retryDelays) {
    await wait(delay)
    const files = await listKnowledgeBaseFiles(kbName)
    latestFiles = files
    const hasDeletedFiles = files.some(file => deletedNameSet.has(file.name))
    if (!hasDeletedFiles) {
      writeKbDocsCache(kbName, files)
      applyFilesToSelectedKnowledgeBase(files)
      syncSelectedKnowledgeBaseDocumentCount()
      return
    }
  }

  if (latestFiles) {
    // 服务端仍未同步删除结果：以本地过滤结果为准，并让缓存失效以免后续读到旧数据
    invalidateKbDocsCache(kbName)
    applyFilesToSelectedKnowledgeBase(
      latestFiles.filter(file => !deletedNameSet.has(file.name))
    )
    syncSelectedKnowledgeBaseDocumentCount()
  }
}

const createDefaultUploadOptions = () => ({
  chunkSize: getKbUploadDefaultChunkSize(),
  chunkOverlap: 50,
  zhTitleEnhance: false,
  classification: null as 'public' | 'internal' | null
})

const uploadOptions = ref<{ chunkSize: number; chunkOverlap: number; zhTitleEnhance: boolean; classification: 'public' | 'internal' | null }>(createDefaultUploadOptions())

// 编辑知识库信息相关
const editModalVisible = ref<boolean>(false)
const editingKb = ref<KnowledgeBase | null>(null)
const editingKbLoading = ref<boolean>(false)
const editingOriginalPermissionGroupIds = ref<string[]>([])
const editingDraftPermissionGroupIds = ref<string[]>([])
const editForm = ref<{ description: string; name: string; permissionCode: 'private' | 'public'; permissionGroupIds: string[] }>({
  description: '',
  name: '',
  permissionCode: 'private',
  permissionGroupIds: []
})
const getCurrentUsername = () => {
  try {
    const raw = localStorage.getItem('user-profile')
    if (!raw) return ''
    const profile = JSON.parse(raw)
    return String(profile?.username || '').trim()
  } catch (_) {
    return ''
  }
}
const isCurrentUserAdmin = computed(() => getCurrentUsername().toLowerCase() === 'admin')
const canEditVisibility = computed(() => isCurrentUserAdmin.value)
const isSharedKnowledgeBaseReadonly = computed(() =>
  !isCurrentUserAdmin.value && editingKb.value?.permissionCode === 'public'
)

// 检索参数配置
const retrievalConfigModalVisible = ref(false)
const retrievalConfig = ref({
  top_k: 3 as number | null,
  score_threshold: 0.1 as number | null
})
const retrievalConfigSaving = ref(false)

function showRetrievalConfigModal() {
  loadRetrievalConfig()
  retrievalConfigModalVisible.value = true
}

async function loadRetrievalConfig() {
  try {
    const config = await listAiSystemConfig()
    retrievalConfig.value.top_k = config.top_k
    retrievalConfig.value.score_threshold = config.score_threshold
  } catch (err) {
    console.error('加载检索配置失败:', err)
  }
}

async function saveRetrievalConfig() {
  // 入口已按 admin 隐藏，这里再兜一层，避免非 admin 直接调用
  if (!isCurrentUserAdmin.value) {
    NotificationService.info('仅 admin 可修改检索配置')
    retrievalConfigModalVisible.value = false
    return
  }
  try {
    retrievalConfigSaving.value = true
    const payload: Record<string, string> = {}
    if (retrievalConfig.value.top_k != null) {
      payload.top_k = String(retrievalConfig.value.top_k)
    }
    if (retrievalConfig.value.score_threshold != null) {
      payload.score_threshold = String(retrievalConfig.value.score_threshold)
    }
    await updateAiSystemConfig(payload)
    NotificationService.success('检索配置已保存')
    retrievalConfigModalVisible.value = false
    // 通知其他组件检索配置已更新
    eventBus.emit('retrieval-config-updated')
  } catch (err) {
    console.error('保存检索配置失败:', err)
    NotificationService.error('保存检索配置失败')
  } finally {
    retrievalConfigSaving.value = false
  }
}

const permissionGroupsLoading = ref(false)
const permissionGroupsLoaded = ref(false)
const availablePermissionGroups = ref<UserGroupItem[]>([])
const KNOWLEDGE_BASE_ENTITY_TYPE = 4
const permissionGroupOptions = computed(() =>
  availablePermissionGroups.value.map((group) => ({
    label: group.name,
    value: group.uuid
  }))
)

// 实体和关系数据
const extractedEntities = ref<ExtractedEntity[]>([])
const extractedRelationships = ref<ExtractedRelationship[]>([])

// 表单数据
const createForm = ref<CreateForm>({
  name: '',
  description: '',
  permissionCode: 'private',
  permissionGroupIds: [],
  vsType: null,
  embedModel: null,
  enableGraphRag: false,
  kgType: 'neo4j',
  allowedNodes: [],
  allowedRelationships: [],
  exampleText: ''
})

const currentStep = ref<string>('basic')


const embeddingModels = ref<string[]>(getKbEmbeddingModels())
const vectorStoreTypes = ref<string[]>(getKbVectorStoreTypes())

// 知识库数据
const knowledgeBases = ref<KnowledgeBase[]>([])
const kbListLoading = ref<boolean>(false)
// 已有缓存、正在后台静默刷新时为 true：此时保留卡片，只显示顶部进度条，不再退回骨架屏
const kbListRefreshing = ref<boolean>(false)
const kbListError = ref('')
// 首屏骨架屏只在「完全没有缓存」时出现
const kbListSkeletonVisible = computed(() => kbListLoading.value && !kbListRefreshing.value)

// 文档切片展示相关状态（移至 SlicesModal 自管理）
const slicesModalVisible = ref<boolean>(false)
const viewingDocName = ref<string>('')
const kgModalVisible = ref<boolean>(false)
const kgModalKb = ref<KnowledgeBase | null>(null)

const handleOpenKgModal = (kb: KnowledgeBase) => {
  kgModalKb.value = kb
  kgModalVisible.value = true
}
const docsLoading = ref<boolean>(false)
const docsError = ref('')

// 自定义加载指示器（Spin 上方图标）
const loadingIndicator = h(LoadingOutlined, { style: { fontSize: '28px' }, spin: true })

// 切片编辑与保存逻辑已封装到 SlicesModal 组件

// 文档搜索
const documentSearchKeyword = ref<string>('')

const refreshKnowledgeBase = async () => {
  // 手动刷新：忽略缓存新鲜度，重新拉取（有缓存时仍保留卡片 + 顶部进度条）
  await loadKnowledgeBases(undefined, { force: true })
  // 通知其他组件知识库列表已更新
  eventBus.emit('knowledge-base-list-updated')
}

const showCreateModal = () => {
  // 可见性默认沿用当前所在的知识库分类：共享库页签打开时默认"共享"，个人知识页签打开时默认"个人"
  // （非 admin 时 updateCreateVisibility 内部会直接返回，仍保持 private）
  updateCreateVisibility(kbPermissionFilter.value)
  createModalVisible.value = true
  currentStep.value = 'basic'
}

const resetCreateForm = () => {
  createForm.value = {
    name: '',
    description: '',
    permissionCode: 'private',
    permissionGroupIds: [],
    vsType: null,
    embedModel: null,
    enableGraphRag: false,
    kgType: 'neo4j',
    allowedNodes: [],
    allowedRelationships: [],
    exampleText: ''
  }
  currentStep.value = 'basic'
}

const ensurePermissionGroupsLoaded = async () => {
  if (!canEditVisibility.value || permissionGroupsLoaded.value || permissionGroupsLoading.value) return
  permissionGroupsLoading.value = true
  try {
    availablePermissionGroups.value = await listAiUserGroups()
    permissionGroupsLoaded.value = true
  } catch {
    availablePermissionGroups.value = []
  } finally {
    permissionGroupsLoading.value = false
  }
}

const updateCreateVisibility = (visibility: 'private' | 'public') => {
  if (!canEditVisibility.value) return
  createForm.value.permissionCode = visibility
  if (visibility !== 'public') {
    createForm.value.permissionGroupIds = []
  } else {
    ensurePermissionGroupsLoaded()
  }
}

const updateEditVisibility = (visibility: 'private' | 'public') => {
  if (!canEditVisibility.value) return
  if (editForm.value.permissionCode === 'public') {
    editingDraftPermissionGroupIds.value = normalizePermissionGroupSelectionValues(editForm.value.permissionGroupIds)
  }
  editForm.value.permissionCode = visibility
  if (visibility !== 'public') {
    editForm.value.permissionGroupIds = []
  } else {
    editForm.value.permissionGroupIds = normalizePermissionGroupSelectionValues(editingDraftPermissionGroupIds.value)
    ensurePermissionGroupsLoaded()
  }
}

const normalizePermissionGroupIds = (source: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(source) ? source : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  )

const normalizePermissionGroupSelectionValues = (source: unknown): string[] =>
  normalizePermissionGroupIds(source).map((groupValue) => {
    const matchedGroup = availablePermissionGroups.value.find((group) =>
      group.id === groupValue || group.uuid === groupValue
    )
    return matchedGroup?.uuid || groupValue
  })

const mapPermissionGroupSelectionToUuids = (source: unknown): string[] =>
  Array.from(
    new Set(
      normalizePermissionGroupIds(source).map((groupValue) => {
        const matchedGroup = availablePermissionGroups.value.find((group) =>
          group.id === groupValue || group.uuid === groupValue
        )
        return matchedGroup?.uuid || groupValue
      })
    )
  )

const areSamePermissionGroups = (left: unknown, right: unknown): boolean => {
  const normalizedLeft = normalizePermissionGroupIds(left).slice().sort()
  const normalizedRight = normalizePermissionGroupIds(right).slice().sort()
  return normalizedLeft.length === normalizedRight.length
    && normalizedLeft.every((groupId, index) => groupId === normalizedRight[index])
}

const handleCreatePermissionGroupsChange = (values: string[]) => {
  createForm.value.permissionGroupIds = normalizePermissionGroupSelectionValues(values)
}

const handleEditPermissionGroupsChange = (values: string[]) => {
  editForm.value.permissionGroupIds = normalizePermissionGroupSelectionValues(values)
  editingDraftPermissionGroupIds.value = editForm.value.permissionGroupIds.slice()
}

const handleCreateKnowledgeBase = () => {
  if (creatingKb.value) return
  const knowledgeBaseName = createForm.value.name.trim()
  const description = createForm.value.description.trim()
  if (!createForm.value.name.trim()) {
    currentStep.value = 'basic'
    NotificationService.error('请输入知识库名称')
    return
  }
  if (knowledgeBaseName.length > 50) {
    currentStep.value = 'basic'
    NotificationService.error('知识库名称不能超过50个字符')
    return
  }
  if (!description) {
    currentStep.value = 'basic'
    NotificationService.error('请输入知识库描述')
    return
  }
  if (description.length > 200) {
    currentStep.value = 'basic'
    NotificationService.error('知识库描述不能超过200个字符')
    return
  }

  if (canEditVisibility.value && createForm.value.permissionCode === 'public' && createForm.value.permissionGroupIds.length === 0) {
    currentStep.value = 'basic'
    NotificationService.error('共享知识库至少需要选择一个用户组')
    return
  }

  if (!createForm.value.vsType) {
    currentStep.value = 'model'
    NotificationService.error('请选择向量库类型')
    return
  }

  if (!createForm.value.embedModel) {
    currentStep.value = 'model'
    NotificationService.error('请选择 Embedding 模型')
    return
  }

  if (createForm.value.enableGraphRag) {
    if (!createForm.value.kgType) {
      currentStep.value = 'graph'
      NotificationService.error('请选择图数据库类型')
      return
    }
    if (!createForm.value.allowedNodes || createForm.value.allowedNodes.length === 0) {
      currentStep.value = 'graph'
      NotificationService.error('请输入至少一个实体类型')
      return
    }
    if (!createForm.value.allowedRelationships || createForm.value.allowedRelationships.length === 0) {
      currentStep.value = 'graph'
      NotificationService.error('请输入至少一个关系类型')
      return
    }
  }


  const payload = {
    knowledge_base_name: knowledgeBaseName,
    vector_store_type: String(createForm.value.vsType),
    kb_info: createForm.value.description.trim(),
    embed_model: String(createForm.value.embedModel),
    permission_code: canEditVisibility.value ? createForm.value.permissionCode : 'private',
    permission_group_ids: canEditVisibility.value && createForm.value.permissionCode === 'public'
      ? mapPermissionGroupSelectionToUuids(createForm.value.permissionGroupIds)
      : [],
    permissionGroupIds: canEditVisibility.value && createForm.value.permissionCode === 'public'
      ? mapPermissionGroupSelectionToUuids(createForm.value.permissionGroupIds)
      : [],
    enable_graph_rag: createForm.value.enableGraphRag,
    kb_type: "default",
    kg_type: createForm.value.kgType,
    allowed_nodes: createForm.value.allowedNodes,
    allowed_relationships: createForm.value.allowedRelationships,
    node_properties: false
  }

  creatingKb.value = true
  createKnowledgeBase(payload)
      .then(async (result) => {
        const createdPermissionCode: KnowledgeBasePermissionCode =
          canEditVisibility.value && createForm.value.permissionCode === 'public' ? 'public' : 'private'
        const permissionGroupUuids = canEditVisibility.value && createForm.value.permissionCode === 'public'
          ? mapPermissionGroupSelectionToUuids(createForm.value.permissionGroupIds)
          : []
        const createdKbUuid = typeof result?.uuid === 'string' ? result.uuid.trim() : ''
        if (createdKbUuid && permissionGroupUuids.length > 0) {
          for (const groupUuid of permissionGroupUuids) {
            await updateAiPermission({
              group_id: groupUuid,
              list: [
                {
                  entity_id: createdKbUuid,
                  entity_type: KNOWLEDGE_BASE_ENTITY_TYPE,
                  permission: 1
                }
              ]
            })
          }
          await listAiEntityAssignedGroups(createdKbUuid, KNOWLEDGE_BASE_ENTITY_TYPE)
        }
        NotificationService.success('知识库创建成功')
        createModalVisible.value = false
        resetCreateForm()
        searchKeyword.value = ''
        pendingPreferredKnowledgeBaseName.value = knowledgeBaseName
        persistKnowledgeBaseViewContext(createdPermissionCode, knowledgeBaseName)
        // 新建后缓存已失效，重新拉取并回写缓存
        invalidateKbListCache()
        if (kbPermissionFilter.value !== createdPermissionCode) {
          kbPermissionFilter.value = createdPermissionCode
        } else {
          await loadKnowledgeBases(knowledgeBaseName, { force: true })
        }
        // 通知其他组件知识库列表已更新
        eventBus.emit('knowledge-base-list-updated')
      })
      .catch((error) => {
        console.error('创建知识库失败:', error)
        NotificationService.error(typeof error?.message === 'string' ? error.message : '创建知识库失败，请重试')
      })
      .finally(() => {
        creatingKb.value = false
      })
}

const onCreateModalCancel = () => {
  if (creatingKb.value) return
  createModalVisible.value = false
  resetCreateForm()
}

const closeKnowledgeWorkspace = () => {
  ++selectedFilesRequestId
  stopKgTasksPolling()
}
const selectKnowledgeBase = async (kb: KnowledgeBase) => {
  if (isDisposed) return
  selectedKnowledgeBase.value = kb
  documentSearchKeyword.value = ''
  persistKnowledgeBaseViewContext(kbPermissionFilter.value, kb.name)
  kgTasks.value = []
  await loadSelectedKnowledgeBaseFiles()
}

const editKnowledgeBase = async (kb: KnowledgeBase) => {
  editingKb.value = kb
  editForm.value.description = kb.description || ''
  editForm.value.name = kb.name
  editForm.value.permissionCode = kb.permissionCode === 'public' ? 'public' : 'private'
  editForm.value.permissionGroupIds = normalizePermissionGroupSelectionValues(kb.permissionGroupIds)
  editingDraftPermissionGroupIds.value = editForm.value.permissionGroupIds.slice()
  editingOriginalPermissionGroupIds.value = editForm.value.permissionGroupIds.slice()
  editModalVisible.value = true
  if (!canEditVisibility.value) {
    return
  }

  editingKbLoading.value = true
  try {
    const tasks: Promise<unknown>[] = []
    if (editForm.value.permissionCode === 'public') {
      tasks.push(ensurePermissionGroupsLoaded())
    }

    const entityId = kb.kbUuid?.trim()
    if (entityId) {
      tasks.push(
        listAiEntityAssignedGroups(entityId, KNOWLEDGE_BASE_ENTITY_TYPE).then((assignedGroups) => {
          editForm.value.permissionGroupIds = normalizePermissionGroupSelectionValues(assignedGroups)
          editingDraftPermissionGroupIds.value = editForm.value.permissionGroupIds.slice()
          editingOriginalPermissionGroupIds.value = editForm.value.permissionGroupIds.slice()
        })
      )
    }

    await Promise.all(tasks)
  } catch (error) {
    console.error('加载知识库权限分组失败:', error)
    NotificationService.error(typeof (error as any)?.message === 'string' ? (error as any).message : '加载可访问用户组失败')
  } finally {
    editingKbLoading.value = false
  }
}

const deleteKnowledgeBase = (kb: KnowledgeBase) => {
  if (!canManageKnowledgeBase(kb, isCurrentUserAdmin.value)) {
    NotificationService.info(KB_DELETE_KB_ADMIN_ONLY_TIP)
    return
  }
  Modal.confirm({
    title: '确认删除知识库',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `确定要删除“${kb.name}”吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: async () => {
      try {
        await deleteKnowledgeBaseApi(kb.name, kb.includeKg)
        delete kgPendingDocsByKnowledgeBase.value[kb.name]
        const index = knowledgeBases.value.findIndex(item => item.id === kb.id)
        if (index > -1) {
          knowledgeBases.value.splice(index, 1)
          // 同步缓存：删除后当前分类的列表仍然是最新的，切换分类回来时不会退回骨架屏
          invalidateKbDocsCache(kb.name)
          writeKbListCache(kbPermissionFilter.value, [...knowledgeBases.value])
          if (selectedKnowledgeBase.value?.id === kb.id) {
            selectedKnowledgeBase.value = knowledgeBases.value[0] || null
            if (selectedKnowledgeBase.value) {
              persistKnowledgeBaseViewContext(kbPermissionFilter.value, selectedKnowledgeBase.value.name)
              kgTasks.value = []
              await loadSelectedKnowledgeBaseFiles()
            } else {
              persistKnowledgeBaseViewContext(kbPermissionFilter.value, null)
              kgTasks.value = []
              stopKgTasksPolling()
            }
          }
        }
        NotificationService.success('知识库已删除')
        // 通知其他组件知识库列表已更新
        eventBus.emit('knowledge-base-list-updated')

        // 同步到所有智能体：如果引用了被删除的知识库，则关闭知识库功能并清空选择
        try {
          const deletedKbName = kb.name
          const allAgents = StorageService.getAgents()
          const updatedAgents = allAgents.map((agent: any) => {
            const k = agent?.config?.knowledge
            if (k?.enabled && k?.selectedKnowledge === deletedKbName) {
              return {
                ...agent,
                config: {
                  ...agent.config,
                  knowledge: {
                    ...k,
                    enabled: false,
                    selectedKnowledge: ''
                  }
                }
              }
            }
            return agent
          })
          StorageService.setAgents(updatedAgents)
          // 广播智能体列表更新事件，通知其他组件刷新UI
          try {
            window.dispatchEvent(new CustomEvent('agents-updated', { detail: { agents: updatedAgents } }))
          } catch (e) {
            console.warn('分发 agents-updated 事件失败（非致命）:', e)
          }

          const changedAgents = updatedAgents.filter((a: any, idx: number) => {
            const prev = allAgents[idx]
            const pk = prev?.config?.knowledge || {}
            const nk = a?.config?.knowledge || {}
            return pk.enabled !== nk.enabled || pk.selectedKnowledge !== nk.selectedKnowledge
          })
          try {
            await Promise.all(changedAgents.map((agent: any) => {
              const agentType = agent.agent_type || agent.config?.basic?.type || 'assistant'
              const isDeepAgent = agentType === 'deepagent'

              return updateAiAgent({
              uuid: agent.uuid,
              id: agent.id,
              name: agent.name,
              description: agent.description,
              themeColor: agent.themeColor,
              agent_type: agentType,
              ...(isDeepAgent ? {
                visibility: agent.visibility || agent.config?.basic?.visibility || 'private',
                skills: Array.isArray(agent.skills) ? agent.skills : (Array.isArray(agent.config?.skills) ? agent.config.skills : [])
              } : {}),
              config: agent.config
            })
            }))
          } catch (_) {}
          try {
            const res = await listAiAgents()
            const arr: any[] = Array.isArray(res?.data) ? res.data : []
            const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim()
            const mapped = arr.map((item: any) => {
              const m = item.config?.model || {}
              const basicConfig = {
                ...(item.config?.basic || {}),
                type: item.config?.basic?.type || item.agent_type || 'assistant',
                visibility: item.config?.basic?.visibility || item.visibility || 'private'
              }
              const skills = Array.isArray(item.skills) ? item.skills : (Array.isArray(item.config?.skills) ? item.config.skills : [])
              const normalizedModel = {
                service: m.service,
                name: m.name,
                temperature: typeof m.temperature === 'number' ? m.temperature : 0.7,
                top_p: typeof m.topP === 'number' ? m.topP : (typeof m.top_p === 'number' ? m.top_p : 1.0),
                presence_penalty: typeof m.presencePenalty === 'number' ? m.presencePenalty : (typeof m.presence_penalty === 'number' ? m.presence_penalty : 0),
                frequency_penalty: typeof m.frequencyPenalty === 'number' ? m.frequencyPenalty : (typeof m.frequency_penalty === 'number' ? m.frequency_penalty : 0),
                apiKey: m.apiKey,
                apiUrl: sanitizeUrl(m.apiUrl)
              }
              return {
                id: item.id,
                name: item.name,
                description: item.description,
                themeColor: item.themeColor,
                uuid: item.uuid,
                agent_type: item.agent_type || basicConfig.type,
                visibility: item.visibility || basicConfig.visibility,
                skills,
                config: {
                  basic: basicConfig,
                  prompt: { ...(item.config?.prompt || {}) },
                  model: normalizedModel,
                  knowledge: { ...(item.config?.knowledge || {}) },
                  mcp: { ...(item.config?.mcp || { enabledServerIdentifiers: [] }) },
                  skills,
                  phrases: Array.isArray(item.config?.phrases) ? item.config.phrases : []
                }
              } as any
            })
            StorageService.setAgents(mapped)
            window.dispatchEvent(new Event('agents-updated'))
          } catch (_) {}

          // 同步当前活跃智能体配置
          const activeAgent = StorageService.getActiveAgent()
          if (activeAgent?.knowledge?.enabled && activeAgent?.knowledge?.selectedKnowledge === deletedKbName) {
            const updatedActiveAgent = {
              ...activeAgent,
              knowledge: {
                ...activeAgent.knowledge,
                enabled: false,
                selectedKnowledge: ''
              }
            }
            StorageService.setActiveAgent(updatedActiveAgent)
            // 广播活跃智能体更新事件
            window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: updatedActiveAgent } }))
            // 清理当前聊天缓存（对话历史、临时检索上下文）
            try {
              const chatStore = useChatStore();
              chatStore.clearChat();
            } catch (clearErr) {
              console.warn('清理聊天缓存失败（非致命）:', clearErr)
            }
          }
        } catch (syncErr) {
          console.error('同步智能体知识库状态失败:', syncErr)
        }
      } catch (error: any) {
        console.error('删除知识库失败:', error)
        NotificationService.error(typeof error?.message === 'string' ? error.message : '删除失败，请重试')
      }
    }
  })
}

const showUploadModal = () => {
  // 如果没有任何知识库，提示先创建知识库
  if (knowledgeBases.value.length === 0) {
    NotificationService.info('请先创建知识库，再上传文档')
    return
  }
  // 如果未选择知识库，提示先选择
  if (!selectedKnowledgeBase.value) {
    NotificationService.info('请在左侧选择一个知识库')
    return
  }
  // 共享知识库仅 admin 可上传文档
  if (!canManageKnowledgeBase(selectedKnowledgeBase.value, isCurrentUserAdmin.value)) {
    NotificationService.info(KB_UPLOAD_ADMIN_ONLY_TIP)
    return
  }
  uploadModalVisible.value = true
}

const resetUploadForm = () => {
  uploadFileList.value = []
  uploadFileFailedReasonMap.value = {}
  isUploadDragging.value = false
  if (uploadFileInputRef.value) {
    uploadFileInputRef.value.value = ''
  }
  uploadOptions.value = createDefaultUploadOptions()
}

const getUploadFileKey = (file: UploadFile) => String(file.uid || file.name || '')
const getUploadFileFailedReason = (file: UploadFile) => uploadFileFailedReasonMap.value[getUploadFileKey(file)] || ''

const removeUploadFile = (target: UploadFile) => {
  const targetKey = getUploadFileKey(target)
  uploadFileList.value = uploadFileList.value.filter(file => getUploadFileKey(file) !== targetKey)
  delete uploadFileFailedReasonMap.value[targetKey]
}

const formatUploadFileSize = (size?: number) => {
  const normalized = Number(size || 0)
  if (!normalized) return '--'
  if (normalized < 1024) return `${normalized}B`
  if (normalized < 1024 * 1024) return `${(normalized / 1024).toFixed(1)}KB`
  return `${(normalized / 1024 / 1024).toFixed(1)}MB`
}

const triggerUploadFileSelect = () => {
  if (uploading.value) return
  uploadFileInputRef.value?.click()
}

const validateUploadFile = (file: File) => {
  const allowedMimes = [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'image/png',
    'image/jpeg',
    'image/bmp'
  ]
  const ext = (file.name || '').toLowerCase()
  const allowedExts = ['.txt', '.md', '.pdf', '.docx', '.doc', '.csv', '.xls', '.xlsx', '.pptx', '.png', '.jpg', '.jpeg', '.bmp']
  const byMime = allowedMimes.includes(file.type || '')
  const byExt = allowedExts.some(e => ext.endsWith(e))
  const isValidType = byMime || byExt
  if (!isValidType) {
    NotificationService.error('只支持 txt、md、pdf、docx、doc、csv、xls、xlsx、pptx、png、jpg、jpeg、bmp 格式文件')
    return false
  }

  const maxSize = getFileUploadMaxSize()
  const isLtLimit = (file.size || 0) / 1024 / 1024 < maxSize
  if (!isLtLimit) {
    NotificationService.info(`文件大小不能超过 ${maxSize}MB`)
    return false
  }
  return true
}

const addFilesToUploadList = (nativeFiles: File[]) => {
  if (nativeFiles.length === 0) return
  const existingIdentitySet = new Set(
    uploadFileList.value.map(item => {
      const raw = (item as any).originFileObj as File | undefined
      return raw ? `${raw.name}__${raw.size}__${raw.lastModified}` : `${item.name || ''}__${item.size || 0}`
    })
  )
  const nextFileList = [...uploadFileList.value]
  nativeFiles.forEach((file, index) => {
    if (!validateUploadFile(file)) return
    const identity = `${file.name}__${file.size}__${file.lastModified}`
    if (existingIdentitySet.has(identity)) return
    existingIdentitySet.add(identity)
    const uploadFile: UploadFile = {
      uid: `${Date.now()}_${index}_${Math.random().toString(36).slice(2, 8)}`,
      name: file.name,
      size: file.size,
      type: file.type,
      originFileObj: file as any
    }
    nextFileList.push(uploadFile)
  })
  uploadFileList.value = nextFileList
}

const handleUploadFileInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement
  const files = Array.from(target.files || [])
  addFilesToUploadList(files)
  target.value = ''
}

const handleUploadDragEnter = (event: DragEvent) => {
  event.stopPropagation()
  if (uploading.value) return
  if (!event.dataTransfer?.types.includes('Files')) return
  isUploadDragging.value = true
}

const handleUploadDragOver = (event: DragEvent) => {
  event.stopPropagation()
  if (uploading.value) return
  isUploadDragging.value = true
}

const handleUploadDragLeave = (event: DragEvent) => {
  event.stopPropagation()
  isUploadDragging.value = false
}

const handleUploadDrop = (event: DragEvent) => {
  event.stopPropagation()
  if (uploading.value) return
  isUploadDragging.value = false
  const files = Array.from(event.dataTransfer?.files || [])
  addFilesToUploadList(files)
}

const uploadDraggerText = computed(() => {
  if (uploadFileList.value.length === 0) return '点击或拖拽文件到此区域上传'
  if (uploadFileFailedReasonMap.value && Object.keys(uploadFileFailedReasonMap.value).length > 0) {
    return `待重试 ${uploadFileList.value.length} 个文件`
  }
  return `已添加 ${uploadFileList.value.length} 个文件`
})

const uploadDraggerHint = computed(() => {
  if (uploadFileList.value.length > 0) {
    return '支持继续拖拽添加文件，可在下方自定义列表中移除文件'
  }
  return '支持单次或批量上传，仅支持上传txt、md、pdf、docx、doc、csv、xls、xlsx、pptx、png、jpg、jpeg、bmp格式文件'
})

const parseUploadError = (error: unknown, fallbackFileNames: string[]) => {
  let message = '上传文档失败'
  const failedFiles: Record<string, string> = {}
  const successFiles: string[] = []

  if (error instanceof UploadDocsError) {
    message = error.message || message
    const apiFailedFiles = error.data?.failed_files || {}
    Object.entries(apiFailedFiles).forEach(([name, reason]) => {
      failedFiles[name] = reason || message
    })
    if (Array.isArray(error.data?.success_files)) {
      successFiles.push(...error.data.success_files)
    }
  } else {
    const responseData = (error as any)?.response?.data as RemoteUploadDocsResponse | undefined
    if (responseData) {
      message = responseData.msg || message
      const apiFailedFiles = responseData.data?.failed_files || {}
      Object.entries(apiFailedFiles).forEach(([name, reason]) => {
        failedFiles[name] = reason || message
      })
      if (Array.isArray(responseData.data?.success_files)) {
        successFiles.push(...responseData.data.success_files)
      }
    } else if ((error as any)?.message) {
      message = String((error as any).message)
    }
  }

  if (Object.keys(failedFiles).length === 0) {
    fallbackFileNames.forEach(fileName => {
      failedFiles[fileName] = message
    })
  }

  return { message, failedFiles, successFiles }
}

const handleUploadDocument = async () => {
  if (!selectedKnowledgeBase.value) {
    NotificationService.info('请在左侧选择一个知识库')
    return
  }
  if (uploadFileList.value.length === 0) {
    NotificationService.error('请选择要上传的文件')
    return
  }
  if (uploadOptions.value.chunkSize === undefined || uploadOptions.value.chunkSize === null || isNaN(Number(uploadOptions.value.chunkSize))) {
    NotificationService.error('请填写单段文本最大长度 (chunk_size)')
    return
  }
  if (uploadOptions.value.chunkOverlap === undefined || uploadOptions.value.chunkOverlap === null || isNaN(Number(uploadOptions.value.chunkOverlap))) {
    NotificationService.error('请填写相邻文本重合长度 (chunk_overlap)')
    return
  }
  if (!uploadOptions.value.classification) {
    NotificationService.warning('请选择文件密级')
    return
  }

  try {
    uploading.value = true
    const files: File[] = []
    uploadFileList.value.forEach((file: UploadFile) => {
      const raw = (file as any).originFileObj as File | undefined
      if (raw) files.push(raw)
    })
    if (files.length === 0) {
      NotificationService.error('请选择要上传的文件')
      return
    }

    const kbName = selectedKnowledgeBase.value.name
    const enableKg = !!selectedKnowledgeBase.value.includeKg
    const pendingDocMap = {
      ...(kgPendingDocsByKnowledgeBase.value[kbName] || {})
    }
    const successFileNames = new Set<string>()
    const failedFileMap: Record<string, string> = {}

    const mergeFailedFiles = (next: Record<string, string>) => {
      Object.entries(next).forEach(([name, reason]) => {
        failedFileMap[name] = reason || '上传失败'
      })
    }

    const parseUploadResponse = (uploadRes: RemoteUploadDocsResponse, fallbackNames: string[]) => {
      const failedMap = uploadRes.data?.failed_files || {}
      mergeFailedFiles(failedMap)
      const failedNameSet = new Set(Object.keys(failedMap))
      const reportedSuccess = Array.isArray(uploadRes.data?.success_files) ? uploadRes.data!.success_files! : []
      const successNames = reportedSuccess.length > 0
        ? reportedSuccess
        : fallbackNames.filter(name => !failedNameSet.has(name))
      successNames.forEach(name => successFileNames.add(name))
      return successNames
    }

    if (enableKg && files.length > 1) {
      for (const file of files) {
        try {
          const uploadRes = await uploadKnowledgeBaseDocs({
            knowledge_base_name: kbName,
            files: [file],
            chunk_size: uploadOptions.value.chunkSize,
            chunk_overlap: uploadOptions.value.chunkOverlap,
            zh_title_enhance: uploadOptions.value.zhTitleEnhance,
            override: false,
            to_vector_store: true,
            not_refresh_vs_cache: false,
            enable_graph_rag: true,
            classification: uploadOptions.value.classification || undefined
          })
          const successNames = parseUploadResponse(uploadRes, [file.name])
          const submittedAt = Date.now()
          successNames.forEach(name => {
            pendingDocMap[name] = { submittedAt, seenInTaskList: false }
          })
        } catch (error) {
          const parsedError = parseUploadError(error, [file.name])
          mergeFailedFiles(parsedError.failedFiles)
          parsedError.successFiles.forEach(name => successFileNames.add(name))
        }
      }
    } else {
      try {
        const uploadRes = await uploadKnowledgeBaseDocs({
          knowledge_base_name: kbName,
          files,
          chunk_size: uploadOptions.value.chunkSize,
          chunk_overlap: uploadOptions.value.chunkOverlap,
          zh_title_enhance: uploadOptions.value.zhTitleEnhance,
          override: false,
          to_vector_store: true,
          not_refresh_vs_cache: false,
          enable_graph_rag: selectedKnowledgeBase.value.includeKg,
          classification: uploadOptions.value.classification || undefined
        })
        const successNames = parseUploadResponse(uploadRes, files.map(file => file.name))
        if (enableKg) {
          const submittedAt = Date.now()
          successNames.forEach(fileName => {
            pendingDocMap[fileName] = { submittedAt, seenInTaskList: false }
          })
        }
      } catch (error) {
        const parsedError = parseUploadError(error, files.map(file => file.name))
        mergeFailedFiles(parsedError.failedFiles)
        parsedError.successFiles.forEach(name => successFileNames.add(name))
      }
    }

    if (enableKg) {
      if (Object.keys(pendingDocMap).length > 0) {
        kgPendingDocsByKnowledgeBase.value[kbName] = pendingDocMap
      } else {
        delete kgPendingDocsByKnowledgeBase.value[kbName]
      }
    }
    if (enableKg && successFileNames.size > 0) {
      startKgTasksPolling()
    }

    const failedEntries = Object.entries(failedFileMap)
    const failedCount = failedEntries.length
    const successCount = successFileNames.size

    if (successCount > 0) {
      // 上传后有新文档，强制重新拉取并回写文档缓存
      await loadSelectedKnowledgeBaseFiles({ force: true })
    }

    if (failedCount === 0) {
      NotificationService.success(enableKg && files.length > 1 ? '文档上传成功，已按顺序加入图谱构建队列' : '文档上传成功')
      uploadModalVisible.value = false
      resetUploadForm()
      return
    }

    const failedFileNames = new Set(failedEntries.map(([name]) => name))
    const nextFailedFileList: UploadFile[] = []
    const nextFailedReasonMap: Record<string, string> = {}
    uploadFileList.value.forEach(item => {
      const fileName = item.name || ''
      if (!failedFileNames.has(fileName)) return
      item.status = 'error'
      item.response = failedFileMap[fileName] || '上传失败'
      nextFailedFileList.push(item)
      nextFailedReasonMap[getUploadFileKey(item)] = failedFileMap[fileName] || '上传失败'
    })
    uploadFileList.value = nextFailedFileList
    uploadFileFailedReasonMap.value = nextFailedReasonMap
    if (successCount > 0) {
      NotificationService.warning(`上传完成：成功 ${successCount} 个，失败 ${failedCount} 个`)
    }
    const failedDetail = failedEntries.map(([name, reason]) => `${name}：${reason}`).join('；')
    NotificationService.error(`以下文件上传失败：${failedDetail}`)
  } catch (e) {
    console.error('上传文档失败:', e)
    NotificationService.error('上传文档失败，请稍后重试')
  } finally {
    uploading.value = false
  }
}

const previewDocument = (doc: Document) => {
  openSlicesModal(doc)
}

const downloadDocument = async (doc: Document) => {
  if (!selectedKnowledgeBase.value) {
    NotificationService.info('请在左侧选择一个知识库')
    return
  }
  const kbName = selectedKnowledgeBase.value.name
  const loadingKey = NotificationService.loading('正在下载文件...', 0)
  try {
    const { data, headers } = await downloadKnowledgeBaseDoc({
      knowledge_base_name: kbName,
      file_name: doc.name,
      preview: false
    })

    // 从响应头尝试解析文件名与类型
    const disposition = headers.get('content-disposition') || ''
    const matchedName = /filename\*=UTF-8''([^;\n]+)|filename="?([^";\n]+)"?/i.exec(disposition)
    const suggestedName = decodeURIComponent((matchedName?.[1] || matchedName?.[2] || doc.name) as string)
    const contentType = headers.get('content-type') || 'application/octet-stream'

    let blob: Blob
    if (data instanceof Blob) {
      blob = data
    } else {
      const textData = data as string
      // 如果是字符串：优先按文本类型处理；否则尝试按 base64 处理
      if (/^data:.+;base64,/.test(textData)) {
        // 直接使用 data URL
        const a = document.createElement('a')
        a.href = textData
        a.download = suggestedName
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        NotificationService.close(loadingKey)
        NotificationService.success('文件已开始下载')
        return
      }
      if (contentType.includes('text/')) {
        blob = new Blob([textData], { type: contentType })
      } else {
        // 尝试按 base64 解码；失败则按纯文本二进制兜底
        try {
          const binaryStr = atob(textData)
          const len = binaryStr.length
          const bytes = new Uint8Array(len)
          for (let i = 0; i < len; i++) bytes[i] = binaryStr.charCodeAt(i)
          blob = new Blob([bytes], { type: contentType || 'application/octet-stream' })
        } catch (e) {
          blob = new Blob([textData], { type: 'application/octet-stream' })
        }
      }
    }

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = suggestedName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    NotificationService.close(loadingKey)
    NotificationService.success('文件已开始下载')
  } catch (error: any) {
    NotificationService.close(loadingKey)
    console.error('下载失败:', error)
    NotificationService.error(typeof error?.message === 'string' ? error.message : '下载失败，请重试')
  }
}

const openSlicesModal = (doc: Document) => {
  if (!selectedKnowledgeBase.value) {
    NotificationService.info('请在左侧选择一个知识库')
    return
  }
  viewingDocName.value = doc.name
  slicesModalVisible.value = true
}

const isDocumentKgPending = (doc: Document) => {
  if (!selectedKnowledgeBase.value?.includeKg) return false
  const kbName = selectedKnowledgeBase.value.name
  const task = kgTasks.value.find(item =>
    item.file_name === doc.name &&
    (item.status === 'running' || item.status === 'pending')
  )
  if (task) return true
  return !!kgPendingDocsByKnowledgeBase.value[kbName]?.[doc.name]
}

const setDeleteConfirmModalLocked = (
  modal: { update: (config: Record<string, unknown>) => void },
  locked: boolean
) => {
  modal.update({
    closable: !locked,
    keyboard: !locked,
    maskClosable: !locked,
    cancelButtonProps: {
      disabled: locked
    }
  })
}

const deleteDocument = (doc: Document) => {
  if (!selectedKnowledgeBase.value) return
  if (!canManageKnowledgeBase(selectedKnowledgeBase.value, isCurrentUserAdmin.value)) {
    NotificationService.info(KB_DELETE_DOC_ADMIN_ONLY_TIP)
    return
  }
  if (isDocumentKgPending(doc)) {
    NotificationService.info('该文档图谱抽取未完成，暂不可删除')
    return
  }
  const modal = Modal.confirm({
    title: '确认删除文档',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `确定要删除“${doc.name}”吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: async () => {
      setDeleteConfirmModalLocked(modal, true)
      try {
        await deleteKnowledgeBaseDocs({
          knowledge_base_name: selectedKnowledgeBase.value!.name,
          file_names: [doc.name],
          delete_content: true,
          not_refresh_vs_cache: false,
          force_delete: true,
          enable_graph_rag: selectedKnowledgeBase.value!.includeKg
        })

        const index = selectedKnowledgeBase.value!.documents.findIndex(item => item.id === doc.id)
        if (index > -1) {
          selectedKnowledgeBase.value!.documents.splice(index, 1)
        }
        syncSelectedKnowledgeBaseDocumentCount()
        const kbName = selectedKnowledgeBase.value!.name
        const pendingDocMap = kgPendingDocsByKnowledgeBase.value[kbName]
        if (pendingDocMap && pendingDocMap[doc.name]) {
          const nextPendingDocMap = { ...pendingDocMap }
          delete nextPendingDocMap[doc.name]
          if (Object.keys(nextPendingDocMap).length > 0) {
            kgPendingDocsByKnowledgeBase.value[kbName] = nextPendingDocMap
          } else {
            delete kgPendingDocsByKnowledgeBase.value[kbName]
          }
        }
        await reconcileSelectedKnowledgeBaseFilesAfterDelete([doc.name])
        NotificationService.success('文档已删除')
      } catch (error: any) {
        setDeleteConfirmModalLocked(modal, false)
        console.error('删除文档失败:', error)
        NotificationService.error(typeof error?.message === 'string' ? error.message : '删除失败，请重试')
      }
    }
  })
}

const bulkDownloadDocuments = async (ids: string[]) => {
  if (!selectedKnowledgeBase.value) {
    NotificationService.info('请在左侧选择一个知识库')
    return
  }
  const kbName = selectedKnowledgeBase.value.name
  const docs = selectedKnowledgeBase.value.documents.filter(d => ids.includes(d.id))
  if (docs.length === 0) return
  const loadingKey = NotificationService.loading(`正在下载 ${docs.length} 个文件...`, 0)
  try {
    for (const doc of docs) {
      const { data, headers } = await downloadKnowledgeBaseDoc({
        knowledge_base_name: kbName,
        file_name: doc.name,
        preview: false
      })
      const disposition = headers.get('content-disposition') || ''
      const matchedName = /filename\*=UTF-8''([^;\n]+)|filename="?([^";\n]+)"?/i.exec(disposition)
      const suggestedName = decodeURIComponent((matchedName?.[1] || matchedName?.[2] || doc.name) as string)
      const contentType = headers.get('content-type') || 'application/octet-stream'
      let blob: Blob
      if (data instanceof Blob) {
        blob = data
      } else {
        const textData = data as string
        if (/^data:.+;base64,/.test(textData)) {
          const a = document.createElement('a')
          a.href = textData
          a.download = suggestedName
          document.body.appendChild(a)
          a.click()
          document.body.removeChild(a)
          continue
        }
        if (contentType.includes('text/')) {
          blob = new Blob([textData], { type: contentType })
        } else {
          try {
            const binaryStr = atob(textData)
            const len = binaryStr.length
            const bytes = new Uint8Array(len)
            for (let i = 0; i < len; i++) bytes[i] = binaryStr.charCodeAt(i)
            blob = new Blob([bytes], { type: contentType || 'application/octet-stream' })
          } catch (e) {
            blob = new Blob([textData], { type: 'application/octet-stream' })
          }
        }
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = suggestedName
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    }
    NotificationService.close(loadingKey)
    NotificationService.success('文件已开始下载')
  } catch (error: any) {
    NotificationService.close(loadingKey)
    console.error('批量下载失败:', error)
    NotificationService.error(typeof error?.message === 'string' ? error.message : '下载失败，请重试')
  }
}

const bulkDeleteDocuments = (ids: string[]) => {
  if (!selectedKnowledgeBase.value) return
  // 与单文档删除、上传保持同一套限制：共享知识库仅 admin 可删除文档
  if (!canManageKnowledgeBase(selectedKnowledgeBase.value, isCurrentUserAdmin.value)) {
    NotificationService.info(KB_DELETE_DOC_ADMIN_ONLY_TIP)
    return
  }
  const docs = selectedKnowledgeBase.value.documents.filter(d => ids.includes(d.id))
  if (docs.length === 0) return
  const lockedDocs = docs.filter(isDocumentKgPending)
  if (lockedDocs.length > 0) {
    NotificationService.info(`有 ${lockedDocs.length} 个文档图谱未完成，暂不可删除`)
    return
  }
  const modal = Modal.confirm({
    title: '确认删除所选文档',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `确定要删除选中的 ${docs.length} 个文档吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: async () => {
      setDeleteConfirmModalLocked(modal, true)
      try {
        await deleteKnowledgeBaseDocs({
          knowledge_base_name: selectedKnowledgeBase.value!.name,
          file_names: docs.map(d => d.name),
          delete_content: true,
          not_refresh_vs_cache: false,
          force_delete: true,
          enable_graph_rag: selectedKnowledgeBase.value!.includeKg
        })
        const deletedNameSet = new Set(docs.map(d => d.name))
        const deletedIdSet = new Set(ids)
        selectedKnowledgeBase.value!.documents = selectedKnowledgeBase.value!.documents.filter(
          d => !deletedIdSet.has(d.id) && !deletedNameSet.has(d.name)
        )
        syncSelectedKnowledgeBaseDocumentCount()
        const kbName = selectedKnowledgeBase.value!.name
        const pendingDocMap = kgPendingDocsByKnowledgeBase.value[kbName]
        if (pendingDocMap) {
          const toDelete = new Set(docs.map(d => d.name))
          const nextPendingDocMap = { ...pendingDocMap }
          let changed = false
          toDelete.forEach(name => {
            if (nextPendingDocMap[name]) {
              delete nextPendingDocMap[name]
              changed = true
            }
          })
          if (changed) {
            if (Object.keys(nextPendingDocMap).length > 0) {
              kgPendingDocsByKnowledgeBase.value[kbName] = nextPendingDocMap
            } else {
              delete kgPendingDocsByKnowledgeBase.value[kbName]
            }
          }
        }
        await reconcileSelectedKnowledgeBaseFilesAfterDelete(docs.map(d => d.name))
        NotificationService.success('选中文档已删除')
      } catch (error: any) {
        setDeleteConfirmModalLocked(modal, false)
        console.error('批量删除失败:', error)
        NotificationService.error(typeof error?.message === 'string' ? error.message : '删除失败，请重试')
      }
    }
  })
}

const handleUpdateKnowledgeBaseInfo = async () => {
  if (!editingKb.value) return
  if (isSharedKnowledgeBaseReadonly.value) {
    NotificationService.info(KB_SHARED_READONLY_TIP)
    return
  }
  const originalName = editingKb.value.name
  const originalDescription = (editingKb.value.description || '').trim()
  const hasOriginalPermission = typeof editingKb.value.permissionCode === 'string' && editingKb.value.permissionCode.trim() !== ''
  const originalPermission = editingKb.value.permissionCode === 'public' ? 'public' : 'private'
  const nextName = editForm.value.name.trim()
  const desc = editForm.value.description.trim()
  const permission = canEditVisibility.value ? editForm.value.permissionCode : originalPermission

  if (!nextName) {
    NotificationService.error('请填写知识库名称')
    return
  }
  if (nextName.length > 50) {
    NotificationService.error('知识库名称不能超过50个字符')
    return
  }
  if (!permission) {
    NotificationService.error('请选择知识库权限')
    return
  }
  if (canEditVisibility.value && permission === 'public' && editForm.value.permissionGroupIds.length === 0) {
    NotificationService.error('共享知识库至少需要选择一个用户组')
    return
  }
  if (!desc) {
    NotificationService.error('请填写知识库描述')
    return
  }
  if (desc.length > 200) {
    NotificationService.error('知识库描述不能超过200个字符')
    return
  }

  const newKbName = nextName && nextName !== originalName ? nextName : ''
  const newPermissionCode = !hasOriginalPermission
    ? permission
    : (permission !== originalPermission ? permission : '')
  const hasPermissionGroupChanged = canEditVisibility.value
    && permission === 'public'
    && areSamePermissionGroups(editForm.value.permissionGroupIds, editingOriginalPermissionGroupIds.value) === false

  if (newKbName === '' && newPermissionCode === '' && desc === originalDescription && !hasPermissionGroupChanged) {
    NotificationService.info('未检测到任何修改')
    return
  }

  editingKbLoading.value = true
  try {
    const permissionGroupUuids = canEditVisibility.value && permission === 'public'
      ? mapPermissionGroupSelectionToUuids(editForm.value.permissionGroupIds)
      : []
    const permissionGroupIds = canEditVisibility.value && permission === 'public'
      ? normalizePermissionGroupIds(editForm.value.permissionGroupIds)
      : []
    await updateKnowledgeBaseInfo({
      knowledge_base_name: originalName,
      kb_info: desc,
      new_kb_name: newKbName,
      new_permission_code: newPermissionCode,
      permission_group_ids: permissionGroupUuids,
      permissionGroupIds: permissionGroupUuids,
      enable_graph_rag: editingKb.value.includeKg
    })
    const entityId = editingKb.value.kbUuid?.trim()
    if (entityId && permissionGroupIds.length > 0) {
      for (const groupId of permissionGroupIds) {
        await updateAiPermission({
          group_id: groupId,
          list: [
            {
              entity_id: entityId,
              entity_type: KNOWLEDGE_BASE_ENTITY_TYPE,
              permission: 1
            }
          ]
        })
      }
    }
    const nextSelectedKbName = newKbName || originalName
    // 名称/可见范围可能变化，两个分类的缓存都失效后重新拉取
    invalidateKbListCache()
    await loadKnowledgeBases(nextSelectedKbName, { force: true })
    eventBus.emit('knowledge-base-list-updated')
    NotificationService.success('知识库信息已更新')
    editModalVisible.value = false
    editingKb.value = null
    editingDraftPermissionGroupIds.value = []
    editingOriginalPermissionGroupIds.value = []
  } catch (error: any) {
    console.error('更新知识库信息失败:', error)
    NotificationService.error(typeof error?.message === 'string' ? error.message : '更新失败，请重试')
  } finally {
    editingKbLoading.value = false
  }
}

let lastEntitySetIndex = -1
const generateRandomEntityTags = () => {
  const entitySets = [
    ['Person', 'Location', 'Organization', 'Event', 'Date'],
    ['Company', 'Product', 'Brand', 'Technology', 'Industry'],
    ['Country', 'City', 'Landmark', 'Institution', 'Person'],
    ['Disease', 'Symptom', 'Drug', 'Treatment', 'Department'],
    ['Author', 'Book', 'Publisher', 'Year', 'Genre']
  ]
  let randomIndex: number
  do {
    randomIndex = Math.floor(Math.random() * entitySets.length)
  } while (randomIndex === lastEntitySetIndex && entitySets.length > 1)
  lastEntitySetIndex = randomIndex
  createForm.value.allowedNodes = entitySets[randomIndex]
}

let lastRelationSetIndex = -1
const generateRandomRelationshipTags = () => {
  const relationSets = [
    ['WORKS_AT', 'COLLEAGUE_OF', 'FRIEND_OF', 'BORN_IN', 'HAPPENED_IN'],
    ['BELONGS_TO', 'PRODUCES', 'PARTNERS_WITH', 'COMPETES_WITH', 'USES'],
    ['LOCATED_IN', 'CONTAINS', 'FOUNDED_IN', 'FOUNDED_BY', 'HEADQUARTERED_IN'],
    ['TREATS', 'CAUSES', 'PREVENTS', 'HAS_INGREDIENT', 'APPLIES_TO'],
    ['WROTE', 'PUBLISHED_IN', 'HAS_GENRE', 'WON_AWARD', 'REVIEWED_BY']
  ]
  let randomIndex: number
  do {
    randomIndex = Math.floor(Math.random() * relationSets.length)
  } while (randomIndex === lastRelationSetIndex && relationSets.length > 1)
  lastRelationSetIndex = randomIndex
  createForm.value.allowedRelationships = relationSets[randomIndex]
}

const onEditModalCancel = () => {
  if (editingKbLoading.value) return
  editModalVisible.value = false
  editingKb.value = null
  editingDraftPermissionGroupIds.value = []
  editingOriginalPermissionGroupIds.value = []
  editForm.value = {
    description: '',
    name: '',
    permissionCode: 'private',
    permissionGroupIds: []
  }
}

const handleExtract = async () => {
  if (!createForm.value.exampleText.trim()) {
    NotificationService.warning('请先输入示例文本')
    return
  }
  
  try {
    isExtracting.value = true
    const res = await autoNodesAndRelationships({ 
      example_text: createForm.value.exampleText,
      allowed_nodes: createForm.value.allowedNodes.length ? createForm.value.allowedNodes : undefined,
      allowed_relationships: createForm.value.allowedRelationships.length ? createForm.value.allowedRelationships : undefined
    })
    console.log('自动提取结果:', res)
    
    // 假设返回的数据直接是对象，或者在 res.data 中
    const responseData = res.data || res;
    
    if (responseData) {
      if (Array.isArray(responseData.allowed_nodes) && responseData.allowed_nodes.length > 0) {
        createForm.value.allowedNodes = responseData.allowed_nodes
      }
      if (Array.isArray(responseData.allowed_relationships) && responseData.allowed_relationships.length > 0) {
        createForm.value.allowedRelationships = responseData.allowed_relationships
      }
      
      // 解析 examples 生成实体和关系列表
      if (Array.isArray(responseData.examples) && responseData.examples.length > 0) {
        const newEntitiesMap = new Map<string, ExtractedEntity>();
        const newRelationships: ExtractedRelationship[] = [];
        
        responseData.examples.forEach((example: any, index: number) => {
          // 处理头实体
          if (example.head && !newEntitiesMap.has(example.head)) {
            newEntitiesMap.set(example.head, {
              id: `entity_head_${index}_${Date.now()}`,
              name: example.head,
              type: example.head_type || '',
              properties: []
            });
          }
          
          // 处理尾实体
          if (example.tail && !newEntitiesMap.has(example.tail)) {
            newEntitiesMap.set(example.tail, {
              id: `entity_tail_${index}_${Date.now()}`,
              name: example.tail,
              type: example.tail_type || '',
              properties: []
            });
          }
          
          // 处理关系
          if (example.head && example.edge && example.tail) {
            newRelationships.push({
              id: `rel_${index}_${Date.now()}`,
              head: example.head,
              head_type: example.head_type || '',
              edge: example.edge,
              tail: example.tail,
              tail_type: example.tail_type || ''
            });
          }
        });
        
        extractedEntities.value = Array.from(newEntitiesMap.values());
        extractedRelationships.value = newRelationships;
      }
    }
    
    NotificationService.success('实体关系提取成功')
  } catch (error: any) {
    console.error('自动提取失败:', error)
    NotificationService.error(error.message || '自动提取失败')
  } finally {
    isExtracting.value = false
  }
}

// 实体和关系列表管理方法
const removeRelationship = (index: number) => {
  extractedRelationships.value.splice(index, 1);
};

const knowledgeBaseStore = useKnowledgeBaseStore();

// 消费"打开上传/创建模态框"的跨组件标记；设置页与聊天工作区两种布局都生效
const tryOpenPendingUploadModal = async () => {
  const kbName = knowledgeBaseStore.getKbNameToOpenUploadModal();
  if (!kbName) return;

  // 清除状态
  knowledgeBaseStore.clearKbNameToOpenUploadModal();

  // 如果是创建新知识库的标识
  if (kbName === '__create_new_kb__') {
    await nextTick()
    if (!isDisposed) showCreateModal()
    return;
  }

  // 查找对应的知识库并选中
  const kb = knowledgeBases.value.find(k => k.name === kbName);
  if (kb) {
    await selectKnowledgeBase(kb)
    await nextTick()
    if (!isDisposed && selectedKnowledgeBase.value?.name === kb.name) showUploadModal()
  }
}

// 在组件挂载时检查是否需要打开上传模态框
onMounted(async () => {
  await loadKnowledgeBases()
  if (isDisposed) return
  await tryOpenPendingUploadModal()
})

watch(kbPermissionFilter, async () => {
  persistKnowledgeBaseViewContext(kbPermissionFilter.value, selectedKnowledgeBase.value?.name || null)
  const preferredKbName = pendingPreferredKnowledgeBaseName.value || undefined
  // 携带目标知识库（新建/编辑后跳转过来）时强制刷新，避免落到过期的缓存上
  const force = !!pendingPreferredKnowledgeBaseName.value
  pendingPreferredKnowledgeBaseName.value = null
  await loadKnowledgeBases(preferredKbName, { force })
})

// 把列表数据落到视图上：选中目标知识库并加载其文档
const applyKnowledgeBases = async (items: KnowledgeBase[], preferredKbName?: string) => {
  hasLoadedKnowledgeBasesOnce = true
  knowledgeBases.value = items
  if (knowledgeBases.value.length > 0) {
    const savedKbName = localStorage.getItem(SELECTED_KB_NAME_STORAGE_KEY)
    const targetKb = knowledgeBases.value.find(kb => kb.name === preferredKbName)
      || knowledgeBases.value.find(kb => kb.name === savedKbName)
      || knowledgeBases.value[0]
    selectedKnowledgeBase.value = targetKb
    persistKnowledgeBaseViewContext(kbPermissionFilter.value, targetKb.name)
    kgTasks.value = []
    await loadSelectedKnowledgeBaseFiles()
  } else {
    selectedKnowledgeBase.value = null
    persistKnowledgeBaseViewContext(kbPermissionFilter.value, null)
    kgTasks.value = []
    stopKgTasksPolling()
  }
}

const oppositeFilterOf = (filter: KnowledgeBasePermissionCode): KnowledgeBasePermissionCode =>
  filter === 'public' ? 'private' : 'public'

// 同一个分类的预热只发一次，避免切换分类时重复请求
const prefetchingKbFilters = new Set<KnowledgeBasePermissionCode>()

// 预热指定分类的列表；与当前分类的请求同时发出，进入页面后两个分类的数据一起就绪
const prefetchKbList = (filter: KnowledgeBasePermissionCode) => {
  if (isDisposed) return
  if (isKbListCacheFresh(filter) || prefetchingKbFilters.has(filter)) return
  prefetchingKbFilters.add(filter)
  listKnowledgeBases(filter)
    .then(items => {
      if (isDisposed) return
      writeKbListCache(filter, items)
    })
    .catch(err => console.warn('预热知识库列表失败:', err))
    .finally(() => prefetchingKbFilters.delete(filter))
}

// 加载远端知识库列表（带缓存：stale-while-revalidate）
// - 有缓存：先用缓存上屏，不显示骨架屏，再按需后台静默刷新
// - 无缓存：走首屏骨架屏
const loadKnowledgeBases = async (preferredKbName?: string, options: { force?: boolean } = {}) => {
  if (isDisposed) return
  const permissionFilter = kbPermissionFilter.value
  const requestId = ++knowledgeBaseListRequestId
  const isCurrentRequest = () => !isDisposed
    && requestId === knowledgeBaseListRequestId
    && permissionFilter === kbPermissionFilter.value

  const cachedList = peekKbListCache(permissionFilter)
  const hasCachedList = Array.isArray(cachedList)
  const cacheIsFresh = isKbListCacheFresh(permissionFilter)

  // 「共享」与「个人」两个请求并行发出：本函数只 await 当前分类，
  // 另一个分类同时预热到缓存，切换过去时不再有网络等待
  prefetchKbList(oppositeFilterOf(permissionFilter))

  // 命中缓存：立刻渲染，避免个人/共享切换、聊天 ↔ 知识库来回切换时反复出现骨架屏
  if (hasCachedList) {
    await applyKnowledgeBases(cachedList as KnowledgeBase[], preferredKbName)
    if (!isCurrentRequest()) return
    kbListLoading.value = false
  }

  // 缓存仍然新鲜且不是强制刷新：直接复用，不再发起请求
  if (hasCachedList && cacheIsFresh && !options.force) {
    kbListRefreshing.value = false
    return
  }

  ++selectedFilesRequestId
  stopKgTasksPolling()
  docsLoading.value = false
  try {
    kbListLoading.value = !hasCachedList
    kbListRefreshing.value = hasCachedList
    kbListError.value = ''
    const nextKnowledgeBases = await listKnowledgeBases(permissionFilter)
    if (!isCurrentRequest()) return
    writeKbListCache(permissionFilter, nextKnowledgeBases)
    await applyKnowledgeBases(nextKnowledgeBases, preferredKbName)
  } catch (err) {
    if (!isCurrentRequest()) return
    console.error('加载知识库失败:', err)
    if (!hasCachedList) {
      // 没有任何缓存时才清空列表并展示错误态；已有缓存则继续展示旧数据，仅提示
      knowledgeBases.value = []
      selectedKnowledgeBase.value = null
      kgTasks.value = []
      docsLoading.value = false
      stopKgTasksPolling()
      kbListError.value = '加载知识库失败，请检查网络或知识库服务后重试'
      NotificationService.error(kbListError.value)
    } else {
      NotificationService.error('知识库刷新失败，仍显示上次加载的内容')
    }
  } finally {
    if (isCurrentRequest()) {
      kbListLoading.value = false
      kbListRefreshing.value = false
    }
  }
}

const stopKgTasksPolling = () => {
  ++kgPollingGeneration
  if (kgTasksInterval) {
    clearInterval(kgTasksInterval)
    kgTasksInterval = null
  }
}

const fetchKgTasks = async () => {
  if (isDisposed || !selectedKnowledgeBase.value) {
    stopKgTasksPolling()
    return
  }
  const kbName = selectedKnowledgeBase.value.name
  const requestId = ++kgTasksRequestId
  const generation = kgPollingGeneration
  const isCurrentRequest = () => !isDisposed
    && requestId === kgTasksRequestId
    && generation === kgPollingGeneration
    && selectedKnowledgeBase.value?.name === kbName
  try {
    const tasks = await listAllKnowledgeGraphTask(kbName)
    if (!isCurrentRequest()) {
      return
    }
    kgTasks.value = tasks
    const previousTaskStatusMap = kgTaskStatusSnapshotByKnowledgeBase.value[kbName] || {}
    const nextTaskStatusMap: Record<string, string> = {}
    tasks.forEach(task => {
      const taskKey = buildKgTaskKey(task)
      if (!taskKey) return
      nextTaskStatusMap[taskKey] = task.status || ''
    })
    kgTaskStatusSnapshotByKnowledgeBase.value[kbName] = nextTaskStatusMap
    const hasTaskCompleted = Object.entries(nextTaskStatusMap).some(([key, status]) => {
      const previousStatus = previousTaskStatusMap[key]
      return !!previousStatus && isKgTaskActive(previousStatus) && !isKgTaskActive(status)
    })
    const hasTaskDisappearedAfterActive = Object.entries(previousTaskStatusMap).some(([key, status]) => {
      return isKgTaskActive(status) && !nextTaskStatusMap[key]
    })
    if (hasTaskCompleted || hasTaskDisappearedAfterActive) {
      const files = await listKnowledgeBaseFiles(kbName)
      if (!isCurrentRequest()) return
      writeKbDocsCache(kbName, files)
      applyFilesToSelectedKnowledgeBase(files)
    }

    const currentPendingDocMap = kgPendingDocsByKnowledgeBase.value[kbName]
    if (currentPendingDocMap) {
      let changed = false
      const now = Date.now()
      const nextPendingDocMap = { ...currentPendingDocMap }
      const activeFileNames = new Set(
        tasks
          .filter(task => task.status === 'running' || task.status === 'pending')
          .map(task => task.file_name)
          .filter(Boolean)
      )
      for (const docName in nextPendingDocMap) {
        const pendingDoc = nextPendingDocMap[docName]
        if (activeFileNames.has(docName)) {
          if (!pendingDoc.seenInTaskList) {
            nextPendingDocMap[docName] = {
              ...pendingDoc,
              seenInTaskList: true
            }
            changed = true
          }
          continue
        }
        if (pendingDoc.seenInTaskList || now - pendingDoc.submittedAt > kgPendingDocGraceMs) {
          delete nextPendingDocMap[docName]
          changed = true
        }
      }
      if (changed) {
        if (Object.keys(nextPendingDocMap).length > 0) {
          kgPendingDocsByKnowledgeBase.value[kbName] = nextPendingDocMap
        } else {
          delete kgPendingDocsByKnowledgeBase.value[kbName]
        }
      }
    }

    const hasRunning = tasks.some(t => t.status === 'running' || t.status === 'pending')
    const hasPendingDocs = Object.keys(kgPendingDocsByKnowledgeBase.value[kbName] || {}).length > 0
    if (!hasRunning && !hasPendingDocs) {
      stopKgTasksPolling()
    }
  } catch (err) {
    if (!isCurrentRequest()) return
    console.error('获取知识图谱任务失败:', err)
  }
}

const startKgTasksPolling = () => {
  stopKgTasksPolling()
  if (isDisposed || !selectedKnowledgeBase.value?.includeKg) return
  fetchKgTasks()
  kgTasksInterval = setInterval(fetchKgTasks, 3000)
}

// 加载当前选中的知识库文件列表（带缓存：重复打开同一知识库时不再出现加载态）
const loadSelectedKnowledgeBaseFiles = async (options: { force?: boolean } = {}) => {
  if (isDisposed || !selectedKnowledgeBase.value) return
  const knowledgeBase = selectedKnowledgeBase.value
  const requestId = ++selectedFilesRequestId
  const isCurrentRequest = () => !isDisposed
    && requestId === selectedFilesRequestId
    && selectedKnowledgeBase.value === knowledgeBase
  stopKgTasksPolling()
  docsError.value = ''

  const cachedFiles = options.force ? null : peekKbDocsCache(knowledgeBase.name)
  if (cachedFiles) applyFilesToSelectedKnowledgeBase(cachedFiles)
  if (cachedFiles && isKbDocsCacheFresh(knowledgeBase.name)) {
    if (knowledgeBase.includeKg) {
      startKgTasksPolling()
    } else {
      kgTasks.value = []
      stopKgTasksPolling()
    }
    docsLoading.value = false
    return
  }

  try {
    docsLoading.value = !cachedFiles && knowledgeBase.documents.length === 0
    const files = await loadKbDocs(knowledgeBase.name, options)
    if (!isCurrentRequest()) return
    applyFilesToSelectedKnowledgeBase(files)
    
    if (knowledgeBase.includeKg) {
      startKgTasksPolling()
    } else {
      kgTasks.value = []
      stopKgTasksPolling()
    }
  } catch (err: any) {
    if (!isCurrentRequest()) return
    console.error('加载知识库文件失败:', err)
    docsError.value = typeof err?.message === 'string' ? err.message : '加载文档列表失败，请重试'
  } finally {
    if (isCurrentRequest()) docsLoading.value = false
  }
}

// 工作区被 KeepAlive 缓存：切回聊天时停掉图谱轮询，切回来时静默校验数据
onActivated(() => {
  if (isDisposed) return
  // 从其它界面带着标记切回知识库工作区时（KeepAlive 走激活而非挂载），同样要打开创建/上传模态框
  void tryOpenPendingUploadModal()
  if (!hasLoadedKnowledgeBasesOnce) return
  if (!isKbListCacheFresh(kbPermissionFilter.value)) {
    // 有缓存时后台刷新，不会退回骨架屏
    void loadKnowledgeBases()
  } else if (selectedKnowledgeBase.value?.includeKg) {
    startKgTasksPolling()
  }
})

onDeactivated(() => {
  stopKgTasksPolling()
})

onUnmounted(() => {
  isDisposed = true
  ++knowledgeBaseListRequestId
  ++selectedFilesRequestId
  stopKgTasksPolling()
})
</script>

<style lang="less">
.knowledge-base.knowledge-base-workspace {
  flex: 0 0 var(--main-content-height, calc(100vh - 65px));
  height: var(--main-content-height, calc(100vh - 65px));
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  background: transparent;
}

.full-screen-modal {
  .ant-modal {
    max-width: 100%;
    top: 0;
    padding-bottom: 0;
    margin: 0;
  }
  .ant-modal-content {
    display: flex;
    flex-direction: column;
    height: 100vh;
    border-radius: 0;
  }
  .ant-modal-body {
    flex: 1;
    overflow: hidden;
    padding: 0;
  }
  
  .ant-modal-close {
    border-radius: 10px !important;
    width: 28px !important;
    height: 28px !important;
    top: 16px;
    inset-inline-end: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  
  .ant-modal-close-x {
    font-size: 13px !important;
    width: 28px !important;
    height: 28px !important;
    line-height: 28px !important;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.create-kb-modal-wrapper {
  .ant-modal-content {
    padding: 0;
    overflow: hidden;
    border-radius: 22px;
  }
  
  .ant-modal-body {
    padding: 0;
  }
}

.kb-layout {
  display: flex;
  height: 750px;
  background: #fff;
}

.kb-sidebar {
  width: 180px;
  background: #ffffff;
  border-right: 1px solid #f0f0f0;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 24px 20px;
  margin-left: 8px;
  
  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 700;
    color: #1f2937;
  }
}

.extract-btn {
  background: #1677ff;
  color: #ffffff;
  border: none;
  border-radius: 12px;
  padding: 7px 18px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 13px;
}

.extract-btn:hover {
  background: #4096ff;
}

/* 实体和关系列表样式 */
.entity-list-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.entity-card {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 12px;
}

.entity-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  
  .entity-icon {
    color: #1677ff;
    font-size: 16px;
  }
  
  .entity-input {
    flex: 1;
    border-radius: 6px;
    border-color: #00d26a;
    &:focus, &:hover {
      border-color: #00d26a;
      box-shadow: 0 0 0 2px rgba(0, 210, 106, 0.2);
    }
  }
}

.entity-card-body {
  padding-left: 24px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.property-row {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .property-input {
    flex: 1;
    border-radius: 6px;
  }
}

.add-property-wrapper {
  margin-top: 4px;
}

.add-property-btn {
  font-size: 12px;
  color: #666;
  background: #f0f0f0;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s;
  
  &:hover {
    background: #e6e6e6;
    color: #333;
  }
}

.manage-entity-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}

.add-entity-btn {
  background: #00d26a;
  color: #ffffff;
  border: none;
  border-radius: 12px;
  padding: 7px 18px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 13px;
  
  &:hover {
    background: #00c060;
  }
}

.relationship-list-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.relationship-row {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fafafa;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid #f0f0f0;
  
  .rel-select {
    flex: 1;
    min-width: 0;
    :deep(.ant-select-selector) {
      border-radius: 6px;
    }
  }
  
  .rel-arrow {
    color: #999;
    font-size: 14px;
    flex-shrink: 0;
  }
}

.delete-btn {
  color: #999;
  padding: 4px;
  height: auto;
  
  &:hover {
    color: #ff4d4f;
    background: transparent;
  }
}

.config-section {
  margin-bottom: -5px;
}

.sidebar-menu-kb-model {
  flex: 1;
  padding: 0;
  overflow-y: auto;
  padding-left: 8px;
  padding-right: 8px;

  .ant-menu {
    border-inline-end: none !important;
  }

  .ant-menu-item {
    height: 40px;
    line-height: 40px;
    width: auto;
    border-radius: 12px;
    padding-left: 15px !important;
    
    &.ant-menu-item-selected {
      background-color: #e6f4ff;
      color: #1677ff;
    }
  }
}

.kb-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.content-header-area {
  padding: 16px 20px;
  border-bottom: 1px solid #f3f4f6;
  position: relative;
  
  .header-title {
    h3 {
      margin: 0;
      font-size: 18px;
      font-weight: 700;
      color: #111827;
    }
    
    p {
      margin: 0;
      font-size: 13px;
      color: #6b7280;
    }
  }
  
  .close-btn {
    position: absolute;
    top: 16px;
    right: 20px;
    background: transparent;
    border: none;
    cursor: pointer;
    color: #9ca3af;
    font-size: 16px;
    padding: 0;
    width: 28px;
    height: 28px;
    border-radius: 10px;
    transition: all 0.2s;
    display: flex;
    align-items: center;
    justify-content: center;
    
    &:hover {
      background: #f3f4f6;
      color: #4b5563;
    }
    
    &:disabled {
      cursor: not-allowed;
      opacity: 0.5;
    }
  }
}

.content-body {
  flex: 1;
  padding-top: 24px;
  padding-bottom: 0;
  padding-left: 20px;
  padding-right: 20px;
  overflow-y: auto;
  
  .kb-form {
    max-width: 100%;
  }
}

.content-footer {
  padding: 12px 20px;
  border-top: 1px solid #f3f4f6;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  background: #fff;
}

.kb-visibility-form-item {
  margin-top: -6px;
  margin-bottom: 18px;
}

.kb-visibility-form-item .ant-form-item-control-input {
  min-height: auto;
}

.kb-permission-groups-form-item {
  margin-top: -6px;
}

.kb-form-help {
  color: #8c8c8c;
  font-size: 12px;
  margin-top: 4px;
}

.kb-visibility-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
}

.kb-visibility-inline-label {
  flex: 0 0 auto;
  padding: 0 !important;
  display: flex;
  align-items: center;
}

.kb-visibility-inline-label.ant-form-item-label {
  padding-bottom: 0 !important;
}

.kb-visibility-inline-label > label {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  margin: 0;
  padding-bottom: 0 !important;
}

.bi-visibility-segment {
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  flex-shrink: 0;
  margin-left: auto;
  position: relative;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 10px;
  background: #f5f5f5;
  isolation: isolate;
  overflow: hidden;
}

.bi-visibility-segment::before {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: calc(50% - 3px);
  height: calc(100% - 4px);
  border-radius: 8px;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.08), 0 6px 18px rgba(15, 23, 42, 0.06);
  transform: translateX(0);
  transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.28s ease, background 0.28s ease;
  z-index: 0;
}

.bi-visibility-segment[data-active='public']::before {
  transform: translateX(calc(100% + 2px));
}

.bi-visibility-segment.is-readonly {
  background: linear-gradient(135deg, #f4f6fb 0%, #eef2f8 100%);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.24);
}

.bi-visibility-segment.is-readonly::before {
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(243, 246, 251, 0.9));
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 4px 12px rgba(15, 23, 42, 0.05);
}

.bi-visibility-segment.is-readonly::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 10px;
  pointer-events: none;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.22), rgba(148, 163, 184, 0.12));
  z-index: 2;
}

.bi-visibility-segment-option {
  height: 28px;
  padding: 0 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #111827;
  font-size: 12px;
  font-weight: 500;
  line-height: 28px;
  cursor: pointer;
  position: relative;
  z-index: 1;
  transition: transform 0.28s cubic-bezier(0.22, 1, 0.36, 1), color 0.2s ease, opacity 0.2s ease;
}

.bi-visibility-segment-option:hover {
  color: #111827;
  transform: translateY(-0.5px);
}

.bi-visibility-segment-option.active {
  color: #111827;
  transform: translateY(-0.5px) scale(0.985);
}

.bi-visibility-segment-option:not(.active) {
  opacity: 0.82;
}

.bi-visibility-segment-option:active {
  transform: scale(0.97);
}

.bi-visibility-segment-option:disabled {
  cursor: not-allowed;
  color: #64748b;
  opacity: 0.82;
  transform: none;
}

.bi-visibility-segment.is-readonly .bi-visibility-segment-option.active {
  color: #334155;
  font-weight: 600;
  transform: none;
}

.bi-visibility-segment.is-readonly .bi-visibility-segment-option:not(.active) {
  color: #94a3b8;
  opacity: 1;
}

.bi-visibility-segment.is-readonly .bi-visibility-segment-option:hover {
  transform: none;
}

@media (max-width: 768px) {
  .kb-visibility-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .bi-visibility-segment {
    margin-left: 0;
  }
}

.empty-state-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
  min-height: 200px;
}

.empty-state {
  text-align: center;
  color: #9ca3af;
  
  p {
    margin-top: 16px;
    font-size: 14px;
    color: #6b7280;
  }
}

.custom-btn {
  min-width: 75px;
  border-radius: 10px;
  height: 32px;
  font-size: 13px;
  font-weight: 400;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  cursor: pointer;
  transition: all 0.3s;
  outline: none;
  border: none;
}

.cancel-btn {
  background-color: #f5f5f5;
  color: #1a1a1a !important;
  
  &:hover, &:focus {
    background-color: #e6e6e6;
    color: #1a1a1a !important;
  }
}

.confirm-btn {
  background: #1677ff;
  color: #ffffff !important;
  
  &:hover, &:focus {
    background-color: #4096ff;
    color: #ffffff !important;
  }
  
  &:disabled, &:disabled:hover {
    background-color: #d9d9d9 !important;
    cursor: not-allowed !important;
    color: rgba(0, 0, 0, 0.25) !important;
  }
}

.graph-config-container {
  padding: 0;
}

.section-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.section-info {
  margin-bottom: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
}

.section-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
}

.config-divider {
  height: 1px;
  background-color: #f3f4f6;
  margin: 16px 0 24px;
}

.section-control-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  
  .ant-select {
    flex: 1;
  }
}

.section-control-col {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.generate-tags-btn {
  height: 32px;
  padding: 0 12px;
  background-color: #f3f4f6;
  border: none;
  border-radius: 8px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  
  &:hover {
    background-color: #e5e7eb;
    color: #1f2937;
  }
  
  &:active {
    background-color: #d1d5db;
  }
}

.scrollable-tags-select {
  :deep(.ant-select-selector) {
    padding-bottom: 2px !important;
  }
  :deep(.ant-select-selection-overflow) {
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    overflow-y: hidden !important;
    scrollbar-width: thin;
    
    &::-webkit-scrollbar {
      height: 4px;
    }
    &::-webkit-scrollbar-thumb {
      background-color: #d9d9d9;
      border-radius: 4px;
    }
    &::-webkit-scrollbar-track {
      background-color: transparent;
    }
  }
  :deep(.ant-select-selection-item) {
    flex: 0 0 auto !important;
  }
  :deep(.ant-select-selection-search) {
    flex: 0 0 auto !important;
  }
}

.edit-kb-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

/* 上传模态窗密级选择样式 */
.upload-modal-classification {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  margin-top: 16px;
  margin-bottom: 0;
  border: 1px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  background: linear-gradient(180deg, #f8fafc 0%, #ffffff 100%);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.75);
}

.upload-modal-classification-meta {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.upload-modal-classification-label {
  font-size: 13px;
  font-weight: 500;
  line-height: 1.2;
  color: #475569;
  white-space: nowrap;
}

.upload-modal-classification-hint {
  font-size: 12px;
  line-height: 1.4;
  color: #94a3b8;
  font-weight: 400;
}

.upload-modal-classification-group {
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

.upload-modal-classification-indicator {
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

.upload-modal-classification-group.is-empty .upload-modal-classification-indicator {
  opacity: 0;
  transform: scale(0.9);
}

.upload-modal-classification-group.is-internal .upload-modal-classification-indicator {
  transform: translateX(calc(100% + 3px));
}

.upload-modal-classification-btn {
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

.upload-modal-classification-btn:hover {
  color: #334155;
}

.upload-modal-classification-btn.is-active {
  color: #2563eb;
  font-weight: 500;
  transform: scale(1.04);
}

.upload-modal-classification-btn:active {
  transform: scale(0.96);
}

/* 中文标题增强自定义圆形复选框 */
.upload-modal-zh-title-enhance {
  margin-top: 16px;
}

.zh-title-enhance-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  color: #475569;
  line-height: 1;
}

.zh-title-enhance-checkbox {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.zh-title-enhance-indicator {
  position: relative;
  flex-shrink: 0;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid #cbd5e1;
  background: #ffffff;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex;
  align-items: center;
  justify-content: center;
}

.zh-title-enhance-indicator::after {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: transparent;
  transition: background 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.zh-title-enhance-checkbox:checked + .zh-title-enhance-indicator {
  border-color: #2563eb;
  background: #eff6ff;
}

.zh-title-enhance-checkbox:checked + .zh-title-enhance-indicator::after {
  background: #2563eb;
}

.zh-title-enhance-label:hover .zh-title-enhance-indicator {
  border-color: #94a3b8;
}

.zh-title-enhance-label:hover .zh-title-enhance-checkbox:checked + .zh-title-enhance-indicator {
  border-color: #3b82f6;
}

.zh-title-enhance-text {
  white-space: nowrap;
}

/* 检索配置模态框样式 */
.retrieval-config-modal-body {
  padding: 0;
}

.retrieval-config-modal-desc {
  font-size: 13px;
  color: #64748b;
  margin: -8px 0 8px 0;
  line-height: 1.5;
}

.retrieval-config-modal-body .form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 24px;
  gap: 8px;
}
</style>

<style>
.edit-kb-modal .ant-modal-content {
  border-radius: 22px !important;
}

.retrieval-config-modal .ant-modal-content {
  border-radius: 22px !important;
}

.confirm-delete-modal .ant-modal-content {
  border-radius: 18px !important;
}

/* 覆盖确认删除模态框的按钮样式，使其与编辑模型一致 */
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
