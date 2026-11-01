<template>
  <div class="rule-skill-settings" :class="{ 'skills-only': !showRulesSection }">
    <div class="page-header">
      <div class="header-content">
        <h2>技能</h2>
        <p>管理技能列表</p>
      </div>
      <div class="header-metrics">
        <div v-if="showRulesSection" class="metric-card">
          <div class="metric-label">个人规则</div>
          <div class="metric-value">{{ personalRules.length }}</div>
        </div>
        <div v-if="showRulesSection" class="metric-card">
          <div class="metric-label">项目规则</div>
          <div class="metric-value">{{ projectRules.length }}</div>
        </div>
        <div class="metric-card highlight">
          <div class="metric-label">已启用技能</div>
          <div class="metric-value">{{ enabledSkillCount }}</div>
        </div>
      </div>
    </div>
    <div class="content-shell" :class="{ 'single-column': !showRulesSection }">
      <div v-if="showRulesSection" class="section-card rules-section-card">
        <div class="section-header">
          <div class="section-title-group">
            <h3>规则</h3>
            <p>个人与项目规则共同作用于对话过程，保证行为一致性</p>
          </div>
        </div>
        <div class="rules-stack">
          <div class="rule-panel">
            <div class="rule-panel-header">
              <div class="rule-title">
                <div class="rule-icon personal">
                  <UserOutlined />
                </div>
                <div>
                  <div class="rule-name">个人规则</div>
                  <div class="rule-subtitle">仅对当前账号生效</div>
                </div>
              </div>
              <button class="icon-btn">
                <ReloadOutlined />
              </button>
            </div>
            <div class="rule-desc-row">
              <div class="rule-desc">创建及管理用户自定义规则，会在聊天过程中遵循这些规则</div>
              <button class="action-btn primary small">
                <PlusOutlined />
                创建规则
              </button>
            </div>
            <div class="rule-panel-list">
              <div class="rule-empty">暂无规则，创建后会显示在这里</div>
            </div>
          </div>
          <div class="rule-panel">
            <div class="rule-panel-header">
              <div class="rule-title">
                <div class="rule-icon project">
                  <FileTextOutlined />
                </div>
                <div>
                  <div class="rule-name">项目规则</div>
                  <div class="rule-subtitle">当前项目专属策略</div>
                </div>
              </div>
              <button class="icon-btn">
                <ReloadOutlined />
              </button>
            </div>
            <div class="rule-desc-row">
              <div class="rule-desc">创建专用于此项目的规则，让协作更稳定、更可控</div>
              <button class="action-btn primary small">
                <PlusOutlined />
                创建规则
              </button>
            </div>
            <div class="rule-panel-list">
              <div class="rule-empty">暂无规则，创建后会显示在这里</div>
            </div>
          </div>
        </div>
        <div class="section-coming-soon-mask">
          <div class="section-coming-soon-content">
            <div class="section-coming-soon-title">- 功能开发中 -</div>
            <div class="section-coming-soon-desc">规则相关能力正在建设中，敬请期待</div>
          </div>
        </div>
      </div>

      <div class="section-card">
        <div class="section-header">
          <div class="section-title-group">
            <h3>技能</h3>
            <p>技能是根据场景触发、确保模型按指令执行的知识集。你可以通过对话的方式，让AI帮你创建技能。</p>
          </div>
          <div class="section-actions">
            <button class="action-btn secondary small" @click="openCreateSkillModal">
              <PlusOutlined />
              创建技能
            </button>
          </div>
        </div>
        <div class="skills-tips">
          <div class="tip-item">场景化触发</div>
          <div class="tip-item">指令一致性</div>
          <div class="tip-item">自动化协作</div>
        </div>
        <div class="skills-card">
          <div class="skills-switcher">
            <div class="permission-filter" role="group" aria-label="技能范围筛选">
              <span class="permission-filter-indicator" :style="skillTabIndicatorStyle"></span>
              <button
                type="button"
                class="permission-filter-btn"
                :class="{ active: activeTab === 'public' }"
                :aria-pressed="activeTab === 'public'"
                @click="activeTab = 'public'"
              >
                公开
              </button>
              <button
                type="button"
                class="permission-filter-btn"
                :class="{ active: activeTab === 'private' }"
                :aria-pressed="activeTab === 'private'"
                @click="activeTab = 'private'"
              >
                个人
              </button>
            </div>
          </div>
          <div v-if="skillsLoading" class="skill-state">技能列表加载中...</div>
          <div v-else-if="activeTab === 'public' && publicSkills.length === 0" class="skill-empty-center skill-panel">
            <div class="skill-empty-icon">
              <FileTextOutlined />
            </div>
            <div class="skill-empty-title">暂无公开共享技能</div>
            <div class="skill-empty-desc">你可以创建一个公开共享技能，让它在所有项目中都能复用。</div>
            <button class="action-btn secondary small skill-empty-action" @click="openCreateSkillModal">
              <PlusOutlined />
              创建技能
            </button>
          </div>
          <div v-else-if="activeTab === 'private' && privateSkills.length === 0" class="skill-empty-center skill-panel">
            <div class="skill-empty-icon project">
              <FileTextOutlined />
            </div>
            <div class="skill-empty-title">暂无个人使用技能</div>
            <div class="skill-empty-desc">你可以创建个人使用技能，让协作更聚焦、更高效。</div>
            <button class="action-btn secondary small skill-empty-action" @click="openCreateSkillModal">
              <PlusOutlined />
              创建技能
            </button>
          </div>
          <div
            v-else-if="activeTab === 'public'"
            class="skill-list skill-panel"
            :class="{ 'hide-scrollbar': publicSkillListHideScrollbar }"
            @scroll.passive="handleSkillListScroll('public')"
            @mouseenter="handleSkillListMouseEnter('public')"
            @mouseleave="handleSkillListMouseLeave('public')"
          >
            <div
              v-for="skill in publicSkills"
              :key="skill.key"
              class="skill-item"
              :class="{ 'skill-item-has-env': hasSkillAdditionalInfo(skill.additionalInfo) }"
            >
              <div class="skill-info">
                <div
                  class="skill-icon"
                  :style="{
                    backgroundColor: skill.color,
                    color: getReadableTextColor(skill.color)
                  }"
                >{{ skill.badge }}</div>
                <div class="skill-text">
                  <div class="skill-name-row">
                    <div class="skill-name">{{ skill.name }}</div>
                    <span
                      v-if="hasSkillAdditionalInfo(skill.additionalInfo)"
                      class="skill-env-badge"
                      :title="getAdditionalInfoTooltip(skill.additionalInfo)"
                    >
                      已配环境变量
                    </span>
                  </div>
                  <div class="skill-desc">{{ skill.description }}</div>
                </div>
              </div>
              <div class="skill-actions">
                <button
                  type="button"
                  class="skill-setting-btn"
                  :class="{ active: previewSkillKey === skill.key }"
                  title="详情"
                  @click.stop="handlePreviewSkill(skill)"
                >
                  <EyeOutlined class="skill-setting" />
                </button>
                <div class="skill-action-wrapper">
                  <button
                    type="button"
                    class="skill-setting-btn"
                    :class="{ active: skillActionMenuState?.key === skill.key }"
                    @click.stop="toggleSkillActionMenu($event, skill.key)"
                  >
                    <SettingOutlined class="skill-setting" />
                  </button>
                </div>
              </div>
              <teleport to="body">
                <div
                  v-if="skillActionMenuState?.key === skill.key"
                  class="skill-action-menu floating"
                  :style="{ top: `${skillActionMenuState.top}px`, left: `${skillActionMenuState.left}px` }"
                  @click.stop
                >
                  <button type="button" class="skill-action-menu-item" @click="handleEditSkill(skill)">
                    <EditOutlined class="menu-icon" />
                    <span>编辑技能</span>
                  </button>
                  <button type="button" class="skill-action-menu-item danger" @click="handleDeleteSkillConfirm(skill)">
                    <DeleteOutlined class="menu-icon" />
                    <span>删除技能</span>
                  </button>
                </div>
              </teleport>
            </div>
          </div>
          <div
            v-else
            class="skill-list skill-panel"
            :class="{ 'hide-scrollbar': privateSkillListHideScrollbar }"
            @scroll.passive="handleSkillListScroll('private')"
            @mouseenter="handleSkillListMouseEnter('private')"
            @mouseleave="handleSkillListMouseLeave('private')"
          >
            <div
              v-for="skill in privateSkills"
              :key="skill.key"
              class="skill-item"
              :class="{ 'skill-item-has-env': hasSkillAdditionalInfo(skill.additionalInfo) }"
            >
              <div class="skill-info">
                <div
                  class="skill-icon"
                  :style="{
                    backgroundColor: skill.color,
                    color: getReadableTextColor(skill.color)
                  }"
                >{{ skill.badge }}</div>
                <div class="skill-text">
                  <div class="skill-name-row">
                    <div class="skill-name">{{ skill.name }}</div>
                    <span
                      v-if="hasSkillAdditionalInfo(skill.additionalInfo)"
                      class="skill-env-badge"
                      :title="getAdditionalInfoTooltip(skill.additionalInfo)"
                    >
                      已配环境变量
                    </span>
                  </div>
                  <div class="skill-desc">{{ skill.description }}</div>
                </div>
              </div>
              <div class="skill-actions">
                <button
                  type="button"
                  class="skill-setting-btn"
                  :class="{ active: previewSkillKey === skill.key }"
                  title="详情"
                  @click.stop="handlePreviewSkill(skill)"
                >
                  <EyeOutlined class="skill-setting" />
                </button>
                <div class="skill-action-wrapper">
                  <button
                    type="button"
                    class="skill-setting-btn"
                    :class="{ active: skillActionMenuState?.key === skill.key }"
                    @click.stop="toggleSkillActionMenu($event, skill.key)"
                  >
                    <SettingOutlined class="skill-setting" />
                  </button>
                </div>
              </div>
              <teleport to="body">
                <div
                  v-if="skillActionMenuState?.key === skill.key"
                  class="skill-action-menu floating"
                  :style="{ top: `${skillActionMenuState.top}px`, left: `${skillActionMenuState.left}px` }"
                  @click.stop
                >
                  <button type="button" class="skill-action-menu-item" @click="handleEditSkill(skill)">
                    <EditOutlined class="menu-icon" />
                    <span>编辑技能</span>
                  </button>
                  <button type="button" class="skill-action-menu-item danger" @click="handleDeleteSkillConfirm(skill)">
                    <DeleteOutlined class="menu-icon" />
                    <span>删除技能</span>
                  </button>
                </div>
              </teleport>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="previewSkillKey" class="section-card skill-preview-panel">
      <div class="preview-header">
        <div class="preview-title-group">
          <img :src="MarkdownSvg" alt="SKILL.md" class="preview-title-icon" />
          <div class="preview-title-text">
            <div class="preview-title">{{ previewSkillName || '技能详情' }}</div>
            <div class="preview-subtitle">SKILL.md 预览</div>
          </div>
        </div>
        <button type="button" class="skill-setting-btn preview-close-btn" title="关闭预览" @click="closeSkillPreview">
          <CloseOutlined class="skill-setting" />
        </button>
      </div>
      <div class="preview-body">
        <div v-if="previewLoading" class="preview-state">
          <LoadingOutlined />
          <span>技能详情加载中...</span>
        </div>
        <div v-else-if="previewError" class="preview-state error">{{ previewError }}</div>
        <div v-else-if="!previewContent" class="preview-state">该技能暂无可预览的 Markdown 内容</div>
        <MarkdownRenderer
          v-else
          :content="previewContent"
          role="system"
          disable-artifacts
          class="preview-markdown"
        />
      </div>
    </div>

    <div v-else class="skill-preview-placeholder">
      <img :src="MarkdownSvg" alt="SKILL.md" class="placeholder-icon" />
      <div class="placeholder-title">技能详情预览</div>
      <div class="placeholder-desc">点击左侧技能的“详情”按钮，即可在此查看对应的 SKILL.md 内容</div>
    </div>

    <a-modal
      v-model:open="createSkillModalVisible"
      :title="skillModalMode === 'edit' ? '编辑技能' : '创建技能'"
      @ok="handleSkillModalOk"
      @cancel="onCreateSkillModalCancel"
      centered
      :width="550"
      :confirmLoading="creatingSkill"
      :maskClosable="!creatingSkill"
      :keyboard="!creatingSkill"
      :closable="!creatingSkill"
      :cancelButtonProps="{ disabled: creatingSkill }"
      okText="确认"
      cancelText="取消"
      class="create-skill-modal upload-modal"
    >
      <div v-if="skillModalMode === 'create'" class="elegant-upload-wrapper">
        <div
          class="elegant-drop-area"
          :class="{
            'is-active': isCreateSkillDragging,
            'is-disabled': creatingSkill,
            'has-content': createSkillFileList.length > 0
          }"
          @click="triggerCreateSkillFileSelect"
          @dragenter.prevent.stop="handleCreateSkillDragEnter"
          @dragover.prevent.stop="handleCreateSkillDragOver"
          @dragleave.prevent.stop="handleCreateSkillDragLeave"
          @drop.prevent.stop="handleCreateSkillDrop"
        >
          <input
            ref="createSkillFileInputRef"
            class="elegant-file-input"
            type="file"
            accept=".md,.zip,.skill"
            :disabled="creatingSkill"
            @change="handleCreateSkillFileInputChange"
          />
          <div class="elegant-upload-content">
            <div class="elegant-icon-ring">
              <LoadingOutlined v-if="creatingSkill" class="modern-icon spinning" />
              <CloudUploadOutlined v-else />
            </div>
            <div class="elegant-text-group">
              <h4 class="elegant-main-text">{{ createSkillUploadText }}</h4>
              <p class="elegant-sub-text">{{ createSkillUploadHint }}</p>
            </div>
          </div>
          <div v-if="createSkillFileList.length > 0" class="innovative-file-list" @click.stop>
            <div v-for="file in createSkillFileList" :key="String(file.uid || file.name)" class="innovative-file-row">
              <div class="innovative-file-icon">
                <img
                  v-if="getFileIconSrc(file.name)"
                  :src="getFileIconSrc(file.name)"
                  :alt="`${file.name} icon`"
                  class="innovative-file-icon-img"
                />
                <FileOutlined v-else />
              </div>
              <div class="innovative-file-info">
                <span class="innovative-file-name" :title="file.name">{{ file.name }}</span>
                <div class="innovative-file-meta">
                  <span>{{ formatUploadFileSize(file.size) }}</span>
                </div>
              </div>
              <button
                type="button"
                class="innovative-file-action"
                :disabled="creatingSkill"
                @click.stop.prevent="removeCreateSkillFile(file)"
                title="移除"
              >
                <CloseOutlined />
              </button>
            </div>
          </div>
        </div>
      </div>

      <a-form layout="vertical" class="upload-modal-form" :style="{ marginTop: skillModalMode === 'create' ? '12px' : '0' }">
        <transition name="bi-visibility-fade" appear>
          <a-form-item
            required
            class="bi-visibility-form-item"
          >
            <div class="bi-visibility-row">
              <div class="ant-form-item-label bi-visibility-inline-label">
                <label class="ant-form-item-required" title="可见范围">可见范围</label>
              </div>
              <div
                class="bi-visibility-segment"
                :class="{ 'is-readonly': !canEditVisibility }"
                :data-active="createSkillForm.type"
                role="tablist"
                aria-label="可见范围"
              >
                <button
                  type="button"
                  class="bi-visibility-segment-option"
                  :class="{ active: createSkillForm.type === 'private' }"
                  :aria-pressed="createSkillForm.type === 'private'"
                  :disabled="!canEditVisibility || creatingSkill"
                  @click="updateSkillVisibility('private')"
                >
                  个人使用
                </button>
                <button
                  type="button"
                  class="bi-visibility-segment-option"
                  :class="{ active: createSkillForm.type === 'public' }"
                  :aria-pressed="createSkillForm.type === 'public'"
                  :disabled="!canEditVisibility || creatingSkill"
                  @click="updateSkillVisibility('public')"
                >
                  公开共享
                </button>
              </div>
            </div>
          </a-form-item>
        </transition>

        <transition name="bi-visibility-fade" appear>
          <a-form-item
            v-if="canEditVisibility && createSkillForm.type === 'public'"
            required
            class="bi-permission-groups-form-item"
            label="可访问用户组"
          >
            <a-select
              mode="multiple"
              v-model:value="createSkillForm.permissionGroupIds"
              :options="permissionGroupOptions"
              :loading="permissionGroupsLoading"
              :disabled="permissionGroupsLoading || creatingSkill"
              :virtual="false"
              popupClassName="user-group-select-dropdown"
              max-tag-count="responsive"
              placeholder="请选择用户组"
              style="width: 100%;"
              @change="handleSkillPermissionGroupsChange"
            />
          </a-form-item>
        </transition>

        <a-form-item label="技能名称" required>
          <a-input
            v-model:value="createSkillForm.name"
            :maxlength="50"
            :disabled="creatingSkill || skillModalMode === 'edit'"
            placeholder="为这个 Skill 起一个简短的名称，例如：codemap"
          />
        </a-form-item>
        <a-form-item label="描述" required>
          <a-textarea
            v-model:value="createSkillForm.description"
            :maxlength="200"
            :auto-size="{ minRows: 3, maxRows: 5 }"
            :disabled="creatingSkill"
            placeholder="简要描述这个 Skill 应该在什么情况下被触发，例如：分析代码库结构、依赖关系和变更"
          />
        </a-form-item>
        <a-form-item
          class="skill-additional-info-form-item"
        >
          <div class="skill-additional-info-card" :class="{ expanded: additionalInfoExpanded }">
            <button
              type="button"
              class="skill-additional-info-toggle"
              :disabled="creatingSkill"
              @click="toggleAdditionalInfoExpanded"
            >
              <span class="skill-additional-info-toggle-title">高级配置</span>
              <RightOutlined class="skill-additional-info-chevron" :class="{ expanded: additionalInfoExpanded }" />
            </button>

            <transition name="bi-visibility-fade" appear>
              <div v-if="additionalInfoExpanded" class="skill-additional-info-panel">
                <div class="skill-additional-info-panel-head">
                  <span class="skill-additional-info-tip">环境变量</span>
                  <button
                    type="button"
                    class="skill-additional-info-add-btn"
                    :disabled="creatingSkill"
                    @click="addAdditionalInfoEntry"
                  >
                    <PlusOutlined />
                    添加变量
                  </button>
                </div>

                <div class="skill-additional-info-grid-head">
                  <span>变量名</span>
                  <span>变量值</span>
                </div>

                <div class="skill-additional-info-scroll">
                  <div class="skill-additional-info-list">
                    <div
                      v-for="(entry, index) in createSkillForm.additionalInfoEntries"
                      :key="`skill-additional-info-${index}`"
                      class="skill-additional-info-row"
                    >
                      <a-input
                        v-model:value="entry.key"
                        :maxlength="50"
                        :disabled="creatingSkill"
                        placeholder="例如 url"
                      />
                      <a-input
                        v-model:value="entry.value"
                        :maxlength="500"
                        :disabled="creatingSkill"
                        placeholder="例如 http://localhost:5173/reports"
                      />
                      <button
                        type="button"
                        class="skill-additional-info-remove-btn"
                        :disabled="creatingSkill || createSkillForm.additionalInfoEntries.length === 1"
                        title="删除变量"
                        @click="removeAdditionalInfoEntry(index)"
                      >
                        <CloseOutlined style="font-size: 8px;" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </transition>
          </div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import type { UploadFile } from 'ant-design-vue';
