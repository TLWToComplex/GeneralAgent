// 应用常量配置文件

// 应用名称
import { getSystemName } from '@/utils/RuntimeConfig';
export const APP_NAME = getSystemName();

// 本地存储键名
export const STORAGE_KEYS = {
  NEED_UPDATE_MSG: 'mcp-need-update-msg',
  OPEN_ADD_SERVER_MODAL: 'mcp-open-add-modal',
  LAST_SETTINGS_SUB_PAGE: 'mcp-last-settings-sub-page'
};

// 路由路径
export const ROUTES = {
  HOME: '/',
  WELCOME: '/welcome',
  CHAT: '/chat',
  SETTINGS: '/settings',
  MODEL_SERVICE: '/settings/model-service',
  MCP_SERVER: '/settings/mcp-server',
  CHAT_PREFERENCES: '/settings/chat-preferences',
  ROLE_SETTINGS: '/settings/role-settings',
  KNOWLEDGE_BASE: '/settings/knowledge-base',
  RULE_SKILL_SETTINGS: '/settings/rule-skill-settings',
  USER_MANAGEMENT: '/settings/user-management',
  ACCOUNT: '/account',
  NOT_FOUND: '/404',
  AUTH: '/auth',
  LOGIN: '/login',
  REGISTER: '/register'
};

// 页面基础标题
export const PAGE_BASE_TITLES = {
  HOME: '首页',
  WELCOME: '欢迎',
  CHAT: '对话',
  SETTINGS: '设置',
  MODEL_SERVICE: '模型服务设置',
  MCP_SERVER: '服务器设置',
  CHAT_PREFERENCES: '聊天偏好设置',
  ROLE_SETTINGS: '角色设置',
  KNOWLEDGE_BASE: '知识库',
  RULE_SKILL_SETTINGS: '技能',
  USER_MANAGEMENT: '用户管理',
  ACCOUNT: '账户',
  NOT_FOUND: '页面未找到',
  AUTH: '登录/注册',
  LOGIN: '登录',
  REGISTER: '注册'
} as const;

// 页面标题（带应用前缀）
export const PAGE_TITLES = {
  HOME: `${APP_NAME} - ${PAGE_BASE_TITLES.HOME}`,
  WELCOME: `${APP_NAME} - ${PAGE_BASE_TITLES.WELCOME}`,
  CHAT: `${APP_NAME} - ${PAGE_BASE_TITLES.CHAT}`,
  SETTINGS: `${APP_NAME} - ${PAGE_BASE_TITLES.SETTINGS}`,
  MODEL_SERVICE: `${APP_NAME} - ${PAGE_BASE_TITLES.MODEL_SERVICE}`,
  MCP_SERVER: `${APP_NAME} - ${PAGE_BASE_TITLES.MCP_SERVER}`,
  CHAT_PREFERENCES: `${APP_NAME} - ${PAGE_BASE_TITLES.CHAT_PREFERENCES}`,
  ROLE_SETTINGS: `${APP_NAME} - ${PAGE_BASE_TITLES.ROLE_SETTINGS}`,
  KNOWLEDGE_BASE: `${APP_NAME} - ${PAGE_BASE_TITLES.KNOWLEDGE_BASE}`,
  RULE_SKILL_SETTINGS: `${APP_NAME} - ${PAGE_BASE_TITLES.RULE_SKILL_SETTINGS}`,
  USER_MANAGEMENT: `${APP_NAME} - ${PAGE_BASE_TITLES.USER_MANAGEMENT}`,
  ACCOUNT: `${APP_NAME} - ${PAGE_BASE_TITLES.ACCOUNT}`,
  NOT_FOUND: `${APP_NAME} - ${PAGE_BASE_TITLES.NOT_FOUND}`,
  AUTH: `${APP_NAME} - ${PAGE_BASE_TITLES.AUTH}`,
  LOGIN: `${APP_NAME} - ${PAGE_BASE_TITLES.LOGIN}`,
  REGISTER: `${APP_NAME} - ${PAGE_BASE_TITLES.REGISTER}`
} as const;

// 事件名称
export const EVENTS = {
  OPEN_MODEL_SELECTOR: 'open-model-selector'
};
