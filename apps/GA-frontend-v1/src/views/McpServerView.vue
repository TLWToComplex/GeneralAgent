<template>
  <div class="settings-content">
    <!-- 服务器列表 -->
    <ServerList
        v-model:servers="mcpServersList"
        :selected-server="selectedServer"
        :loading="isLoading"
        @select="handleServerClick"
        @add="showAddServerModal"
        @save="saveData"
    />

    <!-- 右侧内容区域 -->
    <div class="right-content">
      <div v-if="isLoading" class="loading-content">
        <div class="loading-inner">
          <LoadingOutlined spin style="font-size: 32px; color: #1890ff" />
          <div class="loading-text">正在加载…</div>
        </div>
      </div>
      <div v-else-if="selectedServer && selectedServer !== ''" class="server-section">
        <div class="header">
          <div class="header-right">
            <button class="action-btn secondary" @click="exportCurrentServerConfig">
              <ExportOutlined />导出配置
            </button>
            <button class="action-btn danger" :disabled="isSharedServerReadonly" @click="showDeleteServerModal">
              <DeleteOutlined />删除服务
            </button>
            <button v-if="hasUnsavedChanges && !isSharedServerReadonly" class="action-btn secondary" @click="resetServerDataChanges">
              取消保存
            </button>
            <button v-if="hasUnsavedChanges && !isSharedServerReadonly" class="action-btn primary" @click="saveServerData">
              <SaveOutlined />保存配置
            </button>
          </div>
        </div>

        <!-- 移除分割线，让标签页直接跟在header后面 -->
        <a-tabs v-model:activeKey="activeTabKey" class="server-tabs" @change="handleTabChange">
          <a-tab-pane key="general" tab="通用">
            <div v-if="isSharedServerReadonly" class="readonly-tip">
              <div class="readonly-tip-content">
                <div class="readonly-tip-title">只读模式</div>
                <div class="readonly-tip-text">当前账号非管理用户，仅可查看和导出共享 MCP 服务器配置，不能编辑或删除。</div>
              </div>
            </div>
            <ServerConfigForm v-model="serverData" :readonly="isSharedServerReadonly" />
          </a-tab-pane>

          <a-tab-pane key="tools" tab="工具">
            <ToolList :tools="serverData.tools" :loading="isToolsLoading" @show-detail="showToolDetail"/>
          </a-tab-pane>
        </a-tabs>
      </div>

      <div v-else class="empty-content">
        <div class="empty-icon">
          <SettingOutlined style="font-size: 30px;"/>
        </div>
        <h3 class="empty-title">请配置MCP服务器</h3>
        <p class="empty-description">请在左侧选择或添加一个MCP服务器，并配置相关连接信息和工具。</p>
        <button class="action-btn primary" @click="showAddServerModal">
          <PlusOutlined />
          添加MCP服务器
        </button>
      </div>
    </div>

    <!-- 添加服务器模态窗口 -->
    <AddServerModal
        v-model:open="addServerModalVisible"
        :loading="addServerLoading"
        @confirm="confirmAddServer"
        @cancel="closeAddServerModal"
    />

    <!-- 工具详情模态窗口 -->
    <ToolDetailModal
        v-model:open="toolDetailVisible"
        :tool="selectedTool"
        :parameters="toolParameters"
        :loading="isLoadingParameters"
        @cancel="toolDetailVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import {computed, onMounted, ref, onActivated} from 'vue';
import {PlusOutlined, SettingOutlined, DeleteOutlined, SaveOutlined, ExportOutlined, LoadingOutlined} from '@ant-design/icons-vue';
import NotificationService from '@/utils/NotificationService';
import StorageService from '@/utils/StorageService';
import { STORAGE_KEYS } from '@/config/constants';

// 导入组件
import ServerList from '@/components/mcp-server/ServerList.vue';
import ServerConfigForm from '@/components/mcp-server/ServerConfigForm.vue';
import ToolList from '@/components/mcp-server/ToolList.vue';
import AddServerModal from '@/components/mcp-server/AddServerModal.vue';
import ToolDetailModal from '@/components/mcp-server/ToolDetailModal.vue';

// 导入类型
import type {
  ServerTool,
  ServerData,
  ServerListItem
} from '@/components/mcp-server/types';
import { addMcpServer, listMcpServers, deleteMcpServer, updateMcpServer, testMcpServerConnection } from '@/services/mcpServer';
import { updateAiAgent, listAiAgents } from '@/services/aiAgent';
import { listAiEntityAssignedGroups, updateAiPermission } from '@/services/aiPermission';

// 定义组件名以便keep-alive能够识别
defineOptions({
  name: 'McpServerView'
});

// 本地存储键（仅用于缓存后端列表结果）
const SERVERS_STORAGE_KEY = 'mcp-servers-list';
const SERVER_DATA_STORAGE_KEY = 'mcp-servers-data';
const MCP_SERVER_ENTITY_TYPE = 0;