import '@/assets/styles/knowledge-base.css';
import '@/assets/styles/add-agent-modal.css';
import '@/assets/styles/user-group-select.css';
import '@/assets/styles/markdown.css';
import NotificationService from '@/utils/NotificationService';
import { getFileIconSrc } from '@/utils/fileIcon';
import MarkdownSvg from '@/assets/image/svg/Markdown.svg';
import { deleteAgentSkill, listAgentSkills, readAgentSkillMd, updateAgentSkill, uploadAgentSkill, type SkillInfo } from '@/services/aiAgent';
import { listAiEntityAssignedGroups, listAiUserGroups, updateAiPermission } from '@/services/aiPermission';
import { CloudUploadOutlined, ReloadOutlined, PlusOutlined, SettingOutlined, UserOutlined, FileTextOutlined, FileOutlined, CloseOutlined, LoadingOutlined, EditOutlined, DeleteOutlined, RightOutlined, EyeOutlined } from '@ant-design/icons-vue';
import { Modal } from 'ant-design-vue';

const MarkdownRenderer = defineAsyncComponent(() => import('@/components/common/MarkdownRenderer.vue'));

defineOptions({
  name: 'RuleSkillSettingsView'
});

const route = useRoute();
const activeTab = ref('public');

// 规则相关后端能力尚未开发完成，暂时隐藏规则模块（保留 UI 代码，后续可直接开启）
const showRulesSection = ref(false);

