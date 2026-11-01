<template>
  <div class="skills-config-panel">
    <div class="agent-model-section-header">
      <h3 class="skills-section-title">
        <span>技能配置</span>
        <span class="skills-enabled-count" v-if="!loading && skillOptions.length > 0">已开启 {{ enabledSkillsCount }} 个技能</span>
      </h3>
      <p>为 DeepAgent 选择最适合当前任务的技能能力</p>
    </div>
    <a-form layout="vertical" class="skills-config-form">
      <a-form-item>
        <div class="skills-config-shell">
          <div v-if="loading" class="skills-config-state">
            <span class="skills-state-symbol">···</span>
            <span class="skills-state-title">正在加载技能列表</span>
            <span class="skills-state-description">请稍候，系统正在准备可用能力</span>
          </div>
          <div v-else-if="skillOptions.length === 0" class="skills-config-state skills-empty-hero">
            <div class="skills-empty-hero-icon">✦</div>
            <div class="skills-empty-hero-body">
              <span class="skills-state-title">暂无可用技能</span>
              <span class="skills-state-description">先在技能设置页创建技能，再返回此处进行分配。</span>
            </div>
            <div class="skills-empty-hero-actions">
              <button type="button" class="skills-empty-action-btn" @click="goToCreateSkill">
                <PlusOutlined />
                创建技能
              </button>
            </div>
          </div>
          <template v-else>
            <div class="skills-toolbar">
              <div class="skills-search-box">
                <span class="skills-search-icon">⌕</span>
                <input
                  v-model="keyword"
                  class="skills-search-input"
                  type="text"
                  placeholder="搜索技能名称、命令或用途"
                >
              </div>
              <div class="skills-visibility-switch">
                <span class="skills-visibility-indicator" :style="visibilityIndicatorStyle"></span>
                <button
                  v-for="option in visibilityOptionMeta"
                  :key="option.key"
                  type="button"
                  class="skills-visibility-btn"
                  :class="{ active: visibilityFilter === option.key }"
                  @click="visibilityFilter = option.key"
                >
                  <span>{{ option.label }}</span>
                  <span class="skills-visibility-count">{{ option.count }}</span>
                </button>
              </div>
              <div class="skills-toolbar-actions">
                <button
                  type="button"
                  class="skills-toolbar-button"
                  :disabled="visibleSkills.length === 0 || isAllVisibleSelected"
                  @click="selectAllSkills"
                >
                  全选
                </button>
                <button
                  type="button"
                  class="skills-toolbar-button is-ghost"
                  :disabled="visibleSkills.length === 0 || !hasAnyVisibleSelected"
                  @click="clearAllSkills"
                >
                  取消全选
                </button>
              </div>
            </div>

            <a-checkbox-group
              :value="localSkills"
              class="skills-checkbox-group"
              @change="handleSkillsChange"
            >
              <div v-if="visibleSkills.length > 0" class="skills-scroll-area">
                <div class="skills-group-list">
                  <label
                    v-for="skill in visibleSkills"
                    :key="skill.key"
                    class="skills-card"
                    :class="{ active: localSkills.includes(skill.key) }"
                  >
                    <a-checkbox :value="skill.key" class="skills-card-checkbox">
                      <div class="skills-card-inner">
                        <div class="skills-card-top">
                          <div class="skills-card-media" :style="getSkillMeta(skill.key).accentStyle">
                            {{ formatSkillLabel(skill.name).charAt(0) }}
                          </div>
                          <div class="skills-card-head">
                            <div class="skills-card-title-row">
                              <span class="skills-card-title" :title="formatSkillLabel(skill.name)">{{ formatSkillLabel(skill.name) }}</span>
                              <span class="skills-card-badge" :class="{ 'is-private': skill.visibility === 'private' }">{{ skill.visibility === 'private' ? '个人' : '共享' }}</span>
                            </div>
                            <span class="skills-card-command" :title="skill.description || getSkillMeta(skill.key).description">
                              {{ skill.description || getSkillMeta(skill.key).description }}
                            </span>
                          </div>
                          <span class="skills-card-check"></span>
                        </div>
                      </div>
                    </a-checkbox>
                  </label>
                </div>
              </div>
              <div v-else class="skills-config-state is-empty">
                <div class="skills-empty-hero-icon is-search">⌕</div>
                <div class="skills-empty-hero-body">
                  <span class="skills-state-title">没有找到匹配技能</span>
                  <span class="skills-state-description">可尝试搜索 docx、pdf、browser、xlsx 等关键词。</span>
                </div>
                <div class="skills-empty-hero-actions">
                  <button type="button" class="skills-empty-action-btn" @click="goToCreateSkill">
                    创建新技能
                  </button>
                  <span class="skills-empty-hint">会自动打开创建弹窗</span>
                </div>
              </div>
            </a-checkbox-group>
          </template>
        </div>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { PlusOutlined } from '@ant-design/icons-vue';
import { listAgentSkills } from '@/services/aiAgent';

interface SkillMeta {
  icon: string;
  accentStyle: Record<string, string>;
  category: string;
  description: string;
  tags: string[];
}