// 服务器列表数据
const mcpServersList = ref<ServerListItem[]>([]);

// 当前选中的服务器
const selectedServer = ref('');

// 当前激活的标签页
const activeTabKey = ref('general');

// 服务器数据映射
const serverDataMap = ref<Record<string, ServerData>>({});

// 当前服务器数据
const serverData = ref<ServerData>({
  uuid: '',
  id: '',
  name: '',
  description: '',
  type: 'sse',
  url: '',
  timeout: 60,
  visibility: 'private',
  permissionGroupIds: [],
  headers: [],
  tools: []
});
const originalServerData = ref<ServerData>({
  uuid: '',
  id: '',
  name: '',
  description: '',
  type: 'sse',
  url: '',
  timeout: 60,
  visibility: 'private',
  permissionGroupIds: [],
  headers: [],
  tools: []
});
const originalServerDataSnapshot = ref('');
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

// 添加服务器模态窗口相关
const addServerModalVisible = ref(false);
const addServerLoading = ref(false);

// 工具详情模态窗口相关
const toolDetailVisible = ref(false);
const selectedTool = ref<ServerTool | null>(null);
const toolParameters = ref<Record<string, any> | null>(null);
const isLoadingParameters = ref(false);
const isToolsLoading = ref(false);

// 页面加载状态
const isLoading = ref(true);
let serverLoadRequestId = 0;
let toolsLoadRequestId = 0;

// 处理服务器点击事件
const handleServerClick = async (item: ServerListItem) => {
  // 优先使用ID作为选中的服务器标识
  selectedServer.value = item.id || item.name;
  // 加载服务器数据
  await loadServerData(selectedServer.value);
  // 重置标签页到"通用"
  activeTabKey.value = 'general';
};
// 加载服务器数据
const loadServerData = async (serverIdOrName: string) => {
  const currentRequestId = ++serverLoadRequestId;
  // 查找服务器数据，优先通过ID查找
  let serverDataToLoad = serverDataMap.value[serverIdOrName];
  let matchedServerKey = serverDataToLoad ? serverIdOrName : '';

  // 如果通过ID没有找到，尝试通过名称查找
  if (!serverDataToLoad) {
    const serverIdByServerName = Object.keys(serverDataMap.value).find(id =>
        serverDataMap.value[id] && serverDataMap.value[id].name === serverIdOrName
    );

    if (serverIdByServerName) {
      serverDataToLoad = serverDataMap.value[serverIdByServerName];
      matchedServerKey = serverIdByServerName;
    }
  }

  if (serverDataToLoad) {
    const nextServerData: ServerData = {
      uuid: (serverDataToLoad as any).uuid || '',
      id: serverDataToLoad.id || '',
      name: serverDataToLoad.name || '',
      description: serverDataToLoad.description || '',
      type: serverDataToLoad.type || 'sse',
      url: serverDataToLoad.url || '',
      timeout: serverDataToLoad.timeout || 60,
      visibility: normalizeVisibility((serverDataToLoad as any).visibility),
      permissionGroupIds: normalizePermissionGroupIds((serverDataToLoad as any).permissionGroupIds),
      headers: normalizeServerHeaders(serverDataToLoad.headers),
      tools: [...(serverDataToLoad.tools || [])]
    };
    serverData.value = nextServerData;
    updateOriginalServerDataSnapshot(nextServerData);

    const entityId = nextServerData.uuid?.trim();
    if (nextServerData.visibility === 'public' && entityId) {
      try {
        const assignedGroups = await listAiEntityAssignedGroups(entityId, MCP_SERVER_ENTITY_TYPE);
        if (currentRequestId !== serverLoadRequestId) {
          return;
        }
        const normalizedAssignedGroups = normalizePermissionGroupIds(assignedGroups);
        serverData.value = {
          ...serverData.value,
          permissionGroupIds: normalizedAssignedGroups
        };
        updateOriginalServerDataSnapshot(serverData.value);
        if (matchedServerKey && serverDataMap.value[matchedServerKey]) {
          serverDataMap.value[matchedServerKey] = {
            ...serverDataMap.value[matchedServerKey],
            permissionGroupIds: normalizedAssignedGroups
          };
        }
      } catch (error) {
        NotificationService.error(typeof (error as any)?.message === 'string' ? (error as any).message : '加载可访问用户组失败');
      }
    }
  } else {
    serverData.value = {
      uuid: '',
      id: '',
      name: '',
      description: '',
      type: 'sse',
      url: '',
      timeout: 60,
      visibility: 'private',
      permissionGroupIds: [],
      headers: [],
      tools: []
    };
    updateOriginalServerDataSnapshot(serverData.value);
  }
};

// 显示添加服务器模态窗
const showAddServerModal = () => {
  if (addServerModalVisible.value) return;
  addServerModalVisible.value = true;
};

// 关闭添加服务器模态窗
const closeAddServerModal = () => {
  addServerModalVisible.value = false;
};