const SKILL_ENTITY_TYPE = 5;

const getCurrentUsername = () => {
  try {
    const raw = localStorage.getItem('user-profile');
    if (!raw) return '';
    const profile = JSON.parse(raw);
    return String(profile?.username || '').trim();
  } catch (_) {
    return '';
  }
};
const isCurrentUserAdmin = computed(() => getCurrentUsername().toLowerCase() === 'admin');
const canEditVisibility = computed(() => isCurrentUserAdmin.value);

const permissionGroupsLoading = ref(false);
const availablePermissionGroups = ref<any[]>([]);
const permissionGroupsLoaded = ref(false);
const permissionGroupOptions = computed(() =>
  availablePermissionGroups.value.map((group) => ({
    label: group.name,
    value: group.uuid
  }))
);

const ensurePermissionGroupsLoaded = async () => {
  if (!canEditVisibility.value || permissionGroupsLoaded.value || permissionGroupsLoading.value) return;
  permissionGroupsLoading.value = true;
  try {
    availablePermissionGroups.value = await listAiUserGroups();
    permissionGroupsLoaded.value = true;
  } catch {
    availablePermissionGroups.value = [];
  } finally {
    permissionGroupsLoading.value = false;
  }
};

const personalRules = ref([]);
const projectRules = ref([]);

interface SkillItem {
  key: string;
  uuid?: string;
  id?: number;
  name: string;
  description: string;
  enabled: boolean;
  badge: string;
  color: string;
  type: 'public' | 'private';
  createBy?: string;
  createTime?: string;
  folderName?: string;
  additionalInfo?: unknown;
}

interface SkillAdditionalInfoEntry {
  key: string;
  value: string;
}

const getSkillVisibility = (skill: SkillInfo): 'public' | 'private' => {
  const visibility = String(skill.visibility || '').toLowerCase();
  if (visibility === 'project' || visibility === 'private') return 'private';
  return 'public';
};

const getSkillDescription = (skill: SkillInfo) => {
  if (typeof skill.description === 'string' && skill.description.trim()) return skill.description.trim();
  if (typeof skill.folderName === 'string' && skill.folderName.trim()) return skill.folderName.trim();
  if (typeof skill.additionalInfo === 'string' && skill.additionalInfo.trim()) return skill.additionalInfo.trim();
  return '暂无描述';
};

const getSkillName = (skill: SkillInfo) => {
  if (typeof skill.name === 'string' && skill.name.trim()) return skill.name.trim();
  if (typeof skill.folderName === 'string' && skill.folderName.trim()) return skill.folderName.trim();
  return '未知技能';
};

const getSkillBadge = (name: string) => {
  const trimmed = name.trim();
  return trimmed ? trimmed.charAt(0).toUpperCase() : 'S';
};

const skillsLoading = ref(false);
const skillList = ref<SkillItem[]>([]);
const createSkillModalVisible = ref(false);
const creatingSkill = ref(false);
const editingSkillKey = ref<string | null>(null);
const editingOriginalPermissionGroupIds = ref<string[]>([]);
const skillActionMenuState = ref<{ key: string; top: number; left: number } | null>(null);
const shouldAutoOpenCreateSkill = String(route.query?.openCreateSkill || '') === '1';

// 技能 MD 预览面板状态
const previewSkillKey = ref<string | null>(null);
const previewSkillName = ref('');
const previewLoading = ref(false);
const previewContent = ref('');
const previewError = ref('');

const skillModalMode = computed(() => editingSkillKey.value ? 'edit' : 'create');

