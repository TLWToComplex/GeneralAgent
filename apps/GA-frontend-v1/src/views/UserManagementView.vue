<template>
  <div class="user-management">
    <div v-if="!isCurrentUserAdmin" class="no-permission-card">
      <h2>无访问权限</h2>
      <p>仅管理员账号可访问用户管理页面。</p>
    </div>

    <template v-else>
      <div class="page-header">
        <div class="header-main">
          <h1 class="page-title">用户管理</h1>
          <p class="page-description">按标准后台设置页风格统一管理用户信息与用户组关系。</p>
        </div>
        <div class="header-side">
          <div class="header-metrics">
            <div class="metric-card">
              <div class="metric-label">用户总数</div>
              <div class="metric-value">{{ users.length }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">已分组用户</div>
              <div class="metric-value">{{ groupedUserCount }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">管理员用户</div>
              <div class="metric-value">{{ adminUserCount }}</div>
            </div>
            <div class="metric-card highlight">
              <div class="metric-label">用户组总数</div>
              <div class="metric-value">{{ groupOptions.length }}</div>
            </div>
            <div class="metric-card default-group-metric">
              <div class="metric-label">默认用户组</div>
              <div class="metric-value metric-value-default" :title="defaultGroupName">{{ defaultGroupName }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="content-shell">
        <div class="filters-bar">
          <div class="filters-left">
            <div class="native-search-wrapper">
              <span class="native-search-icon">⌕</span>
              <input
                v-model="filters.keyword"
                type="text"
                class="native-input"
                placeholder="搜索用户名 / 姓名 / 邮箱"
              />
            </div>
            <div ref="groupSelectRef" class="native-select-dropdown">
              <button
                type="button"
                class="native-select-trigger"
                :class="{ open: groupDropdownOpen }"
                @click="toggleGroupDropdown"
              >
                <span class="select-trigger-text">{{ currentGroupLabel }}</span>
                <span class="select-trigger-arrow" />
              </button>
              <div v-if="groupDropdownOpen" class="native-select-menu">
                <button type="button" class="native-select-option" @click="selectGroupOption(undefined)">
                  全部用户组
                </button>
                <button
                  v-for="option in groupSelectOptions"
                  :key="option.value"
                  type="button"
                  class="native-select-option"
                  :class="{ active: filters.groupId === option.value }"
                  @click="selectGroupOption(option.value)"
                >
                  {{ option.label }}
                </button>
              </div>
            </div>
            <button type="button" class="native-btn primary" @click="applyFilters">查询</button>
            <button type="button" class="native-btn secondary" @click="resetFilters">重置</button>
          </div>
          <div class="filters-right">
            <button type="button" class="native-btn secondary icon-btn" :disabled="loading" @click="openGroupManagerModal">
              <TeamOutlined />
              用户组管理
            </button>
            <button type="button" class="native-btn secondary" :disabled="loading" @click="loadData">
              刷新
            </button>
          </div>
        </div>

        <div ref="tableSectionRef" class="table-section">
            <a-table
              class="user-table"
              :loading="loading"
              :columns="userTableColumns"
              :data-source="filteredUsers"
              :pagination="tablePagination"
              :scroll="tableScrollConfig"
              :sticky="true"
              row-key="user_id"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'username'">
                  <div class="user-cell">
                    <div class="user-avatar">{{ getInitial(record.username) }}</div>
                    <span class="user-name">{{ record.username }}</span>
                  </div>
                </template>

                <template v-else-if="column.key === 'realname'">
                  <span class="table-text">{{ record.realname || '未设置姓名' }}</span>
                </template>

                <template v-else-if="column.key === 'role'">
                  <a-tag v-if="isUserAdmin(record.username)" color="blue" class="role-tag">管理员</a-tag>
                  <span v-else class="table-text muted-text">普通用户</span>
                </template>

                <template v-else-if="column.key === 'email'">
                  <span class="table-text muted-text">{{ record.email || '未设置邮箱' }}</span>
                </template>

                <template v-else-if="column.key === 'is_locked'">
                  <a-tag v-if="record.is_locked" color="red" class="status-tag locked">已锁定</a-tag>
                  <a-tag v-else color="green" class="status-tag">正常</a-tag>
                </template>

                <template v-else-if="column.key === 'groups'">
                  <div v-if="record.groups?.length" class="group-tag-list centered">
                    <a-tag v-for="group in record.groups" :key="group.group_id" color="blue">
                      {{ group.group_name }}
                    </a-tag>
                  </div>
                  <span v-else class="table-text muted-text">未分配</span>
                </template>

                <template v-else-if="column.key === 'groupCount'">
                  <span class="table-text">{{ record.groups?.length || 0 }}</span>
                </template>

                <template v-else-if="column.key === 'action'">
                  <div class="row-actions">
                    <a-tooltip :title="record.is_locked ? '解除锁定' : '当前账号未锁定'">
                      <span>
                        <a-button
                          type="text"
                          class="action-icon-btn"
                          :disabled="!record.is_locked"
                          @click="handleUnlockUser(record)"
                        >
                          <template #icon><UnlockOutlined /></template>
                        </a-button>
                      </span>
                    </a-tooltip>
                    <a-button type="text" class="action-icon-btn" @click="openUserEditModal(record)">
                      <template #icon><EditOutlined /></template>
                    </a-button>
                    <a-button
                      type="text"
                      danger
                      class="action-icon-btn danger"
                      :disabled="isUserAdmin(record.username)"
                      @click="handleDeleteUser(record)"
                    >
                      <template #icon><DeleteOutlined /></template>
                    </a-button>
                  </div>
                </template>
              </template>
            </a-table>
          </div>
      </div>
    </template>

    <a-modal
      v-model:open="userEditVisible"
      title="编辑用户"
      :width="520"
      :z-index="1000"
      wrap-class-name="user-edit-modal"
      :footer="null"
      centered
      @cancel="userEditVisible = false"
    >
      <div class="user-edit-modal-content">
        <a-form layout="vertical" class="user-edit-form">
          <div class="modal-form-grid">
            <a-form-item label="用户名">
              <a-input v-model:value="userForm.username" placeholder="请输入用户名" />
            </a-form-item>
            <a-form-item label="姓名">
              <a-input v-model:value="userForm.realname" placeholder="请输入姓名" />
            </a-form-item>
          </div>
          <a-form-item label="邮箱">
            <a-input v-model:value="userForm.email" placeholder="请输入邮箱" />
          </a-form-item>
          <a-form-item label="所属用户组">
            <a-select
              v-model:value="userForm.groupIds"
              mode="multiple"
              allow-clear
              show-search
              :options="groupSelectOptions"
              option-filter-prop="label"
              :virtual="false"
              popupClassName="user-group-select-dropdown"
              max-tag-count="responsive"
              placeholder="请选择用户组"
              style="width: 100%;"
            />
          </a-form-item>
          <a-form-item label="重置密码">
            <a-input-password v-model:value="userForm.password" placeholder="留空则不修改密码" />
          </a-form-item>
        </a-form>
        <div class="form-actions">
          <a-button class="custom-btn cancel-btn" @click="userEditVisible = false">取消</a-button>
          <a-button class="custom-btn confirm-btn" :loading="userSubmitting" @click="submitUserEdit">保存</a-button>
        </div>
      </div>
    </a-modal>

    <a-modal
      v-model:open="groupManagerVisible"
      title="用户组管理"
      :width="700"
      :z-index="1100"
      wrap-class-name="group-manager-modal"
      :footer="null"
      destroy-on-close
      centered
    >
      <div class="group-manager">
        <div class="group-toolbar">
          <div class="native-search-wrapper group-search-wrapper">
            <span class="native-search-icon">⌕</span>
            <input
              v-model="groupKeyword"
              type="text"
              class="native-input"
              placeholder="搜索用户组名称"
            />
          </div>
          <a-button type="primary" class="toolbar-btn primary" @click="openCreateGroupModal">
            <PlusOutlined style="margin-right: -6px;"/>
            新建用户组
          </a-button>
        </div>

        <div class="group-table-wrap">
          <a-table
            class="group-table"
            :columns="groupTableColumns"
            :data-source="filteredGroups"
            :pagination="{ pageSize: 7, showSizeChanger: false, hideOnSinglePage: false }"
            :scroll="{ y: groupTableScrollY }"
            row-key="uuid"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'name'">
                <span class="group-name">{{ record.name }}</span>
              </template>
              <template v-else-if="column.key === 'memberCount'">
                <span>{{ groupUserCountMap[record.uuid] || 0 }} 人</span>
              </template>
              <template v-else-if="column.key === 'isDefault'">
                <div class="default-cell">
                  <a-tag v-if="record.uuid === defaultGroupUuid" class="default-group-tag">默认用户组</a-tag>
                  <span v-else class="table-text muted-text">—</span>
                </div>
              </template>
              <template v-else-if="column.key === 'action'">
                <div class="row-actions">
                  <a-button
                    type="text"
                    class="action-text-btn"
                    :loading="defaultGroupSubmitting && defaultGroupUuid !== record.uuid"
                    :disabled="record.uuid === defaultGroupUuid || defaultGroupSubmitting"
                    @click="handleSetDefaultGroup(record)"
                  >
                    设为默认
                  </a-button>
                  <a-button type="text" class="action-icon-btn" @click="openGroupEditModal(record)">
                    <template #icon><EditOutlined /></template>
                  </a-button>
                  <a-button
                    type="text"
                    danger
                    class="action-icon-btn danger"
                    @click="handleDeleteGroup(record)"
                  >
                    <template #icon><DeleteOutlined /></template>
                  </a-button>
                </div>
              </template>
            </template>
          </a-table>
        </div>
      </div>
    </a-modal>

    <a-modal
      v-model:open="groupEditVisible"
      :title="groupForm.uuid ? '编辑用户组' : '新建用户组'"
      :confirm-loading="groupSubmitting"
      :z-index="1200"
      wrap-class-name="group-edit-modal"
      centered
      :footer="null"
      @cancel="groupEditVisible = false"
      :width="480"
    >
      <div class="group-edit-form">
        <a-form layout="vertical">
          <a-form-item label="用户组名称">
            <a-input v-model:value="groupForm.name" :maxlength="40" placeholder="请输入用户组名称" />
          </a-form-item>
        </a-form>
        <div class="form-actions">
          <a-button class="custom-btn cancel-btn" @click="groupEditVisible = false">取消</a-button>
          <a-button class="custom-btn confirm-btn" :loading="groupSubmitting" @click="submitGroupEdit">保存</a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import {
  PlusOutlined,
  TeamOutlined,
  UnlockOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons-vue';
import { Modal } from 'ant-design-vue';
import '@/assets/styles/user-group-select.css';
import NotificationService from '@/utils/NotificationService';
import {
  addAiUserGroup,
  deleteAiUserGroup,
  getAiUserGroupRecord,
  getDefaultAiUserGroup,
  listAiUserGroups,
  setDefaultAiUserGroup,
  type UserGroupItem,
  updateAiUserGroup
} from '@/services/aiPermission';
import {
  deleteUser,
  getAiUserRecord,
  listAiUsersWithGroups,
  syncAiUserGroups,
  type UpdateUserPayload,
  unlockAiUserAccount,
  type UserWithGroups,
  updateUser
} from '@/services/aiUser';
import {
  isPasswordComplexEnough,
  doesPasswordContainUsername,
  PASSWORD_COMPLEXITY_MESSAGE,
  PASSWORD_USERNAME_MESSAGE
} from '@/utils/passwordPolicy';

defineOptions({
  name: 'UserManagementView'
});

const userTableColumns = [
  {
    title: '用户名',
    dataIndex: 'username',
    key: 'username',
    width: 180,
    fixed: 'left',
    customHeaderCell: () => ({
      class: 'user-table-header-center'
    })
  },
  {
    title: '姓名',
    dataIndex: 'realname',
    key: 'realname',
    width: 150,
    align: 'center'
  },
  {
    title: '角色',
    key: 'role',
    width: 120,
    align: 'center'
  },
  {
    title: '邮箱',
    dataIndex: 'email',
    key: 'email',
    width: 220,
    align: 'center'
  },
  {
    title: '账号状态',
    dataIndex: 'is_locked',
    key: 'is_locked',
    width: 120,
    align: 'center'
  },
  {
    title: '用户组',
    dataIndex: 'groups',
    key: 'groups',
    width: 280,
    align: 'center'
  },
  {
    title: '分组数',
    dataIndex: 'groups',
    key: 'groupCount',
    width: 90,
    align: 'center'
  },
  {
    title: '操作',
    key: 'action',
    width: 150,
    align: 'center',
    fixed: 'right'
  }
];

const groupTableColumns = [
  {
    title: '用户组名称',
    dataIndex: 'name',
    key: 'name'
  },
  {
    title: '绑定用户数',
    key: 'memberCount',
    width: 140
  },
  {
    title: '默认组',
    key: 'isDefault',
    width: 120
  },
  {
    title: '操作',
    key: 'action',
    width: 190
  }
];

const users = ref<UserWithGroups[]>([]);
const groupOptions = ref<UserGroupItem[]>([]);
const defaultGroupUuid = ref('');
const loading = ref(false);
const userSubmitting = ref(false);
const groupSubmitting = ref(false);
const defaultGroupSubmitting = ref(false);

const filters = reactive({
  keyword: '',
  groupId: undefined as string | undefined
});

const appliedFilters = reactive({
  keyword: '',
  groupId: undefined as string | undefined
});

const groupKeyword = ref('');
const userEditVisible = ref(false);
const groupManagerVisible = ref(false);
const groupEditVisible = ref(false);

const userForm = reactive({
  uuid: '',
  username: '',
  email: '',
  realname: '',
  password: '',
  groupIds: [] as string[]
});

const initialUserForm = ref({
  username: '',
  email: '',
  realname: '',
  groupIds: [] as string[]
});

const groupForm = reactive({
  uuid: '',
  name: ''
});

const tablePagination = {
  pageSize: 10,
  showSizeChanger: false,
  hideOnSinglePage: false
};
const groupTableScrollY = 420;

const tableSectionRef = ref<HTMLElement | null>(null);
const groupSelectRef = ref<HTMLElement | null>(null);
const groupDropdownOpen = ref(false);
const tableScrollY = ref(360);
const tableBodyHeightCss = computed(() => `${tableScrollY.value}px`);
const tableScrollConfig = computed(() => ({ x: 'max-content', y: tableScrollY.value }));

const updateTableScrollY = () => {
  const container = tableSectionRef.value;
  if (!container) return;

  const containerHeight = container.clientHeight;
  // scroll.y 仅作用于表格体高度，需要扣除表头与分页高度，避免分页被遮挡
  const tableHeader = container.querySelector('.ant-table-header') as HTMLElement | null;
  const pagination = container.querySelector('.ant-table-pagination') as HTMLElement | null;

  const headerHeight = tableHeader?.offsetHeight ?? 56;
  const paginationHeight = pagination?.offsetHeight ?? 44;
  const extraGap = 20;

  tableScrollY.value = Math.max(containerHeight - headerHeight - paginationHeight - extraGap, 220);
};

const isCurrentUserAdmin = computed(() => {
  try {
    const raw = localStorage.getItem('user-profile');
    const profile = raw ? JSON.parse(raw) : null;
    return String(profile?.username || '').trim().toLowerCase() === 'admin';
  } catch {
    return false;
  }
});

const normalizeGroupIds = (ids: string[]) =>
  Array.from(new Set((ids || []).map((item) => String(item || '').trim()).filter(Boolean))).sort((a, b) =>
    a.localeCompare(b)
  );

const isSameGroups = (left: string[], right: string[]) =>
  normalizeGroupIds(left).join(',') === normalizeGroupIds(right).join(',');

const groupSelectOptions = computed(() =>
  groupOptions.value.map((group) => ({
    label: group.name,
    value: group.uuid
  }))
);

const currentGroupLabel = computed(() => {
  if (!filters.groupId) return '全部用户组';
  const target = groupSelectOptions.value.find((item) => item.value === filters.groupId);
  return target?.label || '全部用户组';
});

const filteredUsers = computed(() => {
  const keyword = appliedFilters.keyword.trim().toLowerCase();
  const groupId = appliedFilters.groupId;

  return users.value.filter((user) => {
    const matchKeyword =
      !keyword ||
      [user.username, user.realname, user.email]
        .map((item) => String(item || '').toLowerCase())
        .some((value) => value.includes(keyword));

    const matchGroup = !groupId || (user.groups || []).some((group) => group.group_id === groupId);
    return matchKeyword && matchGroup;
  });
});

const filteredGroups = computed(() => {
  const keyword = groupKeyword.value.trim().toLowerCase();
  if (!keyword) return groupOptions.value;
  return groupOptions.value.filter((group) => String(group.name || '').toLowerCase().includes(keyword));
});

const groupedUserCount = computed(() => users.value.filter((user) => (user.groups || []).length > 0).length);
const adminUserCount = computed(() => users.value.filter((user) => isUserAdmin(user.username)).length);

const groupUserCountMap = computed(() => {
  const result: Record<string, number> = {};
  users.value.forEach((user) => {
    (user.groups || []).forEach((group) => {
      const groupId = String(group.group_id || '').trim();
      if (groupId) result[groupId] = (result[groupId] || 0) + 1;
    });
  });
  return result;
});

const defaultGroupName = computed(() => {
  if (!defaultGroupUuid.value) return '未设置';
  const target = groupOptions.value.find((group) => group.uuid === defaultGroupUuid.value);
  return target?.name || '未设置';
});

const getInitial = (name: string) => String(name || 'U').charAt(0).toUpperCase();
const isUserAdmin = (name: string) => String(name || '').trim().toLowerCase() === 'admin';

const applyFilters = () => {
  appliedFilters.keyword = filters.keyword;
  appliedFilters.groupId = filters.groupId;
};

const resetFilters = () => {
  filters.keyword = '';
  filters.groupId = undefined;
  appliedFilters.keyword = '';
  appliedFilters.groupId = undefined;
};

const toggleGroupDropdown = () => {
  groupDropdownOpen.value = !groupDropdownOpen.value;
};

const selectGroupOption = (value?: string) => {
  filters.groupId = value;
  groupDropdownOpen.value = false;
};

const handleDocumentClick = (event: MouseEvent) => {
  const target = event.target as Node;
  if (groupSelectRef.value && !groupSelectRef.value.contains(target)) {
    groupDropdownOpen.value = false;
  }
};

const loadData = async () => {
  if (!isCurrentUserAdmin.value) return;
  loading.value = true;
  try {
    const [userList, groupList, defaultGroup] = await Promise.all([
      listAiUsersWithGroups(),
      listAiUserGroups(),
      getDefaultAiUserGroup()
    ]);
    users.value = userList;
    groupOptions.value = groupList;
    defaultGroupUuid.value = String(defaultGroup?.uuid || '').trim();
  } catch {
    NotificationService.error('加载用户管理数据失败，请稍后重试');
  } finally {
    loading.value = false;
  }
};

const openGroupManagerModal = () => {
  groupManagerVisible.value = true;
};

const openUserEditModal = async (user: UserWithGroups) => {
  try {
    const record = await getAiUserRecord({ uuid: user.user_id });
    const username = (record?.username || user.username || '').trim();
    const email = String(record?.email || user.email || '').trim();
    const realname = String(record?.realname || user.realname || '').trim();
    const groupIds = normalizeGroupIds((user.groups || []).map((group) => group.group_id));

    userForm.uuid = user.user_id;
    userForm.username = username;
    userForm.email = email;
    userForm.realname = realname;
    userForm.password = '';
    userForm.groupIds = [...groupIds];

    initialUserForm.value = {
      username,
      email,
      realname,
      groupIds: [...groupIds]
    };

    userEditVisible.value = true;
  } catch {
    NotificationService.error('加载用户详情失败，请稍后重试');
  }
};

const submitUserEdit = async () => {
  const uuid = userForm.uuid.trim();
  if (!uuid) {
    NotificationService.error('用户标识缺失，无法保存');
    return;
  }

  const username = userForm.username.trim();
  const email = userForm.email.trim();
  const realname = userForm.realname.trim();
  const password = userForm.password.trim();
  const groupIds = normalizeGroupIds(userForm.groupIds);
  const passwordOwnerUsername = username || initialUserForm.value.username;

  const userPayload: UpdateUserPayload = { uuid };
  if (username && username !== initialUserForm.value.username) userPayload.username = username;
  if (email !== initialUserForm.value.email) userPayload.email = email;
  if (realname !== initialUserForm.value.realname) userPayload.realname = realname;
  if (password) {
    if (!isPasswordComplexEnough(password)) {
      NotificationService.warning(PASSWORD_COMPLEXITY_MESSAGE);
      return;
    }
    if (doesPasswordContainUsername(password, passwordOwnerUsername)) {
      NotificationService.warning(PASSWORD_USERNAME_MESSAGE);
      return;
    }
    userPayload.password = password;
  }

  const hasUserChanges = Object.keys(userPayload).length > 1;
  const hasGroupChanges = !isSameGroups(groupIds, initialUserForm.value.groupIds);

  if (!hasUserChanges && !hasGroupChanges) {
    NotificationService.info('没有可保存的用户变更');
    return;
  }

  userSubmitting.value = true;
  try {
    const tasks: Promise<unknown>[] = [];

    if (hasUserChanges) {
      tasks.push(updateUser(userPayload));
    }

    if (hasGroupChanges) {
      tasks.push(
        syncAiUserGroups({
          user_group_map: {
            [uuid]: groupIds
          }
        })
      );
    }

    await Promise.all(tasks);
    NotificationService.success('用户信息保存成功');
    userEditVisible.value = false;
    await loadData();
  } catch {
    NotificationService.error('保存用户信息失败，请稍后重试');
  } finally {
    userSubmitting.value = false;
  }
};

const handleDeleteUser = (user: UserWithGroups) => {
  if (isUserAdmin(user.username)) {
    NotificationService.warning('管理员账号不允许删除');
    return;
  }

  Modal.confirm({
    title: '确认删除用户',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `将删除用户「${user.username}」，该操作不可撤销。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    async onOk() {
      await deleteUser({
        uuid: user.user_id
      });
      NotificationService.success('用户删除成功');
      await loadData();
    }
  });
};

const handleUnlockUser = (user: UserWithGroups) => {
  if (!user.is_locked) return;

  Modal.confirm({
    title: '确认解除锁定',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `将解除用户「${user.username}」的账号锁定状态。`,
    okText: '确认',
    cancelText: '取消',
    centered: true,
    async onOk() {
      await unlockAiUserAccount({
        uuid: user.user_id
      });
      NotificationService.success('账号已解除锁定');
      await loadData();
    }
  });
};

const openCreateGroupModal = () => {
  groupForm.uuid = '';
  groupForm.name = '';
  groupEditVisible.value = true;
};

const openGroupEditModal = async (group: UserGroupItem) => {
  try {
    const detail = await getAiUserGroupRecord(group.uuid);
    groupForm.uuid = group.uuid;
    groupForm.name = (detail?.name || group.name || '').trim();
    groupEditVisible.value = true;
  } catch {
    NotificationService.error('加载用户组详情失败，请稍后重试');
  }
};

const submitGroupEdit = async () => {
  const groupName = groupForm.name.trim();
  if (!groupName) {
    NotificationService.warning('请输入用户组名称');
    return;
  }

  groupSubmitting.value = true;
  try {
    if (groupForm.uuid) {
      await updateAiUserGroup({
        uuid: groupForm.uuid,
        name: groupName
      });
      NotificationService.success('用户组更新成功');
    } else {
      await addAiUserGroup({
        name: groupName
      });
      NotificationService.success('用户组创建成功');
    }

    groupEditVisible.value = false;
    await loadData();
  } catch {
    NotificationService.error('保存用户组失败，请稍后重试');
  } finally {
    groupSubmitting.value = false;
  }
};

const handleDeleteGroup = (group: UserGroupItem) => {
  if (group.uuid === defaultGroupUuid.value) {
    NotificationService.warning('默认用户组不允许删除，请先设置其他默认组');
    return;
  }

  Modal.confirm({
    title: '确认删除用户组',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `将删除用户组「${group.name}」，该操作不可撤销。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    zIndex: 3000,
    getContainer: () => document.body,
    async onOk() {
      await deleteAiUserGroup({
        uuid: group.uuid
      });
      NotificationService.success('用户组删除成功');
      await loadData();
    }
  });
};

const handleSetDefaultGroup = async (group: UserGroupItem) => {
  if (!group?.uuid || group.uuid === defaultGroupUuid.value) return;

  defaultGroupSubmitting.value = true;
  try {
    await setDefaultAiUserGroup({
      uuid: group.uuid
    });
    defaultGroupUuid.value = group.uuid;
    NotificationService.success(`已将「${group.name}」设置为默认用户组`);
  } catch {
    NotificationService.error('设置默认用户组失败，请稍后重试');
  } finally {
    defaultGroupSubmitting.value = false;
  }
};

onMounted(() => {
  loadData();
  nextTick(() => {
    updateTableScrollY();
  });
  window.addEventListener('resize', updateTableScrollY);
  document.addEventListener('click', handleDocumentClick);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateTableScrollY);
  document.removeEventListener('click', handleDocumentClick);
});

watch(
  [filteredUsers, loading, groupManagerVisible, userEditVisible, groupEditVisible],
  async () => {
    await nextTick();
    updateTableScrollY();
  },
  { deep: false }
);
</script>

<style scoped>
.user-management {
  height: 100%;
  min-height: 0;
  background: #ffffff;
  padding: 24px 30px 0px 30px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow: hidden;
}

.no-permission-card {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  background: #ffffff;
}

.no-permission-card {
  padding: 24px;
}

.no-permission-card h2 {
  margin: 0 0 8px;
  font-size: 18px;
  color: #111827;
}

.no-permission-card p {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.page-header {
  margin-bottom: 2px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-main {
  flex: 1;
  min-width: 0;
}

.header-side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.page-title {
  margin: 0 0 6px;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
}

.page-description {
  margin: 0;
  color: #6b7280;
  font-size: 13px;
}

.header-metrics {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: nowrap;
  overflow-x: auto;
  scrollbar-gutter: stable;
}

.metric-card {
  min-width: 104px;
  padding: 8px 12px;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  background: #ffffff;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}

.metric-label {
  margin-bottom: 0;
  color: #6b7280;
  font-size: 12px;
}

.metric-value {
  color: #2f89ff;
  font-size: 13px;
  font-weight: 600;
}

.page-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-btn {
  height: 34px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  padding: 0 14px;
  border: none;
  box-shadow: none;
  transition: all 0.2s ease;
}

.toolbar-btn.primary {
  background: #3b82f6;
  border-color: #3b82f6;
  color: #ffffff;
}

.toolbar-btn.secondary {
  color: #374151;
  border-color: transparent;
  background: #f3f4f6;
}

.toolbar-btn.primary:hover {
  background: #2563eb;
  border-color: #2563eb;
}

.toolbar-btn.secondary:hover {
  background: #e5e7eb;
}

.content-shell {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  max-width: 100%;
  margin: 0;
  width: 100%;
  padding: 18px 0;
  overflow: hidden;
}

.filters-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding: 0 0 16px;
  border-bottom: 1px solid #edf0f5;
  flex-wrap: wrap;
}

.filters-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
  flex: 1;
  min-width: 0;
  padding-left: 4px;
}

.filters-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.native-search-wrapper {
  display: flex;
  align-items: center;
  background-color: #f2f3f5;
  border-radius: 12px;
  padding: 0 12px;
  height: 32px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
  width: 260px;
}

.native-search-wrapper:hover {
  background-color: #e5e7eb;
}

.native-search-wrapper:focus-within {
  background-color: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.native-search-icon {
  color: #9ca3af;
  font-size: 14px;
  margin-right: 8px;
  line-height: 1;
}

.native-input {
  border: none;
  background: transparent;
  outline: none;
  width: 100%;
  font-size: 13px;
  color: #374151;
}

.native-input::placeholder {
  color: #bfbfbf;
}

.native-select-dropdown {
  position: relative;
  width: 180px;
}

.native-select-trigger {
  width: 100%;
  height: 32px;
  border-radius: 12px;
  border: 1px solid transparent;
  background: #f2f3f5;
  color: #374151;
  font-size: 13px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all 0.2s ease;
}

.native-select-trigger:hover {
  background-color: #e5e7eb;
}

.native-select-trigger.open {
  background: #ffffff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.select-trigger-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.select-trigger-arrow {
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid #9ca3af;
  transition: transform 0.2s ease;
}

.native-select-trigger.open .select-trigger-arrow {
  transform: rotate(180deg);
}

.native-select-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  width: 100%;
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.14);
  padding: 6px;
  z-index: 50;
  max-height: 220px;
  overflow-y: auto;
}

.native-select-option {
  width: 100%;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #374151;
  font-size: 13px;
  text-align: left;
  padding: 0 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.native-select-option:hover {
  background: #f3f4f6;
}

.native-select-option.active {
  background: #e6f4ff;
  color: #1677ff;
  font-weight: 500;
}

.native-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 32px;
  min-width: 64px;
  padding: 0 14px;
  border-radius: 10px;
  border: none;
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.native-btn.primary {
  background: #3b82f6;
  color: #ffffff;
}

.native-btn.primary:hover {
  background: #2563eb;
}

.native-btn.secondary {
  background: #f3f4f6;
  color: #374151;
}

.native-btn.secondary:hover {
  background: #e5e7eb;
}

.native-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.native-btn.icon-btn {
  gap: 6px;
  letter-spacing: 0;
}

.native-btn.icon-btn :deep(.anticon) {
  font-size: 13px;
}

.table-section {
  flex: 1;
  min-width: 0;
  min-height: 0;
  width: 100%;
  overflow: hidden;
}

:deep(.user-table.ant-table-wrapper) {
  height: 100%;
}

:deep(.user-table .ant-table-body) {
  height: v-bind(tableBodyHeightCss);
  max-height: v-bind(tableBodyHeightCss);
  max-height: v-bind(tableBodyHeightCss) !important;
  min-height: v-bind(tableBodyHeightCss);
}

:deep(.user-table .ant-table-thead > tr > th.ant-table-cell-fix-right),
:deep(.user-table .ant-table-tbody > tr > td.ant-table-cell-fix-right) {
  right: 0 !important;
  border-left: 1px solid #edf0f5 !important;
}

/* 隐藏表格的默认滚动条及留白 */
:deep(.ant-table-body::-webkit-scrollbar),
:deep(.ant-table-header::-webkit-scrollbar) {
  display: none !important;
  width: 0 !important;
  height: 0 !important;
}
:deep(.ant-table-body),
:deep(.ant-table-header) {
  scrollbar-width: none !important;
  -ms-overflow-style: none !important;
}
:deep(.ant-table-cell-scrollbar) {
  display: none !important;
}
:deep(.ant-table-header) {
  overflow-y: hidden !important;
}

:deep(.user-table .ant-table-pagination.ant-pagination) {
  margin: 12px 0 4px;
}

:deep(.ant-table-wrapper) {
  padding: 0;
  width: 100%;
  max-width: 100%;
}

:deep(.ant-table) {
  width: 100%;
}

.user-cell {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #e8f3ff;
  color: #1677ff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-content {
  min-width: 0;
}

.user-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.user-name,
.group-name {
  color: #111827;
  font-size: 14px;
  font-weight: 600;
}

.table-text {
  color: #6b7280;
  font-size: 12px;
  font-weight: 400;
}

.user-secondary,
.muted-text {
  color: #6b7280;
  font-size: 12px;
}

.role-tag,
.status-tag,
.group-tag-list :deep(.ant-tag) {
  margin-inline-end: 0;
  font-size: 11px;
  line-height: 18px;
  padding: 1px 8px;
  border-radius: 7px;
  color: #1677ff;
  background: #eef6ff;
  border: 1px solid #b7dbff;
}

.status-tag {
  color: #16a34a;
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.status-tag.locked {
  color: #dc2626;
  background: #fef2f2;
  border-color: #fecaca;
}

.group-tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.group-tag-list.centered {
  justify-content: center;
}

.row-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.action-link {
  padding-inline: 0;
}

.action-icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  color: #1677ff;
}

.action-icon-btn:hover {
  background: #eef6ff;
}

.action-icon-btn[disabled],
.action-icon-btn[disabled]:hover {
  color: #c0c4cc !important;
  background: transparent !important;
}

.action-icon-btn.danger {
  color: #ef4444;
}

.action-icon-btn.danger:hover {
  background: #fee2e2;
}

.default-cell {
  display: flex;
  justify-content: center;
}

.default-group-tag {
  margin-inline-end: 0;
  font-size: 11px;
  line-height: 18px;
  padding: 1px 8px;
  border-radius: 6px;
  color: #2a27ff;
  border: 1px solid #aba9ff;
  background: #eaeaff;
}

:deep(.group-table .ant-table-body) {
  height: 430px;
  max-height: 430px !important;
  min-height: 430px;
}

:deep(.group-table.ant-table-wrapper) {
  height: 100%;
}

:deep(.group-table .ant-table-thead > tr > th) {
  background: #f8fafc;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid #edf0f5;
}

:deep(.group-table .ant-table-tbody > tr > td) {
  border-bottom: 1px solid #f0f2f5;
  vertical-align: middle;
}

:deep(.group-table .ant-table-thead > tr > th:not(:last-child)) {
  border-right: 1px solid #edf0f5;
}

:deep(.group-table .ant-table-tbody > tr > td:not(:last-child)) {
  border-right: 1px solid #f0f2f5;
}

:deep(.group-table .ant-table-tbody > tr:hover > td) {
  background: #fafcff;
}

:deep(.group-table .ant-table-pagination.ant-pagination) {
  margin: 12px 0 0;
}

:deep(.group-manager-modal .ant-modal-content) {
  height: min(82vh, 760px);
  display: flex;
  flex-direction: column;
}

:deep(.group-manager-modal .ant-modal-body) {
  flex: 1;
  min-height: 0;
}

.group-manager {
  display: flex;
  flex-direction: column;
  gap: 14px;
  height: 100%;
  min-height: 0;
}

.group-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.group-search-wrapper {
  max-width: 320px;
  width: 100%;
}

.group-table-wrap {
  flex: 1;
  min-height: 0;
}

.modal-form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.user-edit-modal-content .form-actions .custom-btn {
  min-width: 68px;
  height: 30px;
  padding: 0 16px;
  border-radius: 9px;
  font-size: 12px;
}

:deep(.user-table .ant-table-thead > tr > th) {
  background: #f8fafc;
  color: #374151;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid #edf0f5;
}

:deep(.user-table .ant-table-tbody > tr > td) {
  border-bottom: 1px solid #f0f2f5;
  vertical-align: middle;
}

:deep(.user-table .ant-table-thead > tr > th:not(:last-child)) {
  border-right: 1px solid #edf0f5;
}

:deep(.user-table .ant-table-thead > tr > th.user-table-header-center) {
  text-align: center;
}

:deep(.user-table .ant-table-tbody > tr > td:not(:last-child)) {
  border-right: 1px solid #f0f2f5;
}

:deep(.ant-table-pagination.ant-pagination) {
  margin: 16px 0 0;
}

:deep(.ant-modal .ant-modal-header) {
  border-bottom: 1px solid #edf0f5;
  margin-bottom: 0;
  padding-bottom: 14px;
}

@media (max-width: 1280px) {
  .header-side {
    justify-content: flex-end;
  }
}

@media (max-width: 768px) {
  .user-management {
    padding: 18px;
  }

  .header-side {
    justify-content: flex-start;
  }

  .filters-bar {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .filters-left {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }

  .toolbar-input,
  .toolbar-select {
    width: 100%;
  }

  .filters-right {
    justify-content: flex-start;
  }

  .header-metrics {
    width: 100%;
  }

  .modal-form-grid {
    grid-template-columns: 1fr;
  }

  .group-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .group-search-wrapper {
    max-width: none;
  }
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 32px;
  gap: 8px;
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
}

.cancel-btn {
  background-color: #f5f5f5;
  border: none;
  color: #1a1a1a;
}

.cancel-btn:hover {
  background-color: #e6e6e6;
  color: #1a1a1a;
  border-color: transparent;
}

.confirm-btn {
  background: #1677ff;
  color: #ffffff;
  border: none;
}

.confirm-btn:hover {
  background-color: #4096ff;
  color: #ffffff;
}

</style>

<style>
.user-edit-modal .ant-modal-content,
.group-manager-modal .ant-modal-content,
.group-edit-modal .ant-modal-content {
  border-radius: 21px !important;
  overflow: hidden;
}

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