// 工具方法：规范化 URL（移除反引号与多余空格）
const sanitizeUrl = (u: string) => (u || '').replace(/`/g, '').trim();
const normalizeVisibility = (value: unknown): 'private' | 'public' =>
  String(value || '').trim().toLowerCase() === 'public' ? 'public' : 'private';
const normalizePermissionGroupIds = (source: unknown): string[] =>
  Array.from(
    new Set(
      (Array.isArray(source) ? source : []).filter(
        (groupId): groupId is string => typeof groupId === 'string' && groupId.trim().length > 0
      )
    )
  );
const normalizeServerHeaders = (source: unknown): Array<{ key: string; value: string }> => {
  if (Array.isArray(source)) {
    return source
      .filter((header): header is { key: string; value: string } => !!header && typeof header.key === 'string' && typeof header.value === 'string')
      .map((header) => ({ key: header.key.trim(), value: header.value }))
      .filter((header) => header.key.length > 0);
  }

  if (source && typeof source === 'object') {
    return Object.entries(source as Record<string, unknown>)
      .filter(([key, value]) => key.trim().length > 0 && typeof value === 'string')
      .map(([key, value]) => ({ key: key.trim(), value: value as string }));
  }

  return [];
};
const normalizeToolSchema = (source: unknown): Record<string, any> | undefined =>
  source && typeof source === 'object' && !Array.isArray(source)
    ? JSON.parse(JSON.stringify(source))
    : undefined;
const cloneServerData = (source?: Partial<ServerData>): ServerData => ({
  uuid: source?.uuid || '',
  id: source?.id || '',
  name: source?.name || '',
  description: source?.description || '',
  type: source?.type || 'sse',
  url: source?.url || '',
  timeout: typeof source?.timeout === 'number' ? source.timeout : 60,
  visibility: normalizeVisibility(source?.visibility),
  permissionGroupIds: normalizeVisibility(source?.visibility) === 'public'
    ? normalizePermissionGroupIds(source?.permissionGroupIds)
    : [],
  headers: normalizeServerHeaders(source?.headers),
  tools: Array.isArray(source?.tools)
    ? source.tools.map((tool) => ({
      id: tool.id,
      name: tool.name,
      description: tool.description || '',
      argsSchema: normalizeToolSchema((tool as ServerTool).argsSchema)
    }))
    : []
});
const normalizeServerTools = (source: unknown): ServerTool[] =>
  Array.isArray(source)
    ? source
      .filter((tool): tool is Record<string, any> => !!tool && typeof tool === 'object')
      .map((tool) => ({
        id: String(tool.id || tool.name || '').trim(),
        name: String(tool.name || tool.id || '').trim(),
        description: typeof tool.description === 'string' ? tool.description : '',
        argsSchema: normalizeToolSchema(tool.argsSchema || tool.args_schema || tool.parameters)
      }))
      .filter((tool) => tool.id && tool.name)
    : [];
const createHeadersObject = (headers: Array<{ key: string; value: string }>): Record<string, string> =>
  headers.reduce<Record<string, string>>((acc, header) => {
    const key = header?.key?.trim();
    if (key) {
      acc[key] = header.value ?? '';
    }
    return acc;
  }, {});
const isValidHttpUrl = (url: string): boolean => {
  try {
    const parsedUrl = new URL(url);
    return parsedUrl.protocol === 'http:' || parsedUrl.protocol === 'https:';
  } catch {
    return false;
  }
};
const createMcpServerTestPayload = (source: ServerData) => ({
  server_name: source.name || selectedServer.value || '未命名服务器',
  url: sanitizeUrl(source.url),
  type: source.type === 'streamableHttp' ? 'streamable_http' : 'sse',
  headers: createHeadersObject(source.headers || [])
});
const createServerDataSnapshot = (source?: Partial<ServerData>): string => {
  const normalizedData = cloneServerData(source);

  return JSON.stringify({
    name: normalizedData.name,
    description: normalizedData.description,
    type: normalizedData.type,
    url: normalizedData.url,
    timeout: normalizedData.timeout,
    visibility: normalizedData.visibility,
    permissionGroupIds: [...normalizedData.permissionGroupIds].sort(),
    headers: normalizedData.headers
  });
};
const updateOriginalServerDataSnapshot = (source?: Partial<ServerData>) => {
  const normalizedData = cloneServerData(source || serverData.value);
  originalServerData.value = normalizedData;
  originalServerDataSnapshot.value = createServerDataSnapshot(normalizedData);
};
const hasUnsavedChanges = computed(() =>
  !!selectedServer.value && createServerDataSnapshot(serverData.value) !== originalServerDataSnapshot.value
);
const isSharedServerReadonly = computed(() =>
  !isCurrentUserAdmin.value && normalizeVisibility(serverData.value.visibility) === 'public'
);
const resetServerDataChanges = () => {
  if (!hasUnsavedChanges.value) return;
  serverData.value = cloneServerData(originalServerData.value);
};

const refreshCurrentServerTools = async () => {
  if (!selectedServer.value) return;

  const url = sanitizeUrl(serverData.value.url);
  if (!url) {
    NotificationService.error('当前MCP服务器缺少可用的URL');
    return;
  }
  if (!isValidHttpUrl(url)) {
    NotificationService.error('当前MCP服务器URL格式无效');
    return;
  }

  const currentRequestId = ++toolsLoadRequestId;
  isToolsLoading.value = true;

  try {
    const result = await testMcpServerConnection(createMcpServerTestPayload(serverData.value));

    if (currentRequestId !== toolsLoadRequestId) {
      return;
    }

    if ((typeof result?.code === 'number' && result.code !== 0) || result?.data?.success === false) {
      throw new Error(result?.message || result?.data?.message || '刷新工具列表失败');
    }

    const nextTools = normalizeServerTools(result?.data?.tools);
    serverData.value = {
      ...serverData.value,
      tools: nextTools
    };

    const serverKey = resolveServerSelectionKey(selectedServer.value);
    if (serverKey && serverDataMap.value[serverKey]) {
      serverDataMap.value[serverKey] = {
        ...serverDataMap.value[serverKey],
        tools: nextTools
      };
      saveData();
    }
  } catch (error: any) {
    NotificationService.error(error?.response?.data?.message || error?.message || '刷新工具列表失败，请稍后重试');
  } finally {
    if (currentRequestId === toolsLoadRequestId) {
      isToolsLoading.value = false;
    }
  }
};

const handleTabChange = async (key: string) => {
  if (key === 'tools') {
    await refreshCurrentServerTools();
  }
};

const resolveServerSelectionKey = (preferredServerIdOrName?: string): string => {
  if (!preferredServerIdOrName) {
    return mcpServersList.value[0]?.id || mcpServersList.value[0]?.name || '';
  }
  if (serverDataMap.value[preferredServerIdOrName]) {
    return preferredServerIdOrName;
  }
  const matchedKey = Object.keys(serverDataMap.value).find((id) => {
    const item = serverDataMap.value[id];
    return item?.name === preferredServerIdOrName;
  });
  return matchedKey || preferredServerIdOrName;
};

const resolveServerKeyByIdentity = (options: {
  preferredId?: string
  preferredUuid?: string
  preferredName?: string
}): string => {
  const { preferredId, preferredUuid, preferredName } = options;

  if (preferredId && serverDataMap.value[preferredId]) {
    return preferredId;
  }

  const matchedKey = Object.keys(serverDataMap.value).find((id) => {
    const item = serverDataMap.value[id];
    if (!item) return false;
    return item.uuid === preferredUuid || item.name === preferredName;
  });

  if (matchedKey) {
    return matchedKey;
  }

  return resolveServerSelectionKey(preferredId || preferredName);
};

const syncMcpServerPermissionGroups = async (
  entityId: string,
  targetGroupIds: string[],
  existingGroupIdsSource: string[] = []
): Promise<string[]> => {
  const normalizedTargetGroupIds = normalizePermissionGroupIds(targetGroupIds);
  const existingGroupIds = normalizePermissionGroupIds(existingGroupIdsSource);
  const nextPermissionByGroupId = new Map<string, 1 | 2>();

  existingGroupIds.forEach((groupId) => {
    nextPermissionByGroupId.set(groupId, normalizedTargetGroupIds.includes(groupId) ? 1 : 2);
  });
  normalizedTargetGroupIds.forEach((groupId) => {
    nextPermissionByGroupId.set(groupId, 1);
  });

  const updates = Array.from(nextPermissionByGroupId.entries()).map(([groupId, permission]) =>
    updateAiPermission({
      group_id: groupId,
      list: [
        {
          entity_id: entityId,
          entity_type: MCP_SERVER_ENTITY_TYPE,
          permission
        }
      ]
    })
  );

  if (updates.length > 0) {
    await Promise.all(updates);
  }

  return normalizePermissionGroupIds(
    await listAiEntityAssignedGroups(entityId, MCP_SERVER_ENTITY_TYPE)
  );
};

// 从后端加载并刷新本地状态与缓存
const reloadServersFromBackend = async (preferredServerIdOrName?: string) => {
  try {
    const res = await listMcpServers();
    const arr: any[] = Array.isArray(res?.data) ? res.data : [];

    const nextList: ServerListItem[] = arr.map((item: any) => ({
      id: item.id,
      name: item.name,
      type: item.type || 'sse'
    }));

    const nextMap: Record<string, ServerData> = {};
    arr.forEach((item: any) => {
      nextMap[item.id] = {
        id: item.id,
        uuid: item.uuid,
        name: item.name || '',
        description: item.description || '',
        type: item.type || 'sse',
        url: sanitizeUrl(item.url || ''),
        timeout: typeof item.timeout === 'number' ? item.timeout : 60,
        visibility: normalizeVisibility(item.visibility),
        permissionGroupIds: normalizePermissionGroupIds(item.permissionGroupIds || item.permission_group_ids),
        headers: normalizeServerHeaders(item.headers),
        tools: Array.isArray(item.tools)
          ? item.tools.map((t: any) => ({ id: t.id, name: t.name, description: t.description || '' }))
          : []
      };
    });

    mcpServersList.value = nextList;
    serverDataMap.value = nextMap;

    // 更新本地缓存供其他模块读取
    saveData();

    // 优先恢复指定服务，否则默认选择第一个
    if (mcpServersList.value.length > 0) {
      selectedServer.value = resolveServerSelectionKey(preferredServerIdOrName);
      await loadServerData(selectedServer.value);
    } else {
      selectedServer.value = '';
    }
  } catch (e) {
    NotificationService.error('加载MCP服务器列表失败');
  }
};

// 确认添加服务器（走后端接口并刷新列表）
const confirmAddServer = async (formData: ServerData) => {
  addServerLoading.value = true;

  try {
    // 基本校验
    try {
      new URL(sanitizeUrl(formData.url));
    } catch (urlError) {
      NotificationService.error('请输入有效的URL格式');
      return;
    }

    const headers: { key: string, value: string }[] = Array.isArray(formData.headers)
      ? formData.headers.filter(h => h && h.key && h.value)
      : [];

    const ensureId = formData.id && formData.id.trim()
      ? formData.id.trim()
      : ('mcp_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11));

    let toolsForPayload: { id: string; name: string; description?: string }[] = [];
    try {
      const testResult = await testMcpServerConnection(createMcpServerTestPayload(formData));
      if (testResult?.data?.tools && Array.isArray(testResult.data.tools)) {
        const normalizedTools = normalizeServerTools(testResult.data.tools);
        toolsForPayload = normalizedTools.map((tool: any) => ({
          id: tool.id || tool.name || '',
          name: tool.name || tool.id || '',
          description: tool.description || ''
        }));
      }
    } catch {}

    const payload = {
      id: ensureId,
      name: formData.name,
      description: formData.description,
      type: formData.type,
      url: sanitizeUrl(formData.url),
      timeout: formData.timeout,
      visibility: normalizeVisibility(formData.visibility),
      permissionGroupIds: normalizeVisibility(formData.visibility) === 'public'
        ? normalizePermissionGroupIds(formData.permissionGroupIds)
        : [],
      headers,
      tools: toolsForPayload.length > 0 ? toolsForPayload : (Array.isArray(formData.tools) ? formData.tools : [])
    };

    const addResult = await addMcpServer(payload);
    const createdUuid = String(
      addResult?.data?.uuid
      || addResult?.uuid
      || ''
    ).trim();

    if (payload.visibility === 'public' && payload.permissionGroupIds.length > 0 && createdUuid) {
      const assignedGroups = await syncMcpServerPermissionGroups(createdUuid, payload.permissionGroupIds, []);
      if (serverDataMap.value[ensureId]) {
        serverDataMap.value[ensureId] = {
          ...serverDataMap.value[ensureId],
          permissionGroupIds: assignedGroups
        };
      }
    }

    await reloadServersFromBackend(ensureId);
    const createdServerKey = resolveServerKeyByIdentity({
      preferredId: ensureId,
      preferredUuid: createdUuid,
      preferredName: payload.name
    });
    selectedServer.value = createdServerKey;
    activeTabKey.value = 'general';
    await loadServerData(createdServerKey);

    // 关闭模态并提示
    closeAddServerModal();
    NotificationService.success('MCP服务器添加成功');
  } catch (error) {
    NotificationService.error('添加MCP服务器失败，请稍后重试');
  } finally {
    addServerLoading.value = false;
  }
};

// 显示删除服务器模态窗
const showDeleteServerModal = () => {
  if (!selectedServer.value) return;
  if (isSharedServerReadonly.value) {
    NotificationService.info('非 admin 用户不能删除共享 MCP 服务器');
    return;
  }
  const key = selectedServer.value;
  let target = serverDataMap.value[key];
  if (!target) {
    const byNameKey = Object.keys(serverDataMap.value).find(id => serverDataMap.value[id]?.name === key);
    if (byNameKey) target = serverDataMap.value[byNameKey];
  }
  const displayName = (target as any)?.name || key;

  const modal = {
    title: '删除MCP服务器',
    wrapClassName: 'confirm-delete-modal',
    class: 'confirm-delete-modal',
    content: `确定要删除服务器 "${displayName}" 吗？此操作不可恢复。`,
    okText: '删除',
    cancelText: '取消',
    centered: true,
    onOk: () => {
      deleteServer();
    }
  };

  // 使用ant-design-vue的Modal.confirm
  // @ts-ignore
  import('ant-design-vue').then(({Modal}) => {
    Modal.confirm(modal);
  });
};

const deleteServer = async () => {
  if (!selectedServer.value) return;
  if (isSharedServerReadonly.value) {
    NotificationService.info('非 admin 用户不能删除共享 MCP 服务器');
    return;
  }

  try {
    const key = selectedServer.value;
    let target = serverDataMap.value[key];
    if (!target) {
      const byNameKey = Object.keys(serverDataMap.value).find(id => serverDataMap.value[id]?.name === key);
      if (byNameKey) target = serverDataMap.value[byNameKey];
    }
    const uuid = (target as any)?.uuid;
    const deletedId = (target as any)?.id || key;
    const deletedName = (target as any)?.name || key;
    if (!uuid) {
      NotificationService.error('未找到服务UUID，无法删除');
      return;
    }

    await deleteMcpServer({ uuid });
    await reloadServersFromBackend();
    NotificationService.success('MCP服务器已删除');

    try {
      const allAgents = StorageService.getAgents();
      const updatedAgents = allAgents.map((agent: any) => {
        const mcp = agent?.config?.mcp || {};
        const ids = Array.isArray(mcp.enabledServerIdentifiers) ? mcp.enabledServerIdentifiers : [];
        const filtered = ids.filter((id: string) => id !== deletedId && id !== deletedName);
        if (filtered.length !== ids.length) {
          return {
            ...agent,
            config: {
              ...agent.config,
              mcp: { ...(agent.config?.mcp || {}), enabledServerIdentifiers: filtered }
            }
          };
        }
        return agent;
      });

      const changedAgents = updatedAgents.filter((a: any, i: number) => {
        const prev = allAgents[i] || {};
        const pi = (prev?.config?.mcp?.enabledServerIdentifiers || []).join('|');
        const ni = (a?.config?.mcp?.enabledServerIdentifiers || []).join('|');
        return pi !== ni;
      });

      if (changedAgents.length > 0) {
        try { await Promise.all(changedAgents.map((agent: any) => {
          const agentType = agent.agent_type || agent.config?.basic?.type || 'assistant';
          const isDeepAgent = agentType === 'deepagent';

          return updateAiAgent({ uuid: agent.uuid, id: agent.id, name: agent.name, description: agent.description, themeColor: agent.themeColor, agent_type: agentType, ...(isDeepAgent ? { visibility: agent.visibility || agent.config?.basic?.visibility || 'private', skills: Array.isArray(agent.skills) ? agent.skills : (Array.isArray(agent.config?.skills) ? agent.config.skills : []) } : {}), config: agent.config });
        })); } catch {}
        try {
          const res = await listAiAgents();
          const arr: any[] = Array.isArray(res?.data) ? res.data : [];
          const sanitizeUrl = (u?: string) => (u || '').replace(/`/g, '').trim();
          const mapped = arr.map((item: any) => {
            const m = item.config?.model || {};
            const basicConfig = {
              ...(item.config?.basic || {}),
              type: item.config?.basic?.type || item.agent_type || 'assistant',
              visibility: item.config?.basic?.visibility || item.visibility || 'private'
            };
            const skills = Array.isArray(item.skills) ? item.skills : (Array.isArray(item.config?.skills) ? item.config.skills : []);
            const normalizedModel = {
              service: m.service,
              name: m.name,
              temperature: typeof m.temperature === 'number' ? m.temperature : 0.7,
              top_p: typeof m.topP === 'number' ? m.topP : (typeof m.top_p === 'number' ? m.top_p : 1.0),
              presence_penalty: typeof m.presencePenalty === 'number' ? m.presencePenalty : (typeof m.presence_penalty === 'number' ? m.presence_penalty : 0),
              frequency_penalty: typeof m.frequencyPenalty === 'number' ? m.frequencyPenalty : (typeof m.frequency_penalty === 'number' ? m.frequency_penalty : 0),
              apiKey: m.apiKey,
              apiUrl: sanitizeUrl(m.apiUrl)
            };
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
            } as any;
          });
          StorageService.setAgents(mapped);
          try { window.dispatchEvent(new Event('agents-updated')); } catch {}
        } catch {}
      }

      try {
        const activeAgent = StorageService.getActiveAgent();
        const ids = Array.isArray(activeAgent?.mcp?.enabledServerIdentifiers) ? activeAgent.mcp.enabledServerIdentifiers : [];
        const filtered = ids.filter((id: string) => id !== deletedId && id !== deletedName);
        if (activeAgent && filtered.length !== ids.length) {
          const updatedActive = { ...activeAgent, mcp: { ...(activeAgent.mcp || {}), enabledServerIdentifiers: filtered } };
          StorageService.setActiveAgent(updatedActive);
          try { window.dispatchEvent(new CustomEvent('active-agent-updated', { detail: { activeAgent: updatedActive } })); } catch {}
        }
      } catch {}
    } catch {}
  } catch (error) {
    NotificationService.error('删除MCP服务器失败，请稍后重试');
  }
};