const createSkillFileList = ref<UploadFile[]>([]);
const createSkillFileInputRef = ref<HTMLInputElement | null>(null);
const isCreateSkillDragging = ref(false);
const skillPermissionGroupDraftIds = ref<string[]>([]);
const additionalInfoExpanded = ref(false);
const createEmptyAdditionalInfoEntry = (): SkillAdditionalInfoEntry => ({
  key: '',
  value: ''
});
const normalizeAdditionalInfoRecord = (value: unknown): Record<string, string> => {
  if (!value) return {};
  
  // 如果是字符串，尝试解析为 JSON
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      return normalizeAdditionalInfoRecord(parsed);
    } catch {
      return {};
    }
  }
  
  // 如果是对象，提取键值对
  if (typeof value === 'object' && !Array.isArray(value)) {
    return Object.entries(value as Record<string, unknown>).reduce<Record<string, string>>((acc, [key, entryValue]) => {
      const normalizedKey = String(key || '').trim();
      const normalizedValue = entryValue == null ? '' : String(entryValue).trim();
      if (!normalizedKey || !normalizedValue) return acc;
      acc[normalizedKey] = normalizedValue;
      return acc;
    }, {});
  }
  
  return {};
};
const convertAdditionalInfoToEntries = (value: unknown): SkillAdditionalInfoEntry[] => {
  const entries = Object.entries(normalizeAdditionalInfoRecord(value)).map(([key, entryValue]) => ({
    key,
    value: entryValue
  }));
  return entries.length > 0 ? entries : [createEmptyAdditionalInfoEntry()];
};
const getAdditionalInfoKeys = (additionalInfo: unknown): string[] => {
  const record = normalizeAdditionalInfoRecord(additionalInfo);
  return Object.keys(record);
};
const hasSkillAdditionalInfo = (additionalInfo: unknown) => getAdditionalInfoKeys(additionalInfo).length > 0;
const getAdditionalInfoTooltip = (additionalInfo: unknown) => {
  const keys = getAdditionalInfoKeys(additionalInfo);
  return keys.length > 0 ? `已配置环境变量：${keys.join('、')}` : '';
};
const createSkillForm = ref({
  type: 'private' as 'public' | 'private',
  uuid: '',
  name: '',
  description: '',
  permissionGroupIds: [] as string[],
  additionalInfoEntries: [createEmptyAdditionalInfoEntry()] as SkillAdditionalInfoEntry[]
});
const publicSkillListHideScrollbar = ref(true);
const updateSkillVisibility = (visibility: 'public' | 'private') => {
  if (!canEditVisibility.value || creatingSkill.value) return;
  if (createSkillForm.value.type === 'public') {
    skillPermissionGroupDraftIds.value = normalizePermissionGroupIds(createSkillForm.value.permissionGroupIds);
  }
  createSkillForm.value.type = visibility;
  if (visibility !== 'public') {
    createSkillForm.value.permissionGroupIds = [];
  } else {
    createSkillForm.value.permissionGroupIds = skillPermissionGroupDraftIds.value.slice();
    ensurePermissionGroupsLoaded();
  }
};

watch(() => createSkillForm.value.type, (newVal) => {
  if (newVal === 'public' && canEditVisibility.value) {
    skillPermissionGroupDraftIds.value = normalizePermissionGroupIds(createSkillForm.value.permissionGroupIds);
    ensurePermissionGroupsLoaded();
  }
});
const privateSkillListHideScrollbar = ref(true);
let publicSkillScrollbarHideTimer: number | null = null;
let privateSkillScrollbarHideTimer: number | null = null;

const normalizeApiCode = (result: any) => Number(result?.code ?? 0) === 0;

