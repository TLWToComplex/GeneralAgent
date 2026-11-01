<template>
  <div class="config-section">
    <div class="agent-model-section-header">
      <h3 style="display: flex; align-items: center;">
        MCP服务器设置
        <a-tooltip placement="top" title="默认启用的MCP服务器">
          <InfoCircleOutlined style="margin-left: 5px; color: rgb(61 61 61); font-size: 14px;" />
        </a-tooltip>
      </h3>
      <p>配置智能体使用的MCP服务器</p>
    </div>
    <div class="form-content">
      <!-- 现有MCP服务器列表 -->
      <div class="mcp-servers-container">
        <div class="mcp-servers-content">
          <div v-if="localServerList.length === 0" class="empty-servers">
            <p>暂无可用的MCP服务器</p>
          </div>
          <div v-else class="mcp-servers-grid">
            <div v-for="server in localServerList" :key="server.id" class="mcp-server-card" :class="{ 'connected': isServerEnabled(server.id), 'agent-server': true }">
              <!-- 卡片头部 -->
              <div class="mcp-server-header">
                <div class="mcp-server-avatar">
                  <a-avatar :style="{ backgroundColor: isServerEnabled(server.id) ? '#b2ebf2' : '#d9d9d9', color: '#fff' }">
                    {{ server.name ? server.name.charAt(0).toUpperCase() : 'M' }}
                  </a-avatar>
                </div>
                <div class="mcp-server-info">
                  <div class="mcp-server-name">{{ server.name }}</div>
                  <div class="mcp-server-url" :title="server.url">{{ server.url }}</div>
                </div>
                <div class="mcp-server-switch">
                  <a-switch :checked="isServerEnabled(server.id)" @change="() => toggleServer(server.id)"/>
                </div>
              </div>

              <!-- 底部信息栏 -->
              <div class="mcp-server-footer">
                <div class="mcp-server-type">
                  <span class="type-label">连接类型:</span>
                  <span class="type-value">{{ server.type || '未知类型' }}</span>
                </div>
                <div class="mcp-server-tools">
                  <span class="tools-count">工具数量: {{ server.fullToolInfo ? server.fullToolInfo.length : server.tools.length }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { InfoCircleOutlined } from '@ant-design/icons-vue';
import { useChatStore } from '@/stores/chat-store';

// 定义接口
interface LocalServerInfo {
  id: string;
  name: string;
  url: string;
  tools: string[];
  connected: boolean;
  reconnecting?: boolean;
  fullToolInfo?: any[];
  type?: string;
}

interface ToolInfo {
  id: string;
  name: string;
  description: string;
  parameters?: Record<string, any>;
}

interface MCPConfig {
  // 使用服务器名称和URL的组合作为唯一标识符，处理名称重复的情况
  enabledServerIdentifiers: string[];
}

interface FormErrors {
  name: boolean;
  description: boolean;
  modelService: boolean;
  modelName: boolean;
}

interface Props {
  mcpConfig: MCPConfig;
  formErrors: FormErrors;
  editMode: boolean;
}

interface Emits {
  (e: 'update:mcpConfig', value: MCPConfig): void;
  (e: 'update:errors', value: Partial<FormErrors>): void;
}

// 组件属性和事件
const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// 使用chatStore获取服务器列表
const chatStore = useChatStore();

// 本地服务器列表
const localServerList = ref<LocalServerInfo[]>([]);

// 本地存储键
const SERVERS_STORAGE_KEY = 'mcp-servers-list';
const SERVER_DATA_STORAGE_KEY = 'mcp-servers-data';

// 辅助函数：通过名称查找服务器数据，处理键名可能不一致的情况
function findServerDataByName(parsedData: Record<string, any>, name: string): any {
  // 尝试直接匹配
  if (parsedData[name]) {
    return parsedData[name];
  }

  // 遍历所有键，进行模糊匹配
  for (const key in parsedData) {
    if (key.includes(name) || name.includes(key)) {
      return parsedData[key];
    }
  }

  return null;
}

// 加载本地存储的服务器配置
const loadLocalServers = async () => {
  try {
    // 从本地存储加载服务器列表
    const serversList = localStorage.getItem(SERVERS_STORAGE_KEY);
    const serversData = localStorage.getItem(SERVER_DATA_STORAGE_KEY);

    if (serversList && serversData) {
      try {
        const parsedList = JSON.parse(serversList);
        const parsedData = JSON.parse(serversData);

        // 将服务器列表与chatStore中的服务器状态合并
          localServerList.value = parsedList.map((item: { id?: string; name: string }) => {
            // 检查item是否有id，如果有则使用id作为键，否则回退到使用name
            const serverKey = item.id || item.name;
            
            // 特殊处理，因为JSON.parse后键可能会有空格或特殊字符
            const serverData = parsedData[serverKey] || findServerDataByName(parsedData, item.name);
            if (!serverData) {
              return null;
            }

            // 从本地存储获取工具信息
            const localTools = serverData.tools || [];

            // 格式化工具列表，提取工具名称
            const toolNames = localTools.map((tool: ToolInfo) => tool.name || tool.id || '未知工具');

            // 使用服务器数据中的id（如果有），否则使用名称和URL组合作为唯一ID
            const uniqueId = serverData.id || (item.id ? item.id : `${item.name}|${serverData.url}`);

            return {
              id: uniqueId,
              name: item.name,
              url: serverData.url,
              tools: toolNames,
              connected: false,
              reconnecting: false,
              fullToolInfo: localTools,
              type: serverData.type || 'default'
            };
        }).filter(Boolean);

        // 不再默认启用所有服务器，保持为空数组表示默认关闭所有服务
        // 让用户手动选择要启用的服务

      } catch (parseError) {
        console.error('解析本地存储数据失败:', parseError);
      }
    } else {
      // 本地存储中没有服务器配置
    }
  } catch (error) {
    console.error('加载本地服务器配置失败:', error);
  }
};

// 检查服务器是否启用
const isServerEnabled = (serverId: string): boolean => {
  return props.mcpConfig.enabledServerIdentifiers.includes(serverId);
};

// 切换服务器启用状态
const toggleServer = (serverId: string) => {
  const updatedIdentifiers = [...props.mcpConfig.enabledServerIdentifiers];
  const index = updatedIdentifiers.indexOf(serverId);
  
  if (index > -1) {
    // 如果已启用，则移除
    updatedIdentifiers.splice(index, 1);
  } else {
    // 如果未启用，则添加
    updatedIdentifiers.push(serverId);
  }
  
  emit('update:mcpConfig', {
    ...props.mcpConfig,
    enabledServerIdentifiers: updatedIdentifiers
  });
  
  // 重置对话历史
  chatStore.clearChat();
};

const handleServerConfigChanged = () => {
  void loadLocalServers();
};

// 组件挂载时加载服务器配置
onMounted(() => {
  void loadLocalServers();
  document.addEventListener('mcp-server-config-changed', handleServerConfigChanged);
});

onUnmounted(() => {
  document.removeEventListener('mcp-server-config-changed', handleServerConfigChanged);
});
</script>