// 保存服务器数据
const saveServerData = async () => {
  if (!selectedServer.value) return;
  if (isSharedServerReadonly.value) {
    NotificationService.info('非 admin 用户不能修改共享 MCP 服务器信息');
    return;
  }

  let isValid = true;
  const visibility = normalizeVisibility(serverData.value.visibility);
  const permissionGroupIds = visibility === 'public'
    ? normalizePermissionGroupIds(serverData.value.permissionGroupIds)
    : [];
  if (!serverData.value.name.trim()) { NotificationService.error('服务器名称不能为空'); isValid = false; }
  if (!serverData.value.type) { NotificationService.error('服务器类型不能为空'); isValid = false; }
  if (!serverData.value.url.trim()) { NotificationService.error('服务器URL不能为空'); isValid = false; }
  if (serverData.value.url.trim()) {
    try { new URL(sanitizeUrl(serverData.value.url)); } catch { NotificationService.error('请输入有效的URL格式'); isValid = false; }
  }
  if (visibility === 'public' && permissionGroupIds.length === 0) {
    NotificationService.error('共享的MCP服务器至少需要选择一个用户组');
    isValid = false;
  }
  if (!isValid) return;

  const headers = Array.isArray(serverData.value.headers)
    ? serverData.value.headers.filter((h: any) => h && h.key && h.value)
    : [];

  const id = serverData.value.id || selectedServer.value;
  const uuid = serverData.value.uuid || (serverDataMap.value[id]?.uuid as any);
  const existingPermissionGroupIds = normalizePermissionGroupIds(serverDataMap.value[id]?.permissionGroupIds);
  const payload = {
    id,
    uuid,
    name: serverData.value.name,
    description: serverData.value.description,
    type: serverData.value.type,
    url: sanitizeUrl(serverData.value.url),
    timeout: serverData.value.timeout,
    visibility,
    permissionGroupIds,
    headers,
    tools: Array.isArray(serverData.value.tools) ? serverData.value.tools : []
  };

  try {
    await updateMcpServer(payload);
    await reloadServersFromBackend(id);
    if (uuid) {
      const assignedGroups = await syncMcpServerPermissionGroups(
        uuid,
        visibility === 'public' ? permissionGroupIds : [],
        existingPermissionGroupIds
      );
      if (serverDataMap.value[id]) {
        serverDataMap.value[id] = {
          ...serverDataMap.value[id],
          permissionGroupIds: assignedGroups
        };
      }
      if (selectedServer.value === id || selectedServer.value === serverData.value.name) {
        serverData.value = {
          ...serverData.value,
          permissionGroupIds: assignedGroups
        };
      }
      await loadServerData(id);
    }
    NotificationService.success('MCP服务器配置已保存');
  } catch (e) {
    NotificationService.error('保存失败，请检查后重试');
  }
};