const normalizePermissionGroupIds = (groupIds: string[] = []) =>
  Array.from(
    new Set(
      groupIds.filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );

const handleSkillPermissionGroupsChange = (values: string[]) => {
  const normalizedValues = normalizePermissionGroupIds(values);
  createSkillForm.value.permissionGroupIds = normalizedValues;
  skillPermissionGroupDraftIds.value = normalizedValues.slice();
};

const getSelectedPermissionGroupIds = () => normalizePermissionGroupIds(createSkillForm.value.permissionGroupIds || []);
const toggleAdditionalInfoExpanded = () => {
  additionalInfoExpanded.value = !additionalInfoExpanded.value;
};
const addAdditionalInfoEntry = () => {
  additionalInfoExpanded.value = true;
  createSkillForm.value.additionalInfoEntries.push(createEmptyAdditionalInfoEntry());
};
const removeAdditionalInfoEntry = (index: number) => {
  if (createSkillForm.value.additionalInfoEntries.length === 1) {
    createSkillForm.value.additionalInfoEntries = [createEmptyAdditionalInfoEntry()];
    return;
  }
  createSkillForm.value.additionalInfoEntries.splice(index, 1);
};
const buildAdditionalInfoPayload = () =>
  createSkillForm.value.additionalInfoEntries.reduce<Record<string, string>>((acc, entry) => {
    const key = entry.key.trim();
    const value = entry.value.trim();
    if (!key || !value) return acc;
    acc[key] = value;
    return acc;
  }, {});
const validateAdditionalInfoEntries = () => {
  const usedKeys = new Set<string>();
  for (const entry of createSkillForm.value.additionalInfoEntries) {
    const key = entry.key.trim();
    const value = entry.value.trim();
    if (!key && !value) {
      continue;
    }
    if (!key) {
      additionalInfoExpanded.value = true;
      NotificationService.error('请输入环境变量名称');
      return false;
    }
    if (!value) {
      additionalInfoExpanded.value = true;
      NotificationService.error(`请输入环境变量 ${key} 的值`);
      return false;
    }
    if (usedKeys.has(key)) {
      additionalInfoExpanded.value = true;
      NotificationService.error(`环境变量 ${key} 重复，请调整后重试`);
      return false;
    }
    usedKeys.add(key);
  }
  return true;
};

const syncSkillPermissionGroups = async (
  skillUuid: string,
  targetGroupIds: string[],
  existingGroupIdsSource: string[] = []
) => {
  const targetGroupIdsNormalized = normalizePermissionGroupIds(targetGroupIds);
  const existingGroupIds = normalizePermissionGroupIds(existingGroupIdsSource);
  const nextPermissionByGroupId = new Map<string, 1 | 2>();

  existingGroupIds.forEach((groupId) => {
    nextPermissionByGroupId.set(groupId, targetGroupIdsNormalized.includes(groupId) ? 1 : 2);
  });
  targetGroupIdsNormalized.forEach((groupId) => {
    nextPermissionByGroupId.set(groupId, 1);
  });

  for (const [groupId, permission] of nextPermissionByGroupId.entries()) {
    const result = await updateAiPermission({
      group_id: groupId,
      list: [
        {
          entity_id: skillUuid,
          entity_type: SKILL_ENTITY_TYPE,
          permission
        }
      ]
    });
    if (!normalizeApiCode(result)) {
      throw new Error(result?.message || `用户组权限更新失败: ${groupId}`);
    }
  }

  return normalizePermissionGroupIds(
    await listAiEntityAssignedGroups(skillUuid, SKILL_ENTITY_TYPE)
  );
};

const buildSkillItem = (skill: SkillInfo): SkillItem => {
  const name = getSkillName(skill);
  const type = getSkillVisibility(skill);
  return {
    key: skill.uuid || String(skill.id || name),
    uuid: skill.uuid,
    id: skill.id,
    name,
    description: getSkillDescription(skill),
    enabled: true,
    badge: getSkillBadge(name),
    color: type === 'public' ? '#60a5fa' : '#34d399',
    type,
    createBy: skill.createBy,
    createTime: skill.createTime,
    folderName: skill.folderName,
    additionalInfo: skill.additionalInfo ?? skill.additional_info
  };
};

const getReadableTextColor = (backgroundColor?: string) => {
  if (!backgroundColor) return '#111827';
  const color = backgroundColor.replace('#', '');
  const expanded = color.length === 3 ? color.split('').map(ch => ch + ch).join('') : color;
  if (expanded.length !== 6) return '#111827';
  const r = parseInt(expanded.slice(0, 2), 16);
  const g = parseInt(expanded.slice(2, 4), 16);
  const b = parseInt(expanded.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.7 ? '#111827' : '#ffffff';
};

const publicSkills = computed(() => skillList.value.filter(skill => skill.type === 'public'));
const privateSkills = computed(() => skillList.value.filter(skill => skill.type === 'private'));
const skillTabIndicatorStyle = computed(() => ({
  transform: `translateX(${activeTab.value === 'private' ? 100 : 0}%)`
}));

const enabledSkillCount = computed(() => {
  return skillList.value.filter(skill => skill.enabled).length;
});

const formatUploadFileSize = (size?: number) => {
  const normalized = Number(size || 0);
  if (!normalized) return '--';
  if (normalized < 1024) return `${normalized}B`;
  if (normalized < 1024 * 1024) return `${(normalized / 1024).toFixed(1)}KB`;
  return `${(normalized / 1024 / 1024).toFixed(1)}MB`;
};

const validateCreateSkillFile = (file: File) => {
  const lowerName = (file.name || '').toLowerCase();
  const allowedExts = ['.md', '.zip', '.skill'];
  const matched = allowedExts.some(ext => lowerName.endsWith(ext));
  if (!matched) {
    NotificationService.error('仅支持 .md、.zip、.skill 格式的技能文件');
    return false;
  }
  return true;
};

const addCreateSkillFiles = (nativeFiles: File[]) => {
  if (nativeFiles.length === 0) return;
  const first = nativeFiles[0];
  if (!validateCreateSkillFile(first)) return;
  createSkillFileList.value = [{
    uid: `${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
    name: first.name,
    size: first.size,
    type: first.type,
    originFileObj: first as any
  }];
};

const triggerCreateSkillFileSelect = () => {
  if (creatingSkill.value) return;
  createSkillFileInputRef.value?.click();
};

const getCreateSkillFileKey = (file: UploadFile) => String(file.uid || file.name || '');

const removeCreateSkillFile = (target: UploadFile) => {
  const key = getCreateSkillFileKey(target);
  createSkillFileList.value = createSkillFileList.value.filter(file => getCreateSkillFileKey(file) !== key);
};

const handleCreateSkillFileInputChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files || []);
  addCreateSkillFiles(files);
  target.value = '';
};

const handleCreateSkillDragEnter = (event: DragEvent) => {
  event.stopPropagation();
  if (creatingSkill.value) return;
  if (!event.dataTransfer?.types.includes('Files')) return;
  isCreateSkillDragging.value = true;
};

const handleCreateSkillDragOver = (event: DragEvent) => {
  event.stopPropagation();
  if (creatingSkill.value) return;
  isCreateSkillDragging.value = true;
};

const handleCreateSkillDragLeave = (event: DragEvent) => {
  event.stopPropagation();
  isCreateSkillDragging.value = false;
};

const handleCreateSkillDrop = (event: DragEvent) => {
  event.stopPropagation();
  if (creatingSkill.value) return;
  isCreateSkillDragging.value = false;
  const files = Array.from(event.dataTransfer?.files || []);
  addCreateSkillFiles(files);
};

const createSkillUploadText = computed(() => {
  if (createSkillFileList.value.length === 0) return '上传进行智能解析';
  return `已选择 ${createSkillFileList.value[0].name}`;
});

const createSkillUploadHint = computed(() => {
  if (createSkillFileList.value.length === 0) {
    return '包含 SKILL.md 文件的 .zip 或 .skill 文件，SKILL.md 位于根目录，包含 YAML 格式的技能名称和描述。';
  }
  return '支持重新点击或拖拽替换当前文件。';
});

const openCreateSkillModal = () => {
  editingSkillKey.value = null;
  editingOriginalPermissionGroupIds.value = [];
  skillPermissionGroupDraftIds.value = [];
  additionalInfoExpanded.value = false;
  createSkillModalVisible.value = true;
  createSkillForm.value = {
    type: 'private',
    uuid: '',
    name: '',
    description: '',
    permissionGroupIds: [],
    additionalInfoEntries: [createEmptyAdditionalInfoEntry()]
  };
  createSkillFileList.value = [];
};

const resetCreateSkillForm = () => {
  editingSkillKey.value = null;
  editingOriginalPermissionGroupIds.value = [];
  skillPermissionGroupDraftIds.value = [];
  additionalInfoExpanded.value = false;
  createSkillForm.value = {
    type: 'private',
    uuid: '',
    name: '',
    description: '',
    permissionGroupIds: [],
    additionalInfoEntries: [createEmptyAdditionalInfoEntry()]
  };
  createSkillFileList.value = [];
  isCreateSkillDragging.value = false;
  if (createSkillFileInputRef.value) {
    createSkillFileInputRef.value.value = '';
  }
};

const onCreateSkillModalCancel = () => {
  if (creatingSkill.value) return;
  createSkillModalVisible.value = false;
  resetCreateSkillForm();
};

const extractSkillsFromResponse = (response: any): SkillInfo[] => {
  const candidates = [
    response?.data?.[0]?.skills,
    response?.data?.skills,
    response?.data,
    response?.skills,
    response?.data?.list,
    response?.data?.items
  ];

  for (const candidate of candidates) {
    if (Array.isArray(candidate)) {
      return candidate;
    }
  }

  return [];
};

const extractCreatedSkillUuid = (response: any) => {
  const candidates = [
    response?.data?.uuid,
    response?.uuid,
    response?.data?.skills?.[0]?.uuid,
    response?.skills?.[0]?.uuid,
    response?.data?.[0]?.uuid,
    response?.[0]?.uuid
  ];

  for (const candidate of candidates) {
    if (typeof candidate === 'string' && candidate.trim()) {
      return candidate.trim();
    }
  }

  return '';
};

const loadSkills = async () => {
  skillsLoading.value = true;
  try {
    const response = await listAgentSkills();
    if (!normalizeApiCode(response)) {
      throw new Error(response?.message || '获取技能列表失败');
    }
    const remoteSkills = extractSkillsFromResponse(response);
    skillList.value = remoteSkills
      .filter((skill: SkillInfo) => skill && typeof skill === 'object')
      .map(buildSkillItem)
      .sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
  } catch (error: any) {
    console.error('加载技能列表失败:', error);
    NotificationService.error(typeof error?.message === 'string' ? error.message : '获取技能列表失败，请重试');
    skillList.value = [];
  } finally {
    skillsLoading.value = false;
  }
};

const handleSkillModalOk = async () => {
  if (skillModalMode.value === 'edit') {
    await handleSaveEditSkill();
  } else {
    await handleCreateSkill();
  }
};

const handleSaveEditSkill = async () => {
  if (!createSkillForm.value.name.trim()) {
    NotificationService.error('请输入技能名称');
    return;
  }
  if (!createSkillForm.value.description.trim()) {
    NotificationService.error('请输入技能描述');
    return;
  }
  if (!validateAdditionalInfoEntries()) {
    return;
  }

  const visibility = canEditVisibility.value ? createSkillForm.value.type : 'private';

  creatingSkill.value = true;
  try {
    const result = await updateAgentSkill({
      uuid: createSkillForm.value.uuid,
      description: createSkillForm.value.description.trim(),
      visibility: visibility,
      additional_info: buildAdditionalInfoPayload()
    });
    if (!normalizeApiCode(result)) {
      throw new Error(result?.message || '技能更新失败');
    }

    if (canEditVisibility.value && createSkillForm.value.uuid) {
      editingOriginalPermissionGroupIds.value = await syncSkillPermissionGroups(
        createSkillForm.value.uuid,
        visibility === 'public' ? getSelectedPermissionGroupIds() : [],
        editingOriginalPermissionGroupIds.value
      );
      createSkillForm.value.permissionGroupIds = editingOriginalPermissionGroupIds.value.slice();
      skillPermissionGroupDraftIds.value = editingOriginalPermissionGroupIds.value.slice();
    }

    NotificationService.success('技能更新成功');
    createSkillModalVisible.value = false;
    resetCreateSkillForm();
    await loadSkills();
  } catch (error: any) {
    NotificationService.error(typeof error?.message === 'string' ? error.message : '技能更新失败，请重试');
  } finally {
    creatingSkill.value = false;
  }
};

const handleCreateSkill = async () => {
  if (createSkillFileList.value.length === 0) {
    NotificationService.error('请先上传技能文件');
    return;
  }
  if (!createSkillForm.value.name.trim()) {
    NotificationService.error('请输入技能名称');
    return;
  }
  if (!createSkillForm.value.description.trim()) {
    NotificationService.error('请输入技能描述');
    return;
  }
  if (!validateAdditionalInfoEntries()) {
    return;
  }

  const file = createSkillFileList.value[0]?.originFileObj as File | undefined;
  if (!file) {
    NotificationService.error('技能文件无效，请重新上传');
    return;
  }

  const visibility = canEditVisibility.value ? createSkillForm.value.type : 'private';

  creatingSkill.value = true;
  try {
    const result = await uploadAgentSkill({
      name: createSkillForm.value.name.trim(),
      description: createSkillForm.value.description.trim(),
      visibility: visibility,
      file,
      additional_info: buildAdditionalInfoPayload()
    });
    if (!normalizeApiCode(result)) {
      throw new Error(result?.message || '创建技能失败');
    }

    const createdUuid = extractCreatedSkillUuid(result);
    if (canEditVisibility.value && visibility === 'public' && !createdUuid) {
      throw new Error('技能创建成功，但未获取到 skill uuid，无法更新用户组权限');
    }
    if (canEditVisibility.value && visibility === 'public' && createdUuid) {
      const assignedGroupIds = await syncSkillPermissionGroups(createdUuid, getSelectedPermissionGroupIds(), []);
      createSkillForm.value.permissionGroupIds = assignedGroupIds.slice();
      editingOriginalPermissionGroupIds.value = assignedGroupIds.slice();
      skillPermissionGroupDraftIds.value = assignedGroupIds.slice();
    }

    NotificationService.success('技能创建成功');
    createSkillModalVisible.value = false;
    resetCreateSkillForm();
    await loadSkills();
  } catch (error: any) {
    NotificationService.error(typeof error?.message === 'string' ? error.message : '创建技能失败，请重试');
  } finally {
    creatingSkill.value = false;
  }
};

const showSkillScrollbarDuringScroll = (type: 'public' | 'private') => {
  if (type === 'public') {
    publicSkillListHideScrollbar.value = false;
    if (publicSkillScrollbarHideTimer) {
      clearTimeout(publicSkillScrollbarHideTimer);
      publicSkillScrollbarHideTimer = null;
    }
    publicSkillScrollbarHideTimer = window.setTimeout(() => {
      publicSkillListHideScrollbar.value = true;
      publicSkillScrollbarHideTimer = null;
    }, 600);
    return;
  }

  privateSkillListHideScrollbar.value = false;
  if (privateSkillScrollbarHideTimer) {
    clearTimeout(privateSkillScrollbarHideTimer);
    privateSkillScrollbarHideTimer = null;
  }
  privateSkillScrollbarHideTimer = window.setTimeout(() => {
    privateSkillListHideScrollbar.value = true;
    privateSkillScrollbarHideTimer = null;
  }, 600);
};

const handleSkillListScroll = (type: 'public' | 'private') => {
  showSkillScrollbarDuringScroll(type);
};

const handleSkillListMouseEnter = (type: 'public' | 'private') => {
  if (type === 'public') {
    publicSkillListHideScrollbar.value = false;
    if (publicSkillScrollbarHideTimer) {
      clearTimeout(publicSkillScrollbarHideTimer);
      publicSkillScrollbarHideTimer = null;
    }
    return;
  }

  privateSkillListHideScrollbar.value = false;
  if (privateSkillScrollbarHideTimer) {
    clearTimeout(privateSkillScrollbarHideTimer);
    privateSkillScrollbarHideTimer = null;
  }
};

const handleSkillListMouseLeave = (type: 'public' | 'private') => {
  showSkillScrollbarDuringScroll(type);
};

const closeSkillActionMenu = () => {
  skillActionMenuState.value = null;
};

const openSkillActionMenu = (event: MouseEvent, skillKey: string) => {
  const button = event.currentTarget as HTMLElement | null;
  if (!button) return;
  const rect = button.getBoundingClientRect();
  const gap = 8;
  const viewportPadding = 12;
  const left = Math.min(rect.right, window.innerWidth - viewportPadding);

  skillActionMenuState.value = {
    key: skillKey,
    top: rect.bottom + gap,
    left
  };
};

const toggleSkillActionMenu = (event: MouseEvent, skillKey: string) => {
  if (skillActionMenuState.value?.key === skillKey) {
    closeSkillActionMenu();
    return;
  }
  openSkillActionMenu(event, skillKey);
};

const handleEditSkill = async (skill: SkillItem) => {
  closeSkillActionMenu();
  editingSkillKey.value = skill.key;
  editingOriginalPermissionGroupIds.value = [];
  skillPermissionGroupDraftIds.value = [];
  const hasAdditionalInfo = getAdditionalInfoKeys(skill.additionalInfo).length > 0;
  createSkillForm.value = {
    type: skill.type,
    uuid: skill.uuid || '',
    name: skill.name,
    description: skill.description,
    permissionGroupIds: [],
    additionalInfoEntries: convertAdditionalInfoToEntries(skill.additionalInfo)
  };
  createSkillFileList.value = [];
  additionalInfoExpanded.value = hasAdditionalInfo;
  createSkillModalVisible.value = true;
  if (!canEditVisibility.value || skill.type !== 'public' || !skill.uuid) {
    return;
  }
  try {
    await ensurePermissionGroupsLoaded();
    const assignedGroups = await listAiEntityAssignedGroups(skill.uuid, SKILL_ENTITY_TYPE);
    const normalizedAssignedGroups = normalizePermissionGroupIds(assignedGroups);
    createSkillForm.value.permissionGroupIds = normalizedAssignedGroups.slice();
    skillPermissionGroupDraftIds.value = normalizedAssignedGroups.slice();
    editingOriginalPermissionGroupIds.value = normalizedAssignedGroups.slice();
  } catch (error: any) {
    NotificationService.error(typeof error?.message === 'string' ? error.message : '加载可访问用户组失败');
  }
};

const handleDeleteSkillConfirm = (skill: SkillItem) => {
  closeSkillActionMenu();
  Modal.confirm({
    title: '确认删除技能',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `确定要删除“${skill.name}”吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: () => handleDeleteSkill(skill)
  });
};

const handleDeleteSkill = async (skill: SkillItem) => {
  try {
    const result = await deleteAgentSkill({ uuid: skill.uuid || '' });
    if (!normalizeApiCode(result)) {
      throw new Error(result?.message || '技能删除失败');
    }
    NotificationService.success(`技能"${skill.name}"已删除`);
    if (previewSkillKey.value === skill.key) {
      closeSkillPreview();
    }
    await loadSkills();
  } catch (error: any) {
    NotificationService.error(typeof error?.message === 'string' ? error.message : '技能删除失败，请重试');
  }
};

const handlePreviewSkill = async (skill: SkillItem) => {
  if (!skill.uuid) {
    NotificationService.error('该技能缺少唯一标识，无法预览');
    return;
  }
  previewSkillKey.value = skill.key;
  previewSkillName.value = skill.name;
  previewLoading.value = true;
  previewContent.value = '';
  previewError.value = '';
  try {
    const result = await readAgentSkillMd(skill.uuid);
    if (previewSkillKey.value !== skill.key) return;
    if (!normalizeApiCode(result)) {
      throw new Error(result?.message || '技能详情加载失败');
    }
    previewContent.value = result?.data?.content || '';
  } catch (error: any) {
    if (previewSkillKey.value !== skill.key) return;
    previewError.value = typeof error?.message === 'string' ? error.message : '技能详情加载失败，请重试';
    NotificationService.error(previewError.value);
  } finally {
    if (previewSkillKey.value === skill.key) {
      previewLoading.value = false;
    }
  }
};

const closeSkillPreview = () => {
  previewSkillKey.value = null;
  previewSkillName.value = '';
  previewLoading.value = false;
  previewContent.value = '';
  previewError.value = '';
};


const handleGlobalClick = () => {
  closeSkillActionMenu();
};

onMounted(() => {
  window.addEventListener('click', handleGlobalClick);
  window.addEventListener('resize', handleGlobalClick);
  window.addEventListener('scroll', handleGlobalClick, true);
  loadSkills();

  if (shouldAutoOpenCreateSkill) {
    openCreateSkillModal();
  }
});

onBeforeUnmount(() => {
  window.removeEventListener('click', handleGlobalClick);
  window.removeEventListener('resize', handleGlobalClick);
  window.removeEventListener('scroll', handleGlobalClick, true);
  if (publicSkillScrollbarHideTimer) {
    clearTimeout(publicSkillScrollbarHideTimer);
    publicSkillScrollbarHideTimer = null;
  }
  if (privateSkillScrollbarHideTimer) {
    clearTimeout(privateSkillScrollbarHideTimer);
    privateSkillScrollbarHideTimer = null;
  }
});
</script>

<style scoped>
.rule-skill-settings {
  height: 100%;
  width: 100%;
  overflow: hidden;
  padding: 24px 30px;
  background-color: #ffffff;
  /* 内容区始终左右平分：左列技能设置、右列预览区，保证左列宽度不随预览开关变化 */
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  grid-template-rows: auto minmax(0, 1fr);
  column-gap: 20px;
}

.rule-skill-settings > .page-header {
  grid-column: 1;
  grid-row: 1;
}

.rule-skill-settings > .content-shell {
  grid-column: 1;
  grid-row: 2;
}

.rule-skill-settings > .skill-preview-panel,
.rule-skill-settings > .skill-preview-placeholder {
  grid-column: 2;
  grid-row: 1 / span 2;
  min-height: 0;
  /* 与 .page-header 的 margin-top 保持一致，使右列顶部与左侧指标卡顶部齐平 */
  margin-top: -7px;
}

.page-header {
  margin-bottom: 18px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-top: -7px;
}

.page-header h2 {
  margin: 0 0 7px 0;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1d;
}

.page-header p {
  margin: 0;
  font-size: 13px;
  color: #8c8c8c;
}

.content-shell {
  max-width: 100%;
  margin: 0;
  width: 100%;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 20px;
  flex: 1;
  min-height: 0;
  align-content: stretch;
  grid-auto-rows: 1fr;
}

.content-shell.single-column {
  grid-template-columns: minmax(0, 1fr);
}

/* 只显示技能时限定内容宽度，避免卡片行在宽屏上被无限拉长；
   页首与内容一起靠左对齐，右侧留白 */
.rule-skill-settings.skills-only .page-header,
.rule-skill-settings.skills-only .content-shell {
  width: 100%;
  max-width: 920px;
  margin-left: 0;
  margin-right: auto;
}

.skill-preview-panel {
  min-height: 0;
  overflow: hidden;
  /* 分隔线改由 header 的 border-bottom 承担，取消默认间距 */
  gap: 0;
}

/* 右侧预览区空态：虚线描边占位提示 */
.skill-preview-placeholder {
  border: 1px dashed #d1d5db;
  border-radius: 16px;
  background: #fafafa;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  text-align: center;
}

.placeholder-icon {
  width: 40px;
  height: 40px;
  /* 空态下降低存在感 */
  opacity: 0.75;
}

.placeholder-title {
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
}

.placeholder-desc {
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.7;
  max-width: 260px;
}

.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  /* 与 .preview-body 的左右内边距对齐，分隔线放在 header 底部 */
  padding: 0 12px 14px;
  border-bottom: 1px solid #f0f0f0;
}

.preview-title-group {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.preview-title-icon {
  width: 26px;
  height: 26px;
  flex-shrink: 0;
}

.preview-title-text {
  min-width: 0;
}

.preview-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.preview-subtitle {
  font-size: 12px;
  color: #8c8c8c;
}

.preview-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  /* 左右留出内边距，避免 Markdown 内容贴边 */
  padding: 14px 12px 18px;
  /* 滚动区向右扩展 8px（与滚动条宽度一致），使滚动条落在内容区之外的留白处，不占用内容宽度 */
  margin-right: -8px;
  scrollbar-width: thin;
  scrollbar-color: #d1d5db transparent;
}

.preview-body::-webkit-scrollbar {
  width: 8px;
}

.preview-body::-webkit-scrollbar-track {
  background: transparent;
}

.preview-body::-webkit-scrollbar-thumb {
  background: #d1d5db;
  border-radius: 4px;
}

.preview-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 48px 0;
  color: #8c8c8c;
  font-size: 13px;
}