interface SkillOption {
  key: string;
  name: string;
  description: string;
  visibility: 'public' | 'private';
  raw: unknown;
}

interface Props {
  skills: string[];
}

interface Emits {
  (e: 'update:skills', value: string[]): void;
  (e: 'close-agent-modal'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();
const router = useRouter();

const loading = ref(false);
const keyword = ref('');
const visibilityFilter = ref<'public' | 'private'>('public');
const skillOptions = ref<SkillOption[]>([]);
const localSkills = ref<string[]>(Array.isArray(props.skills) ? [...props.skills] : []);
const skillMetaMap: Record<string, SkillMeta> = {
  'agent-browser': {
    icon: '↗',
    accentStyle: {
      background: 'linear-gradient(135deg, rgba(59,130,246,0.12), rgba(14,165,233,0.28))',
      color: '#2563eb'
    },
    category: '网页',
    description: '适合网页检索、页面浏览与信息采集，补足实时上下文能力。',
    tags: ['检索', '浏览', '实时']
  },
  docx: {
    icon: 'W',
    accentStyle: {
      background: 'linear-gradient(135deg, rgba(37,99,235,0.14), rgba(96,165,250,0.26))',
      color: '#1d4ed8'
    },
    category: '文档',
    description: '用于生成、读取和整理 Word 文档，适合报告、方案与正式材料输出。',
    tags: ['Word', '报告', '排版']
  },
  pdf: {
    icon: 'P',
    accentStyle: {
      background: 'linear-gradient(135deg, rgba(239,68,68,0.14), rgba(248,113,113,0.26))',
      color: '#dc2626'
    },
    category: '文档',
    description: '适合处理 PDF 阅读、提取与内容转化，用于归档资料和文献场景。',
    tags: ['PDF', '提取', '归档']
  },
  pptx: {
    icon: 'T',
    accentStyle: {
      background: 'linear-gradient(135deg, rgba(249,115,22,0.14), rgba(251,146,60,0.3))',
      color: '#ea580c'
    },
    category: '演示',
    description: '适合创建与调整演示文稿，让汇报材料更适配展示与讲解场景。',
    tags: ['PPT', '演示', '汇报']
  },
  xlsx: {
    icon: 'X',
    accentStyle: {
      background: 'linear-gradient(135deg, rgba(16,185,129,0.15), rgba(52,211,153,0.3))',
      color: '#059669'
    },
    category: '数据',
    description: '适合表格生成、数据整理与结构化分析，用于报表与批量处理任务。',
    tags: ['表格', '数据', '分析']
  }
};

watch(
  () => props.skills,
  (newSkills) => {
    localSkills.value = Array.isArray(newSkills) ? [...newSkills] : [];
  },
  { deep: true }
);

const normalizeSkillOption = (skill: any): SkillOption | null => {
  if (!skill) return null;
  if (typeof skill === 'string') {
    return {
      key: skill,
      name: skill,
      description: skill,
      visibility: 'public',
      raw: skill
    };
  }

  const name = String(skill.name || skill.folderName || skill.uuid || skill.id || '').trim();
  if (!name) return null;
  return {
    key: String(skill.uuid || skill.id || name),
    name,
    description: String(skill.description || skill.folderName || '暂无描述'),
    visibility: (() => {
      const visibility = String(skill.visibility || '').toLowerCase();
      return visibility === 'project' || visibility === 'private' ? 'private' : 'public';
    })(),
    raw: skill
  };
};

const handleSkillsChange = (values: Array<string | number>) => {
  const normalized = values.map((value) => String(value));
  localSkills.value = normalized;
  emit('update:skills', normalized);
};

const updateSkills = (skills: string[]) => {
  localSkills.value = skills;
  emit('update:skills', skills);
};

const formatSkillLabel = (skill: string) => {
  if (skill.includes('-')) {
    return skill
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ');
  }

  if (skill === skill.toLowerCase()) {
    return skill.toUpperCase();
  }

  return skill;
};

const getSkillMeta = (skill: string): SkillMeta => {
  const normalized = typeof skill === 'string' ? skill : String(skill || '');
  const fallbackIcon = normalized.charAt(0).toUpperCase() || 'S';
  return skillMetaMap[normalized] || {
    icon: fallbackIcon,
    accentStyle: {
      background: 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(129,140,248,0.26))',
      color: '#4f46e5'
    },
    category: '扩展',
    description: '可扩展的辅助技能，适合补充专用流程或定制化能力链路。',
    tags: ['扩展', '灵活', '定制']
  };
};

const filteredSkillOptions = computed(() => {
  const query = keyword.value.trim().toLowerCase();
  const skills = [...skillOptions.value];

  if (!query) {
    return skills;
  }

  return skills.filter((skill) => {
    const meta = getSkillMeta(skill.key);
    const haystack = [
      skill.key,
      skill.name,
      formatSkillLabel(skill.name),
      skill.description,
      meta.category,
      meta.description,
      ...meta.tags
    ].join(' ').toLowerCase();

    return haystack.includes(query);
  });
});

const filteredGlobalSkills = computed(() =>
  filteredSkillOptions.value.filter((skill) => skill.visibility === 'public')
);

const filteredPrivateSkills = computed(() =>
  filteredSkillOptions.value.filter((skill) => skill.visibility === 'private')
);

const visibleSkills = computed(() => {
  if (visibilityFilter.value === 'public') {
    return filteredGlobalSkills.value;
  }
  return filteredPrivateSkills.value;
});

const visibilityOptionMeta = computed(() => {
  const globalCount = filteredGlobalSkills.value.length;
  const privateCount = filteredPrivateSkills.value.length;
  return [
    { key: 'public' as const, label: '公开', count: globalCount },
    { key: 'private' as const, label: '个人', count: privateCount }
  ];
});

const visibilityIndicatorStyle = computed(() => ({
  transform: `translateX(${visibilityFilter.value === 'private' ? 100 : 0}%)`
}));

const isAllVisibleSelected = computed(() => {
  if (visibleSkills.value.length === 0) return false;
  return visibleSkills.value.every((skill) => localSkills.value.includes(skill.key));
});

const enabledSkillsCount = computed(() => {
  return localSkills.value.length;
});

const hasAnyVisibleSelected = computed(() => {
  if (visibleSkills.value.length === 0) return false;
  return visibleSkills.value.some((skill) => localSkills.value.includes(skill.key));
});

const selectAllSkills = () => {
  const selected = new Set(localSkills.value);
  visibleSkills.value.forEach((skill) => selected.add(skill.key));
  updateSkills(Array.from(selected));
};

const clearAllSkills = () => {
  const visibleKeys = new Set(visibleSkills.value.map((skill) => skill.key));
  updateSkills(localSkills.value.filter((skill) => !visibleKeys.has(skill)));
};

const goToCreateSkill = async () => {
  emit('close-agent-modal');
  await nextTick();
  await router.push('/settings/rule-skill-settings?openCreateSkill=1');
};

const loadSkills = async () => {
  loading.value = true;
  try {
    const res = await listAgentSkills();
    const data = res?.data as any;
    const skills = Array.isArray(data?.[0]?.skills)
      ? data[0].skills
      : Array.isArray(data?.skills)
        ? data.skills
        : Array.isArray(data)
          ? data
          : [];
    skillOptions.value = skills
      .map(normalizeSkillOption)
      .filter((item: SkillOption | null): item is SkillOption => Boolean(item));
  } catch (error) {
    console.error('加载技能失败:', error);
    skillOptions.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  loadSkills();
});
</script>

<style scoped>
.skills-config-panel {
  width: 100%;
}

.skills-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.skills-enabled-count {
  display: inline-flex;
  align-items: center;
  padding: 1px 10px;
  font-size: 11px;
  font-weight: 500;
  line-height: 1;
  height: 20px;
  color: #2563eb;
  background: #eff6ff;
  border-radius: 10px;
}

.skills-config-form {
  width: 100%;
}

.skills-config-form :deep(.ant-form-item),
.skills-config-form :deep(.ant-form-item-control),
.skills-config-form :deep(.ant-form-item-control-input),
.skills-config-form :deep(.ant-form-item-control-input-content) {
  width: 100%;
}

.skills-config-shell {
  width: 100%;
  min-width: 0;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 100%;
}

.skills-config-state,
.skills-toolbar,
.skills-checkbox-group,
.skills-scroll-area {
  width: 100%;
}

.skills-config-state {
  box-sizing: border-box;
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.skills-config-state.is-empty {
  min-height: 300px;
}

.skills-scroll-area {
  width: 100%;
}

.skills-empty-hero {
  padding: 0 24px;
  gap: 18px;
  border: none;
  border-radius: 0;
  background: transparent;
}

.skills-empty-hero-icon {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #2563eb;
  background: #eaf2ff;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.9);
}

.skills-empty-hero-icon.is-search {
  color: #0f766e;
  background: #e6fffb;
}

.skills-empty-hero-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  max-width: 320px;
}

.skills-state-title {
  font-size: 16px;
  font-weight: 600;
  line-height: 1.5;
  color: #111827;
  letter-spacing: 0.01em;
}

.skills-state-description {
  font-size: 13px;
  line-height: 1.75;
  color: #6b7280;
  text-align: center;
}

.skills-empty-hero-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.skills-empty-action-btn {
  border: none;
  background: #f3f4f6;
  color: #374151;
  border-radius: 12px;
  height: 36px;
  padding: 0 18px;
  font-size: 13px;
  font-weight: 500;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}

.skills-empty-action-btn:hover {
  border-color: none;
  background: #e5e7eb;
}

.skills-empty-action-btn:active {
  transform: translateY(1px);
}

.skills-empty-action-btn:focus-visible {
  outline: 2px solid rgba(99, 102, 241, 0.35);
  outline-offset: 2px;
}

.skills-empty-hint {
  font-size: 12px;
  line-height: 1.4;
  color: #6b7280;
  text-align: center;
}
</style>