// MCP服务器配置导出

const exportCurrentServerConfig = () => {
  try {
    if (!selectedServer.value) {
      NotificationService.warning('请先选择一个MCP服务器');
      return;
    }

    const id = selectedServer.value;
    const cfg = serverDataMap.value[id] || serverData.value;

    const exportPayload = {
      server: {
        name: cfg.name,
        description: cfg.description,
        type: cfg.type,
        url: cfg.url,
        timeout: cfg.timeout,
        visibility: normalizeVisibility((cfg as any).visibility),
        permissionGroupIds: normalizePermissionGroupIds((cfg as any).permissionGroupIds),
        permission_group_ids: normalizePermissionGroupIds((cfg as any).permissionGroupIds)
      },
      visibility: normalizeVisibility((cfg as any).visibility),
      permissionGroupIds: normalizePermissionGroupIds((cfg as any).permissionGroupIds),
      permission_group_ids: normalizePermissionGroupIds((cfg as any).permissionGroupIds),
      headers: Array.isArray(cfg.headers) ? cfg.headers : [],
      tools: Array.isArray(cfg.tools) ? cfg.tools : []
    };

    const json = JSON.stringify(exportPayload, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `mcp-server-${cfg.name || id}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    NotificationService.success('配置已导出');
  } catch (e) {
    NotificationService.error('导出配置失败');
  }
};

// 显示工具详情
const showToolDetail = async (tool: ServerTool) => {
  selectedTool.value = tool;
  toolParameters.value = tool.argsSchema || null;
  isLoadingParameters.value = true;
  toolDetailVisible.value = true;

  try {
    if (tool.argsSchema) {
      return;
    }

    if (selectedServer.value && serverData.value.url) {
      const result = await testMcpServerConnection(createMcpServerTestPayload(serverData.value));
      if ((typeof result?.code === 'number' && result.code !== 0) || result?.data?.success === false) {
        throw new Error(result?.message || result?.data?.message || '获取工具参数失败');
      }

      const refreshedTools = normalizeServerTools(result?.data?.tools);
      const matchedTool = refreshedTools.find((item) => item.id === tool.id);
      toolParameters.value = matchedTool?.argsSchema || null;

      if (refreshedTools.length > 0) {
        serverData.value = {
          ...serverData.value,
          tools: refreshedTools
        };
        const serverKey = resolveServerSelectionKey(selectedServer.value);
        if (serverKey && serverDataMap.value[serverKey]) {
          serverDataMap.value[serverKey] = {
            ...serverDataMap.value[serverKey],
            tools: refreshedTools
          };
          saveData();
        }
      }
    }
  } catch (error) {
    // 工具参数获取失败时静默处理，保持模态窗口打开
  } finally {
    isLoadingParameters.value = false;
  }
};

// 加载数据（改为从后端获取）
const loadSavedData = async () => {
  await reloadServersFromBackend();
};

// 保存数据到本地存储（仅用于缓存从后端获取的列表或最新状态）
const saveData = () => {
  try {
    // 确保所有服务器数据都包含ID
    Object.keys(serverDataMap.value).forEach(key => {
      if (!serverDataMap.value[key].id) {
        // 如果没有ID，生成一个新的
        serverDataMap.value[key].id = key;
      }
    });

    localStorage.setItem(SERVERS_STORAGE_KEY, JSON.stringify(mcpServersList.value));
    localStorage.setItem(SERVER_DATA_STORAGE_KEY, JSON.stringify(serverDataMap.value));

    // 触发自定义事件，通知其他组件MCP服务器配置已更改
    document.dispatchEvent(new CustomEvent('mcp-server-config-changed'));
  } catch (error) {
    NotificationService.error('保存MCP服务器配置失败');
  }
};

// 页面激活时执行的操作，包括首次加载和从其他页面切回
const handlePageActivation = async () => {
  if (mcpServersList.value.length === 0) {
    isLoading.value = true;
    await loadSavedData();
  }
  isLoading.value = false;
};

// 在 onMounted 周期钩子中初始化
onMounted(async () => {
  isLoading.value = true;
  await loadSavedData();
  const openFlag = localStorage.getItem(STORAGE_KEYS.OPEN_ADD_SERVER_MODAL);
  if (openFlag === '1') {
    localStorage.removeItem(STORAGE_KEYS.OPEN_ADD_SERVER_MODAL);
    showAddServerModal();
  }
  isLoading.value = false;
});

// 在页面被重新激活时重新加载数据
onActivated(async () => {
  await handlePageActivation();
});
</script>

<style scoped>
@import '@/assets/styles/mcp-server-view.css';

:deep(.server-tabs .ant-tabs-nav) {
  margin-bottom: 5px;
  border-bottom: 0 solid;
}

:deep(.server-tabs.ant-tabs) {
  flex: 1;
  min-height: 0;
}

:deep(.server-tabs .ant-tabs-content-holder),
:deep(.server-tabs .ant-tabs-content),
:deep(.server-tabs .ant-tabs-tabpane),
:deep(.server-tabs .ant-tabs-tabpane-active) {
  display: flex;
  flex: 1;
  min-height: 0;
  flex-direction: column;
}

:deep(.server-tabs .ant-tabs-content-holder) {
  flex: 1;
  min-height: 0;
}

:deep(.server-tabs .ant-tabs-content) {
  height: 100%;
}

:deep(.server-tabs .ant-tabs-tabpane) {
  height: 100%;
}

:deep(.server-tabs .ant-tabs-tab) {
  padding: 8px 0;
  font-size: 14px;
  transition: all 0.3s;
}

:deep(.server-tabs .ant-tabs-tab-active) {
  font-weight: 500;
}

:deep(.server-tabs .ant-tabs-ink-bar) {
  height: 2px;
  background-color: #1890ff;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
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

.action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.readonly-tip {
  margin-top: 15px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 18px;
  padding: 14px 16px;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  background:
    linear-gradient(135deg, rgba(239, 246, 255, 0.98) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow: 0 10px 24px -20px rgba(59, 130, 246, 0.55);
}

.readonly-tip-content {
  min-width: 0;
}

.readonly-tip-title {
  font-size: 14px;
  line-height: 1.4;
  font-weight: 600;
  color: #1d4ed8;
}

.readonly-tip-text {
  margin-top: 3px;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.action-btn.primary {
  background: #3b82f6;
  color: white;
}

.action-btn.primary:hover {
  background: #2563eb;
  transform: translateY(-1px);
}

.action-btn.secondary {
  background: #f3f4f6;
  color: #374151;
}

.action-btn.secondary:hover {
  background: #e5e7eb;
}

.action-btn.danger {
  background: #ffeeee;
  color: #ff3939;
}

.action-btn.danger:hover {
  background: #ffc5c5;
}

.server-section {
  flex: 1;
  min-height: 100%;
  display: flex;
  flex-direction: column;
}

.server-tabs {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.right-content { position: relative; }
.loading-content { position: absolute; inset: 0; display: grid; place-items: center; }
.loading-inner { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.loading-text { font-size: 13px; color: #666; }
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