.preview-state.error {
  color: #dc2626;
}

.header-metrics {
  display: grid;
  grid-auto-flow: column;
  gap: 12px;
}

.metric-card {
  min-width: 108px;
  padding: 10px 14px;
  border-radius: 12px;
  border: 1px solid #e5e7eb;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.metric-card.highlight {
  background: linear-gradient(135deg, #eff6ff 0%, #f8fafc 100%);
  border-color: #bfdbfe;
}

.metric-label {
  font-size: 12px;
  color: #6b7280;
}

.metric-value {
  font-size: 13px;
  font-weight: 600;
  color: #111827;
}

.section-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 20px 22px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.06);
  min-height: 100%;
}

.rules-section-card {
  position: relative;
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.section-title-group h3 {
  margin: 0 0 6px 0;
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.section-title-group p {
  margin: 0;
  font-size: 12px;
  color: #6b7280;
  max-width: 720px;
  line-height: 1.6;
}

.section-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rules-stack {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.rule-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-bottom: 20px;
  border-bottom: 1px solid #e5e7eb;
}

.rule-panel:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.rule-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rule-title {
  display: flex;
  align-items: center;
  gap: 12px;
}

.rule-subtitle {
  font-size: 12px;
  margin-top: 6px;
  color: #9ca3af;
}

.rule-icon {
  width: 42px;
  height: 42px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b5563;
  background: #e5e7eb;
}

.rule-icon.personal {
  color: #16a34a;
  background: #e6fbe7;
}

.rule-icon.project {
  color: #2563eb;
  background: #e8f1ff;
}

.rule-name {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
}

.rule-desc {
  font-size: 12px;
  color: #8c8c8c;
  line-height: 1.5;
  max-width: 520px;
}

.rule-desc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.rule-panel-list {
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  background: #f9fafb;
  min-height: 72px;
  display: flex;
  align-items: center;
}

.rule-empty {
  font-size: 12px;
  color: #9ca3af;
}

.section-coming-soon-mask {
  position: absolute;
  inset: 0;
  z-index: 5;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(3px);
}

.section-coming-soon-content {
  padding: 18px 24px;
  border-radius: 16px;
  text-align: center;
}

.section-coming-soon-title {
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.section-coming-soon-desc {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}
.icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 10px;
  border: none;
  background: #f3f4f6;
  color: #6b7280;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.icon-btn:hover {
  background: #e5e7eb;
  color: #4b5563;
}

.action-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 12px;
  font-weight: 500;
  font-size: 14px;
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
  background: transparent;
}

.action-btn.primary {
  background: #3b82f6;
  color: #ffffff;
}

.action-btn.primary:hover {
  background: #2563eb;
}

.action-btn.secondary {
  background: #f3f4f6;
  color: #374151;
}

.action-btn.secondary:hover {
  background: #e5e7eb;
}

.action-btn.small {
  padding: 8px 16px;
  font-size: 13px;
  border-radius: 9px;
}

.skills-tips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tip-item {
  padding: 6px 12px;
  border-radius: 999px;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 12px;
}

.skills-card {
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 10px 12px 16px;
  background: linear-gradient(180deg, #fcfdff 0%, #ffffff 100%);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}

.skills-switcher {
  display: flex;
  justify-content: center;
}

.permission-filter {
  display: inline-flex;
  align-items: center;
  background: #f3f4f6;
  border-radius: 12px;
  padding: 2px;
  border: 1px solid #eceff3;
  position: relative;
  overflow: hidden;
}

.permission-filter-btn {
  position: relative;
  z-index: 1;
  flex: 1 1 0;
  border: none;
  background: transparent;
  color: #6b7280;
  font-size: 12px;
  line-height: 1;
  padding: 7px 12px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.permission-filter-indicator {
  position: absolute;
  top: 2px;
  left: 2px;
  width: calc((100% - 4px) / 2);
  height: calc(100% - 4px);
  border-radius: 10px;
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.12);
  transition: transform 0.34s cubic-bezier(0.22, 1, 0.36, 1);
  will-change: transform;
}

.permission-filter-btn:hover {
  color: #374151;
  transform: translateY(-0.5px);
}

.permission-filter-btn.active {
  color: #1677ff;
  font-weight: 500;
}

.skill-panel {
  flex: 1;
  min-height: 0;
  background: #ffffff;
  border-radius: 10px;
}

.skill-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 2px 4px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  scrollbar-gutter: stable both-edges;
  scrollbar-width: thin;
}

.skill-list::-webkit-scrollbar {
  width: 5px;
  height: 5px;
}

.skill-list::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0.15);
  border-radius: 3px;
  transition: background-color 0.2s ease;
}

.skill-list::-webkit-scrollbar-track {
  background-color: transparent;
}

.skill-list.hide-scrollbar::-webkit-scrollbar-thumb {
  background-color: rgba(0, 0, 0, 0);
  transition: background-color 0.2s ease;
}

.skill-list.hide-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: rgba(0, 0, 0, 0.15);
}

.skill-list.hide-scrollbar::-webkit-scrollbar-thumb:active {
  background-color: rgba(0, 0, 0, 0.25);
}

.skill-list.hide-scrollbar {
  scrollbar-color: rgba(0, 0, 0, 0) transparent;
  transition: scrollbar-color 0.2s ease;
}

.skill-list:not(.hide-scrollbar) {
  scrollbar-color: rgba(0, 0, 0, 0.15) transparent;
  transition: scrollbar-color 0.2s ease;
}

.skill-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-radius: 16px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
}

.skill-item-has-env {
  background: linear-gradient(180deg, #f9fafb 0%, #f5fbf7 100%);
  border-color: #d6efe0;
}

.skill-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.skill-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  color: #1f1f1f;
  font-size: 13px;
}

.skill-text {
  min-width: 0;
  flex: 1;
}

.skill-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.skill-name {
  font-size: 13px;
  font-weight: 600;
  color: #1f1f1f;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.skill-env-badge {
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: 999px;
  background: #ecfdf5;
  border: 1px solid #ccefdc;
  color: #047857;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
  letter-spacing: 0.02em;
  flex-shrink: 0;
}

.skill-desc {
  font-size: 12px;
  color: #8c8c8c;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 460px;
}

.skill-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  color: #8c8c8c;
}

.skill-action-wrapper {
  position: relative;
}

.skill-setting-btn {
  width: 30px;
  height: 30px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #8c8c8c;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.skill-setting-btn:hover,
.skill-setting-btn.active {
  background: #f3f4f6;
  color: #374151;
}

.skill-setting {
  font-size: 15px;
}

/* 预览关闭按钮：更小的圆形按钮与图标。 */
.preview-close-btn {
  width: 28px;
  height: 28px;
  border-radius: 50%;
}

.preview-close-btn .skill-setting {
  font-size: 12px;
}

.skill-action-menu {
  position: absolute;
  right: 0;
  top: calc(100% + 8px);
  min-width: 125px;
  padding: 6px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.skill-action-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}

.skill-action-menu-item:hover {
  background: #f3f4f6;
}

.skill-action-menu-item.danger {
  color: #ef4444;
}

.skill-action-menu-item.danger:hover {
  background: #fef2f2;
}

.skill-state {
  font-size: 13px;
  color: #9ca3af;
  padding: 24px 10px;
  text-align: center;
}

.skill-empty-center {
  width: 100%;
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}

.skill-empty-icon {
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  color: #2563eb;
  background: #eaf2ff;
}

.skill-empty-icon.project {
  color: #16a34a;
  background: #e9f9ef;
}

.skill-empty-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.skill-empty-desc {
  max-width: 325px;
  font-size: 12px;
  line-height: 1.6;
  color: #6b7280;
}

.skill-empty-action {
  margin-top: 4px;
}

.skill-action-menu.floating {
  position: fixed;
  width: 110px;
  min-width: 110px;
  max-width: 110px;
  padding: 6px;
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  box-shadow: 0 12px 28px rgba(0, 0, 0, 0.12);
  z-index: 20;
  display: flex;
  flex-direction: column;
  gap: 4px;
  transform: translateX(-100%);
}

.skill-action-menu-item {
  width: 100%;
  border: none;
  background: transparent;
  border-radius: 8px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  color: #374151;
  cursor: pointer;
}

.skill-action-menu-item:hover {
  background: #f3f4f6;
}

.skill-action-menu-item.danger {
  color: #ef4444;
}

.skill-action-menu-item.danger:hover {
  background: #fef2f2;
}

.skill-action-menu .menu-icon {
  font-size: 14px;
}

.skill-additional-info-card {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  background: #ffffff;
  overflow: hidden;
  transition: border-color 0.2s ease;
  margin-top: -10px;
  margin-bottom: -10px;
}

.skill-additional-info-card.expanded {
  border-color: #d1d5db;
}

.skill-additional-info-toggle {
  width: 100%;
  padding: 12px 14px;
  border: none;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
  cursor: pointer;
}

.skill-additional-info-toggle:disabled {
  cursor: not-allowed;
}

.skill-additional-info-toggle-title {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  line-height: 1;
}

.skill-additional-info-chevron {
  font-size: 12px;
  color: #9ca3af;
  transition: transform 0.2s ease, color 0.2s ease;
}

.skill-additional-info-chevron.expanded {
  transform: rotate(90deg);
  color: #6b7280;
}

.skill-additional-info-panel {
  border-top: 1px solid #f3f4f6;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fafafa;
}

.skill-additional-info-panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: -10px;
  margin-top: -5px;
}

.skill-additional-info-tip {
  font-size: 13px;
  line-height: 1.5;
  color: #3b3b3b;
  font-weight: 500;
}

.skill-additional-info-add-btn,
.skill-additional-info-remove-btn {
  border: none;
  cursor: pointer;
  transition: all 0.2s ease;
}

.skill-additional-info-add-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border-radius: 8px;
  background: #f3f4f6;
  color: #374151;
  font-size: 12px;
  white-space: nowrap;
}

.skill-additional-info-add-btn:hover:not(:disabled) {
  background: #e5e7eb;
}

.skill-additional-info-grid-head {
  display: grid;
  grid-template-columns: minmax(120px, 180px) minmax(0, 1fr) 36px;
  gap: 10px;
  align-items: center;
  font-size: 11px;
  color: #9ca3af;
  padding: 0 2px;
  margin-bottom: -10px;
}

.skill-additional-info-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skill-additional-info-scroll {
  max-height: 120px;
  overflow-y: auto;
  padding: 2px 2px 2px 0;
  border-radius: 8px;
}

.skill-additional-info-scroll::-webkit-scrollbar {
  width: 6px;
}

.skill-additional-info-scroll::-webkit-scrollbar-thumb {
  background: rgba(156, 163, 175, 0.55);
  border-radius: 999px;
}

.skill-additional-info-scroll::-webkit-scrollbar-track {
  background: transparent;
}

.skill-additional-info-row {
  display: grid;
  grid-template-columns: minmax(120px, 180px) minmax(0, 1fr) 36px;
  gap: 10px;
  align-items: center;
  padding: 0;
  border-radius: 0;
  border: none;
}

.skill-additional-info-remove-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  padding: 0;
  border-radius: 22px;
  background: #ededed;
  color: #9ca3af;
}

.skill-additional-info-remove-btn:hover:not(:disabled) {
  background: #e4e4e4;
  color: #4b5563;
}

.skill-additional-info-add-btn:disabled,
.skill-additional-info-remove-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

@media (max-width: 960px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .header-metrics {
    width: 100%;
    grid-auto-flow: row;
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .content-shell {
    grid-template-columns: 1fr;
  }

  .rule-skill-settings {
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .rule-skill-settings > .skill-preview-panel,
  .rule-skill-settings > .skill-preview-placeholder {
    min-height: 420px;
    margin-top: 0;
  }

  .rules-stack {
    gap: 16px;
  }

  .skill-additional-info-panel-head {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .rule-skill-settings {
    padding: 20px 18px;
  }

  .header-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .section-card {
    padding: 16px;
  }

  .skills-card {
    padding: 10px 10px 14px;
  }

  .permission-filter-btn {
    min-width: 52px;
    padding: 7px 11px;
    font-size: 11px;
  }

  .skill-additional-info-toggle {
    padding: 14px;
  }

  .skill-additional-info-grid-head {
    display: none;
  }

  .skill-additional-info-scroll {
    max-height: 116px;
  }

  .skill-additional-info-row {
    grid-template-columns: 1fr;
  }

  .skill-additional-info-remove-btn {
    width: 100%;
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
